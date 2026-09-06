from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import ssl
import sys
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.phase_1b1_policies import phase_1b1_policies  # noqa: E402
from v5_2.data.phase_1b1_requests import phase_1b1_requests  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.security_master_governance import SecurityMasterOfficialSampleInventoryV1, select_frozen_security_samples  # noqa: E402
from v5_2.data.real_audits.security_master_normalization import SecurityMasterNormalizationPolicyV1  # noqa: E402
from scripts.acquire_szse_calendar_audit import _fetch_with_retry  # noqa: E402


AS_OF = datetime(2026, 9, 6, tzinfo=timezone.utc)
SZSE_LIST = "https://www.szse.cn/api/report/ShowReport?SHOWTYPE=xlsx&CATALOGID=1110&TABKEY=tab1"
SZSE_DELIST = "https://www.szse.cn/api/report/ShowReport?SHOWTYPE=xlsx&CATALOGID=1793_ssgs&TABKEY=tab2"
SSE_LIST = "https://query.sse.com.cn/sseQuery/commonQuery.do"


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def _opener():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return build_opener(ProxyHandler({}), HTTPSHandler(context=context))


def _get(url: str, *, referer: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer})
    with _opener().open(request, timeout=30) as response:
        return response.read()


def _master_rows():
    store = RawArtifactStore(ROOT / "data" / "phase_1b1")
    rows = []
    for request in phase_1b1_requests()["security_master"]:
        request_root = store.root / "raw" / request.source_name / request.dataset_kind / request.request_id[:16]
        for path in sorted(request_root.rglob("*.json")):
            rows.extend(store.read_payload(path).provider_payload["rows"])
    normalization = SecurityMasterNormalizationPolicyV1.create_default()
    return tuple(row for row in rows if normalization.disposition(row) == "NORMALIZED_ELIGIBLE")


def _date(value):
    if value is None or str(value) in {"", "nan", "NaT", "-"}:
        return None
    return str(value)[:10].replace("-", "").replace("/", "")


def _official_rows(samples, output: Path):
    import pandas as pd
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sz_list = pd.read_excel(BytesIO(_get(SZSE_LIST, referer="https://www.szse.cn/market/product/stock/list/index.html")))
        sz_delist = pd.read_excel(BytesIO(_get(SZSE_DELIST, referer="https://www.szse.cn/market/stock/suspend/index.html")))
    sz_current = {}
    for values in sz_list.itertuples(index=False, name=None):
        if values[4] is None or str(values[4]) == "nan":
            continue
        code = str(int(values[4])).zfill(6)
        sz_current[code] = {"symbol": code, "exchange": "SZSE", "listing_date": _date(values[6]), "delisting_date": None, "board": str(values[0])}
    sz_ended = {}
    for values in sz_delist.itertuples(index=False, name=None):
        code = str(int(values[0])).zfill(6)
        sz_ended[code] = {"symbol": code, "exchange": "SZSE", "listing_date": _date(values[2]), "delisting_date": _date(values[3]), "board": None}

    sh = {}
    sh_codes = sorted({str(sample["ts_code"]).split(".")[0] for sample in samples if sample["exchange"] == "SSE"})
    for requested_code in sh_codes:
        params = {
            "STOCK_TYPE": "1,8", "REG_PROVINCE": "", "CSRC_CODE": "", "STOCK_CODE": requested_code,
            "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L", "COMPANY_STATUS": "2,3,4,5,7,8",
            "type": "inParams", "isPagination": "true", "pageHelp.cacheSize": "1",
            "pageHelp.beginPage": "1", "pageHelp.pageSize": "10", "pageHelp.pageNo": "1", "pageHelp.endPage": "1",
        }
        cached = sorted(output.glob(f"sse-official-security-{requested_code}-*.json"))
        if cached:
            result_rows = json.loads(cached[0].read_text(encoding="utf-8"))["rows"]
        else:
            url = f"{SSE_LIST}?{urlencode(params)}"
            raw = _fetch_with_retry(lambda _: _get(url, referer="https://www.sse.com.cn/assortment/stock/list/share/"), requested_code)
            result_rows = json.loads(raw.decode("utf-8"))["result"]
            artifact = {"schema_version": "SSEOfficialSecurityResponseV1", "requested_code": requested_code, "source_identity": url, "rows": result_rows}
            artifact_id = content_hash(artifact)
            (output / f"sse-official-security-{requested_code}-{artifact_id}.json").write_bytes(canonical_json({**artifact, "content_hash": artifact_id}))
        for row in result_rows:
            code = str(row["A_STOCK_CODE"])
            sh[code] = {"symbol": code, "exchange": "SSE", "listing_date": _date(row.get("LIST_DATE")), "delisting_date": _date(row.get("DELIST_DATE")), "board": "科创板" if str(row.get("STOCK_TYPE")) == "8" else "主板"}
    return sz_current, sz_ended, sh


