from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from v5_2.data.real_audits.identity_lineage import EffectiveDatedSecurityIdentityV1, IdentityIntervalV1
from v5_2.data.real_audits.security_master_governance import (
    ApprovalWithCoverageRulesV1,
    CombinedUpstreamGateV1,
    QuarantineCoverageRuleV1,
    SecurityMasterOfficialSampleInventoryV1,
    select_frozen_security_samples,
)


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _sample(sample_id: str, code: str = "000001.SZ"):
    return {
        "sample_id": sample_id, "ts_code": code, "effective_identity": code,
        "exchange": "SZSE", "sample_stratum": "SZ_main",
        "fields_requiring_verification": ("symbol", "exchange", "listing_date", "delisting_date", "board"),
    }


def test_official_inventory_is_exact_and_replacement_is_prohibited() -> None:
    inventory = SecurityMasterOfficialSampleInventoryV1.create(
        frozen_samples=(_sample("a"), _sample("b", "300001.SZ")),
        official_evidence={"a": {"resolution": "VERIFIED", "evidence_id": "official-a", "official_source_identity": "szse", "official_values": {"symbol": "000001"}}},
        verified_at=NOW, policy_id="frozen-policy", policy_version="official-sample-v1",
    )
    assert (inventory.total, inventory.verified, inventory.mismatch, inventory.unresolved) == (2, 1, 0, 1)
    assert tuple(item["sample_id"] for item in inventory.records) == ("a", "b")
    assert inventory.records[0]["official_source_identity"] == "szse"
    assert inventory.records[0]["official_values"] == {"symbol": "000001"}
    with pytest.raises(ValueError, match="not in frozen"):
        SecurityMasterOfficialSampleInventoryV1.create(
            frozen_samples=(_sample("a"),),
            official_evidence={"replacement": {"resolution": "VERIFIED", "evidence_id": "x"}},
            verified_at=NOW, policy_id="frozen-policy", policy_version="official-sample-v1",
        )


def test_frozen_sample_selection_uses_four_exact_records_per_stratum() -> None:
    rows = []
    for index in range(4):
        rows.extend((
            {"ts_code": f"60010{index}.SH", "symbol": f"60010{index}", "exchange": "SSE", "market": "主板", "list_status": "L", "list_date": "19990101", "delist_date": None},
            {"ts_code": f"68810{index}.SH", "symbol": f"68810{index}", "exchange": "SSE", "market": "科创板", "list_status": "L", "list_date": "20240101", "delist_date": None},
            {"ts_code": f"00010{index}.SZ", "symbol": f"00010{index}", "exchange": "SZSE", "market": "主板", "list_status": "D", "list_date": "19980101", "delist_date": "20200101"},
            {"ts_code": f"30010{index}.SZ", "symbol": f"30010{index}", "exchange": "SZSE", "market": "创业板", "list_status": "L", "list_date": "20240201", "delist_date": None},
        ))
    selected = select_frozen_security_samples(rows, policy_id="frozen-policy")
    assert len(selected) == 32
    assert {item["sample_stratum"] for item in selected} == {
        "currently_listed", "recent_ipo", "old_ipo", "delisted",
        "SH_main", "SH_STAR", "SZ_main", "SZ_ChiNext",
    }
    assert all(sum(item["sample_stratum"] == stratum for item in selected) == 4 for stratum in {item["sample_stratum"] for item in selected})
    assert select_frozen_security_samples(tuple(reversed(rows)), policy_id="frozen-policy") == selected


def test_effective_dated_identity_is_preserved_in_official_inventory() -> None:
    graph = EffectiveDatedSecurityIdentityV1.create(
        provider_identity="302132.SZ",
        intervals=(
            IdentityIntervalV1("300114.SZ", date(2010, 8, 27), date(2025, 2, 16), "A_SHARE", "CHINEXT"),
            IdentityIntervalV1("302132.SZ", date(2025, 2, 17), None, "A_SHARE", "CHINEXT"),
        ), transition_event="SECURITY_CODE_CHANGE", transition_effective_at=date(2025, 2, 17),
        evidence_ids=("listing", "change"), policy_version="identity-v1",
    )
    item = _sample("a", "302132.SZ")
    item["effective_identity"] = graph.graph_id
    inventory = SecurityMasterOfficialSampleInventoryV1.create(
        frozen_samples=(item,), official_evidence={}, verified_at=NOW,
        policy_id="frozen-policy", policy_version="official-sample-v1",
    )
    assert inventory.records[0]["effective_identity"] == graph.graph_id


def test_quarantine_coverage_intersection_is_deterministic_and_pre_2010_fails_closed() -> None:
    rule = QuarantineCoverageRuleV1.create(
        quarantine_id="q", effective_from=date(2000, 7, 19), effective_to=date(2006, 10, 20),
        minimum_coverage_start=date(2010, 1, 1), policy_version="coverage-rule-v1",
    )
    assert rule.admits(date(2010, 1, 1), date(2025, 12, 31))
    assert not rule.admits(date(2006, 1, 1), date(2010, 1, 1))
    assert not rule.admits(date(2007, 1, 1), date(2009, 12, 31))


def test_approval_with_rules_pins_all_coverage_constraints() -> None:
    rule = QuarantineCoverageRuleV1.create(
        quarantine_id="q", effective_from=date(2000, 7, 19), effective_to=date(2006, 10, 20),
        minimum_coverage_start=date(2010, 1, 1), policy_version="coverage-rule-v1",
    )
    approval = ApprovalWithCoverageRulesV1.create(
        source_approval_id="approval", coverage_rule=rule, normalization_policy_id="normalization",
        identity_lineage_policy_id="identity", approval_policy_id="policy", approved_at=NOW,
    )
    assert approval.minimum_coverage_start == date(2010, 1, 1)
    assert approval.quarantine_id == "q"
    assert approval.coverage_rule_id == rule.rule_id


def test_daily_bar_gate_requires_two_valid_unrevoked_approvals() -> None:
    assert CombinedUpstreamGateV1.evaluate(
        trade_calendar_approval_id="calendar", trade_calendar_decision="APPROVED",
        security_master_approval_id="master", security_master_decision="APPROVED_WITH_RULES",
        revoked_approval_ids=(), evaluated_at=NOW,
    ).daily_bar_entry_unlocked
    assert not CombinedUpstreamGateV1.evaluate(
        trade_calendar_approval_id="calendar", trade_calendar_decision="APPROVED",
        security_master_approval_id="master", security_master_decision="APPROVED_WITH_RULES",
        revoked_approval_ids=("calendar",), evaluated_at=NOW,
    ).daily_bar_entry_unlocked
    assert not CombinedUpstreamGateV1.evaluate(
        trade_calendar_approval_id="calendar", trade_calendar_decision="PENDING",
        security_master_approval_id="master", security_master_decision="APPROVED_WITH_RULES",
        revoked_approval_ids=(), evaluated_at=NOW,
    ).daily_bar_entry_unlocked
