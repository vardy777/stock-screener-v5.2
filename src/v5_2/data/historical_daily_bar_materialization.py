"""Offline conversion of frozen Daily Bar raw observations to existing facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import tempfile

from v5_2.data.historical_daily_bar_authority import (
    HistoricalDailyBarFactShardV1,
    HistoricalDailyBarShardDescriptorV1,
    _fact_from_dict,
)
from v5_2.data.identity import canonical_json, content_hash

from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.historical_remediation import classify_daily_bar_identity
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.data.real_audits.daily_bar_normalization import (
    DailyBarNormalizationPolicyV1,
    finite_decimal,
)


class HistoricalDailyBarMaterializationError(RuntimeError):
    """Frozen source or normalization identity cannot be proven."""


FROZEN_UNIT_POLICY_ID = "e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093"
FROZEN_AVAILABILITY_POLICY_VERSION = "daily-bar-availability-v1"


@dataclass(frozen=True, slots=True)
class HistoricalDailyBarMaterializationResultV1:
    shards: tuple[HistoricalDailyBarShardDescriptorV1, ...]
    row_count: int
    symbol_count: int
    excluded_non_target_count: int
    frozen_session_observed_counts: tuple[tuple[str, int], ...]
    frozen_session_symbol_hashes: tuple[tuple[str, str], ...]
    overlap_row_count: int
    overlap_shard_count: int


def _read_raw(path: Path) -> RawPayloadArtifactV1:
    try:
        stored = json.loads(path.read_bytes())
        claimed = stored.pop("payload_hash")
        artifact = RawPayloadArtifactV1.create(**stored)
        if artifact.payload_hash != claimed or path.stem != claimed:
            raise HistoricalDailyBarMaterializationError("raw payload hash mismatch")
        return artifact
    except (ValueError, KeyError, TypeError) as error:
        raise HistoricalDailyBarMaterializationError("raw payload is malformed") from error


def normalize_verified_payload(
    artifact: RawPayloadArtifactV1, *, expected_hash: str,
    target_identities: dict[str, tuple[str, str]],
    next_safe_by_session: dict[str, str],
    normalization_policy_id: str, unit_policy_id: str,
) -> tuple[tuple[DailyBarFactV1, ...], int]:
    if (artifact.payload_hash != expected_hash
            or RawPayloadArtifactV1.create(
                request_id=artifact.request_id, page_identity=artifact.page_identity,
                provider_payload=artifact.provider_payload,
                semantic_metadata=artifact.semantic_metadata,
            ).payload_hash != expected_hash):
        raise HistoricalDailyBarMaterializationError("raw payload identity mismatch")
    if (DailyBarNormalizationPolicyV1.create_default().policy_id != normalization_policy_id
            or unit_policy_id != FROZEN_UNIT_POLICY_ID):
        raise HistoricalDailyBarMaterializationError("normalizer or unit policy identity mismatch")
    rows = artifact.provider_payload.get("rows")
    if not isinstance(rows, list):
        raise HistoricalDailyBarMaterializationError("raw Daily Bar rows are missing")
    facts = []
    excluded = 0
    seen = set()
    for row in rows:
        try:
            symbol, session_text = str(row["ts_code"]), str(row["trade_date"])
            key = (symbol, session_text)
            if key in seen:
                raise HistoricalDailyBarMaterializationError("duplicate raw security-session")
            seen.add(key)
            disposition = classify_daily_bar_identity(symbol, target_identities)
            if disposition == "EXCLUDED_NON_TARGET":
                excluded += 1
                continue
            if disposition != "TARGET":
                raise HistoricalDailyBarMaterializationError("unresolved target identity")
            timestamp = next_safe_by_session[session_text]
            session = date(int(session_text[:4]), int(session_text[4:6]), int(session_text[6:8]))
            available_at = datetime.fromisoformat(timestamp)
            if available_at.date() <= session or available_at.hour != 16 or available_at.minute != 30:
                raise HistoricalDailyBarMaterializationError("next-session-safe boundary violated")
            fact = DailyBarFactV1.create(
                source_symbol=symbol, session=session,
                open=finite_decimal(row["open"]), high=finite_decimal(row["high"]),
                low=finite_decimal(row["low"]), close=finite_decimal(row["close"]),
                raw_volume=finite_decimal(row["vol"]), raw_amount=finite_decimal(row["amount"]),
                source_payload_hash=expected_hash, available_at=available_at,
                availability_policy_version=FROZEN_AVAILABILITY_POLICY_VERSION,
            )
            if not fact.verify():
                raise HistoricalDailyBarMaterializationError("normalized fact integrity failed")
            facts.append(fact)
        except (KeyError, TypeError, ValueError) as error:
            raise HistoricalDailyBarMaterializationError("malformed frozen Daily Bar observation") from error
    return tuple(facts), excluded


def materialize_verified_source(
    *, raw_roots: tuple[Path, ...], expected_hashes: tuple[str, ...],
    output_root: Path, target_identities: dict[str, tuple[str, str]],
    next_safe_by_session: dict[str, str], normalization_policy_id: str,
    unit_policy_id: str,
    sample_sessions: tuple[str, ...] = (),
    corrected_root: Path | None = None,
    corrected_shard_hashes: tuple[str, ...] = (),
    corrected_approval_id: str = "",
) -> HistoricalDailyBarMaterializationResultV1:
    """Verify the complete source set before conversion; never read providers."""
    files = tuple(sorted((path for root in raw_roots for path in root.rglob("*.json")),
                         key=lambda path: str(path)))
    if len(files) != len(expected_hashes) or len(expected_hashes) != len(set(expected_hashes)):
        raise HistoricalDailyBarMaterializationError("raw payload count or inventory duplicate")
    observed_hashes = tuple(_read_raw(path).payload_hash for path in files)
    if (len(observed_hashes) != len(set(observed_hashes))
            or set(observed_hashes) != set(expected_hashes)):
        raise HistoricalDailyBarMaterializationError("missing or extra frozen raw payload")
    output_root.mkdir(parents=True, exist_ok=True)
    symbols: set[str] = set()
    observed_samples = {session: set() for session in sample_sessions}
    descriptors = []
    rows_written = excluded_count = overlap_rows = 0
    corrected_seen: set[str] = set()
    if corrected_root is not None and (
        not corrected_approval_id or len(corrected_shard_hashes) != len(set(corrected_shard_hashes))
    ):
        raise HistoricalDailyBarMaterializationError("corrected overlap pin is incomplete")
    with tempfile.TemporaryDirectory(prefix="daily-bar-remat-", dir=output_root) as stage_name:
        stage = Path(stage_name)
        for path in files:
            artifact = _read_raw(path)
            facts, excluded = normalize_verified_payload(
                artifact, expected_hash=artifact.payload_hash,
                target_identities=target_identities,
                next_safe_by_session=next_safe_by_session,
                normalization_policy_id=normalization_policy_id,
                unit_policy_id=unit_policy_id,
            )
            excluded_count += excluded
            if corrected_root is not None:
                overlap = tuple(fact for fact in facts if date(2024, 1, 1) <= fact.session <= date(2025, 12, 31))
                directory = corrected_root / artifact.request_id[:16]
                matches = tuple(directory.glob("*.json"))
                if len(matches) != (1 if overlap else 0):
                    raise HistoricalDailyBarMaterializationError("corrected overlap shard is missing or ambiguous")
                if matches:
                    corrected_path = matches[0]
                    if (corrected_path.stem not in corrected_shard_hashes
                            or corrected_path.stem in corrected_seen):
                        raise HistoricalDailyBarMaterializationError("corrected overlap shard is not pinned")
                    corrected = json.loads(corrected_path.read_bytes())
                    digest = corrected.pop("content_hash", None)
                    if (digest != corrected_path.stem or content_hash(corrected) != digest
                            or corrected.get("approval_id") != corrected_approval_id):
                        raise HistoricalDailyBarMaterializationError("corrected overlap lineage integrity failed")
                    old_facts = tuple(_fact_from_dict(item) for item in corrected["facts"])
                    if (len(overlap) != len(old_facts)
                            or sorted((fact.fact_id, canonical_json(fact.as_dict())) for fact in overlap)
                            != sorted((fact.fact_id, canonical_json(fact.as_dict())) for fact in old_facts)):
                        raise HistoricalDailyBarMaterializationError("corrected overlap facts disagree")
                    corrected_seen.add(digest)
                    overlap_rows += len(overlap)
            for row in artifact.provider_payload["rows"]:
                source_symbol = str(row["ts_code"])
                if classify_daily_bar_identity(source_symbol, target_identities) == "TARGET":
                    symbols.add(source_symbol)
                    session_text = str(row["trade_date"])
                    if session_text in observed_samples:
                        observed_samples[session_text].add(source_symbol)
            by_month: dict[str, list[DailyBarFactV1]] = {}
            for fact in facts:
                by_month.setdefault(fact.session.strftime("%Y-%m"), []).append(fact)
            for month, month_facts in by_month.items():
                with (stage / f"{month}.jsonl").open("ab") as stream:
                    for fact in month_facts:
                        stream.write(canonical_json(fact.as_dict()) + b"\n")
            rows_written += len(facts)
        for spool in sorted(stage.glob("*.jsonl")):
            facts = tuple(_fact_from_dict(json.loads(line)) for line in spool.read_bytes().splitlines())
            shard = HistoricalDailyBarFactShardV1.create(spool.stem, facts)
            shard.write_exact(output_root)
            descriptors.append(shard.descriptor)
    if sum(item.row_count for item in descriptors) != rows_written:
        raise HistoricalDailyBarMaterializationError("materialized row count changed")
    if corrected_root is not None and corrected_seen != set(corrected_shard_hashes):
        raise HistoricalDailyBarMaterializationError("corrected overlap shard set is incomplete")
    ordered_samples = tuple(sorted(observed_samples))
    return HistoricalDailyBarMaterializationResultV1(
        shards=tuple(descriptors), row_count=rows_written, symbol_count=len(symbols),
        excluded_non_target_count=excluded_count,
        frozen_session_observed_counts=tuple((day, len(observed_samples[day])) for day in ordered_samples),
        frozen_session_symbol_hashes=tuple(
            (day, content_hash(tuple(sorted(observed_samples[day])))) for day in ordered_samples),
        overlap_row_count=overlap_rows, overlap_shard_count=len(corrected_seen),
    )
