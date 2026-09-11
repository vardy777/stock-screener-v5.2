from v5_2.data.real_audits.financial_disclosure_entry import (
    build_financial_disclosure_inventory, run_bounded_retry_rounds,
)
from v5_2.providers.datahub import DATAHUB_ENDPOINTS


def test_only_probed_primary_statements_are_allowlisted():
    assert DATAHUB_ENDPOINTS["financial_income"] == "income"
    assert DATAHUB_ENDPOINTS["financial_balance_sheet"] == "balancesheet"
    assert DATAHUB_ENDPOINTS["financial_cash_flow"] == "cashflow"
    assert "financial_forecast" not in DATAHUB_ENDPOINTS
    assert "financial_express" not in DATAHUB_ENDPOINTS
    assert "financial_indicator" not in DATAHUB_ENDPOINTS


def test_inventory_is_deterministic_and_pins_universe_and_approvals():
    values = dict(symbols=("600000.SH", "000001.SZ"), coverage_start="20100104",
                  coverage_end="20260910", universe_id="universe",
                  upstream_approval_ids=("calendar", "master"))
    first = build_financial_disclosure_inventory(**values)
    second = build_financial_disclosure_inventory(**values)
    assert first == second
    assert len(first.requests) == 12
    assert first.universe_id == "universe"
    assert first.upstream_approval_ids == ("calendar", "master")
    assert all(request.parameters["ts_code"] in values["symbols"] for request in first.requests)
    assert {(request.parameters["start_date"], request.parameters["end_date"]) for request in first.requests} == {
        ("20100104", "20171231"), ("20180101", "20260910")}


def test_inventory_rejects_unapproved_or_noncanonical_scope():
    import pytest
    with pytest.raises(ValueError):
        build_financial_disclosure_inventory(symbols=("600000",), coverage_start="20100104",
            coverage_end="20260910", universe_id="u", upstream_approval_ids=("calendar", "master"))
    with pytest.raises(ValueError):
        build_financial_disclosure_inventory(symbols=("600000.SH",), coverage_start="20100104",
            coverage_end="20260910", universe_id="u", upstream_approval_ids=("calendar", ""))


def test_batch_runner_retries_only_failed_items_without_losing_successes():
    calls = {1: 0, 2: 0}
    def operation(item):
        calls[item] += 1
        if item == 2 and calls[item] == 1:
            raise OSError("transient")
        return item * 10
    assert run_bounded_retry_rounds((1, 2), operation, max_rounds=2, workers=2) == (10, 20)
    assert calls == {1: 1, 2: 2}


def test_batch_runner_fails_closed_after_bounded_rounds():
    import pytest
    with pytest.raises(RuntimeError, match="1 requests remain failed"):
        run_bounded_retry_rounds((1,), lambda _: (_ for _ in ()).throw(OSError()), max_rounds=2, workers=1)
