"""Independent Phase 2B row evidence; never imports the production engine."""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.contracts import LabelInputBundleV1, LabelResultV1
from v5_2.labels.dataset_contracts import LabelRowV1
from v5_2.labels.independent_reference import calculate_independent_reference
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.partition_store import read_partition_rows_exact


@dataclass(frozen=True, slots=True)
class RowIndependentGateEvidenceV2:
    row_id: str
    bundle_id: str
    independent_reference_id: str
    state_match: bool
    reason_match: bool
    numeric_match: bool
    barrier_match: bool
    lineage_match: bool
    matched: bool
    evidence_id: str

    def verify(self) -> bool:
        body = {item.name: getattr(self, item.name) for item in fields(self)
                if item.name != "evidence_id"}
        return self.evidence_id == content_hash({
            "schema_version": type(self).__name__, **body})


def _row_barriers(row: LabelRowV1) -> tuple[tuple[str, str, str], ...]:
    names = ("hit_3pct_before_-2pct", "hit_5pct_before_-3pct")
    values = []
    for name, item in zip(names, row.barrier_evidence):
        ambiguous = getattr(item, "ambiguous_session", None)
        outcome = getattr(item, "outcome", None)
        decisive = getattr(item, "first_decisive_session", None)
        values.append((name, "AMBIGUOUS" if ambiguous else
                       (outcome.value if outcome else ""),
                       decisive.isoformat() if decisive else
                       (ambiguous.isoformat() if ambiguous else "")))
    return tuple(values)


def compare_row_independently(row: LabelRowV1,
                              bundle: LabelInputBundleV1) -> RowIndependentGateEvidenceV2:
    """Recompute expected semantics without calling production calculation."""
    if not row.verify() or not bundle.verify():
        raise ValueError("verified physical row and source bundle required")
    independent = calculate_independent_reference(1, bundle)
    if not independent.verify():
        raise ValueError("independent reference is invalid")
    actual = tuple((item.label_name, item.state.value, str(item.value),
                    item.reason_code.value if item.reason_code else "")
                   for item in row.values)
    expected = independent.result_summary
    state = tuple(item[1] for item in actual) == tuple(item[1] for item in expected)
    reason = tuple(item[3] for item in actual) == tuple(item[3] for item in expected)
    numeric = tuple(item[2] for item in actual) == tuple(item[2] for item in expected)
    expected_barriers = tuple((item.label_name,
        item.outcome or ("AMBIGUOUS" if item.ambiguous_session else ""),
        item.decisive_session.isoformat() if item.decisive_session else "")
        for item in independent.barriers)
    barriers = _row_barriers(row) == expected_barriers
    recreated_result = LabelResultV1.create(
        row.canonical_security_identity, row.anchor_session, row.values,
        bundle.content_hash, row.barrier_evidence)
    lineage = (
        row.canonical_security_identity == bundle.canonical_security_identity
        and row.anchor_session == bundle.anchor_session
        and row.input_bundle_hash == bundle.content_hash
        and row.calculation_result_hash == recreated_result.content_hash
        and row.anchor_boundary_hash == bundle.anchor_boundary.content_hash
        and row.anchor_reference_price_hash == (
            None if bundle.reference_price is None else bundle.reference_price.content_hash)
        and row.domain_lineage_hashes == tuple(
            item.content_hash for item in bundle.domain_lineage)
        and row.anchor_snapshot_id == bundle.anchor_snapshot_id
        and row.outcome_snapshot_id == bundle.outcome_snapshot_id
        and independent.bundle_id == bundle.content_hash
        and independent.lineage_digest == content_hash(
            tuple(item.content_hash for item in bundle.domain_lineage))
    )
    body = {"row_id": row.row_id, "bundle_id": bundle.content_hash,
            "independent_reference_id": independent.reference_id,
            "state_match": state, "reason_match": reason,
            "numeric_match": numeric, "barrier_match": barriers,
            "lineage_match": lineage,
            "matched": all((state, reason, numeric, barriers, lineage))}
    return RowIndependentGateEvidenceV2(**body,
        evidence_id=content_hash({"schema_version": "RowIndependentGateEvidenceV2",
                                  **body}))


