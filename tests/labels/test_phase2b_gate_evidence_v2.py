"""Gate V2 calculation evidence must come from an independent calculator."""

from datetime import date
from dataclasses import fields, replace
from decimal import Decimal
from pathlib import Path

import pytest

from v5_2.labels.calculation import BarrierCalculationV1
from v5_2.labels.contracts import (
    BarrierOutcomeV1, LabelReasonCode, LabelResultV1, LabelState, LabelValueV1,
)
from v5_2.labels.dataset_contracts import LabelPartitionV1, LabelRowV1, _digest
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.partition_store import write_partition
from v5_2.labels.phase2b_gate_evidence_v2 import (
    compare_row_independently, _derive_partition_comparisons,
    derive_partition_comparisons_exact,
    read_row_comparison_ledger_exact, write_row_comparison_ledger,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="approved five-domain source artifacts are not installed",
)


@pytest.fixture(scope="module")
def source_pair():
    producer = HistoricalFiveDomainProducerV1.load_exact(ROOT)
    anchor, lineage, window = producer.produce_anchor("000001.SZ", date(2024, 1, 2))
    bundle = producer.assemble(anchor, lineage, window)
    result = ReferenceLabelEngine().evaluate(bundle)
    row = LabelRowV1.create(result=result, bundle=bundle,
                            materialization_version="phase2b-v1")
    return producer, bundle, result, row


def test_real_row_matches_independent_reference_and_exact_lineage(source_pair):
    _, bundle, _, row = source_pair
    compared = compare_row_independently(row, bundle)
    assert compared.verify() and compared.matched
    assert compared.state_match and compared.reason_match
    assert compared.numeric_match and compared.barrier_match
    assert compared.lineage_match


def test_count_preserving_rehashed_return_mutation_is_not_self_approved(source_pair):
    _, bundle, result, row = source_pair
    changed = LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE,
                                  Decimal("0.90000000"),
                                  horizon_end_session=result.values[0].horizon_end_session,
                                  observed_at=result.values[0].observed_at,
                                  input_fact_ids=result.values[0].input_fact_ids)
    altered_result = LabelResultV1.create(result.canonical_security_identity,
        result.anchor_session, (changed, *result.values[1:]), bundle.content_hash,
        result.barrier_evidence)
    altered = LabelRowV1.create(result=altered_result, bundle=bundle,
                                materialization_version="phase2b-v1")
    assert altered.verify() and altered.row_id != row.row_id
    compared = compare_row_independently(altered, bundle)
    assert not compared.matched and not compared.numeric_match


def test_count_preserving_rehashed_barrier_mutation_is_not_self_approved(source_pair):
    _, bundle, result, _ = source_pair
    original = result.barrier_evidence[0]
    altered_barrier = BarrierCalculationV1(
        BarrierOutcomeV1.UPPER_FIRST, original.first_decisive_session, True)
    altered_result = LabelResultV1.create(result.canonical_security_identity,
        result.anchor_session, result.values, bundle.content_hash,
        (altered_barrier, *result.barrier_evidence[1:]))
    altered = LabelRowV1.create(result=altered_result, bundle=bundle,
                                materialization_version="phase2b-v1")
    assert altered.verify()
    compared = compare_row_independently(altered, bundle)
    assert not compared.matched and not compared.barrier_match


@pytest.mark.parametrize("label_name", (
    "return_3d", "return_5d",
    "max_favorable_excursion_5d", "max_adverse_excursion_5d",
))
def test_rehashed_numeric_semantics_cannot_self_approve(source_pair, label_name):
    _, bundle, result, _ = source_pair
    index = next(i for i, value in enumerate(result.values)
                 if value.label_name == label_name)
    old = result.values[index]
    assert old.state is LabelState.LABEL_AVAILABLE
    forged = LabelValueV1.create(label_name, old.state, old.value + Decimal("1"),
        horizon_end_session=old.horizon_end_session, observed_at=old.observed_at,
        input_fact_ids=old.input_fact_ids)
    values = list(result.values)
    values[index] = forged
    altered = LabelRowV1.create(result=LabelResultV1.create(
        result.canonical_security_identity, result.anchor_session, tuple(values),
        bundle.content_hash, result.barrier_evidence), bundle=bundle,
        materialization_version="phase2b-v1")
    compared = compare_row_independently(altered, bundle)
    assert altered.verify() and not compared.matched and not compared.numeric_match


