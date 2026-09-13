from datetime import date, datetime, timedelta, timezone

import pytest

from v5_2.data.historical_status import HistoricalStatusRepositoryV1, StatusResolutionError


ZONE = timezone(timedelta(hours=8))


def test_effective_lifecycle_and_pit_visible_overrides_resolve_status():
    repository = HistoricalStatusRepositoryV1(
        lifecycles=(("OLD.SH", date(2010, 1, 1), date(2018, 6, 29)),),
        risk_warning_intervals=(("OLD.SH", date(2012, 1, 1), date(2012, 12, 31),
                                 datetime(2012, 1, 4, 16, 30, tzinfo=ZONE)),),
        full_day_suspensions=(("OLD.SH", date(2012, 6, 29),
                               datetime(2012, 6, 29, 16, 30, tzinfo=ZONE)),),
    )
    early = repository.resolve("OLD.SH", date(2012, 6, 29),
                               datetime(2012, 6, 29, 16, 30, tzinfo=ZONE))
    assert early == {"listed": True, "risk_warning": True, "suspended": True}
    assert repository.resolve("OLD.SH", date(2019, 1, 2),
                              datetime(2019, 1, 2, 16, 30, tzinfo=ZONE))["listed"] is False


def test_missing_lifecycle_and_future_knowledge_fail_closed():
    with pytest.raises(StatusResolutionError, match="lifecycle"):
        HistoricalStatusRepositoryV1(lifecycles=(), risk_warning_intervals=(),
                                     full_day_suspensions=()).resolve(
            "UNKNOWN.SH", date(2012, 6, 29), datetime(2012, 6, 29, 16, 30, tzinfo=ZONE))
    repository = HistoricalStatusRepositoryV1(
        lifecycles=(("A.SH", date(2010, 1, 1), None),),
        risk_warning_intervals=(("A.SH", date(2012, 1, 1), None,
                                 datetime(2012, 7, 2, 16, 30, tzinfo=ZONE)),),
        full_day_suspensions=())
    status = repository.resolve("A.SH", date(2012, 6, 29),
                                datetime(2012, 6, 29, 16, 30, tzinfo=ZONE))
    assert status["risk_warning"] is False
