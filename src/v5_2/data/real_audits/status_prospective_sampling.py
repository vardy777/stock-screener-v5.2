from __future__ import annotations

from dataclasses import dataclass
import re

from v5_2.data.identity import content_hash


SEMANTICS = ("ACTIVE_ORDINARY_STATUS", "ACTUAL_FIRST_TRADABLE_SESSION", "DELISTING_BOUNDARY",
             "ST_ENTER", "ST_EXIT", "FULL_DAY_SUSPENSION", "RESUMPTION", "IDENTITY_TRANSITION")


def is_risk_warning_name(value: str) -> bool:
    return re.match(r"^S?\*?ST", value.strip().upper()) is not None


def is_st_exit_transition(previous_name: str, current_name: str) -> bool:
    return is_risk_warning_name(previous_name) and not is_risk_warning_name(current_name)


@dataclass(frozen=True, slots=True)
class ProspectiveStatusEvidenceContractV1:
    coverage_start: str
    coverage_end: str
    target_scope: str
    sample_counts: tuple[tuple[str, int], ...]
    selection_rule: str
    applicability_rule: str
    independent_source_rule: str
    mismatch_rule: str
    unavailable_rule: str
    pit_rule: str
    contract_id: str

    @classmethod
    def adopted(cls):
        counts = tuple((semantic, 1 if semantic == "IDENTITY_TRANSITION" else 10) for semantic in SEMANTICS)
        body = {"schema_version": "ProspectiveStatusEvidenceContractV1", "coverage_start": "20100104",
                "coverage_end": "20251231", "target_scope": "historically tradable SSE/SZSE target A-shares",
                "sample_counts": counts,
                "selection_rule": "canonical hash by semantic, exchange, year, board, identity and session; counts frozen before independent retrieval",
                "applicability_rule": "effective identity and confirmed historical tradability at the sampled session",
                "independent_source_rule": "official exchange anchor for identity/listing/delisting; independent daily source for observable state",
                "mismatch_rule": "any unexplained semantic mismatch is FAIL",
                "unavailable_rule": "unavailable is PENDING and never MATCH",
                "pit_rule": "all research-used semantics require complete StatusAvailabilityPolicyV2 knowledge-time proof"}
        values = {key: value for key, value in body.items() if key != "schema_version"}
        return cls(**values, contract_id=content_hash(body))


@dataclass(frozen=True, slots=True)
class ProspectiveStatusCandidateV1:
    security_identity: str
    session: str
    exchange: str
    board: str
    semantic: str
    provider_value: str
    semantic_assertion: str
    expected_evidence: str
    effective_identity: bool
    confirmed_historically_tradable: bool
    provider_evidence_ids: tuple[str, ...]
    candidate_hash: str

    @classmethod
    def create(cls, **values):
        values["provider_evidence_ids"] = tuple(sorted(set(values["provider_evidence_ids"])))
        return cls(**values, candidate_hash=content_hash({"schema_version": "ProspectiveStatusCandidateV1", **values}))


@dataclass(frozen=True, slots=True)
class ProspectiveStatusSampleInventoryV1:
    contract_id: str
    samples: tuple[ProspectiveStatusCandidateV1, ...]
    counts: tuple[tuple[str, int], ...]
    inventory_id: str


@dataclass(frozen=True, slots=True)
class ProspectiveStatusEvidenceContractV2:
    schema_version: str
    coverage_start: str
    coverage_end: str
    target_scope: str
    sample_counts: tuple[tuple[str, int], ...]
    selection_rule: str
    applicability_rule: str
    independent_source_rule: str
    mismatch_rule: str
    unavailable_rule: str
    pit_rule: str
    contract_id: str

    @classmethod
    def adopted(cls):
        counts = tuple((semantic, 1 if semantic == "IDENTITY_TRANSITION" else 10) for semantic in SEMANTICS)
        body = {"schema_version": "ProspectiveEvidenceContractV2", "coverage_start": "20100104",
                "coverage_end": "20251231", "target_scope": "historically tradable SSE/SZSE target A-shares",
                "sample_counts": counts,
                "selection_rule": "canonical candidate hash by semantic; fixed counts frozen before independent retrieval",
                "applicability_rule": "session must be inside the provider-supported effective identity interval and historically tradable; ST_EXIT requires risk-warning to non-risk-warning transition",
                "independent_source_rule": "SSE/SZSE/exchange-hosted disclosure or independently operated daily source; DataHub endpoints are provider-side only",
                "mismatch_rule": "any unexplained semantic mismatch is FAIL",
                "unavailable_rule": "unavailable is PENDING and never MATCH",
                "pit_rule": "all research-used semantics require complete StatusAvailabilityPolicyV2 knowledge-time proof"}
        return cls(**body, contract_id=content_hash(body))


