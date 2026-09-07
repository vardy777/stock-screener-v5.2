import pytest

from v5_2.data.real_audits.status_entry import StatusEntryError, build_status_request_inventory


UPSTREAM = ("calendar", "master", "daily")


def universe():
    return {
        "universe_id": "universe", "ordered_symbols": ["000001.SZ", "600000.SH"],
        "ordered_sessions": ["20240102", "20251231"], "upstream_approval_ids": ["calendar", "master"],
    }


def test_status_inventory_is_deterministic_and_year_partitioned() -> None:
    first = build_status_request_inventory(universe(), daily_bar_approval_id="daily", active_approval_ids=UPSTREAM, revoked_approval_ids=())
    second = build_status_request_inventory(universe(), daily_bar_approval_id="daily", active_approval_ids=UPSTREAM, revoked_approval_ids=())
    assert first.inventory_id == second.inventory_id
    assert first.ordered_symbols == ("000001.SZ", "600000.SH")
    assert [(request.dataset_kind, request.parameters["start_date"], request.parameters["end_date"]) for request in first.requests] == [
        ("risk_warning_history", "20240101", "20241231"),
        ("suspension_history", "20240101", "20241231"),
        ("risk_warning_history", "20250101", "20251231"),
        ("suspension_history", "20250101", "20251231"),
    ]


def test_status_inventory_fails_closed_on_revoked_upstream() -> None:
    with pytest.raises(StatusEntryError, match="revoked"):
        build_status_request_inventory(universe(), daily_bar_approval_id="daily", active_approval_ids=UPSTREAM, revoked_approval_ids=("daily",))
