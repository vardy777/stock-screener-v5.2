from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Any


class AuditDecision(str, Enum):
    PASS = "PASS"
    PASS_WITH_RULES = "PASS_WITH_RULES"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class DatasetAuditResult:
    decision: AuditDecision
    row_count: int
    findings: tuple[str, ...]
    derived_rules: tuple[str, ...] = ()


def _day(value: object) -> date | None:
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError:
        return None


def audit_trade_calendar(
    rows: Iterable[Mapping[str, Any]], *, start: date, end: date, exchanges: tuple[str, ...]
) -> DatasetAuditResult:
    materialized = tuple(rows)
    by_key: dict[tuple[str, date], Mapping[str, Any]] = {}
    failures: set[str] = set()
    for row in materialized:
        day = _day(row.get("cal_date"))
        exchange = row.get("exchange")
        state = row.get("is_open")
        if day is None or exchange not in exchanges or state not in (0, 1):
            failures.add("invalid calendar schema or semantics")
            continue
        key = (str(exchange), day)
        if key in by_key:
            failures.add("duplicate exchange/calendar date")
        by_key[key] = row
    expected_days = (end - start).days + 1
    if len(by_key) != expected_days * len(exchanges):
        failures.add("coverage is not continuous")
    for exchange in exchanges:
        previous_open: date | None = None
        cursor = start
        while cursor <= end:
            row = by_key.get((exchange, cursor))
            if row is not None:
                supplied_previous = _day(row.get("pretrade_date"))
                if previous_open is not None and supplied_previous != previous_open:
                    failures.add("previous trading session semantics mismatch")
                if row.get("is_open") == 1:
                    previous_open = cursor
            cursor += timedelta(days=1)
    decision = AuditDecision.FAIL if failures else AuditDecision.PASS
    return DatasetAuditResult(decision, len(materialized), tuple(sorted(failures)))


def audit_security_master(rows: Iterable[Mapping[str, Any]]) -> DatasetAuditResult:
    materialized = tuple(rows)
    failures: set[str] = set()
    keys: set[str] = set()
    delisted = 0
    required = {"ts_code", "symbol", "name", "market", "exchange", "list_status", "list_date", "delist_date"}
    for row in materialized:
        if set(row) < required:
            failures.add("required native field missing")
            continue
        code = row.get("ts_code")
        if not isinstance(code, str) or code in keys:
            failures.add("invalid or duplicate security identity")
        else:
            keys.add(code)
        if row.get("exchange") not in ("SSE", "SZSE") or row.get("list_status") not in ("L", "D", "P"):
            failures.add("invalid exchange or listing status")
        if _day(row.get("list_date")) is None:
            failures.add("invalid listing date")
        if row.get("list_status") == "D":
            delisted += 1
            if _day(row.get("delist_date")) is None:
                failures.add("delisted security lacks delisting date")
    if delisted == 0:
        failures.add("historically delisted coverage missing")
    rules = (
        "board<-market",
        "is_a_share<-ts_code/exchange",
        "security_type<-A-share code/exchange",
    )
    decision = AuditDecision.FAIL if failures else AuditDecision.PASS_WITH_RULES
    return DatasetAuditResult(decision, len(materialized), tuple(sorted(failures)), rules)


def audit_daily_bars(
    rows: Iterable[Mapping[str, Any]], *, price_basis: str
) -> DatasetAuditResult:
    materialized = tuple(rows)
    failures: set[str] = set()
    keys: set[tuple[object, object]] = set()
    required = {"ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"}
    if price_basis != "UNADJUSTED_RAW":
        failures.add("adjusted-price contamination")
    for row in materialized:
        if set(row) < required:
            failures.add("required daily field missing")
            continue
        key = (row.get("ts_code"), row.get("trade_date"))
        if key in keys:
            failures.add("duplicate symbol/session")
        keys.add(key)
        if _day(row.get("trade_date")) is None:
            failures.add("invalid session date")
        try:
            open_, high, low, close = (float(row[name]) for name in ("open", "high", "low", "close"))
            volume, amount = float(row["vol"]), float(row["amount"])
            if high < max(open_, close, low) or low > min(open_, close, high):
                failures.add("OHLC invariant failure")
            if volume < 0 or amount < 0:
                failures.add("negative volume or amount")
        except (TypeError, ValueError):
            failures.add("non-numeric market value")
    rules = ("volume_shares<-vol_lots*100", "amount_cny<-amount_thousand_cny*1000")
    decision = AuditDecision.FAIL if failures else AuditDecision.PASS_WITH_RULES
    return DatasetAuditResult(decision, len(materialized), tuple(sorted(failures)), rules)
