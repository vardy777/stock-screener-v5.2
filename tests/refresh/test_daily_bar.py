import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.daily_bar import DailyBarPublicationError, build_daily_bar_increment, daily_bar_state_at, publish_daily_bar_increment

pytestmark=pytest.mark.skipif(not (Path(__file__).resolve().parents[2]/'data/phase_1b_exit_remediation').is_dir(),reason='repository-local governance artifacts are excluded from clean room')

def row(symbol): return {'ts_code':symbol,'trade_date':'20260911','open':10,'high':11,'low':9,'close':10.5,'vol':100,'amount':200}
def build(rows=None,expected=('600000.SH','000001.SZ','000002.SZ')):
    rows=rows or [row('600000.SH'),row('000001.SZ')]
    raw=RawPayloadArtifactV1.create(request_id='x'*64,page_identity={'offset':0},provider_payload={'rows':rows},semantic_metadata={'has_more':False})
    return build_daily_bar_increment(session=date(2026,9,11),next_approved_session=date(2026,9,14),research_safe_symbols=expected,raws=(raw,))

def test_individual_missing_bar_is_explicit_exclusion_not_systemic():
    value=build(); assert value.coverage.excluded_symbols==('000002.SZ',); assert value.coverage.systematic_defect is False
    assert value.available_at.isoformat()=='2026-09-14T16:30:00+08:00'

@pytest.mark.parametrize('clock,visible',[(datetime(2026,9,14,16,29,59,tzinfo=timezone(timedelta(hours=8))),False),(datetime(2026,9,14,16,30,tzinfo=timezone(timedelta(hours=8))),True),(datetime(2026,9,14,16,30,1,tzinfo=timezone(timedelta(hours=8))),True)])
def test_next_session_safe_visibility_boundary(clock,visible): assert build().research_visible(clock) is visible

def test_whole_exchange_missing_is_systemic_failure():
    with pytest.raises(DailyBarPublicationError,match='systemic'): build(rows=[row('600000.SH')])

def test_semantic_input_replays_identically(): assert build()==build()

def test_publication_persists_once_and_clock_only_changes_visibility(tmp_path):
    root=Path(__file__).resolve().parents[2]
    approval=json.loads((root/'data/phase_1b_exit_remediation/governance/daily_bar-approval-fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5.json').read_text(encoding='utf-8'))
    manifest=json.loads((root/'data/phase_1b_exit_remediation/governance/daily_bar-manifest-76c4fe58d0714405d0a6a826bf9b814237d812f88f69b63986a0e0317f924b4b.json').read_text(encoding='utf-8'))
    rows=[row('600000.SH'),row('000001.SZ')]
    raw=RawPayloadArtifactV1.create(request_id='x'*64,page_identity={'offset':0},provider_payload={'rows':rows},semantic_metadata={'has_more':False})
    args=dict(output_root=tmp_path,previous_approval=approval,previous_manifest=manifest,raws=(raw,),receipt_hashes=('r'*64,),
        research_safe_symbols=('600000.SH','000001.SZ','000002.SZ'),session=date(2026,9,11),next_approved_session=date(2026,9,14),
        observed_at=datetime(2026,9,14,0,30,tzinfo=timezone(timedelta(hours=8))))
    first=publish_daily_bar_increment(**args); second=publish_daily_bar_increment(**args)
    assert (first.increment.fact_bundle_id,first.approval_id,first.manifest_id)==(second.increment.fact_bundle_id,second.approval_id,second.manifest_id)
    assert not first.increment.research_visible(datetime(2026,9,14,16,29,59,tzinfo=timezone(timedelta(hours=8))))
    assert first.increment.research_visible(datetime(2026,9,14,16,30,tzinfo=timezone(timedelta(hours=8))))
    before=daily_bar_state_at(first.state,datetime(2026,9,14,16,29,59,tzinfo=timezone(timedelta(hours=8))))
    at=daily_bar_state_at(first.state,datetime(2026,9,14,16,30,tzinfo=timezone(timedelta(hours=8))))
    after=daily_bar_state_at(first.state,datetime(2026,9,14,16,30,1,tzinfo=timezone(timedelta(hours=8))))
    assert before.readiness.value=='NOT_READY' and before.reason_codes==('AVAILABILITY_NOT_REACHED',)
    assert at.readiness.value==after.readiness.value=='READY'
    assert (before.approval_id,before.manifest_id)==(at.approval_id,at.manifest_id)==(after.approval_id,after.manifest_id)

def test_same_day_observed_publication_is_immediately_visible(tmp_path):
    approval=json.loads((Path(__file__).resolve().parents[2]/'data/phase_1b_exit_remediation/governance/daily_bar-approval-fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5.json').read_text())
    manifest=json.loads((Path(__file__).resolve().parents[2]/'data/phase_1b_exit_remediation/governance/daily_bar-manifest-76c4fe58d0714405d0a6a826bf9b814237d812f88f69b63986a0e0317f924b4b.json').read_text())
    rows=[{**row('600000.SH'),'trade_date':'20260914'},{**row('000001.SZ'),'trade_date':'20260914'}]
    raw=RawPayloadArtifactV1.create(request_id='z'*64,page_identity={'offset':0},provider_payload={'rows':rows},semantic_metadata={'has_more':False})
    observed=datetime(2026,9,14,20,tzinfo=timezone(timedelta(hours=8)))
    result=publish_daily_bar_increment(output_root=tmp_path,previous_approval=approval,previous_manifest=manifest,
        raws=(raw,),receipt_hashes=('r'*64,),research_safe_symbols=('600000.SH','000001.SZ'),session=date(2026,9,14),
        next_approved_session=date(2026,9,15),observed_at=observed)
    assert result.increment.available_at==observed
    assert result.increment.availability_mode=='CONTEMPORANEOUS_OBSERVED'
    assert result.state.readiness.value=='READY'

def test_same_day_observation_does_not_require_a_future_calendar_session():
    rows=[{**row('600000.SH'),'trade_date':'20260914'},{**row('000001.SZ'),'trade_date':'20260914'}]
    raw=RawPayloadArtifactV1.create(request_id='y'*64,page_identity={'offset':0},provider_payload={'rows':rows},semantic_metadata={'has_more':False})
    observed=datetime(2026,9,14,22,30,tzinfo=timezone(timedelta(hours=8)))
    result=build_daily_bar_increment(session=date(2026,9,14),next_approved_session=date(2026,9,14),
        research_safe_symbols=('600000.SH','000001.SZ'),raws=(raw,),observed_at=observed)
    assert result.available_at==observed
    assert result.availability_mode=='CONTEMPORANEOUS_OBSERVED'
