from dataclasses import replace

import pytest

from v5_2.labels.acceptance_v2_contracts import (
    EvidenceClass,
    MigrationEntryV2,
    Phase2AAcceptanceArchitectureAmendmentV2,
)


H = "a" * 64


def migration():
    return tuple(
        MigrationEntryV2.create(
            slot=i,
            layers=("B",) if i in {16, 17} else (("A", "C") if i == 22 else ("A",)),
            actual_behavior=f"slot-{i}",
        )
        for i in range(1, 23)
    )


def test_amendment_is_immutable_deterministic_and_content_addressed():
    one = Phase2AAcceptanceArchitectureAmendmentV2.create(
        design_commit=H, plan_commits=("b" * 64, "c" * 64),
        v1_artifact_ids=("d" * 64,), migration=migration(),
    )
    two = Phase2AAcceptanceArchitectureAmendmentV2.create(
        design_commit=H, plan_commits=("b" * 64, "c" * 64),
        v1_artifact_ids=("d" * 64,), migration=migration(),
    )
    assert one == two and one.verify()
    assert one.artifact_id == one.content_hash
    assert not replace(one, content_hash="0" * 64).verify()


def test_amendment_rejects_incomplete_or_duplicate_migration():
    with pytest.raises(ValueError, match="exact 22-slot migration"):
        Phase2AAcceptanceArchitectureAmendmentV2.create(
            design_commit=H, plan_commits=("b" * 64,),
            v1_artifact_ids=("d" * 64,), migration=migration()[:-1],
        )


def test_evidence_classes_are_exact_and_closed():
    assert tuple(item.value for item in EvidenceClass) == (
        "REAL_MARKET_EVIDENCE", "REAL_APPROVED_BOUNDARY_CONDITION",
        "REAL_MACHINE_VISIBLE_UNSUPPORTED_CONDITION",
        "DETERMINISTIC_CONTRACT_FIXTURE", "SYNTHETIC_CONTRACT_FIXTURE",
    )
