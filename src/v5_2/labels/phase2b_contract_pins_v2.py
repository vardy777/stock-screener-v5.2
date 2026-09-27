"""Exact frozen authorities consumed by the Phase 2B contract gate."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.private_corpus_manifest import read_manifest_exact
from v5_2.labels.acceptance_v2_1_final import Phase2AAcceptanceV2_1
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1


_ID = re.compile(r"^[0-9a-f]{64}$")
PHASE2A_ACCEPTANCE_ID = "75df8940cfa5f31757fc9b105be172e60581ead32ff0494fb4c84a2baac43cf7"
MATURATION_REMEDIATION_ID = "28b090531ece57fd41548e31eaa819cb02f7669f3fd8802a84d75b0a6f654fc9"
PRIVATE_CORPUS_MANIFEST_ID = "0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6"
PRIVATE_CAS_INVENTORY_HASH = "a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536"
DATASET_CONTRACT_SHA256 = "4fca4efd4e8df489cbc19971789de5bf3ac08d70cbccae0f3e51ef1a1dccd034"
PRODUCER_SHA256 = "85ca7d571324c32737ee3d16e693d1c36adacbcf7dadc2647129e3d4c941dbc9"
ENGINE_SHA256 = "f90400e9f5d7572df6891e9429ce13f97c1551ae31b4586a42184a887db3cb43"
SOURCE_APPROVAL_IDS = (
    "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601",
    "c515bd582600fed01a64c062901ede713dafadb931e5fa7de15f053d52c4bfc1",
    "834d20964081575ec758abc3f28584b35ff414ac347a04e028d86ecf9752a656",
    "9353de33e62405830a7dbef13e53836a969fb569f9e7d5370a67d5df9078fa95",
    "5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974",
)
SOURCE_AUTHORITY_IDS = (
    "d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc",
    "33f28a549e94be8317dce5216414eb7b4c3c403fda4e2a160fc7d26e431831c5",
    "12ea218b47389979561423a2289791bfe504040b4bbe6d667af26967dad55933",
    "d6f7f5517428891db66da60565baaea5828d7adcaf29c820d5fa746ddf29e59b",
    "3e4a5604e555c036effe66fa5297cffcf374aa34dbd9a8b14eab873c165b6410",
)


@dataclass(frozen=True, slots=True)
class Phase2BContractPinEvidenceV2:
    phase2a_acceptance_id: str
    maturation_remediation_id: str
    dataset_contract_sha256: str
    producer_sha256: str
    producer_version: str
    private_corpus_manifest_id: str
    private_cas_inventory_hash: str
    source_approval_ids: tuple[str, ...]
    source_authority_ids: tuple[str, ...]
    evidence_id: str

    def verify(self) -> bool:
        body = {key: getattr(self, key) for key in self.__dataclass_fields__
                if key != "evidence_id"}
        return (
            self.phase2a_acceptance_id == PHASE2A_ACCEPTANCE_ID
            and self.maturation_remediation_id == MATURATION_REMEDIATION_ID
            and self.dataset_contract_sha256 == DATASET_CONTRACT_SHA256
            and self.producer_sha256 == PRODUCER_SHA256
            and self.producer_version == "historical-five-domain-producer-v1"
            and self.private_corpus_manifest_id == PRIVATE_CORPUS_MANIFEST_ID
            and self.private_cas_inventory_hash == PRIVATE_CAS_INVENTORY_HASH
            and self.source_approval_ids == SOURCE_APPROVAL_IDS
            and self.source_authority_ids == SOURCE_AUTHORITY_IDS
            and self.evidence_id == content_hash({
                "schema_version": type(self).__name__, **body})
        )


def _source_text_sha256(path: Path) -> str:
    return sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def derive_contract_pin_evidence_exact(root: Path) -> Phase2BContractPinEvidenceV2:
    acceptance_path = root / "data/phase_2a/v2_1_final_acceptance" / (
        f"final-phase2a-acceptance-v2-1-{PHASE2A_ACCEPTANCE_ID}.json")
    raw = acceptance_path.read_bytes()
    values = json.loads(raw)
    values["infrastructure_artifact_ids"] = tuple(values["infrastructure_artifact_ids"])
    values["gate_results"] = tuple(tuple(item) for item in values["gate_results"])
    acceptance = Phase2AAcceptanceV2_1(**values)
    if (not acceptance.verify() or acceptance.acceptance_id != PHASE2A_ACCEPTANCE_ID
            or canonical_json(acceptance) != raw):
        raise ValueError("frozen Phase 2A acceptance identity mismatch")
    remediation_path = root / "data/phase_2a/governance" / (
        f"phase2a-maturation-remediation-{MATURATION_REMEDIATION_ID}.json")
    remediation = json.loads(remediation_path.read_bytes())
    remediation_body = {key: value for key, value in remediation.items()
                        if key not in ("artifact_id", "content_hash")}
    if (remediation.get("schema_version") != "Phase2AMaturationRemediationArtifactV1"
            or remediation.get("artifact_id") != MATURATION_REMEDIATION_ID
            or remediation.get("content_hash") != MATURATION_REMEDIATION_ID
            or content_hash(remediation_body) != MATURATION_REMEDIATION_ID
            or remediation["frozen_semantic_authority"]["final_phase2a_acceptance_id"]
               != PHASE2A_ACCEPTANCE_ID
            or remediation["new_implementation"]["engine_sha256"] != ENGINE_SHA256
            or _source_text_sha256(root / "src/v5_2/labels/engine.py") != ENGINE_SHA256):
        raise ValueError("frozen Phase 2A maturation remediation mismatch")
    manifest_path = root / "governance/phase2b" / (
        f"private-corpus-manifest-{PRIVATE_CORPUS_MANIFEST_ID}.json")
    private_manifest = read_manifest_exact(manifest_path, PRIVATE_CORPUS_MANIFEST_ID)
    if (private_manifest.object_count != 44
            or private_manifest.inventory_hash != PRIVATE_CAS_INVENTORY_HASH):
        raise ValueError("private corpus inventory mismatch")
    producer = HistoricalFiveDomainProducerV1.load_exact(root)
    body = {
        "phase2a_acceptance_id": acceptance.acceptance_id,
        "maturation_remediation_id": remediation["artifact_id"],
        "dataset_contract_sha256": _source_text_sha256(
            root / "src/v5_2/labels/dataset_contracts.py"),
        "producer_sha256": _source_text_sha256(
            root / "src/v5_2/labels/historical_five_domain_producer.py"),
        "producer_version": producer.version,
        "private_corpus_manifest_id": private_manifest.manifest_id,
        "private_cas_inventory_hash": private_manifest.inventory_hash,
        "source_approval_ids": (
            producer.calendar.approval_id,
            producer.master.approval["approval_id"],
            producer.bars.reader.derived_approval_id,
            producer.status_pins.approval_id,
            producer.actions.approval_id,
        ),
        "source_authority_ids": (
            producer.calendar.bundle_id,
            producer.master.authority["authority_id"],
            producer.bars.reader.authority.authority_id,
            producer.status_pins.authority_id,
            producer.actions.bundle_id,
        ),
    }
    evidence = Phase2BContractPinEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "Phase2BContractPinEvidenceV2", **body}))
    if not evidence.verify():
        raise ValueError("frozen contract pin evidence differs from authority")
    return evidence


def write_contract_pin_evidence(root: Path,
                                evidence: Phase2BContractPinEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified contract pin evidence required")
    path = root / "gate_evidence" / f"contract-pins-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable contract pin evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_contract_pin_evidence_exact(path: Path, expected_id: str
                                     ) -> Phase2BContractPinEvidenceV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"contract-pins-{expected_id}.json"):
        raise ValueError("contract pin evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        values["source_approval_ids"] = tuple(values["source_approval_ids"])
        values["source_authority_ids"] = tuple(values["source_authority_ids"])
        evidence = Phase2BContractPinEvidenceV2(**values)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("contract pin evidence unavailable or malformed") from error
    if (evidence.evidence_id != expected_id or not evidence.verify()
            or canonical_json(evidence) != raw):
        raise ValueError("contract pin evidence identity mismatch")
    return evidence
