#!/usr/bin/env python3
"""Resumable in-place NAS catalog indexer. Beta only.

Reads state/nas-estate/manifest.tsv (already discovered). Writes catalog rows,
local thumbs under state/content-thumbs, and owner counts. Resolves stale mount
names, unicode normalisation, and URL-encoded paths before marking a file
missing. Re-queues a failed row when the file resolves. Never moves, renames,
deletes, or writes inside a NAS media tree. staff_ready stays false.
full_nas_complete stays false.

Serves the 2026-09-22 NAS commissioning rule and the 2026-09-25 estate discovery.
"""
from __future__ import annotations

import errno
import json
import os
import re
import signal
import sqlite3
import stat
import subprocess
import sys
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from core import content_engine_repair as repair  # noqa: E402
from core import nas_library as nas  # noqa: E402

TZ = ZoneInfo("Asia/Makassar")
BASE = Path(os.environ.get("BETA_OS_ROOT", "/Users/wolfterminal/beta-os"))
HASH_BYTES = 1_048_576

# Folder names seen on NAS that are not yet alias keys. Slug must exist in the registry.
FOLDER_RULES = {
    "amg atrium": "atrium",
    "uma blu cafe": "umablu",
    "rainforest restaurant": "rainforest",
    "selong selo": "selo",
    "tropic at selong": "tropik",
    "habitat": "habitat",
}
STOCK_ROOTS = {"02-Stock-Assets-1", "03-Templates"}

# Live copies only. Match on a path boundary so the -3 / -1 mounts are not rewritten.
# 00-Editing-Workspace, -1, and -2 are empty stubs. 02-Stock-Assets is the empty stub.
STALE_MOUNTS: tuple[tuple[str, str], ...] = (
    ("/Volumes/00-Editing-Workspace-2", "/Volumes/00-Editing-Workspace-3"),
    ("/Volumes/00-Editing-Workspace-1", "/Volumes/00-Editing-Workspace-3"),
    ("/Volumes/00-Editing-Workspace", "/Volumes/00-Editing-Workspace-3"),
    ("/Volumes/02-Stock-Assets", "/Volumes/02-Stock-Assets-1"),
)

_TRANSIENT_ERRNO = {
    n
    for n in (
        getattr(errno, name, None)
        for name in (
            "EIO",
            "ETIMEDOUT",
            "ESTALE",
            "EAGAIN",
            "EINTR",
            "ENOTCONN",
            "EHOSTDOWN",
            "ENODEV",
            "ENETDOWN",
            "ENETUNREACH",
            "EBUSY",
            "ECONNRESET",
        )
    )
    if isinstance(n, int)
}
IMAGE_EXT = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff",
    ".gif", ".bmp",
}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".m2ts", ".mts", ".3gp"}


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def norm(value: str) -> str:
    return re.sub(r"[\s_\-]+", " ", (value or "").lower()).strip()


@dataclass
class Config:
    catalog: Path
    estate: Path
    manifest: Path
    discovery: Path
    ingest_batch: int = 400
    thumb_batch: int = 8
    hash_batch: int = 40

    @property
    def checkpoint(self) -> Path:
        return self.estate / "index-checkpoint.json"

    @property
    def counts(self) -> Path:
        return self.estate / "owner-counts.json"

    @property
    def log_path(self) -> Path:
        return self.estate / "index.log"

    @property
    def pid_path(self) -> Path:
        return self.estate / "index.pid"

    @property
    def failures(self) -> Path:
        return self.estate / "failures.jsonl"

    @property
    def duplicates(self) -> Path:
        return self.estate / "duplicate-candidates.jsonl"


def production_config() -> Config:
    estate = BASE / "state" / "nas-estate"
    return Config(
        catalog=Path(os.environ.get("NAS_CATALOG_DB", str(BASE / "catalog" / "content_library.sqlite"))),
        estate=Path(os.environ.get("NAS_ESTATE_DIR", str(estate))),
        manifest=Path(os.environ.get("NAS_MANIFEST", str(estate / "manifest.tsv"))),
        discovery=Path(os.environ.get("NAS_DISCOVERY", str(estate / "discovery.json"))),
    )


def refuse_nas_write(path: Path) -> None:
    """Raise if a write would land inside a NAS media tree."""
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    text = str(resolved)
    for root in repair.NAS_READ_ROOTS:
        root_text = str(root)
        if text == root_text or text.startswith(root_text + "/"):
            raise RuntimeError(f"refusing write under NAS: {text}")
    if text.startswith("/Volumes/"):
        raise RuntimeError(f"refusing write under /Volumes: {text}")


