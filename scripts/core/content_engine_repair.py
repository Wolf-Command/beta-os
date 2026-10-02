#!/usr/bin/env python3
"""Content Engine Haikal fail repair — shared root (Beta only).

Upload lifecycle, library registration, thumbs, Brand Registry ACL,
in-place NAS index, and Wolf Intelligence hide-until-connected.

staff_ready stays false. Does not move, rename, delete, or duplicate NAS files.
Does not invent a Content Engine agent.
"""
from __future__ import annotations

import json
import os
import shutil
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
CONTENT_ALL_ASSIGNMENT = "ASG-HAIKAL-CD-1"  # legacy seed id; attach is by role
CONTENT_DIRECTOR_ROLE = "ROLE-GGV-CREATIVE-DIRECTOR"
CONTENT_CREATOR_ROLE = "ROLE-CONTENT-CREATOR"
CONTENT_TEAM_ROLES = (CONTENT_DIRECTOR_ROLE, CONTENT_CREATOR_ROLE)
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
UPLOAD_AUDIT_PATH = BETA_ROOT / "state" / "content-engine" / "upload-audit.jsonl"
# launchd serve-beta ships PATH=/usr/bin:/bin:/usr/sbin:/sbin, so a bare "ffmpeg" raises FileNotFoundError.
FFMPEG_CANDIDATES = (
    "/opt/homebrew/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
)
STAFF_TOO_LARGE = "This file is too large to upload."
STAFF_UNSUPPORTED = "This file type is not supported."
STAFF_STORAGE = "Storage is unavailable. Nothing new was saved for this file."
STAFF_INTERRUPTED = "The connection was interrupted. Retry the failed files."
STAFF_ALREADY = "This file is already in the library."
STAFF_SAVED = "Available in the library."
STAFF_RETRY = "This file could not be added to the library. Retry the failed files."
STAFF_FORBIDDEN = "You do not have permission to upload for this brand."
STAFF_PREVIEW = "Video uploaded successfully. Preview processing failed — Retry Preview."
STAFF_INDEX = "The file was saved but could not be indexed. Retry the failed files."
STAFF_CANCELLED = "Upload cancelled."
STAFF_ALREADY_UPLOADED_STOPPED = "File already uploaded. Processing stopped."
UPLOAD_STATE_RUN_ID = "BF-content-engine-upload-state-library-search-20261001"
CANCEL_UPLOAD_RUN_ID = "CE-CANCEL-UPLOAD-1"

# Canonical stages. COMPLETE / READY is last and only when the preview is ready.
# Poster failure after FILE STORED is DERIVATIVE FAILED, not an upload failure.
LIFECYCLE: tuple[tuple[str, str], ...] = (
    ("received", "RECEIVED / UPLOADING"),
    ("file_stored", "FILE STORED"),
    ("indexed", "INDEXED"),
    ("derivatives", "DERIVATIVES PROCESSING"),
    ("ready", "READY"),
)
FAIL_LIFECYCLE: tuple[tuple[str, str], ...] = (
    ("storage_failed", "STORAGE FAILED"),
    ("index_failed", "INDEX FAILED"),
    ("derivative_failed", "DERIVATIVE FAILED"),
)

