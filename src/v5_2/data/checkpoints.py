from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from v5_2.data.identity import canonical_json, content_hash


class CheckpointError(RuntimeError):
    """Checkpoint is missing, corrupt or incompatible."""


@dataclass(frozen=True, slots=True)
class CheckpointV1:
    request_id: str
    accepted_payload_hashes: tuple[str, ...]
    next_offset: int
    request_policy_version: str
    acquisition_policy_version: str
    checkpoint_hash: str

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        accepted_payload_hashes: tuple[str, ...],
        next_offset: int,
        request_policy_version: str,
        acquisition_policy_version: str,
    ) -> CheckpointV1:
        if isinstance(next_offset, bool) or not isinstance(next_offset, int) or next_offset < 0:
            raise CheckpointError("next_offset must be a non-negative integer")
        body = {
            "schema_version": "CheckpointV1",
            "request_id": request_id,
            "accepted_payload_hashes": accepted_payload_hashes,
            "next_offset": next_offset,
            "request_policy_version": request_policy_version,
            "acquisition_policy_version": acquisition_policy_version,
        }
        return cls(
            request_id=request_id,
            accepted_payload_hashes=accepted_payload_hashes,
            next_offset=next_offset,
            request_policy_version=request_policy_version,
            acquisition_policy_version=acquisition_policy_version,
            checkpoint_hash=content_hash(body),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "CheckpointV1",
            "request_id": self.request_id,
            "accepted_payload_hashes": self.accepted_payload_hashes,
            "next_offset": self.next_offset,
            "request_policy_version": self.request_policy_version,
            "acquisition_policy_version": self.acquisition_policy_version,
            "checkpoint_hash": self.checkpoint_hash,
        }


class CheckpointStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, request_id: str) -> Path:
        return self.root / "checkpoints" / f"{request_id}.json"

    def exists(self, request_id: str) -> bool:
        return self._path(request_id).is_file()

    def save(self, checkpoint: CheckpointV1) -> Path:
        path = self._path(checkpoint.request_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(canonical_json(checkpoint.as_dict()))
        os.replace(temporary, path)
        return path

    def load(self, request_id: str) -> CheckpointV1:
        path = self._path(request_id)
        if not path.is_file():
            raise CheckpointError("checkpoint not found")
        values = json.loads(path.read_text(encoding="utf-8"))
        values.pop("schema_version", None)
        claimed = values.pop("checkpoint_hash", None)
        values["accepted_payload_hashes"] = tuple(values["accepted_payload_hashes"])
        checkpoint = CheckpointV1.create(**values)
        if claimed != checkpoint.checkpoint_hash:
            raise CheckpointError("checkpoint hash mismatch")
        return checkpoint

    def require_compatible(
        self,
        request_id: str,
        request_policy_version: str,
        acquisition_policy_version: str,
    ) -> CheckpointV1:
        checkpoint = self.load(request_id)
        if checkpoint.request_policy_version != request_policy_version:
            raise CheckpointError("checkpoint request policy mismatch")
        if checkpoint.acquisition_policy_version != acquisition_policy_version:
            raise CheckpointError("checkpoint acquisition policy mismatch")
        return checkpoint
