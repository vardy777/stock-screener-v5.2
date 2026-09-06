from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType

from v5_2.data.identity import content_hash


class EvidenceResolution(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNRESOLVED_EVIDENCE = "UNRESOLVED_EVIDENCE"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    OFFICIAL_REFERENCE_UNAVAILABLE = "OFFICIAL_REFERENCE_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ApprovalPolicyAdequacyReviewV1:
    review_id: str
    reviewed_policy_ids: tuple[str, ...]
    gate_findings: Mapping[str, str]
    independent_sample_available: bool
    quarantine_impact_bounded: bool
    unresolved_treated_as_mismatch: bool
    decision: str
    methodological_findings: tuple[str, ...]
    reviewed_at: datetime
    policy_version: str
    content_hash: str

    @classmethod
    def evaluate(cls, *, reviewed_policy_ids: Sequence[str], gate_findings: Mapping[str, str], independent_sample_available: bool, quarantine_impact_bounded: bool, reviewed_at: datetime, policy_version: str):
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        decision = "SUPERSEDE_WITH_V2" if independent_sample_available and quarantine_impact_bounded else "RETAIN_V1_PENDING"
        findings = (
            "unresolved official evidence is not a provider mismatch",
            "official archive availability can block V1 independently of provider quality",
            "Tier 3 independent samples plus Tier 1/2 anchors may support equivalence with rules",
            "current independent sample or bounded quarantine evidence is insufficient",
        )
        body = {
            "schema_version": "ApprovalPolicyAdequacyReviewV1",
            "reviewed_policy_ids": tuple(sorted(set(reviewed_policy_ids))),
            "gate_findings": MappingProxyType(dict(sorted(gate_findings.items()))),
            "independent_sample_available": independent_sample_available,
            "quarantine_impact_bounded": quarantine_impact_bounded,
            "unresolved_treated_as_mismatch": False,
            "decision": decision,
            "methodological_findings": findings,
            "reviewed_at": reviewed_at,
            "policy_version": policy_version,
        }
        digest = content_hash(body)
        return cls(review_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})


@dataclass(frozen=True, slots=True)
class CrossSourceEvidencePolicyV2:
    policy_id: str
    policy_version: str
    tiers: tuple[tuple[str, str], ...]
    minimum_official_anchors: int
    minimum_independent_samples: int
    maximum_unexplained_mismatches: int
    content_hash: str

    @classmethod
    def create_default(cls):
        body = {
            "schema_version": "CrossSourceEvidencePolicyV2",
            "policy_version": "cross-source-evidence-v2",
            "tiers": (
                ("TIER_1", "SSE/SZSE structured official data or official historical records"),
                ("TIER_2", "SSE/SZSE official notices and listing/delisting announcements"),
                ("TIER_3", "independent trusted market-data source"),
                ("TIER_4", "internal invariants, coverage and deterministic replay"),
            ),
            "minimum_official_anchors": 5,
            "minimum_independent_samples": 256,
            "maximum_unexplained_mismatches": 0,
        }
        digest = content_hash(body)
        return cls(policy_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})

    def evaluate(self, *, official_anchor_count: int, independent_sample_count: int, unexplained_mismatch_count: int) -> str:
        if unexplained_mismatch_count > self.maximum_unexplained_mismatches:
            return "NOT_EQUIVALENT"
        if official_anchor_count < self.minimum_official_anchors or independent_sample_count < self.minimum_independent_samples:
            return "INSUFFICIENT_EVIDENCE"
        return "EQUIVALENT_WITH_RULES"


@dataclass(frozen=True, slots=True)
class QuarantinedSecurityIdentityV1:
    quarantine_id: str
    identity: str
    reason: str
    raw_artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    effective_at: datetime
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, identity: str, reason: str, raw_artifact_ids: Sequence[str], evidence_ids: Sequence[str], effective_at: datetime, policy_version: str):
        body = {"schema_version": "QuarantinedSecurityIdentityV1", "identity": identity, "reason": reason, "raw_artifact_ids": tuple(sorted(set(raw_artifact_ids))), "evidence_ids": tuple(sorted(set(evidence_ids))), "effective_at": effective_at, "policy_version": policy_version}
        digest = content_hash(body)
        return cls(quarantine_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})


class QuarantinedIdentityError(RuntimeError):
    """An explicitly requested identity is quarantined."""


def filter_research_universe(symbols: Sequence[str], quarantines: Sequence[QuarantinedSecurityIdentityV1], *, explicitly_requested: Sequence[str] = ()) -> tuple[str, ...]:
    blocked = {item.identity for item in quarantines}
    if blocked & set(explicitly_requested):
        raise QuarantinedIdentityError("explicitly requested identity is quarantined")
    return tuple(symbol for symbol in symbols if symbol not in blocked)


@dataclass(frozen=True, slots=True)
class UnresolvedIdentityImpactEvidenceV1:
    evidence_id: str
    identity: str
    possible_effective_from: date
    possible_effective_to: date | None
    affected_sessions: int | None
    uncertainty: str
    maximum_research_impact: str
    recommended_disposition: str
    evidence_ids: tuple[str, ...]
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        values["evidence_ids"] = tuple(sorted(set(values["evidence_ids"])))
        body = {"schema_version": "UnresolvedIdentityImpactEvidenceV1", **values}
        digest = content_hash(body)
        return cls(evidence_id=digest, content_hash=digest, **values)
