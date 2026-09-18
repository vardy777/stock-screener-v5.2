from __future__ import annotations

from v5_2.labels.acceptance import ACCEPTANCE_GATES
from v5_2.labels.acceptance_v2_contracts import (
    CalculationEdgeFixtureLedgerV2,
    FailClosedBoundaryLedgerV2,
    GateArtifactConsumptionMapV2,
    Phase2AAcceptanceArchitectureAmendmentV2,
    Phase2AAcceptanceV2,
    RealReferenceCoverageLedgerV2,
)


EXPECTED_BOUNDARIES = (
    "UNEXPLAINED_MISSING_BAR", "UNSUPPORTED_CA", "REVOKED_APPROVAL",
    "TAMPERED_ARTIFACT", "MISSING_REQUIRED_DOMAIN", "AMBIGUOUS_IDENTITY",
    "MALFORMED_CALENDAR", "INVALID_LINEAGE", "ROLE_SWAP", "DUPLICATE_DOMAIN",
)
EXPECTED_FIXTURES = ("UPPER_FIRST", "LOWER_FIRST", "NEITHER", "SAME_SESSION_BARRIER_AMBIGUITY")


def _identifier(value: object, name: str) -> str:
    candidate = getattr(value, name, None)
    return candidate if isinstance(candidate, str) and len(candidate) == 64 else "0" * 64


def resolve_phase2a_acceptance_v2(
    *,
    amendment: Phase2AAcceptanceArchitectureAmendmentV2,
    real_reference: RealReferenceCoverageLedgerV2,
    fail_closed: FailClosedBoundaryLedgerV2,
    edge_fixtures: CalculationEdgeFixtureLedgerV2,
    gate_map: GateArtifactConsumptionMapV2,
) -> Phase2AAcceptanceV2:
    amendment_ok = amendment is not None and amendment.verify()
    a_ok = (
        real_reference is not None and real_reference.verify()
        and real_reference.amendment_id == amendment.artifact_id
        and tuple(case.slot for case in real_reference.cases) == (*range(1, 16), *range(18, 23))
        and all(case.disposition == "MATCH" for case in real_reference.cases)
    )
    b_ok = (
        fail_closed is not None and fail_closed.verify()
        and fail_closed.amendment_id == amendment.artifact_id
        and tuple(case.semantic_category for case in fail_closed.cases) == EXPECTED_BOUNDARIES
        and all(case.expected_rejection_code == case.observed_rejection_code and case.engine_invocation_count == 0 for case in fail_closed.cases)
    )
    c_ok = (
        edge_fixtures is not None and edge_fixtures.verify()
        and edge_fixtures.amendment_id == amendment.artifact_id
        and tuple(item.name for item in edge_fixtures.fixtures) == EXPECTED_FIXTURES
        and len(edge_fixtures.comparisons) == 4
        and all(item.disposition == "MATCH" for item in edge_fixtures.comparisons)
    )
    expected_ids = {amendment.artifact_id, real_reference.ledger_id, fail_closed.ledger_id, edge_fixtures.ledger_id}
    map_ok = (
        gate_map is not None and gate_map.verify()
        and gate_map.amendment_id == amendment.artifact_id
        and tuple(entry.gate for entry in gate_map.entries) == ACCEPTANCE_GATES
        and all(set(entry.artifact_ids) <= expected_ids for entry in gate_map.entries)
    )
    common = amendment_ok and map_ok
    statuses = []
    for entry in gate_map.entries if map_ok else ():
        requirements = {"A": a_ok, "B": b_ok, "C": c_ok, "CROSS_LAYER": a_ok and b_ok and c_ok}
        needed = entry.primary_layer.split("+")
        passed = common and all(requirements[layer] for layer in needed)
        statuses.append((entry.gate, "PASS" if passed else "FAIL"))
    if len(statuses) != 16:
        statuses = [(name, "FAIL") for name in ACCEPTANCE_GATES]
    ready = all(value == "PASS" for _, value in statuses)
    return Phase2AAcceptanceV2.create(
        amendment_id=_identifier(amendment, "artifact_id"),
        layer_a_ledger_id=_identifier(real_reference, "ledger_id"),
        layer_b_ledger_id=_identifier(fail_closed, "ledger_id"),
        layer_c_ledger_id=_identifier(edge_fixtures, "ledger_id"),
        gate_map_id=_identifier(gate_map, "map_id"),
        gate_results=tuple(statuses),
        phase_2a_status="PASS" if ready else "FAIL",
        ready_for_phase_2b=ready,
    )
