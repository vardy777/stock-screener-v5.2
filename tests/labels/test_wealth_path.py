from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1, KnowledgeClass
from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.labels.calculation import CorporateActionCoverageV1, UnsafeLabelInput, build_economic_wealth_path
from v5_2.labels.contracts import LabelReasonCode, LabelReferencePrice


NOW = datetime(2024, 1, 10, tzinfo=timezone.utc)


def bar(day, o, h, l, c):
    return DailyBarFactV1.create(source_symbol="000001.SZ", session=day, open=Decimal(o), high=Decimal(h), low=Decimal(l), close=Decimal(c), raw_volume=Decimal("1"), raw_amount=Decimal("1"), source_payload_hash="p", available_at=NOW, availability_policy_version="v1")


def action(kind, day, *, cash=None, ratio=None):
    return CorporateActionFactV1.create(security_identity="000001.SZ", action_type=kind, knowledge_class=KnowledgeClass.KNOWN_IN_ADVANCE, published_at=NOW, available_at=NOW, ex_date=day, effective_date=day, cash_per_share=Decimal(cash) if cash else None, share_ratio=Decimal(ratio) if ratio else None, source_fact_id=f"{kind}-{day}", source_version_identity="v", revision_marker="1", supersedes_source_fact_id=None, is_cancelled=False)


def reference():
    return LabelReferencePrice.create(date(2024, 1, 2), Decimal("10"), "a" * 64, NOW)


def test_no_action_wealth_equals_raw_price():
    bars = (bar(date(2024, 1, 3), "10", "11", "9", "10.5"),)
    path = build_economic_wealth_path(reference(), (date(2024, 1, 3),), bars, (), CorporateActionCoverageV1.safe())
    assert (path.points[0].shares, path.points[0].cash, path.points[0].close_wealth) == (Decimal("1"), Decimal("0"), Decimal("10.5"))


def test_cash_then_bonus_uses_pre_bonus_shares_and_economic_prices():
    day = date(2024, 1, 3)
    bars = (bar(day, "5", "5.5", "4.5", "5"),)
    actions = (action(ActionType.CASH_DIVIDEND, day, cash="1"), action(ActionType.BONUS_SHARE, day, ratio="1"))
    point = build_economic_wealth_path(reference(), (day,), bars, actions, CorporateActionCoverageV1.safe()).points[0]
    assert (point.shares, point.cash, point.close_wealth) == (Decimal("2"), Decimal("1"), Decimal("11"))


@pytest.mark.parametrize("coverage, reason", [
    (CorporateActionCoverageV1(covered=False), LabelReasonCode.CORPORATE_ACTION_COVERAGE_GAP),
    (CorporateActionCoverageV1(quarantined=True), LabelReasonCode.CORPORATE_ACTION_QUARANTINE),
    (CorporateActionCoverageV1(revision_valid=False), LabelReasonCode.CORPORATE_ACTION_REVISION_INVALID),
])
def test_bad_coverage_fails_closed(coverage, reason):
    with pytest.raises(UnsafeLabelInput) as error:
        build_economic_wealth_path(reference(), (date(2024, 1, 3),), (), (), coverage)
    assert error.value.reason is reason


def test_unsupported_action_fails_closed():
    day = date(2024, 1, 3)
    with pytest.raises(UnsafeLabelInput) as error:
        build_economic_wealth_path(reference(), (day,), (bar(day, "10", "10", "10", "10"),), (action(ActionType.RIGHTS_ISSUE, day),), CorporateActionCoverageV1.safe())
    assert error.value.reason is LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION


def test_adjusted_bar_is_rejected():
    item = bar(date(2024, 1, 3), "10", "10", "10", "10")
    object.__setattr__(item, "price_basis", "FORWARD_ADJUSTED")
    with pytest.raises(UnsafeLabelInput):
        build_economic_wealth_path(reference(), (item.session,), (item,), (), CorporateActionCoverageV1.safe())
