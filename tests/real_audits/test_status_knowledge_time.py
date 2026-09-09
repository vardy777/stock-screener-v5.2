from datetime import date, datetime, timedelta, timezone

import pytest

from v5_2.data.real_audits.status_knowledge_time import (
    REQUIRED_STATUS_SEMANTICS,
    StatusKnowledgeTimeObservationV1,
    StatusPITKnowledgeTimeEvidenceV1,
)

SESSIONS = (date(2022, 6, 2), date(2022, 6, 6), date(2022, 6, 7))


def test_market_observable_status_is_usable_only_at_after_close_cutoff() -> None:
    item = StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
        security_identity="002699.SZ", status_semantic="RISK_WARNING_ENTER",
        effective_session=date(2022, 6, 6), provider_observation="ST",
        independent_observation="ST effective at open", independent_source_id="SZSE",
        source_reference="official.pdf", source_document_hash="doc", publication_date=date(2022, 6, 2),
        publication_timestamp=None, availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
        approved_sessions=SESSIONS, semantic_mapping_version="status-map-v1",
        input_artifact_ids=("provider", "official"))
    assert item.derived_available_at.isoformat() == "2022-06-06T16:30:00+08:00"
    assert item.usable_at_D_cutoff is True


def test_date_only_same_day_publication_is_not_assumed_known_by_cutoff() -> None:
    item = StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
        security_identity="A", status_semantic="RESUMPTION", effective_session=date(2022, 6, 6),
        provider_observation="R", independent_observation="date-only notice", independent_source_id="SSE",
        source_reference="notice", source_document_hash="doc", publication_date=date(2022, 6, 6),
        publication_timestamp=None, availability_basis="NEXT_SESSION_SAFE", approved_sessions=SESSIONS,
        semantic_mapping_version="status-map-v1", input_artifact_ids=("p", "o"))
    assert item.derived_available_at.date() == date(2022, 6, 7)
    assert item.usable_at_D_cutoff is False


def test_planned_listing_cannot_be_mapped_to_actual_tradable_listing() -> None:
    with pytest.raises(ValueError, match="planned listing"):
        StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
            security_identity="002525.SZ", status_semantic="ACTUAL_FIRST_TRADABLE_SESSION",
            effective_session=date(2010, 1, 1), provider_observation="planned listing",
            independent_observation="planned listing", independent_source_id="SZSE",
            source_reference="notice", source_document_hash="doc", publication_date=date(2010, 1, 1),
            publication_timestamp=None, availability_basis="NEXT_SESSION_SAFE", approved_sessions=SESSIONS,
            semantic_mapping_version="status-map-v1", input_artifact_ids=("p", "o"))


def test_later_document_does_not_backfill_historical_knowledge_time() -> None:
    published = datetime(2025, 7, 1, 9, tzinfo=timezone(timedelta(hours=8)))
    item = StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
        security_identity="688053.SH", status_semantic="ACTUAL_FIRST_TRADABLE_SESSION",
        effective_session=date(2022, 7, 8), provider_observation="actual D trading",
        independent_observation="retrospective listing confirmation", independent_source_id="CNINFO",
        source_reference="2025 disclosure", source_document_hash="doc", publication_date=date(2025, 7, 1),
        publication_timestamp=published, availability_basis="PUBLICATION_TIMESTAMP_BASED",
        approved_sessions=(date(2022, 7, 8), date(2025, 7, 1)), semantic_mapping_version="status-map-v2",
        input_artifact_ids=("provider", "official"))
    assert item.derived_available_at == published
    assert item.usable_at_D_cutoff is False


def test_st_to_star_st_is_not_an_exit() -> None:
    with pytest.raises(ValueError, match="still risk-warning"):
        StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
            security_identity="A", status_semantic="ST_EXIT", effective_session=date(2022, 6, 6),
            provider_observation="*ST", independent_observation="ST to *ST",
            independent_source_id="daily", source_reference="daily status", source_document_hash="doc",
            publication_date=None, publication_timestamp=None, availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
            approved_sessions=SESSIONS, semantic_mapping_version="status-map-v2", input_artifact_ids=("p", "o"))


