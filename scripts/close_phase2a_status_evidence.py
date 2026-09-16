from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.phase2a_status_closure import (  # noqa: E402
    audit_existing_status_evidence,
    materialize_status_closure,
)


def main() -> int:
    canonical_runtime = ROOT.parent.parent / "data/phase_1b2a"
    audit = audit_existing_status_evidence(ROOT, canonical_runtime)
    result = materialize_status_closure(ROOT, audit, ROOT)
    path = ROOT / "data/phase_1b2a_status_closure/governance" / f"status-closure-audit-{audit.audit_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(audit.as_dict()))
    print(json.dumps({
        "status_closure_audit_id": audit.audit_id,
        "existing_status_evidence_reused": len(audit.entries),
        "new_status_provider_requests": audit.provider_request_count,
        "new_status_facts": len(result.facts),
        "status_manifest_id": result.manifest.dataset_id,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
