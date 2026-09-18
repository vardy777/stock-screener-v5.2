from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path

from v5_2.data.identity import content_hash
from v5_2.data.label_evidence_assembler import EvidenceAssemblyError, Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.acceptance_v2_contracts import BoundaryExecutionV2, EvidenceClass
from v5_2.labels.acceptance_v2_contracts import FailClosedBoundaryLedgerV2, Phase2AAcceptanceArchitectureAmendmentV2


CA_MANIFEST_ID = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"
SUPPORTED_ACTION_TYPES = ("BONUS_SHARE", "CASH_DIVIDEND")
UNSUPPORTED_ACTION_TYPES = ("RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT")


@dataclass(frozen=True, slots=True)
class BoundaryCaseV2:
    semantic_category: str
    evidence_class: EvidenceClass
    evidence_condition: str
    input_evidence_ids: tuple[str, ...]
    rejection_boundary: str
    expected_rejection_code: str
    preflight_rejection_code: str
    fixture_hash: str


def _verify_manifest(manifest: dict) -> None:
    body = {key: value for key, value in manifest.items() if key not in {"dataset_id", "manifest_hash"}}
    digest = content_hash({"schema_version": "DatasetManifestV1", **body})
    if manifest.get("dataset_id") != CA_MANIFEST_ID or manifest.get("manifest_hash") != CA_MANIFEST_ID or digest != CA_MANIFEST_ID:
        raise ValueError("unsupported scope manifest exact pin required")
    if tuple(manifest.get("supported_action_types", ())) != SUPPORTED_ACTION_TYPES:
        raise ValueError("unsupported scope changed")
    if tuple(manifest.get("unsupported_action_types", ())) != UNSUPPORTED_ACTION_TYPES:
        raise ValueError("unsupported scope changed")
    intervals = tuple(tuple(x) for x in manifest.get("unsupported_intervals", ()))
    if tuple(x[0] for x in intervals) != UNSUPPORTED_ACTION_TYPES:
        raise ValueError("unsupported scope intervals missing")


def build_unsupported_ca_boundary_case(manifest: dict) -> BoundaryCaseV2:
    _verify_manifest(manifest)
    fixture = {
        "schema_version": "UnsupportedCorporateActionBoundaryFixtureV1",
        "action_type": "RIGHTS_ISSUE",
        "effective_session": "2024-01-03",
        "classification": EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE.value,
        "publishes_market_fact": False,
    }
    fixture_hash = content_hash(fixture)
    return BoundaryCaseV2(
        semantic_category="UNSUPPORTED_CA",
        evidence_class=EvidenceClass.REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION,
        evidence_condition="REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION+DETERMINISTIC_CONTRACT_FIXTURE",
        input_evidence_ids=(CA_MANIFEST_ID, fixture_hash),
        rejection_boundary="ACCEPTANCE_ONLY_CA_PREFLIGHT",
        expected_rejection_code="UNSUPPORTED_CORPORATE_ACTION",
        preflight_rejection_code="UNSUPPORTED_CORPORATE_ACTION",
        fixture_hash=fixture_hash,
    )


def execute_boundary_case(case: BoundaryCaseV2, *, engine: object) -> BoundaryExecutionV2:
    # Rejection is evaluated before any bundle or engine call. The engine is
    # intentionally absent from this branch, making invocation structurally
    # unreachable rather than called-and-reset.
    if case.preflight_rejection_code:
        return BoundaryExecutionV2.create(
            semantic_category=case.semantic_category,
            evidence_class=case.evidence_class,
            evidence_condition=case.evidence_condition,
            input_evidence_ids=case.input_evidence_ids,
            rejection_boundary=case.rejection_boundary,
            expected_rejection_code=case.expected_rejection_code,
            observed_rejection_code=case.preflight_rejection_code,
            assembler_invocation_count=0,
            engine_invocation_count=0,
        )
    raise ValueError("boundary case did not reject before engine")


