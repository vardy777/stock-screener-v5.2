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
        sessions = tuple(sorted(approved_sessions))
        session_index = {session: index for index, session in enumerate(sessions)}
        observations = {}
        for row in ordered:
            required = {"ts_code", "trade_date", "suspend_timing", "suspend_type"}
            if set(row) < required:
                raise StatusNormalizationError("required suspension field missing")
            identity, event_date, event_type = str(row["ts_code"]), _date(row["trade_date"]), str(row["suspend_type"]).upper()
            if event_type not in {"S", "R"}:
                raise StatusNormalizationError("unknown suspension event type")
            if event_date not in session_index:
                raise StatusNormalizationError("suspension observation is outside approved sessions")
            key = (identity, event_date)
            previous = observations.get(key)
            if previous is not None and previous["suspend_type"] != event_type:
                raise StatusNormalizationError("conflicting suspension observations")
            observations[key] = row

        facts = []
        by_identity = {}
        for (identity, event_date), row in observations.items():
            if str(row["suspend_type"]).upper() == "S":
                by_identity.setdefault(identity, []).append((event_date, row))
        for identity, items in sorted(by_identity.items()):
            items.sort(key=lambda item: item[0])
            run = [items[0]]
            for item in items[1:]:
                if session_index[item[0]] == session_index[run[-1][0]] + 1:
                    run.append(item)
                else:
                    facts.append(self._suspension_run_fact(identity, run, sessions, source_payload_hash))
                    run = [item]
            facts.append(self._suspension_run_fact(identity, run, sessions, source_payload_hash))
        return tuple(sorted(facts, key=lambda fact: (fact.security_identity, fact.effective_from, fact.status_value)))

    def _suspension_run_fact(self, identity, run, approved_sessions, source_payload_hash):
        start, end = run[0][0], run[-1][0]
        timing_values = {row.get("suspend_timing") for _, row in run}
        value = "SUSPENDED" if timing_values == {None} or timing_values == {""} else "PARTIAL_SUSPENSION"
        source = {"payload_hash": source_payload_hash, "rows": tuple(row for _, row in run)}
        return self._suspension_fact(identity, value, start, end, source,
                                     approved_sessions=approved_sessions,
                                     source_payload_hash=source_payload_hash)

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
