"""Bounded, offline real-month integration for Checkpoint 18 (not a pilot)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.anchor_enumerator import AnchorDispositionKind
from v5_2.labels.dataset_contracts import CoverageAccountingV1, LabelRowV1
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.historical_five_domain_producer import (
    HistoricalFiveDomainProducerV1, ScopedAnchorExclusionV1,
)
from v5_2.labels.materializer import YearMonthV1, materialize_month


_VERSION = "phase2b-v1"
_ID = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ScopedMonthExclusionLedgerV1:
    month: str
    rows: tuple[ScopedAnchorExclusionV1, ...]
    affected_securities: int
    reason_counts: tuple[tuple[str, int], ...]
    ledger_id: str

    @classmethod
    def create(cls, month: str, rows) -> "ScopedMonthExclusionLedgerV1":
        ordered = tuple(sorted(rows, key=lambda item: (
            item.anchor_session, item.security_identity, item.domain,
            item.reason, item.evidence_ids)))
        keys = tuple((item.security_identity, item.anchor_session) for item in ordered)
        if (len(keys) != len(set(keys))
                or any(item.anchor_session.strftime("%Y-%m") != month
                       or not item.security_identity or not item.domain or not item.reason
                       or not item.evidence_ids
                       or any(not _ID.fullmatch(value) for value in item.evidence_ids)
                       for item in ordered)):
            raise ValueError("scoped exclusion ledger is invalid")
        reasons = tuple(sorted((reason, sum(item.reason == reason for item in ordered))
                               for reason in {item.reason for item in ordered}))
        body = {"month": month, "rows": ordered,
                "affected_securities": len({item.security_identity for item in ordered}),
                "reason_counts": reasons}
        return cls(**body, ledger_id=content_hash({
            "schema_version": cls.__name__, **body}))


def write_scoped_exclusions(root: Path, month: str,
                            rows) -> ScopedMonthExclusionLedgerV1:
    ledger = ScopedMonthExclusionLedgerV1.create(month, rows)
    path = root / "scoped_exclusions" / f"{ledger.ledger_id}.json"
    payload = canonical_json(ledger)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable scoped exclusion ledger collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return ledger


def read_scoped_exclusions_exact(path: Path, expected_id: str) -> ScopedMonthExclusionLedgerV1:
    if not _ID.fullmatch(expected_id) or path.stem != expected_id:
        raise ValueError("scoped exclusion ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        rows = tuple(ScopedAnchorExclusionV1(
            item["security_identity"], date.fromisoformat(item["anchor_session"]),
            item["domain"], item["reason"], tuple(item["evidence_ids"]))
            for item in values["rows"])
        ledger = ScopedMonthExclusionLedgerV1.create(values["month"], rows)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("scoped exclusion ledger unavailable or malformed") from error
    if (ledger.ledger_id != expected_id or canonical_json(ledger) != raw):
        raise ValueError("scoped exclusion ledger identity mismatch")
    return ledger


@dataclass(frozen=True, slots=True)
class HistoricalSourceMonthIntegrationV1:
    month: str
    effective_anchors: int
    excluded_before_label: int
    scoped_excluded_anchors: int
    scoped_excluded_securities: int
    scoped_reason_counts: tuple[tuple[str, int], ...]
    materialized_rows: int
    partition_id: str
    coverage_hash: str
    scoped_exclusion_hash: str
    integration_id: str


def integrate_real_month(source_root: Path, output_root: Path,
                         month: str) -> HistoricalSourceMonthIntegrationV1:
    """Rebuild a month only from pinned Phase 1 sources; preserve local defects."""
    year_month = YearMonthV1.create(*map(int, month.split("-")))
    if year_month.key != month:
        raise ValueError("noncanonical month")
    producer = HistoricalFiveDomainProducerV1.load_exact(source_root)
    sessions = tuple(sorted(set(producer.calendar.sse_sessions) |
                            set(producer.calendar.szse_sessions)))
    anchors = tuple(day for day in sessions if day.strftime("%Y-%m") == month)
    if not anchors:
        raise ValueError("month absent from approved calendar")
    dispositions = []
    scoped = []
    rows = []
    engine = ReferenceLabelEngine()
    for session in anchors:
        candidates, master_quarantines = producer.candidate_identities(session)
        scoped.extend(ScopedAnchorExclusionV1(identity, session,
            "security_master", "MASTER_IDENTITY_QUARANTINED",
            (producer.master.authority["authority_id"],))
            for identity in master_quarantines)
        for _, provider_identity in candidates:
            produced = producer.produce_anchor(provider_identity, session)
            if isinstance(produced, ScopedAnchorExclusionV1):
                scoped.append(produced)
                continue
            if not isinstance(produced, tuple):
                if produced.disposition is not AnchorDispositionKind.EXCLUDED_BEFORE_LABEL:
                    raise ValueError("unexpected pre-label anchor disposition")
                dispositions.append(produced)
                continue
            anchor, lineage, window = produced
            bundle = producer.assemble(anchor, lineage, window)
            result = engine.evaluate(bundle)
            dispositions.append(anchor)
            rows.append(LabelRowV1.create(result=result, bundle=bundle,
                                         materialization_version=_VERSION))
    rows.sort(key=lambda item: (item.anchor_session, item.canonical_security_identity))
    if len(scoped) != len({(item.security_identity, item.anchor_session) for item in scoped}):
        raise ValueError("duplicate scoped anchor")
    accounting = CoverageAccountingV1.from_dispositions(dispositions, rows)
    lineage_ids = (
        producer.calendar.approval_id,
        producer.master.approval["approval_id"],
        producer.bars.reader.derived_approval_id,
        producer.status_pins.approval_id,
        producer.actions.approval_id,
    )
    materialized = materialize_month(output_root, year_month, lineage_ids,
                                     _VERSION, rows=tuple(rows))
    scoped_ledger = write_scoped_exclusions(output_root, month, scoped)
    body = {
        "month": month,
        "effective_anchors": accounting.effective_anchors + len(scoped),
        "excluded_before_label": accounting.excluded_before_label,
        "scoped_excluded_anchors": len(scoped),
        "scoped_excluded_securities": scoped_ledger.affected_securities,
        "scoped_reason_counts": scoped_ledger.reason_counts,
        "materialized_rows": len(rows),
        "partition_id": materialized.partition.partition_id,
        "coverage_hash": accounting.content_hash,
        "scoped_exclusion_hash": scoped_ledger.ledger_id,
    }
    return HistoricalSourceMonthIntegrationV1(**body,
        integration_id=content_hash({"schema_version": "HistoricalSourceMonthIntegrationV1",
                                     **body}))
