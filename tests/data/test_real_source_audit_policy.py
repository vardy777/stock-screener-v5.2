from __future__ import annotations

from datetime import datetime, timezone

import pytest

from v5_2.data.audit_policy import RealSourceAuditPolicyV1
from v5_2.data.phase_1b1_policies import phase_1b1_policies


def test_policy_identity_is_canonical_and_includes_frozen_acceptance_rules() -> None:
    values = dict(
        policy_version="real-source-audit-v1",
        dataset_kind="synthetic",
        required_coverage={"end": "2025-12-31", "start": "2025-01-01"},
        sample_selection_rule={"algorithm": "sha256-lowest", "seed": "fixed"},
        missing_row_policy={"action": "FAIL"},
        duplicate_policy={"max_duplicate_keys": 0},
        cross_source_rule={"required": True, "max_mismatches": 0},
        pit_rule={"date_only": "NEXT_SESSION_CLOSE"},
        revision_rule={"same_page_change": "REVISION"},
        approval_thresholds={"unresolved": 0},
        created_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )
    first = RealSourceAuditPolicyV1.create(**values)
    values["required_coverage"] = {"start": "2025-01-01", "end": "2025-12-31"}
    second = RealSourceAuditPolicyV1.create(**values)
    assert first.policy_id == second.policy_id == first.content_hash
    assert len(first.policy_id) == 64


def test_policy_content_is_deeply_immutable() -> None:
    policy = phase_1b1_policies()["trade_calendar"]
    with pytest.raises(TypeError):
        policy.required_coverage["start"] = "2020-01-01"  # type: ignore[index]
    with pytest.raises(TypeError):
        policy.sample_selection_rule["strata"][0]["minimum"] = 0  # type: ignore[index]


def test_phase_1b1_has_exactly_three_independent_policies() -> None:
    policies = phase_1b1_policies()
    assert set(policies) == {"trade_calendar", "security_master", "daily_bar"}
    assert len({policy.policy_id for policy in policies.values()}) == 3
    assert all(policy.dataset_kind == kind for kind, policy in policies.items())
    assert all(policy.policy_version == "phase-1b1-audit-v1" for policy in policies.values())


def test_trade_calendar_policy_freezes_cross_year_and_holiday_audit() -> None:
    policy = phase_1b1_policies()["trade_calendar"]
    assert policy.required_coverage["start"] == "2010-01-01"
    assert policy.required_coverage["end"] == "2025-12-31"
    assert policy.required_coverage["exchanges"] == ("SSE", "SZSE")
    assert policy.required_coverage["required_fields"] == (
        "exchange", "calendar_date", "is_open"
    )
    assert policy.sample_selection_rule["selection"] == "sha256_lowest_per_year_exchange_stratum"
    assert policy.sample_selection_rule["strata"] == (
        {"name": "spring_festival_boundary", "minimum": 2},
        {"name": "national_day_boundary", "minimum": 2},
        {"name": "weekend_makeup_boundary", "minimum": 2},
    )
    assert policy.missing_row_policy["weekday_inference"] == "FORBIDDEN"
    assert policy.approval_thresholds["unresolved_session_conflicts"] == 0


def test_security_master_policy_requires_delisted_and_board_exchange_strata() -> None:
    policy = phase_1b1_policies()["security_master"]
    assert policy.required_coverage["listing_statuses"] == ("D", "L", "P")
    assert policy.required_coverage["include_historical_delisted"] is True
    assert policy.sample_selection_rule["strata"] == (
        "currently_listed",
        "recent_ipo",
        "old_ipo",
        "delisted",
        "SH_main",
        "SH_STAR",
        "SZ_main",
        "SZ_ChiNext",
    )
    assert policy.approval_thresholds["minimum_delisted_records"] == 1


def test_daily_bar_policy_is_unadjusted_and_observation_only() -> None:
    policy = phase_1b1_policies()["daily_bar"]
    assert policy.required_coverage["price_basis"] == "UNADJUSTED_RAW"
    assert policy.required_coverage["start"] == "2024-01-01"
    assert policy.required_coverage["end"] == "2025-12-31"
    assert policy.missing_row_policy["absence_semantics"] == "DO_NOT_INFER_SUSPENSION"
    assert policy.pit_rule["future_adjustment"] == "FORBIDDEN"
    assert policy.approval_thresholds["ohlc_invariant_failures"] == 0
    assert policy.approval_thresholds["cross_source_value_mismatches"] == 0
