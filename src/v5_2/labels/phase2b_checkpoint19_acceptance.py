"""Public, outcome-free acceptance of the exact Task 12 pilot result."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.phase2b_checkpoint19_pilot import read_pilot_result_exact
from v5_2.labels.pilot_phase2b import Phase2BPilotContractV1


_ID = re.compile(r"^[0-9a-f]{64}$")
_PREDICATES = ("NO_PROVIDER_REQUESTS", "EXACT_FIVE_DOMAIN_LINEAGE",
               "18_GATES_PASS", "DETERMINISTIC_REPLAY", "ZERO_MISMATCH")


@dataclass(frozen=True, slots=True)
class Phase2BCheckpoint19AcceptanceV1:
    checkpoint18_acceptance_id: str
    gate_evaluation_id: str
    candidate_census_id: str
    task12_preregistration_id: str
    pilot_result_id: str
    selected_candidate_ids: tuple[str, ...]
    anchor_sessions: tuple[date, ...]
    absent_strata: tuple[str, ...]
    case_ids: tuple[str, ...]
    case_states: tuple[str, ...]
    case_reasons: tuple[str, ...]
    five_domain_authority_ids: tuple[str, ...]
    acceptance_predicates: tuple[tuple[str, str], ...]
    selection_changed_after_preregistration: bool
    absent_strata_substituted: bool
    provider_request_count: int
    alpha_conclusion: str
    phase3_started: bool
    acceptance_id: str

    @classmethod
    def create(cls, **body: object) -> "Phase2BCheckpoint19AcceptanceV1":
        capsule = cls(**body, acceptance_id=content_hash({
            "schema_version": cls.__name__, **body}))
        if not capsule.verify():
            raise ValueError("Checkpoint 19 acceptance is not exact")
        return capsule

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "acceptance_id"}
        ids = (self.checkpoint18_acceptance_id, self.gate_evaluation_id,
               self.candidate_census_id, self.task12_preregistration_id,
               self.pilot_result_id, self.acceptance_id,
               *self.selected_candidate_ids, *self.case_ids,
               *self.five_domain_authority_ids)
        return (all(type(item) is str and _ID.fullmatch(item) for item in ids)
                and len(self.selected_candidate_ids) == len(self.case_ids)
                    == len(self.case_states) == len(self.case_reasons) == 4
                and len(self.five_domain_authority_ids) == 5
                and len(set(self.selected_candidate_ids)) == 4
                and self.absent_strata == ("SUPPORTED_BONUS_SHARE", "UNSUPPORTED_CA",
                    "DELISTING_BOUNDARY", "IDENTITY_TRANSITION", "PENDING_MATURATION")
                and self.acceptance_predicates == tuple((name, "PASS")
                    for name in _PREDICATES)
                and self.selection_changed_after_preregistration is False
                and self.absent_strata_substituted is False
                and self.provider_request_count == 0
                and self.alpha_conclusion == "NOT_EVALUATED"
                and self.phase3_started is False
                and self.acceptance_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def create_checkpoint19_acceptance_exact(
        private_result_path: Path, expected_result_id: str,
        contract: Phase2BPilotContractV1) -> Phase2BCheckpoint19AcceptanceV1:
    result = read_pilot_result_exact(private_result_path, expected_result_id,
                                     contract)
    if not result.verify() or not all(case.match for case in result.cases):
        raise ValueError("Checkpoint 19 pilot predicates did not all PASS")
    return Phase2BCheckpoint19AcceptanceV1.create(
        checkpoint18_acceptance_id=result.checkpoint18_acceptance_id,
        gate_evaluation_id=result.gate_evaluation_id,
        candidate_census_id=result.candidate_census_id,
        task12_preregistration_id=result.task12_preregistration_id,
        pilot_result_id=result.pilot_result_id,
        selected_candidate_ids=result.selected_candidate_ids,
        anchor_sessions=result.anchor_sessions,
        absent_strata=result.absent_strata,
        case_ids=tuple(case.case_id for case in result.cases),
        case_states=tuple(case.state for case in result.cases),
        case_reasons=tuple(case.reason for case in result.cases),
        five_domain_authority_ids=result.five_domain_authority_ids,
        acceptance_predicates=result.acceptance_predicates,
        selection_changed_after_preregistration=False,
        absent_strata_substituted=False,
        provider_request_count=result.provider_request_count,
        alpha_conclusion="NOT_EVALUATED", phase3_started=False)


def write_checkpoint19_acceptance_exact(
        governance_root: Path,
        capsule: Phase2BCheckpoint19AcceptanceV1) -> Path:
    if not capsule.verify():
        raise ValueError("verified Checkpoint 19 capsule required")
    path = (governance_root / "phase2b"
            / f"checkpoint19-acceptance-{capsule.acceptance_id}.json")
    raw = canonical_json(capsule)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as target:
            target.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError("immutable Checkpoint 19 capsule collision") from None
    return path


def read_checkpoint19_acceptance_exact(
        path: Path, expected_id: str) -> Phase2BCheckpoint19AcceptanceV1:
    if path.name != f"checkpoint19-acceptance-{expected_id}.json":
        raise ValueError("Checkpoint 19 capsule filename/ID mismatch")
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
        if (type(value) is not dict
                or set(value) != {field.name for field in fields(Phase2BCheckpoint19AcceptanceV1)}):
            raise ValueError("Checkpoint 19 capsule fields malformed")
        for name in ("selected_candidate_ids", "absent_strata", "case_ids",
                     "case_states", "case_reasons", "five_domain_authority_ids"):
            if type(value[name]) is not list:
                raise ValueError("Checkpoint 19 capsule tuple malformed")
            value[name] = tuple(value[name])
        value["anchor_sessions"] = tuple(date.fromisoformat(item)
                                          for item in value["anchor_sessions"])
        value["acceptance_predicates"] = tuple(tuple(item)
                                               for item in value["acceptance_predicates"])
        capsule = Phase2BCheckpoint19AcceptanceV1(**value)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("Checkpoint 19 capsule unavailable or malformed") from error
    if (capsule.acceptance_id != expected_id or not capsule.verify()
            or canonical_json(capsule) != raw):
        raise ValueError("Checkpoint 19 capsule identity mismatch")
    return capsule
