import json
from pathlib import Path

import pytest

from v5_2.data.identity import content_hash
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.acceptance_v2_boundaries import (
    build_fail_closed_boundary_ledger_v2_1,
    build_missing_bar_boundary_case_v2_1,
    build_unsupported_ca_boundary_case_v2_1,
    create_remove_future_bar_transform_v2_1,
)
from v5_2.labels.acceptance_v2_contracts import build_frozen_amendment_v2_1


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


def test_unsupported_ca_revalidates_pins_and_executes_repository_boundary():
    engine = ForbiddenEngine()
    result = build_unsupported_ca_boundary_case_v2_1(ROOT, engine=engine)
    assert result.verify()
    assert result.provenance.base_evidence_class == "REAL_MACHINE_VISIBLE_UNSUPPORTED_SCOPE"
    assert result.provenance.boundary_exercise_class == "REAL_UNSUPPORTED_MARKET_EVENT"
    assert result.provenance.real_condition_observed is True
    assert result.observed_condition == (
        "002029.SZ",
        "2012-05-08",
        "UNSUPPORTED_SHARE_CONVERSION",
    )
    assert result.rejection_boundary == "CorporateActionRepository.query"
    assert result.expected_rejection_code == "NOT_RESEARCH_SAFE: unsupported action type"
    assert result.observed_rejection_code == result.expected_rejection_code
    assert result.assembler_invocation_count == 0
    assert result.engine_invocation_count == engine.calls == 0
    assert "ACCEPTANCE_ONLY_CA_PREFLIGHT" not in result.rejection_boundary
    assert result.real_base_bundle_id is None
    assert result.real_base_lineage_ids == ()


@pytest.mark.parametrize(
    "constant",
    [
        "CA_APPROVAL_ID_V2_1",
        "CA_MANIFEST_ID_V2_1",
        "CA_MATERIALIZATION_AUDIT_ID_V2_1",
        "CA_CANDIDATE_BUNDLE_ID_V2_1",
        "CA_QUARANTINE_ID_V2_1",
    ],
)
def test_unsupported_ca_stops_on_any_changed_pin(monkeypatch, constant):
    import v5_2.labels.acceptance_v2_boundaries as boundaries

    monkeypatch.setattr(boundaries, constant, "0" * 64)
    with pytest.raises(ValueError, match="unsupported CA pinned provenance"):
        boundaries.build_unsupported_ca_boundary_case_v2_1(ROOT, engine=ForbiddenEngine())


def test_acceptance_only_preflight_cannot_satisfy_v2_1_unsupported_ca():
    result = build_unsupported_ca_boundary_case_v2_1(ROOT, engine=ForbiddenEngine())
    assert result.rejection_boundary == "CorporateActionRepository.query"
    assert result.rejection_boundary != "ACCEPTANCE_ONLY_CA_PREFLIGHT"


def test_v2_1_boundary_ledger_has_exact_categories_and_truthful_provenance():
    result = build_fail_closed_boundary_ledger_v2_1(ROOT, build_frozen_amendment_v2_1())
    assert result.verify()
    assert tuple(case.semantic_category for case in result.cases) == (
        "UNEXPLAINED_MISSING_BAR",
        "UNSUPPORTED_CA",
        "REVOKED_APPROVAL",
        "TAMPERED_ARTIFACT",
        "MISSING_REQUIRED_DOMAIN",
        "AMBIGUOUS_IDENTITY",
        "MALFORMED_CALENDAR",
        "INVALID_LINEAGE",
        "ROLE_SWAP",
        "DUPLICATE_DOMAIN",
    )
    missing, unsupported = result.cases[:2]
    assert missing.provenance.real_condition_observed is False
    assert missing.provenance.boundary_exercise_class == "DETERMINISTIC_CONTRACT_FIXTURE"
    assert unsupported.provenance.real_condition_observed is True
    assert unsupported.rejection_boundary == "CorporateActionRepository.query"
    assert result.real_observed_boundary_cases == 1
    assert all(case.engine_invocation_count == 0 for case in result.cases)


def test_attempt1_layer_b_remains_historical_and_is_not_v2_1():
    old_id = "ad915a5abb2fcf071929089cf85c7924c6c2254ccf8b870b32c613d96ba62505"
    old = json.loads((ROOT / f"data/phase_2a/v2_infrastructure/fail-closed-boundaries-{old_id}.json").read_text())
    assert old["ledger_id"] == old_id
    assert "provenance" not in old["cases"][0]
