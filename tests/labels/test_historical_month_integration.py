"""Checkpoint 18 source-pinned month integration, explicitly not the pilot."""

import os
from pathlib import Path

import pytest

from datetime import date

from v5_2.labels.historical_five_domain_producer import ScopedAnchorExclusionV1
from v5_2.labels.historical_month_integration import (
    integrate_real_month, read_scoped_exclusions_exact, write_scoped_exclusions,
)


ROOT = Path(__file__).resolve().parents[2]
def test_scoped_exclusion_ledger_is_exact_and_create_or_identical(tmp_path):
    item = ScopedAnchorExclusionV1("000001.SZ", date(2010, 1, 11),
                                    "daily_bar", "UNEXPLAINED_MISSING_BAR", ("a" * 64,))
    first = write_scoped_exclusions(tmp_path, "2010-01", (item,))
    assert write_scoped_exclusions(tmp_path, "2010-01", (item,)) == first
    assert first.affected_securities == 1
    assert first.reason_counts == (("UNEXPLAINED_MISSING_BAR", 1),)
    path = tmp_path / "scoped_exclusions" / f"{first.ledger_id}.json"
    assert read_scoped_exclusions_exact(path, first.ledger_id) == first
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        read_scoped_exclusions_exact(path, first.ledger_id)
    with pytest.raises(ValueError):
        write_scoped_exclusions(tmp_path, "2010-01", (item,))


@pytest.mark.skipif(
    os.environ.get("V52_REAL_MONTH_INTEGRATION") != "1" or
    not (ROOT / "data/replay_status_authority/authority").is_dir(),
    reason="explicit real-month integration requires installed Phase 1 sources",
)
def test_real_2010_01_month_has_exact_partition_and_scoped_accounting(tmp_path):
    first = integrate_real_month(ROOT, tmp_path, "2010-01")
    second = integrate_real_month(ROOT, tmp_path, "2010-01")
    assert first == second
    assert first.month == "2010-01"
    assert first.materialized_rows > 0
    assert first.effective_anchors == (
        first.materialized_rows + first.excluded_before_label + first.scoped_excluded_anchors)
    assert first.partition_id and first.integration_id
    assert first.scoped_excluded_securities > 0
    assert sum(count for _, count in first.scoped_reason_counts) == first.scoped_excluded_anchors
    ledger_path = tmp_path / "scoped_exclusions" / f"{first.scoped_exclusion_hash}.json"
    ledger = read_scoped_exclusions_exact(ledger_path, first.scoped_exclusion_hash)
    assert len(ledger.rows) == first.scoped_excluded_anchors