@dataclass(frozen=True)
class ResolvedPath:
    path: Path | None
    reason: str
    transient: bool = False


def _mount_remap(path: str, mounts: tuple[tuple[str, str], ...]) -> str:
    """Rewrite a stale mount prefix. A longer live name is not treated as the stub."""
    for old, new in mounts:
        if not old or old == new:
            continue
        if path == old or path.startswith(old + "/"):
            return new + path[len(old):]
    return path


def _path_variants(
    stored: str,
    mounts: tuple[tuple[str, str], ...],
    roots: tuple[Path, ...],
) -> list[tuple[str, str]]:
    """Candidate absolute paths. Raw is first so a literal % in a filename is kept."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, value: str) -> None:
        if not value or value in seen:
            return
        seen.add(value)
        out.append((label, value))

    nfc = unicodedata.normalize("NFC", stored)
    nfd = unicodedata.normalize("NFD", stored)
    unq = urllib.parse.unquote(stored)
    labeled = (
        (stored, "raw"),
        (nfc, "nfc"),
        (nfd, "nfd"),
        (unq, "unquote"),
        (unicodedata.normalize("NFC", unq), "unquote_nfc"),
        (unicodedata.normalize("NFD", unq), "unquote_nfd"),
    )
    for value, label in labeled:
        add(label, value)
    for label, value in list(out):
        mapped = _mount_remap(value, mounts)
        add("remap_" + label, mapped)
        add("remap_" + label + "_nfc", unicodedata.normalize("NFC", mapped))
        add("remap_" + label + "_nfd", unicodedata.normalize("NFD", mapped))
    if not stored.startswith("/"):
        for root in roots:
            add("relative_" + root.name, str(Path(root) / stored))
            add("relative_nfc_" + root.name, str(Path(root) / nfc))
            add("relative_nfd_" + root.name, str(Path(root) / nfd))
    return out


def _stat_kind(path: str) -> tuple[str, int | None]:
    try:
        st = os.stat(path, follow_symlinks=True)
    except FileNotFoundError:
        return "missing", errno.ENOENT
    except OSError as exc:
        return "error", exc.errno or 0
    if stat.S_ISREG(st.st_mode):
        return "file", None
    if stat.S_ISDIR(st.st_mode):
        return "dir", None
    return "other", None


def _sibling_nfc(path_str: str) -> str | None:
    """Read-only: find a same-directory name that matches under NFC. Does not rename."""
    parent = os.path.dirname(path_str)
    name = os.path.basename(path_str)
    if not parent or not name or not os.path.isdir(parent):
        return None
    target = unicodedata.normalize("NFC", name)
    try:
        names = os.listdir(parent)
    except OSError:
        return None
    for cand in names:
        if unicodedata.normalize("NFC", cand) == target:
            return os.path.join(parent, cand)
    return None


def resolve_media_path(
    stored: str,
    *,
    mounts: tuple[tuple[str, str], ...] | None = None,
    roots: tuple[Path, ...] | None = None,
) -> ResolvedPath:
    """Find a regular file for a catalog path.

    Tries the stored string, NFC, NFD, URL-unquote, stale-mount remap, and a
    relative join onto the live read roots. Never creates or renames anything.
    """
    mounts = STALE_MOUNTS if mounts is None else mounts
    if roots is None:
        roots = repair.NAS_READ_ROOTS
    stored = (stored or "").strip()
    if not stored:
        return ResolvedPath(None, "missing_file:empty_path")
    saw_dir = False
    transient_errno: int | None = None
    for label, cand in _path_variants(stored, mounts, roots):
        kind, err = _stat_kind(cand)
        if kind == "file":
            return ResolvedPath(Path(cand), label)
        if kind == "dir":
            saw_dir = True
            continue
        if kind == "error" and err in _TRANSIENT_ERRNO:
            transient_errno = err
    for label, cand in (
        ("sibling_nfc", stored),
        ("remap_sibling_nfc", _mount_remap(stored, mounts)),
    ):
        sibling = _sibling_nfc(cand)
        if not sibling:
            continue
        kind, _err = _stat_kind(sibling)
        if kind == "file":
            return ResolvedPath(Path(sibling), label)
    if transient_errno is not None:
        return ResolvedPath(None, f"missing_file:transient_errno_{transient_errno}", transient=True)
    if saw_dir:
        return ResolvedPath(None, "missing_file:not_a_regular_file")
    return ResolvedPath(None, "missing_file:not_found")


def remember_resolved_path(
    cfg: Config,
    conn: sqlite3.Connection,
    row_id: int,
    stored: str,
    resolved: Path,
) -> tuple[str, str | None]:
    """Point the row at a resolved file when that path is free.

    A path already owned by another row is recorded as a duplicate candidate.
    Nothing on disk is deleted.
    """
    new = str(resolved)
    if new == stored:
        return stored, None
    clash = conn.execute(
        "SELECT id FROM nas_index WHERE original_path=? AND id<>?",
        (new, row_id),
    ).fetchone()
    if clash:
        record_duplicate(cfg, conn, stored, new, "resolved_path_already_indexed", None, None)
        return stored, f"missing_file:resolved_path_owned_by_{int(clash['id'])}"
    conn.execute("UPDATE nas_index SET original_path=? WHERE id=?", (new, row_id))
    return new, None


def requeue_resolved_failures(cfg: Config, conn: sqlite3.Connection) -> dict[str, int]:
    """Put FAILED (and blank) rows back on INDEXED when a regular file resolves.

    Rows that still do not exist stay FAILED with a precise reason. Idempotent:
    a second pass only sees rows that are still failed or blank.
    """
    rows = conn.execute(
        """
        SELECT id, original_path, ifnull(index_state,'') AS index_state
        FROM nas_index
        WHERE index_state='FAILED'
           OR ifnull(index_state,'') IN ('', 'DISCOVERED')
        ORDER BY id
        """
    ).fetchall()
    requeued = 0
    still_missing = 0
    transient = 0
    for seen, row in enumerate(rows, start=1):
        row_id = int(row["id"])
        stored = str(row["original_path"] or "")
        resolved = resolve_media_path(stored)
        if resolved.path is not None:
            _adopted, clash = remember_resolved_path(cfg, conn, row_id, stored, resolved.path)
            if clash:
                conn.execute(
                    "UPDATE nas_index SET index_state='FAILED', fail_reason=? WHERE id=?",
                    (clash[:300], row_id),
                )
                still_missing += 1
            else:
                conn.execute(
                    """
                    UPDATE nas_index
                    SET index_state='INDEXED', fail_reason=NULL
                    WHERE id=?
                    """,
                    (row_id,),
                )
                requeued += 1
        elif resolved.transient:
            conn.execute(
                """
                UPDATE nas_index
                SET index_state='INDEXED', fail_reason=?
                WHERE id=?
                """,
                (resolved.reason[:300], row_id),
            )
            transient += 1
        else:
            conn.execute(
                "UPDATE nas_index SET index_state='FAILED', fail_reason=? WHERE id=?",
                (resolved.reason[:300], row_id),
            )
            still_missing += 1
        if seen % 2000 == 0:
            conn.commit()
            log_line(
                cfg,
                f"requeue progress seen={seen} resolved={requeued} "
                f"missing={still_missing} transient={transient}",
            )
    conn.commit()
    return {"requeued": requeued, "still_missing": still_missing, "transient": transient}


def log_line(cfg: Config, message: str) -> None:
    cfg.estate.mkdir(parents=True, exist_ok=True)
    line = f"{now_iso()} {message}\n"
    with cfg.log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def connect(cfg: Config) -> sqlite3.Connection:
    conn = sqlite3.connect(cfg.catalog, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    repair._nas_index_columns(conn)
    try:
        repair.ensure_registry(conn)
    except sqlite3.Error:
        repair._ensure_alias_table(conn)
        for row in repair.REQUIRED_BRANDS:
            for alias in row["aliases"]:
                conn.execute(
                    """
                    INSERT INTO org_brand_aliases (alias_key, org_brand_id, slug, display_name)
                    VALUES (?,?,?,?)
                    ON CONFLICT(alias_key) DO UPDATE SET slug=excluded.slug
                    """,
                    (alias.strip().lower(), row["org_brand_id"], row["slug"], row["display_name"]),
                )
        conn.commit()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nas_duplicate_candidates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          path_a TEXT NOT NULL,
          path_b TEXT NOT NULL,
          reason TEXT NOT NULL,
          size INTEGER,
          sha256_1mb TEXT,
          recorded_at TEXT,
          UNIQUE(path_a, path_b, reason)
        )
        """
    )
    conn.commit()
    return conn


