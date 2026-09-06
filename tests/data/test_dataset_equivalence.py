from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone

import pytest

from v5_2.data.dataset_equivalence import (
    DatasetEquivalenceDecision,
    DatasetEquivalenceEvidenceV1,
)


def make(**overrides):
    values = {
        "source_name": "datahubco_tushare_proxy",
        "dataset_kind": "trade_calendar",
        "reference_contract": "V5.2 trade_calendar phase-1b1-v1",
        "tested_endpoints": ("trade-cal",),
        "tested_fields": ("exchange", "cal_date", "is_open", "pretrade_date"),
        "coverage_tested": {"start": "2010-01-01", "end": "2025-12-31"},
        "sample_rule": {"method": "sha256_lowest_per_stratum", "seed": "fixed"},
        "field_mapping": {"cal_date": "calendar_date"},
        "semantic_findings": ("explicit open state",),
        "missing_fields": (),
        "extra_fields": (),
        "value_comparison_summary": {"matched": 12, "mismatched": 0, "unresolved": 0},
        "pit_findings": ("date is not automatically available_at",),
        "revision_findings": ("repeat payload identity stable",),
        "pagination_findings": ("terminal has_more false",),
        "cross_source_findings": ("SSE and SZSE sample matched",),
        "limitations": ("plaintext HTTP",),
        "decision": DatasetEquivalenceDecision.EQUIVALENT_WITH_RULES,
        "verified_at": datetime(2026, 9, 6, tzinfo=timezone.utc),
        "input_artifact_ids": ("b" * 64, "a" * 64),
        "policy_version": "equivalence-v1",
    }
    values.update(overrides)
    return DatasetEquivalenceEvidenceV1.create(**values)


def test_equivalence_evidence_is_content_addressed_and_order_canonical() -> None:
    first = make()
    second = make(input_artifact_ids=("a" * 64, "b" * 64))
    assert first.evidence_id == first.content_hash == second.evidence_id
    assert first.input_artifact_ids == ("a" * 64, "b" * 64)


def test_source_identity_cannot_impersonate_official_tushare() -> None:
    with pytest.raises(ValueError, match="source identity"):
        make(source_name="official_tushare")


def test_nested_contract_data_is_deeply_immutable() -> None:
    evidence = make()
    with pytest.raises(TypeError):
        evidence.field_mapping["cal_date"] = "wrong"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        evidence.decision = DatasetEquivalenceDecision.EQUIVALENT  # type: ignore[misc]


def test_required_sections_fail_closed_when_empty() -> None:
    with pytest.raises(ValueError, match="required"):
        make(tested_endpoints=())
