from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import AcquisitionReceiptV1, RawArtifactStore, RawPayloadArtifactV1  # noqa: E402
from v5_2.providers.contracts import ProviderRequestV1  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402

INVENTORY_ID = "7ca99bfecd2731d5442ea62eb496afe3cff9b01a7ba32c1434a461c1a931a9c0"


def main() -> int:
    runtime = ROOT / "data" / "phase_1b2a"
    inventory = json.loads((runtime / "governance" / f"status-sample-inventory-{INVENTORY_ID}.json").read_text(encoding="utf-8"))
    extra = "f61a553ca2ec93dc00f9c0658e9fa9691edc8cf17ede02f412a048f3f03f84fc"
    samples = {item["event_id"]: item for item in inventory["samples"]
               if item["stratum"] == "st_transition" or item["event_id"] == extra}
    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    client, store = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30)), RawArtifactStore(runtime)
    observations = []
    for sample in samples.values():
        for kind, endpoint, fields, parameters in (
            ("risk_warning_daily", "stock-st", ("ts_code", "name", "trade_date", "type", "type_name"),
             {"ts_code": sample["security_identity"], "start_date": sample["session"], "end_date": sample["session"]}),
            ("risk_warning_events", "st", ("ts_code", "name", "pub_date", "imp_date", "st_type", "st_reason", "st_explain"),
             {"ts_code": sample["security_identity"]}),
        ):
            request = ProviderRequestV1.create(source_name="datahubco_tushare_proxy", dataset_kind=kind,
                endpoint=endpoint, parameters=parameters, requested_fields=fields, page_size=500,
                request_policy_version="phase-1b2a-evidence-recovery-v1")
            page = client.fetch_page(request, credential, page_identity={"offset": 0})
            artifact = RawPayloadArtifactV1.create(request_id=request.request_id, page_identity=page.page_identity,
                provider_payload={"rows": tuple(dict(row) for row in page.rows), "response_code": page.response_code,
                                  "has_more": page.has_more, "total_count": page.total_count},
                semantic_metadata={"endpoint": endpoint, "sample_event_id": sample["event_id"],
                                   "evidence_only": True, "not_independent_cross_source": True})
            store.put_payload("datahubco_tushare_proxy", kind, artifact)
            receipt = AcquisitionReceiptV1.create(payload_hash=artifact.payload_hash, acquired_at=datetime.now(timezone.utc),
                attempt_metadata={"attempt": 1}, transport_metadata={"scheme": "http", "status": "success"})
            store.put_receipt(receipt)
            observations.append({"event_id": sample["event_id"], "security_identity": sample["security_identity"],
                "session": sample["session"], "dataset_kind": kind, "request_id": request.request_id,
                "payload_hash": artifact.payload_hash, "row_count": len(page.rows)})
    body = {"schema_version": "StatusEvidenceRecoveryDiagnosticV1", "inventory_id": INVENTORY_ID,
            "observations": tuple(observations), "finding": "DataHub stock-st and st are available but are not independent official cross-source evidence",
            "credential_stored": False}
    body["content_hash"] = content_hash(body)
    path = runtime / "governance" / f"status-evidence-recovery-{body['content_hash']}.json"
    path.write_bytes(canonical_json(body))
    print(json.dumps({"events": len(samples), "requests": len(observations),
                      "rows": sum(item["row_count"] for item in observations), "diagnostic_id": body["content_hash"],
                      "cross_source_eligible": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
