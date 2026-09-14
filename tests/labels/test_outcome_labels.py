from datetime import date
from decimal import Decimal

from v5_2.labels.calculation import EconomicPathPointV1, EconomicWealthPathV1, calculate_outcome_labels


def point(day, close, high, low, trade=True):
    return EconomicPathPointV1(date(2024, 1, day), Decimal("1"), Decimal("0"), Decimal(close) if trade else None, Decimal(high) if trade else None, Decimal(low) if trade else None, Decimal(close), trade, ())


def test_returns_use_exact_h1_h3_h5_and_quantize_half_even():
    path = EconomicWealthPathV1(Decimal("10"), (
        point(3, "11", "11", "9"), point(4, "10", "12", "8"), point(5, "9", "10", "8.5"),
        point(8, "10", "10", "10"), point(9, "10.00000005", "10.5", "9.5"),
    ), ())
    result = calculate_outcome_labels(path)
    assert result["return_1d"] == Decimal("0.10000000")
    assert result["return_3d"] == Decimal("-0.10000000")
    assert result["return_5d"] == Decimal("0.00000000")


def test_mfe_mae_use_future_economic_high_low_with_zero_bounds():
    path = EconomicWealthPathV1(Decimal("10"), (
        point(3, "10", "12", "9"), point(4, "10", "11", "8"), point(5, "10", "10", "10"),
        point(8, "10", "10", "10"), point(9, "10", "10", "10"),
    ), ())
    result = calculate_outcome_labels(path)
    assert result["max_favorable_excursion_5d"] == Decimal("0.20000000")
    assert result["max_adverse_excursion_5d"] == Decimal("-0.20000000")


def test_suspension_uses_carried_close_for_excursions_without_fabricated_range():
    path = EconomicWealthPathV1(Decimal("10"), (
        point(3, "11", "11", "9"), point(4, "11", "0", "0", False), point(5, "11", "11", "11"),
        point(8, "11", "11", "11"), point(9, "11", "11", "11"),
    ), ())
    result = calculate_outcome_labels(path)
    assert result["max_favorable_excursion_5d"] == Decimal("0.10000000")
