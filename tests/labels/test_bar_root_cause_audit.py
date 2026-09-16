from pathlib import Path

import pytest

from v5_2.data.real_audits.phase2a_bar_root_cause import audit_remaining_bar_gaps, render_root_cause_report


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/phase_2a/bar_backfill/raw").is_dir(),
    reason="repository-local immutable evidence is excluded from clean room",
)


def test_root_cause_audit_classifies_all_fourteen_frozen_sessions_from_immutable_evidence():
    audit = audit_remaining_bar_gaps(ROOT)
    by_key = {(item.slot, item.session): item for item in audit.entries}

    assert len(audit.entries) == 14
    assert set(by_key) == {
        (9, "2019-04-12"), (9, "2019-04-16"),
        (10, "2015-11-16"), (10, "2015-11-18"), (10, "2015-11-19"),
        (10, "2015-11-20"), (10, "2015-11-23"), (11, "2014-09-11"),
        (14, "2023-08-03"), (14, "2023-08-04"), (14, "2023-08-07"),
        (14, "2023-08-08"), (14, "2023-08-09"), (14, "2023-08-10"),
    }
    assert sum(item.classification == "REQUESTED_AND_OMITTED" for item in audit.entries) == 9
    assert sum(item.classification == "PROVEN_EXPECTED_ABSENCE" for item in audit.entries) == 5
    assert all(item.exchange_open for item in audit.entries)
    assert all(item.request_covered_session and not item.targeted_raw_contains_session for item in audit.entries)
    assert audit.verify()


def test_delisting_boundary_is_applied_only_from_the_proven_effective_date():
    entries = {(item.slot, item.session): item for item in audit_remaining_bar_gaps(ROOT).entries}

    assert entries[(14, "2023-08-03")].classification == "REQUESTED_AND_OMITTED"
    assert entries[(14, "2023-08-03")].identity_valid
    for session in ("2023-08-04", "2023-08-07", "2023-08-08", "2023-08-09", "2023-08-10"):
        assert entries[(14, session)].classification == "PROVEN_EXPECTED_ABSENCE"
        assert entries[(14, session)].delisted


def test_no_acquisition_or_publication_defect_is_hidden_by_the_forensic_classification():
    audit = audit_remaining_bar_gaps(ROOT)

    assert audit.acquisition_defect_found is False
    assert audit.phase1_correctness_defect_found is False
    assert audit.counts == (
        ("REQUESTED_AND_OMITTED", 9), ("NOT_REQUESTED", 0),
        ("RETURNED_RAW_BUT_NOT_NORMALIZED", 0), ("NORMALIZED_BUT_NOT_PUBLISHED", 0),
        ("EXISTS_IN_OTHER_APPROVED_ARTIFACT", 0), ("PROVEN_EXPECTED_ABSENCE", 5),
        ("UNRESOLVED", 0),
    )
    assert audit.proposed_request_count == 0
    assert audit.provider_requests_actually_made == 0


def test_root_cause_report_exposes_each_session_and_stop_boundary():
    report = render_root_cause_report(audit_remaining_bar_gaps(ROOT))

    assert "2019-04-12" in report
    assert "2023-08-10" in report
    assert "REQUESTED_AND_OMITTED = 9" in report
    assert "PROVEN_EXPECTED_ABSENCE = 5" in report
    assert "BUNDLES CREATED = 0" in report
    assert "5-SLOT PILOT = NOT RUN" in report
