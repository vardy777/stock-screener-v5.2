from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.official_anchor_gaps import (  # noqa: E402
    OfficialAnchorAssertionV1, OfficialAnchorGapEntryV1, evaluate_official_anchor,
)
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402

GAP_ID = "5466d1c98a2c2dbae5219ebd3e62512c3d33d96ef12f07f4771c3d46440cb4b9"

# Frozen before acquisition. Each assertion was manually checked for the exact security identity
# and actual listing/trading date or effective delisting/摘牌 date stated in the document.
ANCHORS = {
    ("300798.SZ", "20191122"): ("https://disc.static.szse.cn/disc/disk02/finalpage/2019-11-21/f1249d19-612a-4917-a203-86a99c111eea.PDF", "锦鸡股份首次公开发行股票并在创业板上市之上市公告书", "20191121"),
    ("300122.SZ", "20100928"): ("https://www.szse.cn/aboutus/sse/events/t20110119_497844.html", "2010年深交所大事记（智飞生物上市）", "20110119"),
    # The exact listing announcement is discoverable in third-party mirrors, but the bounded run
    # did not recover an exchange/CNINFO-hosted immutable copy. Keep this gap unavailable.
    ("688053.SH", "20220708"): (None, "思科瑞首次公开发行股票科创板上市公告书", "20220707"),
    ("002594.SZ", "20110630"): ("https://www.szse.cn/disclosure/notice/company/t20110628_508636.html", "关于比亚迪股份有限公司股票上市交易的公告", "20110628"),
    ("688247.SH", "20220825"): ("https://static.cninfo.com.cn/finalpage/2022-08-24/1214372485.PDF", "宣泰医药首次公开发行股票科创板上市公告书", "20220824"),
    ("601208.SH", "20110520"): ("https://static.cninfo.com.cn/finalpage/2022-12-08/1215294337.PDF", "东材科技公开发行可转换公司债券募集说明书（发行人上市日期）", "20221208"),
    ("002517.SZ", "20101207"): ("https://disc.static.szse.cn/download/disc/disk01/finalpage/2015-12-16/bfdd861a-af97-49f8-90ad-c6d2a86f0bb2.PDF", "恺英网络重大资产重组文件（公司上市日期）", "20151216"),
    ("301030.SZ", "20210722"): ("https://www.szse.cn/www/disclosure/notice/company/t20210721_587079.html", "关于仕净科技股票上市交易的公告", "20210721"),
    ("688202.SH", "20191105"): ("https://static.cninfo.com.cn/finalpage/2024-10-29/1221542961.PDF", "美迪西首次公开发行限售股上市流通公告（首次挂牌日期）", "20241029"),
    ("002826.SZ", "20161209"): ("https://disc.static.szse.cn/disc/disk01/finalpage/2016-12-08/f5334927-e4b1-4002-a5d0-3546b1fe7ce8.PDF", "易明医药首次公开发行股票上市公告书", "20161208"),
    ("002118.SZ", "20230804"): ("https://static.cninfo.com.cn/finalpage/2023-08-04/1217460135.PDF", "紫鑫药业关于股票终止上市暨摘牌的公告", "20230804"),
    ("002610.SZ", "20240812"): ("https://static.cninfo.com.cn/finalpage/2024-08-12/1220835141.PDF", "爱康科技关于股票终止上市暨摘牌的公告", "20240812"),
    ("000023.SZ", "20240902"): ("https://static.cninfo.com.cn/finalpage/2024-09-02/1221092726.PDF", "深天地关于公司股票终止上市暨摘牌的公告", "20240902"),
    ("688086.SH", "20230707"): ("https://static.cninfo.com.cn/finalpage/2023-07-01/1217182444.PDF", "紫晶存储关于公司股票终止上市暨摘牌的公告", "20230701"),
    ("002618.SZ", "20220622"): ("https://static.cninfo.com.cn/finalpage/2022-06-22/1213776275.PDF", "丹邦科技关于股票终止上市暨摘牌的公告", "20220622"),
    ("002147.SZ", "20220623"): ("https://static.cninfo.com.cn/finalpage/2022-06-23/1213791796.PDF", "新光圆成关于股票终止上市暨摘牌的公告", "20220623"),
    ("300089.SZ", "20230713"): ("https://static.cninfo.com.cn/finalpage/2023-07-13/1217284301.PDF", "文化长城关于股票终止上市暨摘牌的公告", "20230713"),
    ("600069.SH", "20200827"): ("https://www.sse.com.cn/disclosure/announcement/listing/stock/c/c_20200820_79043908.shtml", "关于退市银鸽股票终止上市的公告", "20200820"),
    ("300023.SZ", "20220629"): ("https://static.cninfo.com.cn/finalpage/2022-06-29/1213852783.PDF", "宝德股份关于股票终止上市暨摘牌的公告", "20220629"),
}


