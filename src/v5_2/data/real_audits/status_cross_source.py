from __future__ import annotations


def resolve_cross_source(semantic: str, *, daily_matches: bool | None,
                         official_anchor_matches: bool) -> str:
    if daily_matches is False:
        return "MISMATCH"
    if daily_matches is None:
        return "INDEPENDENT_EVIDENCE_UNAVAILABLE"
    if semantic in {"ACTUAL_FIRST_TRADABLE_SESSION", "DELISTING_BOUNDARY"}:
        return "MATCH" if official_anchor_matches else "INDEPENDENT_EVIDENCE_UNAVAILABLE"
    return "MATCH"
