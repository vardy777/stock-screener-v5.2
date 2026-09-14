from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping

from v5_2.data.identity import canonical_json, content_hash
from v5_2.refresh.adapters import AvailabilityMode, DatasetStateV1
from v5_2.refresh.contracts import DatasetReadiness


class FinancialIncrementError(RuntimeError): pass


@dataclass(frozen=True, slots=True)
class FinancialScopePublicationV1:
    state: DatasetStateV1
    approval_id: str
    manifest_id: str
    new_fact_count: int
    publication_scope: str


def _valid(value,ids,schema):
    body={key:item for key,item in value.items() if key not in ids}
    return value.get(ids[0])==value.get(ids[1])==content_hash({'schema_version':schema,**body})


def _write(path:Path,value):
    encoded=canonical_json(value); path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
    except FileExistsError:
        if path.read_bytes()!=encoded: raise FinancialIncrementError('immutable financial disclosure collision') from None
    else:
        with os.fdopen(fd,'wb') as stream: stream.write(encoded)


def publish_financial_scope_assessment(*,output_root:Path,previous_approval:Mapping[str,object],
    previous_manifest:Mapping[str,object],endpoint_capability:Mapping[str,object],target_session:date,
    observed_at:datetime,prior_completed_sessions:tuple[date,...]=())->FinancialScopePublicationV1:
    if not _valid(previous_approval,('approval_id','content_hash'),'SourceApprovalArtifactV1'): raise FinancialIncrementError('approval integrity invalid')
    if not _valid(previous_manifest,('dataset_id','manifest_hash'),'DatasetManifestV1'): raise FinancialIncrementError('manifest integrity invalid')
    if previous_manifest.get('approval_id')!=previous_approval.get('approval_id'): raise FinancialIncrementError('lineage mismatch')
    capability_body={key:value for key,value in endpoint_capability.items() if key not in {'audit_id','content_hash'}}
    capability_id=content_hash({'schema_version':'FinancialEndpointCapabilityAuditV1',**{k:v for k,v in capability_body.items() if k!='schema_version'}})
    if endpoint_capability.get('audit_id')!=endpoint_capability.get('content_hash') or endpoint_capability.get('audit_id')!=capability_id:
        raise FinancialIncrementError('capability integrity invalid')
    supported=tuple(sorted(previous_approval['rule_set']['supported_statement_types']))
    if tuple(sorted(endpoint_capability['approved_candidate_endpoints']))!=('balancesheet','cashflow','income'):
        raise FinancialIncrementError('capability scope mismatch')
    assessment_body={'schema_version':'FinancialIncrementScopeAssessmentV1','target_session':target_session,
        'endpoint_capability_id':capability_id,'publication_scope':'OBSERVED_FACTS_ONLY','historical_coverage':'PARTIAL',
        'provider_query_constraint':'TS_CODE_REQUIRED','new_fact_count':0,
        'missing_query_result':'NOT_RESEARCH_SAFE','supported_statement_types':supported}
    assessment_id=content_hash(assessment_body)
    evidence=tuple(sorted((*previous_approval['evidence_ids'],assessment_id)))
    approval_body={'schema_version':'SourceApprovalArtifactV1','source_name':previous_approval['source_name'],
        'dataset_kind':'financial_disclosure','decision':'APPROVED_WITH_RULES','coverage_start':previous_approval['coverage_start'],
        'coverage_end':target_session,'verified_at':observed_at,
        'source_version_identity':content_hash((previous_approval['source_version_identity'],assessment_id)),
        'policy_version':previous_approval['policy_version'],'rule_set':{**previous_approval['rule_set'],
            'incremental_scope_assessment_id':assessment_id,'provider_query_constraint':'TS_CODE_REQUIRED'},
        'evidence_ids':evidence,'evidence_bundle_hash':content_hash(evidence),'evaluator_version':'phase-1c-financial-scope-v1',
        'evidence_validity_policy_version':previous_approval['evidence_validity_policy_version'],
        'equivalence_evidence_id':previous_approval['equivalence_evidence_id'],'supersedes_approval_id':previous_approval['approval_id']}
    approval_id=content_hash(approval_body); approval={'approval_id':approval_id,'content_hash':approval_id,**{k:v for k,v in approval_body.items() if k!='schema_version'}}
    gap=(previous_manifest['coverage_start'],target_session,'PANEL_COMPLETENESS_NOT_ESTABLISHED__MISSING_QUERY_NOT_RESEARCH_SAFE')
    manifest_body={k:v for k,v in previous_manifest.items() if k not in {'dataset_id','manifest_hash'}}
    manifest_body.update({'created_at':observed_at,'approval_id':approval_id,'approval_content_hash':approval_id,
        'approval_resolution_as_of':observed_at,'coverage_end':target_session,'coverage_gaps':(gap,),
        'normalized_content_hashes':tuple((*previous_manifest['normalized_content_hashes'],assessment_id)),
        'quality_findings':tuple((*previous_manifest['quality_findings'],'Phase 1C market-wide date query unsupported; missing remains unknown'))})
    manifest_id=content_hash({'schema_version':'DatasetManifestV1',**manifest_body}); manifest={'dataset_id':manifest_id,'manifest_hash':manifest_id,**manifest_body}
    gov=output_root/'governance'; _write(gov/f'financial-scope-assessment-{assessment_id}.json',assessment_body)
    _write(gov/f'financial_disclosure-approval-{approval_id}.json',approval); _write(gov/f'financial_disclosure-manifest-{manifest_id}.json',manifest)
    state=DatasetStateV1('financial_disclosure',approval_id,manifest_id,target_session,
        tuple(sorted(set((*prior_completed_sessions,target_session)))),target_session.isoformat(),DatasetReadiness.SCOPED_READY,
        reason_codes=('OBSERVED_FACTS_ONLY','PANEL_COMPLETENESS_PARTIAL'),availability_modes=(AvailabilityMode.HISTORICAL_RECONSTRUCTED.value,))
    state_body={'schema_version':'Phase1CDatasetStateV1',**asdict(state)}; state_id=content_hash(state_body)
    _write(gov/f'financial_disclosure-state-{state_id}.json',{'state_id':state_id,**state_body})
    pointer=output_root/'financial_disclosure-current-state-id.txt'; tmp=pointer.with_suffix('.tmp'); tmp.write_text(state_id,encoding='ascii'); os.replace(tmp,pointer)
    return FinancialScopePublicationV1(state,approval_id,manifest_id,0,'OBSERVED_FACTS_ONLY')
