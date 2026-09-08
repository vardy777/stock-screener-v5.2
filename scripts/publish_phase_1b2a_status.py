from __future__ import annotations

from dataclasses import fields, replace
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.dataset_equivalence import DatasetEquivalenceDecision, DatasetEquivalenceEvidenceV1  # noqa: E402
from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType, EvidenceValidityPolicy, EvidenceValidityRuleV1  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.source_approval import SourceApprovalArtifactV1  # noqa: E402
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402


RUNTIME = ROOT / "data" / "phase_1b2a"
GOVERNANCE = RUNTIME / "governance"
NOW = datetime(2026, 9, 7, 6, 30, tzinfo=timezone.utc)
AUDIT_ID = "23fb236fd6d1fdf7e0691c3bf3bfb8db3cf5524f13bcddb510bd21fbc52e03b7"
CLASSIFICATION_ID = "34612813c3bfdeb233bf41b66796a9ca9e89751062523ca7be30fc4c76f56420"
REPLAY_ID = "649f082492e47bf6a8fbfe8921276ed31b706a8a8276b84fbd7396a778cc62b7"
LEDGER_ID = "0f6772947b821a5819614c652d08544ac8bc14b789b796eb0f4338f71c79e473"


def _latest(prefix):
    paths = sorted(GOVERNANCE.glob(f"{prefix}-*.json"), key=lambda path: path.stat().st_mtime)
    if not paths:
        raise RuntimeError(f"required {prefix} artifact is missing")
    return paths[-1], json.loads(paths[-1].read_text(encoding="utf-8"))


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def build_status_equivalence(*, classification, audit, replay, raw_hashes):
    counts = dict(classification["counts"])
    unexplained = int(counts.get("UNEXPLAINED", 0))
    inputs = tuple(sorted((audit["evidence_id"], classification["content_hash"], replay["evidence_id"])))
    return DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        reference_contract="V5.2 Phase 1B-2A PIT daily security status v1",
        tested_endpoints=("namechange", "suspend-d"),
        tested_fields=("ts_code", "name", "start_date", "end_date", "ann_date", "change_reason",
                       "trade_date", "suspend_timing", "suspend_type"),
        coverage_tested={"start": "2010-01-04", "end": "2025-12-31", "rows": 473424},
        sample_rule={"inventory_id": audit["sample_inventory_id"], "sample_count": 61},
        field_mapping={"suspend_type=S": "daily suspension observation", "ST name prefix": "risk warning"},
        semantic_findings=("structural audit PASS", "suspend-d S covers each suspended date"),
        missing_fields=("verified publication timestamp",), extra_fields=(),
        value_comparison_summary={"matched": 0, "mismatched": 0, "unresolved": 61},
        pit_findings=tuple(audit["pit_findings"]),
        revision_findings=("first-middle-last real replay stable",),
        pagination_findings=("32 terminal requests", "116 pages", "473424 rows"),
        cross_source_findings=tuple(audit["cross_source_findings"]),
        limitations=("plaintext provider transport", "survivorship audit failed",
                     f"{unexplained} missing bars unexplained"),
        decision=DatasetEquivalenceDecision.INSUFFICIENT_EVIDENCE,
        verified_at=NOW, input_artifact_ids=inputs,
        policy_version="phase-1b2a-status-equivalence-v1",
    )


