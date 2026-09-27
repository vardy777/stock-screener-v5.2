"""Formal V2 never accepts caller-authored predicate equality."""

from datetime import date
import os
from pathlib import Path

import pytest

from v5_2.labels.dataset_contracts import (
    LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1,
)
from v5_2.labels.phase2b_contract_pins_v2 import (
    PHASE2A_ACCEPTANCE_ID, derive_contract_pin_evidence_exact,
    write_contract_pin_evidence,
)
from v5_2.labels.phase2b_ca_safety_v2 import (
    derive_ca_safety_evidence_exact, write_ca_safety_evidence,
)
from v5_2.labels.phase2b_maturation_gate_v2 import (
    derive_maturation_gate_evidence_exact, write_maturation_gate_evidence,
)
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.partition_store import (
    read_partition_exact, write_manifest, write_partition,
)
from v5_2.labels.phase2b_gates_v2 import (
    evaluate_phase2b_gates_v2_exact, verify_partition_generation_v2,
)
from v5_2.labels.phase2b_semantic_gate_evidence_v2 import (
    derive_semantic_group_ledger_exact, read_semantic_group_ledger_exact,
    write_semantic_group_ledger,
)
from v5_2.labels.phase2b_suspension_safety_v2 import (
    derive_suspension_evidence_exact, write_suspension_evidence,
)
from v5_2.labels.phase2b_identity_safety_v2 import (
    derive_identity_safety_evidence_exact, write_identity_safety_evidence,
)
from v5_2.labels.phase2b_delisting_safety_v2 import (
    derive_delisting_safety_evidence_exact, write_delisting_safety_evidence,
)
from v5_2.labels.phase2b_incremental_gate_v2 import (
    derive_incremental_idempotency_evidence_exact,
    write_incremental_idempotency_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


@pytest.fixture(scope="module")
def real_row():
    producer = HistoricalFiveDomainProducerV1.load_exact(ROOT)
    anchor, lineage, window = producer.produce_anchor("000001.SZ", date(2024, 1, 2))
    bundle = producer.assemble(anchor, lineage, window)
    result = ReferenceLabelEngine().evaluate(bundle)
    return LabelRowV1.create(result=result, bundle=bundle,
                             materialization_version="phase2b-v1")


def test_formal_v2_rederives_four_semantic_gates_and_fails_remaining_closed(
        real_row, tmp_path):
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="gate-v2-fixture", rows=(real_row,))
    partition_path = write_partition(tmp_path, partition, (real_row,))
    semantic = derive_semantic_group_ledger_exact(ROOT, partition_path,
                                                   partition.partition_id)
    evidence_path = write_semantic_group_ledger(tmp_path, semantic)
    contract = derive_contract_pin_evidence_exact(ROOT)
    contract_path = write_contract_pin_evidence(tmp_path, contract)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=partition_path,
        partition_id=partition.partition_id,
        semantic_ledger_path=evidence_path, semantic_ledger_id=semantic.ledger_id,
        contract_path=contract_path, contract_id=contract.evidence_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert len(by_gate) == 18
    assert sum(status == "PASS" for status in by_gate.values()) == 5
    assert by_gate["CONTRACT_PINNING"] == "PASS"
    assert by_gate["RETURN_SEMANTICS"] == "PASS"
    assert by_gate["MFE_MAE_SEMANTICS"] == "PASS"
    assert not evaluation.all_pass


def test_formal_v2_rejects_wrong_exact_semantic_evidence(real_row, tmp_path):
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="gate-v2-negative", rows=(real_row,))
    partition_path = write_partition(tmp_path, partition, (real_row,))
    semantic = derive_semantic_group_ledger_exact(ROOT, partition_path,
                                                   partition.partition_id)
    evidence_path = write_semantic_group_ledger(tmp_path, semantic)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=partition_path,
        partition_id=partition.partition_id,
        semantic_ledger_path=evidence_path, semantic_ledger_id="0" * 64,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert all(by_gate[gate] == "FAIL" for gate in (
        "STATE_SEMANTICS", "RETURN_SEMANTICS", "MFE_MAE_SEMANTICS",
        "BARRIER_SEMANTICS"))


@pytest.mark.skipif(os.environ.get("V52_REAL_MONTH_GATES") != "1",
                    reason="explicit source-pinned real-month gate run required")
def test_real_month_coverage_gate_rereads_exact_candidate_census():
    root = ROOT / "data/phase_2b_checkpoint18_real_month"
    partition_id = "3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9"
    coverage_id = "834534a947d79b10a16404ae35430aafb63b36e0ac467d46b97a57117959ef75"
    scoped_id = "a1092d6465b32c7141a9befb290938adecca2f08b8fb646389becf941f9c656e"
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT,
        partition_path=root / "labels/historical/2010-01" / f"{partition_id}.jsonl",
        partition_id=partition_id,
        semantic_ledger_path=root / "gate_evidence/missing.json",
        semantic_ledger_id="0" * 64,
        coverage_path=root / "gate_evidence" / f"month-coverage-{coverage_id}.json",
        coverage_id=coverage_id,
        scoped_path=root / "scoped_exclusions" / f"{scoped_id}.json",
        scoped_id=scoped_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["HISTORICAL_COVERAGE_ACCOUNTING"] == "PASS"
    assert by_gate["RETURN_SEMANTICS"] == "FAIL"


