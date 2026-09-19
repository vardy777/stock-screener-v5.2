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
    if not values or len(set(values)) != len(values) or any(len(value) not in {40, 64} for value in values):
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class BoundaryEvidenceProvenanceV2_1:
    base_evidence_class: str
    boundary_exercise_class: str
    real_condition_observed: bool
    real_condition_availability: str
    unavailability_evidence_id: str | None
    content_hash: str

    @classmethod
    def create(cls, **values):
        base = values["base_evidence_class"]
        exercise = values["boundary_exercise_class"]
        observed = values["real_condition_observed"]
        availability = values["real_condition_availability"]
        unavailable_id = values["unavailability_evidence_id"]
        allowed_base = {"NONE", "REAL_MARKET_EVIDENCE", "REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE"}
        allowed_exercise = {
            "DETERMINISTIC_CONTRACT_FIXTURE",
            "REAL_UNSUPPORTED_MARKET_EVENT",
            "PURE_SYNTHETIC_CALCULATION_FIXTURE",
        }
        if base not in allowed_base or exercise not in allowed_exercise:
            raise ValueError("invalid V2.1 provenance class")
        if exercise == "DETERMINISTIC_CONTRACT_FIXTURE" and observed:
            raise ValueError("fixture cannot be real observed")
        if exercise == "REAL_UNSUPPORTED_MARKET_EVENT" and not observed:
            raise ValueError("unsupported market event must be observed")
        if availability == "REAL_REFERENCE_SAMPLE_UNAVAILABLE":
            if observed or unavailable_id is None:
                raise ValueError("unavailable condition provenance invalid")
            _ids((unavailable_id,), "unavailability evidence")
        elif unavailable_id is not None:
            raise ValueError("unavailability evidence requires unavailable status")
        body = dict(values)
        return cls(**body, content_hash=_digest(cls.__name__, body))

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in self.__dataclass_fields__ if name != "content_hash"}
        try:
            rebuilt = type(self).create(**body)
        except ValueError:
            return False
        return self.content_hash == rebuilt.content_hash


@dataclass(frozen=True, slots=True)
class BoundaryExecutionV2_1:
    semantic_category: str
    provenance: BoundaryEvidenceProvenanceV2_1
    input_evidence_ids: tuple[str, ...]
    real_base_bundle_id: str | None
    real_base_lineage_ids: tuple[str, ...]
    transform_id: str | None
    transformed_evidence_id: str | None
    removed_session: str | None
    rejection_boundary: str
    expected_rejection_code: str
    observed_rejection_code: str
    assembler_invocation_count: int
    engine_invocation_count: int
    content_hash: str

    @classmethod
    def create(cls, **values):
        provenance = values["provenance"]
        if not provenance.verify():
            raise ValueError("invalid boundary provenance")
        if provenance.boundary_exercise_class == "PURE_SYNTHETIC_CALCULATION_FIXTURE":
            raise ValueError("calculation fixture cannot enter Layer B")
        _ids(values["input_evidence_ids"], "boundary evidence")
        base_id = values["real_base_bundle_id"]
        lineage = values["real_base_lineage_ids"]
        if base_id is not None:
            _ids((base_id,), "real base bundle")
        if lineage:
            _ids(lineage, "real base lineage")
            if len(lineage) != 5:
                raise ValueError("exact five-domain real base required")
        for name in ("transform_id", "transformed_evidence_id"):
            if values[name] is not None:
                _ids((values[name],), name)
        if values["engine_invocation_count"] != 0:
            raise ValueError("pre-engine boundary invoked engine")
        body = dict(values)
        return cls(**body, content_hash=_digest(cls.__name__, body))

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in self.__dataclass_fields__ if name != "content_hash"}
        try:
            rebuilt = type(self).create(**body)
        except ValueError:
            return False
        return self.content_hash == rebuilt.content_hash


