from __future__ import annotations

from collections.abc import Callable

from v5_2.labels.acceptance import ACCEPTANCE_GATES
from v5_2.labels.acceptance_v2_contracts import (
    EvidenceClass,
    GateArtifactConsumptionMapV2_1,
    GateConsumptionV2_1,
    GateEvaluationV2_1,
    GateEvidenceV2_1,
    GatePredicateIdV2_1,
)
from v5_2.labels.acceptance_v2_layer_a import validate_mandatory_real_roles_v2_1
from v5_2.labels.acceptance_v2_layer_c import validate_edge_semantics_v2_1


def _roles(evidence: GateEvidenceV2_1) -> set[str]:
    return {role for case in evidence.layer_a.cases for role in case.semantic_roles}


def _a_match(evidence: GateEvidenceV2_1, roles: set[str]) -> bool:
    return roles <= _roles(evidence) and all(
        case.verify() and case.disposition == "MATCH" and case.evidence_class is EvidenceClass.REAL_MARKET_EVIDENCE
        for case in evidence.layer_a.cases if roles & set(case.semantic_roles)
    )


def _boundary(evidence: GateEvidenceV2_1, category: str):
    return next((case for case in evidence.layer_b.cases if case.semantic_category == category), None)


def _pre_engine(case) -> bool:
    return bool(
        case and case.verify() and bool(case.rejection_boundary)
        and case.assembler_invocation_count in {0, 1} and case.engine_invocation_count == 0
        and case.observed_rejection_code == case.expected_rejection_code
    )


def _label_contract(e):
    return e.contract_identity_verified and e.exact_five_domains_verified and all(len(x.five_domain_lineage_ids) == 5 for x in e.layer_a.cases)


def _causal_isolation(e):
    return e.ast_isolation_verified and all(_pre_engine(case) for case in e.layer_b.cases)


def _trading_session_semantics(e):
    return _a_match(e, {"FIRST_IPO-ELIGIBLE_BOUNDARY", "STILL_INSIDE_IPO_SEASONING", "DELISTING_BOUNDARY"})


def _return_semantics(e):
    return _a_match(e, {"NORMAL_POSITIVE_RETURN", "NORMAL_NEGATIVE_RETURN", "HIGH_VOLATILITY", "LIMIT-UP-LIKE_PATH", "LIMIT-DOWN-LIKE_PATH"})


def _mfe_mae_semantics(e):
    return _a_match(e, {"HIGH_VOLATILITY", "NORMAL_POSITIVE_RETURN", "NORMAL_NEGATIVE_RETURN", "D+1_FULL-DAY_SUSPENSION"})


def _barrier_semantics(e):
    return validate_edge_semantics_v2_1(e.layer_c) and _a_match(e, {"ACTUAL_UPPER_FIRST_REAL_PATH", "ACTUAL_LOWER_FIRST_REAL_PATH", "ACTUAL_LOWER_FIRST_AND_NEITHER_REAL_PATH"})


def _corporate_action_safety(e):
    case = _boundary(e, "UNSUPPORTED_CA")
    return _a_match(e, {"CASH_DIVIDEND", "BONUS_SHARE"}) and _pre_engine(case) and bool(
        case.provenance.real_condition_observed
        and case.provenance.boundary_exercise_class == "REAL_UNSUPPORTED_MARKET_EVENT"
        and case.observed_condition == ("002029.SZ", "2012-05-08", "UNSUPPORTED_SHARE_CONVERSION")
    )


def _suspension_safety(e):
    return _a_match(e, {"D+1_FULL-DAY_SUSPENSION", "MULTI-DAY_SUSPENSION", "SUSPENSION_THROUGH_H5", "RESUMPTION_BEFORE_H5"})


def _delisting_safety(e):
    return _a_match(e, {"DELISTING_BOUNDARY"})


def _identity_safety(e):
    return _a_match(e, {"IDENTITY_TRANSITION"}) and _pre_engine(_boundary(e, "AMBIGUOUS_IDENTITY"))


def _missing_data_fail_closed(e):
    required = {"UNEXPLAINED_MISSING_BAR", "MISSING_REQUIRED_DOMAIN", "MALFORMED_CALENDAR", "TAMPERED_ARTIFACT"}
    return all(_pre_engine(_boundary(e, category)) for category in required) and bool(
        _boundary(e, "UNEXPLAINED_MISSING_BAR").transform_id
        and not _boundary(e, "UNEXPLAINED_MISSING_BAR").provenance.real_condition_observed
    )


