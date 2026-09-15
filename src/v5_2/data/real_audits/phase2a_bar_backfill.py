from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

from v5_2.data.identity import content_hash
from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.real_audits.daily_bar_validation import audit_bars
from v5_2.providers.contracts import ProviderRequestV1
from v5_2.data.raw_artifacts import RawArtifactStore


GAP_AUDIT_ID = "796990a6be6dc53133124cf33c0cdcb8def2aafff9d8041afab6a3cea9a3dd4e"
FROZEN_INVENTORY_ID = "81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9"
FIELDS = ("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount")


@dataclass(frozen=True, slots=True)
class ValidatedBarBackfillV1:
    inventory_id: str
    acquisition_id: str
    payload_hashes: tuple[str, ...]
    receipt_hashes: tuple[str, ...]
    rows: tuple[tuple[str, dict], ...]
    rejected_rows: tuple[dict, ...]
    unexplained_missing_sessions: tuple[tuple[int, str], ...]


def load_validated_backfill(root: Path) -> ValidatedBarBackfillV1:
    """Re-open and validate the frozen acquisition without provider access."""
    inventory = build_bar_backfill_inventory(root)
    runtime = root / "data/phase_2a/bar_backfill"
    acquisition_paths = tuple((runtime / "governance").glob("bar-backfill-acquisition-*.json"))
    if len(acquisition_paths) != 1:
        raise ValueError("missing or ambiguous frozen backfill acquisition")
    acquisition = _load(acquisition_paths[0])
    artifact_id = acquisition.get("artifact_id")
    body = {key: value for key, value in acquisition.items() if key not in {"artifact_id", "content_hash"}}
    if artifact_id != acquisition.get("content_hash") or artifact_id != content_hash(body):
        raise ValueError("backfill acquisition integrity failed")
    if acquisition.get("inventory_id") != inventory.inventory_id:
        raise ValueError("backfill acquisition inventory mismatch")
    request_by_id = {item.provider_request.request_id: item for item in inventory.requests}
    if tuple(acquisition.get("request_ids", ())) != tuple(request_by_id):
        raise ValueError("backfill request identity mismatch")
    store = RawArtifactStore(runtime)
    rows: list[tuple[str, dict]] = []
    seen_payloads = []
    for path in sorted((runtime / "raw").rglob("*.json")):
        raw = store.read_payload(path)
        request = request_by_id.get(raw.request_id)
        if request is None:
            raise ValueError("unexpected request in frozen backfill")
        if raw.semantic_metadata.get("response_code") != 0 or raw.semantic_metadata.get("has_more") is not False:
            raise ValueError("backfill response is incomplete")
        for source_row in raw.provider_payload.get("rows", ()):
            row = dict(source_row)
            if set(row) != set(FIELDS):
                raise ValueError("backfill schema mismatch")
            if row["ts_code"] != request.effective_security_identity:
                raise ValueError("backfill security identity mismatch")
            session = _iso(str(row["trade_date"]))
            if session not in request.required_sessions:
                raise ValueError("backfill session is outside frozen request")
            rows.append((raw.payload_hash, row))
        seen_payloads.append(raw.payload_hash)
    payload_hashes = tuple(sorted(seen_payloads))
    if payload_hashes != tuple(acquisition.get("payload_hashes", ())) or len(rows) != acquisition.get("row_count"):
        raise ValueError("backfill payload membership mismatch")
    receipts = tuple(store.read_receipt(path) for path in sorted((runtime / "receipts").rglob("*.json")))
    if len(receipts) != len(payload_hashes) or {item.payload_hash for item in receipts} != set(payload_hashes):
        raise ValueError("backfill receipt coverage mismatch")
    observed = {(row["ts_code"], _iso(str(row["trade_date"]))) for _, row in rows}
    missing = tuple(
        (slot.slot, session.isoformat())
        for slot in inventory.slots for session in slot.required_bar_sessions
        if (slot.historical_symbol, session) not in observed
    )
    return ValidatedBarBackfillV1(
        inventory.inventory_id, artifact_id, payload_hashes,
        tuple(sorted(item.receipt_hash for item in receipts)),
        tuple(rows), (), missing,
    )


