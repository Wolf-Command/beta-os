#!/usr/bin/env python3
"""Fake orchestrator worker — writes completion file and exits 0."""
from __future__ import annotations

import json
import sys
from pathlib import Path

completion = Path(sys.argv[1])
verdict = sys.argv[2] if len(sys.argv) > 2 else "PASS"
summary = sys.argv[3] if len(sys.argv) > 3 else "ok"
completion.parent.mkdir(parents=True, exist_ok=True)
completion.write_text(
    json.dumps({"verdict": verdict, "summary": summary, "status": "COMPLETED"}) + "\n",
    encoding="utf-8",
)
print(json.dumps({"verdict": verdict, "summary": summary}))
