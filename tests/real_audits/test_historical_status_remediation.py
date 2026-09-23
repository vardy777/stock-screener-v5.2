import os
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from v5_2.data.historical_status_authority import (
    HistoricalStatusAuthorityError,
    load_portable_status_resolver,
    reconstruct_frozen_status_inputs,
)


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "data/phase_1b_exit_remediation/governance"
STAGING = os.environ.get("V5_2_STATUS_STAGING_ROOT")
PORTABLE = ROOT / "data/phase_1_status_lineage_remediation_v1"
DERIVED_APPROVAL = "9353de33e62405830a7dbef13e53836a969fb569f9e7d5370a67d5df9078fa95"
DERIVED_MANIFEST = "0c86954cffaae2ca09ff1efcd4b32d990a9cf3d2b82d520a64172a1875d457a8"
AUTHORITY = "d6f7f5517428891db66da60565baaea5828d7adcaf29c820d5fa746ddf29e59b"
COMPOSITION = "e4110ec6185731d9a2d80e151d79f82006e07e779c10a90a4b4c2e228a35e139"
REPLAY = "235f86dd7269768382c67620cd723d27347c7f99e386488efc9b93665a517baf"
ZONE = timezone(timedelta(hours=8))


def _sessions():
    base = json.loads((ROOT / "data/phase_1b1/governance/daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json").read_text(encoding="utf-8"))
    sessions = set(base["ordered_sessions"])
    extension = json.loads((ROOT / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json").read_text(encoding="utf-8"))
    sessions.update(row[1] for row in extension["ordered_rows"] if row[2] == 1)
    return tuple(date(int(x[:4]), int(x[4:6]), int(x[6:])) for x in sorted(sessions))


@pytest.fixture(scope="module")
def portable_resolver():
    return load_portable_status_resolver(
        portable_root=PORTABLE,
        expected_authority_id=AUTHORITY,
        expected_derived_approval_id=DERIVED_APPROVAL,
        expected_derived_manifest_id=DERIVED_MANIFEST,
        expected_composition_id=COMPOSITION,
        expected_replay_evidence_id=REPLAY,
        approved_sessions=_sessions(),
        revoked_approval_ids=(),
    )


@pytest.mark.skipif(not STAGING, reason="explicit offline status staging root is required")
def test_retained_status_inputs_exactly_reconstruct_frozen_authority():
    reconstructed = reconstruct_frozen_status_inputs(
        repository_root=ROOT,
        staging_root=Path(STAGING),
        manifest_path=GOVERNANCE / "daily_security_status-manifest-d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0.json",
        panel_path=GOVERNANCE / "historical-status-panel-cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707.json",
        approval_path=GOVERNANCE / "daily_security_status-approval-ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07.json",
    )

    assert len(reconstructed.raw_payload_hashes) == 118
    assert len(reconstructed.receipt_hashes) == 163
    assert len(reconstructed.lifecycle_rows) == 5_551
    assert len(reconstructed.namechange_rows) == 8_104
    assert len(reconstructed.suspension_rows) == 468_188
    assert reconstructed.lifecycle_hash == "bb96052035488424dcc7aaa9d577c9ca990fe6669df8bf4e466f0e3c8171d2a5"
    assert reconstructed.risk_warning_hash == "fb81454d499f645283e2c2ede0be3422486546e2a70180926a84a93c24cc199d"
    assert reconstructed.suspension_hash == "87e2a971a17660a632d058f95135ebb6d984d40534a956e052df17a19076c38d"


@pytest.mark.skipif(not PORTABLE.exists(), reason="repository-local portable authority is unavailable")
def test_portable_authority_resolves_arbitrary_exact_lineage(portable_resolver):
    ordinary = portable_resolver.resolve(
        "000001.SZ", date(2010, 1, 4), datetime(2010, 1, 4, 16, 30, tzinfo=ZONE)
    )
    st = portable_resolver.resolve(
        "300051.SZ", date(2021, 4, 26), datetime(2021, 4, 26, 16, 30, tzinfo=ZONE)
    )
    suspended = portable_resolver.resolve(
        "002166.SZ", date(2019, 4, 15), datetime(2019, 4, 15, 16, 30, tzinfo=ZONE)
    )

    assert ordinary.listed and not ordinary.risk_warning and not ordinary.full_day_suspended
    assert st.risk_warning
    assert suspended.full_day_suspended
    for result in (ordinary, st, suspended):
        assert result.derived_approval_id == DERIVED_APPROVAL
        assert result.derived_manifest_id == DERIVED_MANIFEST
        assert result.verify()


@pytest.mark.skipif(not PORTABLE.exists(), reason="repository-local portable authority is unavailable")
def test_portable_loader_rejects_revoked_parent_and_post_coverage(portable_resolver):
    with pytest.raises(HistoricalStatusAuthorityError, match="revoked"):
        load_portable_status_resolver(
            portable_root=PORTABLE, expected_authority_id=AUTHORITY,
            expected_derived_approval_id=DERIVED_APPROVAL,
            expected_derived_manifest_id=DERIVED_MANIFEST,
            expected_composition_id=COMPOSITION,
            expected_replay_evidence_id=REPLAY,
            approved_sessions=_sessions(),
            revoked_approval_ids=("ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07",),
        )
    with pytest.raises(HistoricalStatusAuthorityError, match="coverage"):
        portable_resolver.resolve(
            "000001.SZ", date(2026, 9, 11), datetime(2026, 9, 11, 16, 30, tzinfo=ZONE)
        )
