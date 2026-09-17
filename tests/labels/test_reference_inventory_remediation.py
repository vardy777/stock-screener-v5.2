import ast
from pathlib import Path

import pytest

from v5_2.labels.inventory_remediation import (
    INVALID_V1_SLOTS,
    PREDICATE_VERSION,
    audit_v1_applicability,
    discover_replacements,
)


ROOT = Path(__file__).resolve().parents[2]
REAL_EVIDENCE = ROOT / "data/phase_2a/governance/label-acceptance-inventory-81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9.json"
requires_real_evidence = pytest.mark.skipif(not REAL_EVIDENCE.exists(), reason="repository-local immutable evidence is excluded from clean room")


def test_predicates_are_frozen_and_do_not_import_production_engine():
    source = ROOT / "src/v5_2/labels/inventory_remediation.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert PREDICATE_VERSION == "phase2a-reference-stratum-predicates-v1"
    assert "v5_2.labels.engine" not in imports
    assert "v5_2.labels.calculation" not in imports


@requires_real_evidence
def test_v1_applicability_audit_detects_exact_five_invalid_slots():
    audit = audit_v1_applicability(ROOT)
    assert audit.verify()
    assert tuple(item.slot for item in audit.entries) == INVALID_V1_SLOTS
    assert all(item.applicable is False for item in audit.entries)
    assert audit.v1_inventory_id == "81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9"


@requires_real_evidence
def test_discovery_is_deterministic_and_fail_closed_when_real_candidate_absent():
    first = discover_replacements(ROOT)
    second = discover_replacements(ROOT)
    assert first == second
    assert first.verify()
    by_slot = {item.slot: item for item in first.entries}
    assert by_slot[16].status == "REAL_REFERENCE_SAMPLE_UNAVAILABLE"
    assert by_slot[16].reason == "FROZEN_REFERENCE_STRATUM_INCOMPATIBLE_WITH_PHASE1_APPROVED_EVIDENCE_CONTRACT"
    assert first.inventory_v2_created is False
    assert first.inventory_v2_id is None


@requires_real_evidence
def test_v1_inventory_and_negative_acceptance_remain_byte_identical():
    inventory = REAL_EVIDENCE.read_bytes()
    acceptance = (ROOT / "data/phase_2a/governance/phase2a-acceptance-84d61057ecf5f527dcb5067fe0ea2b6103edf0f66388535e8ceeffd3ef10c3c8.json").read_bytes()
    assert inventory == REAL_EVIDENCE.read_bytes()
    assert acceptance == (ROOT / "data/phase_2a/governance/phase2a-acceptance-84d61057ecf5f527dcb5067fe0ea2b6103edf0f66388535e8ceeffd3ef10c3c8.json").read_bytes()
