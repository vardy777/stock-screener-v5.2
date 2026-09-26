"""Public metadata inventory for private, byte-addressed Phase 2B sources."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
from hashlib import sha256 as sha256_digest
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash


_ID = re.compile(r"^[0-9a-f]{64}$")
_DOMAINS = {"trade_calendar", "security_master", "daily_bar",
            "daily_security_status", "corporate_action"}


@dataclass(frozen=True, slots=True)
class PrivateCorpusEntryV1:
    logical_role: str
    domain: str
    sha256: str
    byte_size: int
    media_type: str
    authority_id: str
    approval_id: str
    dataset_manifest_id: str
    coverage_start: str | None
    coverage_end: str | None
    required_for_checkpoint18: bool

    def verify(self) -> bool:
        parts = self.logical_role.split("/")
        if (not self.logical_role.startswith("data/") or "\\" in self.logical_role
                or ":" in self.logical_role
                or any(part in ("", ".", "..") for part in parts)
                or self.domain not in _DOMAINS
                or not all(_ID.fullmatch(value) for value in (
                    self.sha256, self.authority_id, self.approval_id,
                    self.dataset_manifest_id))
                or type(self.byte_size) is not int or self.byte_size < 0
                or self.media_type not in {"application/json", "application/gzip"}
                or self.required_for_checkpoint18 is not True):
            return False
        try:
            start = date.fromisoformat(self.coverage_start) if self.coverage_start else None
            end = date.fromisoformat(self.coverage_end) if self.coverage_end else None
        except ValueError:
            return False
        return start is None or end is None or start <= end


@dataclass(frozen=True, slots=True)
class Phase2BPrivateCorpusManifestV1:
    entries: tuple[PrivateCorpusEntryV1, ...]
    object_count: int
    total_bytes: int
    inventory_hash: str
    manifest_id: str

    @classmethod
    def create(cls, entries: tuple[PrivateCorpusEntryV1, ...]
               ) -> "Phase2BPrivateCorpusManifestV1":
        if not entries or not all(item.verify() for item in entries):
            raise ValueError("private corpus entries are invalid")
        roles = tuple(item.logical_role for item in entries)
        if roles != tuple(sorted(set(roles))):
            raise ValueError("private corpus roles duplicate or unordered")
        inventory = content_hash({"schema_version": "Phase2BPrivateCorpusInventoryV1",
                                  "entries": entries})
        body = {"entries": entries,
                "object_count": len({item.sha256 for item in entries}),
                "total_bytes": sum(item.byte_size for item in entries),
                "inventory_hash": inventory}
        return cls(**body, manifest_id=content_hash({
            "schema_version": cls.__name__, **body}))

    def verify(self) -> bool:
        try:
            return self == type(self).create(self.entries)
        except ValueError:
            return False


def write_manifest(root: Path, manifest: Phase2BPrivateCorpusManifestV1) -> Path:
    if not manifest.verify():
        raise ValueError("verified private corpus manifest required")
    path = root / "governance" / "phase2b" / f"private-corpus-manifest-{manifest.manifest_id}.json"
    payload = canonical_json(manifest)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable private corpus manifest collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_manifest_exact(path: Path, expected_id: str) -> Phase2BPrivateCorpusManifestV1:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"private-corpus-manifest-{expected_id}.json"):
        raise ValueError("private corpus manifest ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        entries = tuple(PrivateCorpusEntryV1(**item) for item in values["entries"])
        manifest = Phase2BPrivateCorpusManifestV1(
            entries=entries, object_count=values["object_count"],
            total_bytes=values["total_bytes"],
            inventory_hash=values["inventory_hash"],
            manifest_id=values["manifest_id"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise ValueError("private corpus manifest unavailable or malformed") from error
    if (manifest.manifest_id != expected_id or not manifest.verify()
            or canonical_json(manifest) != raw):
        raise ValueError("private corpus manifest identity mismatch")
    return manifest


def build_manifest_exact(source_root: Path) -> Phase2BPrivateCorpusManifestV1:
    """Inventory only untracked byte roles required by current approved pins."""
    from v5_2.labels.historical_ca_lineage import HistoricalCorporateActionLineageV1
    from v5_2.labels.historical_calendar_lineage import HistoricalCalendarLineageV1
    from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1

    producer = HistoricalFiveDomainProducerV1.load_exact(source_root)
    status = producer.status_resolver.authority
    status_base = Path("data/replay_status_authority")
    status_roles = [
        status_base / "authority" / f"historical-status-authority-{status.authority_id}.json",
        status_base / "governance" / f"historical-status-derivation-approval-{producer.status_pins.approval_id}.json",
        status_base / "governance" / f"historical-status-derivation-manifest-{producer.status_pins.manifest_id}.json",
        status_base / "governance" / f"historical-status-composition-{producer.status_pins.composition_id}.json",
        status_base / "governance" / f"historical-status-replay-{producer.status_pins.replay_evidence_id}.json",
    ]
    status_roles.extend(status_base / "authority" / "shards" /
        descriptor.component_kind.lower() / f"{descriptor.storage_hash}.json.gz"
        for descriptor in status.shard_descriptors)
    ca_roles = tuple(Path("data/phase_1b2c") / item
                     for item in HistoricalCorporateActionLineageV1.required_paths())
    calendar_required = HistoricalCalendarLineageV1.required_paths()
    calendar_roles = (calendar_required[1], calendar_required[3])
    identities = (
        ("daily_security_status", status_roles, status.authority_id,
         producer.status_pins.approval_id, producer.status_pins.manifest_id,
         status.coverage_start.isoformat(), status.coverage_end.isoformat()),
        ("corporate_action", ca_roles, producer.actions.bundle_id,
         producer.actions.approval_id, producer.actions.manifest_id, None, None),
        ("trade_calendar", calendar_roles, producer.calendar.bundle_id,
         producer.calendar.approval_id, producer.calendar.manifest_id,
         min((*producer.calendar.sse_sessions, *producer.calendar.szse_sessions)).isoformat(),
         max((*producer.calendar.sse_sessions, *producer.calendar.szse_sessions)).isoformat()),
    )
    entries = []
    for domain, roles, authority, approval, manifest, start, end in identities:
        for role in roles:
            logical_role = role.as_posix()
            path = source_root / role
            if not path.is_file() or path.is_symlink():
                raise ValueError("PRIVATE_CORPUS_UNAVAILABLE: exact source role missing")
            raw = path.read_bytes()
            entries.append(PrivateCorpusEntryV1(
                logical_role=logical_role, domain=domain,
                sha256=sha256_digest(raw).hexdigest(), byte_size=len(raw),
                media_type=("application/gzip" if path.suffix == ".gz"
                            else "application/json"),
                authority_id=authority, approval_id=approval,
                dataset_manifest_id=manifest, coverage_start=start,
                coverage_end=end, required_for_checkpoint18=True))
    return Phase2BPrivateCorpusManifestV1.create(tuple(sorted(
        entries, key=lambda item: item.logical_role)))
