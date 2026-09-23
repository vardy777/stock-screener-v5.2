from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib

import pytest

from v5_2.data.identity import canonical_json

from v5_2.data.historical_status_authority import (
    HistoricalStatusAuthorityError,
    HistoricalStatusAuthorityV1,
    HistoricalStatusComponentV1,
    HistoricalStatusShardStore,
    HistoricalStatusResolverV1,
    ensure_repository_local_staging,
    normalize_status_rows,
    publish_portable_status_authority,
    create_derived_status_governance,
    HistoricalStatusCoverageLedgerV1,
    require_exact_hash_inventory,
)

ZONE = timezone(timedelta(hours=8))


PANEL = "a" * 64
MANIFEST = "b" * 64
APPROVAL = "c" * 64
PIT = "d" * 64
SOURCE_VERSION = "e" * 64


def _component(*, source_row_hash="1" * 64, component_kind="LIFECYCLE"):
    return HistoricalStatusComponentV1.create(
        component_kind=component_kind,
        canonical_security_identity="000001.SZ",
        effective_from=date(2010, 1, 4),
        effective_to=None,
        event_session=None,
        source_row_hash=source_row_hash,
        availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
        availability_input_date=date(2010, 1, 4),
        source_fields={"list_date": "20100104"},
    )


def test_deterministic_shard_bytes_are_canonical_gzip(tmp_path):
    component = _component()
    first = HistoricalStatusShardStore(tmp_path / "one").encode(
        "LIFECYCLE", (component,)
    )
    second = HistoricalStatusShardStore(tmp_path / "two").encode(
        "LIFECYCLE", (component,)
    )

    assert first.compressed_bytes == second.compressed_bytes
    assert first.storage_hash == hashlib.sha256(first.compressed_bytes).hexdigest()
    assert first.content_hash == "c6a898193d4b08c5b549e36f8f4bd33d23f8b264b3ac5fff5a214e8a3e7f997b"
    assert gzip.decompress(first.compressed_bytes).startswith(b'{"component_kind":"LIFECYCLE"')


def test_shard_store_is_create_or_identical_and_detects_wrong_bytes(tmp_path):
    store = HistoricalStatusShardStore(tmp_path)
    encoded = store.encode("LIFECYCLE", (_component(),))
    path = store.put(encoded)

    assert store.put(encoded) == path
    path.write_bytes(b"tampered")
    with pytest.raises(HistoricalStatusAuthorityError, match="collision"):
        store.put(encoded)
    with pytest.raises(HistoricalStatusAuthorityError, match="storage hash"):
        store.read(path, expected=encoded.descriptor)


def test_shard_rejects_wrong_kind_and_duplicate_source_row_identity(tmp_path):
    store = HistoricalStatusShardStore(tmp_path)
    lifecycle = _component()
    risk = _component(component_kind="RISK_WARNING")

    with pytest.raises(HistoricalStatusAuthorityError, match="component kind"):
        store.encode("LIFECYCLE", (risk,))
    with pytest.raises(HistoricalStatusAuthorityError, match="duplicate source row"):
        store.encode("LIFECYCLE", (lifecycle, lifecycle))


def test_authority_verification_pins_every_parent_inventory_and_shard(tmp_path):
    encoded = HistoricalStatusShardStore(tmp_path).encode(
        "LIFECYCLE", (_component(),)
    )
    authority = HistoricalStatusAuthorityV1.create(
        coverage_start=date(2010, 1, 4),
        coverage_end=date(2026, 9, 10),
        parent_panel_id=PANEL,
        parent_manifest_id=MANIFEST,
        parent_approval_id=APPROVAL,
        pit_evidence_id=PIT,
        source_version_identity=SOURCE_VERSION,
        raw_payload_hashes=("2" * 64,),
        receipt_hashes=("3" * 64,),
        request_inventory_id="4" * 64,
        shard_descriptors=(encoded.descriptor,),
        authority_policy_version="historical-status-authority-v1",
    )

    assert authority.verify()
    assert authority.parent_panel_id == PANEL
    assert authority.shard_descriptors == (encoded.descriptor,)

    tampered = replace(authority, parent_panel_id="f" * 64)
    assert not tampered.verify()


@pytest.mark.parametrize(
    ("actual", "message"),
    [
        (("a" * 64,), "missing"),
        (("a" * 64, "b" * 64, "c" * 64), "extra"),
        (("a" * 64, "a" * 64, "b" * 64), "duplicate"),
    ],
)
def test_exact_inventory_rejects_missing_extra_and_duplicate(actual, message):
    with pytest.raises(HistoricalStatusAuthorityError, match=message):
        require_exact_hash_inventory(
            name="raw payload", actual=actual, expected=("a" * 64, "b" * 64)
        )


