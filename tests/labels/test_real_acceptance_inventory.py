from dataclasses import replace

import pytest

from v5_2.labels.acceptance import PHASE2A_STRATA, build_frozen_inventory


def test_inventory_has_exactly_22_named_distinct_slots():
    inventory = build_frozen_inventory()
    assert tuple(item.stratum for item in inventory.slots) == PHASE2A_STRATA
    assert len({(item.security_identity, item.anchor_session) for item in inventory.slots}) == 22


def test_inventory_pins_real_evidence_or_explicit_unavailable():
    inventory = build_frozen_inventory()
    assert all((slot.inventory_status == "EVIDENCE_AVAILABLE" and slot.evidence_ids) or (slot.inventory_status == "EVIDENCE_UNAVAILABLE" and slot.reason) for slot in inventory.slots)
    assert all(slot.source_kind == "REAL_PHASE1_ARTIFACT" for slot in inventory.slots)


def test_inventory_is_deterministic_and_tamper_evident():
    first = build_frozen_inventory(); second = build_frozen_inventory()
    assert first.inventory_id == second.inventory_id and first.verify()
    assert not replace(first, slots=first.slots[:-1]).verify()


def test_selection_rule_is_preregistered_and_does_not_use_engine_result():
    inventory = build_frozen_inventory()
    assert inventory.selection_rule.ordering == "content_hash(contract_version,stratum,canonical_identity,anchor_session)"
    assert "engine" not in inventory.selection_rule.ordering


def test_financial_lineage_is_absent():
    assert all("financial" not in evidence for slot in build_frozen_inventory().slots for evidence in slot.evidence_ids)
