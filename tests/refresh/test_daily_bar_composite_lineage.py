from copy import deepcopy
from datetime import date

import pytest

from v5_2.data.identity import content_hash
from v5_2.data.identity import canonical_json
from v5_2.refresh.daily_bar_composite import (
    CompositeLineageError,
    Phase1CDailyBarComponentV1,
    Phase1CDailyBarCompositeManifestV1,
    resolve_phase1c_daily_bar_composite,
)
from v5_2.refresh.adapters import DatasetStateV1
from v5_2.refresh.contracts import DatasetReadiness
from v5_2.refresh.runtime import _load_published_state


SEMANTIC = "semantic-v1"


def artifact(schema, id_name, **values):
    digest = content_hash({"schema_version": schema, **values})
    return {"schema_version": schema, id_name: digest, "content_hash": digest, **values}


def component(role, start, end, mode, member, *, revoked=()):
    binding = artifact(
        "DailyBarSourceBindingV1", "binding_id",
        source_semantic_identity=SEMANTIC,
        source_content_set_identity=content_hash((member,)),
    )
    availability = artifact(
        "Phase1CDailyBarAvailabilityEvidenceV1", "evidence_id",
        binding_id=binding["binding_id"],
        source_semantic_identity=SEMANTIC,
        source_content_set_identity=binding["source_content_set_identity"],
        availability_mode=mode,
        observed_at_digest=content_hash(("2026-09-14T22:35:07+08:00",)) if mode == "CONTEMPORANEOUS_OBSERVED" else None,
    )
    approval = artifact(
        "SourceApprovalArtifactV1", "approval_id",
        dataset_kind="daily_bar", decision="APPROVED_WITH_RULES",
        source_version_identity=binding["source_content_set_identity"],
        evidence_ids=(availability["evidence_id"],),
    )
    manifest = artifact(
        "DatasetManifestV1", "dataset_id",
        manifest_hash_placeholder=None,
        dataset_kind="daily_bar", approval_id=approval["approval_id"],
        availability_evidence_id=availability["evidence_id"],
        source_content_set_identity=binding["source_content_set_identity"],
        coverage_start=start, coverage_end=end, row_count=1,
        fact_content_hashes=(member,),
    )
    manifest["manifest_hash"] = manifest["dataset_id"]
    revoked_ids = (approval["approval_id"],) if tuple(revoked) == ("CURRENT",) else revoked
    return Phase1CDailyBarComponentV1.create(
        role=role, provenance_mode=("CONTEMPORANEOUS_OBSERVED" if role == "CONTEMPORANEOUS_OBSERVED" else "HISTORICAL_RECONSTRUCTED"),
        availability_mode=mode, manifest=manifest, approval=approval,
        availability=availability, binding=binding, revoked_artifact_ids=revoked_ids,
    )


def three():
    return (
        component("HISTORICAL_BASELINE", "2010-01-04", "2026-09-10", "NEXT_SESSION_SAFE", "baseline"),
        component("HISTORICAL_CATCH_UP", "2026-09-11", "2026-09-11", "NEXT_SESSION_SAFE", "catchup"),
        component("CONTEMPORANEOUS_OBSERVED", "2026-09-14", "2026-09-14", "CONTEMPORANEOUS_OBSERVED", "current"),
    )


def test_composite_requires_exactly_three_typed_roles():
    baseline, catchup, current = three()
    result = Phase1CDailyBarCompositeManifestV1.create(
        historical_baseline=baseline, historical_catch_up=catchup,
        contemporaneous_observed=current,
    )
    assert result.component_roles == (
        "HISTORICAL_BASELINE", "HISTORICAL_CATCH_UP", "CONTEMPORANEOUS_OBSERVED")


