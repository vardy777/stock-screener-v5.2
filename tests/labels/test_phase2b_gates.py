from dataclasses import replace

import pytest

from tests.labels.test_phase2b_coverage import REASONS, inputs as coverage_inputs, row
from v5_2.labels.contracts import LabelState
from v5_2.labels.dataset_contracts import CoverageAccountingV1, LabelDatasetManifestV1, LabelPartitionV1
from v5_2.labels.phase2b_gates import (
    PHASE2B_GATES,
    GatePredicateEvidenceV1,
    Phase2BGateInputsV1,
    evaluate_phase2b_gates,
)


def gate_fixture():
    dispositions, rows = coverage_inputs()
    ordered = tuple(sorted(rows, key=lambda item: (item.anchor_session, item.canonical_security_identity)))
    partition = LabelPartitionV1.create(partition_key="2024-01", generation_id="g1", rows=ordered)
    manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(partition,), partition_supersession=(),
        phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,),
    )
    evidence = tuple(GatePredicateEvidenceV1.create(
        name, f"{index + 1:064x}", f"{index + 1:064x}", (f"{index + 20:064x}",),
    ) for index, name in enumerate(PHASE2B_GATES))
    expected_row_lineage = tuple(sorted(
        (item.row_id, item.domain_lineage_hashes) for item in ordered
    ))
    return Phase2BGateInputsV1(
        contract_version="v5.2-label-contract-v1",
        coverage=CoverageAccountingV1.from_dispositions(dispositions, ordered),
        dispositions=dispositions,
        rows=ordered,
        partitions=((partition, ordered),),
        manifest=manifest,
        expected_manifest_id=manifest.manifest_id,
        expected_partition_ids=(partition.partition_id,),
        expected_lineage_ids=("a" * 64,),
        expected_row_lineage=expected_row_lineage,
        predicate_evidence=evidence,
    )


def test_equal_caller_hashes_cannot_establish_formal_semantic_pass():
    evaluation = evaluate_phase2b_gates(gate_fixture())
    assert not evaluation.all_pass
    assert tuple(item.gate for item in evaluation.results) == PHASE2B_GATES
    assert all(item.status == "FAIL" and item.failure_code == f"{item.gate}_FORMAL_EVIDENCE_MISSING"
               for item in evaluation.results)


@pytest.mark.parametrize("gate", PHASE2B_GATES)
def test_each_gate_fails_closed_on_semantic_evidence_mismatch(gate):
    source = gate_fixture()
    evidence = tuple(
        replace(item, observed_hash="0" * 64) if item.gate == gate else item
        for item in source.predicate_evidence
    )
    result = evaluate_phase2b_gates(replace(source, predicate_evidence=evidence))
    assert not result.all_pass
    assert next(item for item in result.results if item.gate == gate).status == "FAIL"


def test_count_preserving_reason_swap_fails_coverage_gate():
    source = gate_fixture()
    mutated = (
        *source.rows[:2], row(3, LabelState.NOT_LABEL_SAFE, REASONS[1]),
        row(4, LabelState.NOT_LABEL_SAFE, REASONS[0]), *source.rows[4:],
    )
    result = evaluate_phase2b_gates(replace(source, rows=mutated))
    assert next(item for item in result.results if item.gate == "HISTORICAL_COVERAGE_ACCOUNTING").status == "FAIL"


@pytest.mark.parametrize("field,gate", [
    ("expected_manifest_id", "MANIFEST_INTEGRITY"),
    ("expected_partition_ids", "PARTITION_INTEGRITY"),
    ("expected_lineage_ids", "LINEAGE_INTEGRITY"),
])
def test_exact_cross_artifact_pins_fail_closed(field, gate):
    source = gate_fixture()
    bad = "0" * 64 if field == "expected_manifest_id" else ("0" * 64,)
    result = evaluate_phase2b_gates(replace(source, **{field: bad}))
    assert next(item for item in result.results if item.gate == gate).status == "FAIL"


def test_count_preserving_row_lineage_swap_fails_lineage_gate():
    source = gate_fixture()
    first_id, first_lineage = source.expected_row_lineage[0]
    swapped = (
        (first_id, tuple(reversed(first_lineage))),
        *source.expected_row_lineage[1:],
    )
    result = evaluate_phase2b_gates(replace(source, expected_row_lineage=tuple(sorted(swapped))))
    assert next(item for item in result.results if item.gate == "LINEAGE_INTEGRITY").status == "FAIL"
