from datetime import date
from types import SimpleNamespace

from v5_2.labels.calculation import LabelHorizonsV1
from v5_2.labels.contracts import LabelReasonCode
from v5_2.labels.engine import UnsafeWindowV1, validate_label_window


def horizons():
    days = tuple(date(2024, 1, x) for x in (3, 4, 5, 8, 9))
    return LabelHorizonsV1(days[0], days[2], days[4], days, (True, True, True))


def bundle(*, bars=(), statuses=(), identity_map=(), delisting_session=None):
    return SimpleNamespace(
        canonical_security_identity="000001.SZ", future_bars=bars, future_statuses=statuses,
        dated_identity_map=identity_map, delisting_session=delisting_session,
    )


def bar(day, identity="000001.SZ"):
    return SimpleNamespace(session=day, security_identity=identity, close=10, fact_id=f"bar-{day}")


def status(day, *, suspended=False, delisted=False):
    return SimpleNamespace(session=day, security_identity="000001.SZ", is_suspended=suspended, is_delisted=delisted, fact_id=f"status-{day}")


def test_normal_window_is_safe():
    hs = horizons()
    result = validate_label_window(bundle(bars=tuple(bar(day) for day in hs.window_5d), statuses=tuple(status(day) for day in hs.window_5d)), hs)
    assert len(result.observations) == 5 and all(item.intraday_trade for item in result.observations)


def test_full_day_suspension_carries_last_close_without_intraday_range():
    hs = horizons(); suspended = hs.window_5d[0]
    result = validate_label_window(bundle(bars=tuple(bar(day) for day in hs.window_5d[1:]), statuses=tuple(status(day, suspended=day == suspended) for day in hs.window_5d)), hs)
    point = result.observations[0]
    assert point.session == suspended and point.intraday_trade is False and point.carried is True


def test_unexplained_missing_or_resumption_without_bar_fails_closed():
    hs = horizons()
    result = validate_label_window(bundle(bars=tuple(bar(day) for day in hs.window_5d[1:]), statuses=tuple(status(day) for day in hs.window_5d)), hs)
    assert isinstance(result, UnsafeWindowV1)
    assert result.reason is LabelReasonCode.EXPECTED_BAR_MISSING


def test_identity_transition_requires_explicit_mapping():
    hs = horizons(); changed = bar(hs.h1, "001001.SZ")
    bars = (changed, *(bar(day) for day in hs.window_5d[1:]))
    unsafe = validate_label_window(bundle(bars=bars, statuses=tuple(status(day) for day in hs.window_5d)), hs)
    safe = validate_label_window(bundle(bars=bars, statuses=tuple(status(day) for day in hs.window_5d), identity_map=((hs.h1, "001001.SZ", "000001.SZ"),)), hs)
    assert unsafe.reason is LabelReasonCode.IDENTITY_UNRESOLVED
    assert len(safe.observations) == 5


def test_delisting_is_horizon_scoped_and_never_minus_one():
    hs = horizons()
    result = validate_label_window(bundle(bars=tuple(bar(day) for day in hs.window_5d), statuses=tuple(status(day) for day in hs.window_5d), delisting_session=hs.h3), hs)
    assert isinstance(result, UnsafeWindowV1)
    assert result.reason is LabelReasonCode.DELISTING_IN_HORIZON
    assert result.first_affected_horizon == 3 and result.value is None