@dataclass(frozen=True, slots=True)
class FailClosedBoundaryLedgerV2_1:
    amendment_id: str
    cases: tuple[BoundaryExecutionV2_1, ...]
    ledger_id: str
    content_hash: str

    @classmethod
    def create(cls, *, amendment_id: str, cases: tuple[BoundaryExecutionV2_1, ...]):
        _ids((amendment_id,), "amendment")
        if not cases or not all(case.verify() for case in cases):
            raise ValueError("invalid V2.1 boundary cases")
        body = {"amendment_id": amendment_id, "cases": cases}
        digest = _digest(cls.__name__, body)
        return cls(**body, ledger_id=digest, content_hash=digest)

    @property
    def real_observed_boundary_cases(self) -> int:
        return sum(case.provenance.real_condition_observed for case in self.cases)

    def verify(self) -> bool:
        body = {"amendment_id": self.amendment_id, "cases": self.cases}
        return (
            self.ledger_id == self.content_hash == _digest(type(self).__name__, body)
            and all(case.verify() for case in self.cases)
        )


@dataclass(frozen=True, slots=True)
class Phase2AAcceptanceArchitectureAmendmentV2_1:
    original_v2_design_commit: str
    original_v2_plan_commit: str
    plan_correction_commit: str
    v2_1_design_amendment_id: str
    v2_1_design_head: str
    checkpoint8_discovery_id: str
    supersedes_attempt1_amendment_id: str
    reason: str
    artifact_id: str
    content_hash: str

    @classmethod
    def create(cls, **values):
        _ids(tuple(values[name] for name in (
            "original_v2_design_commit", "original_v2_plan_commit", "plan_correction_commit",
            "v2_1_design_amendment_id", "v2_1_design_head", "checkpoint8_discovery_id",
            "supersedes_attempt1_amendment_id",
        )), "V2.1 authorities")
        if values["reason"] != "ACCEPTANCE_EVIDENCE_CLASSIFICATION_AND_GATE_EVALUATION_CORRECTION":
            raise ValueError("invalid V2.1 amendment reason")
        body = dict(values)
        digest = _digest(cls.__name__, body)
        return cls(**body, artifact_id=digest, content_hash=digest)

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in self.__dataclass_fields__ if name not in {"artifact_id", "content_hash"}}
        return self.artifact_id == self.content_hash == _digest(type(self).__name__, body)


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


def build_frozen_amendment_v2() -> Phase2AAcceptanceArchitectureAmendmentV2:
    layers = {16: ("B",), 17: ("B",), 22: ("A", "C")}
    behavior = {
        16: "UNEXPLAINED_MISSING_BAR_PRE_ENGINE_REJECTION",
        17: "UNSUPPORTED_CORPORATE_ACTION_PRE_ENGINE_REJECTION",
        20: "ACTUAL_REAL_UPPER_FIRST_PATH",
        21: "ACTUAL_REAL_LOWER_OR_NEITHER_PATH",
        22: "ACTUAL_REAL_LOWER_FIRST_PATH_PLUS_SYNTHETIC_AMBIGUITY_FIXTURE",
    }
    migration = tuple(MigrationEntryV2.create(
        slot=slot, layers=layers.get(slot, ("A",)),
        actual_behavior=behavior.get(slot, f"RETAINED_REAL_CASE_SLOT_{slot}"),
    ) for slot in range(1, 23))
    return Phase2AAcceptanceArchitectureAmendmentV2.create(
        design_commit="f92f0a564c802ddc28dc71153be44d409b6858ee",
        plan_commits=(
            "4db0f4ecb9e61853190f755d1bee164d9f84fe9a",
            "390149882f3265b778b736a16380c13d9a64652a",
        ),
        v1_artifact_ids=(
            "81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9",
            "84d61057ecf5f527dcb5067fe0ea2b6103edf0f66388535e8ceeffd3ef10c3c8",
            "236039b2286afaff54017317ceeedc08b8e4c40a5a94a676256167c85d96f4d4",
            "947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48",
        ),
        migration=migration,
    )


