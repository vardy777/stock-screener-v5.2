from datetime import date
from decimal import Decimal

import pytest

from v5_2.labels.calculation import EconomicPathPointV1, EconomicWealthPathV1, UnsafeLabelInput, calculate_barrier
from v5_2.labels.contracts import BarrierOutcomeV1, LabelReasonCode


def p(day, high, low, trade=True):
    close = Decimal("10")
    return EconomicPathPointV1(date(2024, 1, day), Decimal("1"), Decimal("0"), close if trade else None, Decimal(high) if trade else None, Decimal(low) if trade else None, close, trade, ())


def path(*points):
    return EconomicWealthPathV1(Decimal("10"), tuple(points), ())


@pytest.mark.parametrize("points,outcome,value,session", [
    ((p(3, "10.4", "9.9"),), BarrierOutcomeV1.UPPER_FIRST, True, date(2024, 1, 3)),
    ((p(3, "10.1", "9.7"),), BarrierOutcomeV1.LOWER_FIRST, False, date(2024, 1, 3)),
    ((p(3, "10.1", "9.9"),), BarrierOutcomeV1.NEITHER, False, None),
])
def test_barrier_preserves_three_valued_outcome(points, outcome, value, session):
    result = calculate_barrier(path(*points), Decimal(".03"), Decimal("-.02"))
    assert (result.outcome, result.boolean_value, result.first_decisive_session) == (outcome, value, session)


def test_both_on_first_decisive_session_is_unsafe():
    with pytest.raises(UnsafeLabelInput) as error:
        calculate_barrier(path(p(3, "10.4", "9.7")), Decimal(".03"), Decimal("-.02"))
    assert error.value.reason is LabelReasonCode.BARRIER_PATH_AMBIGUOUS


def test_prior_decisive_session_ignores_later_double_hit():
    result = calculate_barrier(path(p(3, "10.4", "9.9"), p(4, "10.5", "9.5")), Decimal(".03"), Decimal("-.02"))
    assert result.outcome is BarrierOutcomeV1.UPPER_FIRST


def test_suspension_cannot_hit_barrier():
    result = calculate_barrier(path(p(3, "20", "1", False)), Decimal(".03"), Decimal("-.02"))
    assert result.outcome is BarrierOutcomeV1.NEITHER
