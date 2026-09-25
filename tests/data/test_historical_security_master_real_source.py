"""Portable, source-pinned 5,551-member Master corpus acceptance."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import shutil

import pytest

from v5_2.data.historical_security_master_authority import (
    HistoricalMasterTypingError,
    load_verified_master_source,
    publish_verified_master_source,
    HistoricalSecurityMasterReaderV1,
)


SOURCE = Path(__file__).resolve().parents[2] / "data/phase_1b_historical_master_portable/source"
pytestmark = pytest.mark.skipif(not SOURCE.is_dir(), reason="explicit portable Master source corpus required")


def test_real_source_inventory_matches_approved_parent_and_keeps_scoped_gaps():
    verified = load_verified_master_source(SOURCE)
    assert verified.parent_membership_count == 5551
    assert verified.parent_input_count == 5898
    assert verified.parent_excluded_non_target_count == 347
    assert len(verified.pages) == 16
    assert verified.derived.resolved_count == 5549
    assert [(item.security_identity, item.reason) for item in verified.derived.quarantines] == [
        ("689009.SH", "UNRESOLVED_MASTER_IDENTITY"),
        ("T600018.SH", "UNRESOLVED_MASTER_IDENTITY"),
    ]
    assert verified.bridge.effective_identity_graph_ids == (
        "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0",
    )
    assert verified.bridge.historical_universe_supplement_ids == (
        "d67d886299be85bb5585c9103140ef327fe13b78161903f7e5120646a8ee9e8f",
    )
    assert verified.supplement_scoped_quarantine == "600747.SH"


def test_four_frozen_phase1b_universe_regressions_are_exact_or_scoped():
    derived = load_verified_master_source(SOURCE).derived
    for session, frozen, resolved, scoped in (
        (date(2012, 6, 29), 2421, 2421, ()),
        (date(2018, 6, 29), 3529, 3529, ()),
        (date(2025, 6, 30), 5152, 5151, ("689009.SH",)),
        (date(2026, 6, 30), 5205, 5204, ("689009.SH",)),
    ):
        eligible = {fact.provider_identity for fact in derived.facts
                    if any(interval.effective_from <= session and
                           (interval.effective_to is None or session <= interval.effective_to)
                           for interval in fact.intervals)}
        quarantined = tuple(item.security_identity for item in derived.quarantines
                            if item.affected_from and
                            date.fromisoformat(f"{item.affected_from[:4]}-{item.affected_from[4:6]}-{item.affected_from[6:]}") <= session and
                            (item.affected_to is None or session <=
                             date.fromisoformat(f"{item.affected_to[:4]}-{item.affected_to[4:6]}-{item.affected_to[6:]}")))
        assert len(eligible) == resolved
        assert quarantined == scoped
        assert len(eligible) + len(quarantined) == frozen


def test_missing_raw_page_is_systemic_not_a_security_quarantine(tmp_path):
    copied = tmp_path / "source"
    shutil.copytree(SOURCE, copied)
    raw = sorted((copied / "raw").glob("*.json"))[0]
    raw.unlink()
    with pytest.raises(HistoricalMasterTypingError, match="source corpus file inventory"):
        load_verified_master_source(copied)


def test_semantically_equal_but_byte_changed_raw_source_fails_import_inventory(tmp_path):
    copied = tmp_path / "source"
    shutil.copytree(SOURCE, copied)
    raw = sorted((copied / "raw").glob("*.json"))[0]
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(HistoricalMasterTypingError, match="source corpus byte"):
        load_verified_master_source(copied)


def test_revocation_registry_is_verified_from_exact_source():
    verified = load_verified_master_source(SOURCE)
    assert len(verified.revoked_approval_ids) == 2
    assert "50777e6ca46c0149885f0218291a0ce539f36cbfc1ef71e6e56a9f8131a12eee" in verified.revoked_approval_ids


def test_revocation_artifact_tampering_fails_closed(tmp_path):
    copied = tmp_path / "source"
    shutil.copytree(SOURCE, copied)
    revocation = sorted((copied / "governance").glob("approval-revocation-*.json"))[0]
    revocation.write_bytes(revocation.read_bytes() + b" ")
    with pytest.raises(HistoricalMasterTypingError, match="source corpus byte"):
        load_verified_master_source(copied)


def test_real_source_publishes_immutable_portable_authority_and_replays(tmp_path):
    first = publish_verified_master_source(SOURCE, tmp_path)
    second = publish_verified_master_source(SOURCE, tmp_path)
    assert first == second
    assert first.membership_count == 5551
    assert first.resolved_count == 5549
    assert first.quarantine_count == 2
    reader = HistoricalSecurityMasterReaderV1.load_exact(
        tmp_path, authority_id=first.authority_id, approval_id=first.approval_id,
        manifest_id=first.manifest_id, coverage_ledger_id=first.coverage_ledger_id,
        revoked_approval_ids=load_verified_master_source(SOURCE).revoked_approval_ids,
    )
    assert reader.resolve("300114.SZ", date(2014, 1, 2)).effective_identity == "300114.SZ"
    assert reader.resolve("302132.SZ", date(2025, 2, 17)).effective_identity == "302132.SZ"
    with pytest.raises(HistoricalMasterTypingError, match="scoped quarantine"):
        reader.resolve("689009.SH", date(2025, 1, 2))
    with pytest.raises(HistoricalMasterTypingError, match="revocation registry"):
        publish_verified_master_source(SOURCE, tmp_path,
            revoked_approval_ids=("a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f",))


def test_formal_reader_rechecks_physical_source_and_replay(tmp_path):
    published = publish_verified_master_source(SOURCE, tmp_path)
    reader = HistoricalSecurityMasterReaderV1.load_formal_exact(
        SOURCE, tmp_path, authority_id=published.authority_id,
        approval_id=published.approval_id, manifest_id=published.manifest_id,
        coverage_ledger_id=published.coverage_ledger_id,
    )
    assert reader.resolve("000001.SZ", date(2012, 6, 29)).authority_id == published.authority_id
    replay = tmp_path / "governance" / f"historical-security-master-replay-{published.replay_evidence_id}.json"
    replay.write_bytes(replay.read_bytes() + b" ")
    with pytest.raises(HistoricalMasterTypingError, match="ReplayEvidence"):
        HistoricalSecurityMasterReaderV1.load_formal_exact(
            SOURCE, tmp_path, authority_id=published.authority_id,
            approval_id=published.approval_id, manifest_id=published.manifest_id,
            coverage_ledger_id=published.coverage_ledger_id,
        )
