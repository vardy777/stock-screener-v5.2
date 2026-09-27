"""Incremental idempotency runs the actual selector and materializer on real evidence."""

from pathlib import Path

import pytest

from v5_2.labels.phase2b_incremental_gate_v2 import (
    derive_incremental_idempotency_evidence_exact,
    read_incremental_idempotency_evidence_exact,
    write_incremental_idempotency_evidence,
)
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.incremental import select_incremental_workset
from v5_2.labels.phase2b_maturation_gate_v2 import _with_completion


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


def test_real_incremental_selector_and_materializer_are_idempotent(tmp_path):
    evidence = derive_incremental_idempotency_evidence_exact(ROOT, tmp_path)
    assert evidence.verify()
    assert evidence.initial_work_items == 1
    assert evidence.after_maturity_work_items == 0
    assert evidence.first_manifest_id == evidence.retry_manifest_id
    assert evidence.first_partition_id == evidence.retry_partition_id
    assert evidence.old_partition_unchanged
    assert evidence.duplicate_partition_count == 0
    path = write_incremental_idempotency_evidence(tmp_path, evidence)
    assert read_incremental_idempotency_evidence_exact(path, evidence.evidence_id) == evidence
    with pytest.raises(ValueError):
        read_incremental_idempotency_evidence_exact(path, "f" * 64)


def test_real_h0_pending_without_approved_schedule_fails_closed():
    slot = next(item for item in build_frozen_inventory().slots if item.slot == 4)
    bundle = Phase2AEvidenceAssemblerV1(ROOT).assemble(slot)
    h0 = _with_completion(bundle, bundle.anchor_session)
    row = LabelRowV1.create(result=ReferenceLabelEngine().evaluate(h0),
                            bundle=h0, materialization_version="phase2b-v1")
    assert all(value.horizon_end_session is None for value in row.values)
    partition = LabelPartitionV1.create(partition_key="2024-09",
        generation_id="schedule-negative", rows=(row,))
    manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(partition,),
        partition_supersession=(), phase2a_acceptance_id="f" * 64,
        lineage_ids=("a" * 64,))
    with pytest.raises(ValueError, match="approved horizon schedule"):
        select_incremental_workset(
            manifest, bundle.approved_exchange_sessions[5], (), rows=(row,))
