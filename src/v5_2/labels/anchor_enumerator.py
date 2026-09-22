from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import re
from typing import Iterator

from v5_2.data.identity import content_hash
from v5_2.refresh.eligibility import evaluate_ipo_eligibility


_ID = re.compile(r"^[0-9a-f]{64}$")


class AnchorDispositionKind(StrEnum):
    EFFECTIVE = "EFFECTIVE"
    ELIGIBLE = "ELIGIBLE"
    EXCLUDED_BEFORE_LABEL = "EXCLUDED_BEFORE_LABEL"


@dataclass(frozen=True, slots=True)
class IdentityIntervalV1:
    security_identity: str
    canonical_security_identity: str
    exchange: str
    effective_from: date
    effective_to: date | None

    def applies(self, session: date) -> bool:
        return self.effective_from <= session and (self.effective_to is None or session <= self.effective_to)


@dataclass(frozen=True, slots=True)
class StatusObservationV1:
    security_identity: str
    session: date
    full_day_suspended: bool


@dataclass(frozen=True, slots=True)
class HistoricalAnchorLineageV1:
    calendar_approval_id: str
    calendar_manifest_id: str
    master_approval_id: str
    master_manifest_id: str
    status_approval_id: str
    status_manifest_id: str
    open_sessions: tuple[date, ...]
    identity_intervals: tuple[IdentityIntervalV1, ...]
    status_observations: tuple[StatusObservationV1, ...]
    revoked_approval_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, *, calendar_approval_id: str, calendar_manifest_id: str,
               master_approval_id: str, master_manifest_id: str,
               status_approval_id: str, status_manifest_id: str,
               open_sessions: tuple[date, ...], identity_intervals: tuple[IdentityIntervalV1, ...],
               status_observations: tuple[StatusObservationV1, ...],
               revoked_approval_ids: tuple[str, ...] = ()) -> "HistoricalAnchorLineageV1":
        body = {
            "calendar_approval_id": calendar_approval_id, "calendar_manifest_id": calendar_manifest_id,
            "master_approval_id": master_approval_id, "master_manifest_id": master_manifest_id,
            "status_approval_id": status_approval_id, "status_manifest_id": status_manifest_id,
            "open_sessions": open_sessions, "identity_intervals": identity_intervals,
            "status_observations": status_observations, "revoked_approval_ids": revoked_approval_ids,
        }
        return cls(**body, content_hash=content_hash({"schema_version": cls.__name__, **body}))

    def verify(self) -> bool:
        ids = (self.calendar_approval_id, self.calendar_manifest_id, self.master_approval_id,
               self.master_manifest_id, self.status_approval_id, self.status_manifest_id)
        if not all(_ID.fullmatch(value) for value in ids):
            return False
        if any(value in self.revoked_approval_ids for value in (self.calendar_approval_id, self.master_approval_id, self.status_approval_id)):
            return False
        if not self.open_sessions or self.open_sessions != tuple(sorted(set(self.open_sessions))):
            return False
        pairs = tuple((item.security_identity, item.session) for item in self.status_observations)
        if len(pairs) != len(set(pairs)):
            return False
        for item in self.identity_intervals:
            if item.exchange not in {"SSE", "SZSE"} or not item.security_identity or not item.canonical_security_identity:
                return False
            if item.effective_to is not None and item.effective_to < item.effective_from:
                return False
        for index, left in enumerate(self.identity_intervals):
            for right in self.identity_intervals[index + 1:]:
                if left.security_identity == right.security_identity:
                    left_end = left.effective_to or date.max
                    right_end = right.effective_to or date.max
                    if max(left.effective_from, right.effective_from) <= min(left_end, right_end):
                        return False
        body = {name: getattr(self, name) for name in (
            "calendar_approval_id", "calendar_manifest_id", "master_approval_id", "master_manifest_id",
            "status_approval_id", "status_manifest_id", "open_sessions", "identity_intervals",
            "status_observations", "revoked_approval_ids",
        )}
        return self.content_hash == content_hash({"schema_version": type(self).__name__, **body})


@dataclass(frozen=True, slots=True)
class AnchorDispositionV1:
    security_identity: str
    canonical_security_identity: str
    anchor_session: date
    exchange: str
    effective: bool
    full_day_suspended: bool
    disposition: AnchorDispositionKind
    reason: str | None


def enumerate_historical_anchors(lineage: HistoricalAnchorLineageV1, start: date, end: date) -> Iterator[AnchorDispositionV1]:
    if start > end or not lineage.verify():
        raise ValueError("historical anchor lineage invalid")
    statuses = {(item.security_identity, item.session): item for item in lineage.status_observations}
    sessions = tuple(day for day in lineage.open_sessions if start <= day <= end)
    for session in sessions:
        for interval in sorted((item for item in lineage.identity_intervals if item.applies(session)), key=lambda item: (item.canonical_security_identity, item.security_identity)):
            status = statuses.get((interval.security_identity, session))
            if status is None:
                yield AnchorDispositionV1(interval.security_identity, interval.canonical_security_identity, session,
                    interval.exchange, True, False, AnchorDispositionKind.EXCLUDED_BEFORE_LABEL, "STATUS_UNRESOLVED")
                continue
            eligibility = evaluate_ipo_eligibility(
                symbol=interval.canonical_security_identity, list_date=interval.effective_from,
                as_of_session=session, approved_open_sessions=lineage.open_sessions,
                official_identity_verified=True, bar_coverage_valid=True, status_resolved=True,
            )
            if eligibility.research_eligible:
                kind, reason = AnchorDispositionKind.ELIGIBLE, None
            else:
                kind, reason = AnchorDispositionKind.EXCLUDED_BEFORE_LABEL, eligibility.exclusion_reason
            yield AnchorDispositionV1(interval.security_identity, interval.canonical_security_identity, session,
                interval.exchange, True, status.full_day_suspended, kind, reason)
