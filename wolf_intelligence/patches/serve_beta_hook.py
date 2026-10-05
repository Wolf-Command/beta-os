"""Idempotent injector for serve_beta.py Wolf Intelligence routes.

Run: python3 wolf_intelligence/patches/serve_beta_hook.py
Does not reload Beta. Safe to re-run.
"""
from __future__ import annotations
from pathlib import Path

TARGET = Path("/Users/wolfterminal/beta-os/scripts/serve_beta.py")
ANCHOR = '        # PACK-01 Owner cockpit. Read-only JSON and a read board.'
HOOK = '''
        # Wolf Intelligence Owner board (SHADOW control plane). No Daily Close/Petty coupling.
        try:
            from core import wolf_intel_routes as _wolf_intel_routes
            if _wolf_intel_routes.handle_get(self, path):
                return
        except Exception:
            pass

'''

def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "wolf_intel_routes" in text:
        print("already_present")
        return 0
    if ANCHOR not in text:
        print("anchor_missing")
        return 2
    TARGET.write_text(text.replace(ANCHOR, HOOK + ANCHOR, 1), encoding="utf-8")
    print("injected")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
