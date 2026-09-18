from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

from v5_2.labels.acceptance_v2_contracts import CalculationEdgeFixtureV2, EdgeComparisonV2, EdgeResultV2


Q = Decimal("0.00000001")


def _q(value: Decimal) -> str:
    return format(value.quantize(Q, rounding=ROUND_HALF_EVEN), "f")


def calculate_independent_edge_result(fixture: CalculationEdgeFixtureV2) -> EdgeResultV2:
    if not fixture.verify() or len(fixture.sessions) != 5:
        raise ValueError("invalid edge fixture")
    reference = Decimal(fixture.reference_price)
    highs = tuple(Decimal(x) for x in fixture.highs)
    lows = tuple(Decimal(x) for x in fixture.lows)
    closes = tuple(Decimal(x) for x in fixture.closes)
    outcome, decisive = "NEITHER", ""
    for session, high, low in zip(fixture.sessions, highs, lows):
        upper = high / reference - 1 >= Decimal("0.03")
        lower = low / reference - 1 <= Decimal("-0.02")
        if upper and lower:
            outcome, decisive = "SAME_SESSION_BARRIER_AMBIGUITY", session
            break
        if upper:
            outcome, decisive = "UPPER_FIRST", session
            break
        if lower:
            outcome, decisive = "LOWER_FIRST", session
            break
    return EdgeResultV2(
        outcome=outcome, decisive_session=decisive,
        return_5d=_q(closes[-1] / reference - 1),
        mfe_5d=_q(max(Decimal("0"), *(value / reference - 1 for value in highs))),
        mae_5d=_q(min(Decimal("0"), *(value / reference - 1 for value in lows))),
    )


def compare_edge_results(independent: EdgeResultV2, production: EdgeResultV2, fixture_id: str = "a" * 64) -> EdgeComparisonV2:
    return EdgeComparisonV2(
        fixture_id=fixture_id, production=production, independent=independent,
        disposition="MATCH" if production == independent else "MISMATCH",
    )
