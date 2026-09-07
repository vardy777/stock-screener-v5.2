from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash
from v5_2.providers.contracts import ProviderRequestV1


class StatusEntryError(RuntimeError):
    """The frozen status acquisition boundary is invalid."""


@dataclass(frozen=True, slots=True)
class StatusRequestInventoryV1:
    inventory_id: str
    universe_id: str
    upstream_approval_ids: tuple[str, str, str]
    ordered_symbols: tuple[str, ...]
    coverage_start: str
    coverage_end: str
    requests: tuple[ProviderRequestV1, ...]
    content_hash: str


def build_status_request_inventory(universe, *, daily_bar_approval_id, active_approval_ids, revoked_approval_ids):
    upstream = (*tuple(universe["upstream_approval_ids"]), daily_bar_approval_id)
    active, revoked = set(active_approval_ids), set(revoked_approval_ids)
    if any(identifier in revoked for identifier in upstream):
        raise StatusEntryError("upstream approval is revoked")
    if any(identifier not in active for identifier in upstream):
        raise StatusEntryError("upstream approval is inactive")
    symbols = tuple(universe["ordered_symbols"])
    sessions = tuple(universe["ordered_sessions"])
    if symbols != tuple(sorted(set(symbols))) or sessions != tuple(sorted(set(sessions))):
        raise StatusEntryError("universe ordering is not canonical")
    start_year, end_year = int(sessions[0][:4]), int(sessions[-1][:4])
    requests = []
    endpoint_specs = (
        ("risk_warning_history", "namechange", ("ts_code", "name", "start_date", "end_date", "ann_date", "change_reason")),
        ("suspension_history", "suspend-d", ("ts_code", "trade_date", "suspend_timing", "suspend_type")),
    )
    for year in range(start_year, end_year + 1):
        for dataset_kind, endpoint, fields in endpoint_specs:
            requests.append(ProviderRequestV1.create(
                source_name="datahubco_tushare_proxy", dataset_kind=dataset_kind, endpoint=endpoint,
                parameters={"start_date": f"{year}0101", "end_date": f"{year}1231", "fields": ",".join(fields)},
                requested_fields=fields, page_size=5000, request_policy_version="phase-1b2a-status-v1",
            ))
    values = {
        "universe_id": universe["universe_id"], "upstream_approval_ids": upstream,
        "ordered_symbols": symbols, "coverage_start": sessions[0], "coverage_end": sessions[-1],
        "request_ids": tuple(request.request_id for request in requests),
    }
    digest = content_hash({"schema_version": "StatusRequestInventoryV1", **values})
    return StatusRequestInventoryV1(
        inventory_id=digest, content_hash=digest, requests=tuple(requests),
        **{key: value for key, value in values.items() if key != "request_ids"},
    )
