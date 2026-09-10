from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Mapping

from v5_2.data.identity import content_hash


class DailyBarAvailabilityError(RuntimeError):
    """Daily-bar availability cannot be established without look-ahead."""


class DailyBarAvailabilityBasis(str, Enum):
    MARKET_CLOSE = "MARKET_CLOSE"
    PROVIDER_OBSERVED = "PROVIDER_OBSERVED"
    CONSERVATIVE_AFTER_CLOSE = "CONSERVATIVE_AFTER_CLOSE"
    NEXT_SESSION_SAFE = "NEXT_SESSION_SAFE"


REQUIRED_FIELDS = frozenset(
    {"ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"}
)
SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")


@dataclass(frozen=True, slots=True)
class DailyBarProbeObservationV1:
    session: date
    requested_at: datetime
    expected_symbols: tuple[str, ...]
    observed_symbols: tuple[str, ...]
    rows: tuple[Mapping[str, object], ...]
    payload_hash: str
    receipt_id: str
    source_version_identity: str
    complete: bool
    content_hash: str

    @classmethod
    def create(
        cls,
        *,
        session: date,
        requested_at: datetime,
        expected_symbols: tuple[str, ...],
        rows: tuple[Mapping[str, object], ...],
        payload_hash: str,
        receipt_id: str,
        source_version_identity: str,
    ) -> DailyBarProbeObservationV1:
        if requested_at.tzinfo is None or requested_at.utcoffset() is None:
            raise DailyBarAvailabilityError("requested_at must be timezone-aware")
        expected = tuple(sorted(set(expected_symbols)))
        canonical_rows = tuple(dict(row) for row in rows)
        observed = tuple(sorted({str(row.get("ts_code", "")) for row in rows if row.get("ts_code")}))
        session_text = session.strftime("%Y%m%d")
        complete = (
            bool(expected)
            and observed == expected
            and len(rows) == len(expected)
            and all(REQUIRED_FIELDS <= set(row) for row in rows)
            and all(str(row["trade_date"]) == session_text for row in rows)
            and all(row[field] not in (None, "") for row in rows for field in REQUIRED_FIELDS)
        )
        body = {
            "schema_version": "DailyBarProbeObservationV1",
            "session": session,
            "requested_at": requested_at,
            "expected_symbols": expected,
            "observed_symbols": observed,
            "rows": canonical_rows,
            "payload_hash": payload_hash,
            "receipt_id": receipt_id,
            "source_version_identity": source_version_identity,
            "complete": complete,
        }
        return cls(**{key: value for key, value in body.items() if key != "schema_version"}, content_hash=content_hash(body))

    def verify(self) -> bool:
        body = {
            "schema_version": "DailyBarProbeObservationV1",
            "session": self.session,
            "requested_at": self.requested_at,
            "expected_symbols": self.expected_symbols,
            "observed_symbols": self.observed_symbols,
            "rows": self.rows,
            "payload_hash": self.payload_hash,
            "receipt_id": self.receipt_id,
            "source_version_identity": self.source_version_identity,
            "complete": self.complete,
        }
        return self.content_hash == content_hash(body)


