from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Sequence

from v5_2.refresh.adapters import DatasetRefreshAdapter
from v5_2.refresh.contracts import (
    DatasetReadiness,
    DatasetRefreshResultV1,
    FreshnessStatus,
    RefreshResultV1,
    RefreshStatus,
    ResearchDataSnapshotV1,
    SnapshotStore,
)
from v5_2.refresh.planning import SHANGHAI, detect_session_gaps, resolve_target_session
from v5_2.refresh.readiness import BASE, RefreshReadinessArtifactV1


class RefreshService:
    def __init__(self, calendar_adapter, remaining_adapters: Sequence[DatasetRefreshAdapter],
                 snapshot_store: SnapshotStore, clock: Callable[[], datetime]) -> None:
        self.calendar_adapter = calendar_adapter
        self.adapters = tuple(remaining_adapters)
        self.snapshot_store = snapshot_store
        self.clock = clock
        expected = ("security_master", "daily_bar", "daily_security_status",
                    "corporate_action", "financial_disclosure")
        if tuple(item.dataset_kind for item in self.adapters) != expected:
            raise ValueError("refresh adapters must use the frozen dependency order")

    def _failed(self, *, now: datetime, today: date, is_trading_day: bool | None,
                target: date | None, latest_completed: date | None,
                before: date | None, missing: tuple[date, ...],
                results: dict[str, DatasetRefreshResultV1], reasons: tuple[str, ...],
                incomplete: bool = False) -> RefreshResultV1:
        previous = self.snapshot_store.latest_successful()
        return RefreshResultV1(
            today, is_trading_day, target, latest_completed, before, missing, results,
            RefreshStatus.FAILED, before,
            FreshnessStatus.INCOMPLETE if incomplete else FreshnessStatus.FAILED,
            False, None, previous.snapshot_id if previous else None, reasons,
        )

    def refresh(self) -> RefreshResultV1:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("refresh clock must be timezone-aware")
        today = now.astimezone(SHANGHAI).date()
        try:
            self.calendar_adapter.ensure_calendar_through(today)
            calendar = self.calendar_adapter.calendar_view()
        except Exception as error:
            return self._failed(now=now, today=today, is_trading_day=None, target=None,
                                latest_completed=None, before=None, missing=(), results={},
                                reasons=(type(error).__name__,))
        resolution = resolve_target_session(now, calendar)
        if resolution.target_session is None:
            return self._failed(now=now, today=resolution.today,
                                is_trading_day=resolution.is_trading_day, target=None,
                                latest_completed=None, before=None, missing=(), results={},
                                reasons=(resolution.reason or "TARGET_SESSION_UNRESOLVED",))
        target = resolution.target_session
        base_states = [self.calendar_adapter.inspect_current_state()]
        base_states.extend(item.inspect_current_state() for item in self.adapters[:3])
        before = min(item.latest_approved_session for item in base_states)
        common_completed = set(base_states[0].completed_sessions)
        for state in base_states[1:]:
            common_completed &= set(state.completed_sessions)
        common_plan = detect_session_gaps(calendar.open_sessions, tuple(common_completed), target)
        calendar_state = base_states[0]
        results: dict[str, DatasetRefreshResultV1] = {
            "trade_calendar": DatasetRefreshResultV1(
                "trade_calendar", calendar_state.readiness, calendar_state.approval_id,
                calendar_state.manifest_id, calendar_state.latest_approved_session,
                calendar_state.availability_modes, calendar_state.reason_codes,
                calendar_state.affected_security_ids, False,
                coverage_valid=target in calendar_state.completed_sessions,
            )
        }
        changed = False
        for adapter in self.adapters:
            state = adapter.inspect_current_state()
            plan = detect_session_gaps(calendar.open_sessions, state.completed_sessions, target)
            try:
                result = adapter.refresh(target, plan.missing_sessions)
            except Exception as error:
                results[adapter.dataset_kind] = DatasetRefreshResultV1(
                    adapter.dataset_kind, DatasetReadiness.NOT_READY, None, None, None, (),
                    reason_codes=(type(error).__name__,), coverage_valid=False,
                )
                return self._failed(
                    now=now, today=resolution.today, is_trading_day=resolution.is_trading_day,
                    target=target, latest_completed=resolution.latest_completed_session,
                    before=before, missing=common_plan.missing_sessions, results=results,
                    reasons=(adapter.dataset_kind + ":" + type(error).__name__,),
                )
            results[adapter.dataset_kind] = result
            changed = changed or result.changed
        readiness = RefreshReadinessArtifactV1.evaluate(target, results, now)
        if not readiness.research_ready:
            return self._failed(
                now=now, today=resolution.today, is_trading_day=resolution.is_trading_day,
                target=target, latest_completed=resolution.latest_completed_session,
                before=before, missing=common_plan.missing_sessions, results=results,
                reasons=readiness.failure_reasons, incomplete=True,
            )
        latest = min(results[kind].latest_approved_session for kind in BASE if results[kind].latest_approved_session)
        previous = self.snapshot_store.latest_successful()
        manifests = {kind: results[kind].manifest_id for kind in results}
        if previous and previous.target_session == target and dict(previous.manifest_ids) == manifests:
            snapshot = previous
        else:
            snapshot = ResearchDataSnapshotV1.create(
                target_session=target, created_at=now, latest_approved_session=latest,
                manifest_ids=manifests,
                availability_mode_summary={kind: result.availability_modes for kind, result in results.items()},
                dataset_readiness=results, freshness_status=FreshnessStatus.CURRENT,
                research_ready=True,
                previous_successful_snapshot_id=previous.snapshot_id if previous else None,
            )
            self.snapshot_store.publish_ready(snapshot)
        no_op = not common_plan.missing_sessions and not changed
        return RefreshResultV1(
            resolution.today, resolution.is_trading_day, target,
            resolution.latest_completed_session, before, common_plan.missing_sessions,
            results, RefreshStatus.NO_OP if no_op else RefreshStatus.SUCCESS, latest,
            FreshnessStatus.CURRENT, True, snapshot.snapshot_id,
            previous.snapshot_id if previous else None, (),
        )
