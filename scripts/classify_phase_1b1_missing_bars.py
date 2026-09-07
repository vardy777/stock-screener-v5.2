from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.missing_bar_classification import classify_missing_bar_keys  # noqa: E402


PHASE_1B1 = ROOT / "data" / "phase_1b1"
RUNTIME = ROOT / "data" / "phase_1b2a"
UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
COVERAGE_START = "20240101"
COVERAGE_END = "20251231"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _security_intervals():
    intervals = {}
    root = PHASE_1B1 / "raw" / "datahubco_tushare_proxy" / "security_master"
    for path in root.rglob("*.json"):
        for row in _load(path)["provider_payload"]["rows"]:
            candidate = (row.get("list_date") or "99999999", row.get("delist_date") or "99999999")
            if row["ts_code"] not in intervals or candidate < intervals[row["ts_code"]]:
                intervals[row["ts_code"]] = candidate
    intervals["300114.SZ"] = ("20100827", "20250216")
    intervals["302132.SZ"] = ("20250217", "99999999")
    return intervals


def main() -> int:
    universe = _load(PHASE_1B1 / "governance" / f"daily-bar-universe-{UNIVERSE_ID}.json")
    sessions = tuple(session for session in universe["ordered_sessions"] if COVERAGE_START <= session <= COVERAGE_END)
    intervals = _security_intervals()
    observed = set()
    for path in (PHASE_1B1 / "facts" / "daily_bar").rglob("*.json"):
        for fact in _load(path)["facts"]:
            observed.add((fact["security_identity"], fact["session"].replace("-", "")))
    expected = set()
    symbols = tuple(universe["ordered_symbols"]) + (() if "300114.SZ" in universe["ordered_symbols"] else ("300114.SZ",))
    for symbol in symbols:
        start, end = intervals.get(symbol, ("99999999", "00000000"))
        expected.update((symbol, session) for session in sessions if start <= session <= end)
    missing = expected - observed

    full_day, partial, resumes = set(), set(), set()
    root = RUNTIME / "raw" / "datahubco_tushare_proxy" / "suspension_history"
    for path in root.rglob("*.json"):
        for row in _load(path)["provider_payload"]["rows"]:
            date = str(row["trade_date"])
            if not COVERAGE_START <= date <= COVERAGE_END:
                continue
            key = (str(row["ts_code"]), date)
            if row["suspend_type"] == "R":
                resumes.add(key)
            elif row.get("suspend_timing") in (None, ""):
                full_day.add(key)
            else:
                partial.add(key)
    artifact = classify_missing_bar_keys(
        missing,
        full_day_suspensions=full_day,
        partial_suspensions=partial,
        resume_observations=resumes,
        local_exception_keys=set(),
        expected_total=6489,
    )
    body = asdict(artifact)
    body.update({
        "schema_version": "MissingBarClassificationArtifactV1",
        "universe_id": UNIVERSE_ID,
        "daily_bar_approval_id": "1ead49dfaefdfb8e4e75c9d94170d440abe77986e3388a6e96e6805537c1173c",
        "research_eligible": False,
        "status_approval_id": None,
    })
    output = RUNTIME / "governance" / f"missing-bar-classification-{artifact.content_hash}.json"
    output.write_bytes(canonical_json(body))
    print(json.dumps({"total": artifact.total, "counts": dict(artifact.counts),
                      "content_hash": artifact.content_hash, "research_eligible": False}, indent=2))
    print(f"ARTIFACT={output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
