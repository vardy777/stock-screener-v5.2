from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from types import MappingProxyType
from typing import Any

from v5_2.data.identity import canonical_json, content_hash


def _nonempty(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ProviderRequestV1:
    source_name: str
    dataset_kind: str
    endpoint: str
    parameters: Mapping[str, Any]
    requested_fields: tuple[str, ...]
    page_size: int
    request_policy_version: str
    request_id: str

    @classmethod
    def create(
        cls,
        source_name: str,
        dataset_kind: str,
        endpoint: str,
        parameters: Mapping[str, Any],
        requested_fields: Sequence[str],
        page_size: int,
        request_policy_version: str,
    ) -> ProviderRequestV1:
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
            raise ValueError("page_size must be a positive integer")
        if not isinstance(parameters, Mapping):
            raise ValueError("parameters must be a mapping")
        fields = tuple(sorted({_nonempty("requested field", item) for item in requested_fields}))
        if not fields:
            raise ValueError("requested_fields must not be empty")
        canonical_parameters = canonical_json(parameters)
        normalized_parameters = json.loads(canonical_parameters.decode("utf-8"))
        identity_payload = {
            "source_name": _nonempty("source_name", source_name),
            "dataset_kind": _nonempty("dataset_kind", dataset_kind),
            "endpoint": _nonempty("endpoint", endpoint),
            "parameters": normalized_parameters,
            "requested_fields": fields,
            "page_size": page_size,
            "request_policy_version": _nonempty(
                "request_policy_version", request_policy_version
            ),
        }
        return cls(
            source_name=identity_payload["source_name"],
            dataset_kind=identity_payload["dataset_kind"],
            endpoint=identity_payload["endpoint"],
            parameters=MappingProxyType(normalized_parameters),
            requested_fields=fields,
            page_size=page_size,
            request_policy_version=identity_payload["request_policy_version"],
            request_id=content_hash(identity_payload),
        )
