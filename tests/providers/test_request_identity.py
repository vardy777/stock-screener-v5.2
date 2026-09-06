from __future__ import annotations

import dataclasses

import pytest

from v5_2.data.identity import CanonicalIdentityError, canonical_json
from v5_2.providers.contracts import ProviderRequestV1


def make_request(**changes: object) -> ProviderRequestV1:
    values: dict[str, object] = {
        "source_name": "tushare_pro",
        "dataset_kind": "daily_bar",
        "endpoint": "daily",
        "parameters": {"end_date": "20200131", "start_date": "20200101"},
        "requested_fields": ("close", "trade_date", "ts_code"),
        "page_size": 5000,
        "request_policy_version": "request-v1",
    }
    values.update(changes)
    return ProviderRequestV1.create(**values)


def test_canonical_json_has_stable_mapping_and_sequence_encoding() -> None:
    assert canonical_json({"b": [2, 1], "a": "中"}) == (
        b'{"a":"\xe4\xb8\xad","b":[2,1]}'
    )


def test_same_logical_request_has_same_identity_despite_input_order() -> None:
    first = make_request()
    second = make_request(
        parameters={"start_date": "20200101", "end_date": "20200131"},
        requested_fields=("ts_code", "close", "trade_date", "close"),
    )

    assert first.request_id == second.request_id
    assert second.requested_fields == ("close", "trade_date", "ts_code")
    assert len(first.request_id) == 64


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_name", "other"),
        ("dataset_kind", "trade_calendar"),
        ("endpoint", "weekly"),
        ("parameters", {"start_date": "20200102", "end_date": "20200131"}),
        ("requested_fields", ("close", "trade_date")),
        ("page_size", 1000),
        ("request_policy_version", "request-v2"),
    ],
)
def test_each_logical_request_field_changes_identity(field: str, replacement: object) -> None:
    assert make_request(**{field: replacement}).request_id != make_request().request_id


def test_request_contract_has_no_wall_clock_or_credential_field() -> None:
    names = {field.name for field in dataclasses.fields(ProviderRequestV1)}
    assert names == {
        "source_name",
        "dataset_kind",
        "endpoint",
        "parameters",
        "requested_fields",
        "page_size",
        "request_policy_version",
        "request_id",
    }


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), {1, 2}])
def test_unsupported_or_non_finite_identity_input_fails_closed(bad_value: object) -> None:
    with pytest.raises(CanonicalIdentityError):
        make_request(parameters={"value": bad_value})


@pytest.mark.parametrize("page_size", [0, -1, True])
def test_invalid_page_size_fails_closed(page_size: object) -> None:
    with pytest.raises(ValueError):
        make_request(page_size=page_size)
