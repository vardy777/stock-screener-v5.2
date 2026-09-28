"""Checkpoint 19 tests pin preregistration, not attractive outcomes."""

from dataclasses import replace
from datetime import date
import json
import os
from pathlib import Path
import socket

import pytest

from v5_2.labels.pilot_phase2b import (
    Phase2BCandidateCensusV1, Phase2BPilotContractV1, PilotCandidateV1,
)


ROOT = Path(__file__).resolve().parents[2]


def _frozen_shape():
    candidates = (
        PilotCandidateV1("000001.SZ", "000001.SZ", date(2010, 1, 4),
                         ("EXCLUDED_BEFORE_LABEL",), ("a" * 64,)),
        PilotCandidateV1("000001.SZ", "000001.SZ", date(2010, 1, 8),
                         ("ORDINARY_CONTROL",), ("a" * 64,)),
        PilotCandidateV1("000004.SZ", "000004.SZ", date(2010, 1, 8),
                         ("FULL_DAY_SUSPENSION", "NOT_LABEL_SAFE"), ("a" * 64,)),
        PilotCandidateV1("600495.SH", "600495.SH", date(2010, 1, 8),
                         ("SUPPORTED_CASH_DIVIDEND",), ("a" * 64,)),
    )
    census = Phase2BCandidateCensusV1.create(
        window_start=date(2010, 1, 4), window_end=date(2010, 1, 29),
        candidates=candidates, coverage_evidence_id="b" * 64,
        source_candidate_set_hash="c" * 64,
        source_approval_ids=("1" * 64, "2" * 64, "3" * 64,
                             "4" * 64, "5" * 64))
    contract = Phase2BPilotContractV1.create(
        census=census, five_domain_authority_ids=census.source_approval_ids,
        private_corpus_manifest_id="d" * 64, cas_inventory_hash="e" * 64,
        phase2a_semantic_authority_id="f" * 64,
        maturation_authority_id="0" * 64, gate_contract_id="a" * 64,
        gate_evaluator_id="b" * 64)
    return census, contract


def test_selected_candidates_cannot_be_reordered_or_substituted():
    from v5_2.labels.phase2b_checkpoint19_pilot import selected_candidates_exact
    census, contract = _frozen_shape()
    selected = selected_candidates_exact(census, contract)
    assert tuple(item.candidate_id for item in selected) == contract.selected_candidate_ids
    assert len(selected) == 4
    with pytest.raises(ValueError):
        selected_candidates_exact(census, replace(
            contract, selected_candidate_ids=tuple(reversed(contract.selected_candidate_ids))))
    with pytest.raises(ValueError):
        selected_candidates_exact(census, replace(
            contract, window_end=date(2010, 2, 1)))
    with pytest.raises(ValueError):
        selected_candidates_exact(census, replace(
            contract, five_domain_authority_ids=("9" * 64,) * 5))


def test_runner_network_boundary_denies_connection_and_send_attempts(monkeypatch):
    from v5_2.labels.phase2b_checkpoint19_pilot import _deny_network_for_pilot
    monkeypatch.setattr(socket.socket, "sendto", lambda *_args, **_kwargs: 1)
    with _deny_network_for_pilot() as attempts:
        with pytest.raises(ValueError, match="network request blocked"):
            socket.socket().connect(("127.0.0.1", 1))
        with pytest.raises(ValueError, match="network request blocked"):
            socket.socket().connect_ex(("127.0.0.1", 1))
        with pytest.raises(ValueError, match="network request blocked"):
            socket.create_connection(("127.0.0.1", 1))
        with pytest.raises(ValueError, match="network request blocked"):
            socket.socket(type=socket.SOCK_DGRAM).sendto(b"x", ("127.0.0.1", 1))
    assert attempts.count == 4


