import json
from dataclasses import replace
from pathlib import Path

import pytest

from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.acceptance_v2_contracts import RealReferenceCaseV2, build_frozen_amendment_v2_1
from v5_2.labels.acceptance_v2_layer_a import (
    CHECKPOINT7_COMPARISON_LEDGER_ID,
    build_real_reference_coverage_ledger_v2_1,
    validate_mandatory_real_roles_v2_1,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


def ledger():
    source = json.loads(
        (ROOT / f"data/phase_2a/reference/full-engine-comparison-{CHECKPOINT7_COMPARISON_LEDGER_ID}.json").read_text()
    )
    inventory = build_frozen_inventory()
    assembler = Phase2AEvidenceAssemblerV1(ROOT)
    bundles = tuple(assembler.assemble(slot) for slot in inventory.slots if slot.slot not in {16, 17})
    return build_real_reference_coverage_ledger_v2_1(
        build_frozen_amendment_v2_1(), source, bundles
    )


def test_v2_1_layer_a_indexes_complete_truthful_mandatory_roles():
    result = ledger()
    assert result.verify()
    assert len(result.cases) == 20
    assert validate_mandatory_real_roles_v2_1(result)
    roles = {role for role, _slots in result.semantic_role_index}
    assert {
        "NORMAL_POSITIVE_RETURN",
        "NORMAL_NEGATIVE_RETURN",
        "SUSPENSION_THROUGH_H5",
        "LATEST-SESSION_LABEL_PENDING",
        "IDENTITY_TRANSITION",
        "DELISTING_BOUNDARY",
        "CASH_DIVIDEND",
        "BONUS_SHARE",
    } <= roles


@pytest.mark.parametrize(
    "removed_role",
    ["SUSPENSION_THROUGH_H5", "LATEST-SESSION_LABEL_PENDING", "NORMAL_NEGATIVE_RETURN"],
)
def test_count_preserving_role_removal_fails_semantic_coverage(removed_role):
    result = ledger()
    cases = tuple(
        RealReferenceCaseV2.create(**{
            name: (("NORMAL_POSITIVE_RETURN",) if name == "semantic_roles" else getattr(case, name))
            for name in case.__dataclass_fields__
            if name != "content_hash"
        })
        if removed_role in case.semantic_roles
        else case
        for case in result.cases
    )
    changed = replace(
        result,
        cases=cases,
        semantic_role_index=tuple(
            item for item in result.semantic_role_index if item[0] != removed_role
        ),
    )
    assert len(changed.cases) == 20
    assert not validate_mandatory_real_roles_v2_1(changed)
