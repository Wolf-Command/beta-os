#!/usr/bin/env python3
"""Fake worker — parent exits quickly; child ignores SIGTERM and holds pipes."""
from __future__ import annotations

import os
import signal
import sys
import time

if os.fork() == 0:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    sys.stdout.write("orphan-child-alive\n")
    sys.stdout.flush()
    time.sleep(120)
    sys.exit(0)
sys.exit(0)
