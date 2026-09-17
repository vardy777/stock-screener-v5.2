"""Independent Phase 2A arithmetic.

This module intentionally does not import the production engine or calculation
helpers.  It consumes only the frozen bundle contract and immutable fact types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN

from v5_2.data.identity import content_hash
from v5_2.labels.contracts import CORE_LABELS, LabelInputBundleV1


QUANT = Decimal("0.00000001")


def _q(value: Decimal) -> Decimal:
    return value.quantize(QUANT, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class IndependentEconomicStepV1:
    session: date
    shares: str
    cash: str
    open_wealth: str | None
    high_wealth: str | None
    low_wealth: str | None
    close_wealth: str
    intraday_trade: bool
    input_fact_ids: tuple[str, ...]
    action_steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndependentBarrierTruthV1:
    label_name: str
    outcome: str | None
    decisive_session: date | None
    boolean_value: bool | None
    ambiguous_session: date | None = None


@dataclass(frozen=True, slots=True)
class IndependentReferenceResultV1:
    slot: int
    security_identity: str
    anchor_session: date
    bundle_id: str
    lineage_digest: str
    horizons: tuple[date, ...]
    reference_price: str | None
    reference_fact_id: str | None
    input_fact_ids: tuple[str, ...]
    economic_steps: tuple[IndependentEconomicStepV1, ...]
    unrounded_values: tuple[tuple[str, str], ...]
    result_summary: tuple[tuple[str, str, str, str], ...]
    barriers: tuple[IndependentBarrierTruthV1, ...]
    method_version: str
    reference_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in (
            "slot", "security_identity", "anchor_session", "bundle_id",
            "lineage_digest", "horizons", "reference_price", "reference_fact_id",
            "input_fact_ids", "economic_steps", "unrounded_values",
            "result_summary", "barriers", "method_version",
        )}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.reference_id == self.content_hash == digest


def _terminal_summary(state: str, reason: str):
    return tuple((name, state, "None", reason) for name in CORE_LABELS)


def _finish(*, slot, bundle, horizons, reference_price, reference_fact_id,
            input_fact_ids=(), economic_steps=(), unrounded_values=(), result_summary,
            barriers=()) -> IndependentReferenceResultV1:
    body = {
        "slot": slot, "security_identity": bundle.canonical_security_identity,
        "anchor_session": bundle.anchor_session, "bundle_id": bundle.content_hash,
        "lineage_digest": content_hash(tuple(item.content_hash for item in bundle.domain_lineage)),
        "horizons": tuple(horizons), "reference_price": reference_price,
        "reference_fact_id": reference_fact_id,
        "input_fact_ids": tuple(sorted(set(input_fact_ids))),
        "economic_steps": tuple(economic_steps),
        "unrounded_values": tuple(unrounded_values),
        "result_summary": tuple(result_summary), "barriers": tuple(barriers),
        "method_version": "phase2a-independent-full-v1",
    }
    digest = content_hash({"schema_version": "IndependentReferenceResultV1", **body})
    return IndependentReferenceResultV1(**body, reference_id=digest, content_hash=digest)


def calculate_independent_reference(slot: int, bundle: LabelInputBundleV1) -> IndependentReferenceResultV1:
    sessions = tuple(day for day in bundle.approved_exchange_sessions if day > bundle.anchor_session)[:5]
    horizons = (sessions[0], sessions[2], sessions[4]) if len(sessions) == 5 else ()
    reference = bundle.reference_price
    reference_value = str(reference.price) if reference else None
    reference_fact = reference.daily_bar_fact_id if reference else None
    if bundle.delisting_session is not None and sessions and bundle.delisting_session <= sessions[-1]:
        return _finish(slot=slot, bundle=bundle, horizons=horizons,
                       reference_price=reference_value, reference_fact_id=reference_fact,
                       result_summary=_terminal_summary("NOT_LABEL_SAFE", "DELISTING_IN_HORIZON"))
    if reference is None:
        return _finish(slot=slot, bundle=bundle, horizons=horizons,
                       reference_price=None, reference_fact_id=None,
                       result_summary=_terminal_summary("NOT_LABEL_SAFE", "ANCHOR_BAR_MISSING"))
    completed = tuple(day <= bundle.latest_completed_session for day in horizons)
    if not any(completed):
        return _finish(slot=slot, bundle=bundle, horizons=horizons,
                       reference_price=reference_value, reference_fact_id=reference_fact,
                       input_fact_ids=(reference_fact,),
                       result_summary=_terminal_summary("LABEL_PENDING", "HORIZON_NOT_COMPLETED"))
    bars = {item.session: item for item in bundle.future_bars}
    statuses = {item.session: item for item in bundle.future_statuses}
    shares, cash = Decimal("1"), Decimal("0")
    previous = reference.price
    steps = []
    used = [reference_fact]
    for day in sessions:
        status = statuses.get(day)
        if status is None:
            return _finish(slot=slot, bundle=bundle, horizons=horizons,
                           reference_price=reference_value, reference_fact_id=reference_fact,
                           input_fact_ids=used, economic_steps=steps,
                           result_summary=_terminal_summary("NOT_LABEL_SAFE", "STATUS_UNRESOLVED"))
        todays = tuple(sorted(
            (item for item in bundle.corporate_actions
             if (item.effective_date or item.ex_date) == day and not item.is_cancelled),
            key=lambda item: (item.action_type.value, item.fact_id),
        ))
        pre_shares = shares
        action_steps = []
        for item in todays:
            if item.action_type.value == "CASH_DIVIDEND":
                delta = pre_shares * (item.cash_per_share or Decimal("0"))
                cash += delta
                action_steps.append(f"CASH_DIVIDEND:{item.fact_id}:{delta}")
            elif item.action_type.value == "BONUS_SHARE":
                shares *= Decimal("1") + (item.share_ratio or Decimal("0"))
                action_steps.append(f"BONUS_SHARE:{item.fact_id}:{shares}")
            else:
                return _finish(slot=slot, bundle=bundle, horizons=horizons,
                               reference_price=reference_value, reference_fact_id=reference_fact,
                               input_fact_ids=used, economic_steps=steps,
                               result_summary=_terminal_summary("NOT_LABEL_SAFE", "UNSUPPORTED_CORPORATE_ACTION"))
            used.append(item.fact_id)
        bar = bars.get(day)
        if bar is None:
            if not status.is_suspended:
                return _finish(slot=slot, bundle=bundle, horizons=horizons,
                               reference_price=reference_value, reference_fact_id=reference_fact,
                               input_fact_ids=used, economic_steps=steps,
                               result_summary=_terminal_summary("NOT_LABEL_SAFE", "EXPECTED_BAR_MISSING"))
            steps.append(IndependentEconomicStepV1(
                day, str(shares), str(cash), None, None, None, str(previous), False,
                tuple(item.fact_id for item in todays), tuple(action_steps),
            ))
            continue
        high = cash + shares * bar.high
        low = cash + shares * bar.low
        close = cash + shares * bar.close
        open_wealth = cash + shares * bar.open
        used.append(bar.fact_id)
        steps.append(IndependentEconomicStepV1(
            day, str(shares), str(cash), str(open_wealth), str(high), str(low),
            str(close), True, (bar.fact_id, *(item.fact_id for item in todays)),
            tuple(action_steps),
        ))
        previous = close
    denominator = reference.price
    closes = tuple(Decimal(item.close_wealth) for item in steps)
    highs = tuple(Decimal(item.high_wealth) for item in steps if item.high_wealth is not None)
    lows = tuple(Decimal(item.low_wealth) for item in steps if item.low_wealth is not None)
    raw = {
        "return_1d": closes[0] / denominator - 1,
        "return_3d": closes[2] / denominator - 1,
        "return_5d": closes[4] / denominator - 1,
        "max_favorable_excursion_5d": max((Decimal("0"), *(value / denominator - 1 for value in highs))),
        "max_adverse_excursion_5d": min((Decimal("0"), *(value / denominator - 1 for value in lows))),
    }
    barriers = []
    for name, upper, lower in (
        ("hit_3pct_before_-2pct", Decimal(".03"), Decimal("-.02")),
        ("hit_5pct_before_-3pct", Decimal(".05"), Decimal("-.03")),
    ):
        outcome, decisive, boolean, ambiguous = "NEITHER", None, False, None
        for item in steps:
            if not item.intraday_trade:
                continue
            up = Decimal(item.high_wealth) / denominator - 1 >= upper
            down = Decimal(item.low_wealth) / denominator - 1 <= lower
            if up and down:
                outcome, decisive, boolean, ambiguous = None, item.session, None, item.session
                break
            if up or down:
                outcome, decisive, boolean = ("UPPER_FIRST", item.session, True) if up else ("LOWER_FIRST", item.session, False)
                break
        barriers.append(IndependentBarrierTruthV1(name, outcome, decisive, boolean, ambiguous))
    if any(item.ambiguous_session is not None for item in barriers):
        return _finish(slot=slot, bundle=bundle, horizons=horizons,
                       reference_price=reference_value, reference_fact_id=reference_fact,
                       input_fact_ids=used, economic_steps=steps,
                       unrounded_values=tuple((name, str(value)) for name, value in raw.items()),
                       result_summary=_terminal_summary("NOT_LABEL_SAFE", "BARRIER_PATH_AMBIGUOUS"),
                       barriers=barriers)
    rounded = tuple(_q(raw[name]) for name in CORE_LABELS[:5])
    values = (*rounded, *(item.boolean_value for item in barriers))
    summary = tuple((name, "LABEL_AVAILABLE", str(value), "") for name, value in zip(CORE_LABELS, values))
    return _finish(slot=slot, bundle=bundle, horizons=horizons,
                   reference_price=reference_value, reference_fact_id=reference_fact,
                   input_fact_ids=used, economic_steps=steps,
                   unrounded_values=tuple((name, str(value)) for name, value in raw.items()),
                   result_summary=summary, barriers=barriers)
