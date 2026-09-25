"""Synthetic contract fixtures; no test document is market evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from scripts.ratify_6275_identity_graph import _exact_bytes, _write_immutable
from v5_2.data.real_audits.identity_graph_ratification import (
    GraphRatificationError,
    OfficialGraphEvidenceV1,
    SecurityIdentityGraphApprovalV1,
    ratify_existing_graph,
)


GRAPH = {
    "graph_id": "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0",
    "content_hash": "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0",
    "provider_identity": "302132.SZ",
    "intervals": [
        {"identity": "300114.SZ", "effective_from": "2010-08-27", "effective_to": "2025-02-16", "security_type": "A_SHARE", "board": "CHINEXT"},
        {"identity": "302132.SZ", "effective_from": "2025-02-17", "effective_to": None, "security_type": "A_SHARE", "board": "CHINEXT"},
    ],
    "transition_event": "SECURITY_CODE_CHANGE",
    "transition_effective_at": "2025-02-17",
    "evidence_ids": ["szse-code-change-2025-302132", "szse-listing-2010-300114"],
    "policy_version": "effective-identity-v1",
}

LISTING = "<html><body>中航电测（证券代码：300114）将于2010年8月27日登陆创业板。</body></html>".encode()
TRANSITION = (
    "<html><body>关于变更公司证券简称及证券代码的实施公告。"
    "原证券代码300114变更为302132。变更后的证券代码启用日期：2025年2月17日。"
    "公司法人主体存续，上市主体没有发生实质变化。</body></html>"
).encode()
AS_OF = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)


def evidence(scope: str, raw: bytes, *, url: str | None = None) -> OfficialGraphEvidenceV1:
    return OfficialGraphEvidenceV1.from_bytes(
        raw_bytes=raw,
        url=url or f"https://www.szse.cn/{scope}.html",
        claim_scope=scope,
        document_date="2010-08-27" if scope == "ORIGINAL_LISTING" else "2025-02-14",
        retrieved_at=AS_OF,
    )


def test_exact_two_sided_evidence_ratifies_unchanged_graph():
    listing = evidence("ORIGINAL_LISTING", LISTING)
    transition = evidence("CODE_TRANSITION", TRANSITION)
    result = ratify_existing_graph(GRAPH, ((listing, LISTING), (transition, TRANSITION)), verified_at=AS_OF)
    assert result.graph_id == GRAPH["graph_id"]
    assert result.official_evidence_ids == (listing.artifact_id, transition.artifact_id)
    assert result.decision == "PASS"


@pytest.mark.parametrize(
    ("scope", "old", "new"),
    [
        ("ORIGINAL_LISTING", "2010年8月27日", "2010年8月28日"),
        ("ORIGINAL_LISTING", "300114", "300115"),
        ("CODE_TRANSITION", "302132", "302133"),
        ("CODE_TRANSITION", "2025年2月17日", "2025年2月18日"),
        ("CODE_TRANSITION", "实施公告", "意向公告"),
        ("CODE_TRANSITION", "上市主体没有发生实质变化", "上市主体发生变化"),
    ],
)
def test_changed_official_claim_fails_closed(scope: str, old: str, new: str):
    raw = (LISTING if scope == "ORIGINAL_LISTING" else TRANSITION).decode().replace(old, new).encode()
    with pytest.raises(GraphRatificationError):
        evidence(scope, raw)


def test_changed_raw_document_hash_fails_closed():
    listing = evidence("ORIGINAL_LISTING", LISTING)
    transition = evidence("CODE_TRANSITION", TRANSITION)
    with pytest.raises(GraphRatificationError):
        ratify_existing_graph(GRAPH, ((listing, LISTING + b"tamper"), (transition, TRANSITION)), verified_at=AS_OF)


def test_nonofficial_source_fails_closed():
    with pytest.raises(GraphRatificationError):
        evidence("ORIGINAL_LISTING", LISTING, url="https://example.com/ORIGINAL_LISTING.html")


def test_changed_graph_body_or_id_fails_closed():
    listing = evidence("ORIGINAL_LISTING", LISTING)
    transition = evidence("CODE_TRANSITION", TRANSITION)
    changed = {**GRAPH, "transition_effective_at": "2025-02-18"}
    with pytest.raises(GraphRatificationError):
        ratify_existing_graph(changed, ((listing, LISTING), (transition, TRANSITION)), verified_at=AS_OF)
    changed = {**GRAPH, "graph_id": "0" * 64}
    with pytest.raises(GraphRatificationError):
        ratify_existing_graph(changed, ((listing, LISTING), (transition, TRANSITION)), verified_at=AS_OF)


def test_one_sided_history_fails_closed():
    listing = evidence("ORIGINAL_LISTING", LISTING)
    with pytest.raises(GraphRatificationError):
        ratify_existing_graph(GRAPH, ((listing, LISTING),), verified_at=AS_OF)


def test_graph_scoped_approval_consumes_only_verified_ratification():
    listing = evidence("ORIGINAL_LISTING", LISTING)
    transition = evidence("CODE_TRANSITION", TRANSITION)
    ratification = ratify_existing_graph(GRAPH, ((listing, LISTING), (transition, TRANSITION)), verified_at=AS_OF)
    approval = SecurityIdentityGraphApprovalV1.create(ratification)
    assert approval.decision == "APPROVED"
    assert approval.scope == "EXISTING_GRAPH_RATIFICATION"
    assert approval.graph_id == GRAPH["graph_id"]
    assert approval.ratification_evidence_id == ratification.evidence_id
    assert approval.official_evidence_ids == (listing.artifact_id, transition.artifact_id)


def test_tampered_ratification_cannot_create_approval():
    listing = evidence("ORIGINAL_LISTING", LISTING)
    transition = evidence("CODE_TRANSITION", TRANSITION)
    ratification = ratify_existing_graph(GRAPH, ((listing, LISTING), (transition, TRANSITION)), verified_at=AS_OF)
    with pytest.raises(GraphRatificationError):
        SecurityIdentityGraphApprovalV1.create(replace(ratification, expected_transition_date="2025-02-18"))
    with pytest.raises(GraphRatificationError):
        SecurityIdentityGraphApprovalV1.create(replace(ratification, decision="PENDING"))


def test_offline_materializer_rejects_changed_raw_bytes(tmp_path):
    source = tmp_path / "official.html"
    source.write_bytes(b"official original")
    with pytest.raises(GraphRatificationError):
        _exact_bytes(source, "0" * 64)


def test_offline_materializer_is_create_or_identical(tmp_path):
    listing = evidence("ORIGINAL_LISTING", LISTING)
    output = tmp_path / "evidence.json"
    _write_immutable(output, listing)
    original = output.read_bytes()
    _write_immutable(output, listing)
    assert output.read_bytes() == original
    output.write_bytes(b"tampered")
    with pytest.raises(GraphRatificationError):
        _write_immutable(output, listing)
