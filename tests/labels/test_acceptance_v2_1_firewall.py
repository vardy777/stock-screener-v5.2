from dataclasses import fields

import pytest

from v5_2.labels.acceptance_v2_contracts import (
    BoundaryEvidenceProvenanceV2_1,
    BoundaryExecutionV2_1,
    EvidenceClass,
    RealReferenceCaseV2,
)
from v5_2.labels.acceptance_v2_layer_a import RealReferenceCoverageLedgerV2_1
from v5_2.labels.acceptance_v2_layer_c import CalculationEdgeFixtureLedgerV2_1


H = "a" * 64
IDS = tuple(chr(ord("b") + index) * 64 for index in range(5))


def test_missing_bar_fixture_cannot_claim_real_observation():
    with pytest.raises(ValueError, match="fixture cannot be real observed"):
        BoundaryEvidenceProvenanceV2_1.create(
            base_evidence_class="REAL_MARKET_EVIDENCE",
            boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
            real_condition_observed=True,
            real_condition_availability="OBSERVED",
            unavailability_evidence_id=None,
        )


def test_real_base_plus_mutation_cannot_promote_to_real_boundary_class():
    with pytest.raises(ValueError, match="invalid V2.1 provenance class"):
        BoundaryEvidenceProvenanceV2_1.create(
            base_evidence_class="REAL_APPROVED_BOUNDARY_CONDITION",
            boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
            real_condition_observed=False,
            real_condition_availability="REAL_REFERENCE_SAMPLE_UNAVAILABLE",
            unavailability_evidence_id=H,
        )


def test_pure_calculation_fixture_cannot_enter_real_market_ledger():
    with pytest.raises(ValueError, match="REAL_MARKET_EVIDENCE"):
        case = RealReferenceCaseV2.create(
            slot=1,
            evidence_class=EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE,
            bundle_id=H,
            five_domain_lineage_ids=IDS,
            production_result_id="g" * 64,
            independent_result_id="h" * 64,
            comparison_id="i" * 64,
            semantic_roles=("NORMAL_POSITIVE_RETURN",),
            disposition="MATCH",
        )


def test_real_unsupported_event_cannot_use_synthetic_classification():
    with pytest.raises(ValueError, match="fixture cannot be real observed"):
        BoundaryEvidenceProvenanceV2_1.create(
            base_evidence_class="REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE",
            boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
            real_condition_observed=True,
            real_condition_availability="OBSERVED",
            unavailability_evidence_id=None,
        )


def test_acceptance_only_preflight_cannot_claim_authoritative_unsupported_coverage():
    provenance = BoundaryEvidenceProvenanceV2_1.create(
        base_evidence_class="REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE",
        boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
        real_condition_observed=False,
        real_condition_availability="REAL_REFERENCE_SAMPLE_UNAVAILABLE",
        unavailability_evidence_id=H,
    )
    with pytest.raises(ValueError, match="real unsupported event required"):
        BoundaryExecutionV2_1.create(
            semantic_category="UNSUPPORTED_CA",
            provenance=provenance,
            input_evidence_ids=(H,),
            real_base_bundle_id=None,
            real_base_lineage_ids=(),
            transform_id=None,
            transformed_evidence_id=None,
            removed_session=None,
            rejection_boundary="ACCEPTANCE_ONLY_CA_PREFLIGHT",
            expected_rejection_code="NOT_RESEARCH_SAFE: unsupported action type",
            observed_rejection_code="NOT_RESEARCH_SAFE: unsupported action type",
            assembler_invocation_count=0,
            engine_invocation_count=0,
            observed_condition=None,
        )


def test_v2_1_ledgers_expose_no_total_samples_aggregate():
    for schema in (RealReferenceCoverageLedgerV2_1, CalculationEdgeFixtureLedgerV2_1):
        assert "total_samples" not in {field.name for field in fields(schema)}
