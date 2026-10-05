"""Studio free-space hard guards (Owner P0 5 Oct 2026 21:01 WITA).

Thresholds (WOLF_DISK_*_GB env overrides):
  WARN   < 100 GB  -> NOTIFY WARNING; allow work
  CLEAN  <  50 GB  -> pause nonessential (no new factory dispatches); auto-clean disposable tmp-f1
  P0     <  25 GB  -> P0 protection mode: refuse all disk-growing nonessential jobs

Called by bf_supervisor before each dispatch tick and by bf_watch. Never kills Beta/Prod.
Never deletes evidence, live DBs, git, recovery points, or catalog backups younger than policy.
See docs/BACKUP-RETENTION.md.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
BF = ROOT / "state" / "build-factory"
NOTIFY = BF / "NOTIFY-QUEUE.jsonl"
TMPF1 = BF / "tmp-f1"
WARN_GB = float(os.environ.get("WOLF_DISK_WARN_GB", "100"))
CLEAN_GB = float(os.environ.get("WOLF_DISK_CLEAN_GB", "50"))
P0_GB = float(os.environ.get("WOLF_DISK_P0_GB", "25"))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def free_gb() -> float:
    return shutil.disk_usage(str(ROOT)).free / 1e9


def notify(kind: str, **kw) -> None:
    rec = {"at": now(), "kind": kind, "source": "bf_disk_guard", **kw}
    try:
        NOTIFY.parent.mkdir(parents=True, exist_ok=True)
        with NOTIFY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def clean_disposable_tmpf1(*, min_age_sec: int = 300) -> dict:
    """Remove wolf-f1-* dirs that contain only content_library.sqlite(+wal/shm)."""
    import time
    if not TMPF1.is_dir():
        return {"deleted": 0}
    allowed = {"content_library.sqlite", "content_library.sqlite-shm", "content_library.sqlite-wal",
               "sop_factory.sqlite", "tin-count.md"}
    deleted = 0
    freed = 0
    now_t = time.time()
    for e in list(TMPF1.iterdir()):
        if not e.is_dir() or e.name == "e2e-nota-photos":
            continue
        files = [f for f in e.rglob("*") if f.is_file()]
        names = {f.name for f in files}
        if not names or not names.issubset(allowed):
            continue
        newest = max((f.stat().st_mtime for f in files), default=e.stat().st_mtime)
        if now_t - newest < min_age_sec:
            continue
        sz = sum(f.stat().st_size for f in files)
        shutil.rmtree(e, ignore_errors=True)
        deleted += 1
        freed += sz
    return {"deleted": deleted, "bytes_freed": freed}


def check(*, auto_clean: bool = True) -> dict:
    """Return {level, free_gb, allow_dispatch, allow_disk_grow, actions}."""
    fg = free_gb()
    out = {"at": now(), "free_gb": round(fg, 2), "level": "OK",
           "allow_dispatch": True, "allow_disk_grow": True, "actions": []}
    if fg < P0_GB:
        out.update(level="P0_PROTECTION", allow_dispatch=False, allow_disk_grow=False)
        out["actions"].append("refuse_nonessential_disk_jobs")
        if auto_clean:
            out["cleanup"] = clean_disposable_tmpf1()
            out["actions"].append("auto_clean_tmpf1")
        notify("FAIL_NO_SELF_REPAIR", reason="studio_free_below_25gb_p0_protection",
               free_gb=out["free_gb"], allow_dispatch=False)
    elif fg < CLEAN_GB:
        out.update(level="CLEAN_PAUSE", allow_dispatch=False, allow_disk_grow=False)
        out["actions"].append("pause_new_dispatches")
        if auto_clean:
            out["cleanup"] = clean_disposable_tmpf1()
            out["actions"].append("auto_clean_tmpf1")
        notify("STUCK", reason="studio_free_below_50gb_pause_nonessential",
               free_gb=out["free_gb"], allow_dispatch=False)
    elif fg < WARN_GB:
        out.update(level="WARN")
        out["actions"].append("warn_only")
        notify("WARNING", reason="studio_free_below_100gb", free_gb=out["free_gb"])
    return out


if __name__ == "__main__":
    print(json.dumps(check(auto_clean=False), indent=2))
