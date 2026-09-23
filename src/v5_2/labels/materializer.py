from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
import re
from typing import Any

from v5_2.data.historical_status_authority import HistoricalStatusResolverV1
from v5_2.data.identity import content_hash
from v5_2.labels.anchor_enumerator import (
    AnchorDispositionKind,
    AnchorDispositionV1,
    HistoricalAnchorLineageV1,
)
from v5_2.labels.contracts import (
    DomainLineageV1,
    LabelInputBundleV1,
    LabelReferencePrice,
    ProvenancePath,
)
from v5_2.labels.dataset_contracts import LabelRowV1
from v5_2.labels.engine import ReferenceLabelEngine


_ID = re.compile(r"^[0-9a-f]{64}$")
_ZONE = timezone(timedelta(hours=8), "Asia/Shanghai")
_NON_STATUS_DOMAINS = (
    "trade_calendar", "security_master", "daily_bar", "corporate_action",
)


def _normalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _normalize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return tuple(_normalize(item) for item in value)
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    return value


def _digest(schema: str, body: dict[str, Any]) -> str:
    return content_hash({"schema_version": schema, **_normalize(body)})


@dataclass(frozen=True, slots=True)
class HistoricalStatusLineagePinsV1:
    authority_id: str
    approval_id: str
    manifest_id: str
    composition_id: str
    coverage_ledger_id: str
    replay_evidence_id: str
    parent_panel_id: str
    parent_manifest_id: str
    parent_approval_id: str
    content_hash: str

    @classmethod
    def create(cls, **values: str) -> "HistoricalStatusLineagePinsV1":
        if not all(_ID.fullmatch(value) for value in values.values()):
            raise ValueError("status lineage requires exact immutable IDs")
        return cls(**values, content_hash=_digest(cls.__name__, values))

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "content_hash"}
        return all(_ID.fullmatch(value) for value in body.values()) and (
            self.content_hash == _digest(type(self).__name__, body)
        )


@dataclass(frozen=True, slots=True)
class HistoricalResolvedStatusV1:
    session: date
    is_suspended: bool
    available_at: datetime
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceWindowV1:
    anchor_boundary: object
    anchor_bar: object | None
    future_bars: tuple[object, ...]
    non_status_lineage: tuple[DomainLineageV1, ...]
    corporate_actions: tuple[object, ...]
    action_coverage: object
    dated_identity_map: tuple[tuple[date, str, str], ...]
    delisting_session: date | None
    content_hash: str

    @classmethod
    def create(cls, **values: Any) -> "HistoricalEvidenceWindowV1":
        body = dict(values)
        result = cls(**body, content_hash=_digest(cls.__name__, body))
        if not result.verify():
            raise ValueError("historical evidence window invalid")
        return result

    def verify(self) -> bool:
        if tuple(item.domain for item in self.non_status_lineage) != _NON_STATUS_DOMAINS:
            return False
        if not all(item.verify() for item in self.non_status_lineage):
            return False
        if not getattr(self.anchor_boundary, "verify", lambda: False)():
            return False
        if self.anchor_bar is not None and not self.anchor_bar.verify():
            return False
        if not all(item.verify() for item in self.future_bars):
            return False
        if not all(getattr(item, "verify", lambda: False)() for item in self.corporate_actions):
            return False
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "content_hash"}
        return self.content_hash == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class ExcludedAnchorV1:
    canonical_security_identity: str
    anchor_session: date
    reason: str
    content_hash: str

    @classmethod
    def create(cls, anchor: AnchorDispositionV1) -> "ExcludedAnchorV1":
        if anchor.disposition is not AnchorDispositionKind.EXCLUDED_BEFORE_LABEL or not anchor.reason:
            raise ValueError("excluded anchor disposition required")
        body = {
            "canonical_security_identity": anchor.canonical_security_identity,
            "anchor_session": anchor.anchor_session,
            "reason": anchor.reason,
        }
        return cls(**body, content_hash=_digest(cls.__name__, body))