def build_frozen_amendment_v2_1() -> Phase2AAcceptanceArchitectureAmendmentV2_1:
    return Phase2AAcceptanceArchitectureAmendmentV2_1.create(
        original_v2_design_commit="f92f0a564c802ddc28dc71153be44d409b6858ee",
        original_v2_plan_commit="4db0f4ecb9e61853190f755d1bee164d9f84fe9a",
        plan_correction_commit="390149882f3265b778b736a16380c13d9a64652a",
        v2_1_design_amendment_id="d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b",
        v2_1_design_head="a66825e25d40a46eceae18a50f1f2535ab9ee975",
        checkpoint8_discovery_id="947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48",
        supersedes_attempt1_amendment_id=build_frozen_amendment_v2().artifact_id,
        reason="ACCEPTANCE_EVIDENCE_CLASSIFICATION_AND_GATE_EVALUATION_CORRECTION",
    )


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
        if any(case.evidence_class is not EvidenceClass.REAL_MARKET_EVIDENCE for case in values["cases"]):
            raise ValueError("Layer A requires REAL_MARKET_EVIDENCE")
        body = dict(values); digest = _digest(cls.__name__, body)
        return cls(**body, ledger_id=digest, content_hash=digest)

    @property
    def real_reference_cases(self) -> int:
        return len(self.cases)

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
        if any(case.evidence_class in {EvidenceClass.REAL_MARKET_EVIDENCE, EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE} for case in cases):
            raise ValueError("Layer B evidence classification invalid")
        return cls(**body, ledger_id=digest, content_hash=digest)

    @property
    def real_fail_closed_evidence_cases(self) -> int:
        return sum(case.evidence_class in {
            EvidenceClass.REAL_APPROVED_BOUNDARY_CONDITION,
            EvidenceClass.REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION,
        } for case in self.cases)

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
        if any(item.evidence_class is not EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE for item in fixtures):
            raise ValueError("Layer C requires SYNTHETIC_CONTRACT_FIXTURE")
        if tuple(item.fixture_id for item in comparisons) != tuple(item.fixture_id for item in fixtures):
            raise ValueError("fixture comparison identity mismatch")
        body = {"amendment_id": amendment_id, "fixtures": fixtures, "comparisons": comparisons}; digest = _digest(cls.__name__, body)
        return cls(**body, ledger_id=digest, content_hash=digest)

    @property
    def synthetic_contract_fixtures(self) -> int:
        return len(self.fixtures)

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
        from v5_2.labels.acceptance import ACCEPTANCE_GATES
        if tuple(item.gate for item in entries) != ACCEPTANCE_GATES:
            raise ValueError("exact 16 acceptance gates required")
        if not all(item.verify() for item in entries):
            raise ValueError("tampered gate consumption")
        body = {"amendment_id": amendment_id, "entries": entries}; digest = _digest(cls.__name__, body)
        return cls(**body, map_id=digest, content_hash=digest)

    def verify(self):
        body = {"amendment_id": self.amendment_id, "entries": self.entries}
        return self.map_id == self.content_hash == _digest(type(self).__name__, body) and all(x.verify() for x in self.entries)


def build_gate_consumption_map(amendment: Phase2AAcceptanceArchitectureAmendmentV2, *, layer_a_id: str, layer_b_id: str, layer_c_id: str) -> GateArtifactConsumptionMapV2:
    from v5_2.labels.acceptance import ACCEPTANCE_GATES
    if not amendment.verify():
        raise ValueError("invalid amendment")
    specifications = (
        ("A", (amendment.artifact_id, layer_a_id), "label_contract_verified"),
        ("B", (layer_b_id,), "causal_isolation_verified"),
        ("A", (layer_a_id,), "trading_sessions_match"),
        ("A", (layer_a_id,), "returns_match"),
        ("A", (layer_a_id,), "mfe_mae_match"),
        ("C+A", (layer_c_id, layer_a_id), "barrier_edges_and_real_paths_match"),
        ("A+B", (layer_a_id, layer_b_id), "supported_and_unsupported_ca_safe"),
        ("A", (layer_a_id,), "suspension_paths_match"),
        ("A", (layer_a_id,), "delisting_path_safe"),
        ("A+B", (layer_a_id, layer_b_id), "identity_and_rejections_safe"),
        ("B", (layer_b_id,), "missing_data_rejects_pre_engine"),
        ("A", (layer_a_id,), "pending_state_matches"),
        ("A", (layer_a_id,), "legal_bundle_unsafe_states_match"),
        ("A", (layer_a_id,), "mandatory_real_reference_coverage"),
        ("A+C", (layer_a_id, layer_c_id), "independent_comparisons_match"),
        ("CROSS_LAYER", (amendment.artifact_id, layer_a_id, layer_b_id, layer_c_id), "byte_identical_replay"),
    )
    entries = tuple(GateConsumptionV2.create(
        gate=gate, primary_layer=layer, artifact_ids=ids, predicate=predicate,
    ) for gate, (layer, ids, predicate) in zip(ACCEPTANCE_GATES, specifications))
    return GateArtifactConsumptionMapV2.create(amendment_id=amendment.artifact_id, entries=entries)


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
