from dataclasses import replace
from datetime import datetime, timezone

from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType
from v5_2.data.real_audits.historical_universe import reconcile_historical_universe
from v5_2.data.real_audits.status_official_samples import build_official_sample_ledger
from v5_2.data.real_audits.status_validation import evaluate_status_gates

NOW = datetime(2026, 9, 8, tzinfo=timezone.utc)
SOURCE = "source-version"


def pit(status=EvidenceStatus.PASS, source=SOURCE):
    return EvidenceArtifactV1.create(evidence_type=EvidenceType.PIT_TIME, status=status, observed_at=NOW,
        verified_at=NOW, policy_version="status-pit-v2", source_version_identity=source,
        input_artifact_ids=("availability",), valid_until=None, findings=("16:30 cutoff verified",))


def universe(unresolved=False):
    master = {} if unresolved else {"600747.SH": {"exchange": "SSE", "symbol": "600747", "list_date": "19960916", "delist_date": "20191212"}}
    return reconcile_historical_universe(observed_symbols=("600747.SH",), original_symbols=(), master_rows=master,
        aliases={}, coverage_start="20100104", coverage_end="20251231", original_universe_id="u",
        official_evidence={"600747.SH": ("sse-evidence",)})


def ledger(resolution="MATCH"):
    sample = ({"event_id": "e", "security_identity": "600747.SH", "session": "20191212", "stratum": "delisting"},)
    evidence = {} if resolution == "OFFICIAL_REFERENCE_UNAVAILABLE" else {"e": {"resolution": resolution,
        "observation": "official", "evidence_id": "official-id", "semantic_mapping": "same status"}}
    return build_official_sample_ledger("inventory", sample, evidence)


def evaluate(**changes):
    values = dict(structural_status="PASS", pit_evidence=pit(), official_ledger=ledger(),
        reconciliation=universe(), exception_budget_pass=True, systematic_defect=False,
        source_version_identity=SOURCE, revoked_artifact_ids=(), expected_inventory_id="inventory")
    values.update(changes)
    return evaluate_status_gates(**values)


def test_all_valid_artifacts_are_required_for_approval_and_publication() -> None:
    result = evaluate()
    assert result.pit_status == "PASS"
    assert result.survivorship_status == "PASS"
    assert result.cross_source_status == "PASS"
    assert result.decision == "APPROVED_WITH_RULES"
    assert result.publication_allowed is True


def test_missing_or_unavailable_evidence_is_pending_not_match() -> None:
    assert evaluate(pit_evidence=None).decision == "PENDING"
    result = evaluate(official_ledger=ledger("OFFICIAL_REFERENCE_UNAVAILABLE"))
    assert result.cross_source_status == "PENDING"
    assert result.decision == "PENDING"
    assert evaluate(official_ledger=ledger("INDEPENDENT_EVIDENCE_UNAVAILABLE")).decision == "PENDING"


def test_confirmed_and_systematic_errors_are_rejected() -> None:
    assert evaluate(pit_evidence=pit(EvidenceStatus.FAIL)).decision == "REJECTED"
    mismatch = evaluate(official_ledger=ledger("MISMATCH"))
    assert mismatch.cross_source_status == "FAIL"
    assert mismatch.decision == "REJECTED"
    assert evaluate(systematic_defect=True).decision == "REJECTED"


def test_unresolved_universe_identity_cannot_be_silently_ignored() -> None:
    result = evaluate(reconciliation=universe(unresolved=True))
    assert result.survivorship_status == "PENDING"
    assert result.decision == "PENDING"


def test_revoked_tampered_and_wrong_scope_artifacts_fail_closed() -> None:
    valid = ledger()
    assert evaluate(revoked_artifact_ids=(valid.content_hash,)).decision == "REJECTED"
    assert evaluate(official_ledger=replace(valid, content_hash="tampered")).decision == "REJECTED"
    assert evaluate(pit_evidence=pit(source="other-version")).decision == "REJECTED"
