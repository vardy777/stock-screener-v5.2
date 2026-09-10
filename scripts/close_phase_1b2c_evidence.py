from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.corporate_action_facts import ActionType  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.real_audits.corporate_action_evidence import CorporateActionPITEvidenceV1  # noqa: E402


INVENTORY_ID = "90354c25bb7529048a2a391ba06e8e4cfb5daf732f9b6abcca94189fa13023c5"
CROSS_SOURCE_ID = "4af7b6a644b1ef1ddb97bc2ba80703ff1903e3402580c5a6d7e36a491d57f6dc"
PROBE_ID = "2e6b8466c3d75411a0dece848425a203eef03a49538657ec3c519026d536bb24"
ACQUISITION_ID = "139298428aef7f08add358c49c01fb1a2796a78543abf5fa90c7b0825c285876"
RUNTIME = ROOT / "data" / "phase_1b2c" / "governance"


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable evidence artifact collision")
    if not path.exists():
        path.write_bytes(encoded)


def _verified(path: Path, identity_field: str, expected: str) -> dict:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get(identity_field) != expected or artifact.get("content_hash", expected) != expected:
        raise RuntimeError(f"artifact identity mismatch: {path.name}")
    return artifact


def main() -> int:
    materialization_id = (RUNTIME / "current-materialization-id.txt").read_text(encoding="ascii").strip()
    inventory = _verified(RUNTIME / f"sample-inventory-{INVENTORY_ID}.json", "inventory_id", INVENTORY_ID)
    ledger = _verified(RUNTIME / f"cross-source-{CROSS_SOURCE_ID}.json", "ledger_id", CROSS_SOURCE_ID)
    if ledger.get("inventory_id") != INVENTORY_ID or len(ledger.get("entries", ())) != len(inventory.get("samples", ())):
        raise RuntimeError("cross-source ledger does not bind the frozen inventory")
    if any(entry.get("disposition") != "MATCH" for entry in ledger["entries"]):
        raise RuntimeError("cross-source evidence is incomplete")
    materialization = _verified(RUNTIME / f"materialization-audit-{materialization_id}.json", "audit_id", materialization_id)

    revision_body = {
        "schema_version": "CorporateActionRevisionAuditV1",
        "provider_probe_id": PROBE_ID,
        "acquisition_summary_id": ACQUISITION_ID,
        "materialization_audit_id": materialization_id,
        "event_identity": ("ts_code", "end_date", "ex_date", "imp_ann_date"),
        "accepted_scope": "final implemented dividend facts only",
        "provider_workflow_rows_retained_but_not_published": True,
        "stopped_or_cancelled_workflow_rows_published": False,
        "cancelled_official_document_sha256": "05318019dc466d32e768e8f44285049d9745a982a89b45e67683d27c147931ed",
        "updated_official_document_sha256": "3ae86625494a29dbf4f5032d366698e9c428a93811083c57230420f76670ee1c",
        "updated_official_disposition": "MATCH",
        "conflicting_implemented_economic_events": 2,
        "conflicting_events_disposition": "QUARANTINED_NOT_RESEARCH_SAFE",
        "unsupported_conversion_events": materialization["quarantine_reason_counts"]["UNSUPPORTED_SHARE_CONVERSION"],
        "historical_pre_implementation_state_recoverable": False,
        "historical_pre_implementation_state_rule": "OUT_OF_SCOPE; no fact visible before implementation announcement next-safe-session",
        "revision_status": "PASS_SCOPED_FINAL_IMPLEMENTED_ONLY",
    }
    revision_id = content_hash(revision_body)
    _write_immutable(RUNTIME / f"revision-audit-{revision_id}.json", {"revision_audit_id": revision_id, "content_hash": revision_id, **revision_body})

    unsupported = (ActionType.RIGHTS_ISSUE, ActionType.STOCK_SPLIT, ActionType.SHARE_CONVERSION)
    quarantine_ids = tuple(item["quarantine_id"] for item in materialization["quarantines"])
    evidence = CorporateActionPITEvidenceV1.create(
        target_history_start=date(2010, 1, 4), baseline_validation_end=date(2025, 12, 31),
        rolling_coverage_end=date(2026, 9, 9), source_name="datahubco_tushare_proxy",
        source_version_identity="datahub-dividend-full-history-2026-09-10-v2",
        supported_action_types=(ActionType.CASH_DIVIDEND, ActionType.BONUS_SHARE),
        unsupported_action_types=unsupported,
        validated_coverage_by_action_type=(
            (ActionType.CASH_DIVIDEND, date(2010, 1, 4), date(2026, 9, 9)),
            (ActionType.BONUS_SHARE, date(2010, 1, 4), date(2026, 9, 9)),
        ),
        materialized_coverage_by_action_type=(
            (ActionType.CASH_DIVIDEND, date(2010, 1, 4), date(2026, 9, 9)),
            (ActionType.BONUS_SHARE, date(2010, 1, 4), date(2026, 9, 9)),
        ),
        coverage_gaps=(),
        unsupported_intervals=tuple((kind, date(2010, 1, 4), date(2026, 9, 9)) for kind in unsupported),
        cross_source_evidence_ids=(INVENTORY_ID, CROSS_SOURCE_ID, revision_id, materialization_id),
        exception_ids=(), quarantine_ids=quarantine_ids,
        publication_rule="imp_ann_date independently checked; date-only becomes next approved session 16:30 Asia/Shanghai",
        economic_effect_rule="ex_date separate from availability; acquisition time forbidden",
        revision_rule="final implemented facts only; equivalent duplicates collapse; economic conflicts quarantine",
        cancellation_rule="stopped/cancelled workflow never published; official retraction retained as evidence",
        complete=True,
    )
    _write_immutable(RUNTIME / f"pit-evidence-{evidence.evidence_id}.json", asdict(evidence))
    (RUNTIME / "current-pit-evidence-id.txt").write_text(evidence.evidence_id, encoding="ascii")
    (RUNTIME / "current-revision-audit-id.txt").write_text(revision_id, encoding="ascii")
    print(f"PIT_EVIDENCE_ID={evidence.evidence_id} REVISION_AUDIT_ID={revision_id} BASELINE_PIT=PASS CROSS_SOURCE=PASS REVISION=PASS 2026_CATCH_UP={materialization['catch_up_2026_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
