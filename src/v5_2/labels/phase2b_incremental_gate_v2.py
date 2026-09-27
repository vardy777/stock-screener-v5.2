"""Real-source incremental selector/materializer retry evidence."""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.contracts import LabelInputBundleV1
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelRowV1
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.incremental import (
    materialize_incremental_generation, select_incremental_workset,
)
from v5_2.labels.materializer import YearMonthV1, materialize_month
from v5_2.labels.partition_store import write_manifest
from v5_2.labels.phase2b_contract_pins_v2 import PHASE2A_ACCEPTANCE_ID


_ID = re.compile(r"^[0-9a-f]{64}$")
_BASE_BUNDLE_ID = "8a212db4e0337eaceaf90ddf167ce9b278cd9adde05c584f826a6006c99125fa"


def _completed(base: LabelInputBundleV1, day) -> LabelInputBundleV1:
    values = {field.name: getattr(base, field.name) for field in fields(base)
              if field.name != "content_hash"}
    values["latest_completed_session"] = day
    return LabelInputBundleV1.create(**values)


@dataclass(frozen=True, slots=True)
class IncrementalIdempotencyEvidenceV2:
    base_bundle_id: str
    h0_row_id: str
    h5_row_id: str
    predecessor_manifest_id: str
    first_manifest_id: str
    retry_manifest_id: str
    first_partition_id: str
    retry_partition_id: str
    initial_work_items: int
    after_maturity_work_items: int
    old_partition_unchanged: bool
    duplicate_partition_count: int
    evidence_id: str

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "evidence_id"}
        return (self.base_bundle_id == _BASE_BUNDLE_ID
                and all(_ID.fullmatch(value) for value in (
                    self.h0_row_id, self.h5_row_id,
                    self.predecessor_manifest_id, self.first_manifest_id,
                    self.retry_manifest_id, self.first_partition_id,
                    self.retry_partition_id))
                and self.h0_row_id != self.h5_row_id
                and self.first_manifest_id == self.retry_manifest_id
                and self.first_partition_id == self.retry_partition_id
                and self.initial_work_items == 1
                and self.after_maturity_work_items == 0
                and self.old_partition_unchanged
                and self.duplicate_partition_count == 0
                and self.evidence_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def derive_incremental_idempotency_evidence_exact(
        source_root: Path, scratch_root: Path) -> IncrementalIdempotencyEvidenceV2:
    slot = next(item for item in build_frozen_inventory().slots if item.slot == 4)
    base = Phase2AEvidenceAssemblerV1(source_root).assemble(slot)
    if not base.verify() or base.content_hash != _BASE_BUNDLE_ID:
        raise ValueError("frozen real maturation bundle identity mismatch")
    h0_bundle = _completed(base, base.anchor_session)
    h5_day = base.approved_exchange_sessions[5]
    h5_bundle = _completed(base, h5_day)
    engine = ReferenceLabelEngine()
    h0_row = LabelRowV1.create(
        result=engine.evaluate(h0_bundle), bundle=h0_bundle,
        materialization_version="phase2b-v1")
    h5_row = LabelRowV1.create(
        result=engine.evaluate(h5_bundle), bundle=h5_bundle,
        materialization_version="phase2b-v1")
    if h0_row.row_id == h5_row.row_id:
        raise ValueError("real maturity did not change row identity")
    lineages = tuple(item.approval_id for item in base.domain_lineage)
    month = YearMonthV1.create(base.anchor_session.year, base.anchor_session.month)
    initial = materialize_month(scratch_root, month, lineages,
                                "phase2b-v1", rows=(h0_row,))
    predecessor = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(initial.partition,),
        partition_supersession=(), phase2a_acceptance_id=PHASE2A_ACCEPTANCE_ID,
        lineage_ids=lineages)
    write_manifest(scratch_root, predecessor)
    old_bytes = initial.path.read_bytes()
    workset = select_incremental_workset(
        predecessor, h5_day, (), rows=(h0_row,),
        approved_exchange_sessions_by_anchor={
            (h0_row.canonical_security_identity, h0_row.anchor_session):
                base.approved_exchange_sessions},
    )
    if len(workset.items) != 1:
        raise ValueError("real maturity selector did not choose one row")
    arguments = dict(
        active_partitions=((initial.partition, (h0_row,)),),
        replacement_rows=(h5_row,), materialization_version="phase2b-v1")
    first = materialize_incremental_generation(
        scratch_root, predecessor, workset, **arguments)
    retry = materialize_incremental_generation(
        scratch_root, predecessor, workset, **arguments)
    if (first.manifest != retry.manifest
            or first.replacement_partitions != retry.replacement_partitions
            or first.manifest.active_partition_ids
               != (first.replacement_partitions[0].partition_id,)):
        raise ValueError("real incremental retry changed active generation")
    after = select_incremental_workset(
        first.manifest, h5_day, (), rows=(h5_row,))
    files = tuple((scratch_root / "labels" / "historical" / month.key).glob("*.jsonl"))
    body = {
        "base_bundle_id": base.content_hash,
        "h0_row_id": h0_row.row_id,
        "h5_row_id": h5_row.row_id,
        "predecessor_manifest_id": predecessor.manifest_id,
        "first_manifest_id": first.manifest.manifest_id,
        "retry_manifest_id": retry.manifest.manifest_id,
        "first_partition_id": first.replacement_partitions[0].partition_id,
        "retry_partition_id": retry.replacement_partitions[0].partition_id,
        "initial_work_items": len(workset.items),
        "after_maturity_work_items": len(after.items),
        "old_partition_unchanged": initial.path.read_bytes() == old_bytes,
        "duplicate_partition_count": len(files) - len({path.stem for path in files}),
    }
    result = IncrementalIdempotencyEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "IncrementalIdempotencyEvidenceV2", **body}))
    if not result.verify():
        raise ValueError("incremental idempotency evidence invalid")
    return result


def write_incremental_idempotency_evidence(root: Path,
        evidence: IncrementalIdempotencyEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified incremental evidence required")
    path = root / "gate_evidence" / f"incremental-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable incremental evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_incremental_idempotency_evidence_exact(path: Path, expected_id: str
        ) -> IncrementalIdempotencyEvidenceV2:
    if not _ID.fullmatch(expected_id) or path.name != f"incremental-{expected_id}.json":
        raise ValueError("incremental evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        result = IncrementalIdempotencyEvidenceV2(**json.loads(raw))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("incremental evidence unavailable or malformed") from error
    if (result.evidence_id != expected_id or not result.verify()
            or canonical_json(result) != raw):
        raise ValueError("incremental evidence identity mismatch")
    return result
