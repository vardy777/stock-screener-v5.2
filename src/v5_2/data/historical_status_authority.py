from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.raw_artifacts import RawArtifactStore


class HistoricalStatusAuthorityError(RuntimeError):
    """Portable historical status authority cannot be trusted."""


def require_exact_hash_inventory(
    *, name: str, actual: tuple[str, ...], expected: tuple[str, ...]
) -> tuple[str, ...]:
    if len(actual) != len(set(actual)):
        raise HistoricalStatusAuthorityError(f"duplicate {name} identity")
    actual_set, expected_set = set(actual), set(expected)
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    if missing:
        raise HistoricalStatusAuthorityError(f"missing {name} identity")
    if extra:
        raise HistoricalStatusAuthorityError(f"extra {name} identity")
    return tuple(sorted(actual_set))


def ensure_repository_local_staging(repository_root: Path, staging_root: Path) -> Path:
    repository = repository_root.resolve(strict=True)
    staging = staging_root.resolve(strict=False)
    if staging == repository or repository not in staging.parents:
        raise HistoricalStatusAuthorityError("staging must be repository-local")
    if staging.exists() and staging.is_symlink():
        raise HistoricalStatusAuthorityError("staging symlink is forbidden")
    return staging


def _provider_date(value: Any, *, nullable: bool = False) -> date | None:
    if value in (None, "") and nullable:
        return None
    text = str(value)
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except (TypeError, ValueError) as error:
        raise HistoricalStatusAuthorityError("provider date is invalid") from error


def normalize_status_rows(*, lifecycle_rows, namechange_rows, suspension_rows):
    lifecycle = []
    for row in lifecycle_rows:
        source_hash = content_hash(row)
        start = _provider_date(row.get("list_date"))
        end = _provider_date(row.get("delist_date"), nullable=True)
        lifecycle.append(HistoricalStatusComponentV1.create(
            component_kind="LIFECYCLE",
            canonical_security_identity=str(row.get("ts_code", "")),
            effective_from=start,
            effective_to=end,
            event_session=None,
            source_row_hash=source_hash,
            availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
            availability_input_date=start,
            source_fields={"list_date": row.get("list_date"), "delist_date": row.get("delist_date")},
        ))
    risk = []
    for row in namechange_rows:
        if not re.match(r"^(?:S\*?ST|\*?ST)", str(row.get("name", "")), re.I):
            continue
        start = _provider_date(row.get("start_date"))
        end = _provider_date(row.get("end_date"), nullable=True)
        announcement = _provider_date(row.get("ann_date"))
        risk.append(HistoricalStatusComponentV1.create(
            component_kind="RISK_WARNING",
            canonical_security_identity=str(row.get("ts_code", "")),
            effective_from=start,
            effective_to=end,
            event_session=None,
            source_row_hash=content_hash(row),
            availability_basis="NEXT_SESSION_SAFE",
            availability_input_date=announcement,
            source_fields={key: row.get(key) for key in (
                "name", "start_date", "end_date", "ann_date", "change_reason"
            )},
        ))
    suspension = []
    for row in suspension_rows:
        event = _provider_date(row.get("trade_date"))
        kind = str(row.get("suspend_type", "")).upper()
        if kind == "S":
            component_kind = "PARTIAL_SUSPENSION" if row.get("suspend_timing") else "FULL_DAY_SUSPENSION"
        elif kind == "R":
            component_kind = "RESUMPTION"
        else:
            raise HistoricalStatusAuthorityError("unknown suspension type")
        suspension.append(HistoricalStatusComponentV1.create(
            component_kind=component_kind,
            canonical_security_identity=str(row.get("ts_code", "")),
            effective_from=event,
            effective_to=event,
            event_session=event,
            source_row_hash=content_hash(row),
            availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
            availability_input_date=event,
            source_fields={key: row.get(key) for key in (
                "trade_date", "suspend_type", "suspend_timing"
            )},
        ))
    key = lambda item: item.component_id
    return tuple(sorted(lifecycle, key=key)), tuple(sorted(risk, key=key)), tuple(sorted(suspension, key=key))


@dataclass(frozen=True, slots=True)
class FrozenStatusInputReconstructionV1:
    raw_payload_hashes: tuple[str, ...]
    receipt_hashes: tuple[str, ...]
    lifecycle_rows: tuple[Mapping[str, Any], ...]
    namechange_rows: tuple[Mapping[str, Any], ...]
    suspension_rows: tuple[Mapping[str, Any], ...]
    lifecycle_hash: str
    risk_warning_hash: str
    suspension_hash: str


def _stored_identity(value: Mapping[str, Any], schema: str, identities: tuple[str, ...]) -> bool:
    body = {key: item for key, item in value.items() if key not in identities}
    digest = _identity(schema, body)
    return all(value.get(key) == digest for key in identities)


