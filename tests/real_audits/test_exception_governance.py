from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from v5_2.data.real_audits.exception_governance import (
    ExceptionDisposition,
    ExceptionPatternAuditV1,
    ExceptionType,
    ExceptionalSecurityGovernancePolicyV1,
    ExceptionalSecurityRecordV1,
    HistoricalUniverseAdmissionV1,
    SecurityMasterExceptionBudgetV1,
)


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _exception(code="600747.SH", field="delisting_date", kind=ExceptionType.SEMANTIC_AMBIGUITY):
    return ExceptionalSecurityRecordV1.create(
        security_identity=code, effective_from=date(2010, 1, 1), effective_to=date(2025, 12, 31),
        affected_fields=(field,), verified_fields=("symbol", "exchange", "listing_date"),
        provider_values={field: "20191212"}, reference_values={field: ("20191212", "20191213")},
        exception_type=kind, evidence_ids=("official-a", "official-b"),
        disposition=ExceptionDisposition.QUARANTINE,
        research_impact=f"exclude when {field} is required", created_at=NOW,
        policy_version="exception-policy-v1", dimensions={"exchange": code[-2:], "board": "main", "year": "2019", "listing_status": "D"},
    )


def test_exception_record_is_immutable_and_ambiguity_is_quarantined() -> None:
    record = _exception()
    assert record.affected_fields == ("delisting_date",)
    assert record.disposition is ExceptionDisposition.QUARANTINE
    with pytest.raises(Exception):
        record.security_identity = "changed"  # type: ignore[misc]


def test_budget_is_predeclared_deterministic_and_rejects_systematic_patterns() -> None:
    policy = ExceptionalSecurityGovernancePolicyV1.create_default()
    budget = SecurityMasterExceptionBudgetV1.create_default(policy.policy_id)
    record = _exception()
    audit = ExceptionPatternAuditV1.evaluate((record,), total_securities=5549, policy=policy)
    first = budget.evaluate((record,), total_securities=5549, coverage_impact_ratio=0.0,
                            affected_session_ratio=0.0, pattern_audit=audit)
    assert first == budget.evaluate((record,), total_securities=5549, coverage_impact_ratio=0.0,
                                    affected_session_ratio=0.0, pattern_audit=audit)
    assert first.passed
    clustered = tuple(_exception(f"600{i:03d}.SH") for i in range(3))
    systematic = ExceptionPatternAuditV1.evaluate(clustered, total_securities=5549, policy=policy)
    assert systematic.systematic_defect
    assert not budget.evaluate(clustered, total_securities=5549, coverage_impact_ratio=0.0,
                               affected_session_ratio=0.0, pattern_audit=systematic).passed


def test_field_scoped_quarantine_and_explicit_exclusion_evidence() -> None:
    record = _exception(code="000535.SZ", field="board", kind=ExceptionType.OFFICIAL_FIELD_UNAVAILABLE)
    gate = HistoricalUniverseAdmissionV1((record,), valid_intervals={"000535.SZ": (date(1993, 11, 30), date(2025, 9, 21))})
    assert gate.admit("000535.SZ", date(2019, 1, 2), required_fields=("symbol", "exchange")).admitted
    excluded = gate.admit("000535.SZ", date(2019, 1, 2), required_fields=("board",))
    assert not excluded.admitted
    assert excluded.exclusion_evidence is not None
    assert excluded.exclusion_evidence.exception_id == record.exception_id
    assert excluded.exclusion_evidence.reason == "FIELD_SCOPED_QUARANTINE"
    assert "board" not in record.verified_fields


def test_unknown_board_never_defaults_and_invalid_intervals_fail_closed() -> None:
    record = _exception(code="000535.SZ", field="board", kind=ExceptionType.OFFICIAL_FIELD_UNAVAILABLE)
    gate = HistoricalUniverseAdmissionV1((record,), valid_intervals={"000535.SZ": (date(1993, 11, 30), date(2025, 9, 21))})
    assert not gate.admit("000535.SZ", date(1990, 1, 1), required_fields=("symbol",)).admitted
    with pytest.raises(ValueError, match="silent"):
        gate.build_universe(("000535.SZ",), date(2019, 1, 2), required_fields=("board",), record_exclusions=False)


def test_exception_set_hash_changes_and_must_be_pinned() -> None:
    policy = ExceptionalSecurityGovernancePolicyV1.create_default()
    one = policy.exception_set_hash((_exception(),))
    two = policy.exception_set_hash((_exception(), _exception("000535.SZ", "board", ExceptionType.OFFICIAL_FIELD_UNAVAILABLE)))
    assert one != two
    policy.require_pinned_exception_set(one, (_exception(),))
    with pytest.raises(ValueError, match="re-evaluated"):
        policy.require_pinned_exception_set(one, (_exception(), _exception("000535.SZ", "board", ExceptionType.OFFICIAL_FIELD_UNAVAILABLE)))


def test_budget_threshold_is_frozen_before_evaluation() -> None:
    budget = SecurityMasterExceptionBudgetV1.create_default(ExceptionalSecurityGovernancePolicyV1.create_default().policy_id)
    assert budget.frozen_at == NOW
    with pytest.raises(Exception):
        budget.absolute_exception_limit = 4  # type: ignore[misc]
