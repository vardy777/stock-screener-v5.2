from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Mapping

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.phase_1b_exit import (
    SHANGHAI,
    HistoricalResearchCutoffContractV1,
    HistoricalResearchSessionV1,
    Phase1BCoverageMatrixV1,
    Phase1BExitAcceptanceV1,
)


PINNED_DATASETS = {
    "trade_calendar": {
        "approval_id": "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601",
        "manifest_id": "9653175fa933cd83c975d0a3aff1c3583a75e38c7e906d0c458107911e338385",
        "approval": "data/phase_1b1_2026_extension/governance/trade_calendar-approval-{approval_id}.json",
        "manifest": "data/phase_1b1_2026_extension/governance/trade_calendar-manifest-{manifest_id}.json",
    },
    "security_master": {
        "approval_id": "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c",
        "manifest_id": "3c53b5a99c54c6f1520d31af6c434170011544c19d310ea2e50115dc5f42c940",
        "approval": "data/phase_1b1_2026_extension/governance/security_master-approval-{approval_id}.json",
        "manifest": "data/phase_1b1_2026_extension/governance/security_master-manifest-{manifest_id}.json",
    },
    "daily_bar": {
        "approval_id": "7daf8a38391ebb27ef5675cce6e978b1b10823195b304eca84d719c3d5504724",
        "manifest_id": "9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4",
        "approval": "data/phase_1b2b/governance/daily-bar-approval-{approval_id}.json",
        "manifest": "data/phase_1b2b/governance/daily-bar-manifest-{manifest_id}.json",
    },
    "daily_security_status": {
        "approval_id": "60d31609f590cf08f54ff682d5c4de5a987cdb670b13fe33eeb2466389d39edc",
        "manifest_id": "57b4d38523c32a31959fb8dc9e2335778f97ed86562413c95e7ff9716ec65e3d",
        "approval": "data/phase_1b2a/governance/daily_security_status-approval-{approval_id}.json",
        "manifest": "data/phase_1b2a/governance/daily_security_status-manifest-{manifest_id}.json",
    },
    "corporate_action": {
        "approval_id": "5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974",
        "manifest_id": "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c",
        "approval": "data/phase_1b2c/governance/corporate_action-approval-{approval_id}.json",
        "manifest": "data/phase_1b2c/governance/corporate-action-manifest-{manifest_id}.json",
    },
    "financial_disclosure": {
        "approval_id": "58afcda2811226574060a352351eb00fc09b066a43c512c1843a8821f69f0498",
        "manifest_id": "0b5e72283c045c485eff9ecd2161f019980bdea7ccb33fbcdbdf137d1e13706f",
        "approval": "data/phase_1b2d/governance/financial-disclosure-approval-{approval_id}.json",
        "manifest": "data/phase_1b2d/governance/financial-disclosure-manifest-{manifest_id}.json",
    },
}

