from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from v5_2.data.real_audits.phase2a_bar_backfill import load_validated_backfill, publishable_backfill_facts
from v5_2.data.real_audits.daily_bar_availability import (
    DailyBarAvailabilityBasis,
    DailyBarAvailabilityError,
    DailyBarAvailabilityPolicyV1,
)


SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[2]


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


@pytest.mark.skipif(not (ROOT / "data/phase_2a/bar_backfill/raw").is_dir(), reason="real artifacts excluded")
def test_real_quarantined_backfill_integrity_and_receipts_are_revalidated_without_network():
    result = load_validated_backfill(ROOT)

    assert result.inventory_id == "70c7d78674a9584704f3e8f4306584cc479d61e529d482f5abfe314cfd7f3494"
    assert len(result.payload_hashes) == 10
    assert len(result.receipt_hashes) == 10
    assert len(result.rows) == 43
    assert result.rejected_rows == ()
    assert result.unexplained_missing_sessions == (
        (9, "2019-04-12"), (9, "2019-04-16"),
        (10, "2015-11-16"), (10, "2015-11-18"), (10, "2015-11-19"),
        (10, "2015-11-20"), (10, "2015-11-23"), (11, "2014-09-11"),
        (14, "2023-08-03"), (14, "2023-08-04"), (14, "2023-08-07"),
        (14, "2023-08-08"), (14, "2023-08-09"), (14, "2023-08-10"),
    )
