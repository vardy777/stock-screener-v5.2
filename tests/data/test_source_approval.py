from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone

import pytest

from v5_2.data.evidence import (
    EvidenceArtifactV1,
    EvidenceStatus,
    EvidenceType,
    EvidenceValidityPolicy,
    EvidenceValidityRuleV1,
)
from v5_2.data.source_approval import (
    ApprovalDecision,
    ApprovalEvaluationError,
    SourceApprovalArtifactV1,
)


NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)
REQUIRED = tuple(EvidenceType)


def validity_policy() -> EvidenceValidityPolicy:
    return EvidenceValidityPolicy(
        policy_version="validity-v1",
        rules=tuple(
            EvidenceValidityRuleV1(kind, 30, True, ("evidence-v1",))
            for kind in EvidenceType
        ),
    )


def evidence(kind: EvidenceType, status: EvidenceStatus = EvidenceStatus.PASS) -> EvidenceArtifactV1:
    return EvidenceArtifactV1.create(
        evidence_type=kind,
        status=status,
        observed_at=NOW,
        verified_at=NOW,
        policy_version="evidence-v1",
        source_version_identity="synthetic-provider-v1",
        input_artifact_ids=(f"input-{kind.value}",),
        valid_until=None,
        findings=(),
    )


def approval(items: tuple[EvidenceArtifactV1, ...]) -> SourceApprovalArtifactV1:
    return SourceApprovalArtifactV1.evaluate(
        source_name="synthetic_provider",
        dataset_kind="synthetic_daily_bar",
        coverage_start=date(2020, 1, 1),
        coverage_end=date(2020, 12, 31),
        verified_at=NOW,
        source_version_identity="synthetic-provider-v1",
        policy_version="approval-v1",
        evaluator_version="evaluator-v1",
        evidence=items,
        required_evidence_types=REQUIRED,
        rule_set={"excluded_fields": []},
        evidence_validity_policy=validity_policy(),
        resolution_as_of=NOW,
    )


def test_complete_passing_evidence_produces_content_addressed_approval() -> None:
    artifact = approval(tuple(evidence(kind) for kind in REQUIRED))
    repeated = approval(tuple(reversed([evidence(kind) for kind in REQUIRED])))
    assert artifact.decision is ApprovalDecision.APPROVED
    assert artifact.approval_id == repeated.approval_id
    assert len(artifact.evidence_bundle_hash) == 64


def test_missing_evidence_fails_closed_to_pending() -> None:
    artifact = approval(tuple(evidence(kind) for kind in REQUIRED[:-1]))
    assert artifact.decision is ApprovalDecision.PENDING


def test_failed_evidence_is_rejected() -> None:
    items = tuple(
        evidence(kind, EvidenceStatus.FAIL if kind is EvidenceType.PIT_TIME else EvidenceStatus.PASS)
        for kind in REQUIRED
    )
    assert approval(items).decision is ApprovalDecision.REJECTED


def test_conflicting_duplicate_evidence_fails_closed() -> None:
    items = tuple(evidence(kind) for kind in REQUIRED) + (
        evidence(EvidenceType.COVERAGE, EvidenceStatus.FAIL),
    )
    with pytest.raises(ApprovalEvaluationError, match="conflicting"):
        approval(items)


def test_approval_and_evidence_are_immutable() -> None:
    item = evidence(EvidenceType.COVERAGE)
    artifact = approval(tuple(evidence(kind) for kind in REQUIRED))
    with pytest.raises(FrozenInstanceError):
        item.status = EvidenceStatus.FAIL  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        artifact.decision = ApprovalDecision.REJECTED  # type: ignore[misc]


def test_callers_cannot_pass_an_approved_boolean() -> None:
    with pytest.raises(TypeError):
        SourceApprovalArtifactV1.evaluate(approved=True)  # type: ignore[call-arg]


def test_stale_evidence_fails_closed_to_pending() -> None:
    stale_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    stale_coverage = EvidenceArtifactV1.create(
        evidence_type=EvidenceType.COVERAGE,
        status=EvidenceStatus.PASS,
        observed_at=stale_time,
        verified_at=stale_time,
        policy_version="evidence-v1",
        source_version_identity="synthetic-provider-v1",
        input_artifact_ids=("stale",),
        valid_until=None,
        findings=(),
    )
    items = tuple(
        stale_coverage if kind is EvidenceType.COVERAGE else evidence(kind)
        for kind in REQUIRED
    )
    assert approval(items).decision is ApprovalDecision.PENDING
