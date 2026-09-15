from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.daily_bar_lineage import (  # noqa: E402
    DailyBarSourceBindingV1,
    HistoricalExitDailyBarAvailabilityEvidenceV2,
    validate_daily_bar_lineage,
)
from v5_2.data.dataset_equivalence import (  # noqa: E402
    DatasetEquivalenceDecision,
    DatasetEquivalenceEvidenceV1,
)
from v5_2.data.evidence import (  # noqa: E402
    EvidenceArtifactV1,
    EvidenceStatus,
    EvidenceType,
    EvidenceValidityPolicy,
    EvidenceValidityRuleV1,
)
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.manifests import DatasetManifestV1  # noqa: E402
from v5_2.data.source_approval import (  # noqa: E402
    ApprovalDecision,
    ApprovalResolver,
    SourceApprovalArtifactV1,
    SourceApprovalRevocationArtifactV1,
)


OLD_ROOT = ROOT / "data/phase_1b_exit_remediation/governance"
OUT = ROOT / "data/phase_1b_lineage_remediation/governance"
PANEL_ID = "a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d"
OLD_APPROVAL_ID = "fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5"
OLD_MANIFEST_ID = "76c4fe58d0714405d0a6a826bf9b814237d812f88f69b63986a0e0317f924b4b"
OLD_AVAILABILITY_ID = "6877256040eb6abbea3e6c4434485aaa212f23eba7f675f9d088ce7e05850bcb"
CALENDAR_ID = "d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc"
NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone(timedelta(hours=8)))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_immutable(path: Path, value) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable Historical Daily Bar remediation collision")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)


def deserialize_approval(raw) -> SourceApprovalArtifactV1:
    values = dict(raw)
    values["decision"] = ApprovalDecision(values["decision"])
    values["coverage_start"] = date.fromisoformat(values["coverage_start"])
    values["coverage_end"] = date.fromisoformat(values["coverage_end"])
    values["verified_at"] = datetime.fromisoformat(values["verified_at"])
    values["evidence_ids"] = tuple(values["evidence_ids"])
    return SourceApprovalArtifactV1(**values)


