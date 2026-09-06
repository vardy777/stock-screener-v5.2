from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import content_hash


class ExceptionType(StrEnum):
    SEMANTIC_AMBIGUITY = "SEMANTIC_AMBIGUITY"
    OFFICIAL_SOURCE_CONFLICT = "OFFICIAL_SOURCE_CONFLICT"
    OFFICIAL_FIELD_UNAVAILABLE = "OFFICIAL_FIELD_UNAVAILABLE"
    IDENTITY_TRANSITION = "IDENTITY_TRANSITION"
    OTHER_UNRESOLVED = "OTHER_UNRESOLVED"


class ExceptionDisposition(StrEnum):
    QUARANTINE = "QUARANTINE"
    EXCLUDE_NON_TARGET = "EXCLUDE_NON_TARGET"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, slots=True)
class ExceptionalSecurityGovernancePolicyV1:
    policy_id: str
    absolute_exception_limit: int
    exception_ratio_limit: float
    coverage_impact_ratio_limit: float
    affected_session_ratio_limit: float
    unknown_interval_limit: int
    systematic_cluster_minimum: int
    policy_version: str
    content_hash: str

    @classmethod
    def create_default(cls):
        values = {
            "absolute_exception_limit": 10,
            "exception_ratio_limit": 0.001,
            "coverage_impact_ratio_limit": 0.001,
            "affected_session_ratio_limit": 0.001,
            "unknown_interval_limit": 0,
            "systematic_cluster_minimum": 3,
            "policy_version": "exceptional-security-governance-v1",
        }
        digest = content_hash({"schema_version": "ExceptionalSecurityGovernancePolicyV1", **values})
        return cls(policy_id=digest, content_hash=digest, **values)

    def exception_set_hash(self, records: Sequence["ExceptionalSecurityRecordV1"]) -> str:
        return content_hash({"policy_id": self.policy_id, "exception_ids": tuple(sorted(record.exception_id for record in records))})

    def require_pinned_exception_set(self, pinned_hash: str, records: Sequence["ExceptionalSecurityRecordV1"]) -> None:
        if pinned_hash != self.exception_set_hash(records):
            raise ValueError("exception set changed; source approval must be re-evaluated")


@dataclass(frozen=True, slots=True)
class ExceptionalSecurityRecordV1:
    exception_id: str
    security_identity: str
    effective_from: date | None
    effective_to: date | None
    affected_fields: tuple[str, ...]
    verified_fields: tuple[str, ...]
    provider_values: Mapping[str, Any]
    reference_values: Mapping[str, Any]
    exception_type: ExceptionType
    evidence_ids: tuple[str, ...]
    disposition: ExceptionDisposition
    research_impact: str
    created_at: datetime
    policy_version: str
    dimensions: Mapping[str, str]
    content_hash: str

    @classmethod
    def create(cls, **values):
        values["exception_type"] = ExceptionType(values["exception_type"])
        values["disposition"] = ExceptionDisposition(values["disposition"])
        values["affected_fields"] = tuple(sorted(set(values["affected_fields"])))
        values["verified_fields"] = tuple(sorted(set(values["verified_fields"])))
        if set(values["affected_fields"]) & set(values["verified_fields"]):
            raise ValueError("affected fields cannot be verified")
        values["evidence_ids"] = tuple(sorted(set(values["evidence_ids"])))
        values["provider_values"] = MappingProxyType(dict(sorted(values["provider_values"].items())))
        values["reference_values"] = MappingProxyType(dict(sorted(values["reference_values"].items())))
        values["dimensions"] = MappingProxyType(dict(sorted(values["dimensions"].items())))
        body = {"schema_version": "ExceptionalSecurityRecordV1", **values}
        digest = content_hash(body)
        return cls(exception_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class ExceptionPatternAuditV1:
    audit_id: str
    concentration_counts: Mapping[str, int]
    repeated_semantic_signatures: tuple[str, ...]
    systematic_defect: bool
    exception_set_hash: str
    content_hash: str

    @classmethod
    def evaluate(cls, records, *, total_securities: int, policy: ExceptionalSecurityGovernancePolicyV1):
        active = tuple(record for record in records if record.disposition is not ExceptionDisposition.RESOLVED)
        counts = Counter()
        signatures = Counter()
        for record in active:
            for key in ("exchange", "board", "year", "listing_status"):
                counts[f"{key}={record.dimensions.get(key, 'UNKNOWN')}"] += 1
            for field in record.affected_fields:
                counts[f"field={field}"] += 1
                signatures[f"{record.dimensions.get('exchange', 'UNKNOWN')}|{field}|{record.exception_type.value}"] += 1
        repeated = tuple(sorted(key for key, count in signatures.items() if count >= policy.systematic_cluster_minimum))
        body = {
            "schema_version": "ExceptionPatternAuditV1", "concentration_counts": dict(sorted(counts.items())),
            "repeated_semantic_signatures": repeated, "systematic_defect": bool(repeated),
            "exception_set_hash": policy.exception_set_hash(active), "total_securities": total_securities,
            "policy_id": policy.policy_id,
        }
        digest = content_hash(body)
        return cls(audit_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k not in {"schema_version", "total_securities", "policy_id"}})


