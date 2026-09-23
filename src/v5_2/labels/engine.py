from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from v5_2.labels.calculation import (
    BarrierAmbiguityEvidenceV1, CorporateActionCoverageV1, LabelHorizonsV1, UnsafeLabelInput,
    build_economic_wealth_path, calculate_barrier, calculate_outcome_labels,
    quantize_label, resolve_label_horizons,
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
    observations: tuple[WindowObservationV1, ...] = ()
    value: None = None


def _affected(session: date, horizons: LabelHorizonsV1) -> int:
    for number, endpoint in ((1, horizons.h1), (3, horizons.h3), (5, horizons.h5)):
        if session <= endpoint:
            return number
    return 5


def validate_label_window(bundle, horizons: LabelHorizonsV1,
                          sessions: tuple[date, ...] | None = None) -> ValidatedLabelWindowV1 | UnsafeWindowV1:
    window = horizons.window_5d if sessions is None else sessions
    bars = {item.session: item for item in bundle.future_bars}
    statuses = {item.session: item for item in bundle.future_statuses}
    mappings = {(day, source): canonical for day, source, canonical in bundle.dated_identity_map}
    observations = []
    for session in window:
        if bundle.delisting_session is not None and bundle.delisting_session <= session:
            return UnsafeWindowV1(LabelReasonCode.DELISTING_IN_HORIZON, bundle.delisting_session,
                                  _affected(bundle.delisting_session, horizons), tuple(observations))
        status = statuses.get(session)
        if status is None:
            return UnsafeWindowV1(LabelReasonCode.STATUS_UNRESOLVED, session, _affected(session, horizons), tuple(observations))
        bar = bars.get(session)
        if bar is None:
            if status.is_suspended:
                observations.append(WindowObservationV1(session, None, status, False, True))
                continue
            return UnsafeWindowV1(LabelReasonCode.EXPECTED_BAR_MISSING, session, _affected(session, horizons), tuple(observations))
        resolved = bar.security_identity == bundle.canonical_security_identity or mappings.get((session, bar.security_identity)) == bundle.canonical_security_identity
        if not resolved:
            return UnsafeWindowV1(LabelReasonCode.IDENTITY_UNRESOLVED, session, _affected(session, horizons), tuple(observations))
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
        completed_sessions = tuple(day for day in horizons.window_5d if day <= bundle.latest_completed_session)
        safe = validate_label_window(bundle, horizons, completed_sessions)
        unsafe = safe if isinstance(safe, UnsafeWindowV1) else None
        observations = unsafe.observations if unsafe else safe.observations
        if bundle.reference_price is None and unsafe is None:
            unsafe = UnsafeWindowV1(LabelReasonCode.ANCHOR_BAR_MISSING, bundle.anchor_session, 1)
            observations = ()
        coverage = bundle.action_coverage if isinstance(bundle.action_coverage, CorporateActionCoverageV1) else CorporateActionCoverageV1.safe()
        supported = {"CASH_DIVIDEND", "BONUS_SHARE"}
        relevant_actions = tuple(item for item in bundle.corporate_actions
                                 if (item.effective_date or item.ex_date) in completed_sessions and not item.is_cancelled)
        unsupported = tuple(item for item in relevant_actions if item.action_type.value not in supported)
        if unsafe is None and unsupported:
            day = min(item.effective_date or item.ex_date for item in unsupported)
            unsafe = UnsafeWindowV1(LabelReasonCode.UNSUPPORTED_CORPORATE_ACTION, day, _affected(day, horizons))
            observations = tuple(item for item in observations if item.session < day)
        if unsafe is None and (not coverage.covered or coverage.quarantined or not coverage.revision_valid):
            reason = (LabelReasonCode.CORPORATE_ACTION_REVISION_INVALID if not coverage.revision_valid
                      else LabelReasonCode.CORPORATE_ACTION_QUARANTINE if coverage.quarantined
                      else LabelReasonCode.CORPORATE_ACTION_COVERAGE_GAP)
            unsafe = UnsafeWindowV1(reason, None, 1)
            observations = ()
        path = None
        try:
            if observations and bundle.reference_price is not None:
                path_sessions = tuple(item.session for item in observations)
                path = build_economic_wealth_path(
                    bundle.reference_price, path_sessions, tuple(bundle.future_bars),
                    tuple(bundle.corporate_actions), coverage,
                    tuple(item.session for item in observations if item.status.is_suspended),
                )
        except UnsafeLabelInput as error:
            unsafe = UnsafeWindowV1(error.reason, error.horizon, _affected(error.horizon, horizons) if error.horizon else 1)
            path = None
        endpoints = {"return_1d": horizons.h1, "return_3d": horizons.h3, "return_5d": horizons.h5,
                     "max_favorable_excursion_5d": horizons.h5, "max_adverse_excursion_5d": horizons.h5,
                     "hit_3pct_before_-2pct": horizons.h5, "hit_5pct_before_-3pct": horizons.h5}
        completed = {1: horizons.completed[0], 3: horizons.completed[1], 5: horizons.completed[2]}
        if unsafe is not None and unsafe.reason is LabelReasonCode.DELISTING_IN_HORIZON and completed[5]:
            unsafe = UnsafeWindowV1(unsafe.reason, unsafe.session, 1, unsafe.observations)
        value_paths = {}
        if completed[5] and path is not None:
            value_paths = {1: path, 3: path, 5: path}
        else:
            for horizon, endpoint in ((1, horizons.h1), (3, horizons.h3)):
                if not completed[horizon] or (unsafe is not None and horizon >= unsafe.first_affected_horizon):
                    continue
                prefix = tuple(item for item in observations if item.session <= endpoint)
                value_paths[horizon] = build_economic_wealth_path(
                    bundle.reference_price, tuple(item.session for item in prefix),
                    tuple(bundle.future_bars), tuple(bundle.corporate_actions), coverage,
                    tuple(item.session for item in prefix if item.status.is_suspended),
                )
        numeric = {}
        if 1 in value_paths:
            h1_path = value_paths[1]
            numeric["return_1d"] = quantize_label(h1_path.points[0].close_wealth / h1_path.reference_price - 1)
        if 3 in value_paths:
            h3_path = value_paths[3]
            numeric["return_3d"] = quantize_label(h3_path.points[2].close_wealth / h3_path.reference_price - 1)
        if 5 in value_paths:
            numeric.update(calculate_outcome_labels(value_paths[5]))
        barriers = ()
        ambiguity = False
        if completed[5] and unsafe is None and path is not None:
            items = []
            for upper, lower in ((Decimal(".03"), Decimal("-.02")), (Decimal(".05"), Decimal("-.03"))):
                try:
                    items.append(calculate_barrier(path, upper, lower))
                except UnsafeLabelInput as error:
                    if error.reason is not LabelReasonCode.BARRIER_PATH_AMBIGUOUS or error.horizon is None:
                        unsafe = UnsafeWindowV1(error.reason, error.horizon, 5)
                        break
                    ambiguity = True
                    items.append(BarrierAmbiguityEvidenceV1(None, error.horizon, None, error.horizon))
            barriers = tuple(items)
            if ambiguity:
                ambiguous_session = next(item.ambiguous_session for item in barriers
                                         if isinstance(item, BarrierAmbiguityEvidenceV1))
                unsafe = UnsafeWindowV1(LabelReasonCode.BARRIER_PATH_AMBIGUOUS, ambiguous_session, 1)
        values = []
        barrier_by_name = dict(zip(CORE_LABELS[-2:], barriers))
        for name in CORE_LABELS:
            horizon = 1 if name == "return_1d" else 3 if name == "return_3d" else 5
            if not completed[horizon]:
                values.append(LabelValueV1.create(name, LabelState.LABEL_PENDING, None, LabelReasonCode.HORIZON_NOT_COMPLETED, horizon_end_session=endpoints[name]))
            elif unsafe is not None and horizon >= unsafe.first_affected_horizon:
                values.append(LabelValueV1.create(name, LabelState.NOT_LABEL_SAFE, None, unsafe.reason,
                                                   horizon_end_session=endpoints[name]))
            else:
                value = barrier_by_name[name].boolean_value if name in barrier_by_name else numeric[name]
                value_path = value_paths[horizon]
                endpoint = endpoints[name]
                provenance_endpoint = horizons.h5 if completed[5] else endpoint
                available_times = [bundle.reference_price.available_at]
                available_times.extend(
                    item.available_at for item in (*bundle.future_bars, *bundle.future_statuses)
                    if item.session <= provenance_endpoint
                )
                available_times.extend(
                    item.available_at for item in relevant_actions
                    if (item.effective_date or item.ex_date) <= provenance_endpoint
                )
                values.append(LabelValueV1.create(
                    name, LabelState.LABEL_AVAILABLE, value,
                    horizon_end_session=endpoint, observed_at=max(available_times),
                    input_fact_ids=tuple(value_path.input_fact_ids),
                ))
        return LabelResultV1.create(bundle.canonical_security_identity, bundle.anchor_session, tuple(values), bundle.content_hash, barriers)
