from __future__ import annotations

from types import MappingProxyType

from v5_2.providers.contracts import ProviderRequestV1


SOURCE = "datahubco_tushare_proxy"
POLICY = "datahub-phase-1b1-request-v1"
PAGE_SIZE = 5000


def _request(dataset_kind: str, endpoint: str, parameters: dict[str, object], fields: tuple[str, ...]):
    return ProviderRequestV1.create(
        source_name=SOURCE,
        dataset_kind=dataset_kind,
        endpoint=endpoint,
        parameters=parameters,
        requested_fields=fields,
        page_size=PAGE_SIZE,
        request_policy_version=POLICY,
    )


def phase_1b1_requests():
    calendar_fields = ("exchange", "cal_date", "is_open", "pretrade_date")
    calendars = tuple(
        _request(
            "trade_calendar",
            "trade-cal",
            {
                "exchange": exchange,
                "start_date": "20100101",
                "end_date": "20251231",
                "fields": ",".join(calendar_fields),
            },
            calendar_fields,
        )
        for exchange in ("SSE", "SZSE")
    )
    master_fields = (
        "ts_code", "symbol", "name", "market", "exchange", "list_status",
        "list_date", "delist_date",
    )
    masters = tuple(
        _request(
            "security_master",
            "stock-basic",
            {"exchange": exchange, "list_status": status, "fields": ",".join(master_fields)},
            master_fields,
        )
        for exchange in ("SSE", "SZSE")
        for status in ("L", "D", "P")
    )
    return MappingProxyType(
        {
            "trade_calendar": calendars,
            "security_master": masters,
            "daily_bar": (),
        }
    )
