from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.raw_artifacts import AcquisitionReceiptV1, RawArtifactStore, RawPayloadArtifactV1  # noqa: E402
from v5_2.data.real_audits.corporate_action_probe import evaluate_probe_response  # noqa: E402
from v5_2.providers.contracts import ProviderRequestV1  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402


BASE_URL = "http://datahubco.com/app-api/openapi/v1/tushare"
RUNTIME = ROOT / "data" / "phase_1b2c"
CANDIDATES = (
    ("dividend", {"ts_code": "600000.SH", "start_date": "20240101", "end_date": "20261231", "limit": 3}),
    ("rights", {"ts_code": "600000.SH", "start_date": "20100101", "end_date": "20261231", "limit": 3}),
    ("rights_issue", {"ts_code": "600000.SH", "start_date": "20100101", "end_date": "20261231", "limit": 3}),
    ("adj_factor", {"ts_code": "600000.SH", "start_date": "20260101", "end_date": "20261231", "limit": 3}),
    ("share_float", {"ts_code": "600000.SH", "start_date": "20240101", "end_date": "20261231", "limit": 3}),
)


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable probe artifact collision")
        return
    path.write_bytes(encoded)


def main() -> int:
    credential = load_datahub_credential(env_file=ROOT / ".env", repository_root=ROOT)
    store = RawArtifactStore(RUNTIME)
    probes = []
    for endpoint, parameters in CANDIDATES:
        observed_at = datetime.now(timezone.utc)
        request = Request(
            f"{BASE_URL}/{endpoint}?{urlencode(parameters)}",
            headers={"X-API-Key": credential.reveal_for_transport(), "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read())
            if credential.is_exposed_in(payload):
                raise RuntimeError("provider response failed credential safety check")
        except Exception:
            payload = {"code": -1}
        probe = evaluate_probe_response(
            endpoint=endpoint, response=payload,
            requested_scope="2010-01-04..2026-12-31",
            observed_at=observed_at.isoformat(),
        )
        probes.append(probe)
        if probe.disposition in {"SUPPORTED", "AUDIT_ONLY"}:
            provider_request = ProviderRequestV1.create(
                source_name="datahubco_tushare_proxy", dataset_kind="corporate_action_probe",
                endpoint=endpoint, parameters=parameters, requested_fields=probe.fields,
                page_size=3, request_policy_version="phase-1b2c-provider-probe-v1",
            )
            raw = RawPayloadArtifactV1.create(
                request_id=provider_request.request_id, page_identity={"offset": 0},
                provider_payload=payload,
                semantic_metadata={"endpoint": endpoint, "disposition": probe.disposition},
            )
            store.put_payload("datahubco_tushare_proxy", "corporate_action_probe", raw)
            store.put_receipt(AcquisitionReceiptV1.create(
                payload_hash=raw.payload_hash, acquired_at=observed_at,
                attempt_metadata={"attempts": 1},
                transport_metadata={"transport": "datahub-http", "timeout_seconds": 30},
            ))
    artifact = {
        "schema_version": "CorporateActionProviderProbeBundleV1",
        "probes": tuple(asdict(probe) for probe in probes),
    }
    _write_immutable(RUNTIME / "governance" / "provider_probe.json", artifact)
    for probe in probes:
        print(f"ENDPOINT={probe.endpoint} DISPOSITION={probe.disposition} ROWS={probe.row_count} FIELDS={','.join(probe.fields)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
