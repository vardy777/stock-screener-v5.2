from __future__ import annotations

import pytest

from v5_2.data.identity import content_hash
from v5_2.data.real_audits.daily_bar_entry import DailyBarEntryError, build_acquisition_plan


UPSTREAM = ("calendar", "master")


def _universe():
    values = {"upstream_approval_ids": UPSTREAM, "ordered_symbols": ("000001.SZ", "600000.SH"),
              "ordered_sessions": ("20100104", "20251231"), "adjustment": "UNADJUSTED_RAW",
              "exception_set_hash": "exceptions"}
    digest = content_hash({"schema_version": "DeterministicDailyBarUniverseV1", **values})
    return {"universe_id": digest, "content_hash": digest, **values}


def _inventory(universe):
    logical = tuple(content_hash({"schema_version": "DailyBarLogicalRequestV1", "universe_id": universe["universe_id"],
                                  "symbol": symbol, "start": "20100104", "end": "20251231",
                                  "adjustment": "UNADJUSTED_RAW"}) for symbol in universe["ordered_symbols"])
    values = {"universe_id": universe["universe_id"], "request_ids": logical,
              "sample_strata": ("exchange",), "volume_unit_audit": "REQUIRED",
              "amount_unit_audit": "REQUIRED", "cross_source_rule": "REQUIRED", "acquisition_started": False}
    digest = content_hash({"schema_version": "DailyBarRequestInventoryV1", **values})
    return {"inventory_id": digest, "content_hash": digest, **values}


def test_frozen_entry_maps_every_logical_request_to_canonical_provider_request() -> None:
    universe = _universe()
    plan = build_acquisition_plan(universe, _inventory(universe), active_approval_ids=UPSTREAM, revoked_approval_ids=())
    assert tuple(item.logical_request_id for item in plan.requests) == _inventory(universe)["request_ids"]
    assert len({item.provider_request.request_id for item in plan.requests}) == 2
    assert all(item.provider_request.endpoint == "daily" for item in plan.requests)
    assert all("adj" not in item.provider_request.parameters for item in plan.requests)
    assert plan.adjustment == "UNADJUSTED_RAW"


@pytest.mark.parametrize("mutation", ("hash", "adjustment", "order", "revoked"))
def test_frozen_entry_fails_closed_on_tamper_or_upstream_revocation(mutation) -> None:
    universe = _universe()
    inventory = _inventory(universe)
    revoked = ()
    if mutation == "hash":
        inventory["content_hash"] = "tampered"
    elif mutation == "adjustment":
        universe["adjustment"] = "qfq"
    elif mutation == "order":
        universe["ordered_symbols"] = tuple(reversed(universe["ordered_symbols"]))
    else:
        revoked = ("calendar",)
    with pytest.raises(DailyBarEntryError):
        build_acquisition_plan(universe, inventory, active_approval_ids=UPSTREAM, revoked_approval_ids=revoked)
