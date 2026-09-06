from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from v5_2.data.identity import canonical_json, content_hash


class RawArtifactError(RuntimeError):
    """An immutable raw-artifact contract was violated."""


_SECRET_KEYS = {"token", "credential", "authorization", "api_key", "apikey", "secret"}


def _reject_secret_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in _SECRET_KEYS:
                raise RawArtifactError("secret-shaped field is forbidden in artifacts")
            _reject_secret_keys(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _reject_secret_keys(nested)


def _canonical_copy(value: Any) -> Any:
    return json.loads(canonical_json(value).decode("utf-8"))


@dataclass(frozen=True, slots=True)
class RawPayloadArtifactV1:
    request_id: str
    page_identity: Mapping[str, Any]
    provider_payload: Any
    semantic_metadata: Mapping[str, Any]
    payload_hash: str

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        page_identity: Mapping[str, Any],
        provider_payload: Any,
        semantic_metadata: Mapping[str, Any],
    ) -> RawPayloadArtifactV1:
        _reject_secret_keys((page_identity, provider_payload, semantic_metadata))
        body = {
            "request_id": request_id,
            "page_identity": _canonical_copy(page_identity),
            "provider_payload": _canonical_copy(provider_payload),
            "semantic_metadata": _canonical_copy(semantic_metadata),
        }
        return cls(**body, payload_hash=content_hash(body))

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "page_identity": self.page_identity,
            "provider_payload": self.provider_payload,
            "semantic_metadata": self.semantic_metadata,
            "payload_hash": self.payload_hash,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionReceiptV1:
    payload_hash: str
    acquired_at: datetime
    attempt_metadata: Mapping[str, Any]
    transport_metadata: Mapping[str, Any]
    receipt_hash: str

    @classmethod
    def create(
        cls,
        *,
        payload_hash: str,
        acquired_at: datetime,
        attempt_metadata: Mapping[str, Any],
        transport_metadata: Mapping[str, Any],
    ) -> AcquisitionReceiptV1:
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise RawArtifactError("acquired_at must be timezone-aware")
        _reject_secret_keys((attempt_metadata, transport_metadata))
        body = {
            "payload_hash": payload_hash,
            "acquired_at": acquired_at,
            "attempt_metadata": _canonical_copy(attempt_metadata),
            "transport_metadata": _canonical_copy(transport_metadata),
        }
        return cls(**body, receipt_hash=content_hash(body))

    def as_dict(self) -> dict[str, Any]:
        return {
            "payload_hash": self.payload_hash,
            "acquired_at": self.acquired_at,
            "attempt_metadata": self.attempt_metadata,
            "transport_metadata": self.transport_metadata,
            "receipt_hash": self.receipt_hash,
        }


def observe_revision(previous: RawPayloadArtifactV1, current: RawPayloadArtifactV1) -> bool:
    if (
        previous.request_id != current.request_id
        or previous.page_identity != current.page_identity
    ):
        raise RawArtifactError("revision comparison requires the same logical page")
    return previous.payload_hash != current.payload_hash


class RawArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def payload_path(
        self, source_name: str, dataset_kind: str, artifact: RawPayloadArtifactV1
    ) -> Path:
        page_hash = content_hash(artifact.page_identity)
        return (
            self.root
            / "raw"
            / source_name
            / dataset_kind
            / artifact.request_id[:16]
            / page_hash[:16]
            / f"{artifact.payload_hash}.json"
        )

    def put_payload(
        self, source_name: str, dataset_kind: str, artifact: RawPayloadArtifactV1
    ) -> Path:
        path = self.payload_path(source_name, dataset_kind, artifact)
        content = canonical_json(artifact.as_dict())
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            if path.read_bytes() != content:
                raise RawArtifactError("immutable artifact collision")
            return path
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        return path

    def read_payload(self, path: Path) -> RawPayloadArtifactV1:
        stored = json.loads(path.read_text(encoding="utf-8"))
        claimed_hash = stored.pop("payload_hash", None)
        artifact = RawPayloadArtifactV1.create(**stored)
        if claimed_hash != artifact.payload_hash:
            raise RawArtifactError("payload hash mismatch")
        return artifact

    def require_payload_hashes(
        self,
        source_name: str,
        dataset_kind: str,
        request_id: str,
        payload_hashes: tuple[str, ...],
    ) -> None:
        request_root = (
            self.root / "raw" / source_name / dataset_kind / request_id[:16]
        )
        for payload_hash in payload_hashes:
            matches = tuple(request_root.rglob(f"{payload_hash}.json"))
            if len(matches) != 1:
                raise RawArtifactError("missing or ambiguous raw artifact")
            artifact = self.read_payload(matches[0])
            if artifact.request_id != request_id or artifact.payload_hash != payload_hash:
                raise RawArtifactError("raw artifact identity mismatch")

    def put_receipt(self, receipt: AcquisitionReceiptV1) -> Path:
        path = (
            self.root
            / "receipts"
            / receipt.payload_hash[:16]
            / f"{receipt.receipt_hash}.json"
        )
        content = canonical_json(receipt.as_dict())
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            if path.read_bytes() != content:
                raise RawArtifactError("immutable receipt collision")
            return path
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        return path

    def read_receipt(self, path: Path) -> AcquisitionReceiptV1:
        stored = json.loads(path.read_text(encoding="utf-8"))
        claimed = stored.pop("receipt_hash", None)
        stored["acquired_at"] = datetime.fromisoformat(stored["acquired_at"])
        receipt = AcquisitionReceiptV1.create(**stored)
        if claimed != receipt.receipt_hash:
            raise RawArtifactError("receipt hash mismatch")
        return receipt
