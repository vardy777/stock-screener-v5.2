from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from v5_2.data.evidence import (
    EvidenceArtifactV1,
    EvidenceStatus,
    EvidenceType,
    EvidenceValidityPolicy,
    EvidenceValidityRuleV1,
    EvidenceValidityStatus,
)


NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def item(
    kind: EvidenceType,
    *,
    age_days: int = 0,
    source_version: str = "provider-v1",
    policy_version: str = "evidence-v1",
    valid_until: datetime | None = None,
) -> EvidenceArtifactV1:
    observed = NOW - timedelta(days=age_days)
    return EvidenceArtifactV1.create(
        evidence_type=kind,
        status=EvidenceStatus.PASS,
        observed_at=observed,
        verified_at=observed,
        policy_version=policy_version,
        source_version_identity=source_version,
        input_artifact_ids=("immutable-input",),
        valid_until=valid_until,
        findings=(),
    )


def policy() -> EvidenceValidityPolicy:
    return EvidenceValidityPolicy(
        policy_version="validity-v1",
        rules=(
            EvidenceValidityRuleV1(EvidenceType.COVERAGE, None, False, ("evidence-v1",)),
            EvidenceValidityRuleV1(EvidenceType.HISTORICAL_SAMPLE, None, False, ("evidence-v1",)),
            EvidenceValidityRuleV1(EvidenceType.CONTENT_IDENTITY, None, True, ("evidence-v1",)),
            EvidenceValidityRuleV1(EvidenceType.REVISION, 30, True, ("evidence-v1",)),
            EvidenceValidityRuleV1(EvidenceType.PIT_TIME, 90, True, ("evidence-v1",)),
            EvidenceValidityRuleV1(EvidenceType.LICENSE_USAGE, 30, False, ("evidence-v1",)),
            EvidenceValidityRuleV1(EvidenceType.CROSS_SOURCE, 14, True, ("evidence-v1",)),
        ),
    )


def test_historical_immutable_coverage_does_not_expire_by_arbitrary_age() -> None:
    result = policy().evaluate(
        item(EvidenceType.COVERAGE, age_days=2000, source_version="old-provider"),
        resolution_as_of=NOW,
        source_version_identity="provider-v2",
    )
    assert result.status is EvidenceValidityStatus.VALID


@pytest.mark.parametrize(
    ("kind", "fresh_age", "stale_age"),
    [
        (EvidenceType.REVISION, 30, 31),
        (EvidenceType.PIT_TIME, 90, 91),
        (EvidenceType.LICENSE_USAGE, 30, 31),
        (EvidenceType.CROSS_SOURCE, 14, 15),
    ],
)
def test_evidence_type_has_its_own_deterministic_age_boundary(
    kind: EvidenceType, fresh_age: int, stale_age: int
) -> None:
    assert policy().evaluate(
        item(kind, age_days=fresh_age), NOW, "provider-v1"
    ).status is EvidenceValidityStatus.VALID
    assert policy().evaluate(
        item(kind, age_days=stale_age), NOW, "provider-v1"
    ).status is EvidenceValidityStatus.STALE


def test_source_version_change_stales_only_rules_that_require_it() -> None:
    result = policy().evaluate(item(EvidenceType.REVISION), NOW, "provider-v2")
    assert result.status is EvidenceValidityStatus.STALE
    assert result.reason == "source_version_changed"


def test_explicit_valid_until_is_fail_closed() -> None:
    result = policy().evaluate(
        item(EvidenceType.COVERAGE, valid_until=NOW - timedelta(seconds=1)),
        NOW,
        "provider-v1",
    )
    assert result.status is EvidenceValidityStatus.STALE
    assert result.reason == "valid_until_elapsed"


def test_unaccepted_evidence_policy_version_is_stale() -> None:
    result = policy().evaluate(
        item(EvidenceType.PIT_TIME, policy_version="evidence-v0"), NOW, "provider-v1"
    )
    assert result.status is EvidenceValidityStatus.STALE
    assert result.reason == "evidence_policy_incompatible"


def test_policy_requires_exactly_one_rule_per_evidence_type() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        EvidenceValidityPolicy(
            policy_version="broken",
            rules=(EvidenceValidityRuleV1(EvidenceType.COVERAGE, None, False, ("v1",)),),
        )
