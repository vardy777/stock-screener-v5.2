from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class StatusSampleCandidateV1:
    security_identity: str
    session: str
    stratum: str
    event_id: str
    later_delisted: bool

    @property
    def candidate_hash(self):
        return content_hash({"schema_version": "StatusSampleCandidateV1",
                             "security_identity": self.security_identity, "session": self.session,
                             "stratum": self.stratum, "event_id": self.event_id,
                             "later_delisted": self.later_delisted})


@dataclass(frozen=True, slots=True)
class StatusSampleInventoryV1:
    inventory_id: str
    samples: tuple[StatusSampleCandidateV1, ...]
    counts: tuple[tuple[str, int], ...]
    selection_policy_version: str
    content_hash: str


def select_status_samples(pools, *, identity_transition):
    requirements = {
        "ordinary": 30,
        "st_transition": 10,
        "suspension_transition": 10,
        "listing_delisting_boundary": 10,
    }
    selected = []
    for stratum in sorted(requirements):
        pool = tuple(pools.get(stratum, ()))
        count = requirements[stratum]
        if len(pool) < count or any(candidate.stratum != stratum for candidate in pool):
            raise ValueError(f"insufficient or invalid {stratum} sample pool")
        ordered = sorted(pool, key=lambda candidate: (not candidate.later_delisted, candidate.candidate_hash))
        selected.extend(ordered[:count])
    identity, session, event_id = identity_transition
    selected.append(StatusSampleCandidateV1(identity, session, "identity_transition", event_id, False))
    counts = tuple(sorted(requirements.items()))
    values = {"samples": tuple(selected), "counts": counts,
              "selection_policy_version": "status-sample-hash-v1"}
    digest = content_hash({"schema_version": "StatusSampleInventoryV1", **values})
    return StatusSampleInventoryV1(inventory_id=digest, content_hash=digest, **values)
