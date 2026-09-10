from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.corporate_action_facts import ActionType  # noqa: E402
from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.real_audits.corporate_action_evidence import CorporateActionPITEvidenceV1  # noqa: E402
from v5_2.data.real_audits.corporate_action_validation import evaluate_corporate_action_gates  # noqa: E402


RUNTIME = ROOT / "data" / "phase_1b2c" / "governance"


def _write(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable phase 1b2c artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    unsupported = (ActionType.RIGHTS_ISSUE, ActionType.STOCK_SPLIT, ActionType.SHARE_CONVERSION)
    evidence = CorporateActionPITEvidenceV1.create(
        target_history_start=date(2010, 1, 4), baseline_validation_end=date(2025, 12, 31),
        rolling_coverage_end=date(2026, 9, 9), source_name="datahubco_tushare_proxy",
        source_version_identity="datahub-dividend-probe-2026-09-10-v1",
        supported_action_types=(ActionType.CASH_DIVIDEND, ActionType.BONUS_SHARE),
        unsupported_action_types=unsupported,
        validated_coverage_by_action_type=(), materialized_coverage_by_action_type=(),
        coverage_gaps=((date(2010, 1, 4), date(2026, 9, 9), "bounded probe only; acquisition and independent validation pending"),),
        unsupported_intervals=tuple((kind, date(2010, 1, 4), date(2026, 9, 9)) for kind in unsupported),
        cross_source_evidence_ids=(), exception_ids=(), quarantine_ids=("unsupported-action-types",),
        publication_rule="historical-date-only-next-approved-session-1630-asia-shanghai",
        economic_effect_rule="ex-or-effective-date-separate-from-knowledge-time",
        revision_rule="latest-then-known-source-version",
        cancellation_rule="retain-announcement-history-no-economic-effect", complete=False,
    )
    gate = evaluate_corporate_action_gates(
        evidence, cross_source="PENDING", revision="PENDING", adjustment="PASS",
        catch_up="PENDING", incremental="PASS", exception_budget="PASS", systematic_defect="PASS")
    _write(RUNTIME / f"pit-evidence-{evidence.evidence_id}.json", asdict(evidence))
    _write(RUNTIME / "latest-gate.json", {"evidence_id": evidence.evidence_id, **asdict(gate)})
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
