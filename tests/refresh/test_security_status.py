import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.security_status import (
    SecurityStatusPublicationError,
    _status_lineage_coverage_valid,
    publish_security_status_increment,
    security_status_state_at,
)


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "data/phase_1b_exit_remediation/governance/daily_security_status-approval-ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07.json"
MAN = ROOT / "data/phase_1b_exit_remediation/governance/daily_security_status-manifest-d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0.json"
PANEL = ROOT / "data/phase_1b_exit_remediation/governance/historical-status-panel-cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707.json"
pytestmark=pytest.mark.skipif(not APP.is_file(),reason='repository-local governance artifacts are excluded from clean room')
ZONE = timezone(timedelta(hours=8))


def raw(kind, rows):
    return RawPayloadArtifactV1.create(
        request_id=("n" if kind == "name" else "s") * 64,
        page_identity={"offset": 0}, provider_payload={"rows": rows},
        semantic_metadata={"has_more": False, "total_count": len(rows)},
    )


def run(tmp_path, name_rows=(), suspension_rows=None, prior_risk_rows=None,
        target=date(2026,9,11), next_session=date(2026,9,14), observed=None):
    suspension_rows = suspension_rows if suspension_rows is not None else [
        {"ts_code": "000002.SZ", "trade_date": target.strftime('%Y%m%d'), "suspend_timing": None, "suspend_type": "S"}
    ]
    return publish_security_status_increment(
        output_root=tmp_path,
        previous_approval=json.loads(APP.read_text(encoding="utf-8")),
        previous_manifest=json.loads(MAN.read_text(encoding="utf-8")),
        previous_panel=json.loads(PANEL.read_text(encoding="utf-8")),
        prior_risk_warning_rows=prior_risk_rows or ({"ts_code":"000001.SZ","name":"*ST TEST","start_date":"20260901","end_date":None,"ann_date":"20260831","change_reason":"risk"},),
        raws=(raw("name", list(name_rows)), raw("suspend", suspension_rows)),
        receipt_hashes=("r" * 64, "t" * 64),
        research_safe_symbols=("000001.SZ", "000002.SZ", "600000.SH"),
        upstream_master_approval_id="a" * 64,
        upstream_master_manifest_id="m" * 64,
        target_session=target,
        next_approved_session=next_session,
        observed_at=observed or datetime(2026, 9, 14, 17, tzinfo=ZONE),
        prior_completed_sessions=(date(2026, 9, 10),),
    )


def test_status_increment_projects_only_upstream_universe_and_preserves_suspension(tmp_path):
    result = run(tmp_path)
    facts = {row["security_identity"]: row for row in result.increment.facts}
    assert tuple(facts) == ("000001.SZ", "000002.SZ", "600000.SH")
    assert facts["000002.SZ"]["is_suspended"] is True
    assert facts["000002.SZ"]["is_tradable"] is False
    assert facts["000001.SZ"]["is_risk_warning"] is True
    assert facts["000001.SZ"]["is_tradable"] is False
    assert result.coverage.systematic_defect is False
    assert result.coverage.resolved_status_securities == 3
    assert result.state.readiness.value == "READY"
    assert result.state.latest_approved_session == date(2026, 9, 11)


def test_incremental_manifest_may_extend_the_frozen_historical_panel():
    assert _status_lineage_coverage_valid(
        {"coverage_end": "2026-09-10"}, {"coverage_end": "2026-09-11"})
    assert not _status_lineage_coverage_valid(
        {"coverage_end": "2026-09-12"}, {"coverage_end": "2026-09-11"})


def test_upstream_excluded_status_event_does_not_become_global_blocker(tmp_path):
    event = {"ts_code": "688801.SH", "name": "new listing", "start_date": "20260911",
             "end_date": None, "ann_date": "20260911", "change_reason": "listing"}
    result = run(tmp_path, name_rows=(event,))
    assert result.coverage.systematic_defect is False
    assert "688801.SH" not in {row["security_identity"] for row in result.increment.facts}


def test_unknown_status_semantics_fail_closed_before_publication(tmp_path):
    bad = [{"ts_code": "000002.SZ", "trade_date": "20260911", "suspend_timing": None, "suspend_type": "X"}]
    with pytest.raises(SecurityStatusPublicationError, match="unknown suspension"):
        run(tmp_path, suspension_rows=bad)
    assert not (tmp_path / "governance").exists()


def test_missing_endpoint_payload_is_systemic_not_zero_event(tmp_path):
    with pytest.raises(SecurityStatusPublicationError, match="both status endpoints"):
        values = dict(
            output_root=tmp_path, previous_approval=json.loads(APP.read_text()),
            previous_manifest=json.loads(MAN.read_text()), previous_panel=json.loads(PANEL.read_text()),
            prior_risk_warning_rows=(),
            raws=(raw("name", []),), receipt_hashes=("r" * 64,),
            research_safe_symbols=("000001.SZ",), upstream_master_approval_id="a" * 64,
            upstream_master_manifest_id="m" * 64, target_session=date(2026, 9, 11),
            next_approved_session=date(2026, 9, 14), observed_at=datetime(2026, 9, 14, 1, tzinfo=ZONE),
        )
        publish_security_status_increment(**values)


def test_identical_status_publication_replays_without_artifact_churn(tmp_path):
    first = run(tmp_path)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file())
    second = run(tmp_path)
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file())
    assert (first.increment.fact_bundle_id, first.approval_id, first.manifest_id) == (
        second.increment.fact_bundle_id, second.approval_id, second.manifest_id)
    assert before == after


def test_status_visibility_changes_at_boundary_without_new_lineage(tmp_path):
    result=run(tmp_path)
    before=security_status_state_at(result.state,datetime(2026,9,14,16,29,59,tzinfo=ZONE))
    at=security_status_state_at(result.state,datetime(2026,9,14,16,30,tzinfo=ZONE))
    assert before.readiness.value=='READY'  # publication observed after boundary in run()
    from dataclasses import replace
    pending=replace(result.state,readiness=__import__('v5_2.refresh.contracts',fromlist=['DatasetReadiness']).DatasetReadiness.NOT_READY,
                    reason_codes=('AVAILABILITY_NOT_REACHED',))
    assert security_status_state_at(pending,datetime(2026,9,14,16,29,59,tzinfo=ZONE)).readiness.value=='NOT_READY'
    visible=security_status_state_at(pending,datetime(2026,9,14,16,30,tzinfo=ZONE))
    assert visible.readiness.value=='READY' and visible.reason_codes==()
    assert (visible.approval_id,visible.manifest_id)==(pending.approval_id,pending.manifest_id)


def test_same_day_status_observation_is_immediately_visible(tmp_path):
    observed=datetime(2026,9,14,20,tzinfo=ZONE)
    result=run(tmp_path,target=date(2026,9,14),next_session=date(2026,9,15),observed=observed)
    assert result.increment.available_at==observed
    assert result.state.readiness.value=='READY'
    assert result.state.availability_modes==('CONTEMPORANEOUS_OBSERVED',)
