#!/usr/bin/env python3
"""Wolf NAS Library — source registry + safe index + canonical placement (Beta).

Serves RULE-Wolf-Connection-Commissioning-NAS-GoLive-2026-09-22,
GROK-PLAN-WOLF-NAS-LIBRARY-UPLOAD-P0-2026-09-22, and
GROK-PLAN-WOLF-NAS-INDEX-CONTINUE-2026-09-22.

NAS = canonical operational media. Wolf = staff UI. B2 = backup/DR (observe only).
Never bulk rename/move/delete/reorganise/overwrite/destructively dedupe NAS.
nas_received=true only when the file is really on NAS (exists + size match).
Index continue = READ-only DISCOVER→INVENTORY→HASH→INDEX; never mutate NAS trees.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Makassar")
BETA_ROOT = Path(__file__).resolve().parents[2]
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
INDEX_DIR = BETA_ROOT / "state" / "nas-index"
WOLF_UPLOAD_ROOT_NAME = "Wolf-Library"
TEST_MARKER = "_test"

# Canonical ops media root (OWNER approved READ/WRITE for Wolf Library/upload only)
MEDIA_LIBRARY = Path("/Volumes/01-Media-Library")

# Safe READ-only sample tops (never write here; never touch archive)
SAFE_SAMPLE_TOP_FOLDERS: tuple[str, ...] = (
    "Brand-Assets",
    "_Imports",
    "AMG",
    "AMG-Atrium",
    "BZG",
    "GGV",
    "Clients",
    "_Shared",
)

# Beyond Brand-Assets / _Imports — index-continue slice
CONTINUE_TOP_FOLDERS: tuple[str, ...] = (
    "AMG",
    "AMG-Atrium",
    "BZG",
    "GGV",
    "Clients",
    "_Shared",
)

# Optional READ-only leftover top — sample only; never mutate / never invent files
NEEDS_SORTING_TOP = "_needs_sorting"
OPERATOR_BROWSE_TOP_FOLDERS: tuple[str, ...] = SAFE_SAMPLE_TOP_FOLDERS + (NEEDS_SORTING_TOP,)

# Hard refuse — never sample / never invent
REFUSED_SAMPLE_TOPS: frozenset[str] = frozenset(
    {"#recycle", "_clickup-attachment-archive"}
)

# Extension → media type for operator facets (evidence from filename only)
MEDIA_TYPE_EXTENSIONS: dict[str, frozenset[str]] = {
    "image": frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".svg", ".heic"}),
    "video": frozenset({".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}),
    "audio": frozenset({".mp3", ".m4a", ".wav", ".aac", ".flac"}),
    "document": frozenset({".pdf", ".doc", ".docx", ".txt", ".md", ".csv", ".xlsx"}),
}

# Top-folder → scopes that may see that tree (SCOPE-WOLF-GROUP always allowed)
FOLDER_SCOPES: dict[str, frozenset[str]] = {
    "AMG": frozenset({"SCOPE-AMG"}),
    "AMG-Atrium": frozenset({"SCOPE-AMG"}),
    "BZG": frozenset({"SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA"}),
    "GGV": frozenset({"SCOPE-GGV", "SCOPE-GGV-CONTENT"}),
    # Mixed trees — further filtered by path brand tokens
    "Brand-Assets": frozenset(
        {"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-AMG", "SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA"}
    ),
    "_Imports": frozenset(
        {"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-AMG", "SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA"}
    ),
    "Clients": frozenset(
        {"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-AMG", "SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA"}
    ),
    "_Shared": frozenset(
        {"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-AMG", "SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA"}
    ),
    # Leftover sorting bin — mixed; further filtered by brand tokens when present
    "_needs_sorting": frozenset(
        {"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-AMG", "SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA"}
    ),
}

# Read-only registry of mounts (evidence names — not automatic facts)
NAS_ROOTS: tuple[dict[str, str], ...] = (
    {
        "id": "01-Media-Library",
        "path": "/Volumes/01-Media-Library",
        "role": "canonical_operational_media",
        "wolf_library_target": "true",
    },
    {
        "id": "00-Editing-Workspace",
        "path": "/Volumes/00-Editing-Workspace",
        "role": "editing_scratch",
        "wolf_library_target": "false",
    },
    {
        "id": "02-Stock-Assets",
        "path": "/Volumes/02-Stock-Assets",
        "role": "stock",
        "wolf_library_target": "false",
    },
    {
        "id": "03-Templates",
        "path": "/Volumes/03-Templates",
        "role": "templates",
        "wolf_library_target": "false",
    },
    {
        "id": "04-Time-Machine",
        "path": "/Volumes/04-Time-Machine",
        "role": "time_machine",
        "wolf_library_target": "false",
    },
    {
        "id": "05-Wolf-Vault-Mirror",
        "path": "/Volumes/05-Wolf-Vault-Mirror",
        "role": "vault_mirror",
        "wolf_library_target": "false",
    },
)

# Content-only grant. Maps to the eight content brands. It is not finance, HR, leads, or ops.
CONTENT_ALL_BRANDS_SCOPE = "SCOPE-WOLF-CONTENT-ALL-BRANDS"

# Content brand → allowed Wolf scopes (Person→Role→Assignment→Scope…)
BRAND_SCOPES: dict[str, frozenset[str]] = {
    "habitat": frozenset({"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
    "selo": frozenset({"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
    "tropik": frozenset({"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
    "theone": frozenset({"SCOPE-GGV", "SCOPE-GGV-CONTENT", "SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
    "umablu": frozenset({"SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA", "SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
    "rainforest": frozenset({"SCOPE-BZG-ENTITY", "SCOPE-BZG-UMA", "SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
    "atrium": frozenset({"SCOPE-AMG", "SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
    # Holding brand stays off ordinary content scopes. The content-all scope is the Owner grant.
    "goss": frozenset({"SCOPE-WOLF-GROUP", CONTENT_ALL_BRANDS_SCOPE}),
}

# Folders Wolf may CREATE under (additive only). Never touch other NAS trees.
ALLOWED_WRITE_PREFIX = MEDIA_LIBRARY / "_Imports" / WOLF_UPLOAD_ROOT_NAME

HONESTY = {
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "nas_destructive": False,
    "invented_proven": False,
    "invented_ready": False,
}


class NasLibraryError(ValueError):
    def __init__(self, message: str, *, code: str = "nas_library_error", http: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http = http


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def media_library_connected() -> bool:
    try:
        return MEDIA_LIBRARY.exists() and MEDIA_LIBRARY.is_dir()
    except OSError:
        return False


def indexing_state_from_disk() -> dict[str, Any]:
    """Honesty about what Beta has sampled — never claim full tree."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    manifests = sorted(INDEX_DIR.glob("sample-*.manifest.json"))
    folders: dict[str, int] = {}
    for man in manifests:
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        folder = data.get("sample_folder") or data.get("folder") or ""
        n = int(data.get("files_indexed") or data.get("files") or 0)
        if folder:
            try:
                rel = str(Path(folder).resolve().relative_to(MEDIA_LIBRARY.resolve()))
            except (ValueError, OSError):
                rel = Path(folder).name
            top = rel.split("/", 1)[0] if rel else Path(folder).name
            folders[top] = folders.get(top, 0) + n
        by = data.get("by_folder") or {}
        if isinstance(by, dict):
            for name, meta in by.items():
                if isinstance(meta, dict):
                    folders[str(name)] = folders.get(str(name), 0) + int(
                        meta.get("files_indexed") or 0
                    )
    continue_folders = [f for f in CONTINUE_TOP_FOLDERS if folders.get(f, 0) > 0]
    return {
        "sample_manifests": len(manifests),
        "folders_with_counts": folders,
        "continue_folders_indexed": continue_folders,
        "full_tree_indexed": False,
        "note": "Partial capped samples only — full ~40k tree UNKNOWN / not claimed",
        "staff_ready": False,
    }


