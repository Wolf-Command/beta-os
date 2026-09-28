#!/usr/bin/env python3
"""Content Engine Haikal fail repair — shared root (Beta only).

Upload lifecycle, library registration, thumbs, Brand Registry ACL,
in-place NAS index, and Wolf Intelligence hide-until-connected.

staff_ready stays false. Does not move, rename, delete, or duplicate NAS files.
Does not invent a Content Engine agent.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core import nas_library as _nas

TZ = ZoneInfo("Asia/Makassar")
BETA_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "BF-content-engine-haikal-fail-repair-20260924"
ROUND2_RUN_ID = "BF-content-engine-haikal-round2-20260925"
CONTENT_ALL_ASSIGNMENT = "ASG-HAIKAL-CD-1"
CONTENT_DIRECTOR_ROLE = "ROLE-GGV-CREATIVE-DIRECTOR"
# Desk permissions for the Creative Director role. Not finance, HR, leads, or WI.
CONTENT_DESK_PERMISSIONS = (
    "PERM-CONTENT-PLAN-READ",
    "PERM-CONTENT-PLAN-EDIT",
    "PERM-CONTENT-ASSET-UPLOAD",
    "PERM-CONTENT-PROD-UPDATE",
)
CONTENT_CLASSES: tuple[tuple[str, str], ...] = (
    ("b-roll", "B-roll"),
    ("testimonial", "Testimonial"),
    ("property", "Property"),
    ("food", "Food"),
    ("people", "People"),
    ("event", "Event"),
    ("lifestyle", "Lifestyle"),
)
THUMB_DIR = BETA_ROOT / "state" / "content-thumbs"
COVERAGE_PATH = BETA_ROOT / "state" / "content-engine" / "nas-index-coverage.json"

# Human stages. COMPLETE is last and only when the asset is Library-available.
LIFECYCLE: tuple[tuple[str, str], ...] = (
    ("select", "Select file"),
    ("uploading", "Uploading"),
    ("processing", "Processing"),
    ("saving_nas", "Saving to NAS"),
    ("indexing", "Indexing"),
    ("thumbnail", "Generating thumbnail/preview"),
    ("library", "Available in Library"),
    ("complete", "Complete"),
)

# Staff media labels. broll stays in MEDIA_TYPES as content-class debt, not a media kind.
STAFF_MEDIA_LABELS = {
    "image": "Photo",
    "photo": "Photo",
    "video": "Video",
    "audio": "Audio",
    "graphic": "Graphic",
}


def staff_media_label(media_type: str | None) -> str:
    return STAFF_MEDIA_LABELS.get((media_type or "").strip().lower(), "")


def staff_library_title(subject: str | None, detail: str | None) -> str:
    """Human library title from naming-canon subject + detail. Not a filename."""

    def _clean(value: str | None) -> str:
        return " ".join(str(value or "").replace("-", " ").replace("_", " ").split())

    bits = [b for b in (_clean(subject), _clean(detail)) if b]
    return " · ".join(bits) if bits else "Untitled"


def library_display_title(
    subject: str | None,
    detail: str | None,
    filename: str | None = None,
) -> str:
    """Canonical subject/detail title, otherwise the original filename. Never Untitled when a name exists."""
    human = staff_library_title(subject, detail)
    if human != "Untitled":
        return human
    name = Path(str(filename or "")).name.strip()
    if name and name not in {".", ".."}:
        return name
    return "Untitled"


def content_class_label(value: str | None) -> str:
    key = (value or "").strip().lower()
    for slug, label in CONTENT_CLASSES:
        if key == slug:
            return label
    return ""


def staff_upload_outcome(row: dict[str, Any]) -> str:
    """Latest-upload label. Available in Library only when the registration invariant holds."""
    if row_library_available(row):
        return "Available in Library"
    status = str(row.get("library_status") or row.get("status") or "").upper()
    if status in {"FAILED", "REJECTED", "ERROR"}:
        return "Failed"
    if not row.get("nas_received"):
        return "Saving"
    return "Processing"


def all_brands_authorised(brand_count: int) -> bool:
    """All Brands only when the assignment scope covers more than one brand."""
    return int(brand_count) > 1


INDEX_STATES = (
    "DISCOVERED",
    "INDEXED",
    "THUMB_PREVIEW_READY",
    "THUMBNAIL_READY",
    "SEARCHABLE",
    "HASHED",
    "FAILED",
    "UNKNOWN",
)

# Higher rank wins. FAILED stays failed. Empty legacy rows stay eligible for Library.
STATE_RANK = {
    "": 0,
    "DISCOVERED": 1,
    "INDEXED": 2,
    "THUMBNAIL_READY": 3,
    "THUMB_PREVIEW_READY": 3,
    "SEARCHABLE": 4,
    "HASHED": 5,
    "FAILED": 9,
}

# Library search includes every indexed row, including rows still waiting on a thumb or hash.
LIBRARY_INDEX_STATES = (
    "INDEXED",
    "THUMBNAIL_READY",
    "THUMB_PREVIEW_READY",
    "SEARCHABLE",
    "HASHED",
)

# Read-only roots from the 25 Sep estate discovery. Not write targets.
NAS_READ_ROOTS = (
    Path("/Volumes/01-Media-Library"),
    Path("/Volumes/00-Editing-Workspace-3"),
    Path("/Volumes/02-Stock-Assets-1"),
    Path("/Volumes/03-Templates"),
)

# Canonical registry rows + clean names. Selector reads org_brands + aliases.
# This is the registry map, not a Content Engine HTML copy.
REQUIRED_BRANDS: tuple[dict[str, Any], ...] = (
    {
        "slug": "atrium",
        "org_brand_id": "AMG-ATR",
        "entity_id": "ENT-AMG",
        "display_name": "Atrium",
        "aliases": ["Atrium", "Atrium Lombok", "AMG-Atrium", "atrium"],
    },
    {
        "slug": "umablu",
        "org_brand_id": "BZG-UMA",
        "entity_id": "ENT-BZG",
        "display_name": "Uma Blu",
        "aliases": ["Uma Blu", "Uma Blu Brunch Cafe", "Uma-Blu-Cafe", "umablu"],
    },
    {
        "slug": "selo",
        "org_brand_id": "GGV-SELO",
        "entity_id": "ENT-GGV",
        "display_name": "Selo Group",
        "aliases": ["Selo Group", "Selo", "selo"],
    },
    {
        "slug": "habitat",
        "org_brand_id": "habitat",
        "entity_id": "ENT-GGV",
        "display_name": "Habitat",
        "aliases": ["Habitat", "Habitat-Villas", "Habitat Villas", "habitat"],
    },
    {
        "slug": "tropik",
        "org_brand_id": "GGV-TROPIK",
        "entity_id": "ENT-GGV",
        "display_name": "Tropik",
        "aliases": ["Tropik", "tropik"],
    },
    {
        "slug": "theone",
        "org_brand_id": "GGV-THEONE",
        "entity_id": "ENT-GGV",
        "display_name": "The One",
        "aliases": ["The One", "theone", "the-one"],
    },
    {
        "slug": "rainforest",
        "org_brand_id": "BZG-RAIN",
        "entity_id": "ENT-BZG",
        "display_name": "Blu Zone Rainforest Resto",
        "aliases": [
            "Blu Zone Rainforest Resto",
            "Blu Zone Rainforest Restaurant & Bar",
            "Rainforest-Restaurant",
            "rainforest",
        ],
    },
    {
        "slug": "goss",
        "org_brand_id": "GGV-GOSS",
        "entity_id": "ENT-GGV",
        "display_name": "Goss Group",
        "aliases": ["Goss Group", "goss"],
    },
)

# In-place roots. Empty list means the folder mapping is UNKNOWN — do not invent files.
NAS_ROOTS: dict[str, tuple[tuple[str, str | None], ...]] = {
    "atrium": (("AMG-Atrium", None), ("AMG", "atrium")),
    "umablu": (("BZG", "uma"),),
    "rainforest": (("BZG", "rainforest"),),
    "habitat": (("GGV", None), ("Brand-Assets", "habitat")),
    "selo": (),
    "tropik": (),
    "theone": (),
    "goss": (),
}

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
MEDIA_EXT = IMAGE_EXT | VIDEO_EXT

HONESTY = {
    "staff_ready": False,
    "proven": False,
    "ready": False,
    "commissioned": False,
    "whole_nas": False,
    "nas_destructive": False,
    "wi_connected": False,
    "wi_staff_hidden": True,
}


class RepairError(ValueError):
    def __init__(self, message: str, *, code: str = "content_repair", http: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http = http


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def registry_slugs() -> list[str]:
    return [row["slug"] for row in REQUIRED_BRANDS]


def refuse_staff_ready(_payload: dict | None = None) -> None:
    raise RepairError("Content Engine repair refuses staff_ready.", code="staff_ready_refused")


def public_status() -> dict[str, Any]:
    return {
        "ok": True,
        "run_id": RUN_ID,
        "lifecycle": [{"key": k, "label": label} for k, label in LIFECYCLE],
        "complete_means": "library_available",
        "brand_source": "org_brands+aliases",
        "round2_run_id": ROUND2_RUN_ID,
        "wi_connected": False,
        "wi_staff_hidden": True,
        **HONESTY,
    }


def _ensure_alias_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS org_brand_aliases (
          alias_key TEXT PRIMARY KEY,
          org_brand_id TEXT NOT NULL,
          slug TEXT NOT NULL,
          display_name TEXT NOT NULL
        )
        """
    )