def test_d_plus_one_resumption_cannot_be_known_at_d_close() -> None:
    item = StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
        security_identity="A", status_semantic="RESUMPTION", effective_session=date(2022, 6, 7),
        provider_observation="trading", independent_observation="actual D+1 trading",
        independent_source_id="daily", source_reference="daily status", source_document_hash="doc",
        publication_date=None, publication_timestamp=None, availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
        approved_sessions=SESSIONS, semantic_mapping_version="status-map-v2", input_artifact_ids=("p", "o"))
    d_cutoff = datetime(2022, 6, 6, 16, 30, tzinfo=timezone(timedelta(hours=8)))
    assert item.derived_available_at > d_cutoff


def test_actual_first_trading_becomes_known_at_d_close_not_before() -> None:
    item = StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
        security_identity="688053.SH", status_semantic="ACTUAL_FIRST_TRADABLE_SESSION",
        effective_session=date(2022, 7, 8), provider_observation="actual D trading",
        independent_observation="actual first trading observed", independent_source_id="daily",
        source_reference="daily status", source_document_hash="doc", publication_date=None,
        publication_timestamp=None, availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
        approved_sessions=(date(2022, 7, 8),), semantic_mapping_version="status-map-v2",
        input_artifact_ids=("p", "o"))
    assert item.derived_available_at.isoformat() == "2022-07-08T16:30:00+08:00"


def test_identity_transition_rejects_retrospective_provider_backfill() -> None:
    with pytest.raises(ValueError, match="official effective identity chain"):
        StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
            security_identity="A", status_semantic="IDENTITY_TRANSITION", effective_session=date(2022, 6, 6),
            provider_observation="new code", independent_observation="retrospective provider code backfill",
            independent_source_id="provider", source_reference="backfill", source_document_hash="doc",
            publication_date=None, publication_timestamp=None, availability_basis="NEXT_SESSION_SAFE",
            approved_sessions=SESSIONS, semantic_mapping_version="status-map-v2", input_artifact_ids=("p",))


def test_ambiguous_status_evidence_fails_closed() -> None:
    with pytest.raises(ValueError, match="independent evidence"):
        StatusKnowledgeTimeObservationV1.create(event_id="e", sample_entry_id="s",
            security_identity="A", status_semantic="FULL_DAY_SUSPENSION", effective_session=date(2022, 6, 6),
            provider_observation="S", independent_observation="", independent_source_id="",
            source_reference="", source_document_hash="", publication_date=None, publication_timestamp=None,
            availability_basis="MARKET_OBSERVABLE_BY_CLOSE", approved_sessions=SESSIONS,
            semantic_mapping_version="status-map-v2", input_artifact_ids=("p",))


def test_pit_artifact_requires_all_eight_semantics_for_complete_pass() -> None:
    rules = tuple((semantic, "MARKET_OBSERVABLE_BY_CLOSE", "D@16:30+08:00")
                  for semantic in REQUIRED_STATUS_SEMANTICS)
    complete = StatusPITKnowledgeTimeEvidenceV1.create(policy_version="status-availability-after-close-v2",
        historical_cutoff="16:30:00+08:00", semantic_rules=rules,
        supporting_evidence_ids=("ledger", "calendar", "master", "daily"),
        safe_session_rules=("date-only=>next-approved-session@16:30",), contract_id="contract",
        inventory_id="inventory", final_cross_source_evidence_id="ledger", source_version_identity="source")
    assert complete.complete is True
    assert complete.verify() is True

    incomplete = StatusPITKnowledgeTimeEvidenceV1.create(policy_version="status-availability-after-close-v2",
        historical_cutoff="16:30:00+08:00", semantic_rules=rules[:-1],
        supporting_evidence_ids=("ledger",), safe_session_rules=("date-only=>next-session",),
        contract_id="contract", inventory_id="inventory", final_cross_source_evidence_id="ledger",
        source_version_identity="source")
    assert incomplete.complete is False
