"""Offline, graph-scoped ratification of the frozen 300114/302132 identity."""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Mapping, Sequence

from v5_2.data.identity import content_hash
from v5_2.data.real_audits.identity_lineage import (
    EffectiveDatedSecurityIdentityV1,
    IdentityIntervalV1,
    IdentityLineageError,
)


GRAPH_ID = "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0"
OFFICIAL_HOSTS = frozenset({"szse.cn", "www.szse.cn", "disc.static.szse.cn", "static.cninfo.com.cn", "cninfo.com.cn"})
POLICY_VERSION = "security-identity-graph-ratification-v1"
_OFFICIAL_URL = re.compile(r"https://([a-z0-9.-]+)(/[A-Za-z0-9_./-]+)")


class GraphRatificationError(ValueError):
    """Official bytes or graph do not prove the frozen identity claims."""


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _source_text(raw_bytes: bytes, url: str) -> str:
    match = _OFFICIAL_URL.fullmatch(url)
    if match is None:
        raise GraphRatificationError("official URL syntax is invalid")
    path = match.group(2).lower()
    if path.endswith(".pdf"):
        try:
            import pdfplumber  # optional audit dependency, never needed by research
        except ImportError as exc:
            raise GraphRatificationError("PDF audit dependency pdfplumber unavailable") from exc
        try:
            with pdfplumber.open(io.BytesIO(raw_bytes)) as document:
                return "\n".join(page.extract_text() or "" for page in document.pages)
        except Exception as exc:
            raise GraphRatificationError("official PDF cannot be parsed") from exc
    if path.endswith((".html", ".htm")):
        try:
            decoded = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GraphRatificationError("official HTML is not UTF-8") from exc
        parser = _HTMLText()
        parser.feed(decoded)
        return "".join(parser.parts)
    raise GraphRatificationError("unsupported official document format")


def _claims(text: str, scope: str) -> Mapping[str, str]:
    compact = re.sub(r"\s+", "", text)
    if scope == "ORIGINAL_LISTING":
        if not re.search(r"中航电测.{0,20}(?:证券代码[:：])?300114.{0,35}2010年8月27日.{0,10}(?:登陆|上市).{0,5}创业板", compact):
            raise GraphRatificationError("original listing identity/date/venue not proven")
        return {"identity": "300114.SZ", "listing_date": "2010-08-27", "venue": "SZSE_CHINEXT"}
    if scope == "CODE_TRANSITION":
        if "实施公告" not in compact:
            raise GraphRatificationError("final code-change implementation notice absent")
        if not re.search(r"原证券代码.{0,5}300114.{0,8}变更为.{0,5}302132", compact):
            raise GraphRatificationError("old-to-new security code transition not proven")
        if not re.search(r"(?:启用日期|自)[:：]?(?:为)?2025年2月17日", compact):
            raise GraphRatificationError("transition effective date not proven")
        if "公司法人主体存续" not in compact or "上市主体没有发生实质变化" not in compact:
            raise GraphRatificationError("listed entity continuity not proven")
        return {"predecessor": "300114.SZ", "successor": "302132.SZ", "effective_from": "2025-02-17", "transition_event": "SECURITY_CODE_CHANGE", "listed_entity_continuity": "CONTINUES"}
    raise GraphRatificationError("unsupported evidence claim scope")


@dataclass(frozen=True, slots=True)
class OfficialGraphEvidenceV1:
    artifact_id: str
    source_authority: str
    url: str
    claim_scope: str
    document_date: str
    retrieved_at: datetime
    raw_sha256: str
    extracted_claims: Mapping[str, str]
    policy_version: str
    content_hash: str

    @classmethod
    def from_bytes(cls, *, raw_bytes: bytes, url: str, claim_scope: str, document_date: str, retrieved_at: datetime) -> "OfficialGraphEvidenceV1":
        match = _OFFICIAL_URL.fullmatch(url)
        host = match.group(1) if match else ""
        if host not in OFFICIAL_HOSTS:
            raise GraphRatificationError("official source URL is not allowed")
        if not raw_bytes or retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise GraphRatificationError("empty source or naive acquisition time")
        date.fromisoformat(document_date)
        claims = _claims(_source_text(raw_bytes, url), claim_scope)
        body = {"schema_version": "OfficialGraphEvidenceV1", "source_authority": host, "url": url,
                "claim_scope": claim_scope, "document_date": document_date, "retrieved_at": retrieved_at,
                "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(), "extracted_claims": claims,
                "policy_version": POLICY_VERSION}
        digest = content_hash(body)
        return cls(artifact_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})

    def verify_raw(self, raw_bytes: bytes) -> None:
        if hashlib.sha256(raw_bytes).hexdigest() != self.raw_sha256:
            raise GraphRatificationError("official document bytes changed")
        rebuilt = self.from_bytes(raw_bytes=raw_bytes, url=self.url, claim_scope=self.claim_scope,
                                  document_date=self.document_date, retrieved_at=self.retrieved_at)
        if rebuilt != self:
            raise GraphRatificationError("official evidence artifact changed")


