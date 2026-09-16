from datetime import date
from pathlib import Path

import pytest

from v5_2.data.real_audits.phase2a_status_closure import (
    FROZEN_STATUS_SESSIONS,
    audit_existing_status_evidence,
    materialize_status_closure,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent.parent
pytestmark = pytest.mark.skipif(
    not (SOURCE / "data/phase_1b2a/raw").is_dir(),
    reason="canonical immutable Phase 1 raw store is unavailable",
)


def test_existing_approved_status_evidence_proves_all_nine_sessions() -> None:
    audit = audit_existing_status_evidence(ROOT, SOURCE / "data/phase_1b2a")

    assert len(audit.entries) == 9
    assert tuple((entry.security_identity, entry.session) for entry in audit.entries) == FROZEN_STATUS_SESSIONS
    assert all(entry.disposition == "FULL_DAY_SUSPENSION" for entry in audit.entries)
    assert all(entry.raw_hash_pinned and entry.receipt_hash_pinned for entry in audit.entries)
    assert audit.provider_request_count == 0
    assert audit.verify()


def test_status_closure_uses_approved_lineage_and_conservative_cutoff(tmp_path: Path) -> None:
    audit = audit_existing_status_evidence(ROOT, SOURCE / "data/phase_1b2a")
    result = materialize_status_closure(ROOT, audit, tmp_path)

    assert len(result.facts) == 9
    assert all(fact.is_suspended and not fact.is_tradable for fact in result.facts)
    assert all(fact.available_at.hour == 16 and fact.available_at.minute == 30 for fact in result.facts)
    assert result.manifest.approval_id == "60d31609f590cf08f54ff682d5c4de5a987cdb670b13fe33eeb2466389d39edc"
    assert result.manifest.row_count == 9
    assert set(result.manifest.raw_payload_hashes) == {entry.payload_hash for entry in audit.entries}
    assert all(fact.verify() for fact in result.facts)


def test_status_closure_fails_closed_when_raw_payload_is_tampered(tmp_path: Path) -> None:
    audit = audit_existing_status_evidence(ROOT, SOURCE / "data/phase_1b2a")
    broken = SOURCE / "data/phase_1b2a" / audit.entries[0].raw_artifact_path
    data = broken.read_bytes()
    copy = tmp_path / "phase_1b2a"
    target = copy / broken.relative_to(SOURCE / "data/phase_1b2a")
    target.parent.mkdir(parents=True)
    target.write_bytes(data.replace(b'"suspend_type":"S"', b'"suspend_type":"R"', 1))

    with pytest.raises(RuntimeError, match="missing or tampered"):
        audit_existing_status_evidence(ROOT, copy)


def test_frozen_anchor_suspension_removes_real_bar_gap() -> None:
    audit = audit_existing_status_evidence(ROOT, SOURCE / "data/phase_1b2a")
    entry = next(item for item in audit.entries if item.security_identity == "300131.SZ")

    assert entry.session == date(2014, 9, 11)
    assert entry.disposition == "FULL_DAY_SUSPENSION"
