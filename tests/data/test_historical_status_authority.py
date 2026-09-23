from dataclasses import replace
from datetime import date
import gzip
import hashlib

import pytest

from v5_2.data.historical_status_authority import (
    HistoricalStatusAuthorityError,
    HistoricalStatusAuthorityV1,
    HistoricalStatusComponentV1,
    HistoricalStatusShardStore,
)


PANEL = "a" * 64
MANIFEST = "b" * 64
APPROVAL = "c" * 64
PIT = "d" * 64
SOURCE_VERSION = "e" * 64


def _component(*, source_row_hash="1" * 64, component_kind="LIFECYCLE"):
    return HistoricalStatusComponentV1.create(
        component_kind=component_kind,
        canonical_security_identity="000001.SZ",
        effective_from=date(2010, 1, 4),
        effective_to=None,
        event_session=None,
        source_row_hash=source_row_hash,
        availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
        availability_input_date=date(2010, 1, 4),
        source_fields={"list_date": "20100104"},
    )


def test_deterministic_shard_bytes_are_canonical_gzip(tmp_path):
    component = _component()
    first = HistoricalStatusShardStore(tmp_path / "one").encode(
        "LIFECYCLE", (component,)
    )
    second = HistoricalStatusShardStore(tmp_path / "two").encode(
        "LIFECYCLE", (component,)
    )

    assert first.compressed_bytes == second.compressed_bytes
    assert first.storage_hash == hashlib.sha256(first.compressed_bytes).hexdigest()
    assert first.content_hash == "f042d9008c143868a4eb67365d43cd8898e115ed37eb9c3e74c576315443dc96"
    assert gzip.decompress(first.compressed_bytes).startswith(b'{"component_kind":"LIFECYCLE"')


def test_shard_store_is_create_or_identical_and_detects_wrong_bytes(tmp_path):
    store = HistoricalStatusShardStore(tmp_path)
    encoded = store.encode("LIFECYCLE", (_component(),))
    path = store.put(encoded)

    assert store.put(encoded) == path
    path.write_bytes(b"tampered")
    with pytest.raises(HistoricalStatusAuthorityError, match="collision"):
        store.put(encoded)
    with pytest.raises(HistoricalStatusAuthorityError, match="storage hash"):
        store.read(path, expected=encoded.descriptor)


def test_shard_rejects_wrong_kind_and_duplicate_source_row_identity(tmp_path):
    store = HistoricalStatusShardStore(tmp_path)
    lifecycle = _component()
    risk = _component(component_kind="RISK_WARNING")

    with pytest.raises(HistoricalStatusAuthorityError, match="component kind"):
        store.encode("LIFECYCLE", (risk,))
    with pytest.raises(HistoricalStatusAuthorityError, match="duplicate source row"):
        store.encode("LIFECYCLE", (lifecycle, lifecycle))


def test_authority_verification_pins_every_parent_inventory_and_shard(tmp_path):
    encoded = HistoricalStatusShardStore(tmp_path).encode(
        "LIFECYCLE", (_component(),)
    )
    authority = HistoricalStatusAuthorityV1.create(
        coverage_start=date(2010, 1, 4),
        coverage_end=date(2026, 9, 10),
        parent_panel_id=PANEL,
        parent_manifest_id=MANIFEST,
        parent_approval_id=APPROVAL,
        pit_evidence_id=PIT,
        source_version_identity=SOURCE_VERSION,
        raw_payload_hashes=("2" * 64,),
        receipt_hashes=("3" * 64,),
        request_inventory_id="4" * 64,
        shard_descriptors=(encoded.descriptor,),
        authority_policy_version="historical-status-authority-v1",
    )

    assert authority.verify()
    assert authority.parent_panel_id == PANEL
    assert authority.shard_descriptors == (encoded.descriptor,)

    tampered = replace(authority, parent_panel_id="f" * 64)
    assert not tampered.verify()
