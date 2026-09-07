from datetime import date, datetime, timezone

import pytest

from v5_2.data.manifests import DatasetManifestV1, ManifestError
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1


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
