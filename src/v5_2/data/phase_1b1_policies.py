from __future__ import annotations

from datetime import datetime, timezone
from types import MappingProxyType

from v5_2.data.audit_policy import RealSourceAuditPolicyV1


CREATED_AT = datetime(2026, 9, 6, tzinfo=timezone.utc)
VERSION = "phase-1b1-audit-v1"


def _policy(dataset_kind: str, **sections: object) -> RealSourceAuditPolicyV1:
    return RealSourceAuditPolicyV1.create(
        policy_version=VERSION,
        dataset_kind=dataset_kind,
        created_at=CREATED_AT,
        **sections,  # type: ignore[arg-type]
    )


def phase_1b1_policies():
    calendar = _policy(
        "trade_calendar",
        required_coverage={
            "start": "2010-01-01",
            "end": "2025-12-31",
            "exchanges": ("SSE", "SZSE"),
            "required_fields": ("exchange", "calendar_date", "is_open"),
        },
        sample_selection_rule={
            "selection": "sha256_lowest_per_year_exchange_stratum",
            "seed": "v5.2-phase-1b1-trade-calendar-v1",
            "strata": (
                {"name": "spring_festival_boundary", "minimum": 2},
                {"name": "national_day_boundary", "minimum": 2},
                {"name": "weekend_makeup_boundary", "minimum": 2},
            ),
        },
        missing_row_policy={"action": "REJECT", "weekday_inference": "FORBIDDEN"},
        duplicate_policy={"key": ("exchange", "calendar_date"), "maximum": 0},
        cross_source_rule={
            "sources": ("SSE_OFFICIAL", "SZSE_OFFICIAL"),
            "fields": ("is_open",),
            "tolerance": 0,
            "unresolved_action": "PENDING",
        },
        pit_rule={"availability": "NEXT_VERIFIED_SESSION_CLOSE", "date_only": True},
        revision_rule={"same_request_page_payload_change": "REVISION_EVIDENCE_REQUIRED"},
        approval_thresholds={
            "coverage_ratio": "1.0",
            "duplicate_keys": 0,
            "cross_source_mismatches": 0,
            "unresolved_session_conflicts": 0,
        },
    )
    master = _policy(
        "security_master",
        required_coverage={
            "as_of": "2025-12-31",
            "exchanges": ("SSE", "SZSE"),
            "listing_statuses": ("D", "L", "P"),
            "include_historical_delisted": True,
            "required_fields": (
                "symbol", "exchange", "security_name", "security_type",
                "listing_date", "delisting_date", "board", "is_a_share",
            ),
        },
        sample_selection_rule={
            "selection": "sha256_lowest_per_stratum",
            "seed": "v5.2-phase-1b1-security-master-v1",
            "minimum_per_stratum": 4,
            "strata": (
                "currently_listed", "recent_ipo", "old_ipo", "delisted",
                "SH_main", "SH_STAR", "SZ_main", "SZ_ChiNext",
            ),
        },
        missing_row_policy={"historical_delisted_missing": "PENDING", "null_delist_for_listed": "ALLOW"},
        duplicate_policy={"key": ("symbol", "exchange"), "maximum": 0},
        cross_source_rule={
            "sources": ("SSE_OFFICIAL", "SZSE_OFFICIAL"),
            "fields": ("symbol", "listing_date", "delisting_date", "board"),
            "tolerance": 0,
            "unresolved_action": "PENDING",
        },
        pit_rule={"current_membership_backfill": "FORBIDDEN", "identity_fact": "EFFECTIVE_DATED"},
        revision_rule={"identity_change": "NEW_EFFECTIVE_DATED_FACT"},
        approval_thresholds={
            "duplicate_keys": 0,
            "minimum_delisted_records": 1,
            "cross_source_mismatches": 0,
            "unresolved_cases": 0,
        },
    )
    bars = _policy(
        "daily_bar",
        required_coverage={
            "start": "2024-01-01",
            "end": "2025-12-31",
            "universe": "DETERMINISTIC_PHASE_1B1_SECURITY_MASTER_SAMPLE",
            "price_basis": "UNADJUSTED_RAW",
            "required_fields": ("symbol", "session", "open", "high", "low", "close", "volume", "amount"),
        },
        sample_selection_rule={
            "selection": "sha256_lowest_per_market_event_stratum",
            "seed": "v5.2-phase-1b1-daily-bar-v1",
            "minimum_per_stratum": 5,
            "strata": (
                "normal", "limit_event", "zero_volume", "ipo_boundary",
                "delisting_boundary", "high_volatility", "holiday_adjacent",
            ),
        },
        missing_row_policy={
            "action": "PENDING_IF_UNEXPLAINED",
            "absence_semantics": "DO_NOT_INFER_SUSPENSION",
        },
        duplicate_policy={"key": ("symbol", "session"), "maximum": 0},
        cross_source_rule={
            "sources": ("SSE_OFFICIAL", "SZSE_OFFICIAL"),
            "optional_auxiliary": "BAOSTOCK",
            "fields": ("open", "high", "low", "close", "volume", "amount"),
            "price_tolerance": "0.0001",
            "volume_tolerance": "0",
            "unresolved_action": "PENDING",
        },
        pit_rule={
            "observation": "RAW_MARKET_OBSERVATION",
            "future_adjustment": "FORBIDDEN",
            "historical_acquisition_time": "NOT_AVAILABLE_AT",
        },
        revision_rule={"same_symbol_session_change": "REVISION_EVIDENCE_REQUIRED"},
        approval_thresholds={
            "ohlc_invariant_failures": 0,
            "negative_value_failures": 0,
            "duplicate_keys": 0,
            "cross_source_value_mismatches": 0,
            "unresolved_missing_rows": 0,
        },
    )
    return MappingProxyType({
        "trade_calendar": calendar,
        "security_master": master,
        "daily_bar": bars,
    })
