import json
from pathlib import Path

import pytest

from v5_2.data.historical_daily_bar_governance import (
    HistoricalDailyBarGovernanceError,
    create_derived_artifacts,
    validate_historical_parent,
)
from v5_2.data.historical_daily_bar_authority import (
    HistoricalDailyBarFactAuthorityV1,
    HistoricalDailyBarShardDescriptorV1,
)


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "data" / "phase_1c_lineage_remediation" / "governance"
PANEL = ROOT / "data" / "phase_1b_exit_remediation" / "governance" / (
    "historical-daily-bar-panel-a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d.json"
)
pytestmark = pytest.mark.skipif(
    not PANEL.is_file(), reason="frozen Phase 1 governance artifact is repository-local"
)


def _parents():
    def load(pattern):
        matches = tuple(GOVERNANCE.glob(pattern))
        assert len(matches) == 1
        return json.loads(matches[0].read_text(encoding="utf-8"))
    return dict(
        panel=json.loads(PANEL.read_text(encoding="utf-8")),
        approval=load("historical-baseline-approval-eaa2c254*.json"),
        manifest=load("historical-baseline-manifest-cb79850f*.json"),
        binding=load("historical-baseline-binding-176dba27*.json"),
        availability=load("historical-baseline-availability-2bb3877d*.json"),
        revoked_approval_ids=(),
    )


def test_frozen_historical_parent_chain_is_exact_and_unrevoked():
    parents = _parents()
    assert validate_historical_parent(**parents) == (
        parents["panel"]["panel_id"], parents["approval"]["approval_id"],
        parents["manifest"]["dataset_id"],
    )


def test_tampered_or_revoked_historical_parent_fails_closed():
    parents = _parents()
    with pytest.raises(HistoricalDailyBarGovernanceError):
        validate_historical_parent(**{**parents, "panel": {**parents["panel"], "row_count": 1}})
    with pytest.raises(HistoricalDailyBarGovernanceError):
        validate_historical_parent(**{**parents, "approval": {
            **parents["approval"], "approval_id": "wrong"}})
    with pytest.raises(HistoricalDailyBarGovernanceError):
        validate_historical_parent(**{**parents, "manifest": {
            **parents["manifest"], "dataset_id": "wrong"}})
    with pytest.raises(HistoricalDailyBarGovernanceError):
        validate_historical_parent(**{**parents,
            "revoked_approval_ids": (parents["approval"]["approval_id"],)})


def test_derived_representation_pins_parent_without_new_source_approval():
    parents = _parents()
    panel = parents["panel"]
    descriptor = HistoricalDailyBarShardDescriptorV1(
        month="2010-01", path="shards/2010-01/" + "s" * 64 + ".jsonl.gz",
        row_count=panel["row_count"], first_session="2010-01-04",
        last_session="2026-09-10", content_hash="c" * 64,
        storage_hash="s" * 64, membership_hash="f" * 64,
    )
    authority = HistoricalDailyBarFactAuthorityV1.create(
        parent_panel_id=panel["panel_id"],
        parent_approval_id=parents["approval"]["approval_id"],
        parent_manifest_id=parents["manifest"]["dataset_id"],
        source_binding_id=parents["binding"]["binding_id"],
        source_content_set_id=parents["binding"]["source_content_set_identity"],
        availability_evidence_id=parents["availability"]["evidence_id"],
        calendar_lineage_id=parents["availability"]["approved_calendar_lineage_id"],
        normalization_policy_id=panel["normalization_policy_id"],
        unit_policy_id=panel["unit_policy_id"],
        identity_policy_id=parents["binding"]["identity_policy_version"],
        raw_payload_hashes=tuple(panel["raw_payload_hashes"]),
        shards=(descriptor,), symbol_count=panel["symbol_count"],
        coverage_start=panel["coverage_start"], coverage_end=panel["coverage_end"],
    )
    observed = dict(row_count=panel["row_count"], symbol_count=panel["symbol_count"],
                    excluded_non_target_count=panel["excluded_non_target_row_count"],
                    frozen_session_observed_counts=tuple(map(tuple, panel["frozen_session_observed_counts"])),
                    frozen_session_symbol_hashes=tuple(map(tuple, panel["frozen_session_symbol_hashes"])))
    artifacts = create_derived_artifacts(
        authority=authority, observed=observed,
        requested_effective_symbol_sessions=panel["requested_effective_symbol_sessions"],
        receipt_count=len(parents["manifest"]["receipt_hashes"]),
        corrected_overlap_row_count=2_481_310,
        parent_composite=json.loads((GOVERNANCE / "phase1c-daily-bar-composite-0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744.json").read_text()),
        corrected_manifest=json.loads((ROOT / "data/phase_1b2b/governance/daily-bar-manifest-9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4.json").read_text()),
        **parents,
    )
    assert artifacts["approval"]["parent_approval_id"] == authority.parent_approval_id
    assert artifacts["approval"]["decision"] == "APPROVED_WITH_RULES"
    assert artifacts["manifest"]["authority_id"] == authority.authority_id
    assert artifacts["manifest"]["membership_set_hash"] == authority.membership_set_hash
    assert "source_name" not in artifacts["composition"]
    with pytest.raises(HistoricalDailyBarGovernanceError):
        create_derived_artifacts(
            authority=authority, observed={**observed, "row_count": 1},
            requested_effective_symbol_sessions=panel["requested_effective_symbol_sessions"],
            receipt_count=len(parents["manifest"]["receipt_hashes"]),
            corrected_overlap_row_count=2_481_310,
            parent_composite=json.loads((GOVERNANCE / "phase1c-daily-bar-composite-0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744.json").read_text()),
            corrected_manifest=json.loads((ROOT / "data/phase_1b2b/governance/daily-bar-manifest-9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4.json").read_text()),
            **parents,
        )
    # A changed effective-identity mapping cannot publish the frozen panel:
    # it changes either the target symbol census or its frozen sample set.
    with pytest.raises(HistoricalDailyBarGovernanceError):
        create_derived_artifacts(
            authority=authority,
            observed={**observed, "symbol_count": panel["symbol_count"] - 1},
            requested_effective_symbol_sessions=panel["requested_effective_symbol_sessions"],
            receipt_count=len(parents["manifest"]["receipt_hashes"]),
            corrected_overlap_row_count=2_481_310,
            parent_composite=json.loads((GOVERNANCE / "phase1c-daily-bar-composite-0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744.json").read_text()),
            corrected_manifest=json.loads((ROOT / "data/phase_1b2b/governance/daily-bar-manifest-9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4.json").read_text()),
            **parents,
        )
