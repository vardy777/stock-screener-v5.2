"""Source-pinned full-day suspension carry and horizon safety evidence."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date
import json
from pathlib import Path
import re

from v5_2.data.identity import canonical_json, content_hash
from v5_2.labels.contracts import LabelInputBundleV1
from v5_2.labels.historical_five_domain_producer import HistoricalFiveDomainProducerV1
from v5_2.labels.independent_reference import calculate_independent_reference


_ID = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL = "600658.SH"
_ANCHOR = date(2010, 5, 18)


def _with_statuses(bundle: LabelInputBundleV1, statuses: tuple) -> LabelInputBundleV1:
    values = {field.name: getattr(bundle, field.name) for field in fields(bundle)
              if field.name != "content_hash"}
    values["future_statuses"] = statuses
    return LabelInputBundleV1.create(**values)


def compare_suspension_bundle_to_source(candidate: LabelInputBundleV1,
                                        source: LabelInputBundleV1) -> bool:
    if not candidate.verify() or not source.verify():
        return False
    if (candidate.canonical_security_identity != source.canonical_security_identity
            or candidate.anchor_session != source.anchor_session
            or candidate.future_statuses != source.future_statuses
            or candidate.future_bars != source.future_bars
            or candidate.approved_exchange_sessions
               != source.approved_exchange_sessions
            or candidate.domain_lineage != source.domain_lineage):
        return False
    return calculate_independent_reference(1, candidate).result_summary == (
        calculate_independent_reference(1, source).result_summary)


@dataclass(frozen=True, slots=True)
class SuspensionSafetyEvidenceV2:
    source_approval_id: str
    source_authority_id: str
    bundle_id: str
    full_day_session: str
    resumption_session: str
    horizon_session_count: int
    independent_reference_id: str
    ordinary_mutation_reference_id: str
    evidence_id: str

    def verify(self) -> bool:
        body = {field.name: getattr(self, field.name) for field in fields(self)
                if field.name != "evidence_id"}
        return (all(_ID.fullmatch(value) for value in (
                    self.source_approval_id, self.source_authority_id,
                    self.bundle_id, self.independent_reference_id,
                    self.ordinary_mutation_reference_id))
                and self.full_day_session == "2010-05-19"
                and self.resumption_session == "2010-05-20"
                and self.horizon_session_count == 5
                and self.independent_reference_id
                    != self.ordinary_mutation_reference_id
                and self.evidence_id == content_hash({
                    "schema_version": type(self).__name__, **body}))


def derive_suspension_evidence_exact(root: Path) -> SuspensionSafetyEvidenceV2:
    producer = HistoricalFiveDomainProducerV1.load_exact(root)
    produced = producer.produce_anchor(_SYMBOL, _ANCHOR)
    if not isinstance(produced, tuple):
        raise ValueError("frozen real suspension case source-excluded")
    bundle = producer.assemble(*produced)
    sessions = tuple(day for day in bundle.approved_exchange_sessions
                     if day > bundle.anchor_session)[:5]
    bars = {item.session for item in bundle.future_bars}
    statuses = {item.session: item for item in bundle.future_statuses}
    if (len(sessions) != 5 or len(statuses) != 5
            or statuses[sessions[0]].is_suspended is not True
            or sessions[0] in bars
            or statuses[sessions[1]].is_suspended is not False
            or sessions[1] not in bars
            or not compare_suspension_bundle_to_source(bundle, bundle)):
        raise ValueError("real suspension/resumption source semantics invalid")
    independent = calculate_independent_reference(1, bundle)
    if (not independent.verify() or len(independent.economic_steps) != 5
            or independent.economic_steps[0].intraday_trade
            or independent.economic_steps[0].close_wealth
               != str(bundle.reference_price.price)
            or any(item.decisive_session == sessions[0]
                   for item in independent.barriers)
            or independent.horizons != (sessions[0], sessions[2], sessions[4])):
        raise ValueError("full-day wealth carry or horizon semantics invalid")
    mutated_statuses = tuple(
        replace(item, is_suspended=False) if item.session == sessions[0]
        else item for item in bundle.future_statuses)
    mutated = _with_statuses(bundle, mutated_statuses)
    if compare_suspension_bundle_to_source(mutated, bundle):
        raise ValueError("ordinary mutation passed source comparison")
    mutation_result = calculate_independent_reference(1, mutated)
    if not mutation_result.verify() or not all(
            state == "NOT_LABEL_SAFE" and reason == "EXPECTED_BAR_MISSING"
            for _, state, _, reason in mutation_result.result_summary):
        raise ValueError("ordinary mutation did not expose missing bar")
    body = {
        "source_approval_id": producer.status_pins.approval_id,
        "source_authority_id": producer.status_pins.authority_id,
        "bundle_id": bundle.content_hash,
        "full_day_session": sessions[0].isoformat(),
        "resumption_session": sessions[1].isoformat(),
        "horizon_session_count": len(sessions),
        "independent_reference_id": independent.reference_id,
        "ordinary_mutation_reference_id": mutation_result.reference_id,
    }
    result = SuspensionSafetyEvidenceV2(**body, evidence_id=content_hash({
        "schema_version": "SuspensionSafetyEvidenceV2", **body}))
    if not result.verify():
        raise ValueError("suspension evidence invalid")
    return result


def write_suspension_evidence(root: Path,
                              evidence: SuspensionSafetyEvidenceV2) -> Path:
    if not evidence.verify():
        raise ValueError("verified suspension evidence required")
    path = root / "gate_evidence" / f"suspension-safety-{evidence.evidence_id}.json"
    payload = canonical_json(evidence)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("immutable suspension evidence collision")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return path


def read_suspension_evidence_exact(path: Path, expected_id: str
                                   ) -> SuspensionSafetyEvidenceV2:
    if (not _ID.fullmatch(expected_id)
            or path.name != f"suspension-safety-{expected_id}.json"):
        raise ValueError("suspension evidence ID/path mismatch")
    try:
        raw = path.read_bytes()
        result = SuspensionSafetyEvidenceV2(**json.loads(raw))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("suspension evidence unavailable or malformed") from error
    if (result.evidence_id != expected_id or not result.verify()
            or canonical_json(result) != raw):
        raise ValueError("suspension evidence identity mismatch")
    return result
