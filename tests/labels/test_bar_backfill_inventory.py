from pathlib import Path

from v5_2.data.real_audits.phase2a_bar_backfill import build_bar_backfill_inventory


ROOT = Path(__file__).resolve().parents[2]


def test_backfill_inventory_contains_only_the_ten_frozen_real_evidence_gaps():
    inventory = build_bar_backfill_inventory(ROOT)

    assert tuple(item.slot for item in inventory.slots) == (6, 7, 8, 9, 10, 11, 12, 13, 14, 17)
    assert len({item.canonical_identity for item in inventory.slots}) == 10
    assert inventory.verify()


def test_backfill_inventory_pins_exact_horizons_and_required_sessions():
    inventory = build_bar_backfill_inventory(ROOT)
    by_slot = {item.slot: item for item in inventory.slots}

    assert by_slot[6].h1.isoformat() == "2021-06-02"
    assert by_slot[6].h3.isoformat() == "2021-06-04"
    assert by_slot[6].h5.isoformat() == "2021-06-08"
    assert by_slot[6].required_bar_sessions == (by_slot[6].anchor_session, *by_slot[6].window_5d)
    assert by_slot[8].window_5d[0].isoformat() == "2010-05-19"
    assert by_slot[8].window_5d[0] not in by_slot[8].required_bar_sessions
    assert by_slot[8].status_explained_absence_sessions == (by_slot[8].window_5d[0],)


def test_request_inventory_is_minimal_deterministic_and_reuses_phase1_contract():
    inventory = build_bar_backfill_inventory(ROOT)

    assert len(inventory.requests) == 10
    assert len({item.provider_request.request_id for item in inventory.requests}) == 10
    assert all(item.provider_request.endpoint == "daily" for item in inventory.requests)
    assert all(item.provider_request.dataset_kind == "daily_bar" for item in inventory.requests)
    assert all(item.provider_request.requested_fields == tuple(sorted(("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"))) for item in inventory.requests)
    assert inventory.content_hash == build_bar_backfill_inventory(ROOT).content_hash
