from __future__ import annotations

import argparse
import json
from pathlib import Path

from v5_2.data.identity import canonical_json, content_hash
from v5_2.refresh.daily_bar_composite import resolve_phase1c_daily_bar_composite
from evaluate_phase_1b_exit import load_and_verify_lineage


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
    union_members = tuple(sorted(set().union(*members)))
    composite_membership_digest = content_hash(union_members)
    source_manifest = load(
        args.phase1c_source / "governance"
        / "daily_bar-manifest-2fa12e2cfdcb35db45266c86631822b015111e33c10c4aa484889c30d1365ddf.json")
    expected_members = tuple(sorted(source_manifest["fact_content_hashes"]))
    expected_membership_digest = content_hash(expected_members)
    bindings = []
    for item in components:
        matches = tuple(governance.glob(f"*-binding-{item['binding_id']}.json"))
        if len(matches) != 1:
            raise RuntimeError("component binding artifact is missing or ambiguous")
        bindings.append(load(matches[0]))
    duplicate = sum(len(members[a] & members[b]) for a, b in ((0, 1), (0, 2), (1, 2)))
    old_approval = "f057dc89adaa60e94b4b0763fc2a7902b8b33f845d9ca4c7f06deb78a7379274"
    old_component_approvals = {
        "31d91fd99630e3b63b585ae598e7728fe1922454c3dbee276d0ffe9e7b24d79f",
        "4026913c2f107864849219ecf3d63f6a47d7b31d61b5d030dfecacb58ddd9164",
        "c0d8955966d66c9727f37213d8933b7bb9e46fffbc6538581e055c5a1d449e0e",
    }
    revocations = [load(path) for path in governance.glob("approval-revocation-*.json")]
    revoked_ids = {item["approval_id"] for item in revocations}
    phase1b_lineage = load_and_verify_lineage(Path.cwd())
    phase1b_daily_bar_pass = phase1b_lineage["daily_bar"]["valid"]
    gates = {
        "HISTORICAL_COMPONENT": (
            components[0]["row_count"] == 14_010_422 and phase1b_daily_bar_pass
        ),
        "EXACT_THREE_ROLES": roles == ["HISTORICAL_BASELINE", "HISTORICAL_CATCH_UP", "CONTEMPORANEOUS_OBSERVED"],
        "ROW_COMPOSITION": rows == [14_010_422, 5_204, 5_204] and sum(rows) == 14_020_830,
        "PAIRWISE_DISJOINT": duplicate == 0,
        "UNION_COMPLETENESS": (
            expected_membership_digest == composite_membership_digest
            == composite["expected_membership_digest"]
            == composite["aggregate_membership_digest"]
            and expected_members == union_members
        ),
        "UNCLASSIFIED": composite["unclassified_count"] == 0,
        "AVAILABILITY": [item["availability_mode"] for item in components] == ["NEXT_SESSION_SAFE", "NEXT_SESSION_SAFE", "CONTEMPORANEOUS_OBSERVED"],
        "SOURCE_SEMANTIC_CONTRACT": (
            {item["source_semantic_identity"] for item in components}
            == {item["source_semantic_identity"] for item in bindings}
            and {item["source_semantic_contract_version"] for item in bindings}
            == {"daily-bar-semantic-contract-v2"}
            and [item["availability_policy_version"] for item in bindings] == [
                "daily-bar-availability-v1:NEXT_SESSION_SAFE",
                "daily-bar-availability-v1:NEXT_SESSION_SAFE",
                "daily-bar-availability-v1:CONTEMPORANEOUS_OBSERVED",
            ]
        ),
        "NO_AGGREGATE_APPROVAL": "approval_id" not in composite,
        "OLD_GOVERNANCE_REVOKED": (
            old_approval in revoked_ids and old_component_approvals <= revoked_ids
        ),
        "CURRENT_RESOLUTION": resolve_phase1c_daily_bar_composite(args.remediation_root) == identifier,
    }
    result = {
        "schema_version": "Phase1DailyBarGlobalLineageAcceptanceV1",
        "composite_manifest_id": identifier,
        "gates": {name: "PASS" if passed else "FAIL" for name, passed in gates.items()},
        "historical_rows": rows[0], "historical_catch_up_rows": rows[1],
        "contemporaneous_rows": rows[2], "aggregate_rows": sum(rows),
        "unclassified": composite["unclassified_count"], "duplicate_membership": duplicate,
        "expected_membership_digest": expected_membership_digest,
        "composite_membership_digest": composite_membership_digest,
        "provider_requests": 0,
        "phase_1b_historical_daily_bar_lineage": (
            "PASS" if phase1b_daily_bar_pass else "FAIL"
        ),
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
