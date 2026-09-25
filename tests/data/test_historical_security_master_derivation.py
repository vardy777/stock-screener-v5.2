"""Approved Master membership is preserved independently of research usability."""

from __future__ import annotations

from datetime import date

import pytest

from v5_2.data.historical_security_master_authority import (
    HistoricalMasterTypingError,
    derive_master_intervals,
)
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.data.identity import content_hash


def row(identity: str, *, list_date: str, delist_date: str = "", market: str = "主板", name: str = "fixture"):
    native, suffix = identity.split(".")
    return {"ts_code": identity, "symbol": native,
            "exchange": "SZSE" if suffix == "SZ" else "SSE",
            "market": market, "list_status": "D" if delist_date else "L",
            "list_date": list_date, "delist_date": delist_date, "name": name}


def page(*rows):
    return RawPayloadArtifactV1.create(
        request_id="fixture-request", page_identity={"offset": 0},
        provider_payload={"rows": rows},
        semantic_metadata={"response_code": 0, "response_status": "ok"},
    )


def graph():
    body = {"schema_version": "EffectiveDatedSecurityIdentityV1", "provider_identity": "302132.SZ", "intervals": [
                {"identity": "300114.SZ", "effective_from": "2010-08-27", "effective_to": "2025-02-16", "security_type": "A_SHARE", "board": "CHINEXT"},
                {"identity": "302132.SZ", "effective_from": "2025-02-17", "effective_to": None, "security_type": "A_SHARE", "board": "CHINEXT"},
            ], "transition_event": "SECURITY_CODE_CHANGE", "transition_effective_at": "2025-02-17",
            "evidence_ids": ["szse-code-change-2025-302132", "szse-listing-2010-300114"],
            "policy_version": "effective-identity-v1"}
    digest = content_hash(body)
    assert digest == "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0"
    return {**{key: value for key, value in body.items() if key != "schema_version"},
            "graph_id": digest, "content_hash": digest}


def test_ordinary_and_ratified_transition_intervals_preserve_membership():
    source = page(row("000001.SZ", list_date="19910403"),
                  row("302132.SZ", list_date="20100827", market="创业板"),
                  row("T600018.SH", list_date="20000719", delist_date="20061020", market=""))
    derived = derive_master_intervals(
        membership=("000001.SZ", "302132.SZ", "T600018.SH"),
        pages=(source,), expected_payload_hashes=(source.payload_hash,),
        graph=graph(), graph_approval_id="a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f",
    )
    assert derived.membership_count == 3
    assert derived.resolved_count == 2
    assert derived.quarantine_count == 1
    assert derived.quarantines[0].security_identity == "T600018.SH"
    assert derived.quarantines[0].reason == "UNRESOLVED_MASTER_IDENTITY"
    assert derived.facts[0].provider_identity == "000001.SZ"
    assert derived.facts[0].intervals[0].effective_from == date(1991, 4, 3)
    assert tuple(item.identity for item in derived.facts[1].intervals) == ("300114.SZ", "302132.SZ")
    assert derived.facts[1].graph_id == graph()["graph_id"]


def test_duplicate_provider_name_revision_does_not_create_second_lifecycle():
    first = page(row("000001.SZ", list_date="19910403", name="old name"))
    second = RawPayloadArtifactV1.create(
        request_id="another-request", page_identity={"offset": 0},
        provider_payload={"rows": [row("000001.SZ", list_date="19910403", name="new name")]},
        semantic_metadata={"response_code": 0, "response_status": "ok"},
    )
    derived = derive_master_intervals(
        membership=("000001.SZ",), pages=(first, second),
        expected_payload_hashes=tuple(sorted((first.payload_hash, second.payload_hash))),
        graph=graph(), graph_approval_id="a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f",
    )
    assert derived.resolved_count == 1
    assert derived.facts[0].source_payload_hashes == tuple(sorted((first.payload_hash, second.payload_hash)))


def test_single_identity_date_conflict_is_scoped_but_raw_inventory_mismatch_is_global():
    a = page(row("000001.SZ", list_date="19910403"), row("000002.SZ", list_date="19910129"))
    b = RawPayloadArtifactV1.create(
        request_id="another-request", page_identity={"offset": 0},
        provider_payload={"rows": [row("000001.SZ", list_date="19910404")]},
        semantic_metadata={"response_code": 0, "response_status": "ok"},
    )
    expected = tuple(sorted((a.payload_hash, b.payload_hash)))
    derived = derive_master_intervals(
        membership=("000001.SZ", "000002.SZ"), pages=(a, b),
        expected_payload_hashes=expected, graph=graph(),
        graph_approval_id="a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f",
    )
    assert derived.resolved_count == 1
    assert derived.quarantines[0].security_identity == "000001.SZ"
    assert derived.quarantines[0].reason == "CONFLICTING_MASTER_LIFECYCLE"
    with pytest.raises(HistoricalMasterTypingError, match="payload inventory"):
        derive_master_intervals(
            membership=("000001.SZ", "000002.SZ"), pages=(a, b),
            expected_payload_hashes=(a.payload_hash,), graph=graph(),
            graph_approval_id="a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f",
        )
