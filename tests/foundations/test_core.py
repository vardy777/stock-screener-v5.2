from datetime import datetime

import pytest

from v5_2.foundations.core import (
    CHINA_TZ,
    ContractViolation,
    require_aware,
    strict_bool,
    strict_int,
    strict_number,
    strict_str,
)


def test_strict_validators_reject_bool_as_number_and_naive_time():
    assert strict_bool(True, "enabled") is True
    assert strict_int(3, "count", minimum=1) == 3
    assert strict_number(1.5, "price") == 1.5
    assert strict_str("600000", "symbol") == "600000"
    with pytest.raises(ContractViolation):
        strict_int(True, "count")
    with pytest.raises(ContractViolation):
        strict_number(False, "price")
    with pytest.raises(ContractViolation):
        require_aware(datetime(2026, 9, 6), "known_at")
    aware = datetime(2026, 9, 6, 15, 1, tzinfo=CHINA_TZ)
    assert require_aware(aware, "known_at") == aware
