#!/usr/bin/env python3
"""Fake worker — writes stdin to the path given as argv[1]."""
from __future__ import annotations

import sys
from pathlib import Path

Path(sys.argv[1]).write_text(sys.stdin.read(), encoding="utf-8")
sys.exit(0)
