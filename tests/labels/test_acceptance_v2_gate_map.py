from dataclasses import replace

import pytest

from v5_2.labels.acceptance import ACCEPTANCE_GATES
from v5_2.labels.acceptance_v2_contracts import GateArtifactConsumptionMapV2, build_frozen_amendment_v2, build_gate_consumption_map


IDS = ("a" * 64, "b" * 64, "c" * 64)


def test_literal_gate_map_preserves_exact_original_16_names():
    amendment = build_frozen_amendment_v2()
    result = build_gate_consumption_map(amendment, layer_a_id=IDS[0], layer_b_id=IDS[1], layer_c_id=IDS[2])
    assert result.verify()
    assert tuple(x.gate for x in result.entries) == ACCEPTANCE_GATES
    assert len(result.entries) == 16
    assert {x.primary_layer for x in result.entries} <= {"A", "B", "C", "A+B", "A+C", "C+A", "CROSS_LAYER"}


def test_map_rejects_missing_extra_duplicate_or_alias_gate():
    amendment = build_frozen_amendment_v2()
    valid = build_gate_consumption_map(amendment, layer_a_id=IDS[0], layer_b_id=IDS[1], layer_c_id=IDS[2])
    for entries in (valid.entries[:-1], (*valid.entries, valid.entries[0]), (replace(valid.entries[0], gate="LABEL_CONTRACT"), *valid.entries[1:])):
        with pytest.raises(ValueError, match="exact 16 acceptance gates"):
            GateArtifactConsumptionMapV2.create(amendment_id=amendment.artifact_id, entries=entries)
