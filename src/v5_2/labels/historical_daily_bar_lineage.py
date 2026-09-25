"""Read-only Phase 2B adapter over exact approved historical Daily Bar facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.historical_daily_bar_authority import (
    HistoricalDailyBarAuthorityError,
    HistoricalDailyBarFactReaderV1,
)
from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.contracts import DomainLineageV1


_ID = re.compile(r"^[0-9a-f]{64}$")


def _governance(root: Path, prefix: str, identity: str, schema: str, id_field: str) -> dict:
    path = root / "governance" / f"{prefix}-{identity}.json"
    try:
        raw_bytes = path.read_bytes()
        value = json.loads(raw_bytes)
    except (OSError, ValueError) as error:
        raise ValueError(f"exact {schema} artifact is missing or invalid") from error
    body = {key: item for key, item in value.items()
            if key not in {id_field, "content_hash"}}
    if (value.get("schema_version") != schema or value.get(id_field) != identity
            or value.get("content_hash") != identity
            or content_hash(body) != identity
            or canonical_json(value) != raw_bytes):
        raise ValueError(f"exact {schema} content address mismatch")
    return value


@dataclass(frozen=True, slots=True)
class HistoricalDailyBarMonthWindowV1:
    month: str
    h5_end: date
    approval_id: str
    manifest_id: str
    evidence_ids: tuple[str, ...]
    facts: tuple[DailyBarFactV1, ...]

    def facts_for(self, identity: str, sessions: tuple[date, ...]) -> tuple[DailyBarFactV1, ...]:
        if (not sessions or sessions != tuple(sorted(set(sessions)))
                or sessions[0].strftime("%Y-%m") != self.month
                or sessions[-1] > self.h5_end):
            raise ValueError("requested Daily Bar sessions are outside the bounded window")
        wanted = set(sessions)
        return tuple(row for row in self.facts
                     if row.security_identity == identity and row.session in wanted)

    def lineage_for(self, identity: str, sessions: tuple[date, ...]) -> DomainLineageV1:
        selected = self.facts_for(identity, sessions)
        return DomainLineageV1.create(
            domain="daily_bar", approval_id=self.approval_id,
            manifest_id=self.manifest_id,
            fact_ids=tuple(row.fact_id for row in selected),
            evidence_ids=self.evidence_ids,
        )


@dataclass(frozen=True, slots=True)
class HistoricalDailyBarLineageV1:
    reader: HistoricalDailyBarFactReaderV1
    coverage_ledger_id: str
    composition_id: str
    replay_id: str
    parent_composite_id: str

    @classmethod
    def load_exact(
        cls, root: Path, *, authority_id: str, approval_id: str,
        manifest_id: str, coverage_ledger_id: str, composition_id: str,
        replay_id: str, revoked_approval_ids: tuple[str, ...],
    ) -> "HistoricalDailyBarLineageV1":
        if not all(_ID.fullmatch(value) for value in (
            authority_id, approval_id, manifest_id, coverage_ledger_id,
            composition_id, replay_id,
        )):
            raise ValueError("Daily Bar governance requires exact immutable IDs")
        try:
            reader = HistoricalDailyBarFactReaderV1.load_exact(
                root, authority_id=authority_id, approval_id=approval_id,
                manifest_id=manifest_id, revoked_approval_ids=revoked_approval_ids,
            )
        except HistoricalDailyBarAuthorityError as error:
            raise ValueError("approved Daily Bar membership is not verifiable") from error
        composition = _governance(
            root, "historical-daily-bar-representation-composition", composition_id,
            "HistoricalDailyBarRepresentationCompositionV1", "composition_id",
        )
        replay = _governance(
            root, "historical-daily-bar-replay", replay_id,
            "HistoricalDailyBarDeterministicReplayEvidenceV1", "replay_id",
        )
        if (composition.get("derived_historical_manifest_id") != manifest_id
                or composition.get("parent_historical_manifest_id")
                    != reader.authority.parent_manifest_id
                or replay.get("authority_id") != authority_id
                or replay.get("approval_id") != approval_id
                or replay.get("manifest_id") != manifest_id
                or replay.get("coverage_ledger_id") != coverage_ledger_id
                or replay.get("composition_id") != composition_id
                or replay.get("membership_set_hash")
                    != reader.authority.membership_set_hash
                or replay.get("complete_runs") != 2
                or replay.get("run_1_observation_hash")
                    != replay.get("run_2_observation_hash")
                or replay.get("run_1_shard_descriptors_hash")
                    != replay.get("run_2_shard_descriptors_hash")
                or not _ID.fullmatch(str(composition.get("parent_composite_id", "")))):
            raise ValueError("Daily Bar composition or deterministic replay does not match")
        return cls(reader, coverage_ledger_id, composition_id, replay_id,
                   composition["parent_composite_id"])

    def read_window(self, month: str, h5_end: date) -> HistoricalDailyBarMonthWindowV1:
        rows = self.reader.read_window(month, h5_end)
        authority = self.reader.authority
        evidence = (
            authority.authority_id, authority.membership_set_hash,
            self.reader.derived_approval_id, self.reader.derived_manifest_id,
            self.coverage_ledger_id, self.composition_id, self.replay_id,
            authority.parent_panel_id, authority.parent_manifest_id,
            authority.parent_approval_id, self.parent_composite_id,
        )
        return HistoricalDailyBarMonthWindowV1(
            month, h5_end, self.reader.derived_approval_id,
            self.reader.derived_manifest_id, evidence, rows,
        )
