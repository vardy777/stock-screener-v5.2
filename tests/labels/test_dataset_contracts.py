from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from v5_2.labels.contracts import (
    AnchorKnowledgeBoundary,
    DomainLineageV1,
    LabelInputBundleV1,
    LabelReasonCode,
    LabelReferencePrice,
    LabelResultV1,
    LabelState,
    LabelValueV1,
    ProvenancePath,
    REQUIRED_LABEL_DOMAINS,
)
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1


NOW = datetime(2026, 9, 19, tzinfo=timezone.utc)


def bundle_and_result():
    anchor = date(2024, 1, 2)
    lineages = tuple(
        DomainLineageV1.create(domain=domain, approval_id=(str(index) * 64), manifest_id=(str(index + 5) * 64), fact_ids=(("abcdef"[index]) * 64,))
        for index, domain in enumerate(REQUIRED_LABEL_DOMAINS)
    )
    bundle = LabelInputBundleV1.create(
        canonical_security_identity="000001.SZ",
        anchor_session=anchor,
        anchor_boundary=AnchorKnowledgeBoundary.create(anchor, NOW, "a" * 64, True),
        reference_price=LabelReferencePrice.create(anchor, Decimal("10"), "b" * 64, NOW),
        provenance_path=ProvenancePath.HISTORICAL,
        domain_lineage=lineages,
        approved_exchange_sessions=(anchor,),
        latest_completed_session=anchor,
    )
    values = (
        LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE, Decimal("0.01000000")),
        *tuple(LabelValueV1.create(name, LabelState.LABEL_PENDING, None, LabelReasonCode.HORIZON_NOT_COMPLETED) for name in (
            "return_3d", "return_5d", "max_favorable_excursion_5d", "max_adverse_excursion_5d",
            "hit_3pct_before_-2pct", "hit_5pct_before_-3pct",
        )),
    )
    return bundle, LabelResultV1.create("000001.SZ", anchor, values, bundle.content_hash)


def test_row_preserves_frozen_mixed_value_states_without_row_state():
    bundle, result = bundle_and_result()
    row = LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")
    assert [item.label_name for item in row.values] == [
        "return_1d", "return_3d", "return_5d", "max_favorable_excursion_5d",
        "max_adverse_excursion_5d", "hit_3pct_before_-2pct", "hit_5pct_before_-3pct",
    ]
    assert row.values[0].state is LabelState.LABEL_AVAILABLE
    assert all(value.state is LabelState.LABEL_PENDING for value in row.values[1:])
    assert not hasattr(row, "row_state")
    assert row.verify()


def test_row_rejects_invalid_nested_result_hash_and_changes_identity_for_value_change():
    bundle, result = bundle_and_result()
    with pytest.raises(ValueError, match="result"):
        LabelRowV1.create(result=replace(result, content_hash="0" * 64), bundle=bundle, materialization_version="phase2b-v1")
    first = LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")
    changed = LabelResultV1.create(
        result.canonical_security_identity, result.anchor_session,
        (LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE, Decimal("0.02000000")), *result.values[1:]),
        result.bundle_hash,
    )
    second = LabelRowV1.create(result=changed, bundle=bundle, materialization_version="phase2b-v1")
    assert first.row_id != second.row_id


def test_partition_rejects_duplicate_row_identity():
    bundle, result = bundle_and_result()
    row = LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")
    with pytest.raises(ValueError, match="duplicate"):
        LabelPartitionV1.create(partition_key="2024-01", generation_id="g1", rows=(row, row))


def test_manifest_supersedes_partition_without_mutating_old_artifacts():
    bundle, result = bundle_and_result()
    old_row = LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")
    old = LabelPartitionV1.create(partition_key="2024-01", generation_id="g1", rows=(old_row,))
    changed = LabelResultV1.create(result.canonical_security_identity, result.anchor_session, (
        LabelValueV1.create("return_1d", LabelState.LABEL_AVAILABLE, Decimal("0.02000000")), *result.values[1:]
    ), result.bundle_hash)
    new_row = LabelRowV1.create(result=changed, bundle=bundle, materialization_version="phase2b-v1")
    new = LabelPartitionV1.create(partition_key="2024-01", generation_id="g2", rows=(new_row,))
    first = LabelDatasetManifestV1.create(previous_manifest_id=None, active_partitions=(old,), partition_supersession=(), phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,))
    second = LabelDatasetManifestV1.create(previous_manifest_id=first.manifest_id, previous_manifest=first, active_partitions=(new,), partition_supersession=((old.partition_id, new.partition_id),), phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,))
    assert old.verify() and first.verify() and second.verify()
    assert old.partition_id not in second.active_partition_ids
    assert second.partition_supersession == ((old.partition_id, new.partition_id),)


def test_manifest_rejects_duplicate_or_unrelated_supersession():
    bundle, result = bundle_and_result()
    row = LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")
    partition = LabelPartitionV1.create(partition_key="2024-01", generation_id="g1", rows=(row,))
    with pytest.raises(ValueError, match="duplicate"):
        LabelDatasetManifestV1.create(previous_manifest_id=None, active_partitions=(partition, partition), partition_supersession=(), phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,))
    with pytest.raises(ValueError, match="supersession"):
        LabelDatasetManifestV1.create(previous_manifest_id="b" * 64, active_partitions=(partition,), partition_supersession=(("c" * 64, partition.partition_id),), phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,))
