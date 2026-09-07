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


@dataclass(frozen=True, slots=True)
class StatusExceptionBudgetResultV2:
    passed: bool
    systematic_pattern: bool
    reasons: tuple[str, ...]
    metrics: object


@dataclass(frozen=True, slots=True)
class StatusExceptionBudgetV2:
    absolute_limit: int
    ratio_limit: Decimal
    per_security_limit: int
    per_security_consecutive_limit: int
    exchange_concentration_limit: Decimal
    month_concentration_limit: int
    unknown_effective_interval_limit: int
    policy_version: str
    budget_id: str

    @classmethod
    def default(cls):
        values = {
            "absolute_limit": 250, "ratio_limit": Decimal("0.0001"),
            "per_security_limit": 20, "per_security_consecutive_limit": 10,
            "exchange_concentration_limit": Decimal("0.75"),
            "month_concentration_limit": 25, "unknown_effective_interval_limit": 0,
            "policy_version": "status-exception-budget-v2",
        }
        identity = {key: str(value) if isinstance(value, Decimal) else value for key, value in values.items()}
        return cls(**values, budget_id=content_hash({"schema_version": "StatusExceptionBudgetV2", **identity}))

    def evaluate_records(self, records, *, applicable_symbol_sessions):
        records = tuple(records)
        by_security = Counter(str(item["security_identity"]) for item in records)
        by_exchange = Counter(str(item["exchange"]) for item in records)
        by_month = Counter(str(item["month"]) for item in records)
        unknown = sum(not bool(item["effective_interval_known"]) for item in records)
        longest = 0
        for identity in by_security:
            dates = sorted(self._parse_session(str(item["session"]))
                           for item in records if item["security_identity"] == identity)
            run = 0
            previous = None
            for current in dates:
                run = run + 1 if previous is not None and (current - previous).days <= 3 else 1
                longest = max(longest, run)
                previous = current
        total = len(records)
        reasons = []
        if total > self.absolute_limit:
            reasons.append("absolute_limit")
        if applicable_symbol_sessions <= 0 or Decimal(total) / Decimal(applicable_symbol_sessions) > self.ratio_limit:
            reasons.append("ratio_limit")
        if by_security and max(by_security.values()) > self.per_security_limit:
            reasons.append("per_security_limit")
        if longest > self.per_security_consecutive_limit:
            reasons.append("per_security_consecutive_limit")
        if total and max(by_exchange.values(), default=0) / total > float(self.exchange_concentration_limit):
            reasons.append("exchange_concentration_limit")
        if max(by_month.values(), default=0) > self.month_concentration_limit:
            reasons.append("month_concentration_limit")
        if unknown > self.unknown_effective_interval_limit:
            reasons.append("unknown_effective_interval_limit")
        systematic_names = {"per_security_consecutive_limit", "exchange_concentration_limit", "month_concentration_limit"}
        metrics = MappingProxyType({
            "total": total, "ratio": str(Decimal(total) / Decimal(applicable_symbol_sessions)) if applicable_symbol_sessions else "Infinity",
            "max_per_security": max(by_security.values(), default=0), "max_consecutive": longest,
            "max_exchange_share": str(Decimal(max(by_exchange.values(), default=0)) / Decimal(total)) if total else "0",
            "max_per_month": max(by_month.values(), default=0), "unknown_effective_intervals": unknown,
        })
        return StatusExceptionBudgetResultV2(
            passed=not reasons, systematic_pattern=bool(systematic_names & set(reasons)),
            reasons=tuple(reasons), metrics=metrics,
        )

    @staticmethod
    def _parse_session(value):
        if len(value) == 8 and value.isdigit():
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        return date.fromisoformat(value)
