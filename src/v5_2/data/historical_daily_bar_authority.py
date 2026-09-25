"""Portable, immutable membership for the approved historical Daily Bar panel."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import gzip
import hashlib
import io
import json
import os
from pathlib import Path

from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.identity import canonical_json, content_hash


class HistoricalDailyBarAuthorityError(RuntimeError):
    """Historical Daily Bar membership or lineage is not verifiable."""


def _safe_availability(fact: DailyBarFactV1) -> bool:
    return (
        fact.availability_policy_version == "daily-bar-availability-v1"
        and fact.available_at.tzinfo is not None
        and fact.available_at.utcoffset() == timedelta(hours=8)
        and fact.available_at.date() > fact.session
        and fact.available_at.hour == 16 and fact.available_at.minute == 30
        and fact.available_at.second == 0
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fact_from_dict(value: dict[str, object]) -> DailyBarFactV1:
    fact = DailyBarFactV1(
        fact_id=str(value["fact_id"]), security_identity=str(value["security_identity"]),
        session=date.fromisoformat(str(value["session"])),
        open=Decimal(str(value["open"])), high=Decimal(str(value["high"])),
        low=Decimal(str(value["low"])), close=Decimal(str(value["close"])),
        volume_shares=Decimal(str(value["volume_shares"])),
        amount_yuan=Decimal(str(value["amount_yuan"])),
        price_basis=str(value["price_basis"]),
        available_at=datetime.fromisoformat(str(value["available_at"])),
        availability_policy_version=str(value["availability_policy_version"]),
        source_payload_hash=str(value["source_payload_hash"]),
        content_hash=str(value["content_hash"]),
    )
    if not fact.verify():
        raise HistoricalDailyBarAuthorityError("daily-bar fact integrity failed")
    return fact


@dataclass(frozen=True, slots=True)
class HistoricalDailyBarShardDescriptorV1:
    month: str
    path: str
    row_count: int
    first_session: str
    last_session: str
    content_hash: str
    storage_hash: str
    membership_hash: str


@dataclass(frozen=True, slots=True)
class HistoricalDailyBarFactShardV1:
    descriptor: HistoricalDailyBarShardDescriptorV1
    storage_bytes: bytes

    @classmethod
    def create(cls, month: str, facts: tuple[DailyBarFactV1, ...]):
        if not facts or len(month) != 7 or month[4] != "-":
            raise HistoricalDailyBarAuthorityError("nonempty canonical month is required")
        ordered = tuple(sorted(facts, key=lambda row: (row.session, row.security_identity)))
        keys = [(row.security_identity, row.session) for row in ordered]
        ids = [row.fact_id for row in ordered]
        if (any(not row.verify() or not _safe_availability(row)
                or row.session.strftime("%Y-%m") != month for row in ordered)
                or len(keys) != len(set(keys)) or len(ids) != len(set(ids))):
            raise HistoricalDailyBarAuthorityError("invalid or duplicate daily-bar membership")
        payload = b"".join(canonical_json(row.as_dict()) + b"\n" for row in ordered)
        stream = io.BytesIO()
        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0, compresslevel=6) as archive:
            archive.write(payload)
        storage = stream.getvalue()
        storage_hash = _sha256(storage)
        descriptor = HistoricalDailyBarShardDescriptorV1(
            month=month, path=f"shards/{month}/{storage_hash}.jsonl.gz",
            row_count=len(ordered), first_session=ordered[0].session.isoformat(),
            last_session=ordered[-1].session.isoformat(), content_hash=_sha256(payload),
            storage_hash=storage_hash, membership_hash=content_hash(tuple(ids)),
        )
        return cls(descriptor, storage)

    def write_exact(self, root: Path) -> Path:
        path = root / self.descriptor.path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            if path.read_bytes() != self.storage_bytes:
                raise HistoricalDailyBarAuthorityError("immutable shard collision")
            return path
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(self.storage_bytes)
        return path


@dataclass(frozen=True, slots=True)
class HistoricalDailyBarFactAuthorityV1:
    parent_panel_id: str
    parent_approval_id: str
    parent_manifest_id: str
    source_binding_id: str
    source_content_set_id: str
    availability_evidence_id: str
    calendar_lineage_id: str
    normalization_policy_id: str
    unit_policy_id: str
    identity_policy_id: str
    raw_payload_hashes: tuple[str, ...]
    shards: tuple[HistoricalDailyBarShardDescriptorV1, ...]
    coverage_start: str
    coverage_end: str
    row_count: int
    symbol_count: int
    membership_set_hash: str
    authority_id: str
    content_hash: str

    @property
    def manifest_id(self) -> str:
        return self.parent_manifest_id

    @property
    def approval_id(self) -> str:
        return self.parent_approval_id

    @classmethod
    def create(cls, **values):
        shards = tuple(values["shards"])
        hashes = tuple(values["raw_payload_hashes"])
        if (not shards or len(shards) != len({item.month for item in shards})
                or tuple(sorted(shards, key=lambda item: item.month)) != shards
                or len(hashes) != len(set(hashes)) or tuple(sorted(hashes)) != hashes
                or int(values["symbol_count"]) < 1):
            raise HistoricalDailyBarAuthorityError("noncanonical shard or raw inventory")
        membership_set_hash = content_hash(tuple(
            (item.month, item.row_count, item.membership_hash) for item in shards
        ))
        body = {"schema_version": "HistoricalDailyBarFactAuthorityV1", **values,
                "row_count": sum(item.row_count for item in shards),
                "membership_set_hash": membership_set_hash}
        digest = content_hash(body)
        body.pop("schema_version")
        return cls(**body, authority_id=digest, content_hash=digest)

    def verify(self) -> bool:
        try:
            rebuilt = type(self).create(**{key: getattr(self, key) for key in (
                "parent_panel_id", "parent_approval_id", "parent_manifest_id",
                "source_binding_id", "source_content_set_id", "availability_evidence_id",
                "calendar_lineage_id", "normalization_policy_id", "unit_policy_id",
                "identity_policy_id", "raw_payload_hashes", "shards",
                "coverage_start", "coverage_end", "symbol_count",
            )})
            return self == rebuilt
        except (ValueError, TypeError, HistoricalDailyBarAuthorityError):
            return False

    def write_exact(self, root: Path) -> Path:
        if not self.verify():
            raise HistoricalDailyBarAuthorityError("authority integrity failed")
        path = root / "governance" / f"historical-daily-bar-fact-authority-{self.authority_id}.json"
        content = canonical_json(asdict(self))
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            if path.read_bytes() != content:
                raise HistoricalDailyBarAuthorityError("immutable authority collision")
            return path
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        return path

    @classmethod
    def load_exact(cls, root: Path, expected_authority_id: str):
        path = root / "governance" / f"historical-daily-bar-fact-authority-{expected_authority_id}.json"
        if not path.is_file():
            raise HistoricalDailyBarAuthorityError("exact authority is missing")
        try:
            stored = json.loads(path.read_bytes())
            stored["raw_payload_hashes"] = tuple(stored["raw_payload_hashes"])
            stored["shards"] = tuple(HistoricalDailyBarShardDescriptorV1(**item)
                                     for item in stored["shards"])
            authority = cls(**stored)
        except (ValueError, KeyError, TypeError) as error:
            raise HistoricalDailyBarAuthorityError("authority is malformed") from error
        if (authority.authority_id != expected_authority_id or not authority.verify()
                or path.read_bytes() != canonical_json(asdict(authority))):
            raise HistoricalDailyBarAuthorityError("authority content address mismatch")
        return authority


class HistoricalDailyBarFactReaderV1:
    def __init__(self, root: Path, authority: HistoricalDailyBarFactAuthorityV1,
                 *, expected_manifest_id: str, revoked_approval_ids: tuple[str, ...]):
        if (not authority.verify() or expected_manifest_id != authority.manifest_id
                or authority.approval_id in revoked_approval_ids):
            raise HistoricalDailyBarAuthorityError("historical Daily Bar authority is not approved")
        expected_paths = {item.path for item in authority.shards}
        actual_paths = {path.relative_to(root).as_posix()
                        for path in (root / "shards").rglob("*.jsonl.gz")}
        if actual_paths != expected_paths:
            raise HistoricalDailyBarAuthorityError("portable shard inventory mismatch")
        self.root = root
        self.authority = authority
        self.by_month = {item.month: item for item in authority.shards}
        self.derived_approval_id = ""
        self.derived_manifest_id = ""

    @classmethod
    def load_exact(cls, root: Path, *, authority_id: str, approval_id: str,
                   manifest_id: str, revoked_approval_ids: tuple[str, ...]):
        authority = HistoricalDailyBarFactAuthorityV1.load_exact(root, authority_id)
        approval_path = root / "governance" / f"historical-daily-bar-representation-approval-{approval_id}.json"
        manifest_path = root / "governance" / f"historical-daily-bar-representation-manifest-{manifest_id}.json"
        try:
            approval = json.loads(approval_path.read_bytes())
            manifest = json.loads(manifest_path.read_bytes())
        except (OSError, ValueError) as error:
            raise HistoricalDailyBarAuthorityError("derived approval or manifest is missing") from error
        for value, expected_id, id_field, schema in (
            (approval, approval_id, "approval_id", "HistoricalDailyBarRepresentationApprovalV1"),
            (manifest, manifest_id, "manifest_id", "HistoricalDailyBarRepresentationManifestV1"),
        ):
            body = {key: item for key, item in value.items()
                    if key not in {id_field, "content_hash"}}
            if (value.get("schema_version") != schema or value.get(id_field) != expected_id
                    or value.get("content_hash") != expected_id
                    or content_hash(body) != expected_id):
                raise HistoricalDailyBarAuthorityError("derived governance content address mismatch")
        ledger_id = str(approval.get("coverage_ledger_id", ""))
        ledger_path = root / "governance" / f"historical-daily-bar-coverage-ledger-{ledger_id}.json"
        try:
            ledger = json.loads(ledger_path.read_bytes())
        except (OSError, ValueError) as error:
            raise HistoricalDailyBarAuthorityError("coverage ledger is missing or malformed") from error
        ledger_body = {key: item for key, item in ledger.items()
                       if key not in {"ledger_id", "content_hash"}}
        if (ledger.get("schema_version") != "HistoricalDailyBarCoverageLedgerV1"
                or ledger.get("ledger_id") != ledger_id
                or ledger.get("content_hash") != ledger_id
                or content_hash(ledger_body) != ledger_id):
            raise HistoricalDailyBarAuthorityError("coverage ledger content address mismatch")
        if (approval_id in revoked_approval_ids
                or authority.parent_approval_id in revoked_approval_ids
                or approval.get("decision") != "APPROVED_WITH_RULES"
                or approval.get("scope") != "PORTABLE_ROW_LEVEL_REPRESENTATION_OF_APPROVED_HISTORICAL_DAILY_BAR_TRUTH"
                or approval.get("parent_approval_id") != authority.parent_approval_id
                or approval.get("parent_panel_id") != authority.parent_panel_id
                or approval.get("availability_evidence_id") != authority.availability_evidence_id
                or approval.get("authority_id") != authority.authority_id
                or approval.get("source_content_set_id") != authority.source_content_set_id
                or manifest.get("approval_id") != approval_id
                or manifest.get("coverage_ledger_id") != ledger_id
                or manifest.get("authority_id") != authority.authority_id
                or manifest.get("parent_manifest_id") != authority.parent_manifest_id
                or manifest.get("membership_set_hash") != authority.membership_set_hash
                or tuple(manifest.get("shard_storage_hashes", ()))
                    != tuple(item.storage_hash for item in authority.shards)
                or manifest.get("row_count") != authority.row_count
                or manifest.get("symbol_count") != authority.symbol_count
                or manifest.get("coverage_start") != authority.coverage_start
                or manifest.get("coverage_end") != authority.coverage_end
                or manifest.get("availability_policy_version") != "daily-bar-availability-v1:NEXT_SESSION_SAFE"
                or ledger.get("authority_id") != authority.authority_id
                or ledger.get("parent_panel_id") != authority.parent_panel_id
                or ledger.get("observed_rows") != authority.row_count
                or ledger.get("symbol_count") != authority.symbol_count):
            raise HistoricalDailyBarAuthorityError("derived governance chain mismatch or revoked")
        reader = cls(root, authority, expected_manifest_id=authority.parent_manifest_id,
                     revoked_approval_ids=revoked_approval_ids)
        reader.derived_approval_id = approval_id
        reader.derived_manifest_id = manifest_id
        return reader

    def read_month(self, month: str) -> tuple[DailyBarFactV1, ...]:
        descriptor = self.by_month.get(month)
        if descriptor is None:
            raise HistoricalDailyBarAuthorityError("month is outside approved membership")
        path = self.root / descriptor.path
        if not path.is_file():
            raise HistoricalDailyBarAuthorityError("approved shard is missing")
        storage = path.read_bytes()
        if _sha256(storage) != descriptor.storage_hash:
            raise HistoricalDailyBarAuthorityError("shard storage hash mismatch")
        try:
            payload = gzip.decompress(storage)
            facts = tuple(_fact_from_dict(json.loads(line)) for line in payload.splitlines())
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise HistoricalDailyBarAuthorityError("shard content is invalid") from error
        if (_sha256(payload) != descriptor.content_hash or len(facts) != descriptor.row_count
                or facts[0].session.isoformat() != descriptor.first_session
                or facts[-1].session.isoformat() != descriptor.last_session
                or any(row.session.strftime("%Y-%m") != month for row in facts)
                or any(not _safe_availability(row) for row in facts)
                or tuple(sorted(facts, key=lambda row: (row.session, row.security_identity))) != facts
                or len({(row.security_identity, row.session) for row in facts}) != len(facts)
                or len({row.fact_id for row in facts}) != len(facts)
                or content_hash(tuple(row.fact_id for row in facts)) != descriptor.membership_hash):
            raise HistoricalDailyBarAuthorityError("shard membership mismatch")
        return facts

    def lookup(self, security_identity: str, session: date) -> DailyBarFactV1:
        if not self.authority.coverage_start <= session.isoformat() <= self.authority.coverage_end:
            raise HistoricalDailyBarAuthorityError("session is out of coverage")
        for fact in self.read_month(session.strftime("%Y-%m")):
            if fact.security_identity == security_identity and fact.session == session:
                return fact
        raise HistoricalDailyBarAuthorityError("daily-bar fact is absent")

    def read_window(self, anchor_month: str, h5_end: date) -> tuple[DailyBarFactV1, ...]:
        months = tuple(sorted(self.by_month))
        end_month = h5_end.strftime("%Y-%m")
        if (anchor_month not in self.by_month or end_month not in self.by_month
                or months.index(end_month) < months.index(anchor_month)
                or months.index(end_month) - months.index(anchor_month) > 1
                or h5_end.isoformat() > self.authority.coverage_end):
            raise HistoricalDailyBarAuthorityError("H5 window is outside bounded approved coverage")
        return tuple(fact for month in months[months.index(anchor_month):months.index(end_month) + 1]
                     for fact in self.read_month(month))

    def load_month_index(self, month: str) -> dict[tuple[str, date], DailyBarFactV1]:
        facts = self.read_month(month)
        return {(fact.security_identity, fact.session): fact for fact in facts}

    def resolve(self, security_identity: str, session: date) -> dict[str, object]:
        if not self.derived_approval_id or not self.derived_manifest_id:
            raise HistoricalDailyBarAuthorityError("exact derived governance is required for research")
        fact = self.lookup(security_identity, session)
        return {"fact": fact, "fact_id": fact.fact_id, "content_hash": fact.content_hash,
                "available_at": fact.available_at, "source_payload_hash": fact.source_payload_hash,
                "authority_id": self.authority.authority_id,
                "approval_id": self.derived_approval_id,
                "manifest_id": self.derived_manifest_id}
