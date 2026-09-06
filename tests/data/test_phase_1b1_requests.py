from __future__ import annotations

from v5_2.data.phase_1b1_requests import phase_1b1_requests


def test_request_inventory_is_independent_and_scope_limited() -> None:
    requests = phase_1b1_requests()
    assert tuple(requests) == ("trade_calendar", "security_master", "daily_bar")
    assert [(r.endpoint, r.parameters.get("exchange")) for r in requests["trade_calendar"]] == [
        ("trade-cal", "SSE"),
        ("trade-cal", "SZSE"),
    ]
    assert [(r.parameters.get("exchange"), r.parameters.get("list_status")) for r in requests["security_master"]] == [
        ("SSE", "L"),
        ("SSE", "D"),
        ("SSE", "P"),
        ("SZSE", "L"),
        ("SZSE", "D"),
        ("SZSE", "P"),
    ]
    assert requests["daily_bar"] == ()


def test_requests_pin_frozen_coverage_and_datahub_identity() -> None:
    requests = phase_1b1_requests()
    for group in requests.values():
        for request in group:
            assert request.source_name == "datahubco_tushare_proxy"
            assert request.request_policy_version == "datahub-phase-1b1-request-v1"
            assert request.page_size == 5000
    calendar = requests["trade_calendar"][0]
    assert calendar.parameters["start_date"] == "20100101"
    assert calendar.parameters["end_date"] == "20251231"
    master = requests["security_master"][0]
    assert master.requested_fields == (
        "delist_date", "exchange", "list_date", "list_status", "market", "name", "symbol", "ts_code"
    )


def test_daily_requests_require_a_deterministic_master_sample() -> None:
    assert phase_1b1_requests()["daily_bar"] == ()
