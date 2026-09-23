from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any, Mapping

from v5_2.data.identity import canonical_json, content_hash


class HistoricalStatusAuthorityError(RuntimeError):
    """Portable historical status authority cannot be trusted."""


def _verify_hash(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise HistoricalStatusAuthorityError(f"{name} must be a SHA-256 identity")


def _identity(schema: str, values: Mapping[str, Any]) -> str:
    return content_hash({"schema_version": schema, **values})


def _verify_dataclass(value: object, schema: str, identity_fields: tuple[str, ...]) -> bool:
    body = {
        field.name: getattr(value, field.name)
        for field in fields(value)
        if field.name not in identity_fields
    }
    digest = _identity(schema, body)
    return all(getattr(value, name) == digest for name in identity_fields)


@dataclass(frozen=True, slots=True)
class HistoricalStatusComponentV1:
    component_id: str
    component_kind: str
    canonical_security_identity: str
    effective_from: date
    effective_to: date | None
    event_session: date | None
    source_row_hash: str
    availability_basis: str
    availability_input_date: date
    source_fields: Mapping[str, Any]
    content_hash: str

    @classmethod
    def create(cls, **values: Any) -> HistoricalStatusComponentV1:
        kind = str(values["component_kind"])
        if kind not in {
            "LIFECYCLE", "RISK_WARNING", "FULL_DAY_SUSPENSION",
            "PARTIAL_SUSPENSION", "RESUMPTION",
        }:
            raise HistoricalStatusAuthorityError("unsupported component kind")
        _verify_hash(str(values["source_row_hash"]), "source_row_hash")
        if not str(values["canonical_security_identity"]).strip():
            raise HistoricalStatusAuthorityError("canonical identity is required")
        if values["effective_to"] is not None and values["effective_to"] < values["effective_from"]:
            raise HistoricalStatusAuthorityError("component interval is reversed")
        canonical_fields = json.loads(canonical_json(values["source_fields"]).decode("utf-8"))
        body = {**values, "component_kind": kind, "source_fields": canonical_fields}
        digest = _identity("HistoricalStatusComponentV1", body)
        return cls(component_id=digest, content_hash=digest, **body)

    def verify(self) -> bool:
        return _verify_dataclass(
            self, "HistoricalStatusComponentV1", ("component_id", "content_hash")
        )


@dataclass(frozen=True, slots=True)
class HistoricalStatusShardV1:
    component_kind: str
    component_ids: tuple[str, ...]
    row_count: int
    content_hash: str
    storage_hash: str
    encoding: str

    def verify(self) -> bool:
        body = {
            "component_kind": self.component_kind,
            "component_ids": self.component_ids,
            "row_count": self.row_count,
        }
        return (
            self.encoding == "canonical-json+gzip-mtime0-v1"
            and self.row_count == len(self.component_ids)
            and self.content_hash == _identity("HistoricalStatusShardV1", body)
        )


@dataclass(frozen=True, slots=True)
class EncodedHistoricalStatusShard:
    descriptor: HistoricalStatusShardV1
    compressed_bytes: bytes

    @property
    def content_hash(self) -> str:
        return self.descriptor.content_hash

    @property
    def storage_hash(self) -> str:
        return self.descriptor.storage_hash


def _gzip(payload: bytes) -> bytes:
    target = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as stream:
        stream.write(payload)
    return target.getvalue()


class HistoricalStatusShardStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def encode(
        self, component_kind: str, components: tuple[HistoricalStatusComponentV1, ...]
    ) -> EncodedHistoricalStatusShard:
        if not components:
            raise HistoricalStatusAuthorityError("shard must not be empty")
        if any(item.component_kind != component_kind for item in components):
            raise HistoricalStatusAuthorityError("component kind mismatch")
        if any(not item.verify() for item in components):
            raise HistoricalStatusAuthorityError("component identity mismatch")
        source_rows = tuple(item.source_row_hash for item in components)
        if len(source_rows) != len(set(source_rows)):
            raise HistoricalStatusAuthorityError("duplicate source row identity")
        ordered = tuple(sorted(components, key=lambda item: item.component_id))
        component_ids = tuple(item.component_id for item in ordered)
        body = {
            "component_kind": component_kind,
            "component_ids": component_ids,
            "row_count": len(ordered),
        }
        shard_hash = _identity("HistoricalStatusShardV1", body)
        payload = canonical_json(
            {
                "component_kind": component_kind,
                "components": [
                    {field.name: getattr(item, field.name) for field in fields(item)}
                    for item in ordered
                ],
                "content_hash": shard_hash,
                "schema_version": "HistoricalStatusShardPayloadV1",
            }
        )
        compressed = _gzip(payload)
        descriptor = HistoricalStatusShardV1(
            **body,
            content_hash=shard_hash,
            storage_hash=hashlib.sha256(compressed).hexdigest(),
            encoding="canonical-json+gzip-mtime0-v1",
        )
        return EncodedHistoricalStatusShard(descriptor, compressed)

    def path(self, descriptor: HistoricalStatusShardV1) -> Path:
        return self.root / descriptor.component_kind.lower() / f"{descriptor.storage_hash}.json.gz"

    def put(self, encoded: EncodedHistoricalStatusShard) -> Path:
        path = self.path(encoded.descriptor)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            if path.read_bytes() != encoded.compressed_bytes:
                raise HistoricalStatusAuthorityError("immutable shard collision")
            return path
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded.compressed_bytes)
        return path

    def read(
        self, path: Path, *, expected: HistoricalStatusShardV1
    ) -> tuple[HistoricalStatusComponentV1, ...]:
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected.storage_hash:
            raise HistoricalStatusAuthorityError("storage hash mismatch")
        try:
            stored = json.loads(gzip.decompress(payload))
        except (OSError, json.JSONDecodeError) as error:
            raise HistoricalStatusAuthorityError("shard bytes are invalid") from error
        if stored.get("component_kind") != expected.component_kind:
            raise HistoricalStatusAuthorityError("component kind mismatch")
        components = []
        for raw in stored.get("components", ()):
            raw = dict(raw)
            claimed_id = raw.pop("component_id", None)
            claimed_hash = raw.pop("content_hash", None)
            raw["effective_from"] = date.fromisoformat(raw["effective_from"])
            raw["effective_to"] = date.fromisoformat(raw["effective_to"]) if raw["effective_to"] else None
            raw["event_session"] = date.fromisoformat(raw["event_session"]) if raw["event_session"] else None
            raw["availability_input_date"] = date.fromisoformat(raw["availability_input_date"])
            component = HistoricalStatusComponentV1.create(**raw)
            if component.component_id != claimed_id or component.content_hash != claimed_hash:
                raise HistoricalStatusAuthorityError("component identity mismatch")
            components.append(component)
        rebuilt = self.encode(expected.component_kind, tuple(components))
        if rebuilt.descriptor != expected or rebuilt.compressed_bytes != payload:
            raise HistoricalStatusAuthorityError("shard identity mismatch")
        return tuple(components)


