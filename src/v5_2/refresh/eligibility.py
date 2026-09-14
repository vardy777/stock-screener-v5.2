from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Sequence

from v5_2.data.identity import content_hash


IPO_SEASONING_SESSIONS = 5


class EligibilityReason(str, Enum):
    IPO_SEASONING = "IPO_SEASONING"
    IDENTITY_NOT_VERIFIED = "IDENTITY_NOT_VERIFIED"
    BAR_COVERAGE_INCOMPLETE = "BAR_COVERAGE_INCOMPLETE"
    STATUS_UNRESOLVED = "STATUS_UNRESOLVED"


@dataclass(frozen=True, slots=True)
class ResearchEligibilityV1:
    symbol: str
    list_date: date
    known_security: bool
    research_eligible: bool
    exclusion_reason: str | None
    eligible_after_session: date | None
    completed_post_listing_sessions: int


@dataclass(frozen=True, slots=True)
class UniverseCoverageV1:
    coverage_id: str
    effective_security_count: int
    research_eligible_count: int
    excluded_security_count: int
    coverage_ratio: float
    exclusion_reason_counts: tuple[tuple[str, int], ...]
    excluded_symbols: tuple[str, ...]
    systematic_defect: bool
    content_hash: str

    @classmethod
    def create(cls, results: Sequence[ResearchEligibilityV1], *,
               systematic_defect: bool = False) -> "UniverseCoverageV1":
        symbols = [item.symbol for item in results]
        if len(symbols) != len(set(symbols)):
            raise ValueError("duplicate identity in universe coverage")
        effective = len(results)
        eligible = sum(item.research_eligible for item in results)
        reasons: dict[str, int] = {}
        excluded_symbols = []
        for item in results:
            if not item.research_eligible:
                if not item.exclusion_reason:
                    raise ValueError("excluded identity requires a reason")
                excluded_symbols.append(item.symbol)
                reasons[item.exclusion_reason] = reasons.get(item.exclusion_reason, 0) + 1
        body = {
            "schema_version": "UniverseCoverageV1",
            "effective_security_count": effective,
            "research_eligible_count": eligible,
            "excluded_security_count": effective - eligible,
            "coverage_ratio": 0.0 if effective == 0 else eligible / effective,
            "exclusion_reason_counts": tuple(sorted(reasons.items())),
            "excluded_symbols": tuple(sorted(excluded_symbols)),
            "systematic_defect": systematic_defect,
        }
        digest = content_hash(body)
        return cls(digest, content_hash=digest,
                   **{key: value for key, value in body.items() if key != "schema_version"})


def evaluate_ipo_eligibility(*, symbol: str, list_date: date, as_of_session: date,
                             approved_open_sessions: tuple[date, ...],
                             official_identity_verified: bool,
                             bar_coverage_valid: bool,
                             status_resolved: bool) -> ResearchEligibilityV1:
    sessions = tuple(sorted(set(day for day in approved_open_sessions if day > list_date)))
    completed = tuple(day for day in sessions if day <= as_of_session)
    eligible_after = sessions[IPO_SEASONING_SESSIONS - 1] if len(sessions) >= IPO_SEASONING_SESSIONS else None
    if len(completed) < IPO_SEASONING_SESSIONS:
        reason = EligibilityReason.IPO_SEASONING.value
    elif not official_identity_verified:
        reason = EligibilityReason.IDENTITY_NOT_VERIFIED.value
    elif not bar_coverage_valid:
        reason = EligibilityReason.BAR_COVERAGE_INCOMPLETE.value
    elif not status_resolved:
        reason = EligibilityReason.STATUS_UNRESOLVED.value
    else:
        reason = None
    return ResearchEligibilityV1(
        symbol, list_date, True, reason is None, reason, eligible_after, len(completed)
    )
