import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.corporate_action import CorporateActionIncrementError, publish_corporate_action_increment

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'data/phase_1b2c/governance/corporate_action-approval-5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974.json'
MAN=ROOT/'data/phase_1b2c/governance/corporate-action-manifest-5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c.json'
pytestmark=pytest.mark.skipif(not APP.is_file(),reason='repository-local governance artifacts are excluded from clean room')

def raw(rows=(),has_more=False):
    return RawPayloadArtifactV1.create(request_id='c'*64,page_identity={'offset':0},provider_payload={'rows':list(rows)},semantic_metadata={'has_more':has_more,'total_count':len(rows),'response_code':0})

def run(tmp_path, item=None):
    return publish_corporate_action_increment(output_root=tmp_path,
        previous_approval=json.loads(APP.read_text(encoding='utf-8')),previous_manifest=json.loads(MAN.read_text(encoding='utf-8')),
        raws=(item or raw(),),receipt_hashes=('r'*64,),target_session=date(2026,9,11),
        observed_at=datetime(2026,9,14,tzinfo=timezone.utc),prior_completed_sessions=(date(2026,9,10),))

def test_terminal_zero_rows_extends_scoped_coverage_without_inventing_event(tmp_path):
    result=run(tmp_path)
    assert result.fact_count==0 and result.state.readiness.value=='SCOPED_READY'
    assert result.supported_action_types==('BONUS_SHARE','CASH_DIVIDEND')
    assert result.unsupported_action_types==('RIGHTS_ISSUE','SHARE_CONVERSION','STOCK_SPLIT')

def test_nonterminal_zero_rows_is_unknown_and_fails_closed(tmp_path):
    with pytest.raises(CorporateActionIncrementError,match='pagination'):
        run(tmp_path,raw(has_more=True))
    assert not (tmp_path/'governance').exists()

def test_identical_no_event_publication_is_idempotent(tmp_path):
    first=run(tmp_path); second=run(tmp_path)
    assert (first.approval_id,first.manifest_id)==(second.approval_id,second.manifest_id)
