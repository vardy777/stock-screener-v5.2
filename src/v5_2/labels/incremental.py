from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
import re

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import CORE_LABELS, LabelState
from v5_2.labels.dataset_contracts import (
    LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1,
)
from v5_2.labels.materializer import YearMonthV1, materialize_month
from v5_2.labels.partition_store import (
    read_manifest_exact, read_partition_exact, write_manifest,
)


_HASH = re.compile(r"^[0-9a-f]{64}$")


def _digest(schema: str, body: dict[str, object]) -> str:
    return content_hash({"schema_version": schema, **body})


class IncrementalWorkReason(StrEnum):
    NEW_ANCHOR = "NEW_ANCHOR"
    MATURED_PENDING = "MATURED_PENDING"
    GOVERNANCE_CHANGE = "GOVERNANCE_CHANGE"


@dataclass(frozen=True, slots=True)
class GovernanceChangeV1:
    change_kind: str
    artifact_id: str
    affected_keys: tuple[tuple[str, date], ...]
    content_hash: str

    @classmethod
    def create(
        cls,
        change_kind: str,
        artifact_id: str,
        affected_keys: tuple[tuple[str, date], ...],
    ) -> "GovernanceChangeV1":
        if change_kind not in {"REVOCATION", "SUPERSESSION"}:
            raise ValueError("unsupported governance change")
        if not _HASH.fullmatch(artifact_id):
            raise ValueError("governance artifact ID invalid")
        if not affected_keys or len(affected_keys) != len(set(affected_keys)):
            raise ValueError("unique affected governance keys required")
        ordered = tuple(sorted(affected_keys, key=lambda item: (item[1], item[0])))
        body = {
            "change_kind": change_kind,
            "artifact_id": artifact_id,
            "affected_keys": tuple((identity, session.isoformat()) for identity, session in ordered),
        }
        return cls(change_kind, artifact_id, ordered, _digest(cls.__name__, body))

    def verify(self) -> bool:
        body = {
            "change_kind": self.change_kind,
            "artifact_id": self.artifact_id,
            "affected_keys": tuple(
                (identity, session.isoformat()) for identity, session in self.affected_keys
            ),
        }
        return (
            self.change_kind in {"REVOCATION", "SUPERSESSION"}
            and bool(_HASH.fullmatch(self.artifact_id))
            and bool(self.affected_keys)
            and len(self.affected_keys) == len(set(self.affected_keys))
            and self.affected_keys
            == tuple(sorted(self.affected_keys, key=lambda item: (item[1], item[0])))
            and self.content_hash == _digest(type(self).__name__, body)
        )


@dataclass(frozen=True, slots=True)
class IncrementalWorkItemV1:
    canonical_security_identity: str
    anchor_session: date
    reason: IncrementalWorkReason
    label_names: tuple[str, ...]
    governance_artifact_ids: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(
        cls,
        identity: str,
        anchor_session: date,
        reason: IncrementalWorkReason,
        label_names: tuple[str, ...],
        governance_artifact_ids: tuple[str, ...] = (),
    ) -> "IncrementalWorkItemV1":
        if not identity or len(label_names) != len(set(label_names)):
            raise ValueError("invalid incremental work item")
        if any(name not in CORE_LABELS for name in label_names):
            raise ValueError("unknown label in incremental work item")
        if tuple(name for name in CORE_LABELS if name in label_names) != label_names:
            raise ValueError("canonical label ordering required")
        if reason is IncrementalWorkReason.MATURED_PENDING and not label_names:
            raise ValueError("maturation work requires labels")
        if reason is IncrementalWorkReason.GOVERNANCE_CHANGE and not governance_artifact_ids:
            raise ValueError("governance work requires artifact IDs")
        if any(not _HASH.fullmatch(value) for value in governance_artifact_ids):
            raise ValueError("governance artifact ID invalid")
        body = {
            "canonical_security_identity": identity,
            "anchor_session": anchor_session.isoformat(),
            "reason": reason.value,
            "label_names": label_names,
            "governance_artifact_ids": governance_artifact_ids,
        }
        return cls(identity, anchor_session, reason, label_names, governance_artifact_ids,
                   _digest(cls.__name__, body))


