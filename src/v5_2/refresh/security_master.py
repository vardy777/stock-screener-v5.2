from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.data.real_audits.security_master_normalization import SecurityMasterNormalizationPolicyV1
from v5_2.refresh.adapters import AvailabilityMode, DatasetStateV1
from v5_2.refresh.contracts import DatasetReadiness
from v5_2.refresh.eligibility import ResearchEligibilityV1, UniverseCoverageV1, evaluate_ipo_eligibility


class SecurityMasterPublicationError(RuntimeError):
    pass


def _valid(value: Mapping[str, object], ids: tuple[str, str], schema: str) -> bool:
    body = {key: item for key, item in value.items() if key not in ids}
    return value.get(ids[0]) == value.get(ids[1]) == content_hash({"schema_version": schema, **body})


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value); path.parent.mkdir(parents=True, exist_ok=True)
    try: descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded: raise SecurityMasterPublicationError("immutable master artifact collision") from None
    else:
        with os.fdopen(descriptor, "wb") as stream: stream.write(encoded)


@dataclass(frozen=True, slots=True)
class SecurityMasterPublicationV1:
    state: DatasetStateV1
    coverage: UniverseCoverageV1
    effective_universe_id: str
    eligible_universe_id: str
    identity_fact_id: str


def publish_security_master_increment(*, output_root: Path,
    previous_approval: Mapping[str, object], previous_manifest: Mapping[str, object],
    raws: Sequence[RawPayloadArtifactV1], receipt_hashes: tuple[str, ...],
    prior_effective_symbols: frozenset[str], target_session: date,
    approved_open_sessions: tuple[date, ...], observed_at: datetime,
    revoked_approval_ids: frozenset[str] = frozenset()) -> SecurityMasterPublicationV1:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None: raise SecurityMasterPublicationError("observation time must be aware")
    if not _valid(previous_approval, ("approval_id", "content_hash"), "SourceApprovalArtifactV1"): raise SecurityMasterPublicationError("approval integrity invalid")
    if not _valid(previous_manifest, ("dataset_id", "manifest_hash"), "DatasetManifestV1"): raise SecurityMasterPublicationError("manifest integrity invalid")
    if previous_approval["approval_id"] in revoked_approval_ids: raise SecurityMasterPublicationError("approval revoked")
    if previous_manifest.get("approval_id") != previous_approval.get("approval_id"): raise SecurityMasterPublicationError("lineage mismatch")
    if not raws or not receipt_hashes: raise SecurityMasterPublicationError("raw and receipt lineage required")
    rows = [dict(row) for raw in raws for row in raw.provider_payload.get("rows", ())]
    by_code = {}
    for row in rows:
        code = row.get("ts_code")
        if not isinstance(code, str) or code in by_code: raise SecurityMasterPublicationError("duplicate or missing identity")
        by_code[code] = row
    policy = SecurityMasterNormalizationPolicyV1.create_default()
    normalized = {}
    isolated = []
    for code, row in by_code.items():
        disposition = policy.disposition(row)
        if disposition == "NORMALIZED_ELIGIBLE": normalized[code] = dict(policy.normalize(row))
        elif disposition == "REJECTED_UNRESOLVED": isolated.append(code)
    effective = frozenset(code for code, row in normalized.items()
        if str(row.get("listing_date") or "") <= target_session.strftime("%Y%m%d")
        and (not row.get("delisting_date") or str(row["delisting_date"]) >= target_session.strftime("%Y%m%d")))
    removed = prior_effective_symbols - effective
    unexplained_removed = [code for code in removed if not normalized.get(code, {}).get("delisting_date")]
    if unexplained_removed or len(isolated) > max(100, len(rows) // 20):
        raise SecurityMasterPublicationError("systemic identity defect")
    eligibility = []
    for code in sorted(effective):
        listing = date.fromisoformat(str(normalized[code]["listing_date"])[:4] + "-" + str(normalized[code]["listing_date"])[4:6] + "-" + str(normalized[code]["listing_date"])[6:8])
        if code in prior_effective_symbols:
            eligibility.append(ResearchEligibilityV1(code, listing, True, True, None, None, 5))
        else:
            eligibility.append(evaluate_ipo_eligibility(symbol=code, list_date=listing,
                as_of_session=target_session, approved_open_sessions=approved_open_sessions,
                official_identity_verified=False, bar_coverage_valid=False, status_resolved=False))
    for code in isolated:
        row = by_code[code]; raw_date = str(row.get("list_date") or "19000101")
        listing = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
        eligibility.append(ResearchEligibilityV1(code, listing, True, False, "IDENTITY_UNVERIFIED", None, 0))
    coverage = UniverseCoverageV1.create(eligibility, systematic_defect=False)
    identity_rows = tuple(normalized[code] for code in sorted(effective - prior_effective_symbols))
    fact_body = {"schema_version": "SecurityMasterIncrementFactV1", "target_session": target_session,
                 "identity_rows": identity_rows, "removed_symbols": tuple(sorted(removed))}
    fact_id = content_hash(fact_body)
    effective_body = {"schema_version": "EffectiveSecurityUniverseV1", "target_session": target_session,
                      "symbols": tuple(sorted(effective)), "identity_fact_id": fact_id}
    effective_id = content_hash(effective_body)
    eligible_symbols = tuple(sorted(item.symbol for item in eligibility if item.research_eligible))
    eligible_body = {"schema_version": "ResearchEligibleUniverseV1", "target_session": target_session,
                     "effective_universe_id": effective_id, "symbols": eligible_symbols,
                     "coverage_id": coverage.coverage_id}
    eligible_id = content_hash(eligible_body)
    validation_body = {"schema_version": "SecurityMasterIncrementValidationV1", "target_session": target_session,
        "fact_id": fact_id, "effective_universe_id": effective_id, "eligible_universe_id": eligible_id,
        "coverage_id": coverage.coverage_id, "systematic_defect": False, "decision": "PASS"}
    validation_id = content_hash(validation_body)
    payloads = tuple(sorted(raw.payload_hash for raw in raws))
    evidence = tuple(sorted((*previous_approval.get("evidence_ids", ()), validation_id, coverage.coverage_id)))
    approval_body = {"schema_version": "SourceApprovalArtifactV1", "source_name": previous_approval["source_name"],
        "dataset_kind": "security_master", "decision": "APPROVED_WITH_RULES",
        "coverage_start": previous_approval["coverage_start"], "coverage_end": target_session,
        "verified_at": observed_at, "source_version_identity": content_hash((previous_approval["source_version_identity"], payloads)),
        "policy_version": previous_approval["policy_version"],
        "rule_set": {**previous_approval["rule_set"], "ipo_seasoning_sessions": 5,
                     "universe_coverage_id": coverage.coverage_id},
        "evidence_ids": evidence, "evidence_bundle_hash": content_hash(evidence),
        "evaluator_version": "phase-1c-security-master-increment-v1",
        "evidence_validity_policy_version": previous_approval["evidence_validity_policy_version"],
        "equivalence_evidence_id": previous_approval["equivalence_evidence_id"],
        "supersedes_approval_id": previous_approval["approval_id"]}
    approval_id = content_hash(approval_body)
    approval = {"approval_id": approval_id, "content_hash": approval_id, **{k:v for k,v in approval_body.items() if k != "schema_version"}}
    manifest_body = {k:v for k,v in previous_manifest.items() if k not in {"dataset_id", "manifest_hash"}}
    manifest_body.update({"created_at": observed_at, "approval_id": approval_id, "approval_content_hash": approval_id,
        "approval_resolution_as_of": observed_at, "coverage_end": target_session,
        "row_count": len(eligible_symbols), "symbol_count": len(eligible_symbols),
        "raw_payload_hashes": tuple((*previous_manifest["raw_payload_hashes"], *payloads)),
        "normalized_content_hashes": tuple((*previous_manifest["normalized_content_hashes"], fact_id, effective_id, eligible_id, coverage.coverage_id)),
        "fact_content_hashes": tuple((*previous_manifest["fact_content_hashes"], fact_id, effective_id, eligible_id)),
        "receipt_hashes": tuple((*previous_manifest["receipt_hashes"], *receipt_hashes)),
        "input_count": len(rows), "eligible_count": len(eligible_symbols),
        "excluded_non_target_count": len(rows)-len(effective)-len(isolated),
        "quarantined_count": len(effective)-len(eligible_symbols)+len(isolated),
        "quarantined_identity_hashes": tuple(content_hash(code) for code in sorted(set(coverage.excluded_symbols))),
        "latest_approved_session": target_session})
    manifest_id = content_hash({"schema_version": "DatasetManifestV1", **manifest_body})
    manifest = {"dataset_id": manifest_id, "manifest_hash": manifest_id, **manifest_body}
    gov = output_root / "governance"
    for name, ident, body in (("security-master-facts",fact_id,fact_body),("effective-universe",effective_id,effective_body),
        ("eligible-universe",eligible_id,eligible_body),("universe-coverage",coverage.coverage_id,{"schema_version":"UniverseCoverageV1",**{k:v for k,v in asdict(coverage).items() if k not in {"coverage_id","content_hash"}}}),
        ("security-master-validation",validation_id,validation_body)):
        _write(gov/f"{name}-{ident}.json", {name.replace("-", "_")+"_id":ident, **body})
    _write(gov/f"security_master-approval-{approval_id}.json", approval)
    _write(gov/f"security_master-manifest-{manifest_id}.json", manifest)
    state = DatasetStateV1("security_master", approval_id, manifest_id, target_session,
        tuple(day for day in approved_open_sessions if day <= target_session), target_session.isoformat(), DatasetReadiness.READY,
        affected_security_ids=coverage.excluded_symbols, availability_modes=(AvailabilityMode.CONTEMPORANEOUS_OBSERVED.value,))
    state_body={"schema_version":"Phase1CDatasetStateV1",**asdict(state)}
    state_id=content_hash(state_body)
    _write(gov/f"security_master-state-{state_id}.json",{"state_id":state_id,**state_body})
    pointer=output_root/'security_master-current-state-id.txt'; temporary=pointer.with_suffix('.tmp')
    temporary.write_text(state_id,encoding='ascii'); os.replace(temporary,pointer)
    return SecurityMasterPublicationV1(state, coverage, effective_id, eligible_id, fact_id)