@pytest.mark.parametrize("role,provenance,availability", [
    ("HISTORICAL_BASELINE", "CONTEMPORANEOUS_OBSERVED", "NEXT_SESSION_SAFE"),
    ("HISTORICAL_CATCH_UP", "CONTEMPORANEOUS_OBSERVED", "NEXT_SESSION_SAFE"),
    ("HISTORICAL_CATCH_UP", "HISTORICAL_RECONSTRUCTED", "CONTEMPORANEOUS_OBSERVED"),
    ("CONTEMPORANEOUS_OBSERVED", "HISTORICAL_RECONSTRUCTED", "CONTEMPORANEOUS_OBSERVED"),
    ("CONTEMPORANEOUS_OBSERVED", "CONTEMPORANEOUS_OBSERVED", "NEXT_SESSION_SAFE"),
])
def test_roles_reject_wrong_provenance_or_availability(role, provenance, availability):
    good = component(role, "2026-09-11", "2026-09-11", "NEXT_SESSION_SAFE" if role != "CONTEMPORANEOUS_OBSERVED" else "CONTEMPORANEOUS_OBSERVED", role)
    with pytest.raises(CompositeLineageError):
        Phase1CDailyBarComponentV1(**{
            **good.as_dict(), "provenance_mode": provenance,
            "availability_mode": availability,
        })


@pytest.mark.parametrize("target", ["manifest", "approval", "availability", "binding"])
def test_component_rejects_tampered_or_mismatched_chain(target):
    role = "HISTORICAL_CATCH_UP"
    member = "catchup"
    binding = artifact("DailyBarSourceBindingV1", "binding_id", source_semantic_identity=SEMANTIC, source_content_set_identity=content_hash((member,)))
    availability = artifact("Phase1CDailyBarAvailabilityEvidenceV1", "evidence_id", binding_id=binding["binding_id"], source_semantic_identity=SEMANTIC, source_content_set_identity=binding["source_content_set_identity"], availability_mode="NEXT_SESSION_SAFE", observed_at_digest=None)
    approval = artifact("SourceApprovalArtifactV1", "approval_id", dataset_kind="daily_bar", decision="APPROVED_WITH_RULES", source_version_identity=binding["source_content_set_identity"], evidence_ids=(availability["evidence_id"],))
    manifest = artifact("DatasetManifestV1", "dataset_id", manifest_hash_placeholder=None, dataset_kind="daily_bar", approval_id=approval["approval_id"], availability_evidence_id=availability["evidence_id"], source_content_set_identity=binding["source_content_set_identity"], coverage_start="2026-09-11", coverage_end="2026-09-11", row_count=1, fact_content_hashes=(member,))
    manifest["manifest_hash"] = manifest["dataset_id"]
    values = {"manifest": manifest, "approval": approval, "availability": availability, "binding": binding}
    values[target] = deepcopy(values[target])
    values[target]["dataset_kind" if target == "manifest" else "content_hash"] = "tampered"
    with pytest.raises(CompositeLineageError):
        Phase1CDailyBarComponentV1.create(role=role, provenance_mode="HISTORICAL_RECONSTRUCTED", availability_mode="NEXT_SESSION_SAFE", revoked_artifact_ids=(), **values)


def test_superseded_component_approval_fails_closed():
    with pytest.raises(CompositeLineageError):
        component("HISTORICAL_CATCH_UP", "2026-09-11", "2026-09-11", "NEXT_SESSION_SAFE", "catchup", revoked=("CURRENT",))


def test_three_component_membership_is_pairwise_disjoint():
    baseline, _, current = three()
    overlapping = component("HISTORICAL_CATCH_UP", "2026-09-14", "2026-09-14", "NEXT_SESSION_SAFE", "current")
    with pytest.raises(CompositeLineageError, match="membership"):
        Phase1CDailyBarCompositeManifestV1.create(historical_baseline=baseline, historical_catch_up=overlapping, contemporaneous_observed=current)


def test_union_and_total_must_equal_components():
    baseline, catchup, current = three()
    value = Phase1CDailyBarCompositeManifestV1.create(historical_baseline=baseline, historical_catch_up=catchup, contemporaneous_observed=current)
    assert value.aggregate_row_count == 3
    assert value.unclassified_count == value.duplicate_membership_count == 0


def test_composite_replays_same_hash():
    args = three()
    first = Phase1CDailyBarCompositeManifestV1.create(historical_baseline=args[0], historical_catch_up=args[1], contemporaneous_observed=args[2])
    second = Phase1CDailyBarCompositeManifestV1.create(historical_baseline=args[0], historical_catch_up=args[1], contemporaneous_observed=args[2])
    assert first.composite_manifest_id == second.composite_manifest_id