def _canonical_provider_rows(rows) -> tuple[Mapping[str, Any], ...]:
    unique = {content_hash(row): json.loads(canonical_json(row)) for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _artifact_paths(root: Path, dataset_kind: str) -> tuple[Path, ...]:
    return tuple(sorted(
        path for path in root.rglob("*.json")
        if dataset_kind in path.parts and "receipts" not in path.parts
    ))


def reconstruct_frozen_status_inputs(
    *, repository_root: Path, staging_root: Path, manifest_path: Path,
    panel_path: Path, approval_path: Path, revoked_approval_ids: tuple[str, ...] = (),
) -> FrozenStatusInputReconstructionV1:
    repository = repository_root.resolve(strict=True)
    staging = ensure_repository_local_staging(repository, staging_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if not _stored_identity(panel, "ResearchWideHistoricalSecurityStatusPanelV1", ("panel_id", "content_hash")):
        raise HistoricalStatusAuthorityError("parent panel identity mismatch")
    if not _stored_identity(manifest, "DatasetManifestV1", ("dataset_id", "manifest_hash")):
        raise HistoricalStatusAuthorityError("parent manifest identity mismatch")
    if not _stored_identity(approval, "SourceApprovalArtifactV1", ("approval_id", "content_hash")):
        raise HistoricalStatusAuthorityError("parent approval identity mismatch")
    if approval["approval_id"] in set(revoked_approval_ids):
        raise HistoricalStatusAuthorityError("parent approval is revoked")
    if manifest["approval_id"] != approval["approval_id"] or manifest["fact_content_hashes"] != [panel["panel_id"]]:
        raise HistoricalStatusAuthorityError("parent governance pins mismatch")
    if approval["rule_set"].get("panel_id") != panel["panel_id"]:
        raise HistoricalStatusAuthorityError("approval panel pin mismatch")

    payload_hashes: list[str] = []
    by_kind: dict[str, list[Mapping[str, Any]]] = {
        "risk_warning_history": [], "suspension_history": []
    }
    raw_store = RawArtifactStore(staging)
    for kind in by_kind:
        for path in _artifact_paths(staging, kind):
            artifact = raw_store.read_payload(path)
            if "datahubco_tushare_proxy" not in path.parts:
                raise HistoricalStatusAuthorityError("wrong raw source")
            payload_hashes.append(artifact.payload_hash)
            rows = artifact.provider_payload.get("rows") if isinstance(artifact.provider_payload, Mapping) else None
            if not isinstance(rows, list):
                raise HistoricalStatusAuthorityError("provider rows are missing")
            by_kind[kind].extend(rows)
    exact_raw = require_exact_hash_inventory(
        name="raw payload", actual=tuple(payload_hashes),
        expected=tuple(manifest["raw_payload_hashes"]),
    )

    receipt_hashes = []
    for path in sorted(path for path in staging.rglob("*.json") if "receipts" in path.parts):
        receipt = raw_store.read_receipt(path)
        receipt_hashes.append(receipt.receipt_hash)
    exact_receipts = require_exact_hash_inventory(
        name="receipt", actual=tuple(receipt_hashes), expected=tuple(manifest["receipt_hashes"])
    )

    lifecycle_by_identity: dict[str, Mapping[str, Any]] = {}
    for root in (
        repository / "data/phase_1b1/raw/datahubco_tushare_proxy/security_master",
        repository / "data/phase_1b1_2026_extension/raw/datahubco_tushare_proxy/security_master",
    ):
        for path in sorted(root.rglob("*.json")):
            artifact = RawArtifactStore(root).read_payload(path)
            for row in artifact.provider_payload["rows"]:
                identity = str(row.get("ts_code", ""))
                if not identity.endswith((".SH", ".SZ")):
                    continue
                canonical = {
                    "ts_code": identity,
                    "list_date": row.get("list_date"),
                    "delist_date": row.get("delist_date") or None,
                }
                previous = lifecycle_by_identity.get(identity)
                if previous is not None and previous != canonical:
                    raise HistoricalStatusAuthorityError("conflicting lifecycle identity")
                lifecycle_by_identity[identity] = canonical
    target_path = next((repository / "data/phase_1b_exit_remediation/governance").glob(
        "complete-security-master-fact-bundle-*.json"
    ))
    target = json.loads(target_path.read_text(encoding="utf-8"))["ordered_security_identities"]
    if set(target) - set(lifecycle_by_identity):
        raise HistoricalStatusAuthorityError("missing lifecycle identity")
    lifecycle_rows = tuple(lifecycle_by_identity[item] for item in target)
    names = _canonical_provider_rows(by_kind["risk_warning_history"])
    risk_rows = tuple(row for row in names if re.match(
        r"^(?:S\*?ST|\*?ST)", str(row.get("name", "")), re.I
    ))
    suspensions = _canonical_provider_rows(
        row for row in by_kind["suspension_history"]
        if "20100104" <= str(row.get("trade_date", "")) <= "20260910"
    )
    hashes = {
        "lifecycle_hash": content_hash(tuple(
            (row["ts_code"], row.get("list_date"), row.get("delist_date") or None)
            for row in lifecycle_rows
        )),
        "risk_warning_hash": content_hash(risk_rows),
        "suspension_hash": content_hash(suspensions),
    }
    for name, digest in hashes.items():
        if panel[name] != digest:
            raise HistoricalStatusAuthorityError(f"{name} mismatch")
    return FrozenStatusInputReconstructionV1(
        raw_payload_hashes=exact_raw, receipt_hashes=exact_receipts,
        lifecycle_rows=lifecycle_rows, namechange_rows=names,
        suspension_rows=suspensions, **hashes,
    )


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
