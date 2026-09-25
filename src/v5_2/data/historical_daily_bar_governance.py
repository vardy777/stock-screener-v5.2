"""Exact parent-lineage validation for the portable Daily Bar representation."""

from __future__ import annotations

from typing import Mapping

from v5_2.data.daily_bar_lineage import DailyBarSourceBindingV1
from v5_2.data.historical_daily_bar_authority import HistoricalDailyBarFactAuthorityV1
from v5_2.data.identity import content_hash
from v5_2.refresh.daily_bar_composite import _verify


class HistoricalDailyBarGovernanceError(RuntimeError):
    """A frozen Daily Bar authority or derived representation is invalid."""


def validate_historical_parent(
    *, panel: Mapping[str, object], approval: Mapping[str, object],
    manifest: Mapping[str, object], binding: Mapping[str, object],
    availability: Mapping[str, object], revoked_approval_ids: tuple[str, ...],
) -> tuple[str, str, str]:
    panel_id = str(panel.get("panel_id", ""))
    panel_body = {key: value for key, value in panel.items()
                  if key not in {"panel_id", "content_hash"}}
    if (panel.get("schema_version") != "ResearchWideHistoricalDailyBarPanelV1"
            or panel.get("content_hash") != panel_id
            or content_hash(panel_body) != panel_id):
        raise HistoricalDailyBarGovernanceError("historical panel integrity failed")
    if (not _verify(approval, "approval_id") or not _verify(manifest, "dataset_id")
            or not _verify(availability, "evidence_id")):
        raise HistoricalDailyBarGovernanceError("parent approval, manifest or availability integrity failed")
    try:
        rebuilt_binding = DailyBarSourceBindingV1.create(**{
            key: binding[key] for key in (
                "source_name", "dataset_kind", "endpoint", "payload_hashes",
                "source_semantic_contract_version", "requested_fields",
                "normalizer_version", "identity_policy_version", "unit_policy_id",
                "availability_policy_version",
            )})
    except (KeyError, ValueError, TypeError) as error:
        raise HistoricalDailyBarGovernanceError("source binding is malformed") from error
    if (rebuilt_binding.binding_id != binding.get("binding_id")
            or rebuilt_binding.content_hash != binding.get("content_hash")
            or rebuilt_binding.source_content_set_identity != binding.get("source_content_set_identity")
            or rebuilt_binding.source_semantic_identity != binding.get("source_semantic_identity")):
        raise HistoricalDailyBarGovernanceError("source binding integrity failed")
    approval_id = str(approval["approval_id"])
    manifest_id = str(manifest["dataset_id"])
    rules = approval.get("rule_set", {})
    if not isinstance(rules, Mapping):
        raise HistoricalDailyBarGovernanceError("parent approval rules are malformed")
    if (approval_id in revoked_approval_ids
            or approval.get("decision") not in {"APPROVED", "APPROVED_WITH_RULES"}
            or approval.get("dataset_kind") != "daily_bar"
            or approval.get("source_version_identity") != rebuilt_binding.source_content_set_identity
            or rules.get("panel_id") != panel_id
            or rules.get("source_binding_id") != rebuilt_binding.binding_id
            or rules.get("availability_evidence_id") != availability.get("evidence_id")
            or manifest.get("approval_id") != approval_id
            or manifest.get("approval_content_hash") != approval.get("content_hash")
            or manifest.get("availability_evidence_id") != availability.get("evidence_id")
            or availability.get("source_binding_id") != rebuilt_binding.binding_id
            or availability.get("source_content_set_identity") != rebuilt_binding.source_content_set_identity
            or tuple(manifest.get("fact_content_hashes", ())) != (panel_id,)
            or tuple(panel.get("raw_payload_hashes", ())) != tuple(manifest.get("raw_payload_hashes", ()))
            or tuple(panel.get("raw_payload_hashes", ())) != rebuilt_binding.payload_hashes
            or int(panel.get("row_count", -1)) != int(manifest.get("row_count", -2))
            or int(panel.get("symbol_count", -1)) != int(manifest.get("symbol_count", -2))
            or panel.get("normalization_policy_id") != manifest.get("normalization_policy_id")
            or panel.get("unit_policy_id") != manifest.get("unit_policy_id")
            or panel.get("unit_policy_id") != rebuilt_binding.unit_policy_id
            or panel.get("availability_policy") != "NEXT_SESSION_SAFE@16:30 Asia/Shanghai"
            or rebuilt_binding.availability_policy_version != "daily-bar-availability-v1:NEXT_SESSION_SAFE"):
        raise HistoricalDailyBarGovernanceError("frozen historical parent chain disagrees")
    return panel_id, approval_id, manifest_id


