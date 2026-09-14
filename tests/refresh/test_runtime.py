from datetime import datetime, timedelta, timezone

from datetime import date

import pytest

from v5_2.refresh.adapters import AvailabilityMode
from v5_2.refresh.runtime import (
    IncrementalValidationRequired,
    RawIncrementalExecutor,
    build_incremental_requests,
    build_refresh_service,
    classify_refresh_availability,
    resolve_endpoint_capability,
    resolve_governance_artifact,
)

pytestmark=pytest.mark.skipif(not (__import__('pathlib').Path(__file__).resolve().parents[2]/'data/phase_1b_exit_remediation').is_dir(),reason='repository-local governance artifacts are excluded from clean room')


def test_repository_runtime_builds_ready_snapshot_from_pinned_current_artifacts(tmp_path):
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    sh = timezone(timedelta(hours=8))
    service = build_refresh_service(
        root, snapshot_root=tmp_path,
        clock=lambda: datetime(2026, 9, 10, 20, 0, tzinfo=sh),
    )
    result = service.refresh()
    assert result.target_session.isoformat() == "2026-09-10"
    assert result.research_ready is True
    assert result.snapshot_id


def test_runtime_request_builder_is_target_driven_for_all_six_domains():
    missing = (date(2026, 9, 11), date(2026, 9, 14))
    assert [item.endpoint for item in build_incremental_requests("trade_calendar", missing)] == ["trade-cal", "trade-cal"]
    assert len(build_incremental_requests("security_master", missing)) == 6
    assert [item.parameters["trade_date"] for item in build_incremental_requests("daily_bar", missing)] == ["20260911", "20260914"]
    assert [item.endpoint for item in build_incremental_requests("daily_security_status", missing)] == ["namechange", "suspend-d"]
    assert [item.endpoint for item in build_incremental_requests("corporate_action", missing)] == ["dividend"]
    assert [item.endpoint for item in build_incremental_requests("financial_disclosure", missing)] == ["income", "balancesheet", "cashflow"]


def test_runtime_availability_never_projects_same_day_observation_into_history():
    observed = datetime(2026, 9, 14, 20, 4, tzinfo=timezone(timedelta(hours=8)))
    assert classify_refresh_availability(date(2026, 9, 14), observed)[0] is AvailabilityMode.CONTEMPORANEOUS_OBSERVED
    assert classify_refresh_availability(date(2026, 9, 11), observed)[0] is AvailabilityMode.HISTORICAL_RECONSTRUCTED


def test_repository_runtime_routes_real_gaps_through_one_incremental_executor(tmp_path):
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    sh = timezone(timedelta(hours=8))
    calls = []

    def execute(kind, current, target, missing):
        calls.append((kind, missing))
        from dataclasses import replace
        return replace(
            current, approval_id=(kind[0] + "a") * 32,
            manifest_id=(kind[0] + "m") * 32,
            latest_approved_session=target,
            completed_sessions=tuple(sorted(set((*current.completed_sessions, *missing)))),
            readiness=(current.readiness),
            availability_modes=(AvailabilityMode.CONTEMPORANEOUS_OBSERVED.value,),
        )

    service = build_refresh_service(
        root, snapshot_root=tmp_path,
        clock=lambda: datetime(2026, 9, 11, 20, 0, tzinfo=sh),
        incremental_executor=execute,
    )
    result = service.refresh()
    assert result.research_ready is True
    assert [kind for kind, _ in calls] == [
        "security_master", "daily_bar", "daily_security_status",
        "corporate_action", "financial_disclosure",
    ]


