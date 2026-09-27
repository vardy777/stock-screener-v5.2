"""Delisting effective time is distinct from later PIT knowledge time."""

from pathlib import Path

import pytest

from v5_2.labels.phase2b_delisting_safety_v2 import (
    derive_delisting_safety_evidence_exact, read_delisting_safety_evidence_exact,
    write_delisting_safety_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


def test_delisting_effective_boundary_and_scoped_quarantine_are_exact(tmp_path):
    evidence = derive_delisting_safety_evidence_exact(ROOT)
    assert evidence.verify()
    assert evidence.effective_date == "2023-08-04"
    assert evidence.available_at.startswith("2023-08-07T16:30:00")
    assert evidence.real_scope_reason == "UNEXPLAINED_MISSING_BAR"
    assert evidence.fixture_kind == "FROZEN_PHASE2A_CONTRACT_FIXTURE"
    assert evidence.correct_reason == "DELISTING_IN_HORIZON"
    assert evidence.ignored_boundary_reason != evidence.correct_reason
    path = write_delisting_safety_evidence(tmp_path, evidence)
    assert read_delisting_safety_evidence_exact(path, evidence.evidence_id) == evidence
    with pytest.raises(ValueError):
        read_delisting_safety_evidence_exact(path, "f" * 64)
