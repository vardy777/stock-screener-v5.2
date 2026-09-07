from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.missing_bar_classification import (  # noqa: E402
    MissingBarClassificationArtifactV1, MissingBarClassificationItemV1, quarantine_local_exceptions,
)

CLASSIFICATION_ID = "23a660b27dc476a582401780603d3e7458b823951b5d54c55ef40ef71c9f127d"
EXCEPTION_AUDIT_ID = "5e54d212b5f67b5a7d450698c72a71cebae1aa143cb173cb81883528f51f381d"


def main() -> int:
    directory = ROOT / "data" / "phase_1b2a" / "governance"
    raw = json.loads((directory / f"missing-bar-classification-{CLASSIFICATION_ID}.json").read_text(encoding="utf-8"))
    original = MissingBarClassificationArtifactV1(
        tuple(MissingBarClassificationItemV1(**item) for item in raw["items"]), tuple(tuple(x) for x in raw["counts"]),
        raw["total"], raw["policy_version"], raw["content_hash"],
    )
    audit = json.loads((directory / f"status-exception-audit-{EXCEPTION_AUDIT_ID}.json").read_text(encoding="utf-8"))
    if not audit["result"]["passed"] or audit["result"]["systematic_pattern"]:
        raise RuntimeError("exception audit does not authorize quarantine reclassification")
    record_ids = {(row["security_identity"], row["effective_date"].replace("-", "")): row["exception_id"] for row in audit["records"]}
    result = quarantine_local_exceptions(original, record_ids, EXCEPTION_AUDIT_ID)
    output = directory / f"missing-bar-classification-{result.content_hash}.json"
    output.write_bytes(canonical_json({"schema_version": "MissingBarClassificationArtifactV2", **asdict(result),
                                       "research_eligible": False}))
    print(json.dumps({"total": result.total, "counts": dict(result.counts), "classification_id": result.content_hash,
                      "preserved_keys": tuple(item.key for item in result.items) == tuple(item.key for item in original.items),
                      "research_eligible": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
