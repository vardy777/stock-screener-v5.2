from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.official_anchor_gaps import verify_official_anchor_text  # noqa: E402
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402

CONTRACT_ID = "3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917"
INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
GAP_ID = "5466d1c98a2c2dbae5219ebd3e62512c3d33d96ef12f07f4771c3d46440cb4b9"
URL = "https://star.sse.com.cn/disclosure/listedinfo/announcement/c/new/2023-04-10/688053_20230410_KLOY.pdf"
EXPECTED_DOCUMENT_SHA256 = "2b5cd22ab948ab5c284f9cf378b1f3312f0c34d795cae61976f8d68f70314a66"

# Text extracted from the downloaded four-page PDF. It is retained because the semantic
# check must evaluate what this document says, rather than infer content from its URL.
RELEVANT_DOCUMENT_TEXT = """
证券代码：688053 证券简称：思科瑞 公告编号：2023-023
成都思科瑞微电子股份有限公司关于使用部分超募资金永久性补充流动资金的公告
上述募集资金已全部到位，并经中汇会计师事务所（特殊普通合伙）审验，
于2022年7月5日出具《验资报告》（中汇会验[2022]5892号）。
具体情况详见2022年7月7日披露于上海证券交易所网站的
《成都思科瑞微电子股份有限公司首次公开发行股票科创板上市公告书》。
""".strip()


def main() -> int:
    governance = ROOT / "data" / "phase_1b2a" / "governance"
    gap_inventory = load_pinned_json(governance / f"official-anchor-gap-inventory-{GAP_ID}.json",
        schema_version="OfficialAnchorGapInventoryV1", identity_field="content_hash", expected_identity=GAP_ID)
    gap = next(item for item in gap_inventory["entries"]
               if item["security_identity"] == "688053.SH" and item["session"] == "20220708")
    acquired_at = datetime.now(timezone.utc)
    document = urlopen(Request(URL, headers={"User-Agent": "Mozilla/5.0 V5.2 evidence audit"}), timeout=60).read()
    document_hash = sha256(document).hexdigest()
    if document_hash != EXPECTED_DOCUMENT_SHA256:
        raise RuntimeError("SSE-hosted document content changed; semantic verification aborted")
    raw_dir = ROOT / "data" / "phase_1b2a" / "raw" / "official_anchors"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{document_hash}.bin").write_bytes(document)
    verification = verify_official_anchor_text(
        document_sha256=document_hash, extracted_text=RELEVANT_DOCUMENT_TEXT,
        security_identity="688053.SH", asserted_session="20220708",
        semantic="ACTUAL_FIRST_TRADABLE_SESSION", extractor_identity="verified-pdf-text-v1",
    )
    resolution = "MATCH" if verification.supported else "OFFICIAL_ANCHOR_UNAVAILABLE"
    body = {"schema_version": "OfficialAnchorRecoveryAttemptV1", "contract_id": CONTRACT_ID,
            "inventory_id": INVENTORY_ID, "gap_inventory_id": GAP_ID,
            "candidate_hash": gap["candidate_hash"], "security_identity": "688053.SH",
            "semantic": "ACTUAL_FIRST_TRADABLE_SESSION", "asserted_session": "20220708",
            "source_host": "star.sse.com.cn", "source_type": "SSE_HOSTED_ISSUER_DISCLOSURE",
            "document_title": "关于使用部分超募资金永久性补充流动资金的公告",
            "document_publication_date": "20230410", "source_url": URL,
            "document_sha256": document_hash, "text_verification_id": verification.verification_id,
            "text_verification_reason": verification.reason, "resolution": resolution}
    body["content_hash"] = content_hash(body)
    output = governance / f"official-anchor-recovery-attempt-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    receipt = {"schema_version": "OfficialAnchorRecoveryReceiptV1", "artifact_id": body["content_hash"],
               "retrieved_at": acquired_at, "document_sha256": document_hash}
    receipt["content_hash"] = content_hash(receipt)
    (governance / f"official-anchor-recovery-receipt-{receipt['content_hash']}.json").write_bytes(canonical_json(receipt))
    print(json.dumps({"artifact_id": body["content_hash"], "document_sha256": document_hash,
                      "text_verification_id": verification.verification_id,
                      "resolution": resolution, "reason": verification.reason}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
