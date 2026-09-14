from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from v5_2.refresh.contracts import DatasetReadiness, DatasetRefreshResultV1
from v5_2.refresh.readiness import RefreshReadinessArtifactV1


TARGET = date(2026, 9, 14)
NOW = datetime(2026, 9, 14, 20, 10, tzinfo=timezone.utc)


def result(kind, readiness=DatasetReadiness.READY):
    return DatasetRefreshResultV1(
        dataset_kind=kind, readiness=readiness, approval_id="a" * 64,
        manifest_id=(kind[0] * 64), latest_approved_session=TARGET,
        availability_modes=("CONTEMPORANEOUS_OBSERVED",),
    )


def complete_results():
    return {kind: result(kind, DatasetReadiness.SCOPED_READY if kind in {
        "corporate_action", "financial_disclosure"} else DatasetReadiness.READY)
        for kind in ("trade_calendar", "security_master", "daily_bar",
                     "daily_security_status", "corporate_action", "financial_disclosure")}


def test_all_base_and_scoped_optional_results_produce_ready_artifact():
    artifact = RefreshReadinessArtifactV1.evaluate(TARGET, complete_results(), NOW)
    assert artifact.research_ready is True
    assert artifact.gates["CROSS_DATASET_READINESS"] == "PASS"
    assert artifact.artifact_id == artifact.content_hash


@pytest.mark.parametrize("kind", ["trade_calendar", "security_master", "daily_bar", "daily_security_status"])
def test_each_missing_or_not_ready_base_domain_fails_closed(kind):
    values = complete_results()
    values[kind] = replace(values[kind], readiness=DatasetReadiness.NOT_READY)
    artifact = RefreshReadinessArtifactV1.evaluate(TARGET, values, NOW)
    assert artifact.research_ready is False
    assert kind.upper() + "_READY" in artifact.failure_reasons


@pytest.mark.parametrize("field,gate", [
    ("approval_valid", "APPROVAL_VALIDITY"), ("manifest_valid", "MANIFEST_VALIDITY"),
    ("coverage_valid", "TARGET_COVERAGE"), ("pit_valid", "PIT"),
    ("identity_valid", "IDENTITY_CONSISTENCY"),
])
def test_integrity_dimension_failure_blocks_readiness(field, gate):
    values = complete_results()
    values["daily_bar"] = replace(values["daily_bar"], **{field: False})
    artifact = RefreshReadinessArtifactV1.evaluate(TARGET, values, NOW)
    assert artifact.gates[gate] == "FAIL"
    assert artifact.research_ready is False


def test_optional_unsupported_scope_is_visible_without_invalidating_base_snapshot():
    values = complete_results()
    values["corporate_action"] = replace(
        values["corporate_action"], readiness=DatasetReadiness.SCOPED_READY,
        reason_codes=("UNSUPPORTED_RIGHTS_ISSUE",), affected_security_ids=("000001.SZ",),
    )
    artifact = RefreshReadinessArtifactV1.evaluate(TARGET, values, NOW)
    assert artifact.research_ready is True
    assert artifact.scoped_exclusions == {"corporate_action": ("000001.SZ",)}
