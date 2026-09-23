from dataclasses import replace
import ast
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from v5_2.data.daily_bar_facts import DailyBarFactV1
from v5_2.data.historical_status_authority import (
    HistoricalStatusAuthorityError,
    HistoricalStatusAuthorityV1,
    HistoricalStatusComponentV1,
    HistoricalStatusResolverV1,
    HistoricalStatusShardStore,
)
from v5_2.labels.anchor_enumerator import (
    AnchorDispositionKind,
    AnchorDispositionV1,
    HistoricalAnchorLineageV1,
    IdentityIntervalV1,
    StatusObservationV1,
)
from v5_2.labels.calculation import CorporateActionCoverageV1
from v5_2.labels.contracts import (
    AnchorKnowledgeBoundary,
    DomainLineageV1,
    LabelState,
    ProvenancePath,
    REQUIRED_LABEL_DOMAINS,
)
from v5_2.labels.materializer import (
    HistoricalEvidenceWindowV1,
    HistoricalLabelEvidenceAssemblerV1,
    HistoricalStatusLineagePinsV1,
    materialize_anchor,
)


ZONE = timezone(timedelta(hours=8))
SESSIONS = tuple(date(2024, 1, day) for day in (2, 3, 4, 5, 8, 9))
IDS = tuple(f"{index:x}" * 64 for index in range(1, 16))


def bar(day: date, close: str) -> DailyBarFactV1:
    value = Decimal(close)
    return DailyBarFactV1.create(
        source_symbol="000001.SZ", session=day, open=value,
        high=value + 1, low=value - 1, close=value,
        raw_volume=Decimal("1"), raw_amount=Decimal("1"),
        source_payload_hash="p", available_at=datetime.combine(day, datetime.min.time(), ZONE),
        availability_policy_version="v1",
    )


def status_resolver(tmp_path, *, coverage_end=SESSIONS[-1]) -> HistoricalStatusResolverV1:
    lifecycle = HistoricalStatusComponentV1.create(
        component_kind="LIFECYCLE", canonical_security_identity="000001.SZ",
        effective_from=SESSIONS[0], effective_to=None, event_session=None,
        source_row_hash=IDS[0], availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
        availability_input_date=SESSIONS[0], source_fields={"list_date": "20240102"},
    )
    partial = HistoricalStatusComponentV1.create(
        component_kind="PARTIAL_SUSPENSION", canonical_security_identity="000001.SZ",
        effective_from=SESSIONS[0], effective_to=SESSIONS[0], event_session=SESSIONS[0],
        source_row_hash=IDS[14], availability_basis="MARKET_OBSERVABLE_BY_CLOSE",
        availability_input_date=SESSIONS[0], source_fields={"suspend_type": "S"},
    )
    store = HistoricalStatusShardStore(tmp_path)
    encoded = (
        store.encode("LIFECYCLE", (lifecycle,)),
        store.encode("PARTIAL_SUSPENSION", (partial,)),
    )
    authority = HistoricalStatusAuthorityV1.create(
        coverage_start=SESSIONS[0], coverage_end=coverage_end,
        parent_panel_id=IDS[1], parent_manifest_id=IDS[2], parent_approval_id=IDS[3],
        pit_evidence_id=IDS[4], source_version_identity=IDS[5],
        raw_payload_hashes=(IDS[6],), receipt_hashes=(IDS[7],),
        request_inventory_id=IDS[8], shard_descriptors=tuple(item.descriptor for item in encoded),
        authority_policy_version="historical-status-authority-v1",
    )
    return HistoricalStatusResolverV1(
        authority=authority, components=(lifecycle, partial), approved_sessions=SESSIONS,
        availability_policy_id=IDS[4], derived_approval_id=IDS[9],
        derived_manifest_id=IDS[10],
    )


def lineage() -> HistoricalAnchorLineageV1:
    return HistoricalAnchorLineageV1.create(
        calendar_approval_id=IDS[0], calendar_manifest_id=IDS[1],
        master_approval_id=IDS[2], master_manifest_id=IDS[3],
        status_approval_id=IDS[9], status_manifest_id=IDS[10],
        open_sessions=SESSIONS,
        identity_intervals=(IdentityIntervalV1("000001.SZ", "000001.SZ", "SZSE", SESSIONS[0], None),),
        status_observations=tuple(StatusObservationV1("000001.SZ", day, False) for day in SESSIONS),
    )


def anchor() -> AnchorDispositionV1:
    return AnchorDispositionV1(
        "000001.SZ", "000001.SZ", SESSIONS[0], "SZSE", True, False,
        AnchorDispositionKind.ELIGIBLE, None,
    )


