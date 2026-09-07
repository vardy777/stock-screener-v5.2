from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from v5_2.data.real_audits.daily_bar_adjustment import audit_unadjusted_raw
from v5_2.data.real_audits.daily_bar_completeness import audit_completeness
from v5_2.data.real_audits.daily_bar_exceptions import DailyBarExceptionBudgetV1, DailyBarExceptionPatternAuditV1, DailyBarExceptionalRecordV1
from v5_2.data.real_audits.daily_bar_normalization import DailyBarNormalizationError, DailyBarNormalizationPolicyV1
from v5_2.data.real_audits.daily_bar_units import DailyBarUnitPolicyV1, audit_unit
from v5_2.data.real_audits.daily_bar_validation import audit_bars


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)
RAW = {"ts_code": "000001.SZ", "trade_date": "20250102", "open": "10", "high": "11", "low": "9", "close": "10.5", "vol": "123", "amount": "456"}


def test_normalization_is_exact_pure_and_rejects_invalid_numeric_values() -> None:
    policy = DailyBarNormalizationPolicyV1.create_default()
    bar = policy.normalize(RAW, volume_factor=Decimal("100"), amount_factor=Decimal("1000"), effective_identity="000001.SZ")
    assert (bar.session, bar.volume, bar.amount, bar.price_basis) == (date(2025, 1, 2), Decimal("12300"), Decimal("456000"), "UNADJUSTED_RAW")
    for invalid in ("NaN", "Infinity", "broken"):
        with pytest.raises(DailyBarNormalizationError):
            policy.normalize({**RAW, "open": invalid}, volume_factor=Decimal(100), amount_factor=Decimal(1000), effective_identity="000001.SZ")


@pytest.mark.parametrize("patch", ({"high": "9"}, {"low": "11"}, {"open": "0"}, {"vol": "-1"}))
def test_ohlc_structure_fails_closed(patch) -> None:
    result = audit_bars(({**RAW, **patch},), approved_sessions={date(2025, 1, 2)}, identity_resolver=lambda *_: "000001.SZ")
    assert not result.passed


def test_session_and_effective_identity_alignment() -> None:
    assert not audit_bars((RAW,), approved_sessions={date(2025, 1, 3)}, identity_resolver=lambda *_: "000001.SZ").session_alignment_pass
    assert not audit_bars((RAW,), approved_sessions={date(2025, 1, 2)}, identity_resolver=lambda *_: None).identity_alignment_pass
    resolver = lambda symbol, session: "300114.SZ" if session <= date(2025, 2, 16) else "302132.SZ"
    rows = ({**RAW, "ts_code": "300114.SZ", "trade_date": "20250216"}, {**RAW, "ts_code": "302132.SZ", "trade_date": "20250217"})
    assert audit_bars(rows, approved_sessions={date(2025, 2, 16), date(2025, 2, 17)}, identity_resolver=resolver).identity_alignment_pass


def test_units_require_one_constant_factor_and_reject_mixed_source() -> None:
    volume = audit_unit("volume", ((Decimal(10), Decimal(1000)), (Decimal(20), Decimal(2000))), policy_version="unit-v1")
    assert volume.passed and volume.conversion_factor == Decimal(100)
    assert not audit_unit("amount", ((Decimal(10), Decimal(10000)), (Decimal(20), Decimal(10000))), policy_version="unit-v1").passed
    policy = DailyBarUnitPolicyV1.create(volume_factor=Decimal(100), amount_factor=Decimal(1000), evidence_ids=(volume.evidence_id, "amount"))
    assert policy.volume_factor == Decimal(100)


def test_adjusted_price_contamination_is_dataset_level_failure() -> None:
    assert audit_unadjusted_raw(((Decimal("10"), Decimal("10")),), tolerance=Decimal("0.0001"), evidence_ids=("sample",)).passed
    assert not audit_unadjusted_raw(((Decimal("10"), Decimal("9")),), tolerance=Decimal("0.0001"), evidence_ids=("sample",)).passed


def test_local_exception_budget_and_systematic_pattern() -> None:
    one = DailyBarExceptionalRecordV1.create(security_identity="000001.SZ", session=date(2025, 1, 2),
        affected_fields=("close",), exception_type="REFERENCE_VALUE_CONFLICT", evidence_ids=("e",), disposition="QUARANTINE", created_at=NOW, policy_version="daily-exception-v1", dimensions={"exchange": "SZSE"})
    budget = DailyBarExceptionBudgetV1.create_default()
    audit = DailyBarExceptionPatternAuditV1.evaluate((one,), budget=budget)
    assert budget.evaluate((one,), total_rows=100000, pattern_audit=audit).passed
    clustered = tuple(DailyBarExceptionalRecordV1.create(security_identity=f"00000{i}.SZ", session=date(2025, 1, 2), affected_fields=("close",), exception_type="REFERENCE_VALUE_CONFLICT", evidence_ids=(str(i),), disposition="QUARANTINE", created_at=NOW, policy_version="daily-exception-v1", dimensions={"exchange": "SZSE"}) for i in range(5))
    assert DailyBarExceptionPatternAuditV1.evaluate(clustered, budget=budget).systematic_defect
    assert not budget.evaluate(clustered, total_rows=100000, pattern_audit=DailyBarExceptionPatternAuditV1.evaluate(clustered, budget=budget)).passed


def test_completeness_distinguishes_not_applicable_from_missing() -> None:
    result = audit_completeness(symbols=("A",), sessions=(date(2025, 1, 2), date(2025, 1, 3)),
                                valid_intervals={"A": (date(2025, 1, 3), None)}, observed_keys={("A", date(2025, 1, 3))})
    assert (result.requested, result.applicable, result.not_applicable, result.missing) == (2, 1, 1, 0)