@dataclass(frozen=True, slots=True)
class IncrementalMaturationLedgerV1:
    predecessor_manifest_id: str
    latest_completed_session: date
    input_row_ids: tuple[str, ...]
    governance_change_ids: tuple[str, ...]
    items: tuple[IncrementalWorkItemV1, ...]
    workset_id: str


@dataclass(frozen=True, slots=True)
class IncrementalGenerationV1:
    manifest: LabelDatasetManifestV1
    manifest_path: Path
    replacement_partitions: tuple[LabelPartitionV1, ...]


def select_incremental_workset(
    predecessor: LabelDatasetManifestV1,
    latest_completed_session: date,
    governance_changes: tuple[GovernanceChangeV1, ...],
    *,
    rows: tuple[LabelRowV1, ...],
    new_anchor_keys: tuple[tuple[str, date], ...] = (),
) -> IncrementalMaturationLedgerV1:
    if not predecessor.verify():
        raise ValueError("predecessor manifest failed verification")
    if not all(row.verify() for row in rows):
        raise ValueError("row failed verification")
    row_keys = tuple((row.canonical_security_identity, row.anchor_session) for row in rows)
    if len(row_keys) != len(set(row_keys)):
        raise ValueError("duplicate predecessor row key")
    if not all(change.verify() for change in governance_changes):
        raise ValueError("governance change failed verification")
    if len(new_anchor_keys) != len(set(new_anchor_keys)):
        raise ValueError("duplicate new anchor key")

    items: list[IncrementalWorkItemV1] = []
    occupied: set[tuple[str, date]] = set()
    for row in rows:
        key = (row.canonical_security_identity, row.anchor_session)
        pending = tuple(
            value.label_name
            for value in row.values
            if value.state is LabelState.LABEL_PENDING
            and value.horizon_end_session is not None
            and value.horizon_end_session <= latest_completed_session
        )
        if pending:
            items.append(IncrementalWorkItemV1.create(
                *key, IncrementalWorkReason.MATURED_PENDING, pending,
            ))
            occupied.add(key)

    change_by_key: dict[tuple[str, date], list[str]] = {}
    for change in governance_changes:
        for key in change.affected_keys:
            change_by_key.setdefault(key, []).append(change.artifact_id)
    for key, artifact_ids in change_by_key.items():
        if key in occupied:
            raise ValueError("duplicate incremental work key")
        items.append(IncrementalWorkItemV1.create(
            *key,
            IncrementalWorkReason.GOVERNANCE_CHANGE,
            (),
            tuple(sorted(set(artifact_ids))),
        ))
        occupied.add(key)

    for key in new_anchor_keys:
        if key in occupied:
            raise ValueError("duplicate incremental work key")
        items.append(IncrementalWorkItemV1.create(
            *key, IncrementalWorkReason.NEW_ANCHOR, CORE_LABELS,
        ))
        occupied.add(key)

    ordered_items = tuple(sorted(
        items,
        key=lambda item: (item.anchor_session, item.canonical_security_identity, item.reason.value),
    ))
    input_row_ids = tuple(sorted(row.row_id for row in rows))
    change_ids = tuple(sorted(change.content_hash for change in governance_changes))
    body = {
        "predecessor_manifest_id": predecessor.manifest_id,
        "latest_completed_session": latest_completed_session.isoformat(),
        "input_row_ids": input_row_ids,
        "governance_change_ids": change_ids,
        "item_ids": tuple(item.content_hash for item in ordered_items),
    }
    return IncrementalMaturationLedgerV1(
        predecessor.manifest_id,
        latest_completed_session,
        input_row_ids,
        change_ids,
        ordered_items,
        _digest(IncrementalMaturationLedgerV1.__name__, body),
    )


