from __future__ import annotations

from dataclasses import dataclass
import re

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import LabelContractV1
from v5_2.labels.dataset_contracts import (
    CoverageAccountingV1, LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1,
)


PHASE2B_GATES = (
    "CONTRACT_PINNING",
    "HISTORICAL_COVERAGE_ACCOUNTING",
    "STATE_SEMANTICS",
    "RETURN_SEMANTICS",
    "MFE_MAE_SEMANTICS",
    "BARRIER_SEMANTICS",
    "CORPORATE_ACTION_SAFETY",
    "SUSPENSION_SAFETY",
    "DELISTING_SAFETY",
    "IDENTITY_SAFETY",
    "PENDING_MATURATION",
    "NOT_LABEL_SAFE_PRESERVATION",
    "PARTITION_INTEGRITY",
    "MANIFEST_INTEGRITY",
    "LINEAGE_INTEGRITY",
    "DETERMINISTIC_REPLAY",
    "INCREMENTAL_IDEMPOTENCY",
    "CLEAN_ROOM_STANDALONE",
)

_ID = re.compile(r"^[0-9a-f]{64}$")


def _digest(schema: str, body: object) -> str:
    return content_hash({"schema_version": schema, "body": body})


@dataclass(frozen=True, slots=True)
class GatePredicateEvidenceV1:
    gate: str
    expected_hash: str
    observed_hash: str
    evidence_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(cls, gate: str, expected_hash: str, observed_hash: str,
               evidence_ids: tuple[str, ...]) -> "GatePredicateEvidenceV1":
        if gate not in PHASE2B_GATES:
            raise ValueError("unknown Phase 2B gate")
        if not _ID.fullmatch(expected_hash) or not _ID.fullmatch(observed_hash):
            raise ValueError("predicate hashes invalid")
        if not evidence_ids or not all(_ID.fullmatch(value) for value in evidence_ids):
            raise ValueError("predicate evidence IDs required")
        body = (gate, expected_hash, observed_hash, evidence_ids)
        return cls(gate, expected_hash, observed_hash, evidence_ids,
                   _digest(cls.__name__, body))

    def verify(self) -> bool:
        body = (self.gate, self.expected_hash, self.observed_hash, self.evidence_ids)
        return (
            self.gate in PHASE2B_GATES
            and bool(_ID.fullmatch(self.expected_hash))
            and bool(_ID.fullmatch(self.observed_hash))
            and bool(self.evidence_ids)
            and all(_ID.fullmatch(value) for value in self.evidence_ids)
            and self.content_hash == _digest(type(self).__name__, body)
        )


@dataclass(frozen=True, slots=True)
class Phase2BGateInputsV1:
    contract_version: str
    coverage: CoverageAccountingV1
    dispositions: tuple[object, ...]
    rows: tuple[LabelRowV1, ...]
    partitions: tuple[tuple[LabelPartitionV1, tuple[LabelRowV1, ...]], ...]
    manifest: LabelDatasetManifestV1
    expected_manifest_id: str
    expected_partition_ids: tuple[str, ...]
    expected_lineage_ids: tuple[str, ...]
    expected_row_lineage: tuple[tuple[str, tuple[str, ...]], ...]
    predicate_evidence: tuple[GatePredicateEvidenceV1, ...]


@dataclass(frozen=True, slots=True)
class Phase2BGateResultV1:
    gate: str
    status: str
    failure_code: str | None
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Phase2BGateEvaluationV1:
    results: tuple[Phase2BGateResultV1, ...]
    all_pass: bool
    content_hash: str


def _structural_checks(inputs: Phase2BGateInputsV1) -> dict[str, bool]:
    rows_valid = all(row.verify() for row in inputs.rows)
    contract = (
        inputs.contract_version == LabelContractV1().contract_version
        and rows_valid
        and all(row.label_contract_version == inputs.contract_version for row in inputs.rows)
    )
    try:
        coverage = inputs.coverage.verify_against(inputs.dispositions, inputs.rows)
    except (TypeError, ValueError):
        coverage = False

    partition_ids: list[str] = []
    partition_valid = True
    for partition, rows in inputs.partitions:
        partition_ids.append(partition.partition_id)
        partition_valid = partition_valid and (
            partition.verify()
            and all(row.verify() for row in rows)
            and partition.row_ids == tuple(row.row_id for row in rows)
        )
    partition_valid = (
        partition_valid
        and len(partition_ids) == len(set(partition_ids))
        and tuple(partition_ids) == inputs.expected_partition_ids
    )
    manifest_valid = (
        inputs.manifest.verify()
        and inputs.manifest.manifest_id == inputs.expected_manifest_id
        and inputs.manifest.active_partition_ids == inputs.expected_partition_ids
    )
    actual_row_lineage = tuple(sorted(
        (row.row_id, row.domain_lineage_hashes) for row in inputs.rows
    ))
    lineage_valid = (
        inputs.manifest.lineage_ids == inputs.expected_lineage_ids
        and actual_row_lineage == inputs.expected_row_lineage
        and all(_ID.fullmatch(value) for value in inputs.expected_lineage_ids)
    )
    return {
        "CONTRACT_PINNING": contract,
        "HISTORICAL_COVERAGE_ACCOUNTING": coverage,
        "PARTITION_INTEGRITY": partition_valid,
        "MANIFEST_INTEGRITY": manifest_valid,
        "LINEAGE_INTEGRITY": lineage_valid,
    }


def evaluate_phase2b_gates(inputs: Phase2BGateInputsV1) -> Phase2BGateEvaluationV1:
    evidence_by_gate = {item.gate: item for item in inputs.predicate_evidence}
    complete_evidence = (
        len(inputs.predicate_evidence) == len(PHASE2B_GATES)
        and len(evidence_by_gate) == len(PHASE2B_GATES)
        and tuple(item.gate for item in inputs.predicate_evidence) == PHASE2B_GATES
    )
    structural = _structural_checks(inputs)
    results: list[Phase2BGateResultV1] = []
    for gate in PHASE2B_GATES:
        evidence = evidence_by_gate.get(gate)
        evidence_pass = bool(
            complete_evidence
            and evidence is not None
            and evidence.verify()
            and evidence.expected_hash == evidence.observed_hash
        )
        passed = evidence_pass and structural.get(gate, True)
        results.append(Phase2BGateResultV1(
            gate=gate,
            status="PASS" if passed else "FAIL",
            failure_code=None if passed else f"{gate}_FAILED",
            evidence_ids=() if evidence is None else evidence.evidence_ids,
        ))
    frozen = tuple(results)
    body = tuple((item.gate, item.status, item.failure_code, item.evidence_ids) for item in frozen)
    return Phase2BGateEvaluationV1(
        frozen, all(item.status == "PASS" for item in frozen),
        _digest(Phase2BGateEvaluationV1.__name__, body),
    )
