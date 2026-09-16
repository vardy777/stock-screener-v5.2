from __future__ import annotations

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.phase2a_bar_root_cause import audit_remaining_bar_gaps, render_root_cause_report  # noqa: E402


def write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable root-cause audit collision") from None
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)


def main() -> int:
    audit = audit_remaining_bar_gaps(ROOT)
    artifact = ROOT / "data/phase_2a/governance" / f"remaining-bar-root-cause-audit-{audit.audit_id}.json"
    write_immutable(artifact, audit.as_dict())
    report = ROOT / "docs/reports/V5_2_PHASE_2A_REMAINING_BAR_ROOT_CAUSE_AUDIT.md"
    report.write_text(render_root_cause_report(audit), encoding="utf-8")
    print(f"ROOT_CAUSE_AUDIT_ID={audit.audit_id}")
    for name, count in audit.counts:
        print(f"{name}={count}")
    print(f"ACQUISITION_DEFECT_FOUND={audit.acquisition_defect_found}")
    print(f"PHASE1_CORRECTNESS_DEFECT_FOUND={audit.phase1_correctness_defect_found}")
    print(f"PROPOSED_REQUEST_COUNT={audit.proposed_request_count}")
    print("PROVIDER_REQUESTS_ACTUALLY_MADE=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
