"""Exact Master graph boundary and scoped transition evidence."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, timedelta
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.historical_five_domain_producer import (
    HistoricalFiveDomainProducerV1, ScopedAnchorExclusionV1,
)


_ID = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER = "302132.SZ"
_IDENTITY_BEFORE = "300114.SZ"
_ANCHOR = date(2025, 2, 14)
_TRANSITION = date(2025, 2, 17)
_GRAPH = "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0"
_GRAPH_APPROVAL = "a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f"


def compare_identity_boundary_to_source(candidate_canonical: str,
                                        candidate_transition: date,
                                        resolved, intervals: tuple) -> bool:
    if (resolved.provider_identity != _PROVIDER
            or resolved.effective_identity != candidate_canonical
            or resolved.graph_id != _GRAPH
            or resolved.graph_approval_id != _GRAPH_APPROVAL
            or len(intervals) != 2):
        return False
    before, after = intervals
    return (before.identity == candidate_canonical
            and before.effective_to == date(2025, 2, 16)
            and after.identity == "302132.SZ"
            and after.effective_from == candidate_transition
            and candidate_transition == before.effective_to + timedelta(days=1))


@dataclass(frozen=True, slots=True)
class IdentitySafetyEvidenceV2:
    master_authority_id: str
    master_approval_id: str
    graph_id: str
    graph_approval_id: str
    transition_fact_id: str
    canonical_before: str
    canonical_after: str
    transition_effective: str
    scoped_anchor: str
    scoped_reason: str
    scoped_evidence_ids: tuple[str, ...]
    ordinary_fact_id: str
    ordinary_bundle_id: str
    evidence_id: str

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "evidence_id"}
        return (all(_ID.fullmatch(value) for value in (
                    self.master_authority_id, self.master_approval_id,
                    self.graph_id, self.graph_approval_id,
                    self.transition_fact_id, self.ordinary_fact_id,
                    self.ordinary_bundle_id, *self.scoped_evidence_ids))
                and self.graph_id == _GRAPH
                and self.graph_approval_id == _GRAPH_APPROVAL
                and self.canonical_before == _IDENTITY_BEFORE
                and self.canonical_after == "302132.SZ"
                and self.transition_effective == _TRANSITION.isoformat()
                and self.scoped_anchor == _ANCHOR.isoformat()
                and self.scoped_reason == "IDENTITY_TRANSITION_WINDOW_UNRESOLVED"
                and self.scoped_evidence_ids == (
                    self.transition_fact_id, self.graph_id, self.graph_approval_id)
                and self.evidence_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def derive_identity_safety_evidence_exact(root: Path) -> IdentitySafetyEvidenceV2:
    producer = HistoricalFiveDomainProducerV1.load_exact(root)
    resolved = producer.master.resolve(_IDENTITY_BEFORE, _ANCHOR)
    intervals = producer.master._facts_by_provider[resolved.provider_identity].intervals
    if not compare_identity_boundary_to_source(
            _IDENTITY_BEFORE, _TRANSITION, resolved, intervals):
        raise ValueError("approved Master transition boundary mismatch")
    scoped = producer.produce_anchor(_IDENTITY_BEFORE, _ANCHOR)
    if (not isinstance(scoped, ScopedAnchorExclusionV1)
            or scoped.domain != "security_master"
            or scoped.reason != "IDENTITY_TRANSITION_WINDOW_UNRESOLVED"
            or scoped.evidence_ids != (
                resolved.fact_id, resolved.graph_id, resolved.graph_approval_id)):
        raise ValueError("cross-transition anchor was not scoped fail-closed")
    ordinary = producer.master.resolve("000333.SZ", date(2021, 6, 1))
    produced = producer.produce_anchor("000333.SZ", date(2021, 6, 1))
    if (not isinstance(produced, tuple)
            or ordinary.effective_identity != "000333.SZ"):
        raise ValueError("ordinary canonical Master identity unavailable")
    bundle = producer.assemble(*produced)
    if (not bundle.verify()
            or bundle.canonical_security_identity != ordinary.effective_identity):
        raise ValueError("ordinary identity does not match source bundle")
    body = {
        "master_authority_id": producer.master.authority["authority_id"],
        "master_approval_id": producer.master.approval["approval_id"],
        "graph_id": resolved.graph_id,
        "graph_approval_id": resolved.graph_approval_id,
        "transition_fact_id": resolved.fact_id,
        "canonical_before": resolved.effective_identity,
        "canonical_after": intervals[1].identity,
        "transition_effective": intervals[1].effective_from.isoformat(),
        "scoped_anchor": scoped.anchor_session.isoformat(),
        "scoped_reason": scoped.reason,
        "scoped_evidence_ids": scoped.evidence_ids,
        "ordinary_fact_id": ordinary.fact_id,
        "ordinary_bundle_id": bundle.content_hash,
    }
    result = IdentitySafetyEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "IdentitySafetyEvidenceV2", **body}))
    if not result.verify():
        raise ValueError("identity safety evidence invalid")
    return result


def write_identity_safety_evidence(root: Path, evidence: IdentitySafetyEvidenceV2
                                   ) -> Path:
    if not evidence.verify():
        raise ValueError("verified identity evidence required")
    path = root / "gate_evidence" / f"identity-safety-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable identity evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_identity_safety_evidence_exact(path: Path, expected_id: str
                                        ) -> IdentitySafetyEvidenceV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"identity-safety-{expected_id}.json"):
        raise ValueError("identity evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        values["scoped_evidence_ids"] = tuple(values["scoped_evidence_ids"])
        result = IdentitySafetyEvidenceV2(**values)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("identity evidence unavailable or malformed") from error
    if (result.evidence_id != expected_id or not result.verify()
            or canonical_json(result) != raw):
        raise ValueError("identity evidence identity mismatch")
    return result
