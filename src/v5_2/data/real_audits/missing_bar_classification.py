from __future__ import annotations

from dataclasses import dataclass

from v5_2.data.identity import content_hash


@dataclass(frozen=True, slots=True)
class MissingBarClassificationItemV1:
    security_identity: str
    session: str
    category: str
    item_hash: str

    @property
    def key(self):
        return self.security_identity, self.session


@dataclass(frozen=True, slots=True)
class MissingBarClassificationArtifactV1:
    items: tuple[MissingBarClassificationItemV1, ...]
    counts: tuple[tuple[str, int], ...]
    total: int
    policy_version: str
    content_hash: str


def classify_missing_bar_keys(
    missing_keys,
    *,
    full_day_suspensions,
    partial_suspensions,
    resume_observations,
    local_exception_keys,
    expected_total=None,
):
    supplied = tuple(missing_keys)
    keys = tuple(sorted(set(supplied)))
    if len(keys) != len(supplied):
        raise ValueError("missing keys must be unique")
    if expected_total is not None and len(keys) != expected_total:
        raise ValueError(f"missing-key total must equal {expected_total}")
    items = []
    counts = {}
    for identity, session in keys:
        key = identity, session
        if key in full_day_suspensions:
            category = "FULL_DAY_SUSPENSION"
        elif key in partial_suspensions or key in resume_observations:
            category = "PARTIAL_SUSPENSION_CONTRADICTION"
        elif key in local_exception_keys:
            category = "LOCAL_EXCEPTION"
        else:
            category = "UNEXPLAINED"
        body = {"schema_version": "MissingBarClassificationItemV1",
                "security_identity": identity, "session": session, "category": category}
        items.append(MissingBarClassificationItemV1(identity, session, category, content_hash(body)))
        counts[category] = counts.get(category, 0) + 1
    policy_version = "phase-1b2a-missing-bar-classification-v1"
    ordered_counts = tuple(sorted(counts.items()))
    digest = content_hash({"schema_version": "MissingBarClassificationArtifactV1",
                           "item_hashes": tuple(item.item_hash for item in items),
                           "counts": ordered_counts, "total": len(items),
                           "policy_version": policy_version})
    return MissingBarClassificationArtifactV1(tuple(items), ordered_counts, len(items), policy_version, digest)
