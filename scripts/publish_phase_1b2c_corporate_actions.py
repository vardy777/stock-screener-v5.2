from __future__ import annotations
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1  # noqa: E402

GOVERNANCE = ROOT / "data" / "phase_1b2c" / "governance"
STAGING = ROOT / "data" / "phase_1b2c" / "staging"
APPROVED = ROOT / "data" / "phase_1b2c" / "approved"
NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded: raise RuntimeError("immutable publication artifact collision")
    if not path.exists(): path.write_bytes(encoded)


def main() -> int:
    gate_id = (GOVERNANCE / "current-gate-id.txt").read_text(encoding="ascii").strip()
    gate = json.loads((GOVERNANCE / f"gate-{gate_id}.json").read_text(encoding="utf-8"))
    if content_hash({"schema_version": "CorporateActionGateArtifactV1", **gate}) != gate_id:
        raise RuntimeError("frozen gate integrity failed")
    if not gate.get("publication_allowed") or gate.get("source_approval") != "APPROVED_WITH_RULES":
        print("APPROVED_FACTS=0\nDATASET_MANIFEST=none"); return 0
    evidence_id = gate["evidence_id"]
    evidence = json.loads((GOVERNANCE / f"pit-evidence-{evidence_id}.json").read_text(encoding="utf-8"))
    if evidence.get("content_hash") != evidence_id or not evidence.get("complete"): raise RuntimeError("frozen PIT evidence integrity failed")
    materialization_id = (GOVERNANCE / "current-materialization-id.txt").read_text(encoding="ascii").strip()
    materialization = json.loads((GOVERNANCE / f"materialization-audit-{materialization_id}.json").read_text(encoding="utf-8"))
    candidate_id = materialization["candidate_bundle_id"]
    candidates = json.loads((STAGING / f"candidate-facts-{candidate_id}.json").read_text(encoding="utf-8"))
    if candidates.get("candidate_bundle_id") != candidate_id: raise RuntimeError("candidate bundle identity mismatch")

    evidence_ids = tuple(sorted(set(evidence["cross_source_evidence_ids"] + [evidence_id, gate_id])))
    rules = {"supported_action_types": ("BONUS_SHARE", "CASH_DIVIDEND"),
             "unsupported_action_types": ("RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT"),
             "unsupported_events": "FAIL_CLOSED_QUARANTINE",
             "publication_time": "DATE_ONLY_NEXT_APPROVED_SESSION_16_30_ASIA_SHANGHAI",
             "upstream_extension_audit_id": materialization["upstream_extension_audit_id"]}
    approval_body = {"schema_version": "SourceApprovalArtifactV1", "source_name": "datahubco_tushare_proxy",
        "dataset_kind": "corporate_action", "decision": ApprovalDecision.APPROVED_WITH_RULES,
        "coverage_start": date(2010, 1, 4), "coverage_end": date(2026, 9, 9), "verified_at": NOW,
        "source_version_identity": evidence["source_version_identity"], "policy_version": "corporate-action-scoped-v1",
        "rule_set": rules, "evidence_ids": evidence_ids, "evidence_bundle_hash": content_hash(evidence_ids),
        "evaluator_version": "phase-1b2c-gate-evaluator-v1", "evidence_validity_policy_version": "corporate-action-evidence-v1",
        "equivalence_evidence_id": evidence["cross_source_evidence_ids"][1], "supersedes_approval_id": None}
    approval_id = content_hash(approval_body)
    approval = SourceApprovalArtifactV1(approval_id=approval_id, content_hash=approval_id,
        **{key: value for key, value in approval_body.items() if key != "schema_version"})
    _write(GOVERNANCE / f"corporate_action-approval-{approval_id}.json", asdict(approval))

    facts = tuple(candidates["facts"]); fact_hashes = tuple(str(item["fact_id"]) for item in facts)
    fact_body = {"schema_version": "ApprovedCorporateActionFactBundleV1", "approval_id": approval_id, "gate_id": gate_id, "facts": facts}
    fact_bundle_id = content_hash(fact_body)
    _write(APPROVED / f"corporate-action-facts-{fact_bundle_id}.json", {"fact_bundle_id": fact_bundle_id, **fact_body})
    acquisition = json.loads((GOVERNANCE / "acquisition-summary-139298428aef7f08add358c49c01fb1a2796a78543abf5fa90c7b0825c285876.json").read_text(encoding="utf-8"))
    manifest = DatasetManifestV1.create(created_at=NOW, source_name="datahubco_tushare_proxy", dataset_kind="corporate_action",
        approval=approval, approval_resolution_as_of=NOW, coverage_start=date(2010, 1, 4), coverage_end=date(2026, 9, 9),
        row_count=len(facts), symbol_count=len({item["security_identity"] for item in facts}), raw_payload_hashes=tuple(acquisition["payload_hashes"]),
        normalized_content_hashes=(candidate_id,), fact_content_hashes=fact_hashes, normalizer_version="corporate-action-normalizer-v1",
        availability_policy_version="CorporateActionAvailabilityPolicyV1", quality_findings=("scoped_action_type_approval",),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True, audit_policy_id=gate_id,
        endpoint_identities=("dividend",), receipt_hashes=("139298428aef7f08add358c49c01fb1a2796a78543abf5fa90c7b0825c285876",),
        approval_policy_id="corporate-action-scoped-v1", upstream_approval_ids=(materialization["calendar_approval_id"], materialization["master_approval_id"]),
        availability_evidence_id=evidence_id, supported_action_types=("BONUS_SHARE", "CASH_DIVIDEND"),
        unsupported_action_types=("RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT"),
        validated_coverage_by_action_type=tuple((kind, date.fromisoformat(start), date.fromisoformat(end)) for kind, start, end in evidence["validated_coverage_by_action_type"]),
        materialized_coverage_by_action_type=tuple((kind, date.fromisoformat(start), date.fromisoformat(end)) for kind, start, end in evidence["materialized_coverage_by_action_type"]),
        coverage_gaps=(), unsupported_intervals=tuple((kind, date.fromisoformat(start), date.fromisoformat(end)) for kind, start, end in evidence["unsupported_intervals"]),
        latest_approved_session=date(2026, 9, 9), quarantined_count=materialization["quarantine_count"],
        quarantined_identity_hashes=tuple(item["quarantine_id"] for item in materialization["quarantines"]))
    _write(GOVERNANCE / f"corporate-action-manifest-{manifest.dataset_id}.json", asdict(manifest))
    print(f"APPROVAL_ID={approval_id}\nAPPROVED_FACTS={len(facts)}\nFACT_BUNDLE_ID={fact_bundle_id}\nDATASET_MANIFEST={manifest.dataset_id}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
