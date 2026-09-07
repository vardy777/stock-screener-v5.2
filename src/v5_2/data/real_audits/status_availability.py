from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from v5_2.data.identity import content_hash


class StatusAvailabilityError(RuntimeError):
    """Historical status knowledge time cannot be derived conservatively."""


@dataclass(frozen=True, slots=True)
class StatusAvailabilityPolicyV1:
    basis: str
    policy_version: str
    policy_id: str

    @classmethod
    def _create(cls, basis):
        version = "status-date-only-next-session-v1" if basis == "DATE_ONLY_NEXT_SESSION" else "status-verified-timestamp-v1"
        digest = content_hash({"schema_version": "StatusAvailabilityPolicyV1", "basis": basis, "policy_version": version})
        return cls(basis, version, digest)

    @classmethod
    def date_only_next_session(cls):
        return cls._create("DATE_ONLY_NEXT_SESSION")

    @classmethod
    def verified_timestamp(cls):
        return cls._create("VERIFIED_TIMESTAMP")

    def derive(self, *, event_date: date, published_at: datetime | None, approved_sessions,
               acquired_at: datetime | None = None) -> datetime:
        del acquired_at
        if self.basis == "VERIFIED_TIMESTAMP":
            if published_at is None or published_at.tzinfo is None or published_at.utcoffset() is None:
                raise StatusAvailabilityError("verified publication timestamp is unavailable")
            return published_at
        later = tuple(sorted(session for session in approved_sessions if session > event_date))
        if not later:
            raise StatusAvailabilityError("next session is outside approved calendar")
        zone = timezone(timedelta(hours=8), "Asia/Shanghai")
        return datetime.combine(later[0], time(15, 0), zone)


@dataclass(frozen=True, slots=True)
class StatusAvailabilityPolicyV2:
    basis: str
    semantic: str
    policy_version: str
    policy_id: str

    @classmethod
    def _create(cls, basis: str, semantic: str):
        version = "status-availability-after-close-v2"
        digest = content_hash({"schema_version": "StatusAvailabilityPolicyV2", "basis": basis,
                               "semantic": semantic, "research_cutoff": "16:30:00+08:00",
                               "policy_version": version})
        return cls(basis, semantic, version, digest)

    @classmethod
    def publication_timestamp(cls, semantic: str):
        return cls._create("PUBLICATION_TIMESTAMP_BASED", semantic)

    @classmethod
    def market_observable_by_close(cls, semantic: str):
        return cls._create("MARKET_OBSERVABLE_BY_CLOSE", semantic)

    @classmethod
    def conservative_after_close(cls, semantic: str):
        return cls._create("CONSERVATIVE_AFTER_CLOSE", semantic)

    @classmethod
    def next_session_safe(cls, semantic: str):
        return cls._create("NEXT_SESSION_SAFE", semantic)

    def derive(self, *, event_date: date, published_at: datetime | None, approved_sessions,
               acquired_at: datetime | None = None) -> datetime:
        del acquired_at
        zone = timezone(timedelta(hours=8), "Asia/Shanghai")
        if self.basis == "PUBLICATION_TIMESTAMP_BASED":
            if published_at is None or published_at.tzinfo is None or published_at.utcoffset() is None:
                raise StatusAvailabilityError("verified publication timestamp is unavailable")
            return published_at
        if self.basis in {"MARKET_OBSERVABLE_BY_CLOSE", "CONSERVATIVE_AFTER_CLOSE"}:
            if event_date not in approved_sessions:
                raise StatusAvailabilityError("event date is outside approved calendar")
            return datetime.combine(event_date, time(16, 30), zone)
        later = tuple(sorted(session for session in approved_sessions if session > event_date))
        if not later:
            raise StatusAvailabilityError("next session is outside approved calendar")
        return datetime.combine(later[0], time(16, 30), zone)
