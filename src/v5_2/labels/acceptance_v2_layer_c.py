from __future__ import annotations

from datetime import date
from decimal import Decimal
from dataclasses import dataclass

from v5_2.data.identity import content_hash

from v5_2.labels.calculation import (
    EconomicPathPointV1,
    EconomicWealthPathV1,
    UnsafeLabelInput,
    calculate_barrier,
    calculate_outcome_labels,
)
from v5_2.labels.acceptance_v2_contracts import (
    CalculationEdgeFixtureLedgerV2,
    CalculationEdgeFixtureV2,
    EdgeComparisonV2,
    EdgeResultV2,
    EvidenceClass,
    Phase2AAcceptanceArchitectureAmendmentV2,
    Phase2AAcceptanceArchitectureAmendmentV2_1,
    build_frozen_amendment_v2,
)
from v5_2.labels.independent_edge_reference import calculate_independent_edge_result


SESSIONS = ("2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08")
EDGE_SEMANTICS_V2_1 = (
    "UPPER_FIRST",
    "LOWER_FIRST",
    "NEITHER",
    "SAME_SESSION_BARRIER_AMBIGUITY",
)


@dataclass(frozen=True, slots=True)
class CalculationEdgeFixtureLedgerV2_1:
    amendment_id: str
    fixtures: tuple[CalculationEdgeFixtureV2, ...]
    comparisons: tuple[EdgeComparisonV2, ...]
    ledger_id: str
    content_hash: str

    @classmethod
    def create(cls, *, amendment_id: str, fixtures: tuple[CalculationEdgeFixtureV2, ...],
               comparisons: tuple[EdgeComparisonV2, ...]):
        body = {"amendment_id": amendment_id, "fixtures": fixtures, "comparisons": comparisons}
        digest = content_hash({"schema_version": cls.__name__, **body})
        return cls(**body, ledger_id=digest, content_hash=digest)

    def verify(self) -> bool:
        body = {"amendment_id": self.amendment_id, "fixtures": self.fixtures, "comparisons": self.comparisons}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.ledger_id == self.content_hash == digest and validate_edge_semantics_v2_1(self)


def validate_edge_semantics_v2_1(ledger: CalculationEdgeFixtureLedgerV2_1) -> bool:
    if tuple(item.name for item in ledger.fixtures) != EDGE_SEMANTICS_V2_1:
        return False
    if len(ledger.comparisons) != 4:
        return False
    for fixture, comparison in zip(ledger.fixtures, ledger.comparisons):
        if not fixture.verify() or fixture.evidence_class is not EvidenceClass.SYNTHETIC_CONTRACT_FIXTURE:
            return False
        if fixture.expected_outcome != fixture.name:
            return False
        if comparison.fixture_id != fixture.fixture_id:
            return False
        if comparison.disposition != "MATCH" or comparison.production != comparison.independent:
            return False
    return True


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


def _production_result(fixture: CalculationEdgeFixtureV2) -> EdgeResultV2:
    reference = Decimal(fixture.reference_price)
    points = tuple(EconomicPathPointV1(
        session=date.fromisoformat(session), shares=Decimal("1"), cash=Decimal("0"),
        open_wealth=close, high_wealth=high, low_wealth=low, close_wealth=close,
        intraday_trade=True, input_fact_ids=(),
    ) for session, high, low, close in zip(
        fixture.sessions,
        (Decimal(x) for x in fixture.highs),
        (Decimal(x) for x in fixture.lows),
        (Decimal(x) for x in fixture.closes),
    ))
    path = EconomicWealthPathV1(reference, points, ())
    labels = calculate_outcome_labels(path)
    try:
        barrier = calculate_barrier(path, Decimal("0.03"), Decimal("-0.02"))
        outcome = barrier.outcome.value
        decisive = barrier.first_decisive_session.isoformat() if barrier.first_decisive_session else ""
    except UnsafeLabelInput as error:
        outcome = "SAME_SESSION_BARRIER_AMBIGUITY"
        decisive = error.horizon.isoformat() if error.horizon else ""
    return EdgeResultV2(
        outcome=outcome, decisive_session=decisive,
        return_5d=format(labels["return_5d"], "f"),
        mfe_5d=format(labels["max_favorable_excursion_5d"], "f"),
        mae_5d=format(labels["max_adverse_excursion_5d"], "f"),
    )


def build_edge_fixture_ledger(amendment: Phase2AAcceptanceArchitectureAmendmentV2, fixtures: tuple[CalculationEdgeFixtureV2, ...]) -> CalculationEdgeFixtureLedgerV2:
    if fixtures != build_frozen_edge_fixtures(amendment):
        raise ValueError("frozen edge fixture identity mismatch")
    comparisons = []
    for fixture in fixtures:
        independent = calculate_independent_edge_result(fixture)
        production = _production_result(fixture)
        comparisons.append(EdgeComparisonV2(
            fixture_id=fixture.fixture_id, production=production, independent=independent,
            disposition="MATCH" if production == independent else "MISMATCH",
        ))
    return CalculationEdgeFixtureLedgerV2.create(
        amendment_id=amendment.artifact_id, fixtures=fixtures, comparisons=tuple(comparisons),
    )


def build_edge_fixture_ledger_v2_1(
    amendment: Phase2AAcceptanceArchitectureAmendmentV2_1,
) -> CalculationEdgeFixtureLedgerV2_1:
    if not amendment.verify():
        raise ValueError("invalid V2.1 amendment")
    fixtures = build_frozen_edge_fixtures(build_frozen_amendment_v2())
    previous = build_edge_fixture_ledger(build_frozen_amendment_v2(), fixtures)
    result = CalculationEdgeFixtureLedgerV2_1.create(
        amendment_id=amendment.artifact_id,
        fixtures=previous.fixtures,
        comparisons=previous.comparisons,
    )
    if not result.verify():
        raise ValueError("invalid V2.1 edge semantic coverage")
    return result
