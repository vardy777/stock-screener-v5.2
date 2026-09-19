import ast
from dataclasses import replace
from pathlib import Path

from v5_2.labels.acceptance_v2_contracts import (
    EvidenceClass,
    build_frozen_amendment_v2_1,
)
from v5_2.labels.acceptance_v2_layer_c import (
    EDGE_SEMANTICS_V2_1,
    build_edge_fixture_ledger_v2_1,
    validate_edge_semantics_v2_1,
)


ROOT = Path(__file__).resolve().parents[2]


def test_v2_1_preserves_exact_four_edge_identities_and_semantics():
    ledger = build_edge_fixture_ledger_v2_1(build_frozen_amendment_v2_1())
    assert ledger.verify()
    assert tuple(item.name for item in ledger.fixtures) == EDGE_SEMANTICS_V2_1
    assert tuple(item.fixture_id for item in ledger.fixtures) == (
        "00f7141a55ab44860d79a57d90459a50ad856169c867b1036181a093ca8c33f1",
        "2834dd3367772a4ab283f6f6d944998707e90c0536c17244948d7d8c4388453e",
        "87d3ac4f04c9ca2d1d520e7999ae2327b42a8caba17dcec2966b1cb4c317767a",
        "80169c8c321815d65d5ecda0f9cef3e77ab49de6f506662252f122d583e35a90",
    )
    assert len({item.fixture_id for item in ledger.fixtures}) == 4
    assert all(item.evidence_class is EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE for item in ledger.fixtures)
    assert all(item.production == item.independent and item.disposition == "MATCH" for item in ledger.comparisons)
    assert validate_edge_semantics_v2_1(ledger)


def test_count_preserving_ambiguity_semantic_mutation_fails():
    ledger = build_edge_fixture_ledger_v2_1(build_frozen_amendment_v2_1())
    ambiguity = ledger.fixtures[-1]
    changed_fixture = replace(
        ambiguity,
        name="UPPER_FIRST",
        expected_outcome="UPPER_FIRST",
    )
    changed = replace(ledger, fixtures=(*ledger.fixtures[:-1], changed_fixture))
    assert len(changed.fixtures) == 4
    assert not validate_edge_semantics_v2_1(changed)


def test_independent_calculator_remains_ast_independent():
    tree = ast.parse((ROOT / "src/v5_2/labels/independent_edge_reference.py").read_text(encoding="utf-8"))
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not imports & {
        "v5_2.labels.engine",
        "v5_2.labels.calculation",
        "v5_2.labels.acceptance_v2_layer_c",
    }
