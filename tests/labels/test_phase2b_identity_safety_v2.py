"""Exact approved Master graph controls identity boundary and quarantine."""

from datetime import date
from pathlib import Path

import pytest

from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.phase2b_identity_safety_v2 import (
    compare_identity_boundary_to_source, derive_identity_safety_evidence_exact,
    read_identity_safety_evidence_exact, write_identity_safety_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


def test_wrong_canonical_or_transition_boundary_fails_identity_gate():
    producer = HistoricalFiveDomainProducerV1.load_exact(ROOT)
    fact = producer.master.resolve("300114.SZ", date(2025, 2, 14))
    intervals = producer.master._facts_by_provider[fact.provider_identity].intervals
    assert compare_identity_boundary_to_source(
        "300114.SZ", date(2025, 2, 17), fact, intervals)
    assert not compare_identity_boundary_to_source(
        "302132.SZ", date(2025, 2, 17), fact, intervals)
    assert not compare_identity_boundary_to_source(
        "300114.SZ", date(2025, 2, 16), fact, intervals)


def test_real_identity_scope_is_exact_and_content_addressed(tmp_path):
    evidence = derive_identity_safety_evidence_exact(ROOT)
    assert evidence.verify()
    assert evidence.scoped_reason == "IDENTITY_TRANSITION_WINDOW_UNRESOLVED"
    assert evidence.transition_effective == "2025-02-17"
    path = write_identity_safety_evidence(tmp_path, evidence)
    assert read_identity_safety_evidence_exact(path, evidence.evidence_id) == evidence
    with pytest.raises(ValueError):
        read_identity_safety_evidence_exact(path, "f" * 64)
