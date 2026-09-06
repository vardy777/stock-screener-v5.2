from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.identity import canonical_json  # noqa: E402
from v5_2.data.phase_1b1_policies import phase_1b1_policies  # noqa: E402
from v5_2.data.phase_1b1_requests import phase_1b1_requests  # noqa: E402
from v5_2.data.raw_artifacts import RawArtifactStore  # noqa: E402
from v5_2.data.real_audits.blocker_evidence import SecurityDisposition, SecurityMasterNormalizationExceptionEvidenceV1, TradeCalendarUnresolvedSampleInventoryV1  # noqa: E402
from v5_2.data.real_audits.security_master_normalization import SecurityMasterNormalizationPolicyV1  # noqa: E402


AS_OF = datetime(2026, 9, 6, tzinfo=timezone.utc)
SSE_2025 = "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/announcement/general/c/c_20241223_10767108.shtml"
SZSE_2025 = "https://www.szse.cn/disclosure/notice/general/index_8.html"
SSE_CDR = "https://www.sse.com.cn/disclosure/announcement/listing/c/c_20201027_5242851.shtml"
SSE_LEGACY = "https://www.sse.com.cn/disclosure/bond/c/2011-04-07/122065_20110407_1.pdf"
SZSE_REASSIGNED = "https://investor.szse.cn/disclosure/notice/general/t20250603_613877.html"


def _mapping(item):
    return {field.name: getattr(item, field.name) for field in fields(item)}


def _rows(kind: str):
    root = ROOT / "data" / "phase_1b1"
    store = RawArtifactStore(root)
    result = []
    hashes = []
    for request in phase_1b1_requests()[kind]:
        for path in sorted((root / "raw" / request.source_name / kind / request.request_id[:16]).rglob("*.json")):
            artifact = store.read_payload(path)
            result.extend(artifact.provider_payload["rows"])
            hashes.append(artifact.payload_hash)
    return result, tuple(sorted(hashes))


def _official_2025():
    closed = "01-01 01-26 01-28 01-29 01-30 01-31 02-01 02-02 02-03 02-04 02-08 04-04 04-05 04-06 04-27 05-01 05-02 05-03 05-04 05-05 05-31 06-01 06-02 09-28 10-01 10-02 10-03 10-04 10-05 10-06 10-07 10-08 10-11".split()
    opened = "01-02 02-05 04-07 05-06 06-03 10-09".split()
    values = {(exchange, f"2025-{day}"): 0 for exchange in ("SSE", "SZSE") for day in closed}
    values.update({(exchange, f"2025-{day}"): 1 for exchange in ("SSE", "SZSE") for day in opened})
    return values


def main() -> int:
    output = ROOT / "data" / "phase_1b1" / "governance"
    output.mkdir(parents=True, exist_ok=True)
    calendar_rows, calendar_hashes = _rows("trade_calendar")
    provider = {(row["exchange"], f'{row["cal_date"][:4]}-{row["cal_date"][4:6]}-{row["cal_date"][6:]}'): row["is_open"] for row in calendar_rows}
    policy = phase_1b1_policies()["trade_calendar"]
    inventory = TradeCalendarUnresolvedSampleInventoryV1.create(
        provider_observations=provider, official_observations=_official_2025(),
        official_source_identities={"SSE": SSE_2025, "SZSE": SZSE_2025},
        verified_at=AS_OF, policy_id=policy.policy_id, policy_version="calendar-inventory-v1",
    )
    (output / f"trade-calendar-unresolved-{inventory.inventory_id}.json").write_bytes(canonical_json(_mapping(inventory)))

    master_rows, master_hashes = _rows("security_master")
    normalization = SecurityMasterNormalizationPolicyV1.create_default()
    source_by_code = {"689009.SH": SSE_CDR, "T600018.SH": SSE_LEGACY, "302132.SZ": SZSE_REASSIGNED}
    exception_records = []
    eligible = excluded = unresolved = 0
    for row in master_rows:
        disposition = normalization.disposition(row)
        if disposition == "NORMALIZED_ELIGIBLE":
            normalization.normalize(row)
            eligible += 1
        elif disposition == "EXCLUDED_NON_TARGET":
            excluded += 1
            exception_records.append({**row, "classification": SecurityDisposition.EXCLUDED_NON_TARGET, "reason": "official record identifies CDR rather than A-share", "official_source_identity": source_by_code.get(row["ts_code"])})
        else:
            unresolved += 1
            exception_records.append({**row, "classification": SecurityDisposition.REJECTED_UNRESOLVED, "reason": "provider identity/history cannot be mapped without an exceptional effective-dated rule", "official_source_identity": source_by_code.get(row["ts_code"])})
    exceptions = SecurityMasterNormalizationExceptionEvidenceV1.create(
        records=exception_records, verified_at=AS_OF, policy_version="security-master-exceptions-v1",
        input_artifact_ids=(*master_hashes, normalization.policy_id),
    )
    (output / f"security-master-exceptions-{exceptions.evidence_id}.json").write_bytes(canonical_json(_mapping(exceptions)))
    print(f"TRADE_CALENDAR inventory={inventory.inventory_id} total={inventory.total_samples} verified={inventory.verified_samples} unresolved={inventory.unresolved_samples} mismatch={inventory.mismatch_samples}")
    print(f"SECURITY_MASTER input={len(master_rows)} eligible={eligible} excluded_non_target={excluded} unresolved={unresolved} evidence={exceptions.evidence_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
