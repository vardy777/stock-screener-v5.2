from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from v5_2.data.daily_bar_lineage import DailyBarSourceBindingV1
from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.source_approval import SourceApprovalRevocationArtifactV1
from v5_2.refresh.daily_bar_composite import (
    Phase1CDailyBarComponentV1,
    Phase1CDailyBarCompositeManifestV1,
)


NOW = datetime.fromisoformat("2026-09-15T18:00:00+08:00")
OLD_APPROVAL = "f057dc89adaa60e94b4b0763fc2a7902b8b33f845d9ca4c7f06deb78a7379274"
OLD_MANIFEST = "2fa12e2cfdcb35db45266c86631822b015111e33c10c4aa484889c30d1365ddf"
BASELINE_MANIFEST = "118744559f5869bcbe75b402870524a18ec6f42e813764568bec6c7f070bf5ad"
BASELINE_APPROVAL = "31d91fd99630e3b63b585ae598e7728fe1922454c3dbee276d0ffe9e7b24d79f"
BASELINE_AVAILABILITY = "c52bcc200d4201dae909ee00a95b6a314b8648502cdb9b9ccadd3a6ab8522082"
BASELINE_BINDING = "cd5d2cce173f38a896167399740f0f0f1b550bdf5e37b5bdaaa10a689861b771"
SEMANTIC_IDENTITY = "4f3875e94fe5ff8bf1341dea8ee769b209c301b24204bbc8af65a476e106b1b9"
FACTS = {
    "HISTORICAL_CATCH_UP": "8c0b4dcbcb059ac07f70729177e64fa2985dd8b354e6695f9dd977492308b187",
    "CONTEMPORANEOUS_OBSERVED": "366dba32addcf23f8f18d35ffb714ed537c1aa010947e5210357f7636aee90da",
}
PAYLOADS = {
    "HISTORICAL_CATCH_UP": ("76d8ad2fc3b873d1a9ea352fb1a25698689b63df3e30a92c78c1e8bd884eabec", "b2c2971f6c64b70538112582cfc5fbb2481ab1123f1548c1ad4c48e00b04df65"),
    "CONTEMPORANEOUS_OBSERVED": ("44ae8b473bc11c797db7dd7432fdff58e6f01056bcf1b57c5e228b7f9bc1395a", "da3d269e3645ccfb2866485c207858d9d73e16d92b5ef7203574e216afd8a9e6"),
}
RECEIPTS = {
    "HISTORICAL_CATCH_UP": ("7405d89dd0225d9989b3dd279f29264ea3f2c91d8d57930d3c143deaeaf1d967", "7af77bc8136a6746b52fe19a884ea8d4c07858af970ee1706725677893b1c1ab"),
    "CONTEMPORANEOUS_OBSERVED": ("4eac35196c9842b885dd04e4312908de53320b4054e6c8f3e037540bddddd9fd", "b835bb970d4a0e277090e3604789f7d2a42f27c177de83568b93e557e84997cc"),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable remediation collision") from None
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)


def identified(schema: str, identifier: str, body: dict) -> dict:
    digest = content_hash({"schema_version": schema, **body})
    if identifier == "dataset_id":
        return {identifier: digest, "manifest_hash": digest, **body}
    return {identifier: digest, "content_hash": digest, **body}


def binding_for(payloads: tuple[str, ...]) -> dict:
    value = DailyBarSourceBindingV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar", endpoint="daily",
        payload_hashes=payloads, source_semantic_contract_version="daily-bar-semantic-contract-v1",
        requested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        normalizer_version="daily-bar-normalization-v1+availability-overlay-v1",
        identity_policy_version="historical-effective-identity-v1",
        unit_policy_id="e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093",
        availability_policy_version="daily-bar-availability-v1:NEXT_SESSION_SAFE",
    )
    if value.source_semantic_identity != SEMANTIC_IDENTITY:
        raise RuntimeError("semantic identity drift")
    return asdict(value)


