"""An evaluation is immutable evidence only after an exact disk round trip."""

from dataclasses import replace
import json

import pytest

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.phase2b_gates import PHASE2B_GATES
from v5_2.labels.phase2b_gates_v2 import (
    GATE_V2_CONTRACT_ID, GATE_V2_EVALUATOR_ID,
    Phase2BGateEvaluationV2, Phase2BGateResultV2,
)
from v5_2.labels.phase2b_gate_evaluation_artifact import (
    read_gate_evaluation_exact, write_gate_evaluation_exact,
)


def _evaluation():
    results = tuple(Phase2BGateResultV2(
        gate, "PASS", None, (f"{index:064x}",))
        for index, gate in enumerate(PHASE2B_GATES, start=1))
    body = dict(contract_id=GATE_V2_CONTRACT_ID,
                evaluator_id=GATE_V2_EVALUATOR_ID,
                results=results, all_pass=True)
    return Phase2BGateEvaluationV2(**body, content_hash=content_hash({
        "schema_version": "Phase2BGateEvaluationV2", **body}))


def test_canonical_create_or_identical_round_trip(tmp_path):
    evaluation = _evaluation()
    assert evaluation.verify()
    path = write_gate_evaluation_exact(tmp_path, evaluation)
    first_bytes = path.read_bytes()
    first_mtime = path.stat().st_mtime_ns
    assert path.name == f"gate-evaluation-{evaluation.content_hash}.json"
    assert first_bytes == canonical_json(evaluation)
    assert read_gate_evaluation_exact(path, evaluation.content_hash) == evaluation
    assert write_gate_evaluation_exact(tmp_path, evaluation) == path
    assert path.read_bytes() == first_bytes
    assert path.stat().st_mtime_ns == first_mtime
    path.write_bytes(b"collision")
    with pytest.raises(ValueError, match="collision"):
        write_gate_evaluation_exact(tmp_path, evaluation)


@pytest.mark.parametrize("mutation", (
    "status", "failure_code", "evidence_ids", "content_hash",
    "missing_gate", "duplicate_gate", "reordered_gate", "unknown_gate",
    "contract_id", "evaluator_id", "unknown_field", "noncanonical",
))
def test_exact_reader_rejects_tampered_structure(tmp_path, mutation):
    evaluation = _evaluation()
    path = write_gate_evaluation_exact(tmp_path, evaluation)
    raw = json.loads(path.read_bytes())
    if mutation == "status":
        raw["results"][0]["status"] = "FAIL"
    elif mutation == "failure_code":
        raw["results"][0]["failure_code"] = "FORGED"
    elif mutation == "evidence_ids":
        raw["results"][0]["evidence_ids"] = ["f" * 64]
    elif mutation == "content_hash":
        raw["content_hash"] = "f" * 64
    elif mutation == "missing_gate":
        raw["results"].pop()
    elif mutation == "duplicate_gate":
        raw["results"][1]["gate"] = raw["results"][0]["gate"]
    elif mutation == "reordered_gate":
        raw["results"][0], raw["results"][1] = raw["results"][1], raw["results"][0]
    elif mutation == "unknown_gate":
        raw["results"][0]["gate"] = "UNKNOWN_GATE"
    elif mutation == "contract_id":
        raw["contract_id"] = "f" * 64
    elif mutation == "evaluator_id":
        raw["evaluator_id"] = "f" * 64
    elif mutation == "unknown_field":
        raw["results"][0]["unrecognized"] = True
    elif mutation == "noncanonical":
        path.write_bytes(path.read_bytes() + b"\n")
    if mutation != "noncanonical":
        path.write_bytes(canonical_json(raw))
    with pytest.raises(ValueError, match="identity|malformed"):
        read_gate_evaluation_exact(path, evaluation.content_hash)


def test_wrong_filename_and_rehashed_invalid_result_fail_closed(tmp_path):
    evaluation = _evaluation()
    path = write_gate_evaluation_exact(tmp_path, evaluation)
    wrong_name = path.with_name("gate-evaluation-" + "f" * 64 + ".json")
    wrong_name.write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="ID/path"):
        read_gate_evaluation_exact(wrong_name, evaluation.content_hash)

    invalid_results = (replace(evaluation.results[0], failure_code="FORGED"),
                       *evaluation.results[1:])
    body = dict(contract_id=evaluation.contract_id,
                evaluator_id=evaluation.evaluator_id,
                results=invalid_results, all_pass=True)
    rehashed = Phase2BGateEvaluationV2(**body, content_hash=content_hash({
        "schema_version": "Phase2BGateEvaluationV2", **body}))
    assert rehashed.verify()  # Existing evaluator envelope is intentionally unchanged.
    with pytest.raises(ValueError, match="result"):
        write_gate_evaluation_exact(tmp_path, rehashed)
