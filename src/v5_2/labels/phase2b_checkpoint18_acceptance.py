"""Public, hash-only Checkpoint 18 capsule for an exact private Gate V2 result.

This is a record of evaluation, not a second gate evaluator. In particular it
never infers a gate result from a report, a latest-file lookup, or corpus bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.phase2b_gate_evaluation_artifact import read_gate_evaluation_exact
from v5_2.labels.phase2b_gates_v2 import (
    GATE_V2_CONTRACT_ID, GATE_V2_EVALUATOR_ID,
    Phase2BGateEvaluationV2, Phase2BGateResultV2,
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RESULT_FIELDS = {"gate", "status", "failure_code", "evidence_ids"}


@dataclass(frozen=True, slots=True)
class Phase2BCheckpoint18AcceptanceV1:
    evaluated_code_commit: str
    evaluated_code_tree: str
    gate_v2_contract_id: str
    gate_v2_evaluator_id: str
    gate_evaluation_id: str
    gate_results: tuple[Phase2BGateResultV2, ...]
    private_corpus_manifest_id: str
    private_cas_inventory_hash: str
    cleanroom_receipt_id: str
    partition_id: str
    coverage_id: str
    scoped_ledger_id: str
    integration_id: str
    row_comparison_id: str
    replay_id: str
    incremental_id: str
    candidate_census_id: str
    task12_preregistration_id: str
    mutation_ledger_sha256: str
    pilot_executed: bool
    checkpoint19_started: bool
    phase3_started: bool
    known_historical_public_exposure: bool
    current_public_refs_clean: bool
    content_hash: str

    def verify(self) -> bool:
        try:
            if (type(self.evaluated_code_commit) is not str
                    or not _COMMIT.fullmatch(self.evaluated_code_commit)
                    or type(self.evaluated_code_tree) is not str
                    or not _COMMIT.fullmatch(self.evaluated_code_tree)
                    or self.gate_v2_contract_id != GATE_V2_CONTRACT_ID
                    or self.gate_v2_evaluator_id != GATE_V2_EVALUATOR_ID
                    or type(self.gate_results) is not tuple):
                return False
            for name in (
                "gate_evaluation_id", "private_corpus_manifest_id",
                "private_cas_inventory_hash", "cleanroom_receipt_id",
                "partition_id", "coverage_id", "scoped_ledger_id",
                "integration_id", "row_comparison_id", "replay_id",
                "incremental_id", "candidate_census_id",
                "task12_preregistration_id", "mutation_ledger_sha256",
                "content_hash",
            ):
                value = getattr(self, name)
                if type(value) is not str or not _HASH.fullmatch(value):
                    return False
            if (self.pilot_executed is not False
                    or self.checkpoint19_started is not False
                    or self.phase3_started is not False
                    or self.known_historical_public_exposure is not True
                    or self.current_public_refs_clean is not True):
                return False
            evaluation = Phase2BGateEvaluationV2(
                self.gate_v2_contract_id, self.gate_v2_evaluator_id,
                self.gate_results, True, self.gate_evaluation_id)
            if (not evaluation.verify() or not evaluation.all_pass
                    or len(evaluation.results) != 18
                    or any(type(result) is not Phase2BGateResultV2
                           or result.status != "PASS"
                           or result.failure_code is not None
                           or type(result.evidence_ids) is not tuple
                           or not result.evidence_ids
                           or any(type(item) is not str
                                  or not _HASH.fullmatch(item)
                                  for item in result.evidence_ids)
                           for result in evaluation.results)):
                return False
            body = {field.name: getattr(self, field.name) for field in fields(self)
                    if field.name != "content_hash"}
            return self.content_hash == content_hash({
                "schema_version": type(self).__name__, **body})
        except (AttributeError, TypeError, ValueError):
            return False


def create_checkpoint18_acceptance_exact(
        evaluation_path: Path, evaluation_id: str, **pins: object
) -> Phase2BCheckpoint18AcceptanceV1:
    """Bind metadata to the *persisted* evaluation, never console output."""
    evaluation = read_gate_evaluation_exact(evaluation_path, evaluation_id)
    if not evaluation.all_pass:
        raise ValueError("Checkpoint 18 requires formal 18/18 PASS")
    body = dict(pins)
    body.update(gate_v2_contract_id=evaluation.contract_id,
                gate_v2_evaluator_id=evaluation.evaluator_id,
                gate_evaluation_id=evaluation.content_hash,
                gate_results=evaluation.results)
    capsule = Phase2BCheckpoint18AcceptanceV1(**body, content_hash=content_hash({
        "schema_version": "Phase2BCheckpoint18AcceptanceV1", **body}))
    if not capsule.verify():
        raise ValueError("Checkpoint 18 capsule pins invalid")
    return capsule


def write_checkpoint18_acceptance_exact(
        governance_root: Path, capsule: Phase2BCheckpoint18AcceptanceV1
) -> Path:
    if not isinstance(capsule, Phase2BCheckpoint18AcceptanceV1) or not capsule.verify():
        raise ValueError("verified Checkpoint 18 capsule required")
    path = (governance_root / "phase2b"
            / f"checkpoint18-acceptance-{capsule.content_hash}.json")
    payload = canonical_json(capsule)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as target:
            target.write(payload)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ValueError("immutable Checkpoint 18 capsule collision") from None
    return path


def read_checkpoint18_acceptance_exact(
        path: Path, expected_id: str
) -> Phase2BCheckpoint18AcceptanceV1:
    if (type(expected_id) is not str or not _HASH.fullmatch(expected_id)
            or path.name != f"checkpoint18-acceptance-{expected_id}.json"):
        raise ValueError("Checkpoint 18 capsule ID/path mismatch")
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
        if type(value) is not dict or set(value) != {
                field.name for field in fields(Phase2BCheckpoint18AcceptanceV1)}:
            raise ValueError("Checkpoint 18 capsule fields malformed")
        results = value["gate_results"]
        if type(results) is not list or len(results) != 18:
            raise ValueError("Checkpoint 18 gate results malformed")
        parsed = []
        for item in results:
            if (type(item) is not dict or set(item) != _RESULT_FIELDS
                    or type(item["evidence_ids"]) is not list):
                raise ValueError("Checkpoint 18 gate result malformed")
            parsed.append(Phase2BGateResultV2(
                item["gate"], item["status"], item["failure_code"],
                tuple(item["evidence_ids"])))
        value["gate_results"] = tuple(parsed)
        capsule = Phase2BCheckpoint18AcceptanceV1(**value)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("Checkpoint 18 capsule unavailable or malformed") from error
    if (capsule.content_hash != expected_id or not capsule.verify()
            or canonical_json(capsule) != raw):
        raise ValueError("Checkpoint 18 capsule identity mismatch")
    return capsule