@dataclass(frozen=True, slots=True)
class SecurityIdentityGraphRatificationEvidenceV1:
    evidence_id: str
    graph_id: str
    graph_body_hash: str
    official_evidence_ids: tuple[str, str]
    expected_predecessor: str
    expected_successor: str
    expected_original_listing_date: str
    expected_transition_date: str
    expected_transition_event: str
    verified_at: datetime
    decision: str
    policy_version: str
    content_hash: str

    def verify(self) -> None:
        body = {"schema_version": "SecurityIdentityGraphRatificationEvidenceV1", "graph_id": self.graph_id,
                "graph_body_hash": self.graph_body_hash, "official_evidence_ids": self.official_evidence_ids,
                "expected_predecessor": self.expected_predecessor, "expected_successor": self.expected_successor,
                "expected_original_listing_date": self.expected_original_listing_date,
                "expected_transition_date": self.expected_transition_date,
                "expected_transition_event": self.expected_transition_event, "verified_at": self.verified_at,
                "decision": self.decision, "policy_version": self.policy_version}
        if (self.graph_id != GRAPH_ID or self.graph_body_hash != GRAPH_ID or self.decision != "PASS"
                or self.expected_predecessor != "300114.SZ" or self.expected_successor != "302132.SZ"
                or self.expected_original_listing_date != "2010-08-27"
                or self.expected_transition_date != "2025-02-17"
                or self.expected_transition_event != "SECURITY_CODE_CHANGE"
                or len(self.official_evidence_ids) != 2 or self.policy_version != POLICY_VERSION
                or content_hash(body) != self.evidence_id or self.content_hash != self.evidence_id):
            raise GraphRatificationError("ratification evidence is not exact or has been changed")


@dataclass(frozen=True, slots=True)
class SecurityIdentityGraphApprovalV1:
    approval_id: str
    scope: str
    graph_id: str
    ratification_evidence_id: str
    official_evidence_ids: tuple[str, str]
    verified_at: datetime
    decision: str
    policy_version: str
    content_hash: str

    @classmethod
    def create(cls, ratification: SecurityIdentityGraphRatificationEvidenceV1) -> "SecurityIdentityGraphApprovalV1":
        ratification.verify()
        body = {"schema_version": "SecurityIdentityGraphApprovalV1", "scope": "EXISTING_GRAPH_RATIFICATION",
                "graph_id": ratification.graph_id, "ratification_evidence_id": ratification.evidence_id,
                "official_evidence_ids": ratification.official_evidence_ids, "verified_at": ratification.verified_at,
                "decision": "APPROVED", "policy_version": POLICY_VERSION}
        digest = content_hash(body)
        return cls(approval_id=digest, content_hash=digest, **{k: v for k, v in body.items() if k != "schema_version"})


def ratify_existing_graph(graph_body: Mapping[str, object], sources: Sequence[tuple[OfficialGraphEvidenceV1, bytes]], *, verified_at: datetime) -> SecurityIdentityGraphRatificationEvidenceV1:
    if verified_at.tzinfo is None or verified_at.utcoffset() is None:
        raise GraphRatificationError("naive ratification time")
    try:
        intervals = tuple(IdentityIntervalV1(identity=str(row["identity"]), effective_from=date.fromisoformat(str(row["effective_from"])),
                                            effective_to=date.fromisoformat(str(row["effective_to"])) if row["effective_to"] else None,
                                            security_type=str(row["security_type"]), board=str(row["board"]))
                          for row in graph_body["intervals"])
        graph = EffectiveDatedSecurityIdentityV1.create(provider_identity=str(graph_body["provider_identity"]),
            intervals=intervals, transition_event=str(graph_body["transition_event"]),
            transition_effective_at=date.fromisoformat(str(graph_body["transition_effective_at"])),
            evidence_ids=tuple(graph_body["evidence_ids"]), policy_version=str(graph_body["policy_version"]))
    except (KeyError, TypeError, ValueError, IdentityLineageError) as exc:
        raise GraphRatificationError("graph body malformed") from exc
    if graph.graph_id != GRAPH_ID or graph_body.get("graph_id") != GRAPH_ID or graph_body.get("content_hash") != GRAPH_ID:
        raise GraphRatificationError("graph ID does not match unchanged body")
    if len(intervals) != 2 or len(sources) != 2 or len({source.claim_scope for source, _ in sources}) != 2:
        raise GraphRatificationError("two distinct official claim dimensions required")
    by_scope = {}
    for source, raw in sources:
        source.verify_raw(raw)
        by_scope[source.claim_scope] = source
    if set(by_scope) != {"ORIGINAL_LISTING", "CODE_TRANSITION"}:
        raise GraphRatificationError("original listing and code transition evidence required")
    listing, transition = by_scope["ORIGINAL_LISTING"], by_scope["CODE_TRANSITION"]
    a, b = intervals
    if (a.identity != listing.extracted_claims["identity"] or a.effective_from.isoformat() != listing.extracted_claims["listing_date"]
            or a.security_type != "A_SHARE" or a.board != "CHINEXT"
            or b.identity != transition.extracted_claims["successor"] or a.identity != transition.extracted_claims["predecessor"]
            or b.effective_from.isoformat() != transition.extracted_claims["effective_from"]
            or a.effective_to != b.effective_from - timedelta(days=1) or b.effective_to is not None
            or graph.provider_identity != b.identity or graph.transition_effective_at != b.effective_from
            or graph.transition_event != transition.extracted_claims["transition_event"]
            or transition.extracted_claims["listed_entity_continuity"] != "CONTINUES"):
        raise GraphRatificationError("official claims do not match frozen graph")
    body = {"schema_version": "SecurityIdentityGraphRatificationEvidenceV1", "graph_id": GRAPH_ID,
            "graph_body_hash": graph.graph_id, "official_evidence_ids": (listing.artifact_id, transition.artifact_id),
            "expected_predecessor": a.identity, "expected_successor": b.identity,
            "expected_original_listing_date": a.effective_from.isoformat(),
            "expected_transition_date": b.effective_from.isoformat(), "expected_transition_event": graph.transition_event,
            "verified_at": verified_at, "decision": "PASS", "policy_version": POLICY_VERSION}
    digest = content_hash(body)
    return SecurityIdentityGraphRatificationEvidenceV1(evidence_id=digest, content_hash=digest,
        **{k: v for k, v in body.items() if k != "schema_version"})
