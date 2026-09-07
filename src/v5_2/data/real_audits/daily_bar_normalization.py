from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from v5_2.data.identity import content_hash


class DailyBarNormalizationError(ValueError):
    pass


def finite_decimal(value) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DailyBarNormalizationError("malformed numeric value") from None
    if not result.is_finite():
        raise DailyBarNormalizationError("non-finite numeric value")
    return result


@dataclass(frozen=True, slots=True)
class DailyBarFactCandidateV1:
    security_identity: str
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal
    price_basis: str


@dataclass(frozen=True, slots=True)
class DailyBarNormalizationPolicyV1:
    policy_id: str
    field_mapping: tuple[tuple[str, str], ...]
    policy_version: str
    content_hash: str

    @classmethod
    def create_default(cls):
        mapping = (("ts_code", "security_identity"), ("trade_date", "session"), ("open", "open"),
                   ("high", "high"), ("low", "low"), ("close", "close"), ("vol", "volume"), ("amount", "amount"))
        values = {"field_mapping": mapping, "policy_version": "daily-bar-normalization-v1"}
        digest = content_hash({"schema_version": "DailyBarNormalizationPolicyV1", **values})
        return cls(policy_id=digest, content_hash=digest, **values)

    def normalize(self, row, *, volume_factor, amount_factor, effective_identity):
        if set(row) < {source for source, _ in self.field_mapping}:
            raise DailyBarNormalizationError("required daily-bar field missing")
        try:
            session = date.fromisoformat(f"{row['trade_date'][:4]}-{row['trade_date'][4:6]}-{row['trade_date'][6:8]}")
        except Exception:
            raise DailyBarNormalizationError("invalid trade_date") from None
        return DailyBarFactCandidateV1(
            security_identity=effective_identity, session=session,
            open=finite_decimal(row["open"]), high=finite_decimal(row["high"]), low=finite_decimal(row["low"]), close=finite_decimal(row["close"]),
            volume=finite_decimal(row["vol"]) * finite_decimal(volume_factor),
            amount=finite_decimal(row["amount"]) * finite_decimal(amount_factor), price_basis="UNADJUSTED_RAW",
        )
