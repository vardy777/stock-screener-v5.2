from dataclasses import replace
import pytest

from v5_2.data.real_audits.status_prospective_sampling import (
    ProspectiveStatusCandidateV1, ProspectiveStatusEvidenceContractV1, freeze_prospective_inventory,
    ProspectiveStatusCandidateV2, ProspectiveStatusEvidenceContractV2,
    freeze_prospective_inventory_v2, is_st_exit_transition,
)


@pytest.mark.parametrize(("previous", "current", "expected"), (
    ("ST旧名", "*ST新名", False),
    ("*ST旧名", "ST新名", False),
    ("ST旧名", "普通名称", True),
    ("*ST旧名", "普通名称", True),
    ("BEST科技", "普通名称", False),
))
def test_st_exit_requires_an_actual_risk_warning_to_ordinary_transition(previous, current, expected) -> None:
    assert is_st_exit_transition(previous, current) is expected


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


def candidate_v2(index, semantic="ACTIVE_ORDINARY_STATUS"):
    exchange = "SSE" if index % 2 == 0 else "SZSE"
    return ProspectiveStatusCandidateV2.create(
        security_identity=f"{index:06d}.{'SH' if exchange == 'SSE' else 'SZ'}",
        session=f"{2010 + index % 10}0104", exchange=exchange, board="MAIN", semantic=semantic,
        provider_value="NORMAL_TRADABLE", semantic_assertion="active, tradable, non-risk-warning",
        expected_evidence="independent daily tradestatus=1,isST=0",
        effective_from="20100101", effective_to="20251231", effective_identity=True,
        confirmed_historically_tradable=True, provider_evidence_ids=(f"p{index}",))


def test_v2_contract_and_inventory_are_distinct_content_addressed_artifacts() -> None:
    contract = ProspectiveStatusEvidenceContractV2.adopted()
    pools = {semantic: tuple(candidate_v2(i, semantic) for i in range(20))
             for semantic, count in contract.sample_counts if count == 10}
    pools["IDENTITY_TRANSITION"] = (candidate_v2(99, "IDENTITY_TRANSITION"),)
    inventory = freeze_prospective_inventory_v2(contract, pools)
    assert contract.schema_version == "ProspectiveEvidenceContractV2"
    assert inventory.schema_version == "ProspectiveStatusSampleInventoryV2"
    assert inventory.contract_id == contract.contract_id
    assert len(inventory.samples) == 71
    assert all(item.effective_from <= item.session <= item.effective_to for item in inventory.samples)


def test_v2_rejects_session_outside_effective_interval_before_selection() -> None:
    bad = replace(candidate_v2(1), effective_from="20200101", effective_to="20251231")
    pool = (bad,) + tuple(candidate_v2(index) for index in range(2, 11))
    with pytest.raises(ValueError, match="effective interval"):
        freeze_prospective_inventory_v2(ProspectiveStatusEvidenceContractV2.adopted(),
                                        {"ACTIVE_ORDINARY_STATUS": pool})
