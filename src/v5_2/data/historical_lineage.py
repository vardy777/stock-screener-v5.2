from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from v5_2.data.identity import content_hash


class LineageCompositionError(ValueError):
    """Historical base and extension cannot form one complete lineage."""


@dataclass(frozen=True, slots=True)
class HistoricalDatasetCompositionV1:
    dataset_kind: str
    base_manifest_id: str
    extension_manifest_id: str
    base_fact_bundle_id: str
    base_coverage_start: date
    base_coverage_end: date
    extension_coverage_start: date
    extension_coverage_end: date
    coverage_start: date
    coverage_end: date
    composition_rule: str
    overlap_check: str
    gap_check: str
    composition_id: str
    content_hash: str

    @classmethod
    def create(cls, *, dataset_kind: str, base_manifest_id: str,
               extension_manifest_id: str, base_fact_bundle_id: str,
               base_coverage: tuple[date, date], extension_coverage: tuple[date, date],
               composition_rule: str):
        if not all((dataset_kind, base_manifest_id, extension_manifest_id,
                    base_fact_bundle_id, composition_rule)):
            raise LineageCompositionError("immutable lineage identifiers are required")
        base_start, base_end = base_coverage
        extension_start, extension_end = extension_coverage
        if base_end >= extension_start:
            raise LineageCompositionError("base and extension overlap")
        if extension_start != base_end + timedelta(days=1):
            raise LineageCompositionError("base and extension have a coverage gap")
        if base_end < base_start or extension_end < extension_start:
            raise LineageCompositionError("coverage interval is invalid")
        values = {"dataset_kind": dataset_kind, "base_manifest_id": base_manifest_id,
            "extension_manifest_id": extension_manifest_id,
            "base_fact_bundle_id": base_fact_bundle_id,
            "base_coverage_start": base_start, "base_coverage_end": base_end,
            "extension_coverage_start": extension_start, "extension_coverage_end": extension_end,
            "coverage_start": base_start, "coverage_end": extension_end,
            "composition_rule": composition_rule, "overlap_check": "PASS", "gap_check": "PASS"}
        digest = content_hash({"schema_version": "HistoricalDatasetCompositionV1", **values})
        return cls(**values, composition_id=digest, content_hash=digest)

    def verify(self) -> bool:
        values = {"dataset_kind": self.dataset_kind, "base_manifest_id": self.base_manifest_id,
            "extension_manifest_id": self.extension_manifest_id,
            "base_fact_bundle_id": self.base_fact_bundle_id,
            "base_coverage_start": self.base_coverage_start, "base_coverage_end": self.base_coverage_end,
            "extension_coverage_start": self.extension_coverage_start,
            "extension_coverage_end": self.extension_coverage_end,
            "coverage_start": self.coverage_start, "coverage_end": self.coverage_end,
            "composition_rule": self.composition_rule, "overlap_check": self.overlap_check,
            "gap_check": self.gap_check}
        return self.composition_id == self.content_hash == content_hash(
            {"schema_version": "HistoricalDatasetCompositionV1", **values})