@dataclass(frozen=True, slots=True)
class SourcePinnedRowComparisonLedgerV2:
    partition_id: str
    source_approval_ids: tuple[str, ...]
    checked_rows: int
    comparison_ids: tuple[str, ...]
    mismatch_row_ids: tuple[str, ...]
    ledger_id: str

    def verify(self) -> bool:
        body = {item.name: getattr(self, item.name) for item in fields(self)
                if item.name != "ledger_id"}
        return (self.checked_rows == len(self.comparison_ids)
                and len(self.comparison_ids) == len(set(self.comparison_ids))
                and self.ledger_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def write_row_comparison_ledger(root: Path,
                                ledger: SourcePinnedRowComparisonLedgerV2) -> Path:
    if not ledger.verify():
        raise ValueError("verified row comparison ledger required")
    path = root / "gate_evidence" / f"row-comparison-{ledger.ledger_id}.json"
    payload = canonical_json(ledger)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable row comparison ledger collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_row_comparison_ledger_exact(path: Path, expected_id: str
                                     ) -> SourcePinnedRowComparisonLedgerV2:
    if (not re.fullmatch(r"[0-9a-f]{64}", expected_id)
            or path.name != f"row-comparison-{expected_id}.json"):
        raise ValueError("comparison ledger ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        ledger = SourcePinnedRowComparisonLedgerV2(
            partition_id=values["partition_id"],
            source_approval_ids=tuple(values["source_approval_ids"]),
            checked_rows=values["checked_rows"],
            comparison_ids=tuple(values["comparison_ids"]),
            mismatch_row_ids=tuple(values["mismatch_row_ids"]),
            ledger_id=values["ledger_id"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("comparison ledger unavailable or malformed") from error
    if (ledger.ledger_id != expected_id or not ledger.verify()
            or canonical_json(ledger) != raw):
        raise ValueError("comparison ledger identity mismatch")
    return ledger


def _derive_partition_comparisons(producer: HistoricalFiveDomainProducerV1,
                                  partition_path: Path, expected_partition_id: str
                                  ) -> SourcePinnedRowComparisonLedgerV2:
    """Test seam; formal callers use derive_partition_comparisons_exact."""
    rows = read_partition_rows_exact(partition_path, expected_partition_id)
    candidates_by_session = {}
    comparison_ids = []
    mismatches = []
    for row in rows:
        if row.anchor_session not in candidates_by_session:
            candidates, _ = producer.candidate_identities(row.anchor_session)
            by_canonical = {}
            for canonical, provider in candidates:
                by_canonical.setdefault(canonical, []).append(provider)
            candidates_by_session[row.anchor_session] = by_canonical
        providers = candidates_by_session[row.anchor_session].get(
            row.canonical_security_identity, ())
        if len(providers) != 1:
            raise ValueError("row canonical identity lacks one exact Master provider")
        produced = producer.produce_anchor(providers[0], row.anchor_session)
        if not isinstance(produced, tuple):
            raise ValueError("materialized row is excluded by source authority")
        bundle = producer.assemble(*produced)
        comparison = compare_row_independently(row, bundle)
        comparison_ids.append(comparison.evidence_id)
        if not comparison.matched:
            mismatches.append(row.row_id)
    source_ids = (
        producer.calendar.approval_id,
        producer.master.approval["approval_id"],
        producer.bars.reader.derived_approval_id,
        producer.status_pins.approval_id,
        producer.actions.approval_id,
    )
    body = {"partition_id": expected_partition_id,
            "source_approval_ids": source_ids, "checked_rows": len(rows),
            "comparison_ids": tuple(comparison_ids),
            "mismatch_row_ids": tuple(mismatches)}
    return SourcePinnedRowComparisonLedgerV2(**body,
        ledger_id=content_hash({"schema_version": "SourcePinnedRowComparisonLedgerV2",
                                **body}))


def derive_partition_comparisons_exact(source_root: Path, partition_path: Path,
                                       expected_partition_id: str
                                       ) -> SourcePinnedRowComparisonLedgerV2:
    """Only formal entry: reload physically pinned five-domain source authority."""
    producer = HistoricalFiveDomainProducerV1.load_exact(source_root)
    return _derive_partition_comparisons(producer, partition_path,
                                         expected_partition_id)
