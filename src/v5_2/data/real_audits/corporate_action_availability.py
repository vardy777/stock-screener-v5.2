from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from v5_2.data.corporate_action_facts import KnowledgeClass


class AvailabilityError(RuntimeError):
    """A safe corporate-action availability time cannot be established."""


@dataclass(frozen=True, slots=True)
class CorporateActionAvailabilityResultV1:
    available_at: datetime
    knowledge_class: KnowledgeClass
    basis: str


class CorporateActionAvailabilityPolicyV1:
    policy_version = "corporate-action-availability-v1"

    def __init__(self, *, approved_sessions: tuple[date, ...]):
        if approved_sessions != tuple(sorted(set(approved_sessions))):
            raise AvailabilityError("approved sessions must be canonical")
        self._sessions = approved_sessions
        self._timezone = timezone(timedelta(hours=8), "Asia/Shanghai")

    def _next_safe(self, day: date) -> datetime:
        next_session = next((session for session in self._sessions if session > day), None)
        if next_session is None:
            raise AvailabilityError("next approved session is missing")
        return datetime.combine(next_session, time(16, 30), self._timezone)

    def historical(
        self, *, published_at: datetime | None, publication_date: date | None
    ) -> CorporateActionAvailabilityResultV1:
        if published_at is not None:
            if published_at.tzinfo is None or published_at.utcoffset() is None:
                raise AvailabilityError("published_at must include timezone")
            return CorporateActionAvailabilityResultV1(
                published_at, KnowledgeClass.KNOWN_IN_ADVANCE, "VERIFIED_PUBLICATION_TIMESTAMP"
            )
        if publication_date is None:
            raise AvailabilityError("historical publication evidence is missing")
        return CorporateActionAvailabilityResultV1(
            self._next_safe(publication_date),
            KnowledgeClass.KNOWN_IN_ADVANCE,
            "DATE_ONLY_NEXT_SESSION_SAFE",
        )

    def economic_effect_only(self, *, effective_date: date) -> CorporateActionAvailabilityResultV1:
        return CorporateActionAvailabilityResultV1(
            self._next_safe(effective_date),
            KnowledgeClass.ECONOMIC_EFFECT_ONLY,
            "EFFECTIVE_DATE_ONLY_NEXT_SESSION_SAFE",
        )

    def production_observation(
        self,
        *,
        requested_at: datetime,
        observed_at: datetime,
        payload_hash: str,
        receipt_hash: str,
        source_version_identity: str,
    ) -> CorporateActionAvailabilityResultV1:
        if any(value.tzinfo is None or value.utcoffset() is None for value in (requested_at, observed_at)):
            raise AvailabilityError("observation timestamps must include timezone")
        if observed_at < requested_at:
            raise AvailabilityError("observed_at precedes requested_at")
        if not all(str(value).strip() for value in (payload_hash, receipt_hash, source_version_identity)):
            raise AvailabilityError("complete immutable observation lineage is required")
        return CorporateActionAvailabilityResultV1(
            observed_at, KnowledgeClass.KNOWN_IN_ADVANCE, "CONTEMPORANEOUS_OBSERVATION"
        )