def test_staging_must_resolve_inside_repository(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    staging = repository / "data" / "stage"
    staging.mkdir(parents=True)
    assert ensure_repository_local_staging(repository, staging) == staging.resolve()
    with pytest.raises(HistoricalStatusAuthorityError, match="repository-local"):
        ensure_repository_local_staging(repository, tmp_path / "outside")


def test_normalization_preserves_source_hash_and_status_semantics():
    lifecycle, risk, suspension = normalize_status_rows(
        lifecycle_rows=({"ts_code": "000001.SZ", "list_date": "20100104", "delist_date": None},),
        namechange_rows=(
            {"ts_code": "000001.SZ", "name": "ST测试", "start_date": "20110103", "end_date": "20110104", "ann_date": "20110103"},
        ),
        suspension_rows=(
            {"ts_code": "000001.SZ", "trade_date": "20120104", "suspend_type": "S", "suspend_timing": ""},
            {"ts_code": "000001.SZ", "trade_date": "20120105", "suspend_type": "S", "suspend_timing": "09:30-10:30"},
            {"ts_code": "000001.SZ", "trade_date": "20120106", "suspend_type": "R", "suspend_timing": ""},
        ),
    )
    assert [item.component_kind for item in lifecycle] == ["LIFECYCLE"]
    assert [item.component_kind for item in risk] == ["RISK_WARNING"]
    assert sorted(item.component_kind for item in suspension) == [
        "FULL_DAY_SUSPENSION", "PARTIAL_SUSPENSION", "RESUMPTION"
    ]
    assert all(len(item.source_row_hash) == 64 for item in lifecycle + risk + suspension)


def _resolver(tmp_path):
    lifecycle, risk, suspension = normalize_status_rows(
        lifecycle_rows=({"ts_code": "000001.SZ", "list_date": "20100104", "delist_date": "20100108"},),
        namechange_rows=({"ts_code": "000001.SZ", "name": "ST测试", "start_date": "20100105", "end_date": "20100106", "ann_date": "20100104"},),
        suspension_rows=(
            {"ts_code": "000001.SZ", "trade_date": "20100106", "suspend_type": "S", "suspend_timing": ""},
            {"ts_code": "000001.SZ", "trade_date": "20100107", "suspend_type": "R", "suspend_timing": ""},
        ),
    )
    store = HistoricalStatusShardStore(tmp_path)
    encoded = tuple(store.encode(kind, values) for kind, values in (
        ("LIFECYCLE", lifecycle),
        ("RISK_WARNING", risk),
        ("FULL_DAY_SUSPENSION", tuple(x for x in suspension if x.component_kind == "FULL_DAY_SUSPENSION")),
        ("RESUMPTION", tuple(x for x in suspension if x.component_kind == "RESUMPTION")),
    ))
    authority = HistoricalStatusAuthorityV1.create(
        coverage_start=date(2010, 1, 4), coverage_end=date(2010, 1, 8),
        parent_panel_id=PANEL, parent_manifest_id=MANIFEST,
        parent_approval_id=APPROVAL, pit_evidence_id=PIT,
        source_version_identity=SOURCE_VERSION,
        raw_payload_hashes=("2" * 64,), receipt_hashes=("3" * 64,),
        request_inventory_id="4" * 64,
        shard_descriptors=tuple(item.descriptor for item in encoded),
        authority_policy_version="historical-status-authority-v1",
    )
    return HistoricalStatusResolverV1(
        authority=authority,
        components=lifecycle + risk + suspension,
        approved_sessions=tuple(date(2010, 1, day) for day in range(4, 9)),
        availability_policy_id=PIT,
    )


def test_resolver_derives_ordinary_with_closed_world_lineage(tmp_path):
    result = _resolver(tmp_path).resolve(
        "000001.SZ", date(2010, 1, 4), datetime(2010, 1, 4, 16, 30, tzinfo=ZONE)
    )
    assert (result.listed, result.delisted, result.risk_warning, result.full_day_suspended) == (
        True, False, False, False
    )
    assert result.lifecycle_component_id
    assert len(result.closed_world_shard_ids) == 3
    assert result.available_at == datetime(2010, 1, 4, 16, 30, tzinfo=ZONE)
    assert result.verify()


def test_resolver_applies_next_session_st_and_same_close_suspension(tmp_path):
    resolver = _resolver(tmp_path)
    before = resolver.resolve(
        "000001.SZ", date(2010, 1, 4), datetime(2010, 1, 4, 16, 30, tzinfo=ZONE)
    )
    st = resolver.resolve(
        "000001.SZ", date(2010, 1, 5), datetime(2010, 1, 5, 16, 30, tzinfo=ZONE)
    )
    suspended = resolver.resolve(
        "000001.SZ", date(2010, 1, 6), datetime(2010, 1, 6, 16, 30, tzinfo=ZONE)
    )
    resumed = resolver.resolve(
        "000001.SZ", date(2010, 1, 7), datetime(2010, 1, 7, 16, 30, tzinfo=ZONE)
    )
    assert not before.risk_warning
    assert st.risk_warning
    assert suspended.full_day_suspended
    assert not resumed.full_day_suspended


def test_resolver_fails_closed_outside_coverage_unknown_or_naive(tmp_path):
    resolver = _resolver(tmp_path)
    with pytest.raises(HistoricalStatusAuthorityError, match="coverage"):
        resolver.resolve("000001.SZ", date(2010, 1, 9), datetime(2010, 1, 9, 16, 30, tzinfo=ZONE))
    with pytest.raises(HistoricalStatusAuthorityError, match="identity"):
        resolver.resolve("UNKNOWN.SZ", date(2010, 1, 5), datetime(2010, 1, 5, 16, 30, tzinfo=ZONE))
    with pytest.raises(HistoricalStatusAuthorityError, match="timezone"):
        resolver.resolve("000001.SZ", date(2010, 1, 5), datetime(2010, 1, 5, 16, 30))


def test_portable_authority_publication_is_byte_identical(tmp_path):
    lifecycle, risk, suspension = normalize_status_rows(
        lifecycle_rows=({"ts_code": "000001.SZ", "list_date": "20100104", "delist_date": None},),
        namechange_rows=({"ts_code": "000001.SZ", "name": "ST测试", "start_date": "20100105", "end_date": "20100106", "ann_date": "20100104"},),
        suspension_rows=({"ts_code": "000001.SZ", "trade_date": "20100106", "suspend_type": "S", "suspend_timing": ""},),
    )
    kwargs = dict(
        components=lifecycle + risk + suspension,
        coverage_start=date(2010, 1, 4), coverage_end=date(2010, 1, 8),
        parent_panel_id=PANEL, parent_manifest_id=MANIFEST,
        parent_approval_id=APPROVAL, pit_evidence_id=PIT,
        source_version_identity=SOURCE_VERSION,
        raw_payload_hashes=("2" * 64,), receipt_hashes=("3" * 64,),
        request_inventory_id="4" * 64,
        authority_policy_version="historical-status-authority-v1",
    )
    first = publish_portable_status_authority(output_root=tmp_path / "one", **kwargs)
    second = publish_portable_status_authority(output_root=tmp_path / "two", **kwargs)

    assert first.authority_id == second.authority_id
    assert {
        path.relative_to(tmp_path / "one"): path.read_bytes()
        for path in (tmp_path / "one").rglob("*") if path.is_file()
    } == {
        path.relative_to(tmp_path / "two"): path.read_bytes()
        for path in (tmp_path / "two").rglob("*") if path.is_file()
    }


def test_shard_descriptor_size_does_not_scale_with_component_count(tmp_path):
    components = tuple(
        _component(source_row_hash=f"{index:064x}") for index in range(1, 1001)
    )
    descriptor = HistoricalStatusShardStore(tmp_path).encode(
        "LIFECYCLE", components
    ).descriptor

    assert len(canonical_json(descriptor)) < 600


def test_derived_governance_approves_representation_not_new_provider_truth(tmp_path):
    component = _component()
    authority = publish_portable_status_authority(
        output_root=tmp_path / "authority", components=(component,),
        coverage_start=date(2010, 1, 4), coverage_end=date(2010, 1, 4),
        parent_panel_id=PANEL, parent_manifest_id=MANIFEST,
        parent_approval_id=APPROVAL, pit_evidence_id=PIT,
        source_version_identity=SOURCE_VERSION,
        raw_payload_hashes=("2" * 64,), receipt_hashes=("3" * 64,),
        request_inventory_id="4" * 64,
        authority_policy_version="historical-status-authority-v1",
    )
    ledger = HistoricalStatusCoverageLedgerV1.create(
        authority_id=authority.authority_id,
        coverage_start=date(2010, 1, 4), coverage_end=date(2010, 1, 4),
        counts={"covered_identities": 1}, unresolved_identities=0,
        unresolved_sessions=0, coverage_gaps=(), quarantine_count=0,
    )
    governance = create_derived_status_governance(
        authority=authority, coverage_ledger=ledger, row_count=1, symbol_count=1,
    )

    assert governance.approval.source_name == "v5_2_historical_status_derivation"
    assert governance.approval.decision.value == "APPROVED_WITH_RULES"
    assert governance.approval.rule_set["representation_of_parent_source_truth"] is True
    assert governance.manifest.approval_id == governance.approval.approval_id
    assert governance.composition.parent_approval_id == APPROVAL
    assert governance.replay.first_output_hash == governance.replay.second_output_hash
