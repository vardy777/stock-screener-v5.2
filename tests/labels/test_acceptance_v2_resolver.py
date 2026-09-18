import ast
import json
from dataclasses import replace
from pathlib import Path

from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import ACCEPTANCE_GATES, build_frozen_inventory
from v5_2.labels.acceptance_v2_boundaries import build_fail_closed_boundary_ledger
from v5_2.labels.acceptance_v2_contracts import build_frozen_amendment_v2, build_gate_consumption_map
from v5_2.labels.acceptance_v2_layer_a import CHECKPOINT7_COMPARISON_LEDGER_ID, build_real_reference_coverage_ledger
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger, build_frozen_edge_fixtures
from v5_2.labels.acceptance_v2_resolver import resolve_phase2a_acceptance_v2


ROOT = Path(__file__).resolve().parents[2]
CA = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"


def artifacts():
    amendment = build_frozen_amendment_v2()
    source = json.loads((ROOT / f"data/phase_2a/reference/full-engine-comparison-{CHECKPOINT7_COMPARISON_LEDGER_ID}.json").read_text())
    inventory = build_frozen_inventory(); assembler = Phase2AEvidenceAssemblerV1(ROOT)
    bundles = tuple(assembler.assemble(x) for x in inventory.slots if x.slot not in {16, 17})
    layer_a = build_real_reference_coverage_ledger(amendment, source, bundles)
    manifest = json.loads((ROOT / f"data/phase_1b2c/governance/corporate-action-manifest-{CA}.json").read_text())
    layer_b = build_fail_closed_boundary_ledger(ROOT, amendment, manifest)
    fixtures = build_frozen_edge_fixtures(amendment)
    layer_c = build_edge_fixture_ledger(amendment, fixtures)
    gate_map = build_gate_consumption_map(amendment, layer_a_id=layer_a.ledger_id, layer_b_id=layer_b.ledger_id, layer_c_id=layer_c.ledger_id)
    return amendment, layer_a, layer_b, layer_c, gate_map


def test_pure_resolver_is_deterministic_and_fails_closed_on_tamper():
    values = artifacts()
    first = resolve_phase2a_acceptance_v2(amendment=values[0], real_reference=values[1], fail_closed=values[2], edge_fixtures=values[3], gate_map=values[4])
    second = resolve_phase2a_acceptance_v2(amendment=values[0], real_reference=values[1], fail_closed=values[2], edge_fixtures=values[3], gate_map=values[4])
    assert first == second and first.verify()
    assert first.gate_results == tuple((name, "PASS") for name in ACCEPTANCE_GATES)
    bad = replace(values[1], content_hash="0" * 64)
    failed = resolve_phase2a_acceptance_v2(amendment=values[0], real_reference=bad, fail_closed=values[2], edge_fixtures=values[3], gate_map=values[4])
    assert failed.phase_2a_status == "FAIL" and not failed.ready_for_phase_2b


def test_resolver_source_has_no_ambient_io_or_provider_dependencies():
    tree = ast.parse((ROOT / "src/v5_2/labels/acceptance_v2_resolver.py").read_text(encoding="utf-8"))
    forbidden_imports = {"os", "pathlib", "requests", "v5_2.providers"}
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(name == bad or name.startswith(bad + ".") for name in imports for bad in forbidden_imports)
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls.intersection({"open", "getenv", "now", "utcnow"})