def test_raw_incremental_executor_persists_lineage_then_fails_closed_pending_validation(tmp_path):
    from v5_2.data.raw_artifacts import RawPayloadArtifactV1
    from v5_2.refresh.adapters import DatasetStateV1
    from v5_2.refresh.contracts import DatasetReadiness

    calls = []

    def acquire(request):
        calls.append(request)
        return (RawPayloadArtifactV1.create(
            request_id=request.request_id, page_identity={"offset": 0},
            provider_payload={"rows": [{"trade_date": "20260911"}]},
            semantic_metadata={"has_more": False, "total_count": 1},
        ),)

    state = DatasetStateV1(
        "daily_bar", "a" * 64, "m" * 64, date(2026, 9, 10),
        (date(2026, 9, 10),), "2026-09-10", DatasetReadiness.READY,
    )
    executor = RawIncrementalExecutor(tmp_path, acquire=acquire,
                                      clock=lambda: datetime(2026, 9, 13, tzinfo=timezone.utc))
    try:
        executor("daily_bar", state, date(2026, 9, 11), (date(2026, 9, 11),))
    except IncrementalValidationRequired as error:
        assert error.artifact_id
    else:
        raise AssertionError("unvalidated acquisition must fail closed")
    assert len(calls) == 1
    artifacts = list((tmp_path / "governance" / "incremental-candidates").glob("*.json"))
    assert len(artifacts) == 1
    assert "2026-09-11" in artifacts[0].read_text(encoding="utf-8")


def test_financial_scoped_assessment_does_not_issue_invalid_market_wide_requests(tmp_path):
    from v5_2.refresh.adapters import DatasetStateV1
    from v5_2.refresh.contracts import DatasetReadiness
    state = DatasetStateV1("financial_disclosure", "a"*64, "m"*64, date(2026,9,10),
        (date(2026,9,10),), "2026-09-10", DatasetReadiness.SCOPED_READY)
    observed=[]
    def publish(kind,current,target,missing,artifacts,at):
        observed.append((kind,missing,artifacts)); return current
    executor=RawIncrementalExecutor(tmp_path,acquire=lambda request: (_ for _ in ()).throw(AssertionError('must not acquire')),
        clock=lambda:datetime(2026,9,14,tzinfo=timezone.utc),publisher=publish)
    assert executor("financial_disclosure",state,date(2026,9,11),(date(2026,9,11),)) is state
    assert observed==[("financial_disclosure",(date(2026,9,11),),())]


def test_calendar_bootstrap_consumes_executor_publication_before_target_resolution(tmp_path):
    from dataclasses import replace

    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    sh = timezone(timedelta(hours=8))

    def execute(kind, current, target, missing):
        if kind == "trade_calendar":
            assert target == date(2026, 9, 14)
            completed = tuple(sorted((*current.completed_sessions, date(2026, 9, 14))))
        else:
            completed = tuple(sorted(set((*current.completed_sessions, *missing))))
        return replace(
            current, approval_id="a" * 64, manifest_id="m" * 64,
            latest_approved_session=target,
            completed_sessions=completed,
        )

    service = build_refresh_service(
        root, snapshot_root=tmp_path,
        clock=lambda: datetime(2026, 9, 14, 0, 5, tzinfo=sh),
        incremental_executor=execute,
    )
    result = service.refresh()
    assert result.target_session == date(2026, 9, 11)


def test_superseding_lineage_resolves_from_phase1c_before_frozen_baseline(tmp_path):
    runtime=tmp_path/'phase1c'; baseline=tmp_path/'baseline'; runtime.mkdir(); baseline.mkdir()
    current=runtime/'security_master-approval-current.json'; current.write_text('{}')
    old=baseline/'security_master-approval-current.json'; old.write_text('{"old":true}')
    assert resolve_governance_artifact(runtime,baseline,'security_master-approval-current.json')==current
    current.unlink()
    assert resolve_governance_artifact(runtime,baseline,'security_master-approval-current.json')==old


def test_endpoint_capability_is_resolved_by_schema_not_evidence_order(tmp_path):
    from v5_2.data.identity import canonical_json, content_hash
    root=tmp_path/'governance'; root.mkdir()
    body={'schema_version':'FinancialEndpointCapabilityAuditV1','source_name':'source',
          'approved_candidate_endpoints':['income'],'entries':[],'unsupported_for_primary_facts':[]}
    artifact_id=content_hash(body)
    (root/f'endpoint-capability-{artifact_id}.json').write_bytes(canonical_json(
        {'audit_id':artifact_id,'content_hash':artifact_id,**body}))

    path=resolve_endpoint_capability(('0'*64,artifact_id),(root,))

    assert path.name==f'endpoint-capability-{artifact_id}.json'
