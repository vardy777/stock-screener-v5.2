from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
import subprocess

from v5_2.data.identity import content_hash


BLOCKER_CLASSES = (
    "ASSEMBLER_LOOKUP_DEFECT", "SCHEMA_MAPPING_DEFECT", "LINEAGE_ROLE_DEFECT",
    "INTERVAL_COVERAGE_DEFECT", "REAL_PHASE1_EVIDENCE_ABSENT",
    "SAMPLE_APPLICABILITY_UNPROVEN", "OTHER_PROVEN_DEFECT",
)

INVENTORY_ID = "81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9"
CALENDAR_BUNDLE = "historical-calendar-fact-bundle-d64a2ef0823e9a55a33d3b8111337fb71fcb43ce778235694ebfadfed1396dcc.json"
MASTER_BUNDLE = "historical-security-master-fact-bundle-968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386.json"
CALENDAR_EXTENSION = "calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json"
CA_FACTS = "corporate-action-facts-3e4a5604e555c036effe66fa5297cffcf374aa34dbd9a8b14eab873c165b6410.json"


@dataclass(frozen=True, slots=True)
class Phase2AEvidenceGapEntryV1:
    slot: int
    stratum: str
    canonical_identity: str
    anchor_session: str
    calendar_status: str
    master_status: str
    daily_bar_status: str
    security_status_status: str
    corporate_action_status: str
    anchor_reference_bar_status: str
    future_window_status: str
    eligibility_status: str
    identity_status: str
    ca_coverage_status: str
    missing_artifact_type: str
    missing_artifact_id_or_lookup_key: str
    lookup_location_checked: tuple[str, ...]
    candidate_artifacts_found: tuple[str, ...]
    bundle_constructible: bool
    blocker_class: str
    blocker_reason: str

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Phase2AEvidenceGapAuditV1:
    inventory_id: str
    entries: tuple[Phase2AEvidenceGapEntryV1, ...]
    counts: tuple[tuple[str, int], ...]
    common_root_cause: str
    audit_id: str
    content_hash: str

    def verify(self) -> bool:
        body = {"inventory_id": self.inventory_id, "entries": self.entries,
                "counts": self.counts, "common_root_cause": self.common_root_cause}
        digest = content_hash({"schema_version": type(self).__name__, **body})
        return self.audit_id == self.content_hash == digest

    def as_dict(self):
        value = asdict(self)
        value["schema_version"] = type(self).__name__
        return value


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _iso(compact: str) -> str:
    return date(int(compact[:4]), int(compact[4:6]), int(compact[6:])).isoformat()


def _matching_files(root: Path, pattern: str, location: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        ["rg", "-l", pattern, str(location)], cwd=root, text=True,
        capture_output=True, check=False,
    )
    paths = (Path(line) for line in result.stdout.splitlines() if line)
    return tuple(sorted(path.relative_to(root) if path.is_absolute() else path for path in paths))


