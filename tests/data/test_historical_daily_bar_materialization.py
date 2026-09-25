from datetime import date, datetime
from decimal import Decimal

from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.identity import canonical_json, content_hash

import pytest

from v5_2.data.historical_daily_bar_materialization import (
    HistoricalDailyBarMaterializationError,
    materialize_verified_source,
    normalize_verified_payload,
)
from v5_2.data.raw_artifacts import RawArtifactStore, RawPayloadArtifactV1


def _payload(rows):
    return RawPayloadArtifactV1.create(
        request_id="r" * 64, page_identity={"offset": 0},
        provider_payload={"rows": rows},
        semantic_metadata={"response_code": 0},
    )


def test_verified_payload_uses_frozen_units_and_next_session():
    artifact = _payload([{"ts_code": "000001.SZ", "trade_date": "20250102",
                          "open": 10, "high": 11, "low": 9, "close": 10.5,
                          "vol": 2.5, "amount": 3.75}])
    facts, excluded = normalize_verified_payload(
        artifact, expected_hash=artifact.payload_hash,
        target_identities={"000001.SZ": ("19910403", "99999999")},
        next_safe_by_session={"20250102": "2025-01-03T16:30:00+08:00"},
        normalization_policy_id="53fd452337be9368e37fb01aeb8a38082db0a470a5ab94ea0cad06b8653c2cc4",
        unit_policy_id="e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093",
    )
    assert excluded == 0
    assert len(facts) == 1
    assert facts[0].volume_shares == 250
    assert facts[0].amount_yuan == 3750
    assert facts[0].available_at.date() == date(2025, 1, 3)


def test_wrong_raw_hash_or_missing_next_session_fails_closed():
    artifact = _payload([{"ts_code": "000001.SZ", "trade_date": "20250102",
                          "open": 10, "high": 11, "low": 9, "close": 10.5,
                          "vol": 2.5, "amount": 3.75}])
    common = dict(target_identities={"000001.SZ": ("19910403", "99999999")},
                  normalization_policy_id="53fd452337be9368e37fb01aeb8a38082db0a470a5ab94ea0cad06b8653c2cc4",
                  unit_policy_id="e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093")
    with pytest.raises(HistoricalDailyBarMaterializationError):
        normalize_verified_payload(artifact, expected_hash="x" * 64,
                                   next_safe_by_session={"20250102": "2025-01-03T16:30:00+08:00"}, **common)
    with pytest.raises(HistoricalDailyBarMaterializationError):
        normalize_verified_payload(artifact, expected_hash=artifact.payload_hash,
                                   next_safe_by_session={}, **common)
    with pytest.raises(HistoricalDailyBarMaterializationError):
        normalize_verified_payload(artifact, expected_hash=artifact.payload_hash,
                                   next_safe_by_session={"20250102": "2025-01-03T16:30:00+08:00"},
                                   **{**common, "unit_policy_id": "wrong"})
    with pytest.raises(HistoricalDailyBarMaterializationError):
        normalize_verified_payload(artifact, expected_hash=artifact.payload_hash,
                                   next_safe_by_session={"20250102": "2025-01-03T16:30:00+08:00"},
                                   **{**common, "normalization_policy_id": "wrong"})
    with pytest.raises(HistoricalDailyBarMaterializationError):
        normalize_verified_payload(artifact, expected_hash=artifact.payload_hash,
                                   next_safe_by_session={"20250102": "2025-01-02T15:00:00+08:00"},
                                   **common)


def test_frozen_special_identity_rule_is_reused():
    artifact = _payload([{"ts_code": "302132.SZ", "trade_date": "20240102",
                          "open": 10, "high": 11, "low": 9, "close": 10.5,
                          "vol": 2.5, "amount": 3.75}])
    facts, excluded = normalize_verified_payload(
        artifact, expected_hash=artifact.payload_hash,
        target_identities={"302132.SZ": ("20100101", "99999999")},
        next_safe_by_session={"20240102": "2024-01-03T16:30:00+08:00"},
        normalization_policy_id="53fd452337be9368e37fb01aeb8a38082db0a470a5ab94ea0cad06b8653c2cc4",
        unit_policy_id="e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093",
    )
    assert excluded == 0
    assert facts[0].security_identity == "300114.SZ"


