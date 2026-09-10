from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from v5_2.data.identity import content_hash
from v5_2.providers.contracts import ProviderRequestV1


class CorporateActionEntryError(RuntimeError):
    """The corporate-action acquisition intent is unsafe."""


@dataclass(frozen=True, slots=True)
class SegmentedCorporateActionRequestV1:
    segment: str
    security_identity: str
    request: ProviderRequestV1


@dataclass(frozen=True, slots=True)
class CorporateActionRequestInventoryV1:
    inventory_id: str
    target_history_start: date
    baseline_validation_end: date
    rolling_coverage_end: date
    upstream_approval_ids: tuple[str, ...]
    ordered_symbols: tuple[str, ...]
    requests: tuple[SegmentedCorporateActionRequestV1, ...]
    content_hash: str


def build_corporate_action_inventory(
    *, symbols: tuple[str, ...], endpoint: str, target_history_start: date,
    baseline_validation_end: date, rolling_coverage_end: date,
    upstream_approval_ids: tuple[str, ...], active_approval_ids: tuple[str, ...],
    revoked_approval_ids: tuple[str, ...],
) -> CorporateActionRequestInventoryV1:
    if symbols != tuple(sorted(set(symbols))):
        raise CorporateActionEntryError("symbols must be canonical")
    if not (target_history_start <= baseline_validation_end < rolling_coverage_end):
        raise CorporateActionEntryError("coverage boundaries are invalid")
    active, revoked = set(active_approval_ids), set(revoked_approval_ids)
    if any(identifier in revoked for identifier in upstream_approval_ids):
        raise CorporateActionEntryError("upstream approval is revoked")
    if any(identifier not in active for identifier in upstream_approval_ids):
        raise CorporateActionEntryError("upstream approval is inactive")
    requests = []
    fields = (
        "ts_code", "end_date", "ann_date", "div_proc", "stk_div", "stk_bo_rate",
        "stk_co_rate", "cash_div", "cash_div_tax", "record_date", "ex_date",
        "pay_date", "div_listdate", "imp_ann_date",
    )
    for symbol in symbols:
        request = ProviderRequestV1.create(
            source_name="datahubco_tushare_proxy", dataset_kind="corporate_action",
            endpoint=endpoint, parameters={"ts_code": symbol, "fields": ",".join(fields)},
            requested_fields=fields, page_size=2000,
            request_policy_version="phase-1b2c-corporate-action-v2",
        )
        requests.append(SegmentedCorporateActionRequestV1("FULL_HISTORY", symbol, request))
    identity = {
        "target_history_start": target_history_start,
        "baseline_validation_end": baseline_validation_end,
        "rolling_coverage_end": rolling_coverage_end,
        "upstream_approval_ids": upstream_approval_ids,
        "ordered_symbols": symbols,
        "request_ids": tuple((item.segment, item.security_identity, item.request.request_id) for item in requests),
    }
    digest = content_hash({"schema_version": "CorporateActionRequestInventoryV1", **identity})
    return CorporateActionRequestInventoryV1(
        inventory_id=digest, content_hash=digest, requests=tuple(requests),
        **{key: value for key, value in identity.items() if key != "request_ids"},
    )
