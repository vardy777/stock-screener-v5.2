from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
