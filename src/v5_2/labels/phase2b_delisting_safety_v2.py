"""Effective delisting, later PIT knowledge and scoped label safety evidence."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.data.security_status_facts import DailySecurityStatusFactV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.contracts import LabelInputBundleV1
from v5_2.labels.historical_five_domain_producer import (
    HistoricalFiveDomainProducerV1, ScopedAnchorExclusionV1,
)
from v5_2.labels.independent_reference import calculate_independent_reference


_ID = re.compile(r"^[0-9a-f]{64}$")
_FACT_ID = "bb0caf08220d5eaf7728b891830cf9759df5fc495cc3d6c9e0862b2a1e2eae17"
_MANIFEST_ID = "57b4d38523c32a31959fb8dc9e2335778f97ed86562413c95e7ff9716ec65e3d"


@dataclass(frozen=True, slots=True)
class DelistingSafetyEvidenceV2:
    status_fact_id: str
    status_manifest_id: str
    status_approval_id: str
    effective_date: str
    available_at: str
    real_scope_reason: str
    real_scope_evidence_ids: tuple[str, ...]
    fixture_kind: str
    fixture_bundle_id: str
    correct_reference_id: str
    ignored_boundary_reference_id: str
    correct_reason: str
    ignored_boundary_reason: str
    evidence_id: str

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "evidence_id"}
        return (self.status_fact_id == _FACT_ID
                and self.status_manifest_id == _MANIFEST_ID
                and bool(_ID.fullmatch(self.status_approval_id))
                and self.effective_date == "2023-08-04"
                and self.available_at.startswith("2023-08-07T16:30:00")
                and self.real_scope_reason == "UNEXPLAINED_MISSING_BAR"
                and all(_ID.fullmatch(value) for value in self.real_scope_evidence_ids)
                and self.fixture_kind == "FROZEN_PHASE2A_CONTRACT_FIXTURE"
                and all(_ID.fullmatch(value) for value in (
                    self.fixture_bundle_id, self.correct_reference_id,
                    self.ignored_boundary_reference_id))
                and self.correct_reason == "DELISTING_IN_HORIZON"
                and self.ignored_boundary_reason != self.correct_reason
                and self.evidence_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def _without_delisting(bundle: LabelInputBundleV1) -> LabelInputBundleV1:
    values = {field.name: getattr(bundle, field.name) for field in fields(bundle)
              if field.name != "content_hash"}
    values["delisting_session"] = None
    return LabelInputBundleV1.create(**values)


def derive_delisting_safety_evidence_exact(root: Path) -> DelistingSafetyEvidenceV2:
    fact_path = root / "data/phase_1b2a/facts/daily_security_status" / (
        f"{_FACT_ID}.json")
    raw = fact_path.read_bytes()
    values = json.loads(raw)
    values["session"] = date.fromisoformat(values["session"])
    values["effective_from"] = date.fromisoformat(values["effective_from"])
    values["effective_to"] = (date.fromisoformat(values["effective_to"])
                              if values["effective_to"] else None)
    values["available_at"] = datetime.fromisoformat(values["available_at"])
    values["source_fact_ids"] = tuple(values["source_fact_ids"])
    fact = DailySecurityStatusFactV1(**values)
    if (not fact.verify() or fact.fact_id != _FACT_ID
            or canonical_json(fact) != raw or not fact.is_delisted
            or fact.session != date(2023, 8, 4)):
        raise ValueError("delisting effective fact is invalid")
    manifest_path = root / "data/phase_1b2a/governance" / (
        f"daily_security_status-manifest-{_MANIFEST_ID}.json")
    manifest = json.loads(manifest_path.read_bytes())
    if (manifest.get("dataset_id") != _MANIFEST_ID
            or manifest.get("pit_validation_status") != "PASS"
            or manifest.get("rule_compliance_status") != "PASS"
            or _FACT_ID not in manifest.get("fact_content_hashes", ())):
        raise ValueError("delisting fact lacks approved manifest lineage")
    producer = HistoricalFiveDomainProducerV1.load_exact(root)
    scoped = producer.produce_anchor("002118.SZ", date(2023, 8, 3))
    if (not isinstance(scoped, ScopedAnchorExclusionV1)
            or scoped.domain != "daily_bar"
            or scoped.reason != "UNEXPLAINED_MISSING_BAR"):
        raise ValueError("real delisting boundary was not source-quarantined")
    slot = next(item for item in build_frozen_inventory().slots
                if item.slot == 14)
    if (slot.security_identity != "002118.SZ"
            or slot.anchor_session != date(2023, 8, 3)):
        raise ValueError("frozen Phase 2A delisting fixture changed")
    bundle = Phase2AEvidenceAssemblerV1(root).assemble(slot)
    if not bundle.verify() or bundle.delisting_session != fact.session:
        raise ValueError("frozen delisting fixture does not pin effective date")
    correct = calculate_independent_reference(14, bundle)
    ignored = calculate_independent_reference(14, _without_delisting(bundle))
    reasons = {reason for _, _, _, reason in correct.result_summary}
    ignored_reasons = {reason for _, _, _, reason in ignored.result_summary}
    if (not correct.verify() or not ignored.verify()
            or reasons != {"DELISTING_IN_HORIZON"}
            or len(ignored_reasons) != 1
            or ignored_reasons == reasons):
        raise ValueError("delisting boundary mutation was not detected")
    body = {
        "status_fact_id": fact.fact_id,
        "status_manifest_id": _MANIFEST_ID,
        "status_approval_id": manifest["approval_id"],
        "effective_date": fact.session.isoformat(),
        "available_at": fact.available_at.isoformat(),
        "real_scope_reason": scoped.reason,
        "real_scope_evidence_ids": scoped.evidence_ids,
        "fixture_kind": "FROZEN_PHASE2A_CONTRACT_FIXTURE",
        "fixture_bundle_id": bundle.content_hash,
        "correct_reference_id": correct.reference_id,
        "ignored_boundary_reference_id": ignored.reference_id,
        "correct_reason": next(iter(reasons)),
        "ignored_boundary_reason": next(iter(ignored_reasons)),
    }
    result = DelistingSafetyEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "DelistingSafetyEvidenceV2", **body}))
    if not result.verify():
        raise ValueError("delisting evidence invalid")
    return result


def write_delisting_safety_evidence(root: Path,
                                    evidence: DelistingSafetyEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified delisting evidence required")
    path = root / "gate_evidence" / f"delisting-safety-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable delisting evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_delisting_safety_evidence_exact(path: Path, expected_id: str
                                         ) -> DelistingSafetyEvidenceV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"delisting-safety-{expected_id}.json"):
        raise ValueError("delisting evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        values["real_scope_evidence_ids"] = tuple(values["real_scope_evidence_ids"])
        result = DelistingSafetyEvidenceV2(**values)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("delisting evidence unavailable or malformed") from error
    if (result.evidence_id != expected_id or not result.verify()
            or canonical_json(result) != raw):
        raise ValueError("delisting evidence identity mismatch")
    return result
