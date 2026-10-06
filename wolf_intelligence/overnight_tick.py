"""Safe overnight tick for Wolf Intelligence control plane. No paid spikes."""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from . import dispatcher, learning, shadow_compare, work_items
from .paths import AUDIT_DIR, ensure_dirs
from .stats_store import recompute

TZ = ZoneInfo("Asia/Makassar")


def _grok_lease_recovery() -> dict:
    """Release expired grok_bot leases and re-ring doorbells (lease recovery, not polling). Never breaks the tick."""
    try:
        from . import grok_bridge
        return grok_bridge.release_expired(actor="overnight-tick")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": "RECOVERY_ERROR", "error": type(exc).__name__}


def _grok_doorbell_enabled() -> bool:
    try:
        from . import grok_doorbell
        return grok_doorbell.from_env() is not None
    except Exception:  # noqa: BLE001
        return False


def _grok_audit_verify() -> dict:
    """Verify the grok_bridge audit chain on every tick. Never raises."""
    try:
        from . import events, grok_bridge
        result = grok_bridge.verify_audit_chain()
        if not result.get("ok"):
            try:
                events.emit("grok_bridge.audit_chain_broken",
                            {"problems": result.get("problems"), "broken_at_seq": result.get("broken_at_seq")})
            except Exception:  # noqa: BLE001
                pass
        return result
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": "VERIFY_ERROR", "error": type(exc).__name__}


def run() -> dict:
    ensure_dirs()
    grok_audit_chain = _grok_audit_verify()
    if grok_audit_chain.get("ok"):
        grok_recovery = _grok_lease_recovery()
    else:
        grok_recovery = {"ok": False, "code": "RECOVERY_SKIPPED", "skipped_due_to_audit_failure": True,
                         "audit": grok_audit_chain}
    grok_doorbell_enabled = _grok_doorbell_enabled()
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
    out = {"at": datetime.now(TZ).isoformat(timespec="seconds"), "work_items": ids, "stats": stats,
           "grok_lease_recovery": grok_recovery, "grok_audit_chain": grok_audit_chain,
           "grok_doorbell_enabled": grok_doorbell_enabled}
    (AUDIT_DIR / "overnight-tick-latest.json").write_text(json.dumps(out, indent=2) + "\n")
    return out
