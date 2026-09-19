from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
import re

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import CORE_LABELS, LabelInputBundleV1, LabelResultV1, LabelValueV1


_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _normalize(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _normalize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, tuple):
        return tuple(_normalize(item) for item in value)
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    return value


def _digest(schema: str, body: dict[str, object]) -> str:
    return content_hash({"schema_version": schema, **_normalize(body)})


@dataclass(frozen=True, slots=True)
class LabelRowV1:
    canonical_security_identity: str
    anchor_session: date
    label_contract_version: str
    materialization_version: str
    provenance_path: str
    anchor_boundary_hash: str
    anchor_reference_price_hash: str | None
    input_bundle_hash: str
    calculation_result_hash: str
    domain_lineage_hashes: tuple[str, ...]
    anchor_snapshot_id: str | None
    outcome_snapshot_id: str | None
    values: tuple[LabelValueV1, ...]
    barrier_evidence: tuple[object, ...]
    row_id: str

    @classmethod
    def create(cls, *, result: LabelResultV1, bundle: LabelInputBundleV1, materialization_version: str) -> LabelRowV1:
        if not materialization_version:
            raise ValueError("materialization version required")
        if not result.verify() or not bundle.verify():
            raise ValueError("result and bundle must verify")
        if result.bundle_hash != bundle.content_hash:
            raise ValueError("result bundle hash mismatch")
        if result.canonical_security_identity != bundle.canonical_security_identity or result.anchor_session != bundle.anchor_session:
            raise ValueError("result anchor mismatch")
        if tuple(value.label_name for value in result.values) != CORE_LABELS:
            raise ValueError("frozen label ordering required")
        body = {
            "canonical_security_identity": result.canonical_security_identity,
            "anchor_session": result.anchor_session,
            "label_contract_version": result.values[0].contract_version,
            "materialization_version": materialization_version,
            "provenance_path": bundle.provenance_path,
            "anchor_boundary_hash": bundle.anchor_boundary.content_hash,
            "anchor_reference_price_hash": None if bundle.reference_price is None else bundle.reference_price.content_hash,
            "input_bundle_hash": bundle.content_hash,
            "calculation_result_hash": result.content_hash,
            "domain_lineage_hashes": tuple(lineage.content_hash for lineage in bundle.domain_lineage),
            "anchor_snapshot_id": bundle.anchor_snapshot_id,
            "outcome_snapshot_id": bundle.outcome_snapshot_id,
            "values": result.values,
            "barrier_evidence": result.barrier_evidence,
        }
        return cls(**body, row_id=_digest(cls.__name__, body))

    def verify(self) -> bool:
        if tuple(value.label_name for value in self.values) != CORE_LABELS or not all(value.verify() for value in self.values):
            return False
        body = {name: getattr(self, name) for name in (
            "canonical_security_identity", "anchor_session", "label_contract_version", "materialization_version",
            "provenance_path", "anchor_boundary_hash", "anchor_reference_price_hash", "input_bundle_hash",
            "calculation_result_hash", "domain_lineage_hashes", "anchor_snapshot_id", "outcome_snapshot_id",
            "values", "barrier_evidence",
        )}
        return self.row_id == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class LabelPartitionV1:
    partition_key: str
    generation_id: str
    row_ids: tuple[str, ...]
    row_count: int
    partition_id: str

    @classmethod
    def create(cls, *, partition_key: str, generation_id: str, rows: tuple[LabelRowV1, ...]) -> LabelPartitionV1:
        if not _MONTH.fullmatch(partition_key):
            raise ValueError("invalid anchor-month partition key")
        if not generation_id:
            raise ValueError("generation ID required")
        if not rows or not all(row.verify() for row in rows):
            raise ValueError("verified rows required")
        row_ids = tuple(row.row_id for row in rows)
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("duplicate row identity")
        keys = tuple((row.anchor_session, row.canonical_security_identity) for row in rows)
        if keys != tuple(sorted(keys)):
            raise ValueError("canonical row ordering required")
        body = {"partition_key": partition_key, "generation_id": generation_id, "row_ids": row_ids, "row_count": len(rows)}
        return cls(**body, partition_id=_digest(cls.__name__, body))

    def verify(self) -> bool:
        body = {"partition_key": self.partition_key, "generation_id": self.generation_id, "row_ids": self.row_ids, "row_count": self.row_count}
        return bool(_MONTH.fullmatch(self.partition_key)) and self.row_count == len(self.row_ids) and self.partition_id == _digest(type(self).__name__, body)
