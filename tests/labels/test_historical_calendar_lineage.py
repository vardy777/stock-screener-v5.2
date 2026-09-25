"""The production calendar is the exact approved, ordered Phase 1 chain."""

from datetime import date
from pathlib import Path
import shutil

import pytest

from v5_2.labels.historical_calendar_lineage import HistoricalCalendarLineageV1


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (ROOT / "data/phase_1b1_2026_extension/governance/calendar-extension-3cd7c2f6fbdfcff34d739033d3ac789a7661903c1b32c4c626e24ebe0a1f047a.json").is_file(),
    reason="exact Phase 1 calendar extension not installed",
)


def test_real_calendar_exact_chain_and_h5_sessions():
    calendar = HistoricalCalendarLineageV1.load_exact(ROOT)
    sse = calendar.sessions("SSE")
    assert sse == tuple(sorted(set(sse)))
    assert date(2010, 1, 4) in sse
    assert date(2026, 6, 30) in sse
    assert calendar.window("SSE", date(2024, 1, 2))[:2] == (
        date(2024, 1, 2), date(2024, 1, 3))


def test_missing_or_tampered_extension_fails_closed(tmp_path):
    for relative in HistoricalCalendarLineageV1.required_paths():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    extension = tmp_path / HistoricalCalendarLineageV1.extension_path()
    extension.write_bytes(extension.read_bytes() + b" ")
    with pytest.raises(ValueError, match="calendar IncrementalCalendarExtension"):
        HistoricalCalendarLineageV1.load_exact(tmp_path)


def test_git_normalized_legacy_calendar_line_endings_keep_content_identity(tmp_path):
    for relative in HistoricalCalendarLineageV1.required_paths():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    for relative in (HistoricalCalendarLineageV1.required_paths()[0],
                     HistoricalCalendarLineageV1.required_paths()[2]):
        path = tmp_path / relative
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    assert HistoricalCalendarLineageV1.load_exact(tmp_path).window(
        "SZSE", date(2024, 1, 2))[0] == date(2024, 1, 2)
