from datetime import date, datetime, time, timedelta, timezone
from dataclasses import replace
from decimal import Decimal

import pytest

from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.historical_daily_bar_authority import (
    HistoricalDailyBarFactReaderV1,
    HistoricalDailyBarFactShardV1,
    HistoricalDailyBarFactAuthorityV1,
    HistoricalDailyBarAuthorityError,
)


def _fact(symbol="000001.SZ", day=date(2025, 1, 2)):
    return DailyBarFactV1.create(
        source_symbol=symbol, session=day, open=Decimal("10"), high=Decimal("11"),
        low=Decimal("9"), close=Decimal("10.5"), raw_volume=Decimal("2"),
        raw_amount=Decimal("3"), source_payload_hash="a" * 64,
        available_at=datetime.combine(day + timedelta(days=1), time(16, 30),
                                      timezone(timedelta(hours=8))),
        availability_policy_version="daily-bar-availability-v1",
    )


def _authority(tmp_path, facts):
    shard = HistoricalDailyBarFactShardV1.create("2025-01", facts)
    shard.write_exact(tmp_path)
    return HistoricalDailyBarFactAuthorityV1.create(
        parent_panel_id="p" * 64, parent_approval_id="a" * 64,
        parent_manifest_id="m" * 64, source_binding_id="b" * 64,
        source_content_set_id="c" * 64, availability_evidence_id="e" * 64,
        calendar_lineage_id="l" * 64, normalization_policy_id="n" * 64,
        unit_policy_id="u" * 64, identity_policy_id="i" * 64,
        raw_payload_hashes=("a" * 64,), shards=(shard.descriptor,),
        coverage_start="2025-01-01", coverage_end="2025-01-31",
        symbol_count=1,
    )


def test_exact_lookup_and_bounded_month_read_use_portable_shard(tmp_path):
    fact = _fact()
    authority = _authority(tmp_path, (fact,))
    reader = HistoricalDailyBarFactReaderV1(tmp_path, authority,
                                             expected_manifest_id=authority.manifest_id,
                                             revoked_approval_ids=())
    assert reader.lookup("000001.SZ", date(2025, 1, 2)).fact_id == fact.fact_id
    assert [row.fact_id for row in reader.read_month("2025-01")] == [fact.fact_id]
    assert authority.symbol_count == 1


def test_tampered_shard_and_revoked_approval_fail_closed(tmp_path):
    authority = _authority(tmp_path, (_fact(),))
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactReaderV1(tmp_path, authority,
            expected_manifest_id=authority.manifest_id,
            revoked_approval_ids=(authority.approval_id,))
    path = tmp_path / authority.shards[0].path
    path.write_bytes(path.read_bytes() + b"x")
    reader = HistoricalDailyBarFactReaderV1(tmp_path, authority,
        expected_manifest_id=authority.manifest_id, revoked_approval_ids=())
    with pytest.raises(HistoricalDailyBarAuthorityError):
        reader.lookup("000001.SZ", date(2025, 1, 2))


def test_extra_shard_is_not_silently_accepted(tmp_path):
    authority = _authority(tmp_path, (_fact(),))
    extra = tmp_path / "shards" / "2025-01" / ("f" * 64 + ".jsonl.gz")
    extra.write_bytes(b"unapproved")
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactReaderV1(tmp_path, authority,
            expected_manifest_id=authority.manifest_id, revoked_approval_ids=())


def test_missing_shard_wrong_manifest_and_out_of_coverage_fail_closed(tmp_path):
    authority = _authority(tmp_path, (_fact(),))
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactReaderV1(
            tmp_path, authority, expected_manifest_id="wrong", revoked_approval_ids=())
    reader = HistoricalDailyBarFactReaderV1(
        tmp_path, authority, expected_manifest_id=authority.manifest_id,
        revoked_approval_ids=())
    with pytest.raises(HistoricalDailyBarAuthorityError):
        reader.lookup("000001.SZ", date(2024, 12, 31))
    with pytest.raises(HistoricalDailyBarAuthorityError):
        reader.lookup("unknown", date(2025, 1, 2))
    (tmp_path / authority.shards[0].path).unlink()
    with pytest.raises(HistoricalDailyBarAuthorityError):
        reader.read_month("2025-01")


def test_duplicate_key_and_fact_id_cannot_enter_shard(tmp_path):
    same = _fact()
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactShardV1.create("2025-01", (same, same))
    authority = _authority(tmp_path, (same,))
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactReaderV1(
            tmp_path, replace(authority, membership_set_hash="wrong"),
            expected_manifest_id=authority.manifest_id, revoked_approval_ids=())


def test_authority_requires_exact_content_address_on_reload(tmp_path):
    authority = _authority(tmp_path, (_fact(),))
    authority.write_exact(tmp_path)
    assert HistoricalDailyBarFactAuthorityV1.load_exact(tmp_path, authority.authority_id) == authority
    path = tmp_path / "governance" / f"historical-daily-bar-fact-authority-{authority.authority_id}.json"
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactAuthorityV1.load_exact(tmp_path, authority.authority_id)


