from __future__ import annotations

import pytest

from v5_2.data.real_audits.security_master_normalization import (
    SecurityMasterNormalizationError,
    SecurityMasterNormalizationPolicyV1,
)


def policy():
    return SecurityMasterNormalizationPolicyV1.create_default()


@pytest.mark.parametrize(
    ("row", "board"),
    [
        ({"ts_code": "600000.SH", "symbol": "600000", "name": "A", "market": "主板", "exchange": "SSE", "list_status": "L", "list_date": "19991110", "delist_date": None}, "SH_MAIN"),
        ({"ts_code": "688001.SH", "symbol": "688001", "name": "B", "market": "科创板", "exchange": "SSE", "list_status": "L", "list_date": "20190722", "delist_date": None}, "STAR"),
        ({"ts_code": "000001.SZ", "symbol": "000001", "name": "C", "market": "主板", "exchange": "SZSE", "list_status": "L", "list_date": "19910403", "delist_date": None}, "SZ_MAIN"),
        ({"ts_code": "300001.SZ", "symbol": "300001", "name": "D", "market": "创业板", "exchange": "SZSE", "list_status": "D", "list_date": "20091030", "delist_date": "20250101"}, "CHINEXT"),
    ],
)
def test_known_a_share_mapping_is_deterministic(row, board) -> None:
    normalized = policy().normalize(row)
    assert normalized["board"] == board
    assert normalized["security_type"] == "A_SHARE"
    assert normalized["is_a_share"] is True
    assert normalized["listing_status"] == row["list_status"]


@pytest.mark.parametrize(
    "change",
    [
        {"market": "未知板"},
        {"exchange": "BSE"},
        {"list_status": "X"},
        {"ts_code": "900901.SH", "symbol": "900901"},
        {"ts_code": "200001.SZ", "symbol": "200001"},
    ],
)
def test_unknown_or_non_a_share_input_fails_closed(change) -> None:
    row = {"ts_code": "600000.SH", "symbol": "600000", "name": "A", "market": "主板", "exchange": "SSE", "list_status": "L", "list_date": "19991110", "delist_date": None}
    row.update(change)
    with pytest.raises(SecurityMasterNormalizationError):
        policy().normalize(row)


def test_policy_is_versioned_and_content_addressed() -> None:
    first = policy()
    second = policy()
    assert first.policy_version == "security-master-normalization-v1"
    assert first.policy_id == first.content_hash == second.policy_id
    with pytest.raises(TypeError):
        first.board_mapping["anything"] = "SH_MAIN"  # type: ignore[index]
