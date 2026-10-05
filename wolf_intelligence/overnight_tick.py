"""Safe overnight tick for Wolf Intelligence control plane. No paid spikes."""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from . import dispatcher, learning, shadow_compare, work_items
from .paths import AUDIT_DIR, ensure_dirs
from .stats_store import recompute

TZ = ZoneInfo("Asia/Makassar")


def run() -> dict:
    ensure_dirs()
    # 3 fresh shadow samples
    ids = []
    for i in range(3):
        wi = work_items.create(
            title=f"Overnight shadow tick {datetime.now(TZ).strftime('%H%M%S')}-{i}",
            kind=["code_debug", "review", "security"][i % 3],
            isolated_safe=True,
            tags=["overnight", "shadow"],
        )
        dispatcher.dispatch(wi["id"])
        learning.record_outcome(wi["id"], self_eval_rating=3, notes="overnight self-eval pending human")
        ids.append(wi["id"])
    # expand compare lightly
    shadow_compare.run_compare(samples=5)
    stats = recompute()
    out = {"at": datetime.now(TZ).isoformat(timespec="seconds"), "work_items": ids, "stats": stats}
    (AUDIT_DIR / "overnight-tick-latest.json").write_text(json.dumps(out, indent=2) + "\n")
    return out
