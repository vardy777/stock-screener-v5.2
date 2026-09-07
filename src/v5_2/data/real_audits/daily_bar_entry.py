from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from v5_2.data.identity import content_hash
from v5_2.providers.contracts import ProviderRequestV1


class DailyBarEntryError(RuntimeError):
    """Frozen daily-bar entry intent is invalid or no longer authorized."""


FIELDS = ("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount")


@dataclass(frozen=True, slots=True)
class ExecutableDailyBarRequestV1:
    logical_request_id: str
    provider_request: ProviderRequestV1


@dataclass(frozen=True, slots=True)
class DailyBarAcquisitionPlanV1:
    plan_id: str
    universe_id: str
    inventory_id: str
    upstream_approval_ids: tuple[str, str]
    ordered_symbols: tuple[str, ...]
    ordered_sessions: tuple[str, ...]
    adjustment: str
    sample_policy_id: str
    requests: tuple[ExecutableDailyBarRequestV1, ...]
    content_hash: str


def _require_hash(payload, schema, identity_key, excluded):
    body = {"schema_version": schema, **{key: value for key, value in payload.items() if key not in excluded}}
    digest = content_hash(body)
    if payload.get(identity_key) != digest or payload.get("content_hash") != digest:
        raise DailyBarEntryError(f"{schema} content identity mismatch")
    return digest


def build_acquisition_plan(universe, inventory, *, active_approval_ids, revoked_approval_ids):
    universe_id = _require_hash(universe, "DeterministicDailyBarUniverseV1", "universe_id", {"universe_id", "content_hash"})
    inventory_id = _require_hash(inventory, "DailyBarRequestInventoryV1", "inventory_id", {"inventory_id", "content_hash"})
    symbols = tuple(universe["ordered_symbols"])
    sessions = tuple(universe["ordered_sessions"])
    upstream = tuple(universe["upstream_approval_ids"])
    if symbols != tuple(sorted(set(symbols))) or sessions != tuple(sorted(set(sessions))):
        raise DailyBarEntryError("frozen universe order or uniqueness changed")
    if universe.get("adjustment") != "UNADJUSTED_RAW":
        raise DailyBarEntryError("only UNADJUSTED_RAW is authorized")
    if inventory.get("universe_id") != universe_id or len(inventory.get("request_ids", ())) != len(symbols):
        raise DailyBarEntryError("inventory does not exactly cover frozen universe")
    active, revoked = set(active_approval_ids), set(revoked_approval_ids)
    if any(item not in active or item in revoked for item in upstream):
        raise DailyBarEntryError("upstream approval is missing or revoked")
    start, end = sessions[0], sessions[-1]
    executable = []
    for symbol, logical_id in zip(symbols, inventory["request_ids"], strict=True):
        expected_logical = content_hash({"schema_version": "DailyBarLogicalRequestV1", "universe_id": universe_id,
                                         "symbol": symbol, "start": start, "end": end,
                                         "adjustment": "UNADJUSTED_RAW"})
        if logical_id != expected_logical:
            raise DailyBarEntryError("logical request identity mismatch")
        provider = ProviderRequestV1.create(
            source_name="datahubco_tushare_proxy", dataset_kind="daily_bar", endpoint="daily",
            parameters={"ts_code": symbol, "start_date": start, "end_date": end, "fields": ",".join(FIELDS)},
            requested_fields=FIELDS, page_size=5000, request_policy_version="daily-bar-acquisition-v1",
        )
        executable.append(ExecutableDailyBarRequestV1(logical_id, provider))
    values = {"universe_id": universe_id, "inventory_id": inventory_id, "upstream_approval_ids": upstream,
              "ordered_symbols": symbols, "ordered_sessions": sessions, "adjustment": "UNADJUSTED_RAW",
              "sample_policy_id": "v5.2-phase-1b1-daily-bar-v1",
              "request_mapping": tuple((item.logical_request_id, item.provider_request.request_id) for item in executable)}
    digest = content_hash({"schema_version": "DailyBarAcquisitionPlanV1", **values})
    return DailyBarAcquisitionPlanV1(plan_id=digest, content_hash=digest, requests=tuple(executable),
                                     **{key: value for key, value in values.items() if key != "request_mapping"})
