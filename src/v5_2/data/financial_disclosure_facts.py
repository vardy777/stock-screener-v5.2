from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from v5_2.data.identity import content_hash


class StatementType(str, Enum):
    INCOME = "INCOME"
    BALANCE_SHEET = "BALANCE_SHEET"
    CASH_FLOW = "CASH_FLOW"


class ReportType(str, Enum):
    Q1 = "Q1"
    H1 = "H1"
    Q3 = "Q3"
    ANNUAL = "ANNUAL"


class ReportedValueSemantics(str, Enum):
    PERIOD_CUMULATIVE = "PERIOD_CUMULATIVE"
    POINT_IN_TIME = "POINT_IN_TIME"


@dataclass(frozen=True, slots=True)
class FinancialDisclosureFactV1:
    fact_id: str
    security_identity: str
    statement_type: StatementType
    metric: str
    period_end: date
    report_type: ReportType
    published_at: date | datetime
    available_at: datetime
    value: Decimal
    unit: str
    currency: str
    reported_value_semantics: ReportedValueSemantics
    source_fact_id: str
    source_version_identity: str
    revision_marker: str
    supersedes_source_fact_id: str | None
    announcement_date: date
    update_flag: str
    statement_scope: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        for name in ("security_identity", "metric", "unit", "currency", "source_fact_id",
                     "source_version_identity", "revision_marker", "statement_scope"):
            if not str(values.get(name) or "").strip(): raise ValueError(f"{name} is required")
        available = values["available_at"]
        if available.tzinfo is None or available.utcoffset() is None:
            raise ValueError("available_at must be timezone-aware")
        statement = StatementType(values["statement_type"])
        semantics = ReportedValueSemantics(values["reported_value_semantics"])
        expected = ReportedValueSemantics.POINT_IN_TIME if statement is StatementType.BALANCE_SHEET else ReportedValueSemantics.PERIOD_CUMULATIVE
        if semantics is not expected: raise ValueError("statement value semantics mismatch")
        canonical = dict(values)
        canonical["statement_type"] = statement
        canonical["report_type"] = ReportType(values["report_type"])
        canonical["reported_value_semantics"] = semantics
        canonical["value"] = Decimal(values["value"])
        body = {"schema_version": "FinancialDisclosureFactV1", **canonical,
                "value": format(canonical["value"], "f")}
        digest = content_hash(body)
        return cls(fact_id=digest, content_hash=digest, **canonical)

    def verify(self) -> bool:
        body = {"schema_version": "FinancialDisclosureFactV1", **{
            field.name: getattr(self, field.name) for field in fields(self)
            if field.name not in {"fact_id", "content_hash"}
        }}
        body["value"] = format(self.value, "f")
        return self.fact_id == self.content_hash == content_hash(body)
