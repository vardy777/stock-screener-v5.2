from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import re

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import CORE_LABELS, LabelState
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelRowV1


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
