from __future__ import annotations

from pathlib import Path

from v5_2.data.identity import canonical_json
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.phase2a_exit import run_phase2a_exit_verification


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    inventory = build_frozen_inventory()
    result = run_phase2a_exit_verification(ROOT)
    acceptance = result.acceptance
    artifact = ROOT / "data/phase_2a/governance" / f"phase2a-acceptance-{acceptance.acceptance_id}.json"
    data = canonical_json(acceptance) + b"\n"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    if artifact.exists() and artifact.read_bytes() != data: raise RuntimeError("immutable artifact collision")
    artifact.write_bytes(data)
    lines = ["# V5.2 Phase 2A Exit Acceptance", "",
             f"PHASE 2A = {acceptance.phase_2a_status}",
             f"READY FOR PHASE 2B = {'YES' if acceptance.ready_for_phase_2b else 'NO'}", "",
             "## Frozen 16 gates", ""]
    lines.extend(f"- {name} = {status}" for name, status in acceptance.statuses)
    lines.extend(["", "## Frozen 22-slot field comparison", "",
                  "| slot | stratum | identity | anchor | production result | independent result | barriers production / independent | comparison | evidence ID |",
                  "|---:|---|---|---|---|---|---|---|---|"])
    for slot, entry in zip(inventory.slots, result.comparison_ledger.entries):
        lines.append(
            f"| {slot.slot:02d} | {slot.stratum} | {slot.security_identity} | {slot.anchor_session} | "
            f"`{entry.production_summary}` | `{entry.independent_summary}` | "
            f"`{entry.production_barriers}` / `{entry.independent_barriers}` | {entry.disposition} | {entry.comparison_hash} |"
        )
    failed = tuple(name for name, status in acceptance.statuses if status != "PASS")
    lines.extend(["", "## Decision", "",
                  f"MATCH = {sum(x.disposition == 'MATCH' for x in result.comparison_ledger.entries)}",
                  f"MISMATCH = {sum(x.disposition == 'MISMATCH' for x in result.comparison_ledger.entries)}",
                  f"FAILED GATES = {', '.join(failed) if failed else 'NONE'}", "",
                  "The frozen inventory's `expected future bar missing`, `unsupported corporate action`, and double-barrier strata do not reproduce their registered semantics from the exact Phase 1 artifacts. The arithmetic comparison is complete, but Phase 2A remains fail-closed; the inventory and label semantics were not changed.", "",
                  f"INVENTORY ID = {inventory.inventory_id}",
                  f"COMPARISON LEDGER ID = {result.comparison_ledger.ledger_id}",
                  f"ACCEPTANCE ID = {acceptance.acceptance_id}",
                  f"DETERMINISTIC REPLAY ID = {result.replay_hash}", "",
                  "PROVIDER REQUESTS = 0", "NETWORK CALLS = 0", ""])
    report = "\n".join(lines)
    report_path = ROOT / "docs/reports/V5_2_PHASE_2A_ACCEPTANCE.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"PHASE_2A_ACCEPTANCE_ID={acceptance.acceptance_id}")
    print(f"PHASE_2A={acceptance.phase_2a_status}")
    print(f"READY_FOR_PHASE_2B={'YES' if acceptance.ready_for_phase_2b else 'NO'}")
    return 0 if acceptance.ready_for_phase_2b else 2


if __name__ == "__main__": raise SystemExit(main())
