#!/usr/bin/env python3
"""Fake orchestrator worker — exits non-zero."""
from __future__ import annotations

import json
import sys
from pathlib import Path

completion = Path(sys.argv[1])
completion.parent.mkdir(parents=True, exist_ok=True)
completion.write_text(json.dumps({"verdict": "FAIL", "summary": "failed"}) + "\n", encoding="utf-8")
print("worker failed", file=sys.stderr)
raise SystemExit(2)
