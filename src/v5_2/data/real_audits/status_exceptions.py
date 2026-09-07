from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class StatusExceptionalRecordV1:
    exception_id: str
    security_identity: str
    effective_date: date
    affected_fields: tuple[str, ...]
    reason: str
    evidence_ids: tuple[str, ...]
    disposition: str
    dimensions: object
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        if values["disposition"] != "QUARANTINE":
            raise ValueError("status exception must be explicitly quarantined")
        values["affected_fields"] = tuple(sorted(set(values["affected_fields"])))
        values["evidence_ids"] = tuple(sorted(set(values["evidence_ids"])))
        values["dimensions"] = MappingProxyType(dict(sorted(values["dimensions"].items())))
        digest = content_hash({"schema_version": "StatusExceptionalRecordV1", **values})
        return cls(exception_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class StatusExceptionBudgetResultV1:
    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StatusExceptionBudgetV1:
    budget_id: str
    absolute_limit: int
    ratio_limit: Decimal
    systematic_cluster_minimum: int
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, *, absolute_limit, ratio_limit, systematic_cluster_minimum):
        ratio = Decimal(ratio_limit)
        if absolute_limit < 0 or not Decimal(0) <= ratio <= Decimal(1) or systematic_cluster_minimum < 2:
            raise ValueError("status exception budget is invalid")
        values = {"absolute_limit": absolute_limit, "ratio_limit": ratio,
                  "systematic_cluster_minimum": systematic_cluster_minimum,
                  "policy_version": "status-exception-budget-v1"}
        identity = {**values, "ratio_limit": str(ratio)}
        digest = content_hash({"schema_version": "StatusExceptionBudgetV1", **identity})
        return cls(budget_id=digest, content_hash=digest, **values)

    def evaluate(self, records, *, total_records, pattern_audit):
        reasons = []
        if len(records) > self.absolute_limit:
            reasons.append("absolute_limit")
        if total_records <= 0 or Decimal(len(records)) / Decimal(total_records) > self.ratio_limit:
            reasons.append("ratio_limit")
        if pattern_audit.systematic_dataset_defect:
            reasons.append("systematic_dataset_defect")
        return StatusExceptionBudgetResultV1(not reasons, tuple(reasons))


@dataclass(frozen=True, slots=True)
class StatusExceptionPatternAuditV1:
    audit_id: str
    systematic_dataset_defect: bool
    repeated_signatures: tuple[str, ...]
    content_hash: str

    @classmethod
    def evaluate(cls, records, *, budget):
        counts = Counter(
            f"{record.dimensions.get('exchange', 'UNKNOWN')}|{record.dimensions.get('year', 'UNKNOWN')}|{record.dimensions.get('field', 'UNKNOWN')}"
            for record in records
        )
        repeated = tuple(sorted(signature for signature, count in counts.items()
                                if count >= budget.systematic_cluster_minimum))
        values = {"systematic_dataset_defect": bool(repeated), "repeated_signatures": repeated}
        digest = content_hash({"schema_version": "StatusExceptionPatternAuditV1", **values})
        return cls(audit_id=digest, content_hash=digest, **values)
