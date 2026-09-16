#!/usr/bin/env python3
"""CLI: sync Habitat Metricool performance (blogId from brand_external_ids)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_metricool_performance import sync_metricool_performance  # noqa: E402


def main() -> int:
    window = 60
    if len(sys.argv) > 1:
        try:
            window = int(sys.argv[1])
        except ValueError:
            pass
    report = sync_metricool_performance(brand_key="habitat", window_days=window)
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
