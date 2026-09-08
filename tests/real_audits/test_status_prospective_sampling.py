from dataclasses import replace
import pytest

from v5_2.data.real_audits.status_prospective_sampling import (
    ProspectiveStatusCandidateV1, ProspectiveStatusEvidenceContractV1, freeze_prospective_inventory,
)


def candidate(index, semantic="ACTIVE_ORDINARY_STATUS"):
    exchange = "SSE" if index % 2 == 0 else "SZSE"
    return ProspectiveStatusCandidateV1.create(security_identity=f"{index:06d}.{'SH' if exchange == 'SSE' else 'SZ'}",
        session=f"{2010 + index % 10}0104", exchange=exchange, board="MAIN", semantic=semantic,
        provider_value="NORMAL_TRADABLE", semantic_assertion="active, tradable, non-risk-warning",
        expected_evidence="independent daily tradestatus=1,isST=0", effective_identity=True,
        confirmed_historically_tradable=True, provider_evidence_ids=(f"p{index}",))


def test_contract_is_content_addressed_and_inventory_is_frozen_before_results() -> None:
    contract = ProspectiveStatusEvidenceContractV1.adopted()
    pools = {semantic: tuple(candidate(i, semantic) for i in range(20)) for semantic, count in contract.sample_counts if count == 10}
    pools["IDENTITY_TRANSITION"] = (candidate(99, "IDENTITY_TRANSITION"),)
    inventory = freeze_prospective_inventory(contract, pools)
    assert len(inventory.samples) == 71
    assert inventory.contract_id == contract.contract_id
    assert all(item.provider_value and item.semantic_assertion and item.expected_evidence for item in inventory.samples)


def test_inapplicable_or_non_tradable_candidate_is_rejected_before_selection() -> None:
    bad = replace(candidate(1), effective_identity=False)
    with pytest.raises(ValueError, match="applicable"):
        freeze_prospective_inventory(ProspectiveStatusEvidenceContractV1.adopted(), {"ACTIVE_ORDINARY_STATUS": (bad,)})
