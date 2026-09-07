from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from v5_2.data.real_audits.daily_bar_normalization import DailyBarNormalizationError, finite_decimal


@dataclass(frozen=True, slots=True)
class DailyBarStructuralAuditV1:
    total: int
    malformed: int
    ohlc_failures: int
    negative_value_failures: int
    session_failures: int
    identity_failures: int
    schema_pass: bool
    ohlc_pass: bool
    session_alignment_pass: bool
    identity_alignment_pass: bool
    passed: bool


def audit_bars(rows, *, approved_sessions, identity_resolver):
    malformed = ohlc = negative = session_bad = identity_bad = 0
    required = {"ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"}
    for row in rows:
        if set(row) < required:
            malformed += 1
            continue
        try:
            session = date(int(str(row["trade_date"])[:4]), int(str(row["trade_date"])[4:6]), int(str(row["trade_date"])[6:8]))
            op, high, low, close, vol, amount = (finite_decimal(row[key]) for key in ("open", "high", "low", "close", "vol", "amount"))
        except (DailyBarNormalizationError, ValueError):
            malformed += 1
            continue
        if min(op, high, low, close) <= 0 or high < max(op, close, low) or low > min(op, close):
            ohlc += 1
        if vol < 0 or amount < 0:
            negative += 1
        if session not in approved_sessions:
            session_bad += 1
        if identity_resolver(str(row["ts_code"]), session) != str(row["ts_code"]):
            identity_bad += 1
    schema_pass = malformed == 0
    ohlc_pass = ohlc == 0 and negative == 0
    session_pass = session_bad == 0
    identity_pass = identity_bad == 0
    return DailyBarStructuralAuditV1(len(rows), malformed, ohlc, negative, session_bad, identity_bad,
                                     schema_pass, ohlc_pass, session_pass, identity_pass,
                                     schema_pass and ohlc_pass and session_pass and identity_pass)