def window() -> HistoricalEvidenceWindowV1:
    lineages = (
        DomainLineageV1.create(domain="trade_calendar", approval_id=IDS[0], manifest_id=IDS[1], fact_ids=(IDS[11],)),
        DomainLineageV1.create(domain="security_master", approval_id=IDS[2], manifest_id=IDS[3], fact_ids=(IDS[12],)),
        DomainLineageV1.create(domain="daily_bar", approval_id=IDS[6], manifest_id=IDS[7], fact_ids=(IDS[8],)),
        DomainLineageV1.create(domain="corporate_action", approval_id=IDS[13], manifest_id=IDS[14], evidence_ids=(IDS[5],), fact_ids=()),
    )
    return HistoricalEvidenceWindowV1.create(
        anchor_boundary=AnchorKnowledgeBoundary.create(
            SESSIONS[0], datetime(2024, 1, 2, 16, 30, tzinfo=ZONE), IDS[12], True,
        ),
        anchor_bar=bar(SESSIONS[0], "10"),
        future_bars=tuple(bar(day, str(10 + index)) for index, day in enumerate(SESSIONS[1:], 1)),
        non_status_lineage=lineages,
        corporate_actions=(), action_coverage=CorporateActionCoverageV1.safe(),
        dated_identity_map=(), delisting_session=None,
    )


def pins(resolver) -> HistoricalStatusLineagePinsV1:
    return HistoricalStatusLineagePinsV1.create(
        authority_id=resolver.authority.authority_id,
        approval_id=IDS[9], manifest_id=IDS[10], composition_id=IDS[11],
        coverage_ledger_id=IDS[12], replay_evidence_id=IDS[13],
        parent_panel_id=resolver.authority.parent_panel_id,
        parent_manifest_id=resolver.authority.parent_manifest_id,
        parent_approval_id=resolver.authority.parent_approval_id,
    )


def test_eligible_anchor_uses_historical_five_domain_bundle_and_frozen_engine(tmp_path):
    resolver = status_resolver(tmp_path)
    assembler = HistoricalLabelEvidenceAssemblerV1(resolver, pins(resolver))
    row = materialize_anchor(
        tmp_path, anchor(), lineage(), "phase2b-v1",
        assembler=assembler, evidence_window=window(), latest_completed_session=SESSIONS[-1],
    )

    assert row.provenance_path == ProvenancePath.HISTORICAL
    assert row.anchor_snapshot_id is None and row.outcome_snapshot_id is None
    assert len(row.domain_lineage_hashes) == 5
    assert all(value.state is LabelState.LABEL_AVAILABLE for value in row.values)
    assert row.verify()


def test_status_lineage_pins_each_derivation_and_complete_frozen_authority(tmp_path):
    resolver = status_resolver(tmp_path)
    assembler = HistoricalLabelEvidenceAssemblerV1(resolver, pins(resolver))
    bundle = assembler.assemble(
        anchor(), lineage(), window(), latest_completed_session=SESSIONS[-1],
    )
    status = bundle.domain_lineage[3]
    assert status.domain == "daily_security_status"
    assert len(status.fact_ids) == 5
    assert set((pins(resolver).authority_id, pins(resolver).composition_id,
                pins(resolver).coverage_ledger_id, pins(resolver).replay_evidence_id)).issubset(status.evidence_ids)
    assert tuple(item.domain for item in bundle.domain_lineage) == REQUIRED_LABEL_DOMAINS


def test_partial_maturation_requests_only_completed_status_sessions(tmp_path):
    resolver = status_resolver(tmp_path)
    assembler = HistoricalLabelEvidenceAssemblerV1(resolver, pins(resolver))
    bundle = assembler.assemble(
        anchor(), lineage(), window(), latest_completed_session=SESSIONS[1],
    )
    assert tuple(item.session for item in bundle.future_statuses) == (SESSIONS[1],)
    result = materialize_anchor(
        tmp_path, anchor(), lineage(), "phase2b-v1", assembler=assembler,
        evidence_window=window(), latest_completed_session=SESSIONS[1],
    )
    assert result.values[0].state is LabelState.LABEL_AVAILABLE
    assert all(value.state is LabelState.LABEL_PENDING for value in result.values[1:])


def test_revoked_tampered_or_post_coverage_status_fails_closed(tmp_path):
    resolver = status_resolver(tmp_path)
    assembler = HistoricalLabelEvidenceAssemblerV1(resolver, pins(resolver))
    revoked = replace(lineage(), revoked_approval_ids=(IDS[9],))
    with pytest.raises(ValueError, match="lineage"):
        assembler.assemble(anchor(), revoked, window(), latest_completed_session=SESSIONS[-1])
    with pytest.raises(ValueError, match="status lineage"):
        HistoricalLabelEvidenceAssemblerV1(resolver, replace(pins(resolver), authority_id=IDS[14]))
    narrow = status_resolver(tmp_path / "narrow", coverage_end=SESSIONS[-2])
    narrow_assembler = HistoricalLabelEvidenceAssemblerV1(narrow, pins(narrow))
    with pytest.raises(HistoricalStatusAuthorityError, match="coverage"):
        narrow_assembler.assemble(
            anchor(), lineage(), window(), latest_completed_session=SESSIONS[-1],
        )


def test_excluded_anchor_never_invokes_bundle_or_engine(tmp_path):
    excluded = replace(anchor(), disposition=AnchorDispositionKind.EXCLUDED_BEFORE_LABEL, reason="IPO_SEASONING")
    result = materialize_anchor(tmp_path, excluded, lineage(), "phase2b-v1")
    assert result.reason == "IPO_SEASONING"


def test_materializer_has_no_provider_or_network_dependency():
    module = Path(__file__).resolve().parents[2] / "src/v5_2/labels/materializer.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any("provider" in name or "integrations" in name for name in imports)
