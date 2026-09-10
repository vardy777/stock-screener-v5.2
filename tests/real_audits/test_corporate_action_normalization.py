from datetime import date, datetime, timedelta, timezone

import pytest

from v5_2.data.corporate_action_facts import ActionType
from v5_2.data.real_audits.corporate_action_availability import CorporateActionAvailabilityPolicyV1
from v5_2.data.real_audits.corporate_action_normalization import (
    CorporateActionNormalizationError,
    normalize_dividend_rows,
)


CN = timezone(timedelta(hours=8), "Asia/Shanghai")
POLICY = CorporateActionAvailabilityPolicyV1(
    approved_sessions=(date(2024, 6, 3), date(2024, 6, 4), date(2024, 6, 10), date(2024, 6, 11))
)


def test_normalizer_emits_distinct_cash_and_bonus_facts_with_date_only_fallback():
    facts = normalize_dividend_rows(({
        "ts_code": "600000.SH", "end_date": "20231231", "ann_date": "20240603",
        "div_proc": "实施", "cash_div_tax": "0.3", "stk_div": "0.2",
        "ex_date": "20240610", "imp_ann_date": "20240603",
    },), source_version_identity="schema-v1", policy=POLICY)
    assert tuple(f.action_type for f in facts) == (ActionType.BONUS_SHARE, ActionType.CASH_DIVIDEND)
    assert all(f.available_at == datetime(2024, 6, 4, 16, 30, tzinfo=CN) for f in facts)


def test_normalizer_rejects_nonimplemented_unknown_or_effective_only_rows():
    base = {"ts_code": "600000.SH", "ann_date": "20240603", "div_proc": "实施", "cash_div_tax": "0.3", "stk_div": "0", "ex_date": "20240610"}
    for change in ({"div_proc": "预案"}, {"ts_code": ""}, {"ann_date": ""}):
        with pytest.raises(CorporateActionNormalizationError):
            normalize_dividend_rows(({**base, **change},), source_version_identity="schema-v1", policy=POLICY)
