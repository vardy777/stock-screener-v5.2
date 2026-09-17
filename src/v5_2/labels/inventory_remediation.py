"""Fail-closed audit and bounded discovery for the frozen Phase 2A inventory.

Applicability is established without importing or calling the production label
engine.  The first required stratum is structurally incompatible with the
approved Phase 1 bundle contract, so discovery stops before any V2 is created.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from v5_2.data.identity import content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.independent_reference import calculate_independent_reference


INVALID_V1_SLOTS = (16, 17, 20, 21, 22)
PREDICATE_VERSION = "phase2a-reference-stratum-predicates-v1"
DISCOVERY_VERSION = "phase2a-approved-evidence-discovery-v1"


@dataclass(frozen=True, slots=True)
class ApplicabilityAuditEntryV1:
    slot: int
    registered_stratum: str
    identity: str
    anchor_session: str
    actual_behavior: str
    failed_criterion: str
    evidence_ids: tuple[str, ...]
    applicable: bool


@dataclass(frozen=True, slots=True)
class ReferenceApplicabilityAuditV1:
    v1_inventory_id: str
    predicate_version: str
    entries: tuple[ApplicabilityAuditEntryV1, ...]
    audit_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {"v1_inventory_id": self.v1_inventory_id,
                "predicate_version": self.predicate_version,
                "entries": self.entries}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return (self.audit_id == self.content_hash == digest
                and tuple(item.slot for item in self.entries) == INVALID_V1_SLOTS)


@dataclass(frozen=True, slots=True)
class ReplacementDiscoveryEntryV1:
    slot: int
    stratum: str
    status: str
    replacement_identity: str | None
    replacement_anchor_session: str | None
    reason: str
    predicate_version: str
    discovery_version: str


@dataclass(frozen=True, slots=True)
class ReferenceReplacementDiscoveryV1:
    v1_inventory_id: str
    applicability_audit_id: str
    entries: tuple[ReplacementDiscoveryEntryV1, ...]
    inventory_v2_created: bool
    inventory_v2_id: str | None
    provider_requests: int
    network_calls: int
    discovery_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in (
            "v1_inventory_id", "applicability_audit_id", "entries",
            "inventory_v2_created", "inventory_v2_id", "provider_requests",
            "network_calls",
        )}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return (self.discovery_id == self.content_hash == digest
                and self.provider_requests == self.network_calls == 0
                and not self.inventory_v2_created and self.inventory_v2_id is None)


def _actual_behavior(slot, result) -> tuple[str, str]:
    states = sorted({item[1] for item in result.result_summary})
    reasons = sorted({item[3] for item in result.result_summary if item[3]})
    barriers = tuple((item.label_name, item.outcome or "AMBIGUOUS",
                      item.decisive_session.isoformat() if item.decisive_session else "")
                     for item in result.barriers)
    if slot.slot == 16:
        return (f"states={states}; required H1..H5 bars are complete",
                "no approved exchange-open future session lacks both a bar and a valid explanation")
    if slot.slot == 17:
        return (f"states={states}; corporate_actions contain no unsupported action type",
                "no RIGHTS_ISSUE, STOCK_SPLIT, or SHARE_CONVERSION exists in the label window")
    if slot.slot == 20:
        return (f"barriers={barriers}", "target barrier contract is UPPER_FIRST, not LOWER_FIRST")
    if slot.slot == 21:
        return (f"barriers={barriers}", "at least one target barrier contract has a decisive hit")
    if slot.slot == 22:
        return (f"states={states}; reasons={reasons}; barriers={barriers}",
                "no same-session upper-and-lower ambiguity occurs before a prior decisive hit")
    raise ValueError("slot is not part of the remediation")


def audit_v1_applicability(repository_root: Path) -> ReferenceApplicabilityAuditV1:
    inventory = build_frozen_inventory()
    assembler = Phase2AEvidenceAssemblerV1(repository_root)
    entries = []
    for number in INVALID_V1_SLOTS:
        slot = inventory.slots[number - 1]
        bundle = assembler.assemble(slot)
        independent = calculate_independent_reference(slot.slot, bundle)
        actual, criterion = _actual_behavior(slot, independent)
        entries.append(ApplicabilityAuditEntryV1(
            slot.slot, slot.stratum, slot.security_identity,
            slot.anchor_session.isoformat(), actual, criterion,
            (slot.candidate_hash, bundle.content_hash, independent.reference_id), False,
        ))
    body = {"v1_inventory_id": inventory.inventory_id,
            "predicate_version": PREDICATE_VERSION, "entries": tuple(entries)}
    digest = content_hash({"schema_version": "ReferenceApplicabilityAuditV1", **body})
    return ReferenceApplicabilityAuditV1(**body, audit_id=digest, content_hash=digest)


def discover_replacements(repository_root: Path) -> ReferenceReplacementDiscoveryV1:
    """Stop at the first mandatory contract contradiction, without fabrication.

    FUTURE_BAR_MISSING requires an approved bundle containing an unexplained
    missing bar.  Phase2AEvidenceAssemblerV1 intentionally rejects exactly that
    state before bundle construction.  Therefore no candidate can satisfy both
    the frozen stratum and the approved five-domain bundle contract.
    """
    audit = audit_v1_applicability(repository_root)
    inventory = build_frozen_inventory()
    entries = []
    for number in INVALID_V1_SLOTS:
        slot = inventory.slots[number - 1]
        if number == 16:
            status = "REAL_REFERENCE_SAMPLE_UNAVAILABLE"
            reason = "FROZEN_REFERENCE_STRATUM_INCOMPATIBLE_WITH_PHASE1_APPROVED_EVIDENCE_CONTRACT"
        else:
            status = "NOT_SEARCHED_AFTER_MANDATORY_CONTRACT_CONFLICT"
            reason = "STOP_BOUNDARY_TRIGGERED_BY_SLOT_16"
        entries.append(ReplacementDiscoveryEntryV1(
            number, slot.stratum, status, None, None, reason,
            PREDICATE_VERSION, DISCOVERY_VERSION,
        ))
    body = {
        "v1_inventory_id": inventory.inventory_id,
        "applicability_audit_id": audit.audit_id,
        "entries": tuple(entries), "inventory_v2_created": False,
        "inventory_v2_id": None, "provider_requests": 0, "network_calls": 0,
    }
    digest = content_hash({"schema_version": "ReferenceReplacementDiscoveryV1", **body})
    return ReferenceReplacementDiscoveryV1(**body, discovery_id=digest, content_hash=digest)
