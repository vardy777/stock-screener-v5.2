from datetime import date, datetime, timedelta, timezone

import pytest

from v5_2.data.phase_1b_exit import (
    ExitContractError,
    HistoricalResearchCutoffContractV1,
    HistoricalResearchSessionV1,
    Phase1BCoverageMatrixV1,
    Phase1BExitAcceptanceV1,
)


SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")
SESSION = date(2025, 6, 30)


def cutoff():
    return HistoricalResearchCutoffContractV1.create(
        session=SESSION,
        cutoff=datetime(2025, 6, 30, 16, 30, tzinfo=SHANGHAI),
        timezone_name="Asia/Shanghai",
        calendar_approval_id="calendar-approval",
        approved_open_sessions=(SESSION,),
    )


def matrix(*, daily_start=date(2024, 1, 1), daily_end=date(2025, 12, 31)):
    return Phase1BCoverageMatrixV1.create((
        {"dataset": "trade_calendar", "coverage_start": date(2010, 1, 1), "coverage_end": date(2026, 9, 11),
         "approval_id": "calendar-approval", "manifest_id": "m-cal", "completeness_mode": "COMPLETE",
         "approved_scope": ("OPEN_SESSION",), "unsupported_scope": (), "known_gaps": ()},
        {"dataset": "security_master", "coverage_start": date(2010, 1, 1), "coverage_end": date(2026, 9, 10),
         "approval_id": "a-master", "manifest_id": "m-master", "completeness_mode": "EFFECTIVE_DATED",
         "approved_scope": ("TARGET_A_SHARE",), "unsupported_scope": (), "known_gaps": ()},
        {"dataset": "daily_bar", "coverage_start": daily_start, "coverage_end": daily_end,
         "approval_id": "a-bar", "manifest_id": "m-bar", "completeness_mode": "MATERIALIZED_PANEL",
         "approved_scope": ("UNADJUSTED_RAW",), "unsupported_scope": (), "known_gaps": ()},
        {"dataset": "daily_security_status", "coverage_start": date(2010, 1, 4), "coverage_end": date(2026, 9, 10),
         "approval_id": "a-status", "manifest_id": "m-status", "completeness_mode": "MATERIALIZED_PANEL",
         "approved_scope": ("LISTING", "RISK_WARNING", "SUSPENSION", "IDENTITY"),
         "unsupported_scope": (), "known_gaps": ()},
        {"dataset": "corporate_action", "coverage_start": date(2010, 1, 4), "coverage_end": date(2026, 9, 9),
         "approval_id": "a-ca", "manifest_id": "m-ca", "completeness_mode": "SCOPED_ACTION_TYPES",
         "approved_scope": ("CASH_DIVIDEND", "BONUS_SHARE"),
         "unsupported_scope": ("RIGHTS_ISSUE", "STOCK_SPLIT", "SHARE_CONVERSION"), "known_gaps": ()},
        {"dataset": "financial_disclosure", "coverage_start": date(2010, 1, 4), "coverage_end": date(2026, 9, 10),
         "approval_id": "a-fin", "manifest_id": "m-fin", "completeness_mode": "OBSERVED_FACTS_ONLY",
         "approved_scope": ("revenue",), "unsupported_scope": ("forecast",),
         "known_gaps": ("HISTORICAL_PANEL_COMPLETENESS_PARTIAL",)},
    ))


def test_cutoff_requires_approved_open_session_and_same_shanghai_day():
    with pytest.raises(ExitContractError, match="approved open session"):
        HistoricalResearchCutoffContractV1.create(
            session=SESSION, cutoff=datetime(2025, 6, 30, 16, 30, tzinfo=SHANGHAI),
            timezone_name="Asia/Shanghai", calendar_approval_id="a", approved_open_sessions=())
    with pytest.raises(ExitContractError, match="session context"):
        HistoricalResearchCutoffContractV1.create(
            session=SESSION, cutoff=datetime(2025, 7, 1, 0, 1, tzinfo=SHANGHAI),
            timezone_name="Asia/Shanghai", calendar_approval_id="a", approved_open_sessions=(SESSION,))


def test_cutoff_is_content_addressed_and_rejects_naive_time():
    assert cutoff() == cutoff()
    assert cutoff().verify()
    with pytest.raises(ExitContractError, match="timezone-aware"):
        HistoricalResearchCutoffContractV1.create(
            session=SESSION, cutoff=datetime(2025, 6, 30, 16, 30),
            timezone_name="Asia/Shanghai", calendar_approval_id="a", approved_open_sessions=(SESSION,))


def test_coverage_matrix_preserves_observed_fact_and_unsupported_action_scope():
    item = matrix()
    assert item.entry("financial_disclosure").completeness_mode == "OBSERVED_FACTS_ONLY"
    assert "HISTORICAL_PANEL_COMPLETENESS_PARTIAL" in item.entry("financial_disclosure").known_gaps
    assert item.entry("corporate_action").unsupported_scope == (
        "RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT")
    assert item.verify()


