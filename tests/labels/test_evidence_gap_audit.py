from pathlib import Path

import pytest

from v5_2.data.real_audits.phase2a_evidence_gap import (
    BLOCKER_CLASSES,
    audit_phase2a_evidence_gaps,
    render_evidence_gap_matrix,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/phase_2a/governance").is_dir(),
    reason="repository-local governance artifacts are excluded from clean room",
)


def test_real_gap_audit_covers_frozen_inventory_without_vague_root_causes():
    audit = audit_phase2a_evidence_gaps(ROOT)

    assert audit.inventory_id == "81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9"
    assert len(audit.entries) == 22
    assert tuple(entry.slot for entry in audit.entries) == tuple(range(1, 23))
    assert all(not entry.blocker_class or entry.blocker_class in BLOCKER_CLASSES for entry in audit.entries)
    assert all(entry.blocker_reason != "EVIDENCE_UNAVAILABLE" for entry in audit.entries)
    assert audit.verify()


def test_gap_audit_closes_assembler_lookup_defect_without_hiding_phase1_gaps():
    audit = audit_phase2a_evidence_gaps(ROOT)
    by_slot = {entry.slot: entry for entry in audit.entries}

    assert by_slot[1].daily_bar_status == "D_AND_REQUIRED_WINDOW_FOUND"
    assert by_slot[1].bundle_constructible
    assert by_slot[6].daily_bar_status == "D_AND_REQUIRED_WINDOW_FOUND"
    assert by_slot[6].bundle_constructible
    assert by_slot[8].security_status_status == "PARTIAL_SPECIAL_EVENT_FACTS_FOUND"
    assert by_slot[8].daily_bar_status == "D_AND_REQUIRED_WINDOW_FOUND_WITH_PROVEN_ABSENCE"
    assert by_slot[9].bundle_constructible
    assert by_slot[11].anchor_reference_bar_status == "PROVEN_FULL_DAY_SUSPENSION"
    assert by_slot[11].daily_bar_status == "ANCHOR_SUSPENDED_NOT_LABEL_SAFE"
    assert by_slot[14].bundle_constructible
    assert by_slot[18].future_window_status == "CALENDAR_EXTENSION_FOUND"


def test_gap_audit_records_every_required_diagnostic_field():
    entry = audit_phase2a_evidence_gaps(ROOT).entries[0]
    required = {
        "slot", "stratum", "canonical_identity", "anchor_session",
        "calendar_status", "master_status", "daily_bar_status",
        "security_status_status", "corporate_action_status",
        "anchor_reference_bar_status", "future_window_status",
        "eligibility_status", "identity_status", "ca_coverage_status",
        "missing_artifact_type", "missing_artifact_id_or_lookup_key",
        "lookup_location_checked", "candidate_artifacts_found",
        "bundle_constructible", "blocker_class", "blocker_reason",
    }
    assert set(entry.as_dict()) == required


def test_gap_matrix_renders_each_frozen_slot_and_exact_blocker_counts():
    report = render_evidence_gap_matrix(audit_phase2a_evidence_gaps(ROOT))

    assert report.count("\n| 01 |") == 1
    assert report.count("\n| 22 |") == 1
    assert "ASSEMBLER_LOOKUP_DEFECT COUNT = 0" in report
    assert "REAL_PHASE1_EVIDENCE_ABSENT COUNT = 0" in report
    assert "EVIDENCE_UNAVAILABLE" not in report.split("## 22-slot blocker matrix", 1)[0]


def test_candidate_artifact_locations_are_repository_relative():
    audit = audit_phase2a_evidence_gaps(ROOT)

    assert all(
        not Path(candidate).is_absolute()
        for entry in audit.entries
        for candidate in entry.candidate_artifacts_found
    )
