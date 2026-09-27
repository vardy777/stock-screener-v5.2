"""Unsafe reasons remain exact even when aggregate counts are unchanged."""

from dataclasses import replace
from unittest.mock import patch

import pytest

from v5_2.labels.contracts import LabelState
from v5_2.labels.dataset_contracts import LabelRowV1
from tests.labels.test_phase2b_coverage import REASONS, row
from v5_2.labels.phase2b_unsafe_gate_v2 import (
    derive_unsafe_preservation_evidence, read_unsafe_preservation_evidence_exact,
    write_unsafe_preservation_evidence,
)


def test_count_preserving_reason_swap_changes_unsafe_evidence(tmp_path):
    original = (row(3, LabelState.NOT_LABEL_SAFE, REASONS[0]),
                row(4, LabelState.NOT_LABEL_SAFE, REASONS[1]))
    swapped = (row(3, LabelState.NOT_LABEL_SAFE, REASONS[1]),
               row(4, LabelState.NOT_LABEL_SAFE, REASONS[0]))
    evidence = derive_unsafe_preservation_evidence(original, "a" * 64)
    forged = derive_unsafe_preservation_evidence(swapped, "a" * 64)
    assert evidence.verify() and forged.verify()
    assert evidence.unsafe_value_count == forged.unsafe_value_count == 14
    assert evidence.reason_counts == forged.reason_counts
    assert evidence.evidence_id != forged.evidence_id
    path = write_unsafe_preservation_evidence(tmp_path, evidence)
    assert read_unsafe_preservation_evidence_exact(path, evidence.evidence_id) == evidence


def test_one_missing_unsafe_reason_cannot_hide_behind_other_valid_reasons():
    valid = row(3, LabelState.NOT_LABEL_SAFE, REASONS[0])
    forged_value = replace(valid.values[0], reason_code=None)
    mixed = replace(valid, values=(forged_value, *valid.values[1:]))
    with patch.object(LabelRowV1, "verify", return_value=True):
        with pytest.raises(ValueError, match="unsafe state lacks reason"):
            derive_unsafe_preservation_evidence((mixed,), "a" * 64)