# Staff media labels. broll stays in MEDIA_TYPES as content-class debt, not a media kind.
# Drone is a first-class media kind (HUMFIX-1).
STAFF_MEDIA_LABELS = {
    "image": "Photo",
    "photo": "Photo",
    "video": "Video",
    "audio": "Audio",
    "graphic": "Graphic",
    "drone": "Drone",
}
STAFF_MEDIA_KINDS = frozenset(STAFF_MEDIA_LABELS.keys()) - {"photo"}  # photo aliases image


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
    ffmpeg = resolve_ffmpeg()
    return {
        "ok": True,
        "run_id": RUN_ID,
        "lifecycle": [{"key": k, "label": label} for k, label in LIFECYCLE],
        "complete_means": "library_available",
        "brand_source": "org_brands+aliases",
        "round2_run_id": ROUND2_RUN_ID,
        "wi_connected": False,
        "wi_staff_hidden": True,
        # True when the running process can poster a MOV even if launchd PATH has no ffmpeg.
        "ffmpeg_resolved": bool(ffmpeg),
        "upload_state_run_id": UPLOAD_STATE_RUN_ID,
        "upload_lifecycle": [{"key": k, "label": label} for k, label in LIFECYCLE],
        "upload_fail_states": [{"key": k, "label": label} for k, label in FAIL_LIFECYCLE],
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
    try:
        _nas.migrate_schema(conn)
    except sqlite3.DatabaseError:
        pass
    have = {r[1] for r in conn.execute("PRAGMA table_info(nas_index)").fetchall()}
    if not have:
        return
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
            try:
                conn.execute(f"ALTER TABLE nas_index ADD COLUMN {name} {typ}")
            except sqlite3.DatabaseError:
                pass
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_nas_index_brand_state ON nas_index(brand_slug, index_state)",
        "CREATE INDEX IF NOT EXISTS idx_nas_index_name_size ON nas_index(original_filename, size)",
    ):
        try:
            conn.execute(sql)
        except sqlite3.DatabaseError:
            pass


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
    """Content team grant: CD + Content Creator seats see all active content brands.

    Creative Director = cross-brand. Content Creator assignments carry team scopes
    without brand targets → Content team role covers all active content brands.
    Succession: any new ACTIVE seat on those roles gets the same scope; ended
    assignments stop receiving it. Content-only — not SCOPE-AMG/BZG/WOLF-GROUP.
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
    placeholders = ",".join("?" for _ in CONTENT_TEAM_ROLES)
    role_rows = conn.execute(
        f"""
        SELECT a.assignment_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE p.role_id IN ({placeholders})
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        ORDER BY a.assignment_id
        """,
        CONTENT_TEAM_ROLES,
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
    try:
        ensure_registry(conn)
    except sqlite3.DatabaseError:
        pass
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


def _rows_for_state(state: str) -> list[dict[str, str]]:
    """Canonical stage rows. A fail marks that stage and leaves later stages pending."""
    labels = dict(LIFECYCLE)
    order = [key for key, _label in LIFECYCLE]
    fail_key = {
        "STORAGE_FAILED": "file_stored",
        "INDEX_FAILED": "indexed",
        "DERIVATIVE_FAILED": "derivatives",
    }.get(state)
    if state == "READY" or fail_key is None:
        mark = "done" if state == "READY" else "pending"
        if state == "READY":
            return [{"key": key, "label": labels[key], "state": "done"} for key in order]
        return [{"key": key, "label": labels[key], "state": mark} for key in order]
    fail_at = order.index(fail_key)
    out = []
    for index, key in enumerate(order):
        if index < fail_at:
            row_state = "done"
        elif index == fail_at:
            row_state = "failed"
        else:
            row_state = "pending"
        out.append({"key": key, "label": labels[key], "state": row_state})
    return out


def lifecycle_rows(*, failed_stage: str | None, library_available: bool) -> list[dict[str, str]]:
    if library_available and not failed_stage:
        return _rows_for_state("READY")
    state = {
        "uploading": "STORAGE_FAILED",
        "processing": "STORAGE_FAILED",
        "saving_nas": "STORAGE_FAILED",
        "indexing": "INDEX_FAILED",
        "library": "INDEX_FAILED",
        "thumbnail": "DERIVATIVE_FAILED",
    }.get(failed_stage or "", "STORAGE_FAILED")
    if library_available:
        state = "READY"
    return _rows_for_state(state)


def resolve_ffmpeg() -> str | None:
    """Find ffmpeg even when launchd stripped PATH to the system bins."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for cand in FFMPEG_CANDIDATES:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def log_upload_fault(event: dict[str, Any]) -> None:
    """Admin-only audit. Never returned to the upload page."""
    try:
        UPLOAD_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "at": datetime.now(TZ).isoformat(timespec="seconds"),
            **{k: v for k, v in event.items() if k not in ("data", "file", "bytes")},
        }
        with UPLOAD_AUDIT_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
    except OSError:
        return


