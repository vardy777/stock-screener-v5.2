"""Two fresh offline month replays must yield identical canonical truth."""

import os
from pathlib import Path
from dataclasses import replace

import pytest

from v5_2.labels.phase2b_replay_gate_v2 import (
    SourcePinnedReplayEvidenceV2, derive_replay_evidence_exact, read_replay_evidence_exact,
    replay_binds_evaluated_sources,
    write_replay_evidence,
)
from v5_2.data.identity import content_hash


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


def test_replay_envelope_rejects_single_run_and_divergent_ids(tmp_path):
    common = "a" * 64
    body = dict(month="2010-01", partition_ids=(common, common),
                candidate_set_hashes=(common, common),
                coverage_evidence_ids=(common, common),
                scoped_ledger_ids=(common, common),
                row_set_hashes=(common, common),
                row_comparison_ledger_id=common)
    evidence = SourcePinnedReplayEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "SourcePinnedReplayEvidenceV2", **body}))
    assert evidence.verify()
    path = write_replay_evidence(tmp_path, evidence)
    assert read_replay_evidence_exact(path, evidence.evidence_id) == evidence
    binding = dict(partition_id=common, candidate_set_hash=common,
                   coverage_id=common, scoped_ledger_id=common,
                   comparison_ledger_id=common)
    assert replay_binds_evaluated_sources(evidence, **binding)
    assert not replay_binds_evaluated_sources(
        evidence, **(binding | {"partition_id": "b" * 64}))
    assert not replay_binds_evaluated_sources(
        evidence, **(binding | {"coverage_id": "b" * 64}))
    assert not replay_binds_evaluated_sources(
        evidence, **(binding | {"comparison_ledger_id": "b" * 64}))
    assert not replace(evidence, partition_ids=(common, "b" * 64)).verify()
    assert not replace(evidence, row_set_hashes=(common,)).verify()
    with pytest.raises(ValueError):
        read_replay_evidence_exact(path, "b" * 64)


@pytest.mark.skipif(os.environ.get("V52_REAL_MONTH_REPLAY") != "1",
                    reason="explicit two-run real-month replay required")
def test_two_fresh_real_month_runs_are_canonically_identical(tmp_path):
    evidence = derive_replay_evidence_exact(ROOT, tmp_path)
    assert evidence.verify()
    assert evidence.partition_ids == (
        "3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9",) * 2
    assert len(set(evidence.candidate_set_hashes)) == 1
    assert len(set(evidence.coverage_evidence_ids)) == 1
    assert len(set(evidence.scoped_ledger_ids)) == 1
    assert len(set(evidence.row_set_hashes)) == 1
    assert evidence.row_comparison_ledger_id == (
        "c3b16aa0f7618e702e5bcab8b977b1919a75f72c5d65795576a1eeb74dd0bca8")
    path = write_replay_evidence(tmp_path, evidence)
    assert read_replay_evidence_exact(path, evidence.evidence_id) == evidence
    with pytest.raises(ValueError):
        read_replay_evidence_exact(path, "f" * 64)
