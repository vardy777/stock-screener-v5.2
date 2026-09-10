from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.checkpoints import CheckpointStore  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.corporate_action_acquisition import acquire_corporate_action_requests  # noqa: E402
from v5_2.data.real_audits.corporate_action_entry import build_corporate_action_inventory  # noqa: E402
from v5_2.integrations.datahub_http import DataHubHttpTransport  # noqa: E402
from v5_2.providers.credentials import load_datahub_credential  # noqa: E402
from v5_2.providers.datahub import DataHubClient  # noqa: E402
from v5_2.providers.rate_limit import RateLimiter  # noqa: E402


COHORT = tuple(sorted((
    "000001.SZ", "000002.SZ", "000333.SZ", "000651.SZ", "000858.SZ",
    "002001.SZ", "002415.SZ", "002594.SZ", "300015.SZ", "300059.SZ",
    "300750.SZ", "600000.SH", "600036.SH", "600276.SH", "600519.SH",
    "601318.SH", "601398.SH", "603288.SH", "688981.SH", "688599.SH",
)))
RUNTIME = ROOT / "data" / "phase_1b2c"


def _write_immutable(path: Path, value: object) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError("immutable sample inventory collision")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    upstream = (
        "1581b4d367dba1256247ddd13e09b53d0f95b5b1deeb40af9e6ed4a36606353b",
        "f208c17accba6b669359f476b2fdf3a1bc9ec6856e7fa1831ccdd1c42b80d8cf",
    )
    inventory = build_corporate_action_inventory(
        symbols=COHORT, endpoint="dividend", target_history_start=date(2010, 1, 4),
        baseline_validation_end=date(2025, 12, 31), rolling_coverage_end=date(2026, 9, 9),
        upstream_approval_ids=upstream, active_approval_ids=upstream, revoked_approval_ids=(),
    )
    credential = load_datahub_credential(env_file=ROOT / ".env", repository_root=ROOT)
    result = acquire_corporate_action_requests(
        tuple(item.request for item in inventory.requests),
        client=DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30)),
        credential=credential, raw_store=RawArtifactStore(RUNTIME),
        checkpoint_store=CheckpointStore(RUNTIME), limiter=RateLimiter(min_interval_seconds=0.05),
        utc_clock=lambda: datetime.now(timezone.utc), resume=True,
    )
    candidates = []
    store = RawArtifactStore(RUNTIME)
    for item in inventory.requests:
        request_root = RUNTIME / "raw" / "datahubco_tushare_proxy" / "corporate_action" / item.request.request_id[:16]
        for path in request_root.rglob("*.json"):
            artifact = store.read_payload(path)
            candidates.extend(artifact.provider_payload["rows"])
    eligible = []
    for row in candidates:
        if str(row.get("div_proc")) != "实施" or not row.get("imp_ann_date") or not row.get("ex_date"):
            continue
        announcement = str(row["imp_ann_date"])
        if not ("20100104" <= announcement <= "20260909"):
            continue
        cash = float(row.get("cash_div_tax") or 0)
        bonus = float(row.get("stk_bo_rate") or 0)
        conversion = float(row.get("stk_co_rate") or 0)
        if conversion > 0 or (cash <= 0 and bonus <= 0):
            continue
        stratum = "CASH_BONUS_COMBINED" if cash > 0 and bonus > 0 else ("BONUS_SHARE" if bonus > 0 else "CASH_DIVIDEND")
        period = "EARLY" if announcement < "20150101" else ("MIDDLE" if announcement < "20220101" else ("CATCH_UP_2026" if announcement >= "20260101" else "RECENT"))
        body = {
            "security_identity": row["ts_code"], "stratum": stratum, "period": period,
            "exchange": str(row["ts_code"]).split(".")[-1], "announcement_date": announcement,
            "provider_fields": {key: row.get(key) for key in (
                "ann_date", "div_proc", "stk_div", "stk_bo_rate", "stk_co_rate",
                "cash_div", "cash_div_tax", "record_date", "ex_date", "pay_date",
                "div_listdate", "imp_ann_date")},
        }
        eligible.append({"sample_id": content_hash(body), **body})
    selected = []
    for stratum in ("CASH_DIVIDEND", "BONUS_SHARE", "CASH_BONUS_COMBINED"):
        for period in ("EARLY", "MIDDLE", "RECENT", "CATCH_UP_2026"):
            pool = sorted((row for row in eligible if row["stratum"] == stratum and row["period"] == period), key=lambda row: row["sample_id"])
            selected.extend(pool[:2])
    selected = sorted({row["sample_id"]: row for row in selected}.values(), key=lambda row: row["sample_id"])
    artifact = {
        "schema_version": "CorporateActionSampleInventoryV1", "selection_policy": "lowest-two-content-hashes-per-action-period-v1",
        "candidate_cohort": COHORT, "candidate_inventory_id": inventory.inventory_id,
        "samples": selected,
    }
    artifact_id = content_hash(artifact)
    artifact = {"inventory_id": artifact_id, "content_hash": artifact_id, **artifact}
    _write_immutable(RUNTIME / "governance" / f"sample-inventory-{artifact_id}.json", artifact)
    print(f"INVENTORY_ID={artifact_id} CANDIDATE_ROWS={len(candidates)} SAMPLES={len(selected)} REQUESTS={result.completed_requests}")
    print("STRATA=" + json.dumps({name: sum(row["stratum"] == name for row in selected) for name in ("CASH_DIVIDEND", "BONUS_SHARE", "CASH_BONUS_COMBINED")}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