def test_partition_generation_requires_pinned_lineage_and_row_membership(real_row):
    lineage = tuple(f"{index}" * 64 for index in range(1, 6))
    from v5_2.data.identity import content_hash
    generation = content_hash({
        "schema_version": "LabelPartitionGenerationV1",
        "partition_key": "2024-01", "materialization_version": "phase2b-v1",
        "lineage_ids": lineage, "row_ids": (real_row.row_id,),
    })
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id=generation, rows=(real_row,))
    assert verify_partition_generation_v2(partition, (real_row,), lineage)
    swapped = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="f" * 64, rows=(real_row,))
    assert swapped.verify()
    assert not verify_partition_generation_v2(swapped, (real_row,), lineage)
    assert not verify_partition_generation_v2(partition, (real_row,),
                                               tuple(reversed(lineage)))


def test_formal_maturation_gate_requires_rederived_frozen_real_bundle(tmp_path):
    maturity = derive_maturation_gate_evidence_exact(ROOT)
    path = write_maturation_gate_evidence(tmp_path, maturity)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        maturation_path=path, maturation_id=maturity.evidence_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["PENDING_MATURATION"] == "PASS"
    assert by_gate["RETURN_SEMANTICS"] == "FAIL"
    forged = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        maturation_path=path, maturation_id="f" * 64,
    )
    assert next(item for item in forged.results
                if item.gate == "PENDING_MATURATION").status == "FAIL"


def test_unsafe_gate_missing_exact_artifact_fails_closed(tmp_path):
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        unsafe_path=tmp_path / "missing-unsafe.json",
        unsafe_id="f" * 64,
    )
    assert next(item for item in evaluation.results
                if item.gate == "NOT_LABEL_SAFE_PRESERVATION").status == "FAIL"


def test_manifest_gate_missing_exact_artifact_fails_closed(tmp_path):
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        manifest_path=tmp_path / "missing-manifest.json",
        manifest_id="f" * 64,
        active_partition_paths=(tmp_path / "missing.jsonl",),
    )
    assert next(item for item in evaluation.results
                if item.gate == "MANIFEST_INTEGRITY").status == "FAIL"


def test_ca_gate_requires_exact_real_source_and_explicit_boundary_evidence(tmp_path):
    ca = derive_ca_safety_evidence_exact(ROOT)
    path = write_ca_safety_evidence(tmp_path, ca)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        ca_path=path, ca_id=ca.evidence_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["CORPORATE_ACTION_SAFETY"] == "PASS"
    assert by_gate["RETURN_SEMANTICS"] == "FAIL"
    wrong = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        ca_path=path, ca_id="f" * 64,
    )
    assert next(item for item in wrong.results
                if item.gate == "CORPORATE_ACTION_SAFETY").status == "FAIL"


def test_suspension_gate_rederives_real_carry_and_mutation(tmp_path):
    suspension = derive_suspension_evidence_exact(ROOT)
    path = write_suspension_evidence(tmp_path, suspension)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        suspension_path=path, suspension_id=suspension.evidence_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["SUSPENSION_SAFETY"] == "PASS"
    assert by_gate["CORPORATE_ACTION_SAFETY"] == "FAIL"


def test_identity_gate_rederives_exact_master_transition_and_scoped_exclusion(
        tmp_path):
    identity = derive_identity_safety_evidence_exact(ROOT)
    path = write_identity_safety_evidence(tmp_path, identity)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        identity_path=path, identity_id=identity.evidence_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["IDENTITY_SAFETY"] == "PASS"
    assert by_gate["SUSPENSION_SAFETY"] == "FAIL"


def test_delisting_gate_keeps_effective_and_knowledge_time_distinct(tmp_path):
    delisting = derive_delisting_safety_evidence_exact(ROOT)
    path = write_delisting_safety_evidence(tmp_path, delisting)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        delisting_path=path, delisting_id=delisting.evidence_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["DELISTING_SAFETY"] == "PASS"
    assert by_gate["IDENTITY_SAFETY"] == "FAIL"


def test_incremental_gate_reruns_real_selector_and_materializer(tmp_path):
    evidence = derive_incremental_idempotency_evidence_exact(
        ROOT, tmp_path / "source-run")
    path = write_incremental_idempotency_evidence(tmp_path, evidence)
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT, partition_path=tmp_path / "missing.jsonl",
        partition_id="0" * 64,
        semantic_ledger_path=tmp_path / "missing.json",
        semantic_ledger_id="0" * 64,
        incremental_path=path, incremental_id=evidence.evidence_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["INCREMENTAL_IDEMPOTENCY"] == "PASS"
    assert by_gate["DETERMINISTIC_REPLAY"] == "FAIL"


@pytest.mark.skipif(os.environ.get("V52_REAL_MONTH_GATES") != "1",
                    reason="explicit source-pinned real-month gate run required")
