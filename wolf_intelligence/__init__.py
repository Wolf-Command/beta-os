"""Wolf Intelligence — CONTROL PLANE above workers (not an independent agent).

Canonical work state is owned by this package's store, never by models/agents.
Dispatch defaults to SHADOW MODE: recommend routing; isolated safe tests only;
no Production mutation; no duplicate expensive dispatch.
"""
from __future__ import annotations

__version__ = "0.1.0"
__role__ = "control_plane"

# paths is imported lazily by each module so WOLF_INTELLIGENCE_STATE_ROOT can be set first.
