from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from v5_2.data.financial_disclosure_facts import (
    FinancialDisclosureFactV1, ReportType, ReportedValueSemantics, StatementType,
)
from v5_2.data.identity import content_hash


CONFIG = {
    "financial_income": (StatementType.INCOME, ("revenue", "n_income_attr_p"), ReportedValueSemantics.PERIOD_CUMULATIVE),
    "financial_balance_sheet": (StatementType.BALANCE_SHEET, ("total_assets", "total_liab"), ReportedValueSemantics.POINT_IN_TIME),
    "financial_cash_flow": (StatementType.CASH_FLOW, ("n_cashflow_act", "n_cashflow_inv_act"), ReportedValueSemantics.PERIOD_CUMULATIVE),
}
REPORT_TYPES = {"1": ReportType.Q1, "2": ReportType.H1, "3": ReportType.Q3, "4": ReportType.ANNUAL}


def _day(raw: object) -> date:
    if not isinstance(raw, str) or len(raw) != 8 or not raw.isdigit(): raise ValueError("invalid provider date")
    return date(int(raw[:4]), int(raw[4:6]), int(raw[6:]))


@dataclass(frozen=True, slots=True)
class FinancialNormalizationResultV1:
    facts: tuple[FinancialDisclosureFactV1, ...]
    quarantines: tuple[dict[str, object], ...]


def financial_fact_equivalence_key(fact: FinancialDisclosureFactV1) -> tuple[object, ...]:
    """Identity for collapsing the same disclosed fact reacquired in overlapping payloads."""
    return (
        fact.statement_type.value,
        fact.security_identity,
        fact.period_end,
        fact.metric,
        fact.published_at,
        format(fact.value, "f"),
        fact.report_type.value,
        fact.statement_scope,
    )


def normalize_statement_rows(dataset_kind: str, rows, *, source_version_identity: str, policy) -> FinancialNormalizationResultV1:
    if dataset_kind not in CONFIG: raise ValueError("unsupported statement dataset")
    statement, metrics, semantics = CONFIG[dataset_kind]
    candidates: dict[tuple[str, date, str, date], list[tuple[dict, Decimal]]] = {}
    quarantines = []
    for raw in rows:
        row = dict(raw)
        if str(row.get("report_type")) != "1":
            quarantines.append({"reason": "UNSUPPORTED_STATEMENT_SCOPE", "source_row_hash": content_hash(row)})
            continue
        try:
            period, publication = _day(row.get("end_date")), _day(row.get("f_ann_date") or row.get("ann_date"))
            report_type = REPORT_TYPES[str(row.get("end_type"))]
        except (ValueError, KeyError):
            quarantines.append({"reason": "INVALID_REPORT_OR_PUBLICATION_IDENTITY", "source_row_hash": content_hash(row)})
            continue
        for metric in metrics:
            try:
                if row.get(metric) is None: raise InvalidOperation
                value = Decimal(str(row[metric]))
            except (InvalidOperation, ValueError):
                quarantines.append({"reason": "MISSING_METRIC_VALUE", "metric": metric, "source_row_hash": content_hash(row)})
                continue
            candidates.setdefault((str(row["ts_code"]), period, metric, publication), []).append((row, value))
    facts = []
    by_key: dict[tuple[str, date, str], list[tuple[date, dict, Decimal]]] = {}
    for (security, period, metric, publication), versions in candidates.items():
        distinct = {value for _, value in versions}
        if len(distinct) != 1:
            quarantines.append({"reason": "CONFLICTING_VERSION_WITHOUT_TEMPORAL_ORDER", "security_identity": security,
                                "period_end": period.isoformat(), "metric": metric})
            continue
        chosen = max(versions, key=lambda item: str(item[0].get("update_flag") or ""))[0]
        by_key.setdefault((security, period, metric), []).append((publication, chosen, next(iter(distinct))))
    for (security, period, metric), versions in by_key.items():
        previous = None
        for publication, row, value in sorted(versions, key=lambda item: item[0]):
            source_id = content_hash({"dataset_kind": dataset_kind, "security": security, "period": period,
                                      "metric": metric, "publication": publication, "update_flag": row.get("update_flag"), "value": format(value, "f")})
            facts.append(FinancialDisclosureFactV1.create(security_identity=security, statement_type=statement,
                metric=metric, period_end=period, report_type=REPORT_TYPES[str(row["end_type"])],
                published_at=publication, available_at=policy.date_only(publication), value=value, unit="CNY", currency="CNY",
                reported_value_semantics=semantics, source_fact_id=source_id, source_version_identity=source_version_identity,
                revision_marker=str(row.get("update_flag") or ""), supersedes_source_fact_id=previous,
                announcement_date=_day(row.get("ann_date") or row.get("f_ann_date")), update_flag=str(row.get("update_flag") or ""),
                statement_scope="CONSOLIDATED"))
            previous = source_id
    identified = tuple({"quarantine_id": content_hash(item), **item} for item in quarantines)
    return FinancialNormalizationResultV1(tuple(sorted(facts, key=lambda fact: fact.fact_id)),
                                           tuple(sorted(identified, key=lambda item: item["quarantine_id"])))
