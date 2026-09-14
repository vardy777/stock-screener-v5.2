from datetime import date, datetime, timedelta, timezone

import pytest

from v5_2.refresh.adapters import (
    AcquisitionObservationV1,
    AvailabilityMode,
    DatasetStateV1,
    ThinDatasetAdapter,
    derive_available_at,
)
from v5_2.refresh.contracts import DatasetReadiness


SH = timezone(timedelta(hours=8))


def state(kind="daily_bar"):
    return DatasetStateV1(kind, "a" * 64, "m" * 64, date(2026, 9, 11),
                          (date(2026, 9, 11),), "watermark-1")


def test_adapter_plans_only_missing_scope_and_accepts_terminal_proven_no_change():
    calls = []
    adapter = ThinDatasetAdapter(
        "financial_disclosure", False, lambda: state("financial_disclosure"),
        lambda current, target, missing: (current.watermark, target.isoformat(), missing),
        lambda scope: AcquisitionObservationV1((), (), True, 0, "VALID_NO_CHANGE", None, None, False),
        lambda current, observation, target: current,
    )
    plan = adapter.plan_incremental_scope(date(2026, 9, 14), (date(2026, 9, 14),))
    result = adapter.execute_incremental_refresh(plan)
    assert plan.query_scope == ("watermark-1", "2026-09-14", (date(2026, 9, 14),))
    assert result.semantic_outcome == "VALID_NO_CHANGE"


def test_zero_rows_without_terminal_raw_evidence_fails_closed():
    adapter = ThinDatasetAdapter(
        "corporate_action", False, lambda: state("corporate_action"),
        lambda current, target, missing: (),
        lambda scope: AcquisitionObservationV1((), (), False, 0, None, None, None, False),
        lambda current, observation, target: current,
    )
    with pytest.raises(ValueError, match="zero-row observation"):
        adapter.execute_incremental_refresh(adapter.plan_incremental_scope(date(2026, 9, 14), ()))


def test_historical_and_observed_availability_never_backdate_observation():
    observed = datetime(2026, 9, 14, 20, 4, tzinfo=SH)
    validated = datetime(2026, 9, 14, 20, 7, tzinfo=SH)
    assert derive_available_at(AvailabilityMode.CONTEMPORANEOUS_OBSERVED,
                               date(2026, 9, 14), date(2026, 9, 15), observed, validated) == validated
    assert derive_available_at(AvailabilityMode.HISTORICAL_RECONSTRUCTED,
                               date(2015, 1, 5), date(2015, 1, 6), observed, validated) == datetime(2015, 1, 6, 16, 30, tzinfo=SH)


def test_revision_is_published_as_changed_and_optional_scope_is_visible():
    revised = AcquisitionObservationV1(("raw",), ("receipt",), True, 1, "ROWS", None, None, True)
    adapter = ThinDatasetAdapter(
        "corporate_action", False, lambda: state("corporate_action"),
        lambda current, target, missing: (target,), lambda scope: revised,
        lambda current, observation, target: DatasetStateV1(
            current.dataset_kind, "b" * 64, "n" * 64, target,
            (*current.completed_sessions, target), "watermark-2",
            readiness=DatasetReadiness.SCOPED_READY,
            reason_codes=("UNSUPPORTED_RIGHTS_ISSUE",),
        ),
    )
    result = adapter.refresh(date(2026, 9, 14), (date(2026, 9, 14),))
    assert result.changed is True
    assert result.readiness is DatasetReadiness.SCOPED_READY
    assert result.reason_codes == ("UNSUPPORTED_RIGHTS_ISSUE",)
