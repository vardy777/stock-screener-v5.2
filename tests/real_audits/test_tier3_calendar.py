from __future__ import annotations

from datetime import datetime, timezone

import pytest

from v5_2.data.real_audits.policy_adequacy import CrossSourceEvidencePolicyV2
from v5_2.data.real_audits.tier3_calendar import (
    CrossSourceEvidencePolicyAdoptionArtifactV1,
    IndependentCalendarSampleRequestV1,
    IndependentSourceIdentityV1,
    compare_independent_calendar,
)


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def source(coverage=("SSE",)):
    return IndependentSourceIdentityV1.create(
        source_name="baostock", provider_identity="BaoStock 0.9.3",
        dataset_kind="trade_calendar", endpoint_identity="query_trade_dates",
        source_independence_rationale="separate provider, protocol and distribution",
        coverage_capability={"start": "1990-01-01", "exchanges": coverage},
        schema_identity=("calendar_date", "is_trading_day"), retrieved_at=NOW,
        policy_version="independent-source-v1",
    )


def test_tier3_source_must_be_independent_from_datahub() -> None:
    with pytest.raises(ValueError, match="independent"):
        IndependentSourceIdentityV1.create(
            source_name="datahub-wrapper", provider_identity="DataHub mirror",
            dataset_kind="trade_calendar", endpoint_identity="trade-cal",
            source_independence_rationale="same upstream", coverage_capability={"exchanges": ("SSE",)},
            schema_identity=("calendar_date",), retrieved_at=NOW, policy_version="v1",
        )


def test_request_inventory_reuses_exact_frozen_sample_ids() -> None:
    frozen = (
        {"sample_id": "b", "exchange": "SZSE", "calendar_date": "2025-01-01", "sample_stratum": "cross_year_boundary", "provider_is_open": 0},
        {"sample_id": "a", "exchange": "SSE", "calendar_date": "2025-01-01", "sample_stratum": "cross_year_boundary", "provider_is_open": 0},
    )
    requests = IndependentCalendarSampleRequestV1.from_frozen(frozen, source())
    assert tuple(item.sample_id for item in requests) == ("a", "b")
    assert {item.sample_id for item in requests} == {item["sample_id"] for item in frozen}
    with pytest.raises(Exception):
        requests[0].sample_id = "changed"  # type: ignore[misc]


def test_unavailable_is_not_match_and_mismatch_is_distinct() -> None:
    frozen = (
        {"sample_id": "a", "exchange": "SSE", "calendar_date": "2025-01-01", "sample_stratum": "x", "provider_is_open": 0},
        {"sample_id": "b", "exchange": "SSE", "calendar_date": "2025-01-02", "sample_stratum": "x", "provider_is_open": 1},
        {"sample_id": "c", "exchange": "SZSE", "calendar_date": "2025-01-01", "sample_stratum": "x", "provider_is_open": 0},
    )
    result = compare_independent_calendar(
        IndependentCalendarSampleRequestV1.from_frozen(frozen, source()),
        {"2025-01-01": 0, "2025-01-02": 0}, source(), official_anchors={},
    )
    assert result.match_count == 1
    assert result.mismatch_count == 1
    assert result.unresolved_count == 1


def test_v2_adoption_requires_complete_evidence_and_is_content_addressed() -> None:
    policy = CrossSourceEvidencePolicyV2.create_default()
    with pytest.raises(ValueError, match="complete"):
        CrossSourceEvidencePolicyAdoptionArtifactV1.create(
            v1_policy_id="v1", v2_policy=policy, independent_source=source(),
            sample_evidence_id="sample", total=256, matches=128, mismatches=0,
            unresolved=128, provider_errors=0, official_anchor_evidence_ids=("anchor",),
            adopted_at=NOW, methodological_reason="independent sample plus official anchors",
        )