class HistoricalLabelEvidenceAssemblerV1:
    version = "historical-label-evidence-assembler-v1"

    def __init__(self, status_resolver: HistoricalStatusResolverV1,
                 status_pins: HistoricalStatusLineagePinsV1) -> None:
        if not status_pins.verify() or status_pins.authority_id != status_resolver.authority.authority_id:
            raise ValueError("status lineage mismatch")
        if status_pins.approval_id != status_resolver.derived_approval_id:
            raise ValueError("status lineage approval mismatch")
        if status_pins.manifest_id != status_resolver.derived_manifest_id:
            raise ValueError("status lineage manifest mismatch")
        if (
            status_pins.parent_panel_id != status_resolver.authority.parent_panel_id
            or status_pins.parent_manifest_id != status_resolver.authority.parent_manifest_id
            or status_pins.parent_approval_id != status_resolver.authority.parent_approval_id
        ):
            raise ValueError("status lineage parent mismatch")
        self.status_resolver = status_resolver
        self.status_pins = status_pins

    def assemble(
        self, anchor: AnchorDispositionV1, lineage: HistoricalAnchorLineageV1,
        window: HistoricalEvidenceWindowV1, *, latest_completed_session: date,
    ) -> LabelInputBundleV1:
        if anchor.disposition is not AnchorDispositionKind.ELIGIBLE:
            raise ValueError("eligible anchor required")
        if not lineage.verify():
            raise ValueError("historical anchor lineage invalid")
        if not window.verify():
            raise ValueError("historical evidence window invalid")
        if lineage.status_approval_id != self.status_pins.approval_id or lineage.status_manifest_id != self.status_pins.manifest_id:
            raise ValueError("historical anchor status lineage mismatch")
        if anchor.anchor_session != window.anchor_boundary.anchor_session:
            raise ValueError("anchor evidence mismatch")
        sessions = tuple(day for day in lineage.open_sessions if day > anchor.anchor_session)[:5]
        if len(sessions) != 5 or latest_completed_session not in (anchor.anchor_session, *sessions):
            raise ValueError("completed session is outside frozen horizon")
        completed = tuple(day for day in sessions if day <= latest_completed_session)
        derivations = tuple(self.status_resolver.resolve(
            anchor.canonical_security_identity, day,
            datetime.combine(day, time(16, 30), _ZONE),
        ) for day in completed)
        statuses = tuple(HistoricalResolvedStatusV1(
            session=item.session,
            is_suspended=item.full_day_suspended,
            available_at=item.available_at,
            evidence_ids=(item.derivation_id,),
        ) for item in derivations)
        component_ids = tuple(sorted({
            value
            for item in derivations
            for value in (
                item.lifecycle_component_id,
                *item.applicable_risk_component_ids,
                *item.applicable_suspension_component_ids,
            )
        }))
        evidence_ids = tuple(dict.fromkeys((
            self.status_pins.authority_id,
            self.status_pins.composition_id,
            self.status_pins.coverage_ledger_id,
            self.status_pins.replay_evidence_id,
            self.status_pins.parent_panel_id,
            self.status_pins.parent_manifest_id,
            self.status_pins.parent_approval_id,
            *component_ids,
        )))
        status_lineage = DomainLineageV1.create(
            domain="daily_security_status",
            approval_id=self.status_pins.approval_id,
            manifest_id=self.status_pins.manifest_id,
            fact_ids=tuple(item.derivation_id for item in derivations),
            evidence_ids=evidence_ids,
        )
        non_status = window.non_status_lineage
        domain_lineage = (*non_status[:3], status_lineage, non_status[3])
        future_bars = tuple(item for item in window.future_bars if item.session in completed)
        actions = tuple(item for item in window.corporate_actions
                        if (item.effective_date or item.ex_date) in completed)
        reference = None if window.anchor_bar is None else LabelReferencePrice.create(
            anchor.anchor_session, window.anchor_bar.close, window.anchor_bar.fact_id,
            window.anchor_bar.available_at,
        )
        return LabelInputBundleV1.create(
            canonical_security_identity=anchor.canonical_security_identity,
            anchor_session=anchor.anchor_session,
            anchor_boundary=window.anchor_boundary,
            reference_price=reference,
            provenance_path=ProvenancePath.HISTORICAL,
            domain_lineage=domain_lineage,
            anchor_snapshot_id=None,
            outcome_snapshot_id=None,
            approved_exchange_sessions=(anchor.anchor_session, *sessions),
            latest_completed_session=latest_completed_session,
            future_bars=future_bars,
            future_statuses=statuses,
            corporate_actions=actions,
            action_coverage=window.action_coverage,
            dated_identity_map=window.dated_identity_map,
            delisting_session=window.delisting_session,
        )


def materialize_anchor(
    root: Path,
    anchor: AnchorDispositionV1,
    lineage: HistoricalAnchorLineageV1,
    version: str,
    *,
    assembler: HistoricalLabelEvidenceAssemblerV1 | None = None,
    evidence_window: HistoricalEvidenceWindowV1 | None = None,
    latest_completed_session: date | None = None,
) -> LabelRowV1 | ExcludedAnchorV1:
    del root
    if anchor.disposition is AnchorDispositionKind.EXCLUDED_BEFORE_LABEL:
        return ExcludedAnchorV1.create(anchor)
    if assembler is None or evidence_window is None or latest_completed_session is None:
        raise ValueError("exact historical assembler inputs required")
    bundle = assembler.assemble(
        anchor, lineage, evidence_window,
        latest_completed_session=latest_completed_session,
    )
    result = ReferenceLabelEngine().evaluate(bundle)
    return LabelRowV1.create(result=result, bundle=bundle, materialization_version=version)
