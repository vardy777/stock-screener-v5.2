from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DailyBarCompletenessAuditV1:
    requested: int
    applicable: int
    not_applicable: int
    observed: int
    missing: int
    coverage_ratio: float
    passed: bool


def audit_completeness(*, symbols, sessions, valid_intervals, observed_keys):
    requested = len(symbols) * len(sessions)
    applicable_keys = set()
    for symbol in symbols:
        start, end = valid_intervals[symbol]
        for session in sessions:
            if session >= start and (end is None or session <= end):
                applicable_keys.add((symbol, session))
    observed_applicable = applicable_keys & set(observed_keys)
    missing = len(applicable_keys - set(observed_keys))
    applicable = len(applicable_keys)
    return DailyBarCompletenessAuditV1(requested, applicable, requested - applicable, len(observed_applicable),
                                       missing, len(observed_applicable) / applicable if applicable else 0.0, missing == 0)
