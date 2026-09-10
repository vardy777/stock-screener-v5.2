from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1, KnowledgeClass
from v5_2.data.corporate_action_repository import CorporateActionRepository, NotResearchSafeError


CN = timezone(timedelta(hours=8), "Asia/Shanghai")


def fact(source_id, available_day, *, supersedes=None, cancelled=False):
    return CorporateActionFactV1.create(
        security_identity="600000.SH", action_type=ActionType.CASH_DIVIDEND,
        knowledge_class=KnowledgeClass.KNOWN_IN_ADVANCE, published_at=None,
        available_at=datetime(available_day, 6, 4, 16, 30, tzinfo=CN),
        ex_date=date(2024, 6, 10), effective_date=date(2024, 6, 10),
        cash_per_share=Decimal("0.3"), share_ratio=None, source_fact_id=source_id,
        source_version_identity="schema-v1", revision_marker="cancel" if cancelled else "implementation",
        supersedes_source_fact_id=supersedes, is_cancelled=cancelled)


def repository(facts):
    return CorporateActionRepository(
        facts=facts, supported_action_types=(ActionType.CASH_DIVIDEND,),
        validated_coverage=((ActionType.CASH_DIVIDEND, date(2024, 1, 1), date(2024, 12, 31)),),
        materialized_coverage=((ActionType.CASH_DIVIDEND, date(2024, 1, 1), date(2024, 12, 31)),),
        quarantined_security_periods=(), approval_valid=True, manifest_valid=True)


def test_cutoff_resolves_latest_then_known_revision_and_cancellation():
    original = fact("v1", 2024)
    cancelled = fact("v2", 2025, supersedes="v1", cancelled=True)
    repo = repository((original, cancelled))
    assert repo.query("600000.SH", date(2024, 6, 1), date(2024, 6, 30), ActionType.CASH_DIVIDEND,
                      datetime(2024, 12, 31, tzinfo=CN)) == (original,)
    assert repo.query("600000.SH", date(2024, 6, 1), date(2024, 6, 30), ActionType.CASH_DIVIDEND,
                      datetime(2025, 12, 31, tzinfo=CN)) == ()


def test_uncovered_or_unsupported_query_is_not_research_safe():
    repo = repository(())
    with pytest.raises(NotResearchSafeError, match="NOT_RESEARCH_SAFE"):
        repo.query("600000.SH", date(2023, 1, 1), date(2023, 1, 31), ActionType.CASH_DIVIDEND,
                   datetime(2025, 1, 1, tzinfo=CN))
    with pytest.raises(NotResearchSafeError, match="NOT_RESEARCH_SAFE"):
        repo.query("600000.SH", date(2024, 1, 1), date(2024, 1, 31), ActionType.RIGHTS_ISSUE,
                   datetime(2025, 1, 1, tzinfo=CN))


def test_invalid_approval_or_manifest_fails_closed():
    repo = CorporateActionRepository(facts=(), supported_action_types=(ActionType.CASH_DIVIDEND,),
        validated_coverage=((ActionType.CASH_DIVIDEND, date(2024, 1, 1), date(2024, 12, 31)),),
        materialized_coverage=((ActionType.CASH_DIVIDEND, date(2024, 1, 1), date(2024, 12, 31)),),
        quarantined_security_periods=(), approval_valid=False, manifest_valid=True)
    with pytest.raises(NotResearchSafeError):
        repo.query("600000.SH", date(2024, 1, 1), date(2024, 1, 31), ActionType.CASH_DIVIDEND,
                   datetime(2025, 1, 1, tzinfo=CN))
