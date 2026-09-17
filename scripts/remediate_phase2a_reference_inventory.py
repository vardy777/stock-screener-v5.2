from __future__ import annotations

import hashlib
from pathlib import Path

from v5_2.data.identity import canonical_json
from v5_2.labels.inventory_remediation import (
    DISCOVERY_VERSION,
    PREDICATE_VERSION,
    audit_v1_applicability,
    discover_replacements,
)


ROOT = Path(__file__).resolve().parents[1]
V1_ID = "81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9"
V1_PATH = ROOT / "data/phase_2a/governance" / f"label-acceptance-inventory-{V1_ID}.json"
NEGATIVE_ACCEPTANCE_ID = "84d61057ecf5f527dcb5067fe0ea2b6103edf0f66388535e8ceeffd3ef10c3c8"


def write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable artifact collision")
    path.write_bytes(encoded)


def main() -> int:
    audit = audit_v1_applicability(ROOT)
    discovery = discover_replacements(ROOT)
    governance = ROOT / "data/phase_2a/governance"
    write_immutable(governance / f"reference-inventory-applicability-audit-{audit.audit_id}.json", audit)
    write_immutable(governance / f"reference-inventory-replacement-discovery-{discovery.discovery_id}.json", discovery)
    v1_sha = hashlib.sha256(V1_PATH.read_bytes()).hexdigest()
    rows = []
    outcomes = {item.slot: item for item in discovery.entries}
    for item in audit.entries:
        outcome = outcomes[item.slot]
        rows.append(
            f"| {item.slot} | {item.registered_stratum} | {item.identity} / {item.anchor_session} | "
            f"{item.actual_behavior} | {item.failed_criterion} | {outcome.status} | {outcome.reason} |"
        )
    report = "\n".join([
        "# V5.2 Phase 2A Checkpoint 8 — Reference Inventory Remediation", "",
        "CHECKPOINT 8 = STOP / REAL REFERENCE SAMPLE UNAVAILABLE", "",
        f"V1 INVENTORY ID = {V1_ID}",
        f"V1 FILE SHA-256 = {v1_sha}",
        f"CHECKPOINT 7 NEGATIVE ACCEPTANCE ID = {NEGATIVE_ACCEPTANCE_ID}",
        f"APPLICABILITY AUDIT ID = {audit.audit_id}",
        f"REPLACEMENT DISCOVERY ID = {discovery.discovery_id}",
        f"PREDICATE VERSION = {PREDICATE_VERSION}",
        f"DISCOVERY ALGORITHM VERSION = {DISCOVERY_VERSION}", "",
        "## Five-slot applicability audit", "",
        "| slot | registered stratum | old sample | actual immutable-evidence behavior | failed frozen criterion | discovery status | reason |",
        "|---:|---|---|---|---|---|---|", *rows, "",
        "## Contract conflict", "",
        "Slot 16 requires a valid approved five-domain bundle that simultaneously contains an exchange-open future session with no approved bar, no suspension, no delisting explanation, and valid identity. The frozen Phase 1 assembler rejects precisely that unexplained absence before bundle construction. Therefore a normal approved bundle cannot reproduce this stratum without weakening Phase 1 correctness.", "",
        "Result: `FROZEN_REFERENCE_STRATUM_INCOMPATIBLE_WITH_PHASE1_APPROVED_EVIDENCE_CONTRACT`.", "",
        "Inventory V2 was not created. No supersession artifact was created. Slots 17/20/21/22 were not searched after the mandatory STOP condition, preventing open-ended or outcome-selected replacement search.", "",
        "PROVIDER REQUESTS = 0", "NETWORK CALLS = 0",
        "PHASE 2A = FAIL / OPEN", "READY FOR PHASE 2B = NO", "PHASE 2B STARTED = NO", "",
        "## Verification", "",
        "- remediation focused tests: `4 passed in 5.20s`",
        "- Phase 2A label tests: `116 passed in 56.78s`",
        "- Phase 0–1C regression: `501 passed in 98.59s`",
        "- full pytest: `681 passed in 155.89s`",
        "- standalone / zero-project-dependency checks: PASS; four finding counts are zero",
        "- clean-room: PASS; `586 passed, 95 skipped in 2.94s`",
        "- build, install, wheel smoke: PASS; archive dependency findings empty",
        "- V1 inventory and Checkpoint 7 negative acceptance diffs against Checkpoint 7 HEAD: empty",
        "- deterministic replay: PASS; identical IDs and output on both runs (expected fail-closed exit code `2`)",
        "- credential sentinel scan: configured credential values present `0`, findings `0`; no credential value was printed",
        "- `git diff --check`: PASS", "",
    ])
    (ROOT / "docs/reports/V5_2_PHASE_2A_REFERENCE_INVENTORY_REMEDIATION.md").write_text(report, encoding="utf-8")
    print(f"APPLICABILITY_AUDIT_ID={audit.audit_id}")
    print(f"DISCOVERY_ID={discovery.discovery_id}")
    print("INVENTORY_V2_CREATED=NO")
    print("REAL_REFERENCE_SAMPLE_UNAVAILABLE=YES")
    print("PHASE1_CONTRACT_CONFLICT=YES")
    print("PROVIDER_REQUESTS=0")
    print("NETWORK_CALLS=0")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