def publishable_backfill_facts(
    payload_rows,
    *,
    approved_sessions,
    next_session_by_session,
    available_at,
    availability_policy_version,
    allowed_identities=None,
):
    """Validate Phase-1 daily-bar semantics and construct immutable facts.

    Missing provider rows are intentionally outside this function: no absence is
    converted into a synthetic price record.
    """
    rows = tuple(row for _, row in payload_rows)
    allowed = set(allowed_identities or (str(row.get("ts_code")) for row in rows))
    audit = audit_bars(
        rows, approved_sessions=set(approved_sessions),
        identity_resolver=lambda identity, session: identity if identity in allowed else None,
    )
    if not audit.passed:
        raise ValueError("daily-bar structural, session, or identity audit failed")
    keys = [(str(row["ts_code"]), str(row["trade_date"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate daily-bar fact key")
    facts = []
    for payload_hash, row in payload_rows:
        text = str(row["trade_date"])
        session = date(int(text[:4]), int(text[4:6]), int(text[6:]))
        following = next_session_by_session.get(session)
        if following is None:
            raise ValueError("next approved session is unavailable")
        facts.append(DailyBarFactV1.create(
            source_symbol=str(row["ts_code"]), session=session,
            open=Decimal(str(row["open"])), high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])), close=Decimal(str(row["close"])),
            raw_volume=Decimal(str(row["vol"])), raw_amount=Decimal(str(row["amount"])),
            source_payload_hash=payload_hash,
            available_at=available_at(session, following),
            availability_policy_version=availability_policy_version,
        ))
    return tuple(sorted(facts, key=lambda item: (item.security_identity, item.session)))


@dataclass(frozen=True, slots=True)
class Phase2ABarBackfillSlotV1:
    slot: int
    stratum: str
    canonical_identity: str
    historical_symbol: str
    exchange: str
    anchor_session: date
    h1: date
    h3: date
    h5: date
    window_5d: tuple[date, ...]
    required_bar_sessions: tuple[date, ...]
    status_explained_absence_sessions: tuple[date, ...]
    already_existing_bar_sessions: tuple[date, ...]
    missing_bar_sessions: tuple[date, ...]
    missing_reasons: tuple[tuple[date, str], ...]
    existing_phase1_bar_lineage_checked: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Phase2ABarBackfillRequestV1:
    effective_security_identity: str
    required_sessions: tuple[date, ...]
    slot_ids: tuple[int, ...]
    provider_request: ProviderRequestV1


@dataclass(frozen=True, slots=True)
class Phase2ABarBackfillInventoryV1:
    frozen_inventory_id: str
    evidence_gap_audit_id: str
    slots: tuple[Phase2ABarBackfillSlotV1, ...]
    requests: tuple[Phase2ABarBackfillRequestV1, ...]
    inventory_id: str
    content_hash: str

    def verify(self):
        body = {"frozen_inventory_id": self.frozen_inventory_id,
                "evidence_gap_audit_id": self.evidence_gap_audit_id,
                "slots": self.slots, "requests": self.requests}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.inventory_id == self.content_hash == digest


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _iso(compact: str) -> date:
    return date(int(compact[:4]), int(compact[4:6]), int(compact[6:]))


def build_bar_backfill_inventory(root: Path) -> Phase2ABarBackfillInventoryV1:
    frozen = _load(root / "data/phase_2a/governance" / f"label-acceptance-inventory-{FROZEN_INVENTORY_ID}.json")
    gap = _load(root / "data/phase_2a/governance" / f"phase2a-evidence-gap-audit-{GAP_AUDIT_ID}.json")
    missing_slots = {entry["slot"] for entry in gap["entries"] if entry["blocker_class"] == "REAL_PHASE1_EVIDENCE_ABSENT"}
    calendar = _load(root / "data/phase_1b_exit_remediation/governance/historical-calendar-fact-bundle-d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc.json")
    opens = {"SSE": [], "SZSE": []}
    for row in calendar["ordered_rows"]:
        if row["exchange"] in opens and row["is_open"] == 1:
            opens[row["exchange"]].append(_iso(row["cal_date"]))
    opens = {key: tuple(sorted(set(values))) for key, values in opens.items()}
    suspended = set()
    for path in (root / "data/phase_1b2a/facts/daily_security_status").glob("*.json"):
        fact = _load(path)
        if fact["is_suspended"]:
            suspended.add((fact["security_identity"], date.fromisoformat(fact["session"])))
    lineage = (
        "daily_bar-approval-fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5.json",
        "daily_bar-manifest-76c4fe58d0714405d0a6a826bf9b814237d812f88f69b63986a0e0317f924b4b.json",
        "historical-daily-bar-panel-a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d.json",
    )
    slots = []
    for item in frozen["slots"]:
        if item["slot"] not in missing_slots:
            continue
        anchor = date.fromisoformat(item["anchor_session"])
        future = tuple(day for day in opens[item["exchange"]] if day > anchor)[:5]
        explained = tuple(day for day in future if (item["security_identity"], day) in suspended)
        required = (anchor, *(day for day in future if day not in explained))
        slots.append(Phase2ABarBackfillSlotV1(
            slot=item["slot"], stratum=item["stratum"], canonical_identity=item["security_identity"],
            historical_symbol=item["security_identity"], exchange=item["exchange"], anchor_session=anchor,
            h1=future[0], h3=future[2], h5=future[4], window_5d=future,
            required_bar_sessions=required, status_explained_absence_sessions=explained,
            already_existing_bar_sessions=(), missing_bar_sessions=required,
            missing_reasons=tuple((day, "ANCHOR_REFERENCE_BAR" if day == anchor else "FUTURE_TRADABLE_SESSION_BAR") for day in required),
            existing_phase1_bar_lineage_checked=lineage,
        ))
    requests = []
    for slot in slots:
        provider = ProviderRequestV1.create(
            source_name="datahubco_tushare_proxy", dataset_kind="daily_bar", endpoint="daily",
            parameters={"ts_code": slot.historical_symbol,
                        "start_date": slot.anchor_session.strftime("%Y%m%d"),
                        "end_date": slot.h5.strftime("%Y%m%d"), "fields": ",".join(FIELDS)},
            requested_fields=FIELDS, page_size=5000,
            request_policy_version="daily-bar-acquisition-v1",
        )
        requests.append(Phase2ABarBackfillRequestV1(
            slot.historical_symbol, slot.required_bar_sessions, (slot.slot,), provider))
    body = {"frozen_inventory_id": FROZEN_INVENTORY_ID, "evidence_gap_audit_id": GAP_AUDIT_ID,
            "slots": tuple(slots), "requests": tuple(requests)}
    digest = content_hash({"schema_version": "Phase2ABarBackfillInventoryV1", **body})
    return Phase2ABarBackfillInventoryV1(**body, inventory_id=digest, content_hash=digest)
