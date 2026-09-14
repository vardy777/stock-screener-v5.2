from dataclasses import replace

import pytest

from v5_2.labels.acceptance import ACCEPTANCE_GATES, Phase2AAcceptanceArtifactV1, build_comparison_ledger, build_frozen_inventory, IndependentLabelCalculationV1, render_acceptance_report


def statuses(value="PASS"):
    return tuple((name, value) for name in ACCEPTANCE_GATES)


def unavailable_ledger():
    inventory = build_frozen_inventory()
    calculations = tuple(IndependentLabelCalculationV1.create(slot=s.slot, inventory_evidence_id=s.evidence_ids[0], status="EVIDENCE_UNAVAILABLE", horizons=(), inputs_hash=None, result_summary=(), method_version="phase2a-independent-v1", reason="EXACT_FIVE_DOMAIN_BUNDLE_NOT_YET_ASSEMBLED") for s in inventory.slots)
    return build_comparison_ledger(calculations, {})


def test_acceptance_requires_exact_16_gates():
    with pytest.raises(ValueError): Phase2AAcceptanceArtifactV1.create(statuses=statuses()[:-1], evidence_ids=("a"*64,))


def test_any_nonpass_gate_blocks_phase2b():
    values = list(statuses()); values[13] = (values[13][0], "PENDING")
    result = Phase2AAcceptanceArtifactV1.create(statuses=tuple(values), evidence_ids=("a"*64,))
    assert result.ready_for_phase_2b is False and result.phase_2a_status == "PENDING"


def test_all_pass_is_ready_and_deterministic():
    first = Phase2AAcceptanceArtifactV1.create(statuses=statuses(), evidence_ids=("a"*64,))
    second = Phase2AAcceptanceArtifactV1.create(statuses=statuses(), evidence_ids=("a"*64,))
    assert first.ready_for_phase_2b and first.acceptance_id == second.acceptance_id and first.verify()


def test_report_contains_all_22_rows_and_unavailable_blocks():
    inventory = build_frozen_inventory(); ledger = unavailable_ledger()
    values = list(statuses()); values[13] = ("REFERENCE SAMPLES", "PENDING"); values[14] = ("INDEPENDENT VERIFICATION", "PENDING")
    acceptance = Phase2AAcceptanceArtifactV1.create(statuses=tuple(values), evidence_ids=(inventory.inventory_id, ledger.ledger_id))
    report = render_acceptance_report(inventory, ledger, acceptance)
    assert report.count("| 0") >= 9 and report.count("EVIDENCE_UNAVAILABLE") >= 22
    assert "READY FOR PHASE 2B = NO" in report and "REFERENCE SAMPLES = PENDING" in report
    for phrase in ("cash dividend", "bonus share", "suspension", "resumption", "IPO", "delisting", "identity transition", "missing", "unsupported", "LABEL_PENDING", "double-barrier"):
        assert phrase in report


def test_tampered_acceptance_fails_verification():
    item = Phase2AAcceptanceArtifactV1.create(statuses=statuses(), evidence_ids=("a"*64,))
    assert not replace(item, phase_2a_status="PENDING").verify()
