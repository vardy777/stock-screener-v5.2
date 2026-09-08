from datetime import date

import pytest

from v5_2.data.real_audits.status_knowledge_time import StatusKnowledgeTimeObservationV1

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