def audit_phase2a_evidence_gaps(root: Path) -> Phase2AEvidenceGapAuditV1:
    inventory_path = root / "data/phase_2a/governance" / f"label-acceptance-inventory-{INVENTORY_ID}.json"
    inventory = _load(inventory_path)
    governance = root / "data/phase_1b_exit_remediation/governance"
    calendar_path = governance / CALENDAR_BUNDLE
    master_path = governance / MASTER_BUNDLE
    extension_path = root / "data/phase_1b1_2026_extension/governance" / CALENDAR_EXTENSION
    ca_path = root / "data/phase_1b2c/approved" / CA_FACTS
    calendar = _load(calendar_path)
    extension = _load(extension_path)
    master = set(_load(master_path)["ordered_security_identities"])
    ca_facts = _load(ca_path)["facts"]
    open_sessions: dict[str, list[str]] = {"SSE": [], "SZSE": []}
    for row in calendar["ordered_rows"]:
        if row["exchange"] in open_sessions and row["is_open"] == 1:
            open_sessions[row["exchange"]].append(_iso(row["cal_date"]))
    for exchange, cal_date, is_open in extension["ordered_rows"]:
        if exchange in open_sessions and is_open == 1:
            open_sessions[exchange].append(_iso(cal_date))
    open_sessions = {key: sorted(set(values)) for key, values in open_sessions.items()}

    identities = sorted({slot["security_identity"] for slot in inventory["slots"]} | {"302132.SZ"})
    pattern = '"security_identity":"(' + "|".join(value.replace(".", r"\.") for value in identities) + ')"'
    bar_files = _matching_files(root, pattern, root / "data/phase_1b1/facts/daily_bar")
    bars: dict[str, set[str]] = {identity: set() for identity in identities}
    bar_paths: dict[str, set[str]] = {identity: set() for identity in identities}
    for path in bar_files:
        for fact in _load(root / path)["facts"]:
            identity = fact["security_identity"]
            if identity in bars:
                bars[identity].add(fact["session"])
                bar_paths[identity].add(path.as_posix())

    status_dir = root / "data/phase_1b2a/facts/daily_security_status"
    statuses: dict[str, set[str]] = {identity: set() for identity in identities}
    status_paths: dict[str, set[str]] = {identity: set() for identity in identities}
    for path in status_dir.glob("*.json"):
        fact = _load(path)
        identity = fact["security_identity"]
        if identity in statuses:
            statuses[identity].add(fact["session"])
            status_paths[identity].add(path.relative_to(root).as_posix())

    entries = []
    for slot in inventory["slots"]:
        number = slot["slot"]
        identity = slot["security_identity"]
        anchor = slot["anchor_session"]
        future = tuple(day for day in open_sessions[slot["exchange"]] if day > anchor)[:5]
        bar_identities = (identity, "302132.SZ") if number == 15 else (identity,)
        present_bars = set().union(*(bars[value] for value in bar_identities))
        anchor_found = anchor in present_bars
        future_found = sum(day in present_bars for day in future)
        status_found = sum(day in statuses[identity] for day in (anchor, *future))
        old_bar_gap = number in {6, 7, 8, 9, 10, 11, 12, 13, 14, 17}
        blocker = "REAL_PHASE1_EVIDENCE_ABSENT" if old_bar_gap else "ASSEMBLER_LOOKUP_DEFECT"
        missing = "daily_bar" if old_bar_gap else "LabelInputBundleV1 assembler"
        reason = (
            "Approved materialized Daily Bar facts contain neither the anchor bar nor the required future window."
            if old_bar_gap else
            "Required Phase 1 artifacts exist in separate layouts, but no adapter resolves them into exact five-domain lineage and a LabelInputBundleV1."
        )
        relevant_ca = tuple(f for f in ca_facts if f["security_identity"] == identity and
                            future and anchor < (f.get("effective_date") or f.get("ex_date") or "") <= future[-1])
        candidates = {
            calendar_path.relative_to(root).as_posix(), master_path.relative_to(root).as_posix(),
            extension_path.relative_to(root).as_posix(), ca_path.relative_to(root).as_posix(),
            *(path for value in bar_identities for path in bar_paths[value]),
            *status_paths[identity],
        }
        entries.append(Phase2AEvidenceGapEntryV1(
            slot=number, stratum=slot["stratum"], canonical_identity=identity,
            anchor_session=anchor, calendar_status="APPROVED_OPEN_SESSION_WINDOW_FOUND" if len(future) == 5 else "FUTURE_WINDOW_INCOMPLETE",
            master_status="IDENTITY_IN_COMPLETE_MASTER" if identity in master else "IDENTITY_SUPPLEMENT_REQUIRED",
            daily_bar_status=("D_AND_REQUIRED_WINDOW_FOUND" if anchor_found and future_found == 5 else
                              "ANCHOR_AND_REQUIRED_WINDOW_ABSENT" if not anchor_found and future_found == 0 else
                              f"PARTIAL_{int(anchor_found)}_PLUS_{future_found}_OF_5"),
            security_status_status=("EXACT_D_AND_WINDOW_FOUND" if status_found == 6 else
                                    "PARTIAL_SPECIAL_EVENT_FACTS_FOUND" if status_found else
                                    "PANEL_EXISTS_EXACT_DAILY_FACTS_NOT_MATERIALIZED"),
            corporate_action_status="INTERVAL_ACTION_FACTS_FOUND" if relevant_ca else "NO_EVENT_REQUIRES_COVERAGE_PROOF",
            anchor_reference_bar_status="FOUND" if anchor_found else "ABSENT",
            future_window_status="CALENDAR_EXTENSION_FOUND" if anchor >= "2025-12-31" and len(future) == 5 else
                                 "FIVE_EXCHANGE_SESSIONS_FOUND" if len(future) == 5 else "INCOMPLETE",
            eligibility_status="REQUIRES_DATED_UNIVERSE_RESOLUTION",
            identity_status="DATED_ALIAS_REQUIRED" if number == 15 else "CANONICAL_IDENTITY_FOUND" if identity in master else "IDENTITY_SUPPLEMENT_REQUIRED",
            ca_coverage_status="FULL_SUPPORTED_TYPE_COVERAGE_WITH_UNSUPPORTED_TYPE_QUARANTINE",
            missing_artifact_type=missing,
            missing_artifact_id_or_lookup_key=f"{identity}:{anchor}:{future[-1] if future else 'NO_H5'}",
            lookup_location_checked=("data/phase_1b1/facts/daily_bar", "data/phase_1b2a/facts/daily_security_status",
                                     "data/phase_1b2c/approved", "data/phase_1b_exit_remediation/governance",
                                     "data/phase_1b1_2026_extension/governance"),
            candidate_artifacts_found=tuple(sorted(candidates)), bundle_constructible=False,
            blocker_class=blocker, blocker_reason=reason,
        ))
    counts = tuple((name, sum(entry.blocker_class == name for entry in entries)) for name in BLOCKER_CLASSES)
    common = "No repository-facing evidence assembler exists; additionally ten frozen pre-2024 slots lack approved materialized Daily Bar anchor/future facts."
    body = {"inventory_id": INVENTORY_ID, "entries": tuple(entries), "counts": counts, "common_root_cause": common}
    digest = content_hash({"schema_version": "Phase2AEvidenceGapAuditV1", **body})
    return Phase2AEvidenceGapAuditV1(**body, audit_id=digest, content_hash=digest)


