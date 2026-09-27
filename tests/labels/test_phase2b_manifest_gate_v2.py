"""Manifest hash alone cannot prove active physical partition membership."""

from v5_2.data.identity import content_hash
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelPartitionV1
from v5_2.labels.partition_store import write_manifest, write_partition
from v5_2.labels.phase2b_manifest_gate_v2 import verify_manifest_physical_exact
from tests.labels.test_phase2b_coverage import row
from v5_2.labels.contracts import LabelState


def test_manifest_requires_exact_physical_partition_and_lineage(tmp_path):
    item = row(1, LabelState.LABEL_AVAILABLE)
    lineage = tuple(f"{number}" * 64 for number in range(1, 6))
    generation = content_hash({
        "schema_version": "LabelPartitionGenerationV1",
        "partition_key": "2024-01", "materialization_version": "phase2b-v1",
        "lineage_ids": lineage, "row_ids": (item.row_id,),
    })
    partition = LabelPartitionV1.create(
        partition_key="2024-01", generation_id=generation, rows=(item,))
    partition_path = write_partition(tmp_path, partition, (item,))
    manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(partition,),
        partition_supersession=(), phase2a_acceptance_id="a" * 64,
        lineage_ids=lineage)
    manifest_path = write_manifest(tmp_path, manifest)
    assert verify_manifest_physical_exact(
        manifest_path, manifest.manifest_id, (partition_path,),
        "a" * 64, lineage)
    assert not verify_manifest_physical_exact(
        manifest_path, manifest.manifest_id, (), "a" * 64, lineage)
    assert not verify_manifest_physical_exact(
        manifest_path, manifest.manifest_id, (partition_path,),
        "a" * 64, tuple(reversed(lineage)))
    assert not verify_manifest_physical_exact(
        manifest_path, manifest.manifest_id, (partition_path,),
        "b" * 64, lineage)


def test_successor_cannot_silently_drop_old_active_partition(tmp_path):
    item = row(1, LabelState.LABEL_AVAILABLE)
    lineage = tuple(f"{number}" * 64 for number in range(1, 6))
    generation = content_hash({
        "schema_version": "LabelPartitionGenerationV1",
        "partition_key": "2024-01", "materialization_version": "phase2b-v1",
        "lineage_ids": lineage, "row_ids": (item.row_id,),
    })
    current = LabelPartitionV1.create(
        partition_key="2024-01", generation_id=generation, rows=(item,))
    old = LabelPartitionV1.create(
        partition_key="2024-01", generation_id="old-generation", rows=(item,))
    physical = write_partition(tmp_path, current, (item,))
    predecessor = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(old,),
        partition_supersession=(), phase2a_acceptance_id="a" * 64,
        lineage_ids=lineage)
    previous_path = write_manifest(tmp_path, predecessor)
    successor = LabelDatasetManifestV1.create(
        previous_manifest_id=predecessor.manifest_id,
        previous_manifest=predecessor, active_partitions=(current,),
        partition_supersession=(), phase2a_acceptance_id="a" * 64,
        lineage_ids=lineage)
    successor_path = write_manifest(tmp_path, successor)
    assert not verify_manifest_physical_exact(
        successor_path, successor.manifest_id, (physical,),
        "a" * 64, lineage, previous_path)


def test_noncanonical_manifest_bytes_are_rejected(tmp_path):
    item = row(1, LabelState.LABEL_AVAILABLE)
    lineage = tuple(f"{number}" * 64 for number in range(1, 6))
    generation = content_hash({
        "schema_version": "LabelPartitionGenerationV1",
        "partition_key": "2024-01", "materialization_version": "phase2b-v1",
        "lineage_ids": lineage, "row_ids": (item.row_id,),
    })
    partition = LabelPartitionV1.create(
        partition_key="2024-01", generation_id=generation, rows=(item,))
    physical = write_partition(tmp_path, partition, (item,))
    manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(partition,),
        partition_supersession=(), phase2a_acceptance_id="a" * 64,
        lineage_ids=lineage)
    manifest_path = write_manifest(tmp_path, manifest)
    manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
    assert not verify_manifest_physical_exact(
        manifest_path, manifest.manifest_id, (physical,), "a" * 64, lineage)


def test_rehashed_valid_active_partition_swap_fails_frozen_expected_set(tmp_path):
    original_row = row(1, LabelState.LABEL_AVAILABLE)
    swapped_row = row(2, LabelState.LABEL_AVAILABLE)
    lineage = tuple(f"{number}" * 64 for number in range(1, 6))

    def partition_for(item):
        generation = content_hash({
            "schema_version": "LabelPartitionGenerationV1",
            "partition_key": "2024-01", "materialization_version": "phase2b-v1",
            "lineage_ids": lineage, "row_ids": (item.row_id,),
        })
        return LabelPartitionV1.create(
            partition_key="2024-01", generation_id=generation, rows=(item,))

    original = partition_for(original_row)
    swapped = partition_for(swapped_row)
    swapped_path = write_partition(tmp_path, swapped, (swapped_row,))
    rehashed_manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(swapped,),
        partition_supersession=(), phase2a_acceptance_id="a" * 64,
        lineage_ids=lineage)
    manifest_path = write_manifest(tmp_path, rehashed_manifest)
    assert not verify_manifest_physical_exact(
        manifest_path, rehashed_manifest.manifest_id, (swapped_path,),
        "a" * 64, lineage, expected_active_partition_ids=(original.partition_id,))
