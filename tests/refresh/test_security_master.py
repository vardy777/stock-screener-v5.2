import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.security_master import SecurityMasterPublicationError, publish_security_master_increment

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'data/phase_1b1_2026_extension/governance/security_master-approval-828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c.json'
MAN=ROOT/'data/phase_1b_exit_remediation/governance/security-master-complete-manifest-025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b.json'
pytestmark=pytest.mark.skipif(not APP.is_file(),reason='repository-local governance artifacts are excluded from clean room')
OPEN=tuple(date(2026,9,d) for d in (10,11,14,15,16,17,18))

def row(code,name,listed):
    symbol=code[:6]
    return {'ts_code':code,'symbol':symbol,'name':name,'market':'科创板' if symbol.startswith('688') else '主板',
            'exchange':'SSE','list_status':'L','list_date':listed,'delist_date':None}

def run(tmp_path, rows=None, **extra):
    approval=json.loads(APP.read_text(encoding='utf-8')); manifest=json.loads(MAN.read_text(encoding='utf-8'))
    rows=rows or [row('600000.SH','浦发银行','19991110'),row('688801.SH','燧原科技','20260911')]
    raw=RawPayloadArtifactV1.create(request_id='r'*64,page_identity={'offset':0},provider_payload={'rows':rows},semantic_metadata={'has_more':False,'total_count':len(rows)})
    values=dict(output_root=tmp_path,previous_approval=approval,previous_manifest=manifest,raws=(raw,),receipt_hashes=('x'*64,),
        prior_effective_symbols=frozenset({'600000.SH'}),target_session=date(2026,9,11),approved_open_sessions=OPEN,
        observed_at=datetime(2026,9,14,tzinfo=timezone.utc)); values.update(extra)
    return publish_security_master_increment(**values)

def test_ipo_is_known_effective_but_excluded_without_systemic_failure(tmp_path):
    result=run(tmp_path)
    assert result.state.readiness.value=='READY'
    assert result.coverage.effective_security_count==2
    assert result.coverage.research_eligible_count==1
    assert result.coverage.exclusion_reason_counts==(('IPO_SEASONING',1),)
    assert result.coverage.systematic_defect is False

def test_duplicate_identity_is_systemic_and_publishes_nothing(tmp_path):
    duplicate=row('600000.SH','浦发银行','19991110')
    with pytest.raises(SecurityMasterPublicationError,match='duplicate'):
        run(tmp_path,rows=[duplicate,duplicate])
    assert not (tmp_path/'governance').exists()

def test_unexplained_disappearance_is_systemic(tmp_path):
    with pytest.raises(SecurityMasterPublicationError,match='systemic'):
        run(tmp_path,rows=[row('688801.SH','燧原科技','20260911')])

def test_identical_master_publication_is_deterministic(tmp_path):
    assert run(tmp_path)==run(tmp_path)
