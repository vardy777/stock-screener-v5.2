from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import ACCEPTANCE_GATES, build_frozen_inventory
from v5_2.labels.acceptance_v2_1_predicates import build_gate_consumption_map_v2_1
from v5_2.labels.acceptance_v2_1_resolver import resolve_phase2a_acceptance_v2_1_infrastructure
from v5_2.labels.acceptance_v2_boundaries import build_fail_closed_boundary_ledger_v2_1
from v5_2.labels.acceptance_v2_contracts import (
    ATTEMPT1_INFRASTRUCTURE_IDS,
    AttemptInfrastructureSupersessionV2_1,
    build_frozen_amendment_v2_1,
)
from v5_2.labels.acceptance_v2_layer_a import (
    CHECKPOINT7_COMPARISON_LEDGER_ID,
    build_real_reference_coverage_ledger_v2_1,
)
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger_v2_1


V2_1_DESIGN_HEAD = "a66825e25d40a46eceae18a50f1f2535ab9ee975"
V2_1_DESIGN_AMENDMENT_ID = "d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b"
ATTEMPT2_PLAN_ID = "d9cfcf4822bd0d617e1e599e35fde0b939de03cd"
FROZEN_INFRASTRUCTURE_HEAD = "6e436f5da10fc9d2ba5825897f209f018e35d5bf"
FROZEN_ATTEMPT2_ARTIFACT_IDS = (
    "fadd791ac0562cf218a6e52954c36eff05244d6b69e7a70cb38814b256fb98d5",
    "da6356776020f8d32737184bbd7759e3ecdee49ce8dc67784fe4dda3d9840ec4",
    "161f59093ac9e9949de007bf08989e1220b8a2177991a604ad48cee2c70428a4",
    "5d4cfa298891ad0cf1f2e997429d7e2f505a97f63e66acc9e8a9970ad1c16f4f",
    "fe268e2d080580485715bb69eefc4c6ebc144b959c404ff0f50692be12d685bb",
    "edf35f614c2631b352b47c5680354b86e517a23f7ae620fa0d285a3ec90f407c",
)
FROZEN_SUPERSESSION_ID = "37279c7e92bd33891c833eb95dae1cfc4d104388acc03f01d0ee810f216b390c"


@dataclass(frozen=True, slots=True)
class FreshInfrastructureV2_1:
    amendment: object
    layer_a: object
    layer_b: object
    layer_c: object
    gate_map: object
    evaluation: object
    supersession: object


@dataclass(frozen=True, slots=True)
class Phase2AAcceptanceV2_1:
    schema_version: str
    v2_1_design_head: str
    v2_1_design_amendment_id: str
    attempt2_plan_id: str
    frozen_infrastructure_head: str
    infrastructure_artifact_ids: tuple[str, ...]
    supersession_id: str
    gate_results: tuple[tuple[str, str], ...]
    overall_status: str
    phase_2a_status: str
    ready_for_phase_2b: bool
    phase_2b_started: bool
    acceptance_id: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        if values["schema_version"] != "Phase2AAcceptanceV2_1":
            raise ValueError("invalid final acceptance schema")
        if tuple(values["infrastructure_artifact_ids"]) != FROZEN_ATTEMPT2_ARTIFACT_IDS:
            raise ValueError("exact frozen Attempt 2 artifact IDs required")
        if values["supersession_id"] != FROZEN_SUPERSESSION_ID:
            raise ValueError("exact Attempt 2 supersession required")
        if tuple(values["gate_results"]) != tuple((gate, "PASS") for gate in ACCEPTANCE_GATES):
            raise ValueError("all 16 exact gates must pass final acceptance")
        if (
            values["overall_status"] != "PASS"
            or values["phase_2a_status"] != "PASS / CLOSED"
            or values["ready_for_phase_2b"] is not True
            or values["phase_2b_started"] is not False
        ):
            raise ValueError("invalid final Phase 2A status")
        body = dict(values)
        digest = content_hash({"schema_version": cls.__name__, **body})
        return cls(**body, acceptance_id=digest, content_hash=digest)

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in self.__dataclass_fields__ if name not in {"acceptance_id", "content_hash"}}
        try:
            rebuilt = type(self).create(**body)
        except ValueError:
            return False
        return self.acceptance_id == self.content_hash == rebuilt.acceptance_id


