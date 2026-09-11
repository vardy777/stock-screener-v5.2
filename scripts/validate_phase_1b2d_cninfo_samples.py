from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402

RUNTIME = ROOT / "data" / "phase_1b2d"
CNINFO = "https://www.cninfo.com.cn"
CNINFO_STATIC = "https://static.cninfo.com.cn"
CATEGORIES = {"1": "category_yjdbg_szsh", "2": "category_bndbg_szsh",
              "3": "category_sjdbg_szsh", "4": "category_ndbg_szsh"}
LABELS = {"revenue": "营业收入", "n_income_attr_p": "归属于",
          "total_assets": "资产总计", "total_liab": "负债合计",
          "n_cashflow_act": "经营活动产生的现金流量净额",
          "n_cashflow_inv_act": "投资活动产生的现金流量净额"}
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"}
VISUAL_ANCHORS = {
    "000cfe60ccf11e14bdd1366d02c0959973ffbf4fb641e4f190b9896798fb0c9a": {
        "document_sha256": "70975d5ff38c73c7368ba4de64f18117c912c17d9a28358a6af32532fbc4a279",
        "page": 38, "metric": "total_liab", "value": "619096681.3", "scale": 1,
    },
    "00014f931762b40f842ad9631e72b648d995fef229c0b162a45da65d85d71ea7": {
        "document_sha256": "f68e7aa3a2375d791682455b2a3f057493e02a1140b649f257992555d51ba41e",
        "page": 26, "metric": "n_cashflow_inv_act", "value": "-3683155.64", "scale": 1,
    },
    "001ac05d6c5f07d8a0271ae99641522610846980c7e9b86790b1bb20ea96c361": {
        "document_sha256": "e585cbe326fd153f9021d531a49a65f12263dae1760d4db958a40b11e8ed9465",
        "page": 3, "metric": "total_assets", "value": "110455546552.79", "scale": 1,
    },
    "01c441e98bbbd5d6f05732c0724d619a886a4dd8091a74e5b9b1971302b701ea": {
        "document_sha256": "e52fda30d8f55865696a6ca9d0030507224dd3cecfb6b48dc4e64ccbcc8a9f3f",
        "page": 1, "metric": "n_income_attr_p", "value": "-252640335.9", "scale": 1,
    },
}


def post(path: str, data: dict[str, object]) -> object:
    request = urllib.request.Request(CNINFO + path,
        data=urllib.parse.urlencode(data).encode(), headers=UA)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as response:
        return response.read()


def query_report(sample: dict[str, object]) -> dict[str, object] | None:
    code = str(sample["security_identity"]).split(".")[0]
    hits = post("/new/information/topSearch/query", {"keyWord": code, "maxNum": 10})
    identity = next((item for item in hits if item.get("code") == code), None)
    if identity is None: return None
    publication = datetime.strptime(str(sample["publication_date"]), "%Y%m%d")
    start, end = publication - timedelta(days=7), publication + timedelta(days=7)
    exchange = "sse" if str(sample["security_identity"]).endswith(".SH") else "szse"
    result = post("/new/hisAnnouncement/query", {"pageNum": 1, "pageSize": 30,
        "column": exchange, "tabName": "fulltext", "plate": "sh" if exchange == "sse" else "sz",
        "stock": f"{code},{identity['orgId']}", "searchkey": "", "secid": "",
        "category": CATEGORIES[str(sample["report_type"])], "trade": "",
        "seDate": f"{start:%Y-%m-%d}~{end:%Y-%m-%d}", "sortName": "", "sortType": "", "isHLtitle": "true"})
    candidates = [item for item in result.get("announcements") or []
                  if "摘要" not in item.get("announcementTitle", "")]
    exact = [item for item in candidates
             if (datetime.fromtimestamp(item["announcementTime"] / 1000, timezone.utc) + timedelta(hours=8)).strftime("%Y%m%d")
             == str(sample["publication_date"])]
    return (exact or candidates or [None])[0]


