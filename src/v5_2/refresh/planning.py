from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Sequence


SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")
D_CLOSE = time(16, 30)


@dataclass(frozen=True, slots=True)
class ApprovedCalendarView:
    manifest_id: str
    coverage_start: date
    coverage_end: date
    open_sessions: tuple[date, ...]

    def __post_init__(self) -> None:
        if self.coverage_end < self.coverage_start:
            raise ValueError("calendar coverage is inverted")
        if tuple(sorted(set(self.open_sessions))) != self.open_sessions:
            raise ValueError("open sessions must be unique and ordered")
        if any(not self.coverage_start <= item <= self.coverage_end for item in self.open_sessions):
            raise ValueError("open session outside approved coverage")


@dataclass(frozen=True, slots=True)
class TargetSessionResolutionV1:
    today: date
    is_trading_day: bool | None
    target_session: date | None
    latest_completed_session: date | None
    reason: str | None


def resolve_target_session(now: datetime, calendar: ApprovedCalendarView) -> TargetSessionResolutionV1:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    local = now.astimezone(SHANGHAI)
    today = local.date()
    if not calendar.coverage_start <= today <= calendar.coverage_end:
        return TargetSessionResolutionV1(today, None, None, None, "CALENDAR_DOES_NOT_COVER_TODAY")
    open_set = set(calendar.open_sessions)
    is_open = today in open_set
    candidates = [item for item in calendar.open_sessions if item < today]
    if is_open and local.time().replace(tzinfo=None) >= D_CLOSE:
        target = today
    else:
        target = candidates[-1] if candidates else None
    reason = None if target else "NO_COMPLETED_APPROVED_OPEN_SESSION"
    return TargetSessionResolutionV1(today, is_open, target, target, reason)


@dataclass(frozen=True, slots=True)
class IncrementalGapPlanV1:
    target_session: date
    required_sessions: tuple[date, ...]
    completed_sessions: tuple[date, ...]
    missing_sessions: tuple[date, ...]


def detect_session_gaps(open_sessions: Sequence[date], completed_sessions: Sequence[date],
                        target_session: date) -> IncrementalGapPlanV1:
    required = tuple(sorted({item for item in open_sessions if item <= target_session}))
    completed_set = set(completed_sessions)
    completed = tuple(item for item in required if item in completed_set)
    missing = tuple(item for item in required if item not in completed_set)
    return IncrementalGapPlanV1(target_session, required, completed, missing)
