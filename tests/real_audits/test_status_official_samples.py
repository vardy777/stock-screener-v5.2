from v5_2.data.real_audits.status_official_samples import build_official_sample_ledger


def test_ledger_preserves_every_frozen_entry_including_duplicate_event_ids() -> None:
    samples = ({"event_id": "same", "security_identity": "600001.SH", "session": "20250102", "stratum": "ordinary"},) * 2
    ledger = build_official_sample_ledger("inventory", samples, {})
    assert len(ledger.entries) == 2
    assert len({entry.sample_id for entry in ledger.entries}) == 2
    assert ledger.unique_event_count == 1
    assert ledger.counts == (("UNRESOLVED", 2),)


def test_missing_retrieval_is_unresolved_and_never_promoted_to_match() -> None:
    samples = ({"event_id": "e", "security_identity": "000001.SZ", "session": "20250102", "stratum": "ordinary"},)
    ledger = build_official_sample_ledger("inventory", samples, {})
    assert ledger.entries[0].resolution == "UNRESOLVED"
    assert ledger.systematic_defect is False


def test_stratum_label_does_not_override_explicit_provider_and_independent_values() -> None:
    sample = ({"event_id": "e", "security_identity": "300029.SZ", "session": "20250102", "stratum": "ordinary"},)
    evidence = {"e": {"resolution": "MATCH", "provider_observation": "stock-st: ST",
        "observation": "BaoStock isST=1", "evidence_id": "independent", "semantic_mapping": "daily ST state agrees"}}
    entry = build_official_sample_ledger("inventory", sample, evidence).entries[0]
    assert entry.provider_observation == "stock-st: ST"
    assert entry.resolution == "MATCH"