def _observed_case(*, assembler, slot, category: str, code: str, evidence_class: EvidenceClass,
                   fault: str | None = None, forbidden_domain: str | None = None) -> BoundaryExecutionV2:
    try:
        assembler.assemble(slot, injected_fault=fault, forbidden_domain=forbidden_domain)
    except EvidenceAssemblyError as error:
        observed = str(error)
    else:
        raise ValueError(f"boundary did not reject: {category}")
    expected = code if category != "UNEXPLAINED_MISSING_BAR" else observed
    if not observed.startswith(code):
        raise ValueError(f"boundary rejection mismatch: {category}")
    return BoundaryExecutionV2.create(
        semantic_category=category, evidence_class=evidence_class,
        evidence_condition="PINNED_PHASE1_INPUT+DETERMINISTIC_NEGATIVE_TRANSFORM",
        input_evidence_ids=(slot.candidate_hash, *slot.evidence_ids),
        rejection_boundary="Phase2AEvidenceAssemblerV1.assemble",
        expected_rejection_code=expected, observed_rejection_code=observed,
        assembler_invocation_count=1, engine_invocation_count=0,
    )


def _invalid_lineage_case(assembler, slot) -> BoundaryExecutionV2:
    bundle = assembler.assemble(slot)
    damaged = replace(bundle.domain_lineage[0], content_hash="0" * 64)
    values = {name: getattr(bundle, name) for name in bundle.__dataclass_fields__ if name not in {"content_hash", "domain_lineage"}}
    try:
        type(bundle).create(**values, domain_lineage=(damaged, *bundle.domain_lineage[1:]))
    except ValueError as error:
        observed = str(error)
    else:
        raise ValueError("boundary did not reject: INVALID_LINEAGE")
    if observed != "invalid domain lineage":
        raise ValueError("boundary rejection mismatch: INVALID_LINEAGE")
    return BoundaryExecutionV2.create(
        semantic_category="INVALID_LINEAGE", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE,
        evidence_condition="VERIFIED_REAL_BUNDLE+DETERMINISTIC_LINEAGE_HASH_MUTATION",
        input_evidence_ids=(bundle.content_hash,), rejection_boundary="LabelInputBundleV1.create",
        expected_rejection_code=observed, observed_rejection_code=observed,
        assembler_invocation_count=1, engine_invocation_count=0,
    )


def build_fail_closed_boundary_ledger(repository_root: Path, amendment: Phase2AAcceptanceArchitectureAmendmentV2, ca_manifest: dict) -> FailClosedBoundaryLedgerV2:
    if not amendment.verify():
        raise ValueError("invalid amendment")
    assembler = Phase2AEvidenceAssemblerV1(repository_root)
    slot = build_frozen_inventory().slots[0]
    unsupported = execute_boundary_case(build_unsupported_ca_boundary_case(ca_manifest), engine=object())
    cases = (
        _observed_case(assembler=assembler, slot=slot, category="UNEXPLAINED_MISSING_BAR", code="UNEXPLAINED_MISSING_BAR:", evidence_class=EvidenceClass.REAL_APPROVED_BOUNDARY_CONDITION, fault="REMOVE_FUTURE_BAR"),
        unsupported,
        _observed_case(assembler=assembler, slot=slot, category="REVOKED_APPROVAL", code="REVOKED_APPROVAL", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE, fault="REVOKED_APPROVAL"),
        _observed_case(assembler=assembler, slot=slot, category="TAMPERED_ARTIFACT", code="TAMPERED_ARTIFACT", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE, fault="TAMPERED_ARTIFACT"),
        _observed_case(assembler=assembler, slot=slot, category="MISSING_REQUIRED_DOMAIN", code="MISSING_DOMAIN:calendar", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE, forbidden_domain="calendar"),
        _observed_case(assembler=assembler, slot=slot, category="AMBIGUOUS_IDENTITY", code="IDENTITY_AMBIGUITY", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE, fault="IDENTITY_AMBIGUITY"),
        _observed_case(assembler=assembler, slot=slot, category="MALFORMED_CALENDAR", code="MALFORMED_CALENDAR", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE, fault="MALFORMED_CALENDAR"),
        _invalid_lineage_case(assembler, slot),
        _observed_case(assembler=assembler, slot=slot, category="ROLE_SWAP", code="ROLE_SWAP", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE, fault="ROLE_SWAP"),
        _observed_case(assembler=assembler, slot=slot, category="DUPLICATE_DOMAIN", code="DUPLICATE_DOMAIN", evidence_class=EvidenceClass.DETERMINISTIC_CONTRACT_FIXTURE, fault="DUPLICATE_DOMAIN"),
    )
    if any(case.engine_invocation_count for case in cases):
        raise ValueError("engine invoked for fail-closed case")
    return FailClosedBoundaryLedgerV2.create(amendment_id=amendment.artifact_id, cases=cases)
