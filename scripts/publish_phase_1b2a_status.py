from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.dataset_equivalence import DatasetEquivalenceDecision, DatasetEquivalenceEvidenceV1  # noqa: E402
from v5_2.data.evidence import EvidenceArtifactV1, EvidenceStatus, EvidenceType, EvidenceValidityPolicy, EvidenceValidityRuleV1  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.security_status_facts import DailySecurityStatusFactV1  # noqa: E402
from v5_2.data.source_approval import SourceApprovalArtifactV1  # noqa: E402
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402


RUNTIME = ROOT / "data" / "phase_1b2a"
GOVERNANCE = RUNTIME / "governance"
NOW = datetime(2026, 9, 7, 6, 30, tzinfo=timezone.utc)
AUDIT_ID = "23fb236fd6d1fdf7e0691c3bf3bfb8db3cf5524f13bcddb510bd21fbc52e03b7"
CLASSIFICATION_ID = "34612813c3bfdeb233bf41b66796a9ca9e89751062523ca7be30fc4c76f56420"
REPLAY_ID = "649f082492e47bf6a8fbfe8921276ed31b706a8a8276b84fbd7396a778cc62b7"
FINAL_LEDGER_ID = "7aee446328623da71f2f0ca8ad3655399b8f7d389e4a71ea9304b075d3838cb9"
INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
PIT_ID = "aabfbcd3e8d4d03ff400c52a12ff005638b259bf0185e802d96372b4015f3f8f"


