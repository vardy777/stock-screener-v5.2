from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from v5_2.data.identity import content_hash


class EvidenceClass(StrEnum):
    REAL_MARKET_EVIDENCE = "REAL_MARKET_EVIDENCE"
    REAL_APPROVED_BOUNDARY_CONDITION = "REAL_APPROVED_BOUNDARY_CONDITION"
    REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION = "REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION"
    DETERMINISTIC_CONTRACT_FIXTURE = "DETERMINISTIC_CONTRACT_FIXTURE"
    SYNTHETIC_CONTRACT_FIXTURE = "SYNTHETIC_CONTRACT_FIXTURE"


def _digest(schema: str, body: dict[str, object]) -> str:
    return content_hash({"schema_version": schema, **body})


def _ids(values: tuple[str, ...], name: str) -> None:
    if not values or len(set(values)) != len(values) or any(len(value) != 64 for value in values):
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class MigrationEntryV2:
    slot: int
    layers: tuple[str, ...]
    actual_behavior: str
    content_hash: str

    @classmethod
    def create(cls, *, slot: int, layers: tuple[str, ...], actual_behavior: str):
        if slot < 1 or not layers or any(x not in {"A", "B", "C"} for x in layers):
            raise ValueError("invalid migration entry")
        body = {"slot": slot, "layers": layers, "actual_behavior": actual_behavior}
        return cls(**body, content_hash=_digest(cls.__name__, body))

    def verify(self) -> bool:
        body = {"slot": self.slot, "layers": self.layers, "actual_behavior": self.actual_behavior}
        return self.content_hash == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class Phase2AAcceptanceArchitectureAmendmentV2:
    design_commit: str
    plan_commits: tuple[str, ...]
    v1_artifact_ids: tuple[str, ...]
    migration: tuple[MigrationEntryV2, ...]
    artifact_id: str
    content_hash: str

    @classmethod
    def create(cls, *, design_commit: str, plan_commits: tuple[str, ...], v1_artifact_ids: tuple[str, ...], migration: tuple[MigrationEntryV2, ...]):
        _ids((design_commit,), "design commit"); _ids(plan_commits, "plan commits"); _ids(v1_artifact_ids, "v1 artifacts")
        if tuple(x.slot for x in migration) != tuple(range(1, 23)) or not all(x.verify() for x in migration):
            raise ValueError("exact 22-slot migration required")
        body = {"design_commit": design_commit, "plan_commits": plan_commits, "v1_artifact_ids": v1_artifact_ids, "migration": migration}
        digest = _digest(cls.__name__, body)
        return cls(**body, artifact_id=digest, content_hash=digest)

    def verify(self) -> bool:
        body = {"design_commit": self.design_commit, "plan_commits": self.plan_commits, "v1_artifact_ids": self.v1_artifact_ids, "migration": self.migration}
        return self.artifact_id == self.content_hash == _digest(type(self).__name__, body) and tuple(x.slot for x in self.migration) == tuple(range(1, 23)) and all(x.verify() for x in self.migration)


@dataclass(frozen=True, slots=True)
class RealReferenceCaseV2:
    slot: int
    evidence_class: EvidenceClass
    bundle_id: str
    five_domain_lineage_ids: tuple[str, ...]
    production_result_id: str
    independent_result_id: str
    comparison_id: str
    semantic_roles: tuple[str, ...]
    disposition: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        values["evidence_class"] = EvidenceClass(values["evidence_class"])
        for name in ("bundle_id", "production_result_id", "independent_result_id", "comparison_id"):
            _ids((values[name],), name)
        _ids(values["five_domain_lineage_ids"], "five-domain lineage")
        if len(values["five_domain_lineage_ids"]) != 5 or not values["semantic_roles"]:
            raise ValueError("exact five-domain real case required")
        digest = _digest(cls.__name__, values)
        return cls(**values, content_hash=digest)

    def verify(self):
        body = {name: getattr(self, name) for name in self.__dataclass_fields__ if name != "content_hash"}
        return self.content_hash == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class RealReferenceCoverageLedgerV2:
    amendment_id: str
    checkpoint7_comparison_ledger_id: str
    cases: tuple[RealReferenceCaseV2, ...]
    ledger_id: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        _ids((values["amendment_id"], values["checkpoint7_comparison_ledger_id"]), "ledger provenance")
        body = dict(values); digest = _digest(cls.__name__, body)
        return cls(**body, ledger_id=digest, content_hash=digest)

    def verify(self):
        body = {"amendment_id": self.amendment_id, "checkpoint7_comparison_ledger_id": self.checkpoint7_comparison_ledger_id, "cases": self.cases}
        return self.ledger_id == self.content_hash == _digest(type(self).__name__, body) and all(x.verify() for x in self.cases)