@dataclass(frozen=True, slots=True)
class ExceptionBudgetEvaluationV1:
    evaluation_id: str
    passed: bool
    reasons: tuple[str, ...]
    exception_set_hash: str
    budget_id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class SecurityMasterExceptionBudgetV1:
    budget_id: str
    policy_id: str
    absolute_exception_limit: int
    exception_ratio_limit: float
    coverage_impact_ratio_limit: float
    affected_session_ratio_limit: float
    unknown_interval_limit: int
    frozen_at: datetime
    methodology: str
    content_hash: str

    @classmethod
    def create_default(cls, policy_id: str):
        values = {
            "policy_id": policy_id, "absolute_exception_limit": 10, "exception_ratio_limit": 0.001,
            "coverage_impact_ratio_limit": 0.001, "affected_session_ratio_limit": 0.001,
            "unknown_interval_limit": 0, "frozen_at": datetime(2026, 9, 6, tzinfo=timezone.utc),
            "methodology": "rare-record ceiling independent of observed sample: ten records and 0.1 percent; explicit field-scoped coverage/session impact capped at 0.1 percent; no unknown intervals; systematic clusters always block",
        }
        digest = content_hash({"schema_version": "SecurityMasterExceptionBudgetV1", **values})
        return cls(budget_id=digest, content_hash=digest, **values)

    def evaluate(self, records, *, total_securities, coverage_impact_ratio, affected_session_ratio, pattern_audit):
        active = tuple(record for record in records if record.disposition is not ExceptionDisposition.RESOLVED)
        unknown = sum(record.effective_from is None or record.effective_to is None for record in active)
        ratio = len(active) / total_securities if total_securities else 1.0
        checks = {
            "absolute_exception_limit": len(active) <= self.absolute_exception_limit,
            "exception_ratio_limit": ratio <= self.exception_ratio_limit,
            "coverage_impact_ratio_limit": coverage_impact_ratio <= self.coverage_impact_ratio_limit,
            "affected_session_ratio_limit": affected_session_ratio <= self.affected_session_ratio_limit,
            "unknown_interval_limit": unknown <= self.unknown_interval_limit,
            "systematic_pattern": not pattern_audit.systematic_defect,
        }
        reasons = tuple(key for key, passed in checks.items() if not passed)
        values = {"passed": not reasons, "reasons": reasons, "exception_set_hash": pattern_audit.exception_set_hash, "budget_id": self.budget_id}
        digest = content_hash({"schema_version": "ExceptionBudgetEvaluationV1", **values})
        return ExceptionBudgetEvaluationV1(evaluation_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class UniverseExclusionEvidenceV1:
    evidence_id: str
    session: date
    security: str
    reason: str
    exception_id: str | None
    required_fields: tuple[str, ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class AdmissionDecisionV1:
    admitted: bool
    exclusion_evidence: UniverseExclusionEvidenceV1 | None


class HistoricalUniverseAdmissionV1:
    def __init__(self, exceptions: Sequence[ExceptionalSecurityRecordV1], *, valid_intervals: Mapping[str, tuple[date, date | None]] | None = None) -> None:
        self._exceptions = tuple(exceptions)
        self._valid_intervals = dict(valid_intervals or {})

    def admit(self, security, session, *, required_fields):
        required = tuple(sorted(set(required_fields)))
        valid_interval = self._valid_intervals.get(security)
        if valid_interval is not None:
            start, end = valid_interval
            if session < start or (end is not None and session > end):
                return AdmissionDecisionV1(False, self._exclusion(session, security, "OUTSIDE_VALID_SECURITY_INTERVAL", None, required))
        for record in self._exceptions:
            if record.security_identity != security or record.disposition is ExceptionDisposition.RESOLVED:
                continue
            interval_unknown = record.effective_from is None or record.effective_to is None
            exception_applies = interval_unknown or record.effective_from <= session <= record.effective_to
            affected = bool(set(required) & set(record.affected_fields))
            if interval_unknown or (exception_applies and affected):
                reason = "UNKNOWN_EXCEPTION_INTERVAL" if interval_unknown else "FIELD_SCOPED_QUARANTINE"
                return AdmissionDecisionV1(False, self._exclusion(session, security, reason, record.exception_id, required))
        return AdmissionDecisionV1(True, None)

    @staticmethod
    def _exclusion(session, security, reason, exception_id, required):
        values = {"session": session, "security": security, "reason": reason, "exception_id": exception_id, "required_fields": required}
        digest = content_hash({"schema_version": "UniverseExclusionEvidenceV1", **values})
        return UniverseExclusionEvidenceV1(evidence_id=digest, content_hash=digest, **values)

    def build_universe(self, securities, session, *, required_fields, record_exclusions=True):
        included, excluded = [], []
        for security in securities:
            decision = self.admit(security, session, required_fields=required_fields)
            if decision.admitted:
                included.append(security)
            elif record_exclusions:
                excluded.append(decision.exclusion_evidence)
            else:
                raise ValueError("silent exclusion is prohibited")
        return tuple(included), tuple(excluded)
