from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from v5_2.data.identity import content_hash
from v5_2.data.real_audits.status_availability import StatusAvailabilityPolicyV1
from v5_2.data.security_status_facts import SecurityStatusIntervalFactV1, StatusKind


class StatusNormalizationError(ValueError):
    """Provider status data cannot be normalized deterministically."""


def _date(value, *, optional=False):
    if optional and value in (None, ""):
        return None
    text = str(value)
    try:
        if len(text) != 8 or not text.isdigit():
            raise ValueError
        return date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except ValueError:
        raise StatusNormalizationError("invalid provider date") from None


@dataclass(frozen=True, slots=True)
class StatusNormalizationPolicyV1:
    risk_warning_pattern: str
    policy_version: str
    policy_id: str

    @classmethod
    def default(cls):
        pattern = r"^(?:S\*?ST|\*?ST)"
        version = "status-normalization-v1"
        digest = content_hash({"schema_version": "StatusNormalizationPolicyV1", "risk_warning_pattern": pattern,
                               "policy_version": version})
        return cls(pattern, version, digest)

    def normalize_namechange(self, row, *, approved_sessions, source_payload_hash):
        required = {"ts_code", "name", "start_date", "end_date", "ann_date", "change_reason"}
        if set(row) < required:
            raise StatusNormalizationError("required namechange field missing")
        start = _date(row["start_date"])
        end = _date(row["end_date"], optional=True)
        announcement = _date(row["ann_date"])
        value = "ST" if re.match(self.risk_warning_pattern, str(row["name"]), re.IGNORECASE) else "CLEAR"
        available = StatusAvailabilityPolicyV1.date_only_next_session().derive(
            event_date=announcement, published_at=None, approved_sessions=approved_sessions,
        )
        return SecurityStatusIntervalFactV1.create(
            security_identity=str(row["ts_code"]), status_kind=StatusKind.RISK_WARNING,
            status_value=value, effective_from=start, effective_to=end, published_at=None,
            available_at=available, availability_basis="DATE_ONLY_NEXT_SESSION",
            source_fact_id=content_hash({"payload_hash": source_payload_hash, "row": row}),
            source_name="datahubco_tushare_proxy", policy_version=self.policy_version,
        )

    def normalize_suspension_events(self, rows, *, approved_sessions, source_payload_hash):
        ordered = tuple(sorted(rows, key=lambda row: (str(row.get("ts_code")), str(row.get("trade_date")))))
        active = {}
        facts = []
        sessions = tuple(sorted(approved_sessions))
        for row in ordered:
            required = {"ts_code", "trade_date", "suspend_timing", "suspend_type"}
            if set(row) < required:
                raise StatusNormalizationError("required suspension field missing")
            identity, event_date, event_type = str(row["ts_code"]), _date(row["trade_date"]), str(row["suspend_type"]).upper()
            if event_type == "S":
                if identity in active:
                    raise StatusNormalizationError("overlapping suspension start")
                active[identity] = (event_date, row)
            elif event_type == "R":
                if identity not in active:
                    raise StatusNormalizationError("suspension resume has no start")
                start, start_row = active.pop(identity)
                previous = tuple(session for session in sessions if session < event_date)
                if not previous or event_date not in sessions:
                    raise StatusNormalizationError("suspension boundary is outside approved sessions")
                facts.append(self._suspension_fact(identity, "SUSPENDED", start, previous[-1], start_row,
                                                   approved_sessions=sessions, source_payload_hash=source_payload_hash))
                facts.append(self._suspension_fact(identity, "TRADING", event_date, None, row,
                                                   approved_sessions=sessions, source_payload_hash=source_payload_hash))
            else:
                raise StatusNormalizationError("unknown suspension event type")
        for identity, (start, row) in active.items():
            facts.append(self._suspension_fact(identity, "SUSPENDED", start, None, row,
                                               approved_sessions=sessions, source_payload_hash=source_payload_hash))
        return tuple(sorted(facts, key=lambda fact: (fact.security_identity, fact.effective_from, fact.status_value)))

    def _suspension_fact(self, identity, value, start, end, row, *, approved_sessions, source_payload_hash):
        available = StatusAvailabilityPolicyV1.date_only_next_session().derive(
            event_date=start, published_at=None, approved_sessions=approved_sessions,
        )
        return SecurityStatusIntervalFactV1.create(
            security_identity=identity, status_kind=StatusKind.SUSPENSION, status_value=value,
            effective_from=start, effective_to=end, published_at=None, available_at=available,
            availability_basis="DATE_ONLY_NEXT_SESSION",
            source_fact_id=content_hash({"payload_hash": source_payload_hash, "row": row}),
            source_name="datahubco_tushare_proxy", policy_version=self.policy_version,
        )
