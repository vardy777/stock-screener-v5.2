from datetime import date

import pytest

from v5_2.foundations.calendar import TradingCalendar
from v5_2.foundations.calendar_contract import validate_calendar_records
from v5_2.foundations.core import ContractViolation


RECORDS = [
    {"date": "2026-01-01", "is_open": False, "source": "SSE"},
    {"date": "2026-01-02", "is_open": True, "source": "SSE"},
    {"date": "2026-01-03", "is_open": False, "source": "SSE"},
    {"date": "2026-01-04", "is_open": False, "source": "SSE"},
    {"date": "2026-01-05", "is_open": True, "source": "SSE"},
]


def test_calendar_open_close_and_session_shift():
    calendar = TradingCalendar.from_records(RECORDS, require_complete_years=False)
    assert calendar.is_open(date(2026, 1, 2))
    assert not calendar.is_open(date(2026, 1, 3))
    assert calendar.shift(date(2026, 1, 2), 1) == date(2026, 1, 5)
    assert calendar.shift(date(2026, 1, 5), -1) == date(2026, 1, 2)
    with pytest.raises(ContractViolation):
        calendar.is_open(date(2026, 1, 6))


def test_calendar_rejects_duplicates_invalid_source_and_incomplete_year():
    with pytest.raises(ContractViolation):
        validate_calendar_records(RECORDS + [RECORDS[0]], require_complete_years=False)
    bad = [dict(row) for row in RECORDS]
    bad[0]["source"] = "blog"
    with pytest.raises(ContractViolation):
        validate_calendar_records(bad, require_complete_years=False)
    with pytest.raises(ContractViolation):
        validate_calendar_records(RECORDS, require_complete_years=True)
