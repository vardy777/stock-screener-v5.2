from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class StatusValidationResultV1:
    structural_status: str
    pit_status: str
    cross_source_status: str
    survivorship_status: str
    decision: str
    namechange_row_count: int
    suspension_row_count: int
    observed_symbol_count: int
    unknown_symbol_count: int
    invalid_row_count: int
    official_sample_count: int
    official_mismatch_count: int


def _valid_date(value: object) -> bool:
    text = str(value)
    return len(text) == 8 and text.isdigit()


def validate_status_observations(
    *,
    namechange_rows: Sequence[Mapping[str, object]],
    suspension_rows: Sequence[Mapping[str, object]],
    universe_symbols: Sequence[str],
    coverage_start: str,
    coverage_end: str,
    later_delisted_symbols: Sequence[str],
    official_sample_matches: Sequence[bool],
) -> StatusValidationResultV1:
    invalid = 0
    for row in namechange_rows:
        if not {"ts_code", "ann_date", "start_date"}.issubset(row):
            invalid += 1
        elif not _valid_date(row["ann_date"]) or not _valid_date(row["start_date"]):
            invalid += 1
        elif not coverage_start <= str(row["ann_date"]) <= coverage_end:
            invalid += 1
    for row in suspension_rows:
        if not {"ts_code", "trade_date", "suspend_type"}.issubset(row):
            invalid += 1
        elif not _valid_date(row["trade_date"]):
            invalid += 1
        elif not coverage_start <= str(row["trade_date"]) <= coverage_end:
            invalid += 1
        elif row["suspend_type"] not in {"S", "R"}:
            invalid += 1

    observed = {str(row.get("ts_code")) for row in (*namechange_rows, *suspension_rows)}
    universe = set(universe_symbols)
    delisted = set(later_delisted_symbols)
    survivorship_status = "PASS" if delisted.issubset(universe) else "FAIL"
    sample_count = len(official_sample_matches)
    mismatches = sum(not match for match in official_sample_matches)
    if sample_count == 0:
        cross_source_status = "PENDING"
    elif sample_count >= 10 and mismatches / sample_count > 0.2:
        cross_source_status = "FAIL"
    else:
        cross_source_status = "PASS" if mismatches == 0 else "PENDING"

    structural_status = "PASS" if invalid == 0 else "FAIL"
    # Both provider datasets expose dates, not verified publication timestamps.
    # They therefore cannot establish same-date D-close knowledge by themselves.
    pit_status = "FAIL"
    decision = (
        "REJECTED"
        if structural_status == "FAIL" or cross_source_status == "FAIL"
        else "INSUFFICIENT_EVIDENCE"
    )
    return StatusValidationResultV1(
        structural_status=structural_status,
        pit_status=pit_status,
        cross_source_status=cross_source_status,
        survivorship_status=survivorship_status,
        decision=decision,
        namechange_row_count=len(namechange_rows),
        suspension_row_count=len(suspension_rows),
        observed_symbol_count=len(observed),
        unknown_symbol_count=len(observed - universe),
        invalid_row_count=invalid,
        official_sample_count=sample_count,
        official_mismatch_count=mismatches,
    )
