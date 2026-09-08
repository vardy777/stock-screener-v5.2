from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class OfficialStatusSampleEntryV1:
    sample_id: str
    event_id: str
    security_identity: str
    session: str
    stratum: str
    provider_observation: str
    official_observation: str | None
    official_evidence_id: str | None
    semantic_mapping: str
    resolution: str


@dataclass(frozen=True, slots=True)
class OfficialStatusSampleLedgerV1:
    inventory_id: str
    entries: tuple[OfficialStatusSampleEntryV1, ...]
    unique_event_count: int
    counts: tuple[tuple[str, int], ...]
    systematic_defect: bool
    content_hash: str


def build_official_sample_ledger(inventory_id: str, samples: Sequence[Mapping[str, object]],
                                 official: Mapping[str, Mapping[str, str]]) -> OfficialStatusSampleLedgerV1:
    entries = []
    for index, sample in enumerate(samples):
        event_id = str(sample["event_id"])
        evidence = official.get(event_id)
        resolution = "UNRESOLVED" if not evidence else evidence["resolution"]
        if resolution not in {"MATCH", "MISMATCH", "UNRESOLVED", "OFFICIAL_REFERENCE_UNAVAILABLE",
                              "INDEPENDENT_EVIDENCE_UNAVAILABLE"}:
            raise ValueError("invalid official resolution")
        entry_id = content_hash({"inventory_id": inventory_id, "entry_index": index, "event_id": event_id})
        entries.append(OfficialStatusSampleEntryV1(
            entry_id, event_id, str(sample["security_identity"]), str(sample["session"]), str(sample["stratum"]),
            "frozen provider-derived sample event", evidence.get("observation") if evidence else None,
            evidence.get("evidence_id") if evidence else None,
            evidence.get("semantic_mapping", "not established") if evidence else "not established",
            resolution,
        ))
    counts = tuple(sorted((key, sum(item.resolution == key for item in entries)) for key in set(item.resolution for item in entries)))
    systematic = any(item.resolution == "MISMATCH" for item in entries)
    body = {"inventory_id": inventory_id, "entries": entries, "unique_event_count": len({item.event_id for item in entries}),
            "counts": counts, "systematic_defect": systematic}
    return OfficialStatusSampleLedgerV1(**body, content_hash=content_hash(body))
