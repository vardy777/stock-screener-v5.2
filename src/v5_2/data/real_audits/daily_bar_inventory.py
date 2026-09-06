from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class DeterministicDailyBarUniverseV1:
    universe_id: str
    upstream_approval_ids: tuple[str, str]
    ordered_symbols: tuple[str, ...]
    ordered_sessions: tuple[str, ...]
    adjustment: str
    exception_set_hash: str
    content_hash: str

    @classmethod
    def create(cls, *, upstream_approval_ids, symbols, sessions, exception_set_hash):
        values = {
            "upstream_approval_ids": tuple(upstream_approval_ids),
            "ordered_symbols": tuple(sorted(set(symbols))), "ordered_sessions": tuple(sorted(set(sessions))),
            "adjustment": "UNADJUSTED_RAW", "exception_set_hash": exception_set_hash,
        }
        if len(values["upstream_approval_ids"]) != 2 or not all(values["upstream_approval_ids"]):
            raise ValueError("two approved upstream IDs are required")
        digest = content_hash({"schema_version": "DeterministicDailyBarUniverseV1", **values})
        return cls(universe_id=digest, content_hash=digest, **values)


@dataclass(frozen=True, slots=True)
class DailyBarRequestInventoryV1:
    inventory_id: str
    universe_id: str
    request_ids: tuple[str, ...]
    sample_strata: tuple[str, ...]
    volume_unit_audit: str
    amount_unit_audit: str
    cross_source_rule: str
    acquisition_started: bool
    content_hash: str

    @classmethod
    def create(cls, *, universe, sample_strata, volume_unit_audit, amount_unit_audit, cross_source_rule):
        request_ids = tuple(content_hash({
            "schema_version": "DailyBarLogicalRequestV1", "universe_id": universe.universe_id,
            "symbol": symbol, "start": universe.ordered_sessions[0], "end": universe.ordered_sessions[-1],
            "adjustment": universe.adjustment,
        }) for symbol in universe.ordered_symbols)
        values = {
            "universe_id": universe.universe_id, "request_ids": request_ids,
            "sample_strata": tuple(sample_strata), "volume_unit_audit": volume_unit_audit,
            "amount_unit_audit": amount_unit_audit, "cross_source_rule": cross_source_rule,
            "acquisition_started": False,
        }
        digest = content_hash({"schema_version": "DailyBarRequestInventoryV1", **values})
        return cls(inventory_id=digest, content_hash=digest, **values)
