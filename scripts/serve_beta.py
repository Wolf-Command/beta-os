#!/usr/bin/env python3
"""
Content Engine 2.0 — standalone local backend for beta-os (SQLite planner).

Usage:
  python3 /Users/wolfterminal/beta-os/scripts/serve_beta.py
  # optional: BETA_PORT=8789 python3 .../serve_beta.py

Binds 127.0.0.1:8788 by default (NOT 8787). Serves static from
beta-os/dashboards/ and JSON APIs over content_library.sqlite.

Planner statuses (underscore form) — Content Engine 2.0 flow:
  Draft → AI_Generated → Human_Approved → Ready_for_Render

Legacy status mapping (read/compat):
  Idea → Draft
  Script_Drafted / Raw_Paired → AI_Generated
  Render_Ready → AI_Generated (awaiting human)
  Human_Approved stays; Ready_for_Render is new

Platforms (canonical):
  IG_Reels | TikTok | YT_Shorts
  (UI aliases: instagram_reels, tiktok, youtube_shorts)

HARD GATES:
  - POST /api/planner/save may set Draft or AI_Generated ONLY
    (never Human_Approved / Ready_for_Render via save)
  - Habitat: POST /api/planner/submit-for-approval then
    POST /api/planner/approve {id, approve:true} → Core decide only;
    Human_Approved is DERIVED from Core APPROVED (never reverse)
  - Non-habitat: POST /api/planner/approve still legacy status flip
  - POST /api/planner/ready-render {id} ONLY from Human_Approved
    → Ready_for_Render
  - POST /api/planner/render {id} 403 unless status in
    (Human_Approved, Ready_for_Render)
  - POST /api/planner/attach-asset {id, raw_asset_id}
  - Metricool/webhooks MUST check GET /api/planner/publish-gate?id=
    or call assert_publish_allowed(slot_id) before any publish.
    Legacy Human_Approved alone DENY. Metricool write stays disabled.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import sqlite3
import sys
import uuid
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

# Local staging helpers (same scripts/ dir; never wolf-system)
import stage_inspector as _stage_inspector
import llm_orchestrator as _llm_orchestrator

# Phase 1–2 Content Intelligence (dry skills; X-Wolf-Subject DEVELOPMENT ONLY until CF JWT)
import wolf_intelligence as _wi
import skills as _skills
import smart_upload as _smart_upload
import phase26_team as _p26

# Wolf Core Organisation Registry (read APIs)
from core import organisation as _org
from core import identity as _identity
from core import staffing as _staffing
from core import scope as _scope
from core import rbac as _rbac
from core import authority as _authority
from core import request_auth as _request_auth
from core import audit as _audit
from core import work_items as _work_items
from core import approvals as _approvals
from core import delegation as _delegation
from core import content_publish as _content_publish
from core import venue_close as _venue_close
from core import uma_ops_console as _uma_ops
from core import uma_devi_p0 as _uma_p0
from core import esb_close_snapshot as _esb_close_snapshot
from core import progress_read_model as _progress
from core import intel_orchestration as _intel
from core import lead_spine as _lead_spine

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DASHBOARDS = BETA_ROOT / "dashboards"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIBRARY_V2 = BETA_ROOT / "library_v2"
INCOMING_DROP = BETA_ROOT / "incoming_drop"

HOST = "127.0.0.1"
DEFAULT_PORT = 8788
TZ = ZoneInfo("Asia/Makassar")
# Hard default 500 MiB; TEST override: BETA_UPLOAD_MAX_BYTES=100 (bytes) for 413 smoke.
def _upload_max_bytes() -> int:
    raw = (os.environ.get("BETA_UPLOAD_MAX_BYTES") or "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return 500 * 1024 * 1024  # 500MB


MAX_UPLOAD_BYTES = _upload_max_bytes()
MEDIA_EXT = set(_stage_inspector.MEDIA_EXT.keys())  # broader staging classifier; upload uses whitelist below
UPLOAD_ALLOWED_EXT = {".mp4", ".mov", ".m4a", ".mp3", ".png", ".jpg", ".jpeg", ".webp"}
UPLOAD_ACCEPT_ATTR = ",".join(sorted(UPLOAD_ALLOWED_EXT))
# Soft Content-Type allow (browsers often send octet-stream); magic+ext are authoritative.
UPLOAD_ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "video/mp4",
    "video/quicktime",
    "audio/mp4",
    "audio/m4a",
    "audio/mpeg",
    "audio/mp3",
    "application/octet-stream",
}

BRANDS = ("habitat", "umablu", "atrium", "selo", "tropik")
STAGES = ("RAW", "EDIT", "FINAL")
ASSET_TYPES = ("video", "audio", "broll", "graphic", "image")
DATE_RE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")
SLUG_SAFE = re.compile(r"[^a-z0-9]+")

# Save endpoint may only set these
STATUSES_SAVE = ("Draft", "AI_Generated")
STATUS_APPROVED = "Human_Approved"
STATUS_READY_RENDER = "Ready_for_Render"
STATUS_FLOW = ("Draft", "AI_Generated", "Human_Approved", "Ready_for_Render")
ALL_STATUSES = STATUS_FLOW
# Statuses that may trigger render stub
STATUSES_RENDER_OK = (STATUS_APPROVED, STATUS_READY_RENDER)
# Approve accepted from (after canon) AI_Generated; legacy Render_Ready still in DB
STATUSES_APPROVE_FROM = ("AI_Generated", "Render_Ready")

# UI alias ↔ canonical
PLATFORM_TO_CANON = {
    "instagram_reels": "IG_Reels",
    "ig_reels": "IG_Reels",
    "IG_Reels": "IG_Reels",
    "tiktok": "TikTok",
    "TikTok": "TikTok",
    "youtube_shorts": "YT_Shorts",
    "yt_shorts": "YT_Shorts",
    "YT_Shorts": "YT_Shorts",
}
PLATFORM_TO_UI = {
    "IG_Reels": "instagram_reels",
    "TikTok": "tiktok",
    "YT_Shorts": "youtube_shorts",
}

# Legacy + spaced → new 2.0 underscore statuses
STATUS_TO_CANON = {
    "Draft": "Draft",
    "Idea": "Draft",
    "AI_Generated": "AI_Generated",
    "AI Generated": "AI_Generated",
    "Script Drafted": "AI_Generated",
    "Script_Drafted": "AI_Generated",
    "Raw Asset Paired": "AI_Generated",
    "Raw_Paired": "AI_Generated",
    # Legacy Render_Ready = awaiting human → AI_Generated
    "Render Ready": "AI_Generated",
    "Render_Ready": "AI_Generated",
    "Human Approved": "Human_Approved",
    "Human_Approved": "Human_Approved",
    "Ready for Render": "Ready_for_Render",
    "Ready_for_Render": "Ready_for_Render",
}


def _ensure_under_beta(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(BETA_ROOT)
    except ValueError as exc:
        raise PermissionError(f"path escapes beta-os: {path}") from exc
    return resolved


def _ensure_under_incoming(path: Path) -> Path:
    """Require resolved path under incoming_drop (upload writes only)."""
    drop = _ensure_under_beta(INCOMING_DROP)
    resolved = path.resolve()
    try:
        resolved.relative_to(drop)
    except ValueError as exc:
        raise PermissionError(f"path escapes incoming_drop: {path}") from exc
    return resolved


class UploadTooLarge(Exception):
    """Raised when upload exceeds MAX_UPLOAD_BYTES → HTTP 413."""


class UnsupportedMedia(Exception):
    """Raised for disallowed extension/content → HTTP 415."""


def today_makassar() -> date:
    return datetime.now(TZ).date()


def monday_of(d: date | None = None) -> date:
    d = d or today_makassar()
    return d - timedelta(days=d.weekday())


def week_bounds(week_monday: date) -> tuple[str, str]:
    sun = week_monday + timedelta(days=6)
    return week_monday.isoformat(), sun.isoformat()


def ensure_schema() -> None:
    _ensure_under_beta(CATALOG_DB)
    CATALOG_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS content_planner (
              id INTEGER PRIMARY KEY,
              brand TEXT,
              platform TEXT,
              scheduled_date TEXT,
              slot_time TEXT,
              title_slug TEXT,
              script_body TEXT,
              raw_asset_id INTEGER,
              status TEXT,
              updated_at DATETIME
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
              id INTEGER PRIMARY KEY,
              brand TEXT,
              stage TEXT,
              type TEXT,
              slug TEXT,
              filename TEXT,
              original_path TEXT,
              v2_path TEXT,
              source_system TEXT,
              date_added DATETIME,
              status TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS staged_assets (
              id INTEGER PRIMARY KEY,
              temp_path TEXT,
              detected_mime TEXT,
              aspect_ratio TEXT,
              duration_sec REAL,
              suggested_brand TEXT,
              suggested_stage TEXT,
              suggested_type TEXT,
              suggested_slug TEXT,
              confidence_score REAL,
              status TEXT,
              created_at DATETIME
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_logs (
              id INTEGER PRIMARY KEY,
              created_at DATETIME,
              brand TEXT,
              role TEXT,
              provider TEXT,
              model TEXT,
              prompt TEXT,
              response TEXT,
              input_tokens INTEGER,
              output_tokens INTEGER,
              status TEXT,
              error TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    # Phase 2.5B additive columns (idempotent)
    try:
        from migrations.migrate_phase2_5b_smart_upload import main as _mig_25b
        _mig_25b()
    except Exception:
        # Fallback: run SQL ALTERs inline if package import fails
        try:
            import importlib.util
            mig = Path(__file__).resolve().parent / "migrations" / "migrate_phase2_5b_smart_upload.py"
            spec = importlib.util.spec_from_file_location("migrate_phase2_5b_smart_upload", mig)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            mod.main()
        except Exception:
            pass
    # Phase 2.6 Team Readiness (idempotent)
    try:
        from migrations.migrate_phase2_6_team_readiness import main as _mig_26
        _mig_26()
    except Exception:
        try:
            import importlib.util
            mig26 = Path(__file__).resolve().parent / "migrations" / "migrate_phase2_6_team_readiness.py"
            spec26 = importlib.util.spec_from_file_location("migrate_phase2_6_team_readiness", mig26)
            mod26 = importlib.util.module_from_spec(spec26)
            assert spec26 and spec26.loader
            spec26.loader.exec_module(mod26)
            mod26.main()
        except Exception:
            pass
    # 005 Organisation Registry (idempotent)
    try:
        from migrations.migrate_org_registry import main as _mig_org
        _mig_org()
    except Exception:
        try:
            import importlib.util
            mig_org = Path(__file__).resolve().parent / "migrations" / "migrate_org_registry.py"
            spec_org = importlib.util.spec_from_file_location("migrate_org_registry", mig_org)
            mod_org = importlib.util.module_from_spec(spec_org)
            assert spec_org and spec_org.loader
            spec_org.loader.exec_module(mod_org)
            mod_org.main()
        except Exception:
            pass
    # 006 Person + Auth Identity (idempotent)
    try:
        from migrations.migrate_person_auth_identity import main as _mig_person
        _mig_person()
    except Exception:
        try:
            import importlib.util
            mig_p = Path(__file__).resolve().parent / "migrations" / "migrate_person_auth_identity.py"
            spec_p = importlib.util.spec_from_file_location("migrate_person_auth_identity", mig_p)
            mod_p = importlib.util.module_from_spec(spec_p)
            assert spec_p and spec_p.loader
            spec_p.loader.exec_module(mod_p)
            mod_p.main()
        except Exception:
            pass
    # 007 Role + Position + Assignment (idempotent)
    try:
        from migrations.migrate_role_position_assignment import main as _mig_rpa
        _mig_rpa()
    except Exception:
        try:
            import importlib.util
            mig_r = Path(__file__).resolve().parent / "migrations" / "migrate_role_position_assignment.py"
            spec_r = importlib.util.spec_from_file_location("migrate_role_position_assignment", mig_r)
            mod_r = importlib.util.module_from_spec(spec_r)
            assert spec_r and spec_r.loader
            spec_r.loader.exec_module(mod_r)
            mod_r.main()
        except Exception:
            pass
    # 008 Assignment Scope (idempotent)
    try:
        from migrations.migrate_assignment_scope import main as _mig_scope
        _mig_scope()
    except Exception:
        try:
            import importlib.util
            mig_s = Path(__file__).resolve().parent / "migrations" / "migrate_assignment_scope.py"
            spec_s = importlib.util.spec_from_file_location("migrate_assignment_scope", mig_s)
            mod_s = importlib.util.module_from_spec(spec_s)
            assert spec_s and spec_s.loader
            spec_s.loader.exec_module(mod_s)
            mod_s.main()
        except Exception:
            pass
    # 009 RBAC / Permissions (idempotent)
    try:
        from migrations.migrate_rbac_permissions import main as _mig_rbac
        _mig_rbac()
    except Exception:
        try:
            import importlib.util
            mig_b = Path(__file__).resolve().parent / "migrations" / "migrate_rbac_permissions.py"
            spec_b = importlib.util.spec_from_file_location("migrate_rbac_permissions", mig_b)
            mod_b = importlib.util.module_from_spec(spec_b)
            assert spec_b and spec_b.loader
            spec_b.loader.exec_module(mod_b)
            mod_b.main()
        except Exception:
            pass
    # 010 Authority Limits (idempotent; seeded live = 0)
    try:
        from migrations.migrate_authority_limits import main as _mig_auth
        _mig_auth()
    except Exception:
        try:
            import importlib.util
            mig_a = Path(__file__).resolve().parent / "migrations" / "migrate_authority_limits.py"
            spec_a = importlib.util.spec_from_file_location("migrate_authority_limits", mig_a)
            mod_a = importlib.util.module_from_spec(spec_a)
            assert spec_a and spec_a.loader
            spec_a.loader.exec_module(mod_a)
            mod_a.main()
        except Exception:
            pass
    for _stage in ("RAW", "EDIT", "FINAL"):
        (LIBRARY_V2 / _stage).mkdir(parents=True, exist_ok=True)


def slugify_stem(stem: str) -> str:
    s = stem.lower()
    s = DATE_RE.sub("", s)
    s = SLUG_SAFE.sub("-", s).strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:80] or "asset"


def extract_date_yyyymmdd(path: Path) -> str:
    for text in (path.stem, path.parent.name, path.name):
        m = DATE_RE.search(text)
        if m:
            y, mo, d = m.group(1), m.group(2), m.group(3)
            try:
                datetime(int(y), int(mo), int(d))
                return f"{y}{mo}{d}"
            except ValueError:
                pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d")
    except OSError:
        return datetime.now(TZ).strftime("%Y%m%d")


def build_v2_name(brand: str, stage: str, typ: str, slug: str, ymd: str, ext: str) -> str:
    ext = ext if ext.startswith(".") else f".{ext}"
    return f"{brand}_drop_{stage}_{typ}_{slug}_{ymd}{ext.lower()}"


def unique_dest(dest_dir: Path, filename: str) -> Path:
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    ext = Path(filename).suffix
    n = 2
    while True:
        alt = dest_dir / f"{stem}_v{n}{ext}"
        if not alt.exists():
            return alt
        n += 1



def client_filename_stem_ext(name: str) -> tuple[str, str]:
    """Strip path traversal; return (stem_for_metadata, ext_lower). Never use for disk path."""
    raw = Path(name or "upload").name
    raw = raw.replace("\\", "/").split("/")[-1]
    raw = raw.replace("..", "")
    p = Path(raw)
    ext = p.suffix.lower()
    stem = p.stem or "upload"
    # metadata slug suggestion: alphanumeric + dash only
    stem = re.sub(r"[^A-Za-z0-9-]+", "-", stem).strip("-") or "upload"
    stem = stem[:80]
    return stem, ext


def sanitize_upload_basename(name: str) -> str:
    """Metadata-only safe basename (stem + ext). Not used for disk writes."""
    stem, ext = client_filename_stem_ext(name)
    return f"{stem}{ext}"


def sniff_media_kind(data: bytes) -> str | None:
    """Return coarse kind from magic bytes: png|jpeg|webp|mp3|ftyp|None."""
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if len(data) >= 3 and data[:3] == b"ID3":
        return "mp3"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "mp3"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "ftyp"  # mp4 / mov / m4a family
    return None


def ext_compatible_with_magic(ext: str, kind: str | None) -> bool:
    if kind is None:
        return True  # magic inconclusive — rely on extension whitelist
    if ext == ".png":
        return kind == "png"
    if ext in (".jpg", ".jpeg"):
        return kind == "jpeg"
    if ext == ".webp":
        return kind == "webp"
    if ext == ".mp3":
        return kind == "mp3"
    if ext in (".mp4", ".mov", ".m4a"):
        return kind == "ftyp"
    return False


def unique_incoming_path(ext: str) -> Path:
    """UUID-only filename under incoming_drop + allowed extension."""
    INCOMING_DROP.mkdir(parents=True, exist_ok=True)
    drop = _ensure_under_beta(INCOMING_DROP)
    ext = (ext or "").lower()
    if ext not in UPLOAD_ALLOWED_EXT:
        raise UnsupportedMedia(f"unsupported extension: {ext or '(none)'}")
    for _ in range(32):
        candidate = drop / f"{uuid.uuid4().hex}{ext}"
        resolved = _ensure_under_incoming(candidate)
        if not resolved.exists():
            return resolved
    raise OSError("could not allocate unique incoming_drop name")


def write_upload_streaming(dest: Path, data: bytes, max_bytes: int) -> int:
    """Write bytes in chunks; abort+delete if over max_bytes. Returns bytes written."""
    dest = _ensure_under_incoming(dest)
    written = 0
    chunk = 1024 * 1024
    try:
        with open(dest, "wb") as fh:
            view = memoryview(bytes(data))
            for i in range(0, len(view), chunk):
                part = view[i : i + chunk]
                written += len(part)
                if written > max_bytes:
                    raise UploadTooLarge(f"file exceeds {max_bytes} byte limit")
                fh.write(part)
    except Exception:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return written



def parse_multipart(headers, rfile) -> dict:
    """Parse multipart/form-data into {name: str|dict}.

    File fields → {"filename": str, "content_type": str, "data": bytes}
    Text fields → str
    """
    ctype = headers.get("Content-Type") or ""
    if "multipart/form-data" not in ctype.lower():
        raise ValueError("Content-Type must be multipart/form-data")
    m = re.search(r"boundary\s*=\s*([^;\s]+)", ctype, re.I)
    if not m:
        raise ValueError("missing multipart boundary")
    boundary = m.group(1).strip().strip('"').encode("utf-8", "ignore")
    length = int(headers.get("Content-Length") or 0)
    if length <= 0:
        raise ValueError("empty upload body")
    if length > MAX_UPLOAD_BYTES:
        raise UploadTooLarge(f"upload exceeds {MAX_UPLOAD_BYTES} byte limit")
    body = rfile.read(length)
    if len(body) != length:
        raise ValueError("incomplete upload body")

    delim = b"--" + boundary
    if delim not in body:
        raise ValueError("boundary not found in body")
    parts = body.split(delim)
    fields: dict = {}
    for part in parts:
        if not part or part in (b"--", b"--\r\n", b"--\n"):
            continue
        if part.startswith(b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        elif part.startswith(b"\n"):
            part = part[1:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        elif part.endswith(b"\n"):
            part = part[:-1]
        if part == b"--" or part == b"":
            continue
        # split headers / body
        if b"\r\n\r\n" in part:
            head_b, data = part.split(b"\r\n\r\n", 1)
        elif b"\n\n" in part:
            head_b, data = part.split(b"\n\n", 1)
        else:
            continue
        if data.endswith(b"\r\n"):
            data = data[:-2]
        elif data.endswith(b"\n"):
            data = data[:-1]
        head = head_b.decode("utf-8", "replace")
        name_m = re.search(r'name="([^"]+)"', head, re.I)
        if not name_m:
            continue
        name = name_m.group(1)
        fname_m = re.search(r'filename="([^"]*)"', head, re.I)
        if fname_m is not None:
            ct_m = re.search(r"Content-Type:\s*([^\r\n]+)", head, re.I)
            fields[name] = {
                "filename": fname_m.group(1),
                "content_type": (ct_m.group(1).strip() if ct_m else "application/octet-stream"),
                "data": data,
            }
        else:
            fields[name] = data.decode("utf-8", "replace")
    return fields


def handle_remote_upload(fields: dict) -> dict:
    """Save multipart file to incoming_drop and stage (STAGED only)."""
    file_field = fields.get("file")
    if not isinstance(file_field, dict) or not file_field.get("data"):
        return {"http": 400, "body": {"status": "error", "error": "file field required"}}

    filename = file_field.get("filename") or "upload"
    data = file_field["data"]
    if not isinstance(data, (bytes, bytearray)):
        return {"http": 400, "body": {"status": "error", "error": "invalid file payload"}}
    data = bytes(data)
    if len(data) == 0:
        return {"http": 400, "body": {"status": "error", "error": "empty file"}}
    if len(data) > MAX_UPLOAD_BYTES:
        return {
            "http": 413,
            "body": {"status": "error", "error": f"file exceeds {MAX_UPLOAD_BYTES} byte limit"},
        }

    meta_stem, ext = client_filename_stem_ext(filename)
    if ext not in UPLOAD_ALLOWED_EXT:
        return {
            "http": 415,
            "body": {
                "status": "error",
                "error": f"unsupported media type / extension: {ext or '(none)'}",
            },
        }

    declared_ct = (file_field.get("content_type") or "application/octet-stream").split(";")[0].strip().lower()
    if declared_ct and declared_ct not in UPLOAD_ALLOWED_CONTENT_TYPES:
        return {
            "http": 415,
            "body": {
                "status": "error",
                "error": f"unsupported Content-Type: {declared_ct}",
            },
        }

    kind = sniff_media_kind(data)
    if not ext_compatible_with_magic(ext, kind):
        return {
            "http": 415,
            "body": {
                "status": "error",
                "error": f"content magic mismatch for extension {ext}",
            },
        }

    brand_raw = fields.get("brand")
    brand = None
    if isinstance(brand_raw, str) and brand_raw.strip():
        brand = brand_raw.strip().lower()
        if brand not in BRANDS:
            return {
                "http": 400,
                "body": {"status": "error", "error": f"invalid brand {brand!r}"},
            }

    stage_raw = fields.get("stage")
    stage = "RAW"
    if isinstance(stage_raw, str) and stage_raw.strip():
        stage = stage_raw.strip().upper()
        if stage not in STAGES:
            return {
                "http": 400,
                "body": {"status": "error", "error": f"invalid stage {stage!r}"},
            }

    try:
        dest = unique_incoming_path(ext)
        write_upload_streaming(dest, data, MAX_UPLOAD_BYTES)
        dest = _ensure_under_incoming(dest)
    except UploadTooLarge as exc:
        return {"http": 413, "body": {"status": "error", "error": str(exc)}}
    except UnsupportedMedia as exc:
        return {"http": 415, "body": {"status": "error", "error": str(exc)}}
    except PermissionError as exc:
        return {"http": 400, "body": {"status": "error", "error": str(exc)}}
    except OSError as exc:
        return {"http": 500, "body": {"status": "error", "error": f"save failed: {exc}"}}

    try:
        row = _stage_inspector.stage_file(dest, brand=brand, stage=stage)
        # Prefer slug from original upload basename (UUID disk name is not a slug).
        preferred_slug = slugify_stem(meta_stem)
        if preferred_slug and preferred_slug != row.get("suggested_slug"):
            conn = db_connect()
            try:
                conn.execute(
                    "UPDATE staged_assets SET suggested_slug = ? WHERE id = ?",
                    (preferred_slug, row["id"]),
                )
                conn.commit()
            finally:
                conn.close()
            row["suggested_slug"] = preferred_slug
    except Exception as exc:  # noqa: BLE001
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        return {"http": 500, "body": {"status": "error", "error": f"staging failed: {exc}"}}

    slug = row.get("suggested_slug") or "asset"
    b = row.get("suggested_brand") or brand or "habitat"
    st = row.get("suggested_stage") or stage
    typ = row.get("suggested_type") or "graphic"
    ymd = extract_date_yyyymmdd(dest)
    candidate = build_v2_name(b, st, typ, slug, ymd, "").rstrip(".")  # stem only
    # build_v2_name with empty ext yields trailing nothing if we pass "" — fix:
    candidate = f"{b}_drop_{st}_{typ}_{slug}_{ymd}"

    return {
        "http": 200,
        "body": {
            "status": "success",
            "staged_id": row["id"],
            "candidate_name": candidate,
            "saved_as": dest.name,
            "saved_path": str(dest),
            "original_name": sanitize_upload_basename(filename),
        },
    }



def list_staged(status: str | None) -> list[dict]:
    conn = db_connect()
    try:
        if status and status.lower() != "all":
            rows = conn.execute(
                """
                SELECT id, temp_path, detected_mime, aspect_ratio, duration_sec,
                       suggested_brand, suggested_stage, suggested_type, suggested_slug,
                       confidence_score, status, created_at
                FROM staged_assets
                WHERE status = ?
                ORDER BY created_at DESC, id DESC
                """,
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, temp_path, detected_mime, aspect_ratio, duration_sec,
                       suggested_brand, suggested_stage, suggested_type, suggested_slug,
                       confidence_score, status, created_at
                FROM staged_assets
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def commit_staged_item(item: dict) -> dict:
    """Process one staging commit item. Returns result dict with ok/status/error."""
    raw_id = item.get("id")
    if raw_id is None or str(raw_id).strip() == "":
        return {"ok": False, "id": raw_id, "error": "id required", "http": 400}
    try:
        staged_id = int(raw_id)
    except (TypeError, ValueError):
        return {"ok": False, "id": raw_id, "error": "id must be integer", "http": 400}

    action = str(item.get("action") or "").strip().lower()
    if action not in ("verify", "reject"):
        return {
            "ok": False,
            "id": staged_id,
            "error": "action must be verify|reject",
            "http": 400,
        }

    conn = db_connect()
    try:
        row = conn.execute(
            """
            SELECT id, temp_path, detected_mime, aspect_ratio, duration_sec,
                   suggested_brand, suggested_stage, suggested_type, suggested_slug,
                   confidence_score, status, created_at
            FROM staged_assets WHERE id = ?
            """,
            (staged_id,),
        ).fetchone()
        if row is None:
            return {"ok": False, "id": staged_id, "error": "staged item not found", "http": 404}
        staged = dict(row)
        if staged.get("status") not in ("STAGED",):
            return {
                "ok": False,
                "id": staged_id,
                "error": f"cannot commit: status is {staged.get('status')!r}",
                "http": 409,
            }

        if action == "reject":
            conn.execute(
                "UPDATE staged_assets SET status = ? WHERE id = ?",
                ("REJECTED", staged_id),
            )
            conn.commit()
            return {
                "ok": True,
                "id": staged_id,
                "action": "reject",
                "status": "REJECTED",
            }

        # verify
        brand = str(item.get("brand") or staged["suggested_brand"] or "habitat").strip().lower()
        stage = str(item.get("stage") or staged["suggested_stage"] or "RAW").strip().upper()
        typ = str(item.get("type") or staged["suggested_type"] or "graphic").strip().lower()
        slug = str(item.get("slug") or staged["suggested_slug"] or "asset").strip()
        slug = slugify_stem(slug) if slug else "asset"

        if brand not in BRANDS:
            return {"ok": False, "id": staged_id, "error": f"invalid brand {brand!r}", "http": 400}
        if stage not in STAGES:
            return {"ok": False, "id": staged_id, "error": f"invalid stage {stage!r}", "http": 400}
        if typ not in ASSET_TYPES:
            return {"ok": False, "id": staged_id, "error": f"invalid type {typ!r}", "http": 400}

        temp_path = Path(staged["temp_path"] or "")
        if not temp_path.is_file():
            return {
                "ok": False,
                "id": staged_id,
                "error": f"temp_path missing: {temp_path}",
                "http": 404,
            }

        # Safety: refuse wolf-system sources
        try:
            resolved = str(temp_path.resolve())
        except OSError as exc:
            return {"ok": False, "id": staged_id, "error": str(exc), "http": 409}
        if "/wolf-system" in resolved:
            return {
                "ok": False,
                "id": staged_id,
                "error": "refuse: temp_path under wolf-system",
                "http": 403,
            }

        ymd = extract_date_yyyymmdd(temp_path)
        filename = build_v2_name(brand, stage, typ, slug, ymd, temp_path.suffix)
        dest_dir = LIBRARY_V2 / stage
        dest_dir.mkdir(parents=True, exist_ok=True)
        _ensure_under_beta(dest_dir)
        dest = unique_dest(dest_dir, filename)
        filename = dest.name

        try:
            shutil.move(str(temp_path), str(dest))
        except OSError:
            shutil.copy2(str(temp_path), str(dest))
            try:
                temp_path.unlink()
            except OSError:
                pass

        now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            """
            INSERT INTO assets (
              brand, stage, type, slug, filename,
              original_path, v2_path, source_system, date_added, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brand,
                stage,
                typ,
                slug,
                filename,
                resolved,
                str(dest),
                "staging",
                now,
                "indexed",
            ),
        )
        asset_id = cur.lastrowid
        conn.execute(
            """
            UPDATE staged_assets SET
              status = ?,
              suggested_brand = ?,
              suggested_stage = ?,
              suggested_type = ?,
              suggested_slug = ?
            WHERE id = ?
            """,
            ("VERIFIED", brand, stage, typ, slug, staged_id),
        )
        conn.commit()
        return {
            "ok": True,
            "id": staged_id,
            "action": "verify",
            "status": "VERIFIED",
            "asset_id": asset_id,
            "filename": filename,
            "v2_path": str(dest),
            "brand": brand,
            "stage": stage,
            "type": typ,
            "slug": slug,
        }
    finally:
        conn.close()


