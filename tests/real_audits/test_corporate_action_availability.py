from datetime import date, datetime, timedelta, timezone

import pytest

from v5_2.data.corporate_action_facts import KnowledgeClass
from v5_2.data.real_audits.corporate_action_availability import (
    AvailabilityError,
    CorporateActionAvailabilityPolicyV1,
)


CN = timezone(timedelta(hours=8), "Asia/Shanghai")
POLICY = CorporateActionAvailabilityPolicyV1(
    approved_sessions=(
        date(2024, 6, 3), date(2024, 6, 4), date(2024, 6, 5),
        date(2026, 1, 5), date(2026, 1, 6),
    )
)


def test_verified_timestamp_is_used_as_historical_knowledge_time():
    published = datetime(2024, 6, 3, 15, 15, tzinfo=CN)
    result = POLICY.historical(published_at=published, publication_date=None)
    assert result.available_at == published
    assert result.knowledge_class is KnowledgeClass.KNOWN_IN_ADVANCE


def test_date_only_historical_publication_uses_next_session_cutoff():
    result = POLICY.historical(published_at=None, publication_date=date(2024, 6, 3))
    assert result.available_at == datetime(2024, 6, 4, 16, 30, tzinfo=CN)


def test_effective_only_event_is_not_known_in_advance():
    result = POLICY.economic_effect_only(effective_date=date(2024, 6, 3))
    assert result.available_at == datetime(2024, 6, 4, 16, 30, tzinfo=CN)
    assert result.knowledge_class is KnowledgeClass.ECONOMIC_EFFECT_ONLY


def test_production_observation_requires_complete_immutable_lineage():
    observed = datetime(2026, 9, 10, 20, 5, tzinfo=CN)
    with pytest.raises(AvailabilityError, match="lineage"):
        POLICY.production_observation(
            requested_at=observed,
            observed_at=observed,
            payload_hash="payload",
            receipt_hash="",
            source_version_identity="schema-v1",
        )


def test_production_observation_uses_observed_time_but_backfill_does_not():
    observed = datetime(2026, 9, 10, 20, 5, tzinfo=CN)
    production = POLICY.production_observation(
        requested_at=datetime(2026, 9, 10, 20, 0, tzinfo=CN),
        observed_at=observed,
        payload_hash="payload",
        receipt_hash="receipt",
        source_version_identity="schema-v1",
    )
    backfill = POLICY.historical(published_at=None, publication_date=date(2026, 1, 5))
    assert production.available_at == observed
    assert backfill.available_at != observed
