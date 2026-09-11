from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import AcquisitionReceiptV1, RawArtifactStore, RawPayloadArtifactV1  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402

RUNTIME = ROOT / "data" / "phase_1b2d"
ENDPOINTS = ("income", "balancesheet", "cashflow", "fina-indicator", "forecast", "express")
NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def main() -> int:
    credential = load_datahub_credential(env={}, env_file=ROOT / ".env", repository_root=ROOT)
    store = RawArtifactStore(RUNTIME)
    entries = []
    for endpoint in ENDPOINTS:
        request_id = content_hash({"schema_version": "FinancialEndpointProbeRequestV1", "endpoint": endpoint,
                                   "parameters": {"ts_code": "600000.SH", "start_date": "20230101", "end_date": "20241231", "limit": 3}})
        try:
            parameters = {"ts_code": "600000.SH", "start_date": "20230101", "end_date": "20241231", "limit": 3, "offset": 0}
            url = f"http://datahubco.com/app-api/openapi/v1/tushare/{endpoint}?{urlencode(parameters)}"
            request = Request(url, headers={"X-API-Key": credential.reveal_for_transport(), "Accept": "application/json"})
            with urlopen(request, timeout=30) as provider_response:
                response = json.loads(provider_response.read())
            data = response.get("data") if response.get("code") == 0 else None
            if not isinstance(data, dict): raise RuntimeError("invalid provider response")
            fields, items = data.get("fields", []), data.get("items", [])
            payload = RawPayloadArtifactV1.create(request_id=request_id, page_identity={"offset": 0},
                provider_payload={"rows": tuple(dict(zip(fields, item, strict=True)) for item in items)},
                semantic_metadata={"response_code": response.get("code"), "has_more": data.get("has_more"), "total_count": data.get("count")})
            store.put_payload("datahubco_tushare_proxy", "financial_endpoint_probe", payload)
            receipt = AcquisitionReceiptV1.create(payload_hash=payload.payload_hash, acquired_at=NOW,
                attempt_metadata={"attempts": 1}, transport_metadata={"transport": "DataHubHttpTransport"})
            store.put_receipt(receipt)
            entries.append({"endpoint": endpoint, "supported": True, "fields": tuple(fields), "sample_row_count": len(items),
                            "has_more": data.get("has_more"), "total_count": data.get("count"), "payload_hash": payload.payload_hash,
                            "receipt_hash": receipt.receipt_hash, "publication_fields": tuple(field for field in fields if field in {"ann_date", "f_ann_date", "first_ann_date"}),
                            "period_fields": tuple(field for field in fields if field in {"end_date"}),
                            "revision_fields": tuple(field for field in fields if field in {"update_flag", "first_ann_date"})})
        except Exception as error:
            entries.append({"endpoint": endpoint, "supported": False, "error_type": type(error).__name__})
    body = {"schema_version": "FinancialEndpointCapabilityAuditV1", "source_name": "datahubco_tushare_proxy",
            "entries": tuple(entries), "approved_candidate_endpoints": ("income", "balancesheet", "cashflow"),
            "unsupported_for_primary_facts": ("fina-indicator", "forecast", "express")}
    audit_id = content_hash(body); output = {"audit_id": audit_id, "content_hash": audit_id, **body}
    path = RUNTIME / "governance" / f"endpoint-capability-{audit_id}.json"; path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != canonical_json(output): raise RuntimeError("immutable probe collision")
    if not path.exists(): path.write_bytes(canonical_json(output))
    (path.parent / "current-endpoint-capability-id.txt").write_text(audit_id, encoding="ascii")
    print(" ".join(f"{item['endpoint']}={'SUPPORTED' if item['supported'] else 'UNSUPPORTED'}:{item.get('sample_row_count', 0)}" for item in entries))
    print(f"ENDPOINT_CAPABILITY_AUDIT_ID={audit_id}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
