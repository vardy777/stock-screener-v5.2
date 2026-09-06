from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite


CHINA_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


class ContractViolation(ValueError):
    """Raised when an immutable V5.2 contract is violated."""


def strict_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ContractViolation(f"{field}: strict boolean required")
    return value


def strict_int(value: object, field: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise ContractViolation(f"{field}: strict integer required")
    if minimum is not None and value < minimum:
        raise ContractViolation(f"{field}: out of range")
    return value


def strict_number(value: object, field: str) -> float:
    if type(value) not in {int, float}:
        raise ContractViolation(f"{field}: strict number required")
    result = float(value)
    if not isfinite(result):
        raise ContractViolation(f"{field}: finite number required")
    return result


def strict_str(value: object, field: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise ContractViolation(f"{field}: strict string required")
    if not allow_empty and not value:
        raise ContractViolation(f"{field}: non-empty string required")
    return value


def require_aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractViolation(f"{field}: timezone-aware datetime required")
    return value
