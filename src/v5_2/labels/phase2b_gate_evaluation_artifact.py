"""Exact persistence for the existing formal Phase 2B Gate V2 result."""

from __future__ import annotations

import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json
from v5_2.labels.phase2b_gates import PHASE2B_GATES
from v5_2.labels.phase2b_gates_v2 import (
    Phase2BGateEvaluationV2, Phase2BGateResultV2,
)


_ID = re.compile(r"^[0-9a-f]{64}$")
_EVALUATION_FIELDS = {"contract_id", "evaluator_id", "results", "all_pass",
                      "content_hash"}
_RESULT_FIELDS = {"gate", "status", "failure_code", "evidence_ids"}


def _valid(evaluation: Phase2BGateEvaluationV2) -> bool:
    if not isinstance(evaluation, Phase2BGateEvaluationV2):
        return False
    if (type(evaluation.all_pass) is not bool
            or type(evaluation.results) is not tuple
            or len(evaluation.results) != 18
            or tuple(item.gate for item in evaluation.results) != PHASE2B_GATES):
        return False
    for item in evaluation.results:
        if (not isinstance(item, Phase2BGateResultV2)
                or type(item.gate) is not str
                or type(item.status) is not str
                or item.status not in {"PASS", "FAIL"}
                or type(item.evidence_ids) is not tuple
                or not all(type(value) is str and _ID.fullmatch(value)
                           for value in item.evidence_ids)):
            return False
        if item.status == "PASS":
            if item.failure_code is not None or not item.evidence_ids:
                return False
        elif (type(item.failure_code) is not str
              or not item.failure_code.endswith("_FORMAL_EVIDENCE_MISSING")
              or item.evidence_ids):
            return False
    return evaluation.verify()


def write_gate_evaluation_exact(root: Path,
                                evaluation: Phase2BGateEvaluationV2) -> Path:
    if not _valid(evaluation):
        raise ValueError("verified formal gate evaluation result required")
    path = (root / "gate_evidence"
            / f"gate-evaluation-{evaluation.content_hash}.json")
    payload = canonical_json(evaluation)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as target:
            target.write(payload)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ValueError("immutable gate evaluation collision") from None
    return path


def read_gate_evaluation_exact(path: Path,
                               expected_id: str) -> Phase2BGateEvaluationV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"gate-evaluation-{expected_id}.json"):
        raise ValueError("gate evaluation ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        if type(values) is not dict or set(values) != _EVALUATION_FIELDS:
            raise ValueError("evaluation field structure malformed")
        items = values["results"]
        if type(items) is not list or len(items) != 18:
            raise ValueError("evaluation results malformed")
        results = []
        for item in items:
            if type(item) is not dict or set(item) != _RESULT_FIELDS:
                raise ValueError("evaluation result fields malformed")
            if type(item["evidence_ids"]) is not list:
                raise ValueError("evaluation evidence IDs malformed")
            results.append(Phase2BGateResultV2(
                item["gate"], item["status"], item["failure_code"],
                tuple(item["evidence_ids"])))
        evaluation = Phase2BGateEvaluationV2(
            values["contract_id"], values["evaluator_id"], tuple(results),
            values["all_pass"], values["content_hash"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("gate evaluation unavailable or malformed") from error
    if (evaluation.content_hash != expected_id or not _valid(evaluation)
            or canonical_json(evaluation) != raw):
        raise ValueError("gate evaluation identity mismatch")
    return evaluation