@dataclass(frozen=True, slots=True)
class BoundaryExecutionV2:
    semantic_category: str
    evidence_class: EvidenceClass
    evidence_condition: str
    input_evidence_ids: tuple[str, ...]
    rejection_boundary: str
    expected_rejection_code: str
    observed_rejection_code: str
    assembler_invocation_count: int
    engine_invocation_count: int
    content_hash: str

    @classmethod
    def create(cls, **values):
        values["evidence_class"] = EvidenceClass(values["evidence_class"]); _ids(values["input_evidence_ids"], "boundary evidence")
        digest = _digest(cls.__name__, values); return cls(**values, content_hash=digest)

    def verify(self):
        body = {n: getattr(self, n) for n in self.__dataclass_fields__ if n != "content_hash"}
        return self.content_hash == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class FailClosedBoundaryLedgerV2:
    amendment_id: str
    cases: tuple[BoundaryExecutionV2, ...]
    ledger_id: str
    content_hash: str

    @classmethod
    def create(cls, *, amendment_id: str, cases: tuple[BoundaryExecutionV2, ...]):
        _ids((amendment_id,), "amendment"); body = {"amendment_id": amendment_id, "cases": cases}; digest = _digest(cls.__name__, body)
        return cls(**body, ledger_id=digest, content_hash=digest)

    def verify(self):
        body = {"amendment_id": self.amendment_id, "cases": self.cases}
        return self.ledger_id == self.content_hash == _digest(type(self).__name__, body) and all(x.verify() for x in self.cases)


@dataclass(frozen=True, slots=True)
class CalculationEdgeFixtureV2:
    name: str
    evidence_class: EvidenceClass
    reference_price: str
    sessions: tuple[str, ...]
    highs: tuple[str, ...]
    lows: tuple[str, ...]
    closes: tuple[str, ...]
    expected_outcome: str
    fixture_id: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        values["evidence_class"] = EvidenceClass(values["evidence_class"])
        body = dict(values); digest = _digest(cls.__name__, body)
        return cls(**body, fixture_id=digest, content_hash=digest)

    def verify(self):
        body = {n: getattr(self, n) for n in self.__dataclass_fields__ if n not in {"fixture_id", "content_hash"}}
        return self.fixture_id == self.content_hash == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class EdgeResultV2:
    outcome: str
    decisive_session: str
    return_5d: str
    mfe_5d: str
    mae_5d: str


@dataclass(frozen=True, slots=True)
class EdgeComparisonV2:
    fixture_id: str
    production: EdgeResultV2
    independent: EdgeResultV2
    disposition: str


@dataclass(frozen=True, slots=True)
class CalculationEdgeFixtureLedgerV2:
    amendment_id: str
    fixtures: tuple[CalculationEdgeFixtureV2, ...]
    comparisons: tuple[EdgeComparisonV2, ...]
    ledger_id: str
    content_hash: str

    @classmethod
    def create(cls, *, amendment_id: str, fixtures: tuple[CalculationEdgeFixtureV2, ...], comparisons: tuple[EdgeComparisonV2, ...]):
        body = {"amendment_id": amendment_id, "fixtures": fixtures, "comparisons": comparisons}; digest = _digest(cls.__name__, body)
        return cls(**body, ledger_id=digest, content_hash=digest)

    def verify(self):
        body = {"amendment_id": self.amendment_id, "fixtures": self.fixtures, "comparisons": self.comparisons}
        return self.ledger_id == self.content_hash == _digest(type(self).__name__, body) and all(x.verify() for x in self.fixtures)


@dataclass(frozen=True, slots=True)
class GateConsumptionV2:
    gate: str
    primary_layer: str
    artifact_ids: tuple[str, ...]
    predicate: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        _ids(values["artifact_ids"], "gate artifacts"); digest = _digest(cls.__name__, values); return cls(**values, content_hash=digest)

    def verify(self):
        body = {n: getattr(self, n) for n in self.__dataclass_fields__ if n != "content_hash"}
        return self.content_hash == _digest(type(self).__name__, body)


@dataclass(frozen=True, slots=True)
class GateArtifactConsumptionMapV2:
    amendment_id: str
    entries: tuple[GateConsumptionV2, ...]
    map_id: str
    content_hash: str

    @classmethod
    def create(cls, *, amendment_id: str, entries: tuple[GateConsumptionV2, ...]):
        body = {"amendment_id": amendment_id, "entries": entries}; digest = _digest(cls.__name__, body)
        return cls(**body, map_id=digest, content_hash=digest)

    def verify(self):
        body = {"amendment_id": self.amendment_id, "entries": self.entries}
        return self.map_id == self.content_hash == _digest(type(self).__name__, body) and all(x.verify() for x in self.entries)


@dataclass(frozen=True, slots=True)
class Phase2AAcceptanceV2:
    amendment_id: str
    layer_a_ledger_id: str
    layer_b_ledger_id: str
    layer_c_ledger_id: str
    gate_map_id: str
    gate_results: tuple[tuple[str, str], ...]
    phase_2a_status: str
    ready_for_phase_2b: bool
    artifact_id: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        body = dict(values); digest = _digest(cls.__name__, body)
        return cls(**body, artifact_id=digest, content_hash=digest)

    def verify(self):
        body = {n: getattr(self, n) for n in self.__dataclass_fields__ if n not in {"artifact_id", "content_hash"}}
        return self.artifact_id == self.content_hash == _digest(type(self).__name__, body)
