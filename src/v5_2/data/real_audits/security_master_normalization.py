from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import content_hash


class SecurityMasterNormalizationError(RuntimeError):
    """A provider identity cannot be mapped without guessing."""


@dataclass(frozen=True, slots=True)
class SecurityMasterNormalizationPolicyV1:
    policy_id: str
    policy_version: str
    board_mapping: Mapping[str, str]
    allowed_statuses: tuple[str, ...]
    a_share_prefixes: Mapping[str, tuple[str, ...]]
    explicit_non_target_prefixes: Mapping[str, tuple[str, ...]]
    unresolved_prefixes: Mapping[str, tuple[str, ...]]
    content_hash: str

    @classmethod
    def create_default(cls) -> SecurityMasterNormalizationPolicyV1:
        board_mapping = MappingProxyType({
            "SSE|主板": "SH_MAIN",
            "SSE|科创板": "STAR",
            "SZSE|主板": "SZ_MAIN",
            "SZSE|中小板": "SZ_MAIN",
            "SZSE|创业板": "CHINEXT",
        })
        prefixes = MappingProxyType({
            "SSE": ("600", "601", "603", "605", "688"),
            "SZSE": ("000", "001", "002", "003", "300", "301"),
        })
        non_target = MappingProxyType({"SSE": ("689",), "SZSE": ()})
        unresolved = MappingProxyType({"SSE": ("T",), "SZSE": ("302",)})
        body = {
            "schema_version": "SecurityMasterNormalizationPolicyV1",
            "policy_version": "security-master-normalization-v1",
            "board_mapping": board_mapping,
            "allowed_statuses": ("D", "L", "P"),
            "a_share_prefixes": prefixes,
            "explicit_non_target_prefixes": non_target,
            "unresolved_prefixes": unresolved,
        }
        digest = content_hash(body)
        return cls(
            policy_id=digest,
            content_hash=digest,
            policy_version=body["policy_version"],
            board_mapping=board_mapping,
            allowed_statuses=body["allowed_statuses"],
            a_share_prefixes=prefixes,
            explicit_non_target_prefixes=non_target,
            unresolved_prefixes=unresolved,
        )

    def disposition(self, row: Mapping[str, Any]) -> str:
        exchange = str(row.get("exchange"))
        symbol = row.get("symbol")
        if not isinstance(symbol, str):
            return "REJECTED_UNRESOLVED"
        if symbol.startswith(self.explicit_non_target_prefixes.get(exchange, ())):
            return "EXCLUDED_NON_TARGET"
        if symbol.startswith(self.unresolved_prefixes.get(exchange, ())):
            return "REJECTED_UNRESOLVED"
        prefixes = self.a_share_prefixes.get(exchange)
        if prefixes is None or not symbol.startswith(prefixes):
            return "REJECTED_UNRESOLVED"
        return "NORMALIZED_ELIGIBLE"

    def normalize(self, row: Mapping[str, Any]) -> Mapping[str, Any]:
        exchange = row.get("exchange")
        market = row.get("market")
        status = row.get("list_status")
        symbol = row.get("symbol")
        ts_code = row.get("ts_code")
        board = self.board_mapping.get(f"{exchange}|{market}")
        prefixes = self.a_share_prefixes.get(str(exchange))
        expected_suffix = {"SSE": ".SH", "SZSE": ".SZ"}.get(str(exchange))
        disposition = self.disposition(row)
        if disposition == "EXCLUDED_NON_TARGET":
            raise SecurityMasterNormalizationError("explicit non-target security")
        if (
            disposition != "NORMALIZED_ELIGIBLE"
            or
            board is None
            or status not in self.allowed_statuses
            or not isinstance(symbol, str)
            or len(symbol) != 6
            or not symbol.isdigit()
            or prefixes is None
            or not symbol.startswith(prefixes)
            or not isinstance(ts_code, str)
            or ts_code != symbol + expected_suffix
        ):
            raise SecurityMasterNormalizationError("unsupported or ambiguous security identity")
        return MappingProxyType({
            "symbol": ts_code,
            "exchange": exchange,
            "security_name": row.get("name"),
            "security_type": "A_SHARE",
            "board": board,
            "listing_date": row.get("list_date"),
            "delisting_date": row.get("delist_date"),
            "listing_status": status,
            "is_a_share": True,
        })
