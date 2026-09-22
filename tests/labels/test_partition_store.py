import pytest

from tests.labels.test_dataset_contracts import bundle_and_result
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1
from v5_2.labels.partition_store import (
    ImmutableArtifactCollision,
    read_manifest_exact,
    read_partition_exact,
    write_manifest,
    write_partition,
)


def partition_and_rows():
    bundle, result = bundle_and_result()
    row = LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")
    return LabelPartitionV1.create(partition_key="2024-01", generation_id="g1", rows=(row,)), (row,)


def test_partition_write_is_canonical_and_create_or_identical(tmp_path):
    partition, rows = partition_and_rows()
    first = write_partition(tmp_path, partition, rows)
    second = write_partition(tmp_path, partition, rows)
    assert first == second
    assert first.name == f"{partition.partition_id}.jsonl"
    assert read_partition_exact(first, partition.partition_id) == partition


def test_partition_collision_and_tamper_fail_closed(tmp_path):
    partition, rows = partition_and_rows()
    path = write_partition(tmp_path, partition, rows)
    path.write_bytes(b"different canonical bytes\n")
    with pytest.raises(ImmutableArtifactCollision):
        write_partition(tmp_path, partition, rows)
    path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="canonical"):
        read_partition_exact(path, partition.partition_id)


def test_partition_read_requires_exact_id_and_never_repairs_order(tmp_path):
    partition, rows = partition_and_rows()
    path = write_partition(tmp_path, partition, rows)
    with pytest.raises(ValueError, match="expected partition"):
        read_partition_exact(path, "f" * 64)


def test_manifest_write_is_exact_immutable_and_tamper_fails_closed(tmp_path):
    partition, _ = partition_and_rows()
    manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None,
        active_partitions=(partition,),
        partition_supersession=(),
        phase2a_acceptance_id="f" * 64,
        lineage_ids=("a" * 64,),
    )
    path = write_manifest(tmp_path, manifest)
    assert write_manifest(tmp_path, manifest) == path
    assert read_manifest_exact(path, manifest.manifest_id) == manifest
    path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="canonical manifest"):
        read_manifest_exact(path, manifest.manifest_id)
