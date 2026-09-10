from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.corporate_action_official_validation import (  # noqa: E402
    resolve_official_candidates,
    validate_official_text,
)


INVENTORY_ID = "90354c25bb7529048a2a391ba06e8e4cfb5daf732f9b6abcca94189fa13023c5"
RUNTIME = ROOT / "data" / "phase_1b2c"
CN = timezone(timedelta(hours=8), "Asia/Shanghai")


def _request(url: str, *, data: bytes | None = None) -> bytes:
    return urlopen(Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"}), timeout=30).read()


def _write_immutable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError("immutable official evidence collision")
    if not path.exists():
        path.write_bytes(data)


def _cached_evidence(sample_id: str) -> list[dict]:
    found: dict[str, dict] = {}
    for path in sorted((RUNTIME / "governance").glob("cross-source-*.json")):
        artifact = json.loads(path.read_text(encoding="utf-8"))
        if artifact.get("inventory_id") != INVENTORY_ID:
            continue
        for entry in artifact.get("entries", ()):
            if entry.get("sample_id") != sample_id:
                continue
            for evidence in entry.get("evidence", ()):
                sha = evidence.get("document_sha256")
                if sha and (RUNTIME / "official" / f"{sha}.pdf").is_file():
                    found[sha] = dict(evidence)
    return [found[key] for key in sorted(found)]


def main() -> int:
    inventory_path = RUNTIME / "governance" / f"sample-inventory-{INVENTORY_ID}.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    stocks = json.loads(_request("https://www.cninfo.com.cn/new/data/szse_stock.json"))["stockList"]
    orgs = {item["code"]: item["orgId"] for item in stocks}
    ledger = []
    for sample in inventory["samples"]:
        code = sample["security_identity"].split(".")[0]
        day = sample["provider_fields"]["imp_ann_date"]
        org_id = orgs.get(code)
        if not org_id:
            ledger.append({"sample_id": sample["sample_id"], "disposition": "UNAVAILABLE", "reason": "CNINFO security organization identity missing", "evidence": ()})
            continue
        cached = _cached_evidence(sample["sample_id"])
        announcements = [{
            "announcementTitle": item["title"],
            "announcementTime": item.get("announcement_time"),
            "adjunctUrl": item["url"].removeprefix("https://static.cninfo.com.cn/"),
            "cached_sha256": item["document_sha256"],
        } for item in cached]
        if not announcements:
            parsed = datetime.strptime(day, "%Y%m%d").date()
            start, end = parsed.strftime("%Y-%m-%d"), parsed.strftime("%Y-%m-%d")
            query = urlencode({
                "pageNum": 1, "pageSize": 100, "column": "sse" if sample["exchange"] == "SH" else "szse",
                "tabName": "fulltext", "plate": "sh" if sample["exchange"] == "SH" else "sz",
                "stock": f"{code},{org_id}", "searchkey": "", "secid": "", "category": "",
                "trade": "", "seDate": f"{start}~{end}", "sortName": "", "sortType": "", "isHLtitle": "true",
            }).encode()
            try:
                response = json.loads(_request("https://www.cninfo.com.cn/new/hisAnnouncement/query", data=query))
                announcements = response.get("announcements") or ()
            except Exception:
                ledger.append({"sample_id": sample["sample_id"], "disposition": "UNAVAILABLE", "reason": "CNINFO query failed", "evidence": ()})
                continue
        candidates = []
        for announcement in announcements:
            title = str(announcement.get("announcementTitle") or "").replace("<em>", "").replace("</em>", "")
            if "实施公告" not in title and "分红派息公告" not in title:
                continue
            url = "https://static.cninfo.com.cn/" + announcement["adjunctUrl"]
            try:
                cached_sha = announcement.get("cached_sha256")
                pdf = ((RUNTIME / "official" / f"{cached_sha}.pdf").read_bytes()
                       if cached_sha else _request(url))
                sha = hashlib.sha256(pdf).hexdigest()
                pdf_path = RUNTIME / "official" / f"{sha}.pdf"
                _write_immutable(pdf_path, pdf)
                with pdfplumber.open(pdf_path) as document:
                    text = "\n".join(page.extract_text() or "" for page in document.pages)
                text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                fields = sample["provider_fields"]
                disposition = validate_official_text(
                    security_code=code, announcement_date=day,
                    record_date=str(fields.get("record_date") or ""), ex_date=str(fields.get("ex_date") or ""),
                    cash_per_share=Decimal(str(fields.get("cash_div_tax") or 0)),
                    bonus_per_share=Decimal(str(fields.get("stk_bo_rate") or 0)),
                    title=title, text=text,
                )
                candidates.append({
                    "title": title, "url": url, "announcement_time": announcement.get("announcementTime"),
                    "document_sha256": sha, "text_sha256": text_hash, "disposition": disposition,
                })
            except Exception:
                candidates.append({"title": title, "url": url, "disposition": "UNAVAILABLE", "reason": "download or PDF extraction failed"})
        final = resolve_official_candidates(candidates)
        ledger.append({"sample_id": sample["sample_id"], "security_identity": sample["security_identity"],
                       "announcement_date": day, "disposition": final, "evidence": tuple(candidates)})
    body = {"schema_version": "CorporateActionCrossSourceLedgerV1", "inventory_id": INVENTORY_ID,
            "entries": tuple(ledger), "source": "CNINFO_OFFICIAL_HOSTED_ISSUER_DISCLOSURE"}
    ledger_id = content_hash(body)
    artifact = {"ledger_id": ledger_id, "content_hash": ledger_id, **body}
    _write_immutable(RUNTIME / "governance" / f"cross-source-{ledger_id}.json", canonical_json(artifact))
    counts = {kind: sum(item["disposition"] == kind for item in ledger) for kind in ("MATCH", "MISMATCH", "UNAVAILABLE", "UNRESOLVED")}
    print(f"LEDGER_ID={ledger_id} TOTAL={len(ledger)} " + " ".join(f"{key}={value}" for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
