from datetime import date

import pytest

from v5_2.data.daily_bar_lineage import (
    DailyBarLineageError,
    DailyBarSourceBindingV1,
    HistoricalExitDailyBarAvailabilityEvidenceV2,
    validate_daily_bar_lineage,
)


def binding(payloads=("a", "b"), *, availability_policy="availability-v1",
            semantic_contract="daily-semantic-v1"):
    return DailyBarSourceBindingV1.create(
        source_name="provider", dataset_kind="daily_bar", endpoint="daily",
        payload_hashes=payloads, source_semantic_contract_version=semantic_contract,
        requested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        normalizer_version="normalizer-v1", identity_policy_version="identity-v1",
        unit_policy_id="unit-v1", availability_policy_version=availability_policy,
    )


def availability(item):
    return HistoricalExitDailyBarAvailabilityEvidenceV2.create(
        binding=item, coverage_start=date(2010, 1, 4), coverage_end=date(2026, 9, 10),
        availability_mode="HISTORICAL_RECONSTRUCTED", cutoff="NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
        approved_calendar_lineage_id="calendar-v1", parent_evidence_ids=("probe-v1",),
    )


def lineage_dicts(item, evidence):
    approval = {
        "approval_id": "approval-new", "content_hash": "approval-new",
        "source_version_identity": item.source_content_set_identity,
        "rule_set": {"source_semantic_identity": item.source_semantic_identity,
                     "source_content_set_identity": item.source_content_set_identity,
                     "availability_evidence_id": evidence.evidence_id},
    }
    manifest = {
        "approval_id": "approval-new", "approval_content_hash": "approval-new",
        "availability_evidence_id": evidence.evidence_id,
        "raw_payload_hashes": item.payload_hashes,
    }
    return approval, manifest


def test_daily_bar_content_set_identity_changes_when_payload_scope_expands():
    assert binding(("a", "b")).source_content_set_identity != binding(("a", "b", "c")).source_content_set_identity


def test_daily_bar_semantic_identity_does_not_change_when_only_payload_scope_expands():
    assert binding(("a", "b")).source_semantic_identity == binding(("a", "b", "c")).source_semantic_identity


def test_availability_policy_changes_binding_but_not_source_semantic_identity():
    historical = binding(
        availability_policy="daily-bar-availability-v1:NEXT_SESSION_SAFE",
        semantic_contract="daily-bar-semantic-contract-v2",
    )
    observed = binding(
        availability_policy="daily-bar-availability-v1:CONTEMPORANEOUS_OBSERVED",
        semantic_contract="daily-bar-semantic-contract-v2",
    )

    assert historical.source_semantic_identity == observed.source_semantic_identity
    assert historical.binding_id != observed.binding_id


def test_historical_availability_evidence_binds_exact_content_set_identity():
    item = binding()
    evidence = availability(item)
    assert evidence.verify(item)
    assert not evidence.verify(binding(("a", "b", "c")))


def test_historical_approval_binds_same_content_set_as_availability_evidence():
    item = binding()
    evidence = availability(item)
    approval, manifest = lineage_dicts(item, evidence)
    validate_daily_bar_lineage(binding=item, availability=evidence, approval=approval, manifest=manifest)


def test_historical_manifest_binds_same_approval_and_content_set():
    item = binding()
    evidence = availability(item)
    approval, manifest = lineage_dicts(item, evidence)
    manifest["approval_id"] = "wrong"
    with pytest.raises(DailyBarLineageError, match="manifest approval"):
        validate_daily_bar_lineage(binding=item, availability=evidence, approval=approval, manifest=manifest)


def test_cross_artifact_content_set_mismatch_fails_closed():
    item = binding()
    evidence = availability(item)
    approval, manifest = lineage_dicts(item, evidence)
    approval["source_version_identity"] = "wrong"
    with pytest.raises(DailyBarLineageError, match="approval content set"):
        validate_daily_bar_lineage(binding=item, availability=evidence, approval=approval, manifest=manifest)


def test_subset_predecessor_availability_cannot_approve_superset_panel():
    old = binding(("a", "b"))
    current = binding(("a", "b", "c"))
    evidence = availability(old)
    approval, manifest = lineage_dicts(current, evidence)
    with pytest.raises(DailyBarLineageError, match="availability binding"):
        validate_daily_bar_lineage(binding=current, availability=evidence, approval=approval, manifest=manifest)


def test_revoked_or_superseded_daily_bar_approval_cannot_be_selected():
    item = binding()
    evidence = availability(item)
    approval, manifest = lineage_dicts(item, evidence)
    with pytest.raises(DailyBarLineageError, match="not current"):
        validate_daily_bar_lineage(
            binding=item, availability=evidence, approval=approval, manifest=manifest,
            revoked_approval_ids={"approval-new"},
        )


def test_contemporaneous_and_historical_versions_are_not_assumed_equal():
    historical = binding(("a", "b"))
    contemporaneous = binding(("a", "b", "c"))
    assert historical.source_content_set_identity != contemporaneous.source_content_set_identity
    assert historical.source_semantic_identity == contemporaneous.source_semantic_identity