def component_artifacts(role: str, fact: dict, old_manifest: dict, old_approval: dict):
    mode = "NEXT_SESSION_SAFE" if role == "HISTORICAL_CATCH_UP" else "CONTEMPORANEOUS_OBSERVED"
    provenance = "HISTORICAL_RECONSTRUCTED" if role == "HISTORICAL_CATCH_UP" else role
    session = fact["session"]
    binding = binding_for(PAYLOADS[role])
    available_values = tuple(sorted({item["available_at"] for item in fact["facts"]}))
    membership = tuple(sorted((item["session"], item["security_identity"]) for item in fact["facts"]))
    if len(membership) != 5204 or len(set(membership)) != 5204:
        raise RuntimeError("increment membership is not exact")
    evidence_body = {
        "role": role, "source_binding_id": binding["binding_id"],
        "source_semantic_identity": binding["source_semantic_identity"],
        "source_content_set_identity": binding["source_content_set_identity"],
        "provenance_mode": provenance, "availability_mode": mode,
        "coverage_start": session, "coverage_end": session,
        "fact_bundle_id": fact["fact_bundle_id"], "row_count": len(membership),
        "membership_digest": content_hash(membership), "available_at_values": available_values,
        "raw_payload_hashes": PAYLOADS[role], "receipt_hashes": RECEIPTS[role],
        "observed_at_digest": content_hash(available_values) if role == "CONTEMPORANEOUS_OBSERVED" else None,
    }
    evidence = identified("Phase1CDailyBarAvailabilityEvidenceV1", "evidence_id", evidence_body)
    approval_body = {key: value for key, value in old_approval.items() if key not in {"approval_id", "content_hash"}}
    approval_body.update({
        "coverage_start": session, "coverage_end": session, "verified_at": NOW,
        "source_version_identity": binding["source_content_set_identity"],
        "policy_version": "phase-1c-daily-bar-component-v1",
        "rule_set": {"role": role, "source_binding_id": binding["binding_id"],
                     "source_semantic_identity": SEMANTIC_IDENTITY,
                     "source_content_set_identity": binding["source_content_set_identity"],
                     "availability_evidence_id": evidence["evidence_id"], "availability_mode": mode},
        "evidence_ids": (evidence["evidence_id"],),
        "evidence_bundle_hash": content_hash((evidence["evidence_id"],)),
        "evaluator_version": "phase-1c-daily-bar-component-evaluator-v1",
        "evidence_validity_policy_version": "phase-1c-daily-bar-component-validity-v1",
        "supersedes_approval_id": None,
    })
    approval = identified("SourceApprovalArtifactV1", "approval_id", approval_body)
    manifest_body = {key: value for key, value in old_manifest.items() if key not in {"dataset_id", "manifest_hash"}}
    manifest_body.update({
        "created_at": NOW, "approval_id": approval["approval_id"],
        "approval_content_hash": approval["approval_id"], "approval_resolution_as_of": NOW,
        "coverage_start": session, "coverage_end": session, "row_count": 5204,
        "symbol_count": 5204, "raw_payload_hashes": PAYLOADS[role],
        "normalized_content_hashes": (fact["fact_bundle_id"],),
        "fact_content_hashes": (fact["fact_bundle_id"],), "receipt_hashes": RECEIPTS[role],
        "availability_policy_version": mode, "availability_evidence_id": evidence["evidence_id"],
        "latest_approved_session": session,
        "quality_findings": ("component_membership_exact=5204", "unclassified=0", "duplicate_membership=0"),
    })
    manifest = identified("DatasetManifestV1", "dataset_id", manifest_body)
    component = Phase1CDailyBarComponentV1.create(
        role=role, provenance_mode=provenance, availability_mode=mode,
        manifest=manifest, approval=approval, availability=evidence, binding=binding,
        revoked_artifact_ids=(),
    )
    return binding, evidence, approval, manifest, component


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase1c-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("data/phase_1c_lineage_remediation"))
    args = parser.parse_args()
    source = args.phase1c_root / "governance"
    target = args.output_root / "governance"
    historical = Path("data/phase_1b_lineage_remediation/governance")
    old_paths = list(source.glob("daily_bar-*.json"))
    old_bytes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in old_paths}
    old_manifest = load(source / f"daily_bar-manifest-{OLD_MANIFEST}.json")
    old_approval = load(source / f"daily_bar-approval-{OLD_APPROVAL}.json")
    baseline_manifest = load(historical / f"daily_bar-manifest-{BASELINE_MANIFEST}.json")
    baseline_approval = load(historical / f"daily_bar-approval-{BASELINE_APPROVAL}.json")
    baseline_availability = load(historical / f"daily-bar-availability-{BASELINE_AVAILABILITY}.json")
    baseline_binding = load(historical / f"daily-bar-source-binding-{BASELINE_BINDING}.json")
    baseline = Phase1CDailyBarComponentV1.create(
        role="HISTORICAL_BASELINE", provenance_mode="HISTORICAL_RECONSTRUCTED",
        availability_mode="NEXT_SESSION_SAFE", manifest=baseline_manifest,
        approval=baseline_approval, availability=baseline_availability,
        binding=baseline_binding, revoked_artifact_ids=(),
    )
    built = {}
    for role in ("HISTORICAL_CATCH_UP", "CONTEMPORANEOUS_OBSERVED"):
        fact = load(source / f"daily-bar-facts-{FACTS[role]}.json")
        built[role] = component_artifacts(role, fact, old_manifest, old_approval)
    composite = Phase1CDailyBarCompositeManifestV1.create(
        historical_baseline=baseline, historical_catch_up=built["HISTORICAL_CATCH_UP"][4],
        contemporaneous_observed=built["CONTEMPORANEOUS_OBSERVED"][4])
    if composite.aggregate_row_count != 14_020_830:
        raise RuntimeError("aggregate row count mismatch")
    for role, values in built.items():
        binding, evidence, approval, manifest, component = values
        slug = role.lower().replace("_", "-")
        for name, value in (
            (f"{slug}-binding-{binding['binding_id']}.json", binding),
            (f"{slug}-availability-{evidence['evidence_id']}.json", evidence),
            (f"{slug}-approval-{approval['approval_id']}.json", approval),
            (f"{slug}-manifest-{manifest['dataset_id']}.json", manifest),
            (f"{slug}-component-{component.component_hash}.json", {"schema_version": "Phase1CDailyBarComponentV1", **component.as_dict()}),
        ):
            write(target / name, value)
    write(target / f"historical-baseline-component-{baseline.component_hash}.json", {"schema_version": "Phase1CDailyBarComponentV1", **baseline.as_dict()})
    write(target / f"phase1c-daily-bar-composite-{composite.composite_manifest_id}.json", composite.as_dict())
    revocation = SourceApprovalRevocationArtifactV1.create(
        approval_id=OLD_APPROVAL, reason="MIXED_SOURCE_CONTENT_LINEAGE_REBIND",
        effective_at=NOW, created_at=NOW,
        evidence_ids=(composite.composite_manifest_id,), policy_version="phase-1c-lineage-remediation-v1")
    write(target / f"approval-revocation-{revocation.revocation_id}.json", asdict(revocation))
    supersession_body = {"old_approval_id": OLD_APPROVAL, "old_manifest_id": OLD_MANIFEST,
                         "replacement_composite_manifest_id": composite.composite_manifest_id,
                         "revocation_id": revocation.revocation_id,
                         "reason": "MIXED_SOURCE_CONTENT_LINEAGE_REBIND", "created_at": NOW}
    supersession = identified("Phase1CDailyBarGovernanceSupersessionV1", "supersession_id", supersession_body)
    write(target / f"phase1c-daily-bar-supersession-{supersession['supersession_id']}.json", supersession)
    pointer = args.output_root / "daily_bar-current-composite-id.txt"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(composite.composite_manifest_id, encoding="ascii")
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != digest for path, digest in old_bytes.items()):
        raise RuntimeError("old Phase 1C artifact changed")
    print(json.dumps({"composite_manifest_id": composite.composite_manifest_id,
                      "revocation_id": revocation.revocation_id,
                      "supersession_id": supersession["supersession_id"],
                      "catchup": built["HISTORICAL_CATCH_UP"][4].as_dict(),
                      "contemporaneous": built["CONTEMPORANEOUS_OBSERVED"][4].as_dict(),
                      "old_artifacts_byte_identical": True, "provider_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
