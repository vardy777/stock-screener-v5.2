"""Field-specific gate evidence is independently calculated, never self-attested."""

from dataclasses import fields, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from v5_2.labels.calculation import BarrierCalculationV1
from v5_2.labels.contracts import (
    BarrierOutcomeV1, LabelResultV1, LabelValueV1, _hash_body,
)
from v5_2.labels.dataset_contracts import LabelPartitionV1, LabelRowV1, _digest
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.partition_store import write_partition
from v5_2.labels.phase2b_semantic_gate_evidence_v2 import (
    compare_semantic_gates, derive_semantic_group_ledger_exact,
    read_semantic_group_ledger_exact, write_semantic_group_ledger,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


@pytest.fixture(scope="module")
def real_pair():
    producer = HistoricalFiveDomainProducerV1.load_exact(ROOT)
    anchor, lineage, window = producer.produce_anchor("000001.SZ", date(2024, 1, 2))
    bundle = producer.assemble(anchor, lineage, window)
    result = ReferenceLabelEngine().evaluate(bundle)
    row = LabelRowV1.create(result=result, bundle=bundle,
                            materialization_version="phase2b-v1")
    return bundle, result, row


def changed_value_row(bundle, result, label_name):
    index = next(i for i, value in enumerate(result.values)
                 if value.label_name == label_name)
    old = result.values[index]
    assert old.value is not None
    changed = LabelValueV1.create(label_name, old.state,
        old.value + Decimal("1"), horizon_end_session=old.horizon_end_session,
        observed_at=old.observed_at, input_fact_ids=old.input_fact_ids)
    values = list(result.values)
    values[index] = changed
    altered = LabelResultV1.create(result.canonical_security_identity,
        result.anchor_session, tuple(values), bundle.content_hash,
        result.barrier_evidence)
    return LabelRowV1.create(result=altered, bundle=bundle,
                             materialization_version="phase2b-v1")


def test_real_row_has_independent_field_specific_evidence(real_pair):
    bundle, _, row = real_pair
    evidence = compare_semantic_gates(row, bundle)
    assert evidence.verify()
    assert evidence.passed_gates == (
        "STATE_SEMANTICS", "RETURN_SEMANTICS", "MFE_MAE_SEMANTICS",
        "BARRIER_SEMANTICS")
    assert evidence.failed_gates == ()


@pytest.mark.parametrize("label_name,failed_gate", (
    ("return_1d", "RETURN_SEMANTICS"),
    ("return_3d", "RETURN_SEMANTICS"),
    ("return_5d", "RETURN_SEMANTICS"),
    ("max_favorable_excursion_5d", "MFE_MAE_SEMANTICS"),
    ("max_adverse_excursion_5d", "MFE_MAE_SEMANTICS"),
))
def test_rehashed_numeric_mutation_fails_only_its_semantic_group(
        real_pair, label_name, failed_gate):
    bundle, result, _ = real_pair
    forged = changed_value_row(bundle, result, label_name)
    assert forged.verify()
    evidence = compare_semantic_gates(forged, bundle)
    assert evidence.verify()
    assert evidence.failed_gates == (failed_gate,)
    assert len(evidence.passed_gates) == 3


def test_formal_semantic_ledger_reloads_physical_row_and_exact_sources(real_pair, tmp_path):
    _, _, row = real_pair
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="semantic-gate-fixture", rows=(row,))
    path = write_partition(tmp_path, partition, (row,))
    ledger = derive_semantic_group_ledger_exact(ROOT, path, partition.partition_id)
    assert ledger.verify()
    assert ledger.checked_rows == 1
    assert ledger.failed_row_ids_by_gate == (
        ("STATE_SEMANTICS", ()), ("RETURN_SEMANTICS", ()),
        ("MFE_MAE_SEMANTICS", ()), ("BARRIER_SEMANTICS", ()),
    )
    saved = write_semantic_group_ledger(tmp_path, ledger)
    assert read_semantic_group_ledger_exact(saved, ledger.ledger_id) == ledger
    saved.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        read_semantic_group_ledger_exact(saved, ledger.ledger_id)


