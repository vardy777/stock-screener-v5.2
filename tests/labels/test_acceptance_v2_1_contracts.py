from dataclasses import replace

import pytest

from v5_2.labels.acceptance_v2_contracts import (
    BoundaryEvidenceProvenanceV2_1,
    BoundaryExecutionV2_1,
    EvidenceClass,
    Phase2AAcceptanceArchitectureAmendmentV2_1,
    build_frozen_amendment_v2,
    build_frozen_amendment_v2_1,
)


H = "a" * 64
CHECKPOINT8_DISCOVERY_ID = "947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48"


def test_missing_bar_requires_real_base_plus_non_real_fixture():
    value = BoundaryEvidenceProvenanceV2_1.create(
        base_evidence_class="REAL_MARKET_EVIDENCE",
        boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
        real_condition_observed=False,
        real_condition_availability="REAL_REFERENCE_SAMPLE_UNAVAILABLE",
        unavailability_evidence_id=CHECKPOINT8_DISCOVERY_ID,
    )
    assert value.verify()


def test_fixture_cannot_claim_real_observed_condition():
    with pytest.raises(ValueError, match="fixture cannot be real observed"):
        BoundaryEvidenceProvenanceV2_1.create(
            base_evidence_class="REAL_MARKET_EVIDENCE",
            boundary_exercise_class="DETERMINISTIC_CONTRACT_FIXTURE",
            real_condition_observed=True,
            real_condition_availability="OBSERVED",
            unavailability_evidence_id=None,
        )


def test_real_unsupported_event_requires_observed_true():
    with pytest.raises(ValueError, match="unsupported market event must be observed"):
        BoundaryEvidenceProvenanceV2_1.create(
            base_evidence_class="REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE",
            boundary_exercise_class="REAL_UNSUPPORTED_MARKET_EVENT",
            real_condition_observed=False,
            real_condition_availability="OBSERVED",
            unavailability_evidence_id=None,
        )


def test_pure_calculation_fixture_cannot_enter_layer_b_execution():
    provenance = BoundaryEvidenceProvenanceV2_1.create(
        base_evidence_class="NONE",
        boundary_exercise_class="PURE_SYNTHETIC_CALCULATION_FIXTURE",
        real_condition_observed=False,
        real_condition_availability="NOT_APPLICABLE",
        unavailability_evidence_id=None,
    )
    with pytest.raises(ValueError, match="calculation fixture cannot enter Layer B"):
        BoundaryExecutionV2_1.create(
            semantic_category="UNEXPLAINED_MISSING_BAR",
            provenance=provenance,
            input_evidence_ids=(H,),
            real_base_bundle_id=H,
            real_base_lineage_ids=tuple(chr(98 + i) * 64 for i in range(5)),
            transform_id=H,
            transformed_evidence_id=H,
            removed_session="2024-01-03",
            rejection_boundary="Phase2AEvidenceAssemblerV1.assemble",
            expected_rejection_code="UNEXPLAINED_MISSING_BAR:2024-01-03",
            observed_rejection_code="UNEXPLAINED_MISSING_BAR:2024-01-03",
            assembler_invocation_count=1,
            engine_invocation_count=0,
        )


def test_frozen_v2_1_amendment_pins_all_authorities_and_v2_is_unchanged():
    old = build_frozen_amendment_v2()
    result = build_frozen_amendment_v2_1()
    assert result.verify()
    assert result.original_v2_design_commit == "f92f0a564c802ddc28dc71153be44d409b6858ee"
    assert result.original_v2_plan_commit == "4db0f4ecb9e61853190f755d1bee164d9f84fe9a"
    assert result.plan_correction_commit == "390149882f3265b778b736a16380c13d9a64652a"
    assert result.v2_1_design_amendment_id == "d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b"
    assert result.v2_1_design_head == "a66825e25d40a46eceae18a50f1f2535ab9ee975"
    assert result.supersedes_attempt1_amendment_id == old.artifact_id
    assert build_frozen_amendment_v2() == old
    assert not replace(result, content_hash="0" * 64).verify()