def _attempt2_paths(repository_root: Path) -> tuple[Path, ...]:
    root = repository_root / "data/phase_2a/v2_1_attempt2"
    prefixes = (
        "phase2a-architecture-amendment-v2-1",
        "real-reference-coverage-v2-1",
        "fail-closed-boundaries-v2-1",
        "calculation-edge-fixtures-v2-1",
        "gate-artifact-consumption-map-v2-1",
        "infrastructure-evaluation-v2-1",
    )
    return tuple(root / f"{prefix}-{identity}.json" for prefix, identity in zip(prefixes, FROZEN_ATTEMPT2_ARTIFACT_IDS))


def _verify_exact_bytes(path: Path, expected: object) -> None:
    if not path.is_file():
        raise ValueError(f"frozen infrastructure artifact missing: {path.name}")
    if path.read_bytes() != canonical_json(expected):
        raise ValueError(f"frozen infrastructure artifact identity mismatch: {path.name}")


def _ast_isolation_verified(repository_root: Path) -> bool:
    paths = (
        repository_root / "src/v5_2/labels/acceptance_v2_1_predicates.py",
        repository_root / "src/v5_2/labels/acceptance_v2_1_resolver.py",
        repository_root / "src/v5_2/labels/independent_edge_reference.py",
    )
    forbidden = {"os", "pathlib", "requests", "socket", "httpx", "v5_2.providers", "v5_2.labels.engine"}
    forbidden_calls = {"open", "getenv", "now", "utcnow", "ReferenceLabelEngine"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        if any(name == prefix or name.startswith(prefix + ".") for name in imports for prefix in forbidden):
            return False
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        if calls & forbidden_calls:
            return False
    return True


def _validate_critical_boundaries(layer_b: object) -> None:
    missing = next((case for case in layer_b.cases if case.semantic_category == "UNEXPLAINED_MISSING_BAR"), None)
    unsupported = next((case for case in layer_b.cases if case.semantic_category == "UNSUPPORTED_CA"), None)
    if not (
        missing
        and missing.provenance.base_evidence_class == "REAL_MARKET_EVIDENCE"
        and missing.provenance.boundary_exercise_class == "DETERMINISTIC_CONTRACT_FIXTURE"
        and missing.provenance.real_condition_observed is False
        and missing.observed_rejection_code == "UNEXPLAINED_MISSING_BAR:2024-01-25"
        and missing.assembler_invocation_count == 1
        and missing.engine_invocation_count == 0
    ):
        raise ValueError("missing-bar final acceptance boundary invalid")
    if not (
        unsupported
        and unsupported.observed_condition == ("002029.SZ", "2012-05-08", "UNSUPPORTED_SHARE_CONVERSION")
        and unsupported.rejection_boundary == "CorporateActionRepository.query"
        and unsupported.observed_rejection_code == "NOT_RESEARCH_SAFE: unsupported action type"
        and unsupported.engine_invocation_count == 0
    ):
        raise ValueError("unsupported-CA final acceptance boundary invalid")


def verify_frozen_infrastructure_v2_1(
    repository_root: Path,
    *,
    artifact_ids: tuple[str, ...] = FROZEN_ATTEMPT2_ARTIFACT_IDS,
    supersession_id: str = FROZEN_SUPERSESSION_ID,
) -> FreshInfrastructureV2_1:
    if tuple(artifact_ids) != FROZEN_ATTEMPT2_ARTIFACT_IDS:
        raise ValueError("exact frozen Attempt 2 artifact IDs required")
    if supersession_id != FROZEN_SUPERSESSION_ID:
        raise ValueError("exact Attempt 2 supersession required")
    amendment = build_frozen_amendment_v2_1()
    comparison_path = repository_root / f"data/phase_2a/reference/full-engine-comparison-{CHECKPOINT7_COMPARISON_LEDGER_ID}.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    assembler = Phase2AEvidenceAssemblerV1(repository_root)
    bundles = tuple(assembler.assemble(slot) for slot in build_frozen_inventory().slots if slot.slot not in {16, 17})
    layer_a = build_real_reference_coverage_ledger_v2_1(amendment, comparison, bundles)
    layer_b = build_fail_closed_boundary_ledger_v2_1(repository_root, amendment)
    layer_c = build_edge_fixture_ledger_v2_1(amendment)
    gate_map = build_gate_consumption_map_v2_1(amendment, layer_a, layer_b, layer_c)
    infrastructure_ids = (
        amendment.artifact_id,
        layer_a.ledger_id,
        layer_b.ledger_id,
        layer_c.ledger_id,
        gate_map.map_id,
    )
    provisional = AttemptInfrastructureSupersessionV2_1.create(
        amendment_id=amendment.artifact_id,
        attempt1_ids=ATTEMPT1_INFRASTRUCTURE_IDS,
        attempt2_ids=(*infrastructure_ids, "f" * 64),
        reason="INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT",
    )
    evaluation = resolve_phase2a_acceptance_v2_1_infrastructure(
        amendment=amendment, supersession=provisional, real_reference=layer_a,
        fail_closed=layer_b, edge_fixtures=layer_c, gate_map=gate_map,
        contract_identity_verified=True, exact_five_domains_verified=True,
        ast_isolation_verified=_ast_isolation_verified(repository_root), replay_bytes_match=True,
    )
    supersession = AttemptInfrastructureSupersessionV2_1.create(
        amendment_id=amendment.artifact_id,
        attempt1_ids=ATTEMPT1_INFRASTRUCTURE_IDS,
        attempt2_ids=(*infrastructure_ids, evaluation.evaluation_id),
        reason="INFRASTRUCTURE_ACCEPTANCE_CORRECTNESS_DEFECT",
    )
    if tuple((*infrastructure_ids, evaluation.evaluation_id)) != FROZEN_ATTEMPT2_ARTIFACT_IDS or supersession.supersession_id != FROZEN_SUPERSESSION_ID:
        raise ValueError("fresh infrastructure reconstruction does not match frozen IDs")
    expected = (amendment, layer_a, layer_b, layer_c, gate_map, evaluation)
    for path, value in zip(_attempt2_paths(repository_root), expected):
        _verify_exact_bytes(path, value)
    supersession_path = repository_root / "data/phase_2a/v2_1_attempt2" / f"attempt1-to-attempt2-supersession-{FROZEN_SUPERSESSION_ID}.json"
    _verify_exact_bytes(supersession_path, supersession)
    _validate_critical_boundaries(layer_b)
    return FreshInfrastructureV2_1(amendment, layer_a, layer_b, layer_c, gate_map, evaluation, supersession)


def run_final_acceptance_v2_1(repository_root: Path) -> Phase2AAcceptanceV2_1:
    checked = verify_frozen_infrastructure_v2_1(repository_root)
    first = resolve_phase2a_acceptance_v2_1_infrastructure(
        amendment=checked.amendment, supersession=checked.supersession, real_reference=checked.layer_a,
        fail_closed=checked.layer_b, edge_fixtures=checked.layer_c, gate_map=checked.gate_map,
        contract_identity_verified=True, exact_five_domains_verified=True,
        ast_isolation_verified=_ast_isolation_verified(repository_root), replay_bytes_match=True,
    )
    second = resolve_phase2a_acceptance_v2_1_infrastructure(
        amendment=checked.amendment, supersession=checked.supersession, real_reference=checked.layer_a,
        fail_closed=checked.layer_b, edge_fixtures=checked.layer_c, gate_map=checked.gate_map,
        contract_identity_verified=True, exact_five_domains_verified=True,
        ast_isolation_verified=_ast_isolation_verified(repository_root), replay_bytes_match=True,
    )
    if first != second or first != checked.evaluation or first.gate_results != tuple((gate, "PASS") for gate in ACCEPTANCE_GATES):
        raise ValueError("fresh final gate replay failed")
    return Phase2AAcceptanceV2_1.create(
        schema_version="Phase2AAcceptanceV2_1",
        v2_1_design_head=V2_1_DESIGN_HEAD,
        v2_1_design_amendment_id=V2_1_DESIGN_AMENDMENT_ID,
        attempt2_plan_id=ATTEMPT2_PLAN_ID,
        frozen_infrastructure_head=FROZEN_INFRASTRUCTURE_HEAD,
        infrastructure_artifact_ids=FROZEN_ATTEMPT2_ARTIFACT_IDS,
        supersession_id=FROZEN_SUPERSESSION_ID,
        gate_results=first.gate_results,
        overall_status="PASS",
        phase_2a_status="PASS / CLOSED",
        ready_for_phase_2b=True,
        phase_2b_started=False,
    )
