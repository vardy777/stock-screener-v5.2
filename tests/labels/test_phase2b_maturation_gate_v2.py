"""Maturation gate uses the frozen real Phase 2A bundle and independent math."""

from pathlib import Path
from decimal import Decimal

import pytest

from v5_2.labels.phase2b_maturation_gate_v2 import (
    derive_maturation_gate_evidence_exact,
    maturation_result_matches_independent,
    read_maturation_gate_evidence_exact, write_maturation_gate_evidence,
)
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.contracts import LabelInputBundleV1, LabelResultV1, LabelState, LabelValueV1
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.independent_reference import calculate_independent_reference


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/phase_2a/v2_1_final_acceptance").is_dir(),
    reason="frozen Phase 2A real bundle is unavailable",
)


def test_real_slot4_maturation_respects_h0_h1_h3_h5_and_barrier_cutoff(tmp_path):
    evidence = derive_maturation_gate_evidence_exact(ROOT)
    assert evidence.verify()
    assert evidence.base_bundle_id == (
        "8a212db4e0337eaceaf90ddf167ce9b278cd9adde05c584f826a6006c99125fa")
    assert evidence.pending_counts == (7, 6, 5, 0)
    assert evidence.available_counts == (0, 1, 2, 7)
    assert evidence.mismatch_stages == ()
    assert evidence.h1_early_barrier_hit is True
    assert evidence.h1_barrier_published is False
    path = write_maturation_gate_evidence(tmp_path, evidence)
    assert read_maturation_gate_evidence_exact(path, evidence.evidence_id) == evidence
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        read_maturation_gate_evidence_exact(path, evidence.evidence_id)


def test_rehashed_pending_to_available_without_h5_evidence_is_rejected():
    slot = next(item for item in build_frozen_inventory().slots if item.slot == 4)
    base = Phase2AEvidenceAssemblerV1(ROOT).assemble(slot)
    body = {key: getattr(base, key) for key in base.__dataclass_fields__
            if key != "content_hash"}
    body["latest_completed_session"] = base.approved_exchange_sessions[1]
    h1 = LabelInputBundleV1.create(**body)
    truth = calculate_independent_reference(1, base)
    good = ReferenceLabelEngine().evaluate(h1)
    assert maturation_result_matches_independent(good, truth, 1)
    values = list(good.values)
    values[2] = LabelValueV1.create("return_5d", LabelState.LABEL_AVAILABLE,
                                   Decimal("-0.02453988"))
    forged = LabelResultV1.create(good.canonical_security_identity,
        good.anchor_session, tuple(values), h1.content_hash,
        good.barrier_evidence)
    assert forged.verify()
    assert not maturation_result_matches_independent(forged, truth, 1)
