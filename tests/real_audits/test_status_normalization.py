from datetime import date

import pytest

from v5_2.data.real_audits.status_normalization import StatusNormalizationError, StatusNormalizationPolicyV1
from v5_2.data.security_status_facts import StatusKind


SESSIONS = (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8))


def test_namechange_normalization_freezes_st_semantics_and_date_only_availability() -> None:
    fact = StatusNormalizationPolicyV1.default().normalize_namechange({
        "ts_code": "000001.SZ", "name": "*ST平安", "start_date": "20250103",
        "end_date": "20250106", "ann_date": "20250102", "change_reason": "risk warning",
    }, approved_sessions=SESSIONS, source_payload_hash="a" * 64)
    assert fact.status_kind is StatusKind.RISK_WARNING
    assert fact.status_value == "ST"
    assert fact.effective_from == date(2025, 1, 3)
    assert fact.effective_to == date(2025, 1, 6)
    assert fact.available_at.isoformat() == "2025-01-03T15:00:00+08:00"


def test_non_st_name_is_explicit_clear_interval() -> None:
    fact = StatusNormalizationPolicyV1.default().normalize_namechange({
        "ts_code": "000001.SZ", "name": "平安银行", "start_date": "20250103",
        "end_date": "", "ann_date": "20250102", "change_reason": "remove risk warning",
    }, approved_sessions=SESSIONS, source_payload_hash="a" * 64)
    assert fact.status_value == "CLEAR"
    assert fact.effective_to is None


def test_suspension_start_and_resume_create_adjacent_intervals() -> None:
    facts = StatusNormalizationPolicyV1.default().normalize_suspension_events((
        {"ts_code": "000001.SZ", "trade_date": "20250103", "suspend_timing": "09:30", "suspend_type": "S"},
        {"ts_code": "000001.SZ", "trade_date": "20250107", "suspend_timing": "09:30", "suspend_type": "R"},
    ), approved_sessions=SESSIONS, source_payload_hash="b" * 64)
    assert [(fact.status_value, fact.effective_from, fact.effective_to) for fact in facts] == [
        ("SUSPENDED", date(2025, 1, 3), date(2025, 1, 6)),
        ("TRADING", date(2025, 1, 7), None),
    ]


def test_unmatched_resume_and_malformed_dates_fail_closed() -> None:
    policy = StatusNormalizationPolicyV1.default()
    with pytest.raises(StatusNormalizationError, match="resume"):
        policy.normalize_suspension_events((
            {"ts_code": "000001.SZ", "trade_date": "20250103", "suspend_timing": "09:30", "suspend_type": "R"},
        ), approved_sessions=SESSIONS, source_payload_hash="b" * 64)
    with pytest.raises(StatusNormalizationError, match="date"):
        policy.normalize_namechange({"ts_code": "000001.SZ", "name": "ST坏", "start_date": "bad",
                                     "end_date": "", "ann_date": "20250102", "change_reason": "x"},
                                    approved_sessions=SESSIONS, source_payload_hash="a" * 64)
