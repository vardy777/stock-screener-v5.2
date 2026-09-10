from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1, KnowledgeClass
from v5_2.data.real_audits.corporate_action_adjustment import (
    AdjustmentSemanticsError,
    CausalCorporateActionAdjustmentPolicyV1,
)


CN = timezone(timedelta(hours=8), "Asia/Shanghai")


def make_fact(kind, value, available):
    return CorporateActionFactV1.create(
        security_identity="600000.SH", action_type=kind, knowledge_class=KnowledgeClass.KNOWN_IN_ADVANCE,
        published_at=None, available_at=available, ex_date=date(2024, 6, 10), effective_date=date(2024, 6, 10),
        cash_per_share=value if kind is ActionType.CASH_DIVIDEND else None,
        share_ratio=value if kind is ActionType.BONUS_SHARE else None,
        source_fact_id=f"{kind}-v1", source_version_identity="schema-v1", revision_marker="implementation",
        supersedes_source_fact_id=None, is_cancelled=False)


def test_effects_are_visible_only_when_effective_and_known_and_raw_bar_is_unchanged():
    bar = {"close": Decimal("10.0"), "adjustment": "UNADJUSTED_RAW"}
    fact = make_fact(ActionType.CASH_DIVIDEND, Decimal("0.3"), datetime(2024, 6, 4, 16, 30, tzinfo=CN))
    policy = CausalCorporateActionAdjustmentPolicyV1()
    before = policy.effects_for_bar(bar=bar, session=date(2024, 6, 7), as_of=datetime(2024, 6, 7, 16, 30, tzinfo=CN), facts=(fact,))
    effective = policy.effects_for_bar(bar=bar, session=date(2024, 6, 10), as_of=datetime(2024, 6, 10, 16, 30, tzinfo=CN), facts=(fact,))
    assert before == ()
    assert effective[0].cash_per_share == Decimal("0.3")
    assert bar == {"close": Decimal("10.0"), "adjustment": "UNADJUSTED_RAW"}


def test_final_adjusted_input_is_rejected():
    with pytest.raises(AdjustmentSemanticsError, match="UNADJUSTED_RAW"):
        CausalCorporateActionAdjustmentPolicyV1().effects_for_bar(
            bar={"close": 10, "adjustment": "qfq"}, session=date(2024, 6, 10),
            as_of=datetime(2024, 6, 10, 16, 30, tzinfo=CN), facts=())