@dataclass(frozen=True, slots=True)
class HistoricalStatusAuthorityV1:
    authority_id: str
    coverage_start: date
    coverage_end: date
    parent_panel_id: str
    parent_manifest_id: str
    parent_approval_id: str
    pit_evidence_id: str
    source_version_identity: str
    raw_payload_hashes: tuple[str, ...]
    receipt_hashes: tuple[str, ...]
    request_inventory_id: str
    shard_descriptors: tuple[HistoricalStatusShardV1, ...]
    authority_policy_version: str
    content_hash: str

    @classmethod
    def create(cls, **values: Any) -> HistoricalStatusAuthorityV1:
        if values["coverage_end"] < values["coverage_start"]:
            raise HistoricalStatusAuthorityError("coverage interval is reversed")
        for name in (
            "parent_panel_id", "parent_manifest_id", "parent_approval_id",
            "pit_evidence_id", "source_version_identity", "request_inventory_id",
        ):
            _verify_hash(str(values[name]), name)
        for name in ("raw_payload_hashes", "receipt_hashes"):
            ordered = tuple(values[name])
            if not ordered or ordered != tuple(sorted(set(ordered))):
                raise HistoricalStatusAuthorityError(f"{name} must be a sorted unique set")
            for item in ordered:
                _verify_hash(item, name)
        descriptors = tuple(values["shard_descriptors"])
        if not descriptors or any(not item.verify() for item in descriptors):
            raise HistoricalStatusAuthorityError("shard descriptor is invalid")
        body = {**values, "shard_descriptors": descriptors}
        digest = _identity("HistoricalStatusAuthorityV1", body)
        return cls(authority_id=digest, content_hash=digest, **body)

    def verify(self) -> bool:
        return _verify_dataclass(
            self, "HistoricalStatusAuthorityV1", ("authority_id", "content_hash")
        ) and all(item.verify() for item in self.shard_descriptors)


@dataclass(frozen=True, slots=True)
class HistoricalStatusDerivationV1:
    derivation_id: str
    authority_id: str
    canonical_security_identity: str
    session: date
    cutoff: datetime
    listed: bool
    delisted: bool
    risk_warning: bool
    full_day_suspended: bool
    lifecycle_component_id: str
    applicable_risk_component_ids: tuple[str, ...]
    applicable_suspension_component_ids: tuple[str, ...]
    closed_world_shard_ids: tuple[str, ...]
    available_at: datetime
    availability_policy_id: str
    parent_approval_id: str
    parent_manifest_id: str
    source_version_identity: str
    content_hash: str

    def verify(self) -> bool:
        return _verify_dataclass(
            self, "HistoricalStatusDerivationV1", ("derivation_id", "content_hash")
        )


@dataclass(frozen=True, slots=True)
class HistoricalStatusCoverageLedgerV1:
    ledger_id: str
    authority_id: str
    coverage_start: date
    coverage_end: date
    counts: Mapping[str, int]
    unresolved_identities: int
    unresolved_sessions: int
    coverage_gaps: tuple[str, ...]
    quarantine_count: int
    content_hash: str

    def verify(self) -> bool:
        return _verify_dataclass(
            self, "HistoricalStatusCoverageLedgerV1", ("ledger_id", "content_hash")
        )


@dataclass(frozen=True, slots=True)
class HistoricalStatusReplayEvidenceV1:
    evidence_id: str
    authority_id: str
    first_output_hash: str
    second_output_hash: str
    replay_status: str
    policy_version: str
    content_hash: str

    def verify(self) -> bool:
        return _verify_dataclass(
            self, "HistoricalStatusReplayEvidenceV1", ("evidence_id", "content_hash")
        )


@dataclass(frozen=True, slots=True)
class HistoricalStatusCompositionV1:
    composition_id: str
    parent_panel_id: str
    parent_manifest_id: str
    parent_approval_id: str
    derived_authority_id: str
    derived_manifest_id: str
    derived_approval_id: str
    composition_rule: str
    content_hash: str

    def verify(self) -> bool:
        return _verify_dataclass(
            self, "HistoricalStatusCompositionV1", ("composition_id", "content_hash")
        )

