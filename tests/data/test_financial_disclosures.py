from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from v5_2.data.financial_disclosure_facts import (
    FinancialDisclosureFactV1, ReportType, ReportedValueSemantics,
    StatementType,
)
from v5_2.data.financial_disclosure_repository import (
    FinancialDisclosureRepository, NotResearchSafeError,
)
from v5_2.data.real_audits.financial_disclosure_availability import (
    FinancialDisclosureAvailabilityPolicyV1,
)

UTC = timezone.utc
SESSIONS = (date(2024, 4, 1), date(2024, 4, 2), date(2024, 6, 3))


def fact(*, value="100", published=date(2024, 4, 1), marker="0", supersedes=None):
    available = FinancialDisclosureAvailabilityPolicyV1(SESSIONS).date_only(published)
    return FinancialDisclosureFactV1.create(
        security_identity="600000.SH", statement_type=StatementType.INCOME,
        metric="revenue", period_end=date(2023, 12, 31), report_type=ReportType.ANNUAL,
        published_at=published, available_at=available, value=Decimal(value), unit="CNY",
        currency="CNY", reported_value_semantics=ReportedValueSemantics.PERIOD_CUMULATIVE,
        source_fact_id=f"provider-{marker}", source_version_identity="payload-v1",
        revision_marker=marker, supersedes_source_fact_id=supersedes,
        announcement_date=published, update_flag=marker, statement_scope="CONSOLIDATED")


def test_period_end_never_makes_a_fact_available_before_publication():
    item = fact()
    assert item.period_end == date(2023, 12, 31)
    assert item.available_at == datetime(2024, 4, 2, 16, 30, tzinfo=item.available_at.tzinfo)
    assert item.available_at > datetime(2024, 2, 1, tzinfo=item.available_at.tzinfo)


def test_statement_value_semantics_are_enforced():
    values = dict(fact().__dict__) if hasattr(fact(), "__dict__") else None
    assert values is None  # slots keep facts immutable and compact
    with pytest.raises(ValueError, match="semantics"):
        FinancialDisclosureFactV1.create(
            security_identity="600000.SH", statement_type=StatementType.BALANCE_SHEET,
            metric="total_assets", period_end=date(2023, 12, 31), report_type=ReportType.ANNUAL,
            published_at=date(2024, 4, 1), available_at=FinancialDisclosureAvailabilityPolicyV1(SESSIONS).date_only(date(2024, 4, 1)),
            value=Decimal("1"), unit="CNY", currency="CNY",
            reported_value_semantics=ReportedValueSemantics.PERIOD_CUMULATIVE,
            source_fact_id="x", source_version_identity="v", revision_marker="0",
            supersedes_source_fact_id=None, announcement_date=date(2024, 4, 1), update_flag="0",
            statement_scope="CONSOLIDATED")


def test_revision_is_visible_only_after_its_own_availability():
    original = fact()
    revision = fact(value="120", published=date(2024, 6, 2), marker="1", supersedes="provider-0")
    repo = FinancialDisclosureRepository(
        facts=(original, revision), supported_statement_types=(StatementType.INCOME,),
        supported_metrics=("revenue",), validated_coverage=((StatementType.INCOME, date(2010, 1, 4), date(2024, 12, 31)),),
        quarantined_keys=(), approval_valid=True, manifest_valid=True)
    assert repo.query("600000.SH", "revenue", date(2023, 12, 31), datetime(2024, 5, 1, tzinfo=UTC)).value == Decimal("100")
    assert repo.query("600000.SH", "revenue", date(2023, 12, 31), datetime(2024, 7, 1, tzinfo=UTC)).value == Decimal("120")


@pytest.mark.parametrize("approval,manifest", [(False, True), (True, False)])
def test_repository_fails_closed_on_invalid_lineage(approval, manifest):
    repo = FinancialDisclosureRepository(facts=(fact(),), supported_statement_types=(StatementType.INCOME,),
        supported_metrics=("revenue",), validated_coverage=((StatementType.INCOME, date(2010, 1, 4), date(2024, 12, 31)),),
        quarantined_keys=(), approval_valid=approval, manifest_valid=manifest)
    with pytest.raises(NotResearchSafeError):
        repo.query("600000.SH", "revenue", date(2023, 12, 31), datetime(2024, 7, 1, tzinfo=UTC))


def test_repository_never_returns_zero_for_missing_or_quarantined_fact():
    repo = FinancialDisclosureRepository(facts=(fact(),), supported_statement_types=(StatementType.INCOME,),
        supported_metrics=("revenue",), validated_coverage=((StatementType.INCOME, date(2010, 1, 4), date(2024, 12, 31)),),
        quarantined_keys=(("600000.SH", "revenue", date(2023, 12, 31)),), approval_valid=True, manifest_valid=True)
    with pytest.raises(NotResearchSafeError):
        repo.query("600000.SH", "revenue", date(2023, 12, 31), datetime(2024, 7, 1, tzinfo=UTC))


def test_source_identity_distinguishes_revisions_and_verifies_integrity():
    first, second = fact(), fact(value="120", published=date(2024, 6, 2), marker="1", supersedes="provider-0")
    assert first.fact_id != second.fact_id
    assert first.verify() and second.verify()
