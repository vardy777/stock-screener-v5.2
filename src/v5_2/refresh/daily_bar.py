from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from v5_2.data.identity import content_hash
from v5_2.data.identity import canonical_json
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.data.real_audits.daily_bar_normalization import DailyBarNormalizationPolicyV1
from v5_2.refresh.adapters import AvailabilityMode, SHANGHAI
from v5_2.refresh.adapters import DatasetStateV1
from v5_2.refresh.contracts import DatasetReadiness


class DailyBarPublicationError(RuntimeError): pass


@dataclass(frozen=True, slots=True)
class DailyBarCoverageV1:
    coverage_id: str
    expected_symbols: tuple[str,...]
    valid_symbols: tuple[str,...]
    excluded_symbols: tuple[str,...]
    coverage_ratio: float
    systematic_defect: bool
    content_hash: str


@dataclass(frozen=True, slots=True)
class DailyBarIncrementV1:
    fact_bundle_id: str
    session: date
    available_at: datetime
    availability_mode: str
    facts: tuple[Mapping[str,object],...]
    coverage: DailyBarCoverageV1
    content_hash: str

    def research_visible(self, cutoff: datetime) -> bool:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None: raise ValueError("cutoff must be aware")
        return cutoff.astimezone(SHANGHAI) >= self.available_at


@dataclass(frozen=True, slots=True)
class DailyBarPublicationV1:
    state: DatasetStateV1
    increment: DailyBarIncrementV1
    approval_id: str
    manifest_id: str


def daily_bar_state_at(state: DatasetStateV1, now: datetime) -> DatasetStateV1:
    if state.reason_codes != ('AVAILABILITY_NOT_REACHED',) or not state.watermark.startswith('visibility:'):
        return state
    if now.tzinfo is None or now.utcoffset() is None: raise ValueError('clock must be aware')
    boundary=datetime.fromisoformat(state.watermark.split(':',1)[1])
    if now.astimezone(SHANGHAI) < boundary.astimezone(SHANGHAI): return state
    from dataclasses import replace
    return replace(state,readiness=DatasetReadiness.READY,reason_codes=())


def _valid(value, ids, schema):
    body={k:v for k,v in value.items() if k not in ids}
    return value.get(ids[0])==value.get(ids[1])==content_hash({'schema_version':schema,**body})


def _write(path: Path, value: object):
    encoded=canonical_json(value); path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
    except FileExistsError:
        if path.read_bytes()!=encoded: raise DailyBarPublicationError('immutable daily bar collision') from None
    else:
        with os.fdopen(fd,'wb') as stream: stream.write(encoded)


def build_daily_bar_increment(*, session: date, next_approved_session: date,
    research_safe_symbols: tuple[str,...], raws: Sequence[RawPayloadArtifactV1],
    observed_at: datetime | None = None) -> DailyBarIncrementV1:
    contemporaneous = observed_at is not None and observed_at.astimezone(SHANGHAI).date() == session
    if not contemporaneous and next_approved_session <= session:
        raise DailyBarPublicationError("next approved session required")
    rows=[dict(row) for raw in raws for row in raw.provider_payload.get('rows',())]
    by_symbol={}
    policy=DailyBarNormalizationPolicyV1.create_default()
    for row in rows:
        if row.get('trade_date') != session.strftime('%Y%m%d'): raise DailyBarPublicationError("session drift")
        symbol=str(row.get('ts_code',''))
        if symbol in by_symbol: raise DailyBarPublicationError("duplicate bar")
        candidate=policy.normalize(row,volume_factor=Decimal('100'),amount_factor=Decimal('1000'),effective_identity=symbol)
        if not (candidate.low <= candidate.open <= candidate.high and candidate.low <= candidate.close <= candidate.high
                and candidate.volume >= 0 and candidate.amount >= 0): raise DailyBarPublicationError("OHLC or unit semantic drift")
        by_symbol[symbol]=candidate
    expected=tuple(sorted(set(research_safe_symbols))); observed=set(by_symbol)&set(expected)
    if not observed or not any(x.endswith('.SH') for x in observed) or not any(x.endswith('.SZ') for x in observed):
        raise DailyBarPublicationError("systemic exchange coverage defect")
    excluded=tuple(sorted(set(expected)-observed))
    coverage_body={'schema_version':'DailyBarCoverageV1','expected_symbols':expected,'valid_symbols':tuple(sorted(observed)),
        'excluded_symbols':excluded,'coverage_ratio':len(observed)/len(expected),'systematic_defect':False}
    coverage_id=content_hash(coverage_body); coverage=DailyBarCoverageV1(coverage_id,content_hash=coverage_id,
        **{k:v for k,v in coverage_body.items() if k!='schema_version'})
    available_at=observed_at if contemporaneous else datetime.combine(next_approved_session,time(16,30),SHANGHAI)
    availability_mode=(AvailabilityMode.CONTEMPORANEOUS_OBSERVED.value if contemporaneous
                       else AvailabilityMode.HISTORICAL_RECONSTRUCTED.value)
    facts=tuple({'security_identity':s,'session':session,'open':str(by_symbol[s].open),'high':str(by_symbol[s].high),
        'low':str(by_symbol[s].low),'close':str(by_symbol[s].close),'volume':str(by_symbol[s].volume),
        'amount':str(by_symbol[s].amount),'price_basis':'UNADJUSTED_RAW','availability_mode':availability_mode,
        'available_at':available_at} for s in sorted(observed))
    body={'schema_version':'DailyBarIncrementV1','session':session,'available_at':available_at,
          'availability_mode':availability_mode,'facts':facts,'coverage_id':coverage_id}
    digest=content_hash(body)
    return DailyBarIncrementV1(digest,session,available_at,body['availability_mode'],facts,coverage,digest)


