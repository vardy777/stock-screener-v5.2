"""Field-specific independent Phase 2B evidence; not a formal gate by itself."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.contracts import (
    LabelInputBundleV1, LabelReasonCode, LabelResultV1, LabelState,
)
from v5_2.labels.dataset_contracts import LabelRowV1
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.independent_reference import calculate_independent_reference
from v5_2.labels.partition_store import read_partition_rows_exact
from v5_2.labels.phase2b_gate_evidence_v2 import _row_barriers


SEMANTIC_GATES = (
    "STATE_SEMANTICS", "RETURN_SEMANTICS", "MFE_MAE_SEMANTICS",
    "BARRIER_SEMANTICS",
)
RETURN_LABELS = frozenset(("return_1d", "return_3d", "return_5d"))
EXCURSION_LABELS = frozenset((
    "max_favorable_excursion_5d", "max_adverse_excursion_5d"))
BARRIER_LABELS = frozenset((
    "hit_3pct_before_-2pct", "hit_5pct_before_-3pct"))
_ID = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class RowSemanticGateEvidenceV2:
    row_id: str
    bundle_id: str
    independent_reference_id: str
    lineage_match: bool
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    mismatch_labels: tuple[tuple[str, str], ...]
    evidence_id: str

    def verify(self) -> bool:
        body = {key: getattr(self, key) for key in self.__dataclass_fields__
                if key != "evidence_id"}
        return (
            self.passed_gates == tuple(g for g in SEMANTIC_GATES
                                       if g not in self.failed_gates)
            and self.failed_gates == tuple(g for g in SEMANTIC_GATES
                                           if g in self.failed_gates)
            and self.evidence_id == content_hash({
                "schema_version": type(self).__name__, **body})
        )


def compare_semantic_gates(row: LabelRowV1,
                           bundle: LabelInputBundleV1) -> RowSemanticGateEvidenceV2:
    """Compare each frozen value group against an independent calculation."""
    if not row.verify() or not bundle.verify():
        raise ValueError("verified row and source bundle required")
    independent = calculate_independent_reference(1, bundle)
    if not independent.verify():
        raise ValueError("independent reference is invalid")
    actual = {item.label_name: item for item in row.values}
    expected = {name: (state, value, reason)
                for name, state, value, reason in independent.result_summary}
    if set(actual) != set(expected):
        raise ValueError("label set differs from frozen independent reference")
    if any(not isinstance(value.state, LabelState)
           or (value.reason_code is not None
               and not isinstance(value.reason_code, LabelReasonCode))
           for value in actual.values()):
        raise ValueError("unknown label state or reason")
    mismatches: list[tuple[str, str]] = []
    for name, value in actual.items():
        state, numeric, reason = expected[name]
        if ((value.state is LabelState.LABEL_AVAILABLE
             and (value.value is None or value.reason_code is not None))
                or (value.state is not LabelState.LABEL_AVAILABLE
                    and (value.value is not None or value.reason_code is None))):
            mismatches.append(("STATE_SEMANTICS", name))
        if (value.state.value, value.reason_code.value if value.reason_code else "") != (state, reason):
            mismatches.append(("STATE_SEMANTICS", name))
        if str(value.value) != numeric:
            if name in RETURN_LABELS:
                gate = "RETURN_SEMANTICS"
            elif name in EXCURSION_LABELS:
                gate = "MFE_MAE_SEMANTICS"
            elif name in BARRIER_LABELS:
                gate = "BARRIER_SEMANTICS"
            else:
                raise ValueError("unknown frozen label")
            mismatches.append((gate, name))
    expected_barriers = tuple((item.label_name,
        item.outcome or ("AMBIGUOUS" if item.ambiguous_session else ""),
        item.decisive_session.isoformat() if item.decisive_session else "")
        for item in independent.barriers)
    if _row_barriers(row) != expected_barriers:
        mismatches.append(("BARRIER_SEMANTICS", "barrier_evidence"))
    recreated_result = LabelResultV1.create(
        row.canonical_security_identity, row.anchor_session, row.values,
        bundle.content_hash, row.barrier_evidence)
    lineage_match = (
        row.canonical_security_identity == bundle.canonical_security_identity
        and row.anchor_session == bundle.anchor_session
        and row.input_bundle_hash == bundle.content_hash
        and row.calculation_result_hash == recreated_result.content_hash
        and row.anchor_boundary_hash == bundle.anchor_boundary.content_hash
        and row.anchor_reference_price_hash == (
            None if bundle.reference_price is None
            else bundle.reference_price.content_hash)
        and row.domain_lineage_hashes == tuple(
            item.content_hash for item in bundle.domain_lineage)
        and row.anchor_snapshot_id == bundle.anchor_snapshot_id
        and row.outcome_snapshot_id == bundle.outcome_snapshot_id
        and independent.bundle_id == bundle.content_hash
        and independent.lineage_digest == content_hash(
            tuple(item.content_hash for item in bundle.domain_lineage))
    )
    failed = tuple(gate for gate in SEMANTIC_GATES
                   if any(item[0] == gate for item in mismatches))
    body = {
        "row_id": row.row_id,
        "bundle_id": bundle.content_hash,
        "independent_reference_id": independent.reference_id,
        "lineage_match": lineage_match,
        "passed_gates": tuple(g for g in SEMANTIC_GATES if g not in failed),
        "failed_gates": failed,
        "mismatch_labels": tuple(mismatches),
    }
    return RowSemanticGateEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "RowSemanticGateEvidenceV2", **body}))


@dataclass(frozen=True, slots=True)
class SourcePinnedSemanticGroupLedgerV2:
    partition_id: str
    source_approval_ids: tuple[str, ...]
    checked_rows: int
    comparison_ids: tuple[str, ...]
    failed_row_ids_by_gate: tuple[tuple[str, tuple[str, ...]], ...]
    lineage_mismatch_row_ids: tuple[str, ...]
    ledger_id: str

    def verify(self) -> bool:
        body = {key: getattr(self, key) for key in self.__dataclass_fields__
                if key != "ledger_id"}
        return (
            bool(_ID.fullmatch(self.partition_id))
            and len(self.source_approval_ids) == 5
            and all(_ID.fullmatch(value) for value in self.source_approval_ids)
            and self.checked_rows == len(self.comparison_ids)
            and len(self.comparison_ids) == len(set(self.comparison_ids))
            and self.failed_row_ids_by_gate == tuple(
                (gate, rows) for gate, rows in self.failed_row_ids_by_gate
                if gate in SEMANTIC_GATES)
            and tuple(gate for gate, _ in self.failed_row_ids_by_gate) == SEMANTIC_GATES
            and self.ledger_id == content_hash({
                "schema_version": type(self).__name__, **body})
        )


def _derive_semantic_group_ledger(
        producer: HistoricalFiveDomainProducerV1, partition_path: Path,
        expected_partition_id: str) -> SourcePinnedSemanticGroupLedgerV2:
    """Test seam; formal callers use the exact source-loading entrypoint."""
    rows = read_partition_rows_exact(partition_path, expected_partition_id)
    candidates_by_session = {}
    comparisons: list[str] = []
    failures: dict[str, list[str]] = {gate: [] for gate in SEMANTIC_GATES}
    lineage_failures: list[str] = []
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
        evidence = compare_semantic_gates(row, producer.assemble(*produced))
        comparisons.append(evidence.evidence_id)
        for gate in evidence.failed_gates:
            failures[gate].append(row.row_id)
        if not evidence.lineage_match:
            lineage_failures.append(row.row_id)
    body = {
        "partition_id": expected_partition_id,
        "source_approval_ids": (
            producer.calendar.approval_id,
            producer.master.approval["approval_id"],
            producer.bars.reader.derived_approval_id,
            producer.status_pins.approval_id,
            producer.actions.approval_id,
        ),
        "checked_rows": len(rows),
        "comparison_ids": tuple(comparisons),
        "failed_row_ids_by_gate": tuple(
            (gate, tuple(failures[gate])) for gate in SEMANTIC_GATES),
        "lineage_mismatch_row_ids": tuple(lineage_failures),
    }
    return SourcePinnedSemanticGroupLedgerV2(**body, ledger_id=content_hash({
        "schema_version": "SourcePinnedSemanticGroupLedgerV2", **body}))


def derive_semantic_group_ledger_exact(source_root: Path, partition_path: Path,
                                       expected_partition_id: str
                                       ) -> SourcePinnedSemanticGroupLedgerV2:
    producer = HistoricalFiveDomainProducerV1.load_exact(source_root)
    ledger = _derive_semantic_group_ledger(producer, partition_path,
                                           expected_partition_id)
    if not ledger.verify():
        raise ValueError("source-pinned semantic ledger is invalid")
    return ledger


def write_semantic_group_ledger(root: Path,
                                ledger: SourcePinnedSemanticGroupLedgerV2) -> Path:
    if not ledger.verify():
        raise ValueError("verified semantic group ledger required")
    path = root / "gate_evidence" / f"semantic-groups-{ledger.ledger_id}.json"
    payload = canonical_json(ledger)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable semantic group ledger collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_semantic_group_ledger_exact(path: Path, expected_id: str
                                     ) -> SourcePinnedSemanticGroupLedgerV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"semantic-groups-{expected_id}.json"):
        raise ValueError("semantic group ledger ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        ledger = SourcePinnedSemanticGroupLedgerV2(
            partition_id=values["partition_id"],
            source_approval_ids=tuple(values["source_approval_ids"]),
            checked_rows=values["checked_rows"],
            comparison_ids=tuple(values["comparison_ids"]),
            failed_row_ids_by_gate=tuple(
                (gate, tuple(rows)) for gate, rows in values["failed_row_ids_by_gate"]),
            lineage_mismatch_row_ids=tuple(values["lineage_mismatch_row_ids"]),
            ledger_id=values["ledger_id"],
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("semantic group ledger unavailable or malformed") from error
    if (ledger.ledger_id != expected_id or not ledger.verify()
            or canonical_json(ledger) != raw):
        raise ValueError("semantic group ledger identity mismatch")
    return ledger