def _label_pending(e):
    return _a_match(e, {"LATEST-SESSION_LABEL_PENDING"})


def _not_label_safe(e):
    return _a_match(e, {"MULTI-DAY_SUSPENSION", "SUSPENSION_THROUGH_H5", "RESUMPTION_BEFORE_H5", "DELISTING_BOUNDARY"})


def _reference_samples(e):
    return validate_mandatory_real_roles_v2_1(e.layer_a)


def _independent_verification(e):
    return all(case.disposition == "MATCH" for case in e.layer_a.cases) and validate_edge_semantics_v2_1(e.layer_c)


def _deterministic_replay(e):
    return bool(e.replay_bytes_match and e.amendment.verify() and e.layer_a.verify() and e.layer_b.verify() and e.layer_c.verify() and e.gate_map.verify())


GATE_PREDICATES_V2_1: dict[str, tuple[GatePredicateIdV2_1, Callable[[GateEvidenceV2_1], bool]]] = {
    "LABEL CONTRACT": (GatePredicateIdV2_1.LABEL_CONTRACT, _label_contract),
    "CAUSAL ISOLATION": (GatePredicateIdV2_1.CAUSAL_ISOLATION, _causal_isolation),
    "TRADING SESSION SEMANTICS": (GatePredicateIdV2_1.TRADING_SESSION_SEMANTICS, _trading_session_semantics),
    "RETURN SEMANTICS": (GatePredicateIdV2_1.RETURN_SEMANTICS, _return_semantics),
    "MFE/MAE SEMANTICS": (GatePredicateIdV2_1.MFE_MAE_SEMANTICS, _mfe_mae_semantics),
    "BARRIER SEMANTICS": (GatePredicateIdV2_1.BARRIER_SEMANTICS, _barrier_semantics),
    "CORPORATE ACTION SAFETY": (GatePredicateIdV2_1.CORPORATE_ACTION_SAFETY, _corporate_action_safety),
    "SUSPENSION SAFETY": (GatePredicateIdV2_1.SUSPENSION_SAFETY, _suspension_safety),
    "DELISTING SAFETY": (GatePredicateIdV2_1.DELISTING_SAFETY, _delisting_safety),
    "IDENTITY SAFETY": (GatePredicateIdV2_1.IDENTITY_SAFETY, _identity_safety),
    "MISSING DATA FAIL-CLOSED": (GatePredicateIdV2_1.MISSING_DATA_FAIL_CLOSED, _missing_data_fail_closed),
    "LABEL_PENDING": (GatePredicateIdV2_1.LABEL_PENDING, _label_pending),
    "NOT_LABEL_SAFE": (GatePredicateIdV2_1.NOT_LABEL_SAFE, _not_label_safe),
    "REFERENCE SAMPLES": (GatePredicateIdV2_1.REFERENCE_SAMPLES, _reference_samples),
    "INDEPENDENT VERIFICATION": (GatePredicateIdV2_1.INDEPENDENT_VERIFICATION, _independent_verification),
    "DETERMINISTIC REPLAY": (GatePredicateIdV2_1.DETERMINISTIC_REPLAY, _deterministic_replay),
}


def build_gate_consumption_map_v2_1(amendment, layer_a, layer_b, layer_c) -> GateArtifactConsumptionMapV2_1:
    ids = (amendment.artifact_id, layer_a.ledger_id, layer_b.ledger_id, layer_c.ledger_id)
    entries = tuple(
        GateConsumptionV2_1.create(gate=gate, predicate_id=GATE_PREDICATES_V2_1[gate][0], artifact_ids=ids)
        for gate in ACCEPTANCE_GATES
    )
    return GateArtifactConsumptionMapV2_1.create(amendment_id=amendment.artifact_id, entries=entries)


def evaluate_gate_v2_1(gate: str, evidence: GateEvidenceV2_1) -> GateEvaluationV2_1:
    if gate not in GATE_PREDICATES_V2_1:
        raise ValueError("exact gate name required")
    predicate_id, predicate = GATE_PREDICATES_V2_1[gate]
    entry = next((item for item in evidence.gate_map.entries if item.gate == gate), None)
    passed = bool(entry and entry.predicate_id is predicate_id and predicate(evidence))
    return GateEvaluationV2_1.create(gate=gate, predicate_id=predicate_id, status="PASS" if passed else "FAIL")