def _latest(prefix):
    paths = sorted(GOVERNANCE.glob(f"{prefix}-*.json"), key=lambda path: path.stat().st_mtime)
    if not paths:
        raise RuntimeError(f"required {prefix} artifact is missing")
    return paths[-1], json.loads(paths[-1].read_text(encoding="utf-8"))


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def build_status_equivalence(*, classification, audit, replay, raw_hashes, gate, prospective):
    final_pass = bool(gate.get("pit_status") == "PASS"
                      and gate.get("cross_source_status") == "PASS"
                      and gate.get("publication_allowed") is True)
    observations = prospective["observations"]
    matches = sum(item["resolution"] == "MATCH" for item in observations)
    mismatches = sum(item["resolution"] == "MISMATCH" for item in observations)
    unresolved = len(observations) - matches - mismatches
    if final_pass and (len(observations) != 71 or matches != 71):
        raise RuntimeError("passed gate is inconsistent with final 71/71 ledger")
    inputs = tuple(sorted((audit["evidence_id"], classification["content_hash"], replay["evidence_id"],
                           prospective["content_hash"])))
    return DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        reference_contract="V5.2 Phase 1B-2A PIT daily security status v1",
        tested_endpoints=("namechange", "suspend-d"),
        tested_fields=("ts_code", "name", "start_date", "end_date", "ann_date", "change_reason",
                       "trade_date", "suspend_timing", "suspend_type"),
        coverage_tested={"start": "2010-01-04", "end": "2025-12-31", "rows": 473424},
        sample_rule={"inventory_id": INVENTORY_ID, "sample_count": 71},
        field_mapping={"suspend_type=S": "daily suspension observation", "ST name prefix": "risk warning"},
        semantic_findings=("structural audit PASS", "suspend-d S covers each suspended date"),
        missing_fields=("verified publication timestamp",), extra_fields=(),
        value_comparison_summary={"matched": matches, "mismatched": mismatches, "unresolved": unresolved},
        pit_findings=tuple(audit["pit_findings"]),
        revision_findings=("first-middle-last real replay stable",),
        pagination_findings=("32 terminal requests", "116 pages", "473424 rows"),
        cross_source_findings=tuple(audit["cross_source_findings"]),
        limitations=("plaintext provider transport",),
        decision=(DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES if final_pass
                  else DatasetEquivalenceDecision.INSUFFICIENT_EVIDENCE),
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
    gate = json.loads((GOVERNANCE / "status-gate-evaluation-v2.json").read_text(encoding="utf-8"))
    gate_body = {key: value for key, value in gate.items() if key != "content_hash"}
    if gate.get("content_hash") != content_hash(gate_body):
        raise RuntimeError("status gate artifact is tampered")
    required_gates = ("structural_status", "pit_status", "cross_source_status", "survivorship_status",
                      "exception_budget_status", "systematic_defect_status")
    if (any(gate.get(key) != "PASS" for key in required_gates)
            or gate.get("decision") != "APPROVED_WITH_RULES" or gate.get("publication_allowed") is not True):
        raise RuntimeError("publisher requires the frozen all-PASS gate artifact")
    prospective = load_pinned_json(GOVERNANCE / f"prospective-status-evidence-ledger-v2-{FINAL_LEDGER_ID}.json",
        schema_version="ProspectiveStatusEvidenceLedgerV2", identity_field="content_hash", expected_identity=FINAL_LEDGER_ID)
    inventory = load_pinned_json(GOVERNANCE / f"prospective-status-sample-inventory-v2-{INVENTORY_ID}.json",
        schema_version="ProspectiveStatusSampleInventoryV2", identity_field="inventory_id", expected_identity=INVENTORY_ID)
    pit = load_pinned_json(GOVERNANCE / f"status-pit-knowledge-time-{PIT_ID}.json",
        schema_version="StatusPITKnowledgeTimeEvidenceV1", identity_field="content_hash", expected_identity=PIT_ID)
    if not pit["complete"] or PIT_ID not in gate["input_artifact_ids"] or FINAL_LEDGER_ID not in gate["input_artifact_ids"]:
        raise RuntimeError("gate does not pin the complete PIT and final cross-source artifacts")
    raw_hashes = tuple(audit["raw_payload_hashes"])
    source_version = content_hash(raw_hashes)
    if pit["source_version_identity"] != source_version:
        raise RuntimeError("PIT source version does not match the audited source")
    inputs = tuple(sorted((audit["evidence_id"], classification["content_hash"], replay["evidence_id"],
                           PIT_ID, FINAL_LEDGER_ID)))
    equivalence = build_status_equivalence(classification=classification, audit=audit, replay=replay,
        raw_hashes=raw_hashes, gate=gate, prospective=prospective)
    evidence = []
    for kind in EvidenceType:
        evidence_inputs = (PIT_ID,) if kind is EvidenceType.PIT_TIME else (
            (FINAL_LEDGER_ID,) if kind is EvidenceType.CROSS_SOURCE else inputs)
        evidence.append(EvidenceArtifactV1.create(
            evidence_type=kind, status=EvidenceStatus.PASS, observed_at=NOW, verified_at=NOW,
            policy_version="phase-1b2a-status-final-v2", source_version_identity=source_version,
            input_artifact_ids=evidence_inputs, valid_until=None,
            findings=("frozen all-PASS status gate consumed by publisher",),
        ))
    validity = EvidenceValidityPolicy(
        policy_version="phase-1b2a-status-validity-v1",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, ("phase-1b2a-status-final-v2",)) for kind in EvidenceType),
    )
    approval = SourceApprovalArtifactV1.evaluate(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_security_status",
        coverage_start=date(2010, 1, 4), coverage_end=date(2025, 12, 31), verified_at=NOW,
        source_version_identity=source_version, policy_version="phase-1b2a-status-v1",
        evaluator_version="phase-1b2a-status-evaluator-v1", evidence=evidence,
        required_evidence_types=tuple(EvidenceType),
        rule_set={"pit_evidence_id": PIT_ID, "cross_source_evidence_id": FINAL_LEDGER_ID,
                  "date_only_same_close": "NEXT_APPROVED_SESSION", "transport_security": "PLAINTEXT_HTTP"},
        evidence_validity_policy=validity, resolution_as_of=NOW,
        equivalence_evidence=equivalence,
    )
    (GOVERNANCE / f"daily_security_status-equivalence-{equivalence.evidence_id}.json").write_bytes(canonical_json(_mapping(equivalence)))
    (GOVERNANCE / f"daily_security_status-approval-{approval.approval_id}.json").write_bytes(canonical_json(_mapping(approval)))

    sessions = set()
    for path in (ROOT / "data" / "phase_1b1" / "raw" / "datahubco_tushare_proxy" / "trade_calendar").rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        sessions.update(date.fromisoformat(str(row["cal_date"])) for row in payload["provider_payload"]["rows"]
                        if int(row["is_open"]) == 1)
    zone = timezone(timedelta(hours=8), "Asia/Shanghai")
    observations = {item["candidate_hash"]: item for item in prospective["observations"]}
    facts = []
    for sample in inventory["samples"]:
        session = date(int(sample["session"][:4]), int(sample["session"][4:6]), int(sample["session"][6:]))
        semantic = sample["semantic"]
        if semantic in {"DELISTING_BOUNDARY", "IDENTITY_TRANSITION"}:
            later = sorted(value for value in sessions if value > session)
            if not later:
                raise RuntimeError("next safe session is outside the approved calendar")
            available_at = datetime.combine(later[0], time(16, 30), zone)
        else:
            available_at = datetime.combine(session, time(16, 30), zone)
        observation = observations[sample["candidate_hash"]]
        source_ids = tuple(sample["provider_evidence_ids"]) + tuple(
            value for value in (observation.get("source_document_hash"),
                                observation.get("official_anchor_evidence_id")) if value)
        fact = DailySecurityStatusFactV1.create(
            security_identity=sample["security_identity"], session=session,
            is_listed=True, is_delisted=semantic == "DELISTING_BOUNDARY",
            is_risk_warning=semantic == "ST_ENTER", is_suspended=semantic == "FULL_DAY_SUSPENSION",
            effective_from=session, effective_to=session, available_at=available_at,
            source_fact_ids=source_ids, source_name="datahubco_tushare_proxy",
            policy_version="status-availability-after-close-v2", risk_warning_excluded=True)
        facts.append(fact)
    if not facts or any(not fact.verify() for fact in facts):
        raise RuntimeError("approved status facts are empty or invalid")
    fact_dir = RUNTIME / "facts" / "daily_security_status"
    fact_dir.mkdir(parents=True, exist_ok=True)
    for fact in facts:
        (fact_dir / f"{fact.fact_id}.json").write_bytes(canonical_json(_mapping(fact)))
    receipt_hashes = tuple(sorted(path.stem for path in (RUNTIME / "receipts").rglob("*.json"))) or (REPLAY_ID,)
    manifest = DatasetManifestV1.create(created_at=NOW, source_name="datahubco_tushare_proxy",
        dataset_kind="daily_security_status", approval=approval, approval_resolution_as_of=NOW,
        coverage_start=min(fact.session for fact in facts), coverage_end=max(fact.session for fact in facts),
        row_count=len(facts), symbol_count=len({fact.security_identity for fact in facts}),
        raw_payload_hashes=raw_hashes, normalized_content_hashes=tuple(sample["candidate_hash"] for sample in inventory["samples"]),
        fact_content_hashes=tuple(fact.content_hash for fact in facts), normalizer_version="status-sample-publisher-v2",
        availability_policy_version="status-availability-after-close-v2",
        quality_findings=("V2 cross-source 71/71 MATCH", "PIT semantics 8/8 complete"),
        pit_validation_status="PASS", rule_compliance_status="PASS", pagination_complete=True,
        audit_policy_id=PIT_ID, endpoint_identities=("namechange", "suspend-d", "daily-status"),
        receipt_hashes=receipt_hashes, approval_policy_id=PIT_ID,
        request_inventory_id=INVENTORY_ID, cross_source_evidence_id=FINAL_LEDGER_ID)
    (GOVERNANCE / f"daily_security_status-manifest-{manifest.dataset_id}.json").write_bytes(canonical_json(_mapping(manifest)))
    manifest_paths = (GOVERNANCE / f"daily_security_status-manifest-{manifest.dataset_id}.json",)
    fact_paths = tuple(fact_dir.rglob("*.json"))
    print(json.dumps({"decision": approval.decision.value, "approval_id": approval.approval_id,
                      "equivalence": equivalence.decision.value, "equivalence_id": equivalence.evidence_id,
                      "published_manifest_count": len(manifest_paths), "published_fact_count": len(fact_paths),
                      "audit_artifact": audit_path.name, "classification_artifact": classification_path.name,
                      "replay_artifact": replay_path.name}, indent=2))
    return 0 if approval.decision.value == "APPROVED_WITH_RULES" and manifest_paths and fact_paths else 1


if __name__ == "__main__":
    raise SystemExit(main())
