import os
from pathlib import Path

import pytest

from v5_2.data.historical_status_authority import reconstruct_frozen_status_inputs


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "data/phase_1b_exit_remediation/governance"
STAGING = os.environ.get("V5_2_STATUS_STAGING_ROOT")


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

