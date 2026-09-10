from __future__ import annotations

from decimal import Decimal
import re
from typing import Mapping, Sequence


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("－", "-")


def _date_forms(value: str) -> tuple[str, ...]:
    year, month, day = value[:4], int(value[4:6]), int(value[6:])
    return (
        value,
        f"{year}-{month:02d}-{day:02d}",
        f"{year}/{month}/{day}",
        f"{year}/{month:02d}/{day:02d}",
        f"{year}年{month}月{day}日",
    )


def _number_after(pattern: str, text: str) -> Decimal | None:
    match = re.search(pattern + r"([0-9]+(?:\.[0-9]+)?)元?", text)
    return Decimal(match.group(1)) if match else None


def _first_number(patterns: tuple[str, ...], text: str) -> Decimal | None:
    for pattern in patterns:
        number = _number_after(pattern, text)
        if number is not None:
            return number
    return None


def resolve_official_candidates(candidates: Sequence[Mapping[str, object]]) -> str:
    current = [
        item for item in candidates
        if "取消" not in _compact(str(item.get("title") or ""))
        and "更正公告" not in _compact(str(item.get("title") or ""))
        and item.get("disposition") != "RETRACTED"
    ]
    dispositions = {str(item.get("disposition")) for item in current}
    if "MISMATCH" in dispositions:
        return "MISMATCH"
    if "MATCH" in dispositions:
        return "MATCH"
    if "UNRESOLVED" in dispositions:
        return "UNRESOLVED"
    return "UNAVAILABLE"


def validate_official_text(
    *, security_code: str, announcement_date: str, record_date: str, ex_date: str,
    cash_per_share: Decimal, bonus_per_share: Decimal, title: str, text: str,
) -> str:
    body = _compact(text)
    compact_title = _compact(title)
    if "已取消" in compact_title or "取消" in compact_title:
        return "RETRACTED"
    if "实施公告" not in compact_title and "分红派息公告" not in compact_title:
        return "UNRESOLVED"
    codes = set(re.findall(r"(?<!\d)[036]\d{5}(?!\d)", body))
    if security_code not in codes:
        return "MISMATCH" if codes else "UNRESOLVED"
    for expected in (record_date, ex_date):
        if not any(form in body for form in _date_forms(expected)):
            return "MISMATCH" if re.search(r"20\d{2}年\d{1,2}月\d{1,2}日", body) else "UNRESOLVED"
    expected_cash = cash_per_share * 10
    actual_cash = _first_number((
        r"每10股.{0,40}?派(?:发)?(?:人民币)?(?:现金红利|现金股息)?",
        r"每10股(?:派发)?(?:现金红利|现金股息)",
    ), body)
    per_share_cash = _first_number((
        r"每股(?:派发)?(?:人民币)?(?:现金红利|现金股息)(?:人民币)?",
        r"每股现金红利(?:人民币)?",
    ), body)
    if expected_cash > 0:
        if actual_cash is None and per_share_cash is not None:
            actual_cash = per_share_cash * 10
        if actual_cash is None:
            return "UNRESOLVED"
        if abs(actual_cash - expected_cash) > Decimal("0.00001"):
            return "MISMATCH"
    expected_bonus = bonus_per_share * 10
    actual_bonus = _first_number((r"每10股.{0,40}?送(?:红股)?",), body)
    per_share_bonus = _first_number((r"每股(?:派)?送(?:红股)?",), body)
    if expected_bonus > 0:
        if actual_bonus is None and per_share_bonus is not None:
            actual_bonus = per_share_bonus * 10
        if actual_bonus is None:
            return "UNRESOLVED"
        if abs(actual_bonus - expected_bonus) > Decimal("0.00001"):
            return "MISMATCH"
    return "MATCH"
