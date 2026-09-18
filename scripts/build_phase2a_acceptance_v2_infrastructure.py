from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1  # noqa: E402
from v5_2.labels.acceptance import build_frozen_inventory  # noqa: E402
from v5_2.labels.acceptance_v2_boundaries import build_fail_closed_boundary_ledger  # noqa: E402
from v5_2.labels.acceptance_v2_contracts import build_frozen_amendment_v2, build_gate_consumption_map  # noqa: E402
from v5_2.labels.acceptance_v2_layer_a import CHECKPOINT7_COMPARISON_LEDGER_ID, build_real_reference_coverage_ledger  # noqa: E402
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger, build_frozen_edge_fixtures  # noqa: E402


CA_MANIFEST_ID = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError(f"immutable infrastructure collision: {path.name}")
    path.write_bytes(encoded)


def build_infrastructure(repository_root: Path, output_root: Path) -> dict[str, str]:
    amendment = build_frozen_amendment_v2()
    comparison_path = repository_root / f"data/phase_2a/reference/full-engine-comparison-{CHECKPOINT7_COMPARISON_LEDGER_ID}.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    inventory = build_frozen_inventory()
    assembler = Phase2AEvidenceAssemblerV1(repository_root)
    bundles = tuple(assembler.assemble(slot) for slot in inventory.slots if slot.slot not in {16, 17})
    layer_a = build_real_reference_coverage_ledger(amendment, comparison, bundles)
    ca_path = repository_root / f"data/phase_1b2c/governance/corporate-action-manifest-{CA_MANIFEST_ID}.json"
    layer_b = build_fail_closed_boundary_ledger(repository_root, amendment, json.loads(ca_path.read_text(encoding="utf-8")))
    fixtures = build_frozen_edge_fixtures(amendment)
    layer_c = build_edge_fixture_ledger(amendment, fixtures)
    gate_map = build_gate_consumption_map(
        amendment, layer_a_id=layer_a.ledger_id,
        layer_b_id=layer_b.ledger_id, layer_c_id=layer_c.ledger_id,
    )
    fixture_inventory = {
        "schema_version": "CalculationEdgeFixtureInventoryV2",
        "evidence_class": "SYNTHETIC_CONTRACT_FIXTURE",
        "fixture_ids": tuple(item.fixture_id for item in fixtures),
        "phase1_lineage_claimed": False,
    }
    fixture_inventory_id = content_hash(fixture_inventory)
    output_root.mkdir(parents=True, exist_ok=True)
    outputs = (
        (f"phase2a-architecture-amendment-{amendment.artifact_id}.json", amendment),
        (f"real-reference-coverage-{layer_a.ledger_id}.json", layer_a),
        (f"fail-closed-boundaries-{layer_b.ledger_id}.json", layer_b),
        (f"calculation-edge-fixtures-{layer_c.ledger_id}.json", layer_c),
        (f"gate-artifact-consumption-map-{gate_map.map_id}.json", gate_map),
        (f"calculation-edge-fixture-inventory-{fixture_inventory_id}.json", fixture_inventory),
    )
    for name, value in outputs:
        _write(output_root / name, value)
    return {
        "AMENDMENT V2 ARTIFACT ID": amendment.artifact_id,
        "LAYER A LEDGER ID": layer_a.ledger_id,
        "LAYER B LEDGER ID": layer_b.ledger_id,
        "LAYER C LEDGER ID": layer_c.ledger_id,
        "GATE MAP ID": gate_map.map_id,
        "FIXTURE INVENTORY ID": fixture_inventory_id,
        "CHECKPOINT 11": "INFRASTRUCTURE IMPLEMENTED / AWAITING REVIEW",
        "FINAL V2 ACCEPTANCE": "NOT RUN",
        "PHASE 2A": "FAIL / OPEN",
        "READY FOR PHASE 2B": "NO",
        "PHASE 2B STARTED": "NO",
    }


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/phase_2a/v2_infrastructure"
    print(json.dumps(build_infrastructure(ROOT, destination), indent=2, sort_keys=True))
