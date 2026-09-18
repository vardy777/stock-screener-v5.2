from __future__ import annotations

from v5_2.labels.acceptance_v2_contracts import (
    CalculationEdgeFixtureV2,
    EvidenceClass,
    Phase2AAcceptanceArchitectureAmendmentV2,
)


SESSIONS = ("2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08")


def _fixture(name: str, highs: tuple[str, ...], lows: tuple[str, ...], closes: tuple[str, ...], expected: str) -> CalculationEdgeFixtureV2:
    return CalculationEdgeFixtureV2.create(
        name=name,
        evidence_class=EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE,
        reference_price="100",
        sessions=SESSIONS,
        highs=highs,
        lows=lows,
        closes=closes,
        expected_outcome=expected,
    )


def build_frozen_edge_fixtures(amendment: Phase2AAcceptanceArchitectureAmendmentV2) -> tuple[CalculationEdgeFixtureV2, ...]:
    if not amendment.verify():
        raise ValueError("invalid amendment")
    neutral_high = ("101",) * 5
    neutral_low = ("99",) * 5
    closes = ("101", "100", "102", "99", "103")
    return (
        _fixture("UPPER_FIRST", ("104", *neutral_high[1:]), neutral_low, closes, "UPPER_FIRST"),
        _fixture("LOWER_FIRST", neutral_high, ("97", *neutral_low[1:]), closes, "LOWER_FIRST"),
        _fixture("NEITHER", neutral_high, neutral_low, closes, "NEITHER"),
        _fixture("SAME_SESSION_BARRIER_AMBIGUITY", ("104", *neutral_high[1:]), ("97", *neutral_low[1:]), closes, "SAME_SESSION_BARRIER_AMBIGUITY"),
    )
