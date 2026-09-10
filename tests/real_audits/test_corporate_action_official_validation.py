from decimal import Decimal

from v5_2.data.real_audits.corporate_action_official_validation import (
    resolve_official_candidates,
    validate_official_text,
)


def test_cash_dividend_matches_mechanical_official_terms():
    result = validate_official_text(
        security_code="000333", announcement_date="20210526", record_date="20210601",
        ex_date="20210602", cash_per_share=Decimal("1.600053"), bonus_per_share=Decimal("0"),
        title="2020年年度利润分配实施公告（更新后）",
        text="证券代码：000333 股权登记日为2021年6月1日，除权除息日为2021年6月2日。每10股派发现金红利16.000530元（含税）。",
    )
    assert result == "MATCH"


def test_cash_and_bonus_must_both_match_and_missing_value_is_unresolved():
    mismatch = validate_official_text(
        security_code="600276", announcement_date="20100310", record_date="20100316",
        ex_date="20100317", cash_per_share=Decimal("0.1"), bonus_per_share=Decimal("0.2"),
        title="利润分配实施公告",
        text="证券代码 600276 股权登记日2010年3月16日，除权除息日2010年3月17日，每10股派1元，送1股。",
    )
    unavailable = validate_official_text(
        security_code="600276", announcement_date="20100310", record_date="20100316",
        ex_date="20100317", cash_per_share=Decimal("0.1"), bonus_per_share=Decimal("0.2"),
        title="利润分配实施公告", text="证券代码 600276",
    )
    assert mismatch == "MISMATCH"
    assert unavailable == "UNRESOLVED"


def test_wrong_identity_or_dates_are_mismatch_not_unavailable():
    result = validate_official_text(
        security_code="000333", announcement_date="20210526", record_date="20210601",
        ex_date="20210602", cash_per_share=Decimal("1.6"), bonus_per_share=Decimal("0"),
        title="利润分配实施公告",
        text="证券代码 000001 股权登记日2021年6月1日，除权除息日2021年6月2日，每10股派16元。",
    )
    assert result == "MISMATCH"


def test_sse_per_share_terms_and_slash_dates_match():
    result = validate_official_text(
        security_code="600276", announcement_date="20190321", record_date="20190327",
        ex_date="20190328", cash_per_share=Decimal("0.22"), bonus_per_share=Decimal("0.2"),
        title="2018年年度权益分派实施公告",
        text="证券代码：600276 股权登记日 2019/3/27 除权除息日 2019/3/28 每股现金红利0.22元 每股派送红股0.2股",
    )
    assert result == "MATCH"


def test_per_ten_terms_match_when_bonus_precedes_cash():
    result = validate_official_text(
        security_code="000651", announcement_date="20100706", record_date="20100712",
        ex_date="20100713", cash_per_share=Decimal("0.5"), bonus_per_share=Decimal("0.5"),
        title="2009年度权益分派实施公告",
        text="证券代码：000651 股权登记日为2010年7月12日，除权除息日为2010年7月13日。每10股送红股5股，派5.00元人民币现金。",
    )
    assert result == "MATCH"


def test_cancelled_implementation_announcement_is_not_current_match():
    result = validate_official_text(
        security_code="000333", announcement_date="20210526", record_date="20210601",
        ex_date="20210602", cash_per_share=Decimal("1.6"), bonus_per_share=Decimal("0"),
        title="2020年年度利润分配实施公告（已取消）",
        text="证券代码：000333 股权登记日为2021年6月1日，除权除息日为2021年6月2日。每10股派16元。",
    )
    assert result == "RETRACTED"


def test_official_dividend_distribution_title_is_an_implementation_notice():
    result = validate_official_text(
        security_code="601318", announcement_date="20120920", record_date="20120925",
        ex_date="20120926", cash_per_share=Decimal("0.15"), bonus_per_share=Decimal("0"),
        title="2012年中期分红派息公告",
        text="证券代码：601318 扣税前每股派发现金红利人民币0.15元 股权登记日：2012年9月25日 除息日：2012年9月26日",
    )
    assert result == "MATCH"


def test_only_current_implementation_document_controls_final_disposition():
    candidates = (
        {"title": "利润分配实施公告（已取消）", "disposition": "RETRACTED"},
        {"title": "关于利润分配实施公告的更正公告", "disposition": "MISMATCH"},
        {"title": "利润分配实施公告（更新后）", "disposition": "MATCH"},
    )
    assert resolve_official_candidates(candidates) == "MATCH"


def test_current_official_mismatch_cannot_be_hidden_by_retracted_match():
    candidates = (
        {"title": "利润分配实施公告（已取消）", "disposition": "MATCH"},
        {"title": "利润分配实施公告（更新后）", "disposition": "MISMATCH"},
    )
    assert resolve_official_candidates(candidates) == "MISMATCH"
