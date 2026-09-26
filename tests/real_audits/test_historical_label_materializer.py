from datetime import date
import json
from pathlib import Path

import pytest

from v5_2.data.historical_status_authority import load_portable_status_resolver
from v5_2.data.label_evidence_assembler import Phase2AEvidenceAssemblerV1
from v5_2.labels.acceptance import build_frozen_inventory
from v5_2.labels.anchor_enumerator import (
    AnchorDispositionKind,
    AnchorDispositionV1,
    HistoricalAnchorLineageV1,
    IdentityIntervalV1,
    StatusObservationV1,
)
from v5_2.labels.engine import ReferenceLabelEngine
from v5_2.labels.materializer import (
    HistoricalEvidenceWindowV1,
    HistoricalLabelEvidenceAssemblerV1,
    HistoricalStatusLineagePinsV1,
)


ROOT = Path(__file__).resolve().parents[2]
PORTABLE = ROOT / "data/replay_status_authority"
AUTHORITY = "d6f7f5517428891db66da60565baaea5828d7adcaf29c820d5fa746ddf29e59b"
LEDGER = "b214cc728c867c7b5bdbef5e6b37cea25afa67650522d5aee800cd95f56237cb"
APPROVAL = "9353de33e62405830a7dbef13e53836a969fb569f9e7d5370a67d5df9078fa95"
MANIFEST = "0c86954cffaae2ca09ff1efcd4b32d990a9cf3d2b82d520a64172a1875d457a8"
COMPOSITION = "e4110ec6185731d9a2d80e151d79f82006e07e779c10a90a4b4c2e228a35e139"
REPLAY = "235f86dd7269768382c67620cd723d27347c7f99e386488efc9b93665a517baf"


pytestmark = pytest.mark.skipif(
    not (PORTABLE / "authority" / f"historical-status-authority-{AUTHORITY}.json").is_file()
    or not (ROOT / "data/phase_2a/governance").is_dir(),
    reason="repository-local immutable acceptance evidence is excluded from clean room",
)


def approved_sessions() -> tuple[date, ...]:
    base = json.loads((ROOT / "data/phase_1b1/governance/daily-bar-universe-2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01.json").read_text(encoding="utf-8"))
    sessions = set(base["ordered_sessions"])
    extension = json.loads((ROOT / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json").read_text(encoding="utf-8"))
    sessions.update(row[1] for row in extension["ordered_rows"] if row[2] == 1)
    return tuple(date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:]}") for value in sorted(sessions))


def test_real_layer_a_case_is_semantically_equivalent_with_portable_status_lineage():
    slot = build_frozen_inventory().slots[0]
    acceptance_assembler = Phase2AEvidenceAssemblerV1(ROOT)
    source = acceptance_assembler.assemble(slot)
    sessions = approved_sessions()
    resolver = load_portable_status_resolver(
        portable_root=PORTABLE, expected_authority_id=AUTHORITY,
        expected_derived_approval_id=APPROVAL, expected_derived_manifest_id=MANIFEST,
        expected_composition_id=COMPOSITION, expected_replay_evidence_id=REPLAY,
        approved_sessions=sessions, revoked_approval_ids=(),
    )
    pins = HistoricalStatusLineagePinsV1.create(
        authority_id=AUTHORITY, approval_id=APPROVAL, manifest_id=MANIFEST,
        composition_id=COMPOSITION, coverage_ledger_id=LEDGER,
        replay_evidence_id=REPLAY,
        parent_panel_id=resolver.authority.parent_panel_id,
        parent_manifest_id=resolver.authority.parent_manifest_id,
        parent_approval_id=resolver.authority.parent_approval_id,
    )
    anchor = AnchorDispositionV1(
        source.canonical_security_identity, source.canonical_security_identity,
        source.anchor_session, "SZSE", True, False,
        AnchorDispositionKind.ELIGIBLE, None,
    )
    lineage = HistoricalAnchorLineageV1.create(
        calendar_approval_id=source.domain_lineage[0].approval_id,
        calendar_manifest_id=source.domain_lineage[0].manifest_id,
        master_approval_id=source.domain_lineage[1].approval_id,
        master_manifest_id=source.domain_lineage[1].manifest_id,
        status_approval_id=APPROVAL, status_manifest_id=MANIFEST,
        open_sessions=sessions,
        identity_intervals=(IdentityIntervalV1(
            source.canonical_security_identity, source.canonical_security_identity,
            "SZSE", date(1990, 1, 1), None,
        ),),
        status_observations=tuple(StatusObservationV1(
            source.canonical_security_identity, day, False,
        ) for day in sessions),
    )
    window = HistoricalEvidenceWindowV1.create(
        anchor_boundary=source.anchor_boundary, anchor_bar=None if source.reference_price is None else next(
            item for item in acceptance_assembler._bars(
                slot, acceptance_assembler._entries[slot.slot].candidate_artifacts_found,
            ).values() if item.session == source.anchor_session
        ),
        future_bars=source.future_bars,
        non_status_lineage=(source.domain_lineage[0], source.domain_lineage[1], source.domain_lineage[2], source.domain_lineage[4]),
        corporate_actions=source.corporate_actions,
        action_coverage=source.action_coverage,
        dated_identity_map=source.dated_identity_map,
        delisting_session=source.delisting_session,
    )
    rebuilt = HistoricalLabelEvidenceAssemblerV1(resolver, pins).assemble(
        anchor, lineage, window, latest_completed_session=source.latest_completed_session,
    )
    expected = ReferenceLabelEngine().evaluate(source)
    actual = ReferenceLabelEngine().evaluate(rebuilt)

    assert tuple((item.state, item.value, item.reason_code) for item in actual.values) == tuple(
        (item.state, item.value, item.reason_code) for item in expected.values
    )
    assert rebuilt.domain_lineage[3].approval_id == APPROVAL
    assert LEDGER in rebuilt.domain_lineage[3].evidence_ids