def load_aliases(conn: sqlite3.Connection) -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        rows = conn.execute("SELECT alias_key, slug FROM org_brand_aliases").fetchall()
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        key = str(row["alias_key"] or "")
        slug = str(row["slug"] or "")
        if not key or not slug:
            continue
        found[key.strip().lower()] = slug
        found[norm(key)] = slug
    return found


def brand_for(parts: list[str], aliases: dict[str, str], root_name: str) -> tuple[str, str]:
    """Map a relative folder chain through Brand Registry aliases."""
    known = set(aliases.values())
    for part in parts:
        key = norm(part)
        raw = part.strip().lower()
        if raw in aliases:
            return aliases[raw], "certain"
        if key in aliases:
            return aliases[key], "certain"
    for part in parts:
        for word in norm(part).split():
            if len(word) >= 4 and word in aliases and aliases[word] in known:
                return aliases[word], "alias_word"
    for part in parts:
        key = norm(part)
        slug = FOLDER_RULES.get(key)
        if slug and slug in known:
            return slug, "folder_rule"
    if root_name in STOCK_ROOTS:
        return "SHARED_STOCK", "shared"
    return "UNKNOWN", "review_required"


def load_checkpoint(cfg: Config) -> dict:
    if not cfg.checkpoint.is_file():
        return {}
    try:
        data = json.loads(cfg.checkpoint.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_checkpoint(cfg: Config, payload: dict) -> None:
    cfg.estate.mkdir(parents=True, exist_ok=True)
    body = {
        **payload,
        "updated_at": now_iso(),
        "staff_ready": False,
        "full_nas_complete": False,
        "full_tree_indexed": False,
    }
    cfg.checkpoint.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def write_counts(cfg: Config, conn: sqlite3.Connection, *, phase: str, manifest_line: int) -> dict:
    rows = conn.execute(
        """
        SELECT ifnull(brand_slug,'UNKNOWN') AS brand,
               ifnull(index_state,'DISCOVERED') AS state,
               COUNT(*) AS n
        FROM nas_index
        GROUP BY 1, 2
        """
    ).fetchall()
    by_brand: dict[str, dict[str, int]] = {}
    catalog_rows = 0
    for row in rows:
        brand = str(row["brand"])
        state = str(row["state"])
        count = int(row["n"])
        by_brand.setdefault(brand, {})[state] = count
        catalog_rows += count
    failed = int(conn.execute("SELECT COUNT(*) FROM nas_index WHERE index_state='FAILED'").fetchone()[0])
    dupes = int(conn.execute("SELECT COUNT(*) FROM nas_duplicate_candidates").fetchone()[0])
    manifest_files = 0
    if cfg.discovery.is_file():
        try:
            manifest_files = int(json.loads(cfg.discovery.read_text(encoding="utf-8")).get("files") or 0)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            manifest_files = 0
    payload = {
        "as_of": now_iso(),
        "phase": phase,
        "manifest_line": manifest_line,
        "manifest_files": manifest_files,
        "catalog_rows": catalog_rows,
        "by_brand_state": by_brand,
        "failed": failed,
        "duplicate_candidates": dupes,
        "staff_ready": False,
        "full_nas_complete": False,
        "full_tree_indexed": False,
        "note": (
            "Counts are the catalog rows loaded from the discovery manifest. "
            "This is not a claim that the whole NAS is complete."
        ),
    }
    cfg.estate.mkdir(parents=True, exist_ok=True)
    cfg.counts.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def mark_failed(cfg: Config, conn: sqlite3.Connection, row_id: int, path: str, reason: str) -> None:
    current = conn.execute("SELECT index_state FROM nas_index WHERE id=?", (row_id,)).fetchone()
    state = str(current["index_state"] or "") if current else ""
    if state == "FAILED":
        return
    if repair.STATE_RANK.get(state, 0) >= repair.STATE_RANK["HASHED"] and state == "HASHED":
        return
    conn.execute(
        "UPDATE nas_index SET index_state='FAILED', fail_reason=? WHERE id=?",
        (reason[:300], row_id),
    )
    append_jsonl(cfg.failures, {"at": now_iso(), "id": row_id, "path": path, "reason": reason[:300]})
    log_line(cfg, f"FAILED id={row_id} {reason[:180]}")


def record_duplicate(
    cfg: Config,
    conn: sqlite3.Connection,
    path_a: str,
    path_b: str,
    reason: str,
    size: int | None,
    digest: str | None,
) -> None:
    if not path_a or not path_b or path_a == path_b:
        return
    if path_a > path_b:
        path_a, path_b = path_b, path_a
    cur = conn.execute(
        """
        INSERT INTO nas_duplicate_candidates (path_a, path_b, reason, size, sha256_1mb, recorded_at)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(path_a, path_b, reason) DO NOTHING
        """,
        (path_a, path_b, reason, size, digest or "", now_iso()),
    )
    if cur.rowcount:
        append_jsonl(
            cfg.duplicates,
            {
                "at": now_iso(),
                "path_a": path_a,
                "path_b": path_b,
                "reason": reason,
                "size": size,
                "sha256_1mb": digest or "",
                "action": "recorded_only",
            },
        )


def scan_name_duplicates(cfg: Config, conn: sqlite3.Connection) -> int:
    groups = conn.execute(
        """
        SELECT original_filename, size
        FROM nas_index
        WHERE ifnull(original_filename,'') != ''
        GROUP BY original_filename, size
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    noted = 0
    for group in groups:
        paths = [
            str(row["original_path"])
            for row in conn.execute(
                """
                SELECT original_path FROM nas_index
                WHERE original_filename=? AND size=?
                ORDER BY original_path
                """,
                (group["original_filename"], group["size"]),
            ).fetchall()
        ]
        if len(paths) < 2:
            continue
        base = paths[0]
        for other in paths[1:]:
            record_duplicate(cfg, conn, base, other, "same_name_and_size", int(group["size"] or 0), None)
            noted += 1
    return noted


def scan_hash_duplicates(cfg: Config, conn: sqlite3.Connection) -> int:
    groups = conn.execute(
        """
        SELECT sha256_1mb, size
        FROM nas_index
        WHERE ifnull(sha256_1mb,'') != ''
        GROUP BY sha256_1mb
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    noted = 0
    for group in groups:
        paths = [
            str(row["original_path"])
            for row in conn.execute(
                "SELECT original_path FROM nas_index WHERE sha256_1mb=? ORDER BY original_path",
                (group["sha256_1mb"],),
            ).fetchall()
        ]
        if len(paths) < 2:
            continue
        base = paths[0]
        for other in paths[1:]:
            record_duplicate(
                cfg, conn, base, other, "same_sha256_1mb", int(group["size"] or 0), str(group["sha256_1mb"])
            )
            noted += 1
    return noted


def upsert_manifest_row(
    conn: sqlite3.Connection,
    *,
    path: str,
    filename: str,
    kind: str,
    size: int,
    mtime_epoch: int,
    rel: str,
    slug: str,
    confidence: str,
    root_name: str,
) -> None:
    try:
        mtime = datetime.fromtimestamp(mtime_epoch, TZ).isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        mtime = ""
    conn.execute(
        """
        INSERT INTO nas_index (
          original_path, original_filename, rel, size, mtime,
          sha256_1mb, hash_partial, source_root, folder_evidence,
          rights, classification, indexed_at, data_lane,
          brand_slug, index_state, map_confidence, thumb_ready
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(original_path) DO UPDATE SET
          original_filename=excluded.original_filename,
          rel=excluded.rel,
          size=excluded.size,
          mtime=excluded.mtime,
          source_root=excluded.source_root,
          folder_evidence=excluded.folder_evidence,
          classification=excluded.classification,
          brand_slug=CASE
            WHEN nas_index.index_state IN ('FAILED','HASHED','SEARCHABLE','THUMB_PREVIEW_READY','THUMBNAIL_READY')
            THEN nas_index.brand_slug
            ELSE excluded.brand_slug
          END,
          map_confidence=CASE
            WHEN nas_index.index_state IN ('FAILED','HASHED','SEARCHABLE','THUMB_PREVIEW_READY','THUMBNAIL_READY')
            THEN nas_index.map_confidence
            ELSE excluded.map_confidence
          END,
          index_state=CASE
            WHEN ifnull(nas_index.index_state,'') IN ('','DISCOVERED') THEN 'INDEXED'
            ELSE nas_index.index_state
          END,
          indexed_at=excluded.indexed_at
        """,
        (
            path,
            filename,
            rel,
            size,
            mtime,
            "",
            0,
            root_name,
            rel.split("/", 1)[0] if rel else "",
            "UNKNOWN",
            kind,
            now_iso(),
            "operational",
            slug,
            "INDEXED",
            confidence,
            0,
        ),
    )


def ingest_batch(cfg: Config, conn: sqlite3.Connection, aliases: dict[str, str], start_line: int) -> tuple[int, bool]:
    """Consume the next manifest lines. Returns (new_line, finished)."""
    if not cfg.manifest.is_file():
        raise FileNotFoundError(f"manifest missing: {cfg.manifest}")
    processed = 0
    finished = False
    line_no = 0
    with cfg.manifest.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line_no += 1
            if line_no <= start_line:
                continue
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < 8:
                append_jsonl(cfg.failures, {"at": now_iso(), "path": "", "reason": f"bad_manifest_line_{line_no}"})
                processed += 1
                if processed >= cfg.ingest_batch:
                    break
                continue
            path, filename, kind, size_s, mtime_s, _manifest_brand, _manifest_conf, root = parts[:8]
            try:
                size = int(size_s)
                mtime_epoch = int(mtime_s)
            except ValueError:
                append_jsonl(cfg.failures, {"at": now_iso(), "path": path, "reason": "bad_manifest_numbers"})
                processed += 1
                if processed >= cfg.ingest_batch:
                    break
                continue
            root_name = Path(root).name
            try:
                rel = str(Path(path).relative_to(root)) if root and path.startswith(root) else Path(path).name
            except ValueError:
                rel = Path(path).name
            rel = rel.replace("\\", "/")
            folder_parts = [] if rel in ("", ".") else list(Path(rel).parent.parts)
            slug, confidence = brand_for(folder_parts, aliases, root_name)
            upsert_manifest_row(
                conn,
                path=path,
                filename=filename or Path(path).name,
                kind=kind or "",
                size=size,
                mtime_epoch=mtime_epoch,
                rel=rel,
                slug=slug,
                confidence=confidence,
                root_name=root_name,
            )
            processed += 1
            if processed >= cfg.ingest_batch:
                break
        else:
            finished = True
    conn.commit()
    return start_line + processed, finished or processed == 0


def thumb_dest_for(row_id: int) -> Path:
    override = os.environ.get("NAS_THUMB_DIR")
    if override:
        root = Path(override)
        dest = root / f"nas-{int(row_id)}.jpg"
    else:
        root = repair.THUMB_DIR
        dest = repair.nas_thumb_path(row_id)
    refuse_nas_write(dest)
    root.mkdir(parents=True, exist_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    resolved = dest.resolve()
    resolved.relative_to(root.resolve())
    return resolved


def write_local_thumb(src: Path, dest: Path) -> bool:
    """ffmpeg or sips into the existing thumb cache. Source is opened read-only by the tools."""
    refuse_nas_write(dest)
    ext = src.suffix.lower()
    if ext in IMAGE_EXT:
        proc = subprocess.run(
            ["sips", "-s", "format", "jpeg", "-Z", "480", str(src), "--out", str(dest)],
            capture_output=True,
            timeout=20,
            check=False,
        )
        if proc.returncode == 0 and dest.is_file() and dest.stat().st_size > 32:
            return True
        return repair.write_jpeg_thumb(src, dest)
    if ext in VIDEO_EXT:
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-ss", "0.4", "-i", str(src),
                "-frames:v", "1", "-vf", "scale=480:-1", str(dest),
            ],
            capture_output=True,
            timeout=25,
            check=False,
        )
        return proc.returncode == 0 and dest.is_file() and dest.stat().st_size > 32
    return False


def thumb_batch(cfg: Config, conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT id, original_path, original_filename, classification
        FROM nas_index
        WHERE index_state='INDEXED'
        ORDER BY CASE
            WHEN ifnull(fail_reason,'') LIKE 'missing_file:transient%' THEN 1
            ELSE 0
          END,
          id
        LIMIT ?
        """,
        (cfg.thumb_batch,),
    ).fetchall()
    conn.commit()
    done = 0
    for row in rows:
        row_id = int(row["id"])
        stored = str(row["original_path"] or "")
        resolved = resolve_media_path(stored)
        if resolved.transient:
            conn.execute(
                """
                UPDATE nas_index SET fail_reason=?
                WHERE id=? AND index_state='INDEXED'
                """,
                (resolved.reason[:300], row_id),
            )
            conn.commit()
            continue
        if resolved.path is None:
            mark_failed(cfg, conn, row_id, stored, resolved.reason)
            conn.commit()
            done += 1
            continue
        adopted, clash = remember_resolved_path(cfg, conn, row_id, stored, resolved.path)
        if clash:
            mark_failed(cfg, conn, row_id, stored, clash)
            conn.commit()
            done += 1
            continue
        src = Path(adopted)
        ext = src.suffix.lower()
        try:
            if ext not in IMAGE_EXT and ext not in VIDEO_EXT:
                conn.execute(
                    """
                    UPDATE nas_index
                    SET index_state='SEARCHABLE', preview_note='no_raster_preview',
                        thumb_ready=0, fail_reason=NULL
                    WHERE id=? AND index_state='INDEXED'
                    """,
                    (row_id,),
                )
                conn.commit()
                done += 1
                continue
            dest = thumb_dest_for(row_id)
            if dest.is_file() and dest.stat().st_size > 32:
                ok = True
            else:
                ok = write_local_thumb(src, dest)
            if ok:
                conn.execute(
                    """
                    UPDATE nas_index
                    SET index_state='THUMB_PREVIEW_READY', thumb_ready=1, fail_reason=NULL
                    WHERE id=? AND index_state='INDEXED'
                    """,
                    (row_id,),
                )
            else:
                mark_failed(cfg, conn, row_id, str(src), "thumb_failed")
        except subprocess.TimeoutExpired:
            mark_failed(cfg, conn, row_id, str(src), "thumb_timeout")
        except Exception as exc:  # noqa: BLE001 — one bad file must not stop the run
            mark_failed(cfg, conn, row_id, str(src), f"thumb_error:{type(exc).__name__}")
        conn.commit()
        done += 1
    return done


def promote_searchable(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """
        UPDATE nas_index
        SET index_state='SEARCHABLE'
        WHERE index_state IN ('THUMB_PREVIEW_READY', 'THUMBNAIL_READY')
        """
    )
    conn.commit()
    return int(cur.rowcount or 0)


def hash_batch(cfg: Config, conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT id, original_path, size
        FROM nas_index
        WHERE index_state='SEARCHABLE'
        ORDER BY id
        LIMIT ?
        """,
        (cfg.hash_batch,),
    ).fetchall()
    conn.commit()
    done = 0
    for row in rows:
        row_id = int(row["id"])
        stored = str(row["original_path"] or "")
        resolved = resolve_media_path(stored)
        try:
            if resolved.transient:
                conn.execute(
                    "UPDATE nas_index SET fail_reason=? WHERE id=? AND index_state='SEARCHABLE'",
                    (resolved.reason[:300], row_id),
                )
                conn.commit()
                continue
            if resolved.path is None:
                mark_failed(cfg, conn, row_id, stored, resolved.reason)
                conn.commit()
                done += 1
                continue
            adopted, clash = remember_resolved_path(cfg, conn, row_id, stored, resolved.path)
            if clash:
                mark_failed(cfg, conn, row_id, stored, clash)
                conn.commit()
                done += 1
                continue
            src = Path(adopted)
            digest, partial = nas.sha256_file(src, max_bytes=HASH_BYTES)
            conn.execute(
                """
                UPDATE nas_index
                SET sha256_1mb=?, hash_partial=?, index_state='HASHED'
                WHERE id=? AND index_state='SEARCHABLE'
                """,
                (digest, 1 if partial else 0, row_id),
            )
        except Exception as exc:  # noqa: BLE001
            mark_failed(cfg, conn, row_id, stored, f"hash_error:{type(exc).__name__}")
        conn.commit()
        done += 1
    return done


def remaining_work(conn: sqlite3.Connection) -> dict[str, int]:
    out = {}
    for state in ("INDEXED", "THUMB_PREVIEW_READY", "THUMBNAIL_READY", "SEARCHABLE"):
        out[state] = int(
            conn.execute("SELECT COUNT(*) FROM nas_index WHERE index_state=?", (state,)).fetchone()[0]
        )
    return out


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_pid(cfg: Config) -> bool:
    cfg.estate.mkdir(parents=True, exist_ok=True)
    if cfg.pid_path.is_file():
        try:
            existing = int(cfg.pid_path.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            existing = 0
        if existing and existing != os.getpid() and pid_alive(existing):
            log_line(cfg, f"already running pid={existing}")
            return False
    cfg.pid_path.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    return True


def release_pid(cfg: Config) -> None:
    if not cfg.pid_path.is_file():
        return
    try:
        current = int(cfg.pid_path.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        current = 0
    if current == os.getpid():
        cfg.pid_path.unlink(missing_ok=True)


def run(cfg: Config | None = None) -> dict:
    cfg = cfg or production_config()
    cfg.estate.mkdir(parents=True, exist_ok=True)
    if not acquire_pid(cfg):
        return {"ok": True, "already_running": True, "staff_ready": False, "full_nas_complete": False}
    conn = connect(cfg)
    aliases = load_aliases(conn)
    checkpoint = load_checkpoint(cfg)
    manifest_bytes = cfg.manifest.stat().st_size if cfg.manifest.is_file() else 0
    line = int(checkpoint.get("manifest_line") or 0)
    if int(checkpoint.get("manifest_bytes") or -1) != manifest_bytes:
        line = 0
    healed = requeue_resolved_failures(cfg, conn)
    log_line(
        cfg,
        "requeue "
        f"resolved={healed['requeued']} missing={healed['still_missing']} transient={healed['transient']}",
    )
    write_counts(cfg, conn, phase="requeue", manifest_line=line)
    total_lines = _manifest_lines(cfg)
    name_dupes_done = bool(checkpoint.get("name_dupes_done")) and line != 0 and line >= total_lines
    phase = "ingest"
    try:
        while True:
            if cfg.manifest.is_file() and line < total_lines:
                phase = "ingest"
                line, _finished = ingest_batch(cfg, conn, aliases, line)
                save_checkpoint(cfg, {
                    "phase": phase,
                    "manifest_line": line,
                    "manifest_bytes": manifest_bytes,
                    "name_dupes_done": False,
                })
                name_dupes_done = False
                write_counts(cfg, conn, phase=phase, manifest_line=line)
                log_line(cfg, f"ingest line={line}")
                continue
            if not name_dupes_done:
                phase = "duplicates"
                noted = scan_name_duplicates(cfg, conn)
                conn.commit()
                name_dupes_done = True
                save_checkpoint(cfg, {
                    "phase": phase,
                    "manifest_line": line,
                    "manifest_bytes": manifest_bytes,
                    "name_dupes_done": True,
                })
                log_line(cfg, f"name duplicate candidates recorded groups_pairs={noted}")
                write_counts(cfg, conn, phase=phase, manifest_line=line)
            thumbed = thumb_batch(cfg, conn)
            promoted = promote_searchable(conn)
            hashed = hash_batch(cfg, conn)
            work = remaining_work(conn)
            phase = "enrich" if any(work.values()) else "caught_up"
            save_checkpoint(cfg, {
                "phase": phase,
                "manifest_line": line,
                "manifest_bytes": manifest_bytes,
                "name_dupes_done": True,
                "remaining": work,
            })
            if hashed or thumbed or promoted:
                write_counts(cfg, conn, phase=phase, manifest_line=line)
                log_line(cfg, f"enrich thumbs={thumbed} hashes={hashed} promoted={promoted} remaining={work}")
            if phase == "caught_up":
                scan_hash_duplicates(cfg, conn)
                conn.commit()
                counts = write_counts(cfg, conn, phase=phase, manifest_line=line)
                log_line(cfg, f"caught up catalog_rows={counts.get('catalog_rows')} failed={counts.get('failed')}")
                counts["ok"] = True
                counts["already_running"] = False
                return counts
            if thumbed == 0 and hashed == 0 and promoted == 0:
                time.sleep(1)
    finally:
        conn.close()
        release_pid(cfg)


def _manifest_lines(cfg: Config) -> int:
    if not cfg.manifest.is_file():
        return 0
    count = 0
    with cfg.manifest.open("r", encoding="utf-8", errors="replace") as handle:
        for _ in handle:
            count += 1
    return count


def main() -> None:
    def _stop(_signum, _frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        result = run()
    except Exception as exc:  # noqa: BLE001
        cfg = production_config()
        log_line(cfg, f"indexer error {type(exc).__name__}: {exc}")
        release_pid(cfg)
        raise
    if result.get("already_running"):
        print("already running")
        return
    print(
        f"phase={result.get('phase')} catalog_rows={result.get('catalog_rows')} "
        f"failed={result.get('failed')} staff_ready=false full_nas_complete=false"
    )


if __name__ == "__main__":
    main()
