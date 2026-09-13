from datetime import date

import pytest

from v5_2.data.historical_lineage import HistoricalDatasetCompositionV1, LineageCompositionError


def test_adjacent_base_and_extension_compose_deterministically():
    kwargs = dict(dataset_kind="trade_calendar", base_manifest_id="base",
        extension_manifest_id="extension", base_coverage=(date(2010, 1, 4), date(2025, 12, 31)),
        extension_coverage=(date(2026, 1, 1), date(2026, 9, 11)),
        base_fact_bundle_id="facts", composition_rule="ADJACENT_UNION_V1")
    first = HistoricalDatasetCompositionV1.create(**kwargs)
    second = HistoricalDatasetCompositionV1.create(**kwargs)
    assert first == second and first.verify()
    assert first.coverage_start == date(2010, 1, 4)
    assert first.coverage_end == date(2026, 9, 11)


def test_gap_or_overlap_fails_closed():
    common = dict(dataset_kind="security_master", base_manifest_id="base",
        extension_manifest_id="extension", base_coverage=(date(2010, 1, 4), date(2025, 12, 31)),
        base_fact_bundle_id="facts", composition_rule="ADJACENT_UNION_V1")
    with pytest.raises(LineageCompositionError, match="gap"):
        HistoricalDatasetCompositionV1.create(**common,
            extension_coverage=(date(2026, 1, 2), date(2026, 9, 10)))
    with pytest.raises(LineageCompositionError, match="overlap"):
        HistoricalDatasetCompositionV1.create(**common,
            extension_coverage=(date(2025, 12, 31), date(2026, 9, 10)))


def test_composition_requires_immutable_manifest_and_fact_ids():
    with pytest.raises(LineageCompositionError, match="lineage"):
        HistoricalDatasetCompositionV1.create(dataset_kind="trade_calendar",
            base_manifest_id="", extension_manifest_id="extension",
            base_coverage=(date(2010, 1, 4), date(2025, 12, 31)),
            extension_coverage=(date(2026, 1, 1), date(2026, 9, 11)),
            base_fact_bundle_id="facts", composition_rule="ADJACENT_UNION_V1")
