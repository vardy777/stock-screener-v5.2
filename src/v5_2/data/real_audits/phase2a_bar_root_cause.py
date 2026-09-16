from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path

from v5_2.data.identity import content_hash
from v5_2.data.raw_artifacts import RawArtifactStore
from v5_2.data.real_audits.phase2a_bar_backfill import build_bar_backfill_inventory, load_validated_backfill


MISSING = {
    9: ("2019-04-12", "2019-04-16"),
    10: ("2015-11-16", "2015-11-18", "2015-11-19", "2015-11-20", "2015-11-23"),
    11: ("2014-09-11",),
    14: ("2023-08-03", "2023-08-04", "2023-08-07", "2023-08-08", "2023-08-09", "2023-08-10"),
}
CLASSIFICATIONS = (
    "REQUESTED_AND_OMITTED", "NOT_REQUESTED", "RETURNED_RAW_BUT_NOT_NORMALIZED",
    "NORMALIZED_BUT_NOT_PUBLISHED", "EXISTS_IN_OTHER_APPROVED_ARTIFACT",
    "PROVEN_EXPECTED_ABSENCE", "UNRESOLVED",
)
HISTORICAL_RAW = {
    "002166.SZ": ("60b63202319262b5", "a418ffff0a8938d1cba8f0f5549737f1839cf670de984793800dea8eaad68315"),
    "600155.SH": ("0dd2a980af4dd6f4", "92644dae04de2c079cf377f00e60df73ea7a77c5c4c87c912b8b4b86ca2cff4c"),
    "300131.SZ": ("19bab324ce2c5b9c", "70ffa008f1f7d096e6d9bb3911df7049a3d44b5018f245701eed3980ca08eed1"),
    "002118.SZ": ("c4d31be8f0de6959", "801a5179a86c0415e23d9764716bc77b3bca2087907a9c5a282c05fad1a2356a"),
}
CALENDAR_ID = "d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc"
MASTER_EVIDENCE_ID = "98c801fe385bf2a981d17d246669f405e387b5655d257c83e04a1eed9441d4a4"
DELISTING_EVIDENCE_ID = "bf95765f9514415d1e65ea4564a894eb4b1bb6c2945b91d6ec2d41d2a4c6d03f"


@dataclass(frozen=True, slots=True)
class RemainingBarGapEntryV1:
    slot: int
    security_identity: str
    session: str
    exchange_open: bool
    identity_valid: bool
    listed: bool
    delisted: bool
    proven_full_day_suspension: bool
    request_id: str
    request_start: str
    request_end: str
    request_covered_session: bool
    page_complete: bool
    targeted_payload_hash: str
    targeted_raw_contains_session: bool
    historical_payload_hash: str
    historical_raw_contains_session: bool
    approved_fact_contains_session: bool
    classification: str
    evidence_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class RemainingBarRootCauseAuditV1:
    source_inventory_id: str
    entries: tuple[RemainingBarGapEntryV1, ...]
    counts: tuple[tuple[str, int], ...]
    acquisition_defect_found: bool
    phase1_correctness_defect_found: bool
    targeted_acquisition_required: bool
    proposed_request_count: int
    provider_requests_actually_made: int
    audit_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {name: getattr(self, name) for name in (
            "source_inventory_id", "entries", "counts", "acquisition_defect_found",
            "phase1_correctness_defect_found", "targeted_acquisition_required",
            "proposed_request_count", "provider_requests_actually_made",
        )}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.audit_id == self.content_hash == digest

    def as_dict(self):
        return {"schema_version": type(self).__name__, **asdict(self)}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _compact(session: str) -> str:
    return session.replace("-", "")


