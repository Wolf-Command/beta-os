#!/usr/bin/env python3
"""Run one test script with the canonical ledger guard installed first."""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)
sys.path.insert(0, str(SCRIPTS))

from core.canonical_guard import install  # noqa: E402

install()

if len(sys.argv) < 2:
    print("usage: run_guarded.py scripts/tests/<suite>.py", file=sys.stderr)
    raise SystemExit(2)

target = Path(sys.argv[1])
if not target.is_file():
    target = ROOT / sys.argv[1]
sys.argv = [str(target), *sys.argv[2:]]
runpy.run_path(str(target), run_name="__main__")