def staff_upload_message(http: int, body: dict[str, Any] | None) -> str:
    """Sentence a staff member can act on. Technical text stays in the audit log."""
    body = body or {}
    if body.get("already_uploaded_processing_stopped") is True:
        return STAFF_ALREADY_UPLOADED_STOPPED
    if body.get("cancelled") is True or str(body.get("ui_status") or "").upper() == "CANCELLED":
        return STAFF_CANCELLED
    stage = str(body.get("failed_stage") or "")
    life = str(body.get("lifecycle_state") or "")
    derivative = (
        body.get("derivative_failed") is True
        or life == "DERIVATIVE_FAILED"
        or stage == "thumbnail"
    )
    if derivative and body.get("ok") is not False and http < 400:
        return STAFF_PREVIEW
    if body.get("library_available") is True:
        return STAFF_SAVED
    err = str(body.get("error") or "")
    low = err.lower()
    if http == 413 or "exceeds" in low or "too large" in low:
        return STAFF_TOO_LARGE
    if http == 415 or low.startswith("unsupported") or "magic mismatch" in low:
        return STAFF_UNSUPPORTED
    if http == 409 or err == "possible_duplicate" or body.get("duplicate") is True:
        return STAFF_ALREADY
    if http == 403 or err == "forbidden":
        return STAFF_FORBIDDEN
    if life == "INDEX_FAILED" or stage in {"indexing", "library"}:
        return STAFF_INDEX
    if (
        life == "STORAGE_FAILED"
        or stage == "saving_nas"
        or "nas verify failed" in low
        or low.startswith("save failed")
    ):
        return STAFF_STORAGE
    return STAFF_RETRY


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
            ffmpeg = resolve_ffmpeg()
            if not ffmpeg:
                log_upload_fault(
                    {
                        "where": "write_jpeg_thumb",
                        "error": "ffmpeg not found",
                        "path": os.environ.get("PATH"),
                        "src_name": src.name,
                    }
                )
                return False
            proc = subprocess.run(
                [
                    ffmpeg,
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
                timeout=45,
                check=False,
            )
            ok = proc.returncode == 0 and dest.is_file() and dest.stat().st_size > 32
            if not ok:
                err = (proc.stderr or b"").decode("utf-8", "replace")[-500:]
                log_upload_fault(
                    {
                        "where": "write_jpeg_thumb",
                        "error": "ffmpeg poster failed",
                        "returncode": proc.returncode,
                        "ffmpeg": ffmpeg,
                        "src_name": src.name,
                        "stderr_tail": err,
                    }
                )
            return ok
    except (OSError, subprocess.TimeoutExpired, Exception) as exc:
        log_upload_fault(
            {
                "where": "write_jpeg_thumb",
                "error": type(exc).__name__,
                "detail": str(exc)[:300],
                "src_name": src.name,
            }
        )
        return False
    return False


def asset_thumb_path(asset_id: int) -> Path:
    return THUMB_DIR / f"asset-{int(asset_id)}.jpg"


def nas_thumb_path(nas_id: int) -> Path:
    return THUMB_DIR / f"nas-{int(nas_id)}.jpg"


def annotate_upload(body: dict[str, Any], *, media_path: str | Path | None) -> dict[str, Any]:
    """READY only when NAS file, hash, index, and thumbnail all succeeded.

    A poster miss after the file is stored is DERIVATIVE FAILED. The upload
    itself stays successful and Retry Preview reuses the stored asset.
    """
    out = dict(body)
    asset_id = out.get("asset_id")
    thumb_ok = False
    if out.get("ok") and asset_id and media_path and out.get("nas_received"):
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
    if not out.get("ok") or not registration["hash"] or not registration["nas_file"]:
        state = "STORAGE_FAILED"
        failed = "saving_nas" if out.get("ok") else "uploading"
        if out.get("ok") and not registration["hash"]:
            failed = "processing"
    elif not registration["indexed"]:
        state = "INDEX_FAILED"
        failed = "indexing"
    elif not registration["library"]:
        state = "INDEX_FAILED"
        failed = "library"
    elif not registration["thumbnail"]:
        state = "DERIVATIVE_FAILED"
        failed = "thumbnail"
    else:
        state = "READY"
        failed = None
    file_stored = bool(out.get("ok") and registration["nas_file"])
    derivative_failed = state == "DERIVATIVE_FAILED"
    upload_failed = state in {"STORAGE_FAILED", "INDEX_FAILED"} or not out.get("ok")
    library_available = state == "READY"
    out["registration"] = registration
    out["failed_stage"] = failed
    out["lifecycle_state"] = state
    out["file_stored"] = file_stored
    out["derivative_failed"] = derivative_failed
    out["upload_failed"] = upload_failed
    out["preview_ready"] = bool(thumb_ok and library_available)
    out["preview_retryable"] = bool(derivative_failed and asset_id)
    out["library_available"] = library_available
    out["complete"] = library_available
    out["lifecycle"] = _rows_for_state(state)
    out["preview_url"] = f"/api/assets/{asset_id}/preview" if asset_id else None
    out["staff_ready"] = False
    out["staff_message"] = staff_upload_message(200 if out.get("ok") else 500, out)
    if library_available:
        out["ui_status"] = "COMPLETE"
    elif derivative_failed:
        out["ui_status"] = "STORED"
    elif upload_failed:
        out["ui_status"] = "FAILED"
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
    if kind not in ("image", "video", "audio", "graphic", "drone"):
        kind = _media_kind(filename) or kind
    if kind not in ("image", "video", "audio", "graphic", "drone"):
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


def clamp_library_page(page: int, pages: int) -> int:
    """1-based page clamped into 1..pages. An empty result is page 1."""
    try:
        page_n = int(page)
    except (TypeError, ValueError):
        page_n = 1
    pages_n = int(pages or 0)
    if pages_n < 1:
        return 1
    if page_n < 1:
        return 1
    if page_n > pages_n:
        return pages_n
    return page_n


def library_page_window(current: int, pages: int, neighbours: int = 2) -> list[int | str]:
    """First and last page, neighbours around the current page, ellipsis for gaps."""
    pages_n = int(pages or 0)
    if pages_n <= 0:
        return []
    current_n = clamp_library_page(current, pages_n)
    span = int(neighbours if neighbours is not None else 2)
    if span < 0:
        span = 0
    if pages_n == 1:
        return [1]
    wanted = {1, pages_n}
    for n in range(current_n - span, current_n + span + 1):
        if 1 <= n <= pages_n:
            wanted.add(n)
    ordered = sorted(wanted)
    out: list[int | str] = []
    prev = 0
    for n in ordered:
        if prev and n - prev > 1:
            if n - prev == 2:
                out.append(prev + 1)
            else:
                out.append("ellipsis")
        out.append(n)
        prev = n
    return out


def _library_page_bounds(matched: int, limit: int, offset: int, page: int | None) -> tuple[int, int, int, int]:
    """Return page, pages, offset, limit. page wins over offset. Out of range clamps."""
    limit_n = max(1, min(48, int(limit or 48)))
    matched_n = max(0, int(matched or 0))
    pages_n = (matched_n + limit_n - 1) // limit_n if matched_n else 0
    if page is not None:
        page_n = clamp_library_page(page, pages_n if pages_n else 1)
        offset_n = (page_n - 1) * limit_n if matched_n else 0
        if pages_n == 0:
            page_n = 1
            offset_n = 0
        return page_n, pages_n, offset_n, limit_n
    try:
        offset_n = int(offset or 0)
    except (TypeError, ValueError):
        offset_n = 0
    if offset_n < 0:
        offset_n = 0
    if matched_n == 0:
        return 1, 0, 0, limit_n
    last = (pages_n - 1) * limit_n
    if offset_n > last:
        offset_n = last
    page_n = (offset_n // limit_n) + 1
    return page_n, pages_n, offset_n, limit_n


def _library_page_body(
    cards: list[dict[str, Any]],
    matched: int,
    *,
    limit: int,
    offset: int,
    page: int,
    pages: int,
) -> dict[str, Any]:
    return {
        "cards": cards,
        "matched": matched,
        "total": matched,
        "limit": limit,
        "offset": offset,
        "page": page,
        "pages": pages,
        "page_window": library_page_window(page, pages) if pages else [],
        "staff_ready": False,
        "full_tree_indexed": False,
        "full_nas_complete": False,
    }


ASSET_SEARCH_COLUMNS = (
    "canonical_filename",
    "original_filename",
    "filename",
    "slug",
    "subject",
    "detail",
    "detail_tags_json",
    "location",
    "brand",
    "stage",
    "media_type",
    "type",
    "shoot_date",
    "readiness",
    "library_status",
    "status",
)
NAS_SEARCH_COLUMNS = (
    "original_filename",
    "rel",
    "brand_slug",
    "classification",
    "index_state",
    "preview_note",
)


def footage_date_label(value: str | None) -> str:
    """Shoot date as stored. Blank stays UNKNOWN. Never replaced by upload date."""
    raw = str(value or "").strip()
    if not raw or raw.upper() == "UNKNOWN":
        return "UNKNOWN"
    return raw


def shoot_date_needles(value: str | None) -> list[str]:
    """Accept 2026-08-01 and 20260801 as the same shoot date. No upload-date alias."""
    raw = str(value or "").strip()
    if not raw:
        return []
    digits = "".join(ch for ch in raw if ch.isdigit())
    out: list[str] = []
    if len(digits) >= 8:
        digits = digits[:8]
        iso = f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        for item in (digits, iso, raw):
            if item and item not in out:
                out.append(item)
        return out
    return [raw]


def _like_clause(columns: tuple[str, ...], q: str) -> tuple[str, list[str]]:
    like = f"%{q.strip().lower()}%"
    parts = [f"lower(ifnull({col},'')) LIKE ?" for col in columns]
    # content_class lives in provenance_json. Search the stored JSON, not an invented column.
    parts.append("lower(ifnull(provenance_json,'')) LIKE ?")
    return "(" + " OR ".join(parts) + ")", [like] * (len(columns) + 1)


def _asset_card(row: sqlite3.Row | dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    d = dict(row)
    typ = (d.get("media_type") or d.get("type") or "").lower()
    if typ == "photo":
        typ = "image"
    media_label = staff_media_label(typ)
    if typ == "video":
        thumb = "video"
    elif typ in ("image", "graphic"):
        thumb = "image"
    elif typ == "audio":
        thumb = "audio"
    else:
        thumb = "file"
        if typ == "broll":
            media_label = ""
    tags = []
    try:
        tags = json.loads(d.get("detail_tags_json") or "[]") or []
    except (TypeError, json.JSONDecodeError):
        tags = []
    prov = {}
    try:
        prov = json.loads(d.get("provenance_json") or "{}") or {}
    except (TypeError, json.JSONDecodeError):
        prov = {}
    asset_id = d.get("id")
    thumb_file = asset_thumb_path(int(asset_id)) if asset_id else None
    thumb_ready = bool(thumb_file and thumb_file.is_file() and thumb_file.stat().st_size > 32)
    ready = (d.get("readiness") or "").upper()
    if d.get("nas_received") and not thumb_ready:
        status_label = "Preview processing failed"
    elif ready == "READY_TO_USE":
        status_label = "Ready"
    elif ready == "FAILED":
        status_label = "Failed"
    elif ready == "CHECKING":
        status_label = "Checking"
    else:
        status_label = d.get("library_status") or ready or ""
    slug = (d.get("brand") or "").strip().lower()
    content_class = prov.get("content_class") or ""
    return {
        "id": asset_id,
        "source": "assets",
        "brand": slug,
        "brand_badge": names.get(slug, slug.replace("-", " ").title()),
        "staff_title": library_display_title(d.get("subject"), d.get("detail"), d.get("original_filename") or d.get("canonical_filename")),
        "content_class": content_class,
        "content_class_label": content_class_label(content_class),
        "stage": d.get("stage") or "",
        "canonical_name": d.get("canonical_filename") or d.get("filename") or d.get("slug") or "",
        "original_name": d.get("original_filename") or "",
        "name": d.get("canonical_filename") or d.get("filename") or d.get("slug") or "",
        "media_type": typ,
        "media_label": media_label,
        "thumb": thumb,
        "thumb_ready": thumb_ready,
        "shoot_date": d.get("shoot_date") or "",
        "shoot_date_label": footage_date_label(d.get("shoot_date")),
        "uploaded_at": d.get("uploaded_at") or d.get("date_added") or "",
        "subject": d.get("subject") or "",
        "detail": d.get("detail") or "",
        "detail_tags": tags if isinstance(tags, list) else [],
        "location": d.get("location") or "",
        "readiness": ready,
        "readiness_label": status_label,
        "status_label": status_label,
        "library_status": d.get("library_status") or d.get("status") or "",
        "date_added": d.get("date_added") or "",
        "batch_id": d.get("batch_id"),
        "nas_received": bool(d.get("nas_received")),
        "preview_retryable": bool(d.get("nas_received") and asset_id and not thumb_ready),
        "zip_eligible": True,
        "preview_url": f"/api/assets/{asset_id}/preview" if asset_id else None,
        "download_url": f"/api/assets/{asset_id}/download" if asset_id else None,
    }


def library_search(
    conn: sqlite3.Connection,
    scopes: list[str] | set[str] | None,
    brand: str | None,
    *,
    q: str = "",
    media_type: str | None = None,
    stage: str | None = None,
    readiness: str | None = None,
    shoot_date: str | None = None,
    subject: str | None = None,
    location: str | None = None,
    limit: int = 48,
    offset: int = 0,
    page: int | None = None,
    lane: str = "operational",
) -> dict[str, Any]:
    """One library page. Filters AND. Empty q returns authorised rows. Page size ≤ 48.

    Shoot-date, stage, readiness, subject, and location apply only where the
    column exists. NAS rows have none of those, so they drop out of that AND.
    """
    try:
        limit_n = int(limit)
    except (TypeError, ValueError):
        limit_n = 48
    limit_n = max(1, min(48, limit_n))
    slugs = _library_slugs(scopes, brand)
    names = {row["slug"]: row["display_name"] for row in REQUIRED_BRANDS}
    empty = _library_page_body([], 0, limit=limit_n, offset=0, page=1, pages=0)
    empty.update(
        {
            "nas_matched": 0,
            "catalog_matched": 0,
            "search_fields": list(ASSET_SEARCH_COLUMNS) + ["content_class"],
        }
    )
    if not slugs:
        return empty
    q_text = (q or "").strip().lower()
    media = (media_type or "").strip().lower()
    if media == "photo":
        media = "image"
    stage_v = (stage or "").strip()
    ready_v = (readiness or "").strip()
    subject_v = (subject or "").strip().lower()
    location_v = (location or "").strip().lower()
    shoot_needles = shoot_date_needles(shoot_date)
    lane_v = (lane or "operational").strip().lower()
    if lane_v not in {"operational", "test", "all"}:
        lane_v = "operational"

    asset_where = [f"lower(ifnull(brand,'')) IN ({','.join('?' * len(slugs))})"]
    asset_params: list[Any] = list(slugs)
    if lane_v == "operational":
        asset_where.append("ifnull(data_lane,'operational') = 'operational'")
    elif lane_v == "test":
        asset_where.append("ifnull(data_lane,'operational') = 'test'")
    if q_text:
        clause, likes = _like_clause(ASSET_SEARCH_COLUMNS, q_text)
        asset_where.append(clause)
        asset_params.extend(likes)
    if media in {"image", "video", "audio", "graphic", "drone"}:
        asset_where.append("lower(ifnull(media_type, type)) = ?")
        asset_params.append(media)
    elif media:
        asset_where.append("lower(ifnull(media_type, type)) = ?")
        asset_params.append(media)
    if stage_v:
        asset_where.append("upper(ifnull(stage,'')) = ?")
        asset_params.append(stage_v.upper())
    if ready_v:
        asset_where.append(
            "(upper(ifnull(readiness,'')) = ? OR upper(ifnull(library_status,'')) = ? OR upper(ifnull(status,'')) = ?)"
        )
        token = ready_v.upper()
        asset_params.extend([token, token, token])
    if subject_v:
        asset_where.append("lower(ifnull(subject,'')) LIKE ?")
        asset_params.append(f"%{subject_v}%")
    if location_v:
        asset_where.append("lower(ifnull(location,'')) LIKE ?")
        asset_params.append(f"%{location_v}%")
    if shoot_needles:
        ors = ["lower(ifnull(shoot_date,'')) = ?" for _n in shoot_needles]
        asset_params.extend([n.lower() for n in shoot_needles])
        digits = "".join(ch for ch in shoot_needles[0] if ch.isdigit())[:8]
        if len(digits) == 8:
            ors.append("replace(replace(lower(ifnull(shoot_date,'')),'-',''),'/','') = ?")
            asset_params.append(digits)
        asset_where.append("(" + " OR ".join(ors) + ")")
    asset_sql = " AND ".join(asset_where)

    nas_specific = bool(stage_v or ready_v or subject_v or location_v or shoot_needles)
    nas_where = [
        f"lower(ifnull(brand_slug,'')) IN ({','.join('?' * len(slugs))})",
        f"(ifnull(index_state,'') = '' OR index_state IN ({','.join('?' * len(LIBRARY_INDEX_STATES))}))",
    ]
    nas_params: list[Any] = [*slugs, *LIBRARY_INDEX_STATES]
    if q_text:
        nas_like_cols = [f"lower(ifnull({col},'')) LIKE ?" for col in NAS_SEARCH_COLUMNS]
        nas_where.append("(" + " OR ".join(nas_like_cols) + ")")
        nas_params.extend([f"%{q_text}%"] * len(NAS_SEARCH_COLUMNS))
    if media in {"image", "video", "audio", "graphic"}:
        nas_where.append("lower(ifnull(classification,'')) = ?")
        nas_params.append(media)
    elif media:
        nas_where.append("lower(ifnull(classification,'')) = ?")
        nas_params.append(media)
    nas_sql = " AND ".join(nas_where)

    try:
        catalog_matched = int(conn.execute(f"SELECT COUNT(*) FROM assets WHERE {asset_sql}", asset_params).fetchone()[0])
    except sqlite3.OperationalError:
        catalog_matched = 0
        asset_sql = "0"
        asset_params = []
    if nas_specific:
        nas_matched = 0
    else:
        try:
            nas_matched = int(conn.execute(f"SELECT COUNT(*) FROM nas_index WHERE {nas_sql}", nas_params).fetchone()[0])
        except sqlite3.OperationalError:
            nas_matched = 0
    matched = catalog_matched + nas_matched
    page_n, pages_n, offset_n, limit_n = _library_page_bounds(matched, limit_n, offset, page)
    cards: list[dict[str, Any]] = []
    asset_take = 0
    asset_offset = 0
    nas_take = 0
    nas_offset = 0
    if offset_n < catalog_matched:
        asset_offset = offset_n
        asset_take = min(limit_n, catalog_matched - offset_n)
        nas_take = limit_n - asset_take
        nas_offset = 0
    else:
        nas_offset = offset_n - catalog_matched
        nas_take = limit_n
    if asset_take and asset_sql != "0":
        try:
            rows = conn.execute(
                f"""
                SELECT id, brand, stage, type, slug, filename, date_added, status,
                       original_filename, canonical_filename, subject, detail, location,
                       shoot_date, media_type, uploaded_at, library_status, batch_id,
                       detail_tags_json, readiness, nas_received, provenance_json
                FROM assets
                WHERE {asset_sql}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                [*asset_params, asset_take, asset_offset],
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        for row in rows:
            card = _asset_card(row, names)
            if card.get("brand") in set(slugs):
                cards.append(card)
    if nas_take and not nas_specific and nas_matched:
        try:
            nrows = conn.execute(
                f"""
                SELECT id, original_filename, rel, size, brand_slug, index_state,
                       map_confidence, classification, sha256_1mb, thumb_ready
                FROM nas_index
                WHERE {nas_sql}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                [*nas_params, nas_take, nas_offset],
            ).fetchall()
        except sqlite3.OperationalError:
            nrows = []
        wanted = set(slugs)
        for row in nrows:
            card = _nas_card(row, names)
            if card is None or card["brand"] not in wanted:
                continue
            card["shoot_date"] = ""
            card["shoot_date_label"] = "UNKNOWN"
            card["status_label"] = card.get("index_state") or "INDEXED"
            card["readiness_label"] = card["status_label"]
            cards.append(card)
            if len(cards) >= limit_n:
                break
    body = _library_page_body(
        cards[:limit_n],
        matched,
        limit=limit_n,
        offset=offset_n,
        page=page_n,
        pages=pages_n,
    )
    body["nas_matched"] = nas_matched
    body["catalog_matched"] = catalog_matched
    body["search_fields"] = list(ASSET_SEARCH_COLUMNS) + ["content_class"]
    body["nas_search_fields"] = list(NAS_SEARCH_COLUMNS)
    return body


def nas_library_search(
    conn: sqlite3.Connection,
    scopes: list[str] | set[str] | None,
    brand: str | None,
    *,
    q: str = "",
    media_type: str | None = None,
    limit: int = 48,
    offset: int = 0,
    page: int | None = None,
) -> dict[str, Any]:
    """Search every indexed nas_index row the caller may see. One page comes back; matched is the full count."""
    _nas_index_columns(conn)
    try:
        limit_n = int(limit)
    except (TypeError, ValueError):
        limit_n = 48
    limit_n = max(1, min(48, limit_n))
    slugs = _library_slugs(scopes, brand)
    empty = _library_page_body([], 0, limit=limit_n, offset=0, page=1, pages=0)
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
        page_n, pages_n, offset_n, limit_n = _library_page_bounds(matched, limit_n, offset, page)
        rows = conn.execute(
            f"""
            SELECT id, original_filename, rel, size, brand_slug, index_state,
                   map_confidence, classification, sha256_1mb, thumb_ready
            FROM nas_index
            WHERE {clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit_n, offset_n],
        ).fetchall()
    except sqlite3.OperationalError:
        return empty
    cards = []
    for row in rows:
        card = _nas_card(row, names)
        if card is None or card["brand"] not in wanted:
            continue
        cards.append(card)
    if offset_n == 0 and len(cards) < limit_n:
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
            if len(cards) >= limit_n:
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
    return _library_page_body(
        cards,
        matched,
        limit=limit_n,
        offset=offset_n,
        page=page_n,
        pages=pages_n,
    )


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


def retry_asset_preview(
    conn: sqlite3.Connection,
    asset_id: int,
    scopes: list[str] | set[str] | None,
) -> dict[str, Any]:
    """Rebuild the poster for an existing asset. No second NAS write and no new row."""
    row = conn.execute(
        """
        SELECT id, brand, content_hash, file_size, nas_path, nas_received, v2_path
        FROM assets WHERE id=?
        """,
        (int(asset_id),),
    ).fetchone()
    if not row:
        raise RepairError("asset not found", code="not_found", http=404)
    d = dict(row)
    brand = (d.get("brand") or "").strip().lower()
    if brand and not _nas.scopes_allow_brand(scopes, brand):
        raise RepairError("subject lacks scope for this file", code="forbidden", http=403)
    content_hash = d.get("content_hash") or ""
    before = 0
    if content_hash:
        before = int(
            conn.execute("SELECT COUNT(*) FROM assets WHERE content_hash=?", (content_hash,)).fetchone()[0]
        )
    src: Path | None = None
    nas_size = None
    nas_path = d.get("nas_path") or ""
    if d.get("nas_received") and nas_path:
        candidate = Path(str(nas_path))
        if candidate.is_file():
            src = candidate
            nas_size = candidate.stat().st_size
    if src is None and d.get("v2_path"):
        candidate = Path(str(d["v2_path"]))
        if candidate.is_file():
            src = candidate
    if src is None:
        return {
            "ok": False,
            "asset_id": int(asset_id),
            "upload_failed": True,
            "file_stored": False,
            "derivative_failed": False,
            "lifecycle_state": "STORAGE_FAILED",
            "staff_message": STAFF_STORAGE,
            "duplicate_created": False,
            "catalog_rows_for_hash": before,
            "staff_ready": False,
        }
    dest = asset_thumb_path(int(asset_id))
    thumb_ok = write_jpeg_thumb(src, dest)
    after = before
    if content_hash:
        after = int(
            conn.execute("SELECT COUNT(*) FROM assets WHERE content_hash=?", (content_hash,)).fetchone()[0]
        )
    nas_after = None
    if nas_path and Path(str(nas_path)).is_file():
        nas_after = Path(str(nas_path)).stat().st_size
    return {
        "ok": True,
        "asset_id": int(asset_id),
        "preview_ready": bool(thumb_ok),
        "derivative_failed": not thumb_ok,
        "upload_failed": False,
        "file_stored": True,
        "lifecycle_state": "READY" if thumb_ok else "DERIVATIVE_FAILED",
        "staff_message": STAFF_SAVED if thumb_ok else STAFF_PREVIEW,
        "duplicate_created": after != before,
        "catalog_rows_for_hash": after,
        "nas_bytes_unchanged": nas_size is None or nas_after == nas_size,
        "staff_ready": False,
    }


def reconcile_bbq_batch(conn: sqlite3.Connection, *, repair_missing_posters: bool = True) -> dict[str, Any]:
    """Inventory Tropik bbq-night-grill. Repair only a missing poster on a stored row.

    Does not delete, does not invent the two unknown filenames, does not mark the
    owner-reported 14 successful.
    """
    rows = conn.execute(
        """
        SELECT id, brand, detail, batch_id, sequence_token, original_filename,
               canonical_filename, content_hash, file_size, nas_received, nas_path,
               library_status, shoot_date, media_type, subject, stage
        FROM assets
        WHERE batch_id = ?
           OR (
                lower(ifnull(brand,'')) = 'tropik'
                AND lower(ifnull(detail,'')) LIKE '%bbq-night-grill%'
           )
        ORDER BY id
        """,
        ("bmuowp00n",),
    ).fetchall()
    inventory: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    by_hash: dict[str, list[int]] = {}
    for row in rows:
        d = dict(row)
        nas_path = d.get("nas_path") or ""
        nas_file = Path(str(nas_path)) if nas_path else None
        on_nas = bool(nas_file and nas_file.is_file())
        size_match = bool(on_nas and nas_file.stat().st_size == d.get("file_size"))
        thumb = asset_thumb_path(int(d["id"]))
        had_poster = thumb.is_file() and thumb.stat().st_size > 32
        poster_action = "present" if had_poster else "missing"
        if repair_missing_posters and on_nas and size_match and d.get("nas_received") and not had_poster:
            wrote = write_jpeg_thumb(nas_file, thumb)
            poster_action = "generated" if wrote else "generate_failed"
            actions.append(
                {
                    "asset_id": d["id"],
                    "action": poster_action,
                    "deterministic": True,
                    "reason": "NAS file and catalog row exist; poster was missing",
                }
            )
        digest = d.get("content_hash") or ""
        if digest:
            by_hash.setdefault(digest, []).append(int(d["id"]))
        if on_nas and size_match and d.get("nas_received"):
            storage = "FILE_STORED"
        elif d.get("id"):
            storage = "INDEXED_WITHOUT_NAS"
        else:
            storage = "PRE_STORAGE_UNKNOWN"
        inventory.append(
            {
                "asset_id": d["id"],
                "batch_id": d.get("batch_id"),
                "sequence_token": d.get("sequence_token"),
                "original_filename": d.get("original_filename"),
                "canonical_filename": d.get("canonical_filename"),
                "brand": d.get("brand"),
                "detail": d.get("detail"),
                "on_nas": on_nas,
                "size_match": size_match,
                "indexed": True,
                "poster": thumb.is_file() and thumb.stat().st_size > 32,
                "poster_action": poster_action,
                "storage": storage,
                "content_hash": digest,
            }
        )
    duplicates = [
        {"content_hash": digest, "asset_ids": ids}
        for digest, ids in by_hash.items()
        if len(ids) > 1
    ]
    catalog_ids = {item["asset_id"] for item in inventory}
    return {
        "run_id": UPLOAD_STATE_RUN_ID,
        "batch_id": "bmuowp00n",
        "brand": "tropik",
        "detail": "bbq-night-grill",
        "owner_reported_count": 14,
        "catalog_rows": len(inventory),
        "catalog_asset_ids": sorted(catalog_ids),
        "on_nas": sum(1 for item in inventory if item["on_nas"] and item["size_match"]),
        "indexed": len(inventory),
        "with_derivatives": sum(1 for item in inventory if item["poster"]),
        "duplicates": duplicates,
        "inventory": inventory,
        "deterministic_actions": actions,
        "human_review": [
            {
                "item": "owner_reported_14_vs_catalog_12",
                "catalog_rows": len(inventory),
                "missing_count": max(0, 14 - len(inventory)),
                "missing_filenames": "UNKNOWN",
                "reason": (
                    "Access log records POST /api/upload/smart status only. "
                    "It does not name the two files that never became catalog rows. "
                    "Filenames are not invented and those files are not marked successful."
                ),
                "action": "human_review",
            }
        ],
        "pre_storage_failed": "UNKNOWN_TWO_FILENAMES",
        "force_success": False,
        "deleted": False,
        "staff_ready": False,
    }
