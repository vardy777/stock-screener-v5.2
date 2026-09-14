from datetime import date, datetime, timezone

import pytest

from v5_2.refresh.contracts import (
    DatasetRefreshResultV1,
    FreshnessStatus,
    RefreshContractError,
    RefreshResultV1,
    RefreshStatus,
    ResearchDataSnapshotV1,
    SnapshotStore,
)


NOW = datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc)
MANIFESTS = {
    "trade_calendar": "c" * 64,
    "security_master": "m" * 64,
    "daily_bar": "b" * 64,
    "daily_security_status": "s" * 64,
    "corporate_action": "a" * 64,
    "financial_disclosure": "f" * 64,
}


def ready_snapshot() -> ResearchDataSnapshotV1:
    result = DatasetRefreshResultV1.ready(
        dataset_kind="daily_bar", approval_id="a" * 64,
        manifest_id="b" * 64, latest_approved_session=date(2026, 9, 14),
        availability_modes=("CONTEMPORANEOUS_OBSERVED",),
    )
    return ResearchDataSnapshotV1.create(
        target_session=date(2026, 9, 14), created_at=NOW,
        latest_approved_session=date(2026, 9, 14), manifest_ids=MANIFESTS,
        availability_mode_summary={"daily_bar": ("CONTEMPORANEOUS_OBSERVED",)},
        dataset_readiness={"daily_bar": result}, freshness_status=FreshnessStatus.CURRENT,
        research_ready=True, previous_successful_snapshot_id=None,
    )


def test_snapshot_identity_is_deterministic_and_contains_only_references():
    first = ready_snapshot()
    second = ready_snapshot()
    assert first == second
    assert first.snapshot_id == first.content_hash
    assert not hasattr(first, "facts")


def test_snapshot_rejects_missing_dataset_manifest_reference():
    manifests = dict(MANIFESTS)
    manifests.pop("daily_bar")
    with pytest.raises(RefreshContractError, match="manifest references"):
        ResearchDataSnapshotV1.create(
            target_session=date(2026, 9, 14), created_at=NOW,
            latest_approved_session=date(2026, 9, 14), manifest_ids=manifests,
            availability_mode_summary={}, dataset_readiness={},
            freshness_status=FreshnessStatus.CURRENT, research_ready=True,
            previous_successful_snapshot_id=None,
        )


def test_snapshot_store_reuses_identical_snapshot_and_preserves_pointer_on_rejection(tmp_path):
    store = SnapshotStore(tmp_path)
    snapshot = ready_snapshot()
    assert store.publish_ready(snapshot).snapshot_id == snapshot.snapshot_id
    assert store.publish_ready(snapshot).snapshot_id == snapshot.snapshot_id
    assert len(tuple((tmp_path / "snapshots").glob("*.json"))) == 1
    rejected = ResearchDataSnapshotV1.create(
        target_session=date(2026, 9, 15), created_at=NOW,
        latest_approved_session=date(2026, 9, 14), manifest_ids=MANIFESTS,
        availability_mode_summary={}, dataset_readiness={},
        freshness_status=FreshnessStatus.INCOMPLETE, research_ready=False,
        previous_successful_snapshot_id=snapshot.snapshot_id,
    )
    with pytest.raises(RefreshContractError, match="ready snapshot"):
        store.publish_ready(rejected)
    assert store.latest_successful().snapshot_id == snapshot.snapshot_id


def test_refresh_result_serializes_stable_frontend_contract():
    result = RefreshResultV1(
        today=date(2026, 9, 14), is_trading_day=True,
        target_session=date(2026, 9, 14), latest_completed_session=date(2026, 9, 14),
        latest_approved_session_before_refresh=date(2026, 9, 11),
        missing_sessions=(date(2026, 9, 14),), dataset_results={},
        refresh_status=RefreshStatus.SUCCESS,
        latest_approved_session=date(2026, 9, 14),
        freshness_status=FreshnessStatus.CURRENT, research_ready=True,
        snapshot_id="x" * 64, previous_successful_snapshot_id=None,
        failure_reasons=(),
    )
    assert result.as_dict()["missing_sessions"] == ["2026-09-14"]
    assert result.as_dict()["research_ready"] is True
