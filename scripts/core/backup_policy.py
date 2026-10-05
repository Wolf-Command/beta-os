"""Pre-migration backup policy + free-space guard (Owner P0 5 Oct 2026 20:42 WITA).

Root cause fixed: every migration did `shutil.copy2(db, catalog/backups/pre-...sqlite)`
unconditionally — including when regression tests ran the migration against a throwaway
COPY of the live DB, and when the migration was an idempotent no-op. Factory slices re-run
those tests many times per slice -> 7 x 109 MB per P2P test run -> ~18-28 GB/day.

premig_backup(src, dest) -> Path   (drop-in for `shutil.copy2(src, dest)`; returns the
                                    path that actually holds the backup)
  * src is NOT a live catalog DB (test/scratch copy): no full copy into catalog/backups.
    An APFS clone (cp -c, copy-on-write, ~0 bytes) is made next to the scratch DB so the
    caller still gets a real file; falls back to returning src itself.
  * src IS a live catalog DB (catalog/<name>.sqlite):
      - DEDUPE: if src content (sha256) equals the last backup of that DB and that file
        still exists, reuse it (no new copy);
      - FREE-SPACE GUARD: refuse (RuntimeError) if writing the copy would leave less than
        MIN_FREE_GB free on the Studio; emits FAIL_NO_SELF_REPAIR to NOTIFY-QUEUE.jsonl;
      - else shutil.copy2 as before and record it in catalog/backups/.premig-index.json.
See docs/BACKUP-RETENTION.md. Never deletes anything.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog"
BACKUP_DIR = CATALOG / "backups"
INDEX = BACKUP_DIR / ".premig-index.json"
NOTIFY = ROOT / "state" / "build-factory" / "NOTIFY-QUEUE.jsonl"
EVENTS = ROOT / "state" / "reliability" / "BACKUP-POLICY-EVENTS.jsonl"
MIN_FREE_GB = float(os.environ.get("WOLF_BACKUP_MIN_FREE_GB", "50"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _append(path: Path, rec: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def is_live_db(src: Path) -> bool:
    try:
        r = Path(src).resolve()
    except OSError:
        return False
    return r.parent == CATALOG.resolve() and r.suffix == ".sqlite"


def free_bytes(path: Path = CATALOG) -> int:
    return shutil.disk_usage(str(path)).free


def notify_low_disk(context: str, need_bytes: int) -> None:
    rec = {"at": _now(), "kind": "FAIL_NO_SELF_REPAIR", "source": "backup_policy",
           "reason": "studio_free_space_below_guard", "context": context,
           "free_gb": round(free_bytes() / 1e9, 2), "need_gb": round(need_bytes / 1e9, 2),
           "min_free_gb": MIN_FREE_GB,
           "action": "Backup refused. Archive old catalog/backups to NAS (scripts/ops/catalog_backup_retention.py) or free disk."}
    _append(NOTIFY, rec)
    _append(EVENTS, rec)


def guard_free_space(need_bytes: int, context: str) -> None:
    if free_bytes() - need_bytes < MIN_FREE_GB * 1e9:
        notify_low_disk(context, need_bytes)
        raise RuntimeError(f"REFUSE_LOW_DISK: backup for {context} would leave < {MIN_FREE_GB:.0f} GB free")


def _clone_or_self(src: Path, dest: Path) -> Path:
    sib = src.parent / f".premig-{dest.name}"
    try:
        r = subprocess.run(["cp", "-c", "-p", str(src), str(sib)], capture_output=True, timeout=60)
        if r.returncode == 0 and sib.is_file():
            return sib
    except Exception:  # noqa: BLE001
        pass
    return src


def premig_backup(src, dest) -> Path:
    src, dest = Path(src), Path(dest)
    if not is_live_db(src):
        out = _clone_or_self(src, dest)
        _append(EVENTS, {"at": _now(), "event": "SCRATCH_NO_FULL_COPY", "src_name": src.name,
                         "dest_name": dest.name, "backup": str(out)})
        return out
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with (BACKUP_DIR / ".premig-index.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            idx = json.loads(INDEX.read_text())
        except Exception:  # noqa: BLE001
            idx = {}
        sha = _sha256(src)
        last = idx.get(src.name) or {}
        lp = Path(last.get("path", "")) if last.get("path") else None
        if last.get("sha256") == sha and lp and lp.is_file() and lp.stat().st_size == src.stat().st_size:
            _append(EVENTS, {"at": _now(), "event": "DEDUPE_SKIP", "src_name": src.name,
                             "dest_name": dest.name, "reused": str(lp)})
            return lp
        size = src.stat().st_size
        guard_free_space(size, f"premig:{dest.name}")
        shutil.copy2(src, dest)
        idx[src.name] = {"sha256": sha, "path": str(dest), "size": size, "at": _now()}
        tmp = INDEX.with_suffix(".tmp")
        tmp.write_text(json.dumps(idx, indent=2))
        tmp.replace(INDEX)
        _append(EVENTS, {"at": _now(), "event": "LIVE_BACKUP_WRITTEN", "dest": str(dest), "size": size})
        return dest
