from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from v5_2.data.identity import content_hash
from v5_2.providers.contracts import ProviderRequestV1


FIELDS = {
    "financial_income": ("ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "end_type",
                         "total_revenue", "revenue", "n_income", "n_income_attr_p", "update_flag"),
    "financial_balance_sheet": ("ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "end_type",
                                "total_assets", "total_liab", "total_hldr_eqy_exc_min_int", "money_cap", "total_share", "update_flag"),
    "financial_cash_flow": ("ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "end_type",
                            "n_cashflow_act", "n_cashflow_inv_act", "n_cash_flows_fnc_act", "c_cash_equ_end_period", "update_flag"),
}
ENDPOINTS = {"financial_income": "income", "financial_balance_sheet": "balancesheet", "financial_cash_flow": "cashflow"}


def run_bounded_retry_rounds(items, operation, *, max_rounds: int, workers: int):
    if max_rounds < 1 or workers < 1: raise ValueError("retry rounds and workers must be positive")
    values, pending, results = tuple(items), list(range(len(items))), {}
    for _ in range(max_rounds):
        failed = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(operation, values[index]): index for index in pending}
            for future in as_completed(futures):
                index = futures[future]
                try: results[index] = future.result()
                except Exception: failed.append(index)
        pending = sorted(failed)
        if not pending: return tuple(results[index] for index in range(len(values)))
    raise RuntimeError(f"{len(pending)} requests remain failed after bounded retries")


@dataclass(frozen=True, slots=True)
class FinancialDisclosureInventoryV1:
    inventory_id: str
    universe_id: str
    upstream_approval_ids: tuple[str, str]
    coverage_start: str
    coverage_end: str
    requests: tuple[ProviderRequestV1, ...]
    content_hash: str


def build_financial_disclosure_inventory(*, symbols, coverage_start: str, coverage_end: str,
                                         universe_id: str, upstream_approval_ids):
    canonical_symbols = tuple(sorted(set(symbols)))
    if not canonical_symbols or any(not symbol.endswith((".SH", ".SZ")) for symbol in canonical_symbols):
        raise ValueError("symbols must be canonical A-share identities")
    approvals = tuple(upstream_approval_ids)
    if len(approvals) != 2 or not all(approvals) or not universe_id or coverage_end < coverage_start:
        raise ValueError("approved upstream scope is required")
    segments = tuple((max(coverage_start, start), min(coverage_end, end)) for start, end in
                     (("20100104", "20171231"), ("20180101", "20991231"))
                     if max(coverage_start, start) <= min(coverage_end, end))
    requests = tuple(ProviderRequestV1.create(source_name="datahubco_tushare_proxy", dataset_kind=kind,
        endpoint=ENDPOINTS[kind], parameters={"ts_code": symbol, "start_date": segment_start,
        "end_date": segment_end, "fields": ",".join(FIELDS[kind])}, requested_fields=FIELDS[kind], page_size=5000,
        request_policy_version="financial-disclosure-request-v1") for symbol in canonical_symbols for kind in ENDPOINTS
        for segment_start, segment_end in segments)
    body = {"schema_version": "FinancialDisclosureInventoryV1", "universe_id": universe_id,
            "upstream_approval_ids": approvals, "coverage_start": coverage_start,
            "coverage_end": coverage_end, "universe_symbol_count": len(canonical_symbols),
            "universe_symbols_hash": content_hash(canonical_symbols),
            "request_ids": tuple(request.request_id for request in requests)}
    digest = content_hash(body)
    return FinancialDisclosureInventoryV1(digest, universe_id, approvals, coverage_start, coverage_end, requests, digest)
