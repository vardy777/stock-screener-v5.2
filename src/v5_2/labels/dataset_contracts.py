from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
import re

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import (
    CORE_LABELS, LabelInputBundleV1, LabelResultV1, LabelState, LabelValueV1,
)


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


@dataclass(frozen=True, slots=True)
class LabelDatasetManifestV1:
    previous_manifest_id: str | None
    active_partition_ids: tuple[str, ...]
    partition_supersession: tuple[tuple[str, str], ...]
    phase2a_acceptance_id: str
    lineage_ids: tuple[str, ...]
    manifest_id: str

    @classmethod
    def create(cls, *, previous_manifest_id: str | None, active_partitions: tuple[LabelPartitionV1, ...],
               partition_supersession: tuple[tuple[str, str], ...], phase2a_acceptance_id: str,
               lineage_ids: tuple[str, ...], previous_manifest: LabelDatasetManifestV1 | None = None) -> LabelDatasetManifestV1:
        if not active_partitions or not all(partition.verify() for partition in active_partitions):
            raise ValueError("verified active partitions required")
        active_ids = tuple(partition.partition_id for partition in active_partitions)
        if len(active_ids) != len(set(active_ids)):
            raise ValueError("duplicate active partition")
        if not re.fullmatch(r"[0-9a-f]{64}", phase2a_acceptance_id) or not lineage_ids or not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in lineage_ids):
            raise ValueError("immutable acceptance and lineage IDs required")
        if previous_manifest_id is not None and not re.fullmatch(r"[0-9a-f]{64}", previous_manifest_id):
            raise ValueError("previous manifest ID invalid")
        if previous_manifest is not None and (not previous_manifest.verify() or previous_manifest.manifest_id != previous_manifest_id):
            raise ValueError("previous manifest lineage invalid")
        old_ids = tuple(old for old, _ in partition_supersession)
        new_ids = tuple(new for _, new in partition_supersession)
        if len(old_ids) != len(set(old_ids)) or len(new_ids) != len(set(new_ids)):
            raise ValueError("duplicate supersession mapping")
        if partition_supersession and (previous_manifest_id is None or previous_manifest is None):
            raise ValueError("supersession requires previous manifest")
        if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in (*old_ids, *new_ids)) or any(new not in active_ids or old in active_ids for old, new in partition_supersession) or any(old not in previous_manifest.active_partition_ids for old in old_ids):
            raise ValueError("supersession mapping invalid")
        body = {"previous_manifest_id": previous_manifest_id, "active_partition_ids": active_ids,
                "partition_supersession": partition_supersession, "phase2a_acceptance_id": phase2a_acceptance_id,
                "lineage_ids": lineage_ids}
        return cls(**body, manifest_id=_digest(cls.__name__, body))

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in ("previous_manifest_id", "active_partition_ids", "partition_supersession", "phase2a_acceptance_id", "lineage_ids")}
        return self.manifest_id == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class CoverageAccountingV1:
    effective_anchors: int
    eligible_anchors: int
    excluded_before_label: int
    materialized_rows: int
    state_counts: dict[str, dict[str, int]]
    reason_counts: dict[str, int]
    exclusion_reason_counts: dict[str, int]
    disposition_set_hash: str
    row_semantic_set_hash: str
    content_hash: str

    @classmethod
    def from_dispositions(cls, dispositions, rows) -> "CoverageAccountingV1":
        dispositions = tuple(dispositions)
        rows = tuple(rows)
        if not all(row.verify() for row in rows):
            raise ValueError("verified materialized rows required")
        disposition_keys = tuple(
            (item.canonical_security_identity, item.anchor_session) for item in dispositions
        )
        row_keys = tuple((item.canonical_security_identity, item.anchor_session) for item in rows)
        if len(disposition_keys) != len(set(disposition_keys)) or len(row_keys) != len(set(row_keys)):
            raise ValueError("duplicate coverage key")
        eligible_keys = {
            (item.canonical_security_identity, item.anchor_session)
            for item in dispositions if item.disposition.value == "ELIGIBLE"
        }
        if set(row_keys) != eligible_keys:
            raise ValueError("eligible anchors and materialized rows differ")
        state_counts = {
            label: {state.value: 0 for state in LabelState} for label in CORE_LABELS
        }
        reason_counts: dict[str, int] = {}
        for row in rows:
            for value in row.values:
                state_counts[value.label_name][value.state.value] += 1
                if value.reason_code is not None:
                    reason_counts[value.reason_code.value] = reason_counts.get(value.reason_code.value, 0) + 1
        exclusion_counts: dict[str, int] = {}
        for item in dispositions:
            if item.disposition.value == "EXCLUDED_BEFORE_LABEL":
                if not item.reason:
                    raise ValueError("excluded anchor reason required")
                exclusion_counts[item.reason] = exclusion_counts.get(item.reason, 0) + 1
        disposition_rows = tuple(sorted((
            item.canonical_security_identity, item.anchor_session,
            item.disposition.value, item.reason,
        ) for item in dispositions))
        row_ids = tuple(row.row_id for row in sorted(
            rows, key=lambda item: (item.anchor_session, item.canonical_security_identity)
        ))
        body = {
            "effective_anchors": sum(bool(item.effective) for item in dispositions),
            "eligible_anchors": len(eligible_keys),
            "excluded_before_label": sum(
                item.disposition.value == "EXCLUDED_BEFORE_LABEL" for item in dispositions
            ),
            "materialized_rows": len(rows),
            "state_counts": state_counts,
            "reason_counts": dict(sorted(reason_counts.items())),
            "exclusion_reason_counts": dict(sorted(exclusion_counts.items())),
            "disposition_set_hash": _digest("CoverageDispositionSetV1", {"rows": disposition_rows}),
            "row_semantic_set_hash": _digest("CoverageRowSemanticSetV1", {"row_ids": row_ids}),
        }
        return cls(**body, content_hash=_digest(cls.__name__, body))

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "content_hash"}
        return self.content_hash == _digest(type(self).__name__, body)

    def verify_against(self, dispositions, rows) -> bool:
        if not self.verify():
            return False
        try:
            expected = type(self).from_dispositions(dispositions, rows)
        except (TypeError, ValueError):
            return False
        return self == expected