def test_exclusion_requires_independent_reason_and_evidence():
    from types import SimpleNamespace
    from v5_2.labels.phase2b_checkpoint19_pilot import _independent_ipo_exclusion
    from v5_2.labels.anchor_enumerator import AnchorDispositionKind, AnchorDispositionV1
    from v5_2.refresh.eligibility import IPO_SEASONING_SESSIONS
    listing = date(2010, 1, 4)
    anchor = AnchorDispositionV1("000001.SZ", "000001.SZ", listing, "SZSE",
                                 True, False, AnchorDispositionKind.EXCLUDED_BEFORE_LABEL,
                                 "IPO_SEASONING")
    master = SimpleNamespace(resolve=lambda *_: SimpleNamespace(
        effective_identity="000001.SZ", interval=SimpleNamespace(effective_from=listing),
        fact_id="a" * 64, approval_id="b" * 64))
    calendar = SimpleNamespace(sessions=lambda *_: tuple(date(2010, 1, day)
                                                  for day in (4, 5, 6, 7, 8, 11, 12)))
    producer = SimpleNamespace(master=master, calendar=calendar)
    evidence_id = _independent_ipo_exclusion(producer, anchor)
    assert len(evidence_id) == 64
    assert IPO_SEASONING_SESSIONS == 5
    with pytest.raises(ValueError, match="independent exclusion mismatch"):
        _independent_ipo_exclusion(producer, replace(anchor, reason="STATUS_UNRESOLVED"))


@pytest.mark.skipif(os.environ.get("V52_CHECKPOINT19_PILOT") != "1",
                    reason="explicit exact private-CAS pilot run required")
def test_real_four_candidate_pilot_replays_and_preserves_frozen_selection(tmp_path, monkeypatch):
    from v5_2.labels.phase2b_checkpoint19_pilot import (
        read_pilot_result_exact, run_checkpoint19_exact,
    )
    def deny_network(*_args, **_kwargs):
        raise AssertionError("Checkpoint 19 attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    first = run_checkpoint19_exact(ROOT, output_root=tmp_path)
    second = run_checkpoint19_exact(ROOT, output_root=tmp_path)
    assert first == second
    assert len(first.cases) == 4
    assert first.selected_candidate_ids == (
        "443ffe4cb83036f1748cf584c3b1f915a86daed7995fb6b67a4b7db016aab7f7",
        "7f01a8a52ad98e61917fd582a2c7c59d4e861b9e71139bbd0d32917c43e51994",
        "b5bfb5faf06abbc6c6c446891eb6667d3d7dcccf16d557eb1ac6af21618b888c",
        "70e76ff1db527bcb5415fed647a6e09d4eb5939c05fdba019da379d89d043cae",
    )
    assert all(case.match for case in first.cases)
    assert first.cases[1].state == "EXCLUDED_BEFORE_LABEL"
    assert first.cases[1].independent_result_id is not None
    assert first.cases[1].comparison_id is not None
    assert first.cases[1].bundle_id is None
    assert not replace(first.cases[1], independent_result_id=None).verify()
    assert first.provider_request_count == 0
    assert first.verify()
    census, contract = _read_real_prereg()
    path = tmp_path / "pilot_results" / f"pilot-result-{first.pilot_result_id}.json"
    assert read_pilot_result_exact(path, first.pilot_result_id, contract) == first
    original = path.read_bytes()
    changed = json.loads(original)
    changed["selected_candidate_ids"] = list(reversed(changed["selected_candidate_ids"]))
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError):
        read_pilot_result_exact(path, first.pilot_result_id, contract)


def _read_real_prereg():
    from v5_2.labels.pilot_phase2b import (
        read_candidate_census_exact, read_pilot_contract_exact,
    )
    pre = ROOT / "data/phase_2b_checkpoint18_real_month/pilot_prereg"
    cid = "1a1f2465a2d60e84f61874feccf6538c1c1daec3f69369600255d78379285a8d"
    pid = "5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc"
    census = read_candidate_census_exact(pre / f"census-{cid}.json", cid)
    contract = read_pilot_contract_exact(pre / f"pilot-{pid}.json", pid, census)
    return census, contract
