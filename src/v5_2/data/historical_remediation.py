from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash
from v5_2.providers.contracts import ProviderRequestV1


DAILY_BAR_FIELDS = (
    "ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount",
)


def canonicalize_rows(rows):
    """Order provider rows by canonical content, including nullable values."""
    unique = {content_hash(row): dict(row) for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def build_next_session_availability_map(*, research_sessions, approved_sessions):
    approved = tuple(sorted(set(approved_sessions)))
    positions = {session: index for index, session in enumerate(approved)}
    result = []
    for session in tuple(sorted(set(research_sessions))):
        index = positions.get(session)
        if index is None or index + 1 >= len(approved):
            raise ValueError(f"next approved session is unavailable for {session}")
        next_session = approved[index + 1]
        timestamp = f"{next_session[:4]}-{next_session[4:6]}-{next_session[6:]}T16:30:00+08:00"
        result.append((session, next_session, timestamp))
    return tuple(result)


def classify_daily_bar_identity(identity: str, target_identities) -> str:
    if identity in target_identities:
        return "TARGET"
    if identity.endswith(".BJ"):
        return "EXCLUDED_NON_TARGET"
    return "UNRESOLVED_TARGET_IDENTITY"


@dataclass(frozen=True, slots=True)
class DailyBarSegmentInventoryV1:
    sessions: tuple[str, ...]
    upstream_approval_ids: tuple[str, ...]
    requests: tuple[ProviderRequestV1, ...]
    inventory_id: str
    content_hash: str

    def verify(self) -> bool:
        values = {
            "sessions": self.sessions,
            "upstream_approval_ids": self.upstream_approval_ids,
            "request_ids": tuple(item.request_id for item in self.requests),
        }
        digest = content_hash({"schema_version": "DailyBarSegmentInventoryV1", **values})
        return self.inventory_id == self.content_hash == digest


def build_daily_bar_segment_inventory(*, sessions: tuple[str, ...],
                                      upstream_approval_ids: tuple[str, ...]):
    """Freeze one market-wide request per approved 2026 trading session."""
    if len(sessions) != len(set(sessions)):
        raise ValueError("sessions must be unique")
    ordered = tuple(sorted(sessions))
    if not ordered or any(len(item) != 8 or not item.isdigit() or not item.startswith("2026")
                          for item in ordered):
        raise ValueError("sessions must be YYYYMMDD dates in 2026")
    approvals = tuple(upstream_approval_ids)
    if not approvals or any(not item for item in approvals):
        raise ValueError("upstream approval ids are required")
    requests = tuple(ProviderRequestV1.create(
        source_name="datahubco_tushare_proxy",
        dataset_kind="daily_bar",
        endpoint="daily",
        parameters={"trade_date": session, "fields": ",".join(DAILY_BAR_FIELDS)},
        requested_fields=DAILY_BAR_FIELDS,
        page_size=5000,
        request_policy_version="daily-bar-2026-segment-v1",
    ) for session in ordered)
    values = {"sessions": ordered, "upstream_approval_ids": approvals,
              "request_ids": tuple(item.request_id for item in requests)}
    digest = content_hash({"schema_version": "DailyBarSegmentInventoryV1", **values})
    return DailyBarSegmentInventoryV1(
        sessions=ordered, upstream_approval_ids=approvals, requests=requests,
        inventory_id=digest, content_hash=digest,
    )