def registry() -> dict[str, Any]:
    """Read-only NAS source registry. Unknown stays UNKNOWN."""
    roots_out: list[dict[str, Any]] = []
    for row in NAS_ROOTS:
        p = Path(row["path"])
        connected = False
        try:
            connected = p.exists() and p.is_dir()
        except OSError:
            connected = False
        roots_out.append(
            {
                **row,
                "connected": connected,
                "evidence": "mounted" if connected else "UNKNOWN",
            }
        )
    media = next((r for r in roots_out if r["id"] == "01-Media-Library"), None)
    return {
        "ok": True,
        "bound": "beta-nas-index-continue",
        "canonical_root": str(MEDIA_LIBRARY),
        "canonical_connected": bool(media and media["connected"]),
        "wolf_write_prefix": str(ALLOWED_WRITE_PREFIX),
        "safe_sample_top_folders": list(SAFE_SAMPLE_TOP_FOLDERS),
        "continue_top_folders": list(CONTINUE_TOP_FOLDERS),
        "operator_browse_top_folders": list(OPERATOR_BROWSE_TOP_FOLDERS),
        "refused_sample_tops": sorted(REFUSED_SAMPLE_TOPS),
        "needs_sorting_readonly": True,
        "indexing_state": indexing_state_from_disk(),
        "roots": roots_out,
        "honesty": dict(HONESTY),
        "destructive": False,
        "full_tree_indexed": False,
        "staff_ready": False,
        "haikal_human": "not_started",
    }


def _ensure_under_write_prefix(path: Path) -> Path:
    """Jail writes/reads of Wolf placements under _Imports/Wolf-Library only."""
    resolved = path.resolve()
    prefix = ALLOWED_WRITE_PREFIX.resolve()
    try:
        resolved.relative_to(prefix)
    except ValueError as exc:
        raise NasLibraryError(
            "path escapes Wolf-Library write prefix",
            code="nas_path_jail",
            http=403,
        ) from exc
    return resolved


def _ensure_under_media(path: Path) -> Path:
    """Jail read-only inventory under 01-Media-Library."""
    resolved = path.resolve()
    root = MEDIA_LIBRARY.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise NasLibraryError(
            "path escapes Media Library",
            code="nas_path_jail",
            http=403,
        ) from exc
    return resolved


def sha256_file(path: Path, *, max_bytes: int | None = None) -> tuple[str, bool]:
    """Return (hex, partial). partial=True when only first max_bytes hashed."""
    h = hashlib.sha256()
    partial = False
    total = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            if max_bytes is not None and total + len(chunk) > max_bytes:
                remain = max_bytes - total
                if remain > 0:
                    h.update(chunk[:remain])
                partial = True
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), partial


def _safe_top_folder_name(name: str) -> str:
    name = (name or "").strip().strip("/")
    if not name or "/" in name or name.startswith("."):
        raise NasLibraryError("invalid sample folder", code="nas_folder_invalid", http=400)
    if name in REFUSED_SAMPLE_TOPS:
        raise NasLibraryError(
            f"folder refused for sample: {name}",
            code="nas_folder_refused",
            http=403,
        )
    if name not in SAFE_SAMPLE_TOP_FOLDERS:
        raise NasLibraryError(
            f"folder not in safe sample set: {name}",
            code="nas_folder_not_safe",
            http=403,
        )
    return name


