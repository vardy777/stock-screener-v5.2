from dataclasses import replace

import pytest

from v5_2.labels.acceptance_v2_contracts import (
    CalculationEdgeFixtureLedgerV2,
    EvidenceClass,
    RealReferenceCaseV2,
    RealReferenceCoverageLedgerV2,
    build_frozen_amendment_v2,
)
from v5_2.labels.acceptance_v2_layer_c import build_edge_fixture_ledger, build_frozen_edge_fixtures


H = "a" * 64


def real_case(evidence_class=EvidenceClass.REAL_MARKET_EVIDENCE):
    return RealReferenceCaseV2.create(
        slot=1, evidence_class=evidence_class, bundle_id=H,
        five_domain_lineage_ids=tuple(chr(98 + i) * 64 for i in range(5)),
        production_result_id="g" * 64, independent_result_id="h" * 64,
        comparison_id="i" * 64, semantic_roles=("NORMAL",), disposition="MATCH",
    )


def test_synthetic_cannot_enter_layer_a_or_increment_real_counts():
    with pytest.raises(ValueError, match="REAL_MARKET_EVIDENCE"):
        RealReferenceCoverageLedgerV2.create(
            amendment_id=H, checkpoint7_comparison_ledger_id="b" * 64,
            cases=(real_case(EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE),),
        )
    ledger = RealReferenceCoverageLedgerV2.create(
        amendment_id=H, checkpoint7_comparison_ledger_id="b" * 64, cases=(real_case(),),
    )
    assert ledger.real_reference_cases == 1
    assert not hasattr(ledger, "total_samples")


def test_layer_c_requires_synthetic_class_and_cannot_claim_phase1_lineage():
    amendment = build_frozen_amendment_v2()
    fixtures = build_frozen_edge_fixtures(amendment)
    ledger = build_edge_fixture_ledger(amendment, fixtures)
    assert ledger.synthetic_contract_fixtures == 4
    bad = replace(fixtures[0], evidence_class=EvidenceClass.REAL_MARKET_EVIDENCE)
    with pytest.raises(ValueError, match="SYNTHETIC_CONTRACT_FIXTURE"):
        CalculationEdgeFixtureLedgerV2.create(
            amendment_id=amendment.artifact_id,
            fixtures=(bad, *fixtures[1:]), comparisons=ledger.comparisons,
        )
    assert all(not hasattr(x, "phase1_lineage") for x in fixtures)