def test_month_window_reads_only_required_months(tmp_path):
    january = _fact(day=date(2025, 1, 31))
    february = _fact(day=date(2025, 2, 3))
    shards = tuple(HistoricalDailyBarFactShardV1.create(month, (fact,))
                   for month, fact in (("2025-01", january), ("2025-02", february)))
    for shard in shards:
        shard.write_exact(tmp_path)
    authority = HistoricalDailyBarFactAuthorityV1.create(
        parent_panel_id="p" * 64, parent_approval_id="a" * 64,
        parent_manifest_id="m" * 64, source_binding_id="b" * 64,
        source_content_set_id="c" * 64, availability_evidence_id="e" * 64,
        calendar_lineage_id="l" * 64, normalization_policy_id="n" * 64,
        unit_policy_id="u" * 64, identity_policy_id="i" * 64,
        raw_payload_hashes=("a" * 64,),
        shards=tuple(shard.descriptor for shard in shards),
        coverage_start="2025-01-01", coverage_end="2025-02-28", symbol_count=1,
    )
    reader = HistoricalDailyBarFactReaderV1(tmp_path, authority,
        expected_manifest_id=authority.manifest_id, revoked_approval_ids=())
    assert [item.fact_id for item in reader.read_window("2025-01", date(2025, 2, 3))] == [
        january.fact_id, february.fact_id]
    with pytest.raises(HistoricalDailyBarAuthorityError):
        reader.read_window("2025-01", date(2025, 4, 30))


def test_d15_fact_cannot_enter_portable_membership():
    old = DailyBarFactV1.create(
        source_symbol="000001.SZ", session=date(2025, 1, 2),
        open=Decimal("10"), high=Decimal("11"), low=Decimal("9"), close=Decimal("10.5"),
        raw_volume=Decimal("2"), raw_amount=Decimal("3"), source_payload_hash="a" * 64,
        available_at=datetime(2025, 1, 2, 15, 0, tzinfo=timezone(timedelta(hours=8))),
        availability_policy_version="daily-bar-d-close-v1",
    )
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactShardV1.create("2025-01", (old,))


def test_exact_derived_chain_required_for_research_lookup(tmp_path):
    authority = _authority(tmp_path, (_fact(),))
    authority.write_exact(tmp_path)
    ledger_body = {"schema_version": "HistoricalDailyBarCoverageLedgerV1",
                   "authority_id": authority.authority_id,
                   "parent_panel_id": authority.parent_panel_id,
                   "observed_rows": authority.row_count,
                   "symbol_count": authority.symbol_count}
    ledger_id = content_hash(ledger_body)
    ledger = {**ledger_body, "ledger_id": ledger_id, "content_hash": ledger_id}
    approval_body = {"schema_version": "HistoricalDailyBarRepresentationApprovalV1",
                     "decision": "APPROVED_WITH_RULES", "parent_approval_id": authority.parent_approval_id,
                     "authority_id": authority.authority_id,
                     "source_content_set_id": authority.source_content_set_id,
                     "scope": "PORTABLE_ROW_LEVEL_REPRESENTATION_OF_APPROVED_HISTORICAL_DAILY_BAR_TRUTH",
                     "parent_panel_id": authority.parent_panel_id,
                     "availability_evidence_id": authority.availability_evidence_id,
                     "coverage_ledger_id": ledger_id}
    approval_id = content_hash(approval_body)
    approval = {**approval_body, "approval_id": approval_id, "content_hash": approval_id}
    manifest_body = {"schema_version": "HistoricalDailyBarRepresentationManifestV1",
                     "parent_manifest_id": authority.parent_manifest_id,
                     "approval_id": approval_id, "authority_id": authority.authority_id,
                     "coverage_ledger_id": ledger_id,
                     "membership_set_hash": authority.membership_set_hash,
                     "row_count": authority.row_count, "symbol_count": authority.symbol_count,
                     "coverage_start": authority.coverage_start,
                     "coverage_end": authority.coverage_end,
                     "availability_policy_version": "daily-bar-availability-v1:NEXT_SESSION_SAFE",
                     "shard_storage_hashes": [item.storage_hash for item in authority.shards]}
    manifest_id = content_hash(manifest_body)
    manifest = {**manifest_body, "manifest_id": manifest_id, "content_hash": manifest_id}
    governance = tmp_path / "governance"
    (governance / f"historical-daily-bar-coverage-ledger-{ledger_id}.json").write_bytes(canonical_json(ledger))
    (governance / f"historical-daily-bar-representation-approval-{approval_id}.json").write_bytes(canonical_json(approval))
    (governance / f"historical-daily-bar-representation-manifest-{manifest_id}.json").write_bytes(canonical_json(manifest))
    reader = HistoricalDailyBarFactReaderV1.load_exact(
        tmp_path, authority_id=authority.authority_id,
        approval_id=approval_id, manifest_id=manifest_id, revoked_approval_ids=())
    resolved = reader.resolve("000001.SZ", date(2025, 1, 2))
    assert resolved["fact_id"] == _fact().fact_id
    assert resolved["authority_id"] == authority.authority_id
    assert resolved["approval_id"] == approval_id
    assert resolved["manifest_id"] == manifest_id
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactReaderV1.load_exact(
            tmp_path, authority_id=authority.authority_id,
            approval_id=approval_id, manifest_id=manifest_id,
            revoked_approval_ids=(approval_id,))
    (governance / f"historical-daily-bar-coverage-ledger-{ledger_id}.json").write_bytes(b"tampered")
    with pytest.raises(HistoricalDailyBarAuthorityError):
        HistoricalDailyBarFactReaderV1.load_exact(
            tmp_path, authority_id=authority.authority_id,
            approval_id=approval_id, manifest_id=manifest_id,
            revoked_approval_ids=())
