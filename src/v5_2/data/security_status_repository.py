from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from v5_2.data.security_status_facts import (
    DailySecurityStatusFactV1,
    SecurityStatusIntervalFactV1,
    StatusKind,
)


class StatusResolutionError(RuntimeError):
    def __init__(self, reason: str, security_identity: str, status_kind: StatusKind | None = None):
        self.reason = reason
        self.security_identity = security_identity
        self.status_kind = status_kind
        super().__init__(f"{reason} status for {security_identity}")


@dataclass(frozen=True, slots=True)
class StatusUniverseDiagnosticV1:
    included_symbols: tuple[str, ...]
    skipped_symbols: tuple[str, ...]
    skipped_reasons: tuple[tuple[str, str], ...]
    coverage_ratio: float
    missing_count: int
    ambiguous_count: int
    conflict_count: int
    research_eligible: bool = False


class SecurityStatusRepository:
    def __init__(self, facts, *, identities, risk_warning_excluded: bool = True):
        self._identities = tuple(sorted(set(identities)))
        self._risk_warning_excluded = risk_warning_excluded
        self._facts = tuple(facts)

    def _resolve_dimension(self, identity: str, kind: StatusKind, session: date, as_of: datetime):
        candidates = tuple(
            fact for fact in self._facts
            if fact.security_identity == identity
            and fact.status_kind is kind
            and fact.effective_from <= session
            and (fact.effective_to is None or session <= fact.effective_to)
        )
        if not candidates:
            raise StatusResolutionError("missing", identity, kind)
        visible = tuple(fact for fact in candidates if fact.available_at <= as_of)
        if not visible:
            raise StatusResolutionError("not_available", identity, kind)
        values = {fact.status_value for fact in visible}
        if len(values) > 1:
            raise StatusResolutionError("conflicting", identity, kind)
        if len(visible) > 1:
            raise StatusResolutionError("ambiguous", identity, kind)
        return visible[0]

    def project(self, security_identity: str, session: date, as_of: datetime) -> DailySecurityStatusFactV1:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise StatusResolutionError("naive_as_of", security_identity)
        resolved = {
            kind: self._resolve_dimension(security_identity, kind, session, as_of)
            for kind in StatusKind
        }
        listing = resolved[StatusKind.LISTING].status_value
        risk = resolved[StatusKind.RISK_WARNING].status_value
        suspension = resolved[StatusKind.SUSPENSION].status_value
        identity = resolved[StatusKind.IDENTITY].status_value
        if identity != security_identity:
            raise StatusResolutionError("conflicting", security_identity, StatusKind.IDENTITY)
        starts = tuple(fact.effective_from for fact in resolved.values())
        ends = tuple(fact.effective_to for fact in resolved.values() if fact.effective_to is not None)
        return DailySecurityStatusFactV1.create(
            security_identity=identity, session=session,
            is_listed=listing == "LISTED", is_delisted=listing == "DELISTED",
            is_risk_warning=risk == "ST", is_suspended=suspension == "SUSPENDED",
            risk_warning_excluded=self._risk_warning_excluded,
            effective_from=max(starts), effective_to=min(ends) if ends else None,
            available_at=max(fact.available_at for fact in resolved.values()),
            source_fact_ids=tuple(fact.fact_id for fact in resolved.values()),
            source_name="v5.2-status-projection", policy_version="daily-status-v1",
        )

    def tradable_universe(self, session: date, as_of: datetime) -> tuple[str, ...]:
        projected = tuple(self.project(identity, session, as_of) for identity in self._identities)
        return tuple(fact.security_identity for fact in projected if fact.is_tradable)

    def diagnose_tradable_universe(self, session: date, as_of: datetime) -> StatusUniverseDiagnosticV1:
        included, skipped, reasons = [], [], []
        counts = {"missing": 0, "ambiguous": 0, "conflicting": 0}
        for identity in self._identities:
            try:
                fact = self.project(identity, session, as_of)
                if fact.is_tradable:
                    included.append(identity)
            except StatusResolutionError as error:
                skipped.append(identity)
                reasons.append((identity, error.reason))
                if error.reason in counts:
                    counts[error.reason] += 1
        total = len(self._identities)
        return StatusUniverseDiagnosticV1(
            included_symbols=tuple(included), skipped_symbols=tuple(skipped),
            skipped_reasons=tuple(reasons), coverage_ratio=(total - len(skipped)) / total if total else 0.0,
            missing_count=counts["missing"], ambiguous_count=counts["ambiguous"],
            conflict_count=counts["conflicting"], research_eligible=False,
        )
