from dataclasses import replace
from datetime import date
from decimal import Decimal

from v5_2.data.daily_bar_facts import DailyBarFactV1


def test_daily_bar_fact_applies_units_availability_and_effective_identity() -> None:
    fact = DailyBarFactV1.create(
        source_symbol="302132.SZ", session=date(2025, 2, 14), open=Decimal("1"),
        high=Decimal("2"), low=Decimal("1"), close=Decimal("2"), raw_volume=Decimal("3"),
        raw_amount=Decimal("4"), source_payload_hash="a" * 64,
    )
    assert fact.security_identity == "300114.SZ"
    assert fact.volume_shares == Decimal("300")
    assert fact.amount_yuan == Decimal("4000")
    assert fact.available_at.isoformat() == "2025-02-14T15:00:00+08:00"
    assert fact.verify()


def test_daily_bar_fact_detects_tamper() -> None:
    fact = DailyBarFactV1.create(
        source_symbol="000001.SZ", session=date(2025, 1, 2), open=Decimal("1"),
        high=Decimal("2"), low=Decimal("1"), close=Decimal("2"), raw_volume=Decimal("3"),
        raw_amount=Decimal("4"), source_payload_hash="a" * 64,
    )
    assert not replace(fact, close=Decimal("9")).verify()
