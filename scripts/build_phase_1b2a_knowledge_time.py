from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.status_knowledge_time import StatusKnowledgeTimeObservationV1  # noqa: E402

INVENTORY_ID = "7ca99bfecd2731d5442ea62eb496afe3cff9b01a7ba32c1434a461c1a931a9c0"


def day(value):
    return date(int(value[:4]), int(value[4:6]), int(value[6:]))


def main() -> int:
    directory = ROOT / "data" / "phase_1b2a" / "governance"
    inventory = json.loads((directory / f"status-sample-inventory-{INVENTORY_ID}.json").read_text(encoding="utf-8"))
    source_path = max(directory.glob("baostock-status-evidence-*.json"), key=lambda path: path.stat().st_mtime)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    by_event = {item["event_id"]: item for item in source["observations"] if item["resolution"] == "MATCH"}
    semantics = {"st_transition": "RISK_WARNING_STATE", "suspension_transition": "FULL_DAY_SUSPENSION",
                 "listing_delisting_boundary": "DELISTING_EFFECTIVE_BOUNDARY"}
    observations = []
    for index, sample in enumerate(inventory["samples"]):
        independent = by_event.get(sample["event_id"])
        if independent is None or sample["stratum"] not in semantics:
            continue
        entry_id = content_hash({"inventory_id": INVENTORY_ID, "entry_index": index, "event_id": sample["event_id"]})
        session = day(sample["session"])
        observation = StatusKnowledgeTimeObservationV1.create(
            event_id=sample["event_id"], sample_entry_id=entry_id,
            security_identity=sample["security_identity"], status_semantic=semantics[sample["stratum"]],
            effective_session=session, provider_observation="frozen provider-derived event",
            independent_observation=json.dumps(independent["rows"], ensure_ascii=False, sort_keys=True),
            independent_source_id=source["source_identity"], source_reference=source["retrieval_method"],
            source_document_hash=independent["source_document_hash"], publication_date=None,
            publication_timestamp=None, availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
            approved_sessions=(session,), semantic_mapping_version="status-cross-source-map-v1",
            input_artifact_ids=(source["content_hash"], INVENTORY_ID),
        )
        observations.append(observation)
    body = {"schema_version": "StatusKnowledgeTimeObservationBundleV1", "inventory_id": INVENTORY_ID,
            "availability_policy_version": "status-availability-after-close-v2", "research_cutoff": "16:30:00+08:00",
            "observations": tuple(asdict(item) for item in observations), "complete": False,
            "pit_evidence_published": False,
            "limitation": "unresolved/unavailable frozen samples and non-sampled status semantics prevent complete PIT evidence"}
    body["content_hash"] = content_hash(body)
    output = directory / f"status-knowledge-time-observations-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps({"observation_count": len(observations), "usable_at_D_cutoff": sum(item.usable_at_D_cutoff for item in observations),
                      "complete": False, "pit_evidence_published": False, "bundle_id": body["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
