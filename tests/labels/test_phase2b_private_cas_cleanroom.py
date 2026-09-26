"""Explicit fresh-checkout replay; never runs in the ordinary unit suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from v5_2.data.private_cas import resolve_cas_root
from v5_2.data.private_corpus_manifest import read_manifest_exact
from v5_2.data.private_corpus_resolver import (
    assert_private_objects_untracked,
    stage_verified_private_corpus,
)
from v5_2.labels.historical_month_integration import integrate_real_month


MANIFEST_ID = "0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6"
PARTITION_ID = "3c194baf309486c16dd8f7f9e1916f4a1a4af49c9b108bcc06ce693eee615ba9"
COVERAGE_HASH = "b6108848b3cd469f37f1baaa43e4c3b5aa5f253663d47ac9e32e9fc8022b7e3c"
SCOPED_ID = "a1092d6465b32c7141a9befb290938adecca2f08b8fb646389becf941f9c656e"
INTEGRATION_ID = "df54c5a80093115d469ec0257127ecd59c304f7c6d440ad2dc8bd4b85d641f67"


@pytest.mark.skipif(os.environ.get("V52_PRIVATE_CAS_CLEANROOM") != "1",
                    reason="explicit fresh checkout and private CAS required")
def test_exact_private_cas_replays_approved_2010_01_month(tmp_path):
    root = Path(__file__).resolve().parents[2]
    manifest_path = (root / "governance" / "phase2b"
                     / f"private-corpus-manifest-{MANIFEST_ID}.json")
    manifest = read_manifest_exact(manifest_path, MANIFEST_ID)
    cas = resolve_cas_root(os.environ, require_explicit=True)
    assert not cas.is_relative_to(root)
    assert_private_objects_untracked(manifest, root)
    staged = stage_verified_private_corpus(manifest, cas, root)
    assert len(staged) == manifest.object_count == 44
    result = integrate_real_month(root, tmp_path, "2010-01")
    assert (result.effective_anchors, result.materialized_rows,
            result.excluded_before_label, result.scoped_excluded_anchors) == (
                34_271, 26_899, 6_950, 422)
    assert result.partition_id == PARTITION_ID
    assert result.coverage_hash == COVERAGE_HASH
    assert result.scoped_exclusion_hash == SCOPED_ID
    assert result.integration_id == INTEGRATION_ID
