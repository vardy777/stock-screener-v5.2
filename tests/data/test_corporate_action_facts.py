from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from v5_2.data.corporate_action_facts import (
    ActionType,
    CorporateActionFactError,
    CorporateActionFactV1,
    KnowledgeClass,
)


CN = timezone(timedelta(hours=8), "Asia/Shanghai")


def make_fact(**overrides):
    values = dict(
        security_identity="600000.SH",
        action_type=ActionType.CASH_DIVIDEND,
        knowledge_class=KnowledgeClass.KNOWN_IN_ADVANCE,
        published_at=datetime(2024, 6, 3, 18, 0, tzinfo=CN),
        available_at=datetime(2024, 6, 4, 16, 30, tzinfo=CN),
        ex_date=date(2024, 6, 10),
        effective_date=date(2024, 6, 10),
        cash_per_share=Decimal("0.30"),
        share_ratio=None,
        source_fact_id="provider-row-v1",
        source_version_identity="datahub-dividend-schema-v1",
        revision_marker="implementation",
        supersedes_source_fact_id=None,
        is_cancelled=False,
    )
    values.update(overrides)
    return CorporateActionFactV1.create(**values)


def test_fact_identity_is_deterministic_and_tamper_evident():
    left = make_fact()
    right = make_fact()
    assert left == right
    assert left.verify()
    assert not replace(left, cash_per_share=Decimal("0.31")).verify()


def test_fact_keeps_cash_and_share_economics_distinct():
    fact = make_fact(
        action_type=ActionType.BONUS_SHARE,
        cash_per_share=None,
        share_ratio=Decimal("0.20"),
    )
    assert fact.cash_per_share is None
    assert fact.share_ratio == Decimal("0.20")


def test_revision_and_cancellation_are_new_immutable_versions():
    original = make_fact()
    cancelled = make_fact(
        source_fact_id="provider-row-v2",
        revision_marker="cancelled",
        supersedes_source_fact_id=original.source_fact_id,
        is_cancelled=True,
    )
    assert cancelled.fact_id != original.fact_id
    assert cancelled.supersedes_source_fact_id == "provider-row-v1"
    assert cancelled.is_cancelled


def test_fact_rejects_naive_times_and_negative_economics():
    with pytest.raises(CorporateActionFactError, match="timezone"):
        make_fact(available_at=datetime(2024, 6, 4, 16, 30))
    with pytest.raises(CorporateActionFactError, match="non-negative"):
        make_fact(cash_per_share=Decimal("-0.01"))


def test_fact_requires_an_economic_date_and_type_specific_value():
    with pytest.raises(CorporateActionFactError, match="economic date"):
        make_fact(ex_date=None, effective_date=None)
    with pytest.raises(CorporateActionFactError, match="cash_per_share"):
        make_fact(cash_per_share=None)
