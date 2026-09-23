from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.historical_status_authority import (  # noqa: E402
    HistoricalStatusCoverageLedgerV1,
    _put_create_or_identical,
    normalize_status_rows,
    publish_portable_status_authority,
    reconstruct_frozen_status_inputs,
)
from v5_2.data.identity import canonical_json  # noqa: E402


PANEL_ID = "cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707"
MANIFEST_ID = "d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0"
APPROVAL_ID = "ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07"
PIT_ID = "aabfbcd3e8d4d03ff400c52a12ff005638b259bf0185e802d96372b4015f3f8f"


def _mapping(value):
    return {field.name: getattr(value, field.name) for field in fields(value)}


def _open_session_count() -> int:
    base = json.loads((ROOT / "data/phase_1b1/governance/daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json").read_text(encoding="utf-8"))
    sessions = set(base["ordered_sessions"])
    extension = json.loads((ROOT / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json").read_text(encoding="utf-8"))
    sessions.update(row[1] for row in extension["ordered_rows"] if row[2] == 1)
    return len(sessions)


def materialize(*, staging_root: Path, output_root: Path):
    governance = ROOT / "data/phase_1b_exit_remediation/governance"
    reconstructed = reconstruct_frozen_status_inputs(
        repository_root=ROOT,
        staging_root=staging_root,
        manifest_path=governance / f"daily_security_status-manifest-{MANIFEST_ID}.json",
        panel_path=governance / f"historical-status-panel-{PANEL_ID}.json",
        approval_path=governance / f"daily_security_status-approval-{APPROVAL_ID}.json",
    )
    panel = json.loads((governance / f"historical-status-panel-{PANEL_ID}.json").read_text(encoding="utf-8"))
    manifest = json.loads((governance / f"daily_security_status-manifest-{MANIFEST_ID}.json").read_text(encoding="utf-8"))
    approval = json.loads((governance / f"daily_security_status-approval-{APPROVAL_ID}.json").read_text(encoding="utf-8"))
    lifecycle, risk, suspension = normalize_status_rows(
        lifecycle_rows=reconstructed.lifecycle_rows,
        namechange_rows=reconstructed.namechange_rows,
        suspension_rows=reconstructed.suspension_rows,
    )
    components = lifecycle + risk + suspension
    authority_dir = output_root / "authority"
    authority = publish_portable_status_authority(
        output_root=authority_dir,
        components=components,
        coverage_start=__import__("datetime").date.fromisoformat(panel["coverage_start"]),
        coverage_end=__import__("datetime").date.fromisoformat(panel["coverage_end"]),
        parent_panel_id=PANEL_ID, parent_manifest_id=MANIFEST_ID,
        parent_approval_id=APPROVAL_ID, pit_evidence_id=PIT_ID,
        source_version_identity=approval["source_version_identity"],
        raw_payload_hashes=reconstructed.raw_payload_hashes,
        receipt_hashes=reconstructed.receipt_hashes,
        request_inventory_id=manifest["request_inventory_id"],
        authority_policy_version="historical-status-authority-v1",
    )
    kind_counts = {
        kind: sum(item.component_kind == kind for item in components)
        for kind in ("LIFECYCLE", "RISK_WARNING", "FULL_DAY_SUSPENSION", "PARTIAL_SUSPENSION", "RESUMPTION")
    }
    ledger = HistoricalStatusCoverageLedgerV1.create(
        authority_id=authority.authority_id,
        coverage_start=authority.coverage_start,
        coverage_end=authority.coverage_end,
        counts={
            "covered_identities": len(lifecycle),
            "covered_exchange_sessions": _open_session_count(),
            "lifecycle_intervals": kind_counts["LIFECYCLE"],
            "risk_warning_intervals": kind_counts["RISK_WARNING"],
            "suspension_observations": sum(kind_counts[kind] for kind in (
                "FULL_DAY_SUSPENSION", "PARTIAL_SUSPENSION", "RESUMPTION"
            )),
            "full_day_suspension_observations": kind_counts["FULL_DAY_SUSPENSION"],
            "partial_session_observations": kind_counts["PARTIAL_SUSPENSION"],
            "resumption_observations": kind_counts["RESUMPTION"],
            "delisting_boundaries": sum(item.effective_to is not None for item in lifecycle),
            "ordinary_derivation_identity_coverage": len(lifecycle),
            "out_of_scope_sessions": 0,
        },
        unresolved_identities=0,
        unresolved_sessions=0,
        coverage_gaps=(),
        quarantine_count=0,
    )
    governance_out = output_root / "governance"
    _put_create_or_identical(
        governance_out / f"historical-status-coverage-ledger-{ledger.ledger_id}.json",
        canonical_json(_mapping(ledger)),
    )
    return authority, ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/phase_1_status_lineage_remediation_v1")
    arguments = parser.parse_args()
    authority, ledger = materialize(
        staging_root=arguments.staging_root, output_root=arguments.output_root
    )
    print(json.dumps({"authority_id": authority.authority_id, "coverage_ledger_id": ledger.ledger_id}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