def test_required_base_coverage_gap_is_session_fatal():
    result = HistoricalResearchSessionV1.evaluate(
        cutoff_contract=cutoff(), coverage_matrix=matrix(daily_end=date(2024, 12, 31)),
        base_universe=("000001.SZ",), lineage_valid=True,
        base_availability={"security_master": ("000001.SZ",), "daily_bar": ("000001.SZ",),
                           "daily_security_status": ("000001.SZ",)})
    assert not result.session_valid
    assert result.reason_histogram == (("OUTSIDE_APPROVED_COVERAGE", 1),)
    assert result.base_eligible_count == 0


def test_manifest_failure_is_session_fatal_not_security_missing():
    result = HistoricalResearchSessionV1.evaluate(
        cutoff_contract=cutoff(), coverage_matrix=matrix(), base_universe=("000001.SZ",),
        lineage_valid=False, fatal_reason="MANIFEST_INVALID", base_availability={})
    assert not result.session_valid
    assert result.reason_histogram == (("MANIFEST_INVALID", 1),)


def test_optional_financial_failure_blocks_only_affected_requirement():
    common = dict(cutoff_contract=cutoff(), coverage_matrix=matrix(),
        base_universe=("000001.SZ", "000002.SZ"), lineage_valid=True,
        base_availability={"security_master": ("000001.SZ", "000002.SZ"),
                           "daily_bar": ("000001.SZ", "000002.SZ"),
                           "daily_security_status": ("000001.SZ", "000002.SZ")})
    base = HistoricalResearchSessionV1.evaluate(**common)
    required = HistoricalResearchSessionV1.evaluate(**common,
        required_financial_metrics=("revenue",),
        financial_unsafe={("000002.SZ", "revenue"): "FINANCIAL_FACT_UNAVAILABLE"})
    assert base.session_valid and base.base_eligible_count == 2
    assert required.session_valid and required.base_eligible_count == 2
    assert required.blocked_security_count == 1
    assert ("000002.SZ", "financial:revenue", "NOT_RESEARCH_SAFE", "FINANCIAL_FACT_UNAVAILABLE") in required.security_dataset_eligibility


def test_unsupported_optional_scopes_are_security_level_fail_closed():
    result = HistoricalResearchSessionV1.evaluate(
        cutoff_contract=cutoff(), coverage_matrix=matrix(), base_universe=("000001.SZ",), lineage_valid=True,
        base_availability={"security_master": ("000001.SZ",), "daily_bar": ("000001.SZ",),
                           "daily_security_status": ("000001.SZ",)},
        requires_corporate_action_safe=True,
        corporate_action_unsafe={"000001.SZ": "CORPORATE_ACTION_UNSUPPORTED"},
        required_financial_metrics=("not_approved",))
    assert result.session_valid
    assert result.blocked_security_count == 1
    assert dict(result.reason_histogram) == {
        "CORPORATE_ACTION_UNSUPPORTED": 1, "FINANCIAL_METRIC_UNSUPPORTED": 1}


def test_pit_status_value_blocks_security_without_invalidating_session():
    result = HistoricalResearchSessionV1.evaluate(
        cutoff_contract=cutoff(), coverage_matrix=matrix(), base_universe=("000001.SZ",),
        lineage_valid=True, base_availability={"security_master": ("000001.SZ",),
            "daily_bar": ("000001.SZ",), "daily_security_status": ("000001.SZ",)},
        base_ineligible={"000001.SZ": "RISK_WARNING"})
    assert result.session_valid
    assert result.base_eligible_count == 0
    assert result.blocked_security_count == 1
    assert ("000001.SZ", "daily_security_status", "NOT_RESEARCH_SAFE", "RISK_WARNING") in result.security_dataset_eligibility


def test_session_result_and_exit_acceptance_replay_deterministically():
    kwargs = dict(cutoff_contract=cutoff(), coverage_matrix=matrix(),
        base_universe=("000002.SZ", "000001.SZ"), lineage_valid=True,
        base_availability={"security_master": ("000001.SZ", "000002.SZ"),
                           "daily_bar": ("000002.SZ", "000001.SZ"),
                           "daily_security_status": ("000001.SZ", "000002.SZ")})
    first = HistoricalResearchSessionV1.evaluate(**kwargs)
    second = HistoricalResearchSessionV1.evaluate(**kwargs)
    assert first.session_result_hash == second.session_result_hash
    acceptance = Phase1BExitAcceptanceV1.create(repository_head="head",
        cutoff_contract_id=cutoff().contract_id, coverage_matrix_id=matrix().coverage_matrix_id,
        dataset_approval_ids=("a",), dataset_manifest_ids=("m",), dry_run_ids=(first.session_result_hash,),
        chaos_test_evidence_id="chaos", deterministic_replay_id="replay",
        gate_results=(("STRUCTURAL", "PASS"),), known_limitations=("scope",))
    assert acceptance.verify()
    object.__setattr__(acceptance, "repository_head", "tampered")
    assert not acceptance.verify()
