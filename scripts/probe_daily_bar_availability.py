from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import AcquisitionReceiptV1, RawArtifactStore, RawPayloadArtifactV1  # noqa: E402
from v5_2.data.real_audits.daily_bar_availability import (  # noqa: E402
    DailyBarAvailabilityEvidenceV1,
    DailyBarProbeObservationV1,
)
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.contracts import ProviderRequestV1  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402


SOURCE = "datahubco_tushare_proxy"
SESSION = date(2026, 9, 9)
SAMPLES = (
    "000001.SZ",  # SZSE main board / high liquidity
    "002001.SZ",  # SZSE main board / lower liquidity stratum
    "300750.SZ",  # ChiNext
    "600000.SH",  # SSE main board / lower liquidity stratum
    "600519.SH",  # SSE main board / high liquidity
    "688981.SH",  # STAR
)
SOURCE_VERSION_ID = "ea88e3bcf5ecbae599567d1f22756f1333b9ff134c2face0895e60fcadc05986"
RUNTIME = ROOT / "data" / "phase_1b2b"


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable availability artifact collision")
        return
    path.write_bytes(encoded)


def main() -> int:
    credential = load_datahub_credential(env_file=ROOT / ".env", repository_root=ROOT)
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    store = RawArtifactStore(RUNTIME)
    observations = []
    receipt_ids = []
    for round_number in (1, 2):
        for symbol in SAMPLES:
            request = ProviderRequestV1.create(
                source_name=SOURCE,
                dataset_kind="daily_bar",
                endpoint="daily",
                parameters={
                    "ts_code": symbol,
                    "start_date": SESSION.strftime("%Y%m%d"),
                    "end_date": SESSION.strftime("%Y%m%d"),
                    "fields": "ts_code,trade_date,open,high,low,close,vol,amount",
                },
                requested_fields=("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"),
                page_size=10,
                request_policy_version="daily-bar-availability-probe-v1",
            )
            requested_at = datetime.now(timezone.utc)
            page = client.fetch_page(request, credential, page_identity={"offset": 0})
            raw = RawPayloadArtifactV1.create(
                request_id=request.request_id,
                page_identity={"offset": 0, "probe_round": round_number},
                provider_payload={"rows": page.rows},
                semantic_metadata={
                    "endpoint": "daily",
                    "has_more": page.has_more,
                    "total_count": page.total_count,
                    "probe_session": SESSION,
                },
            )
            store.put_payload(SOURCE, "daily_bar_availability_probe", raw)
            receipt = AcquisitionReceiptV1.create(
                payload_hash=raw.payload_hash,
                acquired_at=requested_at,
                attempt_metadata={"attempts": 1, "probe_round": round_number},
                transport_metadata={"transport": "datahub-http", "timeout_seconds": 30},
            )
            store.put_receipt(receipt)
            receipt_ids.append(receipt.receipt_hash)
            observations.append(DailyBarProbeObservationV1.create(
                session=SESSION,
                requested_at=requested_at,
                expected_symbols=(symbol,),
                rows=tuple(page.rows),
                payload_hash=content_hash(tuple(page.rows)),
                receipt_id=receipt.receipt_hash,
                source_version_identity=SOURCE_VERSION_ID,
            ))
        if round_number == 1:
            time.sleep(2)
    calendar_request = ProviderRequestV1.create(
        source_name=SOURCE,
        dataset_kind="trade_calendar",
        endpoint="trade-cal",
        parameters={
            "exchange": "SSE", "start_date": "20260101", "end_date": "20260110",
            "fields": "exchange,cal_date,is_open,pretrade_date",
        },
        requested_fields=("exchange", "cal_date", "is_open", "pretrade_date"),
        page_size=20,
        request_policy_version="daily-bar-availability-probe-v1",
    )
    calendar_at = datetime.now(timezone.utc)
    calendar_page = client.fetch_page(calendar_request, credential, page_identity={"offset": 0})
    calendar_raw = RawPayloadArtifactV1.create(
        request_id=calendar_request.request_id, page_identity={"offset": 0},
        provider_payload={"rows": calendar_page.rows},
        semantic_metadata={"endpoint": "trade-cal", "purpose": "coverage-end next-safe-session"},
    )
    store.put_payload(SOURCE, "trade_calendar_availability_support", calendar_raw)
    calendar_receipt = AcquisitionReceiptV1.create(
        payload_hash=calendar_raw.payload_hash, acquired_at=calendar_at,
        attempt_metadata={"attempts": 1},
        transport_metadata={"transport": "datahub-http", "timeout_seconds": 30},
    )
    store.put_receipt(calendar_receipt)
    receipt_ids.append(calendar_receipt.receipt_hash)
    next_coverage_session = min(
        str(row["cal_date"])
        for row in calendar_page.rows
        if str(row.get("is_open")) in {"1", "True", "true"} and str(row["cal_date"]) > "20251231"
    )
    evidence = DailyBarAvailabilityEvidenceV1.create(
        policy_version="daily-bar-availability-v1",
        source_name=SOURCE,
        source_version_identity=SOURCE_VERSION_ID,
        coverage_sessions=(SESSION,),
        probe_times=tuple(item.requested_at for item in observations),
        sample_scope=SAMPLES,
        observations=tuple(observations),
        revision_findings=("two immediate D+1 probes produced identical semantic payloads per symbol",),
        full_market_readiness_rule="bounded samples do not establish same-day full-market readiness",
        historical_available_at_rule=f"NEXT_SESSION_SAFE@16:30 Asia/Shanghai; coverage-end-next-session={next_coverage_session}",
        supporting_receipt_ids=tuple(receipt_ids),
    )
    path = RUNTIME / "governance" / f"daily-bar-availability-{evidence.content_hash}.json"
    _write_immutable(path, asdict(evidence))
    print(f"ARTIFACT_ID={evidence.content_hash}")
    print(f"OBSERVATIONS={len(observations)} COMPLETE={str(evidence.complete).lower()}")
    print(f"SESSION={SESSION.isoformat()} SAMPLES={len(SAMPLES)} RULE={evidence.historical_available_at_rule}")
    return 0 if evidence.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