def media_type_from_filename(name: str | None) -> str:
    """Infer media type from extension — evidence only, not classification fact."""
    ext = Path(name or "").suffix.lower()
    if not ext:
        return "unknown"
    for media_type, exts in MEDIA_TYPE_EXTENSIONS.items():
        if ext in exts:
            return media_type
    return "other"


def extension_from_filename(name: str | None) -> str:
    return Path(name or "").suffix.lower() or ""


def _public_index_row(d: dict[str, Any]) -> dict[str, Any]:
    """Client-safe nas_index row — relative paths only, never /Volumes/."""
    rel = d.get("rel") or ""
    top = top_folder_from_rel(rel)
    fname = d.get("original_filename")
    return {
        "id": d.get("id"),
        "original_filename": fname,
        "rel": rel,
        "size": d.get("size"),
        "mtime": d.get("mtime"),
        "content_hash_partial": d.get("sha256_1mb") or d.get("content_hash_partial"),
        "hash_partial": bool(d.get("hash_partial")),
        "source_root": d.get("source_root"),
        "folder_evidence": d.get("folder_evidence"),
        "top_folder": top,
        "brand_token": infer_brand_token(rel),
        "media_type": media_type_from_filename(fname),
        "extension": extension_from_filename(fname),
        "rights": d.get("rights") or "UNKNOWN",
        "classification": d.get("classification") or "UNKNOWN",
        "indexed_at": d.get("indexed_at"),
        "provenance": "nas_index_sample",
    }


def _folder_slug(sample_folder: Path | str) -> str:
    p = Path(sample_folder)
    try:
        rel = str(p.resolve().relative_to(MEDIA_LIBRARY.resolve()))
    except (ValueError, OSError):
        rel = p.name
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", rel).strip("-").lower() or "unknown"
    return slug[:80]


def top_folder_from_rel(rel: str) -> str:
    return (rel or "").replace("\\", "/").strip("/").split("/", 1)[0]


def infer_brand_token(rel: str) -> str | None:
    """Best-effort brand token from relative path (evidence, not fact)."""
    parts = [p.lower() for p in (rel or "").replace("\\", "/").split("/") if p]
    joined = "/".join(parts)
    mapping = (
        ("habitat", "habitat"),
        ("selo", "selo"),
        ("selong", "selo"),
        ("tropik", "tropik"),
        ("uma-blu", "umablu"),
        ("umablu", "umablu"),
        ("atrium", "atrium"),
        ("surga", "atrium"),
        ("amg-atrium", "atrium"),
        ("rainforest", "rainforest"),
        ("the-one", "theone"),
        ("theone", "theone"),
        ("goss", "goss"),
        ("ggv", "habitat"),
        ("bzg", "umablu"),
        ("amg", "atrium"),
    )
    for needle, brand in mapping:
        if needle in parts or f"/{needle}/" in f"/{joined}/":
            return brand
    return None


def scopes_allow_folder(scopes: list[str] | set[str] | None, folder: str) -> bool:
    have = {str(s).strip() for s in (scopes or []) if str(s).strip()}
    if "SCOPE-WOLF-GROUP" in have:
        return True
    allowed = FOLDER_SCOPES.get(folder)
    if not allowed:
        return False
    return bool(have & allowed)


def scopes_allow_nas_rel(scopes: list[str] | set[str] | None, rel: str) -> bool:
    """Four-layer honesty: folder gate + brand token when path implies a brand."""
    have = {str(s).strip() for s in (scopes or []) if str(s).strip()}
    if "SCOPE-WOLF-GROUP" in have:
        return True
    top = top_folder_from_rel(rel)
    if not scopes_allow_folder(have, top):
        return False
    brand = infer_brand_token(rel)
    if brand:
        return scopes_allow_brand(have, brand)
    # Mixed folder without clear brand — require overlapping folder scopes only
    return True


def inventory_sample(
    *,
    folder: Path | None = None,
    cap: int = 200,
    hash_max_bytes: int = 1_048_576,
) -> dict[str, Any]:
    """READ-only sample inventory. Does not mutate NAS files."""
    if not media_library_connected():
        return {
            "ok": False,
            "error": "nas_not_connected",
            "files_indexed": 0,
            "items": [],
            "destructive": False,
        }
    sample_folder = folder or (MEDIA_LIBRARY / "Brand-Assets")
    sample_folder = _ensure_under_media(sample_folder)
    if not sample_folder.is_dir():
        return {
            "ok": False,
            "error": "sample_folder_missing",
            "sample_folder": str(sample_folder),
            "files_indexed": 0,
            "items": [],
            "destructive": False,
        }
    items: list[dict[str, Any]] = []
    for root, dirnames, filenames in os.walk(sample_folder):
        # Skip recycle / hidden system dirs
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "#recycle"]
        for name in filenames:
            if name.startswith("."):
                continue
            fp = Path(root) / name
            try:
                st = fp.stat()
            except OSError:
                continue
            if not fp.is_file():
                continue
            rel = str(fp.relative_to(MEDIA_LIBRARY))
            try:
                digest, partial = sha256_file(fp, max_bytes=hash_max_bytes)
            except OSError:
                digest, partial = "", True
            items.append(
                {
                    "original_path": str(fp),
                    "original_filename": name,
                    "rel": rel,
                    "size": int(st.st_size),
                    "mtime": datetime.fromtimestamp(st.st_mtime, TZ).isoformat(timespec="seconds"),
                    "sha256_1mb": digest,
                    "hash_partial": partial,
                    "source_root": "01-Media-Library",
                    "folder_evidence": str(sample_folder.relative_to(MEDIA_LIBRARY)),
                    "rights": "UNKNOWN",
                    "classification": "UNKNOWN",
                }
            )
            if len(items) >= cap:
                break
        if len(items) >= cap:
            break
    return {
        "ok": True,
        "sampled_at": now_iso(),
        "root": str(MEDIA_LIBRARY),
        "sample_folder": str(sample_folder),
        "files_indexed": len(items),
        "cap": cap,
        "destructive": False,
        "items": items,
        "note": "READ-only sample; full tree not scanned; hash may be partial first 1MB",
        "honesty": dict(HONESTY),
    }


