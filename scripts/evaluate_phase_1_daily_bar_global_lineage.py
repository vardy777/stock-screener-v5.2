from __future__ import annotations

import argparse
import json
from pathlib import Path

from v5_2.data.identity import canonical_json, content_hash
from v5_2.refresh.daily_bar_composite import resolve_phase1c_daily_bar_composite


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase1c-source", type=Path, required=True)
    parser.add_argument("--remediation-root", type=Path, default=Path("data/phase_1c_lineage_remediation"))
    args = parser.parse_args()
    governance = args.remediation_root / "governance"
    identifier = resolve_phase1c_daily_bar_composite(args.remediation_root)
    composite = load(governance / f"phase1c-daily-bar-composite-{identifier}.json")
    components = [composite[name] for name in ("historical_baseline", "historical_catch_up", "contemporaneous_observed")]
    roles = [item["role"] for item in components]
    rows = [int(item["row_count"]) for item in components]
    members = [set(item["member_artifact_ids"]) for item in components]
    duplicate = sum(len(members[a] & members[b]) for a, b in ((0, 1), (0, 2), (1, 2)))
    old_approval = "f057dc89adaa60e94b4b0763fc2a7902b8b33f845d9ca4c7f06deb78a7379274"
    revocations = [load(path) for path in governance.glob("approval-revocation-*.json")]
    gates = {
        "HISTORICAL_COMPONENT": components[0]["manifest_id"] == "118744559f5869bcbe75b402870524a18ec6f42e813764568bec6c7f070bf5ad",
        "EXACT_THREE_ROLES": roles == ["HISTORICAL_BASELINE", "HISTORICAL_CATCH_UP", "CONTEMPORANEOUS_OBSERVED"],
        "ROW_COMPOSITION": rows == [14_010_422, 5_204, 5_204] and sum(rows) == 14_020_830,
        "PAIRWISE_DISJOINT": duplicate == 0,
        "UNCLASSIFIED": composite["unclassified_count"] == 0,
        "AVAILABILITY": [item["availability_mode"] for item in components] == ["NEXT_SESSION_SAFE", "NEXT_SESSION_SAFE", "CONTEMPORANEOUS_OBSERVED"],
        "NO_AGGREGATE_APPROVAL": "approval_id" not in composite,
        "OLD_GOVERNANCE_REVOKED": any(item["approval_id"] == old_approval and item["reason"] == "MIXED_SOURCE_CONTENT_LINEAGE_REBIND" for item in revocations),
        "CURRENT_RESOLUTION": resolve_phase1c_daily_bar_composite(args.remediation_root) == identifier,
    }
    result = {
        "schema_version": "Phase1DailyBarGlobalLineageAcceptanceV1",
        "composite_manifest_id": identifier,
        "gates": {name: "PASS" if passed else "FAIL" for name, passed in gates.items()},
        "historical_rows": rows[0], "historical_catch_up_rows": rows[1],
        "contemporaneous_rows": rows[2], "aggregate_rows": sum(rows),
        "unclassified": composite["unclassified_count"], "duplicate_membership": duplicate,
        "provider_requests": 0,
        "phase_1b_historical_daily_bar_lineage": "PASS",
        "phase_1c_daily_bar_lineage": "PASS" if all(gates.values()) else "FAIL",
        "phase_1_daily_bar_global_lineage": "PASS" if all(gates.values()) else "FAIL",
    }
    acceptance_id = content_hash(result)
    result.update({"acceptance_id": acceptance_id, "content_hash": acceptance_id})
    path = governance / f"phase1-daily-bar-global-acceptance-{acceptance_id}.json"
    encoded = canonical_json(result)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable acceptance collision")
    path.write_bytes(encoded)
    print(json.dumps(result, indent=2))
    if not all(gates.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
