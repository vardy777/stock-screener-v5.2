"""The public capsule binds, but never substitutes for, private exact evidence."""

from dataclasses import replace
import json

import pytest

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.phase2b_gate_evaluation_artifact import write_gate_evaluation_exact
from v5_2.labels.phase2b_gates import PHASE2B_GATES
from v5_2.labels.phase2b_gates_v2 import (
    GATE_V2_CONTRACT_ID, GATE_V2_EVALUATOR_ID,
    Phase2BGateEvaluationV2, Phase2BGateResultV2,
)
from v5_2.labels.phase2b_checkpoint18_acceptance import (
    create_checkpoint18_acceptance_exact,
    read_checkpoint18_acceptance_exact,
    write_checkpoint18_acceptance_exact,
)


PINS = {
    "evaluated_code_commit": "a" * 40,
    "evaluated_code_tree": "b" * 40,
    "private_corpus_manifest_id": "1" * 64,
    "private_cas_inventory_hash": "2" * 64,
    "cleanroom_receipt_id": "3" * 64,
    "partition_id": "4" * 64,
    "coverage_id": "5" * 64,
    "scoped_ledger_id": "6" * 64,
    "integration_id": "7" * 64,
    "row_comparison_id": "8" * 64,
    "replay_id": "9" * 64,
    "incremental_id": "a" * 64,
    "candidate_census_id": "b" * 64,
    "task12_preregistration_id": "c" * 64,
    "mutation_ledger_sha256": "d" * 64,
    "pilot_executed": False,
    "checkpoint19_started": False,
    "phase3_started": False,
    "known_historical_public_exposure": True,
    "current_public_refs_clean": True,
}


def _evaluation():
    results = tuple(Phase2BGateResultV2(gate, "PASS", None, ("e" * 64,))
                    for gate in PHASE2B_GATES)
    body = dict(contract_id=GATE_V2_CONTRACT_ID,
                evaluator_id=GATE_V2_EVALUATOR_ID,
                results=results, all_pass=True)
    return Phase2BGateEvaluationV2(**body, content_hash=content_hash({
        "schema_version": "Phase2BGateEvaluationV2", **body}))


def _capsule(tmp_path):
    evaluation = _evaluation()
    path = write_gate_evaluation_exact(tmp_path, evaluation)
    return create_checkpoint18_acceptance_exact(path, evaluation.content_hash,
                                                 **PINS)


def test_capsule_reads_exact_persisted_gate_result_and_round_trips(tmp_path):
    capsule = _capsule(tmp_path)
    assert capsule.verify()
    assert capsule.gate_evaluation_id == _evaluation().content_hash
    assert len(capsule.gate_results) == 18
    path = write_checkpoint18_acceptance_exact(tmp_path, capsule)
    original = path.read_bytes()
    assert write_checkpoint18_acceptance_exact(tmp_path, capsule) == path
    assert path.read_bytes() == original
    assert read_checkpoint18_acceptance_exact(path, capsule.content_hash) == capsule
    assert b"private-cas" not in original


@pytest.mark.parametrize("change", [
    {"gate_evaluation_id": "f" * 64},
    {"gate_results": ()},
    {"pilot_executed": True},
    {"current_public_refs_clean": False},
    {"private_cas_inventory_hash": "not-a-hash"},
])
def test_capsule_rejects_invalid_content_or_boundary(tmp_path, change):
    capsule = _capsule(tmp_path)
    assert not replace(capsule, **change).verify()


def test_capsule_reader_rejects_tamper_filename_and_noncanonical_json(tmp_path):
    capsule = _capsule(tmp_path)
    path = write_checkpoint18_acceptance_exact(tmp_path, capsule)
    with pytest.raises(ValueError):
        read_checkpoint18_acceptance_exact(path, "f" * 64)
    for mutate in (
        lambda value: value.update(gate_evaluation_id="f" * 64),
        lambda value: value.update(extra="bad"),
        lambda value: value["gate_results"][0].update(status="FAIL"),
    ):
        value = json.loads(canonical_json(capsule))
        mutate(value)
        path.write_bytes(canonical_json(value))
        with pytest.raises(ValueError):
            read_checkpoint18_acceptance_exact(path, capsule.content_hash)
    path.write_bytes(json.dumps(json.loads(canonical_json(capsule)),
                                indent=2).encode())
    with pytest.raises(ValueError):
        read_checkpoint18_acceptance_exact(path, capsule.content_hash)
