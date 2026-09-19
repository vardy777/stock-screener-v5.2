from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from v5_2.labels.dataset_contracts import LabelPartitionV1, LabelRowV1


class ImmutableArtifactCollision(RuntimeError):
    pass


def _normalize(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value))
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _write_identical(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise ImmutableArtifactCollision(f"immutable artifact collision: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_partition(root: Path, partition: LabelPartitionV1, rows: Iterable[LabelRowV1]) -> Path:
    materialized = tuple(rows)
    if tuple(row.row_id for row in materialized) != partition.row_ids:
        raise ValueError("partition rows do not match pinned row IDs")
    if not partition.verify() or not all(row.verify() for row in materialized):
        raise ValueError("verified partition and rows required")
    payload = b"".join(_canonical(row) + b"\n" for row in materialized)
    digest = sha256(payload).hexdigest()
    path = root / "labels" / "historical" / partition.partition_key / f"{partition.partition_id}.jsonl"
    metadata = root / "partitions" / f"{partition.partition_id}.json"
    _write_identical(path, payload)
    _write_identical(metadata, _canonical({"partition": partition, "rows_sha256": digest}))
    return path


def read_partition_exact(path: Path, expected_id: str) -> LabelPartitionV1:
    if path.stem != expected_id:
        raise ValueError("expected partition ID does not match path")
    metadata_path = path.parents[3] / "partitions" / f"{expected_id}.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("canonical partition metadata unavailable") from exc
    if sha256(path.read_bytes()).hexdigest() != metadata.get("rows_sha256"):
        raise ValueError("canonical partition bytes mismatch")
    values = metadata.get("partition", {})
    partition = LabelPartitionV1(
        partition_key=values["partition_key"], generation_id=values["generation_id"],
        row_ids=tuple(values["row_ids"]), row_count=values["row_count"], partition_id=values["partition_id"],
    )
    if partition.partition_id != expected_id or not partition.verify():
        raise ValueError("canonical partition metadata invalid")
    return partition
