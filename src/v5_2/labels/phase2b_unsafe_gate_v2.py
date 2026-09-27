"""Content-addressed unsafe-state preservation evidence for exact rows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.contracts import LabelState
from v5_2.labels.dataset_contracts import LabelRowV1


_ID = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class UnsafePreservationEvidenceV2:
    partition_id: str
    unsafe_rows: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    unsafe_value_count: int
    reason_counts: tuple[tuple[str, int], ...]
    evidence_id: str

    def verify(self) -> bool:
        body = {key: getattr(self, key) for key in self.__dataclass_fields__
                if key != "evidence_id"}
        counts = Counter(reason for _, values in self.unsafe_rows
                         for _, reason in values)
        return (
            bool(_ID.fullmatch(self.partition_id))
            and self.unsafe_value_count == sum(counts.values())
            and self.reason_counts == tuple(sorted(counts.items()))
            and self.unsafe_rows == tuple(sorted(self.unsafe_rows))
            and len(self.unsafe_rows) == len({row_id for row_id, _ in self.unsafe_rows})
            and self.evidence_id == content_hash({
                "schema_version": type(self).__name__, **body})
        )


def derive_unsafe_preservation_evidence(
        rows: tuple[LabelRowV1, ...], partition_id: str
        ) -> UnsafePreservationEvidenceV2:
    if not all(row.verify() for row in rows):
        raise ValueError("verified physical rows required")
    unsafe = []
    for row in rows:
        values = tuple((value.label_name, value.reason_code.value)
                       for value in row.values
                       if value.state is LabelState.NOT_LABEL_SAFE
                       and value.reason_code is not None
                       and value.value is None)
        if sum(value.state is LabelState.NOT_LABEL_SAFE for value in row.values) != len(values):
            raise ValueError("unsafe state lacks reason")
        if values:
            unsafe.append((row.row_id, values))
    ordered = tuple(sorted(unsafe))
    counts = Counter(reason for _, values in ordered for _, reason in values)
    body = {"partition_id": partition_id, "unsafe_rows": ordered,
            "unsafe_value_count": sum(counts.values()),
            "reason_counts": tuple(sorted(counts.items()))}
    evidence = UnsafePreservationEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "UnsafePreservationEvidenceV2", **body}))
    if not evidence.verify():
        raise ValueError("unsafe preservation evidence invalid")
    return evidence


def write_unsafe_preservation_evidence(root: Path,
                                       evidence: UnsafePreservationEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified unsafe preservation evidence required")
    path = root / "gate_evidence" / f"unsafe-preservation-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable unsafe preservation evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_unsafe_preservation_evidence_exact(path: Path, expected_id: str
                                            ) -> UnsafePreservationEvidenceV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"unsafe-preservation-{expected_id}.json"):
        raise ValueError("unsafe preservation ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        evidence = UnsafePreservationEvidenceV2(
            partition_id=values["partition_id"],
            unsafe_rows=tuple((row_id, tuple(tuple(item) for item in reasons))
                              for row_id, reasons in values["unsafe_rows"]),
            unsafe_value_count=values["unsafe_value_count"],
            reason_counts=tuple(tuple(item) for item in values["reason_counts"]),
            evidence_id=values["evidence_id"],
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("unsafe preservation evidence unavailable or malformed") from error
    if (evidence.evidence_id != expected_id or not evidence.verify()
            or canonical_json(evidence) != raw):
        raise ValueError("unsafe preservation evidence identity mismatch")
    return evidence
