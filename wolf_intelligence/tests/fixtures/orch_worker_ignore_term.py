#!/usr/bin/env python3
"""Fake orchestrator worker — ignores SIGTERM to exercise timeout kill path."""
from __future__ import annotations

import signal
import time

signal.signal(signal.SIGTERM, signal.SIG_IGN)
time.sleep(60)