@dataclass(frozen=True, slots=True)
class DailyBarAvailabilityEvidenceV1:
    policy_version: str
    source_name: str
    source_version_identity: str
    coverage_sessions: tuple[date, ...]
    probe_times: tuple[datetime, ...]
    sample_scope: tuple[str, ...]
    observations: tuple[DailyBarProbeObservationV1, ...]
    revision_findings: tuple[str, ...]
    full_market_readiness_rule: str
    historical_available_at_rule: str
    supporting_receipt_ids: tuple[str, ...]
    complete: bool
    content_hash: str

    @classmethod
    def create(cls, **values) -> DailyBarAvailabilityEvidenceV1:
        observations = tuple(values["observations"])
        payloads_by_request: dict[tuple[date, tuple[str, ...]], set[str]] = {}
        for item in observations:
            payloads_by_request.setdefault(
                (item.session, item.expected_symbols), set()
            ).add(item.payload_hash)
        stable = all(len(payloads) == 1 for payloads in payloads_by_request.values())
        observed_scope = {symbol for item in observations for symbol in item.observed_symbols}
        complete = (
            bool(observations)
            and all(item.verify() and item.complete for item in observations)
            and all(item.source_version_identity == values["source_version_identity"] for item in observations)
            and stable
            and observed_scope == set(values["sample_scope"])
            and values["historical_available_at_rule"].startswith("NEXT_SESSION_SAFE")
            and {item.receipt_id for item in observations} <= set(values["supporting_receipt_ids"])
        )
        body = {
            "schema_version": "DailyBarAvailabilityEvidenceV1",
            **values,
            "coverage_sessions": tuple(sorted(set(values["coverage_sessions"]))),
            "probe_times": tuple(sorted(set(values["probe_times"]))),
            "sample_scope": tuple(sorted(set(values["sample_scope"]))),
            "observations": observations,
            "revision_findings": tuple(values["revision_findings"]),
            "supporting_receipt_ids": tuple(sorted(set(values["supporting_receipt_ids"]))),
            "complete": complete,
        }
        return cls(**{key: value for key, value in body.items() if key != "schema_version"}, content_hash=content_hash(body))

    def verify(self) -> bool:
        body = {
            "schema_version": "DailyBarAvailabilityEvidenceV1",
            **{name: getattr(self, name) for name in (
                "policy_version", "source_name", "source_version_identity", "coverage_sessions",
                "probe_times", "sample_scope", "observations", "revision_findings",
                "full_market_readiness_rule", "historical_available_at_rule",
                "supporting_receipt_ids", "complete",
            )},
        }
        return self.content_hash == content_hash(body) and all(item.verify() for item in self.observations)


@dataclass(frozen=True, slots=True)
class DailyBarAvailabilityPolicyV1:
    basis: DailyBarAvailabilityBasis
    cutoff: time
    policy_version: str

    def available_at(
        self,
        session: date,
        *,
        next_session: date,
        evidence: DailyBarAvailabilityEvidenceV1 | None,
        source_version_identity: str,
    ) -> datetime:
        if self.basis is DailyBarAvailabilityBasis.MARKET_CLOSE:
            raise DailyBarAvailabilityError("market close does not prove provider availability")
        if evidence is None or not evidence.verify() or not evidence.complete:
            raise DailyBarAvailabilityError("availability evidence integrity or completeness failed")
        if evidence.source_version_identity != source_version_identity:
            raise DailyBarAvailabilityError("availability evidence source version mismatch")
        if self.policy_version != evidence.policy_version:
            raise DailyBarAvailabilityError("availability policy version mismatch")
        if self.basis is DailyBarAvailabilityBasis.CONSERVATIVE_AFTER_CLOSE:
            same_day_cutoff = datetime.combine(session, self.cutoff, SHANGHAI)
            if not any(item.complete and item.requested_at <= same_day_cutoff for item in evidence.observations):
                raise DailyBarAvailabilityError("evidence does not prove same-day cutoff")
            return same_day_cutoff
        if self.basis is DailyBarAvailabilityBasis.PROVIDER_OBSERVED:
            observed = tuple(item.requested_at.astimezone(SHANGHAI) for item in evidence.observations if item.complete)
            if not observed:
                raise DailyBarAvailabilityError("provider observation is unavailable")
            return max(min(observed), datetime.combine(session, time(15, 0), SHANGHAI))
        if self.basis is DailyBarAvailabilityBasis.NEXT_SESSION_SAFE:
            if next_session <= session:
                raise DailyBarAvailabilityError("next safe session must follow bar session")
            return datetime.combine(next_session, self.cutoff, SHANGHAI)
        raise DailyBarAvailabilityError("availability basis is unsupported")
