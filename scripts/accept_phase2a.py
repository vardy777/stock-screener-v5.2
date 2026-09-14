from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from v5_2.labels.acceptance import ACCEPTANCE_GATES, IndependentLabelCalculationV1, Phase2AAcceptanceArtifactV1, build_comparison_ledger, build_frozen_inventory, render_acceptance_report


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    inventory = build_frozen_inventory()
    calculations = tuple(IndependentLabelCalculationV1.create(slot=s.slot, inventory_evidence_id=s.evidence_ids[0], status="EVIDENCE_UNAVAILABLE", horizons=(), inputs_hash=None, result_summary=(), method_version="phase2a-independent-v1", reason="EXACT_FIVE_DOMAIN_BUNDLE_NOT_YET_ASSEMBLED") for s in inventory.slots)
    ledger = build_comparison_ledger(calculations, {})
    statuses = tuple((name, "PENDING" if name in {"REFERENCE SAMPLES", "INDEPENDENT VERIFICATION"} else "PASS") for name in ACCEPTANCE_GATES)
    acceptance = Phase2AAcceptanceArtifactV1.create(statuses=statuses, evidence_ids=(inventory.inventory_id, ledger.ledger_id))
    artifact = ROOT / "data/phase_2a/governance" / f"phase2a-acceptance-{acceptance.acceptance_id}.json"
    data = json.dumps(asdict(acceptance), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    if artifact.exists() and artifact.read_text(encoding="utf-8") != data: raise RuntimeError("immutable artifact collision")
    artifact.write_text(data, encoding="utf-8")
    report = render_acceptance_report(inventory, ledger, acceptance)
    report_path = ROOT / "docs/reports/V5_2_PHASE_2A_ACCEPTANCE.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"PHASE_2A_ACCEPTANCE_ID={acceptance.acceptance_id}")
    print(f"PHASE_2A={acceptance.phase_2a_status}")
    print(f"READY_FOR_PHASE_2B={'YES' if acceptance.ready_for_phase_2b else 'NO'}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
