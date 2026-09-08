import pytest

from v5_2.data.real_audits.historical_universe import (
    NeverConfirmedTradableExclusionV1, reconcile_historical_universe,
)


def test_reconciliation_classifies_target_non_target_outside_and_alias() -> None:
    result = reconcile_historical_universe(
        observed_symbols=("600747.SH", "832317.BJ", "600001.SH", "302132.SZ"),
        original_symbols=("300114.SZ",),
        master_rows={
            "600747.SH": {"exchange": "SSE", "symbol": "600747", "market": "主板", "list_status": "D", "list_date": "19960916", "delist_date": "20191212", "ts_code": "600747.SH"},
            "832317.BJ": {"exchange": "BSE", "symbol": "832317", "market": "北交所", "list_status": "D", "list_date": "20200727", "delist_date": "20220426", "ts_code": "832317.BJ"},
            "600001.SH": {"exchange": "SSE", "symbol": "600001", "market": "主板", "list_status": "D", "list_date": "19900101", "delist_date": "20090101", "ts_code": "600001.SH"},
            "302132.SZ": {"exchange": "SZSE", "symbol": "302132", "market": "主板", "list_status": "L", "list_date": "20250217", "delist_date": None, "ts_code": "302132.SZ"},
        },
        aliases={"302132.SZ": "300114.SZ"}, coverage_start="20100104", coverage_end="20251231",
        original_universe_id="u", official_evidence={"600747.SH": ("sse-600747",)},
    )
    assert dict(result.counts) == {"IDENTITY_ALIAS": 1, "NON_TARGET": 1,
                                   "OUTSIDE_RESEARCH_COVERAGE": 1, "TARGET_A_SHARE_REQUIRED": 1}
    assert result.supplement.identities[0].security_identity == "600747.SH"
    assert result.supplement.original_universe_id == "u"
    assert result.supplement.content_hash


def test_evidence_backed_resolution_override_records_interval_and_research_impact() -> None:
    result = reconcile_historical_universe(
        observed_symbols=("430017.BJ",), original_symbols=(), master_rows={}, aliases={},
        coverage_start="20100104", coverage_end="20251231", original_universe_id="u",
        official_evidence={}, resolution_overrides={"430017.BJ": {
            "category": "NON_TARGET", "effective_from": "20211115", "effective_to": None,
            "evidence_ids": ("bse-identity-430017",),
            "research_scope_impact": "BSE excluded from SSE/SZSE A-share scope",
        }},
    )
    item = result.items[0]
    assert item.category == "NON_TARGET"
    assert item.evidence_ids == ("bse-identity-430017",)
    assert item.research_scope_impact.startswith("BSE excluded")


def test_planned_listing_without_trading_proof_is_explicitly_excluded_not_deleted() -> None:
    exclusion = NeverConfirmedTradableExclusionV1.create(
        security_identity="002525.SZ", observed_source_record_ids=("namechange-row",),
        absence_of_trading_evidence_ids=("approved-daily-bar-inventory",),
        has_approved_daily_bar=False, has_verified_trading_session=False,
        has_reliable_tradability_proof=False,
        reason="code allocated for planned listing but actual tradable listing was never confirmed",
    )
    assert exclusion.classification == "NEVER_CONFIRMED_TRADABLE"
    assert exclusion.research_eligible is False
    assert exclusion.survivorship_blocking is False
    assert exclusion.content_hash


def test_never_confirmed_rule_rejects_any_actual_trading_proof() -> None:
    with pytest.raises(ValueError, match="cannot exclude"):
        NeverConfirmedTradableExclusionV1.create(
            security_identity="002525.SZ", observed_source_record_ids=("row",),
            absence_of_trading_evidence_ids=("bars",), has_approved_daily_bar=True,
            has_verified_trading_session=False, has_reliable_tradability_proof=False,
            reason="planned listing",
        )
