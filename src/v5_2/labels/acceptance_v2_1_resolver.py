from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash
from v5_2.labels.acceptance import ACCEPTANCE_GATES
from v5_2.labels.acceptance_v2_1_predicates import evaluate_gate_v2_1
from v5_2.labels.acceptance_v2_contracts import GateEvidenceV2_1


@dataclass(frozen=True, slots=True)
class Phase2AInfrastructureEvaluationV2_1:
    amendment_id: str
    layer_a_ledger_id: str
    layer_b_ledger_id: str
    layer_c_ledger_id: str
    gate_map_id: str
    gate_results: tuple[tuple[str, str], ...]
    infrastructure_status: str
    final_acceptance_created: bool
    ready_for_phase_2b: bool
    evaluation_id: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        if values["final_acceptance_created"] or values["ready_for_phase_2b"]:
            raise ValueError("infrastructure evaluation cannot authorize final acceptance")
        body = dict(values)
        digest = content_hash({"schema_version": cls.__name__, **body})
        return cls(**body, evaluation_id=digest, content_hash=digest)

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in self.__dataclass_fields__ if name not in {"evaluation_id", "content_hash"}}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.evaluation_id == self.content_hash == digest


def _identity(value, name: str) -> str:
    candidate = getattr(value, name, None)
    return candidate if isinstance(candidate, str) and len(candidate) == 64 else "0" * 64


def resolve_phase2a_acceptance_v2_1_infrastructure(
    *,
    amendment,
    supersession,
    real_reference,
    fail_closed,
    edge_fixtures,
    gate_map,
    contract_identity_verified: bool,
    exact_five_domains_verified: bool,
    ast_isolation_verified: bool,
    replay_bytes_match: bool,
) -> Phase2AInfrastructureEvaluationV2_1:
    expected = (
        _identity(amendment, "artifact_id"),
        _identity(real_reference, "ledger_id"),
        _identity(fail_closed, "ledger_id"),
        _identity(edge_fixtures, "ledger_id"),
        _identity(gate_map, "map_id"),
    )
    objects = (amendment, supersession, real_reference, fail_closed, edge_fixtures, gate_map)
    integrity = all(value is not None and value.verify() for value in objects)
    cross_ids = bool(
        integrity
        and real_reference.amendment_id == amendment.artifact_id
        and fail_closed.amendment_id == amendment.artifact_id
        and edge_fixtures.amendment_id == amendment.artifact_id
        and gate_map.amendment_id == amendment.artifact_id
        and supersession.amendment_id == amendment.artifact_id
        and supersession.attempt2_ids[:5] == expected
        and all(entry.artifact_ids == expected[:4] for entry in gate_map.entries)
    )
    if cross_ids:
        evidence = GateEvidenceV2_1(
            amendment=amendment,
            layer_a=real_reference,
            layer_b=fail_closed,
            layer_c=edge_fixtures,
            gate_map=gate_map,
            supersession=supersession,
            contract_identity_verified=contract_identity_verified,
            exact_five_domains_verified=exact_five_domains_verified,
            ast_isolation_verified=ast_isolation_verified,
            replay_bytes_match=replay_bytes_match,
        )
        results = tuple((gate, evaluate_gate_v2_1(gate, evidence).status) for gate in ACCEPTANCE_GATES)
    else:
        results = tuple((gate, "FAIL") for gate in ACCEPTANCE_GATES)
    passed = all(status == "PASS" for _gate, status in results)
    return Phase2AInfrastructureEvaluationV2_1.create(
        amendment_id=expected[0],
        layer_a_ledger_id=expected[1],
        layer_b_ledger_id=expected[2],
        layer_c_ledger_id=expected[3],
        gate_map_id=expected[4],
        gate_results=results,
        infrastructure_status="PASS" if passed else "FAIL",
        final_acceptance_created=False,
        ready_for_phase_2b=False,
    )
