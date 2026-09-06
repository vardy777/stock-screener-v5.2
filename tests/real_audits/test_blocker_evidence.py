from __future__ import annotations

from datetime import datetime, timezone

from v5_2.data.real_audits.blocker_evidence import (
    SecurityDisposition,
    SecurityMasterNormalizationExceptionEvidenceV1,
    TradeCalendarUnresolvedSampleInventoryV1,
)


def provider_calendar():
    rows = {}
    from datetime import date, timedelta
    cursor = date(2010, 1, 1)
    while cursor <= date(2025, 12, 31):
        for exchange in ("SSE", "SZSE"):
            rows[(exchange, cursor.isoformat())] = int(cursor.weekday() < 5)
        cursor += timedelta(days=1)
    return rows


def test_calendar_inventory_is_exact_content_addressed_and_stratified() -> None:
    first = TradeCalendarUnresolvedSampleInventoryV1.create(
        provider_observations=provider_calendar(), official_observations={},
        verified_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
        policy_id="policy", policy_version="inventory-v1",
    )
    second = TradeCalendarUnresolvedSampleInventoryV1.create(
        provider_observations=provider_calendar(), official_observations={},
        verified_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
        policy_id="policy", policy_version="inventory-v1",
    )
    assert first.inventory_id == first.content_hash == second.inventory_id
    assert first.total_samples == 256
    assert first.verified_samples == 0
    assert first.unresolved_samples == 256
    assert set(first.by_exchange) == {"SSE", "SZSE"}
    assert set(first.by_stratum) == {
        "spring_festival_boundary", "national_day_boundary",
        "weekend_makeup_boundary", "cross_year_boundary",
    }


def test_official_observation_resolves_only_exact_sample_identity() -> None:
    empty = TradeCalendarUnresolvedSampleInventoryV1.create(
        provider_observations=provider_calendar(), official_observations={},
        verified_at=datetime(2026, 9, 6, tzinfo=timezone.utc), policy_id="policy", policy_version="inventory-v1",
    )
    sample = empty.samples[0]
    official = {(sample.exchange, sample.calendar_date): sample.provider_is_open}
    resolved = TradeCalendarUnresolvedSampleInventoryV1.create(
        provider_observations=provider_calendar(), official_observations=official,
        verified_at=datetime(2026, 9, 6, tzinfo=timezone.utc), policy_id="policy", policy_version="inventory-v1",
    )
    assert resolved.verified_samples == 1
    assert resolved.unresolved_samples == 255


def test_security_exception_evidence_records_all_dispositions() -> None:
    evidence = SecurityMasterNormalizationExceptionEvidenceV1.create(
        records=(
            {"ts_code": "689009.SH", "classification": SecurityDisposition.EXCLUDED_NON_TARGET, "reason": "official CDR identity", "official_source_identity": "sse-official"},
            {"ts_code": "T600018.SH", "classification": SecurityDisposition.REJECTED_UNRESOLVED, "reason": "synthetic historical identity", "official_source_identity": "sse-official"},
        ),
        verified_at=datetime(2026, 9, 6, tzinfo=timezone.utc), policy_version="exceptions-v1",
        input_artifact_ids=("raw",),
    )
    assert evidence.excluded_non_target == 1
    assert evidence.unresolved == 1
    assert evidence.evidence_id == evidence.content_hash
