from datetime import date
from decimal import Decimal

from v5_2.data.financial_disclosure_facts import ReportedValueSemantics, StatementType
from v5_2.data.real_audits.financial_disclosure_availability import FinancialDisclosureAvailabilityPolicyV1
from v5_2.data.real_audits.financial_disclosure_normalization import (
    financial_fact_equivalence_key,
    normalize_statement_rows,
)


SESSIONS = tuple(date(2024, 4, day) for day in (1, 2, 3, 29, 30)) + (date(2024, 5, 6),)


def row(**updates):
    value = {"ts_code": "600000.SH", "ann_date": "20240401", "f_ann_date": "20240401",
             "end_date": "20231231", "report_type": "1", "comp_type": "2", "end_type": "4",
             "revenue": 100, "n_income_attr_p": 10, "update_flag": "0"}
    value.update(updates); return value


def test_normalization_preserves_explicit_report_and_unit_semantics():
    result = normalize_statement_rows("financial_income", (row(),), source_version_identity="payload",
                                      policy=FinancialDisclosureAvailabilityPolicyV1(SESSIONS))
    assert {fact.metric for fact in result.facts} == {"revenue", "n_income_attr_p"}
    assert all(fact.report_type.value == "ANNUAL" for fact in result.facts)
    assert all(fact.reported_value_semantics is ReportedValueSemantics.PERIOD_CUMULATIVE for fact in result.facts)
    assert all(fact.unit == fact.currency == "CNY" for fact in result.facts)


def test_equivalent_update_flag_duplicates_collapse_deterministically():
    result = normalize_statement_rows("financial_income", (row(), row(update_flag="1")),
        source_version_identity="payload", policy=FinancialDisclosureAvailabilityPolicyV1(SESSIONS))
    assert len(result.facts) == 2
    assert result.quarantines == ()
    assert all(fact.update_flag == "1" for fact in result.facts)


def test_equivalent_fact_reacquired_in_another_payload_has_one_publication_key():
    policy = FinancialDisclosureAvailabilityPolicyV1(SESSIONS)
    first = normalize_statement_rows("financial_income", (row(),), source_version_identity="payload-a", policy=policy)
    second = normalize_statement_rows("financial_income", (row(),), source_version_identity="payload-b", policy=policy)
    assert first.facts[0].fact_id != second.facts[0].fact_id
    assert financial_fact_equivalence_key(first.facts[0]) == financial_fact_equivalence_key(second.facts[0])


def test_conflicting_cross_payload_value_is_not_equivalent():
    policy = FinancialDisclosureAvailabilityPolicyV1(SESSIONS)
    first = normalize_statement_rows("financial_income", (row(),), source_version_identity="payload-a", policy=policy)
    second = normalize_statement_rows("financial_income", (row(revenue=120),), source_version_identity="payload-b", policy=policy)
    first_revenue = next(fact for fact in first.facts if fact.metric == "revenue")
    second_revenue = next(fact for fact in second.facts if fact.metric == "revenue")
    assert financial_fact_equivalence_key(first_revenue) != financial_fact_equivalence_key(second_revenue)


def test_same_publication_conflict_is_quarantined_not_arbitrarily_selected():
    result = normalize_statement_rows("financial_income", (row(), row(update_flag="1", revenue=120)),
        source_version_identity="payload", policy=FinancialDisclosureAvailabilityPolicyV1(SESSIONS))
    assert "revenue" not in {fact.metric for fact in result.facts}
    assert result.quarantines[0]["reason"] == "CONFLICTING_VERSION_WITHOUT_TEMPORAL_ORDER"


def test_later_publication_creates_explicit_supersession_lineage():
    result = normalize_statement_rows("financial_income", (row(), row(ann_date="20240429", f_ann_date="20240429", update_flag="1", revenue=120)),
        source_version_identity="payload", policy=FinancialDisclosureAvailabilityPolicyV1(SESSIONS))
    revenue = sorted((fact for fact in result.facts if fact.metric == "revenue"), key=lambda fact: fact.available_at)
    assert [fact.value for fact in revenue] == [Decimal("100"), Decimal("120")]
    assert revenue[1].supersedes_source_fact_id == revenue[0].source_fact_id


def test_unsupported_scope_and_null_values_are_machine_visible():
    result = normalize_statement_rows("financial_income", (row(report_type="6"), row(revenue=None)),
        source_version_identity="payload", policy=FinancialDisclosureAvailabilityPolicyV1(SESSIONS))
    assert any(item["reason"] == "UNSUPPORTED_STATEMENT_SCOPE" for item in result.quarantines)
    assert any(item["reason"] == "MISSING_METRIC_VALUE" for item in result.quarantines)
