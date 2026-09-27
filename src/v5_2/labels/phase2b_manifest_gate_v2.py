"""Cross-artifact verification of a pinned Phase 2B manifest."""

from __future__ import annotations

from pathlib import Path

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.partition_store import (
    read_manifest_exact, read_partition_exact, read_partition_rows_exact,
)


def verify_manifest_physical_exact(
        manifest_path: Path, manifest_id: str,
        active_partition_paths: tuple[Path, ...],
        phase2a_acceptance_id: str,
        lineage_ids: tuple[str, ...],
        previous_manifest_path: Path | None = None,
        *, expected_active_partition_ids: tuple[str, ...] | None = None) -> bool:
    """Read all active bytes and prove month/generation/lineage membership."""
    try:
        manifest = read_manifest_exact(manifest_path, manifest_id)
        if (manifest_path.read_bytes() != canonical_json(manifest)
                or (expected_active_partition_ids is not None
                    and manifest.active_partition_ids
                        != expected_active_partition_ids)
                or manifest.phase2a_acceptance_id != phase2a_acceptance_id
                or manifest.lineage_ids != lineage_ids
                or len(lineage_ids) != 5
                or not active_partition_paths
                or len(active_partition_paths) != len(manifest.active_partition_ids)
                or len(set(manifest.active_partition_ids)) != len(manifest.active_partition_ids)):
            return False
        if manifest.previous_manifest_id is None:
            if manifest.partition_supersession or previous_manifest_path is not None:
                return False
        else:
            if previous_manifest_path is None:
                return False
            previous = read_manifest_exact(
                previous_manifest_path, manifest.previous_manifest_id)
            if previous_manifest_path.read_bytes() != canonical_json(previous):
                return False
            retained = set(previous.active_partition_ids) & set(
                manifest.active_partition_ids)
            superseded = {old for old, _ in manifest.partition_supersession}
            if (any(old not in previous.active_partition_ids
                    or new not in manifest.active_partition_ids
                    or old in manifest.active_partition_ids
                    for old, new in manifest.partition_supersession)
                    or len({old for old, _ in manifest.partition_supersession})
                       != len(manifest.partition_supersession)
                    or retained | superseded != set(previous.active_partition_ids)):
                return False
        months: set[str] = set()
        for expected_id, path in zip(manifest.active_partition_ids,
                                     active_partition_paths, strict=True):
            partition = read_partition_exact(path, expected_id)
            rows = read_partition_rows_exact(path, expected_id)
            if (partition.partition_key in months
                    or partition.row_count != len(rows)
                    or partition.row_ids != tuple(row.row_id for row in rows)
                    or not rows
                    or any(row.anchor_session.strftime("%Y-%m")
                           != partition.partition_key
                           or row.materialization_version != "phase2b-v1"
                           for row in rows)):
                return False
            expected_generation = content_hash({
                "schema_version": "LabelPartitionGenerationV1",
                "partition_key": partition.partition_key,
                "materialization_version": "phase2b-v1",
                "lineage_ids": lineage_ids,
                "row_ids": partition.row_ids,
            })
            if partition.generation_id != expected_generation:
                return False
            months.add(partition.partition_key)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False
