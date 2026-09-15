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
SEMANTIC_CONTRACT = "daily-bar-semantic-contract-v2"
OLD_APPROVAL = "f057dc89adaa60e94b4b0763fc2a7902b8b33f845d9ca4c7f06deb78a7379274"
OLD_MANIFEST = "2fa12e2cfdcb35db45266c86631822b015111e33c10c4aa484889c30d1365ddf"
BASELINE_MANIFEST = "118744559f5869bcbe75b402870524a18ec6f42e813764568bec6c7f070bf5ad"
BASELINE_APPROVAL = "31d91fd99630e3b63b585ae598e7728fe1922454c3dbee276d0ffe9e7b24d79f"
BASELINE_AVAILABILITY = "c52bcc200d4201dae909ee00a95b6a314b8648502cdb9b9ccadd3a6ab8522082"
BASELINE_BINDING = "cd5d2cce173f38a896167399740f0f0f1b550bdf5e37b5bdaaa10a689861b771"
OLD_COMPOSITE = "72eab2642f7143c27536107fed41ea537cd8984ac54d9090486708e182f5d80a"
OLD_COMPONENT_APPROVALS = {
    "HISTORICAL_BASELINE": BASELINE_APPROVAL,
    "HISTORICAL_CATCH_UP": "4026913c2f107864849219ecf3d63f6a47d7b31d61b5d030dfecacb58ddd9164",
    "CONTEMPORANEOUS_OBSERVED": "c0d8955966d66c9727f37213d8933b7bb9e46fffbc6538581e055c5a1d449e0e",
}
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


def binding_for(payloads: tuple[str, ...], availability_policy_version: str) -> dict:
    value = DailyBarSourceBindingV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="daily_bar", endpoint="daily",
        payload_hashes=payloads, source_semantic_contract_version=SEMANTIC_CONTRACT,
        requested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
        normalizer_version="daily-bar-normalization-v1+availability-overlay-v1",
        identity_policy_version="historical-effective-identity-v1",
        unit_policy_id="e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093",
        availability_policy_version=availability_policy_version,
    )
    return asdict(value)


def replace_baseline(old_manifest: dict, old_approval: dict, old_availability: dict,
                     old_binding: dict):
    policy = "daily-bar-availability-v1:NEXT_SESSION_SAFE"
    binding = binding_for(tuple(old_binding["payload_hashes"]), policy)
    evidence_body = {key: value for key, value in old_availability.items()
                     if key not in {"evidence_id", "content_hash", "schema_version"}}
    evidence_body.update({
        "source_binding_id": binding["binding_id"],
        "source_semantic_identity": binding["source_semantic_identity"],
        "source_content_set_identity": binding["source_content_set_identity"],
    })
    evidence = identified(
        "HistoricalExitDailyBarAvailabilityEvidenceV2", "evidence_id", evidence_body)
    approval_body = {key: value for key, value in old_approval.items()
                     if key not in {"approval_id", "content_hash"}}
    rules = dict(approval_body["rule_set"])
    rules.update({
        "source_binding_id": binding["binding_id"],
        "source_semantic_identity": binding["source_semantic_identity"],
        "source_content_set_identity": binding["source_content_set_identity"],
        "availability_evidence_id": evidence["evidence_id"],
    })
    approval_body.update({
        "verified_at": NOW,
        "source_version_identity": binding["source_content_set_identity"],
        "rule_set": rules,
        "evidence_ids": (evidence["evidence_id"],),
        "evidence_bundle_hash": content_hash((evidence["evidence_id"],)),
        "supersedes_approval_id": BASELINE_APPROVAL,
    })
    approval = identified("SourceApprovalArtifactV1", "approval_id", approval_body)
    manifest_body = {key: value for key, value in old_manifest.items()
                     if key not in {"dataset_id", "manifest_hash"}}
    manifest_body.update({
        "created_at": NOW,
        "approval_id": approval["approval_id"],
        "approval_content_hash": approval["approval_id"],
        "approval_resolution_as_of": NOW,
        "availability_evidence_id": evidence["evidence_id"],
        "quality_findings": tuple(old_manifest["quality_findings"])
                            + ("source semantic contract v2 rebound; facts unchanged",),
    })
    manifest = identified("DatasetManifestV1", "dataset_id", manifest_body)
    component = Phase1CDailyBarComponentV1.create(
        role="HISTORICAL_BASELINE", provenance_mode="HISTORICAL_RECONSTRUCTED",
        availability_mode="NEXT_SESSION_SAFE", manifest=manifest, approval=approval,
        availability=evidence, binding=binding, revoked_artifact_ids=(),
    )
    return binding, evidence, approval, manifest, component


