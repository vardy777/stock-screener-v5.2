from copy import deepcopy
from datetime import date
from pathlib import Path
import pytest

from scripts.evaluate_phase_1b_exit import (
    PINNED_DATASETS,
    build_coverage_matrix,
    load_and_verify_lineage,
    run_exit_evaluation,
    revoked_approval_ids,
    audit_frozen_dry_run_references,
    historical_universe,
)
from v5_2.data.source_approval import SourceApprovalRevocationArtifactV1
from datetime import datetime, timezone
from dataclasses import asdict


ROOT = Path(__file__).resolve().parents[2]
REAL_ARTIFACTS_AVAILABLE = (
    ROOT / "data/phase_1b1_2026_extension/governance/trade_calendar-approval-4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601.json"
).is_file()
requires_real_artifacts = pytest.mark.skipif(
    not REAL_ARTIFACTS_AVAILABLE, reason="repository-local governance artifacts are excluded from clean room")


@requires_real_artifacts
def test_exact_pinned_approval_and_manifest_lineage_is_valid():
    lineage = load_and_verify_lineage(ROOT)
    assert set(lineage) == set(PINNED_DATASETS)
    assert all(item["valid"] for item in lineage.values())
    assert all(item["approval_id"] == PINNED_DATASETS[name]["approval_id"] for name, item in lineage.items())


@requires_real_artifacts
def test_tampered_or_wrongly_pinned_manifest_fails_closed():
    lineage = load_and_verify_lineage(ROOT)
    altered = deepcopy(lineage)
    altered["daily_bar"]["manifest"]["row_count"] += 1
    matrix = build_coverage_matrix(altered)
    assert "MANIFEST_INTEGRITY_INVALID" in matrix.entry("daily_bar").known_gaps


def test_valid_revocation_is_machine_consumed_and_tamper_fails_closed():
    artifact = SourceApprovalRevocationArtifactV1.create(approval_id="approval-x", reason="unsafe",
        effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), evidence_ids=("evidence",),
        policy_version="test-v1")
    value = asdict(artifact)
    assert revoked_approval_ids([value]) == {"approval-x"}
    value["reason"] = "tampered"
    try:
        revoked_approval_ids([value])
    except ValueError as error:
        assert "integrity" in str(error)
    else:
        raise AssertionError("tampered revocation was accepted")


@requires_real_artifacts
def test_matrix_preserves_scoped_and_observed_fact_boundaries():
    matrix = build_coverage_matrix(load_and_verify_lineage(ROOT))
    assert matrix.entry("corporate_action").approved_scope == ("BONUS_SHARE", "CASH_DIVIDEND")
    assert matrix.entry("corporate_action").unsupported_scope == (
        "RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT")
    assert matrix.entry("financial_disclosure").completeness_mode == "OBSERVED_FACTS_ONLY"
    assert "HISTORICAL_PANEL_COMPLETENESS_NOT_ESTABLISHED" in matrix.entry("financial_disclosure").known_gaps


@requires_real_artifacts
def test_real_exit_dry_runs_are_deterministic_after_base_remediation():
    first = run_exit_evaluation(ROOT, repository_head="frozen-head", write=False)
    second = run_exit_evaluation(ROOT, repository_head="frozen-head", write=False)
    assert first == second
    assert [item["label"] for item in first["dry_runs"]] == ["EARLY", "MIDDLE", "RECENT", "2026"]
    assert all(item["result"]["session_valid"] for item in first["dry_runs"])
    assert all(item["result"]["base_eligible_count"] > 0 for item in first["dry_runs"])
    assert first["acceptance"]["gate_results"]["DETERMINISTIC_REPLAY"] == "PASS"
    assert first["acceptance"]["gate_results"]["PHASE_1B_EXIT"] == "PASS"


@requires_real_artifacts
def test_frozen_sessions_are_real_approved_open_sessions():
    result = run_exit_evaluation(ROOT, repository_head="frozen-head", write=False)
    assert [item["session"] for item in result["dry_runs"]] == [
        "2012-06-29", "2018-06-29", "2025-06-30", "2026-06-30"]
    assert all(item["cutoff"].endswith("+08:00") for item in result["dry_runs"])


@requires_real_artifacts
def test_old_frozen_dry_run_artifacts_have_one_to_one_label_session_hash_mapping():
    correction = audit_frozen_dry_run_references(ROOT)
    assert correction["status"] == "REFERENCE_CORRECTION_REQUIRED"
    assert correction["correct_mapping"] == {
        "EARLY": "bfd09d04cedec1232c2ad16a8de4f4730029af279e0f15d3d2ce7f61fb5848bd",
        "MIDDLE": "222594638c5e82f44ac25adf76c76dbfc596dae38573863fa2318e383ed14256",
        "RECENT": "1c07e67549a33a4d651b64f75c780f1ab7770b96a2a7ae7c963159ec273f3e0b",
        "2026": "b223802c15de6901459bd07b8bb7f1216a75746277658af76542bf9ad22ce1b3",
    }
    assert correction["artifact_id"] == correction["content_hash"]


@requires_real_artifacts
def test_historical_universe_does_not_backfill_todays_membership():
    early = historical_universe(ROOT, date(2012, 6, 29))
    recent = historical_universe(ROOT, date(2025, 6, 30))
    assert "002477.SZ" in early
    assert "002477.SZ" not in recent
    assert "603448.SH" not in historical_universe(ROOT, date(2026, 6, 30))
    assert "603448.SH" in historical_universe(ROOT, date(2026, 9, 10))
