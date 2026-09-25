"""Production CA lineage must pin both supported facts and unsupported events."""

from datetime import date
from pathlib import Path
import shutil

import pytest

from v5_2.labels.historical_ca_lineage import HistoricalCorporateActionLineageV1


ROOT = Path(__file__).resolve().parents[2] / "data/phase_1b2c"
pytestmark = pytest.mark.skipif(not ROOT.is_dir(), reason="exact Phase 1 CA source not installed")


def test_real_approved_ca_scope_keeps_unsupported_events_machine_visible():
    reader = HistoricalCorporateActionLineageV1.load_exact(ROOT)
    assert reader.fact_count == 39407
    assert reader.quarantine_count == 7899
    assert reader.supported_action_types == ("BONUS_SHARE", "CASH_DIVIDEND")
    assert reader.unsupported_action_types == ("RIGHTS_ISSUE", "SHARE_CONVERSION", "STOCK_SPLIT")
    quarantine = reader.first_quarantine
    day = date.fromisoformat(f"{quarantine['effective_date'][:4]}-{quarantine['effective_date'][4:6]}-{quarantine['effective_date'][6:]}")
    facts, coverage, lineage = reader.window(quarantine["security_identity"], (day,))
    assert coverage.quarantined
    assert lineage.domain == "corporate_action"
    assert quarantine["quarantine_id"] in lineage.evidence_ids
    assert all(fact.verify() for fact in facts)


def test_tampered_ca_quarantine_ledger_fails_closed(tmp_path):
    copied = tmp_path / "ca"
    (copied / "approved").mkdir(parents=True)
    (copied / "governance").mkdir()
    for relative in HistoricalCorporateActionLineageV1.required_paths():
        source = ROOT / relative
        destination = copied / relative
        shutil.copyfile(source, destination)
    audit = copied / HistoricalCorporateActionLineageV1.audit_path()
    audit.write_bytes(audit.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Audit"):
        HistoricalCorporateActionLineageV1.load_exact(copied)