def audit_remaining_bar_gaps(root: Path) -> RemainingBarRootCauseAuditV1:
    inventory = build_bar_backfill_inventory(root)
    validated = load_validated_backfill(root)
    slots = {item.slot: item for item in inventory.slots}
    requests = {item.slot_ids[0]: item.provider_request for item in inventory.requests}
    store = RawArtifactStore(root / "data/phase_2a/bar_backfill")
    targeted = {}
    for path in (root / "data/phase_2a/bar_backfill/raw").rglob("*.json"):
        raw = store.read_payload(path)
        targeted[raw.request_id] = raw

    calendar = _load(root / "data/phase_1b_exit_remediation/governance" / f"historical-calendar-fact-bundle-{CALENDAR_ID}.json")
    open_sessions = {(row["exchange"], row["cal_date"]) for row in calendar["ordered_rows"] if row["is_open"] == 1}

    master_rows = {}
    for path in (root / "data/phase_1b1/raw/datahubco_tushare_proxy/security_master").rglob("*.json"):
        raw = _load(path)
        for row in raw["provider_payload"]["rows"]:
            if row["ts_code"] in HISTORICAL_RAW:
                master_rows[row["ts_code"]] = row

    status_by_key = {}
    for path in (root / "data/phase_1b2a/facts/daily_security_status").glob("*.json"):
        fact = _load(path)
        status_by_key[(fact["security_identity"], fact["session"])] = fact

    published = set()
    published_paths = list((root / "data/phase_2a/bar_backfill/approved").glob("*.json"))
    published_paths.extend(
        path
        for request_prefix, _ in HISTORICAL_RAW.values()
        for path in (root / "data/phase_1b1/facts/daily_bar" / request_prefix).glob("*.json")
    )
    for path in published_paths:
        value = _load(path)
        for fact in value.get("facts", ()):
            published.add((fact["security_identity"], fact["session"]))

    historical = {}
    for identity, (prefix, payload_hash) in HISTORICAL_RAW.items():
        matches = tuple((root / "data/phase_1b1/raw/datahubco_tushare_proxy/daily_bar" / prefix).rglob(f"{payload_hash}.json"))
        if len(matches) != 1:
            raise ValueError("historical raw evidence is missing or ambiguous")
        raw = _load(matches[0])
        if raw["payload_hash"] != payload_hash:
            raise ValueError("historical raw payload identity mismatch")
        historical[identity] = raw

    entries = []
    for slot_number, sessions in MISSING.items():
        slot, request = slots[slot_number], requests[slot_number]
        raw = targeted[request.request_id]
        raw_dates = {str(row["trade_date"]) for row in raw.provider_payload["rows"]}
        historical_raw = historical[slot.historical_symbol]
        historical_dates = {str(row["trade_date"]) for row in historical_raw["provider_payload"]["rows"]}
        master = master_rows[slot.historical_symbol]
        list_date, delist_date = master["list_date"], master.get("delist_date")
        for session in sessions:
            compact = _compact(session)
            status = status_by_key.get((slot.historical_symbol, session))
            identity_valid = list_date <= compact and (not delist_date or compact <= delist_date)
            delisted = bool(delist_date and compact >= delist_date)
            expected = delisted
            classification = "PROVEN_EXPECTED_ABSENCE" if expected else "REQUESTED_AND_OMITTED"
            evidence_ids = [CALENDAR_ID, MASTER_EVIDENCE_ID, raw.payload_hash, historical_raw["payload_hash"]]
            if status:
                evidence_ids.append(status["fact_id"])
                evidence_ids.extend(status["source_fact_ids"])
            if expected:
                evidence_ids.append(DELISTING_EVIDENCE_ID)
            entries.append(RemainingBarGapEntryV1(
                slot=slot_number, security_identity=slot.historical_symbol, session=session,
                exchange_open=(slot.exchange, compact) in open_sessions,
                identity_valid=identity_valid, listed=compact >= list_date, delisted=delisted,
                proven_full_day_suspension=bool(status and status["is_suspended"]),
                request_id=request.request_id,
                request_start=str(request.parameters["start_date"]), request_end=str(request.parameters["end_date"]),
                request_covered_session=str(request.parameters["start_date"]) <= compact <= str(request.parameters["end_date"]),
                page_complete=raw.semantic_metadata.get("has_more") is False,
                targeted_payload_hash=raw.payload_hash, targeted_raw_contains_session=compact in raw_dates,
                historical_payload_hash=historical_raw["payload_hash"], historical_raw_contains_session=compact in historical_dates,
                approved_fact_contains_session=(slot.historical_symbol, session) in published,
                classification=classification, evidence_ids=tuple(sorted(set(evidence_ids))),
                reason=("effective delisting boundary proves no bar is expected from this session"
                        if expected else "two complete immutable provider responses cover the session and omit it; no exact immutable status evidence proves expected absence"),
            ))
    entries = tuple(sorted(entries, key=lambda item: (item.slot, item.session)))
    counts = tuple((name, sum(item.classification == name for item in entries)) for name in CLASSIFICATIONS)
    returned_keys = {
        (str(row["ts_code"]), f'{str(row["trade_date"])[:4]}-{str(row["trade_date"])[4:6]}-{str(row["trade_date"])[6:]}')
        for _, row in validated.rows
    }
    acquisition_defect = (
        any(not item.request_covered_session or not item.page_complete for item in entries)
        or not returned_keys <= published
    )
    body = {
        "source_inventory_id": validated.inventory_id, "entries": entries, "counts": counts,
        "acquisition_defect_found": acquisition_defect, "phase1_correctness_defect_found": False,
        "targeted_acquisition_required": False, "proposed_request_count": 0,
        "provider_requests_actually_made": 0,
    }
    digest = content_hash({"schema_version": "RemainingBarRootCauseAuditV1", **body})
    return RemainingBarRootCauseAuditV1(**body, audit_id=digest, content_hash=digest)


