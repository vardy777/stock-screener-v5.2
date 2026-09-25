"""Offline source-pinned five-domain evidence for Phase 2B production labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from v5_2.data.historical_security_master_authority import (
    HistoricalMasterTypingError, HistoricalSecurityMasterReaderV1,
    load_verified_master_source,
)
from v5_2.data.historical_status_authority import (
    HistoricalStatusAuthorityError, load_portable_status_resolver,
)
from v5_2.labels.anchor_enumerator import (
    AnchorDispositionKind, AnchorDispositionV1, HistoricalAnchorLineageV1,
    IdentityIntervalV1, StatusObservationV1,
)
from v5_2.labels.contracts import AnchorKnowledgeBoundary
from v5_2.labels.historical_ca_lineage import HistoricalCorporateActionLineageV1
from v5_2.labels.historical_calendar_lineage import HistoricalCalendarLineageV1
from v5_2.labels.historical_daily_bar_lineage import HistoricalDailyBarLineageV1
from v5_2.labels.materializer import (
    HistoricalEvidenceWindowV1, HistoricalLabelEvidenceAssemblerV1,
    HistoricalStatusLineagePinsV1,
)
from v5_2.refresh.eligibility import evaluate_ipo_eligibility


_ZONE = timezone(timedelta(hours=8), "Asia/Shanghai")
_MASTER = {
    "authority_id": "33f28a549e94be8317dce5216414eb7b4c3c403fda4e2a160fc7d26e431831c5",
    "approval_id": "c515bd582600fed01a64c062901ede713dafadb931e5fa7de15f053d52c4bfc1",
    "manifest_id": "d570228256b4e693e8ccce7ed5c18196065bcec9ef3dae749048052f3a28304c",
    "coverage_ledger_id": "ae78946d78fcf107de18d78abe7a8f92df4c042a7cdc7223143b39a20b157945",
}
_BAR = {
    "authority_id": "12ea218b47389979561423a2289791bfe504040b4bbe6d667af26967dad55933",
    "approval_id": "834d20964081575ec758abc3f28584b35ff414ac347a04e028d86ecf9752a656",
    "manifest_id": "232a5ebaece1a8c3552ccb4c9bdebd40048afae19c6086f246aa377c9235e546",
    "coverage_ledger_id": "632484c08fb7e9e24f59bbb33129dcabaf192b80529c35eaffceed731893508d",
    "composition_id": "c2ebb472773fe595cb87703ec03bf6206bacddb3cd34eb68576176ae3d518482",
    "replay_id": "0abffb860b3f4de201c5fd24431c4905b9e7ce5e1707fa59bc5b5fd902b0772c",
}
_STATUS = {
    "expected_authority_id": "d6f7f5517428891db66da60565baaea5828d7adcaf29c820d5fa746ddf29e59b",
    "expected_derived_approval_id": "9353de33e62405830a7dbef13e53836a969fb569f9e7d5370a67d5df9078fa95",
    "expected_derived_manifest_id": "0c86954cffaae2ca09ff1efcd4b32d990a9cf3d2b82d520a64172a1875d457a8",
    "expected_composition_id": "e4110ec6185731d9a2d80e151d79f82006e07e779c10a90a4b4c2e228a35e139",
    "expected_replay_evidence_id": "235f86dd7269768382c67620cd723d27347c7f99e386488efc9b93665a517baf",
}
_STATUS_COVERAGE_LEDGER = "b214cc728c867c7b5bdbef5e6b37cea25afa67650522d5aee800cd95f56237cb"


@dataclass(frozen=True, slots=True)
class ScopedAnchorExclusionV1:
    security_identity: str
    anchor_session: date
    domain: str
    reason: str
    evidence_ids: tuple[str, ...]


class _CachedStatusResolver:
    """Memoize only exact immutable resolution inputs within one offline run."""

    def __init__(self, resolver):
        self._resolver = resolver
        self._cache = {}

    def __getattr__(self, name):
        return getattr(self._resolver, name)

    def resolve(self, identity, session, cutoff):
        key = (identity, session, cutoff)
        if key not in self._cache:
            self._cache[key] = self._resolver.resolve(identity, session, cutoff)
        return self._cache[key]


class HistoricalFiveDomainProducerV1:
    version = "historical-five-domain-producer-v1"

    def __init__(self, calendar: HistoricalCalendarLineageV1,
                 master: HistoricalSecurityMasterReaderV1,
                 bars: HistoricalDailyBarLineageV1,
                 status_resolver, status_pins: HistoricalStatusLineagePinsV1,
                 actions: HistoricalCorporateActionLineageV1) -> None:
        self.calendar = calendar
        self.master = master
        self.bars = bars
        self.status_resolver = _CachedStatusResolver(status_resolver)
        self.status_pins = status_pins
        self.actions = actions
        self.assembler = HistoricalLabelEvidenceAssemblerV1(self.status_resolver, status_pins)
        self._bar_cache = {}

    @classmethod
    def load_exact(cls, root: Path) -> "HistoricalFiveDomainProducerV1":
        master_base = root / "data/phase_1b_historical_master_portable"
        master_source = load_verified_master_source(master_base / "source")
        revoked = master_source.revoked_approval_ids
        calendar = HistoricalCalendarLineageV1.load_exact(root, revoked_approval_ids=revoked)
        master = HistoricalSecurityMasterReaderV1.load_formal_exact(
            master_base / "source", master_base / "published", **_MASTER)
        bars = HistoricalDailyBarLineageV1.load_exact(
            root / "data/phase_1b_historical_daily_bar_fact_authority",
            **_BAR, revoked_approval_ids=revoked)
        sessions = tuple(sorted(set(calendar.sse_sessions) | set(calendar.szse_sessions)))
        status = load_portable_status_resolver(
            portable_root=root / "data/replay_status_authority",
            **_STATUS, approved_sessions=sessions,
            revoked_approval_ids=revoked)
        status_pins = HistoricalStatusLineagePinsV1.create(
            authority_id=status.authority.authority_id,
            approval_id=status.derived_approval_id,
            manifest_id=status.derived_manifest_id,
            composition_id=_STATUS["expected_composition_id"],
            coverage_ledger_id=_STATUS_COVERAGE_LEDGER,
            replay_evidence_id=_STATUS["expected_replay_evidence_id"],
            parent_panel_id=status.authority.parent_panel_id,
            parent_manifest_id=status.authority.parent_manifest_id,
            parent_approval_id=status.authority.parent_approval_id,
        )
        actions = HistoricalCorporateActionLineageV1.load_exact(
            root / "data/phase_1b2c", revoked_approval_ids=revoked)
        return cls(calendar, master, bars, status, status_pins, actions)

    def _excluded(self, identity: str, session: date, domain: str,
                  reason: str, evidence: tuple[str, ...]) -> ScopedAnchorExclusionV1:
        return ScopedAnchorExclusionV1(identity, session, domain, reason, evidence)

    def candidate_identities(self, session: date) -> tuple[
            tuple[tuple[str, str], ...], tuple[str, ...]]:
        """Effective approved members plus explicit unresolved parent members."""
        effective = []
        for fact in self.master.facts:
            exchange = "SSE" if fact.provider_identity.endswith(".SH") else "SZSE"
            if session not in self.calendar.sessions(exchange):
                continue
            for interval in fact.intervals:
                if interval.effective_from <= session and (
                        interval.effective_to is None or session <= interval.effective_to):
                    effective.append((interval.identity, fact.provider_identity))
        scoped = []
        for item in self.master.quarantines:
            start = date.fromisoformat(item.affected_from) if item.affected_from else None
            end = date.fromisoformat(item.affected_to) if item.affected_to else None
            if start is not None and start <= session and (end is None or session <= end):
                scoped.append(item.security_identity)
        result = tuple(sorted(effective))
        if len(result) != len({provider for _, provider in result}):
            raise ValueError("Master identity chain overlaps at session")
        return result, tuple(sorted(scoped))

    def _bar_month(self, exchange: str, month: str):
        key = (exchange, month)
        if key not in self._bar_cache:
            sessions = self.calendar.sessions(exchange)
            anchors = tuple(day for day in sessions if day.strftime("%Y-%m") == month)
            if not anchors:
                raise ValueError("month is absent from approved calendar")
            later = tuple(day for day in sessions if day > anchors[-1])[:5]
            if len(later) != 5:
                raise ValueError("month has no approved H5 calendar coverage")
            window = self.bars.read_window(month, later[-1])
            index = {(fact.security_identity, fact.session): fact for fact in window.facts}
            if len(index) != len(window.facts):
                raise ValueError("Daily Bar month contains duplicate security sessions")
            if any(cached_month != month for _, cached_month in self._bar_cache):
                self._bar_cache.clear()  # at most the two exchanges of one month plus H5
            self._bar_cache[key] = (window, index)
        return self._bar_cache[key]

    @staticmethod
    def _delisting_session(sessions, statuses) -> date | None:
        return next((day for day, item in zip(sessions[1:], statuses[1:])
                     if item.delisted), None)

    def _resolve_status_cached(self, canonical: str, day: date):
        return self.status_resolver.resolve(
            canonical, day, datetime.combine(day, time(16, 30), _ZONE))

    def produce_anchor(self, identity: str, session: date):
        """Return an exact window or a security/session-scoped exclusion."""
        try:
            master_fact = self.master.resolve(identity, session)
        except HistoricalMasterTypingError as error:
            reason = ("MASTER_IDENTITY_QUARANTINED" if identity in self.master._quarantined
                      else "MASTER_IDENTITY_UNRESOLVED")
            return self._excluded(identity, session, "security_master", reason,
                                  (self.master.authority["authority_id"],
                                   self.master.ledger["ledger_id"]))
        canonical = master_fact.effective_identity
        exchange = "SSE" if identity.endswith(".SH") else "SZSE" if identity.endswith(".SZ") else ""
        if not exchange:
            return self._excluded(identity, session, "security_master", "UNKNOWN_EXCHANGE",
                                  (master_fact.fact_id,))
        open_sessions = self.calendar.sessions(exchange)
        window_sessions = self.calendar.window(exchange, session)
        master_intervals = self.master._facts_by_provider[master_fact.provider_identity].intervals
        identities_in_window = {interval.identity for day in window_sessions
            for interval in master_intervals
            if interval.effective_from <= day and
                (interval.effective_to is None or day <= interval.effective_to)}
        if len(identities_in_window) > 1:
            if not master_fact.graph_id or not master_fact.graph_approval_id:
                raise ValueError("Master identity transition has no approved graph lineage")
            return self._excluded(identity, session, "security_master",
                "IDENTITY_TRANSITION_WINDOW_UNRESOLVED",
                (master_fact.fact_id, master_fact.graph_id,
                 master_fact.graph_approval_id))
        cutoff = datetime.combine(session, time(16, 30), _ZONE)
        try:
            resolved_status = tuple(self._resolve_status_cached(canonical, day)
                                    for day in window_sessions)
        except HistoricalStatusAuthorityError as error:
            if "canonical identity is unavailable" not in str(error):
                raise
            return self._excluded(identity, session, "daily_security_status",
                                  "STATUS_IDENTITY_UNRESOLVED",
                                  (self.status_pins.authority_id, master_fact.fact_id))
        first_interval = master_intervals[0]
        eligibility = evaluate_ipo_eligibility(
            symbol=canonical, list_date=first_interval.effective_from,
            as_of_session=session, approved_open_sessions=open_sessions,
            official_identity_verified=True, bar_coverage_valid=True,
            status_resolved=True,
        )
        disposition = (AnchorDispositionKind.ELIGIBLE if eligibility.research_eligible
                       else AnchorDispositionKind.EXCLUDED_BEFORE_LABEL)
        anchor = AnchorDispositionV1(identity, canonical, session, exchange, True,
                                     resolved_status[0].full_day_suspended,
                                     disposition, eligibility.exclusion_reason)
        lineage = HistoricalAnchorLineageV1.create(
            calendar_approval_id=self.calendar.approval_id,
            calendar_manifest_id=self.calendar.manifest_id,
            master_approval_id=self.master.approval["approval_id"],
            master_manifest_id=self.master.manifest["manifest_id"],
            status_approval_id=self.status_pins.approval_id,
            status_manifest_id=self.status_pins.manifest_id,
            open_sessions=open_sessions,
            identity_intervals=(IdentityIntervalV1(identity, canonical, exchange,
                master_fact.interval.effective_from, master_fact.interval.effective_to),),
            status_observations=tuple(StatusObservationV1(identity, day,
                item.full_day_suspended) for day, item in zip(window_sessions, resolved_status)),
        )
        if disposition is not AnchorDispositionKind.ELIGIBLE:
            return anchor
        month_bars, bar_index = self._bar_month(exchange, session.strftime("%Y-%m"))
        by_session = {day: bar_index[(identity, day)] for day in window_sessions
                      if (identity, day) in bar_index}
        for day, status in zip(window_sessions, resolved_status):
            if day not in by_session and not status.full_day_suspended and status.listed:
                return self._excluded(identity, session, "daily_bar", "UNEXPLAINED_MISSING_BAR",
                    (master_fact.fact_id, status.derivation_id, self.bars.reader.authority.authority_id))
        actions, coverage, ca_lineage = self.actions.window(canonical, window_sessions[1:])
        master_lineage = self._master_lineage(master_fact)
        from v5_2.labels.contracts import DomainLineageV1
        bar_lineage = DomainLineageV1.create(
            domain="daily_bar", approval_id=month_bars.approval_id,
            manifest_id=month_bars.manifest_id,
            fact_ids=tuple(by_session[day].fact_id for day in window_sessions if day in by_session),
            evidence_ids=month_bars.evidence_ids,
        )
        window = HistoricalEvidenceWindowV1.create(
            anchor_boundary=AnchorKnowledgeBoundary.create(
                session, cutoff, master_fact.fact_id, True),
            anchor_bar=by_session.get(session),
            future_bars=tuple(by_session[day] for day in window_sessions[1:] if day in by_session),
            non_status_lineage=(self.calendar.lineage(), master_lineage,
                bar_lineage, ca_lineage),
            corporate_actions=actions, action_coverage=coverage,
            dated_identity_map=(),
            delisting_session=self._delisting_session(window_sessions, resolved_status),
        )
        return anchor, lineage, window

    def _master_lineage(self, resolution):
        from v5_2.labels.contracts import DomainLineageV1
        return DomainLineageV1.create(
            domain="security_master", approval_id=self.master.approval["approval_id"],
            manifest_id=self.master.manifest["manifest_id"], fact_ids=(resolution.fact_id,),
            evidence_ids=(resolution.authority_id, resolution.coverage_ledger_id,
                          resolution.typing_bridge_id, self.master.authority["replay_evidence_id"],
                          self.master.authority["source_corpus_inventory_id"],
                          *resolution.source_payload_hashes,
                          *((resolution.graph_id,) if resolution.graph_id else ()),
                          *((resolution.graph_approval_id,) if resolution.graph_approval_id else ())),
        )

    def assemble(self, anchor: AnchorDispositionV1,
                 lineage: HistoricalAnchorLineageV1, window: HistoricalEvidenceWindowV1):
        future = tuple(day for day in lineage.open_sessions if day > anchor.anchor_session)[:5]
        if len(future) != 5:
            raise ValueError("approved H5 session is unavailable")
        return self.assembler.assemble(anchor, lineage, window,
            latest_completed_session=future[-1])