def test_materializer_requires_exact_source_set_and_emits_month_shard(tmp_path):
    artifact = _payload([{"ts_code": "000001.SZ", "trade_date": "20250102",
                          "open": 10, "high": 11, "low": 9, "close": 10.5,
                          "vol": 2.5, "amount": 3.75}])
    source = tmp_path / "source"
    RawArtifactStore(source).put_payload("provider", "daily_bar", artifact)
    args = dict(
        raw_roots=(source / "raw" / "provider" / "daily_bar",),
        expected_hashes=(artifact.payload_hash,), output_root=tmp_path / "portable",
        target_identities={"000001.SZ": ("19910403", "99999999")},
        next_safe_by_session={"20250102": "2025-01-03T16:30:00+08:00"},
        normalization_policy_id="53fd452337be9368e37fb01aeb8a38082db0a470a5ab94ea0cad06b8653c2cc4",
        unit_policy_id="e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093",
    )
    result = materialize_verified_source(**args)
    assert result.row_count == 1
    assert result.symbol_count == 1
    assert result.excluded_non_target_count == 0
    assert len(result.shards) == 1
    with pytest.raises(HistoricalDailyBarMaterializationError):
        materialize_verified_source(**{**args, "expected_hashes": ("x" * 64,)})
    extra = _payload([])
    RawArtifactStore(source).put_payload("provider", "daily_bar", extra)
    with pytest.raises(HistoricalDailyBarMaterializationError):
        materialize_verified_source(**args)


def test_corrected_overlap_must_match_exact_fact_identity(tmp_path):
    row = {"ts_code": "000001.SZ", "trade_date": "20250102", "open": 10,
           "high": 11, "low": 9, "close": 10.5, "vol": 2.5, "amount": 3.75}
    artifact = _payload([row])
    source = tmp_path / "source"
    RawArtifactStore(source).put_payload("provider", "daily_bar", artifact)
    corrected = tmp_path / "corrected" / artifact.request_id[:16]
    corrected.mkdir(parents=True)
    valid = DailyBarFactV1.create(
        source_symbol="000001.SZ", session=date(2025, 1, 2),
        open=Decimal("10"), high=Decimal("11"), low=Decimal("9"),
        close=Decimal("10.5"), raw_volume=Decimal("2.5"), raw_amount=Decimal("3.75"),
        source_payload_hash=artifact.payload_hash,
        available_at=datetime.fromisoformat("2025-01-03T16:30:00+08:00"),
        availability_policy_version="daily-bar-availability-v1",
    )
    body = {"schema_version": "DailyBarFactAvailabilitySupersessionShardV1",
            "approval_id": "approved", "availability_evidence_id": "evidence",
            "supersedes_shard_hash": "old", "facts": [valid.as_dict()]}
    shard_hash = content_hash(body)
    (corrected / f"{shard_hash}.json").write_bytes(canonical_json({**body, "content_hash": shard_hash}))
    args = dict(raw_roots=(source / "raw" / "provider" / "daily_bar",),
                expected_hashes=(artifact.payload_hash,), output_root=tmp_path / "portable",
                target_identities={"000001.SZ": ("19910403", "99999999")},
                next_safe_by_session={"20250102": "2025-01-03T16:30:00+08:00"},
                normalization_policy_id="53fd452337be9368e37fb01aeb8a38082db0a470a5ab94ea0cad06b8653c2cc4",
                unit_policy_id="e7a744be0f572b6bfe7ad909829f366e0bc75c16a795edb46e561d70effaf093",
                corrected_root=tmp_path / "corrected",
                corrected_shard_hashes=(shard_hash,), corrected_approval_id="approved")
    assert materialize_verified_source(**args).overlap_row_count == 1
    bad = DailyBarFactV1.create(
        source_symbol="000001.SZ", session=date(2025, 1, 2),
        open=Decimal("10"), high=Decimal("11"), low=Decimal("9"),
        close=Decimal("99"), raw_volume=Decimal("2.5"), raw_amount=Decimal("3.75"),
        source_payload_hash=artifact.payload_hash,
        available_at=datetime.fromisoformat("2025-01-03T16:30:00+08:00"),
        availability_policy_version="daily-bar-availability-v1",
    )
    (corrected / f"{shard_hash}.json").unlink()
    changed = {**body, "facts": [bad.as_dict()]}
    changed_hash = content_hash(changed)
    (corrected / f"{changed_hash}.json").write_bytes(canonical_json({**changed, "content_hash": changed_hash}))
    with pytest.raises(HistoricalDailyBarMaterializationError):
        materialize_verified_source(**{**args, "corrected_shard_hashes": (changed_hash,)})
