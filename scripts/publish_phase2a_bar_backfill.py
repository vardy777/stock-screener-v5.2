from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.daily_bar_lineage import DailyBarSourceBindingV1, HistoricalExitDailyBarAvailabilityEvidenceV2  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.real_audits.phase2a_bar_backfill import load_validated_backfill, publishable_backfill_facts  # noqa: E402
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1  # noqa: E402


NOW = datetime(2026, 9, 16, 22, 30, tzinfo=timezone(timedelta(hours=8)))
OUT = ROOT / "data/phase_2a/bar_backfill"
CALENDAR_ID = "d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable targeted backfill publication collision") from None
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)


def identified(schema: str, identifier: str, body: dict) -> dict:
    digest = content_hash({"schema_version": schema, **body})
    extra = {"manifest_hash": digest} if identifier == "dataset_id" else {"content_hash": digest}
    return {identifier: digest, **extra, **body}


def approval_object(value: dict) -> SourceApprovalArtifactV1:
    coverage_start = value["coverage_start"] if isinstance(value["coverage_start"], date) else date.fromisoformat(value["coverage_start"])
    coverage_end = value["coverage_end"] if isinstance(value["coverage_end"], date) else date.fromisoformat(value["coverage_end"])
    verified_at = value["verified_at"] if isinstance(value["verified_at"], datetime) else datetime.fromisoformat(value["verified_at"])
    return SourceApprovalArtifactV1(
        approval_id=value["approval_id"], source_name=value["source_name"], dataset_kind=value["dataset_kind"],
        decision=ApprovalDecision(value["decision"]), coverage_start=coverage_start,
        coverage_end=coverage_end, verified_at=verified_at,
        source_version_identity=value["source_version_identity"], policy_version=value["policy_version"],
        rule_set=value["rule_set"], evidence_ids=tuple(value["evidence_ids"]), evidence_bundle_hash=value["evidence_bundle_hash"],
        evaluator_version=value["evaluator_version"], evidence_validity_policy_version=value["evidence_validity_policy_version"],
        equivalence_evidence_id=value["equivalence_evidence_id"], supersedes_approval_id=value["supersedes_approval_id"],
        content_hash=value["content_hash"],
    )