def main() -> int:
    audit_path = GOVERNANCE / f"status-audit-{AUDIT_ID}.json"
    classification_path = GOVERNANCE / f"missing-bar-classification-{CLASSIFICATION_ID}.json"
    replay_path = GOVERNANCE / f"status-replay-{REPLAY_ID}.json"
    audit = load_pinned_json(audit_path, schema_version="Phase1B2AStatusAuditV1",
                             identity_field="evidence_id", expected_identity=AUDIT_ID)
    classification = load_pinned_json(classification_path, schema_version="MissingBarClassificationArtifactV2",
                                      identity_field="content_hash", expected_identity=CLASSIFICATION_ID)
    replay = load_pinned_json(replay_path, schema_version="StatusRealReplayEvidenceV1",
                              identity_field="evidence_id", expected_identity=REPLAY_ID)
    raw_hashes = tuple(audit["raw_payload_hashes"])
    source_version = content_hash(raw_hashes)
    inputs = tuple(sorted((audit["evidence_id"], classification["content_hash"], replay["evidence_id"])))
    equivalence = build_status_equivalence(
        classification=classification, audit=audit, replay=replay, raw_hashes=raw_hashes
    )
    gate = json.loads((GOVERNANCE / "status-gate-evaluation-v2.json").read_text(encoding="utf-8"))
    if gate["cross_source_status"] == "FAIL":
        prospective_path = GOVERNANCE / f"prospective-status-evidence-ledger-v2-{LEDGER_ID}.json"
        prospective = load_pinned_json(prospective_path, schema_version="ProspectiveStatusEvidenceLedgerV2",
            identity_field="content_hash", expected_identity=LEDGER_ID)
        equivalence = replace(equivalence, decision=DatasetEquivalenceDecision.NOT_EQUIVALENT)
        equivalence = replace(equivalence, evidence_id=content_hash({
            **{field.name: getattr(equivalence, field.name) for field in fields(equivalence)
               if field.name not in {"evidence_id", "content_hash"}},
            "schema_version": "DatasetEquivalenceEvidenceV1",
        }))
        equivalence = replace(equivalence, content_hash=equivalence.evidence_id)
    evidence = []
    statuses = {
        EvidenceType.COVERAGE: EvidenceStatus.PASS,
        EvidenceType.REVISION: EvidenceStatus.PASS,
        EvidenceType.CONTENT_IDENTITY: EvidenceStatus.PASS,
        EvidenceType.LICENSE_USAGE: EvidenceStatus.PASS,
    }
    for kind, status in statuses.items():
        evidence.append(EvidenceArtifactV1.create(
            evidence_type=kind, status=status, observed_at=NOW, verified_at=NOW,
            policy_version="phase-1b2a-status-evidence-v1", source_version_identity=source_version,
            input_artifact_ids=inputs, valid_until=None,
            findings=(f"status_audit={audit['result'].get(kind.value.split('_')[0] + '_status', status.value)}",),
        ))
    if gate["cross_source_status"] == "FAIL":
        evidence.append(EvidenceArtifactV1.create(
            evidence_type=EvidenceType.CROSS_SOURCE, status=EvidenceStatus.FAIL,
            observed_at=NOW, verified_at=NOW, policy_version="phase-1b2a-prospective-cross-source-v1",
            source_version_identity=source_version,
            input_artifact_ids=(prospective["content_hash"],), valid_until=None,
            findings=("prospective contract contains confirmed semantic mismatches",),
        ))
    validity = EvidenceValidityPolicy(
        policy_version="phase-1b2a-status-validity-v1",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, ("phase-1b2a-status-evidence-v1",)) for kind in EvidenceType),
    )
    approval = SourceApprovalArtifactV1.evaluate(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        coverage_start=date(2010, 1, 4), coverage_end=date(2025, 12, 31), verified_at=NOW,
        source_version_identity=source_version, policy_version="phase-1b2a-status-v1",
        evaluator_version="phase-1b2a-status-evaluator-v1", evidence=evidence,
        required_evidence_types=tuple(EvidenceType),
        rule_set={"date_only_same_close": "UNAVAILABLE", "transport_security": "PLAINTEXT_HTTP"},
        evidence_validity_policy=validity, resolution_as_of=NOW,
        equivalence_evidence=equivalence,
    )
    (GOVERNANCE / f"daily_security_status-equivalence-{equivalence.evidence_id}.json").write_bytes(canonical_json(_mapping(equivalence)))
    (GOVERNANCE / f"daily_security_status-approval-{approval.approval_id}.json").write_bytes(canonical_json(_mapping(approval)))
    manifest_paths = tuple(GOVERNANCE.glob("daily_security_status-manifest-*.json"))
    fact_paths = tuple((RUNTIME / "facts" / "daily_security_status").rglob("*.json")) if (RUNTIME / "facts" / "daily_security_status").exists() else ()
    print(json.dumps({"decision": approval.decision.value, "approval_id": approval.approval_id,
                      "equivalence": equivalence.decision.value, "equivalence_id": equivalence.evidence_id,
                      "published_manifest_count": len(manifest_paths), "published_fact_count": len(fact_paths),
                      "audit_artifact": audit_path.name, "classification_artifact": classification_path.name,
                      "replay_artifact": replay_path.name}, indent=2))
    return 0 if approval.decision.value in {"PENDING", "REJECTED"} and not manifest_paths and not fact_paths else 1


if __name__ == "__main__":
    raise SystemExit(main())
