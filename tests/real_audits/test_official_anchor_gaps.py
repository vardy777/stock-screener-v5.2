import pytest

from v5_2.data.real_audits.official_anchor_gaps import (
    OfficialAnchorAssertionV1,
    build_official_anchor_gap_inventory,
    evaluate_official_anchor,
    merge_official_anchor_supplement,
    verify_official_anchor_text,
)


def sample(candidate_hash="c", semantic="ACTUAL_FIRST_TRADABLE_SESSION"):
    return {"candidate_hash": candidate_hash, "security_identity": "600001.SH", "session": "20100104",
            "semantic": semantic, "provider_value": "20100104", "provider_evidence_ids": ["provider"]}


def observation(candidate_hash="c", resolution="INDEPENDENT_EVIDENCE_UNAVAILABLE"):
    return {"candidate_hash": candidate_hash, "resolution": resolution,
            "independent_value": [{"date": "2010-01-04", "tradestatus": "1"}],
            "source_document_hash": "daily-hash"}


def test_gap_inventory_binds_frozen_candidate_to_existing_daily_evidence() -> None:
    inventory = build_official_anchor_gap_inventory("contract", "inventory", (sample(),), (observation(),),
                                                    expected_count=None)
    assert inventory.counts == (("ACTUAL_FIRST_TRADABLE_SESSION", 1),)
    assert inventory.entries[0].required_official_anchor_type == "ACTUAL_LISTING_TRADING_DATE"
    assert inventory.entries[0].current_evidence_ids == ("daily-hash", "provider")
    assert inventory.content_hash


def test_gap_inventory_rejects_non_anchor_semantics_and_missing_observations() -> None:
    with pytest.raises(ValueError, match="official-anchor semantic"):
        build_official_anchor_gap_inventory("c", "i", (sample(semantic="ST_EXIT"),), (observation(),), expected_count=None)
    with pytest.raises(ValueError, match="observation"):
        build_official_anchor_gap_inventory("c", "i", (sample(),), (), expected_count=None)


def assertion(**changes):
    values = {"candidate_hash": "c", "security_identity": "600001.SH", "session": "20100104",
              "semantic": "ACTUAL_FIRST_TRADABLE_SESSION", "source_url": "https://example.test/a.pdf",
              "document_title": "listing announcement", "publication_date": "20100103",
              "asserted_identity": "600001.SH", "asserted_effective_session": "20100104"}
    values.update(changes)
    return OfficialAnchorAssertionV1(**values)


def test_official_anchor_requires_exact_frozen_binding_and_downloaded_content() -> None:
    gap = build_official_anchor_gap_inventory("contract", "inventory", (sample(),), (observation(),),
                                              expected_count=None).entries[0]
    result = evaluate_official_anchor(gap, assertion(), b"%PDF official immutable bytes")
    assert result.resolution == "MATCH"
    assert result.document_sha256
    assert result.candidate_hash == gap.candidate_hash
    assert result.evidence_id

    mismatch = evaluate_official_anchor(gap, assertion(asserted_effective_session="20100105"), b"%PDF bytes")
    assert mismatch.resolution == "OFFICIAL_MISMATCH"
    unavailable = evaluate_official_anchor(gap, assertion(), None)
    assert unavailable.resolution == "OFFICIAL_ANCHOR_UNAVAILABLE"


def test_supplement_merge_preserves_frozen_candidates_and_fails_closed() -> None:
    original = ({"candidate_hash": "c", "resolution": "INDEPENDENT_EVIDENCE_UNAVAILABLE",
                 "source_document_hash": "daily", "independent_value": ("daily",)},)
    gap = build_official_anchor_gap_inventory("contract", "inventory", (sample(),), original,
                                              expected_count=None).entries[0]
    matched = evaluate_official_anchor(gap, assertion(), b"%PDF bytes")
    merged = merge_official_anchor_supplement(original, (matched,))
    assert merged[0]["candidate_hash"] == "c"
    assert merged[0]["resolution"] == "MATCH"
    assert merged[0]["official_anchor_evidence_id"] == matched.evidence_id

    with pytest.raises(ValueError, match="exactly"):
        merge_official_anchor_supplement(original, ())


def test_semantic_verification_requires_identity_and_effective_session_in_document_text() -> None:
    supporting = "证券代码：688053 公司股票于2022年7月8日在上海证券交易所科创板挂牌上市"
    result = verify_official_anchor_text(
        document_sha256="a" * 64,
        extracted_text=supporting,
        security_identity="688053.SH",
        asserted_session="20220708",
        semantic="ACTUAL_FIRST_TRADABLE_SESSION",
        extractor_identity="pdf-text-extractor-v1",
    )
    assert result.supported is True
    assert result.verification_id

    reference_only = (
        "证券代码：688053。具体情况详见2022年7月7日披露于上海证券交易所网站的"
        "《成都思科瑞微电子股份有限公司首次公开发行股票科创板上市公告书》。"
    )
    unsupported = verify_official_anchor_text(
        document_sha256="b" * 64,
        extracted_text=reference_only,
        security_identity="688053.SH",
        asserted_session="20220708",
        semantic="ACTUAL_FIRST_TRADABLE_SESSION",
        extractor_identity="pdf-text-extractor-v1",
    )
    assert unsupported.supported is False
    assert unsupported.reason == "document text does not state the asserted effective session"


def test_listing_date_must_be_tied_to_the_listing_semantic() -> None:
    unrelated_date = (
        "证券代码：688053。公司于2022年7月8日发布其他公告；"
        "公司股票于2025年7月8日在上海证券交易所科创板挂牌上市。"
    )
    result = verify_official_anchor_text(
        document_sha256="c" * 64,
        extracted_text=unrelated_date,
        security_identity="688053.SH",
        asserted_session="20220708",
        semantic="ACTUAL_FIRST_TRADABLE_SESSION",
        extractor_identity="pdf-text-extractor-v1",
    )
    assert result.supported is False
    assert result.reason == "document text does not tie the asserted session to the listing semantic"
