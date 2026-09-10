from datetime import date

import pytest

from v5_2.data.real_audits.corporate_action_entry import (
    CorporateActionEntryError,
    build_corporate_action_inventory,
)


def test_inventory_separates_baseline_and_catchup_and_is_deterministic():
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
    assert {request.segment for request in first.requests} == {"BASELINE", "CATCH_UP"}
    assert len(first.requests) == 4


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