def main() -> int:
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    frozen = load_pinned_json(governance / f"official-anchor-gap-inventory-{GAP_ID}.json",
        schema_version="OfficialAnchorGapInventoryV1", identity_field="content_hash", expected_identity=GAP_ID)
    if set(ANCHORS) != {(item["security_identity"], item["session"]) for item in frozen["entries"]}:
        raise RuntimeError("frozen anchor assertion inventory does not exactly match gap inventory")
    raw_dir = ROOT / "data" / "phase_1b2a" / "raw" / "official_anchors"
    raw_dir.mkdir(parents=True, exist_ok=True)
    evidence, receipts = [], []
    for raw_gap in frozen["entries"]:
        gap = OfficialAnchorGapEntryV1(**raw_gap)
        url, title, published = ANCHORS[(gap.security_identity, gap.session)]
        source_url = url or "https://star.sse.com.cn/disclosure/listannouncement/"
        assertion = OfficialAnchorAssertionV1(gap.candidate_hash, gap.security_identity, gap.session,
            gap.semantic, source_url, title, published, gap.security_identity, gap.session)
        document = None
        error = None
        acquired_at = datetime.now(timezone.utc)
        try:
            if url is None:
                raise FileNotFoundError("exact exchange/CNINFO-hosted document was not recovered in bounded search")
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 V5.2 evidence audit"})
            document = urlopen(request, timeout=30).read()
            if len(document) < 128:
                raise ValueError("official response is unexpectedly short")
        except Exception as exc:  # recorded fail-closed; never promoted to MATCH
            error = f"{type(exc).__name__}: {exc}"
            document = None
        item = evaluate_official_anchor(gap, assertion, document)
        evidence.append(item)
        if document:
            (raw_dir / f"{item.document_sha256}.bin").write_bytes(document)
        receipt = {"schema_version": "OfficialAnchorAcquisitionReceiptV1",
                   "evidence_id": item.evidence_id, "acquired_at": acquired_at,
                   "transport_error": error}
        receipt["content_hash"] = content_hash(receipt)
        receipts.append(receipt)
    body = {"schema_version": "OfficialAnchorSupplementV1", "gap_inventory_id": GAP_ID,
            "evidence": tuple(asdict(item) for item in evidence)}
    body["content_hash"] = content_hash(body)
    (governance / f"official-anchor-supplement-{body['content_hash']}.json").write_bytes(canonical_json(body))
    receipt_body = {"schema_version": "OfficialAnchorAcquisitionReceiptBundleV1",
                    "supplement_id": body["content_hash"], "receipts": tuple(receipts)}
    receipt_body["content_hash"] = content_hash(receipt_body)
    (governance / f"official-anchor-receipts-{receipt_body['content_hash']}.json").write_bytes(canonical_json(receipt_body))
    counts = {key: sum(item.resolution == key for item in evidence)
              for key in ("MATCH", "OFFICIAL_MISMATCH", "OFFICIAL_ANCHOR_UNAVAILABLE")}
    print(json.dumps({"gap_inventory_id": GAP_ID, "supplement_id": body["content_hash"],
                      "counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
