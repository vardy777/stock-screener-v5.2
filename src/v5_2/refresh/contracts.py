from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Mapping

from v5_2.data.identity import canonical_json, content_hash


DATASET_KINDS = (
    "trade_calendar", "security_master", "daily_bar", "daily_security_status",
    "corporate_action", "financial_disclosure",
)


class RefreshContractError(ValueError):
    """A refresh artifact is incomplete or unsafe."""


class FreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"


class RefreshStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NO_OP = "NO_OP"
    FAILED = "FAILED"


class DatasetReadiness(str, Enum):
    READY = "READY"
    SCOPED_READY = "SCOPED_READY"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True, slots=True)
class DatasetRefreshResultV1:
    dataset_kind: str
    readiness: DatasetReadiness
    approval_id: str | None
    manifest_id: str | None
    latest_approved_session: date | None
    availability_modes: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()
    affected_security_ids: tuple[str, ...] = ()
    changed: bool = False
    approval_valid: bool = True
    manifest_valid: bool = True
    coverage_valid: bool = True
    pit_valid: bool = True
    identity_valid: bool = True

    @classmethod
    def ready(cls, *, dataset_kind: str, approval_id: str, manifest_id: str,
              latest_approved_session: date, availability_modes: tuple[str, ...],
              changed: bool = False) -> DatasetRefreshResultV1:
        return cls(dataset_kind, DatasetReadiness.READY, approval_id, manifest_id,
                   latest_approved_session, tuple(sorted(set(availability_modes))), changed=changed)

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_kind": self.dataset_kind, "readiness": self.readiness.value,
            "approval_id": self.approval_id, "manifest_id": self.manifest_id,
            "latest_approved_session": self.latest_approved_session.isoformat() if self.latest_approved_session else None,
            "availability_modes": list(self.availability_modes),
            "reason_codes": list(self.reason_codes),
            "affected_security_ids": list(self.affected_security_ids), "changed": self.changed,
            "approval_valid": self.approval_valid, "manifest_valid": self.manifest_valid,
            "coverage_valid": self.coverage_valid, "pit_valid": self.pit_valid,
            "identity_valid": self.identity_valid,
        }


@dataclass(frozen=True, slots=True)
class ResearchDataSnapshotV1:
    snapshot_id: str
    target_session: date
    created_at: datetime
    latest_approved_session: date
    manifest_ids: Mapping[str, str]
    availability_mode_summary: Mapping[str, tuple[str, ...]]
    dataset_readiness: Mapping[str, DatasetRefreshResultV1]
    freshness_status: FreshnessStatus
    research_ready: bool
    previous_successful_snapshot_id: str | None
    content_hash: str

    @classmethod
    def create(cls, *, target_session: date, created_at: datetime,
               latest_approved_session: date, manifest_ids: Mapping[str, str],
               availability_mode_summary: Mapping[str, tuple[str, ...]],
               dataset_readiness: Mapping[str, DatasetRefreshResultV1],
               freshness_status: FreshnessStatus, research_ready: bool,
               previous_successful_snapshot_id: str | None) -> ResearchDataSnapshotV1:
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise RefreshContractError("created_at must be timezone-aware")
        if set(manifest_ids) != set(DATASET_KINDS) or not all(manifest_ids.values()):
            raise RefreshContractError("all six manifest references are required")
        if research_ready and freshness_status is not FreshnessStatus.CURRENT:
            raise RefreshContractError("ready snapshot must be CURRENT")
        body = {
            "schema_version": "ResearchDataSnapshotV1", "target_session": target_session,
            "created_at": created_at, "latest_approved_session": latest_approved_session,
            "manifest_ids": dict(manifest_ids),
            "availability_mode_summary": {key: tuple(value) for key, value in availability_mode_summary.items()},
            "dataset_readiness": {key: value.as_dict() for key, value in dataset_readiness.items()},
            "freshness_status": freshness_status, "research_ready": research_ready,
            "previous_successful_snapshot_id": previous_successful_snapshot_id,
        }
        digest = content_hash(body)
        return cls(digest, target_session, created_at, latest_approved_session,
                   dict(manifest_ids), {key: tuple(value) for key, value in availability_mode_summary.items()},
                   dict(dataset_readiness), freshness_status, research_ready,
                   previous_successful_snapshot_id, digest)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "ResearchDataSnapshotV1", "snapshot_id": self.snapshot_id,
            "target_session": self.target_session.isoformat(), "created_at": self.created_at.isoformat(),
            "latest_approved_session": self.latest_approved_session.isoformat(),
            "manifest_ids": dict(self.manifest_ids),
            "availability_mode_summary": {key: list(value) for key, value in self.availability_mode_summary.items()},
            "dataset_readiness": {key: value.as_dict() for key, value in self.dataset_readiness.items()},
            "freshness_status": self.freshness_status.value, "research_ready": self.research_ready,
            "previous_successful_snapshot_id": self.previous_successful_snapshot_id,
            "content_hash": self.content_hash,
        }


class SnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def publish_ready(self, snapshot: ResearchDataSnapshotV1) -> ResearchDataSnapshotV1:
        if not snapshot.research_ready or snapshot.freshness_status is not FreshnessStatus.CURRENT:
            raise RefreshContractError("only a ready snapshot may be published")
        path = self.root / "snapshots" / f"{snapshot.snapshot_id}.json"
        content = canonical_json(snapshot.as_dict())
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != content:
            raise RefreshContractError("snapshot identity collision")
        if not path.exists():
            path.write_bytes(content)
        pointer = self.root / "latest-successful-snapshot-id.txt"
        temporary = pointer.with_suffix(".tmp")
        temporary.write_text(snapshot.snapshot_id, encoding="ascii")
        os.replace(temporary, pointer)
        return snapshot

    def latest_successful(self) -> ResearchDataSnapshotV1 | None:
        pointer = self.root / "latest-successful-snapshot-id.txt"
        if not pointer.is_file():
            return None
        identifier = pointer.read_text(encoding="ascii").strip()
        path = self.root / "snapshots" / f"{identifier}.json"
        if not path.is_file():
            raise RefreshContractError("latest snapshot pointer is dangling")
        value = json.loads(path.read_text(encoding="utf-8"))
        results = {
            key: DatasetRefreshResultV1(
                dataset_kind=item["dataset_kind"], readiness=DatasetReadiness(item["readiness"]),
                approval_id=item["approval_id"], manifest_id=item["manifest_id"],
                latest_approved_session=date.fromisoformat(item["latest_approved_session"]) if item["latest_approved_session"] else None,
                availability_modes=tuple(item["availability_modes"]), reason_codes=tuple(item["reason_codes"]),
                affected_security_ids=tuple(item["affected_security_ids"]), changed=bool(item["changed"]),
                approval_valid=bool(item.get("approval_valid", True)),
                manifest_valid=bool(item.get("manifest_valid", True)),
                coverage_valid=bool(item.get("coverage_valid", True)),
                pit_valid=bool(item.get("pit_valid", True)),
                identity_valid=bool(item.get("identity_valid", True)),
            ) for key, item in value["dataset_readiness"].items()
        }
        snapshot = ResearchDataSnapshotV1.create(
            target_session=date.fromisoformat(value["target_session"]),
            created_at=datetime.fromisoformat(value["created_at"]),
            latest_approved_session=date.fromisoformat(value["latest_approved_session"]),
            manifest_ids=value["manifest_ids"],
            availability_mode_summary={key: tuple(item) for key, item in value["availability_mode_summary"].items()},
            dataset_readiness=results, freshness_status=FreshnessStatus(value["freshness_status"]),
            research_ready=bool(value["research_ready"]),
            previous_successful_snapshot_id=value["previous_successful_snapshot_id"],
        )
        if snapshot.snapshot_id != identifier or value.get("content_hash") != identifier:
            raise RefreshContractError("snapshot content hash mismatch")
        return snapshot


@dataclass(frozen=True, slots=True)
class RefreshResultV1:
    today: date
    is_trading_day: bool | None
    target_session: date | None
    latest_completed_session: date | None
    latest_approved_session_before_refresh: date | None
    missing_sessions: tuple[date, ...]
    dataset_results: Mapping[str, DatasetRefreshResultV1]
    refresh_status: RefreshStatus
    latest_approved_session: date | None
    freshness_status: FreshnessStatus
    research_ready: bool
    snapshot_id: str | None
    previous_successful_snapshot_id: str | None
    failure_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        day = lambda value: value.isoformat() if value else None
        return {
            "today": day(self.today), "is_trading_day": self.is_trading_day,
            "target_session": day(self.target_session), "latest_completed_session": day(self.latest_completed_session),
            "latest_approved_session_before_refresh": day(self.latest_approved_session_before_refresh),
            "missing_sessions": [day(item) for item in self.missing_sessions],
            "dataset_results": {key: value.as_dict() for key, value in self.dataset_results.items()},
            "refresh_status": self.refresh_status.value, "latest_approved_session": day(self.latest_approved_session),
            "freshness_status": self.freshness_status.value, "research_ready": self.research_ready,
            "snapshot_id": self.snapshot_id, "previous_successful_snapshot_id": self.previous_successful_snapshot_id,
            "failure_reasons": list(self.failure_reasons),
        }
