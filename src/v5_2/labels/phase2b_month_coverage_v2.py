"""Independent source-pinned census of a materialized label month."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.anchor_enumerator import AnchorDispositionKind
from v5_2.labels.dataset_contracts import CoverageAccountingV1, LabelRowV1
from v5_2.labels.historical_five_domain_producer import (
    HistoricalFiveDomainProducerV1, ScopedAnchorExclusionV1,
)
from v5_2.labels.historical_month_integration import (
    ScopedMonthExclusionLedgerV1, read_scoped_exclusions_exact,
)
from v5_2.labels.partition_store import read_partition_rows_exact


_ID = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class SourcePinnedMonthCoverageEvidenceV2:
    month: str
    partition_id: str
    calendar_approval_id: str
    master_approval_id: str
    effective_anchors: int
    eligible_anchors: int
    excluded_before_label: int
    scoped_excluded_anchors: int
    materialized_rows: int
    coverage_hash: str
    scoped_ledger_id: str
    candidate_set_hash: str
    evidence_id: str

    def verify(self) -> bool:
        body = {key: getattr(self, key) for key in self.__dataclass_fields__
                if key != "evidence_id"}
        return (all(_ID.fullmatch(value) for value in (
            self.partition_id, self.calendar_approval_id, self.master_approval_id,
            self.coverage_hash, self.scoped_ledger_id, self.candidate_set_hash))
            and self.effective_anchors == (self.eligible_anchors
                                           + self.excluded_before_label
                                           + self.scoped_excluded_anchors)
            and self.materialized_rows == self.eligible_anchors
            and self.evidence_id == content_hash({"schema_version": type(self).__name__, **body}))


def derive_month_coverage_evidence(producer: HistoricalFiveDomainProducerV1,
                                   rows: tuple[LabelRowV1, ...],
                                   scoped_ledger: ScopedMonthExclusionLedgerV1,
                                   partition_id: str) -> SourcePinnedMonthCoverageEvidenceV2:
    """Enumerate expected keys from pinned Master/Calendar, not from output rows."""
    month = scoped_ledger.month
    if not _ID.fullmatch(partition_id):
        raise ValueError("invalid exact partition ID")
    sessions = tuple(sorted(set(producer.calendar.sse_sessions) |
                            set(producer.calendar.szse_sessions)))
    month_sessions = tuple(day for day in sessions if day.strftime("%Y-%m") == month)
    if not month_sessions:
        raise ValueError("approved calendar has no month sessions")
    candidates = []
    for fact in producer.master.facts:
        exchange = "SSE" if fact.provider_identity.endswith(".SH") else "SZSE"
        for interval in fact.intervals:
            for day in month_sessions:
                if day in producer.calendar.sessions(exchange) and interval.effective_from <= day and (
                        interval.effective_to is None or day <= interval.effective_to):
                    candidates.append((interval.identity, fact.provider_identity, day))
    candidate_keys = tuple((provider, day) for _, provider, day in candidates)
    if len(candidate_keys) != len(set(candidate_keys)):
        raise ValueError("Master candidate identity overlap")
    scoped = []
    for item in producer.master.quarantines:
        start = date.fromisoformat(item.affected_from) if item.affected_from else None
        end = date.fromisoformat(item.affected_to) if item.affected_to else None
        for day in month_sessions:
            if start is not None and start <= day and (end is None or day <= end):
                scoped.append(ScopedAnchorExclusionV1(item.security_identity, day,
                    "security_master", "MASTER_IDENTITY_QUARANTINED",
                    (producer.master.authority["authority_id"],)))
    dispositions = []
    for _, provider, day in sorted(candidates, key=lambda item: (item[2], item[1], item[0])):
        produced = producer.produce_anchor(provider, day)
        if isinstance(produced, ScopedAnchorExclusionV1):
            scoped.append(produced)
        elif isinstance(produced, tuple):
            anchor, _, _ = produced
            if anchor.disposition is not AnchorDispositionKind.ELIGIBLE:
                raise ValueError("constructed window is not eligible")
            dispositions.append(anchor)
        elif produced.disposition is AnchorDispositionKind.EXCLUDED_BEFORE_LABEL:
            dispositions.append(produced)
        else:
            raise ValueError("unexpected anchor disposition")
    computed_scoped = ScopedMonthExclusionLedgerV1.create(month, scoped)
    if computed_scoped != scoped_ledger:
        raise ValueError("scoped exclusion census differs from exact ledger")
    accounting = CoverageAccountingV1.from_dispositions(dispositions, rows)
    body = {
        "month": month,
        "partition_id": partition_id,
        "calendar_approval_id": producer.calendar.approval_id,
        "master_approval_id": producer.master.approval["approval_id"],
        "effective_anchors": accounting.effective_anchors + len(scoped),
        "eligible_anchors": accounting.eligible_anchors,
        "excluded_before_label": accounting.excluded_before_label,
        "scoped_excluded_anchors": len(scoped),
        "materialized_rows": accounting.materialized_rows,
        "coverage_hash": accounting.content_hash,
        "scoped_ledger_id": scoped_ledger.ledger_id,
        "candidate_set_hash": content_hash({"schema_version": "MasterCalendarCandidateSetV2",
                                            "month": month, "candidates": tuple(sorted(candidates))}),
    }
    evidence = SourcePinnedMonthCoverageEvidenceV2(**body,
        evidence_id=content_hash({"schema_version": "SourcePinnedMonthCoverageEvidenceV2", **body}))
    if not evidence.verify():
        raise ValueError("independent month coverage evidence invalid")
    return evidence


def derive_month_coverage_evidence_exact(source_root: Path, partition_path: Path,
                                         expected_partition_id: str, scoped_path: Path,
                                         expected_scoped_id: str) -> SourcePinnedMonthCoverageEvidenceV2:
    producer = HistoricalFiveDomainProducerV1.load_exact(source_root)
    rows = read_partition_rows_exact(partition_path, expected_partition_id)
    scoped = read_scoped_exclusions_exact(scoped_path, expected_scoped_id)
    if any(row.anchor_session.strftime("%Y-%m") != scoped.month for row in rows):
        raise ValueError("partition rows outside scoped month")
    return derive_month_coverage_evidence(producer, rows, scoped, expected_partition_id)


def write_month_coverage_evidence(root: Path,
                                  evidence: SourcePinnedMonthCoverageEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified month coverage evidence required")
    path = root / "gate_evidence" / f"month-coverage-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable month coverage evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_month_coverage_evidence_exact(path: Path, expected_id: str
                                       ) -> SourcePinnedMonthCoverageEvidenceV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"month-coverage-{expected_id}.json"):
        raise ValueError("month coverage evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        evidence = SourcePinnedMonthCoverageEvidenceV2(**json.loads(raw))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("month coverage evidence unavailable or malformed") from error
    if (evidence.evidence_id != expected_id or not evidence.verify()
            or canonical_json(evidence) != raw):
        raise ValueError("month coverage evidence identity mismatch")
    return evidence