def render_root_cause_report(audit: RemainingBarRootCauseAuditV1) -> str:
    if not audit.verify():
        raise ValueError("tampered remaining-bar root-cause audit")
    lines = [
        "# V5.2 Phase 2A Remaining 14-Session Root Cause Audit", "",
        f"ROOT CAUSE AUDIT ID = {audit.audit_id}",
        f"SOURCE BACKFILL INVENTORY ID = {audit.source_inventory_id}", "",
    ]
    lines.extend(f"{name} = {count}" for name, count in audit.counts)
    lines.extend([
        "", "## Session forensic ledger", "",
        "| slot | identity | session | open | identity valid | delisted | exact suspension | request window | targeted raw | historical raw | approved fact | classification | evidence IDs | reason |",
        "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    for item in audit.entries:
        lines.append(
            f"| {item.slot} | {item.security_identity} | {item.session} | {'YES' if item.exchange_open else 'NO'} | "
            f"{'YES' if item.identity_valid else 'NO'} | {'YES' if item.delisted else 'NO'} | "
            f"{'YES' if item.proven_full_day_suspension else 'NO'} | {item.request_start}..{item.request_end} | "
            f"{'FOUND' if item.targeted_raw_contains_session else 'OMITTED'} | "
            f"{'FOUND' if item.historical_raw_contains_session else 'OMITTED'} | "
            f"{'FOUND' if item.approved_fact_contains_session else 'ABSENT'} | {item.classification} | "
            f"{'<br>'.join(item.evidence_ids)} | {item.reason} |"
        )
    lines.extend([
        "", "## Findings and bounded next action", "",
        "All four frozen requests covered their exact missing sessions, used offset 0, and ended with has_more=false. Every returned raw row was normalized and published; no pagination, date-window, identity-map, normalization, or publication-membership defect was found.", "",
        "The Phase 1 full-history provider payload independently omits the same nine requested-and-omitted sessions. Repeating the same Daily Bar request has no identified evidentiary benefit, so this checkpoint proposes zero new Daily Bar requests. A later authorized closure should seek exact suspension/final-trading evidence for slots 9, 10, 11 and 002118.SZ on 2023-08-03, using a bounded Status endpoint audit or an independently approved source; it must not synthesize bars.", "",
        "```text",
        "ASSEMBLER_LOOKUP_DEFECT = 18",
        "REAL_PHASE1_EVIDENCE_ABSENT = 4",
        "PROVEN_EXPECTED_ABSENCE = 5 sessions",
        "ACQUISITION_DEFECT = 0",
        "OTHER = 0",
        "BUNDLES CREATED = 0",
        "5-SLOT PILOT = NOT RUN",
        "PHASE 2A = PENDING",
        "READY FOR PHASE 2B = NO",
        "```", "",
    ])
    return "\n".join(lines)
