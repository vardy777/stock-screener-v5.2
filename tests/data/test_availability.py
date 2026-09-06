from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest

from v5_2.data.availability import (
    AvailabilityBasis,
    AvailabilityError,
    AvailabilityPolicyV1,
    derive_available_at,
)
from v5_2.foundations.calendar import TradingCalendar


CALENDAR = TradingCalendar.from_records(
    [
        {"date": "2026-01-02", "is_open": True, "source": "SSE"},
        {"date": "2026-01-03", "is_open": False, "source": "SSE"},
        {"date": "2026-01-04", "is_open": False, "source": "SSE"},
        {"date": "2026-01-05", "is_open": True, "source": "SSE"},
    ],
    require_complete_years=False,
)
SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")


def test_date_only_announcement_is_unavailable_at_same_date_close() -> None:
    policy = AvailabilityPolicyV1(
        dataset_kind="synthetic_disclosure",
        basis=AvailabilityBasis.DATE_ONLY_NEXT_SESSION_CLOSE,
        date_field="ann_date",
        timestamp_field=None,
        publication_time=time(15, 0),
        timezone_name="Asia/Shanghai",
        policy_version="availability-v1",
        validation_evidence_id="synthetic-evidence",
    )
    result = derive_available_at(policy, {"ann_date": "2026-01-02"}, CALENDAR)
    assert result.available_at == datetime(
        2026, 1, 5, 15, 0, tzinfo=SHANGHAI
    )
    assert result.available_at > datetime(
        2026, 1, 2, 15, 0, tzinfo=SHANGHAI
    )


def test_historical_backfill_acquisition_time_never_becomes_historical_availability() -> None:
    policy = AvailabilityPolicyV1(
        dataset_kind="synthetic_daily_bar",
        basis=AvailabilityBasis.SESSION_PUBLICATION_TIME,
        date_field="trade_date",
        timestamp_field=None,
        publication_time=time(15, 30),
        timezone_name="Asia/Shanghai",
        policy_version="availability-v1",
        validation_evidence_id="synthetic-evidence",
    )
    result = derive_available_at(
        policy,
        {"trade_date": "2026-01-02"},
        CALENDAR,
        historical_backfill=True,
        acquired_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert result.available_at == datetime(
        2026, 1, 2, 15, 30, tzinfo=SHANGHAI
    )


def test_live_ingestion_uses_later_of_policy_boundary_and_acquisition() -> None:
    policy = AvailabilityPolicyV1(
        "synthetic_daily_bar",
        AvailabilityBasis.SESSION_PUBLICATION_TIME,
        "trade_date",
        None,
        time(15, 30),
        "Asia/Shanghai",
        "availability-v1",
        "synthetic-evidence",
    )
    acquired = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
    result = derive_available_at(
        policy, {"trade_date": "2026-01-02"}, CALENDAR, acquired_at=acquired
    )
    assert result.available_at == acquired.astimezone(SHANGHAI)


def test_unverified_timestamp_field_cannot_be_mapped_to_available_at() -> None:
    policy = AvailabilityPolicyV1(
        "synthetic_disclosure",
        AvailabilityBasis.VERIFIED_TIMESTAMP,
        "ann_date",
        "f_ann_date",
        time(15, 0),
        "Asia/Shanghai",
        "availability-v1",
        "",
    )
    with pytest.raises(AvailabilityError, match="evidence"):
        derive_available_at(
            policy,
            {"ann_date": "2026-01-02", "f_ann_date": "2026-01-02T10:00:00+08:00"},
            CALENDAR,
        )


def test_missing_or_unknown_calendar_mapping_fails_closed() -> None:
    policy = AvailabilityPolicyV1(
        "synthetic_daily_bar",
        AvailabilityBasis.SESSION_PUBLICATION_TIME,
        "trade_date",
        None,
        time(15, 30),
        "Asia/Shanghai",
        "availability-v1",
        "synthetic-evidence",
    )
    with pytest.raises(AvailabilityError, match="calendar"):
        derive_available_at(policy, {"trade_date": date(2026, 1, 6)}, CALENDAR)