def main() -> int:
    policy = phase_1b1_policies()["security_master"]
    samples = select_frozen_security_samples(_master_rows(), policy_id=policy.policy_id)
    output = ROOT / "data" / "phase_1b1" / "governance"
    sz_current, sz_ended, sh = _official_rows(samples, output)
    evidence = {}
    for sample in samples:
        provider = dict(sample["provider_values"])
        code = str(sample["ts_code"]).split(".")[0]
        source = SSE_LIST if sample["exchange"] == "SSE" else (SZSE_DELIST if provider["delisting_date"] else SZSE_LIST)
        official = sh.get(code) if sample["exchange"] == "SSE" else (sz_current.get(code) or sz_ended.get(code))
        resolution = "UNRESOLVED"
        if official is not None and all(official.get(field) is not None or provider.get(field) is None for field in provider):
            resolution = "VERIFIED" if official == provider else "MISMATCH"
        body = {"sample_id": sample["sample_id"], "official_source_identity": source, "official_values": official, "provider_values": provider, "resolution": resolution, "verified_at": AS_OF, "policy_version": "official-security-sample-evidence-v1"}
        evidence[sample["sample_id"]] = {**body, "evidence_id": content_hash({"schema_version": "OfficialSecuritySampleEvidenceV1", **body})}
    inventory = SecurityMasterOfficialSampleInventoryV1.create(
        frozen_samples=samples, official_evidence=evidence, verified_at=AS_OF,
        policy_id=policy.policy_id, policy_version="official-security-sample-v1",
    )
    (output / f"security-master-official-sample-{inventory.inventory_id}.json").write_bytes(canonical_json(_mapping(inventory)))
    discrepancies = tuple(
        {
            "sample_id": record["sample_id"], "ts_code": record["ts_code"],
            "provider_values": record["provider_values"], "official_values": record["official_values"],
            "official_source_identity": record["official_source_identity"],
            "classification": "UNEXPLAINED_SEMANTIC_MISMATCH",
            "required_action": "REJECT_PENDING_PROVIDER_FIELD_SEMANTICS",
        }
        for record in inventory.records if record["official_evidence_status"] == "MISMATCH"
    )
    if discrepancies:
        body = {"schema_version": "SecurityMasterDiscrepancyAnalysisV1", "inventory_id": inventory.inventory_id, "records": discrepancies, "verified_at": AS_OF, "policy_version": "security-master-discrepancy-v1"}
        discrepancy_id = content_hash(body)
        (output / f"security-master-discrepancy-{discrepancy_id}.json").write_bytes(canonical_json({**body, "content_hash": discrepancy_id}))
        print(f"SECURITY_MASTER_DISCREPANCY={discrepancy_id} COUNT={len(discrepancies)} DISPOSITION=FAIL_CLOSED")
    print(f"SECURITY_MASTER_OFFICIAL_SAMPLE={inventory.inventory_id} TOTAL={inventory.total} VERIFIED={inventory.verified} MISMATCH={inventory.mismatch} UNRESOLVED={inventory.unresolved}")
    for record in inventory.records:
        if record["official_evidence_status"] != "VERIFIED":
            print(f"{record['sample_id']} {record['ts_code']} {record['sample_stratum']} {record['official_evidence_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
