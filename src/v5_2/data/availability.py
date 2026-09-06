from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any

from v5_2.data.identity import canonical_json
from v5_2.foundations.calendar import TradingCalendar
from v5_2.foundations.core import ContractViolation


class AvailabilityError(RuntimeError):
    """Historical availability cannot be derived conservatively."""


class AvailabilityBasis(str, Enum):
    DATE_ONLY_NEXT_SESSION_CLOSE = "DATE_ONLY_NEXT_SESSION_CLOSE"
    SESSION_PUBLICATION_TIME = "SESSION_PUBLICATION_TIME"
    VERIFIED_TIMESTAMP = "VERIFIED_TIMESTAMP"


@dataclass(frozen=True, slots=True)
class AvailabilityPolicyV1:
    dataset_kind: str
    basis: AvailabilityBasis
    date_field: str
    timestamp_field: str | None
    publication_time: time
    timezone_name: str
    policy_version: str
    validation_evidence_id: str


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    available_at: datetime
    availability_policy_version: str
    source_fields: Mapping[str, Any]


def _date(value: object, field: str) -> date:
    if isinstance(value, datetime):
        raise AvailabilityError(f"{field} must be a date, not a timestamp")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise AvailabilityError(f"{field} is missing or invalid")


def _next_open_after(calendar: TradingCalendar, day: date) -> date:
    candidate = day + timedelta(days=1)
    while True:
        try:
            if calendar.is_open(candidate):
                return candidate
        except ContractViolation as error:
            raise AvailabilityError("calendar mapping is unavailable") from error
        candidate += timedelta(days=1)


def derive_available_at(
    policy: AvailabilityPolicyV1,
    source_fields: Mapping[str, Any],
    calendar: TradingCalendar,
    *,
    historical_backfill: bool = False,
    acquired_at: datetime | None = None,
) -> AvailabilityResult:
    if policy.timezone_name != "Asia/Shanghai":
        raise AvailabilityError("timezone is unavailable")
    zone = timezone(timedelta(hours=8), "Asia/Shanghai")
    if policy.basis is AvailabilityBasis.VERIFIED_TIMESTAMP:
        if not policy.validation_evidence_id:
            raise AvailabilityError("verified timestamp requires validation evidence")
        if policy.timestamp_field is None:
            raise AvailabilityError("verified timestamp field is missing")
        supplied = source_fields.get(policy.timestamp_field)
        try:
            available_at = datetime.fromisoformat(str(supplied))
        except ValueError as error:
            raise AvailabilityError("verified timestamp is invalid") from error
        if available_at.tzinfo is None or available_at.utcoffset() is None:
            raise AvailabilityError("verified timestamp must be timezone-aware")
        used_fields = {policy.timestamp_field: supplied}
    else:
        event_date = _date(source_fields.get(policy.date_field), policy.date_field)
        try:
            is_open = calendar.is_open(event_date)
        except ContractViolation as error:
            raise AvailabilityError("calendar mapping is unavailable") from error
        if policy.basis is AvailabilityBasis.DATE_ONLY_NEXT_SESSION_CLOSE:
            eligible_session = _next_open_after(calendar, event_date)
        elif policy.basis is AvailabilityBasis.SESSION_PUBLICATION_TIME:
            if not is_open:
                raise AvailabilityError("calendar event date is not an open session")
            eligible_session = event_date
        else:
            raise AvailabilityError("availability basis is unsupported")
        available_at = datetime.combine(eligible_session, policy.publication_time, zone)
        used_fields = {policy.date_field: source_fields.get(policy.date_field)}
    if acquired_at is not None:
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise AvailabilityError("acquired_at must be timezone-aware")
        if not historical_backfill:
            available_at = max(available_at, acquired_at.astimezone(zone))
    canonical_fields = json.loads(canonical_json(used_fields).decode("utf-8"))
    return AvailabilityResult(
        available_at=available_at,
        availability_policy_version=policy.policy_version,
        source_fields=canonical_fields,
    )
