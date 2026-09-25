"""Portable representation of already-approved historical Security Master truth.

The first boundary corrects *types* in the old immutable bundle without
changing its bytes, membership, or the approved 300114/302132 graph.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Mapping, Any

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.raw_artifacts import RawArtifactStore, RawPayloadArtifactV1
from v5_2.data.real_audits.identity_lineage import IdentityIntervalV1
from v5_2.data.real_audits.security_master_normalization import (
    SecurityMasterNormalizationError,
    SecurityMasterNormalizationPolicyV1,
)


GRAPH_ID = "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0"
SUPPLEMENT_ID = "d67d886299be85bb5585c9103140ef327fe13b78161903f7e5120646a8ee9e8f"
GRAPH_APPROVAL_ID = "a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f"
_ID = re.compile(r"^[0-9a-f]{64}$")


class HistoricalMasterTypingError(ValueError):
    """A claimed source artifact cannot support this narrow type correction."""


def _verify_content(value: Mapping[str, Any], schema: str, id_field: str, *, stored_schema: bool) -> str:
    claimed = value.get(id_field)
    if not isinstance(claimed, str) or claimed != value.get("content_hash"):
        raise HistoricalMasterTypingError(f"{schema} identity is missing")
    body = {key: item for key, item in value.items() if key not in {id_field, "content_hash"}}
    if stored_schema:
        if body.get("schema_version") != schema:
            raise HistoricalMasterTypingError(f"{schema} has wrong type")
    else:
        if "schema_version" in body:
            raise HistoricalMasterTypingError(f"{schema} stored form changed")
        body = {"schema_version": schema, **body}
    if content_hash(body) != claimed:
        raise HistoricalMasterTypingError(f"{schema} content was changed")
    return claimed


def _verify_supplement(value: Mapping[str, Any]) -> str:
    try:
        rows = value["identities"]
        if len(rows) != 1 or rows[0]["security_identity"] != "600747.SH":
            raise HistoricalMasterTypingError("historical supplement identity scope changed")
        hashes = []
        for row in rows:
            body = {key: item for key, item in row.items() if key != "content_hash"}
            digest = content_hash({"schema_version": "HistoricalUniverseSupplementIdentityV1", **body})
            if row.get("content_hash") != digest:
                raise HistoricalMasterTypingError("supplement identity content changed")
            hashes.append(digest)
        digest = content_hash({"schema_version": "HistoricalUniverseSupplementV1",
                               "original_universe_id": value["original_universe_id"],
                               "identity_hashes": tuple(hashes)})
    except (KeyError, TypeError, IndexError) as exc:
        raise HistoricalMasterTypingError("historical supplement malformed") from exc
    if digest != SUPPLEMENT_ID or value.get("content_hash") != digest or set(value) != {"original_universe_id", "identities", "content_hash"}:
        raise HistoricalMasterTypingError("historical supplement content or type changed")
    return digest


@dataclass(frozen=True, slots=True)
class HistoricalMasterTypingBridgeV1:
    old_bundle_id: str
    effective_identity_graph_ids: tuple[str, ...]
    historical_universe_supplement_ids: tuple[str, ...]
    graph_approval_id: str
    defect: str
    business_truth_changed: bool
    identity_semantics_changed: bool
    universe_membership_changed: bool
    policy_version: str
    composition_id: str
    content_hash: str


def type_historical_master_bundle(
    old_bundle: Mapping[str, Any], graph: Mapping[str, Any],
    ratification: Mapping[str, Any], graph_approval: Mapping[str, Any],
    supplement: Mapping[str, Any],
) -> HistoricalMasterTypingBridgeV1:
    old_id = _verify_content(old_bundle, "HistoricalSecurityMasterFactBundleV1", "fact_bundle_id", stored_schema=True)
    graph_id = _verify_content(graph, "EffectiveDatedSecurityIdentityV1", "graph_id", stored_schema=False)
    ratification_id = _verify_content(ratification, "SecurityIdentityGraphRatificationEvidenceV1", "evidence_id", stored_schema=False)
    approval_id = _verify_content(graph_approval, "SecurityIdentityGraphApprovalV1", "approval_id", stored_schema=False)
    supplement_id = _verify_supplement(supplement)
    if (graph_id != GRAPH_ID or approval_id != GRAPH_APPROVAL_ID
            or tuple(old_bundle.get("effective_identity_graph_ids", ())) != (GRAPH_ID, SUPPLEMENT_ID)
            or graph.get("provider_identity") != "302132.SZ"
            or graph.get("transition_event") != "SECURITY_CODE_CHANGE"
            or graph.get("transition_effective_at") != "2025-02-17"
            or ratification.get("decision") != "PASS"
            or ratification.get("graph_id") != graph_id
            or ratification.get("graph_body_hash") != graph_id
            or graph_approval.get("decision") != "APPROVED"
            or graph_approval.get("scope") != "EXISTING_GRAPH_RATIFICATION"
            or graph_approval.get("graph_id") != graph_id
            or graph_approval.get("ratification_evidence_id") != ratification_id
            or tuple(graph_approval.get("official_evidence_ids", ()))
                != tuple(ratification.get("official_evidence_ids", ()))):
        raise HistoricalMasterTypingError("typed provenance does not match approved frozen authority")
    body = {
        "schema_version": "HistoricalMasterTypingBridgeV1", "old_bundle_id": old_id,
        "effective_identity_graph_ids": (graph_id,),
        "historical_universe_supplement_ids": (supplement_id,),
        "graph_approval_id": approval_id,
        "defect": "PROVENANCE_TYPE_MISCLASSIFICATION",
        "business_truth_changed": False, "identity_semantics_changed": False,
        "universe_membership_changed": False,
        "policy_version": "historical-master-typing-bridge-v1",
    }
    digest = content_hash(body)
    return HistoricalMasterTypingBridgeV1(
        **{key: item for key, item in body.items() if key != "schema_version"},
        composition_id=digest, content_hash=digest,
    )


@dataclass(frozen=True, slots=True)
class HistoricalMasterIntervalFactV1:
    provider_identity: str
    intervals: tuple[IdentityIntervalV1, ...]
    source_payload_hashes: tuple[str, ...]
    normalization_policy_id: str
    graph_id: str | None
    fact_id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class HistoricalMasterScopedQuarantineV1:
    security_identity: str
    reason: str
    source_payload_hashes: tuple[str, ...]
    affected_from: str | None
    affected_to: str | None
    quarantine_id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class DerivedMasterRowsV1:
    membership: tuple[str, ...]
    membership_count: int
    facts: tuple[HistoricalMasterIntervalFactV1, ...]
    quarantines: tuple[HistoricalMasterScopedQuarantineV1, ...]
    resolved_count: int
    quarantine_count: int
    membership_set_hash: str


def _provider_date(value: object, *, nullable: bool = False) -> date | None:
    if nullable and value in (None, ""):
        return None
    text = str(value)
    if len(text) != 8 or not text.isdigit():
        raise ValueError("invalid Master source date")
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def _fact(identity: str, intervals: tuple[IdentityIntervalV1, ...], payload_hashes: tuple[str, ...],
          policy_id: str, graph_id: str | None) -> HistoricalMasterIntervalFactV1:
    body = {"schema_version": "HistoricalMasterIntervalFactV1", "provider_identity": identity,
            "intervals": intervals, "source_payload_hashes": payload_hashes,
            "normalization_policy_id": policy_id, "graph_id": graph_id}
    digest = content_hash(body)
    return HistoricalMasterIntervalFactV1(identity, intervals, payload_hashes, policy_id, graph_id,
                                          digest, digest)


def _quarantine(identity: str, reason: str, hashes: tuple[str, ...],
                rows: list[Mapping[str, Any]]) -> HistoricalMasterScopedQuarantineV1:
    starts = sorted(str(row.get("list_date")) for row in rows if row.get("list_date"))
    ends = sorted(str(row.get("delist_date")) for row in rows if row.get("delist_date"))
    body = {"schema_version": "HistoricalMasterScopedQuarantineV1", "security_identity": identity,
            "reason": reason, "source_payload_hashes": hashes,
            "affected_from": starts[0] if starts else None,
            "affected_to": ends[-1] if ends else None}
    digest = content_hash(body)
    return HistoricalMasterScopedQuarantineV1(identity, reason, hashes,
                                               body["affected_from"], body["affected_to"], digest, digest)


def derive_master_intervals(
    *, membership: tuple[str, ...], pages: tuple[RawPayloadArtifactV1, ...],
    expected_payload_hashes: tuple[str, ...], graph: Mapping[str, Any],
    graph_approval_id: str,
) -> DerivedMasterRowsV1:
    """Derive lifecycle facts from exact approved fields; quarantine per-ID ambiguity."""
    if (not membership or membership != tuple(sorted(set(membership)))
            or not pages or tuple(sorted(page.payload_hash for page in pages)) != expected_payload_hashes
            or len(set(expected_payload_hashes)) != len(expected_payload_hashes)):
        raise HistoricalMasterTypingError("payload inventory or membership is not exact")
    for page in pages:
        if (RawPayloadArtifactV1.create(request_id=page.request_id, page_identity=page.page_identity,
                provider_payload=page.provider_payload, semantic_metadata=page.semantic_metadata) != page
                or page.semantic_metadata.get("response_code") != 0
                or not isinstance(page.provider_payload, Mapping)
                or not isinstance(page.provider_payload.get("rows"), (tuple, list))):
            raise HistoricalMasterTypingError("raw payload integrity or response semantics failed")
    graph_id = _verify_content(graph, "EffectiveDatedSecurityIdentityV1", "graph_id", stored_schema=False)
    if graph_id != GRAPH_ID or graph_approval_id != GRAPH_APPROVAL_ID or graph.get("provider_identity") != "302132.SZ":
        raise HistoricalMasterTypingError("approved exact graph is required")
    rows_by_identity: dict[str, list[Mapping[str, Any]]] = {}
    hashes_by_identity: dict[str, set[str]] = {}
    for page in pages:
        for row in page.provider_payload["rows"]:
            if not isinstance(row, Mapping) or not isinstance(row.get("ts_code"), str):
                raise HistoricalMasterTypingError("raw Master source row is malformed")
            identity = row["ts_code"]
            rows_by_identity.setdefault(identity, []).append(row)
            hashes_by_identity.setdefault(identity, set()).add(page.payload_hash)
    if not set(membership).issubset(rows_by_identity):
        raise HistoricalMasterTypingError("parent Master membership lacks raw source rows")
    policy = SecurityMasterNormalizationPolicyV1.create_default()
    facts: list[HistoricalMasterIntervalFactV1] = []
    quarantines: list[HistoricalMasterScopedQuarantineV1] = []
    fields = ("ts_code", "symbol", "exchange", "market", "list_status", "list_date", "delist_date")
    for identity in membership:
        candidates = rows_by_identity[identity]
        hashes = tuple(sorted(hashes_by_identity[identity]))
        if len({tuple(row.get(key) for key in fields) for row in candidates}) != 1:
            quarantines.append(_quarantine(identity, "CONFLICTING_MASTER_LIFECYCLE", hashes, candidates))
            continue
        row = candidates[0]
        try:
            if identity == "302132.SZ":
                if (row.get("symbol") != "302132" or row.get("exchange") != "SZSE"
                        or row.get("market") != "创业板" or row.get("list_date") != "20100827"
                        or row.get("delist_date") not in (None, "")):
                    raise ValueError("approved graph conflicts with Master row")
                intervals = tuple(IdentityIntervalV1(
                    identity=str(item["identity"]), effective_from=date.fromisoformat(str(item["effective_from"])),
                    effective_to=date.fromisoformat(str(item["effective_to"])) if item["effective_to"] else None,
                    security_type=str(item["security_type"]), board=str(item["board"]),
                ) for item in graph["intervals"])
                graph_ref = graph_id
            else:
                normalized = policy.normalize(row)
                start = _provider_date(normalized["listing_date"])
                end = _provider_date(normalized["delisting_date"], nullable=True)
                if end is not None and end < start:
                    raise ValueError("Master lifecycle is reversed")
                intervals = (IdentityIntervalV1(identity=identity, effective_from=start,
                    effective_to=end, security_type=str(normalized["security_type"]),
                    board=str(normalized["board"])),)
                graph_ref = None
        except (ValueError, KeyError, TypeError, SecurityMasterNormalizationError):
            quarantines.append(_quarantine(identity, "UNRESOLVED_MASTER_IDENTITY", hashes, candidates))
            continue
        facts.append(_fact(identity, intervals, hashes, policy.policy_id, graph_ref))
    if len(facts) + len(quarantines) != len(membership):
        raise HistoricalMasterTypingError("Master membership partition is incomplete")
    return DerivedMasterRowsV1(membership, len(membership), tuple(facts), tuple(quarantines),
                               len(facts), len(quarantines), content_hash(membership))


def _put_exact(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != value:
            raise HistoricalMasterTypingError("immutable Master artifact collision")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(value)


def _artifact(schema: str, id_field: str, **fields: Any) -> dict[str, Any]:
    body = {"schema_version": schema, **fields}
    digest = content_hash(body)
    return {**body, id_field: digest, "content_hash": digest}


def _read_artifact(path: Path, schema: str, id_field: str, expected_id: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise HistoricalMasterTypingError(f"exact {schema} artifact missing or malformed") from exc
    body = {key: item for key, item in value.items() if key not in {id_field, "content_hash"}}
    if (value.get("schema_version") != schema or value.get(id_field) != expected_id
            or value.get("content_hash") != expected_id or content_hash(body) != expected_id
            or canonical_json(value) != raw):
        raise HistoricalMasterTypingError(f"exact {schema} content mismatch")
    return value


@dataclass(frozen=True, slots=True)
class PublishedHistoricalMasterV1:
    authority_id: str
    approval_id: str
    manifest_id: str
    coverage_ledger_id: str
    facts_storage_sha256: str
    membership_count: int
    resolved_count: int
    quarantine_count: int
    replay_evidence_id: str


def publish_portable_master(
    *, root: Path, derived: DerivedMasterRowsV1, parent_manifest_id: str,
    parent_approval_id: str, parent_complete_bundle_id: str,
    typing_bridge_id: str, raw_payload_hashes: tuple[str, ...], replay_evidence_id: str,
    source_corpus_inventory_id: str,
) -> PublishedHistoricalMasterV1:
    ids = (parent_manifest_id, parent_approval_id, parent_complete_bundle_id,
           typing_bridge_id, replay_evidence_id, source_corpus_inventory_id)
    if (not all(_ID.fullmatch(value) for value in ids)
            or raw_payload_hashes != tuple(sorted(set(raw_payload_hashes)))
            or derived.membership != tuple(sorted(set(derived.membership)))
            or derived.membership_count != len(derived.membership)
            or derived.membership_set_hash != content_hash(derived.membership)
            or derived.resolved_count != len(derived.facts)
            or derived.quarantine_count != len(derived.quarantines)
            or derived.resolved_count + derived.quarantine_count != derived.membership_count):
        raise HistoricalMasterTypingError("portable Master inputs are not exact")
    members = set(derived.membership)
    if ({item.provider_identity for item in derived.facts} | {item.security_identity for item in derived.quarantines}) != members:
        raise HistoricalMasterTypingError("Master member accounting incomplete")
    if (len({item.provider_identity for item in derived.facts}) != len(derived.facts)
            or len({item.security_identity for item in derived.quarantines}) != len(derived.quarantines)):
        raise HistoricalMasterTypingError("Master member duplicated")
    for item in derived.facts:
        if (_fact(item.provider_identity, item.intervals, item.source_payload_hashes,
                  item.normalization_policy_id, item.graph_id) != item
                or not set(item.source_payload_hashes) <= set(raw_payload_hashes)):
            raise HistoricalMasterTypingError("Master interval fact changed or unbound")
    for item in derived.quarantines:
        body = {"schema_version": "HistoricalMasterScopedQuarantineV1",
                **{key: value for key, value in asdict(item).items()
                   if key not in {"quarantine_id", "content_hash"}}}
        if (item.quarantine_id != item.content_hash or content_hash(body) != item.quarantine_id
                or not set(item.source_payload_hashes) <= set(raw_payload_hashes)):
            raise HistoricalMasterTypingError("Master scoped quarantine changed or unbound")
    ordered = tuple(sorted(derived.facts, key=lambda item: item.provider_identity))
    facts_bytes = b"".join(canonical_json(asdict(item)) + b"\n" for item in ordered)
    storage_sha = hashlib.sha256(facts_bytes).hexdigest()
    policy_id = SecurityMasterNormalizationPolicyV1.create_default().policy_id
    authority = _artifact(
        "HistoricalSecurityMasterAuthorityV1", "authority_id",
        parent_manifest_id=parent_manifest_id, parent_approval_id=parent_approval_id,
        parent_complete_bundle_id=parent_complete_bundle_id,
        typing_bridge_id=typing_bridge_id, graph_id=GRAPH_ID,
        graph_approval_id=GRAPH_APPROVAL_ID, normalization_policy_id=policy_id,
        replay_evidence_id=replay_evidence_id,
        source_corpus_inventory_id=source_corpus_inventory_id,
        raw_payload_hashes=raw_payload_hashes,
        membership_set_hash=derived.membership_set_hash,
        fact_set_hash=content_hash(tuple(item.fact_id for item in ordered)),
        quarantine_set_hash=content_hash(tuple(item.quarantine_id for item in derived.quarantines)),
        facts_storage_sha256=storage_sha,
        membership_count=derived.membership_count, resolved_count=derived.resolved_count,
        quarantine_count=derived.quarantine_count,
        scope="PORTABLE_EFFECTIVE_INTERVAL_REPRESENTATION_OF_ALREADY_APPROVED_SECURITY_MASTER_TRUTH",
    )
    ledger = _artifact(
        "HistoricalSecurityMasterCoverageLedgerV1", "ledger_id",
        authority_id=authority["authority_id"], membership=derived.membership,
        fact_ids=tuple(item.fact_id for item in ordered),
        quarantines=tuple(asdict(item) for item in derived.quarantines),
        membership_count=derived.membership_count, resolved_count=derived.resolved_count,
        quarantine_count=derived.quarantine_count,
    )
    approval = _artifact(
        "HistoricalSecurityMasterRepresentationApprovalV1", "approval_id",
        authority_id=authority["authority_id"], coverage_ledger_id=ledger["ledger_id"],
        parent_approval_id=parent_approval_id, parent_manifest_id=parent_manifest_id,
        typing_bridge_id=typing_bridge_id, graph_approval_id=GRAPH_APPROVAL_ID,
        replay_evidence_id=replay_evidence_id,
        source_corpus_inventory_id=source_corpus_inventory_id,
        decision="APPROVED_WITH_RULES", scope=authority["scope"],
        rule="SCOPED_QUARANTINES_EXCLUDED_FROM_RESEARCH",
    )
    manifest = _artifact(
        "HistoricalSecurityMasterRepresentationManifestV1", "manifest_id",
        authority_id=authority["authority_id"], approval_id=approval["approval_id"],
        coverage_ledger_id=ledger["ledger_id"],
        parent_manifest_id=parent_manifest_id, parent_complete_bundle_id=parent_complete_bundle_id,
        replay_evidence_id=replay_evidence_id,
        source_corpus_inventory_id=source_corpus_inventory_id,
        membership_set_hash=derived.membership_set_hash, facts_storage_sha256=storage_sha,
        membership_count=derived.membership_count, resolved_count=derived.resolved_count,
        quarantine_count=derived.quarantine_count,
    )
    _put_exact(root / "facts" / f"master-intervals-{storage_sha}.jsonl", facts_bytes)
    for prefix, value, id_field in (
        ("historical-security-master-authority", authority, "authority_id"),
        ("historical-security-master-coverage-ledger", ledger, "ledger_id"),
        ("historical-security-master-representation-approval", approval, "approval_id"),
        ("historical-security-master-representation-manifest", manifest, "manifest_id"),
    ):
        _put_exact(root / "governance" / f"{prefix}-{value[id_field]}.json", canonical_json(value))
    return PublishedHistoricalMasterV1(authority["authority_id"], approval["approval_id"],
        manifest["manifest_id"], ledger["ledger_id"], storage_sha,
        derived.membership_count, derived.resolved_count, derived.quarantine_count,
        replay_evidence_id)


@dataclass(frozen=True, slots=True)
class HistoricalMasterResolutionV1:
    provider_identity: str
    effective_identity: str
    session: date
    interval: IdentityIntervalV1
    fact_id: str
    authority_id: str
    approval_id: str
    manifest_id: str
    coverage_ledger_id: str
    typing_bridge_id: str
    graph_id: str | None
    graph_approval_id: str | None
    source_payload_hashes: tuple[str, ...]
    normalization_policy_id: str


class HistoricalSecurityMasterReaderV1:
    def __init__(self, facts: tuple[HistoricalMasterIntervalFactV1, ...],
                 quarantines: tuple[HistoricalMasterScopedQuarantineV1, ...],
                 authority: Mapping[str, Any], approval: Mapping[str, Any],
                 manifest: Mapping[str, Any], ledger: Mapping[str, Any]):
        self.facts = facts
        self.quarantines = quarantines
        self.authority = authority
        self.approval = approval
        self.manifest = manifest
        self.ledger = ledger
        self._facts_by_provider = {item.provider_identity: item for item in facts}
        self._quarantined = {item.security_identity for item in quarantines}

    @classmethod
    def load_exact(cls, root: Path, *, authority_id: str, approval_id: str,
                   manifest_id: str, coverage_ledger_id: str,
                   revoked_approval_ids: tuple[str, ...]) -> "HistoricalSecurityMasterReaderV1":
        if not all(_ID.fullmatch(value) for value in (authority_id, approval_id, manifest_id, coverage_ledger_id)):
            raise HistoricalMasterTypingError("exact Master governance IDs required")
        paths = (
            ("historical-security-master-authority", "HistoricalSecurityMasterAuthorityV1", "authority_id", authority_id),
            ("historical-security-master-coverage-ledger", "HistoricalSecurityMasterCoverageLedgerV1", "ledger_id", coverage_ledger_id),
            ("historical-security-master-representation-approval", "HistoricalSecurityMasterRepresentationApprovalV1", "approval_id", approval_id),
            ("historical-security-master-representation-manifest", "HistoricalSecurityMasterRepresentationManifestV1", "manifest_id", manifest_id),
        )
        authority, ledger, approval, manifest = tuple(_read_artifact(
            root / "governance" / f"{prefix}-{identity}.json", schema, id_field, identity,
        ) for prefix, schema, id_field, identity in paths)
        if (approval_id in revoked_approval_ids or authority["parent_approval_id"] in revoked_approval_ids
                or authority["graph_approval_id"] in revoked_approval_ids):
            raise HistoricalMasterTypingError("Master approval revoked")
        if (approval.get("decision") != "APPROVED_WITH_RULES"
                or approval.get("scope") != authority.get("scope")
                or approval.get("authority_id") != authority_id
                or approval.get("coverage_ledger_id") != coverage_ledger_id
                or approval.get("parent_manifest_id") != authority.get("parent_manifest_id")
                or approval.get("parent_approval_id") != authority.get("parent_approval_id")
                or approval.get("typing_bridge_id") != authority.get("typing_bridge_id")
                or approval.get("graph_approval_id") != GRAPH_APPROVAL_ID
                or approval.get("replay_evidence_id") != authority.get("replay_evidence_id")
                or manifest.get("authority_id") != authority_id
                or manifest.get("approval_id") != approval_id
                or manifest.get("coverage_ledger_id") != coverage_ledger_id
                or manifest.get("parent_manifest_id") != authority.get("parent_manifest_id")
                or manifest.get("parent_complete_bundle_id") != authority.get("parent_complete_bundle_id")
                or manifest.get("membership_set_hash") != authority.get("membership_set_hash")
                or manifest.get("facts_storage_sha256") != authority.get("facts_storage_sha256")
                or manifest.get("replay_evidence_id") != authority.get("replay_evidence_id")
                or manifest.get("source_corpus_inventory_id") != authority.get("source_corpus_inventory_id")
                or approval.get("source_corpus_inventory_id") != authority.get("source_corpus_inventory_id")
                or ledger.get("authority_id") != authority_id):
            raise HistoricalMasterTypingError("Master governance chain does not agree")
        storage_sha = authority["facts_storage_sha256"]
        try:
            raw = (root / "facts" / f"master-intervals-{storage_sha}.jsonl").read_bytes()
            stored_facts = tuple(json.loads(line) for line in raw.splitlines())
        except (OSError, ValueError) as exc:
            raise HistoricalMasterTypingError("Master fact storage missing or malformed") from exc
        if hashlib.sha256(raw).hexdigest() != storage_sha:
            raise HistoricalMasterTypingError("Master fact storage hash mismatch")
        try:
            facts = tuple(HistoricalMasterIntervalFactV1(
                provider_identity=item["provider_identity"],
                intervals=tuple(IdentityIntervalV1(
                    identity=value["identity"], effective_from=date.fromisoformat(value["effective_from"]),
                    effective_to=date.fromisoformat(value["effective_to"]) if value["effective_to"] else None,
                    security_type=value["security_type"], board=value["board"],
                ) for value in item["intervals"]),
                source_payload_hashes=tuple(item["source_payload_hashes"]),
                normalization_policy_id=item["normalization_policy_id"],
                graph_id=item["graph_id"], fact_id=item["fact_id"], content_hash=item["content_hash"],
            ) for item in stored_facts)
            quarantines = tuple(HistoricalMasterScopedQuarantineV1(
                **{**item, "source_payload_hashes": tuple(item["source_payload_hashes"])})
                for item in ledger["quarantines"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HistoricalMasterTypingError("Master facts or quarantine ledger malformed") from exc
        if (tuple(item.provider_identity for item in facts) != tuple(sorted(set(item.provider_identity for item in facts)))
                or tuple(item.fact_id for item in facts) != tuple(ledger.get("fact_ids", ()))
                or content_hash(tuple(item.fact_id for item in facts)) != authority.get("fact_set_hash")
                or content_hash(tuple(item.quarantine_id for item in quarantines)) != authority.get("quarantine_set_hash")
                or any(_fact(item.provider_identity, item.intervals, item.source_payload_hashes,
                             item.normalization_policy_id, item.graph_id) != item for item in facts)
                or content_hash(tuple(ledger.get("membership", ()))) != authority.get("membership_set_hash")
                or set(ledger.get("membership", ())) != ({item.provider_identity for item in facts}
                    | {item.security_identity for item in quarantines})
                or any(value.get(key) != authority.get(key) for value in (ledger, manifest)
                       for key in ("membership_count", "resolved_count", "quarantine_count"))):
            raise HistoricalMasterTypingError("Master fact membership or lineage integrity failed")
        return cls(facts, quarantines, authority, approval, manifest, ledger)

    @classmethod
    def load_formal_exact(cls, source_root: Path, published_root: Path, *,
                          authority_id: str, approval_id: str, manifest_id: str,
                          coverage_ledger_id: str) -> "HistoricalSecurityMasterReaderV1":
        """Formal reader binds the representation to verified physical parents."""
        source = load_verified_master_source(source_root)
        reader = cls.load_exact(
            published_root, authority_id=authority_id, approval_id=approval_id,
            manifest_id=manifest_id, coverage_ledger_id=coverage_ledger_id,
            revoked_approval_ids=source.revoked_approval_ids,
        )
        authority = reader.authority
        if (authority.get("parent_manifest_id") != PARENT_MANIFEST_ID
                or authority.get("parent_approval_id") != PARENT_APPROVAL_ID
                or authority.get("parent_complete_bundle_id") != PARENT_BUNDLE_ID
                or authority.get("typing_bridge_id") != source.bridge.composition_id
                or authority.get("source_corpus_inventory_id") != SOURCE_CORPUS_INVENTORY_ID
                or tuple(authority.get("raw_payload_hashes", ()))
                    != tuple(sorted(source.parent_manifest["raw_payload_hashes"]))
                or set(source.revoked_approval_ids) &
                    {BASE_APPROVAL_ID, PARENT_APPROVAL_ID, GRAPH_APPROVAL_ID, approval_id}
                or tuple(reader.facts) != tuple(sorted(source.derived.facts,
                    key=lambda item: item.provider_identity))
                or tuple(reader.quarantines) != source.derived.quarantines):
            raise HistoricalMasterTypingError("formal Master authority differs from verified source")
        bridge_id = source.bridge.composition_id
        bridge = _read_artifact(
            published_root / "governance" / f"historical-master-typing-bridge-{bridge_id}.json",
            "HistoricalMasterTypingBridgeV1", "composition_id", bridge_id,
        )
        if canonical_json(bridge) != canonical_json(
                {"schema_version": "HistoricalMasterTypingBridgeV1", **asdict(source.bridge)}):
            raise HistoricalMasterTypingError("formal Master typing bridge differs from source")
        replay_id = authority["replay_evidence_id"]
        replay = _read_artifact(
            published_root / "governance" / f"historical-security-master-replay-{replay_id}.json",
            "HistoricalSecurityMasterReplayEvidenceV1", "replay_id", replay_id,
        )
        derived_hash = content_hash(asdict(source.derived))
        if (replay.get("parent_manifest_id") != PARENT_MANIFEST_ID
                or replay.get("source_corpus_inventory_id") != SOURCE_CORPUS_INVENTORY_ID
                or replay.get("typing_bridge_id") != bridge_id
                or replay.get("complete_runs") != 2
                or replay.get("run_1_derivation_hash") != derived_hash
                or replay.get("run_2_derivation_hash") != derived_hash):
            raise HistoricalMasterTypingError("formal Master replay does not prove source derivation")
        return reader

    def resolve(self, identity: str, session: date) -> HistoricalMasterResolutionV1:
        if identity in self._quarantined:
            raise HistoricalMasterTypingError("security-scoped quarantine blocks this identity")
        fact = self._facts_by_provider.get(identity)
        if fact is None and identity == "300114.SZ":
            fact = self._facts_by_provider.get("302132.SZ")
        if fact is None:
            raise HistoricalMasterTypingError("unknown Master identity")
        applicable = tuple(item for item in fact.intervals if item.effective_from <= session
                           and (item.effective_to is None or session <= item.effective_to))
        if len(applicable) != 1:
            raise HistoricalMasterTypingError("Master identity not effective or ambiguous at session")
        interval = applicable[0]
        return HistoricalMasterResolutionV1(
            fact.provider_identity, interval.identity, session, interval, fact.fact_id,
            self.authority["authority_id"], self.approval["approval_id"],
            self.manifest["manifest_id"], self.ledger["ledger_id"],
            self.authority["typing_bridge_id"], fact.graph_id,
            GRAPH_APPROVAL_ID if fact.graph_id else None,
            fact.source_payload_hashes, fact.normalization_policy_id,
        )


PARENT_MANIFEST_ID = "025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b"
PARENT_APPROVAL_ID = "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c"
BASE_APPROVAL_ID = "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf"
PARENT_BUNDLE_ID = "2675dc691521dbcfecc3ac48c8ef3af1e3fb69a9230afb6835c9a3a0ad86e69a"
OLD_BUNDLE_ID = "968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386"
RATIFICATION_ID = "e6f2a0ab1bbfc6df9d3e52f2ba4d13b661a8407ad056bd0729571cf62aa4fe92"
EXTENSION_ACQUISITION_ID = "91d432f8cf406bb12ddf08a0fcfd31ab25565177b6aa68493a903026931124ff"
SOURCE_CORPUS_INVENTORY_ID = "a534f3969943efa206d0085e5fcbf810eb70c54970610cf2e3b53c46c81ac66e"


@dataclass(frozen=True, slots=True)
class VerifiedMasterSourceV1:
    parent_manifest: Mapping[str, Any]
    parent_approval: Mapping[str, Any]
    parent_bundle: Mapping[str, Any]
    bridge: HistoricalMasterTypingBridgeV1
    pages: tuple[RawPayloadArtifactV1, ...]
    derived: DerivedMasterRowsV1
    parent_membership_count: int
    parent_input_count: int
    parent_excluded_non_target_count: int
    supplement_scoped_quarantine: str
    revoked_approval_ids: tuple[str, ...]


def _source_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise HistoricalMasterTypingError(f"exact Master source artifact missing: {path.name}") from exc
    if not isinstance(value, dict):
        raise HistoricalMasterTypingError("Master source artifact is not an object")
    return value


def _verify_parent_manifest(value: Mapping[str, Any]) -> None:
    body = {key: item for key, item in value.items() if key not in {"dataset_id", "manifest_hash"}}
    if (value.get("dataset_id") != PARENT_MANIFEST_ID
            or value.get("manifest_hash") != PARENT_MANIFEST_ID
            or content_hash({"schema_version": "DatasetManifestV1", **body}) != PARENT_MANIFEST_ID
            or value.get("dataset_kind") != "security_master"
            or value.get("approval_id") != PARENT_APPROVAL_ID
            or value.get("input_count") != 5898
            or value.get("eligible_count") != 5551
            or value.get("excluded_non_target_count") != 347
            or value.get("quarantined_count") != 0
            or value.get("row_count") != 5551
            or value.get("symbol_count") != 5551):
        raise HistoricalMasterTypingError("parent Security Master manifest mismatch")


def create_master_source_corpus_inventory(root: Path) -> dict[str, Any]:
    """Inventory every imported byte before any derived Master approval."""
    paths = tuple(sorted((path for directory in ("raw", "receipts", "governance", "graph")
                          for path in (root / directory).rglob("*.json")),
                         key=lambda item: item.relative_to(root).as_posix()))
    supplement = root / f"historical-universe-supplement-{SUPPLEMENT_ID}.json"
    paths = tuple(sorted((*paths, supplement), key=lambda item: item.relative_to(root).as_posix()))
    if len(paths) != 46 or any(not path.is_file() for path in paths):
        raise HistoricalMasterTypingError("source corpus file inventory incomplete")
    entries = tuple({"path": path.relative_to(root).as_posix(),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "bytes": path.stat().st_size} for path in paths)
    return _artifact("HistoricalSecurityMasterSourceCorpusImportV1", "inventory_id",
                     parent_manifest_id=PARENT_MANIFEST_ID, files=entries)


def _verify_source_corpus_bytes(root: Path) -> str:
    path = root / f"source-corpus-inventory-{SOURCE_CORPUS_INVENTORY_ID}.json"
    frozen = _read_artifact(path, "HistoricalSecurityMasterSourceCorpusImportV1",
                            "inventory_id", SOURCE_CORPUS_INVENTORY_ID)
    current = create_master_source_corpus_inventory(root)
    if canonical_json(current) != canonical_json(frozen):
        raise HistoricalMasterTypingError("source corpus byte identity changed")
    return SOURCE_CORPUS_INVENTORY_ID


def load_verified_master_source(root: Path) -> VerifiedMasterSourceV1:
    """Offline audit loader; never called by a research run or provider client."""
    _verify_source_corpus_bytes(root)
    gov = root / "governance"
    old = _source_json(gov / f"historical-security-master-fact-bundle-{OLD_BUNDLE_ID}.json")
    parent_bundle = _source_json(gov / f"complete-security-master-fact-bundle-{PARENT_BUNDLE_ID}.json")
    manifest = _source_json(gov / f"security-master-complete-manifest-{PARENT_MANIFEST_ID}.json")
    current_approval = _source_json(gov / f"security_master-approval-{PARENT_APPROVAL_ID}.json")
    base_approval = _source_json(gov / f"security_master-approval-{BASE_APPROVAL_ID}.json")
    acquisition = _source_json(gov / f"security_master-acquisition-{EXTENSION_ACQUISITION_ID}.json")
    graph_root = root / "graph"
    graph = _source_json(graph_root / f"effective-identity-{GRAPH_ID}.json")
    ratification = _source_json(graph_root / f"identity-graph-ratification-{RATIFICATION_ID}.json")
    graph_approval = _source_json(graph_root / f"identity-graph-approval-{GRAPH_APPROVAL_ID}.json")
    supplement = _source_json(root / f"historical-universe-supplement-{SUPPLEMENT_ID}.json")
    revocations = tuple(_source_json(path) for path in sorted(gov.glob("approval-revocation-*.json")))
    if len(revocations) != 2:
        raise HistoricalMasterTypingError("Master source revocation registry incomplete")
    for revocation in revocations:
        identity = _verify_content(revocation, "SourceApprovalRevocationArtifactV1",
                                   "revocation_id", stored_schema=False)
        if revocation.get("revocation_id") not in {
            "9591e05cc5fae5a059a6183f791f20ca4261ba8fb9b50619439fe1aef625037b",
            "e601bcabe576e3f96c660a0d8258a5a93e988453d20f58cdc069cf34337be34c",
        } or not _ID.fullmatch(str(revocation.get("approval_id", ""))):
            raise HistoricalMasterTypingError(f"Master source revocation registry mismatch: {identity}")
    revoked_approval_ids = tuple(sorted(item["approval_id"] for item in revocations))
    _verify_parent_manifest(manifest)
    _verify_content(parent_bundle, "CompleteHistoricalSecurityMasterFactBundleV1", "fact_bundle_id", stored_schema=True)
    _verify_content(current_approval, "SourceApprovalArtifactV1", "approval_id", stored_schema=False)
    _verify_content(base_approval, "SourceApprovalArtifactV1", "approval_id", stored_schema=False)
    if (parent_bundle["fact_bundle_id"] != PARENT_BUNDLE_ID
            or parent_bundle.get("base_fact_bundle_id") != OLD_BUNDLE_ID
            or manifest.get("approval_content_hash") != PARENT_APPROVAL_ID
            or tuple(manifest.get("upstream_approval_ids", ())) != (BASE_APPROVAL_ID,)
            or current_approval.get("decision") not in {"APPROVED", "APPROVED_WITH_RULES"}
            or current_approval.get("supersedes_approval_id") != BASE_APPROVAL_ID
            or base_approval.get("decision") not in {"APPROVED", "APPROVED_WITH_RULES"}
            or PARENT_BUNDLE_ID not in manifest.get("fact_content_hashes", ())
            or OLD_BUNDLE_ID not in manifest.get("fact_content_hashes", ())):
        raise HistoricalMasterTypingError("parent Master approval, bundle, or manifest chain differs")
    bridge = type_historical_master_bundle(old, graph, ratification, graph_approval, supplement)
    raw_hashes = tuple(sorted(manifest.get("raw_payload_hashes", ())))
    paths = tuple(sorted((root / "raw").glob("*.json")))
    if (len(paths) != len(raw_hashes) or tuple(sorted(path.stem for path in paths)) != raw_hashes):
        raise HistoricalMasterTypingError("source payload inventory missing or extra")
    store = RawArtifactStore(root)
    pages = tuple(store.read_payload(path) for path in paths)
    if tuple(sorted(page.payload_hash for page in pages)) != raw_hashes:
        raise HistoricalMasterTypingError("source payload inventory content mismatch")
    receipt_ids = set(manifest.get("receipt_hashes", ())) - {EXTENSION_ACQUISITION_ID}
    receipt_paths = tuple(sorted((root / "receipts").glob("*.json")))
    if {path.stem for path in receipt_paths} != receipt_ids:
        raise HistoricalMasterTypingError("source receipt inventory missing or extra")
    receipts = tuple(store.read_receipt(path) for path in receipt_paths)
    if (set(item.receipt_hash for item in receipts) != receipt_ids
            or any(item.payload_hash not in raw_hashes for item in receipts)):
        raise HistoricalMasterTypingError("source receipt chain mismatch")
    acquisition_body = {key: item for key, item in acquisition.items() if key != "artifact_id"}
    if (acquisition.get("artifact_id") != EXTENSION_ACQUISITION_ID
            or content_hash(acquisition_body) != EXTENSION_ACQUISITION_ID
            or not set(acquisition.get("payload_hashes", ())) <= set(raw_hashes)):
        raise HistoricalMasterTypingError("source extension acquisition mismatch")
    membership = tuple(parent_bundle.get("ordered_security_identities", ()))
    if (len(membership) != 5551 or membership != tuple(sorted(set(membership)))
            or not set(membership) <= {str(row.get("ts_code"))
                for page in pages for row in page.provider_payload["rows"]}):
        raise HistoricalMasterTypingError("parent Master membership does not match source census")
    derived = derive_master_intervals(membership=membership, pages=pages,
        expected_payload_hashes=raw_hashes, graph=graph,
        graph_approval_id=GRAPH_APPROVAL_ID)
    return VerifiedMasterSourceV1(manifest, current_approval, parent_bundle, bridge,
        pages, derived, len(membership), manifest["input_count"],
        manifest["excluded_non_target_count"], "600747.SH", revoked_approval_ids)


def publish_verified_master_source(
    source_root: Path, output_root: Path, *, revoked_approval_ids: tuple[str, ...] | None = None,
) -> PublishedHistoricalMasterV1:
    """Only the exact physical source corpus may issue the formal representation."""
    first = load_verified_master_source(source_root)
    if revoked_approval_ids is not None and tuple(sorted(revoked_approval_ids)) != first.revoked_approval_ids:
        raise HistoricalMasterTypingError("caller revocation registry differs from exact source")
    if set(first.revoked_approval_ids) & {BASE_APPROVAL_ID, PARENT_APPROVAL_ID, GRAPH_APPROVAL_ID}:
        raise HistoricalMasterTypingError("parent or graph approval revoked")
    second = load_verified_master_source(source_root)
    first_hash = content_hash(asdict(first.derived))
    second_hash = content_hash(asdict(second.derived))
    if first_hash != second_hash or first.derived != second.derived:
        raise HistoricalMasterTypingError("Master deterministic replay diverged")
    replay = _artifact(
        "HistoricalSecurityMasterReplayEvidenceV1", "replay_id",
        parent_manifest_id=PARENT_MANIFEST_ID,
        source_corpus_inventory_id=SOURCE_CORPUS_INVENTORY_ID,
        typing_bridge_id=first.bridge.composition_id,
        run_1_derivation_hash=first_hash, run_2_derivation_hash=second_hash,
        complete_runs=2,
    )
    bridge = {"schema_version": "HistoricalMasterTypingBridgeV1",
              **asdict(first.bridge)}
    _put_exact(output_root / "governance" /
               f"historical-master-typing-bridge-{first.bridge.composition_id}.json",
               canonical_json(bridge))
    _put_exact(output_root / "governance" /
               f"historical-security-master-replay-{replay['replay_id']}.json",
               canonical_json(replay))
    return publish_portable_master(
        root=output_root, derived=first.derived,
        parent_manifest_id=PARENT_MANIFEST_ID, parent_approval_id=PARENT_APPROVAL_ID,
        parent_complete_bundle_id=PARENT_BUNDLE_ID,
        typing_bridge_id=first.bridge.composition_id,
        raw_payload_hashes=tuple(sorted(first.parent_manifest["raw_payload_hashes"])),
        replay_evidence_id=replay["replay_id"],
        source_corpus_inventory_id=SOURCE_CORPUS_INVENTORY_ID,
    )
