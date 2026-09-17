"""Phase 2A full 22-slot verification and frozen gate evaluation.

This module is an offline orchestrator.  The independent arithmetic lives in
``independent_reference`` and deliberately has no dependency on the production
engine or its calculation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import (
    ACCEPTANCE_GATES,
    FullComparisonLedgerV1,
    Phase2AAcceptanceArtifactV1,
    build_frozen_inventory,
    build_full_comparison_entry,
)
from v5_2.labels.contracts import CORE_LABELS, LabelContractV1, REQUIRED_LABEL_DOMAINS
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.independent_reference import calculate_independent_reference


@dataclass(frozen=True, slots=True)
class Phase2AExitVerificationV1:
    inventory_id: str
    bundles: tuple[object, ...]
    production_results: tuple[object, ...]
    independent_results: tuple[object, ...]
    comparison_ledger: FullComparisonLedgerV1
    acceptance: Phase2AAcceptanceArtifactV1
    provider_requests: int
    network_calls: int
    replay_hash: str


def _states(result) -> set[str]:
    return {item.state.value for item in result.values}


def _reasons(result) -> set[str]:
    return {item.reason_code.value for item in result.values if item.reason_code}


def _gate_statuses(*, inventory, bundles, production, independent, ledger,
                   replay_equal: bool) -> tuple[tuple[str, str], ...]:
    by_slot = {slot.slot: (slot, bundle, actual, expected, comparison)
               for slot, bundle, actual, expected, comparison in zip(
                   inventory.slots, bundles, production, independent, ledger.entries)}
    all_match = all(item.disposition == "MATCH" for item in ledger.entries)
    exact_contract = (
        LabelContractV1().contract_version == "v5.2-label-contract-v1"
        and tuple(LabelContractV1().required_domains) == REQUIRED_LABEL_DOMAINS
        and len(CORE_LABELS) == 7
        and all(tuple(item.domain for item in bundle.domain_lineage) == REQUIRED_LABEL_DOMAINS
                for bundle in bundles)
    )
    lineage_safe = all(item.lineage_validation for item in ledger.entries)
    exact_sessions = all(
        len(bundle.approved_exchange_sessions) == 6
        and bundle.approved_exchange_sessions[0] == slot.anchor_session
        and tuple(sorted(set(bundle.approved_exchange_sessions))) == bundle.approved_exchange_sessions
        and expected.horizons == (
            bundle.approved_exchange_sessions[1],
            bundle.approved_exchange_sessions[3],
            bundle.approved_exchange_sessions[5],
        )
        for slot, bundle, _actual, expected, _comparison in by_slot.values()
    )
    available_numeric_match = all(
        item.numeric_match for item in ledger.entries
    )
    barriers_match = all(
        item.barrier_categorical_match and item.barrier_decisive_session_match
        for item in ledger.entries
    )
    ca_safe = (
        "LABEL_AVAILABLE" in _states(by_slot[6][2])
        and "LABEL_AVAILABLE" in _states(by_slot[7][2])
        and "UNSUPPORTED_CORPORATE_ACTION" in _reasons(by_slot[17][2])
    )
    suspension_safe = (
        "NOT_LABEL_SAFE" in _states(by_slot[11][2])
        and "ANCHOR_BAR_MISSING" in _reasons(by_slot[11][2])
        and all(by_slot[number][4].disposition == "MATCH" for number in (8, 9, 10, 11))
    )
    delisting_safe = "DELISTING_IN_HORIZON" in _reasons(by_slot[14][2])
    identity_safe = by_slot[15][4].lineage_validation and by_slot[15][4].disposition == "MATCH"
    missing_safe = "EXPECTED_BAR_MISSING" in _reasons(by_slot[16][2])
    pending_safe = "LABEL_PENDING" in _states(by_slot[18][2])
    not_safe = all("NOT_LABEL_SAFE" in _states(by_slot[number][2]) for number in (11, 14, 16, 17, 22))
    stratum_applicable = (
        ca_safe and missing_safe and pending_safe and delisting_safe
        and "BARRIER_PATH_AMBIGUOUS" in _reasons(by_slot[22][2])
    )
    checks = (
        exact_contract,
        lineage_safe,
        exact_sessions,
        available_numeric_match,
        available_numeric_match,
        barriers_match,
        ca_safe,
        suspension_safe,
        delisting_safe,
        identity_safe,
        missing_safe,
        pending_safe,
        not_safe,
        inventory.verify() and len(bundles) == len(production) == len(independent) == 22
        and stratum_applicable,
        ledger.verify() and all_match,
        replay_equal,
    )
    return tuple((name, "PASS" if passed else "FAIL")
                 for name, passed in zip(ACCEPTANCE_GATES, checks))


def run_phase2a_exit_verification(repository_root) -> Phase2AExitVerificationV1:
    root = repository_root
    inventory = build_frozen_inventory()
    if not inventory.verify():
        raise ValueError("tampered frozen inventory")
    assembler = Phase2AEvidenceAssemblerV1(root)
    engine = ReferenceLabelEngine()
    bundles = tuple(assembler.assemble(slot) for slot in inventory.slots)
    production = tuple(engine.evaluate(bundle) for bundle in bundles)
    independent = tuple(
        calculate_independent_reference(slot.slot, bundle)
        for slot, bundle in zip(inventory.slots, bundles)
    )
    entries = tuple(
        build_full_comparison_entry(slot, bundle, actual, expected)
        for slot, bundle, actual, expected in zip(
            inventory.slots, bundles, production, independent
        )
    )
    ledger = FullComparisonLedgerV1.create(entries=entries)
    replay_production = tuple(engine.evaluate(bundle).content_hash for bundle in bundles)
    replay_independent = tuple(
        calculate_independent_reference(slot.slot, bundle).content_hash
        for slot, bundle in zip(inventory.slots, bundles)
    )
    replay_hash = content_hash((replay_production, replay_independent))
    replay_equal = (
        replay_production == tuple(item.content_hash for item in production)
        and replay_independent == tuple(item.content_hash for item in independent)
    )
    statuses = _gate_statuses(
        inventory=inventory, bundles=bundles, production=production,
        independent=independent, ledger=ledger, replay_equal=replay_equal,
    )
    acceptance = Phase2AAcceptanceArtifactV1.create(
        statuses=statuses,
        evidence_ids=(inventory.inventory_id, ledger.ledger_id, replay_hash),
    )
    return Phase2AExitVerificationV1(
        inventory.inventory_id, bundles, production, independent, ledger,
        acceptance, 0, 0, replay_hash,
    )
