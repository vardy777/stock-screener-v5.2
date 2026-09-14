import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from v5_2.refresh.financial_disclosure import FinancialIncrementError, publish_financial_scope_assessment

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'data/phase_1b2d/governance/financial-disclosure-approval-58afcda2811226574060a352351eb00fc09b066a43c512c1843a8821f69f0498.json'
MAN=ROOT/'data/phase_1b2d/governance/financial-disclosure-manifest-0b5e72283c045c485eff9ecd2161f019980bdea7ccb33fbcdbdf137d1e13706f.json'
CAP=ROOT/'data/phase_1b2d/governance/endpoint-capability-f3ebeac1041826962904c1980e3b311dcb8e176d8c50546fe8b82c309b32eba1.json'
pytestmark=pytest.mark.skipif(not APP.is_file(),reason='repository-local governance artifacts are excluded from clean room')

def run(tmp_path,capability=None):
    return publish_financial_scope_assessment(output_root=tmp_path,
        previous_approval=json.loads(APP.read_text(encoding='utf-8')),previous_manifest=json.loads(MAN.read_text(encoding='utf-8')),
        endpoint_capability=capability or json.loads(CAP.read_text(encoding='utf-8')),target_session=date(2026,9,11),
        observed_at=datetime(2026,9,14,tzinfo=timezone.utc),prior_completed_sessions=(date(2026,9,10),))

def test_symbol_scoped_provider_limitation_remains_observed_facts_only(tmp_path):
    result=run(tmp_path)
    assert result.state.readiness.value=='SCOPED_READY'
    assert result.new_fact_count==0
    assert result.publication_scope=='OBSERVED_FACTS_ONLY'
    manifest=json.loads((tmp_path/'governance'/f'financial_disclosure-manifest-{result.manifest_id}.json').read_text())
    assert manifest['latest_approved_publication_date']=='2026-09-01'
    assert manifest['coverage_gaps'][-1][2]=='PANEL_COMPLETENESS_NOT_ESTABLISHED__MISSING_QUERY_NOT_RESEARCH_SAFE'

def test_tampered_capability_fails_closed(tmp_path):
    value=json.loads(CAP.read_text()); value['source_name']='tampered'
    with pytest.raises(FinancialIncrementError,match='capability integrity'):
        run(tmp_path,value)
    assert not (tmp_path/'governance').exists()

def test_scope_assessment_replays_identically(tmp_path):
    first=run(tmp_path); second=run(tmp_path)
    assert (first.approval_id,first.manifest_id)==(second.approval_id,second.manifest_id)
