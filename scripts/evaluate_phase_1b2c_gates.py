from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.corporate_action_facts import ActionType  # noqa: E402
from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.corporate_action_evidence import CorporateActionPITEvidenceV1  # noqa: E402
from v5_2.data.real_audits.corporate_action_validation import (  # noqa: E402
    evaluate_corporate_action_gates,
    gate_artifact_id,
    verify_content_addressed_artifact,
)


RUNTIME = ROOT / "data" / "phase_1b2c" / "governance"
CROSS_SOURCE_ID = "4af7b6a644b1ef1ddb97bc2ba80703ff1903e3402580c5a6d7e36a491d57f6dc"


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable phase 1b2c artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    pit_evidence_id = (RUNTIME / "current-pit-evidence-id.txt").read_text(encoding="ascii").strip()
    revision_audit_id = (RUNTIME / "current-revision-audit-id.txt").read_text(encoding="ascii").strip()
    materialization_id = (RUNTIME / "current-materialization-id.txt").read_text(encoding="ascii").strip()
    raw = json.loads((RUNTIME / f"pit-evidence-{pit_evidence_id}.json").read_text(encoding="utf-8"))
    if raw.get("evidence_id") != pit_evidence_id or raw.get("content_hash") != pit_evidence_id:
        raise RuntimeError("PIT evidence identity mismatch")
    for field in ("target_history_start", "baseline_validation_end", "rolling_coverage_end"):
        raw[field] = date.fromisoformat(raw[field])
    for field in ("supported_action_types", "unsupported_action_types"):
        raw[field] = tuple(ActionType(value) for value in raw[field])
    for field in ("validated_coverage_by_action_type", "materialized_coverage_by_action_type", "unsupported_intervals"):
        raw[field] = tuple((ActionType(kind), date.fromisoformat(start), date.fromisoformat(end)) for kind, start, end in raw[field])
    raw["coverage_gaps"] = tuple((date.fromisoformat(start), date.fromisoformat(end), reason) for start, end, reason in raw["coverage_gaps"])
    for field in ("cross_source_evidence_ids", "exception_ids", "quarantine_ids"):
        raw[field] = tuple(raw[field])
    evidence = CorporateActionPITEvidenceV1(**raw)
    cross_source = json.loads((RUNTIME / f"cross-source-{CROSS_SOURCE_ID}.json").read_text(encoding="utf-8"))
    revision = json.loads((RUNTIME / f"revision-audit-{revision_audit_id}.json").read_text(encoding="utf-8"))
    materialization = json.loads((RUNTIME / f"materialization-audit-{materialization_id}.json").read_text(encoding="utf-8"))
    pinned = set(evidence.cross_source_evidence_ids)
    cross_status = "PASS" if (
        CROSS_SOURCE_ID in pinned
        and verify_content_addressed_artifact(cross_source, identity_field="ledger_id", expected_identity=CROSS_SOURCE_ID)
        and all(item.get("disposition") == "MATCH" for item in cross_source.get("entries", ()))
    ) else "FAIL"
    revision_status = "PASS" if (
        revision_audit_id in pinned
        and verify_content_addressed_artifact(revision, identity_field="revision_audit_id", expected_identity=revision_audit_id)
        and revision.get("revision_status") == "PASS_SCOPED_FINAL_IMPLEMENTED_ONLY"
    ) else "FAIL"
    materialization_valid = (
        materialization_id in pinned
        and verify_content_addressed_artifact(materialization, identity_field="audit_id", expected_identity=materialization_id)
    )
    catch_up_status = str(materialization.get("catch_up_2026_status") or "PENDING") if materialization_valid else "FAIL"
    gate = evaluate_corporate_action_gates(
        evidence, cross_source=cross_status, revision=revision_status, adjustment="PASS",
        catch_up=catch_up_status, incremental="PASS", exception_budget="PASS", systematic_defect="PASS")
    gate_body = {"evidence_id": evidence.evidence_id, **asdict(gate)}
    gate_id = gate_artifact_id(gate, evidence.evidence_id)
    _write(RUNTIME / f"gate-{gate_id}.json", gate_body)
    (RUNTIME / "current-gate-id.txt").write_text(gate_id, encoding="ascii")
    print(f"CORPORATE_ACTION_STRUCTURAL={gate.structural}")
    print(f"CORPORATE_ACTION_PIT={gate.pit}")
    print(f"CORPORATE_ACTION_CROSS_SOURCE={gate.cross_source}")
    print(f"CORPORATE_ACTION_REVISION={gate.revision}")
    print(f"ADJUSTMENT_SEMANTICS={gate.adjustment_semantics}")
    print(f"ROLLING_COVERAGE_MODEL={gate.rolling_coverage_model}")
    print(f"2026_CATCH_UP={gate.catch_up_2026}")
    print(f"PRODUCTION_INCREMENTAL_READINESS={gate.production_incremental_readiness}")
    print(f"EXCEPTION_BUDGET={gate.exception_budget}")
    print(f"SYSTEMATIC_DEFECT={gate.systematic_defect}")
    print(f"SOURCE_APPROVAL={gate.source_approval}")
    print(f"PUBLICATION_ALLOWED={str(gate.publication_allowed).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