def db_connect() -> sqlite3.Connection:
    _ensure_under_beta(CATALOG_DB)
    conn = sqlite3.connect(str(CATALOG_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def canon_platform(p: str | None) -> str:
    raw = (p or "").strip()
    return PLATFORM_TO_CANON.get(raw, PLATFORM_TO_CANON.get(raw.lower(), raw or "IG_Reels"))


def canon_status(s: str | None) -> str:
    raw = (s or "Draft").strip()
    if raw in STATUS_TO_CANON:
        return STATUS_TO_CANON[raw]
    if raw in ALL_STATUSES:
        return raw
    return "Draft"


def row_to_slot(row: sqlite3.Row | dict, week_monday: date) -> dict:
    d = dict(row)
    sched = d.get("scheduled_date") or week_monday.isoformat()
    try:
        sd = date.fromisoformat(str(sched)[:10])
        day = (sd - week_monday).days
        if day < 0 or day > 6:
            day = 0
    except ValueError:
        day = 0
        sd = week_monday
    plat = d.get("platform") or "IG_Reels"
    return {
        "id": d["id"],
        "day": day,
        "platform": PLATFORM_TO_UI.get(plat, plat),
        "platform_canon": plat,
        "title": d.get("title_slug") or "",
        "title_slug": d.get("title_slug") or "",
        "script_body": d.get("script_body") or "",
        "slot_time": d.get("slot_time") or "",
        "status": canon_status(d.get("status")),
        "asset_id": d.get("raw_asset_id"),
        "raw_asset_id": d.get("raw_asset_id"),
        "scheduled_date": sd.isoformat(),
        "brand": d.get("brand"),
        "updated_at": d.get("updated_at"),
    }


def fetch_week(brand: str, week_monday: date) -> list[dict]:
    start, end = week_bounds(week_monday)
    conn = db_connect()
    try:
        brand_key = (brand or "").strip().lower()
        if brand_key in ("", "all", "*"):
            rows = conn.execute(
                """
                SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                       script_body, raw_asset_id, status, updated_at
                FROM content_planner
                WHERE scheduled_date >= ? AND scheduled_date <= ?
                ORDER BY scheduled_date, brand, platform, id
                """,
                (start, end),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                       script_body, raw_asset_id, status, updated_at
                FROM content_planner
                WHERE brand = ? AND scheduled_date >= ? AND scheduled_date <= ?
                ORDER BY scheduled_date, platform, id
                """,
                (brand, start, end),
            ).fetchall()
        return [row_to_slot(r, week_monday) for r in rows]
    finally:
        conn.close()


def get_slot(slot_id: int) -> dict | None:
    conn = db_connect()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(content_planner)")}
        extra = ""
        for c in (
            "content_version_hash",
            "work_item_id",
            "core_approval_request_id",
            "approved_version_hash",
        ):
            if c in cols:
                extra += f", {c}"
        row = conn.execute(
            f"""
            SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                   script_body, raw_asset_id, status, updated_at{extra}
            FROM content_planner WHERE id = ?
            """,
            (slot_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def assert_publish_allowed(slot_id: int, *, verified_person_id: str | None = None) -> dict:
    """Core-canonical Habitat publish gate. Raises unless READY_TO_PUBLISH.

    Legacy Human_Approved alone is NEVER sufficient. Does not enable Metricool write.
    """
    gate = _content_publish.assert_habitat_publish_allowed(
        int(slot_id),
        verified_person_id=verified_person_id,
    )
    if not gate.get("ok") or gate.get("stage") != "READY_TO_PUBLISH":
        raise PermissionError(
            f"publish denied: slot {slot_id} stage={gate.get('stage')!r} "
            f"reason={gate.get('reason')!r}"
        )
    return gate


def query_assets(qs: dict) -> list[dict]:
    """Library listing — Phase 2.6 filters. Default data_lane=operational. No FS paths."""
    _ensure_under_beta(CATALOG_DB)
    if not CATALOG_DB.exists():
        return []
    clauses: list[str] = []
    params: list = []

    def _one(key, col=None):
        vals = qs.get(key) or []
        val = (vals[0] if vals else "").strip()
        if val:
            clauses.append(f"{col or key} = ?")
            params.append(val)

    _one("brand")
    _one("stage")
    _one("source_system")
    # status / readiness
    readiness = ((qs.get("readiness") or [""])[0] or "").strip().upper()
    status = ((qs.get("status") or [""])[0] or "").strip()
    if readiness:
        clauses.append("upper(ifnull(readiness, '')) = ?")
        params.append(readiness)
    elif status:
        if status.upper() in ("READY_TO_USE", "CHECKING", "FAILED"):
            clauses.append("upper(ifnull(readiness, '')) = ?")
            params.append(status.upper())
        else:
            clauses.append("status = ?")
            params.append(status)

    media = ((qs.get("media_type") or qs.get("type") or [""])[0] or "").strip().lower()
    if media in ("video", "photo", "image"):
        if media == "photo":
            media = "image"
        clauses.append("lower(ifnull(media_type, type)) IN (?, ?)" if media == "image" else "lower(ifnull(media_type, type)) = ?")
        if media == "image":
            params.extend(["image", "graphic"])
        else:
            params.append(media)
    elif media:
        clauses.append("lower(ifnull(media_type, type)) = ?")
        params.append(media)

    shoot = ((qs.get("shoot_date") or [""])[0] or "").strip()
    if shoot:
        clauses.append("shoot_date = ?")
        params.append(shoot)
    subject = ((qs.get("subject") or [""])[0] or "").strip()
    if subject:
        clauses.append("lower(ifnull(subject,'')) LIKE ?")
        params.append(f"%{subject.lower()}%")
    location = ((qs.get("location") or [""])[0] or "").strip()
    if location:
        clauses.append("lower(ifnull(location,'')) LIKE ?")
        params.append(f"%{location.lower()}%")

    q = ((qs.get("q") or qs.get("search") or [""])[0] or "").strip()
    if q:
        clauses.append(
            "(lower(ifnull(canonical_filename,'')) LIKE ? OR lower(ifnull(original_filename,'')) LIKE ? "
            "OR lower(ifnull(subject,'')) LIKE ? OR lower(ifnull(detail,'')) LIKE ? OR lower(ifnull(slug,'')) LIKE ?)"
        )
        like = f"%{q.lower()}%"
        params.extend([like, like, like, like, like])

    lane = ((qs.get("data_lane") or qs.get("lane") or ["operational"])[0] or "operational").strip().lower()
    if lane == "operational":
        clauses.append("ifnull(data_lane,'operational') = 'operational'")
    elif lane == "test":
        clauses.append("ifnull(data_lane,'operational') = 'test'")

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        "SELECT id, brand, stage, type, slug, filename, "
        "source_system, date_added, status, "
        "original_filename, canonical_filename, subject, detail, location, "
        "shoot_date, sequence_token, media_type, uploaded_by, uploaded_at, "
        "content_plan_id, content_card_id, processing_status, library_status, "
        "data_lane, batch_id, content_hash, file_size, detail_tags_json, "
        "readiness, readiness_note "
        f"FROM assets{where} "
        "ORDER BY date_added DESC, id DESC"
    )
    conn = db_connect()
    try:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        out = []
        for r in rows:
            typ = (r.get("media_type") or r.get("type") or "").lower()
            if typ in ("video", "broll"):
                thumb = "video"
                media_label = "Video"
            elif typ in ("image", "graphic"):
                thumb = "image"
                media_label = "Photo" if typ == "image" else "Graphic"
            elif typ == "audio":
                thumb = "audio"
                media_label = "Audio"
            else:
                thumb = "file"
                media_label = typ or "File"
            ready, note = _p26.readiness_from_row(r)
            tags = []
            try:
                tags = json.loads(r.get("detail_tags_json") or "[]") or []
            except (TypeError, json.JSONDecodeError):
                tags = _p26.parse_detail_tags(r.get("detail"))
            out.append({
                "id": r.get("id"),
                "brand": r.get("brand"),
                "brand_badge": (r.get("brand") or "").title(),
                "stage": r.get("stage"),
                "canonical_name": r.get("canonical_filename") or r.get("filename") or r.get("slug"),
                "original_name": r.get("original_filename") or "",
                "name": r.get("canonical_filename") or r.get("filename") or r.get("slug"),
                "media_type": typ,
                "media_label": media_label,
                "thumb": thumb,
                "shoot_date": r.get("shoot_date") or "",
                "subject": r.get("subject") or "",
                "detail": r.get("detail") or "",
                "detail_tags": tags,
                "location": r.get("location") or "",
                "readiness": ready,
                "readiness_label": _p26.READINESS_LABELS.get(ready, ready),
                "readiness_note": note,
                "library_status": r.get("library_status") or r.get("status"),
                "date_added": r.get("date_added"),
                "file_size": r.get("file_size"),
                "batch_id": r.get("batch_id"),
                "preview_url": f"/api/assets/{r.get('id')}/preview" if r.get("id") else None,
                "download_url": f"/api/assets/{r.get('id')}/download" if r.get("id") else None,
                # never paths
            })
        return out
    finally:
        conn.close()


# ----- Phase 2.5 UX helpers (additive; no schema destroy) -----

UX_WORKFLOW_STATUSES = (
    "NOT_STARTED",
    "NEEDS_FILMING",
    "READY",
    "IN_PRODUCTION",
    "EDITING",
    "READY_FOR_REVIEW",
    "COMPLETE",
)

UX_STATUS_LABELS = {
    "NOT_STARTED": "NOT STARTED",
    "NEEDS_FILMING": "NEEDS FILMING",
    "READY": "READY",
    "IN_PRODUCTION": "IN PRODUCTION",
    "EDITING": "EDITING",
    "READY_FOR_REVIEW": "READY FOR REVIEW",
    "COMPLETE": "COMPLETE",
}

_BRAND_TITLE_NAMES = {
    "habitat": "Habitat",
    "umablu": "Uma Blu",
    "atrium": "Atrium",
    "selo": "Selo",
    "tropik": "Tropik",
}
_TITLE_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _human_fortnight_title(
    brand_id: str,
    period_start: str,
    period_end: str,
    display_name: str | None = None,
) -> str:
    """Human plan title on read and on new creates. e.g. Habitat Fortnight Sep 14—27.

    Uses wolf_intelligence.format_fortnight_title when that helper is present.
    Does not rewrite historical rows.
    """
    fn = getattr(_wi, "format_fortnight_title", None)
    if callable(fn):
        try:
            return fn(brand_id, period_start, period_end, display_name)
        except TypeError:
            return fn(brand_id, period_start, period_end)
    bid = (brand_id or "").strip().lower()
    if bid in _BRAND_TITLE_NAMES:
        name = _BRAND_TITLE_NAMES[bid]
    elif display_name:
        name = str(display_name).split("/")[0].strip() or (bid.title() if bid else "Brand")
    else:
        name = bid.title() if bid else "Brand"
    try:
        start = date.fromisoformat(str(period_start)[:10])
        end = date.fromisoformat(str(period_end)[:10])
    except ValueError:
        return f"{name} Fortnight"
    if start.month == end.month and start.year == end.year:
        span = f"{_TITLE_MONTHS[start.month - 1]} {start.day}—{end.day}"
    else:
        span = (
            f"{_TITLE_MONTHS[start.month - 1]} {start.day}—"
            f"{_TITLE_MONTHS[end.month - 1]} {end.day}"
        )
    return f"{name} Fortnight {span}"


def _ux_derive_workflow_status(card: dict, body: dict | None = None) -> str:
    """Map card + body to team-facing workflow status without exposing AI/HUMAN roles."""
    body = body if isinstance(body, dict) else {}
    ws = (body.get("workflow_status") or "").strip().upper().replace(" ", "_")
    if ws in UX_WORKFLOW_STATUSES:
        return ws
    asset = (card.get("asset_status") or body.get("asset_status") or "").upper()
    raw = (card.get("status") or "").upper()
    if raw in UX_WORKFLOW_STATUSES:
        return raw
    if raw == "COMPLETE" or asset in ("MATCH", "READY", "HAVE"):
        if asset in ("MATCH", "READY", "HAVE") and raw not in ("AI_PROPOSAL", "HUMAN_EDIT"):
            return "READY"
    if asset in ("FILM", "NEEDED", "MISSING", "NEED"):
        return "NEEDS_FILMING"
    # Default for new AI proposals that still need filming
    if asset == "FILM" or not asset:
        return "NEEDS_FILMING" if asset == "FILM" else "NOT_STARTED"
    return "NOT_STARTED"



def _ux_card_brief(card: dict) -> dict:
    """Phase 2.6 human brief — posts/stories primary fields only (no forced Goal/Theme/Concept/Hook on team brief)."""
    try:
        body = card.get("body") if isinstance(card.get("body"), dict) else json.loads(card.get("body_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    workflow = _ux_derive_workflow_status(card, body)
    card_type = (card.get("card_type") or "feed").lower()
    kind = "POST" if card_type in ("feed", "post") else "STORY"
    seq = int(card.get("sequence") or 0)
    shot_list = body.get("recommended_shot_list") or body.get("shot_list") or []
    if isinstance(shot_list, str):
        shot_list = [s.strip() for s in shot_list.split("\n") if s.strip()]
    hashtags = body.get("hashtags") or []
    if isinstance(hashtags, str):
        hashtags = [s.strip() for s in hashtags.replace(",", " ").split() if s.strip()]
    pillar = body.get("pillar") or body.get("theme") or ""
    caption_dir = body.get("caption_direction") or body.get("caption") or body.get("caption_draft") or ""
    cta = body.get("cta") or body.get("story_cta") or ""
    post_type = _p26.map_post_type(body) if kind == "POST" else ""
    breakdown = _p26.content_breakdown_from_body(body, kind)
    evergreen = bool(body.get("evergreen")) if "evergreen" in body else False
    story_cta = (body.get("story_cta") or body.get("cta_type") or body.get("cta") or "NONE")
    if kind == "STORY" and isinstance(story_cta, str):
        story_cta = story_cta.strip().upper() or "NONE"
    inspiration = body.get("inspiration_examples") or body.get("inspiration") or ""
    assignee = body.get("assignee") or ""
    brief = {
        # POST primary
        "post_title": card.get("title") or "",
        "post_type": post_type,
        "pillar": pillar,
        "content_breakdown": breakdown,
        "caption_direction": caption_dir,
        "cta": cta if kind == "POST" else "",
        "hashtags": hashtags,
        "recommended_shot_list": shot_list,
        "status": workflow,
        "assignee": assignee,
        "inspiration_examples": inspiration,
        # STORY primary
        "story_title": card.get("title") or "",
        "goal_purpose": body.get("goal") or body.get("goal_purpose") or "",
        "story_breakdown": breakdown if kind == "STORY" else [],
        "story_cta": story_cta if kind == "STORY" else "",
        "evergreen": evergreen,
        # retained internal (not forced in team UI)
        "hook": body.get("hook") or "",
        "theme": pillar,
        "goal": body.get("goal") or "",
        "shot_list_note": body.get("shot_list_note")
        or "Suggested coverage. Adapt based on conditions, talent and creative opportunities on location.",
        "production_notes": body.get("production_notes") or "",
    }
    return {
        "id": card.get("id"),
        "plan_id": card.get("plan_id"),
        "kind": kind,
        "number": seq,
        "label": f"{kind} {seq}" if seq else kind,
        "date": "" if evergreen else (body.get("scheduled_date") or ""),
        "evergreen": evergreen,
        "format": post_type or body.get("format") or body.get("platform") or ("IG_Reels" if kind == "POST" else "IG_Story"),
        "theme": pillar,
        "title": card.get("title") or "",
        "status": workflow,
        "status_label": UX_STATUS_LABELS.get(workflow, workflow.replace("_", " ")),
        "asset_status": card.get("asset_status") or body.get("asset_status") or "",
        "assignee": assignee,
        "brief": brief,
    }


def _ux_shape_plan(draft: dict) -> dict:
    """Order posts then stories; posts/stories progress; review_state labels for team."""
    plan = dict(draft.get("plan") or {})
    feeds = draft.get("feed_cards") or []
    stories = draft.get("story_spine") or []
    posts = [_ux_card_brief(c) for c in sorted(feeds, key=lambda x: int(x.get("sequence") or 0))]
    story_cards = [_ux_card_brief(c) for c in sorted(stories, key=lambda x: int(x.get("sequence") or 0))]
    # Brand-level default assignee inheritance (display + empty fields); human override preserved when set
    try:
        brand_id = (plan.get("brand_id") or "").strip().lower()
        if brand_id:
            _bc = db_connect()
            try:
                brow = _bc.execute(
                    "SELECT default_assignee, theme_json, display_name, id, logo_url FROM brands WHERE id=?",
                    (brand_id,),
                ).fetchone()
                default_asg = ""
                if brow:
                    default_asg = (dict(brow).get("default_assignee") or "").strip()
                if default_asg:
                    for c in posts + story_cards:
                        if not (c.get("assignee") or "").strip():
                            c["assignee"] = default_asg
                            if isinstance(c.get("brief"), dict):
                                c["brief"]["assignee"] = default_asg
            finally:
                _bc.close()
    except Exception:
        pass
    strategy = draft.get("strategy") or {}
    feed_t = int(strategy.get("feed_target") or plan.get("feed_target") or 3)
    story_t = int(strategy.get("story_target") or plan.get("story_target") or 14)
    complete_posts = sum(1 for c in posts if c["status"] == "COMPLETE")
    complete_stories = sum(1 for c in story_cards if c["status"] == "COMPLETE")
    filming = [c for c in posts + story_cards if c["status"] == "NEEDS_FILMING"]
    awaiting = [c for c in posts + story_cards if c["status"] == "READY_FOR_REVIEW"]
    lane = plan.get("data_lane") or "operational"
    rev_label = _p26.review_label(plan)
    # Map DB status to UI without jargon
    ui_status = rev_label
    if rev_label == "WORKING":
        ui_status = "WORKING"
    # Format-on-read: human fortnight title; keep DB title as title_raw
    title_raw = plan.get("title") or ""
    title_human = _human_fortnight_title(
        plan.get("brand_id") or "",
        plan.get("period_start") or "",
        plan.get("period_end") or "",
    ) if (plan.get("period_start") and plan.get("period_end")) else title_raw
    return {
        "plan": {
            **{k: plan.get(k) for k in (
                "id", "brand_id", "title", "period_start", "period_end",
                "status", "created_by", "created_at", "updated_at", "data_lane",
                "review_state", "approved_revision_id",
            )},
            "title": title_human or title_raw,
            "title_raw": title_raw,
            "status_label": ui_status,
            "review_state": plan.get("review_state") or ("APPROVED" if rev_label == "APPROVED" else "WORKING"),
            "review_label": rev_label,
            "ui_status": ui_status,
        },
        "posts": posts,
        "stories": story_cards,
        "progress": {
            "posts_complete": complete_posts,
            "posts_target": feed_t,
            "posts_label": f"{complete_posts}/{feed_t}",
            "stories_complete": complete_stories,
            "stories_target": story_t,
            "stories_label": f"{complete_stories}/{story_t}",
            "needs_filming": len(filming),
            "awaiting_review": len(awaiting),
        },
        "strategy": {
            "feed_target": feed_t,
            "story_target": story_t,
            "theme": strategy.get("theme") or "",
            "checklist_line": (strategy.get("checklist_line")
                               or "Plan prepared using available brand, historical and performance information."),
        },
        "data_lane": lane,
    }

class BetaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARDS), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            body: dict = {}
        else:
            parsed = json.loads(raw.decode("utf-8"))
            body = parsed if isinstance(parsed, dict) else {}
        # Cache for resolve_authenticated_subject(self) duck-typing
        self._wolf_body_cache = body
        return body

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_err(self, status: int, message: str) -> None:
        self._send_json({"ok": False, "error": message}, status=status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if ".." in path:
            self._send_err(403, "path escapes beta-os")
            return

        if path == "/api/health":
            self._send_json({"ok": True, "root": "beta-os", "planner": "sqlite"})
            return

        if path == "/api/assets":
            try:
                rows = query_assets(qs)
                # Phase 2.6: query_assets already strips FS paths
                self._send_json({"ok": True, "assets": rows, "count": len(rows)})
            except Exception as exc:  # noqa: BLE001
                self._send_err(500, str(exc))
            return

        # GET /api/assets/{id}/preview|download — stream media (no path leak in JSON)
        m_asset = re.match(r"^/api/assets/(\d+)/(preview|download)$", path)
        if m_asset:
            self._asset_media(int(m_asset.group(1)), m_asset.group(2), qs)
            return

        if path == "/api/nas/status":
            self._send_json({"ok": True, **_smart_upload.nas_status()})
            return

        if path == "/api/upload/recent":
            try:
                items = _smart_upload.list_smart_uploads(sys.modules[__name__], qs)
                self._send_json({"ok": True, "items": items, "count": len(items), "nas": _smart_upload.nas_status()})
            except Exception as exc:  # noqa: BLE001
                self._send_err(500, str(exc))
            return

        if path == "/api/staging/list":
            try:
                status = (qs.get("status") or ["STAGED"])[0].strip() or "STAGED"
                rows = list_staged(status)
                self._send_json({"ok": True, "items": rows, "count": len(rows), "status": status})
            except Exception as exc:  # noqa: BLE001
                self._send_err(500, str(exc))
            return

        if path == "/api/planner":
            self._get_planner(qs)
            return

        if path == "/api/planner/publish-gate":
            self._publish_gate(qs)
            return

        # Wolf Core auth mode diagnostics (no secrets)
        if path == "/api/core/auth-mode":
            self._send_json(_request_auth.auth_mode_payload())
            return

        # BZG / Uma Blu ops console (Beta — read). Fail-closed: identity + permission + Uma scope.
        if path == "/api/bzg/uma-blu" or path.startswith("/api/bzg/uma-blu/"):
            if self._require_uma_ops() is None:
                return
            if path == "/api/bzg/uma-blu/today":
                self._uma_ops_today()
                return
            if path == "/api/bzg/uma-blu/prs":
                self._uma_ops_prs()
                return
            m_pr = re.match(r"^/api/bzg/uma-blu/prs/([^/]+)$", path)
            if m_pr:
                self._uma_ops_pr_detail(m_pr.group(1))
                return
            if path == "/api/bzg/uma-blu/issues":
                self._uma_ops_issues()
                return
            if path == "/api/bzg/uma-blu/history":
                self._uma_ops_history()
                return
            if path == "/api/bzg/uma-blu/honesty":
                self._uma_ops_honesty()
                return
            if path == "/api/bzg/uma-blu/petty":
                self._uma_ops_petty()
                return
            self._send_json(
                {
                    "ok": False,
                    "error": "not_found",
                    "message": "Unknown Uma Blu route.",
                },
                status=404,
            )
            return

        # Uma Blu daily close (Beta — read)
        if path == "/api/venue-close/honesty":
            self._venue_close_honesty()
            return
        if path == "/api/venue-close/list":
            self._venue_close_list(qs)
            return
        if path == "/api/venue-close/previous":
            self._venue_close_previous(qs)
            return
        if path == "/api/venue-close/capabilities":
            self._venue_close_capabilities()
            return
        # CAP-INTEL-01 read-only orchestration. Owner / PERS-MATT. Anon → 403.
        if path == "/api/intel/orchestrate":
            self._intel_orchestrate(qs)
            return
        # Matt Progress Dashboard — Owner / PERS-MATT only
        if path == "/api/progress/honesty":
            self._progress_honesty()
            return
        if path == "/api/progress/calculation":
            self._progress_calculation()
            return
        if path == "/api/progress/view":
            self._progress_view(qs)
            return
        if path == "/api/progress":
            self._progress_empire()
            return
        m_vc = re.match(r"^/api/venue-close/([^/]+)$", path)
        if m_vc and m_vc.group(1) not in (
            "open",
            "capture",
            "declare-cash",
            "reconcile",
            "exception",
            "resolve",
            "verify",
            "honesty",
            "list",
            "previous",
            "capabilities",
        ):
            self._venue_close_get(m_vc.group(1), qs)
            return

        # Wolf Core RBAC (WHAT; identity via request_auth)
        if path == "/api/core/permissions":
            self._get_core_permissions()
            return
        if path == "/api/core/me/permissions":
            self._get_core_me_permissions()
            return

        # Wolf Core Authority Limits (HOW MUCH; read/check only — no admin UI)
        if path == "/api/core/authority/check":
            self._get_core_authority_check(qs)
            return
        if path == "/api/core/me/authority-limits":
            self._get_core_me_authority_limits()
            return

        # Wolf Core Audit / Evidence Spine (read-only; Matt / Owner only)
        if path == "/api/core/audit":
            self._get_core_audit(qs)
            return

        # Wolf Core Work Items (task primitive; not org_assignments)
        if path == "/api/core/work-items":
            self._get_core_work_items(qs)
            return
        m_wi = re.match(r"^/api/core/work-items/([^/]+)$", path)
        if m_wi:
            self._get_core_work_item(m_wi.group(1))
            return

        # Wolf Core Approval Engine (REQUESTED ≠ APPROVED ≠ EXECUTED)
        if path == "/api/core/approvals":
            self._get_core_approvals(qs)
            return
        m_apr = re.match(r"^/api/core/approvals/([^/]+)$", path)
        if m_apr:
            self._get_core_approval(m_apr.group(1))
            return

        # Wolf Core Delegation (IDENTITY NEVER DELEGATES)
        if path == "/api/core/delegations":
            self._get_core_delegations(qs)
            return
        m_dlg = re.match(r"^/api/core/delegations/([^/]+)$", path)
        if m_dlg:
            self._get_core_delegation(m_dlg.group(1))
            return

        # Wolf Core Assignment Scope (read-only; WHERE only — no RBAC)
        if path == "/api/core/scopes":
            self._get_core_scopes()
            return
        m_scope = re.match(r"^/api/core/scopes/([^/]+)$", path)
        if m_scope:
            self._get_core_scope(m_scope.group(1))
            return
        m_asg_scopes = re.match(r"^/api/core/assignments/([^/]+)/scopes$", path)
        if m_asg_scopes:
            self._get_core_assignment_scopes(m_asg_scopes.group(1))
            return
        if path == "/api/core/me/scopes":
            self._get_core_me_scopes()
            return

        # Wolf Core Role / Position / Assignment (read-only; org_* not LLM role)
        if path == "/api/core/roles":
            self._get_core_roles()
            return
        m_role = re.match(r"^/api/core/roles/([^/]+)$", path)
        if m_role:
            self._get_core_role(m_role.group(1))
            return
        if path == "/api/core/positions":
            self._get_core_positions()
            return
        m_pos = re.match(r"^/api/core/positions/([^/]+)$", path)
        if m_pos:
            self._get_core_position(m_pos.group(1))
            return
        m_pos_asg = re.match(r"^/api/core/positions/([^/]+)/assignments$", path)
        if m_pos_asg:
            self._get_core_position_assignments(m_pos_asg.group(1))
            return
        m_pers_asg = re.match(r"^/api/core/persons/([^/]+)/assignments$", path)
        if m_pers_asg:
            self._get_core_person_assignments(m_pers_asg.group(1))
            return
        if path == "/api/core/me/assignments":
            self._get_core_me_assignments()
            return

        # Wolf Core Person + Auth Identity (read-only; DEVELOPMENT assertion honesty)
        if path == "/api/core/persons":
            self._get_core_persons()
            return
        m_pers = re.match(r"^/api/core/persons/([^/]+)$", path)
        if m_pers:
            self._get_core_person(m_pers.group(1))
            return
        m_pers_auth = re.match(r"^/api/core/persons/([^/]+)/auth-identities$", path)
        if m_pers_auth:
            self._get_core_person_auth_identities(m_pers_auth.group(1))
            return
        if path == "/api/core/me":
            self._get_core_me()
            return

        # Wolf Core Organisation Registry (read-only)
        if path == "/api/core/entities":
            self._get_core_entities()
            return
        m_ent = re.match(r"^/api/core/entities/([^/]+)$", path)
        if m_ent:
            self._get_core_entity(m_ent.group(1))
            return
        m_ent_brands = re.match(r"^/api/core/entities/([^/]+)/brands$", path)
        if m_ent_brands:
            self._get_core_entity_brands(m_ent_brands.group(1))
            return
        m_ent_locs = re.match(r"^/api/core/entities/([^/]+)/locations$", path)
        if m_ent_locs:
            self._get_core_entity_locations(m_ent_locs.group(1))
            return
        m_ent_deps = re.match(r"^/api/core/entities/([^/]+)/departments$", path)
        if m_ent_deps:
            self._get_core_entity_departments(m_ent_deps.group(1))
            return
        m_brand = re.match(r"^/api/core/brands/([^/]+)$", path)
        if m_brand:
            self._get_core_brand(m_brand.group(1))
            return

        if path == "/api/brands":
            self._get_brands()
            return

        if path == "/api/admin/sync-metricool":
            self._admin_sync_metricool(from_get=True)
            return

        # GET /api/planner/plans — list Working Drafts for brand (Phase 2.5)
        if path == "/api/planner/plans":
            self._list_intel_plans(qs)
            return

        # GET /api/planner/dashboard?brand= — team dashboard summary
        if path == "/api/planner/dashboard":
            self._get_ux_dashboard(qs)
            return

        # GET /api/me/capabilities — can_create_plan for management UI (no secrets)
        if path == "/api/me/capabilities":
            self._get_me_capabilities(qs)
            return

        # GET /api/planner/plans/{id}/changes — VIEW CHANGES (approved vs current)
        m_changes = re.match(r"^/api/planner/plans/(\d+)/changes$", path)
        if m_changes:
            self._get_plan_changes(int(m_changes.group(1)))
            return

        # GET /api/wolf/actions — WI quick actions catalog
        if path == "/api/wolf/actions":
            self._send_json({
                "ok": True,
                "connected": False,
                "actions": [{"id": a, "label": l} for a, l in _p26.WI_QUICK_ACTIONS],
                "message": "Chat shell ready. Live generation not connected this phase.",
            })
            return

        # GET /api/planner/cards/{id} — content brief (human fields)
        m_card = re.match(r"^/api/planner/cards/(\d+)$", path)
        if m_card:
            self._get_ux_card(int(m_card.group(1)))
            return

        # GET /api/planner/plans/{id} — Working Draft (+ ux=1 for product shape)
        m_plan = re.match(r"^/api/planner/plans/(\d+)$", path)
        if m_plan:
            self._get_intel_plan(int(m_plan.group(1)), qs=qs)
            return

        # Lead Spine operator (Beta fixtures) — identity from CF Access only
        if path == "/api/leads":
            self._get_leads(qs)
            return
        m_lead = re.match(r"^/api/leads/([^/]+)$", path)
        if m_lead:
            self._get_lead(m_lead.group(1))
            return

        if path in ("/", "/index.html"):
            self.path = "/content-2.0.html"
        elif path in ("/progress", "/progress/"):
            self.path = "/progress.html"
        elif path in ("/uma-blu-close", "/uma-blu-close/"):
            self.path = "/uma-blu-close.html"
        elif path in ("/bzg", "/bzg/"):
            self.path = "/bzg.html"
        elif path in ("/bzg/uma-blu", "/bzg/uma-blu/"):
            self.path = "/bzg-uma-blu.html"
        elif path in ("/bzg/uma-blu/bills", "/bzg/uma-blu/bills/") and (qs.get("pr") or [""])[0].strip():
            self.path = "/bzg-uma-blu-pr.html"
        elif path in ("/bzg/uma-blu/bills", "/bzg/uma-blu/bills/"):
            self.path = "/bzg-uma-blu-bills.html"
        elif re.match(r"^/bzg/uma-blu/bills/([^/]+)/?$", path):
            self.path = "/bzg-uma-blu-pr.html"
        elif path in ("/bzg/uma-blu/issues", "/bzg/uma-blu/issues/"):
            self.path = "/bzg-uma-blu-issues.html"
        elif path in ("/bzg/uma-blu/petty", "/bzg/uma-blu/petty/"):
            self.path = "/bzg-uma-blu-petty.html"
        elif path in ("/habitat-operator", "/habitat-operator/"):
            self.path = "/habitat-operator.html"
        elif path in ("/lead-spine", "/lead-spine/"):
            self.path = "/lead-spine.html"
        elif path == "/dashboards/progress.html":
            self.path = "/progress.html"
        elif path == "/dashboards/uma-blu-close.html":
            self.path = "/uma-blu-close.html"
        elif path == "/dashboards/bzg.html":
            self.path = "/bzg.html"
        elif path == "/dashboards/bzg-uma-blu.html":
            self.path = "/bzg-uma-blu.html"
        elif path == "/dashboards/bzg-uma-blu-bills.html":
            self.path = "/bzg-uma-blu-bills.html"
        elif path == "/dashboards/bzg-uma-blu-issues.html":
            self.path = "/bzg-uma-blu-issues.html"
        elif path == "/dashboards/bzg-uma-blu-petty.html":
            self.path = "/bzg-uma-blu-petty.html"
        elif path == "/dashboards/habitat-operator.html":
            self.path = "/habitat-operator.html"
        elif path == "/dashboards/lead-spine.html":
            self.path = "/lead-spine.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/planner/save":
            self._save_slot()
            return
        if path == "/api/planner/approve":
            self._approve_slot()
            return
        if path == "/api/planner/submit-for-approval":
            self._submit_for_approval()
            return
        if path == "/api/planner/ready-render":
            self._ready_render_slot()
            return
        if path == "/api/planner/render":
            self._render_slot()
            return
        if path == "/api/planner/attach-asset":
            self._attach_asset()
            return
        if path == "/api/staging/commit":
            self._staging_commit()
            return
        if path == "/api/upload/preview-names":
            self._upload_preview_names()
            return

        if path == "/api/upload/smart":
            self._upload_smart()
            return

        if path == "/api/upload/remote":
            self._upload_remote()
            return
        if path == "/api/llm/generate":
            self._llm_generate()
            return
        # Uma Blu mutations. Reads use the same gate. Unknown writes stay forbidden
        # (payment approve / closer submit / float invent are not granted here).
        if path == "/api/bzg/uma-blu" or path.startswith("/api/bzg/uma-blu/"):
            if self._require_uma_ops() is None:
                return
            if path == "/api/bzg/uma-blu/petty":
                self._uma_ops_petty_post()
                return
            if path == "/api/bzg/uma-blu/receive":
                self._uma_ops_receive_post()
                return
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Uma Blu mutation is not authorised on this route.",
                    "required_permission": "venue.close.read",
                },
                status=403,
            )
            return
        # Legacy aliases → same handlers
        if path == "/api/planner":
            self._save_slot()
            return

        # --- Phase 1 Intelligence ---
        if path == "/api/planner/build-next":
            self._intel_build_next()
            return

        m_plan_edit = re.match(r"^/api/planner/plans/(\d+)/(edit|revision)$", path)
        if m_plan_edit:
            self._intel_plan_edit(int(m_plan_edit.group(1)))
            return
        m_plan_edit2 = re.match(r"^/api/plans/(\d+)/revision$", path)
        if m_plan_edit2:
            self._intel_plan_edit(int(m_plan_edit2.group(1)))
            return

        m_card_edit = re.match(r"^/api/planner/cards/(\d+)/edit$", path)
        if m_card_edit:
            self._intel_card_edit(int(m_card_edit.group(1)))
            return

        m_card_prod = re.match(r"^/api/planner/cards/(\d+)/production-status$", path)
        if m_card_prod:
            self._intel_card_production_status(int(m_card_prod.group(1)))
            return

        m_plan_approve = re.match(r"^/api/planner/plans/(\d+)/approve$", path)
        if m_plan_approve:
            self._intel_plan_approve(int(m_plan_approve.group(1)))
            return

        m_appr_ch = re.match(r"^/api/planner/plans/(\d+)/approve-changes$", path)
        if m_appr_ch:
            self._intel_plan_approve(int(m_appr_ch.group(1)))  # same gate: can_approve_plan
            return

        m_req_rev = re.match(r"^/api/planner/plans/(\d+)/request-revision$", path)
        if m_req_rev:
            self._intel_request_revision(int(m_req_rev.group(1)))
            return

        if path == "/api/wolf/chat":
            self._wolf_chat()
            return

        if path == "/api/assets/zip":
            self._assets_zip()
            return

        if path == "/api/upload/check-duplicate":
            self._upload_check_duplicate()
            return

        # Phase 2 — Metricool READ sync (gated)
        if path == "/api/admin/sync-metricool":
            self._admin_sync_metricool()
            return

        # Wolf Core Work Items
        if path == "/api/core/work-items":
            self._post_core_work_item()
            return

        # Uma Blu daily close mutations (server computes totals/variance/state)
        if path == "/api/venue-close/open":
            self._venue_close_open()
            return
        if path == "/api/venue-close/capture":
            self._venue_close_capture()
            return
        if path == "/api/venue-close/declare-cash":
            self._venue_close_declare_cash()
            return
        if path == "/api/venue-close/reconcile":
            self._venue_close_reconcile()
            return
        if path == "/api/venue-close/exception":
            self._venue_close_exception()
            return
        if path == "/api/venue-close/resolve":
            self._venue_close_resolve()
            return
        if path == "/api/venue-close/verify":
            self._venue_close_verify()
            return

        m_wi_assign = re.match(r"^/api/core/work-items/([^/]+)/assign$", path)
        if m_wi_assign:
            self._post_core_work_item_assign(m_wi_assign.group(1))
            return
        m_wi_start = re.match(r"^/api/core/work-items/([^/]+)/start$", path)
        if m_wi_start:
            self._post_core_work_item_start(m_wi_start.group(1))
            return
        m_wi_block = re.match(r"^/api/core/work-items/([^/]+)/block$", path)
        if m_wi_block:
            self._post_core_work_item_block(m_wi_block.group(1))
            return
        m_wi_complete = re.match(r"^/api/core/work-items/([^/]+)/complete$", path)
        if m_wi_complete:
            self._post_core_work_item_complete(m_wi_complete.group(1))
            return
        m_wi_verify = re.match(r"^/api/core/work-items/([^/]+)/verify$", path)
        if m_wi_verify:
            self._post_core_work_item_verify(m_wi_verify.group(1))
            return
        m_wi_cancel = re.match(r"^/api/core/work-items/([^/]+)/cancel$", path)
        if m_wi_cancel:
            self._post_core_work_item_cancel(m_wi_cancel.group(1))
            return

        # Wolf Core Approval Engine
        if path == "/api/core/approvals":
            self._post_core_approval()
            return
        m_apr_approve = re.match(r"^/api/core/approvals/([^/]+)/approve$", path)
        if m_apr_approve:
            self._post_core_approval_approve(m_apr_approve.group(1))
            return
        m_apr_reject = re.match(r"^/api/core/approvals/([^/]+)/reject$", path)
        if m_apr_reject:
            self._post_core_approval_reject(m_apr_reject.group(1))
            return
        m_apr_cancel = re.match(r"^/api/core/approvals/([^/]+)/cancel$", path)
        if m_apr_cancel:
            self._post_core_approval_cancel(m_apr_cancel.group(1))
            return

        # Wolf Core Delegation
        if path == "/api/core/delegations":
            self._post_core_delegation()
            return
        m_dlg_revoke = re.match(r"^/api/core/delegations/([^/]+)/revoke$", path)
        if m_dlg_revoke:
            self._post_core_delegation_revoke(m_dlg_revoke.group(1))
            return

        # Lead Spine operator mutations (Beta fixtures)
        m_lead_act = re.match(
            r"^/api/leads/([^/]+)/(touch|note|stage|assign|unassign|work-item|claim)$",
            path,
        )
        if m_lead_act:
            self._post_lead_action(m_lead_act.group(1), m_lead_act.group(2))
            return

        self._send_err(404, "not found")

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        m_wi = re.match(r"^/api/core/work-items/([^/]+)$", path)
        if m_wi:
            self._patch_core_work_item(m_wi.group(1))
            return
        self._send_err(404, "not found")

    def _llm_generate(self) -> None:
        """POST /api/llm/generate — Multi-LLM dispatch (isolated; never 8787).

        Phase 2.5A prepare: gated by can_use_wolf_intelligence.
        """
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._require_permission("can_use_wolf_intelligence", body) is None:
            return
        brand = (body.get("brand") or "").strip()
        role = (body.get("role") or "").strip()
        prompt = body.get("prompt")
        if isinstance(prompt, str):
            prompt = prompt.strip() or None
        else:
            prompt = None
        if not brand:
            self._send_json({"ok": False, "error": "brand required"}, status=400)
            return
        if not role:
            self._send_json({"ok": False, "error": "role required"}, status=400)
            return
        dry_flag = body.get("dry_run")
        prev_dry = os.environ.get("BETA_LLM_DRY_RUN")
        force_dry = dry_flag is True or str(dry_flag).strip().lower() in (
            "1", "true", "yes", "on",
        )
        if force_dry:
            os.environ["BETA_LLM_DRY_RUN"] = "1"
        try:
            _llm_orchestrator.load_env()
            _llm_orchestrator.ensure_llm_logs_table()
            result = _llm_orchestrator.dispatch_task(role, prompt, brand)
            # Structured result always; HTTP 200 even on provider errors (ok=False)
            self._send_json(result, status=200)
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "role": role,
                    "brand": brand,
                    "provider": None,
                    "model": None,
                    "text": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "error": str(exc),
                },
                status=200,
            )
        finally:
            if force_dry:
                if prev_dry is None:
                    os.environ.pop("BETA_LLM_DRY_RUN", None)
                else:
                    os.environ["BETA_LLM_DRY_RUN"] = prev_dry

    def _upload_preview_names(self) -> None:
        """POST JSON → preview Wolf canonical names for a batch (no write)."""
        if self._require_permission("can_upload", {}) is None:
            return
        try:
            body = self._read_json()
            result = _smart_upload.preview_batch(sys.modules[__name__], body)
            self._send_json(result["body"], status=int(result["http"]))
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _upload_smart(self) -> None:
        """POST multipart smart upload — Wolf naming + library ingest.

        Phase 2.5B: gated by can_upload. Never overwrites. Stores original_filename.
        Response omits filesystem paths. NAS status is honest (nas_received always false).
        """
        subject = self._require_permission("can_upload", {})
        if subject is None:
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD_BYTES:
                self._send_json(
                    {"ok": False, "status": "error", "error": f"upload exceeds {MAX_UPLOAD_BYTES} byte limit", "ui_status": "FAILED"},
                    status=413,
                )
                return
            fields = parse_multipart(self.headers, self.rfile)
            result = _smart_upload.handle_smart_upload(
                fields, subject=subject, serve_mod=sys.modules[__name__]
            )
            self._send_json(result["body"], status=int(result["http"]))
        except UploadTooLarge as exc:
            self._send_json({"ok": False, "status": "error", "error": str(exc), "ui_status": "FAILED"}, status=413)
        except UnsupportedMedia as exc:
            self._send_json({"ok": False, "status": "error", "error": str(exc), "ui_status": "FAILED"}, status=415)
        except ValueError as exc:
            self._send_json({"ok": False, "status": "error", "error": str(exc), "ui_status": "FAILED"}, status=400)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "status": "error", "error": str(exc), "ui_status": "FAILED"}, status=500)

    def _upload_remote(self) -> None:
        """POST multipart → incoming_drop + staged_assets (STAGED). No library_v2.

        Phase 2.5A: gated by can_upload. Subject via X-Wolf-Subject (DEVELOPMENT ONLY).
        """
        # Multipart: subject from header only (no JSON body)
        if self._require_permission("can_upload", {}) is None:
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD_BYTES:
                self._send_json(
                    {"status": "error", "error": f"upload exceeds {MAX_UPLOAD_BYTES} byte limit"},
                    status=413,
                )
                return
            fields = parse_multipart(self.headers, self.rfile)
            result = handle_remote_upload(fields)
            self._send_json(result["body"], status=int(result["http"]))
        except UploadTooLarge as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=413)
        except UnsupportedMedia as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=415)
        except ValueError as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    def _staging_commit(self) -> None:
        """Verify/reject staged assets. verify moves into library_v2 + assets."""
        try:
            body = self._read_json()
            items = body.get("items")
            if not isinstance(items, list) or not items:
                self._send_err(400, "items array required")
                return
            results = []
            for item in items:
                if not isinstance(item, dict):
                    results.append({"ok": False, "error": "item must be object", "http": 400})
                    continue
                try:
                    results.append(commit_staged_item(item))
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        {
                            "ok": False,
                            "id": item.get("id"),
                            "error": str(exc),
                            "http": 500,
                        }
                    )
            ok_count = sum(1 for r in results if r.get("ok"))
            self._send_json(
                {
                    "ok": ok_count == len(results),
                    "results": results,
                    "committed": ok_count,
                    "total": len(results),
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def do_PUT(self) -> None:
        # Legacy whole-plan PUT no longer supported as bulk replace;
        # accept single-slot body via save semantics for compat.
        if urlparse(self.path).path == "/api/planner":
            self._save_slot()
            return
        self._send_err(404, "not found")

    def _get_planner(self, qs: dict) -> None:
        brand = (qs.get("brand") or ["habitat"])[0].strip() or "habitat"
        week = (qs.get("week") or [""])[0].strip()
        try:
            if week:
                week_monday = date.fromisoformat(week[:10])
                week_monday = monday_of(week_monday)  # normalize to Monday
            else:
                week_monday = monday_of()
            slots = fetch_week(brand, week_monday)
            self._send_json(
                {
                    "ok": True,
                    "plan": {
                        "brand": brand,
                        "week_start": week_monday.isoformat(),
                        "slots": slots,
                    },
                    "items": slots,
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _publish_gate(self, qs: dict) -> None:
        raw_id = (qs.get("id") or [""])[0].strip()
        if not raw_id:
            self._send_err(400, "id required")
            return
        try:
            slot_id = int(raw_id)
        except ValueError:
            self._send_err(400, "id must be integer")
            return
        try:
            identity = self._resolve_identity(emit_audit=False)
            person_id = identity.get("person_id")
        except Exception:  # noqa: BLE001
            person_id = None
        gate = _content_publish.assert_habitat_publish_allowed(
            slot_id, verified_person_id=person_id
        )
        self._send_json(
            {
                "ok": True,
                "allowed": bool(gate.get("ok")),
                "id": slot_id,
                "stage": gate.get("stage"),
                "reason": gate.get("reason"),
                "metricool": gate.get("metricool"),
                "real_external_publish": gate.get("real_external_publish"),
                "status": (get_slot(slot_id) or {}).get("status"),
                "core_status": gate.get("core_status"),
                "note": "Core Approval canonical; Metricool write stays disabled unless already enabled",
            }
        )

    def _save_slot(self) -> None:
        """Create or update one planner slot. Human_Approved forbidden via save."""
        try:
            body = self._read_json()
            # Accept nested {slot: {...}} or flat, or legacy {plan:{slots:[...]}}
            # Prefer single slot; if plan.slots present, process last/only changes
            # as individual upserts for UI batch-compat.
            if isinstance(body.get("slot"), dict):
                items = [body["slot"]]
            elif isinstance(body.get("plan"), dict) and isinstance(
                body["plan"].get("slots"), list
            ):
                items = list(body["plan"]["slots"])
                brand_default = str(body["plan"].get("brand") or body.get("brand") or "").strip()
                week_default = str(
                    body["plan"].get("week_start") or body.get("week") or ""
                ).strip()
                for it in items:
                    if brand_default and not it.get("brand"):
                        it["brand"] = brand_default
                    if week_default and it.get("day") is not None and not it.get("scheduled_date"):
                        it["_week_start"] = week_default
            elif "slots" in body and isinstance(body["slots"], list):
                items = list(body["slots"])
                brand_default = str(body.get("brand") or "").strip()
                week_default = str(body.get("week_start") or body.get("week") or "").strip()
                for it in items:
                    if brand_default and not it.get("brand"):
                        it["brand"] = brand_default
                    if week_default and it.get("day") is not None and not it.get("scheduled_date"):
                        it["_week_start"] = week_default
            else:
                items = [body]

            results = []
            for item in items:
                saved = self._upsert_one(item)
                if saved is None:
                    return  # error already sent
                results.append(saved)

            # Return plan-shaped response for UI
            brand = results[-1].get("brand") if results else "habitat"
            week_start = results[-1].get("scheduled_date", monday_of().isoformat())[:10]
            try:
                wm = monday_of(date.fromisoformat(week_start))
            except ValueError:
                wm = monday_of()
            slots = fetch_week(brand or "habitat", wm)
            self._send_json(
                {
                    "ok": True,
                    "slot": results[0] if len(results) == 1 else None,
                    "slots": results,
                    "plan": {
                        "brand": brand or "habitat",
                        "week_start": wm.isoformat(),
                        "slots": slots,
                    },
                }
            )
        except PermissionError as exc:
            self._send_err(403, str(exc))
        except ValueError as exc:
            self._send_err(400, str(exc))
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _upsert_one(self, item: dict) -> dict | None:
        if not isinstance(item, dict):
            self._send_err(400, "JSON object required")
            return None

        brand = str(item.get("brand") or "").strip()
        if not brand:
            self._send_err(400, "brand required")
            return None

        # Status gate: save may set Draft / AI_Generated only
        raw_status = item.get("status")
        demoted = False
        if raw_status is None or str(raw_status).strip() == "":
            requested = None  # preserve on update; Draft on create
        else:
            raw_s = str(raw_status).strip()
            if raw_s in (
                "Human Approved",
                "Human_Approved",
                "Ready for Render",
                "Ready_for_Render",
            ):
                self._send_err(
                    403,
                    "cannot set Human_Approved or Ready_for_Render via save; "
                    "use /api/planner/approve or /api/planner/ready-render",
                )
                return None
            requested = canon_status(raw_s)
            if requested in (STATUS_APPROVED, STATUS_READY_RENDER):
                self._send_err(
                    403,
                    "cannot set Human_Approved or Ready_for_Render via save; "
                    "use /api/planner/approve or /api/planner/ready-render",
                )
                return None
            if requested not in STATUSES_SAVE:
                requested = "Draft"

        platform = canon_platform(item.get("platform") or item.get("platform_canon"))

        # scheduled_date from explicit field or week + day
        scheduled = str(item.get("scheduled_date") or "").strip()
        if not scheduled:
            week_raw = str(
                item.get("_week_start")
                or item.get("week_start")
                or item.get("week")
                or ""
            ).strip()
            if week_raw and item.get("day") is not None:
                try:
                    wm = monday_of(date.fromisoformat(week_raw[:10]))
                    scheduled = (wm + timedelta(days=int(item["day"]))).isoformat()
                except (ValueError, TypeError):
                    scheduled = monday_of().isoformat()
            else:
                scheduled = monday_of().isoformat()
        else:
            scheduled = scheduled[:10]

        title_slug = str(
            item.get("title_slug") or item.get("title") or ""
        ).strip()
        script_body = str(item.get("script_body") or "").strip()
        slot_time = str(item.get("slot_time") or "").strip()
        raw_asset = item.get("raw_asset_id", item.get("asset_id"))
        if raw_asset is not None and raw_asset != "":
            try:
                raw_asset = int(raw_asset)
            except (TypeError, ValueError):
                raw_asset = None
        else:
            raw_asset = None

        now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        slot_id = item.get("id")
        conn = db_connect()
        try:
            if slot_id is not None and str(slot_id).strip() != "":
                try:
                    slot_id = int(slot_id)
                except (TypeError, ValueError):
                    # Non-integer legacy UUID — treat as create
                    slot_id = None

            if slot_id is not None:
                existing = conn.execute(
                    "SELECT id, status FROM content_planner WHERE id = ?",
                    (slot_id,),
                ).fetchone()
                if existing:
                    cur_status = existing["status"]
                    cur_canon = canon_status(cur_status)
                    if requested is None:
                        status_to_write = cur_status if cur_status else "Draft"
                    elif cur_canon in (STATUS_APPROVED, STATUS_READY_RENDER) and requested in STATUSES_SAVE:
                        status_to_write = requested  # explicit demotion
                    else:
                        status_to_write = requested
                    conn.execute(
                        """
                        UPDATE content_planner SET
                          brand = ?, platform = ?, scheduled_date = ?,
                          slot_time = ?, title_slug = ?, script_body = ?,
                          raw_asset_id = ?, status = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            brand,
                            platform,
                            scheduled,
                            slot_time,
                            title_slug,
                            script_body,
                            raw_asset,
                            status_to_write,
                            now,
                            slot_id,
                        ),
                    )
                    conn.commit()
                    new_id = slot_id
                else:
                    insert_status = requested if requested in STATUSES_SAVE else "Draft"
                    cur = conn.execute(
                        """
                        INSERT INTO content_planner
                          (brand, platform, scheduled_date, slot_time, title_slug,
                           script_body, raw_asset_id, status, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            brand,
                            platform,
                            scheduled,
                            slot_time,
                            title_slug,
                            script_body,
                            raw_asset,
                            insert_status,
                            now,
                        ),
                    )
                    conn.commit()
                    new_id = cur.lastrowid
            else:
                insert_status = requested if requested in STATUSES_SAVE else "Draft"
                cur = conn.execute(
                    """
                    INSERT INTO content_planner
                      (brand, platform, scheduled_date, slot_time, title_slug,
                       script_body, raw_asset_id, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        brand,
                        platform,
                        scheduled,
                        slot_time,
                        title_slug,
                        script_body,
                        raw_asset,
                        insert_status,
                        now,
                    ),
                )
                conn.commit()
                new_id = cur.lastrowid

            row = conn.execute(
                """
                SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                       script_body, raw_asset_id, status, updated_at
                FROM content_planner WHERE id = ?
                """,
                (new_id,),
            ).fetchone()
            wm = monday_of(date.fromisoformat(scheduled))
            out = row_to_slot(row, wm)
            if demoted:
                out["demoted_from_human_approved"] = True
            # Integration #5: Content Machine mutation AFTER successful commit
            try:
                identity = self._resolve_identity(emit_audit=False)
                if identity.get("ok") and identity.get("person_id"):
                    _audit.safe_record(
                        action="content_planner.save",
                        result="SUCCEEDED",
                        source="content_planner",
                        actor_type="PERSON",
                        verified_person_id=identity["person_id"],
                        actor_person_id=identity["person_id"],
                        actor_auth_identity_id=identity.get("auth_identity_id"),
                        identity_assurance=identity.get("identity_assurance"),
                        brand_id=brand,
                        resource_type="content_planner_slot",
                        resource_id=str(new_id),
                        correlation_id=getattr(self, "_wolf_correlation_id", None)
                        or _audit.mint_correlation_id(),
                        metadata={
                            "brand": brand,
                            "slot_id": new_id,
                            "status": out.get("status"),
                        },
                    )
            except Exception:  # noqa: BLE001
                pass
            return out
        finally:
            conn.close()

    def _submit_for_approval(self) -> None:
        """POST /api/planner/submit-for-approval {id} — Habitat Core evidence + APR create."""
        try:
            body = self._read_json()
            # Reject client spoof of identity fields
            for spoof in ("verified_person_id", "person_id", "requested_by_person_id"):
                if spoof in body and body.get(spoof) not in (None, ""):
                    # Still allow identity resolution headers; body claims ignored below
                    pass
            identity = self._resolve_identity(body if isinstance(body, dict) else {})
            person_id = identity.get("person_id")
            if not person_id:
                self._send_err(401, "verified identity required")
                return
            # Body person spoof refused
            claim = (body.get("verified_person_id") or body.get("person_id") or "").strip()
            if claim and claim != person_id:
                self._send_err(400, "person_id spoof refused")
                return

            raw_id = body.get("id")
            if raw_id is None or str(raw_id).strip() == "":
                self._send_err(400, "id required")
                return
            try:
                slot_id = int(raw_id)
            except (TypeError, ValueError):
                self._send_err(400, "id must be integer")
                return

            row = get_slot(slot_id)
            if row is None:
                self._send_err(404, "slot not found")
                return
            if (row.get("brand") or "").strip().lower() != "habitat":
                self._send_err(400, "submit-for-approval is Habitat pilot only")
                return

            result = _content_publish.submit_for_approval(
                slot_id,
                verified_person_id=person_id,
                identity=identity,
            )
            self._send_json(result)
        except _content_publish.ContentPublishError as exc:
            self._send_err(exc.http_status, str(exc))
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _approve_slot(self) -> None:
        """HARD GATE: {id, approve:true}. Habitat → Core only; derive Human_Approved."""
        try:
            body = self._read_json()
            if body.get("approve") is not True:
                self._send_err(400, "approve:true required")
                return

            raw_id = body.get("id")
            if raw_id is None or str(raw_id).strip() == "":
                self._send_err(400, "id required")
                return
            try:
                slot_id = int(raw_id)
            except (TypeError, ValueError):
                self._send_err(400, "id must be integer")
                return

            # Peek brand first
            peek = get_slot(slot_id)
            if peek is None:
                self._send_err(404, "slot not found")
                return

            if (peek.get("brand") or "").strip().lower() == "habitat":
                identity = self._resolve_identity(body if isinstance(body, dict) else {})
                person_id = identity.get("person_id")
                if not person_id:
                    self._send_err(401, "verified identity required")
                    return
                claim = (body.get("verified_person_id") or body.get("person_id") or "").strip()
                if claim and claim != person_id:
                    self._send_err(400, "person_id spoof refused")
                    return
                # Reject client status spoof — Human_Approved only derived from Core
                if body.get("status") in (STATUS_APPROVED, "Human_Approved", "APPROVED"):
                    self._send_err(400, "status spoof refused; Core decide only")
                    return
                try:
                    core_out = _content_publish.apply_core_approval_to_slot(
                        slot_id,
                        verified_person_id=person_id,
                        reason=(body.get("reason") or None),
                        identity=identity,
                    )
                except _content_publish.ContentPublishError as exc:
                    self._send_err(exc.http_status, str(exc))
                    return
                row = get_slot(slot_id)
                assert row is not None
                sched = row["scheduled_date"] or monday_of().isoformat()
                wm = monday_of(date.fromisoformat(str(sched)[:10]))
                slot = row_to_slot(row, wm)
                slots = fetch_week(row["brand"], wm)
                self._send_json(
                    {
                        "ok": True,
                        "slot": slot,
                        "core": core_out,
                        "derived_from_core": True,
                        "plan": {
                            "brand": row["brand"],
                            "week_start": wm.isoformat(),
                            "slots": slots,
                        },
                    }
                )
                return

            # Non-Habitat: legacy path (not publish-gated by Habitat Core)
            conn = db_connect()
            try:
                row = conn.execute(
                    """
                    SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                           script_body, raw_asset_id, status, updated_at
                    FROM content_planner WHERE id = ?
                    """,
                    (slot_id,),
                ).fetchone()
                if row is None:
                    self._send_err(404, "slot not found")
                    return
                current = row["status"]
                ok_from = (
                    current in STATUSES_APPROVE_FROM
                    or canon_status(current) == "AI_Generated"
                )
                if not ok_from:
                    self._send_err(
                        409,
                        f"cannot approve: status is {current!r}, must be AI_Generated "
                        f"(or legacy Render_Ready)",
                    )
                    return
                now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE content_planner SET status = ?, updated_at = ? WHERE id = ?",
                    (STATUS_APPROVED, now, slot_id),
                )
                conn.commit()
                row = conn.execute(
                    """
                    SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                           script_body, raw_asset_id, status, updated_at
                    FROM content_planner WHERE id = ?
                    """,
                    (slot_id,),
                ).fetchone()
            finally:
                conn.close()

            sched = row["scheduled_date"] or monday_of().isoformat()
            wm = monday_of(date.fromisoformat(str(sched)[:10]))
            slot = row_to_slot(row, wm)
            slots = fetch_week(row["brand"], wm)
            self._send_json(
                {
                    "ok": True,
                    "slot": slot,
                    "plan": {
                        "brand": row["brand"],
                        "week_start": wm.isoformat(),
                        "slots": slots,
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _ready_render_slot(self) -> None:
        """POST /api/planner/ready-render {id} — Human_Approved → Ready_for_Render."""
        try:
            body = self._read_json()
            raw_id = body.get("id")
            if raw_id is None or str(raw_id).strip() == "":
                self._send_err(400, "id required")
                return
            try:
                slot_id = int(raw_id)
            except (TypeError, ValueError):
                self._send_err(400, "id must be integer")
                return

            conn = db_connect()
            try:
                row = conn.execute(
                    """
                    SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                           script_body, raw_asset_id, status, updated_at
                    FROM content_planner WHERE id = ?
                    """,
                    (slot_id,),
                ).fetchone()
                if row is None:
                    self._send_err(404, "slot not found")
                    return
                current = row["status"]
                if current != STATUS_APPROVED and canon_status(current) != STATUS_APPROVED:
                    self._send_err(
                        409,
                        f"cannot ready-render: status is {current!r}, must be Human_Approved",
                    )
                    return
                now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE content_planner SET status = ?, updated_at = ? WHERE id = ?",
                    (STATUS_READY_RENDER, now, slot_id),
                )
                conn.commit()
                row = conn.execute(
                    """
                    SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                           script_body, raw_asset_id, status, updated_at
                    FROM content_planner WHERE id = ?
                    """,
                    (slot_id,),
                ).fetchone()
            finally:
                conn.close()

            sched = row["scheduled_date"] or monday_of().isoformat()
            wm = monday_of(date.fromisoformat(str(sched)[:10]))
            slot = row_to_slot(row, wm)
            slots = fetch_week(row["brand"], wm)
            self._send_json(
                {
                    "ok": True,
                    "slot": slot,
                    "plan": {
                        "brand": row["brand"],
                        "week_start": wm.isoformat(),
                        "slots": slots,
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _render_slot(self) -> None:
        """POST /api/planner/render {id} — stub; 403 unless Human_Approved or Ready_for_Render."""
        try:
            body = self._read_json()
            raw_id = body.get("id")
            if raw_id is None or str(raw_id).strip() == "":
                self._send_err(400, "id required")
                return
            try:
                slot_id = int(raw_id)
            except (TypeError, ValueError):
                self._send_err(400, "id must be integer")
                return
            row = get_slot(slot_id)
            if row is None:
                self._send_err(404, "slot not found")
                return
            current = row.get("status")
            canon = canon_status(current)
            if canon not in STATUSES_RENDER_OK and current not in STATUSES_RENDER_OK:
                self._send_err(
                    403,
                    f"render denied: status is {current!r}; must be Human_Approved "
                    f"(or Ready_for_Render)",
                )
                return
            self._send_json(
                {
                    "ok": True,
                    "stub": True,
                    "id": slot_id,
                    "status": canon,
                    "message": "render stub accepted (no video pipeline in this build)",
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _attach_asset(self) -> None:
        """POST /api/planner/attach-asset {id, raw_asset_id} → content_planner.raw_asset_id."""
        try:
            body = self._read_json()
            raw_id = body.get("id")
            raw_asset_id = body.get("raw_asset_id")
            if raw_id is None or str(raw_id).strip() == "":
                self._send_err(400, "id required")
                return
            if raw_asset_id is None or str(raw_asset_id).strip() == "":
                self._send_err(400, "raw_asset_id required")
                return
            try:
                slot_id = int(raw_id)
                asset_id = int(raw_asset_id)
            except (TypeError, ValueError):
                self._send_err(400, "id and raw_asset_id must be integers")
                return

            conn = db_connect()
            try:
                slot = conn.execute(
                    "SELECT id, brand, scheduled_date FROM content_planner WHERE id = ?",
                    (slot_id,),
                ).fetchone()
                if slot is None:
                    self._send_err(404, "slot not found")
                    return
                asset = conn.execute(
                    "SELECT id, brand, stage FROM assets WHERE id = ?",
                    (asset_id,),
                ).fetchone()
                if asset is None:
                    self._send_err(404, "asset not found")
                    return
                now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE content_planner SET raw_asset_id = ?, updated_at = ? WHERE id = ?",
                    (asset_id, now, slot_id),
                )
                conn.commit()
                row = conn.execute(
                    """
                    SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
                           script_body, raw_asset_id, status, updated_at
                    FROM content_planner WHERE id = ?
                    """,
                    (slot_id,),
                ).fetchone()
            finally:
                conn.close()

            sched = row["scheduled_date"] or monday_of().isoformat()
            wm = monday_of(date.fromisoformat(str(sched)[:10]))
            slot_out = row_to_slot(row, wm)
            slots = fetch_week(row["brand"], wm)
            self._send_json(
                {
                    "ok": True,
                    "slot": slot_out,
                    "plan": {
                        "brand": row["brand"],
                        "week_start": wm.isoformat(),
                        "slots": slots,
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))




    # ----- Phase 1 Wolf Intelligence -----

    def _request_headers_dict(self) -> dict:
        return {k: v for k, v in self.headers.items()}

    def _resolve_identity(self, body: dict | None = None, *, emit_audit: bool = True) -> dict:
        """Single identity entry — Cloudflare JWT or explicit development assertion."""
        cached = getattr(self, "_wolf_body_cache", None)
        use_body = body if body is not None else (cached if isinstance(cached, dict) else {})
        return _request_auth.resolve_request_identity(
            self,
            body=use_body if isinstance(use_body, dict) else {},
            emit_audit=emit_audit,
        )

    def _send_identity_deny(self, identity: dict, *, required_permission: str | None = None) -> None:
        payload = {
            "ok": False,
            "error": identity.get("error") or "unauthorized",
            "message": identity.get("message") or "Identity denied.",
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "auth_mode": identity.get("auth_mode") or _request_auth.auth_mode(),
        }
        if required_permission:
            payload["required_permission"] = required_permission
        if identity.get("email"):
            payload["email"] = identity.get("email")
        self._send_json(payload, status=403)

    def _require_permission(
        self,
        permission: str,
        body: dict | None = None,
        *,
        target: dict | None = None,
    ) -> str | None:
        """Return permission subject email if identity + permission ok; else 403 / None.

        Identity from core.request_auth (Cloudflare JWT fail-closed by default).
        Client subject channels ignored in cloudflare_access mode.
        """
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission=permission)
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if not subject:
            self._send_identity_deny(
                {
                    "error": "missing_subject",
                    "message": "Resolved identity has no email subject.",
                    "identity_assurance": identity.get("identity_assurance"),
                    "real_authentication": identity.get("real_authentication"),
                },
                required_permission=permission,
            )
            return None
        if target is not None:
            person_id_for_target = identity.get("person_id")
            allowed = bool(person_id_for_target) and _rbac.can(
                person_id_for_target, permission, target
            )
        else:
            allowed = _wi.has_permission(subject, permission)
        if not allowed:
            # Integration #3: RBAC denial on a representative protected action
            person_id = identity.get("person_id")
            if person_id:
                _audit.safe_record(
                    action="rbac.evaluate",
                    result="DENIED",
                    source="rbac",
                    actor_type="PERSON",
                    verified_person_id=person_id,
                    actor_person_id=person_id,
                    actor_auth_identity_id=identity.get("auth_identity_id"),
                    identity_assurance=identity.get("identity_assurance"),
                    correlation_id=getattr(self, "_wolf_correlation_id", None)
                    or _audit.mint_correlation_id(),
                    reason_code="forbidden",
                    metadata={
                        "permission": permission,
                        "required_permission": permission,
                        "error": "forbidden",
                    },
                )
            else:
                _audit.safe_record(
                    action="rbac.evaluate",
                    result="DENIED",
                    source="rbac",
                    actor_type="SYSTEM",
                    identity_assurance=identity.get("identity_assurance")
                    or _identity.IDENTITY_ASSURANCE_NONE,
                    correlation_id=getattr(self, "_wolf_correlation_id", None)
                    or _audit.mint_correlation_id(),
                    reason_code="forbidden",
                    metadata={
                        "permission": permission,
                        "required_permission": permission,
                        "error": "forbidden",
                    },
                )
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": f"subject lacks {permission}: {subject}",
                    "subject": subject,
                    "required_permission": permission,
                    "identity_assurance": identity.get("identity_assurance"),
                    "real_authentication": identity.get("real_authentication"),
                    "person_id": identity.get("person_id"),
                },
                status=403,
            )
            return None
        return subject

    def _require_can_create_plan(self, body: dict | None = None) -> str | None:
        """Compatibility wrapper — build-next / admin sync still use can_create_plan."""
        return self._require_permission("can_create_plan", body)

    # ----- Matt Progress Dashboard (Owner / PERS-MATT only) -----

    def _require_progress_owner(self, body: dict | None = None) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Staff seats → 403."""
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Progress Dashboard is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **_progress.honesty_flags(),
                },
                status=403,
            )
            return None
        # RBAC belt: progress.read on ROLE-MATT (migration 022)
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **_progress.honesty_flags(),
                },
                status=403,
            )
            return None
        return identity

    def _progress_honesty(self) -> None:
        identity = self._require_progress_owner()
        if identity is None:
            return
        self._send_json({"ok": True, "person_id": identity.get("person_id"), **_progress.honesty_flags()})

    def _progress_calculation(self) -> None:
        identity = self._require_progress_owner()
        if identity is None:
            return
        self._send_json(
            {
                "ok": True,
                "person_id": identity.get("person_id"),
                **_progress.calculation_english(),
                **_progress.honesty_flags(),
            }
        )

    def _progress_empire(self) -> None:
        identity = self._require_progress_owner()
        if identity is None:
            return
        try:
            model = _progress.build_read_model()
            model["person_id"] = identity.get("person_id")
            self._send_json(model)
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _progress_view(self, qs: dict) -> None:
        identity = self._require_progress_owner()
        if identity is None:
            return
        name = (qs.get("name") or qs.get("view") or ["Empire"])[0]
        try:
            out = _progress.get_view(str(name or "Empire"))
            if not out.get("ok"):
                self._send_json(out, status=404)
                return
            out["person_id"] = identity.get("person_id")
            self._send_json(out)
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _intel_orchestrate(self, qs: dict) -> None:
        """GET /api/intel/orchestrate — read-only. Does not claim Cloudflare JWT as evidence."""
        identity = self._require_progress_owner()
        if identity is None:
            return
        question = (qs.get("question") or [_intel.DEMO_QUESTION])[0]
        scope = (qs.get("scope") or [_intel.DEMO_SCOPE])[0]
        kind = (qs.get("kind") or [""])[0].strip()
        work_item_id = (qs.get("work_item_id") or [""])[0].strip() or None
        actor: dict = {
            "person_id": identity.get("person_id"),
            "permission_context": {"person_id": identity.get("person_id")},
        }
        if kind:
            actor["kind"] = kind
        try:
            out = _intel.orchestrate_institutional_question(
                question,
                scope,
                actor_context=actor,
                work_item_id=work_item_id,
            )
        except _intel.IntelOrchestrationError as exc:
            status = 404 if exc.code == "work_item_missing" else 400
            self._send_json(
                {"ok": False, "error": exc.code, "message": str(exc)},
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json(
            {
                "ok": True,
                "person_id": identity.get("person_id"),
                **out,
            }
        )

    # ----- Uma Blu ops (Devi commissioning: fail-closed) -----

    def _require_uma_ops(self, body: dict | None = None) -> str | None:
        """Identity + venue.close.read on Uma + active SCOPE-BZG-UMA. Fail closed.

        Does not grant payment approve, closer submit, float invent, or Progress.
        Keeps ROLE-BZG-HFB. Does not invent bzg.pr.payment_approve.
        """
        permission = "venue.close.read"
        subject = self._require_permission(
            permission,
            body,
            target={"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"},
        )
        if subject is None:
            return None
        identity = self._resolve_identity(body, emit_audit=False)
        person_id = identity.get("person_id")
        scopes = _scope.list_active_scopes_for_person(person_id) if person_id else []
        if not any(row.get("scope_id") == "SCOPE-BZG-UMA" for row in scopes):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks SCOPE-BZG-UMA",
                    "subject": subject,
                    "person_id": person_id,
                    "required_permission": permission,
                    "required_scope": "SCOPE-BZG-UMA",
                    "identity_assurance": identity.get("identity_assurance"),
                    "real_authentication": identity.get("real_authentication"),
                },
                status=403,
            )
            return None
        return subject

    # ----- Uma Blu daily close -----

    def _uma_ops_honesty(self) -> None:
        self._send_json({"ok": True, **_uma_ops.honesty_flags()})

    def _uma_ops_today(self) -> None:
        try:
            identity = self._resolve_identity(emit_audit=False)
            person_id = identity.get("person_id") if identity.get("ok") else None
            self._send_json(_uma_ops.today_cards(person_id=person_id))
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _uma_ops_pr_detail(self, key: str) -> None:
        try:
            from urllib.parse import unquote

            identity = self._resolve_identity(emit_audit=False)
            person_id = identity.get("person_id") if identity.get("ok") else None
            detail = _uma_p0.pr_detail(unquote(key))
            if not detail:
                self._send_json(
                    {"ok": False, "error": "not_found", "message": "Purchase request not found."},
                    status=404,
                )
                return
            actions = {}
            if person_id:
                conn = _uma_ops.db_connect()
                try:
                    actions = _uma_p0.pr_actions(person_id, conn=conn)
                finally:
                    conn.close()
            self._send_json(
                {
                    "ok": True,
                    "pr": detail,
                    "actions": actions,
                    "payment_approve": False,
                    **_uma_ops.honesty_flags(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _uma_ops_receive_post(self) -> None:
        """Append-only Wolf receipt. Fail closed without a venue receive permission."""
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        identity = self._resolve_identity(body, emit_audit=False)
        person_id = identity.get("person_id") if identity.get("ok") else None
        if not person_id:
            self._send_json(
                {"ok": False, "error": "forbidden", "message": "Identity required."},
                status=403,
            )
            return
        try:
            out = _uma_p0.receive_goods(
                person_id=person_id,
                pr_key=str(body.get("pr") or body.get("pr_key") or ""),
                lines=body.get("lines") or [],
                notes=body.get("notes"),
                corrects_receipt_id=body.get("corrects_receipt_id"),
                identity=identity,
            )
            self._send_json({"ok": True, "receipt": out, "payment_approve": False})
        except _uma_ops.UmaOpsError as exc:
            self._send_json(
                {"ok": False, "error": str(exc), "code": getattr(exc, "code", None)},
                status=int(getattr(exc, "http_status", 400) or 400),
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _uma_ops_prs(self) -> None:
        try:
            rows = _uma_ops.list_prs()
            payload = {
                "ok": True,
                "prs": rows,
                "count": len(rows),
                **_uma_ops.honesty_flags(),
            }
            payload["fixture_notice"] = _uma_ops.fixture_notice_for(rows)
            self._send_json(payload)
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _uma_ops_issues(self) -> None:
        try:
            self._send_json(_uma_ops.list_issues())
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _uma_ops_history(self) -> None:
        try:
            self._send_json(_uma_ops.list_history())
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _uma_ops_petty(self) -> None:
        try:
            self._send_json(_uma_ops.list_petty())
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _uma_ops_petty_post(self) -> None:
        """Test-mode-only fixture movement. No ESB/ClickUp/Telegram/bank writes."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(body, dict):
                body = {}
            out = _uma_ops.create_petty_movement_test_mode(
                business_date=body.get("business_date"),
                direction=body.get("direction") or "OUT",
                amount=body.get("amount") if body.get("amount") is not None else 1.0,
                currency=body.get("currency"),
                purpose=body.get("purpose"),
                example=bool(body.get("example", True)),
                opening_float=body.get("opening_float"),
            )
            self._send_json({"ok": True, "movement": out, **_uma_ops.honesty_flags()})
        except _uma_ops.UmaOpsError as exc:
            self._send_json(
                {"ok": False, "error": str(exc), "code": getattr(exc, "code", None)},
                status=int(getattr(exc, "http_status", 400) or 400),
            )
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _venue_close_person(self, body: dict | None = None) -> dict | None:
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="venue.close.*")
            return None
        pid = identity.get("person_id")
        if not pid:
            self._send_identity_deny(
                {
                    "error": "missing_person",
                    "message": "Resolved identity has no Person binding.",
                    "identity_assurance": identity.get("identity_assurance"),
                    "real_authentication": identity.get("real_authentication"),
                },
                required_permission="venue.close.*",
            )
            return None
        return identity

    def _venue_close_err(self, exc: Exception) -> None:
        if isinstance(exc, _venue_close.VenueCloseError):
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    **_venue_close.HONESTY,
                },
                status=exc.http_status,
            )
            return
        if isinstance(exc, _esb_close_snapshot.EsbSnapshotError):
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    **_esb_close_snapshot.HONESTY,
                },
                status=exc.http_status,
            )
            return
        self._send_err(500, str(exc))

    def _venue_close_honesty(self) -> None:
        try:
            self._send_json({"ok": True, **_venue_close.honesty_flags()})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_list(self, qs: dict) -> None:
        identity = self._venue_close_person()
        if identity is None:
            return
        try:
            state = (qs.get("state") or [None])[0]
            rows = _venue_close.list_closes(state=state)
            self._send_json(
                {
                    "ok": True,
                    "closes": rows,
                    "count": len(rows),
                    **_venue_close.honesty_flags(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_previous(self, qs: dict) -> None:
        identity = self._venue_close_person()
        if identity is None:
            return
        try:
            exclude = (qs.get("exclude_business_date") or qs.get("business_date") or [None])[0]
            self._send_json(_uma_p0.previous_closes(exclude_business_date=exclude))
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_capabilities(self) -> None:
        identity = self._venue_close_person()
        if identity is None:
            return
        try:
            self._send_json(_uma_p0.close_capabilities(identity["person_id"]))
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_get(self, close_id: str, qs: dict) -> None:
        identity = self._venue_close_person()
        if identity is None:
            return
        try:
            date = (qs.get("business_date") or [None])[0]
            if close_id == "by-date":
                row = _venue_close.get_close(business_date=date)
            else:
                row = _venue_close.get_close(close_id)
            if not row:
                self._send_json(
                    {"ok": False, "error": "not_found", "message": "close not found"},
                    status=404,
                )
                return
            detail = _uma_p0.close_detail(row["close_id"])
            self._send_json(
                {
                    "ok": True,
                    "close": row,
                    "detail": detail,
                    **_venue_close.HONESTY,
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_refuse_overrides(self, body: dict, keys: tuple[str, ...]) -> bool:
        for forbidden in keys:
            if forbidden in body:
                self._send_json(
                    {
                        "ok": False,
                        "error": "client_override_refused",
                        "message": f"client cannot submit {forbidden}",
                    },
                    status=400,
                )
                return True
        return False

    def _venue_close_open(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._venue_close_refuse_overrides(
            body, ("state", "variance_cash_amount", "esb_totals", "esb_totals_json", "expected_cash")
        ):
            return
        identity = self._venue_close_person(body)
        if identity is None:
            return
        try:
            out = _venue_close.open_or_get(
                str(body.get("business_date") or ""),
                verified_person_id=identity["person_id"],
                identity=identity,
            )
            self._send_json({"ok": True, "close": out})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_capture(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._venue_close_refuse_overrides(
            body, ("state", "esb_totals", "esb_fingerprint_sha256", "variance_cash_amount")
        ):
            return
        identity = self._venue_close_person(body)
        if identity is None:
            return
        try:
            out = _venue_close.capture_esb_snapshot(
                str(body.get("close_id") or ""),
                verified_person_id=identity["person_id"],
                identity=identity,
            )
            self._send_json({"ok": True, "close": out})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_declare_cash(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._venue_close_refuse_overrides(
            body, ("state", "variance_cash_amount", "esb_totals", "verified_cash")
        ):
            return
        identity = self._venue_close_person(body)
        if identity is None:
            return
        try:
            out = _venue_close.attach_declared_cash(
                str(body.get("close_id") or ""),
                declared_cash_amount=body.get("declared_cash_amount"),
                verified_person_id=identity["person_id"],
                object_ref=(body.get("object_ref") or None),
                notes=(body.get("notes") or None),
                identity=identity,
            )
            self._send_json({"ok": True, "close": out})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_reconcile(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._venue_close_refuse_overrides(
            body, ("state", "variance_cash_amount", "esb_totals")
        ):
            return
        identity = self._venue_close_person(body)
        if identity is None:
            return
        try:
            out = _venue_close.reconcile(
                str(body.get("close_id") or ""),
                verified_person_id=identity["person_id"],
                identity=identity,
            )
            self._send_json({"ok": True, "close": out})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_exception(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._venue_close_refuse_overrides(
            body, ("state", "variance_cash_amount", "esb_totals")
        ):
            return
        identity = self._venue_close_person(body)
        if identity is None:
            return
        try:
            out = _venue_close.open_exception(
                str(body.get("close_id") or ""),
                verified_person_id=identity["person_id"],
                identity=identity,
            )
            self._send_json({"ok": True, "close": out})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_resolve(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._venue_close_refuse_overrides(
            body, ("state", "variance_cash_amount", "esb_totals")
        ):
            return
        identity = self._venue_close_person(body)
        if identity is None:
            return
        try:
            out = _venue_close.resolve_exception(
                str(body.get("close_id") or ""),
                verified_person_id=identity["person_id"],
                resolution_notes=str(body.get("resolution_notes") or ""),
                object_ref=(body.get("object_ref") or None),
                identity=identity,
            )
            self._send_json({"ok": True, "close": out})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _venue_close_verify(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        if self._venue_close_refuse_overrides(
            body, ("state", "variance_cash_amount", "esb_totals", "verified_at")
        ):
            return
        identity = self._venue_close_person(body)
        if identity is None:
            return
        try:
            out = _venue_close.verify_close(
                str(body.get("close_id") or ""),
                verified_person_id=identity["person_id"],
                identity=identity,
            )
            self._send_json({"ok": True, "close": out})
        except Exception as exc:  # noqa: BLE001
            self._venue_close_err(exc)

    def _get_core_permissions(self) -> None:
        self._send_json({
            "ok": True,
            "permissions": _rbac.list_permissions(),
            "role_grants": _rbac.list_role_permission_grants(),
            "authority_limits": "NOT_BUILT",
            "access_control_live": False,
        })

    def _get_core_me_permissions(self) -> None:
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        person_id = identity.get("person_id")
        target = _rbac.default_content_target()
        codes = (
            _rbac.effective_permissions_for_person(person_id, target)
            if person_id else []
        )
        self._send_json({
            "ok": True,
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "asserted_identifier": identity.get("asserted_identifier"),
            "email": identity.get("email"),
            "permission_subject": identity.get("permission_subject"),
            "person_id": person_id,
            "target_context": target,
            "permissions": codes,
            "authority_limits": "SEE_core.authority",
            "access_control_live": False,
            "auth_mode": identity.get("auth_mode"),
            "note": identity.get("note"),
        })

    def _get_core_authority_check(self, qs: dict) -> None:
        """Read-only within_authority check. No write/admin."""
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        person_id = identity.get("person_id")
        permission_code = (qs.get("permission_code") or [""])[0].strip()
        target = {
            k: (qs.get(k) or [""])[0].strip() or None
            for k in ("entity_id", "brand_id", "location_id", "department_id")
        }
        target = {k: v for k, v in target.items() if v}
        if not target:
            target = _rbac.default_content_target()
        amount_raw = (qs.get("amount") or [None])[0]
        currency = (qs.get("currency") or [None])[0]
        at = (qs.get("at") or [None])[0]
        amount_context: dict = {}
        if amount_raw is not None and str(amount_raw).strip() != "":
            amount_context["amount"] = amount_raw
        if currency is not None and str(currency).strip() != "":
            amount_context["currency"] = str(currency).strip()
        if at is not None and str(at).strip() != "":
            amount_context["at"] = str(at).strip()
        if not person_id:
            self._send_json({
                "ok": False,
                "error": "no_person",
                "identity_assurance": identity.get("identity_assurance"),
                "real_authentication": identity.get("real_authentication"),
                "note": identity.get("note"),
            }, status=403)
            return
        if not permission_code:
            self._send_json({
                "ok": False,
                "error": "missing_permission_code",
            }, status=400)
            return
        decision = _authority.within_authority(
            person_id, permission_code, target, amount_context
        )
        # Integration #4: Authority denial (amount + no limit / out of threshold)
        if not decision.get("allowed"):
            _audit.safe_record(
                action="authority.check",
                result="DENIED",
                source="authority",
                actor_type="PERSON",
                verified_person_id=person_id,
                actor_person_id=person_id,
                actor_auth_identity_id=identity.get("auth_identity_id"),
                identity_assurance=identity.get("identity_assurance"),
                entity_id=target.get("entity_id"),
                brand_id=target.get("brand_id"),
                location_id=target.get("location_id"),
                department_id=target.get("department_id"),
                correlation_id=getattr(self, "_wolf_correlation_id", None)
                or _audit.mint_correlation_id(),
                reason_code=str(decision.get("reason") or "denied"),
                metadata={
                    "permission_code": permission_code,
                    "amount": amount_context.get("amount"),
                    "currency": amount_context.get("currency"),
                    "reason": decision.get("reason"),
                },
            )
        self._send_json({
            "ok": True,
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "asserted_identifier": identity.get("asserted_identifier"),
            "email": identity.get("email"),
            "decision": decision,
            "access_control_live": False,
        })

    def _get_core_audit(self, qs: dict) -> None:
        """GET /api/core/audit — Matt-only read of append-only evidence spine."""
        subject = self._require_permission("audit.event.read")
        if subject is None:
            return
        identity = self._resolve_identity(emit_audit=False)
        person_id = identity.get("person_id") if identity.get("ok") else None
        try:
            limit = int((qs.get("limit") or ["50"])[0])
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = int((qs.get("offset") or ["0"])[0])
        except (TypeError, ValueError):
            offset = 0
        events = _audit.list_events(
            entity_id=((qs.get("entity_id") or [None])[0] or None) or None,
            action=((qs.get("action") or [None])[0] or None) or None,
            result=((qs.get("result") or [None])[0] or None) or None,
            source=((qs.get("source") or [None])[0] or None) or None,
            correlation_id=((qs.get("correlation_id") or [None])[0] or None) or None,
            occurred_from=((qs.get("occurred_from") or [None])[0] or None) or None,
            occurred_to=((qs.get("occurred_to") or [None])[0] or None) or None,
            actor_person_id=((qs.get("actor_person_id") or [None])[0] or None) or None,
            limit=limit,
            offset=offset,
        )
        self._send_json(
            {
                "ok": True,
                "events": events,
                "limit": max(1, min(limit, 200)),
                "offset": max(0, offset),
                "count": len(events),
                "hash_chain": "NOT_BUILT",
                "immutability": "append_only_service_and_triggers",
                "person_id": person_id,
            }
        )

    def _work_identity(self, permission: str, body: dict | None = None) -> dict | None:
        """Permission gate + verified person_id for work-item mutations."""
        subject = self._require_permission(permission, body)
        if subject is None:
            return None
        identity = self._resolve_identity(body, emit_audit=False)
        if not identity.get("ok") or not identity.get("person_id"):
            self._send_json(
                {
                    "ok": False,
                    "error": "no_person",
                    "message": "Work items require a verified Person binding.",
                    "required_permission": permission,
                },
                status=403,
            )
            return None
        identity = dict(identity)
        identity["correlation_id"] = getattr(self, "_wolf_correlation_id", None) or _audit.mint_correlation_id()
        return identity

    def _lead_identity(self, body: dict | None = None) -> dict | None:
        """Verified Person for Lead Spine. Never trust person id from the browser body."""
        identity = self._resolve_identity(body, emit_audit=False)
        if not identity.get("ok"):
            self._send_json(
                {
                    "ok": False,
                    "error": identity.get("error") or "unauthorized",
                    "message": identity.get("message")
                    or "You must be signed in to use Lead Spine.",
                },
                status=403,
            )
            return None
        if not identity.get("person_id"):
            self._send_json(
                {
                    "ok": False,
                    "error": "no_person",
                    "message": "Lead Spine requires a verified Person binding.",
                },
                status=403,
            )
            return None
        if isinstance(body, dict):
            for key in ("person_id", "verified_person_id", "actor_person_id"):
                spoof = body.get(key)
                if spoof and str(spoof).strip() != str(identity.get("person_id")).strip():
                    self._send_json(
                        {
                            "ok": False,
                            "error": "person_id_spoof",
                            "message": "Person id from the browser body is refused.",
                        },
                        status=400,
                    )
                    return None
        return identity

    def _send_lead_error(self, exc: Exception) -> None:
        if isinstance(exc, _lead_spine.LeadSpineError):
            code = exc.code
            if code in ("denied",):
                status = 403
                message = str(exc) if str(exc).startswith("You ") else (
                    "You do not have permission to access leads for this brand."
                )
                if "denied" in str(exc).lower() and not str(exc).startswith("You "):
                    message = (
                        "You do not have permission to access leads for this brand."
                    )
            elif code == "not_found":
                status = 404
                message = str(exc)
            else:
                status = 400
                message = str(exc)
            self._send_json(
                {"ok": False, "error": code, "message": message},
                status=status,
            )
            return
        self._send_json(
            {"ok": False, "error": "server_error", "message": str(exc)},
            status=500,
        )

    def _get_leads(self, qs: dict) -> None:
        identity = self._lead_identity()
        if identity is None:
            return
        brand = ((qs.get("brand") or [None])[0] or "").strip()
        if not brand:
            self._send_json(
                {"ok": False, "error": "invalid", "message": "brand query required."},
                status=400,
            )
            return
        try:
            payload = _lead_spine.api_list_leads(
                verified_person_id=identity["person_id"],
                brand_id=brand,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_lead_error(exc)
            return
        self._send_json(payload)

    def _get_lead(self, lead_id: str) -> None:
        identity = self._lead_identity()
        if identity is None:
            return
        try:
            payload = _lead_spine.api_get_lead(
                lead_id,
                verified_person_id=identity["person_id"],
            )
        except Exception as exc:  # noqa: BLE001
            self._send_lead_error(exc)
            return
        self._send_json(payload)

    def _post_lead_action(self, lead_id: str, action: str) -> None:
        try:
            body = self._read_json()
        except Exception:  # noqa: BLE001
            body = {}
        if not isinstance(body, dict):
            body = {}
        identity = self._lead_identity(body)
        if identity is None:
            return
        pid = identity["person_id"]
        try:
            if action == "touch":
                result = _lead_spine.record_human_touch(
                    lead_id,
                    verified_person_id=pid,
                    actor_type="PERSON",
                )
            elif action == "note":
                result = _lead_spine.record_note(
                    lead_id,
                    str(body.get("note") or ""),
                    verified_person_id=pid,
                    actor_type="PERSON",
                )
            elif action == "stage":
                if "source_stage" in body:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "source_stage_refused",
                            "message": "This path changes Wolf lifecycle only. Source stage stays as observed.",
                        },
                        status=400,
                    )
                    return
                ws = body.get("wolf_stage")
                if not ws:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "invalid",
                            "message": "wolf_stage required.",
                        },
                        status=400,
                    )
                    return
                result = _lead_spine.set_wolf_stage(
                    lead_id,
                    str(ws),
                    verified_person_id=pid,
                    actor_type="PERSON",
                )
            elif action == "assign":
                owner = body.get("owner_person_id")
                if not owner:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "invalid",
                            "message": "owner_person_id required. Use /unassign to clear.",
                        },
                        status=400,
                    )
                    return
                result = _lead_spine.assign_owner(
                    lead_id,
                    str(owner),
                    owner_assignment_id=(body.get("owner_assignment_id") or None),
                    verified_person_id=pid,
                )
            elif action == "unassign":
                # assign_owner already clears when owner is null — no separate unassign core.
                result = _lead_spine.assign_owner(
                    lead_id,
                    None,
                    owner_assignment_id=None,
                    verified_person_id=pid,
                )
            elif action == "work-item":
                wid = body.get("work_item_id")
                if not wid:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "invalid",
                            "message": "work_item_id required. This links an existing Core work item only.",
                        },
                        status=400,
                    )
                    return
                result = _lead_spine.link_work_item(
                    lead_id,
                    str(wid),
                    verified_person_id=pid,
                    actor_type="PERSON",
                )
            elif action == "claim":
                if "amount" in body:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "amount_refused",
                            "message": "Claim sets CLAIMED only. No amount. Verification needs evidence.",
                        },
                        status=400,
                    )
                    return
                result = _lead_spine.claim_conversion(
                    lead_id,
                    verified_person_id=pid,
                    actor_type="PERSON",
                    payload={k: v for k, v in body.items() if k != "person_id"},
                )
            else:
                self._send_err(404, "not found")
                return
        except Exception as exc:  # noqa: BLE001
            self._send_lead_error(exc)
            return
        lead = result.get("lead") or {}
        self._send_json(
            {
                "ok": True,
                "action": action,
                "lead": _lead_spine.lead_operator_card(lead),
                "event": result.get("event"),
            }
        )

    def _send_work_error(self, exc: Exception) -> None:
        if isinstance(exc, _work_items.WorkItemError):
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                },
                status=int(exc.http_status),
            )
            return
        self._send_json({"ok": False, "error": "server_error", "message": str(exc)}, status=500)

    def _get_core_work_items(self, qs: dict) -> None:
        identity = self._work_identity("work.read")
        if identity is None:
            return
        try:
            limit = int((qs.get("limit") or ["50"])[0])
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = int((qs.get("offset") or ["0"])[0])
        except (TypeError, ValueError):
            offset = 0
        try:
            items = _work_items.list_work_items(
                identity["person_id"],
                status=((qs.get("status") or [None])[0] or None) or None,
                owning_entity_id=((qs.get("owning_entity_id") or [None])[0] or None) or None,
                owner_person_id=((qs.get("owner_person_id") or [None])[0] or None) or None,
                work_type=((qs.get("work_type") or [None])[0] or None) or None,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json(
            {
                "ok": True,
                "work_items": items,
                "count": len(items),
                "limit": max(1, min(limit, 200)),
                "offset": max(0, offset),
                "person_id": identity["person_id"],
                "claimed_completed_is_not_verified": True,
            }
        )

    def _get_core_work_item(self, work_item_id: str) -> None:
        identity = self._work_identity("work.read")
        if identity is None:
            return
        item = _work_items.get_work_item(work_item_id)
        if not item:
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        if not _work_items.person_can_see_entity(
            identity["person_id"], item["owning_entity_id"]
        ):
            self._send_json({"ok": False, "error": "entity_out_of_scope"}, status=403)
            return
        self._send_json(
            {
                "ok": True,
                "work_item": item,
                "claimed_completed_is_not_verified": True,
            }
        )

    def _post_core_work_item(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        identity = self._work_identity("work.create", body)
        if identity is None:
            return
        # Refuse client status=VERIFIED / forged provenance
        if str(body.get("status") or "").strip().upper() == "VERIFIED":
            self._send_json(
                {
                    "ok": False,
                    "error": "illegal_transition",
                    "message": "Cannot set status=VERIFIED on create; use /verify",
                },
                status=400,
            )
            return
        actor_type = (body.get("created_by_actor_type") or "PERSON").strip().upper()
        try:
            item = _work_items.create_work_item(
                title=body.get("title") or "",
                description=body.get("description"),
                work_type=body.get("work_type") or "GENERAL",
                priority=body.get("priority", 3),
                owning_entity_id=body.get("owning_entity_id") or "",
                source_type=body.get("source_type") or "HUMAN",
                source_id=body.get("source_id"),
                created_by_actor_type=actor_type,
                created_by_person_id=body.get("created_by_person_id"),
                verified_person_id=identity["person_id"] if actor_type == "PERSON" else None,
                owner_person_id=body.get("owner_person_id"),
                owner_org_assignment_id=body.get("owner_org_assignment_id"),
                due_at=body.get("due_at"),
                parent_work_item_id=body.get("parent_work_item_id"),
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json({"ok": True, "work_item": item}, status=201)

    def _patch_core_work_item(self, work_item_id: str) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        identity = self._work_identity("work.update", body)
        if identity is None:
            return
        forbidden = {
            "status",
            "owner_person_id",
            "owner_org_assignment_id",
            "source_type",
            "source_id",
            "created_by_actor_type",
            "created_by_person_id",
            "owning_entity_id",
            "work_type",
        }
        hit = [k for k in forbidden if k in body]
        if hit:
            self._send_json(
                {
                    "ok": False,
                    "error": "immutable_or_wrong_endpoint",
                    "message": f"PATCH cannot set {hit}; use assign/transition endpoints",
                },
                status=400,
            )
            return
        kwargs: dict = {
            "verified_person_id": identity["person_id"],
            "identity": identity,
        }
        if "title" in body:
            kwargs["title"] = body.get("title")
        if "description" in body:
            kwargs["description"] = body.get("description")
        if "priority" in body:
            kwargs["priority"] = body.get("priority")
        if "due_at" in body:
            kwargs["due_at"] = body.get("due_at")
        try:
            item = _work_items.update_work_item_fields(work_item_id, **kwargs)
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json({"ok": True, "work_item": item})

    def _post_core_work_item_assign(self, work_item_id: str) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        identity = self._work_identity("work.assign", body)
        if identity is None:
            return
        try:
            item = _work_items.reassign_owner(
                work_item_id,
                verified_person_id=identity["person_id"],
                owner_person_id=body.get("owner_person_id"),
                owner_org_assignment_id=body.get("owner_org_assignment_id"),
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json({"ok": True, "work_item": item})

    def _post_core_work_item_start(self, work_item_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        identity = self._work_identity("work.update", body if isinstance(body, dict) else {})
        if identity is None:
            return
        try:
            item = _work_items.start_work_item(
                work_item_id,
                verified_person_id=identity["person_id"],
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json({"ok": True, "work_item": item})

    def _post_core_work_item_block(self, work_item_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        identity = self._work_identity("work.update", body if isinstance(body, dict) else {})
        if identity is None:
            return
        try:
            item = _work_items.block_work_item(
                work_item_id,
                verified_person_id=identity["person_id"],
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json({"ok": True, "work_item": item})

    def _post_core_work_item_complete(self, work_item_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        identity = self._work_identity("work.complete", body)
        if identity is None:
            return
        try:
            item = _work_items.claim_complete(
                work_item_id,
                verified_person_id=identity["person_id"],
                outcome=body.get("outcome"),
                completion_evidence_reference=body.get("completion_evidence_reference"),
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json(
            {
                "ok": True,
                "work_item": item,
                "claimed_completed_is_not_verified": True,
            }
        )

    def _post_core_work_item_verify(self, work_item_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        identity = self._work_identity("work.verify", body if isinstance(body, dict) else {})
        if identity is None:
            return
        try:
            item = _work_items.verify_work_item(
                work_item_id,
                verified_person_id=identity["person_id"],
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json({"ok": True, "work_item": item})

    def _post_core_work_item_cancel(self, work_item_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        identity = self._work_identity("work.update", body)
        if identity is None:
            return
        try:
            item = _work_items.cancel_work_item(
                work_item_id,
                verified_person_id=identity["person_id"],
                outcome=body.get("outcome"),
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_work_error(exc)
            return
        self._send_json({"ok": True, "work_item": item})

    def _approval_identity(self, permission: str, body: dict | None = None) -> dict | None:
        """Permission gate + verified person_id for approval mutations."""
        subject = self._require_permission(permission, body)
        if subject is None:
            return None
        identity = self._resolve_identity(body, emit_audit=False)
        if not identity.get("ok") or not identity.get("person_id"):
            self._send_json(
                {
                    "ok": False,
                    "error": "no_person",
                    "message": "Approvals require a verified Person binding.",
                    "required_permission": permission,
                },
                status=403,
            )
            return None
        identity = dict(identity)
        identity["correlation_id"] = getattr(self, "_wolf_correlation_id", None) or _audit.mint_correlation_id()
        return identity

    def _send_approval_error(self, exc: Exception) -> None:
        if isinstance(exc, _approvals.ApprovalError):
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                },
                status=int(exc.http_status),
            )
            return
        self._send_json({"ok": False, "error": "server_error", "message": str(exc)}, status=500)

    def _get_core_approvals(self, qs: dict) -> None:
        identity = self._approval_identity("approval.read")
        if identity is None:
            return
        try:
            limit = int((qs.get("limit") or ["50"])[0])
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = int((qs.get("offset") or ["0"])[0])
        except (TypeError, ValueError):
            offset = 0
        try:
            items = _approvals.list_approval_requests(
                identity["person_id"],
                status=((qs.get("status") or [None])[0] or None) or None,
                owning_entity_id=((qs.get("owning_entity_id") or [None])[0] or None) or None,
                requested_by_person_id=((qs.get("requested_by_person_id") or [None])[0] or None)
                or None,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_approval_error(exc)
            return
        self._send_json(
            {
                "ok": True,
                "approvals": items,
                "count": len(items),
                "limit": max(1, min(limit, 200)),
                "offset": max(0, offset),
                "person_id": identity["person_id"],
                "requested_is_not_approved": True,
                "approved_is_not_executed": True,
                "dual_approval": "NOT_BUILT",
            }
        )

    def _get_core_approval(self, approval_request_id: str) -> None:
        identity = self._approval_identity("approval.read")
        if identity is None:
            return
        item = _approvals.get_approval_request(approval_request_id)
        if not item:
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        if not _work_items.person_can_see_entity(
            identity["person_id"], item["owning_entity_id"]
        ):
            self._send_json({"ok": False, "error": "entity_out_of_scope"}, status=403)
            return
        decisions = _approvals.list_decisions(approval_request_id)
        self._send_json(
            {
                "ok": True,
                "approval": item,
                "decisions": decisions,
                "requested_is_not_approved": True,
                "approved_is_not_executed": True,
                "dual_approval": "NOT_BUILT",
            }
        )

    def _post_core_approval(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        identity = self._approval_identity("approval.request", body)
        if identity is None:
            return
        try:
            rdc_raw = body.get("required_decision_count", None)
            item = _approvals.create_approval_request(
                title=body.get("title") or "",
                description=body.get("description"),
                request_type=body.get("request_type") or "GENERAL",
                owning_entity_id=body.get("owning_entity_id") or "",
                brand_id=body.get("brand_id"),
                location_id=body.get("location_id"),
                department_id=body.get("department_id"),
                required_permission_code=body.get("required_permission_code") or "",
                material_amount=body.get("material_amount"),
                currency=body.get("currency"),
                source_type=body.get("source_type") or "HUMAN",
                source_id=body.get("source_id"),
                evidence_reference=body.get("evidence_reference"),
                expires_at=body.get("expires_at"),
                prior_request_id=body.get("prior_request_id"),
                requested_by_assignment_id=body.get("requested_by_assignment_id"),
                link_work_item=bool(body.get("link_work_item")),
                review_owner_person_id=body.get("review_owner_person_id"),
                required_decision_count=rdc_raw,
                bind_policy=bool(body.get("bind_policy")),
                scope_id=body.get("scope_id"),
                # Ignore client spoof of requester
                requested_by_person_id=None,
                verified_person_id=identity["person_id"],
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_approval_error(exc)
            return
        self._send_json({"ok": True, "approval": item}, status=201)

    def _post_core_approval_approve(self, approval_request_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        identity = self._approval_identity("approval.decide", body)
        if identity is None:
            return
        try:
            result = _approvals.approve_request(
                approval_request_id,
                verified_person_id=identity["person_id"],
                reason=body.get("reason"),
                decided_by_assignment_id=body.get("decided_by_assignment_id"),
                # Ignore client spoof of decider
                decided_by_person_id=None,
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_approval_error(exc)
            return
        self._send_json(result)

    def _post_core_approval_reject(self, approval_request_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        identity = self._approval_identity("approval.decide", body)
        if identity is None:
            return
        try:
            result = _approvals.reject_request(
                approval_request_id,
                verified_person_id=identity["person_id"],
                reason=body.get("reason"),
                decided_by_assignment_id=body.get("decided_by_assignment_id"),
                decided_by_person_id=None,
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_approval_error(exc)
            return
        self._send_json(result)

    def _post_core_approval_cancel(self, approval_request_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        identity = self._approval_identity("approval.cancel", body)
        if identity is None:
            return
        try:
            item = _approvals.cancel_request(
                approval_request_id,
                verified_person_id=identity["person_id"],
                reason=body.get("reason"),
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_approval_error(exc)
            return
        self._send_json({"ok": True, "approval": item})


    def _delegation_identity(self, permission: str, body: dict | None = None) -> dict | None:
        subject = self._require_permission(permission, body)
        if subject is None:
            return None
        identity = self._resolve_identity(body, emit_audit=False)
        if not identity.get("ok") or not identity.get("person_id"):
            self._send_json(
                {
                    "ok": False,
                    "error": "no_person",
                    "message": "Delegations require a verified Person binding.",
                    "required_permission": permission,
                },
                status=403,
            )
            return None
        identity = dict(identity)
        identity["correlation_id"] = getattr(self, "_wolf_correlation_id", None) or _audit.mint_correlation_id()
        return identity

    def _send_delegation_error(self, exc: Exception) -> None:
        if isinstance(exc, _delegation.DelegationError):
            self._send_json(
                {"ok": False, "error": exc.code, "message": str(exc)},
                status=int(exc.http_status),
            )
            return
        self._send_json({"ok": False, "error": "server_error", "message": str(exc)}, status=500)

    def _get_core_delegations(self, qs: dict) -> None:
        identity = self._delegation_identity("delegation.read")
        if identity is None:
            return
        try:
            limit = int((qs.get("limit") or ["50"])[0])
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = int((qs.get("offset") or ["0"])[0])
        except (TypeError, ValueError):
            offset = 0
        try:
            items = _delegation.list_delegations(
                identity["person_id"],
                status=((qs.get("status") or [None])[0] or None) or None,
                entity_id=((qs.get("entity_id") or [None])[0] or None) or None,
                delegator_person_id=((qs.get("delegator_person_id") or [None])[0] or None) or None,
                delegate_person_id=((qs.get("delegate_person_id") or [None])[0] or None) or None,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_delegation_error(exc)
            return
        self._send_json(
            {
                "ok": True,
                "delegations": items,
                "count": len(items),
                "limit": max(1, min(limit, 200)),
                "offset": max(0, offset),
                "person_id": identity["person_id"],
                "redelegation": "DENIED",
                "impersonation": "BLOCKED",
            }
        )

    def _get_core_delegation(self, delegation_id: str) -> None:
        identity = self._delegation_identity("delegation.read")
        if identity is None:
            return
        item = _delegation.get_delegation(delegation_id)
        if not item:
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        if not _work_items.person_can_see_entity(identity["person_id"], item["entity_id"]):
            self._send_json({"ok": False, "error": "entity_out_of_scope"}, status=403)
            return
        self._send_json(
            {
                "ok": True,
                "delegation": item,
                "redelegation": "DENIED",
                "impersonation": "BLOCKED",
            }
        )

    def _post_core_delegation(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        identity = self._delegation_identity("delegation.create", body)
        if identity is None:
            return
        # Prefer body fields for other party only; ignore forged delegator/delegate vs verified
        try:
            item = _delegation.create_delegation(
                verified_person_id=identity["person_id"],
                # Server ignores client spoof of delegator unless equal verified / Matt path
                delegator_person_id=body.get("delegator_person_id"),
                delegate_person_id=body.get("delegate_person_id") or "",
                delegator_assignment_id=body.get("delegator_assignment_id") or "",
                delegate_assignment_id=body.get("delegate_assignment_id") or "",
                entity_id=body.get("entity_id") or "",
                scope_id=body.get("scope_id") or "",
                permission_code=body.get("permission_code") or "",
                effective_from=body.get("effective_from") or "",
                effective_to=body.get("effective_to") or "",
                delegated_cap_amount=body.get("delegated_cap_amount"),
                currency=body.get("currency"),
                authority_limit_id=body.get("authority_limit_id"),
                reason=body.get("reason"),
                linked_work_item_id=body.get("linked_work_item_id"),
                allow_redelegation=int(body.get("allow_redelegation") or 0),
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_delegation_error(exc)
            return
        self._send_json({"ok": True, "delegation": item}, status=201)

    def _post_core_delegation_revoke(self, delegation_id: str) -> None:
        try:
            body = self._read_json() if int(self.headers.get("Content-Length") or 0) > 0 else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        identity = self._delegation_identity("delegation.revoke", body)
        if identity is None:
            return
        try:
            item = _delegation.revoke_delegation(
                delegation_id,
                verified_person_id=identity["person_id"],
                reason=body.get("reason"),
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_delegation_error(exc)
            return
        self._send_json({"ok": True, "delegation": item})

    def _get_core_me_authority_limits(self) -> None:
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        person_id = identity.get("person_id")
        limits = (
            _authority.list_authority_limits_for_person(person_id)
            if person_id else []
        )
        self._send_json({
            "ok": True,
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "asserted_identifier": identity.get("asserted_identifier"),
            "email": identity.get("email"),
            "person_id": person_id,
            "authority_limits": limits,
            "delegation": "BUILT",
            "redelegation": "DENIED",
            "impersonation": "BLOCKED",
            "dual_approval": "BUILT",
            "segregation_of_duties": "BUILT",
            "access_control_live": False,
            "note": identity.get("note"),
        })

    def _get_core_scopes(self) -> None:
        self._send_json({"ok": True, "scopes": _scope.list_scopes()})

    def _get_core_scope(self, scope_id: str) -> None:
        scope = _scope.get_scope(scope_id)
        if not scope:
            self._send_json({"ok": False, "error": "not_found", "scope_id": scope_id}, status=404)
            return
        self._send_json({
            "ok": True,
            "scope": scope,
            "targets": _scope.list_scope_targets(scope_id),
            "effective_context": _scope.resolve_effective_scope_context(scope_id),
        })

    def _get_core_assignment_scopes(self, assignment_id: str) -> None:
        # Assignment existence via staffing assignments table
        conn = _staffing.db_connect()
        try:
            row = conn.execute(
                "SELECT assignment_id FROM org_assignments WHERE assignment_id=?",
                (assignment_id,),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            self._send_json({"ok": False, "error": "not_found", "assignment_id": assignment_id}, status=404)
            return
        self._send_json({
            "ok": True,
            "assignment_id": assignment_id,
            "scopes": _scope.list_scopes_for_assignment(assignment_id, include_ended=True),
        })

    def _get_core_me_scopes(self) -> None:
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        person_id = identity.get("person_id")
        scopes = _scope.list_active_scopes_for_person(person_id) if person_id else []
        contexts = [
            _scope.resolve_effective_scope_context(s["scope_id"]) for s in scopes
        ]
        self._send_json({
            "ok": True,
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "asserted_identifier": identity.get("asserted_identifier"),
            "email": identity.get("email"),
            "person_id": person_id,
            "scopes": scopes,
            "effective_contexts": contexts,
            "note": identity.get("note"),
        })

    def _get_core_roles(self) -> None:
        self._send_json({"ok": True, "roles": _staffing.list_roles()})

    def _get_core_role(self, role_id: str) -> None:
        role = _staffing.get_role(role_id)
        if not role:
            self._send_json({"ok": False, "error": "not_found", "role_id": role_id}, status=404)
            return
        self._send_json({"ok": True, "role": role})

    def _get_core_positions(self) -> None:
        self._send_json({"ok": True, "positions": _staffing.list_positions()})

    def _get_core_position(self, position_id: str) -> None:
        pos = _staffing.get_position(position_id)
        if not pos:
            self._send_json({"ok": False, "error": "not_found", "position_id": position_id}, status=404)
            return
        self._send_json({"ok": True, "position": pos})

    def _get_core_position_assignments(self, position_id: str) -> None:
        if not _staffing.get_position(position_id):
            self._send_json({"ok": False, "error": "not_found", "position_id": position_id}, status=404)
            return
        self._send_json({
            "ok": True,
            "position_id": position_id,
            "assignments": _staffing.list_assignments_for_position(position_id),
            "current_occupants": _staffing.get_current_occupants(position_id),
        })

    def _get_core_person_assignments(self, person_id: str) -> None:
        if not _identity.get_person(person_id):
            self._send_json({"ok": False, "error": "not_found", "person_id": person_id}, status=404)
            return
        self._send_json({
            "ok": True,
            "person_id": person_id,
            "assignments": _staffing.list_assignments_for_person(person_id, include_ended=True),
            "org_context": _staffing.resolve_org_context_for_person(person_id),
        })

    def _get_core_me_assignments(self) -> None:
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        person_id = identity.get("person_id")
        assignments = (
            _staffing.list_active_assignments_for_person(person_id) if person_id else []
        )
        self._send_json({
            "ok": True,
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "asserted_identifier": identity.get("asserted_identifier"),
            "email": identity.get("email"),
            "person_id": person_id,
            "assignments": assignments,
            "org_context": _staffing.resolve_org_context_for_person(person_id) if person_id else None,
            "note": identity.get("note"),
        })

    def _get_core_persons(self) -> None:
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        person_id = identity.get("person_id")
        if not person_id or not _rbac.can(
            person_id, "organisation.person.read", _rbac.default_content_target()
        ):
            self._send_json({
                "ok": False,
                "error": "forbidden",
                "permission": "organisation.person.read",
                "identity_assurance": identity.get("identity_assurance"),
                "real_authentication": identity.get("real_authentication"),
            }, status=403)
            return
        self._send_json({"ok": True, "persons": _identity.list_persons()})

    def _get_core_person(self, person_id: str) -> None:
        person = _identity.get_person(person_id)
        if not person:
            self._send_json({"ok": False, "error": "not_found", "person_id": person_id}, status=404)
            return
        # Omit nothing required; legal_name may be null
        self._send_json({
            "ok": True,
            "person": {
                "person_id": person["person_id"],
                "display_name": person["display_name"],
                "legal_name": person.get("legal_name"),
                "status": person["status"],
            },
        })

    def _get_core_person_auth_identities(self, person_id: str) -> None:
        if not _identity.get_person(person_id):
            self._send_json({"ok": False, "error": "not_found", "person_id": person_id}, status=404)
            return
        rows = _identity.list_auth_identities_for_person(person_id)
        # Return identifiers for operator debug on Beta; not a public marketing API
        safe = [
            {
                "auth_identity_id": r["auth_identity_id"],
                "provider": r["provider"],
                "identifier": r["identifier"],
                "status": r["status"],
                "is_primary": r["is_primary"],
            }
            for r in rows
        ]
        self._send_json({"ok": True, "person_id": person_id, "auth_identities": safe})

    def _get_core_me(self) -> None:
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        self._send_json({
            "ok": True,
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "asserted_identifier": identity.get("asserted_identifier"),
            "email": identity.get("email"),
            "permission_subject": identity.get("permission_subject"),
            "person_id": identity.get("person_id"),
            "person": identity.get("person"),
            "auth_identity_id": identity.get("auth_identity_id"),
            "auth_mode": identity.get("auth_mode"),
            "development_assertion_allowed": (
                identity.get("auth_mode") == _request_auth.AUTH_MODE_DEVELOPMENT
            ),
            "note": identity.get("note"),
        })

    def _get_core_entities(self) -> None:
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        person_id = identity.get("person_id")
        if not person_id or not _rbac.can(
            person_id, "organisation.entity.read", _rbac.default_content_target()
        ):
            self._send_json({
                "ok": False,
                "error": "forbidden",
                "permission": "organisation.entity.read",
                "identity_assurance": identity.get("identity_assurance"),
                "real_authentication": identity.get("real_authentication"),
            }, status=403)
            return
        self._send_json({"ok": True, "entities": _org.list_entities()})

    def _get_core_entity(self, entity_id: str) -> None:
        ent = _org.get_entity(entity_id)
        if not ent:
            self._send_json({"ok": False, "error": "not_found", "entity_id": entity_id}, status=404)
            return
        self._send_json({"ok": True, "entity": ent})

    def _get_core_entity_brands(self, entity_id: str) -> None:
        if not _org.get_entity(entity_id):
            self._send_json({"ok": False, "error": "not_found", "entity_id": entity_id}, status=404)
            return
        self._send_json({
            "ok": True,
            "entity_id": entity_id,
            "brands": _org.list_brands_by_entity(entity_id),
        })

    def _get_core_entity_locations(self, entity_id: str) -> None:
        if not _org.get_entity(entity_id):
            self._send_json({"ok": False, "error": "not_found", "entity_id": entity_id}, status=404)
            return
        self._send_json({
            "ok": True,
            "entity_id": entity_id,
            "locations": _org.list_locations_by_entity(entity_id),
        })

    def _get_core_entity_departments(self, entity_id: str) -> None:
        if not _org.get_entity(entity_id):
            self._send_json({"ok": False, "error": "not_found", "entity_id": entity_id}, status=404)
            return
        self._send_json({
            "ok": True,
            "entity_id": entity_id,
            "departments": _org.list_departments_by_entity(entity_id),
        })

    def _get_core_brand(self, brand_id: str) -> None:
        brand = _org.get_brand(brand_id)
        if not brand:
            self._send_json({"ok": False, "error": "not_found", "brand_id": brand_id}, status=404)
            return
        self._send_json({"ok": True, "brand": brand})

    def _get_brands(self) -> None:
        try:
            conn = db_connect()
            try:
                # theme_json / default_assignee / logo_url may be missing on very old DBs
                cols = {r[1] for r in conn.execute("PRAGMA table_info(brands)").fetchall()}
                base = "id, display_name, aliases_json, cadence_json, status"
                if "theme_json" in cols:
                    base += ", theme_json"
                if "default_assignee" in cols:
                    base += ", default_assignee"
                if "logo_url" in cols:
                    base += ", logo_url"
                rows = [dict(r) for r in conn.execute(
                    f"SELECT {base} FROM brands ORDER BY id"
                ).fetchall()]
                for r in rows:
                    try:
                        r["aliases"] = json.loads(r.pop("aliases_json") or "[]")
                    except json.JSONDecodeError:
                        r["aliases"] = []
                    try:
                        r["cadence"] = json.loads(r.pop("cadence_json") or "{}")
                    except json.JSONDecodeError:
                        r["cadence"] = {}
                    theme = _p26.brand_theme_payload(r)
                    r["theme"] = theme
                    r["default_assignee"] = r.get("default_assignee") or theme.get("default_assignee") or ""
                    r.pop("theme_json", None)
                self._send_json({"ok": True, "brands": rows, "count": len(rows)})
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _get_intel_plan(self, plan_id: int, qs: dict | None = None) -> None:
        qs = qs or {}
        try:
            conn = db_connect()
            try:
                draft = _skills.get_plan_working_draft(conn, plan_id)
                if not draft:
                    self._send_err(404, "plan not found")
                    return
                want_ux = (qs.get("ux") or ["0"])[0].strip().lower() in ("1", "true", "yes")
                payload = {"ok": True, **draft}
                if want_ux:
                    payload["ux"] = _ux_shape_plan(draft)
                self._send_json(payload)
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _list_intel_plans(self, qs: dict) -> None:
        """List content_plans for a brand — surface existing Working Drafts (critical).

        Phase 2.5A: default data_lane=operational ONLY (hide test fixtures #1–3 from
        normal UI). Pass data_lane=all|test to include non-operational rows (dev).
        Rows stay in DB — never deleted.
        """
        brand = (qs.get("brand") or qs.get("brand_id") or [""])[0].strip().lower()
        status = (qs.get("status") or [""])[0].strip()
        lane_q = (qs.get("data_lane") or qs.get("lane") or ["operational"])[0].strip().lower()
        try:
            conn = db_connect()
            try:
                clauses = []
                params: list = []
                if brand:
                    clauses.append("brand_id = ?")
                    params.append(brand)
                if status:
                    clauses.append("status = ?")
                    params.append(status)
                # Default: operational only. data_lane=all → no lane filter; =test → test only.
                if lane_q in ("", "operational", "default"):
                    clauses.append("ifnull(data_lane,'operational') = 'operational'")
                elif lane_q == "test":
                    clauses.append("ifnull(data_lane,'operational') = 'test'")
                elif lane_q in ("all", "*", "any"):
                    pass  # no lane filter (dev)
                else:
                    clauses.append("ifnull(data_lane,'operational') = ?")
                    params.append(lane_q)
                where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
                # Operational primary (Habitat), then latest id
                rows = [
                    dict(r)
                    for r in conn.execute(
                        f"""
                        SELECT id, brand_id, title, period_start, period_end, status,
                               created_by, created_at, updated_at, data_lane,
                               review_state, approved_revision_id
                        FROM content_plans
                        {where}
                        ORDER BY
                          CASE WHEN ifnull(data_lane,'operational')='operational' THEN 0 ELSE 1 END,
                          id DESC
                        """,
                        params,
                    ).fetchall()
                ]
                for r in rows:
                    r["is_test_lane"] = (r.get("data_lane") or "") == "test"
                    r["review_label"] = _p26.review_label(r)
                    r["status_label"] = r["review_label"]
                    r["title_raw"] = r.get("title") or ""
                    if r.get("period_start") and r.get("period_end"):
                        r["title"] = _human_fortnight_title(
                            r.get("brand_id") or "",
                            r.get("period_start") or "",
                            r.get("period_end") or "",
                        )
                    # light card counts
                    cc = conn.execute(
                        """
                        SELECT card_type, COUNT(*) AS n FROM content_cards
                        WHERE plan_id=? GROUP BY card_type
                        """,
                        (r["id"],),
                    ).fetchall()
                    counts = {row["card_type"]: row["n"] for row in cc}
                    r["posts"] = int(counts.get("feed") or counts.get("post") or 0)
                    r["stories"] = int(counts.get("story") or 0)
                self._send_json({"ok": True, "plans": rows, "count": len(rows), "brand": brand or None, "data_lane": lane_q or "operational"})
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _get_ux_card(self, card_id: int) -> None:
        try:
            conn = db_connect()
            try:
                row = conn.execute("SELECT * FROM content_cards WHERE id=?", (card_id,)).fetchone()
                if not row:
                    self._send_err(404, "card not found")
                    return
                card = dict(row)
                try:
                    card["body"] = json.loads(card.get("body_json") or "{}")
                except json.JSONDecodeError:
                    card["body"] = {}
                brief = _ux_card_brief(card)
                self._send_json({"ok": True, "card": brief})
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _get_ux_dashboard(self, qs: dict) -> None:
        brand = (qs.get("brand") or qs.get("brand_id") or ["habitat"])[0].strip().lower() or "habitat"
        try:
            conn = db_connect()
            try:
                # Phase 2.5A: operational lane ONLY for normal dashboard / WI context
                row = conn.execute(
                    """
                    SELECT id FROM content_plans
                    WHERE brand_id=?
                      AND ifnull(data_lane,'operational')='operational'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (brand,),
                ).fetchone()
                plan_ux = None
                if row:
                    draft = _skills.get_plan_working_draft(conn, int(row["id"]))
                    if draft:
                        plan_ux = _ux_shape_plan(draft)
                # Recent uploads: prefer smart_upload assets (operational), fallback staged
                uploads = []
                try:
                    for r in conn.execute(
                        """
                        SELECT id, brand, media_type, type, canonical_filename, original_filename,
                               library_status, processing_status, uploaded_at, date_added, subject
                        FROM assets
                        WHERE source_system='smart_upload'
                          AND ifnull(data_lane,'operational')='operational'
                          AND brand=?
                        ORDER BY id DESC LIMIT 8
                        """,
                        (brand,),
                    ).fetchall():
                        d = dict(r)
                        lib = d.get("library_status") or ""
                        ui = "READY" if lib == "LIBRARY_READY" else ("FAILED" if lib == "FAILED" else "CHECKING")
                        uploads.append({
                            "id": d["id"],
                            "brand": d.get("brand"),
                            "type": d.get("media_type") or d.get("type"),
                            "name": d.get("canonical_filename") or d.get("subject") or f"upload-{d['id']}",
                            "original_filename": d.get("original_filename"),
                            "status": ui,
                            "library_status": lib,
                            "created_at": d.get("uploaded_at") or d.get("date_added"),
                        })
                except sqlite3.Error:
                    uploads = []
                if not uploads:
                    try:
                        for r in conn.execute(
                            """
                            SELECT id, suggested_brand, suggested_type, suggested_slug, status, created_at,
                                   detected_mime, canonical_filename, original_filename, library_status
                            FROM staged_assets
                            WHERE ifnull(data_lane,'operational')='operational'
                            ORDER BY id DESC LIMIT 8
                            """
                        ).fetchall():
                            d = dict(r)
                            uploads.append({
                                "id": d["id"],
                                "brand": d.get("suggested_brand"),
                                "type": d.get("suggested_type"),
                                "name": d.get("canonical_filename") or d.get("suggested_slug") or f"upload-{d['id']}",
                                "original_filename": d.get("original_filename"),
                                "status": d.get("library_status") or d.get("status") or "STAGED",
                                "created_at": d.get("created_at"),
                            })
                    except sqlite3.Error:
                        uploads = []
                # Library count
                try:
                    asset_n = conn.execute(
                        "SELECT COUNT(*) FROM assets WHERE brand=? AND ifnull(data_lane,'operational')='operational'",
                        (brand,),
                    ).fetchone()[0]
                except sqlite3.Error:
                    asset_n = 0
                progress = (plan_ux or {}).get("progress") or {}
                self._send_json({
                    "ok": True,
                    "brand": brand,
                    "current_plan": plan_ux,
                    "recent_uploads": uploads,
                    "library_count": asset_n,
                    "posts_progress": progress.get("posts_label") or "0/0",
                    "stories_progress": progress.get("stories_label") or "0/0",
                    "review_label": ((plan_ux or {}).get("plan") or {}).get("review_label"),
                })
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _get_me_capabilities(self, qs: dict) -> None:
        """Return permission bits for UI gates (Build Next / Approve / etc)."""
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        subject = identity.get("permission_subject") or identity.get("email")
        perms = _wi.list_permissions(subject)
        self._send_json({
            "ok": True,
            "subject": subject,
            "identity_assurance": identity.get("identity_assurance"),
            "real_authentication": identity.get("real_authentication"),
            "person_id": identity.get("person_id"),
            "auth_mode": identity.get("auth_mode"),
            **perms,
            "can_create_plan": perms.get("can_create_plan", False),
            "can_approve_plan": perms.get("can_approve_plan", False),
            "can_edit_plan": perms.get("can_edit_plan", False),
            "can_upload": perms.get("can_upload", False),
            "can_update_production": perms.get("can_update_production", False),
            "can_use_wolf_intelligence": perms.get("can_use_wolf_intelligence", False),
            "can_view_plan": perms.get("can_view_plan", False),
        })

    def _intel_build_next(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        subject = self._require_can_create_plan(body)
        if subject is None:
            return
        brand_id = (body.get("brand_id") or body.get("brand") or "habitat").strip().lower()
        try:
            conn = db_connect()
            try:
                brand = conn.execute("SELECT id FROM brands WHERE id=?", (brand_id,)).fetchone()
                if not brand:
                    self._send_err(404, f"brand not found: {brand_id}")
                    return
                result = _skills.orchestrate_build_next(conn, brand_id, subject)
                ps = result.get("period_start")
                pe = result.get("period_end")
                pid = result.get("plan_id")
                if pid and ps and pe:
                    human = _human_fortnight_title(brand_id, ps, pe)
                    conn.execute(
                        "UPDATE content_plans SET title=?, updated_at=? WHERE id=?",
                        (human, _wi.now_iso(), pid),
                    )
                    conn.commit()
                    result["title"] = human
                self._send_json({"ok": True, **result})
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _intel_plan_edit(self, plan_id: int) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        subject = self._require_permission("can_edit_plan", body)
        if subject is None:
            return
        patch = body.get("patch") if isinstance(body.get("patch"), dict) else {
            k: v for k, v in body.items() if k not in ("subject", "actor")
        }
        try:
            conn = db_connect()
            try:
                draft = _skills.human_edit_plan(conn, plan_id, patch, subject)
                self._send_json({"ok": True, "role": "HUMAN_EDIT", **draft})
            except KeyError:
                self._send_err(404, "plan not found")
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _intel_card_edit(self, card_id: int) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        subject = self._require_permission("can_edit_plan", body)
        if subject is None:
            return
        patch = body.get("patch") if isinstance(body.get("patch"), dict) else {
            k: v for k, v in body.items() if k not in ("subject", "actor")
        }
        # Production / workflow status changes also require can_update_production
        if isinstance(patch, dict) and "workflow_status" in patch:
            if self._require_permission("can_update_production", body) is None:
                return
        try:
            conn = db_connect()
            try:
                card = _skills.human_edit_card(conn, card_id, patch, subject)
                # Inherit brand default assignee only when creating — edits keep override
                review_label = card.get("plan_review_label") or card.get("plan_review_state")
                self._send_json({
                    "ok": True,
                    "role": "HUMAN_EDIT",
                    "card": card,
                    "review_label": review_label,
                    "review_state": card.get("plan_review_state"),
                    "message": (
                        "Saved. " + (review_label or "")
                        if review_label == "CHANGES PENDING REVIEW"
                        else "Saved."
                    ),
                })
            except KeyError:
                self._send_err(404, "card not found")
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))


    def _intel_card_production_status(self, card_id: int) -> None:
        """POST /api/planner/cards/{id}/production-status — workflow_status only.

        Gated by can_update_production. Subject: X-Wolf-Subject DEVELOPMENT ONLY.
        """
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        subject = self._require_permission("can_update_production", body)
        if subject is None:
            return
        status = body.get("workflow_status") or body.get("status")
        if not status and isinstance(body.get("patch"), dict):
            status = body["patch"].get("workflow_status") or body["patch"].get("status")
        if not status:
            self._send_err(400, "workflow_status required")
            return
        try:
            conn = db_connect()
            try:
                card = _skills.human_edit_card(
                    conn, card_id, {"workflow_status": str(status).strip()}, subject
                )
                self._send_json({
                    "ok": True,
                    "card": card,
                    "workflow_status": str(status).strip(),
                    "subject": subject,
                })
            except KeyError:
                self._send_err(404, "card not found")
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _intel_plan_approve(self, plan_id: int) -> None:
        try:
            body = self._read_json()
        except Exception:
            body = {}
        subject = self._require_permission(
            "can_approve_plan", body if isinstance(body, dict) else {}
        )
        if subject is None:
            return
        try:
            conn = db_connect()
            try:
                snap = _skills.approve_plan(conn, plan_id, subject)
                # DB keeps Human_Approved / HUMAN_APPROVED revision; UI label is APPROVED
                # Also used for APPROVE CHANGES (pending → approved)
                self._send_json({
                    "ok": True,
                    "role": "HUMAN_APPROVED",
                    "status_label": "APPROVED",
                    "ui_status": "APPROVED",
                    "review_label": "APPROVED",
                    "review_state": "APPROVED",
                    "published": False,
                    "message": "Approved. Previous approved version preserved in history. No publish side effects.",
                    **snap,
                })
            except KeyError:
                self._send_err(404, "plan not found")
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))



    def _admin_sync_metricool(self, from_get: bool = False) -> None:
        """POST/GET /api/admin/sync-metricool?brand=habitat — Metricool READ sync only.

        Gated by can_create_plan. Never schedules/publishes. No secrets in response.
        """
        body: dict = {}
        if not from_get:
            try:
                body = self._read_json()
            except Exception:
                body = {}
        if not isinstance(body, dict):
            body = {}
        qs = parse_qs(urlparse(self.path).query)
        brand = (
            (body.get("brand") or body.get("brand_key") or "")
            or (qs.get("brand") or [""])[0]
            or "habitat"
        ).strip().lower()
        try:
            window_days = int(body.get("window_days") or (qs.get("window_days") or ["60"])[0])
        except (TypeError, ValueError):
            window_days = 60
        subject = self._require_can_create_plan(body)
        if subject is None:
            return
        try:
            scripts_dir = str(Path(__file__).resolve().parent)
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from metricool_read_client import metricool_enabled, metricool_status
            if not metricool_enabled():
                st = metricool_status()
                self._send_json(
                    {
                        "ok": False,
                        "error": "metricool_disabled",
                        "status": st.get("status") or "DISABLED IN BETA",
                        "metricool": st,
                        "brand": brand,
                        "subject": subject,
                    },
                    status=200,
                )
                return
            from sync_metricool_performance import sync_metricool_performance
            report = sync_metricool_performance(brand_key=brand, window_days=window_days)
            safe = {
                k: v
                for k, v in report.items()
                if k not in ("token", "user_token", "authorization", "raw", "headers")
            }
            self._send_json({"ok": bool(safe.get("ok")), "sync": safe, "subject": subject})
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "sync_failed",
                    "message": f"Metricool sync soft-failed: {type(exc).__name__}",
                    "brand": brand,
                },
                status=200,
            )



    def _get_plan_changes(self, plan_id: int) -> None:
        """VIEW CHANGES — current vs last approved. No technical revision jargon in payload labels."""
        try:
            conn = db_connect()
            try:
                view = _skills.get_plan_changes_view(conn, plan_id)
                # Shape for UI: human labels only
                current_ux = _ux_shape_plan(view.get("current") or {}) if view.get("current") else None
                approved_ux = None
                if view.get("approved_snapshot"):
                    try:
                        approved_ux = _ux_shape_plan(view["approved_snapshot"])
                    except Exception:
                        approved_ux = None
                edits = []
                for e in view.get("pending_edits") or []:
                    edits.append({
                        "card_id": e.get("card_id"),
                        "title": e.get("title"),
                        "kind": "POST" if (e.get("card_type") or "").lower() in ("feed", "post") else "STORY",
                        "number": e.get("sequence"),
                        "edited_by": e.get("actor"),
                        "edited_at": e.get("created_at"),
                    })
                self._send_json({
                    "ok": True,
                    "plan_id": plan_id,
                    "review_label": view.get("review_label"),
                    "current": current_ux,
                    "approved": approved_ux,
                    "recent_edits": edits,
                })
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _intel_request_revision(self, plan_id: int) -> None:
        """REQUEST REVISION — Matt/Amanda only (can_approve_plan)."""
        try:
            body = self._read_json()
        except Exception:
            body = {}
        subject = self._require_permission("can_approve_plan", body if isinstance(body, dict) else {})
        if subject is None:
            return
        note = ""
        if isinstance(body, dict):
            note = str(body.get("note") or body.get("message") or "")
        try:
            conn = db_connect()
            try:
                snap = _skills.request_plan_revision(conn, plan_id, subject, note=note)
                self._send_json({
                    "ok": True,
                    "review_label": "CHANGES PENDING REVIEW",
                    "review_state": "CHANGES_PENDING_REVIEW",
                    "message": "Revision requested. Team can keep editing.",
                    "note": note,
                    **{k: snap.get(k) for k in ("plan", "review_state", "review_label") if k in snap},
                })
            except KeyError:
                self._send_err(404, "plan not found")
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))

    def _wolf_chat(self) -> None:
        """WI chat shell — honest unavailable when not connected. No fabricate. No silent plan edit."""
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        subject = self._require_permission("can_use_wolf_intelligence", body)
        if subject is None:
            return
        action = str((body or {}).get("action") or (body or {}).get("quick_action") or "CHAT").strip().upper()
        message = str((body or {}).get("message") or "").strip()
        brand = str((body or {}).get("brand") or (body or {}).get("brand_id") or "").strip()
        card_id = (body or {}).get("card_id") or (body or {}).get("content_item_id")
        reply = _p26.wi_unavailable_reply(action)
        reply.update({
            "subject": subject,
            "brand": brand or None,
            "card_id": card_id,
            "user_message": message,
            "transcript_append": [
                {"role": "user", "text": message or action},
                {"role": "assistant", "text": reply["message"]},
            ],
        })
        self._send_json(reply)

    def _asset_media(self, asset_id: int, mode: str, qs: dict) -> None:
        """Stream preview/download bytes. Paths never returned in JSON."""
        identity = self._resolve_identity()
        if not identity.get("ok"):
            self._send_identity_deny(identity)
            return
        subject = identity.get("permission_subject") or identity.get("email")
        if not subject or not (
            _wi.has_permission(subject, "can_upload")
            or _wi.has_permission(subject, "can_view_plan")
            or _wi.has_permission(subject, "can_edit_plan")
        ):
            self._send_json({
                "ok": False,
                "error": "forbidden",
                "required_permission": "can_view_plan|can_upload",
                "identity_assurance": identity.get("identity_assurance"),
            }, status=403)
            return
        conn = db_connect()
        try:
            row = conn.execute(
                "SELECT id, brand, stage, filename, v2_path, canonical_filename, original_filename, media_type, type, data_lane "
                "FROM assets WHERE id=?",
                (asset_id,),
            ).fetchone()
            if not row:
                self._send_err(404, "asset not found")
                return
            d = dict(row)
            # Resolve under beta library only
            v2 = d.get("v2_path") or ""
            stage = d.get("stage") or "RAW"
            fname = d.get("canonical_filename") or d.get("filename") or ""
            candidates = []
            if v2:
                candidates.append(Path(v2))
            if fname:
                candidates.append(LIBRARY_V2 / stage / fname)
                candidates.append(LIBRARY_V2 / fname)
            fpath = None
            for c in candidates:
                try:
                    p = _ensure_under_beta(c) if c.is_absolute() else _ensure_under_beta((BETA_ROOT / c).resolve())
                except Exception:
                    try:
                        p = (LIBRARY_V2 / stage / fname).resolve()
                        _ensure_under_beta(p)
                    except Exception:
                        continue
                if p.exists() and p.is_file():
                    fpath = p
                    break
            if not fpath:
                # hover preview not ready — honest
                self._send_json({
                    "ok": False,
                    "error": "preview_unavailable",
                    "message": "Media file not available for preview yet (no fake proxy). Download may also be unavailable.",
                    "readiness": "CHECKING",
                }, status=404)
                return
            data = fpath.read_bytes()
            # MIME
            ext = fpath.suffix.lower()
            mime = {
                ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".webp": "image/webp", ".gif": "image/gif",
                ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
            }.get(ext, "application/octet-stream")
            disp = "attachment" if mode == "download" else "inline"
            name = d.get("canonical_filename") or d.get("original_filename") or fpath.name
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'{disp}; filename="{name}"')
            self.send_header("Cache-Control", "private, max-age=60")
            self.end_headers()
            self.wfile.write(data)
        finally:
            conn.close()

    def _assets_zip(self) -> None:
        """Multi-select ZIP download if practical — permissioned."""
        import io
        import zipfile
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        subject = self._require_permission("can_upload", body)
        if subject is None:
            # allow view too
            subject = self._require_permission("can_view_plan", body)
            if subject is None:
                return
        ids = body.get("ids") or body.get("asset_ids") or []
        if not isinstance(ids, list) or not ids:
            self._send_err(400, "ids required")
            return
        if len(ids) > 40:
            self._send_err(400, "max 40 files per ZIP")
            return
        conn = db_connect()
        buf = io.BytesIO()
        added = 0
        try:
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for raw_id in ids:
                    try:
                        aid = int(raw_id)
                    except (TypeError, ValueError):
                        continue
                    row = conn.execute(
                        "SELECT id, stage, filename, v2_path, canonical_filename FROM assets WHERE id=?",
                        (aid,),
                    ).fetchone()
                    if not row:
                        continue
                    d = dict(row)
                    fname = d.get("canonical_filename") or d.get("filename") or f"asset-{aid}"
                    stage = d.get("stage") or "RAW"
                    candidates = []
                    if d.get("v2_path"):
                        candidates.append(Path(d["v2_path"]))
                    candidates.append(LIBRARY_V2 / stage / fname)
                    for c in candidates:
                        try:
                            p = c if c.is_absolute() else (BETA_ROOT / c)
                            p = _ensure_under_beta(p.resolve())
                        except Exception:
                            continue
                        if p.exists() and p.is_file():
                            zf.write(p, arcname=fname)
                            added += 1
                            break
            if added == 0:
                self._send_json({
                    "ok": False,
                    "error": "zip_empty",
                    "message": "No readable files for ZIP (honest: files may still be checking).",
                }, status=404)
                return
            data = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", 'attachment; filename="library-selection.zip"')
            self.end_headers()
            self.wfile.write(data)
        finally:
            conn.close()

    def _upload_check_duplicate(self) -> None:
        """Warn if hash/size/original/canonical already exists (same lane)."""
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
            return
        subject = self._require_permission("can_upload", body)
        if subject is None:
            return
        lane = str(body.get("data_lane") or "operational")
        conn = db_connect()
        try:
            hits = _p26.find_duplicates(
                conn,
                content_hash=body.get("content_hash"),
                file_size=body.get("file_size") or body.get("size"),
                original_filename=body.get("original_filename"),
                canonical_filename=body.get("canonical_filename"),
                data_lane=lane,
            )
            self._send_json({
                "ok": True,
                "duplicate": bool(hits),
                "matches": hits,
                "message": "Possible duplicate — already in Library." if hits else "No duplicate found.",
            })
        finally:
            conn.close()


def pick_port(preferred: int) -> int:
    """Bind preferred port only for Beta (no silent fallback to 8789).

    Phase 2 rule: Beta Intelligence serves :8788 ONLY. Falling back to 8789
    caused deploy confusion; fail loud if 8788 is busy.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, preferred))
            return preferred
        except OSError as exc:
            raise RuntimeError(
                f"Beta port {preferred} busy — refusing fallback. "
                f"Stop the other serve_beta and retry. ({exc})"
            ) from None


def main() -> None:
    # Load beta-os/.env auth keys if unset (AUD / mode / team domain)
    _request_auth._load_auth_env()
    preferred = int(os.environ.get("BETA_PORT", DEFAULT_PORT))
    if preferred == 8787:
        print("Refusing port 8787 (reserved). Use 8788+.", file=sys.stderr)
        sys.exit(1)

    ensure_schema()
    DASHBOARDS.mkdir(parents=True, exist_ok=True)
    INCOMING_DROP.mkdir(parents=True, exist_ok=True)

    port = pick_port(preferred)
    if port != preferred:
        print(f"Port {preferred} busy; using {port}")

    server = ThreadingHTTPServer((HOST, port), BetaHandler)
    print(f"Content Engine 2.0  http://{HOST}:{port}/content-2.0.html")
    print(f"  health  http://{HOST}:{port}/api/health")
    print(f"  planner sqlite → {CATALOG_DB}")
    print(f"  root    {BETA_ROOT}")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