def inventory_continue(
    *,
    folders: list[str] | None = None,
    per_folder_cap: int = 25,
    hash_max_bytes: int = 1_048_576,
) -> dict[str, Any]:
    """READ-only multi-folder sample beyond Brand-Assets/_Imports. Never mutates NAS."""
    if not media_library_connected():
        return {
            "ok": False,
            "error": "nas_not_connected",
            "files_indexed": 0,
            "by_folder": {},
            "items": [],
            "destructive": False,
        }
    names = folders or list(CONTINUE_TOP_FOLDERS)
    by_folder: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    for raw in names:
        name = _safe_top_folder_name(raw)
        sample = inventory_sample(
            folder=MEDIA_LIBRARY / name,
            cap=per_folder_cap,
            hash_max_bytes=hash_max_bytes,
        )
        by_folder[name] = {
            "ok": bool(sample.get("ok")),
            "files_indexed": int(sample.get("files_indexed") or 0),
            "error": sample.get("error"),
            "cap": per_folder_cap,
        }
        items.extend(sample.get("items") or [])
    return {
        "ok": True,
        "sampled_at": now_iso(),
        "root": str(MEDIA_LIBRARY),
        "mode": "continue",
        "folders": list(by_folder.keys()),
        "by_folder": by_folder,
        "files_indexed": len(items),
        "per_folder_cap": per_folder_cap,
        "destructive": False,
        "items": items,
        "note": (
            "READ-only continue sample; full tree not scanned; "
            "hash may be partial first 1MB; staff_ready=false"
        ),
        "honesty": dict(HONESTY),
    }


