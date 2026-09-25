"""One-time, zero-provider reconstruction of approved historical Daily Bar membership.

The named source checkout is input only. All published readers use the physical
portable corpus written under --output and never reopen the source checkout.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.historical_daily_bar_authority import (  # noqa: E402
    HistoricalDailyBarFactAuthorityV1, HistoricalDailyBarFactReaderV1,
)
from v5_2.data.historical_daily_bar_governance import (  # noqa: E402
    create_derived_artifacts, validate_historical_parent,
)
from v5_2.data.historical_daily_bar_materialization import materialize_verified_source  # noqa: E402
from v5_2.data.historical_remediation import build_next_session_availability_map  # noqa: E402
from v5_2.data.identity import canonical_json, content_hash  # noqa: E402
from v5_2.data.raw_artifacts import AcquisitionReceiptV1, RawPayloadArtifactV1  # noqa: E402
from v5_2.refresh.daily_bar_composite import _verify  # noqa: E402

PANEL_ID = "a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d"
PARENT_APPROVAL_ID = "eaa2c254b85077ae8f988c393b133ba90f5443025d2cfdbe10523229f8f753f4"
PARENT_MANIFEST_ID = "cb79850fac1c28e7b1e8bd9991d65c26f61add832b2f5ed67c40c586a13fd8c6"
BINDING_ID = "176dba27d4cb6943e2434f1608668dc5bc756fa2e1357e18098927873032f3e8"
AVAILABILITY_ID = "2bb3877daa164b5c09b617c9a44168d1a8035fae6e247ef4cb023d313070448e"
COMPOSITE_ID = "0053aa0c80a5561dd8557156555bfdb47c841901477a737a0a0a2f5807918744"
CORRECTED_MANIFEST_ID = "9f38b28b3b2a4f93a16fe80144a1b894fdbabc1afea0e9dbe58009d3bce051e4"
BASE_CALENDAR_ID = "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01"
EXTENSION_CALENDAR_ID = "3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a"
MASTER_BUNDLE_ID = "2675dc691521dbcfecc3ac48c8ef3af1e3fb69a9230afb6835c9a3a0ad86e69a"


def _load(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _require_hash(value: dict, *, schema: str, id_field: str, expected: str) -> None:
    body = {key: item for key, item in value.items() if key not in {id_field, "content_hash"}}
    if (value.get(id_field) != expected or value.get("content_hash") != expected
            or content_hash({"schema_version": schema, **body}) != expected):
        raise RuntimeError(f"frozen {schema} integrity failed")


def _write_exact(path: Path, value: dict) -> None:
    encoded = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("immutable governance artifact collision")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)


def _calendar(source_main: Path) -> tuple[str, ...]:
    base = _load(source_main / "data/phase_1b1/governance" / f"daily-bar-universe-{BASE_CALENDAR_ID}.json")
    extension = _load(source_main / "data/phase_1b1_2026_extension/governance"
                      / f"calendar-extension-{EXTENSION_CALENDAR_ID}.json")
    _require_hash(base, schema="DeterministicDailyBarUniverseV1",
                  id_field="universe_id", expected=BASE_CALENDAR_ID)
    _require_hash(extension, schema="IncrementalCalendarExtensionV1",
                  id_field="extension_id", expected=EXTENSION_CALENDAR_ID)
    sessions = set(base["ordered_sessions"])
    sessions.update(row[1] for row in extension["ordered_rows"]
                    if row[2] == 1 and row[1] <= "20260911")
    if "20260911" not in sessions:
        raise RuntimeError("2026-09-10 has no approved next safe session")
    return tuple(sorted(sessions))


def _lifecycles(source_main: Path) -> dict[str, tuple[str, str]]:
    target = _load(ROOT / "data/phase_1b_exit_remediation/governance"
                   / f"complete-security-master-fact-bundle-{MASTER_BUNDLE_ID}.json")
    body = {key: item for key, item in target.items()
            if key not in {"fact_bundle_id", "content_hash"}}
    if (target.get("fact_bundle_id") != MASTER_BUNDLE_ID
            or target.get("content_hash") != MASTER_BUNDLE_ID
            or content_hash(body) != MASTER_BUNDLE_ID):
        raise RuntimeError("frozen target master bundle integrity failed")
    all_lifecycles: dict[str, tuple[str, str]] = {}
    for root in (source_main / "data/phase_1b1", source_main / "data/phase_1b1_2026_extension"):
        for path in (root / "raw/datahubco_tushare_proxy/security_master").rglob("*.json"):
            raw = _load(path)
            artifact = RawPayloadArtifactV1.create(**{
                key: raw[key] for key in ("request_id", "page_identity", "provider_payload", "semantic_metadata")})
            if artifact.payload_hash != raw.get("payload_hash") or path.stem != artifact.payload_hash:
                raise RuntimeError("frozen security-master raw integrity failed")
            for row in raw["provider_payload"]["rows"]:
                identity = str(row.get("ts_code", ""))
                if identity.endswith((".SH", ".SZ")):
                    lifecycle = (str(row.get("list_date") or "00000000"),
                                 str(row.get("delist_date") or "99999999"))
                    if identity in all_lifecycles and all_lifecycles[identity] != lifecycle:
                        raise RuntimeError("conflicting frozen security lifecycle")
                    all_lifecycles[identity] = lifecycle
    target_set = set(target["ordered_security_identities"])
    if target_set - set(all_lifecycles):
        raise RuntimeError("target security lifecycle is incomplete")
    return {identity: all_lifecycles[identity] for identity in sorted(target_set)}


def _verify_receipts(source_main: Path, expected: tuple[str, ...]) -> int:
    paths = tuple(path for root in (
        source_main / "data/phase_1b1/receipts",
        source_main / "data/phase_1b_exit_daily_bar_2026/receipts",
    ) for path in root.rglob("*.json"))
    observed = []
    for path in paths:
        raw = _load(path)
        receipt = AcquisitionReceiptV1.create(
            payload_hash=raw["payload_hash"],
            acquired_at=datetime.fromisoformat(raw["acquired_at"]),
            attempt_metadata=raw["attempt_metadata"],
            transport_metadata=raw["transport_metadata"],
        )
        if receipt.receipt_hash != raw.get("receipt_hash") or path.stem != receipt.receipt_hash:
            raise RuntimeError("receipt content identity failed")
        observed.append(receipt.receipt_hash)
    if (len(observed) != len(set(observed))
            or tuple(sorted(observed)) != tuple(expected)):
        raise RuntimeError("receipt inventory disagrees with frozen parent")
    return len(observed)


def _parents() -> dict:
    parent_root = ROOT / "data/phase_1c_lineage_remediation/governance"
    parents = {
        "panel": _load(ROOT / "data/phase_1b_exit_remediation/governance"
                       / f"historical-daily-bar-panel-{PANEL_ID}.json"),
        "approval": _load(parent_root / f"historical-baseline-approval-{PARENT_APPROVAL_ID}.json"),
        "manifest": _load(parent_root / f"historical-baseline-manifest-{PARENT_MANIFEST_ID}.json"),
        "binding": _load(parent_root / f"historical-baseline-binding-{BINDING_ID}.json"),
        "availability": _load(parent_root / f"historical-baseline-availability-{AVAILABILITY_ID}.json"),
    }
    revoked = tuple(_load(path)["approval_id"] for path in parent_root.glob("approval-revocation-*.json"))
    validate_historical_parent(**parents, revoked_approval_ids=revoked)
    parents["revoked_approval_ids"] = revoked
    parents["parent_composite"] = _load(parent_root / f"phase1c-daily-bar-composite-{COMPOSITE_ID}.json")
    corrected = _load(ROOT / "data/phase_1b2b/governance"
                      / f"daily-bar-manifest-{CORRECTED_MANIFEST_ID}.json")
    if not _verify(corrected, "dataset_id") or corrected["dataset_id"] != CORRECTED_MANIFEST_ID:
        raise RuntimeError("corrected overlap manifest integrity failed")
    parents["corrected_manifest"] = corrected
    return parents


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-main", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/phase_1b_historical_daily_bar_fact_authority")
    args = parser.parse_args()
    source_main = args.source_main.resolve(strict=True)
    output = args.output.resolve()
    if source_main == ROOT.resolve() or source_main == output:
        raise RuntimeError("source checkout and portable output must be distinct")
    parents = _parents()
    panel, corrected = parents["panel"], parents["corrected_manifest"]
    sessions = _calendar(source_main)
    research_sessions = tuple(day for day in sessions if "20100104" <= day <= "20260910")
    next_safe = {day: timestamp for day, _, timestamp in build_next_session_availability_map(
        research_sessions=research_sessions, approved_sessions=sessions)}
    lifecycles = _lifecycles(source_main)
    requested = sum(sum(max(start, "20100104") <= day <= min(end, "20260910")
                        for day in research_sessions) for start, end in lifecycles.values())
    if requested != panel["requested_effective_symbol_sessions"]:
        raise RuntimeError("independent effective symbol-session census disagrees")
    receipt_count = _verify_receipts(source_main, tuple(parents["manifest"]["receipt_hashes"]))
    raw_roots = (source_main / "data/phase_1b1/raw/datahubco_tushare_proxy/daily_bar",
                 source_main / "data/phase_1b_exit_daily_bar_2026/raw/datahubco_tushare_proxy/daily_bar")
    results = []
    for run_number in (1, 2):
        result = materialize_verified_source(
            raw_roots=raw_roots, expected_hashes=tuple(panel["raw_payload_hashes"]),
            output_root=output, target_identities=lifecycles,
            next_safe_by_session=next_safe,
            normalization_policy_id=panel["normalization_policy_id"],
            unit_policy_id=panel["unit_policy_id"],
            sample_sessions=tuple(item[0] for item in panel["frozen_session_observed_counts"]),
            corrected_root=source_main / "data/phase_1b2b/facts/daily_bar",
            corrected_shard_hashes=tuple(corrected["fact_content_hashes"]),
            corrected_approval_id=corrected["approval_id"],
        )
        if (result.row_count != panel["row_count"]
                or result.symbol_count != panel["symbol_count"]
                or result.excluded_non_target_count != panel["excluded_non_target_row_count"]
                or result.frozen_session_observed_counts
                    != tuple(map(tuple, panel["frozen_session_observed_counts"]))
                or result.frozen_session_symbol_hashes
                    != tuple(map(tuple, panel["frozen_session_symbol_hashes"]))
                or result.overlap_row_count != corrected["row_count"]
                or result.overlap_shard_count != len(corrected["fact_content_hashes"])):
            raise RuntimeError("reconstructed facts disagree with frozen parent or corrected overlap")
        results.append(result)
        print(f"RUN {run_number}: rows={result.row_count} symbols={result.symbol_count} "
              f"overlap={result.overlap_row_count} shards={len(result.shards)}", flush=True)
    if results[0] != results[1]:
        raise RuntimeError("two complete rematerializations are not deterministic")
    result = results[0]
    authority = HistoricalDailyBarFactAuthorityV1.create(
        parent_panel_id=PANEL_ID, parent_approval_id=PARENT_APPROVAL_ID,
        parent_manifest_id=PARENT_MANIFEST_ID, source_binding_id=BINDING_ID,
        source_content_set_id=parents["binding"]["source_content_set_identity"],
        availability_evidence_id=AVAILABILITY_ID,
        calendar_lineage_id=parents["availability"]["approved_calendar_lineage_id"],
        normalization_policy_id=panel["normalization_policy_id"],
        unit_policy_id=panel["unit_policy_id"],
        identity_policy_id=parents["binding"]["identity_policy_version"],
        raw_payload_hashes=tuple(panel["raw_payload_hashes"]),
        shards=result.shards, symbol_count=result.symbol_count,
        coverage_start=panel["coverage_start"], coverage_end=panel["coverage_end"],
    )
    authority.write_exact(output)
    # Independently traverse the portable corpus; no provider/raw access here.
    reader = HistoricalDailyBarFactReaderV1(
        output, authority, expected_manifest_id=PARENT_MANIFEST_ID,
        revoked_approval_ids=parents["revoked_approval_ids"])
    verified_rows = 0
    approved_raw_hashes = set(authority.raw_payload_hashes)
    for month in sorted(reader.by_month):
        for fact in reader.read_month(month):
            day = fact.session.strftime("%Y%m%d")
            if (fact.available_at.isoformat() != next_safe[day]
                    or fact.source_payload_hash not in approved_raw_hashes):
                raise RuntimeError("portable fact violates frozen PIT or source lineage")
            verified_rows += 1
    if verified_rows != authority.row_count:
        raise RuntimeError("portable corpus row count disagrees with authority")
    observed = asdict(result)
    artifacts = create_derived_artifacts(
        authority=authority, observed=observed,
        requested_effective_symbol_sessions=requested,
        receipt_count=receipt_count,
        corrected_overlap_row_count=result.overlap_row_count,
        **parents,
    )
    names = {"coverage_ledger": ("historical-daily-bar-coverage-ledger", "ledger_id"),
             "approval": ("historical-daily-bar-representation-approval", "approval_id"),
             "manifest": ("historical-daily-bar-representation-manifest", "manifest_id"),
             "composition": ("historical-daily-bar-representation-composition", "composition_id")}
    for kind, (prefix, id_field) in names.items():
        value = artifacts[kind]
        _write_exact(output / "governance" / f"{prefix}-{value[id_field]}.json", value)
    replay_body = {
        "schema_version": "HistoricalDailyBarDeterministicReplayEvidenceV1",
        "authority_id": authority.authority_id,
        "membership_set_hash": authority.membership_set_hash,
        "run_1_shard_descriptors_hash": content_hash(results[0].shards),
        "run_2_shard_descriptors_hash": content_hash(results[1].shards),
        "run_1_observation_hash": content_hash(asdict(results[0])),
        "run_2_observation_hash": content_hash(asdict(results[1])),
        "coverage_ledger_id": artifacts["coverage_ledger"]["ledger_id"],
        "approval_id": artifacts["approval"]["approval_id"],
        "manifest_id": artifacts["manifest"]["manifest_id"],
        "composition_id": artifacts["composition"]["composition_id"],
        "complete_runs": 2,
    }
    replay_id = content_hash(replay_body)
    _write_exact(output / "governance" / f"historical-daily-bar-replay-{replay_id}.json",
                 {**replay_body, "replay_id": replay_id, "content_hash": replay_id})
    exact_reader = HistoricalDailyBarFactReaderV1.load_exact(
        output, authority_id=authority.authority_id,
        approval_id=artifacts["approval"]["approval_id"],
        manifest_id=artifacts["manifest"]["manifest_id"],
        revoked_approval_ids=parents["revoked_approval_ids"],
    )
    first = exact_reader.read_month(authority.shards[0].month)[0]
    if exact_reader.resolve(first.security_identity, first.session)["fact_id"] != first.fact_id:
        raise RuntimeError("portable exact lookup failed")
    print(json.dumps({
        "rows": authority.row_count, "symbols": authority.symbol_count,
        "shards": len(authority.shards), "raw_payloads": len(authority.raw_payload_hashes),
        "receipts": receipt_count, "requested_effective_symbol_sessions": requested,
        "missing_symbol_sessions": requested - authority.row_count,
        "corrected_overlap_rows": result.overlap_row_count,
        "authority_id": authority.authority_id,
        "membership_set_hash": authority.membership_set_hash,
        "coverage_ledger_id": artifacts["coverage_ledger"]["ledger_id"],
        "approval_id": artifacts["approval"]["approval_id"],
        "manifest_id": artifacts["manifest"]["manifest_id"],
        "composition_id": artifacts["composition"]["composition_id"],
        "replay_id": replay_id, "provider_requests": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
