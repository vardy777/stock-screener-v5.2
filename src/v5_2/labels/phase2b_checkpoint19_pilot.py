"""Exact, offline Checkpoint 19 pilot of the frozen Task 12 selection."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.acceptance import build_full_comparison_entry
from v5_2.labels.anchor_enumerator import AnchorDispositionV1
from v5_2.labels.contracts import REQUIRED_LABEL_DOMAINS
from v5_2.labels.dataset_contracts import LabelRowV1
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.historical_five_domain_producer import (
    HistoricalFiveDomainProducerV1, ScopedAnchorExclusionV1,
)
from v5_2.labels.independent_reference import calculate_independent_reference
from v5_2.labels.materializer import ExcludedAnchorV1
from v5_2.labels.phase2b_checkpoint18_acceptance import read_checkpoint18_acceptance_exact
from v5_2.labels.phase2b_contract_pins_v2 import derive_contract_pin_evidence_exact
from v5_2.labels.phase2b_gate_evaluation_artifact import read_gate_evaluation_exact
from v5_2.labels.pilot_phase2b import (
    Phase2BCandidateCensusV1, Phase2BPilotContractV1, PilotCandidateV1,
    _source_strata, read_candidate_census_exact, read_pilot_contract_exact,
)


_CENSUS_ID = "1a1f2465a2d60e84f61874feccf6538c1c1daec3f69369600255d78379285a8d"
_PREREG_ID = "5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc"
_ACCEPTANCE_ID = "c2ff1d3ff8ffffd49279af39b7bb539a251f226e82923b85bf9234470a53f310"
_GATE_ID = "2ee052fd40beccee86f62d4b5fe29eb8710e2548ac8ee5c5e418d0a39646be66"
_ABSENT = ("SUPPORTED_BONUS_SHARE", "UNSUPPORTED_CA", "DELISTING_BOUNDARY",
           "IDENTITY_TRANSITION", "PENDING_MATURATION")
_PREDICATES = ("NO_PROVIDER_REQUESTS", "EXACT_FIVE_DOMAIN_LINEAGE",
               "18_GATES_PASS", "DETERMINISTIC_REPLAY", "ZERO_MISMATCH")


def selected_candidates_exact(
        census: Phase2BCandidateCensusV1,
        contract: Phase2BPilotContractV1) -> tuple[PilotCandidateV1, ...]:
    """Preserve preregistration order; never select from outcome data."""
    if (not census.verify() or not contract.verify(census)
            or len(contract.selected_candidate_ids) != 4
            or len(set(contract.selected_candidate_ids)) != 4):
        raise ValueError("four exact preregistered candidates required")
    by_id = {item.candidate_id: item for item in census.candidates}
    try:
        selected = tuple(by_id[item_id] for item_id in contract.selected_candidate_ids)
    except KeyError as error:
        raise ValueError("preregistered candidate missing from census") from error
    if tuple(sorted({item.anchor_session for item in selected})) != contract.anchor_sessions:
        raise ValueError("preregistered anchor sessions changed")
    return selected


@dataclass(frozen=True, slots=True)
class Phase2BCheckpoint19CaseV1:
    candidate_id: str
    canonical_security_identity: str
    provider_identity: str
    anchor_session: date
    source_strata: tuple[str, ...]
    state: str
    reason: str
    label_values: tuple[tuple[str, str, str, str], ...]
    source_evidence_ids: tuple[str, ...]
    five_domain_authority_ids: tuple[str, ...]
    domain_lineage_ids: tuple[str, ...]
    bundle_id: str | None
    row_id: str | None
    production_result_id: str
    independent_result_id: str | None
    comparison_id: str | None
    match: bool
    case_id: str

    @classmethod
    def create(cls, **body: object) -> "Phase2BCheckpoint19CaseV1":
        case = cls(**body, case_id=content_hash({"schema_version": cls.__name__,
                                                 **body}))
        if not case.verify():
            raise ValueError("pilot case is not exact")
        return case

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "case_id"}
        has_bundle = self.bundle_id is not None
        return (len(self.five_domain_authority_ids) == 5
                and bool(self.source_evidence_ids)
                and self.match is True
                and (len(self.domain_lineage_ids) == 5
                     and len(self.label_values) == 7
                     and self.row_id is not None
                     and self.independent_result_id is not None
                     and self.comparison_id is not None
                     if has_bundle else
                     not self.domain_lineage_ids and not self.label_values
                     and self.row_id is None and self.independent_result_id is None
                     and self.comparison_id is None
                     and self.state in {"EXCLUDED_BEFORE_LABEL", "SCOPED_EXCLUDED"})
                and self.case_id == content_hash({"schema_version": type(self).__name__,
                                                  **body}))


@dataclass(frozen=True, slots=True)
class Phase2BCheckpoint19PilotResultV1:
    checkpoint18_acceptance_id: str
    gate_evaluation_id: str
    candidate_census_id: str
    task12_preregistration_id: str
    selected_candidate_ids: tuple[str, ...]
    anchor_sessions: tuple[date, ...]
    absent_strata: tuple[str, ...]
    five_domain_authority_ids: tuple[str, ...]
    cases: tuple[Phase2BCheckpoint19CaseV1, ...]
    provider_request_count: int
    deterministic_replay: bool
    acceptance_predicates: tuple[tuple[str, str], ...]
    pilot_result_id: str

    @classmethod
    def create(cls, **body: object) -> "Phase2BCheckpoint19PilotResultV1":
        result = cls(**body, pilot_result_id=content_hash({
            "schema_version": cls.__name__, **body}))
        if not result.verify():
            raise ValueError("pilot result is not exact")
        return result

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "pilot_result_id"}
        return (self.checkpoint18_acceptance_id == _ACCEPTANCE_ID
                and self.gate_evaluation_id == _GATE_ID
                and self.candidate_census_id == _CENSUS_ID
                and self.task12_preregistration_id == _PREREG_ID
                and len(self.cases) == len(self.selected_candidate_ids) == 4
                and tuple(item.candidate_id for item in self.cases)
                    == self.selected_candidate_ids
                and tuple(sorted({item.anchor_session for item in self.cases}))
                    == self.anchor_sessions
                and all(item.verify() and item.five_domain_authority_ids
                        == self.five_domain_authority_ids for item in self.cases)
                and self.absent_strata == _ABSENT
                and self.provider_request_count == 0
                and self.deterministic_replay is True
                and self.acceptance_predicates == tuple((name, "PASS")
                    for name in _PREDICATES)
                and self.pilot_result_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def _source_evidence(produced: object, producer: HistoricalFiveDomainProducerV1
                     ) -> tuple[str, ...]:
    if isinstance(produced, ScopedAnchorExclusionV1):
        return produced.evidence_ids
    if isinstance(produced, tuple):
        _, _, window = produced
        return (producer.status_pins.approval_id,
                *(item.approval_id for item in window.non_status_lineage),
                window.content_hash)
    return (producer.calendar.approval_id, producer.master.approval["approval_id"])


def _one_case(index: int, candidate: PilotCandidateV1,
              producer: HistoricalFiveDomainProducerV1,
              engine: ReferenceLabelEngine,
              authorities: tuple[str, ...]) -> Phase2BCheckpoint19CaseV1:
    produced = producer.produce_anchor(candidate.provider_identity,
                                       candidate.anchor_session)
    if (_source_strata(produced) != candidate.strata
            or _source_evidence(produced, producer) != candidate.source_evidence_ids):
        raise ValueError("selected candidate differs from frozen source census")
    common = dict(candidate_id=candidate.candidate_id,
                  canonical_security_identity=candidate.canonical_security_identity,
                  provider_identity=candidate.provider_identity,
                  anchor_session=candidate.anchor_session,
                  source_strata=candidate.strata,
                  source_evidence_ids=candidate.source_evidence_ids,
                  five_domain_authority_ids=authorities)
    if isinstance(produced, ScopedAnchorExclusionV1):
        return Phase2BCheckpoint19CaseV1.create(
            **common, state="SCOPED_EXCLUDED", reason=produced.reason,
            label_values=(), domain_lineage_ids=(), bundle_id=None, row_id=None,
            production_result_id=content_hash({
                "schema_version": "ScopedAnchorExclusionV1", **{
                    "security_identity": produced.security_identity,
                    "anchor_session": produced.anchor_session,
                    "domain": produced.domain, "reason": produced.reason,
                    "evidence_ids": produced.evidence_ids}}),
            independent_result_id=None, comparison_id=None, match=True)
    if isinstance(produced, AnchorDispositionV1):
        excluded = ExcludedAnchorV1.create(produced)
        if (excluded.canonical_security_identity
                != candidate.canonical_security_identity):
            raise ValueError("excluded identity differs from frozen census")
        return Phase2BCheckpoint19CaseV1.create(
            **common, state="EXCLUDED_BEFORE_LABEL", reason=excluded.reason,
            label_values=(), domain_lineage_ids=(), bundle_id=None, row_id=None,
            production_result_id=excluded.content_hash,
            independent_result_id=None, comparison_id=None, match=True)
    anchor, lineage, window = produced
    if (anchor.canonical_security_identity != candidate.canonical_security_identity
            or anchor.anchor_session != candidate.anchor_session):
        raise ValueError("anchor identity differs from frozen census")
    bundle = producer.assemble(anchor, lineage, window)
    if (not bundle.verify()
            or tuple(item.domain for item in bundle.domain_lineage)
               != REQUIRED_LABEL_DOMAINS):
        raise ValueError("five-domain pilot bundle invalid")
    expected_approvals = (producer.calendar.approval_id,
                          producer.master.approval["approval_id"],
                          producer.bars.reader.derived_approval_id,
                          producer.status_pins.approval_id,
                          producer.actions.approval_id)
    if tuple(item.approval_id for item in bundle.domain_lineage) != expected_approvals:
        raise ValueError("five-domain approval lineage differs from exact producer")
    production = engine.evaluate(bundle)
    independent = calculate_independent_reference(index, bundle)
    comparison = build_full_comparison_entry(SimpleNamespace(
        slot=index, security_identity=candidate.canonical_security_identity,
        anchor_session=candidate.anchor_session), bundle, production, independent)
    if not comparison.verify() or comparison.disposition != "MATCH":
        raise ValueError(f"pilot independent mismatch: {candidate.candidate_id}")
    row = LabelRowV1.create(result=production, bundle=bundle,
                            materialization_version="phase2b-v1")
    values = comparison.production_summary
    states = {item[1] for item in values}
    reasons = {item[3] for item in values if item[3]}
    return Phase2BCheckpoint19CaseV1.create(
        **common, state=next(iter(states)) if len(states) == 1 else "MIXED",
        reason=next(iter(reasons)) if len(reasons) == 1 else ";".join(sorted(reasons)),
        label_values=values,
        domain_lineage_ids=tuple(item.content_hash for item in bundle.domain_lineage),
        bundle_id=bundle.content_hash, row_id=row.row_id,
        production_result_id=production.content_hash,
        independent_result_id=independent.content_hash,
        comparison_id=comparison.content_hash, match=True)


def write_pilot_result_exact(root: Path,
                             result: Phase2BCheckpoint19PilotResultV1) -> Path:
    if not result.verify():
        raise ValueError("verified pilot result required")
    path = root / "pilot_results" / f"pilot-result-{result.pilot_result_id}.json"
    raw = canonical_json(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as target:
            target.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError("immutable pilot result collision") from None
    return path


def read_pilot_result_exact(
        path: Path, expected_id: str,
        contract: Phase2BPilotContractV1) -> Phase2BCheckpoint19PilotResultV1:
    if path.name != f"pilot-result-{expected_id}.json":
        raise ValueError("pilot result filename/ID mismatch")
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
        if (type(value) is not dict
                or set(value) != {item.name for item in fields(Phase2BCheckpoint19PilotResultV1)}
                or type(value["cases"]) is not list or len(value["cases"]) != 4):
            raise ValueError("pilot result structure invalid")
        cases = []
        for item in value["cases"]:
            if (type(item) is not dict
                    or set(item) != {field.name for field in fields(Phase2BCheckpoint19CaseV1)}):
                raise ValueError("pilot case structure invalid")
            item["anchor_session"] = date.fromisoformat(item["anchor_session"])
            for name in ("source_strata", "source_evidence_ids",
                         "five_domain_authority_ids", "domain_lineage_ids"):
                if type(item[name]) is not list:
                    raise ValueError("pilot case tuple structure invalid")
                item[name] = tuple(item[name])
            if type(item["label_values"]) is not list:
                raise ValueError("pilot label tuple structure invalid")
            item["label_values"] = tuple(tuple(x) for x in item["label_values"])
            cases.append(Phase2BCheckpoint19CaseV1(**item))
        value["cases"] = tuple(cases)
        value["anchor_sessions"] = tuple(date.fromisoformat(x)
                                          for x in value["anchor_sessions"])
        for name in ("selected_candidate_ids", "absent_strata",
                     "five_domain_authority_ids"):
            if type(value[name]) is not list:
                raise ValueError("pilot result tuple structure invalid")
            value[name] = tuple(value[name])
        value["acceptance_predicates"] = tuple(tuple(x) for x in value["acceptance_predicates"])
        result = Phase2BCheckpoint19PilotResultV1(**value)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("pilot result unavailable or malformed") from error
    if (result.pilot_result_id != expected_id or not result.verify()
            or result.task12_preregistration_id != contract.contract_id
            or result.selected_candidate_ids != contract.selected_candidate_ids
            or result.anchor_sessions != contract.anchor_sessions
            or result.absent_strata != contract.absent_strata
            or result.five_domain_authority_ids != contract.five_domain_authority_ids
            or tuple(name for name, _ in result.acceptance_predicates)
               != contract.acceptance_predicates
            or canonical_json(result) != raw):
        raise ValueError("pilot result exact authority mismatch")
    return result


def run_checkpoint19_exact(
        source_root: Path, *, output_root: Path
) -> Phase2BCheckpoint19PilotResultV1:
    """Run only the four Task 12 candidates, twice, without market-data I/O."""
    base = source_root / "data/phase_2b_checkpoint18_real_month"
    pre = base / "pilot_prereg"
    census = read_candidate_census_exact(pre / f"census-{_CENSUS_ID}.json",
                                         _CENSUS_ID)
    contract = read_pilot_contract_exact(pre / f"pilot-{_PREREG_ID}.json",
                                         _PREREG_ID, census)
    if (census.window_start != date(2010, 1, 4)
            or census.window_end != date(2010, 1, 29)
            or contract.absent_strata != _ABSENT
            or contract.acceptance_predicates != _PREDICATES):
        raise ValueError("pilot window or preregistered strata changed")
    selected = selected_candidates_exact(census, contract)
    acceptance = read_checkpoint18_acceptance_exact(
        source_root / "governance/phase2b"
        / f"checkpoint18-acceptance-{_ACCEPTANCE_ID}.json", _ACCEPTANCE_ID)
    evaluation = read_gate_evaluation_exact(
        base / "gate_evidence" / f"gate-evaluation-{_GATE_ID}.json", _GATE_ID)
    if (not acceptance.verify() or not evaluation.verify()
            or not evaluation.all_pass or len(evaluation.results) != 18
            or acceptance.gate_evaluation_id != evaluation.content_hash
            or acceptance.gate_results != evaluation.results
            or contract.gate_contract_id != evaluation.contract_id
            or contract.gate_evaluator_id != evaluation.evaluator_id):
        raise ValueError("Checkpoint 18 authority differs from exact pilot pins")
    pins = derive_contract_pin_evidence_exact(source_root)
    if (contract.five_domain_authority_ids != pins.source_authority_ids
            or contract.private_corpus_manifest_id
               != acceptance.private_corpus_manifest_id
            or contract.cas_inventory_hash != acceptance.private_cas_inventory_hash):
        raise ValueError("five-domain pilot authority differs from frozen source")
    runs = []
    for _ in range(2):
        producer = HistoricalFiveDomainProducerV1.load_exact(source_root)
        engine = ReferenceLabelEngine()
        runs.append(tuple(_one_case(index, candidate, producer, engine,
                                    contract.five_domain_authority_ids)
                          for index, candidate in enumerate(selected, 1)))
    if runs[0] != runs[1]:
        raise ValueError("pilot deterministic replay mismatch")
    result = Phase2BCheckpoint19PilotResultV1.create(
        checkpoint18_acceptance_id=_ACCEPTANCE_ID,
        gate_evaluation_id=_GATE_ID,
        candidate_census_id=census.census_id,
        task12_preregistration_id=contract.contract_id,
        selected_candidate_ids=contract.selected_candidate_ids,
        anchor_sessions=contract.anchor_sessions,
        absent_strata=contract.absent_strata,
        five_domain_authority_ids=contract.five_domain_authority_ids,
        cases=runs[0], provider_request_count=0,
        deterministic_replay=True,
        acceptance_predicates=tuple((item, "PASS")
                                    for item in contract.acceptance_predicates))
    write_pilot_result_exact(output_root, result)
    return result
