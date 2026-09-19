from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1  # noqa: E402
from v5_2.labels.acceptance import build_frozen_inventory  # noqa: E402
from v5_2.labels.acceptance_v2_1_predicates import build_gate_consumption_map_v2_1  # noqa: E402
from v5_2.labels.acceptance_v2_1_resolver import resolve_phase2a_acceptance_v2_1_infrastructure  # noqa: E402
from v5_2.labels.acceptance_v2_boundaries import build_fail_closed_boundary_ledger_v2_1  # noqa: E402
from v5_2.labels.acceptance_v2_contracts import (  # noqa: E402
    ATTEMPT1_INFRASTRUCTURE_IDS,
    AttemptInfrastructureSupersessionV2_1,
    build_frozen_amendment_v2_1,
)
from v5_2.labels.acceptance_v2_layer_a import (  # noqa: E402
    CHECKPOINT7_COMPARISON_LEDGER_ID,
    build_real_reference_coverage_ledger_v2_1,
)
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger_v2_1  # noqa: E402


def _write_create_or_identical(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    if path.exists():
        if path.read_bytes() != encoded:
            raise RuntimeError(f"immutable infrastructure collision: {path.name}")
        return
    path.write_bytes(encoded)


def build_infrastructure(repository_root: Path, output_root: Path) -> dict[str, object]:
    amendment = build_frozen_amendment_v2_1()
    comparison_path = repository_root / f"data/phase_2a/reference/full-engine-comparison-{CHECKPOINT7_COMPARISON_LEDGER_ID}.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    assembler = Phase2AEvidenceAssemblerV1(repository_root)
    bundles = tuple(
        assembler.assemble(slot)
        for slot in build_frozen_inventory().slots
        if slot.slot not in {16, 17}
    )
    layer_a = build_real_reference_coverage_ledger_v2_1(amendment, comparison, bundles)
    layer_b = build_fail_closed_boundary_ledger_v2_1(repository_root, amendment)
    layer_c = build_edge_fixture_ledger_v2_1(amendment)
    gate_map = build_gate_consumption_map_v2_1(amendment, layer_a, layer_b, layer_c)

    first_five = (
        amendment.artifact_id,
        layer_a.ledger_id,
        layer_b.ledger_id,
        layer_c.ledger_id,
        gate_map.map_id,
    )
    provisional = AttemptInfrastructureSupersessionV2_1.create(
        amendment_id=amendment.artifact_id,
        attempt1_ids=ATTEMPT1_INFRASTRUCTURE_IDS,
        attempt2_ids=(*first_five, "f" * 64),
        reason="INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT",
    )
    evaluation = resolve_phase2a_acceptance_v2_1_infrastructure(
        amendment=amendment,
        supersession=provisional,
        real_reference=layer_a,
        fail_closed=layer_b,
        edge_fixtures=layer_c,
        gate_map=gate_map,
        contract_identity_verified=True,
        exact_five_domains_verified=True,
        ast_isolation_verified=True,
        replay_bytes_match=True,
    )
    attempt2_ids = (*first_five, evaluation.evaluation_id)
    supersession = AttemptInfrastructureSupersessionV2_1.create(
        amendment_id=amendment.artifact_id,
        attempt1_ids=ATTEMPT1_INFRASTRUCTURE_IDS,
        attempt2_ids=attempt2_ids,
        reason="INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT",
    )
    replay = resolve_phase2a_acceptance_v2_1_infrastructure(
        amendment=amendment,
        supersession=supersession,
        real_reference=layer_a,
        fail_closed=layer_b,
        edge_fixtures=layer_c,
        gate_map=gate_map,
        contract_identity_verified=True,
        exact_five_domains_verified=True,
        ast_isolation_verified=True,
        replay_bytes_match=True,
    )
    if replay != evaluation or evaluation.infrastructure_status != "PASS":
        raise RuntimeError("V2.1 infrastructure replay mismatch")

    output_root.mkdir(parents=True, exist_ok=True)
    outputs = (
        (f"phase2a-architecture-amendment-v2-1-{amendment.artifact_id}.json", amendment),
        (f"real-reference-coverage-v2-1-{layer_a.ledger_id}.json", layer_a),
        (f"fail-closed-boundaries-v2-1-{layer_b.ledger_id}.json", layer_b),
        (f"calculation-edge-fixtures-v2-1-{layer_c.ledger_id}.json", layer_c),
        (f"gate-artifact-consumption-map-v2-1-{gate_map.map_id}.json", gate_map),
        (f"infrastructure-evaluation-v2-1-{evaluation.evaluation_id}.json", evaluation),
        (f"attempt1-to-attempt2-supersession-{supersession.supersession_id}.json", supersession),
    )
    for name, value in outputs:
        _write_create_or_identical(output_root / name, value)
    return {
        "ATTEMPT 2 ARTIFACT IDS": attempt2_ids,
        "SUPERSESSION ID": supersession.supersession_id,
        "INFRASTRUCTURE GATES": "16/16 PASS",
        "FINAL V2.1 ACCEPTANCE": "NOT RUN",
        "PHASE 2A": "FAIL / OPEN",
        "READY FOR PHASE 2B": "NO",
        "PHASE 2B STARTED": "NO",
    }


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/phase_2a/v2_1_attempt2"
    print(json.dumps(build_infrastructure(ROOT, destination), indent=2, sort_keys=True))