def _nas_index_columns(conn: sqlite3.Connection) -> None:
    _nas.migrate_schema(conn)
    have = {r[1] for r in conn.execute("PRAGMA table_info(nas_index)").fetchall()}
    adds = {
        "brand_slug": "TEXT",
        "index_state": "TEXT",
        "map_confidence": "TEXT",
        "thumb_ready": "INTEGER",
        "fail_reason": "TEXT",
        "preview_note": "TEXT",
    }
    for name, typ in adds.items():
        if name not in have:
            conn.execute(f"ALTER TABLE nas_index ADD COLUMN {name} {typ}")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_nas_index_brand_state ON nas_index(brand_slug, index_state)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_nas_index_name_size ON nas_index(original_filename, size)"
    )


def ensure_registry(conn: sqlite3.Connection) -> dict[str, Any]:
    """Insert missing required brands into org_brands. Never overwrite LIVE rows."""
    _ensure_alias_table(conn)
    inserted = []
    present = {
        r[0]
        for r in conn.execute("SELECT brand_id FROM org_brands").fetchall()
    }
    stamp = now_iso()
    for row in REQUIRED_BRANDS:
        if row["org_brand_id"] not in present:
            conn.execute(
                """
                INSERT INTO org_brands (
                  brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    row["org_brand_id"],
                    row["entity_id"],
                    row["display_name"],
                    "content",
                    "SPECIFIED",
                    stamp,
                    stamp,
                ),
            )
            inserted.append(row["org_brand_id"])
        for alias in row["aliases"]:
            conn.execute(
                """
                INSERT INTO org_brand_aliases (alias_key, org_brand_id, slug, display_name)
                VALUES (?,?,?,?)
                ON CONFLICT(alias_key) DO UPDATE SET
                  org_brand_id=excluded.org_brand_id,
                  slug=excluded.slug,
                  display_name=excluded.display_name
                """,
                (alias.strip().lower(), row["org_brand_id"], row["slug"], row["display_name"]),
            )
    conn.commit()
    return {"ok": True, "inserted": inserted, "source": "org_brands+aliases", **HONESTY}


def ensure_content_all_brands_scope(conn: sqlite3.Connection) -> dict[str, Any]:
    """Owner grant: Creative Director assignment may see all eight content brands.

    Content-only. Does not attach SCOPE-AMG, SCOPE-BZG-ENTITY, or SCOPE-WOLF-GROUP.
    """
    scope_id = _nas.CONTENT_ALL_BRANDS_SCOPE
    stamp = now_iso()
    conn.execute(
        """
        INSERT INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at)
        VALUES (?, 'content', 'Wolf content — all brands', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          scope_type='content',
          display_name=excluded.display_name,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (scope_id, stamp, stamp),
    )
    for row in REQUIRED_BRANDS:
        conn.execute(
            """
            INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
            VALUES (?, 'brand', ?, ?)
            ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
            """,
            (scope_id, row["org_brand_id"], stamp),
        )
    assignment_ids = [CONTENT_ALL_ASSIGNMENT]
    role_rows = conn.execute(
        """
        SELECT a.assignment_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE p.role_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        ORDER BY a.assignment_id
        """,
        (CONTENT_DIRECTOR_ROLE,),
    ).fetchall()
    for row in role_rows:
        aid = row["assignment_id"] if hasattr(row, "keys") else row[0]
        if aid and aid not in assignment_ids:
            assignment_ids.append(aid)
    attached = False
    for assignment_id in assignment_ids:
        asg = conn.execute(
            "SELECT start_at, status FROM org_assignments WHERE assignment_id=?",
            (assignment_id,),
        ).fetchone()
        if asg is None:
            continue
        asg_status = asg["status"] if hasattr(asg, "keys") else asg[1]
        asg_start = asg["start_at"] if hasattr(asg, "keys") else asg[0]
        if str(asg_status or "") != "ACTIVE":
            continue
        existing = conn.execute(
            """
            SELECT start_at, status, end_at FROM org_assignment_scopes
            WHERE assignment_id=? AND scope_id=?
            ORDER BY start_at DESC LIMIT 1
            """,
            (assignment_id, scope_id),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO org_assignment_scopes (
                  assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (assignment_id, scope_id, asg_start, stamp, stamp),
            )
            attached = True
            continue
        ex_start = existing["start_at"] if hasattr(existing, "keys") else existing[0]
        ex_status = existing["status"] if hasattr(existing, "keys") else existing[1]
        ex_end = existing["end_at"] if hasattr(existing, "keys") else existing[2]
        if str(ex_status or "") != "ACTIVE" or ex_end:
            conn.execute(
                """
                UPDATE org_assignment_scopes
                SET status='ACTIVE', end_at=NULL, updated_at=?
                WHERE assignment_id=? AND scope_id=? AND start_at=?
                """,
                (stamp, assignment_id, scope_id, ex_start),
            )
        attached = True
    for permission_id in CONTENT_DESK_PERMISSIONS:
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW',
              updated_at=excluded.updated_at
            """,
            (CONTENT_DIRECTOR_ROLE, permission_id, stamp, stamp),
        )
    conn.commit()
    return {
        "ok": bool(attached),
        "scope_id": scope_id,
        "assignment_id": CONTENT_ALL_ASSIGNMENT,
        "content_only": True,
        "desk_permissions": list(CONTENT_DESK_PERMISSIONS),
        "staff_ready": False,
    }


def authorised_brands(conn: sqlite3.Connection, scopes: list[str] | set[str] | None) -> list[dict[str, Any]]:
    """Person→Role→Assignment→Scope filter over the canonical registry."""
    ensure_registry(conn)
    try:
        ensure_content_all_brands_scope(conn)
    except sqlite3.Error:
        pass
    allowed = set(_nas.brands_for_scopes(scopes))
    org_ids = {
        r[0]
        for r in conn.execute(
            "SELECT brand_id FROM org_brands WHERE ifnull(status,'') != 'RETIRED'"
        ).fetchall()
    }
    out = []
    for row in REQUIRED_BRANDS:
        if row["slug"] not in allowed:
            continue
        if row["org_brand_id"] not in org_ids:
            continue
        out.append(
            {
                "slug": row["slug"],
                "id": row["slug"],
                "org_brand_id": row["org_brand_id"],
                "display_name": row["display_name"],
                "aliases": list(row["aliases"]),
                "source": "org_brands+aliases",
            }
        )
    return out


def suggest_brand(filename: str, scopes: list[str] | set[str] | None, conn: sqlite3.Connection) -> dict[str, Any]:
    """Suggestion only. Never applied. Uncertain results require a human confirm."""
    ensure_registry(conn)
    allowed = {b["slug"] for b in authorised_brands(conn, scopes)}
    text = (filename or "").lower()
    hit = None
    for row in REQUIRED_BRANDS:
        if row["slug"] not in allowed:
            continue
        for alias in row["aliases"]:
            token = alias.lower().replace(" ", "")
            if len(token) >= 4 and token in text.replace(" ", "").replace("_", "").replace("-", ""):
                hit = row
                break
        if hit:
            break
    if not hit:
        return {
            "ok": True,
            "suggestion": None,
            "applied": False,
            "confirm_required": True,
            "message": "No brand suggestion. Choose a brand.",
            **HONESTY,
        }
    return {
        "ok": True,
        "suggestion": hit["slug"],
        "display_name": hit["display_name"],
        "confidence": "low",
        "applied": False,
        "confirm_required": True,
        "message": f"Suggested {hit['display_name']}. Confirm before upload.",
        **HONESTY,
    }


def lifecycle_rows(*, failed_stage: str | None, library_available: bool) -> list[dict[str, str]]:
    order = [k for k, _ in LIFECYCLE]
    labels = dict(LIFECYCLE)
    if library_available:
        return [{"key": k, "label": labels[k], "state": "done"} for k in order]
    if failed_stage not in order or failed_stage == "complete":
        failed_stage = "library"
    out = []
    for key in order:
        if key == "complete":
            out.append({"key": key, "label": labels[key], "state": "pending"})
        elif key == failed_stage:
            out.append({"key": key, "label": labels[key], "state": "failed"})
        elif order.index(key) < order.index(failed_stage):
            out.append({"key": key, "label": labels[key], "state": "done"})
        else:
            out.append({"key": key, "label": labels[key], "state": "pending"})
    return out


def write_jpeg_thumb(src: Path, dest: Path) -> bool:
    """Photo thumb or video poster. Never moves the source file."""
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower()
    try:
        if ext in IMAGE_EXT:
            from PIL import Image

            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((480, 480))
                im.save(dest, "JPEG", quality=80)
            return dest.is_file() and dest.stat().st_size > 32
        if ext in VIDEO_EXT:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    "0.4",
                    "-i",
                    str(src),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=480:-1",
                    str(dest),
                ],
                capture_output=True,
                timeout=20,
                check=False,
            )
            return proc.returncode == 0 and dest.is_file() and dest.stat().st_size > 32
    except (OSError, subprocess.TimeoutExpired, Exception):
        return False
    return False


def asset_thumb_path(asset_id: int) -> Path:
    return THUMB_DIR / f"asset-{int(asset_id)}.jpg"


def nas_thumb_path(nas_id: int) -> Path:
    return THUMB_DIR / f"nas-{int(nas_id)}.jpg"


def annotate_upload(body: dict[str, Any], *, media_path: str | Path | None) -> dict[str, Any]:
    """COMPLETE only when NAS file, hash, index, and thumbnail all succeeded."""
    out = dict(body)
    asset_id = out.get("asset_id")
    thumb_ok = False
    if out.get("ok") and asset_id and media_path:
        thumb_ok = write_jpeg_thumb(Path(media_path), asset_thumb_path(int(asset_id)))
    registration = {
        "upload": "ok" if out.get("ok") else "failed",
        "nas_file": bool(out.get("nas_received")),
        "hash": out.get("content_hash") or None,
        "indexed": bool(asset_id),
        "brand": out.get("brand"),
        "scope_allowed": True,
        "library": bool(asset_id) and out.get("library_status") == "LIBRARY_READY",
        "thumbnail": thumb_ok,
    }
    failed = None
    if not out.get("ok"):
        failed = "uploading"
    elif not registration["hash"]:
        failed = "processing"
    elif not registration["nas_file"]:
        failed = "saving_nas"
    elif not registration["indexed"]:
        failed = "indexing"
    elif not registration["thumbnail"]:
        failed = "thumbnail"
    elif not registration["library"]:
        failed = "library"
    library_available = failed is None and bool(registration["library"])
    out["registration"] = registration
    out["failed_stage"] = failed
    out["library_available"] = library_available
    out["complete"] = library_available
    out["lifecycle"] = lifecycle_rows(failed_stage=failed, library_available=library_available)
    out["preview_url"] = f"/api/assets/{asset_id}/preview" if asset_id else None
    out["staff_ready"] = False
    if library_available:
        out["ui_status"] = "COMPLETE"
    elif out.get("ok"):
        out["ui_status"] = "CHECKING"
    return out


def row_library_available(row: dict[str, Any]) -> bool:
    asset_id = row.get("id") or row.get("asset_id")
    if not asset_id:
        return False
    if (row.get("library_status") or "") != "LIBRARY_READY":
        return False
    if not row.get("nas_received"):
        return False
    if not row.get("content_hash") and "content_hash" in row and not row.get("content_hash"):
        return False
    return asset_thumb_path(int(asset_id)).is_file()


def _media_kind(name: str) -> str | None:
    ext = Path(name or "").suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return None


def _index_one(
    conn: sqlite3.Connection,
    fp: Path,
    *,
    slug: str,
    confidence: str,
) -> str:
    rel = str(fp.relative_to(_nas.MEDIA_LIBRARY))
    kind = _media_kind(fp.name)
    if not kind:
        return "SKIP"
    try:
        st = fp.stat()
    except OSError:
        return "FAILED"
    try:
        digest, partial = _nas.sha256_file(fp, max_bytes=1_048_576)
        state = "HASHED"
    except OSError:
        digest, partial = "", True
        state = "FAILED"
    thumb_ok = 0
    prior = conn.execute(
        "SELECT index_state FROM nas_index WHERE original_path=?",
        (str(fp),),
    ).fetchone()
    new_state = "SEARCHABLE" if state == "HASHED" else state
    if prior is not None:
        old_state = (prior["index_state"] if hasattr(prior, "keys") else prior[0]) or ""
        if STATE_RANK.get(str(old_state), 0) >= STATE_RANK.get(new_state, 0):
            new_state = str(old_state)
    conn.execute(
        """
        INSERT INTO nas_index (
          original_path, original_filename, rel, size, mtime,
          sha256_1mb, hash_partial, source_root, folder_evidence,
          rights, classification, indexed_at, data_lane,
          brand_slug, index_state, map_confidence, thumb_ready
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(original_path) DO UPDATE SET
          size=excluded.size,
          mtime=excluded.mtime,
          sha256_1mb=CASE
            WHEN excluded.sha256_1mb != '' THEN excluded.sha256_1mb
            ELSE nas_index.sha256_1mb
          END,
          hash_partial=excluded.hash_partial,
          brand_slug=excluded.brand_slug,
          index_state=excluded.index_state,
          map_confidence=excluded.map_confidence,
          indexed_at=excluded.indexed_at
        """,
        (
            str(fp),
            fp.name,
            rel,
            st.st_size,
            datetime.fromtimestamp(st.st_mtime, TZ).isoformat(timespec="seconds"),
            digest,
            1 if partial else 0,
            "01-Media-Library",
            rel.split("/", 1)[0],
            "UNKNOWN",
            kind,
            now_iso(),
            "operational",
            slug,
            new_state,
            confidence,
            thumb_ok,
        ),
    )
    return new_state


def start_inplace_index(
    conn: sqlite3.Connection,
    scopes: list[str] | set[str] | None,
    *,
    cap_per_brand: int = 6,
) -> dict[str, Any]:
    """READ-only progressive index. Preserves path, filename, hash. No bulk NAS edits."""
    _nas_index_columns(conn)
    allowed = set(_nas.brands_for_scopes(scopes))
    try:
        pending = conn.execute(
            "SELECT id, rel, original_filename FROM nas_index WHERE ifnull(brand_slug,'') = ''"
        ).fetchall()
    except sqlite3.OperationalError:
        pending = []
    for raw in pending:
        rel = raw["rel"] or ""
        slug = _nas.infer_brand_token(rel) or ""
        if slug not in allowed:
            continue
        kind = _media_kind(raw["original_filename"] or "")
        conn.execute(
            """
            UPDATE nas_index
            SET brand_slug=?, index_state=?, map_confidence=?,
                classification=CASE WHEN ? != '' THEN ? ELSE classification END
            WHERE id=?
            """,
            (slug, "INDEXED", "path_token", kind or "", kind or "", raw["id"]),
        )
    brands_out = []
    if not _nas.media_library_connected():
        payload = {
            "ok": True,
            "started": False,
            "whole_nas": False,
            "message": "Media library is not connected. Index not started.",
            "brands": [
                {"slug": s, "index_state": "UNKNOWN", "files_indexed": 0}
                for s in registry_slugs()
                if s in allowed
            ],
            **HONESTY,
        }
        _write_coverage(payload)
        return payload
    for row in REQUIRED_BRANDS:
        slug = row["slug"]
        if slug not in allowed:
            continue
        roots = NAS_ROOTS.get(slug) or ()
        if not roots:
            brands_out.append(
                {
                    "slug": slug,
                    "display_name": row["display_name"],
                    "index_state": "UNKNOWN",
                    "files_indexed": 0,
                    "message": "Folder mapping unknown. Nothing was moved or invented.",
                }
            )
            continue
        found = 0
        failed = 0
        for top, needle in roots:
            if found >= cap_per_brand:
                break
            base = _nas.MEDIA_LIBRARY / top
            if not base.is_dir():
                continue
            try:
                _nas._ensure_under_media(base)
            except Exception:
                continue
            scanned = 0
            for dirpath, dirnames, filenames in __import__("os").walk(base):
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("#recycle",)]
                if found >= cap_per_brand or scanned >= 400:
                    break
                for name in filenames:
                    if found >= cap_per_brand:
                        break
                    if name.startswith("."):
                        continue
                    scanned += 1
                    if scanned >= 400:
                        break
                    if needle and needle not in (dirpath + "/" + name).lower():
                        continue
                    fp = Path(dirpath) / name
                    if _media_kind(name) is None:
                        continue
                    state = _index_one(conn, fp, slug=slug, confidence="folder_map")
                    if state == "FAILED":
                        failed += 1
                    elif state != "SKIP":
                        found += 1
        if found:
            index_state = "SEARCHABLE" if not failed else "FAILED"
            message = (
                f"{found} file{'s' if found != 1 else ''} indexed in place. "
                "This is not the whole library."
            )
        elif failed:
            index_state = "FAILED"
            message = "Index attempt failed for this brand. Files were not moved."
        else:
            index_state = "DISCOVERED"
            message = "Root seen. No media indexed in this pass."
        brands_out.append(
            {
                "slug": slug,
                "display_name": row["display_name"],
                "index_state": index_state,
                "files_indexed": found,
                "message": message,
            }
        )
    conn.commit()
    habitat = next((b for b in brands_out if b["slug"] == "habitat"), None)
    if habitat and habitat["files_indexed"]:
        human = habitat["message"]
    elif habitat:
        human = "Habitat indexing is underway or the folder did not yield media in this pass."
    else:
        human = "No authorised brand was indexed."
    payload = {
        "ok": True,
        "started": True,
        "whole_nas": False,
        "destructive": False,
        "message": human,
        "brands": brands_out,
        **HONESTY,
    }
    _write_coverage(payload)
    return payload


def _write_coverage(payload: dict[str, Any]) -> None:
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


_PLAIN_FAIL = {
    "thumb_failed": "Preview failed",
    "thumb_timeout": "Preview timed out",
}


def plain_fail_reason(reason: str) -> str:
    """Staff/owner label for a stored fail reason. Does not invent a new failure."""
    text = (reason or "").strip()
    if text in _PLAIN_FAIL:
        return _PLAIN_FAIL[text]
    if text.startswith("hash_error:"):
        return "File could not be read"
    return "Preview failed"


def read_library_exceptions(path: Path | None = None) -> dict[str, Any]:
    """Read-only genuine preview/hash failures. missing_file rows are not included."""
    src = path or (BETA_ROOT / "state" / "nas-estate" / "exceptions.json")
    empty: dict[str, Any] = {
        "ok": True,
        "count": 0,
        "items": [],
        "note": "",
        "as_of": "",
        "staff_ready": False,
        "read_only": True,
        "human_commissioned": False,
    }
    if not src.is_file():
        return empty
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    names = {row["slug"]: row["display_name"] for row in REQUIRED_BRANDS}
    items: list[dict[str, Any]] = []
    for row in data.get("items") or []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("brand_slug") or "UNKNOWN")
        reason = str(row.get("reason") or "")
        items.append(
            {
                "id": row.get("id"),
                "filename": str(row.get("filename") or ""),
                "brand_slug": slug,
                "brand": names.get(slug, slug),
                "source_root": str(row.get("source_root") or ""),
                "reason": reason,
                "reason_plain": plain_fail_reason(reason),
            }
        )
    return {
        "ok": True,
        "count": len(items),
        "as_of": str(data.get("as_of") or ""),
        "note": (
            "These files have no preview. They stay out of the library grid. "
            "The other files are still searchable."
        ),
        "items": items,
        "staff_ready": False,
        "read_only": True,
        "human_commissioned": False,
    }


def library_exception_audience(who: dict[str, Any] | None) -> bool:
    """Owner and the Creative Director role. Not every content seat."""
    if not isinstance(who, dict):
        return False
    audience = str(who.get("audience") or "")
    if audience in {"OWNER", "SYSTEM"}:
        return True
    roles = {str(role) for role in (who.get("roles") or []) if str(role)}
    active = who.get("active_assignment") or {}
    if isinstance(active, dict) and active.get("role"):
        roles.add(str(active.get("role")))
    return CONTENT_DIRECTOR_ROLE in roles


def read_coverage() -> dict[str, Any]:
    if not COVERAGE_PATH.is_file():
        return {
            "ok": True,
            "started": False,
            "whole_nas": False,
            "message": "In-place index has not been started.",
            "brands": [],
            **HONESTY,
        }
    try:
        data = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "ok": True,
            "started": False,
            "whole_nas": False,
            "message": "Index coverage could not be read.",
            "brands": [],
            **HONESTY,
        }
    data["whole_nas"] = False
    data["staff_ready"] = False
    return data


def _library_slugs(scopes: list[str] | set[str] | None, brand: str | None) -> list[str]:
    allowed = set(_nas.brands_for_scopes(scopes))
    brand = (brand or "").strip().lower()
    if brand in ("", "all", "*"):
        slugs = sorted(allowed)
        have = {str(s).strip() for s in (scopes or []) if str(s).strip()}
        if "SCOPE-WOLF-GROUP" in have:
            slugs = sorted(set(slugs) | {"SHARED_STOCK", "UNKNOWN"})
        return slugs
    if brand not in allowed and brand not in {"SHARED_STOCK", "UNKNOWN"}:
        return []
    if brand in {"SHARED_STOCK", "UNKNOWN"}:
        have = {str(s).strip() for s in (scopes or []) if str(s).strip()}
        if "SCOPE-WOLF-GROUP" not in have:
            return []
    elif brand not in allowed:
        return []
    return [brand]


def _nas_card(row: sqlite3.Row | dict[str, Any], names: dict[str, str]) -> dict[str, Any] | None:
    d = dict(row)
    filename = d.get("original_filename") or Path(str(d.get("original_path") or "")).name
    kind = (d.get("classification") or "").lower()
    if kind == "photo":
        kind = "image"
    if kind not in ("image", "video", "audio", "graphic"):
        kind = _media_kind(filename) or kind
    if kind not in ("image", "video", "audio", "graphic"):
        return None
    slug = (d.get("brand_slug") or "").strip().lower()
    nas_id = d.get("id")
    title = library_display_title(None, None, filename)
    thumb_file = nas_thumb_path(int(nas_id))
    thumb_kind = "video" if kind == "video" else "audio" if kind == "audio" else "image"
    return {
        "id": f"nas:{nas_id}",
        "nas_index_id": nas_id,
        "source": "nas_index",
        "brand": slug,
        "brand_badge": names.get(slug, slug),
        "stage": d.get("index_state") or "INDEXED",
        "canonical_name": filename or "file",
        "original_name": filename or "",
        "name": filename or "file",
        "staff_title": title,
        "media_type": kind,
        "media_label": staff_media_label(kind),
        "content_class": "",
        "subject": "",
        "location": "",
        "shoot_date": "",
        "thumb": thumb_kind,
        "thumb_ready": bool(d.get("thumb_ready")) or thumb_file.is_file(),
        "zip_eligible": kind in ("image", "video"),
        "index_state": d.get("index_state") or "INDEXED",
        "preview_url": f"/api/content/nas-media/{nas_id}/preview",
        "content_hash": d.get("sha256_1mb") or None,
    }


def nas_library_search(
    conn: sqlite3.Connection,
    scopes: list[str] | set[str] | None,
    brand: str | None,
    *,
    q: str = "",
    media_type: str | None = None,
    limit: int = 48,
    offset: int = 0,
) -> dict[str, Any]:
    """Search every indexed nas_index row the caller may see. One page comes back; matched is the full count."""
    _nas_index_columns(conn)
    limit = max(1, min(48, int(limit)))
    offset = max(0, int(offset))
    slugs = _library_slugs(scopes, brand)
    empty = {
        "cards": [],
        "matched": 0,
        "limit": limit,
        "offset": offset,
        "staff_ready": False,
        "full_tree_indexed": False,
        "full_nas_complete": False,
    }
    if not slugs:
        return empty
    q = (q or "").strip().lower()
    media = (media_type or "").strip().lower()
    if media == "photo":
        media = "image"
    names = {r["slug"]: r["display_name"] for r in REQUIRED_BRANDS}
    wanted = set(slugs)
    state_sql = ",".join("?" * len(LIBRARY_INDEX_STATES))
    slug_sql = ",".join("?" * len(slugs))
    where = [
        f"lower(ifnull(brand_slug,'')) IN ({slug_sql})",
        f"(ifnull(index_state,'') = '' OR index_state IN ({state_sql}))",
    ]
    params: list[Any] = [*slugs, *LIBRARY_INDEX_STATES]
    if q:
        where.append(
            "(lower(ifnull(original_filename,'')) LIKE ? OR lower(ifnull(rel,'')) LIKE ?)"
        )
        like = f"%{q}%"
        params.extend([like, like])
    if media in ("image", "video", "audio", "graphic"):
        where.append("lower(ifnull(classification,'')) = ?")
        params.append(media)
    clause = " AND ".join(where)
    try:
        matched = int(
            conn.execute(f"SELECT COUNT(*) FROM nas_index WHERE {clause}", params).fetchone()[0]
        )
        rows = conn.execute(
            f"""
            SELECT id, original_filename, rel, size, brand_slug, index_state,
                   map_confidence, classification, sha256_1mb, thumb_ready
            FROM nas_index
            WHERE {clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    except sqlite3.OperationalError:
        return empty
    cards = []
    for row in rows:
        card = _nas_card(row, names)
        if card is None or card["brand"] not in wanted:
            continue
        cards.append(card)
    if offset == 0 and len(cards) < limit:
        try:
            legacy = conn.execute(
                """
                SELECT id, original_filename, rel, size, brand_slug, index_state,
                       map_confidence, classification, sha256_1mb, thumb_ready, original_path
                FROM nas_index
                WHERE ifnull(brand_slug,'') = ''
                ORDER BY id DESC
                LIMIT 40
                """
            ).fetchall()
        except sqlite3.OperationalError:
            legacy = []
        seen = {c["nas_index_id"] for c in cards}
        for row in legacy:
            if len(cards) >= limit:
                break
            d = dict(row)
            inferred = (
                _nas.infer_brand_token(d.get("rel") or "")
                or _nas.infer_brand_token(str(d.get("original_path") or ""))
                or ""
            )
            if inferred not in wanted:
                continue
            d["brand_slug"] = inferred
            card = _nas_card(d, names)
            if card is None or card["nas_index_id"] in seen:
                continue
            if q and q not in (card["original_name"] or "").lower() and q not in str(d.get("rel") or "").lower():
                continue
            cards.append(card)
            seen.add(card["nas_index_id"])
    return {
        "cards": cards,
        "matched": matched,
        "limit": limit,
        "offset": offset,
        "staff_ready": False,
        "full_tree_indexed": False,
        "full_nas_complete": False,
    }


def nas_library_cards(
    conn: sqlite3.Connection,
    scopes: list[str] | set[str] | None,
    brand: str | None,
    *,
    limit: int = 24,
    offset: int = 0,
    q: str = "",
    media_type: str | None = None,
) -> list[dict[str, Any]]:
    """Library tiles for indexed NAS media the caller is allowed to see. No path leak."""
    page = nas_library_search(
        conn,
        scopes,
        brand,
        q=q,
        media_type=media_type,
        limit=limit,
        offset=offset,
    )
    return page["cards"]


def resolve_indexed_media(
    conn: sqlite3.Connection,
    scopes: list[str] | set[str] | None,
    *,
    limit: int = 400,
) -> dict[str, Any]:
    """Generate or reuse thumbs for indexed NAS media the caller may see. Does not move NAS files."""
    cards = nas_library_cards(conn, scopes, "all", limit=limit)
    resolved_thumb = 0
    filename_title = 0
    untitled = 0
    missing_file = 0
    for card in cards:
        title = str(card.get("staff_title") or "")
        if title == "Untitled":
            untitled += 1
        elif card.get("original_name") and title == card.get("original_name"):
            filename_title += 1
        nas_id = int(card.get("nas_index_id") or 0)
        if not nas_id:
            continue
        dest = nas_thumb_path(nas_id)
        if dest.is_file() and dest.stat().st_size > 32:
            resolved_thumb += 1
            continue
        try:
            src = resolve_nas_media(conn, nas_id, scopes)
        except RepairError:
            src = None
        if src is None:
            missing_file += 1
            continue
        if write_jpeg_thumb(src, dest):
            conn.execute("UPDATE nas_index SET thumb_ready=1 WHERE id=?", (nas_id,))
            resolved_thumb += 1
            card["thumb_ready"] = True
        else:
            missing_file += 1
    conn.commit()
    return {
        "ok": True,
        "considered": len(cards),
        "resolved_thumb": resolved_thumb,
        "filename_title": filename_title,
        "untitled": untitled,
        "thumb_failed": missing_file,
        "nas_destructive": False,
        "staff_ready": False,
    }


def resolve_nas_media(
    conn: sqlite3.Connection,
    nas_id: int,
    scopes: list[str] | set[str] | None,
) -> Path | None:
    _nas_index_columns(conn)
    row = conn.execute(
        "SELECT id, original_path, rel, brand_slug FROM nas_index WHERE id=?",
        (nas_id,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    slug = (d.get("brand_slug") or _nas.infer_brand_token(d.get("rel") or "") or "").lower()
    if slug and not _nas.scopes_allow_brand(scopes, slug):
        raise RepairError("subject lacks scope for this file", code="forbidden", http=403)
    raw = d.get("original_path") or ""
    if not raw:
        return None
    try:
        import nas_estate_index as estate_index
        resolved = estate_index.resolve_media_path(str(raw))
        path = resolved.path
    except ImportError:
        path = Path(str(raw))
        if not path.is_file():
            path = None
    if path is None or not _path_under_nas_read_root(path):
        return None
    if not path.is_file():
        return None
    return path


def _path_under_nas_read_root(path: Path) -> bool:
    """True when path resolves inside a discovery read root. Does not create or modify anything."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in NAS_READ_ROOTS:
        try:
            root_resolved = root.resolve()
        except OSError:
            continue
        try:
            resolved.relative_to(root_resolved)
            return True
        except ValueError:
            continue
    return False