def publish_daily_bar_increment(*, output_root: Path, previous_approval: Mapping[str,object],
    previous_manifest: Mapping[str,object], raws: Sequence[RawPayloadArtifactV1],
    receipt_hashes: tuple[str,...], research_safe_symbols: tuple[str,...], session: date,
    next_approved_session: date, observed_at: datetime,
    prior_completed_sessions: tuple[date,...] = ()) -> DailyBarPublicationV1:
    if not _valid(previous_approval,('approval_id','content_hash'),'SourceApprovalArtifactV1'): raise DailyBarPublicationError('approval integrity invalid')
    if not _valid(previous_manifest,('dataset_id','manifest_hash'),'DatasetManifestV1'): raise DailyBarPublicationError('manifest integrity invalid')
    if previous_manifest.get('approval_id')!=previous_approval.get('approval_id'): raise DailyBarPublicationError('lineage mismatch')
    increment=build_daily_bar_increment(session=session,next_approved_session=next_approved_session,
        research_safe_symbols=research_safe_symbols,raws=raws,observed_at=observed_at)
    payloads=tuple(sorted(x.payload_hash for x in raws)); evidence=tuple(sorted((*previous_approval.get('evidence_ids',()),increment.coverage.coverage_id,increment.fact_bundle_id)))
    approval_body={'schema_version':'SourceApprovalArtifactV1','source_name':previous_approval['source_name'],'dataset_kind':'daily_bar',
        'decision':'APPROVED_WITH_RULES','coverage_start':previous_approval['coverage_start'],'coverage_end':session,
        'verified_at':observed_at,'source_version_identity':content_hash((previous_approval['source_version_identity'],payloads)),
        'policy_version':previous_approval['policy_version'],'rule_set':{**previous_approval['rule_set'],
            'incremental_coverage_id':increment.coverage.coverage_id,'next_visibility_boundary':increment.available_at},
        'evidence_ids':evidence,'evidence_bundle_hash':content_hash(evidence),'evaluator_version':'phase-1c-daily-bar-increment-v1',
        'evidence_validity_policy_version':previous_approval['evidence_validity_policy_version'],
        'equivalence_evidence_id':previous_approval['equivalence_evidence_id'],'supersedes_approval_id':previous_approval['approval_id']}
    approval_id=content_hash(approval_body); approval={'approval_id':approval_id,'content_hash':approval_id,**{k:v for k,v in approval_body.items() if k!='schema_version'}}
    manifest_body={k:v for k,v in previous_manifest.items() if k not in {'dataset_id','manifest_hash'}}
    manifest_body.update({'created_at':observed_at,'approval_id':approval_id,'approval_content_hash':approval_id,
        'approval_resolution_as_of':observed_at,'coverage_end':session,'latest_approved_session':session,
        'row_count':int(previous_manifest['row_count'])+len(increment.facts),'symbol_count':len(research_safe_symbols),
        'raw_payload_hashes':tuple((*previous_manifest['raw_payload_hashes'],*payloads)),
        'normalized_content_hashes':tuple((*previous_manifest['normalized_content_hashes'],increment.fact_bundle_id,increment.coverage.coverage_id)),
        'fact_content_hashes':tuple((*previous_manifest['fact_content_hashes'],increment.fact_bundle_id)),
        'receipt_hashes':tuple((*previous_manifest['receipt_hashes'],*receipt_hashes)),
        'quality_findings':tuple((*previous_manifest['quality_findings'],f'incremental_excluded={len(increment.coverage.excluded_symbols)}'))})
    manifest_id=content_hash({'schema_version':'DatasetManifestV1',**manifest_body}); manifest={'dataset_id':manifest_id,'manifest_hash':manifest_id,**manifest_body}
    gov=output_root/'governance'
    _write(gov/f'daily-bar-facts-{increment.fact_bundle_id}.json',{'fact_bundle_id':increment.fact_bundle_id,
        'schema_version':'DailyBarIncrementV1','session':session,'available_at':increment.available_at,
        'availability_mode':increment.availability_mode,'facts':increment.facts,'coverage_id':increment.coverage.coverage_id})
    _write(gov/f'daily-bar-coverage-{increment.coverage.coverage_id}.json',asdict(increment.coverage))
    _write(gov/f'daily_bar-approval-{approval_id}.json',approval); _write(gov/f'daily_bar-manifest-{manifest_id}.json',manifest)
    ready=observed_at.astimezone(SHANGHAI)>=increment.available_at
    state=DatasetStateV1('daily_bar',approval_id,manifest_id,session,tuple(sorted(set((*prior_completed_sessions,session)))),f'visibility:{increment.available_at.isoformat()}',
        DatasetReadiness.READY if ready else DatasetReadiness.NOT_READY,reason_codes=() if ready else ('AVAILABILITY_NOT_REACHED',),affected_security_ids=increment.coverage.excluded_symbols,
        availability_modes=(increment.availability_mode,))
    state_body={'schema_version':'Phase1CDatasetStateV1',**asdict(state)}; state_id=content_hash(state_body)
    _write(gov/f'daily_bar-state-{state_id}.json',{'state_id':state_id,**state_body})
    pointer=output_root/'daily_bar-current-state-id.txt'; tmp=pointer.with_suffix('.tmp'); tmp.write_text(state_id,encoding='ascii'); os.replace(tmp,pointer)
    return DailyBarPublicationV1(state,increment,approval_id,manifest_id)
