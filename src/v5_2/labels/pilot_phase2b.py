"""Offline Phase 2B pilot preregistration; this module never runs a pilot."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.anchor_enumerator import AnchorDispositionKind
from v5_2.labels.historical_five_domain_producer import (
    HistoricalFiveDomainProducerV1, ScopedAnchorExclusionV1,
)
from v5_2.labels.phase2b_month_coverage_v2 import read_month_coverage_evidence_exact


_ID = re.compile(r"^[0-9a-f]{64}$")
PILOT_STRATA = (
    "ORDINARY_CONTROL", "EXCLUDED_BEFORE_LABEL",
    "SUPPORTED_CASH_DIVIDEND", "SUPPORTED_BONUS_SHARE",
    "UNSUPPORTED_CA", "FULL_DAY_SUSPENSION", "DELISTING_BOUNDARY",
    "IDENTITY_TRANSITION", "NOT_LABEL_SAFE", "PENDING_MATURATION",
)
_SELECTION_RULE = "FIRST_SOURCE_ORDERED_CANDIDATE_PER_STRATUM_V1"
_PREDICATES = (
    "NO_PROVIDER_REQUESTS", "EXACT_FIVE_DOMAIN_LINEAGE", "18_GATES_PASS",
    "DETERMINISTIC_REPLAY", "ZERO_MISMATCH",
)


@dataclass(frozen=True, slots=True)
class PilotCandidateV1:
    canonical_security_identity: str
    provider_identity: str
    anchor_session: date
    strata: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]

    @property
    def candidate_id(self) -> str:
        return content_hash({"schema_version": type(self).__name__,
                             **{field.name: getattr(self, field.name)
                                for field in fields(self)}})

    def verify(self) -> bool:
        return (bool(self.canonical_security_identity and self.provider_identity)
                and type(self.anchor_session) is date
                and bool(self.strata)
                and self.strata == tuple(item for item in PILOT_STRATA
                                          if item in self.strata)
                and len(set(self.strata)) == len(self.strata)
                and bool(self.source_evidence_ids)
                and all(_ID.fullmatch(value) for value in self.source_evidence_ids))


@dataclass(frozen=True, slots=True)
class Phase2BCandidateCensusV1:
    window_start: date
    window_end: date
    candidates: tuple[PilotCandidateV1, ...]
    coverage_evidence_id: str
    source_candidate_set_hash: str
    source_approval_ids: tuple[str, ...]
    census_id: str

    @classmethod
    def create(cls, *, window_start: date, window_end: date,
               candidates: tuple[PilotCandidateV1, ...],
               coverage_evidence_id: str, source_candidate_set_hash: str,
               source_approval_ids: tuple[str, ...]) -> "Phase2BCandidateCensusV1":
        body = dict(window_start=window_start, window_end=window_end,
                    candidates=candidates, coverage_evidence_id=coverage_evidence_id,
                    source_candidate_set_hash=source_candidate_set_hash,
                    source_approval_ids=source_approval_ids)
        result = cls(**body, census_id=content_hash({"schema_version": cls.__name__,
                                                      **body}))
        if not result.verify():
            raise ValueError("candidate census is not canonical or source-pinned")
        return result

    def verify(self) -> bool:
        ordered = tuple(sorted(self.candidates, key=lambda item: (
            item.anchor_session, item.canonical_security_identity,
            item.provider_identity)))
        keys = tuple((item.canonical_security_identity, item.anchor_session)
                     for item in self.candidates)
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "census_id"}
        return (type(self.window_start) is date and type(self.window_end) is date
                and self.window_start <= self.window_end
                and bool(self.candidates) and self.candidates == ordered
                and len(keys) == len(set(keys))
                and all(item.verify() and self.window_start <= item.anchor_session
                        <= self.window_end for item in self.candidates)
                and _ID.fullmatch(self.coverage_evidence_id) is not None
                and _ID.fullmatch(self.source_candidate_set_hash) is not None
                and len(self.source_approval_ids) == 5
                and all(_ID.fullmatch(value) for value in self.source_approval_ids)
                and self.census_id == content_hash({"schema_version": type(self).__name__,
                                                    **body}))


def _select(census: Phase2BCandidateCensusV1
            ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[date, ...]]:
    chosen = []
    absent = []
    for stratum in PILOT_STRATA:
        match = next((item for item in census.candidates if stratum in item.strata), None)
        if match is None:
            absent.append(stratum)
        elif match.candidate_id not in chosen:
            chosen.append(match.candidate_id)
    sessions = tuple(sorted({item.anchor_session for item in census.candidates
                             if item.candidate_id in chosen}))
    return tuple(chosen), tuple(absent), sessions


@dataclass(frozen=True, slots=True)
class Phase2BPilotContractV1:
    candidate_census_id: str
    window_start: date
    window_end: date
    selection_rule: str
    required_strata: tuple[str, ...]
    absent_strata: tuple[str, ...]
    selected_candidate_ids: tuple[str, ...]
    anchor_sessions: tuple[date, ...]
    five_domain_authority_ids: tuple[str, ...]
    private_corpus_manifest_id: str
    cas_inventory_hash: str
    phase2a_semantic_authority_id: str
    maturation_authority_id: str
    gate_contract_id: str
    gate_evaluator_id: str
    acceptance_predicates: tuple[str, ...]
    contract_id: str

    @classmethod
    def create(cls, *, census: Phase2BCandidateCensusV1,
               five_domain_authority_ids: tuple[str, ...],
               private_corpus_manifest_id: str, cas_inventory_hash: str,
               phase2a_semantic_authority_id: str, maturation_authority_id: str,
               gate_contract_id: str, gate_evaluator_id: str
               ) -> "Phase2BPilotContractV1":
        if len(five_domain_authority_ids) != 5:
            raise ValueError("exact five-domain authority pins required")
        selected, absent, sessions = _select(census)
        body = dict(candidate_census_id=census.census_id,
                    window_start=census.window_start, window_end=census.window_end,
                    selection_rule=_SELECTION_RULE, required_strata=PILOT_STRATA,
                    absent_strata=absent, selected_candidate_ids=selected,
                    anchor_sessions=sessions,
                    five_domain_authority_ids=five_domain_authority_ids,
                    private_corpus_manifest_id=private_corpus_manifest_id,
                    cas_inventory_hash=cas_inventory_hash,
                    phase2a_semantic_authority_id=phase2a_semantic_authority_id,
                    maturation_authority_id=maturation_authority_id,
                    gate_contract_id=gate_contract_id,
                    gate_evaluator_id=gate_evaluator_id,
                    acceptance_predicates=_PREDICATES)
        result = cls(**body, contract_id=content_hash({"schema_version": cls.__name__,
                                                       **body}))
        if not result.verify(census):
            raise ValueError("pilot preregistration lacks exact authority")
        return result

    def verify(self, census: Phase2BCandidateCensusV1) -> bool:
        if not census.verify():
            return False
        selected, absent, sessions = _select(census)
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "contract_id"}
        pins = (*self.five_domain_authority_ids, self.private_corpus_manifest_id,
                self.cas_inventory_hash, self.phase2a_semantic_authority_id,
                self.maturation_authority_id, self.gate_contract_id,
                self.gate_evaluator_id)
        return (self.candidate_census_id == census.census_id
                and self.window_start == census.window_start
                and self.window_end == census.window_end
                and self.selection_rule == _SELECTION_RULE
                and self.required_strata == PILOT_STRATA
                and self.absent_strata == absent
                and self.selected_candidate_ids == selected
                and self.anchor_sessions == sessions
                and len(self.five_domain_authority_ids) == 5
                and all(_ID.fullmatch(value) for value in pins)
                and self.acceptance_predicates == _PREDICATES
                and self.contract_id == content_hash({"schema_version": type(self).__name__,
                                                       **body}))


def _source_strata(produced: object) -> tuple[str, ...]:
    if isinstance(produced, ScopedAnchorExclusionV1):
        if produced.reason == "IDENTITY_TRANSITION_WINDOW_UNRESOLVED":
            return ("IDENTITY_TRANSITION", "NOT_LABEL_SAFE")
        return ("NOT_LABEL_SAFE",)
    if not isinstance(produced, tuple):
        if produced.disposition is not AnchorDispositionKind.EXCLUDED_BEFORE_LABEL:
            raise ValueError("unexpected source anchor disposition")
        return ("EXCLUDED_BEFORE_LABEL",)
    anchor, lineage, window = produced
    observed = set()
    action_types = {item.action_type.value for item in window.corporate_actions}
    if "CASH_DIVIDEND" in action_types:
        observed.add("SUPPORTED_CASH_DIVIDEND")
    if "BONUS_SHARE" in action_types:
        observed.add("SUPPORTED_BONUS_SHARE")
    if window.action_coverage.quarantined:
        observed.update(("UNSUPPORTED_CA", "NOT_LABEL_SAFE"))
    if not window.action_coverage.covered:
        observed.add("NOT_LABEL_SAFE")
    if anchor.full_day_suspended or any(item.full_day_suspended
                                         for item in lineage.status_observations):
        observed.add("FULL_DAY_SUSPENSION")
    if window.delisting_session is not None:
        observed.add("DELISTING_BOUNDARY")
    if window.anchor_bar is None and anchor.full_day_suspended:
        observed.add("NOT_LABEL_SAFE")
    if not observed:
        observed.add("ORDINARY_CONTROL")
    return tuple(item for item in PILOT_STRATA if item in observed)


def derive_source_pinned_candidate_census_exact(
        source_root: Path, coverage_path: Path,
        expected_coverage_id: str) -> Phase2BCandidateCensusV1:
    """Classify only approved source conditions, never label outcomes."""
    coverage = read_month_coverage_evidence_exact(coverage_path,
                                                   expected_coverage_id)
    producer = HistoricalFiveDomainProducerV1.load_exact(source_root)
    if (coverage.calendar_approval_id != producer.calendar.approval_id
            or coverage.master_approval_id != producer.master.approval["approval_id"]):
        raise ValueError("coverage authority differs from exact source")
    sessions = tuple(sorted(set(producer.calendar.sse_sessions)
                            | set(producer.calendar.szse_sessions)))
    month_sessions = tuple(day for day in sessions
                           if day.strftime("%Y-%m") == coverage.month)
    if not month_sessions:
        raise ValueError("approved pilot month is absent")
    triples = []
    candidates = []
    for session in month_sessions:
        effective, _ = producer.candidate_identities(session)
        for canonical, provider in effective:
            triples.append((canonical, provider, session))
            produced = producer.produce_anchor(provider, session)
            if isinstance(produced, ScopedAnchorExclusionV1):
                evidence_ids = produced.evidence_ids
            elif isinstance(produced, tuple):
                _, lineage, window = produced
                evidence_ids = (producer.status_pins.approval_id,
                                *(item.approval_id for item in window.non_status_lineage),
                                window.content_hash)
            else:
                evidence_ids = (producer.calendar.approval_id,
                                producer.master.approval["approval_id"])
            candidates.append(PilotCandidateV1(
                canonical, provider, session, _source_strata(produced),
                tuple(evidence_ids)))
    candidate_set_hash = content_hash({
        "schema_version": "MasterCalendarCandidateSetV2", "month": coverage.month,
        "candidates": tuple(sorted(triples))})
    if candidate_set_hash != coverage.candidate_set_hash:
        raise ValueError("source candidate membership differs from frozen coverage")
    candidates.sort(key=lambda item: (item.anchor_session,
                                       item.canonical_security_identity,
                                       item.provider_identity))
    approvals = (producer.calendar.approval_id,
                 producer.master.approval["approval_id"],
                 producer.bars.reader.derived_approval_id,
                 producer.status_pins.approval_id, producer.actions.approval_id)
    return Phase2BCandidateCensusV1.create(
        window_start=month_sessions[0], window_end=month_sessions[-1],
        candidates=tuple(candidates), coverage_evidence_id=coverage.evidence_id,
        source_candidate_set_hash=candidate_set_hash,
        source_approval_ids=approvals)


def derive_real_pilot_preregistration_exact(
        source_root: Path,
        census: Phase2BCandidateCensusV1) -> Phase2BPilotContractV1:
    """Refuse caller-authored census and pin the existing Gate V2 authority."""
    from v5_2.labels.phase2b_contract_pins_v2 import (
        MATURATION_REMEDIATION_ID, PHASE2A_ACCEPTANCE_ID,
        PRIVATE_CAS_INVENTORY_HASH, PRIVATE_CORPUS_MANIFEST_ID,
        derive_contract_pin_evidence_exact,
    )
    from v5_2.labels.phase2b_gates_v2 import (
        GATE_V2_CONTRACT_ID, GATE_V2_EVALUATOR_ID,
    )

    coverage_id = "834534a947d79b10a16404ae35430aafb63b36e0ac467d46b97a57117959ef75"
    coverage_path = (source_root / "data/phase_2b_checkpoint18_real_month/gate_evidence"
                     / f"month-coverage-{coverage_id}.json")
    exact = derive_source_pinned_candidate_census_exact(
        source_root, coverage_path, coverage_id)
    pins = derive_contract_pin_evidence_exact(source_root)
    if census != exact or census.source_approval_ids != pins.source_approval_ids:
        raise ValueError("candidate census differs from exact source authority")
    return Phase2BPilotContractV1.create(
        census=census, five_domain_authority_ids=pins.source_authority_ids,
        private_corpus_manifest_id=PRIVATE_CORPUS_MANIFEST_ID,
        cas_inventory_hash=PRIVATE_CAS_INVENTORY_HASH,
        phase2a_semantic_authority_id=PHASE2A_ACCEPTANCE_ID,
        maturation_authority_id=MATURATION_REMEDIATION_ID,
        gate_contract_id=GATE_V2_CONTRACT_ID,
        gate_evaluator_id=GATE_V2_EVALUATOR_ID)


def _write_exact(path: Path, payload: bytes) -> Path:
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable pilot artifact collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def write_candidate_census_exact(root: Path,
                                 census: Phase2BCandidateCensusV1) -> Path:
    if not census.verify():
        raise ValueError("verified source census required")
    return _write_exact(root / "pilot_prereg" / f"census-{census.census_id}.json",
                        canonical_json(census))


def read_candidate_census_exact(path: Path,
                                expected_id: str) -> Phase2BCandidateCensusV1:
    if not _ID.fullmatch(expected_id) or path.name != f"census-{expected_id}.json":
        raise ValueError("candidate census identity/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        candidates = tuple(PilotCandidateV1(
            item["canonical_security_identity"], item["provider_identity"],
            date.fromisoformat(item["anchor_session"]), tuple(item["strata"]),
            tuple(item["source_evidence_ids"])) for item in values["candidates"])
        census = Phase2BCandidateCensusV1(
            date.fromisoformat(values["window_start"]),
            date.fromisoformat(values["window_end"]), candidates,
            values["coverage_evidence_id"], values["source_candidate_set_hash"],
            tuple(values["source_approval_ids"]), values["census_id"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("candidate census identity mismatch") from error
    if (census.census_id != expected_id or not census.verify()
            or canonical_json(census) != raw):
        raise ValueError("candidate census identity mismatch")
    return census


def write_pilot_contract_exact(root: Path, contract: Phase2BPilotContractV1,
                               census: Phase2BCandidateCensusV1) -> Path:
    if not contract.verify(census):
        raise ValueError("verified pilot preregistration required")
    return _write_exact(root / "pilot_prereg" / f"pilot-{contract.contract_id}.json",
                        canonical_json(contract))


def read_pilot_contract_exact(path: Path, expected_id: str,
                              census: Phase2BCandidateCensusV1) -> Phase2BPilotContractV1:
    if not _ID.fullmatch(expected_id) or path.name != f"pilot-{expected_id}.json":
        raise ValueError("pilot preregistration identity/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        for key in ("window_start", "window_end"):
            values[key] = date.fromisoformat(values[key])
        values["anchor_sessions"] = tuple(date.fromisoformat(item)
                                           for item in values["anchor_sessions"])
        for key in ("required_strata", "absent_strata", "selected_candidate_ids",
                    "five_domain_authority_ids", "acceptance_predicates"):
            values[key] = tuple(values[key])
        contract = Phase2BPilotContractV1(**values)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("pilot preregistration identity mismatch") from error
    if (contract.contract_id != expected_id or not contract.verify(census)
            or canonical_json(contract) != raw):
        raise ValueError("pilot preregistration identity mismatch")
    return contract