def test_real_month_partition_and_lineage_gates_require_source_pins():
    root = ROOT / "data/phase_2b_checkpoint18_real_month"
    partition_id = "3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9"
    coverage_id = "834534a947d79b10a16404ae35430aafb63b36e0ac467d46b97a57117959ef75"
    scoped_id = "a1092d6465b32c7141a9befb290938adecca2f08b8fb646389becf941f9c656e"
    semantic_id = "61a785a351ff208a9a931d40980119eee1f268c803845782fae938bdab6b4b01"
    comparison_id = "c3b16aa0f7618e702e5bcab8b977b1919a75f72c5d65795576a1eeb74dd0bca8"
    contract_id = "ca95825596b61cf9591da88ebca2b4465691a7cfb524aa64cea963168088e14c"
    maturation_id = "0f25ed765f0d590ed67871ed1cf5bfb547d094c51e3acd152d51f2a1e8b1ac35"
    unsafe_id = "14c7c288ffac146fd90c1e1d3d426d999cf1212825e96805c04513c105af19ae"
    partition_path = root / "labels/historical/2010-01" / f"{partition_id}.jsonl"
    source_approvals = read_semantic_group_ledger_exact(
        root / "gate_evidence" / f"semantic-groups-{semantic_id}.json",
        semantic_id).source_approval_ids
    manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None,
        active_partitions=(read_partition_exact(partition_path, partition_id),),
        partition_supersession=(), phase2a_acceptance_id=PHASE2A_ACCEPTANCE_ID,
        lineage_ids=source_approvals)
    manifest_path = write_manifest(root, manifest)
    ca = derive_ca_safety_evidence_exact(ROOT)
    ca_path = write_ca_safety_evidence(root, ca)
    suspension = derive_suspension_evidence_exact(ROOT)
    suspension_path = write_suspension_evidence(root, suspension)
    identity = derive_identity_safety_evidence_exact(ROOT)
    identity_path = write_identity_safety_evidence(root, identity)
    delisting = derive_delisting_safety_evidence_exact(ROOT)
    delisting_path = write_delisting_safety_evidence(root, delisting)
    incremental = derive_incremental_idempotency_evidence_exact(
        ROOT, root / "incremental-gate-scratch")
    incremental_path = write_incremental_idempotency_evidence(root, incremental)
    replay_id = "349b09b145cd7f7877d0989b0c72d8a4f0cd621391fc032663a1d9221eef726b"
    replay_path = root / "gate_evidence" / f"replay-{replay_id}.json"
    evaluation = evaluate_phase2b_gates_v2_exact(
        source_root=ROOT,
        partition_path=partition_path,
        partition_id=partition_id,
        semantic_ledger_path=root / "gate_evidence" / f"semantic-groups-{semantic_id}.json",
        semantic_ledger_id=semantic_id,
        coverage_path=root / "gate_evidence" / f"month-coverage-{coverage_id}.json",
        coverage_id=coverage_id,
        scoped_path=root / "scoped_exclusions" / f"{scoped_id}.json",
        scoped_id=scoped_id,
        comparison_path=root / "gate_evidence" / f"row-comparison-{comparison_id}.json",
        comparison_id=comparison_id,
        contract_path=root / "gate_evidence" / f"contract-pins-{contract_id}.json",
        contract_id=contract_id,
        maturation_path=root / "gate_evidence" / f"maturation-{maturation_id}.json",
        maturation_id=maturation_id,
        unsafe_path=root / "gate_evidence" / f"unsafe-preservation-{unsafe_id}.json",
        unsafe_id=unsafe_id,
        manifest_path=manifest_path,
        manifest_id=manifest.manifest_id,
        active_partition_paths=(partition_path,),
        ca_path=ca_path, ca_id=ca.evidence_id,
        suspension_path=suspension_path, suspension_id=suspension.evidence_id,
        identity_path=identity_path, identity_id=identity.evidence_id,
        delisting_path=delisting_path, delisting_id=delisting.evidence_id,
        incremental_path=incremental_path, incremental_id=incremental.evidence_id,
        replay_path=replay_path, replay_id=replay_id,
    )
    by_gate = {item.gate: item.status for item in evaluation.results}
    assert by_gate["CONTRACT_PINNING"] == "PASS"
    assert by_gate["PARTITION_INTEGRITY"] == "PASS"
    assert by_gate["LINEAGE_INTEGRITY"] == "PASS"
    assert by_gate["PENDING_MATURATION"] == "PASS"
    assert by_gate["NOT_LABEL_SAFE_PRESERVATION"] == "PASS"
    assert by_gate["MANIFEST_INTEGRITY"] == "PASS"
    assert by_gate["CORPORATE_ACTION_SAFETY"] == "PASS"
    assert by_gate["SUSPENSION_SAFETY"] == "PASS"
    assert by_gate["IDENTITY_SAFETY"] == "PASS"
    assert by_gate["DELISTING_SAFETY"] == "PASS"
    assert by_gate["INCREMENTAL_IDEMPOTENCY"] == "PASS"
    assert by_gate["DETERMINISTIC_REPLAY"] == "PASS"
    assert sum(status == "PASS" for status in by_gate.values()) == 17
