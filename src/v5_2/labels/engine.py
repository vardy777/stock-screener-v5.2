from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from v5_2.labels.calculation import LabelHorizonsV1
from v5_2.labels.contracts import LabelReasonCode


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
