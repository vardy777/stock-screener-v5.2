import ast
from dataclasses import replace
import importlib.util
from pathlib import Path

import pytest

from v5_2.labels.acceptance import (
    IndependentLabelCalculationV1, build_comparison_ledger,
    build_full_comparison_entry, FullComparisonLedgerV1,
)
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.independent_reference import calculate_independent_reference
from v5_2.labels.engine import ReferenceLabelEngine


ROOT = Path(__file__).resolve().parents[2]
REAL_EVIDENCE = ROOT / "data/phase_2a/governance/label-acceptance-inventory-81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9.json"
requires_real_evidence = pytest.mark.skipif(not REAL_EVIDENCE.exists(), reason="repository-local immutable evidence is excluded from clean room")


def test_full_reference_module_exists():
    assert importlib.util.find_spec("v5_2.labels.independent_reference") is not None


def calculation(value="0.10000000"):
    return IndependentLabelCalculationV1.create(slot=1, inventory_evidence_id="a"*64, status="CALCULATED", horizons=("2024-01-03", "2024-01-05", "2024-01-09"), inputs_hash="b"*64, result_summary=(("return_1d", "LABEL_AVAILABLE", value, ""),), method_version="phase2a-independent-v1")


def test_independent_script_does_not_import_engine_or_calculation():
    tree = ast.parse((ROOT / "scripts/verify_phase2a_reference.py").read_text(encoding="utf-8"))
    modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert "v5_2.labels.engine" not in modules and "v5_2.labels.calculation" not in modules


def test_independent_calculation_is_deterministic_and_tamper_evident():
    first = calculation(); second = calculation()
    assert first.calculation_id == second.calculation_id and first.verify()
    assert not replace(first, inputs_hash="c"*64).verify()


def test_comparison_detects_field_mismatch():
    match = build_comparison_ledger((calculation(),), {1: (("return_1d", "LABEL_AVAILABLE", "0.10000000", ""),)})
    mismatch = build_comparison_ledger((calculation(),), {1: (("return_1d", "LABEL_AVAILABLE", "0.20000000", ""),)})
    assert match.entries[0].disposition == "MATCH"
    assert mismatch.entries[0].disposition == "MISMATCH"


def test_unavailable_calculation_cannot_match():
    item = IndependentLabelCalculationV1.create(slot=2, inventory_evidence_id="a"*64, status="EVIDENCE_UNAVAILABLE", horizons=(), inputs_hash=None, result_summary=(), method_version="phase2a-independent-v1", reason="EXACT_BUNDLE_UNAVAILABLE")
    ledger = build_comparison_ledger((item,), {})
    assert ledger.entries[0].disposition == "EVIDENCE_UNAVAILABLE"


@requires_real_evidence
def test_full_reference_records_inputs_steps_lineage_and_barrier_truth():
    bundle = Phase2AEvidenceAssemblerV1(ROOT).assemble(build_frozen_inventory().slots[0])
    result = calculate_independent_reference(1, bundle)
    assert result.verify()
    assert result.bundle_id == bundle.content_hash
    assert result.lineage_digest
    assert len(result.horizons) == 3
    assert len(result.economic_steps) == 5
    assert len(result.result_summary) == 7
    assert len(result.barriers) == 2
    assert all(item.outcome in {"UPPER_FIRST", "LOWER_FIRST", "NEITHER"} for item in result.barriers)


def test_independent_reference_does_not_import_production_engine_or_calculation():
    tree = ast.parse((ROOT / "src/v5_2/labels/independent_reference.py").read_text(encoding="utf-8"))
    modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert "v5_2.labels.engine" not in modules
    assert "v5_2.labels.calculation" not in modules


@requires_real_evidence
def test_independent_reference_replays_identically():
    bundle = Phase2AEvidenceAssemblerV1(ROOT).assemble(build_frozen_inventory().slots[5])
    first = calculate_independent_reference(6, bundle)
    second = calculate_independent_reference(6, bundle)
    assert first.reference_id == second.reference_id
    assert first == second


@requires_real_evidence
def test_full_comparison_records_every_required_dimension():
    slot = build_frozen_inventory().slots[0]
    bundle = Phase2AEvidenceAssemblerV1(ROOT).assemble(slot)
    production = ReferenceLabelEngine().evaluate(bundle)
    independent = calculate_independent_reference(slot.slot, bundle)
    entry = build_full_comparison_entry(slot, bundle, production, independent)
    assert entry.disposition == "MATCH"
    assert entry.numeric_match and entry.state_match and entry.reason_match
    assert entry.barrier_categorical_match and entry.barrier_decisive_session_match
    assert entry.lineage_validation
    assert len(entry.five_domain_lineage_ids) == 5
    assert entry.production_result_hash == production.content_hash
    assert entry.independent_result_hash == independent.content_hash
    assert entry.verify()


@requires_real_evidence
def test_full_comparison_detects_independent_numeric_mutation():
    slot = build_frozen_inventory().slots[0]
    bundle = Phase2AEvidenceAssemblerV1(ROOT).assemble(slot)
    production = ReferenceLabelEngine().evaluate(bundle)
    independent = calculate_independent_reference(slot.slot, bundle)
    changed = list(independent.result_summary)
    changed[0] = (changed[0][0], changed[0][1], "9.00000000", changed[0][3])
    tampered = replace(independent, result_summary=tuple(changed))
    entry = build_full_comparison_entry(slot, bundle, production, tampered)
    assert entry.disposition == "MISMATCH"
    assert not entry.numeric_match


@requires_real_evidence
def test_ambiguous_barrier_preserves_both_categorical_truths_for_comparison():
    slot = build_frozen_inventory().slots[11]
    bundle = Phase2AEvidenceAssemblerV1(ROOT).assemble(slot)
    production = ReferenceLabelEngine().evaluate(bundle)
    independent = calculate_independent_reference(slot.slot, bundle)
    entry = build_full_comparison_entry(slot, bundle, production, independent)
    assert len(production.barrier_evidence) == 2
    assert entry.production_barriers == entry.independent_barriers
    assert entry.disposition == "MATCH"


def test_full_ledger_requires_exact_22_distinct_slots():
    with pytest.raises(ValueError, match="exact 22"):
        FullComparisonLedgerV1.create(entries=())
