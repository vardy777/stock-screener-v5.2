"""Offline exact-source publication of historical Master intervals; no provider IO."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v5_2.data.historical_security_master_authority import (  # noqa: E402
    publish_verified_master_source,
)


def main() -> int:
    base = ROOT / "data/phase_1b_historical_master_portable"
    result = publish_verified_master_source(base / "source", base / "published")
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