@dataclass(frozen=True, slots=True)
class ProspectiveStatusCandidateV2:
    security_identity: str
    session: str
    exchange: str
    board: str
    semantic: str
    provider_value: str
    semantic_assertion: str
    expected_evidence: str
    effective_from: str
    effective_to: str
    effective_identity: bool
    confirmed_historically_tradable: bool
    provider_evidence_ids: tuple[str, ...]
    candidate_hash: str

    @classmethod
    def create(cls, **values):
        values["provider_evidence_ids"] = tuple(sorted(set(values["provider_evidence_ids"])))
        return cls(**values, candidate_hash=content_hash({"schema_version": "ProspectiveStatusCandidateV2", **values}))


@dataclass(frozen=True, slots=True)
class ProspectiveStatusSampleInventoryV2:
    schema_version: str
    contract_id: str
    samples: tuple[ProspectiveStatusCandidateV2, ...]
    counts: tuple[tuple[str, int], ...]
    inventory_id: str


def freeze_prospective_inventory(contract, pools):
    selected = []
    for semantic, required in contract.sample_counts:
        pool = tuple(pools.get(semantic, ()))
        if len(pool) < required:
            raise ValueError(f"insufficient applicable candidates for {semantic}")
        if any(item is None or item.semantic != semantic or not item.effective_identity
               or not item.confirmed_historically_tradable for item in pool):
            raise ValueError("candidate is not applicable at sampled session")
        ordered = sorted(pool, key=lambda item: (item.exchange, item.session[:4], item.board, item.candidate_hash))
        chosen = sorted(ordered, key=lambda item: item.candidate_hash)[:required]
        if required > 1 and len({item.exchange for item in chosen}) < 2:
            raise ValueError("sample lacks exchange coverage")
        selected.extend(chosen)
    samples = tuple(selected)
    counts = tuple((semantic, sum(item.semantic == semantic for item in samples)) for semantic, _ in contract.sample_counts)
    digest = content_hash({"schema_version": "ProspectiveStatusSampleInventoryV1", "contract_id": contract.contract_id,
                           "sample_hashes": tuple(item.candidate_hash for item in samples), "counts": counts})
    return ProspectiveStatusSampleInventoryV1(contract.contract_id, samples, counts, digest)


def freeze_prospective_inventory_v2(contract, pools):
    selected = []
    for semantic, required in contract.sample_counts:
        pool = tuple(pools.get(semantic, ()))
        if len(pool) < required:
            raise ValueError(f"insufficient applicable candidates for {semantic}")
        if any(item.semantic != semantic or not item.effective_identity
               or not item.confirmed_historically_tradable for item in pool):
            raise ValueError("candidate is not applicable at sampled session")
        if any(not item.effective_from <= item.session <= item.effective_to for item in pool):
            raise ValueError("candidate session is outside effective interval")
        chosen = sorted(pool, key=lambda item: item.candidate_hash)[:required]
        if required > 1 and len({item.exchange for item in chosen}) < 2:
            raise ValueError("sample lacks exchange coverage")
        selected.extend(chosen)
    samples = tuple(selected)
    if len({item.candidate_hash for item in samples}) != len(samples):
        raise ValueError("duplicate candidate in frozen inventory")
    counts = tuple((semantic, sum(item.semantic == semantic for item in samples)) for semantic, _ in contract.sample_counts)
    body = {"schema_version": "ProspectiveStatusSampleInventoryV2", "contract_id": contract.contract_id,
            "sample_hashes": tuple(item.candidate_hash for item in samples), "counts": counts}
    return ProspectiveStatusSampleInventoryV2(body["schema_version"], contract.contract_id, samples, counts,
                                              content_hash(body))
