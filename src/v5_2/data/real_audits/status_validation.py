from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus
from v5_2.data.identity import content_hash
from v5_2.data.real_audits.historical_universe import HistoricalUniverseReconciliationV1
from v5_2.data.real_audits.status_official_samples import OfficialStatusSampleLedgerV1
from v5_2.data.real_audits.status_knowledge_time import StatusPITKnowledgeTimeEvidenceV1


@dataclass(frozen=True, slots=True)
class StatusValidationResultV1:
    structural_status: str
    pit_status: str
    cross_source_status: str
    survivorship_status: str
    decision: str
    namechange_row_count: int
    suspension_row_count: int
    observed_symbol_count: int
    unknown_symbol_count: int
    invalid_row_count: int
    official_sample_count: int
    official_mismatch_count: int


@dataclass(frozen=True, slots=True)
class StatusGateEvaluationV2:
    structural_status: str
    pit_status: str
    cross_source_status: str
    survivorship_status: str
    exception_budget_status: str
    systematic_defect_status: str
    decision: str
    publication_allowed: bool
    reasons: tuple[str, ...]


def _evidence_integrity(item: EvidenceArtifactV1) -> bool:
    body = {"schema_version": "EvidenceArtifactV1", "evidence_type": item.evidence_type,
            "status": item.status, "observed_at": item.observed_at, "verified_at": item.verified_at,
            "policy_version": item.policy_version, "source_version_identity": item.source_version_identity,
            "input_artifact_ids": item.input_artifact_ids, "valid_until": item.valid_until,
            "findings": item.findings}
    return item.evidence_id == item.content_hash == content_hash(body)


def _ledger_integrity(item: OfficialStatusSampleLedgerV1) -> bool:
    body = {"inventory_id": item.inventory_id, "entries": item.entries,
            "unique_event_count": item.unique_event_count, "counts": item.counts,
            "systematic_defect": item.systematic_defect}
    return item.content_hash == content_hash(body)


def _universe_integrity(item: HistoricalUniverseReconciliationV1) -> bool:
    supplement_values = {"schema_version": "HistoricalUniverseSupplementV1",
        "original_universe_id": item.supplement.original_universe_id,
        "identity_hashes": tuple(value.content_hash for value in item.supplement.identities)}
    if item.supplement.content_hash != content_hash(supplement_values):
        return False
    body = {"schema_version": "HistoricalUniverseReconciliationV1", "original_universe_id": item.original_universe_id,
            "total": item.total, "counts": item.counts, "item_hashes": tuple(value.item_hash for value in item.items),
            "supplement_hash": item.supplement.content_hash}
    return item.content_hash == content_hash(body)


def evaluate_status_gates(*, structural_status: str,
                          pit_evidence: EvidenceArtifactV1 | StatusPITKnowledgeTimeEvidenceV1 | None,
                          official_ledger: OfficialStatusSampleLedgerV1 | None,
                          reconciliation: HistoricalUniverseReconciliationV1 | None,
                          exception_budget_pass: bool, systematic_defect: bool,
                          source_version_identity: str, revoked_artifact_ids: Sequence[str],
                          expected_inventory_id: str) -> StatusGateEvaluationV2:
    revoked = set(revoked_artifact_ids)
    reasons = []
    confirmed_error = structural_status != "PASS" or not exception_budget_pass or systematic_defect
    pit_status = "PENDING"
    if pit_evidence is not None:
        if isinstance(pit_evidence, StatusPITKnowledgeTimeEvidenceV1):
            valid = (pit_evidence.verify() and pit_evidence.content_hash not in revoked
                     and pit_evidence.source_version_identity == source_version_identity)
            if not valid:
                pit_status, confirmed_error = "FAIL", True
                reasons.append("pit artifact revoked, tampered, or out of scope")
            elif pit_evidence.complete:
                pit_status = "PASS"
        elif (not _evidence_integrity(pit_evidence) or pit_evidence.evidence_id in revoked
              or pit_evidence.source_version_identity != source_version_identity):
            pit_status, confirmed_error = "FAIL", True
            reasons.append("pit artifact revoked, tampered, or out of scope")
        else:
            pit_status = "PASS" if pit_evidence.status is EvidenceStatus.PASS else "FAIL"
            confirmed_error |= pit_status == "FAIL"

    cross_source_status = "PENDING"
    if official_ledger is not None:
        if (not _ledger_integrity(official_ledger) or official_ledger.content_hash in revoked
                or official_ledger.inventory_id != expected_inventory_id):
            cross_source_status, confirmed_error = "FAIL", True
            reasons.append("cross-source ledger revoked, tampered, or out of scope")
        else:
            resolutions = {entry.resolution for entry in official_ledger.entries}
            if "MISMATCH" in resolutions or official_ledger.systematic_defect:
                cross_source_status, confirmed_error = "FAIL", True
            elif resolutions <= {"MATCH"} and official_ledger.entries:
                cross_source_status = "PASS"

    survivorship_status = "PENDING"
    if reconciliation is not None:
        if not _universe_integrity(reconciliation) or reconciliation.content_hash in revoked:
            survivorship_status, confirmed_error = "FAIL", True
            reasons.append("universe artifact revoked or tampered")
        else:
            categories = dict(reconciliation.counts)
            supplemented = {item.security_identity for item in reconciliation.supplement.identities
                            if item.official_evidence_ids and item.effective_from}
            required = {item.security_identity for item in reconciliation.items if item.category == "TARGET_A_SHARE_REQUIRED"}
            if categories.get("UNRESOLVED", 0):
                survivorship_status = "PENDING"
            elif required <= supplemented:
                survivorship_status = "PASS"

    all_pass = (structural_status == "PASS" and pit_status == "PASS" and cross_source_status == "PASS"
                and survivorship_status == "PASS" and exception_budget_pass and not systematic_defect)
    decision = "REJECTED" if confirmed_error else ("APPROVED_WITH_RULES" if all_pass else "PENDING")
    return StatusGateEvaluationV2(structural_status, pit_status, cross_source_status, survivorship_status,
                                  "PASS" if exception_budget_pass else "FAIL",
                                  "FAIL" if systematic_defect else "PASS", decision,
                                  decision in {"APPROVED", "APPROVED_WITH_RULES"}, tuple(reasons))


