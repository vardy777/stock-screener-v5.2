from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from v5_2.refresh.adapters import AvailabilityMode, DatasetStateV1
from v5_2.refresh.contracts import DatasetReadiness, FreshnessStatus, SnapshotStore
from v5_2.refresh.planning import ApprovedCalendarView
from v5_2.refresh.service import RefreshService


SH = timezone(timedelta(hours=8))
NOW = datetime(2026, 9, 14, 20, 0, tzinfo=SH)
OPEN = (date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 14), date(2026, 9, 15))


class FakeAdapter:
    def __init__(self, kind, completed, *, required=True, readiness=DatasetReadiness.READY,
                 fail=False, calls=None):
        self.dataset_kind, self.required, self.completed = kind, required, tuple(completed)
        self.readiness, self.fail, self.calls = readiness, fail, calls if calls is not None else []
        self.revision = False

    def inspect_current_state(self):
        latest = max(self.completed) if self.completed else date(2026, 9, 1)
        return DatasetStateV1(self.dataset_kind, self.dataset_kind[0] * 64,
                              (self.dataset_kind[-1] or "x") * 64, latest,
                              self.completed, latest.isoformat(), readiness=self.readiness,
                              availability_modes=(AvailabilityMode.CONTEMPORANEOUS_OBSERVED.value,))

    def refresh(self, target, missing):
        self.calls.append((self.dataset_kind, tuple(missing)))
        if self.fail:
            raise RuntimeError(self.dataset_kind + " provider failed")
        self.completed = tuple(sorted(set((*self.completed, *missing))))
        state = self.inspect_current_state()
        from v5_2.refresh.contracts import DatasetRefreshResultV1
        return DatasetRefreshResultV1(
            state.dataset_kind, state.readiness, state.approval_id, state.manifest_id,
            state.latest_approved_session, state.availability_modes,
            changed=bool(missing), coverage_valid=target in self.completed,
        )


class FakeCalendar(FakeAdapter):
    def __init__(self, completed=OPEN, **kwargs):
        super().__init__("trade_calendar", completed, **kwargs)
        self.coverage_end = date(2026, 9, 30)

    def ensure_calendar_through(self, today):
        if self.fail:
            raise RuntimeError("calendar provider failed")

    def calendar_view(self):
        return ApprovedCalendarView("c" * 64, date(2026, 9, 1), self.coverage_end, OPEN)


def adapters(completed, *, fail_kind=None, status_readiness=DatasetReadiness.READY, calls=None):
    calls = calls if calls is not None else []
    return (
        FakeAdapter("security_master", completed, fail=fail_kind == "security_master", calls=calls),
        FakeAdapter("daily_bar", completed, fail=fail_kind == "daily_bar", calls=calls),
        FakeAdapter("daily_security_status", completed, readiness=status_readiness,
                    fail=fail_kind == "daily_security_status", calls=calls),
        FakeAdapter("corporate_action", completed, required=False,
                    readiness=DatasetReadiness.SCOPED_READY, calls=calls),
        FakeAdapter("financial_disclosure", completed, required=False,
                    readiness=DatasetReadiness.SCOPED_READY, calls=calls),
    )


def test_already_current_is_no_op_and_second_run_reuses_snapshot(tmp_path):
    store = SnapshotStore(tmp_path)
    service = RefreshService(FakeCalendar(), adapters(OPEN[:3]), store, lambda: NOW)
    first = service.refresh()
    second = service.refresh()
    assert first.refresh_status.value == "NO_OP"
    assert first.freshness_status is FreshnessStatus.CURRENT
    assert second.snapshot_id == first.snapshot_id
    assert len(tuple((tmp_path / "snapshots").glob("*.json"))) == 1


def test_one_day_and_multi_day_catch_up_use_all_missing_open_sessions(tmp_path):
    one = RefreshService(FakeCalendar(), adapters(OPEN[:2]), SnapshotStore(tmp_path / "one"), lambda: NOW).refresh()
    multi = RefreshService(FakeCalendar(), adapters(OPEN[:1]), SnapshotStore(tmp_path / "multi"), lambda: NOW).refresh()
    assert one.missing_sessions == (date(2026, 9, 14),)
    assert multi.missing_sessions == (date(2026, 9, 11), date(2026, 9, 14))
    assert one.research_ready and multi.research_ready


def test_fixed_order_stops_after_daily_bar_failure_and_publishes_no_snapshot(tmp_path):
    calls = []
    service = RefreshService(FakeCalendar(calls=calls), adapters(OPEN[:2], fail_kind="daily_bar", calls=calls),
                             SnapshotStore(tmp_path), lambda: NOW)
    result = service.refresh()
    assert [kind for kind, _ in calls] == ["security_master", "daily_bar"]
    assert result.research_ready is False
    assert result.snapshot_id is None
    assert result.freshness_status is FreshnessStatus.FAILED


def test_status_failure_preserves_previous_ready_snapshot_without_relabeling_it(tmp_path):
    store = SnapshotStore(tmp_path)
    first = RefreshService(FakeCalendar(), adapters(OPEN[:3]), store, lambda: NOW).refresh()
    later = datetime(2026, 9, 15, 20, 0, tzinfo=SH)
    failed = RefreshService(FakeCalendar(), adapters(OPEN[:3], fail_kind="daily_security_status"), store, lambda: later).refresh()
    assert failed.target_session == date(2026, 9, 15)
    assert failed.previous_successful_snapshot_id == first.snapshot_id
    assert failed.snapshot_id is None
    assert store.latest_successful().target_session == date(2026, 9, 14)


def test_after_cutoff_provider_incomplete_does_not_imply_ready(tmp_path):
    service = RefreshService(FakeCalendar(), adapters(OPEN[:2], status_readiness=DatasetReadiness.NOT_READY),
                             SnapshotStore(tmp_path), lambda: NOW)
    result = service.refresh()
    assert result.target_session == date(2026, 9, 14)
    assert result.research_ready is False
    assert result.freshness_status is FreshnessStatus.INCOMPLETE


def test_calendar_resolution_failure_is_failed_and_never_calls_other_adapters(tmp_path):
    calls = []
    calendar = FakeCalendar(calls=calls)
    calendar.coverage_end = date(2026, 9, 13)
    result = RefreshService(calendar, adapters(OPEN[:2], calls=calls), SnapshotStore(tmp_path), lambda: NOW).refresh()
    assert result.target_session is None
    assert result.freshness_status is FreshnessStatus.FAILED
    assert calls == []
