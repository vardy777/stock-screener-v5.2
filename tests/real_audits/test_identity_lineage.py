from __future__ import annotations

from datetime import date

import pytest

from v5_2.data.real_audits.identity_lineage import (
    EffectiveDatedSecurityIdentityV1,
    HistoricalSecurityIdentityQuestionV1,
    IdentityIntervalV1,
    IdentityLineageError,
)


def test_identity_question_states_historical_problem_not_current_lookup() -> None:
    question = HistoricalSecurityIdentityQuestionV1.create(
        provider_identity="302132.SZ", provider_listing_date=date(2010, 8, 27),
        questions=("historical owner of listing_date", "code transition effective date", "predecessor identity"),
        input_artifact_ids=("raw",), policy_version="identity-question-v1",
    )
    assert question.question_id == question.content_hash
    assert "current company lookup" not in question.questions


def test_effective_dated_graph_requires_evidence_and_nonoverlapping_intervals() -> None:
    graph = EffectiveDatedSecurityIdentityV1.create(
        provider_identity="302132.SZ",
        intervals=(
            IdentityIntervalV1("300114.SZ", date(2010, 8, 27), date(2025, 2, 16), "A_SHARE", "CHINEXT"),
            IdentityIntervalV1("302132.SZ", date(2025, 2, 17), None, "A_SHARE", "CHINEXT"),
        ),
        transition_event="SECURITY_CODE_CHANGE",
        transition_effective_at=date(2025, 2, 17),
        evidence_ids=("szse-listing-2010", "szse-code-change-2025"),
        policy_version="effective-identity-v1",
    )
    assert graph.graph_id == graph.content_hash
    assert graph.intervals[0].identity == "300114.SZ"
    assert graph.intervals[1].effective_from == date(2025, 2, 17)

    with pytest.raises(IdentityLineageError, match="overlap"):
        EffectiveDatedSecurityIdentityV1.create(
            provider_identity="302132.SZ",
            intervals=(
                IdentityIntervalV1("300114.SZ", date(2010, 8, 27), date(2025, 2, 17), "A_SHARE", "CHINEXT"),
                IdentityIntervalV1("302132.SZ", date(2025, 2, 17), None, "A_SHARE", "CHINEXT"),
            ), transition_event="SECURITY_CODE_CHANGE", transition_effective_at=date(2025, 2, 17),
            evidence_ids=("a", "b"), policy_version="v1",
        )


def test_current_code_cannot_silently_inherit_historical_listing_date() -> None:
    with pytest.raises(IdentityLineageError, match="transition evidence"):
        EffectiveDatedSecurityIdentityV1.create(
            provider_identity="302132.SZ",
            intervals=(IdentityIntervalV1("302132.SZ", date(2010, 8, 27), None, "A_SHARE", "CHINEXT"),),
            transition_event="UNKNOWN", transition_effective_at=None,
            evidence_ids=("current-only",), policy_version="v1",
        )
