from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from v5_2.data.identity import content_hash


class EvidenceType(str, Enum):
    COVERAGE = "coverage"
    PIT_TIME = "pit_time_semantics"
    REVISION = "revision"
    HISTORICAL_SAMPLE = "historical_sample"
    CONTENT_IDENTITY = "content_identity"
    LICENSE_USAGE = "license_usage"
    CROSS_SOURCE = "cross_source"


class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class EvidenceValidityStatus(str, Enum):
    VALID = "VALID"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class EvidenceValidityResult:
    status: EvidenceValidityStatus
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceValidityRuleV1:
    evidence_type: EvidenceType
    max_age_days: int | None
    require_source_version_match: bool
    accepted_evidence_policy_versions: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.max_age_days is not None and self.max_age_days < 0:
            raise ValueError("max_age_days cannot be negative")
        if not self.accepted_evidence_policy_versions:
            raise ValueError("accepted evidence policy versions must not be empty")


@dataclass(frozen=True, slots=True)
class EvidenceArtifactV1:
    evidence_id: str
    evidence_type: EvidenceType
    status: EvidenceStatus
    observed_at: datetime
    verified_at: datetime
    policy_version: str
    source_version_identity: str
    input_artifact_ids: tuple[str, ...]
    valid_until: datetime | None
    findings: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(
        cls,
        *,
        evidence_type: EvidenceType,
        status: EvidenceStatus,
        observed_at: datetime,
        verified_at: datetime,
        policy_version: str,
        source_version_identity: str,
        input_artifact_ids: tuple[str, ...],
        valid_until: datetime | None,
        findings: tuple[str, ...],
    ) -> EvidenceArtifactV1:
        for name, value in (("observed_at", observed_at), ("verified_at", verified_at)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if valid_until is not None and (
            valid_until.tzinfo is None or valid_until.utcoffset() is None
        ):
            raise ValueError("valid_until must be timezone-aware")
        if verified_at < observed_at:
            raise ValueError("verified_at cannot precede observed_at")
        inputs = tuple(sorted(set(input_artifact_ids)))
        if not inputs:
            raise ValueError("input_artifact_ids must not be empty")
        body = {
            "schema_version": "EvidenceArtifactV1",
            "evidence_type": evidence_type,
            "status": status,
            "observed_at": observed_at,
            "verified_at": verified_at,
            "policy_version": policy_version,
            "source_version_identity": source_version_identity,
            "input_artifact_ids": inputs,
            "valid_until": valid_until,
            "findings": tuple(sorted(findings)),
        }
        digest = content_hash(body)
        return cls(
            evidence_id=digest,
            content_hash=digest,
            evidence_type=evidence_type,
            status=status,
            observed_at=observed_at,
            verified_at=verified_at,
            policy_version=policy_version,
            source_version_identity=source_version_identity,
            input_artifact_ids=inputs,
            valid_until=valid_until,
            findings=tuple(sorted(findings)),
        )


class EvidenceValidityPolicy:
    def __init__(
        self, *, policy_version: str, rules: tuple[EvidenceValidityRuleV1, ...]
    ) -> None:
        by_type = {rule.evidence_type: rule for rule in rules}
        if len(rules) != len(by_type) or set(by_type) != set(EvidenceType):
            raise ValueError("validity policy requires exactly one rule per evidence type")
        self.policy_version = policy_version
        self._rules = by_type

    def evaluate(
        self,
        evidence: EvidenceArtifactV1,
        resolution_as_of: datetime,
        source_version_identity: str,
    ) -> EvidenceValidityResult:
        if resolution_as_of.tzinfo is None or resolution_as_of.utcoffset() is None:
            raise ValueError("resolution_as_of must be timezone-aware")
        rule = self._rules[evidence.evidence_type]
        if evidence.verified_at > resolution_as_of:
            return EvidenceValidityResult(EvidenceValidityStatus.STALE, "not_verified_as_of")
        if evidence.valid_until is not None and resolution_as_of > evidence.valid_until:
            return EvidenceValidityResult(
                EvidenceValidityStatus.STALE, "valid_until_elapsed"
            )
        if evidence.policy_version not in rule.accepted_evidence_policy_versions:
            return EvidenceValidityResult(
                EvidenceValidityStatus.STALE, "evidence_policy_incompatible"
            )
        if (
            rule.require_source_version_match
            and evidence.source_version_identity != source_version_identity
        ):
            return EvidenceValidityResult(
                EvidenceValidityStatus.STALE, "source_version_changed"
            )
        if rule.max_age_days is not None and (
            resolution_as_of - evidence.verified_at > timedelta(days=rule.max_age_days)
        ):
            return EvidenceValidityResult(
                EvidenceValidityStatus.STALE, "type_specific_age_elapsed"
            )
        return EvidenceValidityResult(EvidenceValidityStatus.VALID, "valid")
