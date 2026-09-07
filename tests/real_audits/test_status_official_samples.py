from v5_2.data.real_audits.status_official_samples import build_official_sample_ledger


def test_ledger_preserves_every_frozen_entry_including_duplicate_event_ids() -> None:
    samples = ({"event_id": "same", "security_identity": "600001.SH", "session": "20250102", "stratum": "ordinary"},) * 2
    ledger = build_official_sample_ledger("inventory", samples, {})
    assert len(ledger.entries) == 2
    assert len({entry.sample_id for entry in ledger.entries}) == 2
    assert ledger.unique_event_count == 1
    assert ledger.counts == (("OFFICIAL_REFERENCE_UNAVAILABLE", 2),)


def test_unavailable_is_never_promoted_to_match() -> None:
    samples = ({"event_id": "e", "security_identity": "000001.SZ", "session": "20250102", "stratum": "ordinary"},)
    ledger = build_official_sample_ledger("inventory", samples, {})
    assert ledger.entries[0].resolution == "OFFICIAL_REFERENCE_UNAVAILABLE"
    assert ledger.systematic_defect is False
