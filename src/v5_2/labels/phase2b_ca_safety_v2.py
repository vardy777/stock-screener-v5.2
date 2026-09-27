"""Source-pinned corporate-action gate with explicit contract-only negatives."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
import json
from pathlib import Path
import re

from v5_2.data.corporate_action_facts import ActionType, CorporateActionFactV1
from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.contracts import LabelInputBundleV1
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.independent_reference import calculate_independent_reference


_ID = re.compile(r"^[0-9a-f]{64}$")
_REAL_CASES = (("000333.SZ", date(2021, 6, 1)),
               ("600276.SH", date(2019, 3, 27)))
_UNSUPPORTED = (ActionType.RIGHTS_ISSUE, ActionType.SHARE_CONVERSION,
                ActionType.STOCK_SPLIT)


def _with_actions(bundle: LabelInputBundleV1,
                  actions: tuple[CorporateActionFactV1, ...]) -> LabelInputBundleV1:
    values = {field.name: getattr(bundle, field.name) for field in fields(bundle)
              if field.name != "content_hash"}
    values["corporate_actions"] = actions
    return LabelInputBundleV1.create(**values)


def compare_ca_bundle_to_source(candidate: LabelInputBundleV1,
                                source: LabelInputBundleV1) -> bool:
    """An otherwise valid rehashed bundle cannot omit or replace source CA."""
    if not candidate.verify() or not source.verify():
        return False
    if (candidate.canonical_security_identity != source.canonical_security_identity
            or candidate.anchor_session != source.anchor_session
            or candidate.action_coverage != source.action_coverage
            or candidate.domain_lineage != source.domain_lineage
            or tuple(item.fact_id for item in candidate.corporate_actions)
               != tuple(item.fact_id for item in source.corporate_actions)
            or not all(item.verify() for item in candidate.corporate_actions)):
        return False
    return calculate_independent_reference(1, candidate).result_summary == (
        calculate_independent_reference(1, source).result_summary)


@dataclass(frozen=True, slots=True)
class CASafetyEvidenceV2:
    source_approval_id: str
    source_authority_id: str
    supported_action_types: tuple[str, ...]
    real_cases: tuple[tuple[str, str, str, tuple[str, ...], str,
                            tuple[str, ...]], ...]
    unsupported_fixture_kind: str
    unsupported_rejections: tuple[str, ...]
    synthetic_fixture_ids: tuple[str, ...]
    evidence_id: str

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "evidence_id"}
        return (bool(_ID.fullmatch(self.source_approval_id))
                and bool(_ID.fullmatch(self.source_authority_id))
                and self.supported_action_types == ("BONUS_SHARE", "CASH_DIVIDEND")
                and self.unsupported_fixture_kind == "SYNTHETIC_CONTRACT_FIXTURE"
                and self.unsupported_rejections == tuple(
                    kind.value for kind in _UNSUPPORTED)
                and len(self.real_cases) == len(_REAL_CASES)
                and len(self.synthetic_fixture_ids) == len(_UNSUPPORTED)
                and all(_ID.fullmatch(value) for value in self.synthetic_fixture_ids)
                and self.evidence_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def _synthetic_unsupported(base: CorporateActionFactV1,
                           kind: ActionType) -> CorporateActionFactV1:
    values = {field.name: getattr(base, field.name) for field in fields(base)
              if field.name not in ("fact_id", "content_hash")}
    values.update(action_type=kind, cash_per_share=None,
                  share_ratio=base.share_ratio if kind is not ActionType.RIGHTS_ISSUE
                  else None,
                  source_fact_id=f"SYNTHETIC_CONTRACT_FIXTURE:{kind.value}")
    if kind is not ActionType.RIGHTS_ISSUE and values["share_ratio"] is None:
        from decimal import Decimal
        values["share_ratio"] = Decimal("1")
    return CorporateActionFactV1.create(**values)


def derive_ca_safety_evidence_exact(root: Path) -> CASafetyEvidenceV2:
    producer = HistoricalFiveDomainProducerV1.load_exact(root)
    cases = []
    supported = set()
    first_bundle = None
    for symbol, session in _REAL_CASES:
        produced = producer.produce_anchor(symbol, session)
        if not isinstance(produced, tuple):
            raise ValueError("frozen real CA case is source-excluded")
        bundle = producer.assemble(*produced)
        if not bundle.corporate_actions or not bundle.verify():
            raise ValueError("frozen real CA case lacks approved actions")
        independent = calculate_independent_reference(1, bundle)
        if not independent.verify() or not compare_ca_bundle_to_source(bundle, bundle):
            raise ValueError("real CA baseline invalid")
        omission_ids = []
        for action in bundle.corporate_actions:
            supported.add(action.action_type.value)
            omitted = _with_actions(bundle, tuple(item for item in
                bundle.corporate_actions if item.fact_id != action.fact_id))
            if compare_ca_bundle_to_source(omitted, bundle):
                raise ValueError("supported CA omission passed source comparison")
            changed = calculate_independent_reference(1, omitted)
            if changed.result_summary == independent.result_summary:
                raise ValueError("supported CA omission lacked economic effect")
            omission_ids.append(changed.reference_id)
        cases.append((symbol, session.isoformat(), bundle.content_hash,
                      tuple(item.fact_id for item in bundle.corporate_actions),
                      independent.reference_id, tuple(omission_ids)))
        if first_bundle is None:
            first_bundle = bundle
    if supported != {ActionType.CASH_DIVIDEND.value,
                     ActionType.BONUS_SHARE.value}:
        raise ValueError("supported CA cases incomplete")
    fixture_ids = []
    for kind in _UNSUPPORTED:
        fixture = _synthetic_unsupported(first_bundle.corporate_actions[0], kind)
        candidate = _with_actions(first_bundle, (fixture,))
        independent = calculate_independent_reference(1, candidate)
        if not independent.verify() or not all(
                state == "NOT_LABEL_SAFE"
                and reason == "UNSUPPORTED_CORPORATE_ACTION"
                for _, state, _, reason in independent.result_summary):
            raise ValueError("unsupported CA was not rejected")
        fixture_ids.append(fixture.fact_id)
    body = {
        "source_approval_id": producer.actions.approval_id,
        "source_authority_id": producer.actions.bundle_id,
        "supported_action_types": tuple(sorted(supported)),
        "real_cases": tuple(cases),
        "unsupported_fixture_kind": "SYNTHETIC_CONTRACT_FIXTURE",
        "unsupported_rejections": tuple(kind.value for kind in _UNSUPPORTED),
        "synthetic_fixture_ids": tuple(fixture_ids),
    }
    evidence = CASafetyEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "CASafetyEvidenceV2", **body}))
    if not evidence.verify():
        raise ValueError("CA safety evidence invalid")
    return evidence


def write_ca_safety_evidence(root: Path, evidence: CASafetyEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified CA evidence required")
    path = root / "gate_evidence" / f"ca-safety-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable CA evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_ca_safety_evidence_exact(path: Path, expected_id: str) -> CASafetyEvidenceV2:
    if not _ID.fullmatch(expected_id) or path.name != f"ca-safety-{expected_id}.json":
        raise ValueError("CA evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        values = json.loads(raw)
        evidence = CASafetyEvidenceV2(
            source_approval_id=values["source_approval_id"],
            source_authority_id=values["source_authority_id"],
            supported_action_types=tuple(values["supported_action_types"]),
            real_cases=tuple((symbol, session, bundle_id, tuple(fact_ids),
                              reference_id, tuple(omission_ids))
                             for symbol, session, bundle_id, fact_ids,
                                 reference_id, omission_ids in values["real_cases"]),
            unsupported_fixture_kind=values["unsupported_fixture_kind"],
            unsupported_rejections=tuple(values["unsupported_rejections"]),
            synthetic_fixture_ids=tuple(values["synthetic_fixture_ids"]),
            evidence_id=values["evidence_id"],
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("CA evidence unavailable or malformed") from error
    if (evidence.evidence_id != expected_id or not evidence.verify()
            or canonical_json(evidence) != raw):
        raise ValueError("CA evidence identity mismatch")
    return evidence
