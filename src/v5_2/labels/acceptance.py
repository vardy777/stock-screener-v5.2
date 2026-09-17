from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import ProvenancePath


PHASE2A_STRATA = (
    "normal positive return", "normal negative return", "high volatility",
    "limit-up-like path", "limit-down-like path", "cash dividend", "bonus share",
    "D+1 full-day suspension", "multi-day suspension", "suspension through H5",
    "resumption before H5", "first IPO-eligible boundary", "still inside IPO seasoning",
    "delisting boundary", "identity transition", "expected future bar missing",
    "unsupported corporate action", "latest-session LABEL_PENDING",
    "upper barrier first", "lower barrier first", "neither barrier",
    "same-session double-barrier ambiguity",
)


@dataclass(frozen=True, slots=True)
class LabelAcceptanceSelectionRuleV1:
    contract_version: str
    ordering: str
    result_blind: bool
    content_hash: str

    @classmethod
    def create(cls):
        body = {"contract_version": "v5.2-label-contract-v1", "ordering": "content_hash(contract_version,stratum,canonical_identity,anchor_session)", "result_blind": True}
        return cls(**body, content_hash=content_hash({"schema_version": cls.__name__, **body}))


@dataclass(frozen=True, slots=True)
class LabelAcceptanceSlotV1:
    slot: int
    stratum: str
    security_identity: str
    anchor_session: date
    exchange: str
    board: str
    provenance_path: ProvenancePath
    inventory_status: str
    source_kind: str
    evidence_ids: tuple[str, ...]
    reason: str | None
    candidate_hash: str


@dataclass(frozen=True, slots=True)
class LabelAcceptanceInventoryV1:
    selection_rule: LabelAcceptanceSelectionRuleV1
    slots: tuple[LabelAcceptanceSlotV1, ...]
    inventory_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {"selection_rule": self.selection_rule, "slots": self.slots}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.inventory_id == self.content_hash == digest and len(self.slots) == 22


