from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash
from v5_2.labels.acceptance import PHASE2A_STRATA
from v5_2.labels.acceptance_v2_contracts import (
    EvidenceClass,
    Phase2AAcceptanceArchitectureAmendmentV2,
    Phase2AAcceptanceArchitectureAmendmentV2_1,
    RealReferenceCaseV2,
    RealReferenceCoverageLedgerV2,
    build_frozen_amendment_v2,
)


CHECKPOINT7_COMPARISON_LEDGER_ID = "0ee799a175a5e6832b9ca79d88ff9a0b9583ff92e204849274f96a031c397247"
RETAINED_SLOTS = (*range(1, 16), *range(18, 23))


def _verify_source(source: dict) -> None:
    if source.get("ledger_id") != CHECKPOINT7_COMPARISON_LEDGER_ID or source.get("content_hash") != CHECKPOINT7_COMPARISON_LEDGER_ID:
        raise ValueError("checkpoint7 comparison ledger exact pin required")
    entries = source.get("entries", ())
    if tuple(item.get("slot") for item in entries) != tuple(range(1, 23)):
        raise ValueError("checkpoint7 comparison ledger malformed")
    for item in entries:
        body = {key: value for key, value in item.items() if key not in {"comparison_hash", "content_hash"}}
        digest = content_hash({"schema_version": "FullComparisonEntryV1", **body})
        if item.get("comparison_hash") != digest or item.get("content_hash") != digest:
            raise ValueError("checkpoint7 comparison entry tampered")
    digest = content_hash({"schema_version": "FullComparisonLedgerV1", "entries": entries})
    if digest != CHECKPOINT7_COMPARISON_LEDGER_ID:
        raise ValueError("checkpoint7 comparison ledger tampered")


def _roles(slot: int) -> tuple[str, ...]:
    overrides = {
        20: ("ACTUAL_UPPER_FIRST_REAL_PATH",),
        21: ("ACTUAL_LOWER_FIRST_AND_NEITHER_REAL_PATH",),
        22: ("ACTUAL_LOWER_FIRST_REAL_PATH",),
    }
    return overrides.get(slot, (PHASE2A_STRATA[slot - 1].upper().replace(" ", "_"),))


MANDATORY_REAL_ROLES_V2_1 = frozenset(role for slot in RETAINED_SLOTS for role in _roles(slot))


@dataclass(frozen=True, slots=True)
class RealReferenceCoverageLedgerV2_1:
    amendment_id: str
    checkpoint7_comparison_ledger_id: str
    cases: tuple[RealReferenceCaseV2, ...]
    semantic_role_index: tuple[tuple[str, tuple[int, ...]], ...]
    ledger_id: str
    content_hash: str

    @classmethod
    def create(cls, *, amendment_id: str, checkpoint7_comparison_ledger_id: str,
               cases: tuple[RealReferenceCaseV2, ...]):
        role_slots: dict[str, list[int]] = {}
        for case in cases:
            for role in case.semantic_roles:
                role_slots.setdefault(role, []).append(case.slot)
        index = tuple((role, tuple(slots)) for role, slots in sorted(role_slots.items()))
        body = {
            "amendment_id": amendment_id,
            "checkpoint7_comparison_ledger_id": checkpoint7_comparison_ledger_id,
            "cases": cases,
            "semantic_role_index": index,
        }
        digest = content_hash({"schema_version": cls.__name__, **body})
        return cls(**body, ledger_id=digest, content_hash=digest)

    def verify(self) -> bool:
        body = {
            "amendment_id": self.amendment_id,
            "checkpoint7_comparison_ledger_id": self.checkpoint7_comparison_ledger_id,
            "cases": self.cases,
            "semantic_role_index": self.semantic_role_index,
        }
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return (
            self.ledger_id == self.content_hash == digest
            and len(self.cases) == 20
            and tuple(case.slot for case in self.cases) == RETAINED_SLOTS
            and all(case.verify() and case.evidence_class is EvidenceClass.REAL_MARKET_EVIDENCE for case in self.cases)
        )


def validate_mandatory_real_roles_v2_1(ledger: RealReferenceCoverageLedgerV2_1) -> bool:
    indexed = {role for role, slots in ledger.semantic_role_index if slots}
    actual = {role for case in ledger.cases for role in case.semantic_roles}
    return indexed == actual and MANDATORY_REAL_ROLES_V2_1 <= actual


def build_real_reference_coverage_ledger(
    amendment: Phase2AAcceptanceArchitectureAmendmentV2,
    checkpoint7_comparison_ledger: dict,
    bundles: tuple[object, ...],
) -> RealReferenceCoverageLedgerV2:
    if not amendment.verify():
        raise ValueError("invalid amendment")
    _verify_source(checkpoint7_comparison_ledger)
    if len(bundles) != 20 or any(not bundle.verify() for bundle in bundles):
        raise ValueError("exact 20 verified bundles required")
    bundle_by_id = {bundle.content_hash: bundle for bundle in bundles}
    source_by_slot = {item["slot"]: item for item in checkpoint7_comparison_ledger["entries"]}
    cases = []
    for slot in RETAINED_SLOTS:
        item = source_by_slot[slot]
        if item["disposition"] != "MATCH" or not all(item[name] for name in (
            "numeric_match", "state_match", "reason_match", "barrier_categorical_match",
            "barrier_decisive_session_match", "lineage_validation",
        )):
            raise ValueError(f"checkpoint7 mismatch at slot {slot}")
        bundle = bundle_by_id.get(item["bundle_id"])
        if bundle is None or tuple(x.content_hash for x in bundle.domain_lineage) != tuple(item["five_domain_lineage_ids"]):
            raise ValueError(f"bundle lineage mismatch at slot {slot}")
        cases.append(RealReferenceCaseV2.create(
            slot=slot,
            evidence_class=EvidenceClass.REAL_MARKET_EVIDENCE,
            bundle_id=item["bundle_id"],
            five_domain_lineage_ids=tuple(item["five_domain_lineage_ids"]),
            production_result_id=item["production_result_hash"],
            independent_result_id=item["independent_result_hash"],
            comparison_id=item["comparison_hash"],
            semantic_roles=_roles(slot),
            disposition="MATCH",
        ))
    return RealReferenceCoverageLedgerV2.create(
        amendment_id=amendment.artifact_id,
        checkpoint7_comparison_ledger_id=CHECKPOINT7_COMPARISON_LEDGER_ID,
        cases=tuple(cases),
    )


def build_real_reference_coverage_ledger_v2_1(
    amendment: Phase2AAcceptanceArchitectureAmendmentV2_1,
    checkpoint7_comparison_ledger: dict,
    bundles: tuple[object, ...],
) -> RealReferenceCoverageLedgerV2_1:
    if not amendment.verify():
        raise ValueError("invalid V2.1 amendment")
    previous = build_real_reference_coverage_ledger(
        build_frozen_amendment_v2(),
        checkpoint7_comparison_ledger,
        bundles,
    )
    result = RealReferenceCoverageLedgerV2_1.create(
        amendment_id=amendment.artifact_id,
        checkpoint7_comparison_ledger_id=previous.checkpoint7_comparison_ledger_id,
        cases=previous.cases,
    )
    if not result.verify() or not validate_mandatory_real_roles_v2_1(result):
        raise ValueError("mandatory real semantic coverage incomplete")
    return result
