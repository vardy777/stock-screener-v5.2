from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Callable, Protocol

from v5_2.refresh.contracts import DatasetReadiness, DatasetRefreshResultV1


SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")


class AvailabilityMode(str, Enum):
    HISTORICAL_RECONSTRUCTED = "HISTORICAL_RECONSTRUCTED"
    CONTEMPORANEOUS_OBSERVED = "CONTEMPORANEOUS_OBSERVED"


def derive_available_at(mode: AvailabilityMode, session: date, next_session: date,
                        observed_at: datetime | None, validated_at: datetime | None) -> datetime:
    if mode is AvailabilityMode.HISTORICAL_RECONSTRUCTED:
        return datetime.combine(next_session, time(16, 30), SHANGHAI)
    if observed_at is None or validated_at is None:
        raise ValueError("contemporaneous availability requires observation and validation times")
    if any(value.tzinfo is None or value.utcoffset() is None for value in (observed_at, validated_at)):
        raise ValueError("observation times must be timezone-aware")
    if validated_at < observed_at:
        raise ValueError("validation cannot predate observation")
    return max(observed_at, validated_at)


@dataclass(frozen=True, slots=True)
class DatasetStateV1:
    dataset_kind: str
    approval_id: str
    manifest_id: str
    latest_approved_session: date
    completed_sessions: tuple[date, ...]
    watermark: str
    readiness: DatasetReadiness = DatasetReadiness.READY
    reason_codes: tuple[str, ...] = ()
    affected_security_ids: tuple[str, ...] = ()
    availability_modes: tuple[str, ...] = (AvailabilityMode.HISTORICAL_RECONSTRUCTED.value,)


@dataclass(frozen=True, slots=True)
class IncrementalPlanV1:
    dataset_kind: str
    target_session: date
    missing_sessions: tuple[date, ...]
    query_scope: object


@dataclass(frozen=True, slots=True)
class AcquisitionObservationV1:
    raw_payload_hashes: tuple[str, ...]
    receipt_hashes: tuple[str, ...]
    terminal: bool
    row_count: int
    semantic_outcome: str | None
    observed_at: datetime | None
    validated_at: datetime | None
    revision_observed: bool


class DatasetRefreshAdapter(Protocol):
    dataset_kind: str
    required: bool

    def inspect_current_state(self) -> DatasetStateV1: ...
    def plan_incremental_scope(self, target_session: date,
                               missing_sessions: tuple[date, ...]) -> IncrementalPlanV1: ...
    def refresh(self, target_session: date,
                missing_sessions: tuple[date, ...]) -> DatasetRefreshResultV1: ...


class ThinDatasetAdapter:
    def __init__(self, dataset_kind: str, required: bool,
                 state_reader: Callable[[], DatasetStateV1],
                 scope_planner: Callable[[DatasetStateV1, date, tuple[date, ...]], object],
                 acquirer: Callable[[object], AcquisitionObservationV1],
                 publisher: Callable[[DatasetStateV1, AcquisitionObservationV1, date], DatasetStateV1]) -> None:
        self.dataset_kind = dataset_kind
        self.required = required
        self._state_reader = state_reader
        self._scope_planner = scope_planner
        self._acquirer = acquirer
        self._publisher = publisher

    def inspect_current_state(self) -> DatasetStateV1:
        state = self._state_reader()
        if state.dataset_kind != self.dataset_kind:
            raise ValueError("adapter state dataset mismatch")
        return state

    def plan_incremental_scope(self, target_session: date,
                               missing_sessions: tuple[date, ...]) -> IncrementalPlanV1:
        current = self.inspect_current_state()
        return IncrementalPlanV1(self.dataset_kind, target_session, tuple(missing_sessions),
                                 self._scope_planner(current, target_session, tuple(missing_sessions)))

    def execute_incremental_refresh(self, plan: IncrementalPlanV1) -> AcquisitionObservationV1:
        observation = self._acquirer(plan.query_scope)
        if observation.row_count == 0 and not (
            observation.terminal and observation.semantic_outcome == "VALID_NO_CHANGE"
        ):
            raise ValueError("zero-row observation lacks terminal valid-no-change evidence")
        if observation.row_count > 0 and (not observation.terminal or not observation.raw_payload_hashes or not observation.receipt_hashes):
            raise ValueError("acquisition observation is incomplete")
        return observation

    def publish_result(self, current: DatasetStateV1, observation: AcquisitionObservationV1,
                       target_session: date) -> DatasetStateV1:
        return self._publisher(current, observation, target_session)

    def readiness_for(self, state: DatasetStateV1) -> DatasetRefreshResultV1:
        return DatasetRefreshResultV1(
            state.dataset_kind, state.readiness, state.approval_id, state.manifest_id,
            state.latest_approved_session, state.availability_modes, state.reason_codes,
            state.affected_security_ids, False,
        )

    def refresh(self, target_session: date,
                missing_sessions: tuple[date, ...]) -> DatasetRefreshResultV1:
        current = self.inspect_current_state()
        if not missing_sessions and current.latest_approved_session >= target_session:
            return self.readiness_for(current)
        plan = IncrementalPlanV1(self.dataset_kind, target_session, tuple(missing_sessions),
                                 self._scope_planner(current, target_session, tuple(missing_sessions)))
        observation = self.execute_incremental_refresh(plan)
        published = self.publish_result(current, observation, target_session)
        result = self.readiness_for(published)
        return DatasetRefreshResultV1(
            result.dataset_kind, result.readiness, result.approval_id, result.manifest_id,
            result.latest_approved_session, result.availability_modes, result.reason_codes,
            result.affected_security_ids, observation.revision_observed or published.manifest_id != current.manifest_id,
        )


def make_calendar_adapter(**kwargs) -> ThinDatasetAdapter:
    return ThinDatasetAdapter("trade_calendar", True, **kwargs)


def make_security_master_adapter(**kwargs) -> ThinDatasetAdapter:
    return ThinDatasetAdapter("security_master", True, **kwargs)


def make_daily_bar_adapter(**kwargs) -> ThinDatasetAdapter:
    return ThinDatasetAdapter("daily_bar", True, **kwargs)


def make_security_status_adapter(**kwargs) -> ThinDatasetAdapter:
    return ThinDatasetAdapter("daily_security_status", True, **kwargs)


def make_corporate_action_adapter(**kwargs) -> ThinDatasetAdapter:
    return ThinDatasetAdapter("corporate_action", False, **kwargs)


def make_financial_disclosure_adapter(**kwargs) -> ThinDatasetAdapter:
    return ThinDatasetAdapter("financial_disclosure", False, **kwargs)
