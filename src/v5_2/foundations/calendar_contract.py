from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Mapping

from .core import ContractViolation, strict_bool, strict_str


OFFICIAL_SOURCES = {"SSE", "SZSE"}


def _whole_year(year: int):
    current = date(year, 1, 1)
    end = date(year, 12, 31)
    while current <= end:
        yield current
        current += timedelta(days=1)


def validate_calendar_records(
    records: Iterable[Mapping[str, object]], *, require_complete_years: bool = True
) -> dict[date, bool]:
    strict_bool(require_complete_years, "require_complete_years")
    sessions: dict[date, bool] = {}
    for row in records:
        if not {"date", "is_open", "source"}.issubset(row):
            raise ContractViolation("calendar columns are incomplete")
        try:
            session = date.fromisoformat(strict_str(row["date"], "date"))
        except ValueError as exc:
            raise ContractViolation("calendar contains invalid date") from exc
        if session in sessions:
            raise ContractViolation("calendar contains duplicate date")
        source = strict_str(row["source"], "source")
        if source not in OFFICIAL_SOURCES:
            raise ContractViolation("calendar source is not approved")
        sessions[session] = strict_bool(row["is_open"], "is_open")
    if not sessions:
        raise ContractViolation("calendar is empty")
    if require_complete_years:
        for year in {day.year for day in sessions}:
            expected = set(_whole_year(year))
            actual = {day for day in sessions if day.year == year}
            if actual != expected:
                raise ContractViolation(f"calendar year {year} is incomplete")
    return sessions
