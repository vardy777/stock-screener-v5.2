from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from v5_2.data.evidence import (
    EvidenceArtifactV1,
    EvidenceStatus,
    EvidenceType,
    EvidenceValidityPolicy,
    EvidenceValidityStatus,
)
from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.dataset_equivalence import (
    DatasetEquivalenceDecision,
    DatasetEquivalenceEvidenceV1,
)


class ApprovalEvaluationError(RuntimeError):
    """Approval inputs are inconsistent or ambiguous."""


class ApprovalResolutionError(RuntimeError):
    """No unique approval exists for an explicit historical resolution."""


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
    evidence_validity_policy_version: str
    equivalence_evidence_id: str | None
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
        evidence_validity_policy: EvidenceValidityPolicy,
        resolution_as_of: datetime,
        equivalence_evidence: DatasetEquivalenceEvidenceV1 | None = None,
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
        validity = tuple(
            evidence_validity_policy.evaluate(
                item, resolution_as_of, source_version_identity
            )
            for item in selected
        )
        equivalence_required = source_name == "datahubco_tushare_proxy"
        if equivalence_evidence is not None and (
            equivalence_evidence.source_name != source_name
            or equivalence_evidence.dataset_kind != dataset_kind
            or equivalence_evidence.verified_at > resolution_as_of
        ):
            raise ApprovalEvaluationError("equivalence evidence scope mismatch")
        if any(item.status is EvidenceStatus.FAIL for item in selected) or (
            equivalence_evidence is not None
            and equivalence_evidence.decision is DatasetEquivalenceDecision.NOT_EQUIVALENT
        ):
            decision = ApprovalDecision.REJECTED
        elif (
            (equivalence_required and equivalence_evidence is None)
            or (
                equivalence_evidence is not None
                and equivalence_evidence.decision
                is DatasetEquivalenceDecision.INSUFFICIENT_EVIDENCE
            )
            or set(by_type) < required
            or any(
            result.status is EvidenceValidityStatus.STALE for result in validity
            )
        ):
            decision = ApprovalDecision.PENDING
        else:
            has_rules = any(value not in (None, False, "", (), [], {}) for value in rule_set.values()) or (
                equivalence_evidence is not None
                and equivalence_evidence.decision
                is DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES
            )
            decision = (
                ApprovalDecision.APPROVED_WITH_RULES
                if has_rules
                else ApprovalDecision.APPROVED
            )
        evidence_ids = tuple(sorted(
            [item.evidence_id for item in selected]
            + ([equivalence_evidence.evidence_id] if equivalence_evidence else [])
        ))
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
            "evidence_validity_policy_version": evidence_validity_policy.policy_version,
            "equivalence_evidence_id": (
                equivalence_evidence.evidence_id if equivalence_evidence else None
            ),
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
            evidence_validity_policy_version=evidence_validity_policy.policy_version,
            equivalence_evidence_id=(
                equivalence_evidence.evidence_id if equivalence_evidence else None
            ),
            supersedes_approval_id=supersedes_approval_id,
        )


@dataclass(frozen=True, slots=True)
class SourceApprovalRevocationArtifactV1:
    revocation_id: str
    approval_id: str
    reason: str
    effective_at: datetime
    created_at: datetime
    evidence_ids: tuple[str, ...]
    policy_version: str
    content_hash: str

    @classmethod
    def create(
        cls,
        *,
        approval_id: str,
        reason: str,
        effective_at: datetime,
        created_at: datetime,
        evidence_ids: Sequence[str],
        policy_version: str,
    ) -> SourceApprovalRevocationArtifactV1:
        if not reason.strip():
            raise ApprovalEvaluationError("revocation reason must not be empty")
        for name, value in (("effective_at", effective_at), ("created_at", created_at)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ApprovalEvaluationError(f"{name} must be timezone-aware")
        identifiers = tuple(sorted(set(evidence_ids)))
        if not identifiers:
            raise ApprovalEvaluationError("revocation evidence must not be empty")
        body = {
            "schema_version": "SourceApprovalRevocationArtifactV1",
            "approval_id": approval_id,
            "reason": reason.strip(),
            "effective_at": effective_at,
            "created_at": created_at,
            "evidence_ids": identifiers,
            "policy_version": policy_version,
        }
        digest = content_hash(body)
        return cls(
            revocation_id=digest,
            content_hash=digest,
            approval_id=approval_id,
            reason=reason.strip(),
            effective_at=effective_at,
            created_at=created_at,
            evidence_ids=identifiers,
            policy_version=policy_version,
        )


class ApprovalResolver:
    def __init__(
        self,
        approvals: Sequence[SourceApprovalArtifactV1],
        revocations: Sequence[SourceApprovalRevocationArtifactV1],
    ) -> None:
        self._approvals = tuple(approvals)
        self._revocations = tuple(revocations)

    def resolve(
        self,
        *,
        source_name: str,
        dataset_kind: str,
        requested_coverage: tuple[date, date],
        resolution_as_of: datetime,
    ) -> str:
        if resolution_as_of.tzinfo is None or resolution_as_of.utcoffset() is None:
            raise ApprovalResolutionError("resolution_as_of must be timezone-aware")
        coverage_start, coverage_end = requested_coverage
        if coverage_end < coverage_start:
            raise ApprovalResolutionError("requested coverage is invalid")
        approving = {ApprovalDecision.APPROVED, ApprovalDecision.APPROVED_WITH_RULES}
        candidates = {
            item.approval_id: item
            for item in self._approvals
            if item.source_name == source_name
            and item.dataset_kind == dataset_kind
            and item.decision in approving
            and item.coverage_start <= coverage_start
            and item.coverage_end >= coverage_end
            and item.verified_at <= resolution_as_of
        }
        revoked = {
            item.approval_id
            for item in self._revocations
            if item.created_at <= resolution_as_of and item.effective_at <= resolution_as_of
        }
        for approval_id in revoked:
            candidates.pop(approval_id, None)
        superseded = {
            item.supersedes_approval_id
            for item in candidates.values()
            if item.supersedes_approval_id is not None
        }
        for approval_id in superseded:
            candidates.pop(approval_id, None)
        if not candidates:
            raise ApprovalResolutionError("no applicable approval")
        if len(candidates) != 1:
            raise ApprovalResolutionError("ambiguous applicable approvals")
        return next(iter(candidates))