def _seal(schema: str, id_field: str, body: dict[str, object]) -> dict[str, object]:
    digest = content_hash({"schema_version": schema, **body})
    return {"schema_version": schema, **body, id_field: digest, "content_hash": digest}


def create_derived_artifacts(
    *, authority: HistoricalDailyBarFactAuthorityV1,
    observed: Mapping[str, object], requested_effective_symbol_sessions: int,
    receipt_count: int, corrected_overlap_row_count: int,
    parent_composite: Mapping[str, object],
    corrected_manifest: Mapping[str, object],
    panel: Mapping[str, object], approval: Mapping[str, object],
    manifest: Mapping[str, object], binding: Mapping[str, object],
    availability: Mapping[str, object], revoked_approval_ids: tuple[str, ...],
) -> dict[str, dict[str, object]]:
    panel_id, approval_id, manifest_id = validate_historical_parent(
        panel=panel, approval=approval, manifest=manifest, binding=binding,
        availability=availability, revoked_approval_ids=revoked_approval_ids,
    )
    composite_id = str(parent_composite.get("composite_manifest_id", ""))
    composite_body = {key: value for key, value in parent_composite.items()
                      if key not in {"composite_manifest_id", "content_hash"}}
    historical_component = parent_composite.get("historical_baseline", {})
    if not isinstance(historical_component, Mapping):
        raise HistoricalDailyBarGovernanceError("historical composite component is malformed")
    if (composite_id != "0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744"
            or parent_composite.get("content_hash") != composite_id
            or content_hash(composite_body) != composite_id
            or historical_component.get("manifest_id") != manifest_id
            or historical_component.get("approval_id") != approval_id
            or historical_component.get("row_count") != panel["row_count"]
            or tuple(historical_component.get("member_artifact_ids", ())) != (panel_id,)
            or not _verify(corrected_manifest, "dataset_id")
            or corrected_manifest.get("dataset_id") != "9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4"
            or corrected_manifest.get("approval_id") != "7daf8a38391ebb27ef5675cce6e978b1b10823195b304eca84d719c3d5504724"
            or corrected_manifest.get("coverage_start") != "2024-01-01"
            or corrected_manifest.get("coverage_end") != "2025-12-31"):
        raise HistoricalDailyBarGovernanceError("exact composite or corrected overlap authority mismatch")
    if (not authority.verify()
            or authority.parent_panel_id != panel_id
            or authority.parent_approval_id != approval_id
            or authority.parent_manifest_id != manifest_id
            or authority.source_binding_id != binding["binding_id"]
            or authority.source_content_set_id != binding["source_content_set_identity"]
            or authority.availability_evidence_id != availability["evidence_id"]
            or authority.calendar_lineage_id != availability["approved_calendar_lineage_id"]
            or authority.normalization_policy_id != panel["normalization_policy_id"]
            or authority.unit_policy_id != panel["unit_policy_id"]
            or authority.identity_policy_id != binding["identity_policy_version"]
            or authority.raw_payload_hashes != tuple(panel["raw_payload_hashes"])
            or authority.coverage_start != panel["coverage_start"]
            or authority.coverage_end != panel["coverage_end"]
            or authority.row_count != panel["row_count"]
            or authority.symbol_count != panel["symbol_count"]
            or int(observed["row_count"]) != panel["row_count"]
            or int(observed["symbol_count"]) != panel["symbol_count"]
            or int(observed["excluded_non_target_count"]) != panel["excluded_non_target_row_count"]
            or tuple(map(tuple, observed["frozen_session_observed_counts"]))
                != tuple(map(tuple, panel["frozen_session_observed_counts"]))
            or tuple(map(tuple, observed["frozen_session_symbol_hashes"]))
                != tuple(map(tuple, panel["frozen_session_symbol_hashes"]))
            or requested_effective_symbol_sessions != panel["requested_effective_symbol_sessions"]
            or receipt_count != len(manifest["receipt_hashes"])
            or corrected_overlap_row_count != corrected_manifest["row_count"]):
        raise HistoricalDailyBarGovernanceError("derived representation does not reconcile to frozen truth")
    missing = requested_effective_symbol_sessions - authority.row_count
    if missing != panel["missing_symbol_sessions"]:
        raise HistoricalDailyBarGovernanceError("missing symbol-session census changed")
    ledger = _seal("HistoricalDailyBarCoverageLedgerV1", "ledger_id", {
        "authority_id": authority.authority_id,
        "parent_panel_id": panel_id,
        "coverage_start": authority.coverage_start,
        "coverage_end": authority.coverage_end,
        "raw_payload_count": len(authority.raw_payload_hashes),
        "receipt_count": receipt_count,
        "requested_effective_symbol_sessions": requested_effective_symbol_sessions,
        "observed_rows": authority.row_count,
        "missing_unclassified_symbol_sessions": missing,
        "symbol_count": authority.symbol_count,
        "shard_count": len(authority.shards),
        "fact_count": authority.row_count,
        "duplicate_count": 0,
        "invalid_identity_count": 0,
        "excluded_non_target_count": int(observed["excluded_non_target_count"]),
        "unresolved_facts": 0,
        "quarantined_facts": 0,
        "coverage_gaps": missing,
        "frozen_session_observed_counts": tuple(map(tuple, observed["frozen_session_observed_counts"])),
        "frozen_session_symbol_hashes": tuple(map(tuple, observed["frozen_session_symbol_hashes"])),
        "corrected_overlap_row_count": corrected_overlap_row_count,
        "corrected_overlap_fact_id_mismatch_count": 0,
        "corrected_overlap_semantic_mismatch_count": 0,
    })
    derived_approval = _seal("HistoricalDailyBarRepresentationApprovalV1", "approval_id", {
        "decision": "APPROVED_WITH_RULES",
        "scope": "PORTABLE_ROW_LEVEL_REPRESENTATION_OF_APPROVED_HISTORICAL_DAILY_BAR_TRUTH",
        "parent_approval_id": approval_id,
        "parent_panel_id": panel_id,
        "authority_id": authority.authority_id,
        "coverage_ledger_id": ledger["ledger_id"],
        "source_content_set_id": authority.source_content_set_id,
        "availability_evidence_id": authority.availability_evidence_id,
        "rules": ("NO_NEW_PROVIDER_OBSERVATIONS", "NO_NEW_MARKET_COVERAGE",
                  "NEXT_SESSION_SAFE", "UNCLASSIFIED_MISSING_BARS_FAIL_CLOSED"),
    })
    derived_manifest = _seal("HistoricalDailyBarRepresentationManifestV1", "manifest_id", {
        "parent_manifest_id": manifest_id,
        "approval_id": derived_approval["approval_id"],
        "authority_id": authority.authority_id,
        "coverage_ledger_id": ledger["ledger_id"],
        "membership_set_hash": authority.membership_set_hash,
        "shard_storage_hashes": tuple(item.storage_hash for item in authority.shards),
        "row_count": authority.row_count,
        "symbol_count": authority.symbol_count,
        "coverage_start": authority.coverage_start,
        "coverage_end": authority.coverage_end,
        "availability_policy_version": "daily-bar-availability-v1:NEXT_SESSION_SAFE",
    })
    composition = _seal("HistoricalDailyBarRepresentationCompositionV1", "composition_id", {
        "parent_composite_id": composite_id,
        "parent_historical_manifest_id": manifest_id,
        "derived_historical_manifest_id": derived_manifest["manifest_id"],
        "role": "HISTORICAL_BASELINE_PORTABLE_REPRESENTATION",
        "supersession_scope": "ROW_LEVEL_REPRESENTATION_ONLY_PARENT_TRUTH_UNCHANGED",
    })
    return {"coverage_ledger": ledger, "approval": derived_approval,
            "manifest": derived_manifest, "composition": composition}
