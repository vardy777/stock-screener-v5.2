import json
from dataclasses import replace
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
from v5_2.labels.acceptance_v2_contracts import (
    CalculationEdgeFixtureV2,
    GateArtifactConsumptionMapV2_1,
    GateConsumptionV2_1,
    GateEvidenceV2_1,
    GatePredicateIdV2_1,
    RealReferenceCaseV2,
    build_frozen_amendment_v2_1,
)
from v5_2.labels.acceptance_v2_layer_a import (
    CHECKPOINT7_COMPARISON_LEDGER_ID,
    RealReferenceCoverageLedgerV2_1,
    build_real_reference_coverage_ledger_v2_1,
)
from v5_2.labels.acceptance_v2_layer_c import (
    CalculationEdgeFixtureLedgerV2_1,
    build_edge_fixture_ledger_v2_1,
)


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


def _without_role(evidence, removed_role):
    cases = tuple(
        RealReferenceCaseV2.create(**{
            name: (("NORMAL_POSITIVE_RETURN",) if name == "semantic_roles" else getattr(case, name))
            for name in case.__dataclass_fields__ if name != "content_hash"
        }) if removed_role in case.semantic_roles else case
        for case in evidence.layer_a.cases
    )
    layer_a = RealReferenceCoverageLedgerV2_1.create(
        amendment_id=evidence.layer_a.amendment_id,
        checkpoint7_comparison_ledger_id=evidence.layer_a.checkpoint7_comparison_ledger_id,
        cases=cases,
    )
    return replace(evidence, layer_a=layer_a)


@pytest.mark.parametrize(
    ("role", "gate"),
    (
        ("SUSPENSION_THROUGH_H5", "SUSPENSION SAFETY"),
        ("LATEST-SESSION_LABEL_PENDING", "LABEL_PENDING"),
        ("NORMAL_NEGATIVE_RETURN", "RETURN SEMANTICS"),
    ),
)
def test_count_preserving_layer_a_role_loss_fails_owning_gate(evidence, role, gate):
    changed = _without_role(evidence, role)
    assert len(changed.layer_a.cases) == 20
    assert evaluate_gate_v2_1(gate, changed).status == "FAIL"


@pytest.mark.parametrize(
    ("category", "gate"),
    (
        ("UNEXPLAINED_MISSING_BAR", "MISSING DATA FAIL-CLOSED"),
        ("UNSUPPORTED_CA", "CORPORATE ACTION SAFETY"),
    ),
)
def test_count_preserving_layer_b_semantic_loss_fails_owning_gate(evidence, category, gate):
    target = next(case for case in evidence.layer_b.cases if case.semantic_category == category)
    replacement = next(case for case in evidence.layer_b.cases if case.semantic_category != category)
    cases = tuple(replacement if case is target else case for case in evidence.layer_b.cases)
    layer_b = type(evidence.layer_b).create(amendment_id=evidence.layer_b.amendment_id, cases=cases)
    changed = replace(evidence, layer_b=layer_b)
    assert len(changed.layer_b.cases) == 10
    assert evaluate_gate_v2_1(gate, changed).status == "FAIL"


def test_count_preserving_layer_c_ambiguity_loss_fails_barrier_gate(evidence):
    old = evidence.layer_c.fixtures[-1]
    changed_fixture = CalculationEdgeFixtureV2.create(**{
        name: ("UPPER_FIRST" if name in {"name", "expected_outcome"} else getattr(old, name))
        for name in old.__dataclass_fields__ if name not in {"fixture_id", "content_hash"}
    })
    layer_c = CalculationEdgeFixtureLedgerV2_1.create(
        amendment_id=evidence.layer_c.amendment_id,
        fixtures=(*evidence.layer_c.fixtures[:-1], changed_fixture),
        comparisons=evidence.layer_c.comparisons,
    )
    changed = replace(evidence, layer_c=layer_c)
    assert len(changed.layer_c.fixtures) == 4
    assert evaluate_gate_v2_1("BARRIER SEMANTICS", changed).status == "FAIL"


def test_count_preserving_gate_map_predicate_swap_fails_gate(evidence):
    entries = list(evidence.gate_map.entries)
    old = entries[0]
    entries[0] = GateConsumptionV2_1.create(
        gate=old.gate,
        predicate_id=GatePredicateIdV2_1.RETURN_SEMANTICS,
        artifact_ids=old.artifact_ids,
    )
    gate_map = GateArtifactConsumptionMapV2_1.create(
        amendment_id=evidence.gate_map.amendment_id,
        entries=tuple(entries),
    )
    changed = replace(evidence, gate_map=gate_map)
    assert len(changed.gate_map.entries) == 16
    assert evaluate_gate_v2_1("LABEL CONTRACT", changed).status == "FAIL"
