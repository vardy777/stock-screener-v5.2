from __future__ import annotations

from datetime import date, datetime


class StatusResolutionError(LookupError):
    """A historical identity cannot be resolved without guessing."""


class HistoricalStatusRepositoryV1:
    """Small PIT resolver over lifecycle, risk-warning and suspension intervals."""

    def __init__(self, *, lifecycles, risk_warning_intervals, full_day_suspensions):
        self._lifecycles = {identity: (start, end) for identity, start, end in lifecycles}
        if len(self._lifecycles) != len(tuple(lifecycles)):
            raise StatusResolutionError("conflicting lifecycle identity")
        self._risk = tuple(risk_warning_intervals)
        self._suspensions = tuple(full_day_suspensions)

    def resolve(self, identity: str, session: date, cutoff: datetime) -> dict[str, bool]:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise StatusResolutionError("cutoff must be timezone-aware")
        if identity not in self._lifecycles:
            raise StatusResolutionError("lifecycle is missing")
        start, end = self._lifecycles[identity]
        listed = start <= session and (end is None or session <= end)
        risk = any(item_identity == identity and effective_start <= session
                   and (effective_end is None or session <= effective_end)
                   and available_at <= cutoff
                   for item_identity, effective_start, effective_end, available_at in self._risk)
        suspended = any(item_identity == identity and event_session == session and available_at <= cutoff
                        for item_identity, event_session, available_at in self._suspensions)
        return {"listed": listed, "risk_warning": listed and risk, "suspended": listed and suspended}
