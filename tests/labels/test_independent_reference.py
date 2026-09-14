import ast
from dataclasses import replace
from pathlib import Path

from v5_2.labels.acceptance import IndependentLabelCalculationV1, build_comparison_ledger


ROOT = Path(__file__).resolve().parents[2]


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
