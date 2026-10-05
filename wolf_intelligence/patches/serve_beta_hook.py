"""Idempotent injector for serve_beta.py Wolf Intelligence routes.

Run: python3 wolf_intelligence/patches/serve_beta_hook.py
Does not reload Beta. Safe to re-run.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("/Users/wolfterminal/beta-os/scripts/serve_beta.py")
GET_ANCHOR = "        # PACK-01 Owner cockpit. Read-only JSON and a read board."
GET_HOOK = '''
        # Wolf Intelligence Owner board (SHADOW control plane). No Daily Close/Petty coupling.
        try:
            from core import wolf_intel_routes as _wolf_intel_routes
            if _wolf_intel_routes.handle_get(self, path):
                return
        except Exception:
            pass

'''
POST_MARK = "wolf_intel_routes.handle_post"
POST_HOOK = '''
        # Wolf Intelligence human decisions (SHADOW). No Daily Close/Petty coupling.
        try:
            from core import wolf_intel_routes as _wolf_intel_routes
            if _wolf_intel_routes.handle_post(self, path):
                return
        except Exception:
            pass
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    changed = False
    if "wolf_intel_routes.handle_get" not in text and "wolf_intel_routes" not in text:
        if GET_ANCHOR not in text:
            print("get_anchor_missing")
            return 2
        text = text.replace(GET_ANCHOR, GET_HOOK + GET_ANCHOR, 1)
        changed = True
        print("get_injected")
    else:
        print("get_already_present")
    if POST_MARK not in text:
        # Insert near start of do_POST if we can find a common early anchor
        post_anchors = [
            "    def do_POST(self):",
            "    def do_POST(self) -> None:",
        ]
        inserted = False
        for a in post_anchors:
            if a in text:
                # after the def line + path parse if present
                idx = text.find(a)
                # find first blank line after a short window and inject
                window = text[idx: idx + 800]
                # inject right after function def line
                text = text.replace(a, a + "\n" + POST_HOOK, 1)
                inserted = True
                changed = True
                print("post_injected")
                break
        if not inserted:
            print("post_anchor_missing")
    else:
        print("post_already_present")
    if changed:
        TARGET.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