def main() -> int:
    validated = load_validated_backfill(ROOT)
    calendar = load(ROOT / "data/phase_1b_exit_remediation/governance" / f"historical-calendar-fact-bundle-{CALENDAR_ID}.json")
    opens = sorted({date(int(r["cal_date"][:4]), int(r["cal_date"][4:6]), int(r["cal_date"][6:]))
                    for r in calendar["ordered_rows"] if r["is_open"] == 1})
    next_session = {day: opens[index + 1] for index, day in enumerate(opens[:-1])}
    facts = publishable_backfill_facts(
        validated.rows, approved_sessions=set(opens), next_session_by_session=next_session,
        available_at=lambda _day, following: datetime.combine(following, time(16, 30), timezone(timedelta(hours=8))),
        availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
    )
    if len(facts) != 43:
        raise RuntimeError("validated backfill row count changed")
    membership = tuple(sorted((item.security_identity, item.session.isoformat()) for item in facts))
    fact_body = {"inventory_id": validated.inventory_id, "acquisition_id": validated.acquisition_id,
                 "row_count": len(facts), "membership_digest": content_hash(membership),
                 "facts": tuple(item.as_dict() for item in facts)}
    fact_bundle = identified("Phase2ATargetedDailyBarFactBundleV1", "fact_bundle_id", fact_body)

    baseline_dir = ROOT / "data/phase_1c_lineage_remediation/governance"
    baseline_manifest = load(next(baseline_dir.glob("historical-baseline-manifest-*.json")))
    baseline_approval = load(next(baseline_dir.glob("historical-baseline-approval-*.json")))
    binding = DailyBarSourceBindingV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar", endpoint="daily",
        payload_hashes=validated.payload_hashes, source_semantic_contract_version="daily-bar-semantic-contract-v2",
        requested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        normalizer_version="daily-bar-normalization-v1", identity_policy_version="historical-effective-identity-v1",
        unit_policy_id=baseline_manifest["unit_policy_id"],
        availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
    )
    availability = HistoricalExitDailyBarAvailabilityEvidenceV2.create(
        binding=binding, coverage_start=min(item.session for item in facts), coverage_end=max(item.session for item in facts),
        availability_mode="HISTORICAL_RECONSTRUCTED", cutoff="NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
        approved_calendar_lineage_id=CALENDAR_ID,
        parent_evidence_ids=(validated.acquisition_id, fact_bundle["fact_bundle_id"], baseline_manifest["availability_evidence_id"]),
    )
    approval_body = {
        "source_name": "datahubco_tushare_proxy", "dataset_kind": "daily_bar", "decision": "APPROVED_WITH_RULES",
        "coverage_start": min(item.session for item in facts), "coverage_end": max(item.session for item in facts),
        "verified_at": NOW, "source_version_identity": binding.source_content_set_identity,
        "policy_version": "phase2a-targeted-daily-bar-backfill-v1",
        "rule_set": {"scope": "EXACT_FROZEN_MEMBERSHIP_ONLY", "membership_digest": fact_bundle["membership_digest"],
                     "source_semantic_identity": binding.source_semantic_identity,
                     "source_content_set_identity": binding.source_content_set_identity,
                     "availability_evidence_id": availability.evidence_id,
                     "unexplained_missing_sessions": validated.unexplained_missing_sessions},
        "evidence_ids": (availability.evidence_id, fact_bundle["fact_bundle_id"]),
        "evidence_bundle_hash": content_hash(tuple(sorted((availability.evidence_id, fact_bundle["fact_bundle_id"])))),
        "evaluator_version": "phase2a-targeted-daily-bar-backfill-evaluator-v1",
        "evidence_validity_policy_version": "phase2a-targeted-daily-bar-backfill-validity-v1",
        "equivalence_evidence_id": baseline_approval["equivalence_evidence_id"], "supersedes_approval_id": None,
    }
    approval = identified("SourceApprovalArtifactV1", "approval_id", approval_body)
    manifest = DatasetManifestV1.create(
        created_at=NOW, source_name="datahubco_tushare_proxy", dataset_kind="daily_bar",
        approval=approval_object(approval), approval_resolution_as_of=NOW,
        coverage_start=approval_object(approval).coverage_start, coverage_end=approval_object(approval).coverage_end,
        row_count=43, symbol_count=8, raw_payload_hashes=validated.payload_hashes,
        normalized_content_hashes=(fact_bundle["fact_bundle_id"],),
        fact_content_hashes=tuple(item.fact_id for item in facts), normalizer_version="daily-bar-normalization-v1",
        availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
        quality_findings=("exact frozen membership only", "14 unexplained required sessions remain fail-closed"),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=baseline_manifest["audit_policy_id"], endpoint_identities=("daily",),
        receipt_hashes=validated.receipt_hashes, approval_policy_id="phase2a-targeted-daily-bar-backfill-v1",
        upstream_approval_ids=tuple(baseline_manifest["upstream_approval_ids"]), request_inventory_id=validated.inventory_id,
        normalization_policy_id=baseline_manifest["normalization_policy_id"], unit_policy_id=baseline_manifest["unit_policy_id"],
        exception_policy_id=baseline_manifest["exception_policy_id"], exception_set_hash=baseline_manifest["exception_set_hash"],
        cross_source_evidence_id=baseline_manifest["cross_source_evidence_id"], availability_evidence_id=availability.evidence_id,
    )
    write(OUT / "approved" / f"daily-bar-facts-{fact_bundle['fact_bundle_id']}.json", fact_bundle)
    write(OUT / "governance" / f"daily-bar-source-binding-{binding.binding_id}.json", asdict(binding))
    write(OUT / "governance" / f"daily-bar-availability-{availability.evidence_id}.json", asdict(availability))
    write(OUT / "governance" / f"daily_bar-approval-{approval['approval_id']}.json", approval)
    write(OUT / "governance" / f"daily_bar-manifest-{manifest.dataset_id}.json", asdict(manifest))
    print(json.dumps({"provider_requests": 0, "validated": 43, "approved_facts": 43,
                      "unexplained_missing": len(validated.unexplained_missing_sessions),
                      "fact_bundle_id": fact_bundle["fact_bundle_id"], "approval_id": approval["approval_id"],
                      "manifest_id": manifest.dataset_id}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
