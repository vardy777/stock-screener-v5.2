"""Checkpoint 18 preregistration only; no pilot calculation is invoked."""

from dataclasses import replace
from datetime import date
import os
from pathlib import Path

import pytest

from v5_2.labels.pilot_phase2b import (
    PILOT_STRATA, Phase2BCandidateCensusV1, Phase2BPilotContractV1,
    PilotCandidateV1, derive_source_pinned_candidate_census_exact,
    derive_real_pilot_preregistration_exact,
    read_candidate_census_exact, read_pilot_contract_exact,
    write_candidate_census_exact, write_pilot_contract_exact,
)


PINS = tuple(str(number) * 64 for number in range(1, 6))


def _candidate(identity, day, strata):
    return PilotCandidateV1(identity, identity, date.fromisoformat(day),
                            strata, ("a" * 64,))


def _census():
    return Phase2BCandidateCensusV1.create(
        window_start=date(2010, 1, 4), window_end=date(2010, 1, 8),
        candidates=(
            _candidate("000001.SZ", "2010-01-04", ("ORDINARY_CONTROL",)),
            _candidate("000002.SZ", "2010-01-05", ("SUPPORTED_CASH_DIVIDEND",)),
            _candidate("000003.SZ", "2010-01-06", ("ORDINARY_CONTROL",)),
        ),
        coverage_evidence_id="b" * 64, source_candidate_set_hash="c" * 64,
        source_approval_ids=PINS)


def _contract(census):
    return Phase2BPilotContractV1.create(
        census=census, five_domain_authority_ids=PINS,
        private_corpus_manifest_id="d" * 64, cas_inventory_hash="e" * 64,
        phase2a_semantic_authority_id="f" * 64,
        maturation_authority_id="0" * 64,
        gate_contract_id="a" * 64, gate_evaluator_id="b" * 64)


def test_preregistration_selects_from_pinned_candidates_without_results():
    census = _census()
    contract = _contract(census)
    assert census.verify()
    assert contract.verify(census)
    assert contract.selection_rule == "FIRST_SOURCE_ORDERED_CANDIDATE_PER_STRATUM_V1"
    assert contract.selected_candidate_ids == (
        census.candidates[0].candidate_id, census.candidates[1].candidate_id)
    assert contract.anchor_sessions == (date(2010, 1, 4), date(2010, 1, 5))
    assert contract.absent_strata == tuple(
        item for item in PILOT_STRATA
        if item not in ("ORDINARY_CONTROL", "SUPPORTED_CASH_DIVIDEND"))
    assert not hasattr(contract, "pilot_results")


def test_candidate_reordering_or_missing_pins_fails_closed():
    census = _census()
    with pytest.raises(ValueError, match="canonical"):
        Phase2BCandidateCensusV1.create(
            window_start=census.window_start, window_end=census.window_end,
            candidates=tuple(reversed(census.candidates)),
            coverage_evidence_id=census.coverage_evidence_id,
            source_candidate_set_hash=census.source_candidate_set_hash,
            source_approval_ids=PINS)
    with pytest.raises(ValueError, match="five-domain"):
        Phase2BPilotContractV1.create(
            census=census, five_domain_authority_ids=PINS[:-1],
            private_corpus_manifest_id="d" * 64, cas_inventory_hash="e" * 64,
            phase2a_semantic_authority_id="f" * 64,
            maturation_authority_id="0" * 64,
            gate_contract_id="a" * 64, gate_evaluator_id="b" * 64)


def test_post_result_selection_change_invalidates_preregistration():
    census = _census()
    contract = _contract(census)
    changed = replace(contract, selected_candidate_ids=(census.candidates[2].candidate_id,))
    assert not changed.verify(census)
    assert _contract(census).contract_id == contract.contract_id


def test_census_and_preregistration_are_immutable_exact_artifacts(tmp_path):
    census = _census()
    contract = _contract(census)
    census_path = write_candidate_census_exact(tmp_path, census)
    contract_path = write_pilot_contract_exact(tmp_path, contract, census)
    assert write_candidate_census_exact(tmp_path, census) == census_path
    assert write_pilot_contract_exact(tmp_path, contract, census) == contract_path
    assert read_candidate_census_exact(census_path, census.census_id) == census
    assert read_pilot_contract_exact(contract_path, contract.contract_id, census) == contract
    contract_path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="identity"):
        read_pilot_contract_exact(contract_path, contract.contract_id, census)
    with pytest.raises(ValueError, match="collision"):
        write_pilot_contract_exact(tmp_path, contract, census)


@pytest.mark.skipif(os.environ.get("V52_REAL_PILOT_CENSUS") != "1",
                    reason="explicit approved-source census run required")
def test_real_census_reconstructs_frozen_month_candidates_without_label_outcomes(tmp_path):
    root = Path(__file__).resolve().parents[2]
    coverage_id = "834534a947d79b10a16404ae35430aafb63b36e0ac467d46b97a57117959ef75"
    path = (root / "data/phase_2b_checkpoint18_real_month/gate_evidence"
            / f"month-coverage-{coverage_id}.json")
    census = derive_source_pinned_candidate_census_exact(root, path, coverage_id)
    assert census.verify()
    assert census.source_candidate_set_hash == (
        "76ed7e266c91e0dcef1326555b3c1fae08d47e0530c4a97f7fd381292f655770")
    assert len(census.candidates) > 30_000
    assert all(not hasattr(candidate, "label_result") for candidate in census.candidates)
    contract = derive_real_pilot_preregistration_exact(root, census)
    assert contract.verify(census)
    assert contract.candidate_census_id == census.census_id
    census_path = write_candidate_census_exact(tmp_path, census)
    contract_path = write_pilot_contract_exact(tmp_path, contract, census)
    assert read_candidate_census_exact(census_path, census.census_id) == census
    assert read_pilot_contract_exact(contract_path, contract.contract_id, census) == contract
