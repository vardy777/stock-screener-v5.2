from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class IncompleteCalendarCoverage(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LabelHorizonsV1:
    h1: date
    h3: date
    h5: date
    window_5d: tuple[date, ...]
    completed: tuple[bool, bool, bool]


def resolve_label_horizons(anchor_session: date, approved_exchange_sessions: tuple[date, ...], latest_completed_session: date) -> LabelHorizonsV1:
    if len(set(approved_exchange_sessions)) != len(approved_exchange_sessions):
        raise IncompleteCalendarCoverage("DUPLICATE_APPROVED_SESSION")
    if tuple(sorted(approved_exchange_sessions)) != approved_exchange_sessions:
        raise IncompleteCalendarCoverage("NON_MONOTONIC_APPROVED_CALENDAR")
    if anchor_session not in approved_exchange_sessions:
        raise IncompleteCalendarCoverage("ANCHOR_SESSION_ABSENT")
    future = tuple(day for day in approved_exchange_sessions if day > anchor_session)
    if len(future) < 5:
        raise IncompleteCalendarCoverage("INSUFFICIENT_FUTURE_COVERAGE")
    horizons = (future[0], future[2], future[4])
    return LabelHorizonsV1(*horizons, future[:5], tuple(day <= latest_completed_session for day in horizons))
