#!/usr/bin/env python3
"""P0 regression: Haikal Smart Upload preview with file-level-only detail."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import smart_upload as su  # noqa: E402


class _Serve:
    LIBRARY_V2 = Path("/tmp")

    @staticmethod
    def db_connect():
        c = sqlite3.connect(":memory:")
        c.execute(
            """CREATE TABLE assets (
                id INTEGER PRIMARY KEY,
                brand TEXT, stage TEXT, media_type TEXT,
                subject TEXT, shoot_date TEXT, canonical_filename TEXT
            )"""
        )
        return c


def _body(**over):
    b = {
        "brand": "habitat",
        "stage": "RAW",
        "shoot_date": "2026-09-22",
        "subject": "Allen testimonial",
        "media_type": "video",
        "files": [
            {"original_filename": "IMG_0001.MP4", "detail": "owner-testimonial"},
        ],
    }
    b.update(over)
    return b


def main() -> int:
    fails = 0

    def check(cond, msg):
        nonlocal fails
        if cond:
            print(f"PASS {msg}")
        else:
            fails += 1
            print(f"FAIL {msg}")

    r = su.preview_batch(_Serve(), _body())
    check(r.get("http") == 200, "Allen + files[].detail=owner-testimonial -> 200")
    check((r.get("body") or {}).get("ok") is not False, "body not false")
    previews = (r.get("body") or {}).get("previews") or []
    check(len(previews) == 1, "one preview row")
    blob = ""
    if previews:
        blob = "%s/%s" % (previews[0].get("detail") or "", previews[0].get("canonical_filename") or "")
    check(("owner-testimonial" in blob) or ("owner" in blob), "preview carries owner-testimonial")

    r2 = su.preview_batch(
        _Serve(),
        _body(detail="owner-testimonial", files=[{"original_filename": "a.mp4"}]),
    )
    check(r2.get("http") == 200, "top-level detail still 200")

    r3 = su.preview_batch(_Serve(), _body(files=[{"original_filename": "a.mp4", "detail": ""}]))
    check(r3.get("http") == 400, "empty detail -> 400")
    err = (r3.get("body") or {}).get("error") or ""
    check("meaningful slug" in err, "empty error mentions meaningful slug")

    r4 = su.preview_batch(_Serve(), _body(files=[{"original_filename": "a.mp4", "detail": "a"}]))
    check(r4.get("http") == 400, "single-char detail -> 400")

    r5 = su.preview_batch(_Serve(), _body(files=[{"original_filename": "a.mp4", "detail": "   "}]))
    check(r5.get("http") == 400, "whitespace detail -> 400")

    total = 8
    print("PASS=%d FAIL=%d" % (total - fails, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