def persist_sample_index(sample: dict[str, Any] | None = None, *, cap: int = 200) -> dict[str, Any]:
    """Write sample JSONL under state/nas-index (Beta). Does not mutate NAS."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    sample = sample or inventory_sample(cap=cap)
    stamp = datetime.now(TZ).strftime("%Y%m%d")
    folder_path = sample.get("sample_folder") or "Brand-Assets"
    slug = _folder_slug(folder_path)
    jsonl = INDEX_DIR / f"sample-{slug}-{stamp}.jsonl"
    manifest = INDEX_DIR / f"sample-{slug}-{stamp}.manifest.json"
    with jsonl.open("w", encoding="utf-8") as fh:
        for item in sample.get("items") or []:
            # Never persist absolute path into client-facing exports — keep for local Beta only
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    man = {k: v for k, v in sample.items() if k != "items"}
    manifest.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "jsonl": str(jsonl), "manifest": str(manifest), **man}


def persist_continue_index(
    sample: dict[str, Any] | None = None,
    *,
    per_folder_cap: int = 25,
) -> dict[str, Any]:
    """Persist per-folder + combined continue manifests under state/nas-index."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    sample = sample or inventory_continue(per_folder_cap=per_folder_cap)
    stamp = datetime.now(TZ).strftime("%Y%m%d")
    written: list[dict[str, str]] = []
    # Group items by top folder for per-folder artifacts
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in sample.get("items") or []:
        top = top_folder_from_rel(str(item.get("rel") or ""))
        grouped.setdefault(top, []).append(item)
    for top, group in grouped.items():
        slug = _folder_slug(MEDIA_LIBRARY / top)
        jsonl = INDEX_DIR / f"sample-{slug}-{stamp}.jsonl"
        manifest = INDEX_DIR / f"sample-{slug}-{stamp}.manifest.json"
        with jsonl.open("w", encoding="utf-8") as fh:
            for item in group:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        man = {
            "ok": True,
            "sampled_at": sample.get("sampled_at") or now_iso(),
            "root": str(MEDIA_LIBRARY),
            "sample_folder": str(MEDIA_LIBRARY / top),
            "folder": top,
            "files_indexed": len(group),
            "cap": per_folder_cap,
            "destructive": False,
            "mode": "continue",
            "honesty": dict(HONESTY),
            "note": "READ-only continue sample; NAS files not mutated",
        }
        manifest.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append({"folder": top, "jsonl": str(jsonl), "manifest": str(manifest)})
    combined = INDEX_DIR / f"sample-continue-{stamp}.manifest.json"
    combined_body = {k: v for k, v in sample.items() if k != "items"}
    combined_body["written"] = written
    combined.write_text(json.dumps(combined_body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "combined_manifest": str(combined),
        "written": written,
        **combined_body,
    }


def migrate_schema(conn: sqlite3.Connection) -> list[str]:
    """Additive NAS columns on assets + nas_index table. Idempotent."""
    added: list[str] = []
    have = {r[1] for r in conn.execute("PRAGMA table_info(assets)").fetchall()}
    cols = [
        ("nas_path", "TEXT"),
        ("nas_rel", "TEXT"),
        ("nas_received", "INTEGER"),
        ("nas_received_at", "TEXT"),
        ("nas_verified_size", "INTEGER"),
        ("provenance_json", "TEXT"),
    ]
    for name, typ in cols:
        if name not in have:
            conn.execute(f"ALTER TABLE assets ADD COLUMN {name} {typ}")
            added.append(f"assets.{name}")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nas_index (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          original_path TEXT NOT NULL UNIQUE,
          original_filename TEXT,
          rel TEXT,
          size INTEGER,
          mtime TEXT,
          sha256_1mb TEXT,
          hash_partial INTEGER,
          source_root TEXT,
          folder_evidence TEXT,
          rights TEXT,
          classification TEXT,
          indexed_at TEXT,
          data_lane TEXT DEFAULT 'operational'
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_nas_index_rel ON nas_index(rel)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_assets_nas_received ON assets(nas_received)"
    )
    return added


def ingest_sample_to_catalog(
    conn: sqlite3.Connection,
    sample: dict[str, Any] | None = None,
    *,
    cap: int = 200,
) -> dict[str, Any]:
    """Index sample into Beta nas_index. Never mutates NAS files."""
    migrate_schema(conn)
    sample = sample or inventory_sample(cap=cap)
    if not sample.get("ok"):
        return sample
    indexed_at = now_iso()
    n = 0
    for item in sample.get("items") or []:
        conn.execute(
            """
            INSERT INTO nas_index (
              original_path, original_filename, rel, size, mtime,
              sha256_1mb, hash_partial, source_root, folder_evidence,
              rights, classification, indexed_at, data_lane
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(original_path) DO UPDATE SET
              size=excluded.size,
              mtime=excluded.mtime,
              sha256_1mb=excluded.sha256_1mb,
              hash_partial=excluded.hash_partial,
              folder_evidence=excluded.folder_evidence,
              indexed_at=excluded.indexed_at
            """,
            (
                item.get("original_path"),
                item.get("original_filename"),
                item.get("rel"),
                item.get("size"),
                item.get("mtime"),
                item.get("sha256_1mb"),
                1 if item.get("hash_partial") else 0,
                item.get("source_root"),
                item.get("folder_evidence"),
                item.get("rights") or "UNKNOWN",
                item.get("classification") or "UNKNOWN",
                indexed_at,
                "operational",
            ),
        )
        n += 1
    conn.commit()
    return {
        "ok": True,
        "rows_upserted": n,
        "sample_folder": sample.get("sample_folder"),
        "by_folder": sample.get("by_folder"),
        "destructive": False,
        "honesty": dict(HONESTY),
    }


def search_nas_index(
    conn: sqlite3.Connection,
    *,
    q: str = "",
    limit: int = 50,
    folder: str | None = None,
    brand_token: str | None = None,
    media_type: str | None = None,
    extension: str | None = None,
    recent: bool = True,
    scopes: list[str] | set[str] | None = None,
) -> list[dict[str, Any]]:
    migrate_schema(conn)
    limit = max(1, min(200, int(limit)))
    q = (q or "").strip().lower()
    folder = (folder or "").strip().strip("/") or None
    brand_token = (brand_token or "").strip().lower() or None
    media_type = (media_type or "").strip().lower() or None
    extension = (extension or "").strip().lower() or None
    if extension and not extension.startswith("."):
        extension = f".{extension}"
    if folder and folder in REFUSED_SAMPLE_TOPS:
        raise NasLibraryError(
            f"folder refused: {folder}",
            code="nas_folder_refused",
            http=403,
        )
    if folder and folder not in OPERATOR_BROWSE_TOP_FOLDERS:
        raise NasLibraryError(
            f"folder filter not safe: {folder}",
            code="nas_folder_not_safe",
            http=403,
        )
    if folder and scopes is not None and not scopes_allow_folder(scopes, folder):
        raise NasLibraryError(
            f"subject lacks scope for folder {folder}",
            code="nas_folder_forbidden",
            http=403,
        )
    if brand_token and scopes is not None and not scopes_allow_brand(scopes, brand_token):
        raise NasLibraryError(
            f"subject lacks scope for brand {brand_token}",
            code="nas_brand_forbidden",
            http=403,
        )
    # Over-fetch then scope-filter (paths are relative; no absolute leak)
    fetch_limit = min(800, max(limit * 6, limit))
    order = "ORDER BY indexed_at DESC, id DESC" if recent else "ORDER BY id DESC"
    if q:
        like = f"%{q}%"
        rows = conn.execute(
            f"""
            SELECT id, original_filename, rel, size, mtime, sha256_1mb, hash_partial,
                   source_root, folder_evidence, rights, classification, indexed_at
            FROM nas_index
            WHERE lower(ifnull(original_filename,'')) LIKE ?
               OR lower(ifnull(rel,'')) LIKE ?
            {order}
            LIMIT ?
            """,
            (like, like, fetch_limit),
        ).fetchall()
    else:
        rows = conn.execute(
            f"""
            SELECT id, original_filename, rel, size, mtime, sha256_1mb, hash_partial,
                   source_root, folder_evidence, rights, classification, indexed_at
            FROM nas_index
            {order}
            LIMIT ?
            """,
            (fetch_limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        rel = d.get("rel") or ""
        top = top_folder_from_rel(rel)
        if folder and top != folder and not rel.startswith(folder + "/"):
            # Also allow folder_evidence match
            fe = str(d.get("folder_evidence") or "")
            if fe != folder and not fe.startswith(folder + "/"):
                continue
        if scopes is not None and not scopes_allow_nas_rel(scopes, rel):
            continue
        pub = _public_index_row(d)
        if brand_token and (pub.get("brand_token") or "") != brand_token:
            continue
        if media_type and (pub.get("media_type") or "") != media_type:
            continue
        if extension and (pub.get("extension") or "") != extension:
            continue
        out.append(pub)
        if len(out) >= limit:
            break
    return out


def get_nas_index_object(
    conn: sqlite3.Connection,
    object_id: int | str,
    *,
    scopes: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Indexed object detail — relative path honesty + scope gate. Never /Volumes/."""
    migrate_schema(conn)
    try:
        oid = int(object_id)
    except (TypeError, ValueError) as exc:
        raise NasLibraryError("invalid nas_index id", code="nas_object_invalid", http=400) from exc
    row = conn.execute(
        """
        SELECT id, original_filename, rel, size, mtime, sha256_1mb, hash_partial,
               source_root, folder_evidence, rights, classification, indexed_at
        FROM nas_index WHERE id=?
        """,
        (oid,),
    ).fetchone()
    if row is None:
        raise NasLibraryError("nas_index object not found", code="nas_object_not_found", http=404)
    d = dict(row)
    rel = d.get("rel") or ""
    if scopes is not None and not scopes_allow_nas_rel(scopes, rel):
        raise NasLibraryError(
            "subject lacks scope for indexed object",
            code="nas_object_forbidden",
            http=403,
        )
    pub = _public_index_row(d)
    indexing = indexing_state_from_disk()
    return {
        "ok": True,
        "object": pub,
        "scope_gate": {
            "top_folder": pub.get("top_folder"),
            "brand_token": pub.get("brand_token"),
            "allowed": True,
        },
        "path_honesty": {
            "rel_only": True,
            "absolute_leaked": False,
            "volumes_forbidden": True,
        },
        "indexing_state": {
            "full_tree_indexed": False,
            "staff_ready": False,
            "sample_manifests": indexing.get("sample_manifests"),
            "note": indexing.get("note"),
        },
        "destructive": False,
        "honesty": dict(HONESTY),
    }


def browse_nas_index(
    conn: sqlite3.Connection,
    *,
    q: str = "",
    folder: str | None = None,
    brand_token: str | None = None,
    media_type: str | None = None,
    extension: str | None = None,
    limit: int = 50,
    recent: bool = True,
    scopes: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Operator browse/filter over Beta nas_index samples. EMPTY honesty when no rows."""
    items = search_nas_index(
        conn,
        q=q,
        limit=limit,
        folder=folder,
        brand_token=brand_token,
        media_type=media_type,
        extension=extension,
        recent=recent,
        scopes=scopes,
    )
    indexing = indexing_state_from_disk()
    empty = len(items) == 0
    return {
        "ok": True,
        "items": items,
        "count": len(items),
        "empty": empty,
        "empty_message": (
            "No indexed objects match these facets — EMPTY (partial sample; "
            "full_tree_indexed=false; not invent)."
            if empty
            else None
        ),
        "facets_applied": {
            "q": q or None,
            "folder": folder,
            "brand_token": brand_token,
            "media_type": media_type,
            "extension": extension,
            "recent": recent,
            "limit": limit,
        },
        "indexing_state": {
            "full_tree_indexed": False,
            "staff_ready": False,
            "folders_with_counts": indexing.get("folders_with_counts"),
            "continue_folders_indexed": indexing.get("continue_folders_indexed"),
            "sample_manifests": indexing.get("sample_manifests"),
            "note": indexing.get("note"),
        },
        "destructive": False,
        "honesty": dict(HONESTY),
    }


def nas_index_facets(
    conn: sqlite3.Connection,
    *,
    scopes: list[str] | set[str] | None = None,
    limit_scan: int = 500,
) -> dict[str, Any]:
    """Operator-useful facet lists from sampled nas_index (scope-gated)."""
    migrate_schema(conn)
    rows = conn.execute(
        """
        SELECT id, original_filename, rel, folder_evidence, indexed_at
        FROM nas_index
        ORDER BY indexed_at DESC, id DESC
        LIMIT ?
        """,
        (max(1, min(2000, int(limit_scan))),),
    ).fetchall()
    folders: dict[str, int] = {}
    brands: dict[str, int] = {}
    media_types: dict[str, int] = {}
    extensions: dict[str, int] = {}
    for r in rows:
        d = dict(r)
        rel = d.get("rel") or ""
        if scopes is not None and not scopes_allow_nas_rel(scopes, rel):
            continue
        top = top_folder_from_rel(rel)
        if top:
            folders[top] = folders.get(top, 0) + 1
        brand = infer_brand_token(rel)
        if brand:
            brands[brand] = brands.get(brand, 0) + 1
        mt = media_type_from_filename(d.get("original_filename"))
        media_types[mt] = media_types.get(mt, 0) + 1
        ext = extension_from_filename(d.get("original_filename"))
        if ext:
            extensions[ext] = extensions.get(ext, 0) + 1
    indexing = indexing_state_from_disk()
    return {
        "ok": True,
        "folders": [
            {"id": k, "count": v}
            for k, v in sorted(folders.items(), key=lambda x: (-x[1], x[0]))
        ],
        "brand_tokens": [
            {"id": k, "count": v}
            for k, v in sorted(brands.items(), key=lambda x: (-x[1], x[0]))
        ],
        "media_types": [
            {"id": k, "count": v}
            for k, v in sorted(media_types.items(), key=lambda x: (-x[1], x[0]))
        ],
        "extensions": [
            {"id": k, "count": v}
            for k, v in sorted(extensions.items(), key=lambda x: (-x[1], x[0]))
        ],
        "browse_tops": list(OPERATOR_BROWSE_TOP_FOLDERS),
        "refused_tops": sorted(REFUSED_SAMPLE_TOPS),
        "indexing_state": {
            "full_tree_indexed": False,
            "staff_ready": False,
            "sample_manifests": indexing.get("sample_manifests"),
        },
        "destructive": False,
        "honesty": dict(HONESTY),
    }


def inventory_needs_sorting_sample(
    *,
    cap: int = 25,
    hash_max_bytes: int = 1_048_576,
) -> dict[str, Any]:
    """READ-only capped sample of leftover top `_needs_sorting` only.

    Never mutates NAS. Refuses #recycle / _clickup-attachment-archive.
    EMPTY honesty when the folder has no files (do not invent).
    """
    if NEEDS_SORTING_TOP in REFUSED_SAMPLE_TOPS:
        raise NasLibraryError(
            "needs_sorting refused",
            code="nas_folder_refused",
            http=403,
        )
    if not media_library_connected():
        return {
            "ok": False,
            "error": "nas_not_connected",
            "folder": NEEDS_SORTING_TOP,
            "files_indexed": 0,
            "items": [],
            "empty": True,
            "destructive": False,
            "honesty": dict(HONESTY),
        }
    folder = MEDIA_LIBRARY / NEEDS_SORTING_TOP
    try:
        folder = _ensure_under_media(folder)
    except NasLibraryError:
        raise
    if not folder.is_dir():
        return {
            "ok": True,
            "folder": NEEDS_SORTING_TOP,
            "files_indexed": 0,
            "items": [],
            "empty": True,
            "empty_message": "_needs_sorting missing or empty — EMPTY (not invent).",
            "destructive": False,
            "mode": "needs_sorting_readonly",
            "honesty": dict(HONESTY),
        }
    sample = inventory_sample(folder=folder, cap=cap, hash_max_bytes=hash_max_bytes)
    # Strip absolute paths from client-facing items (keep rel only)
    public_items = []
    for item in sample.get("items") or []:
        public_items.append(
            {
                "original_filename": item.get("original_filename"),
                "rel": item.get("rel"),
                "size": item.get("size"),
                "mtime": item.get("mtime"),
                "sha256_1mb": item.get("sha256_1mb"),
                "hash_partial": item.get("hash_partial"),
                "source_root": item.get("source_root"),
                "folder_evidence": item.get("folder_evidence"),
                "brand_token": infer_brand_token(str(item.get("rel") or "")),
                "media_type": media_type_from_filename(item.get("original_filename")),
                "rights": item.get("rights") or "UNKNOWN",
                "classification": item.get("classification") or "UNKNOWN",
            }
        )
    n = len(public_items)
    return {
        "ok": True,
        "sampled_at": sample.get("sampled_at") or now_iso(),
        "folder": NEEDS_SORTING_TOP,
        "files_indexed": n,
        "cap": cap,
        "items": public_items,
        "empty": n == 0,
        "empty_message": (
            "_needs_sorting has no files in this READ-only capped sample — EMPTY (not invent)."
            if n == 0
            else None
        ),
        "destructive": False,
        "mode": "needs_sorting_readonly",
        "note": (
            "READ-only leftover sample; refuse #recycle / _clickup-attachment-archive; "
            "full_tree_indexed=false; staff_ready=false"
        ),
        "honesty": dict(HONESTY),
        # Keep raw sample (with abs paths) only for optional Beta ingest callers
        "_raw_for_ingest": sample if n else None,
    }


def persist_and_ingest_needs_sorting(
    conn: sqlite3.Connection,
    *,
    cap: int = 25,
) -> dict[str, Any]:
    """Optional: persist + upsert needs_sorting sample into Beta nas_index. Never mutates NAS."""
    sample_pub = inventory_needs_sorting_sample(cap=cap)
    raw = sample_pub.pop("_raw_for_ingest", None)
    if not sample_pub.get("ok"):
        return sample_pub
    if not raw or not (raw.get("items") or []):
        sample_pub["persisted"] = None
        sample_pub["ingested"] = {"ok": True, "rows_upserted": 0, "empty": True}
        return sample_pub
    persisted = persist_sample_index(raw, cap=cap)
    ingested = ingest_sample_to_catalog(conn, raw, cap=cap)
    sample_pub["persisted"] = {
        "ok": True,
        "folder": NEEDS_SORTING_TOP,
        "files_indexed": persisted.get("files_indexed"),
        "cap": cap,
        "destructive": False,
        "manifest_rel": (
            f"state/nas-index/sample-{_folder_slug(MEDIA_LIBRARY / NEEDS_SORTING_TOP)}-"
            f"{datetime.now(TZ).strftime('%Y%m%d')}.manifest.json"
        ),
    }
    sample_pub["ingested"] = {
        "ok": bool(ingested.get("ok")),
        "rows_upserted": ingested.get("rows_upserted"),
        "destructive": False,
    }
    return sample_pub


def scopes_allow_brand(scopes: list[str] | set[str] | None, brand: str) -> bool:
    brand = (brand or "").strip().lower()
    allowed = BRAND_SCOPES.get(brand)
    if not allowed:
        return False
    have = {str(s).strip() for s in (scopes or []) if str(s).strip()}
    if "SCOPE-WOLF-GROUP" in have:
        return True
    return bool(have & allowed)


def brands_for_scopes(scopes: list[str] | set[str] | None) -> list[str]:
    have = {str(s).strip() for s in (scopes or []) if str(s).strip()}
    if "SCOPE-WOLF-GROUP" in have:
        return sorted(BRAND_SCOPES.keys())
    out = []
    for brand, allowed in BRAND_SCOPES.items():
        if have & allowed:
            out.append(brand)
    return sorted(out)


def canonical_nas_path(
    *,
    brand: str,
    stage: str,
    shoot_date: str,
    canonical_filename: str,
    data_lane: str = "operational",
) -> Path:
    """Deterministic placement under _Imports/Wolf-Library. Never overwrites."""
    brand = (brand or "unknown").strip().lower() or "unknown"
    stage = (stage or "RAW").strip().upper() or "RAW"
    year = (shoot_date or "")[:4] if shoot_date and len(shoot_date) >= 4 else datetime.now(TZ).strftime("%Y")
    safe_name = Path(canonical_filename).name
    if data_lane == "test":
        base = ALLOWED_WRITE_PREFIX / TEST_MARKER / brand / stage / year
    else:
        base = ALLOWED_WRITE_PREFIX / brand / stage / year
    return base / safe_name


def unique_nas_path(dest: Path) -> Path:
    """Never overwrite. Append -2, -3… before extension if needed."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    for i in range(2, 10000):
        cand = parent / f"{stem}-{i}{suffix}"
        if not cand.exists():
            return cand
    raise NasLibraryError("could not allocate unique NAS filename", code="nas_unique_fail", http=500)


def place_on_nas(
    source: Path,
    *,
    brand: str,
    stage: str,
    shoot_date: str,
    canonical_filename: str,
    data_lane: str = "operational",
    content_hash: str | None = None,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Copy source → canonical NAS path. Never overwrite. Never delete other NAS files.

    Returns nas_received True only when destination exists with matching size.
    """
    if not media_library_connected():
        return {
            "nas_received": False,
            "nas_path": None,
            "nas_rel": None,
            "message": "NAS not connected — file stays on Beta library only.",
            "verified_size": None,
        }
    if not source.is_file():
        return {
            "nas_received": False,
            "nas_path": None,
            "nas_rel": None,
            "message": "source missing — refuse NAS claim",
            "verified_size": None,
        }
    dest = canonical_nas_path(
        brand=brand,
        stage=stage,
        shoot_date=shoot_date,
        canonical_filename=canonical_filename,
        data_lane=data_lane,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    _ensure_under_write_prefix(dest.parent)
    dest = unique_nas_path(dest)
    dest = _ensure_under_write_prefix(dest)
    if dest.exists():
        raise NasLibraryError("refuse overwrite on NAS", code="nas_overwrite_refused", http=409)
    try:
        shutil.copy2(str(source), str(dest))
    except OSError as exc:
        return {
            "nas_received": False,
            "nas_path": None,
            "nas_rel": None,
            "message": f"NAS copy failed: {exc}",
            "verified_size": None,
        }
    # Honesty prove: file really on NAS
    try:
        dest = _ensure_under_write_prefix(dest)
        ok = dest.is_file() and dest.stat().st_size == source.stat().st_size
    except OSError:
        ok = False
    if not ok:
        return {
            "nas_received": False,
            "nas_path": None,
            "nas_rel": None,
            "message": "NAS copy did not verify — refuse nas_received",
            "verified_size": None,
        }
    rel = str(dest.relative_to(MEDIA_LIBRARY))
    return {
        "nas_received": True,
        "nas_path": str(dest),
        "nas_rel": rel,
        "nas_received_at": now_iso(),
        "verified_size": dest.stat().st_size,
        "message": "File verified on NAS under Wolf-Library.",
        "original_filename": original_filename,
        "content_hash": content_hash,
        "data_lane": data_lane,
        "test_marked": data_lane == "test",
    }


def verify_nas_received(nas_path: str | None, *, expected_size: int | None = None) -> bool:
    if not nas_path:
        return False
    try:
        p = _ensure_under_write_prefix(Path(nas_path))
        if not p.is_file():
            return False
        if expected_size is not None and p.stat().st_size != expected_size:
            return False
        return True
    except (OSError, NasLibraryError):
        return False


def cleanup_test_asset(nas_path: str | None) -> dict[str, Any]:
    """Audited cleanup — only deletes under _Imports/Wolf-Library/_test/."""
    if not nas_path:
        return {"ok": False, "deleted": False, "reason": "no_path"}
    try:
        p = _ensure_under_write_prefix(Path(nas_path))
    except NasLibraryError as exc:
        return {"ok": False, "deleted": False, "reason": str(exc)}
    test_root = (ALLOWED_WRITE_PREFIX / TEST_MARKER).resolve()
    try:
        p.relative_to(test_root)
    except ValueError:
        return {"ok": False, "deleted": False, "reason": "not_under_test_prefix"}
    if not p.is_file():
        return {"ok": True, "deleted": False, "reason": "already_absent"}
    try:
        p.unlink()
        return {"ok": True, "deleted": True, "path": str(p)}
    except OSError as exc:
        return {"ok": False, "deleted": False, "reason": str(exc)}


def public_nas_status() -> dict[str, Any]:
    """Honest connectivity for UI banner — never claims nas_received without a file."""
    connected = media_library_connected()
    if connected:
        return {
            "connected": True,
            "path": str(MEDIA_LIBRARY),
            "wolf_write_prefix": str(ALLOWED_WRITE_PREFIX),
            "message": (
                "NAS mounted. Authorised Smart Upload places files under "
                "_Imports/Wolf-Library. nas_received is true only after verify."
            ),
            "nas_received": False,  # status endpoint never claims a file received
            "honesty": dict(HONESTY),
        }
    return {
        "connected": False,
        "path": None,
        "wolf_write_prefix": str(ALLOWED_WRITE_PREFIX),
        "message": "NAS not connected — uploads stay on Beta library only. We will not claim NAS received.",
        "nas_received": False,
        "honesty": dict(HONESTY),
    }


def retired_systems() -> list[dict[str, Any]]:
    """ClickUp + Telegram — RETIRED / HISTORICAL ONLY (Owner approved)."""
    return [
        {
            "source_id": "clickup",
            "name": "ClickUp",
            "lifecycle": "RETIRED",
            "status": "RETIRED",
            "evidence": "Owner Connection Commissioning 2026-09-22: ClickUp RETIRED / HISTORICAL ONLY. Not waiting to commission.",
            "commission": False,
            "external_writes": False,
        },
        {
            "source_id": "telegram",
            "name": "Telegram",
            "lifecycle": "RETIRED",
            "status": "RETIRED",
            "evidence": "Owner Connection Commissioning 2026-09-22: Telegram RETIRED / HISTORICAL ONLY. Not waiting to commission.",
            "commission": False,
            "external_writes": False,
        },
    ]
