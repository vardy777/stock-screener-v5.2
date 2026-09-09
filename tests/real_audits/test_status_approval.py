from datetime import date, datetime, timezone

import pytest

from v5_2.data.manifests import DatasetManifestV1, ManifestError
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1
from scripts.publish_phase_1b2a_status import build_status_equivalence


def test_equivalence_consumes_passed_gate_and_final_71_match_ledger() -> None:
    equivalence = build_status_equivalence(
        classification={"counts": [["UNEXPLAINED", 0]], "content_hash": "c"},
        audit={"sample_inventory_id": "sample", "pit_findings": ["pit"],
               "cross_source_findings": ["cross"], "evidence_id": "audit"},
        replay={"evidence_id": "replay"}, raw_hashes=("raw",),
        gate={"pit_status": "PASS", "cross_source_status": "PASS", "publication_allowed": True},
        prospective={"content_hash": "ledger", "observations": tuple(
            {"resolution": "MATCH"} for _ in range(71))},
    )
    assert equivalence.decision.value == "EQUIVALENT_WITH_RULES"
    assert equivalence.value_comparison_summary == {"matched": 71, "mismatched": 0, "unresolved": 0}
    assert not any("survivorship audit failed" in item for item in equivalence.limitations)


def test_rejected_status_approval_cannot_publish_manifest() -> None:
    approval = SourceApprovalArtifactV1(
        approval_id="a", source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        decision=ApprovalDecision.REJECTED, coverage_start=date(2010, 1, 4), coverage_end=date(2025, 12, 31),
        verified_at=datetime(2026, 9, 7, tzinfo=timezone.utc), source_version_identity="s",
        policy_version="p", rule_set={}, evidence_ids=(), evidence_bundle_hash="e",
        evaluator_version="v", evidence_validity_policy_version="vp", equivalence_evidence_id="q",
        supersedes_approval_id=None, content_hash="a",
    )
    with pytest.raises(ManifestError, match="approving"):
        DatasetManifestV1.create(
            created_at=approval.verified_at, source_name=approval.source_name,
            dataset_kind=approval.dataset_kind, approval=approval,
            approval_resolution_as_of=approval.verified_at, coverage_start=approval.coverage_start,
            coverage_end=approval.coverage_end, row_count=1, symbol_count=1,
            raw_payload_hashes=("r",), normalized_content_hashes=("n",), fact_content_hashes=("f",),
            normalizer_version="n", availability_policy_version="a", quality_findings=(),
            pit_validation_status="FAIL", rule_compliance_status="FAIL", pagination_complete=True,
        )
