from pathlib import Path

import pytest

from v5_2.data.identity import content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.acceptance_v2_boundaries import (
    build_missing_bar_boundary_case_v2_1,
    create_remove_future_bar_transform_v2_1,
)


ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ID = "947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48"
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_2a/reference").is_dir(), reason="immutable evidence excluded")


class ForbiddenEngine:
    def __init__(self):
        self.calls = 0

    def evaluate(self, _bundle):
        self.calls += 1
        raise AssertionError("engine must be structurally unreachable")


def test_missing_bar_uses_exact_real_base_and_truthful_fixture_provenance():
    engine = ForbiddenEngine()
    result = build_missing_bar_boundary_case_v2_1(ROOT, engine=engine)
    base = Phase2AEvidenceAssemblerV1(ROOT).assemble(build_frozen_inventory().slots[0])
    removed = next(day for day in base.approved_exchange_sessions if day > base.anchor_session)
    expected_transform_body = {
        "schema_version": "RemoveFutureBarTransformV2_1",
        "base_bundle_id": base.content_hash,
        "five_domain_lineage_ids": tuple(item.content_hash for item in base.domain_lineage),
        "removed_required_future_session": removed.isoformat(),
        "operation": "REMOVE_FUTURE_BAR",
    }
    assert result.verify()
    assert result.provenance.base_evidence_class == "REAL_MARKET_EVIDENCE"
    assert result.provenance.boundary_exercise_class == "DETERMINISTIC_CONTRACT_FIXTURE"
    assert result.provenance.real_condition_observed is False
    assert result.provenance.unavailability_evidence_id == DISCOVERY_ID
    assert result.real_base_bundle_id == base.content_hash
    assert result.real_base_lineage_ids == tuple(item.content_hash for item in base.domain_lineage)
    assert result.transform_id == content_hash(expected_transform_body)
    assert result.removed_session == removed.isoformat()
    assert result.rejection_boundary == "Phase2AEvidenceAssemblerV1.assemble"
    assert result.observed_rejection_code == f"UNEXPLAINED_MISSING_BAR:{removed.isoformat()}"
    assert result.assembler_invocation_count == 1
    assert result.engine_invocation_count == engine.calls == 0


@pytest.mark.parametrize(
    "changed_components",
    [
        ("anchor_bar",),
        ("calendar",),
        ("master_identity",),
        ("status",),
        ("corporate_action",),
        ("future_bars", "second_future_bar"),
    ],
)
def test_missing_bar_transform_rejects_every_out_of_scope_mutation(changed_components):
    base = Phase2AEvidenceAssemblerV1(ROOT).assemble(build_frozen_inventory().slots[0])
    removed = next(day for day in base.approved_exchange_sessions if day > base.anchor_session)
    with pytest.raises(ValueError, match="REMOVE_FUTURE_BAR transform scope violation"):
        create_remove_future_bar_transform_v2_1(
            base,
            removed_session=removed,
            changed_components=changed_components,
        )
