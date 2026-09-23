from datetime import date
from decimal import Decimal

import pytest

from tests.labels.test_dataset_contracts import bundle_and_result
from v5_2.labels.contracts import CORE_LABELS, LabelReasonCode, LabelResultV1, LabelState, LabelValueV1
from v5_2.labels.dataset_contracts import LabelDatasetManifestV1, LabelPartitionV1, LabelRowV1
from v5_2.labels.incremental import (
    GovernanceChangeV1,
    IncrementalWorkReason,
    select_incremental_workset,
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

