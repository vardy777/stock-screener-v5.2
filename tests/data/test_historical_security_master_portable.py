"""Exact portable Master publication and security-scoped reader boundary."""

from __future__ import annotations

from datetime import date

import pytest

from v5_2.data.historical_security_master_authority import (
    HistoricalMasterTypingError,
    HistoricalSecurityMasterReaderV1,
    publish_portable_master,
)
from test_historical_security_master_derivation import derive_master_intervals, graph, page, row


def publication(tmp_path):
    source = page(row("000001.SZ", list_date="19910403"),
                  row("T600018.SH", list_date="20000719", delist_date="20061020", market=""))
    derived = derive_master_intervals(
        membership=("000001.SZ", "T600018.SH"), pages=(source,),
        expected_payload_hashes=(source.payload_hash,), graph=graph(),
        graph_approval_id="a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f",
    )
    return publish_portable_master(
        root=tmp_path, derived=derived,
        parent_manifest_id="1" * 64, parent_approval_id="2" * 64,
        parent_complete_bundle_id="3" * 64, typing_bridge_id="4" * 64,
        raw_payload_hashes=(source.payload_hash,), replay_evidence_id="6" * 64,
        source_corpus_inventory_id="7" * 64,
    )


def test_exact_reader_resolves_ordinary_interval_and_quarantines_one_member(tmp_path):
    first = publication(tmp_path)
    second = publication(tmp_path)
    assert first == second
    reader = HistoricalSecurityMasterReaderV1.load_exact(
        tmp_path, authority_id=first.authority_id, approval_id=first.approval_id,
        manifest_id=first.manifest_id, coverage_ledger_id=first.coverage_ledger_id,
        revoked_approval_ids=(),
    )
    proof = reader.resolve("000001.SZ", date(2012, 6, 29))
    assert proof.effective_identity == "000001.SZ"
    assert proof.authority_id == first.authority_id
    assert proof.approval_id == first.approval_id
    assert proof.manifest_id == first.manifest_id
    assert proof.coverage_ledger_id == first.coverage_ledger_id
    assert proof.fact_id == reader.facts[0].fact_id
    with pytest.raises(HistoricalMasterTypingError, match="scoped quarantine"):
        reader.resolve("T600018.SH", date(2005, 1, 3))
    with pytest.raises(HistoricalMasterTypingError, match="not effective"):
        reader.resolve("000001.SZ", date(1990, 1, 1))


def test_tampered_fact_and_revoked_approval_fail_closed(tmp_path):
    published = publication(tmp_path)
    with pytest.raises(HistoricalMasterTypingError, match="revoked"):
        HistoricalSecurityMasterReaderV1.load_exact(
            tmp_path, authority_id=published.authority_id, approval_id=published.approval_id,
            manifest_id=published.manifest_id, coverage_ledger_id=published.coverage_ledger_id,
            revoked_approval_ids=(published.approval_id,),
        )
    path = tmp_path / "facts" / f"master-intervals-{published.facts_storage_sha256}.jsonl"
    path.write_bytes(path.read_bytes().replace(b"000001.SZ", b"000009.SZ"))
    with pytest.raises(HistoricalMasterTypingError, match="fact storage"):
        HistoricalSecurityMasterReaderV1.load_exact(
            tmp_path, authority_id=published.authority_id, approval_id=published.approval_id,
            manifest_id=published.manifest_id, coverage_ledger_id=published.coverage_ledger_id,
            revoked_approval_ids=(),
        )
