"""Two fresh, source-pinned offline builds of the same historical month."""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.historical_month_integration import integrate_real_month
from v5_2.labels.partition_store import read_partition_exact, read_partition_rows_exact
from v5_2.labels.phase2b_gate_evidence_v2 import derive_partition_comparisons_exact
from v5_2.labels.phase2b_month_coverage_v2 import derive_month_coverage_evidence_exact


_ID = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class SourcePinnedReplayEvidenceV2:
    month: str
    partition_ids: tuple[str, str]
    candidate_set_hashes: tuple[str, str]
    coverage_evidence_ids: tuple[str, str]
    scoped_ledger_ids: tuple[str, str]
    row_set_hashes: tuple[str, str]
    row_comparison_ledger_id: str
    evidence_id: str

    def verify(self) -> bool:
        body = {item.name: getattr(self, item.name) for item in fields(self)
                if item.name != "evidence_id"}
        pairs = (self.partition_ids, self.candidate_set_hashes,
                 self.coverage_evidence_ids, self.scoped_ledger_ids,
                 self.row_set_hashes)
        return (
            self.month == "2010-01"
            and all(len(pair) == 2 and pair[0] == pair[1]
                    and all(_ID.fullmatch(value) for value in pair)
                    for pair in pairs)
            and bool(_ID.fullmatch(self.row_comparison_ledger_id))
            and self.evidence_id == content_hash({
                "schema_version": type(self).__name__, **body})
        )


def replay_binds_evaluated_sources(evidence: SourcePinnedReplayEvidenceV2,
                                   *, partition_id: str, candidate_set_hash: str,
                                   coverage_id: str, scoped_ledger_id: str,
                                   comparison_ledger_id: str) -> bool:
    """A valid replay of a different generation cannot approve this one."""
    return (evidence.verify()
            and evidence.partition_ids[0] == partition_id
            and evidence.candidate_set_hashes[0] == candidate_set_hash
            and evidence.coverage_evidence_ids[0] == coverage_id
            and evidence.scoped_ledger_ids[0] == scoped_ledger_id
            and evidence.row_comparison_ledger_id == comparison_ledger_id)


def derive_replay_evidence_exact(source_root: Path,
                                 scratch_root: Path) -> SourcePinnedReplayEvidenceV2:
    """Rerun production materialization twice; independently verify both outputs."""
    runs = []
    for name in ("run-a", "run-b"):
        output = scratch_root / name
        if output.exists():
            raise ValueError("fresh replay output directory required")
        result = integrate_real_month(source_root, output, "2010-01")
        partition_path = (output / "labels" / "historical" / result.month
                          / f"{result.partition_id}.jsonl")
        scoped_path = output / "scoped_exclusions" / f"{result.scoped_exclusion_hash}.json"
        partition = read_partition_exact(partition_path, result.partition_id)
        rows = read_partition_rows_exact(partition_path, result.partition_id)
        coverage = derive_month_coverage_evidence_exact(
            source_root, partition_path, result.partition_id,
            scoped_path, result.scoped_exclusion_hash)
        if (coverage.coverage_hash != result.coverage_hash
                or coverage.materialized_rows != result.materialized_rows
                or partition.row_ids != tuple(row.row_id for row in rows)):
            raise ValueError("replay coverage or physical membership differs")
        comparison = derive_partition_comparisons_exact(
            source_root, partition_path, result.partition_id)
        if (comparison.mismatch_row_ids
                or comparison.checked_rows != result.materialized_rows):
            raise ValueError("replay independent row comparison failed")
        runs.append((result, coverage, content_hash(tuple(row.row_id for row in rows)),
                     comparison))
    left, right = runs
    if left[3] != right[3]:
        raise ValueError("replay row comparison ledgers differ")
    body = {
        "month": "2010-01",
        "partition_ids": (left[0].partition_id, right[0].partition_id),
        "candidate_set_hashes": (left[1].candidate_set_hash, right[1].candidate_set_hash),
        "coverage_evidence_ids": (left[1].evidence_id, right[1].evidence_id),
        "scoped_ledger_ids": (left[0].scoped_exclusion_hash,
                              right[0].scoped_exclusion_hash),
        "row_set_hashes": (left[2], right[2]),
        "row_comparison_ledger_id": left[3].ledger_id,
    }
    evidence = SourcePinnedReplayEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "SourcePinnedReplayEvidenceV2", **body}))
    if not evidence.verify():
        raise ValueError("source-pinned replay differs across fresh builds")
    return evidence


def write_replay_evidence(root: Path, evidence: SourcePinnedReplayEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified replay evidence required")
    path = root / "gate_evidence" / f"replay-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable replay evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_replay_evidence_exact(path: Path, expected_id: str) -> SourcePinnedReplayEvidenceV2:
    if not _ID.fullmatch(expected_id) or path.name != f"replay-{expected_id}.json":
        raise ValueError("replay ID/path mismatch")
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
        for key in ("partition_ids", "candidate_set_hashes", "coverage_evidence_ids",
                    "scoped_ledger_ids", "row_set_hashes"):
            value[key] = tuple(value[key])
        evidence = SourcePinnedReplayEvidenceV2(**value)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("replay evidence unavailable or malformed") from error
    if (evidence.evidence_id != expected_id or not evidence.verify()
            or canonical_json(evidence) != raw):
        raise ValueError("replay evidence identity mismatch")
    return evidence
