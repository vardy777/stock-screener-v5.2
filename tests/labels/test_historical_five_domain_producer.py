"""A real Phase 1 source-pinned path, never a Phase 2A slot assembler."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from v5_2.labels.historical_five_domain_producer import (
    HistoricalFiveDomainProducerV1, _CachedStatusResolver,
)
from v5_2.labels.contracts import REQUIRED_LABEL_DOMAINS, ProvenancePath
from v5_2.labels.engine import ReferenceLabelEngine


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="exact portable Phase 1 status source not installed",
)


@pytest.fixture(scope="module")
def producer():
    return HistoricalFiveDomainProducerV1.load_exact(ROOT)


def test_real_source_pinned_normal_anchor_has_five_verified_domains(producer):
    anchor, lineage, window = producer.produce_anchor("000001.SZ", date(2024, 1, 2))
    assert anchor.canonical_security_identity == "000001.SZ"
    assert lineage.master_approval_id == producer.master.approval["approval_id"]
    assert tuple(item.domain for item in window.non_status_lineage) == (
        "trade_calendar", "security_master", "daily_bar", "corporate_action")
    bundle = producer.assemble(anchor, lineage, window)
    assert tuple(item.domain for item in bundle.domain_lineage) == REQUIRED_LABEL_DOMAINS
    assert bundle.provenance_path is ProvenancePath.HISTORICAL
    assert bundle.anchor_snapshot_id is None and bundle.outcome_snapshot_id is None
    assert ReferenceLabelEngine().evaluate(bundle).verify()


def test_scoped_unknown_identity_is_excluded_without_fabricated_master_interval(producer):
    outcome = producer.produce_anchor("689009.SH", date(2025, 6, 30))
    assert outcome.reason == "MASTER_IDENTITY_QUARANTINED"
    assert outcome.security_identity == "689009.SH"


def test_approved_identity_transition_keeps_original_ipo_seasoning_date(producer):
    outcome = producer.produce_anchor("302132.SZ", date(2025, 2, 17))
    assert isinstance(outcome, tuple)
    anchor, _, window = outcome
    assert anchor.disposition == "ELIGIBLE"
    assert anchor.canonical_security_identity == "302132.SZ"
    assert window.non_status_lineage[1].evidence_ids


def test_cross_transition_horizon_is_scoped_not_misread_as_same_identity(producer):
    outcome = producer.produce_anchor("302132.SZ", date(2025, 2, 14))
    assert outcome.security_identity == "302132.SZ"
    assert outcome.reason == "IDENTITY_TRANSITION_WINDOW_UNRESOLVED"
    alias = producer.produce_anchor("300114.SZ", date(2025, 2, 14))
    assert alias.reason == "IDENTITY_TRANSITION_WINDOW_UNRESOLVED"


def test_assembler_completed_session_is_h5_even_when_h5_bar_is_absent():
    seen = {}
    producer = object.__new__(HistoricalFiveDomainProducerV1)
    producer.assembler = SimpleNamespace(assemble=lambda *args, **kwargs: seen.update(kwargs))
    anchor = SimpleNamespace(anchor_session=date(2024, 1, 2))
    lineage = SimpleNamespace(open_sessions=tuple(date(2024, 1, day) for day in range(2, 8)))
    producer.assemble(anchor, lineage, SimpleNamespace(future_bars=()))
    assert seen["latest_completed_session"] == date(2024, 1, 7)


def test_month_bar_window_is_loaded_once_for_all_same_month_anchors():
    calls = []
    producer = object.__new__(HistoricalFiveDomainProducerV1)
    producer.calendar = SimpleNamespace(sessions=lambda exchange: (
        date(2024, 1, 2), date(2024, 1, 3),
        *(date(2024, 2, day) for day in range(1, 7))))
    producer.bars = SimpleNamespace(read_window=lambda month, h5: (
        calls.append((month, h5)) or SimpleNamespace(facts=())))
    producer._bar_cache = {}
    producer._bar_month("SZSE", "2024-01")
    producer._bar_month("SZSE", "2024-01")
    assert calls == [("2024-01", date(2024, 2, 5))]
    producer._bar_month("SSE", "2024-01")
    producer._bar_month("SZSE", "2024-01")
    assert len(calls) == 2


def test_first_delisted_future_session_is_preserved_for_engine():
    sessions = tuple(date(2024, 1, day) for day in range(2, 8))
    statuses = tuple(SimpleNamespace(delisted=index >= 3) for index in range(6))
    assert HistoricalFiveDomainProducerV1._delisting_session(sessions, statuses) == date(2024, 1, 5)


def test_candidate_census_keeps_parent_membership_and_scoped_quarantine(producer):
    early, early_scoped = producer.candidate_identities(date(2012, 6, 29))
    recent, recent_scoped = producer.candidate_identities(date(2025, 6, 30))
    assert len(early) == 2421 and early_scoped == ()
    assert ("300114.SZ", "302132.SZ") in early
    assert len(recent) == 5151
    assert recent_scoped == ("689009.SH",)
    assert ("302132.SZ", "302132.SZ") in recent


def test_overlapping_anchor_windows_reuse_same_exact_status_derivation():
    calls = []
    producer = object.__new__(HistoricalFiveDomainProducerV1)
    producer.status_resolver = _CachedStatusResolver(SimpleNamespace(
        resolve=lambda identity, day, cutoff: (
            calls.append((identity, day, cutoff)) or object())))
    first = producer._resolve_status_cached("000001.SZ", date(2010, 1, 11))
    second = producer._resolve_status_cached("000001.SZ", date(2010, 1, 11))
    third = producer._resolve_status_cached("000001.SZ", date(2010, 1, 12))
    assert first is second and third is not first
    assert len(calls) == 2
    assert calls[0][2].hour == 16 and calls[0][2].minute == 30


def test_producer_and_assembler_share_exact_status_derivation_cache(monkeypatch):
    calls = []
    class Assembler:
        def __init__(self, resolver, pins):
            self.status_resolver = resolver
    monkeypatch.setattr(
        "v5_2.labels.historical_five_domain_producer.HistoricalLabelEvidenceAssemblerV1",
        Assembler)
    raw = SimpleNamespace(resolve=lambda identity, day, cutoff: (
        calls.append((identity, day, cutoff)) or object()))
    producer = HistoricalFiveDomainProducerV1(None, None, None, raw, None, None)
    day = date(2010, 1, 11)
    first = producer._resolve_status_cached("000001.SZ", day)
    second = producer.assembler.status_resolver.resolve(
        "000001.SZ", day, calls[0][2])
    assert first is second
    assert len(calls) == 1