def component_artifacts(role: str, fact: dict, old_manifest: dict, old_approval: dict):
    mode = "NEXT_SESSION_SAFE" if role == "HISTORICAL_CATCH_UP" else "CONTEMPORANEOUS_OBSERVED"
    provenance = "HISTORICAL_RECONSTRUCTED" if role == "HISTORICAL_CATCH_UP" else role
    session = fact["session"]
    policy = f"daily-bar-availability-v1:{mode}"
    binding = binding_for(PAYLOADS[role], policy)
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
                     "source_semantic_identity": binding["source_semantic_identity"],
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
        "availability_policy_version": policy, "availability_evidence_id": evidence["evidence_id"],
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
    old_paths = list(source.glob("daily_bar-*.json")) + list(target.glob("*.json"))
    old_bytes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in old_paths}
    old_manifest = load(source / f"daily_bar-manifest-{OLD_MANIFEST}.json")
    old_approval = load(source / f"daily_bar-approval-{OLD_APPROVAL}.json")
    baseline_manifest = load(historical / f"daily_bar-manifest-{BASELINE_MANIFEST}.json")
    baseline_approval = load(historical / f"daily_bar-approval-{BASELINE_APPROVAL}.json")
    baseline_availability = load(historical / f"daily-bar-availability-{BASELINE_AVAILABILITY}.json")
    baseline_binding = load(historical / f"daily-bar-source-binding-{BASELINE_BINDING}.json")
    baseline_values = replace_baseline(
        baseline_manifest, baseline_approval, baseline_availability, baseline_binding)
    baseline = baseline_values[4]
    built = {}
    for role in ("HISTORICAL_CATCH_UP", "CONTEMPORANEOUS_OBSERVED"):
        fact = load(source / f"daily-bar-facts-{FACTS[role]}.json")
        built[role] = component_artifacts(role, fact, old_manifest, old_approval)
    composite = Phase1CDailyBarCompositeManifestV1.create(
        historical_baseline=baseline, historical_catch_up=built["HISTORICAL_CATCH_UP"][4],
        contemporaneous_observed=built["CONTEMPORANEOUS_OBSERVED"][4],
        expected_membership_digest=content_hash(tuple(sorted(old_manifest["fact_content_hashes"]))))
    if composite.aggregate_row_count != 14_020_830:
        raise RuntimeError("aggregate row count mismatch")
    semantic_identities = {
        baseline.source_semantic_identity,
        built["HISTORICAL_CATCH_UP"][4].source_semantic_identity,
        built["CONTEMPORANEOUS_OBSERVED"][4].source_semantic_identity,
    }
    if len(semantic_identities) != 1:
        raise RuntimeError("component source semantic identity mismatch")
    for name, value in (
        (f"historical-baseline-binding-{baseline_values[0]['binding_id']}.json", baseline_values[0]),
        (f"historical-baseline-availability-{baseline_values[1]['evidence_id']}.json", baseline_values[1]),
        (f"historical-baseline-approval-{baseline_values[2]['approval_id']}.json", baseline_values[2]),
        (f"historical-baseline-manifest-{baseline_values[3]['dataset_id']}.json", baseline_values[3]),
    ):
        write(target / name, value)
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
    replacement_revocations = []
    for role, approval_id in OLD_COMPONENT_APPROVALS.items():
        replacement = SourceApprovalRevocationArtifactV1.create(
            approval_id=approval_id,
            reason="SOURCE_SEMANTIC_CONTRACT_V2_REBIND",
            effective_at=NOW, created_at=NOW,
            evidence_ids=(composite.composite_manifest_id,),
            policy_version="phase-1c-lineage-remediation-v2",
        )
        write(target / f"approval-revocation-{replacement.revocation_id}.json", asdict(replacement))
        replacement_revocations.append(replacement.revocation_id)
    replacement_body = {
        "replaces_composite_manifest_id": OLD_COMPOSITE,
        "replacement_composite_manifest_id": composite.composite_manifest_id,
        "old_component_approval_ids": tuple(OLD_COMPONENT_APPROVALS.values()),
        "replacement_component_approval_ids": (
            baseline_values[2]["approval_id"],
            built["HISTORICAL_CATCH_UP"][2]["approval_id"],
            built["CONTEMPORANEOUS_OBSERVED"][2]["approval_id"],
        ),
        "revocation_ids": tuple(replacement_revocations),
        "semantic_contract_version": SEMANTIC_CONTRACT,
        "reason": "SOURCE_SEMANTIC_CONTRACT_V2_REBIND",
        "created_at": NOW,
    }
    replacement = identified(
        "Phase1CDailyBarCompositeReplacementV1", "replacement_id", replacement_body)
    write(target / f"phase1c-daily-bar-replacement-{replacement['replacement_id']}.json", replacement)
    pointer = args.output_root / "daily_bar-current-composite-id.txt"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(composite.composite_manifest_id, encoding="ascii")
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != digest for path, digest in old_bytes.items()):
        raise RuntimeError("old Phase 1C artifact changed")
    print(json.dumps({"composite_manifest_id": composite.composite_manifest_id,
                      "revocation_id": revocation.revocation_id,
                      "supersession_id": supersession["supersession_id"],
                      "replacement_id": replacement["replacement_id"],
                      "replacement_revocation_ids": replacement_revocations,
                      "semantic_contract_version": SEMANTIC_CONTRACT,
                      "source_semantic_identity": next(iter(semantic_identities)),
                      "expected_membership_digest": composite.expected_membership_digest,
                      "composite_membership_digest": composite.aggregate_membership_digest,
                      "catchup": built["HISTORICAL_CATCH_UP"][4].as_dict(),
                      "contemporaneous": built["CONTEMPORANEOUS_OBSERVED"][4].as_dict(),
                      "old_artifacts_byte_identical": True, "provider_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
