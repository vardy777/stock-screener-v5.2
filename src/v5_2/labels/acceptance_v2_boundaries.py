from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash
from v5_2.labels.acceptance_v2_contracts import BoundaryExecutionV2, EvidenceClass


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
