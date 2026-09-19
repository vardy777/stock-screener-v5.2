import json
from pathlib import Path

import pytest

from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import ACCEPTANCE_GATES, build_frozen_inventory
from v5_2.labels.acceptance_v2_1_predicates import (
    GATE_PREDICATES_V2_1,
    build_gate_consumption_map_v2_1,
    evaluate_gate_v2_1,
)
from v5_2.labels.acceptance_v2_boundaries import build_fail_closed_boundary_ledger_v2_1
from v5_2.labels.acceptance_v2_contracts import GateEvidenceV2_1, build_frozen_amendment_v2_1
from v5_2.labels.acceptance_v2_layer_a import (
    CHECKPOINT7_COMPARISON_LEDGER_ID,
    build_real_reference_coverage_ledger_v2_1,
)
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger_v2_1


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


@pytest.fixture(scope="module")
def evidence():
    amendment = build_frozen_amendment_v2_1()
    source = json.loads(
        (ROOT / f"data/phase_2a/reference/full-engine-comparison-{CHECKPOINT7_COMPARISON_LEDGER_ID}.json").read_text()
    )
    inventory = build_frozen_inventory()
    assembler = Phase2AEvidenceAssemblerV1(ROOT)
    bundles = tuple(assembler.assemble(slot) for slot in inventory.slots if slot.slot not in {16, 17})
    layer_a = build_real_reference_coverage_ledger_v2_1(amendment, source, bundles)
    layer_b = build_fail_closed_boundary_ledger_v2_1(ROOT, amendment)
    layer_c = build_edge_fixture_ledger_v2_1(amendment)
    gate_map = build_gate_consumption_map_v2_1(amendment, layer_a, layer_b, layer_c)
    return GateEvidenceV2_1(
        amendment=amendment,
        layer_a=layer_a,
        layer_b=layer_b,
        layer_c=layer_c,
        gate_map=gate_map,
        supersession=None,
        contract_identity_verified=True,
        exact_five_domains_verified=True,
        ast_isolation_verified=True,
        replay_bytes_match=True,
    )


@pytest.mark.parametrize("gate", ACCEPTANCE_GATES)
def test_each_exact_gate_executes_its_literal_predicate(gate, evidence):
    result = evaluate_gate_v2_1(gate, evidence)
    assert result.gate == gate
    assert result.status == "PASS"
    assert result.predicate_id == GATE_PREDICATES_V2_1[gate][0]
    assert result.verify()


def test_alias_is_not_accepted(evidence):
    with pytest.raises(ValueError, match="exact gate"):
        evaluate_gate_v2_1("LABEL_CONTRACT", evidence)
