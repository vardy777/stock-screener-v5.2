from __future__ import annotations

from dataclasses import asdict, dataclass

from v5_2.data.identity import content_hash
from v5_2.data.real_audits.corporate_action_evidence import CorporateActionPITEvidenceV1


class CorporateActionPublicationError(RuntimeError):
    """Frozen gate/approval artifacts do not authorize publication."""


@dataclass(frozen=True, slots=True)
class CorporateActionGateResultV1:
    structural: str
    pit: str
    cross_source: str
    revision: str
    adjustment_semantics: str
    rolling_coverage_model: str
    catch_up_2026: str
    production_incremental_readiness: str
    exception_budget: str
    systematic_defect: str
    source_approval: str
    publication_allowed: bool


def gate_artifact_id(gate: CorporateActionGateResultV1, evidence_id: str) -> str:
    return content_hash({"schema_version": "CorporateActionGateArtifactV1", "evidence_id": evidence_id, **asdict(gate)})


def evaluate_corporate_action_gates(
    evidence: CorporateActionPITEvidenceV1, *, cross_source: str, revision: str,
    adjustment: str, catch_up: str, incremental: str, exception_budget: str,
    systematic_defect: str,
) -> CorporateActionGateResultV1:
    integrity = evidence.verify()
    structural = "PASS" if integrity else "FAIL"
    pit = "PASS" if integrity and evidence.complete else ("PENDING" if integrity else "FAIL")
    rolling = "PASS" if integrity and evidence.rolling_coverage_end > evidence.baseline_validation_end else "FAIL"
    statuses = (structural, pit, cross_source, revision, adjustment, rolling,
                catch_up, incremental, exception_budget, systematic_defect)
    rejected = not integrity or "FAIL" in statuses
    all_pass = all(status == "PASS" for status in statuses)
    decision = "REJECTED" if rejected else ("APPROVED_WITH_RULES" if all_pass else "PENDING")
    return CorporateActionGateResultV1(
        structural=structural, pit=pit, cross_source=cross_source, revision=revision,
        adjustment_semantics=adjustment, rolling_coverage_model=rolling,
        catch_up_2026=catch_up, production_incremental_readiness=incremental,
        exception_budget=exception_budget, systematic_defect=systematic_defect,
        source_approval=decision, publication_allowed=all_pass,
    )


def authorize_corporate_action_publication(
    gate: CorporateActionGateResultV1, approval_decision: str,
    evidence: CorporateActionPITEvidenceV1,
) -> bool:
    if not evidence.verify():
        raise CorporateActionPublicationError("evidence integrity failed")
    if not gate.publication_allowed or gate.source_approval != "APPROVED_WITH_RULES":
        raise CorporateActionPublicationError("gate does not authorize publication")
    if approval_decision != gate.source_approval:
        raise CorporateActionPublicationError("approval does not match frozen gate")
    return True
