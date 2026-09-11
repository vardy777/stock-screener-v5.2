from __future__ import annotations

from dataclasses import dataclass, fields

from v5_2.data.identity import content_hash


class FinancialDisclosurePublicationError(RuntimeError):
    """Frozen evidence and gate artifacts do not authorize publication."""


@dataclass(frozen=True, slots=True)
class FinancialDisclosureGateEvidenceV1:
    structural: str
    pit: str
    cross_source: str
    revision: str
    value_semantics: str
    unit_semantics: str
    historical_coverage: str
    catch_up_2026: str
    survivorship: str
    rolling_coverage_model: str
    production_incremental_readiness: str
    exception_budget: str
    systematic_defect: str
    publication_scope: str
    evidence_ids: tuple[str, ...]
    evidence_id: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        evidence_ids = tuple(values["evidence_ids"])
        if not evidence_ids or any(not item for item in evidence_ids):
            raise ValueError("evidence_ids must be non-empty")
        canonical = {**values, "evidence_ids": evidence_ids}
        digest = content_hash({"schema_version": "FinancialDisclosureGateEvidenceV1", **canonical})
        return cls(evidence_id=digest, content_hash=digest, **canonical)

    def verify(self) -> bool:
        body = {
            field.name: getattr(self, field.name)
            for field in fields(self)
            if field.name not in {"evidence_id", "content_hash"}
        }
        digest = content_hash({"schema_version": "FinancialDisclosureGateEvidenceV1", **body})
        return self.evidence_id == self.content_hash == digest


@dataclass(frozen=True, slots=True)
class FinancialDisclosureGateResultV1:
    structural: str
    pit: str
    cross_source: str
    revision: str
    value_semantics: str
    unit_semantics: str
    historical_coverage: str
    catch_up_2026: str
    survivorship: str
    rolling_coverage_model: str
    production_incremental_readiness: str
    exception_budget: str
    systematic_defect: str
    publication_scope: str
    source_approval: str
    publication_allowed: bool
    evidence_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {"schema_version": "FinancialDisclosureGateResultV1", **{
            field.name: getattr(self, field.name) for field in fields(self)
            if field.name != "content_hash"
        }}
        return self.content_hash == content_hash(body)


def evaluate_financial_disclosure_gates(
    evidence: FinancialDisclosureGateEvidenceV1,
) -> FinancialDisclosureGateResultV1:
    status_fields = (
        "structural", "pit", "cross_source", "revision", "value_semantics",
        "unit_semantics", "historical_coverage", "catch_up_2026", "survivorship",
        "rolling_coverage_model", "production_incremental_readiness",
        "exception_budget", "systematic_defect",
    )
    integrity = evidence.verify()
    statuses = tuple(getattr(evidence, field) for field in status_fields)
    rejected = not integrity or "FAIL" in statuses
    scope_safe = (
        (evidence.publication_scope == "COMPLETE_DATASET" and evidence.historical_coverage == "PASS")
        or (evidence.publication_scope == "OBSERVED_FACTS_ONLY" and evidence.historical_coverage == "PARTIAL")
    )
    all_pass = integrity and scope_safe and all(
        status == "PASS" or (field == "historical_coverage" and scope_safe)
        for field, status in zip(status_fields, statuses)
    )
    decision = "REJECTED" if rejected else ("APPROVED_WITH_RULES" if all_pass else "PENDING")
    copied = {field: getattr(evidence, field) for field in status_fields}
    copied["publication_scope"] = evidence.publication_scope
    body = {"schema_version": "FinancialDisclosureGateResultV1", **copied,
            "source_approval": decision, "publication_allowed": all_pass,
            "evidence_id": evidence.evidence_id}
    return FinancialDisclosureGateResultV1(
        **copied,
        source_approval=decision,
        publication_allowed=all_pass,
        evidence_id=evidence.evidence_id,
        content_hash=content_hash(body),
    )


def authorize_financial_disclosure_publication(
    gate: FinancialDisclosureGateResultV1,
    evidence: FinancialDisclosureGateEvidenceV1,
) -> bool:
    if not evidence.verify() or not gate.verify() or gate.evidence_id != evidence.evidence_id:
        raise FinancialDisclosurePublicationError("gate/evidence integrity failed")
    if not gate.publication_allowed or gate.source_approval != "APPROVED_WITH_RULES":
        raise FinancialDisclosurePublicationError("gate does not authorize publication")
    return True