def test_rehashed_state_reason_and_lineage_mutations_cannot_self_approve(source_pair):
    _, bundle, result, row = source_pair
    old = result.values[0]
    forged = LabelValueV1.create(old.label_name, LabelState.NOT_LABEL_SAFE, None,
        LabelReasonCode.INPUT_LINEAGE_INVALID,
        horizon_end_session=old.horizon_end_session, observed_at=old.observed_at,
        input_fact_ids=old.input_fact_ids)
    altered = LabelRowV1.create(result=LabelResultV1.create(
        result.canonical_security_identity, result.anchor_session,
        (forged, *result.values[1:]), bundle.content_hash,
        result.barrier_evidence), bundle=bundle,
        materialization_version="phase2b-v1")
    compared = compare_row_independently(altered, bundle)
    assert altered.verify() and not compared.matched
    assert not compared.state_match and not compared.reason_match

    altered_lineage = replace(row, domain_lineage_hashes=("a" * 64, *row.domain_lineage_hashes[1:]))
    body = {item.name: getattr(altered_lineage, item.name) for item in fields(altered_lineage)
            if item.name != "row_id"}
    altered_lineage = replace(altered_lineage, row_id=_digest("LabelRowV1", body))
    compared_lineage = compare_row_independently(altered_lineage, bundle)
    assert altered_lineage.verify() and not compared_lineage.matched
    assert not compared_lineage.lineage_match


def test_physical_partition_rederives_one_real_row_from_exact_source(source_pair, tmp_path):
    producer, _, _, row = source_pair
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="source-pinned-contract-fixture", rows=(row,))
    path = write_partition(tmp_path, partition, (row,))
    ledger = _derive_partition_comparisons(producer, path, partition.partition_id)
    assert ledger.verify() and ledger.checked_rows == 1
    assert ledger.mismatch_row_ids == ()
    assert ledger.partition_id == partition.partition_id
    evidence_path = write_row_comparison_ledger(tmp_path, ledger)
    assert write_row_comparison_ledger(tmp_path, ledger) == evidence_path
    assert read_row_comparison_ledger_exact(evidence_path, ledger.ledger_id) == ledger
    evidence_path.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        read_row_comparison_ledger_exact(evidence_path, ledger.ledger_id)


def test_forged_but_self_consistent_physical_partition_still_mismatches(source_pair, tmp_path):
    producer, bundle, result, _ = source_pair
    old = result.values[0]
    forged_value = LabelValueV1.create(old.label_name, old.state,
        Decimal("0.90000000"), horizon_end_session=old.horizon_end_session,
        observed_at=old.observed_at, input_fact_ids=old.input_fact_ids)
    forged_result = LabelResultV1.create(result.canonical_security_identity,
        result.anchor_session, (forged_value, *result.values[1:]), bundle.content_hash,
        result.barrier_evidence)
    forged_row = LabelRowV1.create(result=forged_result, bundle=bundle,
                                   materialization_version="phase2b-v1")
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="forged-contract-fixture", rows=(forged_row,))
    path = write_partition(tmp_path, partition, (forged_row,))
    ledger = _derive_partition_comparisons(producer, path, partition.partition_id)
    assert ledger.verify() and ledger.checked_rows == 1
    assert ledger.mismatch_row_ids == (forged_row.row_id,)


def test_formal_entrypoint_reloads_exact_source_and_rejects_caller_hashes(source_pair, tmp_path):
    _, _, _, row = source_pair
    partition = LabelPartitionV1.create(partition_key="2024-01",
        generation_id="formal-source-contract-fixture", rows=(row,))
    path = write_partition(tmp_path, partition, (row,))
    ledger = derive_partition_comparisons_exact(ROOT, path, partition.partition_id)
    assert ledger.verify() and ledger.checked_rows == 1
    assert ledger.mismatch_row_ids == ()
