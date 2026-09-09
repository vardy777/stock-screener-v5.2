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
from v5_2.data.real_audits.official_anchor_gaps import (  # noqa: E402
    OfficialAnchorAssertionV1, OfficialAnchorGapEntryV1, evaluate_official_anchor,
    verify_official_anchor_text,
)
from v5_2.data.real_audits.pinned_artifacts import load_pinned_json  # noqa: E402

CONTRACT_ID = "3a9efd2f1047d9ad0432a72202bf1b8e7f926d153c339106475c37a694b20917"
INVENTORY_ID = "cef91ec0a055f01ac2f0f82ec8e15ce75f4e000acd2123a70685fb25d1df3c9c"
GAP_ID = "5466d1c98a2c2dbae5219ebd3e62512c3d33d96ef12f07f4771c3d46440cb4b9"
PRIOR_SUPPLEMENT_ID = "806fb76ff4a4afe94c4e4c6382121d3685b04cee9487959c8bec8781d2caf733"
URL = "https://static.cninfo.com.cn/finalpage/2025-07-01/1224039754.PDF"
EXPECTED_DOCUMENT_SHA256 = "c5bac86324145bdbfb5f7d6e47671ea5f8b12a26d54125ee1bf472f02acad92c"

# Text extracted from the downloaded five-page PDF. It is retained because the semantic
# check must evaluate what this document says, rather than infer content from its URL.
RELEVANT_DOCUMENT_TEXT = """
证券代码：688053 证券简称：思科瑞 公告编号：2025-026
成都思科瑞微电子股份有限公司首次公开发行部分限售股上市流通公告
公司首次向社会公开发行人民币普通股（A股）2,500.00万股，
并于2022年7月8日在上海证券交易所科创板挂牌上市。
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
        raise RuntimeError("CNINFO-hosted document content changed; semantic verification aborted")
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
            "source_host": "static.cninfo.com.cn", "source_type": "CNINFO_HOSTED_ISSUER_DISCLOSURE",
            "document_title": "首次公开发行部分限售股上市流通公告",
            "document_publication_date": "20250701", "source_url": URL,
            "document_sha256": document_hash, "text_verification_id": verification.verification_id,
            "text_verification_reason": verification.reason, "resolution": resolution}
    body["content_hash"] = content_hash(body)
    output = governance / f"official-anchor-recovery-attempt-{body['content_hash']}.json"
    output.write_bytes(canonical_json(body))
    receipt = {"schema_version": "OfficialAnchorRecoveryReceiptV1", "artifact_id": body["content_hash"],
               "retrieved_at": acquired_at, "document_sha256": document_hash}
    receipt["content_hash"] = content_hash(receipt)
    (governance / f"official-anchor-recovery-receipt-{receipt['content_hash']}.json").write_bytes(canonical_json(receipt))
    if verification.supported:
        prior = load_pinned_json(governance / f"official-anchor-supplement-{PRIOR_SUPPLEMENT_ID}.json",
            schema_version="OfficialAnchorSupplementV1", identity_field="content_hash",
            expected_identity=PRIOR_SUPPLEMENT_ID)
        gap_entry = OfficialAnchorGapEntryV1(**gap)
        assertion = OfficialAnchorAssertionV1(
            candidate_hash=gap["candidate_hash"], security_identity="688053.SH", session="20220708",
            semantic="ACTUAL_FIRST_TRADABLE_SESSION", source_url=URL,
            document_title="首次公开发行部分限售股上市流通公告", publication_date="20250701",
            asserted_identity="688053.SH", asserted_effective_session="20220708",
        )
        anchor = evaluate_official_anchor(gap_entry, assertion, document)
        evidence = [dict(item) for item in prior["evidence"]]
        evidence = [({"candidate_hash": anchor.candidate_hash, "security_identity": anchor.security_identity,
                      "session": anchor.session, "semantic": anchor.semantic, "source_url": anchor.source_url,
                      "document_title": anchor.document_title, "publication_date": anchor.publication_date,
                      "document_sha256": anchor.document_sha256, "resolution": anchor.resolution,
                      "evidence_id": anchor.evidence_id}
                     if item["candidate_hash"] == gap["candidate_hash"] else item) for item in evidence]
        supplement = {"schema_version": "OfficialAnchorSupplementV1", "gap_inventory_id": GAP_ID,
                      "evidence": evidence, "recovery_artifact_id": body["content_hash"],
                      "supersedes_supplement_id": PRIOR_SUPPLEMENT_ID}
        supplement["content_hash"] = content_hash(supplement)
        (governance / f"official-anchor-supplement-{supplement['content_hash']}.json").write_bytes(
            canonical_json(supplement))
    print(json.dumps({"artifact_id": body["content_hash"], "document_sha256": document_hash,
                      "text_verification_id": verification.verification_id,
                      "resolution": resolution, "reason": verification.reason,
                      "supplement_id": supplement["content_hash"] if verification.supported else None}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
