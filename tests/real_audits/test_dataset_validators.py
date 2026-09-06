from __future__ import annotations

from datetime import date

from v5_2.data.real_audits.validators import (
    AuditDecision,
    audit_daily_bars,
    audit_security_master,
    audit_trade_calendar,
)


def test_calendar_requires_every_date_and_explicit_state() -> None:
    rows = [
        {"exchange": "SSE", "cal_date": "20250101", "is_open": 0, "pretrade_date": "20241231"},
        {"exchange": "SSE", "cal_date": "20250102", "is_open": 1, "pretrade_date": "20241231"},
    ]
    passed = audit_trade_calendar(rows, start=date(2025, 1, 1), end=date(2025, 1, 2), exchanges=("SSE",))
    assert passed.decision is AuditDecision.PASS
    assert passed.row_count == 2
    assert audit_trade_calendar(rows[:1], start=date(2025, 1, 1), end=date(2025, 1, 2), exchanges=("SSE",)).decision is AuditDecision.FAIL
    bad = [dict(rows[0], is_open=None), rows[1]]
    assert audit_trade_calendar(bad, start=date(2025, 1, 1), end=date(2025, 1, 2), exchanges=("SSE",)).decision is AuditDecision.FAIL


def test_calendar_rejects_duplicate_and_wrong_previous_session() -> None:
    rows = [
        {"exchange": "SSE", "cal_date": "20250101", "is_open": 1, "pretrade_date": "20241231"},
        {"exchange": "SSE", "cal_date": "20250102", "is_open": 1, "pretrade_date": "20240101"},
    ]
    assert audit_trade_calendar(rows, start=date(2025, 1, 1), end=date(2025, 1, 2), exchanges=("SSE",)).decision is AuditDecision.FAIL
    assert audit_trade_calendar(rows + [rows[1]], start=date(2025, 1, 1), end=date(2025, 1, 2), exchanges=("SSE",)).decision is AuditDecision.FAIL


def test_master_derives_board_and_a_share_without_hiding_source() -> None:
    rows = [
        {"ts_code": "600000.SH", "symbol": "600000", "name": "A", "market": "主板", "exchange": "SSE", "list_status": "L", "list_date": "19991110", "delist_date": None},
        {"ts_code": "300001.SZ", "symbol": "300001", "name": "B", "market": "创业板", "exchange": "SZSE", "list_status": "D", "list_date": "20091030", "delist_date": "20250101"},
    ]
    result = audit_security_master(rows)
    assert result.decision is AuditDecision.PASS_WITH_RULES
    assert result.row_count == 2
    assert result.derived_rules == ("board<-market", "is_a_share<-ts_code/exchange", "security_type<-A-share code/exchange")


def test_master_requires_historical_delisted_and_rejects_duplicates() -> None:
    listed = {"ts_code": "600000.SH", "symbol": "600000", "name": "A", "market": "主板", "exchange": "SSE", "list_status": "L", "list_date": "19991110", "delist_date": None}
    assert audit_security_master([listed]).decision is AuditDecision.FAIL
    assert audit_security_master([listed, listed]).decision is AuditDecision.FAIL


def test_daily_bar_invariants_and_unadjusted_contract() -> None:
    row = {"ts_code": "000001.SZ", "trade_date": "20250102", "open": 10, "high": 12, "low": 9, "close": 11, "vol": 100, "amount": 1000}
    assert audit_daily_bars([row], price_basis="UNADJUSTED_RAW").decision is AuditDecision.PASS_WITH_RULES
    assert audit_daily_bars([dict(row, high=8)], price_basis="UNADJUSTED_RAW").decision is AuditDecision.FAIL
    assert audit_daily_bars([row], price_basis="QFQ").decision is AuditDecision.FAIL
    assert audit_daily_bars([row, row], price_basis="UNADJUSTED_RAW").decision is AuditDecision.FAIL