def test_formal_semantic_ledger_detects_rehashed_numeric_mutation(real_pair, tmp_path):
    bundle, result, _ = real_pair
    forged = changed_value_row(bundle, result, "return_3d")
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="semantic-mutation-fixture", rows=(forged,))
    path = write_partition(tmp_path, partition, (forged,))
    ledger = derive_semantic_group_ledger_exact(ROOT, path, partition.partition_id)
    assert ledger.verify()
    assert ledger.failed_row_ids_by_gate[1] == ("RETURN_SEMANTICS", (forged.row_id,))
    assert ledger.lineage_mismatch_row_ids == ()
    assert all(not ids for gate, ids in ledger.failed_row_ids_by_gate
               if gate != "RETURN_SEMANTICS")


def test_rehashed_barrier_outcome_fails_only_barrier_gate(real_pair):
    bundle, result, _ = real_pair
    original = result.barrier_evidence[0]
    forged_barrier = BarrierCalculationV1(
        BarrierOutcomeV1.UPPER_FIRST, original.first_decisive_session, True)
    forged_result = LabelResultV1.create(result.canonical_security_identity,
        result.anchor_session, result.values, bundle.content_hash,
        (forged_barrier, *result.barrier_evidence[1:]))
    forged = LabelRowV1.create(result=forged_result, bundle=bundle,
                               materialization_version="phase2b-v1")
    assert forged.verify()
    evidence = compare_semantic_gates(forged, bundle)
    assert evidence.failed_gates == ("BARRIER_SEMANTICS",)


def test_numeric_mutation_does_not_masquerade_as_lineage_failure(real_pair):
    bundle, result, row = real_pair
    numeric = compare_semantic_gates(
        changed_value_row(bundle, result, "return_1d"), bundle)
    assert numeric.lineage_match
    swapped = replace(row, domain_lineage_hashes=(
        "a" * 64, *row.domain_lineage_hashes[1:]))
    body = {field.name: getattr(swapped, field.name) for field in fields(swapped)
            if field.name != "row_id"}
    swapped = replace(swapped, row_id=_digest("LabelRowV1", body))
    assert swapped.verify()
    assert not compare_semantic_gates(swapped, bundle).lineage_match


def test_available_without_numeric_evidence_fails_state_semantics(real_pair):
    bundle, result, _ = real_pair
    original = result.values[0]
    assert original.value is not None
    invalid = replace(original, value=None)
    body = {field.name: getattr(invalid, field.name) for field in fields(invalid)
            if field.name != "content_hash"}
    invalid = replace(invalid, content_hash=_hash_body("LabelValueV1", body))
    altered = LabelResultV1.create(result.canonical_security_identity,
        result.anchor_session, (invalid, *result.values[1:]),
        bundle.content_hash, result.barrier_evidence)
    forged = LabelRowV1.create(result=altered, bundle=bundle,
                               materialization_version="phase2b-v1")
    assert forged.verify()
    evidence = compare_semantic_gates(forged, bundle)
    assert "STATE_SEMANTICS" in evidence.failed_gates


def test_unknown_rehashed_state_is_rejected_without_crashing_formal_gate(real_pair):
    bundle, result, _ = real_pair
    invalid = replace(result.values[0], state="UNKNOWN")
    body = {field.name: getattr(invalid, field.name) for field in fields(invalid)
            if field.name != "content_hash"}
    invalid = replace(invalid, content_hash=_hash_body("LabelValueV1", body))
    altered = LabelResultV1.create(result.canonical_security_identity,
        result.anchor_session, (invalid, *result.values[1:]),
        bundle.content_hash, result.barrier_evidence)
    forged = LabelRowV1.create(result=altered, bundle=bundle,
                               materialization_version="phase2b-v1")
    with pytest.raises(ValueError, match="unknown label state"):
        compare_semantic_gates(forged, bundle)
