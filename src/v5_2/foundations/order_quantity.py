from __future__ import annotations

from decimal import Decimal, ROUND_DOWN


RULE_VERSION = "v5.2-a-share-quantity-v1"


def board(code: str) -> str:
    normalized = str(code).zfill(6)
    if normalized.startswith(("688", "689")):
        return "STAR"
    if normalized.startswith(("4", "8", "92")):
        return "BSE"
    if normalized.startswith(("300", "301")):
        return "CHINEXT"
    return "MAIN"


def minimum_buy(code: str) -> int:
    return 200 if board(code) == "STAR" else 100


def valid_buy(code: str, shares: int) -> bool:
    if shares < minimum_buy(code):
        return False
    return shares % 100 == 0 if board(code) in {"MAIN", "CHINEXT"} else True


def valid_sell(code: str, shares: int, position_shares: int) -> bool:
    if shares <= 0 or shares > position_shares:
        return False
    return shares == position_shares or valid_buy(code, shares)


def floor_quantity(code: str, raw_shares: object) -> int:
    raw = int(Decimal(str(raw_shares)).to_integral_value(rounding=ROUND_DOWN))
    if board(code) in {"MAIN", "CHINEXT"}:
        raw = raw // 100 * 100
    return raw if raw >= minimum_buy(code) else 0
