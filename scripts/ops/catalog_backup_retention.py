#!/usr/bin/env python3
"""Beta catalog/backups -> NAS archive with verify-then-prune (Owner P0 5 Oct 2026 20:42 WITA).

Archives OLD entries of /Users/wolfterminal/beta-os/catalog/backups to
  /Volumes/05-Wolf-Vault-Mirror/WolfArchive/beta-os/catalog-backups/<RUN-DATE>/
(outside .../mac-studio/, which r2-sync mirrors to cloud) and deletes a Studio copy ONLY
after its NAS copy is verified:
  * every source file sha256 (local) == sha256 of the bytes read BACK from the NAS
    (uncached read, F_NOCACHE, decompressed) and byte size matches;
  * SQLite files: PRAGMA quick_check == ok on the (byte-identical) source, read-only/immutable;
  * bundles (tar.zst of files < 1 MB): re-read from NAS, every member listed + hashed.
Layout on NAS:
  objects/<sha[:2]>/<sha256>.zst     one zstd object per unique file >= 1 MB (dedupe)
  bundles/small-<birth-day>.tar.zst  small files grouped by entry birth day
  MANIFEST.json / MANIFEST.csv       one row per source file
  RESTORE.md
Never touches: entries younger than --min-age-min, the newest known-good local backup,
the newest known-good per day for the last --keep-daily-days days, .premig-index*.
Nothing outside catalog/backups is read for deletion. NAS retention is REPORT-ONLY
unless --nas-prune-apply is given (see docs/BACKUP-RETENTION.md).
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from compression import zstd

TZ = ZoneInfo("Asia/Makassar")
ROOT = Path("/Users/wolfterminal/beta-os")
SRC = ROOT / "catalog" / "backups"
NAS_BASE = Path("/Volumes/05-Wolf-Vault-Mirror/WolfArchive/beta-os/catalog-backups")
REL_OUT = ROOT / "state" / "reliability"
NOTIFY = ROOT / "state" / "build-factory" / "NOTIFY-QUEUE.jsonl"
LOCK = ROOT / "state" / "build-factory" / "CATALOG-RETENTION.flock"
BIG = 1_000_000
F_NOCACHE = 48
SKIP_NAMES = {".premig-index.json", ".premig-index.lock", ".premig-index.tmp"}


def now() -> datetime:
    return datetime.now(TZ)


def iso(ts: float | None = None) -> str:
    return (datetime.fromtimestamp(ts, TZ) if ts else now()).isoformat(timespec="seconds")


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(8 << 20), b""):
            h.update(c)
    return h.hexdigest()


def quick_check(p: Path) -> str:
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro&immutable=1", uri=True, timeout=5)
        try:
            r = c.execute("PRAGMA quick_check").fetchone()
            return str(r[0]) if r else "no-result"
        finally:
            c.close()
    except Exception as e:  # noqa: BLE001
        return f"error:{e.__class__.__name__}:{str(e)[:80]}"


def integrity_check(p: Path) -> tuple[str, int]:
    c = sqlite3.connect(f"file:{p}?mode=ro&immutable=1", uri=True, timeout=5)
    try:
        r = c.execute("PRAGMA integrity_check").fetchone()
        n = c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        return (str(r[0]) if r else "no-result"), int(n)
    finally:
        c.close()


def is_sqlite(p: Path) -> bool:
    try:
        with p.open("rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


class NoCacheReader(io.RawIOBase):
    def __init__(self, path: Path):
        self.fd = os.open(str(path), os.O_RDONLY)
        try:
            fcntl.fcntl(self.fd, F_NOCACHE, 1)
        except OSError:
            pass

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:  # noqa: ANN001
        data = os.read(self.fd, len(b))
        n = len(data)
        b[:n] = data
        return n

    def close(self) -> None:
        if not self.closed:
            os.close(self.fd)
        super().close()


def entry_birth(e: Path) -> float:
    st = e.lstat()
    return getattr(st, "st_birthtime", st.st_mtime)


def entry_newest_mtime(e: Path) -> float:
    t = e.lstat().st_mtime
    if e.is_dir() and not e.is_symlink():
        for dp, dn, fn in os.walk(e):
            for x in dn + fn:
                try:
                    t = max(t, os.lstat(os.path.join(dp, x)).st_mtime)
                except OSError:
                    pass
    return t


def notify(kind: str, **kw) -> None:
    rec = {"at": iso(), "kind": kind, "source": "catalog_backup_retention", **kw}
    try:
        with NOTIFY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def plan(args) -> dict:
    t_now = time.time()
    entries = [SRC / n for n in os.listdir(SRC) if n not in SKIP_NAMES]
    info = []
    for e in entries:
        try:
            info.append({"path": e, "birth": entry_birth(e), "newest": entry_newest_mtime(e)})
        except FileNotFoundError:
            continue
    keep: dict[str, str] = {}
    for i in info:
        if t_now - max(i["birth"], i["newest"]) < args.min_age_min * 60:
            keep[str(i["path"])] = f"younger_than_{args.min_age_min}min_inflight"
    # newest known-good + newest known-good per day for last N days (top-level sqlite files)
    sq = sorted([i for i in info if i["path"].is_file() and i["path"].suffix == ".sqlite"
                 and i["path"].stat().st_size > BIG], key=lambda i: -i["birth"])
    known_good = None
    per_day: dict[str, dict] = {}
    today = now().date()
    for i in sq:
        day = datetime.fromtimestamp(i["birth"], TZ).date()
        need_global = known_good is None
        need_day = (today - day).days < args.keep_daily_days and day.isoformat() not in per_day
        if not (need_global or need_day):
            continue
        res, ntab = integrity_check(i["path"])
        if res != "ok" or ntab < 50:
            continue
        rec = {"path": str(i["path"]), "integrity_check": res, "tables": ntab,
               "size": i["path"].stat().st_size, "birth": iso(i["birth"])}
        if need_global:
            known_good = rec
            keep[rec["path"]] = "newest_known_good"
        if need_day:
            per_day[day.isoformat()] = rec
            keep.setdefault(rec["path"], f"newest_known_good_of_{day.isoformat()}")
    archive = sorted([i for i in info if str(i["path"]) not in keep], key=lambda i: i["birth"])
    sized = []
    for i in archive:
        try:
            sz = sum(f.stat().st_size for f in iter_files(i["path"])) if i["path"].is_dir() else i["path"].lstat().st_size
        except FileNotFoundError:
            continue
        if sz >= args.min_size:
            sized.append((i, sz))
    archive = [i for i, _ in sized]
    if args.limit_gb:
        out, tot = [], 0
        for i, sz in sized:
            if tot + sz > args.limit_gb * 1e9 and out:
                break
            out.append(i); tot += sz
        archive = out
    return {"keep": keep, "known_good": known_good, "per_day": per_day, "archive": archive}


def iter_files(e: Path):
    if e.is_symlink():
        yield e
    elif e.is_dir():
        for dp, dn, fn in os.walk(e):
            for f in fn:
                yield Path(dp) / f
    else:
        yield e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-date", default=now().date().isoformat())
    ap.add_argument("--min-age-min", type=int, default=60)
    ap.add_argument("--keep-daily-days", type=int, default=2)
    ap.add_argument("--limit-gb", type=float, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delete", action="store_true", help="delete Studio copies whose NAS verification passed")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--min-size", type=int, default=0, help="only archive files/entries whose total size >= this (bytes)")
    args = ap.parse_args()

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lk = LOCK.open("w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(json.dumps({"result": "BUSY"}))
        return 1
    if not NAS_BASE.parent.parent.is_dir():
        notify("STUCK", reason="nas_not_mounted", path=str(NAS_BASE))
        print(json.dumps({"result": "BLOCKED_NAS_NOT_MOUNTED", "path": str(NAS_BASE)}))
        return 2
    t0 = time.time()
    df_before = shutil.disk_usage(str(SRC)).free
    p = plan(args)
    files = []  # (entry, file)
    unsupported_entries = set()
    for i in p["archive"]:
        for f in iter_files(i["path"]):
            if f.is_symlink() or not f.is_file():
                unsupported_entries.add(str(i["path"]))
                continue
            files.append((i, f))
    summary = {"run_date": args.run_date, "started_at": iso(t0), "keep": p["keep"],
               "known_good": p["known_good"], "per_day_known_good": p["per_day"],
               "entries_to_archive": len(p["archive"]), "files": len(files),
               "bytes": sum(f.stat().st_size for _, f in files)}
    print(json.dumps({k: summary[k] for k in ("entries_to_archive", "files", "bytes", "known_good")}), flush=True)
    if args.dry_run:
        print(json.dumps({"keep": p["keep"]}, indent=1))
        return 0

    dest = NAS_BASE / args.run_date
    (dest / "objects").mkdir(parents=True, exist_ok=True)
    (dest / "bundles").mkdir(parents=True, exist_ok=True)

    # 1. hash sources (+ stat snapshot for change detection)
    rows: dict[str, dict] = {}

    def h(item):
        i, f = item
        st = f.stat()
        return str(f), {"source": str(f), "entry": str(i["path"]), "size": st.st_size, "mtime": st.st_mtime,
                        "entry_birth": iso(i["birth"]), "sha256_src": sha_file(f), "is_sqlite": is_sqlite(f)}

    with ThreadPoolExecutor(args.workers * 2) as ex:
        for k, v in ex.map(h, files):
            rows[k] = v
    print(f"hashed {len(rows)} files in {time.time()-t0:.0f}s", flush=True)

    # 2. readability of sqlite sources (quick_check once per unique sha)
    qc: dict[str, str] = {}
    by_sha_first: dict[str, str] = {}
    for r in rows.values():
        if r["is_sqlite"]:
            by_sha_first.setdefault(r["sha256_src"], r["source"])
    with ThreadPoolExecutor(args.workers * 2) as ex:
        futs = {ex.submit(quick_check, Path(src)): sha for sha, src in by_sha_first.items()}
        for fu in as_completed(futs):
            qc[futs[fu]] = fu.result()
    print(f"quick_check {len(qc)} unique sqlite contents; not ok: {sum(1 for v in qc.values() if v!='ok')}", flush=True)

    # 3. big files -> content-addressed zstd objects, verified by uncached readback
    big_sha: dict[str, str] = {}
    for r in rows.values():
        if r["size"] >= BIG:
            big_sha.setdefault(r["sha256_src"], r["source"])
    obj_result: dict[str, dict] = {}

    def put_obj(sha: str, src: str) -> tuple[str, dict]:
        od = dest / "objects" / sha[:2]
        od.mkdir(parents=True, exist_ok=True)
        obj = od / f"{sha}.zst"
        if not obj.exists():
            tmp = od / f".{sha}.zst.part"
            with open(src, "rb") as fi, zstd.ZstdFile(tmp, "wb", level=args.level) as zo:
                shutil.copyfileobj(fi, zo, 8 << 20)
            with open(tmp, "rb+") as fh:
                os.fsync(fh.fileno())
            tmp.replace(obj)
        hh, n = hashlib.sha256(), 0
        rd = NoCacheReader(obj)
        try:
            with zstd.ZstdFile(io.BufferedReader(rd, 8 << 20), "rb") as zi:
                for c in iter(lambda: zi.read(8 << 20), b""):
                    hh.update(c)
                    n += len(c)
        finally:
            rd.close()
        return sha, {"dest": str(obj), "sha256_dest": hh.hexdigest(), "size_dest": n,
                     "stored_bytes": obj.stat().st_size, "verified_at": iso()}

    done = 0
    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(put_obj, s, src) for s, src in big_sha.items()]
        for fu in as_completed(futs):
            try:
                s, res = fu.result()
                obj_result[s] = res
            except Exception as e:  # noqa: BLE001
                print(f"object error: {e.__class__.__name__}: {str(e)[:120]}", flush=True)
            done += 1
            if done % 25 == 0:
                print(f"objects {done}/{len(big_sha)} {time.time()-t0:.0f}s", flush=True)
    print(f"objects done {len(obj_result)}/{len(big_sha)} {time.time()-t0:.0f}s", flush=True)

    # 4. small files -> per-day tar.zst bundles, verified by listing + hashing every member on readback
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows.values():
        if r["size"] < BIG:
            groups[r["entry_birth"][:10]].append(r)
    bundle_ok: dict[str, dict] = {}
    for day, rs in sorted(groups.items()):
        bpath = dest / "bundles" / f"small-{day}.tar.zst"
        tmp = bpath.with_name("." + bpath.name + ".part")
        with zstd.ZstdFile(tmp, "wb", level=args.level) as zo:
            with tarfile.open(fileobj=zo, mode="w|", format=tarfile.PAX_FORMAT) as tf:
                for r in rs:
                    tf.add(r["source"], arcname=os.path.relpath(r["source"], SRC), recursive=False)
        with open(tmp, "rb+") as fh:
            os.fsync(fh.fileno())
        tmp.replace(bpath)
        rd = NoCacheReader(bpath)
        got = {}
        try:
            with zstd.ZstdFile(io.BufferedReader(rd, 8 << 20), "rb") as zi:
                with tarfile.open(fileobj=zi, mode="r|") as tf:
                    for m in tf:
                        if m.isfile():
                            fo = tf.extractfile(m)
                            hh = hashlib.sha256(fo.read())
                            got[str(SRC / m.name)] = (hh.hexdigest(), m.size)
        finally:
            rd.close()
        for r in rs:
            g = got.get(r["source"])
            bundle_ok[r["source"]] = {"dest": f"{bpath}::{os.path.relpath(r['source'], SRC)}",
                                      "sha256_dest": g[0] if g else None, "size_dest": g[1] if g else None,
                                      "verified_at": iso()}
        print(f"bundle {day}: {len(rs)} files, members listed {len(got)}, {bpath.stat().st_size/1e6:.1f} MB", flush=True)

    # 5. per-file verdicts
    manifest = []
    for r in rows.values():
        d = obj_result.get(r["sha256_src"]) if r["size"] >= BIG else bundle_ok.get(r["source"])
        readable = (qc.get(r["sha256_src"]) == "ok") if r["is_sqlite"] else (d is not None)
        ok = bool(d) and d.get("sha256_dest") == r["sha256_src"] and d.get("size_dest") == r["size"] and readable
        manifest.append({"source_path": r["source"], "entry": r["entry"], "dest_path": d["dest"] if d else None,
                         "size": r["size"], "size_dest": d.get("size_dest") if d else None,
                         "sha256_src": r["sha256_src"], "sha256_dest": d.get("sha256_dest") if d else None,
                         "readable": readable,
                         "readability_check": (f"sqlite quick_check={qc.get(r['sha256_src'])}" if r["is_sqlite"]
                                               else "listed+hashed from NAS readback"),
                         "entry_birth": r["entry_birth"], "verified": ok,
                         "verified_at": d.get("verified_at") if d else None, "_mtime": r["mtime"]})

    # 6. delete only fully verified, unchanged entries
    by_entry: dict[str, list[dict]] = defaultdict(list)
    for m in manifest:
        by_entry[m["entry"]].append(m)
    deleted, del_bytes, kept_fail = [], 0, []
    for e, ms in by_entry.items():
        if e in unsupported_entries or not all(m["verified"] for m in ms):
            kept_fail.append(e)
            continue
        unchanged = True
        for m in ms:
            try:
                st = os.stat(m["source_path"])
                unchanged &= (st.st_size == m["size"] and st.st_mtime == m["_mtime"])
            except FileNotFoundError:
                unchanged = False
        ep = Path(e)
        if ep.is_dir():
            n_now = sum(1 for _ in iter_files(ep))
            unchanged &= n_now == len(ms)
        if not unchanged:
            kept_fail.append(e)
            continue
        if args.delete:
            sz = sum(m["size"] for m in ms)
            if ep.is_dir():
                shutil.rmtree(ep)
            else:
                ep.unlink()
            deleted.append(e)
            del_bytes += sz
            for m in ms:
                m["studio_copy_deleted_at"] = iso()
    for m in manifest:
        m.pop("_mtime", None)

    births = sorted(m["entry_birth"] for m in manifest)
    summary.update({
        "finished_at": iso(), "nas_destination": str(dest),
        "verified_files": sum(1 for m in manifest if m["verified"]), "total_files": len(manifest),
        "unique_objects": len(obj_result), "stored_object_bytes": sum(v["stored_bytes"] for v in obj_result.values()),
        "bundles": sorted(str(p) for p in (dest / "bundles").glob("small-*.tar.zst")),
        "entries_deleted": len(deleted), "bytes_deleted": del_bytes, "entries_kept_unverified": kept_fail,
        "source_birth_range": [births[0], births[-1]] if births else None,
        "studio_free_before": df_before, "studio_free_after": shutil.disk_usage(str(SRC)).free,
    })
    stamp = now().strftime("%Y%m%d-%H%M%S")
    REL_OUT.mkdir(parents=True, exist_ok=True)
    outs = [dest / f"MANIFEST-{stamp}.json", REL_OUT / f"CATALOG-BACKUP-ARCHIVE-MANIFEST-{stamp}.json"]
    for o in outs:
        o.write_text(json.dumps({"summary": summary, "files": manifest}, indent=1))
    cols = ["source_path", "dest_path", "size", "size_dest", "sha256_src", "sha256_dest", "readable",
            "readability_check", "verified", "verified_at", "entry_birth", "studio_copy_deleted_at"]
    for o in [dest / f"MANIFEST-{stamp}.csv", REL_OUT / f"CATALOG-BACKUP-ARCHIVE-MANIFEST-{stamp}.csv"]:
        with o.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(manifest)
    (dest / "RESTORE.md").write_text(
        "Restore a file: find its row in MANIFEST-*.json.\n"
        "objects/<aa>/<sha256>.zst  ->  zstd -d objects/aa/<sha>.zst -o <original name>  (then sha256 must equal sha256_src)\n"
        "bundles/small-<day>.tar.zst -> zstd -dc bundles/small-<day>.tar.zst | tar -x -C <dir> '<member>'\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("keep", "entries_kept_unverified")}, indent=1))
    print("manifest:", outs[1])
    if kept_fail:
        print(f"kept (not verified/unchanged): {len(kept_fail)}")
    return 0 if summary["verified_files"] == summary["total_files"] else 3


if __name__ == "__main__":
    sys.exit(main())
