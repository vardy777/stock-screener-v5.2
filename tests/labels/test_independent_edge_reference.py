import ast
from dataclasses import replace
from pathlib import Path

from v5_2.labels.acceptance_v2_contracts import build_frozen_amendment_v2
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger, build_frozen_edge_fixtures
from v5_2.labels.independent_edge_reference import calculate_independent_edge_result, compare_edge_results


ROOT = Path(__file__).resolve().parents[2]


def test_four_edge_cases_match_independent_results_and_detect_mutations():
    fixtures = build_frozen_edge_fixtures(build_frozen_amendment_v2())
    ledger = build_edge_fixture_ledger(build_frozen_amendment_v2(), fixtures)
    assert ledger.verify()
    assert len(ledger.comparisons) == 4
    assert all(x.disposition == "MATCH" for x in ledger.comparisons)
    result = calculate_independent_edge_result(fixtures[0])
    assert compare_edge_results(result, replace(result, mfe_5d="999")).disposition == "MISMATCH"
    assert compare_edge_results(result, replace(result, outcome="NEITHER")).disposition == "MISMATCH"
    assert compare_edge_results(result, replace(result, decisive_session="")).disposition == "MISMATCH"


def test_independent_module_has_no_production_calculation_imports_or_calls():
    path = ROOT / "src/v5_2/labels/independent_edge_reference.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(name in imports for name in (
        "v5_2.labels.engine", "v5_2.labels.calculation", "v5_2.labels.acceptance_v2_layer_c",
    ))
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "calculate_barrier" not in calls
    assert "calculate_outcome_labels" not in calls
