from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from v5_2.data.identity import CanonicalIdentityError, canonical_json
from v5_2.data.raw_artifacts import RawPayloadArtifactV1


class NormalizationError(RuntimeError):
    """Normalizer output is incomplete, ambiguous or non-deterministic."""


Normalizer = Callable[[RawPayloadArtifactV1], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True, slots=True)
class _Registration:
    normalizer: Normalizer
    output_fields: tuple[str, ...]
    key_fields: tuple[str, ...]
    normalizer_version: str


class NormalizerRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, _Registration] = {}

    def register(
        self,
        *,
        dataset_kind: str,
        normalizer: Normalizer,
        output_fields: tuple[str, ...],
        key_fields: tuple[str, ...],
        normalizer_version: str,
    ) -> None:
        if dataset_kind in self._registrations:
            raise NormalizationError("dataset kind is already registered")
        fields = tuple(sorted(set(output_fields)))
        keys = tuple(key_fields)
        if not fields or not keys or not set(keys) <= set(fields):
            raise NormalizationError("normalizer fields and keys are invalid")
        self._registrations[dataset_kind] = _Registration(
            normalizer, fields, keys, normalizer_version
        )

    def normalize(
        self, dataset_kind: str, artifact: RawPayloadArtifactV1
    ) -> tuple[Mapping[str, Any], ...]:
        registration = self._registrations.get(dataset_kind)
        if registration is None:
            raise NormalizationError("dataset kind is not registered")
        expected = set(registration.output_fields)
        normalized: list[dict[str, Any]] = []
        keys_seen: set[tuple[Any, ...]] = set()
        for supplied in registration.normalizer(artifact):
            actual = set(supplied)
            if expected - actual:
                raise NormalizationError("normalizer output has missing fields")
            if actual - expected:
                raise NormalizationError("normalizer output has unregistered fields")
            try:
                row = json.loads(canonical_json(supplied).decode("utf-8"))
                key = tuple(row[field] for field in registration.key_fields)
                canonical_json(key)
            except (CanonicalIdentityError, KeyError, TypeError) as error:
                raise NormalizationError("normalizer output is not canonical") from error
            if key in keys_seen:
                raise NormalizationError("duplicate normalized key")
            keys_seen.add(key)
            normalized.append(row)
        normalized.sort(
            key=lambda row: canonical_json(
                tuple(row[field] for field in registration.key_fields)
            )
        )
        return tuple(normalized)