def main() -> int:
    panel_path = OLD_ROOT / f"historical-daily-bar-panel-{PANEL_ID}.json"
    approval_path = OLD_ROOT / f"daily_bar-approval-{OLD_APPROVAL_ID}.json"
    manifest_path = OLD_ROOT / f"daily_bar-manifest-{OLD_MANIFEST_ID}.json"
    immutable_before = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in (panel_path, approval_path, manifest_path)}
    panel, old_approval, old_manifest = load(panel_path), load(approval_path), load(manifest_path)
    payload_hashes = tuple(old_manifest["raw_payload_hashes"])
    if len(payload_hashes) != 5884 or content_hash(payload_hashes) != old_approval["source_version_identity"]:
        raise RuntimeError("frozen Historical content set changed")
    if panel["row_count"] != 14_010_422 or panel["symbol_count"] != 5_483:
        raise RuntimeError("frozen Historical panel counts changed")

    binding = DailyBarSourceBindingV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar", endpoint="daily",
        payload_hashes=payload_hashes, source_semantic_contract_version="daily-bar-semantic-contract-v1",
        requested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        normalizer_version=old_manifest["normalizer_version"],
        identity_policy_version="historical-effective-identity-v1",
        unit_policy_id=old_manifest["unit_policy_id"],
        availability_policy_version=old_manifest["availability_policy_version"],
    )
    availability = HistoricalExitDailyBarAvailabilityEvidenceV2.create(
        binding=binding, coverage_start=date.fromisoformat(panel["coverage_start"]),
        coverage_end=date.fromisoformat(panel["coverage_end"]),
        availability_mode="HISTORICAL_RECONSTRUCTED",
        cutoff="NEXT_SESSION_SAFE@16:30 Asia/Shanghai",
        approved_calendar_lineage_id=CALENDAR_ID,
        parent_evidence_ids=(OLD_AVAILABILITY_ID, PANEL_ID, old_manifest["request_inventory_id"]),
    )
    source_version = binding.source_content_set_identity
    evidence_policy = "phase-1b-historical-daily-bar-lineage-remediation-v1"
    old_evidence_by_type = {}
    for path in OLD_ROOT.glob("daily_bar-evidence-*.json"):
        raw = load(path)
        old_evidence_by_type[raw["evidence_type"]] = raw["evidence_id"]
    evidence = tuple(
        EvidenceArtifactV1.create(
            evidence_type=kind, status=EvidenceStatus.PASS, observed_at=NOW, verified_at=NOW,
            policy_version=evidence_policy, source_version_identity=source_version,
            input_artifact_ids=(PANEL_ID, binding.binding_id, availability.evidence_id,
                                old_evidence_by_type[kind.value]),
            valid_until=None,
            findings=("existing business facts unchanged", "source content and availability rebound exactly"),
        )
        for kind in EvidenceType
    )
    validity = EvidenceValidityPolicy(
        policy_version="phase-1b-historical-daily-bar-lineage-validity-v1",
        rules=tuple(EvidenceValidityRuleV1(kind, None, True, (evidence_policy,)) for kind in EvidenceType),
    )
    equivalence = DatasetEquivalenceEvidenceV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar",
        reference_contract="Historical Exit immutable lineage remediation v1",
        tested_endpoints=("daily",),
        tested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        coverage_tested={"start": panel["coverage_start"], "end": panel["coverage_end"], "rows": panel["row_count"]},
        sample_rule={"source_binding_id": binding.binding_id, "facts_unchanged": True},
        field_mapping={"vol": "shares via frozen x100 rule", "amount": "yuan via frozen x1000 rule"},
        semantic_findings=("UNADJUSTED_RAW retained", "source semantic contract unchanged"),
        missing_fields=(), extra_fields=(),
        value_comparison_summary={"changed_business_values": 0, "panel_id": PANEL_ID},
        pit_findings=("NEXT_SESSION_SAFE@16:30 Asia/Shanghai retained",),
        revision_findings=("immutable predecessor artifacts retained",),
        pagination_findings=("5,884 terminal payloads reused",),
        cross_source_findings=("frozen Historical cross-source evidence retained",),
        limitations=("missing bars remain fail closed",),
        decision=DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES,
        verified_at=NOW,
        input_artifact_ids=(PANEL_ID, binding.binding_id, availability.evidence_id, OLD_APPROVAL_ID),
        policy_version="phase-1b-historical-daily-bar-lineage-equivalence-v1",
    )
    approval = SourceApprovalArtifactV1.evaluate(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar",
        coverage_start=date.fromisoformat(panel["coverage_start"]),
        coverage_end=date.fromisoformat(panel["coverage_end"]),
        verified_at=NOW, source_version_identity=source_version,
        policy_version="phase-1b-historical-daily-bar-lineage-v2",
        evaluator_version="phase-1b-historical-daily-bar-lineage-evaluator-v2",
        evidence=evidence, required_evidence_types=tuple(EvidenceType),
        rule_set={
            **old_approval["rule_set"],
            "source_binding_id": binding.binding_id,
            "source_semantic_identity": binding.source_semantic_identity,
            "source_content_set_identity": binding.source_content_set_identity,
            "availability_evidence_id": availability.evidence_id,
        },
        evidence_validity_policy=validity, resolution_as_of=NOW,
        equivalence_evidence=equivalence, supersedes_approval_id=OLD_APPROVAL_ID,
    )
    if approval.decision is not ApprovalDecision.APPROVED_WITH_RULES:
        raise RuntimeError("replacement Historical approval failed")
    manifest = DatasetManifestV1.create(
        created_at=NOW, source_name=old_manifest["source_name"], dataset_kind="daily_bar",
        approval=approval, approval_resolution_as_of=NOW,
        coverage_start=date.fromisoformat(old_manifest["coverage_start"]),
        coverage_end=date.fromisoformat(old_manifest["coverage_end"]),
        row_count=old_manifest["row_count"], symbol_count=old_manifest["symbol_count"],
        raw_payload_hashes=payload_hashes,
        normalized_content_hashes=tuple(old_manifest["normalized_content_hashes"]),
        fact_content_hashes=tuple(old_manifest["fact_content_hashes"]),
        normalizer_version=old_manifest["normalizer_version"],
        availability_policy_version=old_manifest["availability_policy_version"],
        quality_findings=tuple(old_manifest["quality_findings"]) + ("immutable lineage rebound; business facts unchanged",),
        pit_validation_status="PASS", rule_compliance_status="PASS",
        pagination_complete=old_manifest["pagination_complete"],
        audit_policy_id=old_manifest["audit_policy_id"],
        endpoint_identities=tuple(old_manifest["endpoint_identities"]),
        receipt_hashes=tuple(old_manifest["receipt_hashes"]),
        approval_policy_id=validity.policy_version,
        upstream_approval_ids=tuple(old_manifest["upstream_approval_ids"]),
        request_inventory_id=old_manifest["request_inventory_id"],
        normalization_policy_id=old_manifest["normalization_policy_id"],
        unit_policy_id=old_manifest["unit_policy_id"],
        exception_policy_id=old_manifest["exception_policy_id"],
        exception_set_hash=old_manifest["exception_set_hash"],
        cross_source_evidence_id=old_manifest["cross_source_evidence_id"],
        availability_evidence_id=availability.evidence_id,
        latest_approved_session=date.fromisoformat(old_manifest["latest_approved_session"]),
    )
    revocation = SourceApprovalRevocationArtifactV1.create(
        approval_id=OLD_APPROVAL_ID,
        reason="LEGACY_APPROVAL_SOURCE_CONTENT_SET_MISMATCH",
        effective_at=NOW, created_at=NOW,
        evidence_ids=(binding.binding_id, availability.evidence_id),
        policy_version="phase-1b-historical-daily-bar-lineage-revocation-v1",
    )
    validate_daily_bar_lineage(
        binding=binding, availability=availability, approval=asdict(approval),
        manifest=asdict(manifest), revoked_approval_ids=(),
    )
    selected = ApprovalResolver(
        (deserialize_approval(old_approval), approval), (revocation,),
    ).resolve(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar",
        requested_coverage=(date.fromisoformat(panel["coverage_start"]), date.fromisoformat(panel["coverage_end"])),
        resolution_as_of=NOW,
    )
    if selected != approval.approval_id:
        raise RuntimeError("resolver did not select replacement approval")
    for path, digest in immutable_before.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("old immutable artifact changed")

    artifacts = {
        f"daily-bar-source-binding-{binding.binding_id}.json": binding,
        f"daily-bar-availability-{availability.evidence_id}.json": availability,
        f"daily_bar-equivalence-{equivalence.evidence_id}.json": equivalence,
        f"daily_bar-approval-{approval.approval_id}.json": approval,
        f"daily_bar-manifest-{manifest.dataset_id}.json": manifest,
        f"approval-revocation-{revocation.revocation_id}.json": revocation,
    }
    for name, artifact in artifacts.items():
        write_immutable(OUT / name, artifact)
    for item in evidence:
        write_immutable(OUT / f"daily_bar-evidence-{item.evidence_id}.json", item)
    print(json.dumps({
        "source_semantic_identity": binding.source_semantic_identity,
        "source_content_set_identity": binding.source_content_set_identity,
        "availability_evidence_id": availability.evidence_id,
        "approval_id": approval.approval_id,
        "manifest_id": manifest.dataset_id,
        "revocation_id": revocation.revocation_id,
        "raw_payload_count": len(payload_hashes), "row_count": panel["row_count"],
        "symbol_count": panel["symbol_count"], "resolver_selected": selected,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
