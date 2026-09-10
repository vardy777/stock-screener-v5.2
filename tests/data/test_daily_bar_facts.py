from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from v5_2.data.daily_bar_facts import DailyBarFactV1


def test_daily_bar_fact_applies_units_availability_and_effective_identity() -> None:
    available = datetime(2025, 2, 17, 16, 30, tzinfo=timezone(timedelta(hours=8)))
    fact = DailyBarFactV1.create(
        source_symbol="302132.SZ", session=date(2025, 2, 14), open=Decimal("1"),
        high=Decimal("2"), low=Decimal("1"), close=Decimal("2"), raw_volume=Decimal("3"),
        raw_amount=Decimal("4"), source_payload_hash="a" * 64,
        available_at=available, availability_policy_version="daily-bar-availability-v1",
    )
    assert fact.security_identity == "300114.SZ"
    assert fact.volume_shares == Decimal("300")
    assert fact.amount_yuan == Decimal("4000")
    assert fact.available_at == available
    assert fact.availability_policy_version == "daily-bar-availability-v1"
    assert fact.verify()


def test_daily_bar_fact_detects_tamper() -> None:
    fact = DailyBarFactV1.create(
        source_symbol="000001.SZ", session=date(2025, 1, 2), open=Decimal("1"),
        high=Decimal("2"), low=Decimal("1"), close=Decimal("2"), raw_volume=Decimal("3"),
        raw_amount=Decimal("4"), source_payload_hash="a" * 64,
        available_at=datetime(2025, 1, 3, 16, 30, tzinfo=timezone(timedelta(hours=8))),
        availability_policy_version="daily-bar-availability-v1",
    )
    assert not replace(fact, close=Decimal("9")).verify()


def test_daily_bar_fact_availability_supersession_preserves_values_and_changes_identity() -> None:
    original = DailyBarFactV1.create(
        source_symbol="000001.SZ", session=date(2025, 1, 2), open=Decimal("1"),
        high=Decimal("2"), low=Decimal("1"), close=Decimal("2"), raw_volume=Decimal("3"),
        raw_amount=Decimal("4"), source_payload_hash="a" * 64,
        available_at=datetime(2025, 1, 2, 15, 0, tzinfo=timezone(timedelta(hours=8))),
        availability_policy_version="daily-bar-d-close-v1",
    )
    corrected = original.supersede_availability(
        available_at=datetime(2025, 1, 3, 16, 30, tzinfo=timezone(timedelta(hours=8))),
        availability_policy_version="daily-bar-availability-v1",
    )
    assert corrected.fact_id != original.fact_id
    assert corrected.available_at.isoformat() == "2025-01-03T16:30:00+08:00"
    assert corrected.open == original.open
    assert corrected.source_payload_hash == original.source_payload_hash
    assert corrected.verify()
    assert corrected.as_dict()["close"] == "2"
    assert corrected.as_dict()["available_at"] == corrected.available_at
