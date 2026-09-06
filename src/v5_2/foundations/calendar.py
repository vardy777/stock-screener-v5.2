from __future__ import annotations

from datetime import date
from typing import Iterable, Mapping

from .calendar_contract import validate_calendar_records
from .core import ContractViolation


class TradingCalendar:
    def __init__(self, sessions: Mapping[date, bool]):
        self._sessions = dict(sessions)

    @classmethod
    def from_records(
        cls,
        records: Iterable[Mapping[str, object]],
        *,
        require_complete_years: bool = True,
    ) -> "TradingCalendar":
        return cls(validate_calendar_records(records, require_complete_years=require_complete_years))

    def is_open(self, day: date) -> bool:
        if day not in self._sessions:
            raise ContractViolation("calendar date unavailable")
        return self._sessions[day]

    def shift(self, day: date, sessions: int) -> date:
        if sessions == 0:
            if not self.is_open(day):
                raise ContractViolation("anchor is not an open session")
            return day
        if day not in self._sessions or not self._sessions[day]:
            raise ContractViolation("anchor is not an open session")
        open_days = sorted(value for value, is_open in self._sessions.items() if is_open)
        index = open_days.index(day) + sessions
        if index < 0 or index >= len(open_days):
            raise ContractViolation("shifted trading session unavailable")
        return open_days[index]
