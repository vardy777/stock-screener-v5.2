from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from v5_2.labels.calculation import (
    CorporateActionCoverageV1, LabelHorizonsV1, UnsafeLabelInput,
    build_economic_wealth_path, calculate_barrier, calculate_outcome_labels,
    resolve_label_horizons,
)
from v5_2.labels.contracts import (
    CORE_LABELS, LabelInputBundleV1, LabelReasonCode, LabelResultV1,
    LabelState, LabelValueV1,
)


@dataclass(frozen=True, slots=True)
class WindowObservationV1:
    session: date
    bar: object | None
    status: object
    intraday_trade: bool
    carried: bool


@dataclass(frozen=True, slots=True)
class ValidatedLabelWindowV1:
    observations: tuple[WindowObservationV1, ...]


@dataclass(frozen=True, slots=True)
class UnsafeWindowV1:
    reason: LabelReasonCode
    session: date | None
    first_affected_horizon: int
    value: None = None


def _affected(session: date, horizons: LabelHorizonsV1) -> int:
    for number, endpoint in ((1, horizons.h1), (3, horizons.h3), (5, horizons.h5)):
        if session <= endpoint:
            return number
    return 5


def validate_label_window(bundle, horizons: LabelHorizonsV1) -> ValidatedLabelWindowV1 | UnsafeWindowV1:
    if bundle.delisting_session is not None and bundle.delisting_session <= horizons.h5:
        return UnsafeWindowV1(LabelReasonCode.DELISTING_IN_HORIZON, bundle.delisting_session, _affected(bundle.delisting_session, horizons))
    bars = {item.session: item for item in bundle.future_bars}
    statuses = {item.session: item for item in bundle.future_statuses}
    mappings = {(day, source): canonical for day, source, canonical in bundle.dated_identity_map}
    observations = []
    for session in horizons.window_5d:
        status = statuses.get(session)
        if status is None:
            return UnsafeWindowV1(LabelReasonCode.STATUS_UNRESOLVED, session, _affected(session, horizons))
        bar = bars.get(session)
        if bar is None:
            if status.is_suspended:
                observations.append(WindowObservationV1(session, None, status, False, True))
                continue
            return UnsafeWindowV1(LabelReasonCode.EXPECTED_BAR_MISSING, session, _affected(session, horizons))
        resolved = bar.security_identity == bundle.canonical_security_identity or mappings.get((session, bar.security_identity)) == bundle.canonical_security_identity
        if not resolved:
            return UnsafeWindowV1(LabelReasonCode.IDENTITY_UNRESOLVED, session, _affected(session, horizons))
        observations.append(WindowObservationV1(session, bar, status, True, False))
    return ValidatedLabelWindowV1(tuple(observations))


def _state_values(bundle: LabelInputBundleV1, state: LabelState, reason: LabelReasonCode) -> LabelResultV1:
    values = tuple(LabelValueV1.create(name, state, None, reason) for name in CORE_LABELS)
    return LabelResultV1.create(bundle.canonical_security_identity, bundle.anchor_session, values, bundle.content_hash)


class ReferenceLabelEngine:
    def evaluate(self, bundle: LabelInputBundleV1) -> LabelResultV1:
        if not bundle.verify():
            return _state_values(bundle, LabelState.NOT_LABEL_SAFE, LabelReasonCode.INPUT_LINEAGE_INVALID)
        if not bundle.anchor_boundary.research_eligible:
            return _state_values(bundle, LabelState.NOT_LABEL_SAFE, LabelReasonCode.ANCHOR_NOT_RESEARCH_ELIGIBLE)
        try:
            horizons = resolve_label_horizons(bundle.anchor_session, bundle.approved_exchange_sessions, bundle.latest_completed_session)
        except ValueError:
            return _state_values(bundle, LabelState.NOT_LABEL_SAFE, LabelReasonCode.INPUT_LINEAGE_INVALID)
        if not any(horizons.completed):
            return _state_values(bundle, LabelState.LABEL_PENDING, LabelReasonCode.HORIZON_NOT_COMPLETED)
        safe = validate_label_window(bundle, horizons)
        if isinstance(safe, UnsafeWindowV1):
            values = []
            for name in CORE_LABELS:
                needed = 1 if name == "return_1d" else 3 if name == "return_3d" else 5
                if needed < safe.first_affected_horizon:
                    values.append(LabelValueV1.create(name, LabelState.NOT_LABEL_SAFE, None, safe.reason))
                else:
                    values.append(LabelValueV1.create(name, LabelState.NOT_LABEL_SAFE, None, safe.reason))
            return LabelResultV1.create(bundle.canonical_security_identity, bundle.anchor_session, tuple(values), bundle.content_hash)
        if bundle.reference_price is None:
            return _state_values(bundle, LabelState.NOT_LABEL_SAFE, LabelReasonCode.ANCHOR_BAR_MISSING)
        coverage = bundle.action_coverage if isinstance(bundle.action_coverage, CorporateActionCoverageV1) else CorporateActionCoverageV1.safe()
        try:
            path = build_economic_wealth_path(
                bundle.reference_price, horizons.window_5d, tuple(bundle.future_bars),
                tuple(bundle.corporate_actions), coverage,
                tuple(item.session for item in bundle.future_statuses if item.is_suspended),
            )
            numeric = calculate_outcome_labels(path)
            barriers = (
                calculate_barrier(path, Decimal(".03"), Decimal("-.02")),
                calculate_barrier(path, Decimal(".05"), Decimal("-.03")),
            )
        except UnsafeLabelInput as error:
            return _state_values(bundle, LabelState.NOT_LABEL_SAFE, error.reason)
        endpoints = {"return_1d": horizons.h1, "return_3d": horizons.h3, "return_5d": horizons.h5,
                     "max_favorable_excursion_5d": horizons.h5, "max_adverse_excursion_5d": horizons.h5,
                     "hit_3pct_before_-2pct": horizons.h5, "hit_5pct_before_-3pct": horizons.h5}
        completed = {1: horizons.completed[0], 3: horizons.completed[1], 5: horizons.completed[2]}
        values = []
        barrier_by_name = dict(zip(CORE_LABELS[-2:], barriers))
        fact_ids = tuple(path.input_fact_ids)
        available_times = [bundle.reference_price.available_at]
        available_times.extend(item.available_at for item in (*bundle.future_bars, *bundle.future_statuses, *bundle.corporate_actions) if hasattr(item, "available_at"))
        observed = max(available_times)
        for name in CORE_LABELS:
            horizon = 1 if name == "return_1d" else 3 if name == "return_3d" else 5
            if not completed[horizon]:
                values.append(LabelValueV1.create(name, LabelState.LABEL_PENDING, None, LabelReasonCode.HORIZON_NOT_COMPLETED, horizon_end_session=endpoints[name]))
            else:
                value = barrier_by_name[name].boolean_value if name in barrier_by_name else numeric[name]
                values.append(LabelValueV1.create(name, LabelState.LABEL_AVAILABLE, value, horizon_end_session=endpoints[name], observed_at=observed, input_fact_ids=fact_ids))
        return LabelResultV1.create(bundle.canonical_security_identity, bundle.anchor_session, tuple(values), bundle.content_hash, barriers)
