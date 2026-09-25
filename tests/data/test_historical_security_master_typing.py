"""Frozen Master provenance type correction; no business-fact mutation."""

from __future__ import annotations

import pytest

from v5_2.data.identity import content_hash
from v5_2.data.historical_security_master_authority import (
    HistoricalMasterTypingError,
    type_historical_master_bundle,
)


GRAPH = "6275f4df087e40a11eb12b4ece0e569865814002d4da301342c2279af98acda0"
SUPPLEMENT = "d67d886299be85bb5585c9103140ef327fe13b78161903f7e5120646a8ee9e8f"
APPROVAL = "a14be1c8443902fd3c28fd9ec43243710d124ba5c498cf760c9fe4396f11189f"


def artifact(schema: str, id_field: str, **fields):
    body = {"schema_version": schema, **fields}
    digest = content_hash(body)
    return {**body, id_field: digest, "content_hash": digest}


def provenance():
    old = artifact(
        "HistoricalSecurityMasterFactBundleV1", "fact_bundle_id",
        coverage_start="2010-01-01", coverage_end="2025-12-31",
        ordered_security_identities=["302132.SZ", "T600018.SH"],
        effective_identity_graph_ids=[GRAPH, SUPPLEMENT],
        source_payload_hashes=["raw-a"], current_snapshot_backfill=False,
    )
    child_body = dict(
        security_identity="600747.SH", effective_from="19960916",
        effective_to="20191212", official_evidence_ids=["https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20191018_4929400.shtml"],
        reason="historical eligible A-share omitted from frozen universe",
    )
    child = {**child_body, "content_hash": content_hash({"schema_version": "HistoricalUniverseSupplementIdentityV1", **child_body})}
    supplement = {"original_universe_id": "2456669d1158c8efec6e3204082ce67ca87646236120316307822f9e0f19ad01", "identities": [child]}
    supplement["content_hash"] = content_hash({"schema_version": "HistoricalUniverseSupplementV1",
        "original_universe_id": supplement["original_universe_id"], "identity_hashes": [child["content_hash"]]})
    graph = artifact(
        "EffectiveDatedSecurityIdentityV1", "graph_id",
        provider_identity="302132.SZ", intervals=[
            {"identity": "300114.SZ", "effective_from": "2010-08-27", "effective_to": "2025-02-16", "security_type": "A_SHARE", "board": "CHINEXT"},
            {"identity": "302132.SZ", "effective_from": "2025-02-17", "effective_to": None, "security_type": "A_SHARE", "board": "CHINEXT"},
        ], transition_event="SECURITY_CODE_CHANGE", transition_effective_at="2025-02-17",
        evidence_ids=["szse-code-change-2025-302132", "szse-listing-2010-300114"],
        policy_version="effective-identity-v1",
    )
    graph.pop("schema_version")
    ratification = artifact(
        "SecurityIdentityGraphRatificationEvidenceV1", "evidence_id",
        graph_id=GRAPH, graph_body_hash=GRAPH,
        official_evidence_ids=["94ed51b460193c837d81ab6e916276accf15fdf4846c89b4d72621251a02c630", "16a3644f36adc46af76e1e016b049bc5fc60502979b8399cf4a317eb87090398"],
        expected_predecessor="300114.SZ", expected_successor="302132.SZ",
        expected_original_listing_date="2010-08-27", expected_transition_date="2025-02-17",
        expected_transition_event="SECURITY_CODE_CHANGE", verified_at="2026-09-25T08:33:48+00:00",
        decision="PASS", policy_version="security-identity-graph-ratification-v1",
    )
    ratification.pop("schema_version")
    approval = artifact(
        "SecurityIdentityGraphApprovalV1", "approval_id",
        scope="EXISTING_GRAPH_RATIFICATION", graph_id=GRAPH,
        ratification_evidence_id=ratification["evidence_id"],
        official_evidence_ids=["94ed51b460193c837d81ab6e916276accf15fdf4846c89b4d72621251a02c630", "16a3644f36adc46af76e1e016b049bc5fc60502979b8399cf4a317eb87090398"],
        verified_at="2026-09-25T08:33:48+00:00", decision="APPROVED",
        policy_version="security-identity-graph-ratification-v1",
    )
    approval.pop("schema_version")
    assert graph["graph_id"] == GRAPH
    assert supplement["content_hash"] == SUPPLEMENT
    return old, graph, ratification, approval, supplement


def test_typing_bridge_separates_graph_from_historical_universe_supplement():
    old, graph, ratification, approval, supplement = provenance()
    bridge = type_historical_master_bundle(old, graph, ratification, approval, supplement)
    assert bridge.old_bundle_id == old["fact_bundle_id"]
    assert bridge.effective_identity_graph_ids == (GRAPH,)
    assert bridge.historical_universe_supplement_ids == (supplement["content_hash"],)
    assert bridge.graph_approval_id == approval["approval_id"]
    assert bridge.defect == "PROVENANCE_TYPE_MISCLASSIFICATION"
    assert not bridge.business_truth_changed
    assert not bridge.identity_semantics_changed
    assert not bridge.universe_membership_changed
    assert old["effective_identity_graph_ids"] == [GRAPH, SUPPLEMENT]


@pytest.mark.parametrize("mutation", ["supplement_as_graph", "tampered_graph", "wrong_approval", "tampered_supplement"])
def test_typing_bridge_fails_closed_on_wrong_artifact_type_or_provenance(mutation):
    values = list(provenance())
    if mutation == "supplement_as_graph":
        values[0]["effective_identity_graph_ids"] = [SUPPLEMENT, GRAPH]
    elif mutation == "tampered_graph":
        values[1]["intervals"][0]["effective_from"] = "2010-08-28"
    elif mutation == "wrong_approval":
        values[3]["decision"] = "PENDING"
    else:
        values[4]["identities"][0]["effective_to"] = "20191213"
    with pytest.raises(HistoricalMasterTypingError):
        type_historical_master_bundle(*values)
