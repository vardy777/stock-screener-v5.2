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
from v5_2.data.source_approval import (
    ApprovalResolutionError,
    ApprovalResolver,
    SourceApprovalArtifactV1,
    SourceApprovalRevocationArtifactV1,
)


def at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def make_approval(day: int, supersedes: str | None = None) -> SourceApprovalArtifactV1:
    evidence = tuple(
        EvidenceArtifactV1.create(
            evidence_type=kind,
            status=EvidenceStatus.PASS,
            observed_at=at(day),
            verified_at=at(day),
            policy_version="evidence-v1",
            source_version_identity="synthetic-v1",
            input_artifact_ids=(f"{kind.value}-{day}",),
            valid_until=None,
            findings=(),
        )
        for kind in EvidenceType
    )
    return SourceApprovalArtifactV1.evaluate(
        source_name="synthetic",
        dataset_kind="synthetic_daily_bar",
        coverage_start=date(2020, 1, 1),
        coverage_end=date(2020, 12, 31),
        verified_at=at(day),
        source_version_identity="synthetic-v1",
        policy_version="approval-v1",
        evaluator_version="evaluator-v1",
        evidence=evidence,
        required_evidence_types=tuple(EvidenceType),
        rule_set={},
        supersedes_approval_id=supersedes,
        evidence_validity_policy=EvidenceValidityPolicy(
            policy_version="validity-v1",
            rules=tuple(
                EvidenceValidityRuleV1(kind, None, True, ("evidence-v1",))
                for kind in EvidenceType
            ),
        ),
        resolution_as_of=at(day),
    )


def resolve(resolver: ApprovalResolver, day: int) -> str:
    return resolver.resolve(
        source_name="synthetic",
        dataset_kind="synthetic_daily_bar",
        requested_coverage=(date(2020, 2, 1), date(2020, 2, 29)),
        resolution_as_of=at(day),
    )


def test_explicit_supersession_changes_only_later_resolution() -> None:
    old = make_approval(1)
    new = make_approval(5, supersedes=old.approval_id)
    resolver = ApprovalResolver((new, old), ())
    assert resolve(resolver, 3) == old.approval_id
    assert resolve(resolver, 6) == new.approval_id


def test_revocation_is_effective_only_after_creation_and_effective_time() -> None:
    old = make_approval(1)
    revocation = SourceApprovalRevocationArtifactV1.create(
        approval_id=old.approval_id,
        reason="synthetic audit invalidated",
        effective_at=at(5),
        created_at=at(4),
        evidence_ids=("revocation-evidence",),
        policy_version="revocation-v1",
    )
    resolver = ApprovalResolver((old,), (revocation,))
    assert resolve(resolver, 3) == old.approval_id
    with pytest.raises(ApprovalResolutionError, match="no applicable"):
        resolve(resolver, 6)


def test_unrelated_applicable_approvals_are_ambiguous_not_newest_wins() -> None:
    resolver = ApprovalResolver((make_approval(1), make_approval(2)), ())
    with pytest.raises(ApprovalResolutionError, match="ambiguous"):
        resolve(resolver, 3)


def test_resolution_is_independent_of_repository_iteration_order() -> None:
    old = make_approval(1)
    new = make_approval(5, supersedes=old.approval_id)
    assert resolve(ApprovalResolver((old, new), ()), 6) == resolve(
        ApprovalResolver((new, old), ()), 6
    )


def test_requested_coverage_must_be_fully_contained() -> None:
    resolver = ApprovalResolver((make_approval(1),), ())
    with pytest.raises(ApprovalResolutionError, match="no applicable"):
        resolver.resolve(
            source_name="synthetic",
            dataset_kind="synthetic_daily_bar",
            requested_coverage=(date(2019, 12, 1), date(2020, 2, 1)),
            resolution_as_of=at(3),
        )
