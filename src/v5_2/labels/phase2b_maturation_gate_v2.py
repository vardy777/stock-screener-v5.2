"""Source-pinned H0/H1/H3/H5 maturity evidence, separate from label policy."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.contracts import LabelInputBundleV1, LabelResultV1, LabelState
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.independent_reference import (
    IndependentReferenceResultV1, calculate_independent_reference,
)


_ID = re.compile(r"^[0-9a-f]{64}$")
_BASE_BUNDLE_ID = "8a212db4e0337eaceaf90ddf167ce9b278cd9adde05c584f826a6006c99125fa"
_STAGES = ("H0", "H1", "H3", "H5")
_LABEL_MATURITY = (1, 3, 5, 5, 5, 5, 5)


@dataclass(frozen=True, slots=True)
class Phase2BMaturationGateEvidenceV2:
    base_bundle_id: str
    stage_sessions: tuple[str, ...]
    production_result_ids: tuple[str, ...]
    independent_reference_ids: tuple[str, ...]
    pending_counts: tuple[int, ...]
    available_counts: tuple[int, ...]
    mismatch_stages: tuple[str, ...]
    h1_early_barrier_hit: bool
    h1_barrier_published: bool
    evidence_id: str

    def verify(self) -> bool:
        body = {key: getattr(self, key) for key in self.__dataclass_fields__
                if key != "evidence_id"}
        return (
            self.base_bundle_id == _BASE_BUNDLE_ID
            and len(self.stage_sessions) == len(self.production_result_ids)
            == len(self.independent_reference_ids) == len(self.pending_counts)
            == len(self.available_counts) == len(_STAGES)
            and all(_ID.fullmatch(item) for item in (
                *self.production_result_ids, *self.independent_reference_ids))
            and all(stage in _STAGES for stage in self.mismatch_stages)
            and self.evidence_id == content_hash({
                "schema_version": type(self).__name__, **body})
        )


def _with_completion(base: LabelInputBundleV1, completed) -> LabelInputBundleV1:
    body = {key: getattr(base, key) for key in base.__dataclass_fields__
            if key != "content_hash"}
    body["latest_completed_session"] = completed
    return LabelInputBundleV1.create(**body)


def maturation_result_matches_independent(
        result: LabelResultV1, full_truth: IndependentReferenceResultV1,
        completed_count: int) -> bool:
    if (not result.verify() or not full_truth.verify()
            or completed_count not in (0, 1, 3, 5)
            or len(result.values) != len(_LABEL_MATURITY)
            or len(full_truth.result_summary) != len(_LABEL_MATURITY)):
        return False
    actual = tuple((item.label_name, item.state.value, str(item.value),
                    item.reason_code.value if item.reason_code else "")
                   for item in result.values)
    expected = tuple(
        item if completed_count >= endpoint else
        (item[0], "LABEL_PENDING", "None", "HORIZON_NOT_COMPLETED")
        for item, endpoint in zip(full_truth.result_summary, _LABEL_MATURITY)
    )
    return actual == expected


def derive_maturation_gate_evidence_exact(root: Path) -> Phase2BMaturationGateEvidenceV2:
    slot = next(item for item in build_frozen_inventory().slots if item.slot == 4)
    base = Phase2AEvidenceAssemblerV1(root).assemble(slot)
    if not base.verify() or base.content_hash != _BASE_BUNDLE_ID:
        raise ValueError("frozen real maturation source bundle mismatch")
    sessions = base.approved_exchange_sessions
    if len(sessions) != 6 or sessions[0] != base.anchor_session:
        raise ValueError("frozen five-session maturity window mismatch")
    stage_days = (sessions[0], sessions[1], sessions[3], sessions[5])
    stage_ids = []
    independent_ids = []
    pending = []
    available = []
    mismatches = []
    h1_result = None
    full_truth = calculate_independent_reference(1, base)
    for name, day, completed_count in zip(_STAGES, stage_days, (0, 1, 3, 5)):
        bundle = _with_completion(base, day)
        result = ReferenceLabelEngine().evaluate(bundle)
        if not maturation_result_matches_independent(result, full_truth,
                                                     completed_count):
            mismatches.append(name)
        if name == "H1":
            h1_result = result
        stage_ids.append(result.content_hash)
        independent_ids.append(full_truth.reference_id)
        pending.append(sum(item.state is LabelState.LABEL_PENDING
                           for item in result.values))
        available.append(sum(item.state is LabelState.LABEL_AVAILABLE
                             for item in result.values))
    h1_hit = any(item.decisive_session == sessions[1]
                 for item in full_truth.barriers)
    h1_published = any(item.state is LabelState.LABEL_AVAILABLE
                       for item in h1_result.values[5:])
    body = {
        "base_bundle_id": base.content_hash,
        "stage_sessions": tuple(day.isoformat() for day in stage_days),
        "production_result_ids": tuple(stage_ids),
        "independent_reference_ids": tuple(independent_ids),
        "pending_counts": tuple(pending),
        "available_counts": tuple(available),
        "mismatch_stages": tuple(mismatches),
        "h1_early_barrier_hit": h1_hit,
        "h1_barrier_published": h1_published,
    }
    result = Phase2BMaturationGateEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "Phase2BMaturationGateEvidenceV2", **body}))
    if not result.verify():
        raise ValueError("maturation gate evidence invalid")
    return result


def write_maturation_gate_evidence(root: Path,
                                   evidence: Phase2BMaturationGateEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified maturation gate evidence required")
    path = root / "gate_evidence" / f"maturation-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable maturation gate evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_maturation_gate_evidence_exact(path: Path, expected_id: str
                                        ) -> Phase2BMaturationGateEvidenceV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"maturation-{expected_id}.json"):
        raise ValueError("maturation gate evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        for key in ("stage_sessions", "production_result_ids",
                    "independent_reference_ids", "pending_counts",
                    "available_counts", "mismatch_stages"):
            values[key] = tuple(values[key])
        evidence = Phase2BMaturationGateEvidenceV2(**values)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("maturation gate evidence unavailable or malformed") from error
    if (evidence.evidence_id != expected_id or not evidence.verify()
            or canonical_json(evidence) != raw):
        raise ValueError("maturation gate evidence identity mismatch")
    return evidence