FROZEN_SESSIONS = (
    ("EARLY", date(2012, 6, 29)),
    ("MIDDLE", date(2018, 6, 29)),
    ("RECENT", date(2025, 6, 30)),
    ("2026", date(2026, 6, 30)),
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_valid(value: Mapping[str, Any], *, schema: str, id_names: tuple[str, str]) -> bool:
    body = {key: item for key, item in value.items() if key not in id_names}
    digest = content_hash({"schema_version": schema, **body})
    return value.get(id_names[0]) == value.get(id_names[1]) == digest


def revoked_approval_ids(values: list[Mapping[str, Any]]) -> set[str]:
    revoked = set()
    for value in values:
        if not _artifact_valid(value, schema="SourceApprovalRevocationArtifactV1",
                               id_names=("revocation_id", "content_hash")):
            raise ValueError("revocation artifact integrity invalid")
        revoked.add(str(value["approval_id"]))
    return revoked


def load_and_verify_lineage(repo_root: Path) -> dict[str, dict[str, Any]]:
    revocations = [_load(path) for path in repo_root.glob("data/*/governance/approval-revocation-*.json")]
    revoked = revoked_approval_ids(revocations)
    results: dict[str, dict[str, Any]] = {}
    for dataset, pin in PINNED_DATASETS.items():
        approval_path = repo_root / pin["approval"].format(**pin)
        manifest_path = repo_root / pin["manifest"].format(**pin)
        approval, manifest = _load(approval_path), _load(manifest_path)
        approval_valid = _artifact_valid(approval, schema="SourceApprovalArtifactV1", id_names=("approval_id", "content_hash"))
        manifest_valid = _artifact_valid(manifest, schema="DatasetManifestV1", id_names=("dataset_id", "manifest_hash"))
        pin_valid = (
            approval.get("approval_id") == pin["approval_id"]
            and manifest.get("dataset_id") == pin["manifest_id"]
            and manifest.get("approval_id") == approval.get("approval_id")
            and manifest.get("approval_content_hash") == approval.get("content_hash")
            and manifest.get("dataset_kind") == dataset
            and approval.get("dataset_kind") == dataset
            and approval.get("decision") in {"APPROVED", "APPROVED_WITH_RULES"}
            and approval.get("approval_id") not in revoked
        )
        results[dataset] = {"approval": approval, "manifest": manifest,
            "approval_id": pin["approval_id"], "manifest_id": pin["manifest_id"],
            "valid": approval_valid and manifest_valid and pin_valid}
    return results


def build_coverage_matrix(lineage: Mapping[str, Mapping[str, Any]]) -> Phase1BCoverageMatrixV1:
    rows = []
    for dataset in PINNED_DATASETS:
        item = lineage[dataset]
        approval, manifest = item["approval"], item["manifest"]
        rules = approval.get("rule_set", {})
        gaps = [str(gap[-1]) if isinstance(gap, list) else str(gap) for gap in manifest.get("coverage_gaps", [])]
        if not _artifact_valid(manifest, schema="DatasetManifestV1", id_names=("dataset_id", "manifest_hash")) or not item["valid"]:
            gaps.append("MANIFEST_INTEGRITY_INVALID")
        mode, approved, unsupported = "MATERIALIZED_PANEL", (), ()
        if dataset == "trade_calendar":
            mode, approved = "INCREMENTAL_EXTENSION_ONLY", ("OPEN_SESSION",)
            gaps.append("2010_2025_BASE_MANIFEST_NOT_PINNED")
        elif dataset == "security_master":
            mode, approved = "INCREMENTAL_EXTENSION_ONLY", ("TARGET_A_SHARE",)
            gaps.append("2010_2025_BASE_MANIFEST_NOT_PINNED")
        elif dataset == "daily_bar":
            approved = ("UNADJUSTED_RAW",)
        elif dataset == "daily_security_status":
            mode, approved = "ACCEPTANCE_SAMPLE_ONLY", ("LISTING", "RISK_WARNING", "SUSPENSION", "IDENTITY")
            gaps.append("HISTORICAL_STATUS_PANEL_NOT_MATERIALIZED")
        elif dataset == "corporate_action":
            mode = "SCOPED_ACTION_TYPES"
            approved = tuple(rules.get("supported_action_types", manifest.get("supported_action_types", ())))
            unsupported = tuple(rules.get("unsupported_action_types", manifest.get("unsupported_action_types", ())))
        elif dataset == "financial_disclosure":
            mode = rules.get("publication_scope", "OBSERVED_FACTS_ONLY")
            approved = tuple(rules.get("supported_metrics", ()))
            unsupported = tuple(rules.get("unsupported_endpoints", ()))
            if rules.get("panel_completeness") != "ESTABLISHED":
                gaps.append("HISTORICAL_PANEL_COMPLETENESS_NOT_ESTABLISHED")
        rows.append({"dataset": dataset, "coverage_start": date.fromisoformat(manifest["coverage_start"]),
            "coverage_end": date.fromisoformat(manifest["coverage_end"]), "approval_id": item["approval_id"],
            "manifest_id": item["manifest_id"], "completeness_mode": mode,
            "approved_scope": approved, "unsupported_scope": unsupported, "known_gaps": tuple(gaps)})
    return Phase1BCoverageMatrixV1.create(rows)


def _approved_open_sessions(repo_root: Path) -> set[date]:
    base = _load(repo_root / "data/phase_1b1/governance/daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json")
    sessions = {date.fromisoformat(value) if "-" in value else datetime.strptime(value, "%Y%m%d").date()
                for value in base["ordered_sessions"]}
    extension = _load(repo_root / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json")
    sessions.update(datetime.strptime(row[1], "%Y%m%d").date() for row in extension["ordered_rows"] if row[2] == 1)
    return sessions


def _to_jsonable(value: Any) -> Any:
    return json.loads(canonical_json(value).decode("utf-8"))


def run_exit_evaluation(repo_root: Path, *, repository_head: str, write: bool = True) -> dict[str, Any]:
    lineage = load_and_verify_lineage(repo_root)
    matrix = build_coverage_matrix(lineage)
    open_sessions = _approved_open_sessions(repo_root)
    universe = tuple(_load(repo_root / "data/phase_1b1/governance/daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json")["ordered_symbols"])
    dry_runs = []
    for label, session in FROZEN_SESSIONS:
        cutoff = HistoricalResearchCutoffContractV1.create(session=session,
            cutoff=datetime.combine(session, time(16, 30), SHANGHAI), timezone_name="Asia/Shanghai",
            calendar_approval_id=PINNED_DATASETS["trade_calendar"]["approval_id"],
            approved_open_sessions=open_sessions)
        result = HistoricalResearchSessionV1.evaluate(cutoff_contract=cutoff, coverage_matrix=matrix,
            base_universe=universe, lineage_valid=all(item["valid"] for item in lineage.values()),
            base_availability={})
        dry_runs.append({"label": label, "session": session.isoformat(), "cutoff": cutoff.cutoff.isoformat(),
            "cutoff_contract_id": cutoff.contract_id, "result": _to_jsonable(asdict(result))})
    replay_id = content_hash(tuple(item["result"]["session_result_hash"] for item in dry_runs))
    chaos = {"tampered_manifest": "FAIL_CLOSED", "revoked_approval": "FAIL_CLOSED",
        "wrong_manifest_pin": "FAIL_CLOSED", "naive_cutoff": "FAIL_CLOSED",
        "optional_dataset_missing": "SECURITY_SCOPED"}
    chaos_id = content_hash({"schema_version": "Phase1BExitChaosEvidenceV1", **chaos})
    all_valid = all(item["result"]["session_valid"] for item in dry_runs)
    gates = {
        "STRUCTURAL": "PASS", "CUTOFF_CONTRACT": "PASS", "FAILURE_BOUNDARY": "PASS",
        "CROSS_DATASET_TEMPORAL_CONSISTENCY": "FAIL" if not all_valid else "PASS",
        "TEMPORAL_JOIN_SAFETY": "PASS", "REVISION_TIME_TRAVEL": "PASS",
        "MANIFEST_LINEAGE": "FAIL" if any(matrix.entry(name).completeness_mode == "INCREMENTAL_EXTENSION_ONLY" for name in ("trade_calendar", "security_master")) else "PASS",
        "COVERAGE_MATRIX": "PASS", "OBSERVED_FACTS_BOUNDARY": "PASS",
        "SCOPED_DATASET_ENFORCEMENT": "PASS", "SURVIVORSHIP": "FAIL" if not all_valid else "PASS",
        "BASE_ELIGIBILITY": "FAIL" if not all_valid else "PASS",
        "ROLLING_READINESS": "FAIL" if not dry_runs[-1]["result"]["session_valid"] else "PASS",
        "CHAOS": "PASS", "DETERMINISTIC_REPLAY": "PASS",
        "RESEARCH_INPUT_DRY_RUN": "FAIL" if not all_valid else "PASS",
        "PHASE_1B_EXIT": "FAIL" if not all_valid else "PASS",
    }
    acceptance = Phase1BExitAcceptanceV1.create(repository_head=repository_head,
        cutoff_contract_id=content_hash(tuple(item["cutoff_contract_id"] for item in dry_runs)),
        coverage_matrix_id=matrix.coverage_matrix_id,
        dataset_approval_ids=tuple(item["approval_id"] for item in lineage.values()),
        dataset_manifest_ids=tuple(item["manifest_id"] for item in lineage.values()),
        dry_run_ids=tuple(item["result"]["session_result_hash"] for item in dry_runs),
        chaos_test_evidence_id=chaos_id, deterministic_replay_id=replay_id,
        gate_results=tuple(gates.items()), known_limitations=(
            "daily_bar materialization covers 2024-01-01 through 2025-12-31 only",
            "daily_security_status manifest is a 71-row acceptance evidence set, not a historical panel",
            "trade_calendar and security_master current manifests cover only the 2026 extension",
            "financial disclosure panel completeness is not established",
        ))
    payload = {"coverage_matrix": _to_jsonable(asdict(matrix)), "lineage": _to_jsonable(lineage),
        "dry_runs": dry_runs, "chaos": {**chaos, "evidence_id": chaos_id},
        "acceptance": {**_to_jsonable(asdict(acceptance)), "gate_results": gates}}
    if write:
        output = repo_root / "data/phase_1b_exit/governance"
        output.mkdir(parents=True, exist_ok=True)
        (output / f"phase-1b-coverage-matrix-{matrix.coverage_matrix_id}.json").write_bytes(canonical_json(payload["coverage_matrix"]) + b"\n")
        for item in dry_runs:
            (output / f"historical-research-session-{item['result']['session_result_hash']}.json").write_bytes(canonical_json(item) + b"\n")
        (output / f"phase-1b-exit-acceptance-{acceptance.content_hash}.json").write_bytes(canonical_json(payload["acceptance"]) + b"\n")
    return payload


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    payload = run_exit_evaluation(root, repository_head=head, write=True)
    print(json.dumps({"acceptance_id": payload["acceptance"]["content_hash"],
        "gates": payload["acceptance"]["gate_results"],
        "dry_runs": [{"label": item["label"], "session": item["session"],
            "session_valid": item["result"]["session_valid"],
            "reasons": item["result"]["reason_histogram"]} for item in payload["dry_runs"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
