import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import ACCEPTANCE_GATES, build_frozen_inventory
from v5_2.labels.acceptance_v2_1_predicates import build_gate_consumption_map_v2_1
from v5_2.labels.acceptance_v2_1_resolver import resolve_phase2a_acceptance_v2_1_infrastructure
from v5_2.labels.acceptance_v2_boundaries import (
    build_fail_closed_boundary_ledger_v2_1,
    build_missing_bar_boundary_case_v2_1,
    build_unsupported_ca_boundary_case_v2_1,
)
from v5_2.labels.acceptance_v2_contracts import (
    ATTEMPT1_INFRASTRUCTURE_IDS,
    AttemptInfrastructureSupersessionV2_1,
    build_frozen_amendment_v2_1,
)
from v5_2.labels.acceptance_v2_layer_a import CHECKPOINT7_COMPARISON_LEDGER_ID, build_real_reference_coverage_ledger_v2_1
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger_v2_1


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


class RaisingEngine:
    def __getattr__(self, name):
        raise AssertionError(f"engine must be structurally unreachable: {name}")


def artifacts():
    amendment = build_frozen_amendment_v2_1()
    source = json.loads((ROOT / f"data/phase_2a/reference/full-engine-comparison-{CHECKPOINT7_COMPARISON_LEDGER_ID}.json").read_text())
    inventory = build_frozen_inventory(); assembler = Phase2AEvidenceAssemblerV1(ROOT)
    bundles = tuple(assembler.assemble(x) for x in inventory.slots if x.slot not in {16, 17})
    a = build_real_reference_coverage_ledger_v2_1(amendment, source, bundles)
    b = build_fail_closed_boundary_ledger_v2_1(ROOT, amendment)
    c = build_edge_fixture_ledger_v2_1(amendment)
    gate_map = build_gate_consumption_map_v2_1(amendment, a, b, c)
    attempt2 = (amendment.artifact_id, a.ledger_id, b.ledger_id, c.ledger_id, gate_map.map_id, "f" * 64)
    supersession = AttemptInfrastructureSupersessionV2_1.create(
        amendment_id=amendment.artifact_id,
        attempt1_ids=ATTEMPT1_INFRASTRUCTURE_IDS,
        attempt2_ids=attempt2,
        reason="INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT",
    )
    return amendment, supersession, a, b, c, gate_map


def resolve(values):
    return resolve_phase2a_acceptance_v2_1_infrastructure(
        amendment=values[0], supersession=values[1], real_reference=values[2],
        fail_closed=values[3], edge_fixtures=values[4], gate_map=values[5],
        contract_identity_verified=True, exact_five_domains_verified=True,
        ast_isolation_verified=True, replay_bytes_match=True,
    )


def test_pure_resolver_is_deterministic_and_never_creates_final_acceptance():
    values = artifacts()
    first = resolve(values); second = resolve(values)
    assert first == second and first.verify()
    assert first.gate_results == tuple((name, "PASS") for name in ACCEPTANCE_GATES)
    assert first.infrastructure_status == "PASS"
    assert first.final_acceptance_created is False
    assert first.ready_for_phase_2b is False


@pytest.mark.parametrize("index", (0, 2, 3, 4, 5))
def test_integrity_failure_fails_all_gates(index):
    values = list(artifacts())
    field = "content_hash"
    values[index] = replace(values[index], **{field: "0" * 64})
    result = resolve(tuple(values))
    assert result.gate_results == tuple((name, "FAIL") for name in ACCEPTANCE_GATES)


def test_supersession_mismatch_fails_all_gates():
    values = list(artifacts())
    values[1] = replace(values[1], content_hash="0" * 64)
    result = resolve(tuple(values))
    assert result.gate_results == tuple((name, "FAIL") for name in ACCEPTANCE_GATES)


def test_boundary_builders_make_engine_structurally_unreachable():
    assert build_missing_bar_boundary_case_v2_1(ROOT, engine=RaisingEngine()).engine_invocation_count == 0
    assert build_unsupported_ca_boundary_case_v2_1(ROOT, engine=RaisingEngine()).engine_invocation_count == 0


def test_resolver_source_has_no_ambient_io_engine_provider_or_network():
    path = ROOT / "src/v5_2/labels/acceptance_v2_1_resolver.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    forbidden = {"os", "pathlib", "datetime", "requests", "v5_2.providers", "v5_2.labels.engine"}
    assert not any(name == item or name.startswith(item + ".") for name in imports for item in forbidden)
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls & {"open", "getenv", "now", "utcnow", "ReferenceLabelEngine"}
    assert not hasattr(__import__("v5_2.labels.acceptance_v2_contracts", fromlist=["x"]), "Phase2AAcceptanceV2_1")
