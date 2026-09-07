from datetime import date

from v5_2.data.real_audits.status_exceptions import (
    StatusExceptionBudgetV1,
    StatusExceptionPatternAuditV1,
    StatusExceptionalRecordV1,
)


def record(symbol="000001.SZ", *, exchange="SZ", year=2025, field="suspension"):
    return StatusExceptionalRecordV1.create(
        security_identity=symbol, effective_date=date(year, 1, 2), affected_fields=(field,),
        reason="isolated unavailable announcement", evidence_ids=("evidence",),
        disposition="QUARANTINE", dimensions={"exchange": exchange, "year": year, "field": field},
        policy_version="status-exception-v1",
    )


def test_isolated_exception_stays_local_and_within_budget() -> None:
    budget = StatusExceptionBudgetV1.create(absolute_limit=10, ratio_limit="0.01", systematic_cluster_minimum=3)
    audit = StatusExceptionPatternAuditV1.evaluate((record(),), budget=budget)
    result = budget.evaluate((record(),), total_records=1000, pattern_audit=audit)
    assert audit.systematic_dataset_defect is False
    assert result.passed is True


def test_exchange_field_cluster_escalates_to_systematic_defect() -> None:
    budget = StatusExceptionBudgetV1.create(absolute_limit=10, ratio_limit="0.5", systematic_cluster_minimum=3)
    records = tuple(record(f"00000{i}.SZ") for i in range(1, 4))
    audit = StatusExceptionPatternAuditV1.evaluate(records, budget=budget)
    assert audit.systematic_dataset_defect is True
    assert "SZ|2025|suspension" in audit.repeated_signatures
    assert budget.evaluate(records, total_records=100, pattern_audit=audit).passed is False


def test_budget_overflow_fails_without_systematic_cluster() -> None:
    budget = StatusExceptionBudgetV1.create(absolute_limit=1, ratio_limit="0.5", systematic_cluster_minimum=5)
    records = (record("000001.SZ"), record("600000.SH", exchange="SH", field="risk_warning"))
    audit = StatusExceptionPatternAuditV1.evaluate(records, budget=budget)
    result = budget.evaluate(records, total_records=100, pattern_audit=audit)
    assert result.passed is False
    assert result.reasons == ("absolute_limit",)