_STATUS_INV = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
_CA_INV = "90354c25bb7529048a2a391ba06e8e4cfb5daf732f9b6abcca94189fa13023c5"
_BAR_MANIFEST = "1ad71807083aba6222fa6ab27aedf47c0ac2e2ba65a56ad1ce5ae5956db43ead"
_REAL_CASES = (
    ("000969.SZ", "2024-01-24", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-01-02", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-05", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-09-30", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-10-08", "SZSE", "main", _BAR_MANIFEST),
    ("000333.SZ", "2021-06-01", "SZSE", "main", _CA_INV),
    ("600276.SH", "2019-03-27", "SSE", "main", _CA_INV),
    ("600658.SH", "2010-05-18", "SSE", "main", _STATUS_INV),
    ("002166.SZ", "2019-04-12", "SZSE", "main", _STATUS_INV),
    ("600155.SH", "2015-11-16", "SSE", "main", _STATUS_INV),
    ("300131.SZ", "2014-09-11", "SZSE", "ChiNext", _STATUS_INV),
    ("688053.SH", "2022-07-14", "SSE", "STAR", _STATUS_INV),
    ("688247.SH", "2022-08-30", "SSE", "STAR", _STATUS_INV),
    ("002118.SZ", "2023-08-03", "SZSE", "main", _STATUS_INV),
    ("300114.SZ", "2025-02-14", "SZSE", "ChiNext", _STATUS_INV),
    ("000969.SZ", "2024-06-05", "SZSE", "main", _BAR_MANIFEST),
    ("000651.SZ", "2010-07-12", "SZSE", "main", _CA_INV),
    ("000969.SZ", "2025-12-31", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-06", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-07", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-03-01", "SZSE", "main", _BAR_MANIFEST),
    ("000969.SZ", "2024-02-08", "SZSE", "main", _BAR_MANIFEST),
)


def build_frozen_inventory() -> LabelAcceptanceInventoryV1:
    rule = LabelAcceptanceSelectionRuleV1.create()
    slots = []
    evidence_proven_slots = {6, 7, 14, 15}
    for index, (stratum, case) in enumerate(zip(PHASE2A_STRATA, _REAL_CASES), 1):
        identity, day, exchange, board, evidence = case
        candidate = content_hash((rule.contract_version, stratum, identity, day))
        available = index in evidence_proven_slots
        slots.append(LabelAcceptanceSlotV1(index, stratum, identity, date.fromisoformat(day), exchange, board,
                                           ProvenancePath.HISTORICAL,
                                           "EVIDENCE_AVAILABLE" if available else "EVIDENCE_UNAVAILABLE",
                                           "REAL_PHASE1_ARTIFACT", (evidence,),
                                           None if available else "STRATUM_APPLICABILITY_NOT_YET_PROVEN",
                                           candidate))
    body = {"selection_rule": rule, "slots": tuple(slots)}
    digest = content_hash({"schema_version": "LabelAcceptanceInventoryV1", **body})
    return LabelAcceptanceInventoryV1(rule, tuple(slots), digest, digest)


@dataclass(frozen=True, slots=True)
class IndependentLabelCalculationV1:
    slot: int
    inventory_evidence_id: str
    status: str
    horizons: tuple[str, ...]
    inputs_hash: str | None
    result_summary: tuple[tuple[str, str, str, str], ...]
    method_version: str
    reason: str | None
    calculation_id: str
    content_hash: str

    @classmethod
    def create(cls, *, slot: int, inventory_evidence_id: str, status: str, horizons: tuple[str, ...],
               inputs_hash: str | None, result_summary: tuple[tuple[str, str, str, str], ...],
               method_version: str, reason: str | None = None):
        if status == "CALCULATED" and (not horizons or not inputs_hash or not result_summary or reason): raise ValueError("calculated reference requires complete evidence")
        if status == "EVIDENCE_UNAVAILABLE" and (result_summary or not reason): raise ValueError("unavailable reference requires reason and no result")
        body = {"slot": slot, "inventory_evidence_id": inventory_evidence_id, "status": status, "horizons": horizons, "inputs_hash": inputs_hash, "result_summary": result_summary, "method_version": method_version, "reason": reason}
        digest = content_hash({"schema_version": cls.__name__, **body})
        return cls(**body, calculation_id=digest, content_hash=digest)

    def verify(self):
        body = {name: getattr(self, name) for name in ("slot", "inventory_evidence_id", "status", "horizons", "inputs_hash", "result_summary", "method_version", "reason")}
        return self.calculation_id == self.content_hash == content_hash({"schema_version": type(self).__name__, **body})


@dataclass(frozen=True, slots=True)
class ComparisonEntryV1:
    slot: int
    calculation_id: str
    disposition: str
    engine_summary: tuple[tuple[str, str, str, str], ...]
    independent_summary: tuple[tuple[str, str, str, str], ...]
    reason: str | None


@dataclass(frozen=True, slots=True)
class EngineComparisonLedgerV1:
    entries: tuple[ComparisonEntryV1, ...]
    ledger_id: str
    content_hash: str

    def verify(self):
        digest = content_hash({"schema_version": type(self).__name__, "entries": self.entries})
        return self.ledger_id == self.content_hash == digest


def build_comparison_ledger(calculations: tuple[IndependentLabelCalculationV1, ...], engine_results: dict[int, tuple[tuple[str, str, str, str], ...]]) -> EngineComparisonLedgerV1:
    entries = []
    for item in calculations:
        if not item.verify(): raise ValueError("tampered independent calculation")
        engine = engine_results.get(item.slot, ()) if item.status == "CALCULATED" else ()
        disposition = "EVIDENCE_UNAVAILABLE" if item.status != "CALCULATED" else "MATCH" if engine == item.result_summary else "MISMATCH"
        entries.append(ComparisonEntryV1(item.slot, item.calculation_id, disposition, engine, item.result_summary, item.reason))
    digest = content_hash({"schema_version": "EngineComparisonLedgerV1", "entries": tuple(entries)})
    return EngineComparisonLedgerV1(tuple(entries), digest, digest)


@dataclass(frozen=True, slots=True)
class FullComparisonEntryV1:
    slot: int
    security_identity: str
    anchor_session: date
    bundle_id: str
    five_domain_lineage_ids: tuple[str, ...]
    production_result_hash: str
    independent_result_hash: str
    production_summary: tuple[tuple[str, str, str, str], ...]
    independent_summary: tuple[tuple[str, str, str, str], ...]
    production_barriers: tuple[tuple[str, str, str], ...]
    independent_barriers: tuple[tuple[str, str, str], ...]
    numeric_match: bool
    state_match: bool
    reason_match: bool
    barrier_categorical_match: bool
    barrier_decisive_session_match: bool
    lineage_validation: bool
    disposition: str
    comparison_hash: str
    content_hash: str

    def verify(self):
        body = {name: getattr(self, name) for name in (
            "slot", "security_identity", "anchor_session", "bundle_id",
            "five_domain_lineage_ids", "production_result_hash",
            "independent_result_hash", "production_summary", "independent_summary",
            "production_barriers", "independent_barriers", "numeric_match",
            "state_match", "reason_match", "barrier_categorical_match",
            "barrier_decisive_session_match", "lineage_validation", "disposition",
        )}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.comparison_hash == self.content_hash == digest


def _public_summary(result):
    return tuple((item.label_name, item.state.value, str(item.value),
                  item.reason_code.value if item.reason_code else "") for item in result.values)


def _production_barriers(result):
    values = []
    names = ("hit_3pct_before_-2pct", "hit_5pct_before_-3pct")
    for name, item in zip(names, result.barrier_evidence):
        outcome = item.outcome.value if getattr(item, "outcome", None) is not None else ""
        decisive = item.first_decisive_session.isoformat() if getattr(item, "first_decisive_session", None) else ""
        ambiguous = getattr(item, "ambiguous_session", None)
        values.append((name, outcome or "AMBIGUOUS" if ambiguous else outcome,
                       decisive or (ambiguous.isoformat() if ambiguous else "")))
    return tuple(values)


def _independent_barriers(result):
    return tuple((item.label_name, item.outcome or ("AMBIGUOUS" if item.ambiguous_session else ""),
                  item.decisive_session.isoformat() if item.decisive_session else "")
                 for item in result.barriers)


def build_full_comparison_entry(slot, bundle, production, independent) -> FullComparisonEntryV1:
    produced = _public_summary(production)
    expected = independent.result_summary
    states = tuple(item[1] for item in produced) == tuple(item[1] for item in expected)
    reasons = tuple(item[3] for item in produced) == tuple(item[3] for item in expected)
    numeric = tuple(item[2] for item in produced) == tuple(item[2] for item in expected)
    prod_barriers = _production_barriers(production)
    independent_barriers = _independent_barriers(independent)
    categorical = tuple(item[:2] for item in prod_barriers) == tuple(item[:2] for item in independent_barriers)
    decisive = tuple((item[0], item[2]) for item in prod_barriers) == tuple((item[0], item[2]) for item in independent_barriers)
    lineage = (bundle.verify() and production.verify() and independent.verify()
               and production.bundle_hash == bundle.content_hash
               and independent.bundle_id == bundle.content_hash
               and independent.lineage_digest == content_hash(tuple(item.content_hash for item in bundle.domain_lineage)))
    matched = all((numeric, states, reasons, categorical, decisive, lineage))
    body = {
        "slot": slot.slot, "security_identity": slot.security_identity,
        "anchor_session": slot.anchor_session, "bundle_id": bundle.content_hash,
        "five_domain_lineage_ids": tuple(item.content_hash for item in bundle.domain_lineage),
        "production_result_hash": production.content_hash,
        "independent_result_hash": independent.content_hash,
        "production_summary": produced, "independent_summary": expected,
        "production_barriers": prod_barriers, "independent_barriers": independent_barriers,
        "numeric_match": numeric, "state_match": states, "reason_match": reasons,
        "barrier_categorical_match": categorical,
        "barrier_decisive_session_match": decisive,
        "lineage_validation": lineage,
        "disposition": "MATCH" if matched else "MISMATCH",
    }
    digest = content_hash({"schema_version": "FullComparisonEntryV1", **body})
    return FullComparisonEntryV1(**body, comparison_hash=digest, content_hash=digest)


@dataclass(frozen=True, slots=True)
class FullComparisonLedgerV1:
    entries: tuple[FullComparisonEntryV1, ...]
    ledger_id: str
    content_hash: str

    @classmethod
    def create(cls, *, entries: tuple[FullComparisonEntryV1, ...]):
        if tuple(item.slot for item in entries) != tuple(range(1, 23)):
            raise ValueError("exact 22 distinct ordered slots required")
        if not all(item.verify() for item in entries):
            raise ValueError("tampered comparison entry")
        digest = content_hash({"schema_version": cls.__name__, "entries": entries})
        return cls(entries, digest, digest)

    def verify(self):
        digest = content_hash({"schema_version": type(self).__name__, "entries": self.entries})
        return (self.ledger_id == self.content_hash == digest
                and tuple(item.slot for item in self.entries) == tuple(range(1, 23))
                and all(item.verify() for item in self.entries))


ACCEPTANCE_GATES = (
    "LABEL CONTRACT", "CAUSAL ISOLATION", "TRADING SESSION SEMANTICS",
    "RETURN SEMANTICS", "MFE/MAE SEMANTICS", "BARRIER SEMANTICS",
    "CORPORATE ACTION SAFETY", "SUSPENSION SAFETY", "DELISTING SAFETY",
    "IDENTITY SAFETY", "MISSING DATA FAIL-CLOSED", "LABEL_PENDING",
    "NOT_LABEL_SAFE", "REFERENCE SAMPLES", "INDEPENDENT VERIFICATION",
    "DETERMINISTIC REPLAY",
)


@dataclass(frozen=True, slots=True)
class Phase2AAcceptanceArtifactV1:
    statuses: tuple[tuple[str, str], ...]
    evidence_ids: tuple[str, ...]
    phase_2a_status: str
    ready_for_phase_2b: bool
    acceptance_id: str
    content_hash: str

    @classmethod
    def create(cls, *, statuses: tuple[tuple[str, str], ...], evidence_ids: tuple[str, ...]):
        if tuple(name for name, _ in statuses) != ACCEPTANCE_GATES: raise ValueError("exact 16 acceptance gates required")
        if any(value not in {"PASS", "PENDING", "FAIL"} for _, value in statuses): raise ValueError("invalid gate status")
        ready = all(value == "PASS" for _, value in statuses)
        state = "PASS" if ready else "FAIL" if any(value == "FAIL" for _, value in statuses) else "PENDING"
        body = {"statuses": statuses, "evidence_ids": evidence_ids, "phase_2a_status": state, "ready_for_phase_2b": ready}
        digest = content_hash({"schema_version": cls.__name__, **body})
        return cls(**body, acceptance_id=digest, content_hash=digest)

    def verify(self):
        body = {name: getattr(self, name) for name in ("statuses", "evidence_ids", "phase_2a_status", "ready_for_phase_2b")}
        return self.acceptance_id == self.content_hash == content_hash({"schema_version": type(self).__name__, **body})


def render_acceptance_report(inventory: LabelAcceptanceInventoryV1, ledger: EngineComparisonLedgerV1,
                             acceptance: Phase2AAcceptanceArtifactV1) -> str:
    if not inventory.verify() or not ledger.verify() or not acceptance.verify(): raise ValueError("tampered acceptance input")
    comparisons = {item.slot: item for item in ledger.entries}
    lines = ["# V5.2 Phase 2A Acceptance", "", f"PHASE 2A = {acceptance.phase_2a_status}",
             f"READY FOR PHASE 2B = {'YES' if acceptance.ready_for_phase_2b else 'NO'}", "",
             "## 16 gates", ""]
    lines.extend(f"- {name} = {value}" for name, value in acceptance.statuses)
    lines.extend(["", "## Frozen 22-slot audit", "",
        "| slot | stratum | canonical security identity | anchor session | provenance path | inventory status | engine label state | independent label state | reference result summary | independent result summary | comparison result | reason / EVIDENCE_UNAVAILABLE | inventory evidence ID | independent calculation ID | comparison evidence ID |",
        "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"])
    for slot in inventory.slots:
        comp = comparisons[slot.slot]
        independent_state = "EVIDENCE_UNAVAILABLE" if comp.disposition == "EVIDENCE_UNAVAILABLE" else "CALCULATED"
        reason = comp.reason or slot.reason or ""
        lines.append(f"| {slot.slot:02d} | {slot.stratum} | {slot.security_identity} | {slot.anchor_session.isoformat()} | {slot.provenance_path.value} | {slot.inventory_status} | EVIDENCE_UNAVAILABLE | {independent_state} | EVIDENCE_UNAVAILABLE | {comp.independent_summary or 'EVIDENCE_UNAVAILABLE'} | {comp.disposition} | {reason or 'EVIDENCE_UNAVAILABLE'} | {slot.evidence_ids[0]} | {comp.calculation_id} | {ledger.ledger_id} |")
    lines.extend(["", "## Immutable evidence", "", f"REAL SAMPLE INVENTORY ID = {inventory.inventory_id}",
                  f"INDEPENDENT VERIFICATION ID = {ledger.ledger_id}", f"PHASE 2A ACCEPTANCE ID = {acceptance.acceptance_id}", "",
                  "Raw runtime evidence remains ignored under `data/phase_2a/`; this table preserves the GitHub-auditable disposition of every mandatory slot.", ""])
    return "\n".join(lines)
