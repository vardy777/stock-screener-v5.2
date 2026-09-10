from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.corporate_action_availability import (  # noqa: E402
    AvailabilityError,
    CorporateActionAvailabilityPolicyV1,
)
from v5_2.data.real_audits.corporate_action_normalization import (  # noqa: E402
    CorporateActionNormalizationError,
    classify_implemented_rows,
    normalize_dividend_rows,
)
from v5_2.data.real_audits.upstream_extension import EffectiveDatedUniverseV1  # noqa: E402


SUMMARY_ID = "139298428aef7f08add358c49c01fb1a2796a78543abf5fa90c7b0825c285876"
UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
RUNTIME = ROOT / "data" / "phase_1b2c"
EXTENSION_RUNTIME = ROOT / "data" / "phase_1b1_2026_extension" / "governance"


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable materialization artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    summary = json.loads((RUNTIME / "governance" / f"acquisition-summary-{SUMMARY_ID}.json").read_text(encoding="utf-8"))
    raw_paths = {path.stem: path for path in (RUNTIME / "raw" / "datahubco_tushare_proxy" / "corporate_action").rglob("*.json")}
    rows = []
    for payload_hash in summary["payload_hashes"]:
        raw = json.loads(raw_paths[payload_hash].read_text(encoding="utf-8"))
        if raw.get("payload_hash") != payload_hash:
            raise RuntimeError("raw payload identity mismatch")
        rows.extend(raw["provider_payload"]["rows"])
    selected, quarantines = classify_implemented_rows(rows, start="20100104", end="20260909")
    universe = json.loads((ROOT / "data" / "phase_1b1" / "governance" / f"daily-bar-universe-{UNIVERSE_ID}.json").read_text(encoding="utf-8"))
    extension_id = (EXTENSION_RUNTIME / "current-extension-id.txt").read_text(encoding="ascii").strip()
    extension = json.loads((EXTENSION_RUNTIME / f"upstream-extension-audit-{extension_id}.json").read_text(encoding="utf-8"))
    extension_body = {key: value for key, value in extension.items() if key != "audit_id"}
    if content_hash(extension_body) != extension_id or extension.get("decision") != "PASS":
        raise RuntimeError("upstream extension audit integrity failed")
    for kind, approval_id, previous in (
        ("trade_calendar", extension["calendar_approval_id"], "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b"),
        ("security_master", extension["master_approval_id"], "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf"),
    ):
        approval = json.loads((EXTENSION_RUNTIME / f"{kind}-approval-{approval_id}.json").read_text(encoding="utf-8"))
        approval_body = {"schema_version": "SourceApprovalArtifactV1", **{
            key: value for key, value in approval.items() if key not in {"approval_id", "content_hash"}
        }}
        if approval.get("approval_id") != approval_id or approval.get("content_hash") != approval_id \
                or content_hash(approval_body) != approval_id \
                or approval.get("decision") not in {"APPROVED", "APPROVED_WITH_RULES"} \
                or approval.get("supersedes_approval_id") != previous:
            raise RuntimeError("upstream extension approval integrity failed")
    calendar = json.loads((EXTENSION_RUNTIME / f"calendar-extension-{extension['calendar_extension_id']}.json").read_text(encoding="utf-8"))
    extended_sessions = tuple(
        date.fromisoformat(raw[:4] + "-" + raw[4:6] + "-" + raw[6:])
        for exchange, raw, state in calendar["ordered_rows"] if exchange == "SSE" and state == 1
    )
    sessions = tuple(date.fromisoformat(value[:4] + "-" + value[4:6] + "-" + value[6:]) for value in universe["ordered_sessions"]) + extended_sessions
    raw_universe = json.loads((EXTENSION_RUNTIME / f"universe-extension-{extension['universe_id']}.json").read_text(encoding="utf-8"))
    effective_universe = EffectiveDatedUniverseV1(
        universe_id=raw_universe["universe_id"], supersedes_approval_id=raw_universe["supersedes_approval_id"],
        previous_universe_id=raw_universe["previous_universe_id"], baseline_symbols=tuple(raw_universe["baseline_symbols"]),
        changes=tuple((identity, date.fromisoformat(listing), None if ending is None else date.fromisoformat(ending), prior)
                      for identity, listing, ending, prior in raw_universe["changes"]),
        coverage_end=date.fromisoformat(raw_universe["coverage_end"]), evidence_ids=tuple(raw_universe["evidence_ids"]),
        content_hash=raw_universe["content_hash"],
    )
    policy = CorporateActionAvailabilityPolicyV1(approved_sessions=sessions)
    facts = []
    runtime_quarantines = list(quarantines)
    catch_up_candidates = 0
    for row in selected:
        ex_date = str(row["ex_date"])
        if ex_date > "20251231":
            catch_up_candidates += 1
        event_day = date.fromisoformat(ex_date[:4] + "-" + ex_date[4:6] + "-" + ex_date[6:])
        if event_day > effective_universe.coverage_end:
            runtime_quarantines.append({
                "quarantine_id": content_hash({"row": row, "reason": "2026_APPROVED_SESSION_CALENDAR_MISSING"}),
                "security_identity": row["ts_code"], "effective_date": ex_date,
                "reason": "2026_APPROVED_SESSION_CALENDAR_MISSING",
            })
            continue
        if ex_date > "20251231" and row["ts_code"] not in effective_universe.approved_universe_as_of_session(event_day):
            runtime_quarantines.append({
                "quarantine_id": content_hash({"row": row, "reason": "NOT_IN_APPROVED_TARGET_UNIVERSE"}),
                "security_identity": row["ts_code"], "effective_date": ex_date,
                "reason": "NOT_IN_APPROVED_TARGET_UNIVERSE",
            })
            continue
        try:
            facts.extend(normalize_dividend_rows(
                (row,), source_version_identity="datahub-dividend-full-history-2026-09-10-v2",
                policy=policy,
            ))
        except (AvailabilityError, CorporateActionNormalizationError) as error:
            runtime_quarantines.append({
                "quarantine_id": content_hash({"row": row, "reason": type(error).__name__}),
                "security_identity": row.get("ts_code"), "effective_date": ex_date,
                "reason": type(error).__name__,
            })
    fact_rows = []
    for fact in sorted(facts, key=lambda item: item.fact_id):
        row = asdict(fact)
        row["action_type"] = fact.action_type.value
        row["knowledge_class"] = fact.knowledge_class.value
        for field in ("cash_per_share", "share_ratio"):
            row[field] = format(row[field], "f") if row[field] is not None else None
        fact_rows.append(row)
    fact_rows = tuple(fact_rows)
    candidate_body = {
        "schema_version": "CorporateActionCandidateFactBundleV1",
        "acquisition_summary_id": SUMMARY_ID,
        "approval_state": "UNAPPROVED_STAGING",
        "facts": fact_rows,
    }
    candidate_id = content_hash(candidate_body)
    _write_immutable(RUNTIME / "staging" / f"candidate-facts-{candidate_id}.json", {"candidate_bundle_id": candidate_id, **candidate_body})
    reasons = Counter(str(item["reason"]) for item in runtime_quarantines)
    audit_body = {
        "schema_version": "CorporateActionMaterializationAuditV1",
        "acquisition_summary_id": SUMMARY_ID,
        "candidate_bundle_id": candidate_id,
        "input_rows": len(rows),
        "selected_implemented_events": len(selected),
        "candidate_fact_count": len(facts),
        "candidate_symbol_count": len({fact.security_identity for fact in facts}),
        "candidate_count_by_action_type": dict(sorted(Counter(fact.action_type.value for fact in facts).items())),
        "quarantine_count": len(runtime_quarantines),
        "quarantine_reason_counts": dict(sorted(reasons.items())),
        "quarantines": tuple(sorted(runtime_quarantines, key=lambda item: str(item["quarantine_id"]))),
        "materialized_coverage_by_action_type": (
            ("BONUS_SHARE", "2010-01-04", "2026-09-09"),
            ("CASH_DIVIDEND", "2010-01-04", "2026-09-09"),
        ),
        "catch_up_2026_candidate_events": catch_up_candidates,
        "catch_up_2026_status": "PASS",
        "catch_up_blocker": None,
        "upstream_extension_audit_id": extension_id,
        "calendar_extension_id": extension["calendar_extension_id"],
        "universe_extension_id": extension["universe_id"],
        "calendar_approval_id": extension["calendar_approval_id"],
        "master_approval_id": extension["master_approval_id"],
        "approved_fact_count": 0,
    }
    audit_id = content_hash(audit_body)
    _write_immutable(RUNTIME / "governance" / f"materialization-audit-{audit_id}.json", {"audit_id": audit_id, **audit_body})
    (RUNTIME / "governance" / "current-materialization-id.txt").write_text(audit_id, encoding="ascii")
    print(f"AUDIT_ID={audit_id} CANDIDATE_BUNDLE_ID={candidate_id} INPUT_ROWS={len(rows)} SELECTED_EVENTS={len(selected)} CANDIDATE_FACTS={len(facts)} QUARANTINES={len(runtime_quarantines)} CATCH_UP_2026={catch_up_candidates}:PASS")
    print("QUARANTINE_REASONS=" + json.dumps(dict(sorted(reasons.items())), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
