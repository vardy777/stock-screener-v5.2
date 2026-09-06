from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from v5_2.data.evidence import (
    EvidenceArtifactV1,
    EvidenceStatus,
    EvidenceType,
    EvidenceValidityPolicy,
    EvidenceValidityRuleV1,
)
from v5_2.data.manifests import DatasetManifestV1, ManifestError
from v5_2.data.source_approval import (
    SourceApprovalArtifactV1,
    SourceApprovalRevocationArtifactV1,
)


NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)


def approval(failed: bool = False) -> SourceApprovalArtifactV1:
    evidence = tuple(
        EvidenceArtifactV1.create(
            evidence_type=kind,
            status=(
                EvidenceStatus.FAIL
                if failed and kind is EvidenceType.PIT_TIME
                else EvidenceStatus.PASS
            ),
            observed_at=NOW,
            verified_at=NOW,
            policy_version="evidence-v1",
            source_version_identity="synthetic-v1",
            input_artifact_ids=(kind.value,),
            valid_until=None,
            findings=(),
        )
        for kind in EvidenceType
    )
    validity = EvidenceValidityPolicy(
        policy_version="validity-v1",
        rules=tuple(
            EvidenceValidityRuleV1(kind, None, True, ("evidence-v1",))
            for kind in EvidenceType
        ),
    )
    return SourceApprovalArtifactV1.evaluate(
        source_name="synthetic",
        dataset_kind="synthetic_daily_bar",
        coverage_start=date(2020, 1, 1),
        coverage_end=date(2020, 12, 31),
        verified_at=NOW,
        source_version_identity="synthetic-v1",
        policy_version="approval-v1",
        evaluator_version="evaluator-v1",
        evidence=evidence,
        required_evidence_types=tuple(EvidenceType),
        rule_set={},
        evidence_validity_policy=validity,
        resolution_as_of=NOW,
    )


def manifest(item: SourceApprovalArtifactV1 | None = None) -> DatasetManifestV1:
    return DatasetManifestV1.create(
        created_at=NOW,
        source_name="synthetic",
        dataset_kind="synthetic_daily_bar",
        approval=item or approval(),
        approval_resolution_as_of=NOW,
        coverage_start=date(2020, 2, 1),
        coverage_end=date(2020, 2, 29),
        row_count=20,
        symbol_count=2,
        raw_payload_hashes=("a" * 64,),
        normalized_content_hashes=("b" * 64,),
        fact_content_hashes=("c" * 64,),
        normalizer_version="synthetic-normalizer-v1",
        availability_policy_version="availability-v1",
        quality_findings=(),
        pit_validation_status="PASS",
        rule_compliance_status="PASS",
        pagination_complete=True,
    )


def test_manifest_pins_exact_approval_and_resolution_time() -> None:
    selected = approval()
    result = manifest(selected)
    assert result.approval_id == selected.approval_id
    assert result.approval_resolution_as_of == NOW
    assert result.verify_pinned_approval(selected) is True


def test_future_revocation_does_not_change_old_manifest_identity() -> None:
    selected = approval()
    old = manifest(selected)
    old_hash = old.manifest_hash
    SourceApprovalRevocationArtifactV1.create(
        approval_id=selected.approval_id,
        reason="future synthetic revocation",
        effective_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        evidence_ids=("future",),
        policy_version="revocation-v1",
    )
    assert old.manifest_hash == old_hash
    assert old.verify_pinned_approval(selected) is True


def test_manifest_rejects_nonapproving_artifact() -> None:
    with pytest.raises(ManifestError, match="approving"):
        manifest(approval(failed=True))


def test_manifest_rejects_failed_pit_or_uncovered_rows() -> None:
    values = dict(
        created_at=NOW,
        source_name="synthetic",
        dataset_kind="synthetic_daily_bar",
        approval=approval(),
        approval_resolution_as_of=NOW,
        coverage_start=date(2019, 12, 1),
        coverage_end=date(2020, 2, 1),
        row_count=1,
        symbol_count=1,
        raw_payload_hashes=("a" * 64,),
        normalized_content_hashes=("b" * 64,),
        fact_content_hashes=("c" * 64,),
        normalizer_version="v1",
        availability_policy_version="v1",
        quality_findings=(),
        pit_validation_status="PASS",
        rule_compliance_status="PASS",
        pagination_complete=True,
    )
    with pytest.raises(ManifestError, match="coverage"):
        DatasetManifestV1.create(**values)
    values["coverage_start"] = date(2020, 1, 1)
    values["pit_validation_status"] = "FAIL"
    with pytest.raises(ManifestError, match="PIT"):
        DatasetManifestV1.create(**values)


def test_wrong_approval_object_cannot_satisfy_pinned_manifest() -> None:
    selected = approval()
    result = manifest(selected)
    replacement = SourceApprovalArtifactV1.evaluate(
        source_name=selected.source_name,
        dataset_kind=selected.dataset_kind,
        coverage_start=selected.coverage_start,
        coverage_end=selected.coverage_end,
        verified_at=selected.verified_at,
        source_version_identity=selected.source_version_identity,
        policy_version="approval-v2",
        evaluator_version=selected.evaluator_version,
        evidence=(),
        required_evidence_types=tuple(EvidenceType),
        rule_set={},
        evidence_validity_policy=EvidenceValidityPolicy(
            policy_version="validity-v1",
            rules=tuple(
                EvidenceValidityRuleV1(kind, None, True, ("evidence-v1",))
                for kind in EvidenceType
            ),
        ),
        resolution_as_of=NOW,
    )
    assert result.verify_pinned_approval(replacement) is False
