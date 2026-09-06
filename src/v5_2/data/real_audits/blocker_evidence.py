from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import content_hash


class ResolutionStatus(str, Enum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    UNRESOLVED = "UNRESOLVED"


class SecurityDisposition(str, Enum):
    NORMALIZED_ELIGIBLE = "NORMALIZED_ELIGIBLE"
    EXCLUDED_NON_TARGET = "EXCLUDED_NON_TARGET"
    REJECTED_UNRESOLVED = "REJECTED_UNRESOLVED"


@dataclass(frozen=True, slots=True)
class TradeCalendarSampleV1:
    sample_id: str
    exchange: str
    year: int
    sample_stratum: str
    calendar_date: str
    provider_is_open: int
    official_is_open: int | None
    official_source_identity: str | None
    resolution_status: ResolutionStatus


def _dates(start: date, end: date):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def _candidates(year: int, stratum: str) -> tuple[date, ...]:
    if stratum == "spring_festival_boundary":
        values = _dates(date(year, 1, 15), date(year, 3, 15))
    elif stratum == "national_day_boundary":
        values = _dates(date(year, 9, 25), date(year, 10, 15))
    elif stratum == "weekend_makeup_boundary":
        combined = (*_dates(date(year, 1, 15), date(year, 3, 15)), *_dates(date(year, 9, 25), date(year, 10, 15)))
        values = (item for item in combined if item.weekday() >= 5)
    else:
        values = (*_dates(date(year, 1, 1), date(year, 1, 7)), *_dates(date(year, 12, 25), date(year, 12, 31)))
    return tuple(values)


@dataclass(frozen=True, slots=True)
class TradeCalendarUnresolvedSampleInventoryV1:
    inventory_id: str
    samples: tuple[TradeCalendarSampleV1, ...]
    total_samples: int
    verified_samples: int
    unresolved_samples: int
    mismatch_samples: int
    by_year: Mapping[str, Mapping[str, int]]
    by_exchange: Mapping[str, Mapping[str, int]]
    by_stratum: Mapping[str, Mapping[str, int]]
    verified_at: datetime
    policy_id: str
    policy_version: str
    content_hash: str

    @classmethod
    def create(
        cls, *, provider_observations: Mapping[tuple[str, str], int],
        official_observations: Mapping[tuple[str, str], int], verified_at: datetime,
        policy_id: str, policy_version: str,
        official_source_identities: Mapping[str, str] | None = None,
    ) -> TradeCalendarUnresolvedSampleInventoryV1:
        if verified_at.tzinfo is None or verified_at.utcoffset() is None:
            raise ValueError("verified_at must be timezone-aware")
        strata = ("spring_festival_boundary", "national_day_boundary", "weekend_makeup_boundary", "cross_year_boundary")
        samples = []
        for year in range(2010, 2026):
            for exchange in ("SSE", "SZSE"):
                for stratum in strata:
                    ranked = sorted(
                        _candidates(year, stratum),
                        key=lambda day: content_hash({"seed": "v5.2-phase-1b1-trade-calendar-v1", "exchange": exchange, "year": year, "stratum": stratum, "date": day}),
                    )[:2]
                    for day in ranked:
                        iso = day.isoformat()
                        provider = provider_observations.get((exchange, iso))
                        if provider not in (0, 1):
                            raise ValueError("provider observation missing for frozen sample")
                        official = official_observations.get((exchange, iso))
                        status = ResolutionStatus.UNRESOLVED if official not in (0, 1) else (ResolutionStatus.VERIFIED if official == provider else ResolutionStatus.MISMATCH)
                        sample_id = content_hash({"exchange": exchange, "year": year, "stratum": stratum, "calendar_date": iso, "policy_id": policy_id})
                        source_identity = None
                        if official in (0, 1):
                            source_identity = (official_source_identities or {}).get(
                                exchange, "official-observation-bundle"
                            )
                        samples.append(TradeCalendarSampleV1(sample_id, exchange, year, stratum, iso, provider, official, source_identity, status))
        counts = Counter(item.resolution_status for item in samples)
        def grouped(attribute: str):
            result = {}
            for value in sorted({str(getattr(item, attribute)) for item in samples}):
                selected = [item for item in samples if str(getattr(item, attribute)) == value]
                result[value] = MappingProxyType(dict(Counter(item.resolution_status.value for item in selected)))
            return MappingProxyType(result)
        body = {
            "schema_version": "TradeCalendarUnresolvedSampleInventoryV1", "samples": tuple(samples),
            "total_samples": len(samples), "verified_samples": counts[ResolutionStatus.VERIFIED],
            "unresolved_samples": counts[ResolutionStatus.UNRESOLVED], "mismatch_samples": counts[ResolutionStatus.MISMATCH],
            "by_year": grouped("year"), "by_exchange": grouped("exchange"), "by_stratum": grouped("sample_stratum"),
            "verified_at": verified_at, "policy_id": policy_id, "policy_version": policy_version,
        }
        digest = content_hash(body)
        return cls(inventory_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})


@dataclass(frozen=True, slots=True)
class SecurityMasterNormalizationExceptionEvidenceV1:
    evidence_id: str
    records: tuple[Mapping[str, Any], ...]
    excluded_non_target: int
    unresolved: int
    verified_at: datetime
    policy_version: str
    input_artifact_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, *, records: Sequence[Mapping[str, Any]], verified_at: datetime, policy_version: str, input_artifact_ids: Sequence[str]):
        frozen = tuple(MappingProxyType(dict(sorted(record.items()))) for record in sorted(records, key=lambda item: str(item.get("ts_code"))))
        excluded = sum(item.get("classification") == SecurityDisposition.EXCLUDED_NON_TARGET for item in frozen)
        unresolved = sum(item.get("classification") == SecurityDisposition.REJECTED_UNRESOLVED for item in frozen)
        body = {"schema_version": "SecurityMasterNormalizationExceptionEvidenceV1", "records": frozen, "excluded_non_target": excluded, "unresolved": unresolved, "verified_at": verified_at, "policy_version": policy_version, "input_artifact_ids": tuple(sorted(set(input_artifact_ids)))}
        digest = content_hash(body)
        return cls(evidence_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})
