from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone

import pytest

from v5_2.data.real_audits.daily_bar_availability import (
    DailyBarAvailabilityBasis,
    DailyBarAvailabilityError,
    DailyBarAvailabilityEvidenceV1,
    DailyBarAvailabilityPolicyV1,
    DailyBarProbeObservationV1,
)


SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")
SESSION = date(2026, 9, 9)
NEXT_SESSION = date(2026, 9, 10)
SYMBOLS = ("000001.SZ", "300750.SZ", "600000.SH", "688981.SH")
COMPLETE_ROWS = tuple(
    {
        "ts_code": symbol,
        "trade_date": "20260909",
        "open": "1",
        "high": "2",
        "low": "1",
        "close": "2",
        "vol": "3",
        "amount": "4",
    }
    for symbol in SYMBOLS
)


def observation(*, requested_at, rows=COMPLETE_ROWS, payload_hash="a" * 64, source="source-v1"):
    return DailyBarProbeObservationV1.create(
        session=SESSION,
        requested_at=requested_at,
        expected_symbols=SYMBOLS,
        rows=rows,
        payload_hash=payload_hash,
        receipt_id="b" * 64,
        source_version_identity=source,
    )


def evidence(*, observations, source="source-v1"):
    return DailyBarAvailabilityEvidenceV1.create(
        policy_version="daily-bar-availability-v1",
        source_name="datahubco_tushare_proxy",
        source_version_identity=source,
        coverage_sessions=(SESSION,),
        probe_times=tuple(item.requested_at for item in observations),
        sample_scope=SYMBOLS,
        observations=observations,
        revision_findings=(),
        full_market_readiness_rule="no same-day full-market readiness claim",
        historical_available_at_rule="NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
        supporting_receipt_ids=tuple(item.receipt_id for item in observations),
    )


def test_market_close_is_not_provider_availability() -> None:
    policy = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.MARKET_CLOSE,
        cutoff=time(15, 0),
        policy_version="daily-bar-availability-v1",
    )
    with pytest.raises(DailyBarAvailabilityError, match="does not prove provider availability"):
        policy.available_at(SESSION, next_session=NEXT_SESSION, evidence=None, source_version_identity="source-v1")


def test_missing_bar_keeps_availability_evidence_incomplete() -> None:
    item = observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI), rows=())
    assert not item.complete
    assert not evidence(observations=(item,)).complete


def test_incomplete_bar_keeps_availability_evidence_incomplete() -> None:
    rows = tuple({key: value for key, value in row.items() if key != "amount"} for row in COMPLETE_ROWS)
    item = observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI), rows=rows)
    assert not item.complete


def test_partial_universe_is_not_full_sample_ready() -> None:
    item = observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI), rows=COMPLETE_ROWS[:-1])
    assert not item.complete
    assert item.observed_symbols != SYMBOLS


def test_revision_after_first_appearance_prevents_stability_claim() -> None:
    first = observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI))
    revised = observation(
        requested_at=datetime(2026, 9, 10, 8, 5, tzinfo=SHANGHAI),
        rows=tuple({**row, "close": "3"} for row in COMPLETE_ROWS),
        payload_hash="c" * 64,
    )
    assert not evidence(observations=(first, revised)).complete


def test_before_conservative_cutoff_is_not_visible() -> None:
    item = evidence(observations=(observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI)),))
    policy = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.NEXT_SESSION_SAFE,
        cutoff=time(16, 30),
        policy_version="daily-bar-availability-v1",
    )
    available = policy.available_at(SESSION, next_session=NEXT_SESSION, evidence=item, source_version_identity="source-v1")
    assert datetime(2026, 9, 10, 16, 29, tzinfo=SHANGHAI) < available


def test_verified_next_session_cutoff_is_visible_at_cutoff() -> None:
    item = evidence(observations=(observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI)),))
    policy = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.NEXT_SESSION_SAFE,
        cutoff=time(16, 30),
        policy_version="daily-bar-availability-v1",
    )
    assert policy.available_at(SESSION, next_session=NEXT_SESSION, evidence=item, source_version_identity="source-v1") == datetime(2026, 9, 10, 16, 30, tzinfo=SHANGHAI)


def test_next_day_observation_cannot_backfill_same_day_cutoff() -> None:
    item = evidence(observations=(observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI)),))
    same_day = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.CONSERVATIVE_AFTER_CLOSE,
        cutoff=time(16, 30),
        policy_version="daily-bar-availability-v1",
    )
    with pytest.raises(DailyBarAvailabilityError, match="same-day cutoff"):
        same_day.available_at(SESSION, next_session=NEXT_SESSION, evidence=item, source_version_identity="source-v1")


def test_tampered_availability_artifact_fails_closed() -> None:
    item = evidence(observations=(observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI)),))
    policy = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.NEXT_SESSION_SAFE,
        cutoff=time(16, 30),
        policy_version="daily-bar-availability-v1",
    )
    with pytest.raises(DailyBarAvailabilityError, match="integrity"):
        policy.available_at(SESSION, next_session=NEXT_SESSION, evidence=replace(item, complete=False), source_version_identity="source-v1")


def test_source_version_mismatch_fails_closed() -> None:
    item = evidence(observations=(observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI)),))
    policy = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.NEXT_SESSION_SAFE,
        cutoff=time(16, 30),
        policy_version="daily-bar-availability-v1",
    )
    with pytest.raises(DailyBarAvailabilityError, match="source version"):
        policy.available_at(SESSION, next_session=NEXT_SESSION, evidence=item, source_version_identity="source-v2")


def test_supporting_receipts_can_include_safe_session_calendar_lineage() -> None:
    item = observation(requested_at=datetime(2026, 9, 10, 8, 0, tzinfo=SHANGHAI))
    result = DailyBarAvailabilityEvidenceV1.create(
        policy_version="daily-bar-availability-v1", source_name="datahubco_tushare_proxy",
        source_version_identity="source-v1", coverage_sessions=(SESSION,), probe_times=(item.requested_at,),
        sample_scope=SYMBOLS, observations=(item,), revision_findings=(),
        full_market_readiness_rule="no same-day full-market readiness claim",
        historical_available_at_rule="NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
        supporting_receipt_ids=(item.receipt_id, "calendar-receipt"),
    )
    assert result.complete
