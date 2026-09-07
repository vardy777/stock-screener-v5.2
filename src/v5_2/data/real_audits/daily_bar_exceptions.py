from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from types import MappingProxyType

from v5_2.data.identity import content_hash


class DailyBarExceptionType(StrEnum):
    IDENTITY_ANOMALY = "IDENTITY_ANOMALY"
    REFERENCE_VALUE_CONFLICT = "REFERENCE_VALUE_CONFLICT"
    ISOLATED_MISSING_BAR = "ISOLATED_MISSING_BAR"
    ISOLATED_SCHEMA_ANOMALY = "ISOLATED_SCHEMA_ANOMALY"
    OTHER_LOCAL_ANOMALY = "OTHER_LOCAL_ANOMALY"


@dataclass(frozen=True, slots=True)
class DailyBarExceptionalRecordV1:
    exception_id: str
    security_identity: str
    session: date
    affected_fields: tuple[str, ...]
    exception_type: DailyBarExceptionType
    evidence_ids: tuple[str, ...]
    disposition: str
    created_at: datetime
    policy_version: str
    dimensions: object
    content_hash: str

    @classmethod
    def create(cls, **values):
        values["exception_type"] = DailyBarExceptionType(values["exception_type"])
        values["affected_fields"] = tuple(sorted(set(values["affected_fields"])))
        values["evidence_ids"] = tuple(sorted(set(values["evidence_ids"])))
        values["dimensions"] = MappingProxyType(dict(sorted(values["dimensions"].items())))
        if values["disposition"] != "QUARANTINE":
            raise ValueError("unresolved daily-bar exceptions must be quarantined")
        digest = content_hash({"schema_version": "DailyBarExceptionalRecordV1", **values})
        return cls(exception_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class DailyBarExceptionPatternAuditV1:
    audit_id: str
    systematic_defect: bool
    repeated_signatures: tuple[str, ...]
    content_hash: str

    @classmethod
    def evaluate(cls, records, *, budget):
        counts = Counter((record.dimensions.get("exchange", "UNKNOWN"), record.exception_type.value, record.affected_fields) for record in records)
        repeated = tuple(sorted(str(key) for key, count in counts.items() if count >= budget.systematic_cluster_minimum))
        values = {"systematic_defect": bool(repeated), "repeated_signatures": repeated}
        digest = content_hash({"schema_version": "DailyBarExceptionPatternAuditV1", **values})
        return cls(audit_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class DailyBarExceptionBudgetResultV1:
    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DailyBarExceptionBudgetV1:
    budget_id: str
    absolute_limit: int
    ratio_limit: float
    systematic_cluster_minimum: int
    frozen_at: datetime
    content_hash: str

    @classmethod
    def create_default(cls):
        values = {"absolute_limit": 100, "ratio_limit": 0.0001, "systematic_cluster_minimum": 5,
                  "frozen_at": datetime(2026, 9, 6, tzinfo=timezone.utc)}
        digest = content_hash({"schema_version": "DailyBarExceptionBudgetV1", **values})
        return cls(budget_id=digest, content_hash=digest, **values)

    def evaluate(self, records, *, total_rows, pattern_audit):
        reasons = []
        if len(records) > self.absolute_limit or not total_rows or len(records) / total_rows > self.ratio_limit:
            reasons.append("exception_limit")
        if pattern_audit.systematic_defect:
            reasons.append("systematic_defect")
        return DailyBarExceptionBudgetResultV1(not reasons, tuple(reasons))
