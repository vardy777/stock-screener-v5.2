from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


ASIA_SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")


class FinancialDisclosureAvailabilityError(RuntimeError):
    """A disclosure availability time cannot be established safely."""


class FinancialDisclosureAvailabilityPolicyV1:
    policy_version = "FinancialDisclosureAvailabilityPolicyV1"

    def __init__(self, approved_sessions) -> None:
        self._sessions = tuple(sorted(set(approved_sessions)))
        if not self._sessions:
            raise FinancialDisclosureAvailabilityError("approved sessions are required")

    def date_only(self, published_on: date) -> datetime:
        try:
            next_session = next(session for session in self._sessions if session > published_on)
        except StopIteration:
            raise FinancialDisclosureAvailabilityError("next approved session unavailable") from None
        return datetime.combine(next_session, time(16, 30), ASIA_SHANGHAI)

    def observed(self, observed_at: datetime) -> datetime:
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise FinancialDisclosureAvailabilityError("observed_at must be timezone-aware")
        return observed_at
