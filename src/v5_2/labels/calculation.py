from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1
from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.labels.contracts import LabelReasonCode, LabelReferencePrice


class IncompleteCalendarCoverage(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LabelHorizonsV1:
    h1: date
    h3: date
    h5: date
    window_5d: tuple[date, ...]
    completed: tuple[bool, bool, bool]


def resolve_label_horizons(anchor_session: date, approved_exchange_sessions: tuple[date, ...], latest_completed_session: date) -> LabelHorizonsV1:
    if len(set(approved_exchange_sessions)) != len(approved_exchange_sessions):
        raise IncompleteCalendarCoverage("DUPLICATE_APPROVED_SESSION")
    if tuple(sorted(approved_exchange_sessions)) != approved_exchange_sessions:
        raise IncompleteCalendarCoverage("NON_MONOTONIC_APPROVED_CALENDAR")
    if anchor_session not in approved_exchange_sessions:
        raise IncompleteCalendarCoverage("ANCHOR_SESSION_ABSENT")
    future = tuple(day for day in approved_exchange_sessions if day > anchor_session)
    if len(future) < 5:
        raise IncompleteCalendarCoverage("INSUFFICIENT_FUTURE_COVERAGE")
    horizons = (future[0], future[2], future[4])
    return LabelHorizonsV1(*horizons, future[:5], tuple(day <= latest_completed_session for day in horizons))


class UnsafeLabelInput(ValueError):
    def __init__(self, reason: LabelReasonCode, horizon: date | None = None):
        super().__init__(reason.value)
        self.reason = reason
        self.horizon = horizon


@dataclass(frozen=True, slots=True)
class CorporateActionCoverageV1:
    covered: bool = True
    quarantined: bool = False
    revision_valid: bool = True

    @classmethod
    def safe(cls):
        return cls()


@dataclass(frozen=True, slots=True)
class EconomicPathPointV1:
    session: date
    shares: Decimal
    cash: Decimal
    open_wealth: Decimal | None
    high_wealth: Decimal | None
    low_wealth: Decimal | None
    close_wealth: Decimal
    intraday_trade: bool
    input_fact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EconomicWealthPathV1:
    reference_price: Decimal
    points: tuple[EconomicPathPointV1, ...]
    input_fact_ids: tuple[str, ...]


def _coverage_guard(coverage: CorporateActionCoverageV1) -> None:
    if not coverage.revision_valid:
        raise UnsafeLabelInput(LabelReasonCode.CORPORATE_ACTION_REVISION_INVALID)
    if coverage.quarantined:
        raise UnsafeLabelInput(LabelReasonCode.CORPORATE_ACTION_QUARANTINE)
    if not coverage.covered:
        raise UnsafeLabelInput(LabelReasonCode.CORPORATE_ACTION_COVERAGE_GAP)


def build_economic_wealth_path(reference_price: LabelReferencePrice, sessions: tuple[date, ...],
                               bars: tuple[DailyBarFactV1, ...], actions: tuple[CorporateActionFactV1, ...],
                               action_coverage: CorporateActionCoverageV1) -> EconomicWealthPathV1:
    _coverage_guard(action_coverage)
    supported = {ActionType.CASH_DIVIDEND, ActionType.BONUS_SHARE}
    relevant = tuple(item for item in actions if (item.effective_date or item.ex_date) in sessions and not item.is_cancelled)
    if any(item.action_type not in supported for item in relevant):
        raise UnsafeLabelInput(LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION)
    by_day = {item.session: item for item in bars}
    shares, cash = Decimal("1"), Decimal("0")
    points = []
    used = []
    for session in sessions:
        todays = sorted((item for item in relevant if (item.effective_date or item.ex_date) == session), key=lambda x: (x.action_type.value, x.fact_id))
        pre_shares = shares
        for item in todays:
            if not item.verify(): raise UnsafeLabelInput(LabelReasonCode.CORPORATE_ACTION_REVISION_INVALID)
            if item.action_type is ActionType.CASH_DIVIDEND:
                cash += pre_shares * (item.cash_per_share or Decimal("0"))
            elif item.action_type is ActionType.BONUS_SHARE:
                shares *= Decimal("1") + (item.share_ratio or Decimal("0"))
            used.append(item.fact_id)
        bar = by_day.get(session)
        if bar is None or not bar.verify() or bar.price_basis != "UNADJUSTED_RAW":
            raise UnsafeLabelInput(LabelReasonCode.EXPECTED_BAR_MISSING, session)
        used.append(bar.fact_id)
        points.append(EconomicPathPointV1(
            session, shares, cash, cash + shares * bar.open, cash + shares * bar.high,
            cash + shares * bar.low, cash + shares * bar.close, True,
            tuple([bar.fact_id, *(item.fact_id for item in todays)]),
        ))
    return EconomicWealthPathV1(reference_price.price, tuple(points), tuple(used))


QUANT = Decimal("0.00000001")


def quantize_label(value: Decimal) -> Decimal:
    return value.quantize(QUANT, rounding=ROUND_HALF_EVEN)


def calculate_outcome_labels(path: EconomicWealthPathV1) -> dict[str, Decimal]:
    if len(path.points) != 5:
        raise ValueError("five exchange-session points are required")
    denominator = path.reference_price
    returns = {
        "return_1d": quantize_label(path.points[0].close_wealth / denominator - 1),
        "return_3d": quantize_label(path.points[2].close_wealth / denominator - 1),
        "return_5d": quantize_label(path.points[4].close_wealth / denominator - 1),
    }
    highs = tuple((point.high_wealth if point.intraday_trade else point.close_wealth) for point in path.points)
    lows = tuple((point.low_wealth if point.intraday_trade else point.close_wealth) for point in path.points)
    returns["max_favorable_excursion_5d"] = quantize_label(max((Decimal("0"), *(value / denominator - 1 for value in highs if value is not None))))
    returns["max_adverse_excursion_5d"] = quantize_label(min((Decimal("0"), *(value / denominator - 1 for value in lows if value is not None))))
    return returns
