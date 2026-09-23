from datetime import date
from decimal import Decimal

import pytest

from tests.labels.test_dataset_contracts import bundle_and_result
from v5_2.labels.contracts import (
    CORE_LABELS, LabelInputBundleV1, LabelReasonCode, LabelResultV1, LabelState, LabelValueV1,
)
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1
from v5_2.labels.incremental import (
    GovernanceChangeV1,
    IncrementalWorkReason,
    materialize_incremental_generation,
    select_incremental_workset,
)
from v5_2.labels.partition_store import (
    ImmutableArtifactCollision, read_manifest_exact, write_manifest, write_partition,
)


H1 = date(2024, 1, 3)
H3 = date(2024, 1, 5)
H5 = date(2024, 1, 9)


def row_with_states(*, h1=LabelState.LABEL_PENDING, h3=LabelState.LABEL_PENDING,
                    h5=LabelState.LABEL_PENDING, unsafe=False):
    bundle, _ = bundle_and_result()
    states = (h1, h3, h5, h5, h5, h5, h5)
    endpoints = (H1, H3, H5, H5, H5, H5, H5)
    values = []
    for name, state, endpoint in zip(CORE_LABELS, states, endpoints):
        if unsafe:
            values.append(LabelValueV1.create(
                name, LabelState.NOT_LABEL_SAFE, None,
                LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION,
                horizon_end_session=endpoint,
            ))
        elif state is LabelState.LABEL_AVAILABLE:
            value = True if name.startswith("hit_") else Decimal("0.01000000")
            values.append(LabelValueV1.create(name, state, value, horizon_end_session=endpoint))
        else:
            values.append(LabelValueV1.create(
                name, state, None, LabelReasonCode.HORIZON_NOT_COMPLETED,
                horizon_end_session=endpoint,
            ))
    result = LabelResultV1.create(
        bundle.canonical_security_identity, bundle.anchor_session,
        tuple(values), bundle.content_hash,
    )
    return LabelRowV1.create(result=result, bundle=bundle, materialization_version="phase2b-v1")


def manifest_for(row):
    partition = LabelPartitionV1.create(partition_key="2024-01", generation_id="g1", rows=(row,))
    manifest = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(partition,), partition_supersession=(),
        phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,),
    )
    return manifest


def row_for_identity(identity, *, h1=LabelState.LABEL_PENDING, h3=LabelState.LABEL_PENDING,
                     h5=LabelState.LABEL_PENDING):
    source = row_with_states(h1=h1, h3=h3, h5=h5)
    bundle, _ = bundle_and_result()
    changed_bundle = LabelInputBundleV1.create(
        canonical_security_identity=identity,
        anchor_session=bundle.anchor_session,
        anchor_boundary=bundle.anchor_boundary,
        reference_price=bundle.reference_price,
        provenance_path=bundle.provenance_path,
        domain_lineage=bundle.domain_lineage,
        approved_exchange_sessions=bundle.approved_exchange_sessions,
        latest_completed_session=bundle.latest_completed_session,
    )
    changed_result = LabelResultV1.create(
        identity, bundle.anchor_session, source.values, changed_bundle.content_hash,
    )
    return LabelRowV1.create(
        result=changed_result, bundle=changed_bundle, materialization_version="phase2b-v1",
    )


def test_h1_h3_h5_select_only_frozen_field_maturity_endpoints():
    h0 = row_with_states()
    at_h1 = select_incremental_workset(
        manifest_for(h0), H1, (), rows=(h0,),
    )
    assert at_h1.items[0].label_names == ("return_1d",)

    h1_row = row_with_states(h1=LabelState.LABEL_AVAILABLE)
    at_h3 = select_incremental_workset(
        manifest_for(h1_row), H3, (), rows=(h1_row,),
    )
    assert at_h3.items[0].label_names == ("return_3d",)

    h3_row = row_with_states(h1=LabelState.LABEL_AVAILABLE, h3=LabelState.LABEL_AVAILABLE)
    at_h5 = select_incremental_workset(
        manifest_for(h3_row), H5, (), rows=(h3_row,),
    )
    assert at_h5.items[0].label_names == CORE_LABELS[2:]
    assert at_h5.items[0].label_names[-2:] == (
        "hit_3pct_before_-2pct", "hit_5pct_before_-3pct",
    )


def test_barriers_never_mature_before_h5_and_same_inputs_replay():
    row = row_with_states(h1=LabelState.LABEL_AVAILABLE)
    first = select_incremental_workset(manifest_for(row), H3, (), rows=(row,))
    second = select_incremental_workset(manifest_for(row), H3, (), rows=(row,))
    assert all(not name.startswith("hit_") for name in first.items[0].label_names)
    assert first.workset_id == second.workset_id


def test_new_anchor_and_governance_change_are_explicit_work_reasons():
    row = row_with_states(h1=LabelState.LABEL_AVAILABLE, h3=LabelState.LABEL_AVAILABLE, h5=LabelState.LABEL_AVAILABLE)
    change = GovernanceChangeV1.create("REVOCATION", "b" * 64, ((row.canonical_security_identity, row.anchor_session),))
    ledger = select_incremental_workset(
        manifest_for(row), H5, (change,), rows=(row,),
        new_anchor_keys=(("000002.SZ", date(2024, 1, 3)),),
    )
    assert {item.reason for item in ledger.items} == {
        IncrementalWorkReason.NEW_ANCHOR, IncrementalWorkReason.GOVERNANCE_CHANGE,
    }


