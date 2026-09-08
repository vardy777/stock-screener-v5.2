from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class OfficialAnchorGapEntryV1:
    candidate_hash: str
    security_identity: str
    session: str
    semantic: str
    provider_value: str
    baostock_observation: object
    required_official_anchor_type: str
    current_evidence_ids: tuple[str, ...]
    gap_reason: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class OfficialAnchorGapInventoryV1:
    contract_id: str
    inventory_id: str
    entries: tuple[OfficialAnchorGapEntryV1, ...]
    counts: tuple[tuple[str, int], ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class OfficialAnchorAssertionV1:
    candidate_hash: str
    security_identity: str
    session: str
    semantic: str
    source_url: str
    document_title: str
    publication_date: str
    asserted_identity: str
    asserted_effective_session: str


@dataclass(frozen=True, slots=True)
class OfficialAnchorEvidenceV1:
    candidate_hash: str
    security_identity: str
    session: str
    semantic: str
    source_url: str
    document_title: str
    publication_date: str
    document_sha256: str | None
    resolution: str
    evidence_id: str


ANCHOR_TYPES = {
    "ACTUAL_FIRST_TRADABLE_SESSION": "ACTUAL_LISTING_TRADING_DATE",
    "DELISTING_BOUNDARY": "DELISTING_EFFECTIVE_DATE",
}


def build_official_anchor_gap_inventory(contract_id, inventory_id, samples, observations,
                                        *, expected_count=19):
    by_candidate = {item["candidate_hash"]: item for item in observations}
    entries = []
    for sample in samples:
        candidate_hash = sample["candidate_hash"]
        observation = by_candidate.get(candidate_hash)
        if observation is None:
            raise ValueError("gap candidate has no independent observation")
        if observation["resolution"] != "INDEPENDENT_EVIDENCE_UNAVAILABLE":
            continue
        semantic = sample["semantic"]
        if semantic not in ANCHOR_TYPES:
            raise ValueError("gap candidate is not an official-anchor semantic")
        evidence_ids = tuple(sorted(set((*sample["provider_evidence_ids"],
                                         observation["source_document_hash"]))))
        body = {"schema_version": "OfficialAnchorGapEntryV1", "candidate_hash": candidate_hash,
                "security_identity": sample["security_identity"], "session": sample["session"],
                "semantic": semantic, "provider_value": sample["provider_value"],
                "baostock_observation": observation["independent_value"],
                "required_official_anchor_type": ANCHOR_TYPES[semantic],
                "current_evidence_ids": evidence_ids,
                "gap_reason": "official anchor required by frozen V2 contract is absent"}
        values = {key: value for key, value in body.items() if key != "schema_version"}
        entries.append(OfficialAnchorGapEntryV1(**values, content_hash=content_hash(body)))
    entries = tuple(sorted(entries, key=lambda item: item.candidate_hash))
    if expected_count is not None and len(entries) != expected_count:
        raise ValueError(f"expected {expected_count} official-anchor gaps, found {len(entries)}")
    counts = tuple(sorted((semantic, sum(item.semantic == semantic for item in entries))
                          for semantic in {item.semantic for item in entries}))
    body = {"schema_version": "OfficialAnchorGapInventoryV1", "contract_id": contract_id,
            "inventory_id": inventory_id, "entry_hashes": tuple(item.content_hash for item in entries),
            "counts": counts}
    return OfficialAnchorGapInventoryV1(contract_id, inventory_id, entries, counts, content_hash(body))


def evaluate_official_anchor(gap: OfficialAnchorGapEntryV1, assertion: OfficialAnchorAssertionV1,
                             document: bytes | None) -> OfficialAnchorEvidenceV1:
    binding_matches = (
        assertion.candidate_hash == gap.candidate_hash
        and assertion.security_identity == gap.security_identity
        and assertion.session == gap.session
        and assertion.semantic == gap.semantic
    )
    semantic_matches = (assertion.asserted_identity == gap.security_identity
                        and assertion.asserted_effective_session == gap.session)
    digest = sha256(document).hexdigest() if document else None
    if not document:
        resolution = "OFFICIAL_ANCHOR_UNAVAILABLE"
    elif not binding_matches or not semantic_matches:
        resolution = "OFFICIAL_MISMATCH"
    else:
        resolution = "MATCH"
    body = {"schema_version": "OfficialAnchorEvidenceV1", "candidate_hash": gap.candidate_hash,
            "security_identity": gap.security_identity, "session": gap.session, "semantic": gap.semantic,
            "source_url": assertion.source_url, "document_title": assertion.document_title,
            "publication_date": assertion.publication_date, "document_sha256": digest,
            "resolution": resolution}
    return OfficialAnchorEvidenceV1(**{key: value for key, value in body.items() if key != "schema_version"},
                                    evidence_id=content_hash(body))


def merge_official_anchor_supplement(observations, evidence):
    by_candidate = {item.candidate_hash: item for item in evidence}
    gaps = [item for item in observations if item["resolution"] == "INDEPENDENT_EVIDENCE_UNAVAILABLE"]
    if set(by_candidate) != {item["candidate_hash"] for item in gaps}:
        raise ValueError("supplement must bind exactly every unavailable frozen candidate")
    merged = []
    for observation in observations:
        anchor = by_candidate.get(observation["candidate_hash"])
        if anchor is None:
            merged.append(dict(observation))
            continue
        item = dict(observation)
        item["resolution"] = ("MATCH" if anchor.resolution == "MATCH" else
                              "MISMATCH" if anchor.resolution == "OFFICIAL_MISMATCH" else
                              "INDEPENDENT_EVIDENCE_UNAVAILABLE")
        item["official_anchor_evidence_id"] = anchor.evidence_id
        item["official_anchor_document_hash"] = anchor.document_sha256
        merged.append(item)
    return tuple(merged)
