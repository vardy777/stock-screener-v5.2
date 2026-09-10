from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Mapping, Sequence

from v5_2.data.identity import content_hash


class UpstreamExtensionError(RuntimeError):
    """An incremental upstream fact cannot be used without guessing."""


def _day(value: object) -> date:
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        raise UpstreamExtensionError("effective date is missing or invalid")
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError as error:
        raise UpstreamExtensionError("effective date is missing or invalid") from error


@dataclass(frozen=True, slots=True)
class IncrementalCalendarExtensionV1:
    extension_id: str
    supersedes_approval_id: str
    coverage_start: date
    coverage_end: date
    ordered_rows: tuple[tuple[str, str, int], ...]
    official_anchor_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, *, previous_approval_id: str, coverage_start: date,
               coverage_end: date, rows: Sequence[Mapping[str, Any]],
               official_anchor_ids: Sequence[str]):
        if not previous_approval_id or coverage_end < coverage_start:
            raise UpstreamExtensionError("invalid calendar extension scope")
        anchors = tuple(sorted(set(official_anchor_ids)))
        if len(anchors) < 2:
            raise UpstreamExtensionError("both exchange official anchors are required")
        canonical = tuple(sorted(
            (str(row.get("exchange")), str(row.get("cal_date")), int(row.get("is_open", -1)))
            for row in rows
        ))
        expected = {
            (exchange, (coverage_start + timedelta(days=offset)).strftime("%Y%m%d"))
            for exchange in ("SSE", "SZSE")
            for offset in range((coverage_end - coverage_start).days + 1)
        }
        keys = {(exchange, day) for exchange, day, state in canonical if state in (0, 1)}
        if keys != expected or len(canonical) != len(expected):
            raise UpstreamExtensionError("calendar coverage is not continuous")
        body = {"schema_version": "IncrementalCalendarExtensionV1",
                "supersedes_approval_id": previous_approval_id,
                "coverage_start": coverage_start, "coverage_end": coverage_end,
                "ordered_rows": canonical, "official_anchor_ids": anchors}
        digest = content_hash(body)
        return cls(digest, previous_approval_id, coverage_start, coverage_end,
                   canonical, anchors, digest)

    def is_open(self, day: date) -> bool:
        if not self.coverage_start <= day <= self.coverage_end:
            raise UpstreamExtensionError("calendar date unavailable")
        values = {state for _, raw, state in self.ordered_rows if raw == day.strftime("%Y%m%d")}
        if len(values) != 1:
            raise UpstreamExtensionError("exchange calendars conflict")
        return values.pop() == 1

    def next_open_session(self, day: date) -> date:
        cursor = day + timedelta(days=1)
        while cursor <= self.coverage_end:
            if self.is_open(cursor):
                return cursor
            cursor += timedelta(days=1)
        raise UpstreamExtensionError("next approved session unavailable")


@dataclass(frozen=True, slots=True)
class EffectiveDatedUniverseV1:
    universe_id: str
    supersedes_approval_id: str
    previous_universe_id: str
    baseline_symbols: tuple[str, ...]
    changes: tuple[tuple[str, date, date | None, str | None], ...]
    coverage_end: date
    evidence_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, *, previous_approval_id: str, previous_universe_id: str,
               baseline_symbols: Sequence[str], changes: Sequence[Mapping[str, Any]],
               coverage_end: date, evidence_ids: Sequence[str]):
        if not previous_approval_id or not previous_universe_id or not evidence_ids:
            raise UpstreamExtensionError("universe lineage is incomplete")
        parsed = []
        for row in changes:
            identity = row.get("security_identity")
            if not isinstance(identity, str) or not identity:
                raise UpstreamExtensionError("security identity is missing")
            listing = _day(row.get("listing_date"))
            raw_delisting = row.get("delisting_date")
            delisting = None if raw_delisting in (None, "") else _day(raw_delisting)
            if delisting is not None and delisting < listing:
                raise UpstreamExtensionError("identity interval is reversed")
            prior = row.get("prior_identity")
            if prior is not None:
                raise UpstreamExtensionError("identity transition requires explicit approved linkage")
            parsed.append((identity, listing, delisting, None))
        canonical = tuple(sorted(parsed))
        body = {"schema_version": "EffectiveDatedUniverseV1",
                "supersedes_approval_id": previous_approval_id,
                "previous_universe_id": previous_universe_id,
                "baseline_symbols": tuple(sorted(set(baseline_symbols))),
                "changes": canonical, "coverage_end": coverage_end,
                "evidence_ids": tuple(sorted(set(evidence_ids)))}
        digest = content_hash(body)
        return cls(digest, previous_approval_id, previous_universe_id,
                   body["baseline_symbols"], canonical, coverage_end,
                   body["evidence_ids"], digest)

    def approved_universe_as_of_session(self, session: date) -> frozenset[str]:
        if session > self.coverage_end:
            raise UpstreamExtensionError("universe session unavailable")
        result = set(self.baseline_symbols)
        for identity, listing, delisting, _ in self.changes:
            if listing <= session and (delisting is None or session <= delisting):
                result.add(identity)
            elif delisting is not None and session > delisting:
                result.discard(identity)
        return frozenset(result)