def test_duplicate_work_keys_fail_and_permanent_unsafe_is_not_auto_retried():
    unsafe = row_with_states(unsafe=True)
    assert select_incremental_workset(
        manifest_for(unsafe), H5, (), rows=(unsafe,),
    ).items == ()
    duplicate = (unsafe, unsafe)
    with pytest.raises(ValueError, match="duplicate"):
        select_incremental_workset(manifest_for(unsafe), H5, (), rows=duplicate)


@pytest.mark.parametrize("latest,states", [
    (H1, (LabelState.LABEL_AVAILABLE, LabelState.LABEL_PENDING, LabelState.LABEL_PENDING)),
    (H3, (LabelState.LABEL_AVAILABLE, LabelState.LABEL_AVAILABLE, LabelState.LABEL_PENDING)),
    (H5, (LabelState.LABEL_AVAILABLE, LabelState.LABEL_AVAILABLE, LabelState.LABEL_AVAILABLE)),
])
def test_incremental_generation_supersedes_complete_month_and_preserves_other_rows(
    tmp_path, latest, states,
):
    old = row_for_identity("000001.SZ")
    untouched = row_for_identity(
        "000002.SZ", h1=LabelState.LABEL_AVAILABLE,
        h3=LabelState.LABEL_AVAILABLE, h5=LabelState.LABEL_AVAILABLE,
    )
    old_partition = LabelPartitionV1.create(
        partition_key="2024-01", generation_id="old", rows=(old, untouched),
    )
    predecessor = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(old_partition,), partition_supersession=(),
        phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,),
    )
    old_path = write_partition(tmp_path, old_partition, (old, untouched))
    old_bytes = old_path.read_bytes()
    write_manifest(tmp_path, predecessor)
    replacement = row_for_identity("000001.SZ", h1=states[0], h3=states[1], h5=states[2])
    workset = select_incremental_workset(predecessor, latest, (), rows=(old, untouched))

    result = materialize_incremental_generation(
        tmp_path, predecessor, workset,
        active_partitions=((old_partition, (old, untouched)),),
        replacement_rows=(replacement,), materialization_version="phase2b-v1",
    )
    assert result.manifest.previous_manifest_id == predecessor.manifest_id
    assert result.manifest.partition_supersession == (
        (old_partition.partition_id, result.replacement_partitions[0].partition_id),
    )
    assert untouched.row_id in result.replacement_partitions[0].row_ids
    assert old.row_id not in result.replacement_partitions[0].row_ids
    assert old_path.read_bytes() == old_bytes
    assert read_manifest_exact(result.manifest_path, result.manifest.manifest_id) == result.manifest

    replay = materialize_incremental_generation(
        tmp_path, predecessor, workset,
        active_partitions=((old_partition, (old, untouched)),),
        replacement_rows=(replacement,), materialization_version="phase2b-v1",
    )
    assert replay.manifest.manifest_id == result.manifest.manifest_id
    replacement_path = (
        tmp_path / "labels" / "historical" / "2024-01"
        / f"{result.replacement_partitions[0].partition_id}.jsonl"
    )
    replacement_path.write_text("collision\n", encoding="utf-8")
    with pytest.raises(ImmutableArtifactCollision):
        materialize_incremental_generation(
            tmp_path, predecessor, workset,
            active_partitions=((old_partition, (old, untouched)),),
            replacement_rows=(replacement,), materialization_version="phase2b-v1",
        )


def test_incremental_generation_rejects_tampered_predecessor_and_incomplete_workset(tmp_path):
    old = row_for_identity("000001.SZ")
    old_partition = LabelPartitionV1.create(
        partition_key="2024-01", generation_id="old", rows=(old,),
    )
    predecessor = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(old_partition,), partition_supersession=(),
        phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,),
    )
    path = write_partition(tmp_path, old_partition, (old,))
    original_bytes = path.read_bytes()
    write_manifest(tmp_path, predecessor)
    workset = select_incremental_workset(predecessor, H1, (), rows=(old,))
    replacement = row_for_identity("000001.SZ", h1=LabelState.LABEL_AVAILABLE)
    path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="canonical partition"):
        materialize_incremental_generation(
            tmp_path, predecessor, workset,
            active_partitions=((old_partition, (old,)),), replacement_rows=(replacement,),
            materialization_version="phase2b-v1",
        )
    path.write_bytes(original_bytes)
    with pytest.raises(ValueError, match="replacement"):
        materialize_incremental_generation(
            tmp_path, predecessor, workset,
            active_partitions=((old_partition, (old,)),), replacement_rows=(),
            materialization_version="phase2b-v1",
        )


def test_incremental_generation_rejects_tampered_predecessor_manifest(tmp_path):
    old = row_for_identity("000001.SZ")
    partition = LabelPartitionV1.create(
        partition_key="2024-01", generation_id="old", rows=(old,),
    )
    predecessor = LabelDatasetManifestV1.create(
        previous_manifest_id=None, active_partitions=(partition,), partition_supersession=(),
        phase2a_acceptance_id="f" * 64, lineage_ids=("a" * 64,),
    )
    write_partition(tmp_path, partition, (old,))
    manifest_path = write_manifest(tmp_path, predecessor)
    workset = select_incremental_workset(predecessor, H1, (), rows=(old,))
    manifest_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="canonical manifest"):
        materialize_incremental_generation(
            tmp_path, predecessor, workset,
            active_partitions=((partition, (old,)),),
            replacement_rows=(row_for_identity("000001.SZ", h1=LabelState.LABEL_AVAILABLE),),
            materialization_version="phase2b-v1",
        )
