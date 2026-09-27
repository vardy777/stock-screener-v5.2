"""Fail-closed formal Phase 2B gates; V1 caller hashes are never authority."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from v5_2.data.identity import content_hash
from v5_2.labels.dataset_contracts import LabelPartitionV1, LabelRowV1
from v5_2.labels.phase2b_contract_pins_v2 import (
    derive_contract_pin_evidence_exact, read_contract_pin_evidence_exact,
)
from v5_2.labels.phase2b_ca_safety_v2 import (
    derive_ca_safety_evidence_exact, read_ca_safety_evidence_exact,
)
from v5_2.labels.phase2b_gates import PHASE2B_GATES
from v5_2.labels.partition_store import read_partition_exact, read_partition_rows_exact
from v5_2.labels.phase2b_gate_evidence_v2 import (
    derive_partition_comparisons_exact, read_row_comparison_ledger_exact,
)
from v5_2.labels.phase2b_month_coverage_v2 import (
    derive_month_coverage_evidence_exact, read_month_coverage_evidence_exact,
)
from v5_2.labels.phase2b_maturation_gate_v2 import (
    derive_maturation_gate_evidence_exact, read_maturation_gate_evidence_exact,
)
from v5_2.labels.phase2b_manifest_gate_v2 import verify_manifest_physical_exact
from v5_2.labels.phase2b_semantic_gate_evidence_v2 import (
    SEMANTIC_GATES, derive_semantic_group_ledger_exact,
    read_semantic_group_ledger_exact,
)
from v5_2.labels.phase2b_unsafe_gate_v2 import (
    derive_unsafe_preservation_evidence, read_unsafe_preservation_evidence_exact,
)
from v5_2.labels.phase2b_suspension_safety_v2 import (
    derive_suspension_evidence_exact, read_suspension_evidence_exact,
)
from v5_2.labels.phase2b_identity_safety_v2 import (
    derive_identity_safety_evidence_exact, read_identity_safety_evidence_exact,
)
from v5_2.labels.phase2b_delisting_safety_v2 import (
    derive_delisting_safety_evidence_exact, read_delisting_safety_evidence_exact,
)
from v5_2.labels.phase2b_incremental_gate_v2 import (
    derive_incremental_idempotency_evidence_exact,
    read_incremental_idempotency_evidence_exact,
)
from v5_2.labels.phase2b_replay_gate_v2 import (
    derive_replay_evidence_exact, read_replay_evidence_exact,
    replay_binds_evaluated_sources,
)
from v5_2.labels.phase2b_cleanroom_gate_v2 import (
    derive_cleanroom_evidence_exact, read_cleanroom_evidence_exact,
)


GATE_V2_CONTRACT_ID = content_hash({
    "schema_version": "Phase2BGateEvidenceContractV2",
    "gates": PHASE2B_GATES,
    "trust_rule": "exact-source-independent-rederivation",
})
GATE_V2_EVALUATOR_ID = content_hash({
    "schema_version": "Phase2BGateEvaluatorV2",
    "version": "source-pinned-semantic-groups-v1",
    "contract_id": GATE_V2_CONTRACT_ID,
})


@dataclass(frozen=True, slots=True)
class Phase2BGateResultV2:
    gate: str
    status: str
    failure_code: str | None
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Phase2BGateEvaluationV2:
    contract_id: str
    evaluator_id: str
    results: tuple[Phase2BGateResultV2, ...]
    all_pass: bool
    content_hash: str

    def verify(self) -> bool:
        body = {key: getattr(self, key) for key in self.__dataclass_fields__
                if key != "content_hash"}
        return (
            self.contract_id == GATE_V2_CONTRACT_ID
            and self.evaluator_id == GATE_V2_EVALUATOR_ID
            and tuple(item.gate for item in self.results) == PHASE2B_GATES
            and self.all_pass == all(item.status == "PASS" for item in self.results)
            and self.content_hash == content_hash({
                "schema_version": type(self).__name__, **body})
        )


def verify_partition_generation_v2(partition: LabelPartitionV1,
                                   rows: tuple[LabelRowV1, ...],
                                   lineage_ids: tuple[str, ...]) -> bool:
    """Recompute the generation from exact physical membership and lineage."""
    if (not partition.verify() or len(lineage_ids) != 5
            or partition.row_count != len(rows)
            or partition.row_ids != tuple(row.row_id for row in rows)
            or not rows
            or any(not row.verify() or row.materialization_version != "phase2b-v1"
                   or row.anchor_session.strftime("%Y-%m") != partition.partition_key
                   for row in rows)):
        return False
    expected = content_hash({
        "schema_version": "LabelPartitionGenerationV1",
        "partition_key": partition.partition_key,
        "materialization_version": "phase2b-v1",
        "lineage_ids": lineage_ids,
        "row_ids": partition.row_ids,
    })
    return partition.generation_id == expected


def evaluate_phase2b_gates_v2_exact(*, source_root: Path,
                                    partition_path: Path, partition_id: str,
                                    semantic_ledger_path: Path,
                                    semantic_ledger_id: str,
                                    coverage_path: Path | None = None,
                                    coverage_id: str | None = None,
                                    scoped_path: Path | None = None,
                                    scoped_id: str | None = None,
                                    comparison_path: Path | None = None,
                                    comparison_id: str | None = None,
                                    contract_path: Path | None = None,
                                    contract_id: str | None = None,
                                    maturation_path: Path | None = None,
                                    maturation_id: str | None = None,
                                    unsafe_path: Path | None = None,
                                    unsafe_id: str | None = None,
                                    manifest_path: Path | None = None,
                                    manifest_id: str | None = None,
                                    active_partition_paths: tuple[Path, ...] = (),
                                    previous_manifest_path: Path | None = None,
                                    ca_path: Path | None = None,
                                    ca_id: str | None = None,
                                    suspension_path: Path | None = None,
                                    suspension_id: str | None = None,
                                    identity_path: Path | None = None,
                                    identity_id: str | None = None,
                                    delisting_path: Path | None = None,
                                    delisting_id: str | None = None,
                                    incremental_path: Path | None = None,
                                    incremental_id: str | None = None,
                                    replay_path: Path | None = None,
                                    replay_id: str | None = None,
                                    cleanroom_path: Path | None = None,
                                    cleanroom_id: str | None = None,
                                    ) -> Phase2BGateEvaluationV2:
    """Independently rederive pinned semantic evidence before any PASS.

    Gates without dedicated evidence producers remain FAIL; this interim
    evaluator cannot authorize a Checkpoint 18 acceptance.
    """
    semantic = None
    try:
        recorded = read_semantic_group_ledger_exact(
            semantic_ledger_path, semantic_ledger_id)
        derived = derive_semantic_group_ledger_exact(
            source_root, partition_path, partition_id)
        if recorded != derived or derived.checked_rows == 0:
            raise ValueError("semantic evidence differs from exact sources")
        semantic = derived
    except (OSError, ValueError):
        pass
    contract = None
    if contract_path is not None and contract_id is not None:
        try:
            recorded_contract = read_contract_pin_evidence_exact(
                contract_path, contract_id)
            derived_contract = derive_contract_pin_evidence_exact(source_root)
            if recorded_contract != derived_contract:
                raise ValueError("contract pins differ from frozen authority")
            contract = derived_contract
        except (OSError, ValueError, KeyError, TypeError):
            pass
    ca = None
    if ca_path is not None and ca_id is not None:
        try:
            recorded_ca = read_ca_safety_evidence_exact(ca_path, ca_id)
            derived_ca = derive_ca_safety_evidence_exact(source_root)
            if recorded_ca != derived_ca:
                raise ValueError("CA evidence differs from frozen source")
            ca = derived_ca
        except (OSError, ValueError, KeyError, TypeError):
            pass
    suspension = None
    if suspension_path is not None and suspension_id is not None:
        try:
            recorded_suspension = read_suspension_evidence_exact(
                suspension_path, suspension_id)
            derived_suspension = derive_suspension_evidence_exact(source_root)
            if recorded_suspension != derived_suspension:
                raise ValueError("suspension evidence differs from frozen source")
            suspension = derived_suspension
        except (OSError, ValueError, KeyError, TypeError):
            pass
    identity = None
    if identity_path is not None and identity_id is not None:
        try:
            recorded_identity = read_identity_safety_evidence_exact(
                identity_path, identity_id)
            derived_identity = derive_identity_safety_evidence_exact(source_root)
            if recorded_identity != derived_identity:
                raise ValueError("identity evidence differs from frozen source")
            identity = derived_identity
        except (OSError, ValueError, KeyError, TypeError):
            pass
    delisting = None
    if delisting_path is not None and delisting_id is not None:
        try:
            recorded_delisting = read_delisting_safety_evidence_exact(
                delisting_path, delisting_id)
            derived_delisting = derive_delisting_safety_evidence_exact(source_root)
            if recorded_delisting != derived_delisting:
                raise ValueError("delisting evidence differs from frozen source")
            delisting = derived_delisting
        except (OSError, ValueError, KeyError, TypeError):
            pass
    incremental = None
    if incremental_path is not None and incremental_id is not None:
        try:
            recorded_incremental = read_incremental_idempotency_evidence_exact(
                incremental_path, incremental_id)
            with TemporaryDirectory(prefix="v52-incremental-gate-") as scratch:
                derived_incremental = derive_incremental_idempotency_evidence_exact(
                    source_root, Path(scratch))
            if recorded_incremental != derived_incremental:
                raise ValueError("incremental evidence differs from real source")
            incremental = derived_incremental
        except (OSError, ValueError, KeyError, TypeError):
            pass
    replay = None
    if replay_path is not None and replay_id is not None:
        try:
            recorded_replay = read_replay_evidence_exact(replay_path, replay_id)
            with TemporaryDirectory(prefix="v52-replay-gate-") as scratch:
                derived_replay = derive_replay_evidence_exact(
                    source_root, Path(scratch))
            if recorded_replay != derived_replay:
                raise ValueError("replay evidence differs from frozen source")
            replay = derived_replay
        except (OSError, ValueError, KeyError, TypeError):
            pass
    cleanroom = None
    if cleanroom_path is not None and cleanroom_id is not None:
        try:
            recorded_cleanroom = read_cleanroom_evidence_exact(
                cleanroom_path, cleanroom_id)
            derived_cleanroom = derive_cleanroom_evidence_exact(source_root)
            if recorded_cleanroom != derived_cleanroom:
                raise ValueError("clean-room evidence differs from fresh checkout")
            cleanroom = derived_cleanroom
        except (OSError, ValueError, KeyError, TypeError):
            pass
    maturation = None
    if maturation_path is not None and maturation_id is not None:
        try:
            recorded_maturation = read_maturation_gate_evidence_exact(
                maturation_path, maturation_id)
            derived_maturation = derive_maturation_gate_evidence_exact(source_root)
            if recorded_maturation != derived_maturation:
                raise ValueError("maturation differs from frozen real bundle")
            maturation = derived_maturation
        except (OSError, ValueError, KeyError, TypeError):
            pass
    coverage = None
    if all(item is not None for item in (
            coverage_path, coverage_id, scoped_path, scoped_id)):
        try:
            recorded_coverage = read_month_coverage_evidence_exact(
                coverage_path, coverage_id)
            derived_coverage = derive_month_coverage_evidence_exact(
                source_root, partition_path, partition_id,
                scoped_path, scoped_id)
            if (recorded_coverage != derived_coverage
                    or derived_coverage.partition_id != partition_id):
                raise ValueError("coverage evidence differs from exact sources")
            coverage = derived_coverage
        except (OSError, ValueError):
            pass
    comparison = None
    if comparison_path is not None and comparison_id is not None:
        try:
            recorded_comparison = read_row_comparison_ledger_exact(
                comparison_path, comparison_id)
            derived_comparison = derive_partition_comparisons_exact(
                source_root, partition_path, partition_id)
            if (recorded_comparison != derived_comparison
                    or derived_comparison.partition_id != partition_id
                    or derived_comparison.checked_rows == 0):
                raise ValueError("row comparison differs from exact sources")
            comparison = derived_comparison
        except (OSError, ValueError):
            pass
    partition_valid = False
    if coverage is not None and comparison is not None and not comparison.mismatch_row_ids:
        try:
            partition = read_partition_exact(partition_path, partition_id)
            rows = read_partition_rows_exact(partition_path, partition_id)
            partition_valid = (
                len(rows) == coverage.materialized_rows == comparison.checked_rows
                and partition.partition_key == coverage.month
                and verify_partition_generation_v2(
                    partition, rows, comparison.source_approval_ids)
            )
        except (OSError, ValueError):
            pass
    unsafe = None
    if unsafe_path is not None and unsafe_id is not None and semantic is not None:
        try:
            recorded_unsafe = read_unsafe_preservation_evidence_exact(
                unsafe_path, unsafe_id)
            rows = read_partition_rows_exact(partition_path, partition_id)
            derived_unsafe = derive_unsafe_preservation_evidence(
                rows, partition_id)
            if (recorded_unsafe != derived_unsafe
                    or derived_unsafe.unsafe_value_count == 0
                    or semantic.checked_rows != len(rows)
                    or semantic.lineage_mismatch_row_ids
                    or next(failed for gate, failed in semantic.failed_row_ids_by_gate
                            if gate == "STATE_SEMANTICS")):
                raise ValueError("unsafe evidence differs from source rows")
            unsafe = derived_unsafe
        except (OSError, ValueError, KeyError, TypeError):
            pass
    manifest_valid = False
    if (manifest_path is not None and manifest_id is not None
            and contract is not None and comparison is not None
            and partition_valid and active_partition_paths == (partition_path,)
            and comparison.source_approval_ids == contract.source_approval_ids):
        manifest_valid = verify_manifest_physical_exact(
            manifest_path, manifest_id, active_partition_paths,
            contract.phase2a_acceptance_id, comparison.source_approval_ids,
            previous_manifest_path,
            expected_active_partition_ids=(partition_id,))
    results = []
    for gate in PHASE2B_GATES:
        if gate == "CONTRACT_PINNING" and contract is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None, (contract.evidence_id,)))
        elif gate == "HISTORICAL_COVERAGE_ACCOUNTING" and coverage is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None, (coverage.evidence_id,)))
        elif gate in SEMANTIC_GATES and semantic is not None:
            failed = next(rows for name, rows in semantic.failed_row_ids_by_gate
                          if name == gate)
            results.append(Phase2BGateResultV2(
                gate, "FAIL" if failed else "PASS",
                f"{gate}_SOURCE_MISMATCH" if failed else None,
                (semantic.ledger_id,)))
        elif gate == "LINEAGE_INTEGRITY" and semantic is not None and comparison is not None:
            passed = (
                not semantic.lineage_mismatch_row_ids
                and semantic.checked_rows == comparison.checked_rows
                and semantic.source_approval_ids == comparison.source_approval_ids
            )
            results.append(Phase2BGateResultV2(
                gate, "PASS" if passed else "FAIL",
                None if passed else "LINEAGE_INTEGRITY_SOURCE_MISMATCH",
                (semantic.ledger_id, comparison.ledger_id)))
        elif gate == "PARTITION_INTEGRITY" and partition_valid:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None, (coverage.evidence_id, comparison.ledger_id,
                                      partition_id)))
        elif gate == "PENDING_MATURATION" and maturation is not None:
            passed = (
                maturation.pending_counts == (7, 6, 5, 0)
                and maturation.available_counts == (0, 1, 2, 7)
                and not maturation.mismatch_stages
                and maturation.h1_early_barrier_hit
                and not maturation.h1_barrier_published
            )
            results.append(Phase2BGateResultV2(
                gate, "PASS" if passed else "FAIL",
                None if passed else "PENDING_MATURATION_CONTRACT_MISMATCH",
                (maturation.evidence_id,)))
        elif gate == "CORPORATE_ACTION_SAFETY" and ca is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None, (ca.evidence_id, ca.source_approval_id,
                                      ca.source_authority_id)))
        elif gate == "SUSPENSION_SAFETY" and suspension is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None,
                (suspension.evidence_id, suspension.source_approval_id,
                 suspension.source_authority_id)))
        elif gate == "IDENTITY_SAFETY" and identity is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None,
                (identity.evidence_id, identity.master_approval_id,
                 identity.graph_approval_id)))
        elif gate == "DELISTING_SAFETY" and delisting is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None,
                (delisting.evidence_id, delisting.status_fact_id,
                 delisting.status_manifest_id)))
        elif gate == "INCREMENTAL_IDEMPOTENCY" and incremental is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None,
                (incremental.evidence_id, incremental.first_manifest_id,
                 incremental.first_partition_id)))
        elif (gate == "DETERMINISTIC_REPLAY" and replay is not None
              and coverage is not None and comparison is not None
              and partition_valid
              and replay_binds_evaluated_sources(
                  replay, partition_id=partition_id,
                  candidate_set_hash=coverage.candidate_set_hash,
                  coverage_id=coverage.evidence_id,
                  scoped_ledger_id=scoped_id,
                  comparison_ledger_id=comparison.ledger_id)):
            results.append(Phase2BGateResultV2(
                gate, "PASS", None,
                (replay.evidence_id, replay.partition_ids[0],
                 replay.row_comparison_ledger_id)))
        elif gate == "CLEAN_ROOM_STANDALONE" and cleanroom is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None,
                (cleanroom.evidence_id, cleanroom.corpus_manifest_id,
                 cleanroom.inventory_hash, cleanroom.reproduced_partition_id)))
        elif gate == "NOT_LABEL_SAFE_PRESERVATION" and unsafe is not None:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None, (unsafe.evidence_id, semantic.ledger_id)))
        elif gate == "MANIFEST_INTEGRITY" and manifest_valid:
            results.append(Phase2BGateResultV2(
                gate, "PASS", None, (manifest_id, partition_id,
                                      contract.evidence_id, comparison.ledger_id)))
        else:
            results.append(Phase2BGateResultV2(
                gate, "FAIL", f"{gate}_FORMAL_EVIDENCE_MISSING", ()))
    frozen = tuple(results)
    body = {"contract_id": GATE_V2_CONTRACT_ID,
            "evaluator_id": GATE_V2_EVALUATOR_ID,
            "results": frozen,
            "all_pass": all(item.status == "PASS" for item in frozen)}
    result = Phase2BGateEvaluationV2(**body, content_hash=content_hash({
        "schema_version": "Phase2BGateEvaluationV2", **body}))
    if not result.verify():
        raise ValueError("formal V2 gate evaluation is invalid")
    return result
