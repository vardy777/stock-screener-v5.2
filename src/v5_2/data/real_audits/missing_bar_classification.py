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


@dataclass(frozen=True, slots=True)
class MissingBarClassificationArtifactV2:
    items: tuple[MissingBarClassificationItemV1, ...]
    counts: tuple[tuple[str, int], ...]
    total: int
    supersedes_classification_id: str
    quarantine_audit_id: str
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
    counts = {category: 0 for category in (
        "SUSPENDED", "NOT_YET_LISTED", "DELISTED", "IDENTITY_NOT_APPLICABLE",
        "OTHER_LEGITIMATE", "LOCAL_EXCEPTION", "UNEXPLAINED",
    )}
    for identity, session in keys:
        key = identity, session
        if key in full_day_suspensions:
            category = "SUSPENDED"
        elif key in partial_suspensions or key in resume_observations:
            category = "UNEXPLAINED"
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


def quarantine_local_exceptions(original: MissingBarClassificationArtifactV1, exception_record_ids, quarantine_audit_id: str):
    unknown = set(exception_record_ids) - {item.key for item in original.items}
    if unknown:
        raise ValueError("exception key is outside frozen missing-bar inventory")
    items = []
    for item in original.items:
        category = "LOCAL_EXCEPTION" if item.key in exception_record_ids else item.category
        body = {"schema_version": "MissingBarClassificationItemV2", "security_identity": item.security_identity,
                "session": item.session, "category": category,
                "quarantine_record_id": exception_record_ids.get(item.key)}
        items.append(MissingBarClassificationItemV1(item.security_identity, item.session, category, content_hash(body)))
    counts = tuple(sorted((key, sum(item.category == key for item in items)) for key, _ in original.counts))
    policy_version = "phase-1b2a-missing-bar-classification-v2"
    body = {"schema_version": "MissingBarClassificationArtifactV2", "item_hashes": tuple(item.item_hash for item in items),
            "counts": counts, "total": len(items), "supersedes_classification_id": original.content_hash,
            "quarantine_audit_id": quarantine_audit_id, "policy_version": policy_version}
    return MissingBarClassificationArtifactV2(tuple(items), counts, len(items), original.content_hash,
                                               quarantine_audit_id, policy_version, content_hash(body))