def materialize_incremental_generation(
    root: Path,
    predecessor: LabelDatasetManifestV1,
    workset: IncrementalMaturationLedgerV1,
    *,
    active_partitions: tuple[tuple[LabelPartitionV1, tuple[LabelRowV1, ...]], ...],
    replacement_rows: tuple[LabelRowV1, ...],
    materialization_version: str,
) -> IncrementalGenerationV1:
    """Create an immutable successor from complete affected anchor-months.

    Callers must supply every active predecessor partition with its exact rows.
    This function validates their on-disk identities before replacing any month.
    """
    if not predecessor.verify() or workset.predecessor_manifest_id != predecessor.manifest_id:
        raise ValueError("predecessor manifest mismatch")
    manifest_path = root / "manifests" / f"{predecessor.manifest_id}.json"
    if read_manifest_exact(manifest_path, predecessor.manifest_id) != predecessor:
        raise ValueError("predecessor manifest bytes mismatch")
    if not materialization_version:
        raise ValueError("materialization version required")

    partition_by_id: dict[str, tuple[LabelPartitionV1, tuple[LabelRowV1, ...]]] = {}
    month_to_partition: dict[str, LabelPartitionV1] = {}
    month_rows: dict[str, dict[tuple[str, date], LabelRowV1]] = {}
    for partition, rows in active_partitions:
        if partition.partition_id in partition_by_id:
            raise ValueError("duplicate active partition")
        if partition.partition_id not in predecessor.active_partition_ids:
            raise ValueError("unrelated active partition")
        if tuple(row.row_id for row in rows) != partition.row_ids or not all(row.verify() for row in rows):
            raise ValueError("active partition rows mismatch")
        path = root / "labels" / "historical" / partition.partition_key / f"{partition.partition_id}.jsonl"
        if read_partition_exact(path, partition.partition_id) != partition:
            raise ValueError("canonical partition mismatch")
        if partition.partition_key in month_to_partition:
            raise ValueError("multiple active generations for anchor month")
        month_to_partition[partition.partition_key] = partition
        month_rows[partition.partition_key] = {
            (row.canonical_security_identity, row.anchor_session): row for row in rows
        }
        partition_by_id[partition.partition_id] = (partition, rows)
    if set(partition_by_id) != set(predecessor.active_partition_ids):
        raise ValueError("complete predecessor active partition set required")

    work_keys = {
        (item.canonical_security_identity, item.anchor_session) for item in workset.items
    }
    replacement_by_key = {
        (row.canonical_security_identity, row.anchor_session): row for row in replacement_rows
    }
    if (
        len(replacement_by_key) != len(replacement_rows)
        or set(replacement_by_key) != work_keys
        or not all(row.verify() for row in replacement_rows)
    ):
        raise ValueError("replacement rows must exactly match workset")

    affected_months = tuple(sorted({session.strftime("%Y-%m") for _, session in work_keys}))
    replacements: list[LabelPartitionV1] = []
    supersession: list[tuple[str, str]] = []
    for month_key in affected_months:
        rows_by_key = dict(month_rows.get(month_key, {}))
        for key, row in replacement_by_key.items():
            if row.anchor_session.strftime("%Y-%m") == month_key:
                rows_by_key[key] = row
        ordered_rows = tuple(sorted(
            rows_by_key.values(),
            key=lambda row: (row.anchor_session, row.canonical_security_identity),
        ))
        year, month = (int(value) for value in month_key.split("-"))
        materialized = materialize_month(
            root,
            YearMonthV1.create(year, month),
            predecessor.lineage_ids,
            materialization_version,
            rows=ordered_rows,
        )
        replacements.append(materialized.partition)
        old = month_to_partition.get(month_key)
        if old is not None:
            supersession.append((old.partition_id, materialized.partition.partition_id))

    replaced_months = set(affected_months)
    unchanged = [
        partition for partition, _ in active_partitions
        if partition.partition_key not in replaced_months
    ]
    active = tuple(sorted(
        (*unchanged, *replacements), key=lambda partition: partition.partition_key,
    ))
    successor = LabelDatasetManifestV1.create(
        previous_manifest_id=predecessor.manifest_id,
        previous_manifest=predecessor,
        active_partitions=active,
        partition_supersession=tuple(sorted(supersession)),
        phase2a_acceptance_id=predecessor.phase2a_acceptance_id,
        lineage_ids=predecessor.lineage_ids,
    )
    successor_path = write_manifest(root, successor)
    return IncrementalGenerationV1(
        successor, successor_path, tuple(sorted(replacements, key=lambda item: item.partition_key)),
    )
