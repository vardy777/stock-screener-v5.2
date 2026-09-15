from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest

from v5_2.data.real_audits.phase2a_bar_backfill import publishable_backfill_facts
from v5_2.data.real_audits.daily_bar_availability import (
    DailyBarAvailabilityBasis,
    DailyBarAvailabilityError,
    DailyBarAvailabilityPolicyV1,
)


SHANGHAI = timezone(timedelta(hours=8))


def test_backfill_normalizes_units_and_uses_next_session_safe():
    rows = (("payload-1", {
        "ts_code": "000333.SZ", "trade_date": "20210601", "open": "80.91",
        "high": "81.00", "low": "79.50", "close": "80.17",
        "vol": "12.5", "amount": "99.25",
    }),)

    facts = publishable_backfill_facts(
        rows, approved_sessions={date(2021, 6, 1)},
        next_session_by_session={date(2021, 6, 1): date(2021, 6, 2)},
        available_at=lambda session, following: datetime.combine(following, time(16, 30), SHANGHAI),
        availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
    )

    assert len(facts) == 1
    fact = facts[0]
    assert fact.volume_shares == Decimal("1250.0")
    assert fact.amount_yuan == Decimal("99250.00")
    assert fact.price_basis == "UNADJUSTED_RAW"
    assert fact.available_at == datetime(2021, 6, 2, 16, 30, tzinfo=SHANGHAI)
    assert fact.source_payload_hash == "payload-1"
    assert fact.verify()


@pytest.mark.parametrize("mutation", [
    {"high": "79"},
    {"ts_code": "999999.SH"},
    {"trade_date": "20210602"},
])
def test_backfill_rejects_invalid_ohlc_identity_or_session(mutation):
    row = {"ts_code": "000333.SZ", "trade_date": "20210601", "open": "80",
           "high": "81", "low": "79", "close": "80", "vol": "1", "amount": "2"}
    row.update(mutation)
    with pytest.raises(ValueError):
        publishable_backfill_facts(
            (("payload-1", row),), approved_sessions={date(2021, 6, 1)},
            next_session_by_session={date(2021, 6, 1): date(2021, 6, 2)},
            available_at=lambda session, following: datetime.combine(following, time(16, 30), SHANGHAI),
            availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
            allowed_identities={"000333.SZ"},
        )


def test_backfill_rejects_duplicate_fact_keys():
    row = {"ts_code": "000333.SZ", "trade_date": "20210601", "open": "80",
           "high": "81", "low": "79", "close": "80", "vol": "1", "amount": "2"}
    with pytest.raises(ValueError, match="duplicate"):
        publishable_backfill_facts(
            (("payload-1", row), ("payload-2", row)),
            approved_sessions={date(2021, 6, 1)},
            next_session_by_session={date(2021, 6, 1): date(2021, 6, 2)},
            available_at=lambda session, following: datetime.combine(following, time(16, 30), SHANGHAI),
            availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
        )


def test_frozen_availability_policy_rejects_source_version_mismatch():
    class Evidence:
        complete = True
        source_version_identity = "availability-version"
        policy_version = "daily-bar-availability-v1"

        @staticmethod
        def verify():
            return True

    policy = DailyBarAvailabilityPolicyV1(
        basis=DailyBarAvailabilityBasis.NEXT_SESSION_SAFE,
        cutoff=time(16, 30), policy_version="daily-bar-availability-v1",
    )
    with pytest.raises(DailyBarAvailabilityError, match="source version mismatch"):
        policy.available_at(
            date(2021, 6, 1), next_session=date(2021, 6, 2),
            evidence=Evidence(), source_version_identity="approval-version",
        )
