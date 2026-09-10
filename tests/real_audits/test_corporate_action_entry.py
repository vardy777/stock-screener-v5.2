from datetime import date

import pytest

from v5_2.data.real_audits.corporate_action_entry import (
    CorporateActionEntryError,
    build_corporate_action_inventory,
)


def test_inventory_fetches_full_history_once_per_symbol_and_is_deterministic():
    first = build_corporate_action_inventory(
        symbols=("000001.SZ", "600000.SH"), endpoint="dividend",
        target_history_start=date(2010, 1, 4), baseline_validation_end=date(2025, 12, 31),
        rolling_coverage_end=date(2026, 9, 9), upstream_approval_ids=("master", "calendar"),
        active_approval_ids=("master", "calendar"), revoked_approval_ids=(),
    )
    second = build_corporate_action_inventory(
        symbols=("000001.SZ", "600000.SH"), endpoint="dividend",
        target_history_start=date(2010, 1, 4), baseline_validation_end=date(2025, 12, 31),
        rolling_coverage_end=date(2026, 9, 9), upstream_approval_ids=("master", "calendar"),
        active_approval_ids=("master", "calendar"), revoked_approval_ids=(),
    )
    assert first.inventory_id == second.inventory_id
    assert {request.segment for request in first.requests} == {"FULL_HISTORY"}
    assert len(first.requests) == 2
    assert all("start_date" not in request.request.parameters for request in first.requests)
    assert all("end_date" not in request.request.parameters for request in first.requests)
    assert first.requests[0].request.requested_fields == tuple(sorted((
        "ts_code", "end_date", "ann_date", "div_proc", "stk_div", "stk_bo_rate",
        "stk_co_rate", "cash_div", "cash_div_tax", "record_date", "ex_date",
        "pay_date", "div_listdate", "imp_ann_date",
    )))


def test_inventory_rejects_noncanonical_symbols_and_revoked_upstream():
    kwargs = dict(
        endpoint="dividend", target_history_start=date(2010, 1, 4),
        baseline_validation_end=date(2025, 12, 31), rolling_coverage_end=date(2026, 9, 9),
        upstream_approval_ids=("master", "calendar"), active_approval_ids=("master", "calendar"),
        revoked_approval_ids=(),
    )
    with pytest.raises(CorporateActionEntryError, match="canonical"):
        build_corporate_action_inventory(symbols=("600000.SH", "000001.SZ"), **kwargs)
    with pytest.raises(CorporateActionEntryError, match="revoked"):
        build_corporate_action_inventory(
            symbols=("000001.SZ",), **{**kwargs, "revoked_approval_ids": ("calendar",)}
        )
