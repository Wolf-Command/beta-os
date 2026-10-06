#!/usr/bin/env python3
"""Shim. The control plane lives in nogrok_control.

Older imports keep resolving. This module does not start a second scheduler,
a model, or a blocked worker.
"""
from __future__ import annotations

from core.nogrok_control import (  # noqa: F401
    DIRECTIVE_ID,
    LEASE_SECONDS,
    LOCAL_WORKER,
    apply_event,
    apply_owner_action,
    blocked_name,
    disk_report,
    hold_local,
    load,
    needs_you,
    running_items,
    runtime_evidence,
    save,
    tick,
    worker_eligibility,
)