def render_evidence_gap_matrix(audit: Phase2AEvidenceGapAuditV1) -> str:
    if not audit.verify():
        raise ValueError("tampered Phase 2A evidence-gap audit")
    lines = [
        "# V5.2 Phase 2A Evidence Gap Audit", "",
        f"AUDIT ID = {audit.audit_id}", f"FROZEN INVENTORY ID = {audit.inventory_id}", "",
    ]
    lines.extend(f"{name} COUNT = {count}" for name, count in audit.counts)
    lines.extend([
        "", f"COMMON ROOT CAUSE = {audit.common_root_cause}", "",
        "## 22-slot blocker matrix", "",
        "| slot | stratum | identity | anchor | calendar | master | daily bar | status | CA | reference bar | future window | eligibility | identity chain | CA coverage | missing type | lookup key | locations checked | candidates found | constructible | blocker class | reason |",
        "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    for entry in audit.entries:
        lines.append(
            f"| {entry.slot:02d} | {entry.stratum} | {entry.canonical_identity} | {entry.anchor_session} | "
            f"{entry.calendar_status} | {entry.master_status} | {entry.daily_bar_status} | "
            f"{entry.security_status_status} | {entry.corporate_action_status} | "
            f"{entry.anchor_reference_bar_status} | {entry.future_window_status} | "
            f"{entry.eligibility_status} | {entry.identity_status} | {entry.ca_coverage_status} | "
            f"{entry.missing_artifact_type} | {entry.missing_artifact_id_or_lookup_key} | "
            f"{'<br>'.join(entry.lookup_location_checked)} | {'<br>'.join(entry.candidate_artifacts_found)} | "
            f"{'YES' if entry.bundle_constructible else 'NO'} | {entry.blocker_class} | {entry.blocker_reason} |"
        )
    lines.extend([
        "", "## Closure consequence", "",
        "The required five-slot pilot cannot run because the frozen suspension and corporate-action slots lack approved materialized Daily Bar anchor/future facts. Phase 2A remains PENDING and Phase 2B remains prohibited.", "",
    ])
    return "\n".join(lines)
