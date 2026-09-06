from __future__ import annotations

import pytest

from v5_2.data.normalization import NormalizationError, NormalizerRegistry
from v5_2.data.raw_artifacts import RawPayloadArtifactV1


def raw(rows: list[dict[str, object]]) -> RawPayloadArtifactV1:
    return RawPayloadArtifactV1.create(
        request_id="a" * 64,
        page_identity={"offset": 0},
        provider_payload={"rows": rows},
        semantic_metadata={"fixture": "synthetic"},
    )


def registry() -> NormalizerRegistry:
    result = NormalizerRegistry()
    result.register(
        dataset_kind="synthetic_kind",
        normalizer=lambda artifact: artifact.provider_payload["rows"],
        output_fields=("security_id", "trade_date", "close"),
        key_fields=("security_id", "trade_date"),
        normalizer_version="synthetic-v1",
    )
    return result


def test_normalized_output_is_independent_of_provider_row_order() -> None:
    first = {"security_id": "B", "trade_date": "20200102", "close": 2.0}
    second = {"security_id": "A", "trade_date": "20200102", "close": 1.0}
    assert registry().normalize("synthetic_kind", raw([first, second])) == registry().normalize(
        "synthetic_kind", raw([second, first])
    )


def test_duplicate_canonical_key_fails_closed() -> None:
    row = {"security_id": "A", "trade_date": "20200102", "close": 1.0}
    with pytest.raises(NormalizationError, match="duplicate"):
        registry().normalize("synthetic_kind", raw([row, row]))


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({"security_id": "A", "trade_date": "20200102"}, "missing"),
        (
            {"security_id": "A", "trade_date": "20200102", "close": 1.0, "future": 9},
            "unregistered",
        ),
    ],
)
def test_invalid_normalizer_output_fails_closed(row: dict[str, object], message: str) -> None:
    with pytest.raises(NormalizationError, match=message):
        registry().normalize("synthetic_kind", raw([row]))


def test_unregistered_dataset_kind_fails_closed() -> None:
    with pytest.raises(NormalizationError, match="not registered"):
        registry().normalize("real_kind", raw([]))


def test_noncanonical_normalizer_output_fails_closed() -> None:
    registered = NormalizerRegistry()
    registered.register(
        dataset_kind="synthetic_kind",
        normalizer=lambda artifact: (
            {"security_id": "A", "trade_date": "20200102", "close": float("nan")},
        ),
        output_fields=("security_id", "trade_date", "close"),
        key_fields=("security_id", "trade_date"),
        normalizer_version="synthetic-v1",
    )
    with pytest.raises(NormalizationError, match="canonical"):
        registered.normalize("synthetic_kind", raw([]))


def test_registry_rejects_duplicate_dataset_registration() -> None:
    registered = registry()
    with pytest.raises(NormalizationError, match="already registered"):
        registered.register(
            dataset_kind="synthetic_kind",
            normalizer=lambda artifact: (),
            output_fields=("id",),
            key_fields=("id",),
            normalizer_version="synthetic-v2",
        )
