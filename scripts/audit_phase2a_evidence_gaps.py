from __future__ import annotations

import json
from pathlib import Path

from v5_2.data.real_audits.phase2a_evidence_gap import audit_phase2a_evidence_gaps, render_evidence_gap_matrix


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    audit = audit_phase2a_evidence_gaps(ROOT)
    artifact = ROOT / "data/phase_2a/governance" / f"phase2a-evidence-gap-audit-{audit.audit_id}.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(audit.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report = ROOT / "docs/reports/V5_2_PHASE_2A_EVIDENCE_GAP_AUDIT.md"
    report.write_text(render_evidence_gap_matrix(audit), encoding="utf-8")
    print(f"PHASE_2A_EVIDENCE_GAP_AUDIT_ID={audit.audit_id}")
    for name, count in audit.counts:
        print(f"{name}={count}")
    print(f"BUNDLES_CONSTRUCTIBLE={sum(entry.bundle_constructible for entry in audit.entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
