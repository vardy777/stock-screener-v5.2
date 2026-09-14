from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from v5_2.data.identity import content_hash


PHASE_1C_GATES = (
    "STRUCTURAL", "TARGET_SESSION_RESOLUTION", "GAP_DETECTION",
    "INCREMENTAL_ACQUISITION", "HISTORICAL_AVAILABILITY",
    "CONTEMPORANEOUS_AVAILABILITY", "IDEMPOTENCY", "REVISION_HANDLING",
    "PARTIAL_FAILURE_FAIL_CLOSED", "SNAPSHOT_ATOMICITY",
    "PREVIOUS_SNAPSHOT_PRESERVATION", "CROSS_DATASET_READINESS",
    "FRONTEND_CONTRACT", "CREDENTIAL_BOUNDARY", "DETERMINISTIC_REPLAY",
)


@dataclass(frozen=True, slots=True)
class Phase1CRefreshAcceptanceV1:
    acceptance_id: str
    starting_head: str
    design_commit: str
    implementation_head: str
    gate_results: Mapping[str, str]
    snapshot_ids: tuple[str, ...]
    test_results: Mapping[str, str]
    final_decision: str
    ready_for_phase_2_implementation: bool
    content_hash: str

    @classmethod
    def create(cls, *, starting_head: str, design_commit: str,
               implementation_head: str, gate_results: Mapping[str, str],
               snapshot_ids: tuple[str, ...],
               test_results: Mapping[str, str]) -> Phase1CRefreshAcceptanceV1:
        gates = dict(gate_results)
        if set(gates) != set(PHASE_1C_GATES) or any(value not in {"PASS", "FAIL"} for value in gates.values()):
            raise ValueError("all frozen Phase 1C gates require PASS/FAIL")
        passed = all(gates[gate] == "PASS" for gate in PHASE_1C_GATES)
        body = {
            "schema_version": "Phase1CRefreshAcceptanceV1",
            "starting_head": starting_head, "design_commit": design_commit,
            "implementation_head": implementation_head,
            "gate_results": {key: gates[key] for key in PHASE_1C_GATES},
            "snapshot_ids": tuple(snapshot_ids), "test_results": dict(test_results),
            "final_decision": "PASS" if passed else "FAIL",
            "ready_for_phase_2_implementation": passed,
        }
        digest = content_hash(body)
        return cls(digest, starting_head, design_commit, implementation_head,
                   body["gate_results"], tuple(snapshot_ids), dict(test_results),
                   body["final_decision"], passed, digest)
