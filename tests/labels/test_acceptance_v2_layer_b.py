import json
from pathlib import Path

import pytest

from v5_2.labels.acceptance_v2_boundaries import build_fail_closed_boundary_ledger
from v5_2.labels.acceptance_v2_contracts import build_frozen_amendment_v2


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_ID = "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c"
pytestmark = pytest.mark.skipif(not (ROOT / "data/phase_1b2c/governance").is_dir(), reason="immutable evidence excluded")
EXPECTED = (
    "UNEXPLAINED_MISSING_BAR", "UNSUPPORTED_CA", "REVOKED_APPROVAL",
    "TAMPERED_ARTIFACT", "MISSING_REQUIRED_DOMAIN", "AMBIGUOUS_IDENTITY",
    "MALFORMED_CALENDAR", "INVALID_LINEAGE", "ROLE_SWAP", "DUPLICATE_DOMAIN",
)


def test_layer_b_contains_exact_ten_fail_closed_cases_with_zero_engine_calls():
    manifest = json.loads((ROOT / f"data/phase_1b2c/governance/corporate-action-manifest-{MANIFEST_ID}.json").read_text())
    ledger = build_fail_closed_boundary_ledger(ROOT, build_frozen_amendment_v2(), manifest)
    assert ledger.verify()
    assert tuple(x.semantic_category for x in ledger.cases) == EXPECTED
    assert all(x.observed_rejection_code == x.expected_rejection_code for x in ledger.cases)
    assert all(x.engine_invocation_count == 0 for x in ledger.cases)
    assert all(x.input_evidence_ids for x in ledger.cases)
    assert ledger.cases[0].assembler_invocation_count == 1
    assert ledger.cases[1].assembler_invocation_count == 0