def _valid_date(value: object) -> bool:
    text = str(value)
    return len(text) == 8 and text.isdigit()


def validate_status_observations(
    *,
    namechange_rows: Sequence[Mapping[str, object]],
    suspension_rows: Sequence[Mapping[str, object]],
    universe_symbols: Sequence[str],
    coverage_start: str,
    coverage_end: str,
    later_delisted_symbols: Sequence[str],
    official_sample_matches: Sequence[bool],
    pit_evidence_status: str | None = None,
) -> StatusValidationResultV1:
    invalid = 0
    for row in namechange_rows:
        if not {"ts_code", "ann_date", "start_date"}.issubset(row):
            invalid += 1
        elif not _valid_date(row["ann_date"]) or not _valid_date(row["start_date"]):
            invalid += 1
        elif not coverage_start <= str(row["ann_date"]) <= coverage_end:
            invalid += 1
    for row in suspension_rows:
        if not {"ts_code", "trade_date", "suspend_type"}.issubset(row):
            invalid += 1
        elif not _valid_date(row["trade_date"]):
            invalid += 1
        elif not coverage_start <= str(row["trade_date"]) <= coverage_end:
            invalid += 1
        elif row["suspend_type"] not in {"S", "R"}:
            invalid += 1

    observed = {str(row.get("ts_code")) for row in (*namechange_rows, *suspension_rows)}
    universe = set(universe_symbols)
    delisted = set(later_delisted_symbols)
    survivorship_status = "PASS" if delisted.issubset(universe) else "FAIL"
    sample_count = len(official_sample_matches)
    mismatches = sum(not match for match in official_sample_matches)
    if sample_count == 0:
        cross_source_status = "PENDING"
    elif sample_count >= 10 and mismatches / sample_count > 0.2:
        cross_source_status = "FAIL"
    else:
        cross_source_status = "PASS" if mismatches == 0 else "PENDING"

    structural_status = "PASS" if invalid == 0 else "FAIL"
    pit_status = pit_evidence_status or "PENDING"
    if pit_status not in {"PASS", "PENDING", "FAIL"}:
        raise ValueError("invalid PIT evidence status")
    decision = (
        "REJECTED"
        if structural_status == "FAIL" or cross_source_status == "FAIL" or pit_status == "FAIL"
        else "INSUFFICIENT_EVIDENCE"
    )
    return StatusValidationResultV1(
        structural_status=structural_status,
        pit_status=pit_status,
        cross_source_status=cross_source_status,
        survivorship_status=survivorship_status,
        decision=decision,
        namechange_row_count=len(namechange_rows),
        suspension_row_count=len(suspension_rows),
        observed_symbol_count=len(observed),
        unknown_symbol_count=len(observed - universe),
        invalid_row_count=invalid,
        official_sample_count=sample_count,
        official_mismatch_count=mismatches,
    )
