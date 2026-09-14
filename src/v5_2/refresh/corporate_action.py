from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.refresh.adapters import AvailabilityMode, DatasetStateV1
from v5_2.refresh.contracts import DatasetReadiness


class CorporateActionIncrementError(RuntimeError): pass


@dataclass(frozen=True, slots=True)
class CorporateActionPublicationV1:
    state: DatasetStateV1
    approval_id: str
    manifest_id: str
    fact_count: int
    supported_action_types: tuple[str,...]
    unsupported_action_types: tuple[str,...]


def _valid(value,ids,schema):
    body={key:item for key,item in value.items() if key not in ids}
    return value.get(ids[0])==value.get(ids[1])==content_hash({'schema_version':schema,**body})


def _write(path:Path,value):
    encoded=canonical_json(value); path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
    except FileExistsError:
        if path.read_bytes()!=encoded: raise CorporateActionIncrementError('immutable corporate action collision') from None
    else:
        with os.fdopen(fd,'wb') as stream: stream.write(encoded)


def publish_corporate_action_increment(*,output_root:Path,previous_approval:Mapping[str,object],
    previous_manifest:Mapping[str,object],raws:Sequence[RawPayloadArtifactV1],receipt_hashes:tuple[str,...],
    target_session:date,observed_at:datetime,prior_completed_sessions:tuple[date,...]=())->CorporateActionPublicationV1:
    if not _valid(previous_approval,('approval_id','content_hash'),'SourceApprovalArtifactV1'): raise CorporateActionIncrementError('approval integrity invalid')
    if not _valid(previous_manifest,('dataset_id','manifest_hash'),'DatasetManifestV1'): raise CorporateActionIncrementError('manifest integrity invalid')
    if previous_manifest.get('approval_id')!=previous_approval.get('approval_id'): raise CorporateActionIncrementError('lineage mismatch')
    if len(raws)!=1 or len(receipt_hashes)!=1: raise CorporateActionIncrementError('raw and receipt lineage required')
    raw=raws[0]
    if raw.semantic_metadata.get('has_more') is not False: raise CorporateActionIncrementError('pagination completeness required')
    rows=tuple(dict(row) for row in raw.provider_payload.get('rows',()))
    if rows: raise CorporateActionIncrementError('non-empty corporate action increment requires semantic normalization')
    supported=tuple(sorted(previous_approval['rule_set']['supported_action_types']))
    unsupported=tuple(sorted(previous_approval['rule_set']['unsupported_action_types']))
    if supported!=('BONUS_SHARE','CASH_DIVIDEND') or unsupported!=('RIGHTS_ISSUE','SHARE_CONVERSION','STOCK_SPLIT'):
        raise CorporateActionIncrementError('frozen scoped action contract mismatch')
    evidence_body={'schema_version':'CorporateActionNoEventCoverageV1','target_session':target_session,
        'request_id':raw.request_id,'payload_hash':raw.payload_hash,'row_count':0,'pagination_complete':True,
        'supported_action_types':supported,'unsupported_action_types':unsupported}
    evidence_id=content_hash(evidence_body)
    evidence=tuple(sorted((*previous_approval['evidence_ids'],evidence_id)))
    approval_body={'schema_version':'SourceApprovalArtifactV1','source_name':previous_approval['source_name'],
        'dataset_kind':'corporate_action','decision':'APPROVED_WITH_RULES','coverage_start':previous_approval['coverage_start'],
        'coverage_end':target_session,'verified_at':observed_at,
        'source_version_identity':content_hash((previous_approval['source_version_identity'],raw.payload_hash)),
        'policy_version':previous_approval['policy_version'],'rule_set':{**previous_approval['rule_set'],'incremental_coverage_id':evidence_id},
        'evidence_ids':evidence,'evidence_bundle_hash':content_hash(evidence),'evaluator_version':'phase-1c-corporate-action-increment-v1',
        'evidence_validity_policy_version':previous_approval['evidence_validity_policy_version'],
        'equivalence_evidence_id':previous_approval['equivalence_evidence_id'],'supersedes_approval_id':previous_approval['approval_id']}
    approval_id=content_hash(approval_body); approval={'approval_id':approval_id,'content_hash':approval_id,**{k:v for k,v in approval_body.items() if k!='schema_version'}}
    manifest_body={k:v for k,v in previous_manifest.items() if k not in {'dataset_id','manifest_hash'}}
    def extend(items):
        result=[]
        for kind,start,end in items:
            result.append((kind,start,target_session if kind in supported else end))
        return tuple(result)
    manifest_body.update({'created_at':observed_at,'approval_id':approval_id,'approval_content_hash':approval_id,
        'approval_resolution_as_of':observed_at,'coverage_end':target_session,'latest_approved_session':target_session,
        'raw_payload_hashes':tuple((*previous_manifest['raw_payload_hashes'],raw.payload_hash)),
        'normalized_content_hashes':tuple((*previous_manifest['normalized_content_hashes'],evidence_id)),
        'receipt_hashes':tuple((*previous_manifest['receipt_hashes'],*receipt_hashes)),
        'validated_coverage_by_action_type':extend(previous_manifest['validated_coverage_by_action_type']),
        'materialized_coverage_by_action_type':extend(previous_manifest['materialized_coverage_by_action_type']),
        'quality_findings':tuple((*previous_manifest['quality_findings'],'terminal zero-row increment; no supported event observed'))})
    manifest_id=content_hash({'schema_version':'DatasetManifestV1',**manifest_body}); manifest={'dataset_id':manifest_id,'manifest_hash':manifest_id,**manifest_body}
    gov=output_root/'governance'; _write(gov/f'corporate-action-coverage-{evidence_id}.json',evidence_body)
    _write(gov/f'corporate_action-approval-{approval_id}.json',approval); _write(gov/f'corporate_action-manifest-{manifest_id}.json',manifest)
    state=DatasetStateV1('corporate_action',approval_id,manifest_id,target_session,
        tuple(sorted(set((*prior_completed_sessions,target_session)))),target_session.isoformat(),DatasetReadiness.SCOPED_READY,
        availability_modes=(AvailabilityMode.HISTORICAL_RECONSTRUCTED.value,))
    state_body={'schema_version':'Phase1CDatasetStateV1',**asdict(state)}; state_id=content_hash(state_body)
    _write(gov/f'corporate_action-state-{state_id}.json',{'state_id':state_id,**state_body})
    pointer=output_root/'corporate_action-current-state-id.txt'; tmp=pointer.with_suffix('.tmp'); tmp.write_text(state_id,encoding='ascii'); os.replace(tmp,pointer)
    return CorporateActionPublicationV1(state,approval_id,manifest_id,0,supported,unsupported)
