from dataclasses import replace
from datetime import date

import pytest

from v5_2.data.corporate_action_facts import ActionType
from v5_2.data.real_audits.corporate_action_evidence import (
    CorporateActionEvidenceError,
    CorporateActionPITEvidenceV1,
)


def make_evidence(**overrides):
    values = dict(
        target_history_start=date(2010, 1, 4), baseline_validation_end=date(2025, 12, 31),
        rolling_coverage_end=date(2026, 9, 9), source_name="datahubco_tushare_proxy",
        source_version_identity="dividend-schema-v1",
        supported_action_types=(ActionType.CASH_DIVIDEND, ActionType.BONUS_SHARE),
        unsupported_action_types=(ActionType.RIGHTS_ISSUE, ActionType.STOCK_SPLIT, ActionType.SHARE_CONVERSION),
        validated_coverage_by_action_type=((ActionType.CASH_DIVIDEND, date(2024, 1, 1), date(2026, 9, 9)), (ActionType.BONUS_SHARE, date(2024, 1, 1), date(2026, 9, 9))),
        materialized_coverage_by_action_type=((ActionType.CASH_DIVIDEND, date(2024, 1, 1), date(2026, 9, 9)), (ActionType.BONUS_SHARE, date(2024, 1, 1), date(2026, 9, 9))),
        coverage_gaps=((date(2010, 1, 4), date(2023, 12, 31), "historical validation pending"),),
        unsupported_intervals=(
            (ActionType.RIGHTS_ISSUE, date(2010, 1, 4), date(2026, 9, 9)),
            (ActionType.STOCK_SPLIT, date(2010, 1, 4), date(2026, 9, 9)),
            (ActionType.SHARE_CONVERSION, date(2010, 1, 4), date(2026, 9, 9)),
        ),
        cross_source_evidence_ids=("official-1",), exception_ids=(), quarantine_ids=("rights-all",),
        publication_rule="date-only-next-session-1630", economic_effect_rule="ex-date",
        revision_rule="latest-known-version", cancellation_rule="cancelled-no-effect",
        complete=True,
    )
    values.update(overrides)
    return CorporateActionPITEvidenceV1.create(**values)


def test_complete_means_scoped_subset_not_full_target_coverage():
    evidence = make_evidence()
    assert evidence.complete
    assert evidence.coverage_gaps
    assert evidence.verify()


def test_complete_evidence_requires_independent_evidence_and_visible_unsupported_scope():
    with pytest.raises(CorporateActionEvidenceError):
        make_evidence(cross_source_evidence_ids=())
    with pytest.raises(CorporateActionEvidenceError):
        make_evidence(unsupported_intervals=())


def test_evidence_tamper_is_detected():
    evidence = make_evidence()
    assert not replace(evidence, rolling_coverage_end=date(2026, 9, 10)).verify()
