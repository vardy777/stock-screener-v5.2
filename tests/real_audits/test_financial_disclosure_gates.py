import pytest

from v5_2.data.real_audits.financial_disclosure_validation import (
    FinancialDisclosureGateEvidenceV1, evaluate_financial_disclosure_gates,
    authorize_financial_disclosure_publication, FinancialDisclosurePublicationError,
)


def evidence(**updates):
    values = dict(structural="PASS", pit="PASS", cross_source="PASS", revision="PASS",
        value_semantics="PASS", unit_semantics="PASS", historical_coverage="PASS",
        catch_up_2026="PASS", survivorship="PASS", rolling_coverage_model="PASS",
        production_incremental_readiness="PASS", exception_budget="PASS", systematic_defect="PASS",
        publication_scope="COMPLETE_DATASET",
        evidence_ids=("raw", "sample", "revision"))
    values.update(updates); return FinancialDisclosureGateEvidenceV1.create(**values)


def test_all_correctness_gates_are_required_for_scoped_approval():
    gate = evaluate_financial_disclosure_gates(evidence())
    assert gate.source_approval == "APPROVED_WITH_RULES"
    assert gate.publication_allowed
    assert authorize_financial_disclosure_publication(gate, evidence())


@pytest.mark.parametrize("field,status,decision", [
    ("pit", "PENDING", "PENDING"), ("cross_source", "PENDING", "PENDING"),
    ("revision", "FAIL", "REJECTED"), ("historical_coverage", "PARTIAL", "PENDING"),
    ("systematic_defect", "FAIL", "REJECTED"),
])
def test_any_non_pass_gate_disables_publication(field, status, decision):
    gate = evaluate_financial_disclosure_gates(evidence(**{field: status}))
    assert gate.source_approval == decision
    assert not gate.publication_allowed
    with pytest.raises(FinancialDisclosurePublicationError):
        authorize_financial_disclosure_publication(gate, evidence(**{field: status}))


def test_partial_history_can_only_publish_as_observed_fact_scope():
    gate = evaluate_financial_disclosure_gates(evidence(
        historical_coverage="PARTIAL", publication_scope="OBSERVED_FACTS_ONLY"))
    assert gate.source_approval == "APPROVED_WITH_RULES"
    assert gate.publication_allowed


def test_unknown_publication_scope_fails_closed():
    gate = evaluate_financial_disclosure_gates(evidence(publication_scope="UNKNOWN"))
    assert gate.source_approval == "PENDING"
    assert not gate.publication_allowed


def test_tampered_evidence_fails_closed():
    item = evidence(); object.__setattr__(item, "pit", "FAIL")
    gate = evaluate_financial_disclosure_gates(item)
    assert gate.source_approval == "REJECTED"
    assert not gate.publication_allowed
