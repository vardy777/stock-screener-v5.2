from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType
from v5_2.data.identity import canonical_json, content_hash


class ApprovalEvaluationError(RuntimeError):
    """Approval inputs are inconsistent or ambiguous."""


class ApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_RULES = "APPROVED_WITH_RULES"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class SourceApprovalArtifactV1:
    approval_id: str
    source_name: str
    dataset_kind: str
    decision: ApprovalDecision
    coverage_start: date
    coverage_end: date
    verified_at: datetime
    source_version_identity: str
    policy_version: str
    rule_set: Mapping[str, Any]
    evidence_ids: tuple[str, ...]
    evidence_bundle_hash: str
    evaluator_version: str
    supersedes_approval_id: str | None
    content_hash: str

    @classmethod
    def evaluate(
        cls,
        *,
        source_name: str,
        dataset_kind: str,
        coverage_start: date,
        coverage_end: date,
        verified_at: datetime,
        source_version_identity: str,
        policy_version: str,
        evaluator_version: str,
        evidence: Sequence[EvidenceArtifactV1],
        required_evidence_types: Sequence[EvidenceType],
        rule_set: Mapping[str, Any],
        supersedes_approval_id: str | None = None,
    ) -> SourceApprovalArtifactV1:
        if coverage_end < coverage_start:
            raise ApprovalEvaluationError("coverage end precedes start")
        if verified_at.tzinfo is None or verified_at.utcoffset() is None:
            raise ApprovalEvaluationError("verified_at must be timezone-aware")
        by_type: dict[EvidenceType, EvidenceArtifactV1] = {}
        for item in evidence:
            existing = by_type.get(item.evidence_type)
            if existing is not None and existing.evidence_id != item.evidence_id:
                raise ApprovalEvaluationError("conflicting evidence for one evidence type")
            by_type[item.evidence_type] = item
        required = set(required_evidence_types)
        selected = [by_type[kind] for kind in required if kind in by_type]
        if any(item.source_version_identity != source_version_identity for item in selected):
            raise ApprovalEvaluationError("evidence source version mismatch")
        if any(item.status is EvidenceStatus.FAIL for item in selected):
            decision = ApprovalDecision.REJECTED
        elif set(by_type) < required:
            decision = ApprovalDecision.PENDING
        else:
            has_rules = any(value not in (None, False, "", (), [], {}) for value in rule_set.values())
            decision = (
                ApprovalDecision.APPROVED_WITH_RULES
                if has_rules
                else ApprovalDecision.APPROVED
            )
        evidence_ids = tuple(sorted(item.evidence_id for item in selected))
        bundle_hash = content_hash(evidence_ids)
        canonical_rules = json.loads(canonical_json(rule_set).decode("utf-8"))
        body = {
            "schema_version": "SourceApprovalArtifactV1",
            "source_name": source_name,
            "dataset_kind": dataset_kind,
            "decision": decision,
            "coverage_start": coverage_start,
            "coverage_end": coverage_end,
            "verified_at": verified_at,
            "source_version_identity": source_version_identity,
            "policy_version": policy_version,
            "rule_set": canonical_rules,
            "evidence_ids": evidence_ids,
            "evidence_bundle_hash": bundle_hash,
            "evaluator_version": evaluator_version,
            "supersedes_approval_id": supersedes_approval_id,
        }
        digest = content_hash(body)
        return cls(
            approval_id=digest,
            content_hash=digest,
            source_name=source_name,
            dataset_kind=dataset_kind,
            decision=decision,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            verified_at=verified_at,
            source_version_identity=source_version_identity,
            policy_version=policy_version,
            rule_set=canonical_rules,
            evidence_ids=evidence_ids,
            evidence_bundle_hash=bundle_hash,
            evaluator_version=evaluator_version,
            supersedes_approval_id=supersedes_approval_id,
        )
