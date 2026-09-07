from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from v5_2.data.identity import content_hash


def _identity(values):
    return {
        key: (str(value) if isinstance(value, Decimal) else value)
        for key, value in values.items()
    }


@dataclass(frozen=True, slots=True)
class DailyBarFactV1:
    fact_id: str
    security_identity: str
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume_shares: Decimal
    amount_yuan: Decimal
    price_basis: str
    available_at: datetime
    availability_policy_version: str
    source_payload_hash: str
    content_hash: str

    @classmethod
    def create(cls, *, source_symbol: str, session: date, open: Decimal, high: Decimal,
               low: Decimal, close: Decimal, raw_volume: Decimal, raw_amount: Decimal,
               source_payload_hash: str):
        identity = "300114.SZ" if source_symbol == "302132.SZ" and session < date(2025, 2, 17) else source_symbol
        zone = timezone(timedelta(hours=8), "Asia/Shanghai")
        values = {
            "security_identity": identity, "session": session,
            "open": open, "high": high, "low": low, "close": close,
            "volume_shares": raw_volume * Decimal("100"),
            "amount_yuan": raw_amount * Decimal("1000"), "price_basis": "UNADJUSTED_RAW",
            "available_at": datetime.combine(session, time(15, 0), zone),
            "availability_policy_version": "daily-bar-d-close-v1",
            "source_payload_hash": source_payload_hash,
        }
        digest = content_hash({"schema_version": "DailyBarFactV1", **_identity(values)})
        return cls(fact_id=digest, content_hash=digest, **values)

    def verify(self) -> bool:
        values = {name: getattr(self, name) for name in (
            "security_identity", "session", "open", "high", "low", "close",
            "volume_shares", "amount_yuan", "price_basis", "available_at",
            "availability_policy_version", "source_payload_hash",
        )}
        return self.fact_id == self.content_hash == content_hash({"schema_version": "DailyBarFactV1", **_identity(values)})
