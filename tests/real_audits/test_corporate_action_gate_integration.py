from dataclasses import replace
from datetime import date

from v5_2.data.corporate_action_facts import ActionType
from v5_2.data.real_audits.corporate_action_evidence import CorporateActionPITEvidenceV1
from v5_2.data.real_audits.corporate_action_validation import (
    CorporateActionPublicationError,
    authorize_corporate_action_publication,
    evaluate_corporate_action_gates,
    gate_artifact_id,
)
import pytest


def evidence(complete=True):
    unsupported = (ActionType.RIGHTS_ISSUE, ActionType.STOCK_SPLIT, ActionType.SHARE_CONVERSION)
    return CorporateActionPITEvidenceV1.create(
        target_history_start=date(2010,1,4), baseline_validation_end=date(2025,12,31), rolling_coverage_end=date(2026,9,9),
        source_name="datahubco_tushare_proxy", source_version_identity="schema-v1",
        supported_action_types=(ActionType.CASH_DIVIDEND, ActionType.BONUS_SHARE), unsupported_action_types=unsupported,
        validated_coverage_by_action_type=((ActionType.CASH_DIVIDEND,date(2024,1,1),date(2026,9,9)),(ActionType.BONUS_SHARE,date(2024,1,1),date(2026,9,9))),
        materialized_coverage_by_action_type=((ActionType.CASH_DIVIDEND,date(2024,1,1),date(2026,9,9)),(ActionType.BONUS_SHARE,date(2024,1,1),date(2026,9,9))),
        coverage_gaps=((date(2010,1,4),date(2023,12,31),"pending"),),
        unsupported_intervals=tuple((kind,date(2010,1,4),date(2026,9,9)) for kind in unsupported),
        cross_source_evidence_ids=("official",), exception_ids=(), quarantine_ids=("unsupported-types",),
        publication_rule="date-only-next-session-1630", economic_effect_rule="ex-date",
        revision_rule="latest-known-version", cancellation_rule="cancelled-no-effect", complete=complete)


def test_all_scoped_gates_pass_allows_approval_with_rules():
    result = evaluate_corporate_action_gates(
        evidence(), cross_source="PASS", revision="PASS", adjustment="PASS",
        catch_up="PASS", incremental="PASS", exception_budget="PASS", systematic_defect="PASS")
    assert result.source_approval == "APPROVED_WITH_RULES"
    assert result.publication_allowed


def test_incomplete_or_tampered_evidence_fails_closed():
    pending = evaluate_corporate_action_gates(
        evidence(False), cross_source="PASS", revision="PASS", adjustment="PASS",
        catch_up="PARTIAL", incremental="PASS", exception_budget="PASS", systematic_defect="PASS")
    tampered = evaluate_corporate_action_gates(
        replace(evidence(), source_version_identity="tampered"), cross_source="PASS", revision="PASS",
        adjustment="PASS", catch_up="PASS", incremental="PASS", exception_budget="PASS", systematic_defect="PASS")
    assert pending.source_approval == "PENDING" and not pending.publication_allowed
    assert tampered.source_approval == "REJECTED" and not tampered.publication_allowed


def test_confirmed_mismatch_or_systematic_defect_rejects():
    result = evaluate_corporate_action_gates(
        evidence(), cross_source="FAIL", revision="PASS", adjustment="PASS",
        catch_up="PASS", incremental="PASS", exception_budget="PASS", systematic_defect="FAIL")
    assert result.source_approval == "REJECTED"
    assert not result.publication_allowed


def test_publisher_consumes_verified_gate_and_approval_without_rejudging():
    passing = evaluate_corporate_action_gates(
        evidence(), cross_source="PASS", revision="PASS", adjustment="PASS",
        catch_up="PASS", incremental="PASS", exception_budget="PASS", systematic_defect="PASS")
    assert authorize_corporate_action_publication(passing, "APPROVED_WITH_RULES", evidence())
    pending = replace(passing, publication_allowed=False, source_approval="PENDING")
    with pytest.raises(CorporateActionPublicationError):
        authorize_corporate_action_publication(pending, "PENDING", evidence())
    with pytest.raises(CorporateActionPublicationError):
        authorize_corporate_action_publication(passing, "APPROVED_WITH_RULES", replace(evidence(), source_version_identity="tampered"))


def test_gate_artifact_identity_changes_when_a_gate_disposition_changes():
    passing = evaluate_corporate_action_gates(
        evidence(), cross_source="PASS", revision="PASS", adjustment="PASS",
        catch_up="PASS", incremental="PASS", exception_budget="PASS", systematic_defect="PASS")
    pending = replace(passing, catch_up_2026="PENDING", source_approval="PENDING", publication_allowed=False)
    assert gate_artifact_id(passing, evidence().evidence_id) != gate_artifact_id(pending, evidence().evidence_id)