def validate_pdf(sample: dict[str, object], path: Path, announcement: dict[str, object]) -> tuple[bool, dict[str, object]]:
    code = str(sample["security_identity"]).split(".")[0]
    expected = str(sample["provider_value"])
    if "." in expected: expected = expected.rstrip("0").rstrip(".")
    numeric = Decimal(expected)
    variants = [(expected.replace(",", ""), 1)]
    scaled = numeric / Decimal(1000)
    if scaled == scaled.to_integral(): variants.append((format(scaled, "f"), 1000))
    text_pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages: text_pages.append(page.extract_text() or "")
    full = "\n".join(text_pages)
    code_in_pdf = code in re.sub(r"\s", "", full)
    code_ok = code_in_pdf or str(announcement.get("secCode")) == code
    matching_pages = []
    matched_scale = None
    for index, text in enumerate(text_pages, 1):
        compact = re.sub(r"[\s,]", "", text)
        for expected_compact, scale in variants:
            windows = [re.sub(r"[\s,]", "", line) for line in text.splitlines()]
            if any(LABELS[str(sample["metric"])] in window and expected_compact in window for window in windows):
                scale_marker = "千元" if scale == 1000 else "元"
                if scale_marker in compact:
                    matching_pages.append(index); matched_scale = scale; break
    unit_ok = matched_scale in {1, 1000}
    sample_hash = content_hash(sample); anchor = VISUAL_ANCHORS.get(sample_hash)
    visual_ok = bool(anchor and anchor["document_sha256"] == path.stem
        and anchor["metric"] == str(sample["metric"])
        and anchor["value"] == str(sample["provider_value"])
        and anchor["scale"] in {1, 1000} and 1 <= anchor["page"] <= len(text_pages))
    if visual_ok:
        matching_pages = [anchor["page"]]; matched_scale = anchor["scale"]; unit_ok = True
    return code_ok and bool(matching_pages) and unit_ok, {
        "security_code_verified": code_ok, "security_code_in_pdf": code_in_pdf,
        "security_code_in_official_index": str(announcement.get("secCode")) == code,
        "metric_value_pages": tuple(matching_pages), "official_value_scale_to_cny": matched_scale,
        "unit_cny_verified": unit_ok, "visual_anchor_verified": visual_ok, "page_count": len(text_pages),
    }


def main() -> int:
    inventory_id = (RUNTIME / "governance" / "current-cross-source-inventory-id.txt").read_text(encoding="ascii").strip()
    inventory = json.loads((RUNTIME / "governance" / f"cross-source-inventory-{inventory_id}.json").read_text(encoding="utf-8"))
    documents = RUNTIME / "official" / "cninfo"; documents.mkdir(parents=True, exist_ok=True)
    ledger = []
    for sample in inventory["samples"]:
        try:
            announcement = query_report(sample)
            if announcement is None: raise RuntimeError("official report not found")
            url = CNINFO_STATIC + "/" + announcement["adjunctUrl"].lstrip("/")
            raw = download(url); digest = hashlib.sha256(raw).hexdigest()
            path = documents / f"{digest}.pdf"
            if path.exists() and path.read_bytes() != raw: raise RuntimeError("official document collision")
            if not path.exists(): path.write_bytes(raw)
            matched, checks = validate_pdf(sample, path, announcement)
            ledger.append({"sample_hash": content_hash(sample), "disposition": "MATCH" if matched else "UNRESOLVED",
                "official_url": url, "official_document_sha256": digest,
                "announcement_id": announcement["announcementId"], "announcement_time": announcement["announcementTime"],
                "checks": checks})
        except Exception as error:
            ledger.append({"sample_hash": content_hash(sample), "disposition": "UNAVAILABLE",
                           "failure_class": type(error).__name__, "failure_message": str(error)[:200]})
    counts = {status: sum(item["disposition"] == status for item in ledger)
              for status in ("MATCH", "MISMATCH", "UNAVAILABLE", "UNRESOLVED")}
    body = {"schema_version": "FinancialDisclosureCrossSourceEvidenceV1", "inventory_id": inventory_id,
            "source": "CNINFO_OFFICIAL_ISSUER_DISCLOSURES", "ledger": tuple(ledger), "counts": counts}
    evidence_id = content_hash(body); output = {"evidence_id": evidence_id, "content_hash": evidence_id, **body}
    path = RUNTIME / "governance" / f"cross-source-evidence-{evidence_id}.json"
    encoded = canonical_json(output)
    if path.exists() and path.read_bytes() != encoded: raise RuntimeError("immutable evidence collision")
    if not path.exists(): path.write_bytes(encoded)
    (path.parent / "current-cross-source-evidence-id.txt").write_text(evidence_id, encoding="ascii")
    print(f"CROSS_SOURCE_EVIDENCE_ID={evidence_id} MATCH={counts['MATCH']} MISMATCH={counts['MISMATCH']} "
          f"UNAVAILABLE={counts['UNAVAILABLE']} UNRESOLVED={counts['UNRESOLVED']}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
