from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.status_prospective_sampling import (  # noqa: E402
    ProspectiveStatusCandidateV1, ProspectiveStatusEvidenceContractV1, freeze_prospective_inventory,
)

P1, P2 = ROOT / "data" / "phase_1b1", ROOT / "data" / "phase_1b2a"
UNIVERSE_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"


def artifacts(root, kind):
    for path in root.joinpath("raw", "datahubco_tushare_proxy", kind).rglob("*.json"):
        yield json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    contract = ProspectiveStatusEvidenceContractV1.adopted()
    universe = set(json.loads((P1 / "governance" / f"daily-bar-universe-{UNIVERSE_ID}.json").read_text(encoding="utf-8"))["ordered_symbols"])
    master, master_hash = {}, {}
    for artifact in artifacts(P1, "security_master"):
        for row in artifact["provider_payload"]["rows"]:
            master[row["ts_code"]], master_hash[row["ts_code"]] = row, artifact["payload_hash"]
    sessions = set()
    for artifact in artifacts(P1, "trade_calendar"):
        sessions.update(row["cal_date"] for row in artifact["provider_payload"]["rows"] if row["is_open"] == 1)
    ordered_sessions = sorted(sessions)
    next_session = {day: ordered_sessions[index + 1] for index, day in enumerate(ordered_sessions[:-1])}
    missing = {(item["security_identity"], item["session"]) for item in json.loads(
        (P2 / "governance" / "missing-bar-classification-34612813c3bfdeb233bf41b66796a9ca9e89751062523ca7be30fc4c76f56420.json").read_text(encoding="utf-8"))["items"]}
    names, suspensions = [], []
    for kind, target in (("risk_warning_history", names), ("suspension_history", suspensions)):
        for artifact in artifacts(P2, kind):
            target.extend((row, artifact["payload_hash"]) for row in artifact["provider_payload"]["rows"])
    pools = {key: [] for key, _ in contract.sample_counts}

    def add(semantic, identity, session, value, assertion, expected, evidence):
        row = master.get(identity, {})
        exchange = "SSE" if identity.endswith(".SH") else "SZSE"
        pools[semantic].append(ProspectiveStatusCandidateV1.create(
            security_identity=identity, session=session, exchange=exchange, board=str(row.get("market") or "UNKNOWN"),
            semantic=semantic, provider_value=value, semantic_assertion=assertion, expected_evidence=expected,
            effective_identity=True, confirmed_historically_tradable=identity in universe,
            provider_evidence_ids=tuple(evidence)))

    ordinary_day = "20250102"
    risk_on_day = {row["ts_code"] for row, _ in names if "ST" in str(row.get("name", "")).upper()
                   and row.get("start_date", "99999999") <= ordinary_day
                   and (not row.get("end_date") or ordinary_day <= row["end_date"])}
    suspended_on_day = {row["ts_code"] for row, _ in suspensions
                        if row.get("trade_date") == ordinary_day and row.get("suspend_type") == "S"}
    for identity in sorted(universe):
        row = master.get(identity, {})
        if (row.get("list_date", "99999999") <= ordinary_day
                and (not row.get("delist_date") or ordinary_day < row["delist_date"])
                and (identity, ordinary_day) not in missing and identity not in risk_on_day
                and identity not in suspended_on_day):
            add("ACTIVE_ORDINARY_STATUS", identity, ordinary_day, "NORMAL_TRADABLE",
                "effective target identity traded and was not risk-warning or suspended at D close",
                "independent daily tradestatus=1 and isST=0", (master_hash[identity], UNIVERSE_ID))
    for identity, row in master.items():
        if identity not in universe:
            continue
        if row.get("list_date") in sessions:
            add("ACTUAL_FIRST_TRADABLE_SESSION", identity, row["list_date"], row["list_date"],
                "provider master asserts first listed session", "official listing anchor plus independent first daily record", (master_hash[identity],))
        if row.get("delist_date") in sessions:
            add("DELISTING_BOUNDARY", identity, row["delist_date"], row["delist_date"],
                "provider master asserts delisting effective boundary", "official delisting anchor and no trading from effective date", (master_hash[identity],))
    for row, evidence in names:
        identity = row["ts_code"]
        if identity not in universe or "ST" not in str(row.get("name", "")).upper():
            continue
        if row.get("start_date") in sessions:
            add("ST_ENTER", identity, row["start_date"], row["name"], "risk-warning state effective on session",
                "independent daily isST=1", (evidence,))
        end = row.get("end_date")
        if end in next_session:
            exit_day = next_session[end]
            add("ST_EXIT", identity, exit_day, "CLEAR_AFTER_INTERVAL", "risk-warning interval ended before session",
                "independent daily isST=0", (evidence,))
    for row, evidence in suspensions:
        identity, session = row["ts_code"], row["trade_date"]
        if identity not in universe or session not in sessions:
            continue
        if row["suspend_type"] == "S" and not row.get("suspend_timing"):
            add("FULL_DAY_SUSPENSION", identity, session, "S", "full-day suspension on session",
                "independent daily tradestatus=0", (evidence,))
        elif row["suspend_type"] == "R":
            add("RESUMPTION", identity, session, "R", "trading resumed on session",
                "independent daily tradestatus=1", (evidence,))
    pools["IDENTITY_TRANSITION"].append(ProspectiveStatusCandidateV1.create(
        security_identity="300114.SZ", session="20250214", exchange="SZSE", board="创业板",
        semantic="IDENTITY_TRANSITION", provider_value="300114 through T-1; 302132 from 20250217",
        semantic_assertion="non-overlapping old/new effective identity chain",
        expected_evidence="SZSE-hosted effective-code notice", effective_identity=True,
        confirmed_historically_tradable=True, provider_evidence_ids=("300114-to-302132-v1",)))
    inventory = freeze_prospective_inventory(contract, {key: tuple(value) for key, value in pools.items()})
    body = {"schema_version": "ProspectiveStatusSampleInventoryV1", **asdict(inventory)}
    output = P2 / "governance" / f"prospective-status-sample-inventory-{inventory.inventory_id}.json"
    output.write_bytes(canonical_json(body))
    contract_path = P2 / "governance" / f"prospective-status-evidence-contract-{contract.contract_id}.json"
    contract_path.write_bytes(canonical_json({"schema_version": "ProspectiveStatusEvidenceContractV1", **asdict(contract)}))
    print(json.dumps({"contract_id": contract.contract_id, "inventory_id": inventory.inventory_id,
                      "sample_count": len(inventory.samples), "counts": dict(inventory.counts)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
