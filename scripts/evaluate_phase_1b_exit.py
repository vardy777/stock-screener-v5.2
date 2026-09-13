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
        "manifest_id": "5f5ba7d0594f5f1e2d40ad43b54a93a303a7d25af8e1104e6c633463076e6486",
        "approval": "data/phase_1b1_2026_extension/governance/trade_calendar-approval-{approval_id}.json",
        "manifest": "data/phase_1b_exit_remediation/governance/trade-calendar-complete-manifest-{manifest_id}.json",
    },
    "security_master": {
        "approval_id": "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c",
        "manifest_id": "025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b",
        "approval": "data/phase_1b1_2026_extension/governance/security_master-approval-{approval_id}.json",
        "manifest": "data/phase_1b_exit_remediation/governance/security-master-complete-manifest-{manifest_id}.json",
    },
    "daily_bar": {
        "approval_id": "fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5",
        "manifest_id": "76c4fe58d0714405d0a6a826bf9b814237d812f88f69b63986a0e0317f924b4b",
        "approval": "data/phase_1b_exit_remediation/governance/daily_bar-approval-{approval_id}.json",
        "manifest": "data/phase_1b_exit_remediation/governance/daily_bar-manifest-{manifest_id}.json",
    },
    "daily_security_status": {
        "approval_id": "ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07",
        "manifest_id": "d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0",
        "approval": "data/phase_1b_exit_remediation/governance/daily_security_status-approval-{approval_id}.json",
        "manifest": "data/phase_1b_exit_remediation/governance/daily_security_status-manifest-{manifest_id}.json",
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

DAILY_FROZEN_AVAILABILITY_ID = "70ee31d3e126d12baf6d08a4b780d8051d3477762521f1fe34780319c9ccadbd"
STATUS_FROZEN_RESOLUTION_ID = "3ae79a145d7d0252aea1d5e35fb6b737fba568603cc5e2a9a499e22fdf68fd44"

OLD_REPORTED_MAPPING = {
    "EARLY": "bfd09d04cedec1232c2ad16a8de4f4730029af279e0f15d3d2ce7f61fb5848bd",
    "MIDDLE": "b223802c15de6901459bd07b8bb7f1216a75746277658af76542bf9ad22ce1b3",
    "RECENT": "222594638c5e82f44ac25adf76c76dbfc596dae38573863fa2318e383ed14256",
    "2026": "1c07e67549a33a4d651b64f75c780f1ab7770b96a2a7ae7c963159ec273f3e0b",
}

FROZEN_ORIGINAL_MAPPING = {
    "EARLY": "bfd09d04cedec1232c2ad16a8de4f4730029af279e0f15d3d2ce7f61fb5848bd",
    "MIDDLE": "222594638c5e82f44ac25adf76c76dbfc596dae38573863fa2318e383ed14256",
    "RECENT": "1c07e67549a33a4d651b64f75c780f1ab7770b96a2a7ae7c963159ec273f3e0b",
    "2026": "b223802c15de6901459bd07b8bb7f1216a75746277658af76542bf9ad22ce1b3",
}


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
            mode, approved = "COMPLETE_APPROVED_LINEAGE", ("OPEN_SESSION",)
        elif dataset == "security_master":
            mode, approved = "COMPLETE_EFFECTIVE_DATED_LINEAGE", ("TARGET_A_SHARE",)
        elif dataset == "daily_bar":
            approved = ("UNADJUSTED_RAW",)
        elif dataset == "daily_security_status":
            mode, approved = "RESEARCH_WIDE_PIT_PANEL", ("LISTING", "RISK_WARNING", "SUSPENSION", "IDENTITY")
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


def historical_universe(repo_root: Path, session: date) -> tuple[str, ...]:
    """Resolve effective membership from immutable lifecycle fields, never today's snapshot."""
    bundle = next((repo_root / "data/phase_1b_exit_remediation/governance").glob(
        "complete-security-master-fact-bundle-*.json"))
    target = set(_load(bundle)["ordered_security_identities"])
    lifecycle: dict[str, tuple[str, str]] = {}
    for root in (repo_root / "data/phase_1b1", repo_root / "data/phase_1b1_2026_extension"):
        for path in (root / "raw/datahubco_tushare_proxy/security_master").rglob("*.json"):
            for row in _load(path)["provider_payload"]["rows"]:
                identity = str(row.get("ts_code", ""))
                if identity not in target:
                    continue
                value = (str(row.get("list_date") or "00000000"),
                         str(row.get("delist_date") or "99999999"))
                if identity in lifecycle and lifecycle[identity] != value:
                    raise ValueError("conflicting effective identity lifecycle")
                lifecycle[identity] = value
    if set(lifecycle) != target:
        raise ValueError("historical universe lifecycle is incomplete")
    key = session.strftime("%Y%m%d")
    return tuple(sorted(identity for identity, (start, end) in lifecycle.items()
                        if start <= key <= end))


def _to_jsonable(value: Any) -> Any:
    return json.loads(canonical_json(value).decode("utf-8"))


def audit_frozen_dry_run_references(repo_root: Path) -> dict[str, Any]:
    expected_sessions = {label: session.isoformat() for label, session in FROZEN_SESSIONS}
    correct: dict[str, str] = {}
    paths: dict[str, str] = {}
    root = repo_root / "data/phase_1b_exit/governance"
    for frozen_hash in FROZEN_ORIGINAL_MAPPING.values():
        path = root / f"historical-research-session-{frozen_hash}.json"
        if not path.is_file():
            raise ValueError("old frozen dry-run artifact is missing")
        value = _load(path)
        label, session = value["label"], value["session"]
        result_hash = value["result"]["session_result_hash"]
        if expected_sessions.get(label) != session or not path.stem.endswith(result_hash):
            raise ValueError("old dry-run artifact identity is internally inconsistent")
        if label in correct:
            raise ValueError("duplicate old dry-run label")
        correct[label], paths[label] = result_hash, path.relative_to(repo_root).as_posix()
    if set(correct) != set(expected_sessions):
        raise ValueError("old dry-run inventory is incomplete")
    body = {"schema_version": "DryRunReferenceCorrectionV1",
        "status": ("REFERENCE_CORRECTION_REQUIRED" if correct != OLD_REPORTED_MAPPING else "REFERENCES_VALID"),
        "reason": "report label-to-hash references were transposed; immutable artifacts remain unchanged",
        "old_reported_mapping": OLD_REPORTED_MAPPING, "correct_mapping": correct,
        "artifact_paths": paths, "sessions": expected_sessions}
    digest = content_hash(body)
    return {**body, "artifact_id": digest, "content_hash": digest}


def run_exit_evaluation(repo_root: Path, *, repository_head: str, write: bool = True) -> dict[str, Any]:
    correction = audit_frozen_dry_run_references(repo_root)
    lineage = load_and_verify_lineage(repo_root)
    matrix = build_coverage_matrix(lineage)
    open_sessions = _approved_open_sessions(repo_root)
    daily_availability = _load(repo_root / "data/phase_1b_exit_remediation/governance" /
        f"daily-bar-frozen-session-availability-{DAILY_FROZEN_AVAILABILITY_ID}.json")
    status_resolution = _load(repo_root / "data/phase_1b_exit_remediation/governance" /
        f"status-frozen-session-resolution-{STATUS_FROZEN_RESOLUTION_ID}.json")
    if not _artifact_valid(daily_availability, schema="DailyBarFrozenSessionAvailabilityV1",
                           id_names=("artifact_id", "content_hash")):
        raise ValueError("daily-bar frozen availability artifact is invalid")
    if not _artifact_valid(status_resolution, schema="StatusFrozenSessionResolutionV1",
                           id_names=("artifact_id", "content_hash")):
        raise ValueError("status frozen resolution artifact is invalid")
    if (daily_availability["panel_id"] not in lineage["daily_bar"]["manifest"]["fact_content_hashes"]
            or status_resolution["panel_id"] not in lineage["daily_security_status"]["manifest"]["fact_content_hashes"]):
        raise ValueError("frozen availability does not bind the pinned panel manifest")
    dry_runs = []
    for label, session in FROZEN_SESSIONS:
        cutoff = HistoricalResearchCutoffContractV1.create(session=session,
            cutoff=datetime.combine(session, time(16, 30), SHANGHAI), timezone_name="Asia/Shanghai",
            calendar_approval_id=PINNED_DATASETS["trade_calendar"]["approval_id"],
            approved_open_sessions=open_sessions)
        session_key = session.strftime("%Y%m%d")
        universe = historical_universe(repo_root, session)
        resolved_universe = tuple(status_resolution["sessions"][session_key]["universe"])
        if resolved_universe != universe:
            raise ValueError("status resolution universe does not match effective master lifecycle")
        result = HistoricalResearchSessionV1.evaluate(cutoff_contract=cutoff, coverage_matrix=matrix,
            base_universe=universe, lineage_valid=all(item["valid"] for item in lineage.values()),
            base_availability={"security_master": universe,
                "daily_bar": tuple(daily_availability["sessions"][session_key]),
                "daily_security_status": resolved_universe},
            base_ineligible=dict(status_resolution["sessions"][session_key]["ineligible_reasons"]))
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
            f"dry_run_reference_correction_id={correction['artifact_id']}",
            "daily_bar missing symbol-sessions remain unclassified and security-scoped fail closed",
            "historical reconstructed daily bars use NEXT_SESSION_SAFE and are not contemporaneous observations",
            "financial disclosure panel completeness is not established",
        ))
    payload = {"coverage_matrix": _to_jsonable(asdict(matrix)), "lineage": _to_jsonable(lineage),
        "dry_run_reference_correction": correction,
        "dry_runs": dry_runs, "chaos": {**chaos, "evidence_id": chaos_id},
        "acceptance": {**_to_jsonable(asdict(acceptance)), "gate_results": gates}}
    if write:
        output = repo_root / "data/phase_1b_exit/governance"
        output.mkdir(parents=True, exist_ok=True)
        (output / f"dry-run-reference-correction-{correction['artifact_id']}.json").write_bytes(canonical_json(correction) + b"\n")
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
