from v5_2.data.real_audits.daily_bar_inventory import DailyBarRequestInventoryV1, DeterministicDailyBarUniverseV1


def test_daily_bar_inventory_is_deterministic_and_never_acquires() -> None:
    universe = DeterministicDailyBarUniverseV1.create(
        upstream_approval_ids=("calendar", "master"), symbols=("000002.SZ", "000001.SZ"),
        sessions=("2025-01-03", "2025-01-02"), exception_set_hash="exceptions",
    )
    inventory = DailyBarRequestInventoryV1.create(
        universe=universe, sample_strata=("exchange", "year"), volume_unit_audit="REQUIRED",
        amount_unit_audit="REQUIRED", cross_source_rule="OFFICIAL_OR_INDEPENDENT_REQUIRED",
    )
    assert universe.ordered_symbols == ("000001.SZ", "000002.SZ")
    assert universe.adjustment == "UNADJUSTED_RAW"
    assert not inventory.acquisition_started
    assert len(inventory.request_ids) == 2