def test_20260911_and_20260914_resolve_to_distinct_roles():
    _, catchup, current = three()
    assert catchup.coverage_start == catchup.coverage_end == "2026-09-11"
    assert catchup.role == "HISTORICAL_CATCH_UP"
    assert current.coverage_start == current.coverage_end == "2026-09-14"
    assert current.role == "CONTEMPORANEOUS_OBSERVED"


def test_payload_scope_changes_content_not_semantic_identity():
    one = component("HISTORICAL_CATCH_UP", "2026-09-11", "2026-09-11", "NEXT_SESSION_SAFE", "one")
    two = component("HISTORICAL_CATCH_UP", "2026-09-12", "2026-09-12", "NEXT_SESSION_SAFE", "two")
    assert one.source_semantic_identity == two.source_semantic_identity
    assert one.source_content_set_identity != two.source_content_set_identity


def test_phase1c_resolver_selects_verified_composite_without_aggregate_approval(tmp_path):
    baseline, catchup, current = three()
    composite = Phase1CDailyBarCompositeManifestV1.create(
        historical_baseline=baseline, historical_catch_up=catchup,
        contemporaneous_observed=current)
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / f"phase1c-daily-bar-composite-{composite.composite_manifest_id}.json").write_bytes(canonical_json(composite.as_dict()))
    for name, item in (("historical-baseline", baseline), ("historical-catch-up", catchup), ("contemporaneous-observed", current)):
        (governance / f"{name}-component-{item.component_hash}.json").write_bytes(
            canonical_json({"schema_version": "Phase1CDailyBarComponentV1", **item.as_dict()}))
    (tmp_path / "daily_bar-current-composite-id.txt").write_text(composite.composite_manifest_id)
    assert resolve_phase1c_daily_bar_composite(tmp_path) == composite.composite_manifest_id


def test_phase1c_resolver_rejects_tampered_composite(tmp_path):
    baseline, catchup, current = three()
    value = Phase1CDailyBarCompositeManifestV1.create(
        historical_baseline=baseline, historical_catch_up=catchup,
        contemporaneous_observed=current).as_dict()
    value["aggregate_row_count"] = 999
    governance = tmp_path / "governance"
    governance.mkdir()
    identifier = value["composite_manifest_id"]
    (governance / f"phase1c-daily-bar-composite-{identifier}.json").write_bytes(canonical_json(value))
    (tmp_path / "daily_bar-current-composite-id.txt").write_text(identifier)
    with pytest.raises(CompositeLineageError):
        resolve_phase1c_daily_bar_composite(tmp_path)


def test_runtime_state_resolves_daily_bar_to_composite_without_aggregate_approval(tmp_path):
    baseline, catchup, current = three()
    composite = Phase1CDailyBarCompositeManifestV1.create(
        historical_baseline=baseline, historical_catch_up=catchup,
        contemporaneous_observed=current)
    remediation = tmp_path / "phase_1c_lineage_remediation"
    governance = remediation / "governance"
    governance.mkdir(parents=True)
    (governance / f"phase1c-daily-bar-composite-{composite.composite_manifest_id}.json").write_bytes(canonical_json(composite.as_dict()))
    for name, item in (("historical-baseline", baseline), ("historical-catch-up", catchup), ("contemporaneous-observed", current)):
        (governance / f"{name}-component-{item.component_hash}.json").write_bytes(
            canonical_json({"schema_version": "Phase1CDailyBarComponentV1", **item.as_dict()}))
    (remediation / "daily_bar-current-composite-id.txt").write_text(composite.composite_manifest_id)
    state_root = tmp_path / "phase_1c"
    fallback = DatasetStateV1("daily_bar", "old-aggregate-approval", "old-manifest",
                              date(2026, 9, 14), (date(2026, 9, 14),), "ready",
                              DatasetReadiness.READY)
    resolved = _load_published_state(state_root, "daily_bar", fallback)
    assert resolved.manifest_id == composite.composite_manifest_id
    assert resolved.approval_id is None
    assert resolved.availability_modes == ("HISTORICAL_RECONSTRUCTED", "CONTEMPORANEOUS_OBSERVED")
