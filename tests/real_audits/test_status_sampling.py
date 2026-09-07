from v5_2.data.real_audits.status_sampling import StatusSampleCandidateV1, select_status_samples


def candidates(stratum, count, *, later_delisted=False):
    return tuple(
        StatusSampleCandidateV1(
            security_identity=f"{i:06d}.SZ", session=f"2025{i % 12 + 1:02d}02",
            stratum=stratum, event_id=f"{stratum}-{i}", later_delisted=later_delisted and i == 0,
        )
        for i in range(count)
    )


def test_status_sample_inventory_has_exact_frozen_strata_and_is_deterministic() -> None:
    pools = {
        "ordinary": candidates("ordinary", 40, later_delisted=True),
        "st_transition": candidates("st_transition", 15),
        "suspension_transition": candidates("suspension_transition", 15),
        "listing_delisting_boundary": candidates("listing_delisting_boundary", 15, later_delisted=True),
    }
    first = select_status_samples(pools, identity_transition=("302132.SZ", "20250217", "identity-event"))
    second = select_status_samples(pools, identity_transition=("302132.SZ", "20250217", "identity-event"))
    assert first.inventory_id == second.inventory_id
    assert first.counts == (("listing_delisting_boundary", 10), ("ordinary", 30),
                            ("st_transition", 10), ("suspension_transition", 10))
    assert len(first.samples) == 61
    assert any(sample.later_delisted for sample in first.samples)
    assert first.samples[-1].stratum == "identity_transition"


def test_current_membership_is_not_a_sampling_input() -> None:
    pools = {
        "ordinary": candidates("ordinary", 30, later_delisted=True),
        "st_transition": candidates("st_transition", 10),
        "suspension_transition": candidates("suspension_transition", 10),
        "listing_delisting_boundary": candidates("listing_delisting_boundary", 10, later_delisted=True),
    }
    selected = select_status_samples(pools, identity_transition=("302132.SZ", "20250217", "identity-event"))
    assert any(sample.later_delisted for sample in selected.samples)
