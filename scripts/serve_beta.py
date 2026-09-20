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
from core import intel_eval_cost as _intel_cost
from core import intel_approve_to_rule as _intel_rule
from core import lead_spine as _lead_spine
from core import integration_health as _integration_health
from core import tech_capability_registry as _tech_registry
from core import sop_factory as _sop
from core import strat_12wy_prove as _strat_12wy
from core import escalation_burndown as _burndown
from core import sale_evidence_pack as _sale_pack
from core import sale_buyer_dataroom as _buyer_room
from core import sale_buyer_mode as _buyer_mode
from core import sale_attack_audit as _attack_audit
from core import restore_drill as _restore_drill
from core import failure_domains as _failure_domains
from core import dr_crown_jewel as _crown_jewel
from core import crm_connector_prove as _crm_connector
from core import gws_integrate_prove as _gws_prove
from core import crm_package_intel as _pkg_intel
from core import msc_asset_register as _msc_assets
from core import msc_compliance_pack as _msc_compliance
from core import msc_cyber_baseline as _msc_cyber
from core import msc_records_defensibility as _msc_records
from core import intg_secrets_env as _intg_secrets
from core import ggv_client_profitability as _ggv_pnl
from core import ggv_strategy_machine as _ggv_strategy
from core import amg_journey_workflow as _amg_journey
from core import amg_daily_ops_state as _amg_ops
from core import amg_packages_products as _amg_packages
from core import amg_revenue_yield as _amg_yield
from core import amg_service_improve as _amg_improve
from core import amg_sla_incident as _amg_sla
from core import amg_pms_orchestration as _amg_pms
from core import hr_hiring_onboarding as _hr_hire
from core import hr_training_competency as _hr_train
from core import hr_payroll_inputs as _hr_pay
from core import hr_retention_signals as _hr_ret
from core import fin_mgmt_reporting as _fin_mgmt
from core import ggv_intercompany_client as _ggv_ic
from core import bzg_venue_pnl as _bzg_pnl
from core import bzg_variance_waste as _bzg_var
from core import bzg_allocation_engine as _bzg_alloc
from core import bzg_bom_yield as _bzg_bom
from core import msc_posture_prove as _msc_posture
from core import intg_connector_contract as _intg_contract
from core import intg_connector_cap_tests as _intg_cap_tests
from core import crm_lead_cap_prove as _crm_lead_prove
from core import strat_radar_prove as _strat_radar
from core import ggv_speed_to_lead_prove as _ggv_speed
from core import crm_identity_memory as _crm_ident
from core import bzg_reputation_observe as _bzg_rep
from core import ggv_social_derive as _ggv_social

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
        # Eval/cost ledger. Owner only. No price lookup, no billing.
        if path == "/api/intel/eval-cost":
            self._intel_eval_cost_get(qs)
            return
        # CAP-INTEL-05 approve-to-rule skeleton. Owner or role. Not a production rule.
        if self._intel_rule_handled(path, "GET"):
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
        if path == "/api/integration-health":
            self._integration_health_get()
            return
        # CAP-INTG-06 Tech & Capability Registry. Owner read. Writes refused.
        if path == "/api/tech-registry":
            self._tech_registry_get(qs)
            return
        m_reg = re.match(r"^/api/tech-registry/([^/]+)$", path)
        if m_reg:
            self._tech_registry_get(qs, m_reg.group(1))
            return
        # CAP-STRAT-01 prove pack. Owner read. Does not invent PROVEN.
        if path == "/api/strat/12wy-prove":
            self._strat_12wy_prove()
            return
        # CAP-CORE-12 burn-down counters. Owner read. Does not clear Needs Matt.
        if path == "/api/core/escalation-burndown":
            self._escalation_burndown_get()
            return
        # CAP-SALE-01 framework. Owner read. No VDR, no filled evidence.
        if self._sale_pack_export_code(path):
            self._sale_pack_write_refused(path)
            return
        if path == "/api/sale-evidence-pack":
            self._sale_pack_get(qs)
            return
        if path == "/api/sale-evidence-pack/domains":
            self._sale_pack_get(qs, domains_only=True)
            return
        m_sale = re.match(r"^/api/sale-evidence-pack/([^/]+)$", path)
        if m_sale:
            self._sale_pack_get(qs, m_sale.group(1))
            return
        # CAP-SALE-02 framework. Owner read. Empty folders. No share, no export, no buyer.
        if self._buyer_room_refuse_code(path):
            self._buyer_room_write_refused(path)
            return
        if path == "/api/buyer-dataroom":
            self._buyer_room_get(qs)
            return
        if path == "/api/buyer-dataroom/tree":
            self._buyer_room_get(qs, view="tree")
            return
        if path == "/api/buyer-dataroom/checklist":
            self._buyer_room_get(qs, view="checklist")
            return
        m_room = re.match(r"^/api/buyer-dataroom/([^/]+)$", path)
        if m_room:
            self._buyer_room_get(qs, folder_id=m_room.group(1))
            return
        # CAP-SALE-03 framework. Owner read. Hides stay hidden. Export slots stay empty.
        # /api/buyer-mode/export stays on the sale-pack refuse above this block.
        if self._buyer_mode_refuse_code(path):
            self._buyer_mode_write_refused(path)
            return
        if path == "/api/buyer-mode":
            self._buyer_mode_get(qs)
            return
        if path == "/api/buyer-mode/surfaces":
            self._buyer_mode_get(qs, view="surfaces")
            return
        if path == "/api/buyer-mode/hides":
            self._buyer_mode_get(qs, view="hides")
            return
        if path == "/api/buyer-mode/exports":
            self._buyer_mode_get(qs, view="exports")
            return
        m_mode = re.match(r"^/api/buyer-mode/([^/]+)$", path)
        if m_mode:
            self._buyer_mode_get(qs, surface_id=m_mode.group(1))
            return
        # CAP-SALE-04 framework. Owner read. Sections named. Packs empty. Licence preserved.
        if self._attack_audit_refuse_code(path):
            self._attack_audit_write_refused(path)
            return
        if path == "/api/attack-audit":
            self._attack_audit_get(qs)
            return
        if path == "/api/attack-audit/sections":
            self._attack_audit_get(qs, view="sections")
            return
        if path == "/api/attack-audit/packs":
            self._attack_audit_get(qs, view="packs")
            return
        if path == "/api/attack-audit/licence":
            self._attack_audit_get(qs, view="licence")
            return
        m_audit = re.match(r"^/api/attack-audit/([^/]+)$", path)
        if m_audit:
            self._attack_audit_get(qs, section_id=m_audit.group(1))
            return
        # CAP-DR-01 framework. Owner read. No live restore. No NAS/B2/Production write.
        if self._restore_drill_refuse_code(path):
            self._restore_drill_write_refused(path)
            return
        if path == "/api/restore-drill":
            self._restore_drill_get(qs)
            return
        if path == "/api/restore-drill/checklist":
            self._restore_drill_get(qs, view="checklist")
            return
        if path == "/api/restore-drill/schema":
            self._restore_drill_get(qs, view="schema")
            return
        if path == "/api/restore-drill/log":
            self._restore_drill_get(qs, view="log")
            return
        if path.startswith("/api/restore-drill/"):
            self._restore_drill_get(qs, step_id=path.rsplit("/", 1)[-1])
            return
        # CAP-DR-02 failure domains. Owner read. Beta is not Production. Slots stay empty.
        if self._failure_domains_refuse_code(path):
            self._failure_domains_write_refused(path)
            return
        if path == "/api/failure-domains":
            self._failure_domains_get(qs)
            return
        if path == "/api/failure-domains/checklist":
            self._failure_domains_get(qs, view="checklist")
            return
        if path == "/api/failure-domains/schema":
            self._failure_domains_get(qs, view="schema")
            return
        if path == "/api/failure-domains/log":
            self._failure_domains_get(qs, view="log")
            return
        if path == "/api/failure-domains/domains":
            self._failure_domains_get(qs, view="domains")
            return
        if path.startswith("/api/failure-domains/"):
            self._failure_domains_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-DR-02 crown-jewel register. Owner read. Contents stay closed. Slots stay empty.
        if self._crown_jewel_refuse_code(path):
            self._crown_jewel_write_refused(path)
            return
        if path == "/api/crown-jewels":
            self._crown_jewel_get(qs)
            return
        if path == "/api/crown-jewels/checklist":
            self._crown_jewel_get(qs, view="checklist")
            return
        if path == "/api/crown-jewels/schema":
            self._crown_jewel_get(qs, view="schema")
            return
        if path == "/api/crown-jewels/register":
            self._crown_jewel_get(qs, view="register")
            return
        if path == "/api/crown-jewels/systems":
            self._crown_jewel_get(qs, view="systems")
            return
        if path == "/api/crown-jewels/log":
            self._crown_jewel_get(qs, view="log")
            return
        if path == "/api/crown-jewels/domains":
            self._crown_jewel_get(qs, view="domains")
            return
        if path.startswith("/api/crown-jewels/"):
            self._crown_jewel_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-CRM-04 connector prove. Owner read. Klaviyo is not ActiveCampaign. No send.
        if self._crm_connector_refuse_code(path):
            self._crm_connector_write_refused(path)
            return
        if path == "/api/crm-connector-prove":
            self._crm_connector_get(qs)
            return
        if path == "/api/crm-connector-prove/checklist":
            self._crm_connector_get(qs, view="checklist")
            return
        if path == "/api/crm-connector-prove/schema":
            self._crm_connector_get(qs, view="schema")
            return
        if path == "/api/crm-connector-prove/log":
            self._crm_connector_get(qs, view="log")
            return
        if path == "/api/crm-connector-prove/connectors":
            self._crm_connector_get(qs, view="connectors")
            return
        if path == "/api/crm-connector-prove/brands":
            self._crm_connector_get(qs, view="brands")
            return
        if path == "/api/crm-connector-prove/gaps":
            self._crm_connector_get(qs, view="gaps")
            return
        if path.startswith("/api/crm-connector-prove/"):
            self._crm_connector_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-INTG-03 workspace prove. Owner read. Four surfaces. No probe. No GREEN.
        if self._gws_prove_refuse_code(path):
            self._gws_prove_write_refused(path)
            return
        if path == "/api/gws-integrate-prove":
            self._gws_prove_get(qs)
            return
        if path == "/api/gws-integrate-prove/checklist":
            self._gws_prove_get(qs, view="checklist")
            return
        if path == "/api/gws-integrate-prove/schema":
            self._gws_prove_get(qs, view="schema")
            return
        if path == "/api/gws-integrate-prove/log":
            self._gws_prove_get(qs, view="log")
            return
        if path == "/api/gws-integrate-prove/surfaces":
            self._gws_prove_get(qs, view="surfaces")
            return
        if path == "/api/gws-integrate-prove/gaps":
            self._gws_prove_get(qs, view="gaps")
            return
        if path.startswith("/api/gws-integrate-prove/"):
            self._gws_prove_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-CRM-03 package register. Owner read. Empty is not a price. No booking.
        if self._pkg_intel_refuse_code(path):
            self._pkg_intel_write_refused(path)
            return
        if path == "/api/crm/package-intel":
            self._pkg_intel_get(qs)
            return
        if path == "/api/crm/package-intel/schema":
            self._pkg_intel_get(qs, view="schema")
            return
        if path == "/api/crm/package-intel/products":
            self._pkg_intel_get(qs, view="products")
            return
        if path == "/api/crm/package-intel/brands":
            self._pkg_intel_get(qs, view="brands")
            return
        if path.startswith("/api/crm/package-intel/"):
            self._pkg_intel_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-MSC-01 asset register. Owner read. Empty is not an inventory count. No payment.
        if self._msc_assets_refuse_code(path):
            self._msc_assets_write_refused(path)
            return
        if path == "/api/msc/assets":
            self._msc_assets_get(qs)
            return
        if path == "/api/msc/assets/schema":
            self._msc_assets_get(qs, view="schema")
            return
        if path == "/api/msc/assets/venues":
            self._msc_assets_get(qs, view="venues")
            return
        if path == "/api/msc/assets/register":
            self._msc_assets_get(qs, view="register")
            return
        if path.startswith("/api/msc/assets/"):
            self._msc_assets_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-MSC-03 compliance pack. Owner read. Empty is not proof. No payment. No Cloudflare mutate.
        if self._msc_compliance_refuse_code(path):
            self._msc_compliance_write_refused(path)
            return
        if path == "/api/msc/compliance":
            self._msc_compliance_get(qs)
            return
        if path == "/api/msc/compliance/schema":
            self._msc_compliance_get(qs, view="schema")
            return
        if path == "/api/msc/compliance/kinds":
            self._msc_compliance_get(qs, view="kinds")
            return
        if path == "/api/msc/compliance/pack":
            self._msc_compliance_get(qs, view="pack")
            return
        if path.startswith("/api/msc/compliance/"):
            self._msc_compliance_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-MSC-04 cyber baseline. Owner read. Empty is not proof. No current MFA. No Cloudflare mutate.
        if self._msc_cyber_refuse_code(path):
            self._msc_cyber_write_refused(path)
            return
        if path == "/api/msc/cyber":
            self._msc_cyber_get(qs)
            return
        if path == "/api/msc/cyber/schema":
            self._msc_cyber_get(qs, view="schema")
            return
        if path == "/api/msc/cyber/kinds":
            self._msc_cyber_get(qs, view="kinds")
            return
        if path == "/api/msc/cyber/baseline":
            self._msc_cyber_get(qs, view="baseline")
            return
        if path.startswith("/api/msc/cyber/"):
            self._msc_cyber_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-MSC-05 records register. Owner read. Empty is not proof. No live hold. No Cloudflare mutate.
        if self._msc_records_refuse_code(path):
            self._msc_records_write_refused(path)
            return
        if path == "/api/msc/records":
            self._msc_records_get(qs)
            return
        if path == "/api/msc/records/schema":
            self._msc_records_get(qs, view="schema")
            return
        if path == "/api/msc/records/kinds":
            self._msc_records_get(qs, view="kinds")
            return
        if path == "/api/msc/records/register":
            self._msc_records_get(qs, view="register")
            return
        if path.startswith("/api/msc/records/"):
            self._msc_records_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-INTG-07 secrets/env separation. Owner read. Empty is not proof. Not a live vault.
        if self._intg_secrets_refuse_code(path):
            self._intg_secrets_write_refused(path)
            return
        if path == "/api/intg/secrets":
            self._intg_secrets_get(qs)
            return
        if path == "/api/intg/secrets/schema":
            self._intg_secrets_get(qs, view="schema")
            return
        if path == "/api/intg/secrets/kinds":
            self._intg_secrets_get(qs, view="kinds")
            return
        if path == "/api/intg/secrets/register":
            self._intg_secrets_get(qs, view="register")
            return
        if path == "/api/intg/secrets/pointers":
            self._intg_secrets_get(qs, view="pointers")
            return
        if path.startswith("/api/intg/secrets/"):
            self._intg_secrets_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-GGV-03 client/contract P&L skeleton. Owner read. Empty is not a live P&L. No invented numbers.
        if self._ggv_pnl_refuse_code(path):
            self._ggv_pnl_write_refused(path)
            return
        if path == "/api/ggv/client-profitability":
            self._ggv_pnl_get(qs)
            return
        if path == "/api/ggv/client-profitability/schema":
            self._ggv_pnl_get(qs, view="schema")
            return
        if path == "/api/ggv/client-profitability/kinds":
            self._ggv_pnl_get(qs, view="kinds")
            return
        if path == "/api/ggv/client-profitability/register":
            self._ggv_pnl_get(qs, view="register")
            return
        if path.startswith("/api/ggv/client-profitability/"):
            self._ggv_pnl_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-GGV-01 strategy machine. Owner read. Empty is not a live strategy machine.
        if self._ggv_strategy_refuse_code(path):
            self._ggv_strategy_write_refused(path)
            return
        if path == "/api/ggv/strategy-machine":
            self._ggv_strategy_get(qs)
            return
        if path == "/api/ggv/strategy-machine/schema":
            self._ggv_strategy_get(qs, view="schema")
            return
        if path == "/api/ggv/strategy-machine/kinds":
            self._ggv_strategy_get(qs, view="kinds")
            return
        if path == "/api/ggv/strategy-machine/framework":
            self._ggv_strategy_get(qs, view="framework")
            return
        if path.startswith("/api/ggv/strategy-machine/"):
            self._ggv_strategy_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-AMG-02 guest journey. Owner read. Empty is not a live journey workflow.
        if self._amg_journey_refuse_code(path):
            self._amg_journey_write_refused(path)
            return
        if path == "/api/amg/journey-workflow":
            self._amg_journey_get(qs)
            return
        if path == "/api/amg/journey-workflow/schema":
            self._amg_journey_get(qs, view="schema")
            return
        if path == "/api/amg/journey-workflow/kinds":
            self._amg_journey_get(qs, view="kinds")
            return
        if path == "/api/amg/journey-workflow/framework":
            self._amg_journey_get(qs, view="framework")
            return
        if path.startswith("/api/amg/journey-workflow/"):
            self._amg_journey_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-AMG-04 daily hotel operating state. Owner read. Empty is not live ops.
        if self._amg_ops_refuse_code(path):
            self._amg_ops_write_refused(path)
            return
        if path == "/api/amg/daily-ops-state":
            self._amg_ops_get(qs)
            return
        if path == "/api/amg/daily-ops-state/schema":
            self._amg_ops_get(qs, view="schema")
            return
        if path == "/api/amg/daily-ops-state/kinds":
            self._amg_ops_get(qs, view="kinds")
            return
        if path == "/api/amg/daily-ops-state/framework":
            self._amg_ops_get(qs, view="framework")
            return
        if path.startswith("/api/amg/daily-ops-state/"):
            self._amg_ops_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-AMG-03 packages as products. Owner read. Empty is not a live catalog.
        if self._amg_packages_refuse_code(path):
            self._amg_packages_write_refused(path)
            return
        if path == "/api/amg/packages-products":
            self._amg_packages_get(qs)
            return
        if path == "/api/amg/packages-products/schema":
            self._amg_packages_get(qs, view="schema")
            return
        if path == "/api/amg/packages-products/kinds":
            self._amg_packages_get(qs, view="kinds")
            return
        if path == "/api/amg/packages-products/framework":
            self._amg_packages_get(qs, view="framework")
            return
        if path.startswith("/api/amg/packages-products/"):
            self._amg_packages_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-AMG-05 hotel revenue and yield. Owner read. Empty is not live yield.
        if self._amg_yield_refuse_code(path):
            self._amg_yield_write_refused(path)
            return
        if path == "/api/amg/revenue-yield":
            self._amg_yield_get(qs)
            return
        if path == "/api/amg/revenue-yield/schema":
            self._amg_yield_get(qs, view="schema")
            return
        if path == "/api/amg/revenue-yield/kinds":
            self._amg_yield_get(qs, view="kinds")
            return
        if path == "/api/amg/revenue-yield/framework":
            self._amg_yield_get(qs, view="framework")
            return
        if path.startswith("/api/amg/revenue-yield/"):
            self._amg_yield_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-GGV-06 intercompany client mode. Owner read. Empty is not live billing.
        if self._ggv_ic_refuse_code(path):
            self._ggv_ic_write_refused(path)
            return
        if path == "/api/ggv/intercompany-client":
            self._ggv_ic_get(qs)
            return
        if path == "/api/ggv/intercompany-client/schema":
            self._ggv_ic_get(qs, view="schema")
            return
        if path == "/api/ggv/intercompany-client/kinds":
            self._ggv_ic_get(qs, view="kinds")
            return
        if path == "/api/ggv/intercompany-client/framework":
            self._ggv_ic_get(qs, view="framework")
            return
        if path.startswith("/api/ggv/intercompany-client/"):
            self._ggv_ic_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-BZG-02 venue P&L / management rollup. Owner read. Empty is not a live venue P&L.
        if self._bzg_pnl_refuse_code(path):
            self._bzg_pnl_write_refused(path)
            return
        if path == "/api/bzg/venue-pnl":
            self._bzg_pnl_get(qs)
            return
        if path == "/api/bzg/venue-pnl/schema":
            self._bzg_pnl_get(qs, view="schema")
            return
        if path == "/api/bzg/venue-pnl/kinds":
            self._bzg_pnl_get(qs, view="kinds")
            return
        if path == "/api/bzg/venue-pnl/framework":
            self._bzg_pnl_get(qs, view="framework")
            return
        if path.startswith("/api/bzg/venue-pnl/"):
            self._bzg_pnl_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-BZG-04 variance / waste analysis. Owner read. Empty is not a live analysis.
        if self._bzg_var_refuse_code(path):
            self._bzg_var_write_refused(path)
            return
        if path == "/api/bzg/variance-waste":
            self._bzg_var_get(qs)
            return
        if path == "/api/bzg/variance-waste/schema":
            self._bzg_var_get(qs, view="schema")
            return
        if path == "/api/bzg/variance-waste/kinds":
            self._bzg_var_get(qs, view="kinds")
            return
        if path == "/api/bzg/variance-waste/framework":
            self._bzg_var_get(qs, view="framework")
            return
        if path.startswith("/api/bzg/variance-waste/"):
            self._bzg_var_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-BZG-05 central kitchen / shared cost allocation. Owner read. Empty is not a live allocation engine.
        if self._bzg_alloc_refuse_code(path):
            self._bzg_alloc_write_refused(path)
            return
        if path == "/api/bzg/allocation-engine":
            self._bzg_alloc_get(qs)
            return
        if path == "/api/bzg/allocation-engine/schema":
            self._bzg_alloc_get(qs, view="schema")
            return
        if path == "/api/bzg/allocation-engine/kinds":
            self._bzg_alloc_get(qs, view="kinds")
            return
        if path == "/api/bzg/allocation-engine/framework":
            self._bzg_alloc_get(qs, view="framework")
            return
        if path.startswith("/api/bzg/allocation-engine/"):
            self._bzg_alloc_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-BZG-06 Recipe / Cost Standards (BOM/yield). Owner read. Empty is not live BOM/yield machinery.
        if self._bzg_bom_refuse_code(path):
            self._bzg_bom_write_refused(path)
            return
        if path == "/api/bzg/bom-yield":
            self._bzg_bom_get(qs)
            return
        if path == "/api/bzg/bom-yield/schema":
            self._bzg_bom_get(qs, view="schema")
            return
        if path == "/api/bzg/bom-yield/kinds":
            self._bzg_bom_get(qs, view="kinds")
            return
        if path == "/api/bzg/bom-yield/framework":
            self._bzg_bom_get(qs, view="framework")
            return
        if path.startswith("/api/bzg/bom-yield/"):
            self._bzg_bom_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-AMG-07 service improvement / review-to-improve loop. Owner read. Empty is not a live loop.
        if self._amg_improve_refuse_code(path):
            self._amg_improve_write_refused(path)
            return
        if path == "/api/amg/service-improve":
            self._amg_improve_get(qs)
            return
        if path == "/api/amg/service-improve/schema":
            self._amg_improve_get(qs, view="schema")
            return
        if path == "/api/amg/service-improve/kinds":
            self._amg_improve_get(qs, view="kinds")
            return
        if path == "/api/amg/service-improve/framework":
            self._amg_improve_get(qs, view="framework")
            return
        if path.startswith("/api/amg/service-improve/"):
            self._amg_improve_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-AMG-06 SLA / incident trail. Owner read. Empty is not a live trail.
        if self._amg_sla_refuse_code(path):
            self._amg_sla_write_refused(path)
            return
        if path == "/api/amg/sla-incident":
            self._amg_sla_get(qs)
            return
        if path == "/api/amg/sla-incident/schema":
            self._amg_sla_get(qs, view="schema")
            return
        if path == "/api/amg/sla-incident/kinds":
            self._amg_sla_get(qs, view="kinds")
            return
        if path == "/api/amg/sla-incident/framework":
            self._amg_sla_get(qs, view="framework")
            return
        if path.startswith("/api/amg/sla-incident/"):
            self._amg_sla_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-AMG-01 Hotel PMS orchestration. Owner read. Empty is not live PMS.
        if self._amg_pms_refuse_code(path):
            self._amg_pms_write_refused(path)
            return
        if path == "/api/amg/pms-orchestration":
            self._amg_pms_get(qs)
            return
        if path == "/api/amg/pms-orchestration/schema":
            self._amg_pms_get(qs, view="schema")
            return
        if path == "/api/amg/pms-orchestration/kinds":
            self._amg_pms_get(qs, view="kinds")
            return
        if path == "/api/amg/pms-orchestration/framework":
            self._amg_pms_get(qs, view="framework")
            return
        if path.startswith("/api/amg/pms-orchestration/"):
            self._amg_pms_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-HR-02 Hiring & Onboarding. Owner read. Empty is not live hiring.
        if self._hr_hire_refuse_code(path):
            self._hr_hire_write_refused(path)
            return
        if path == "/api/hr/hiring-onboarding":
            self._hr_hire_get(qs)
            return
        if path == "/api/hr/hiring-onboarding/schema":
            self._hr_hire_get(qs, view="schema")
            return
        if path == "/api/hr/hiring-onboarding/kinds":
            self._hr_hire_get(qs, view="kinds")
            return
        if path == "/api/hr/hiring-onboarding/framework":
            self._hr_hire_get(qs, view="framework")
            return
        if path.startswith("/api/hr/hiring-onboarding/"):
            self._hr_hire_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-HR-03 Training & Competency. Owner read. Empty is not live training.
        if self._hr_train_refuse_code(path):
            self._hr_train_write_refused(path)
            return
        if path == "/api/hr/training-competency":
            self._hr_train_get(qs)
            return
        if path == "/api/hr/training-competency/schema":
            self._hr_train_get(qs, view="schema")
            return
        if path == "/api/hr/training-competency/kinds":
            self._hr_train_get(qs, view="kinds")
            return
        if path == "/api/hr/training-competency/framework":
            self._hr_train_get(qs, view="framework")
            return
        if path.startswith("/api/hr/training-competency/"):
            self._hr_train_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-HR-04 Payroll Inputs. Owner read. Empty is not live payroll inputs.
        if self._hr_pay_refuse_code(path):
            self._hr_pay_write_refused(path)
            return
        if path == "/api/hr/payroll-inputs":
            self._hr_pay_get(qs)
            return
        if path == "/api/hr/payroll-inputs/schema":
            self._hr_pay_get(qs, view="schema")
            return
        if path == "/api/hr/payroll-inputs/kinds":
            self._hr_pay_get(qs, view="kinds")
            return
        if path == "/api/hr/payroll-inputs/framework":
            self._hr_pay_get(qs, view="framework")
            return
        if path.startswith("/api/hr/payroll-inputs/"):
            self._hr_pay_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-HR-05 Retention & Succession Signals. Owner read. Empty is not live retention/succession.
        if self._hr_ret_refuse_code(path):
            self._hr_ret_write_refused(path)
            return
        if path == "/api/hr/retention-signals":
            self._hr_ret_get(qs)
            return
        if path == "/api/hr/retention-signals/schema":
            self._hr_ret_get(qs, view="schema")
            return
        if path == "/api/hr/retention-signals/kinds":
            self._hr_ret_get(qs, view="kinds")
            return
        if path == "/api/hr/retention-signals/framework":
            self._hr_ret_get(qs, view="framework")
            return
        if path.startswith("/api/hr/retention-signals/"):
            self._hr_ret_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-FIN-05 Management Reporting. Owner read. Empty is not a live management-reporting pack.
        if self._fin_mgmt_refuse_code(path):
            self._fin_mgmt_write_refused(path)
            return
        if path == "/api/fin/mgmt-reporting":
            self._fin_mgmt_get(qs)
            return
        if path == "/api/fin/mgmt-reporting/schema":
            self._fin_mgmt_get(qs, view="schema")
            return
        if path == "/api/fin/mgmt-reporting/kinds":
            self._fin_mgmt_get(qs, view="kinds")
            return
        if path == "/api/fin/mgmt-reporting/framework":
            self._fin_mgmt_get(qs, view="framework")
            return
        if path.startswith("/api/fin/mgmt-reporting/"):
            self._fin_mgmt_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-MSC-02 posture prove. Owner read. Empty is not a prove and not READY.
        if self._msc_posture_refuse_code(path):
            self._msc_posture_write_refused(path)
            return
        if path == "/api/msc/posture":
            self._msc_posture_get(qs)
            return
        if path == "/api/msc/posture/schema":
            self._msc_posture_get(qs, view="schema")
            return
        if path == "/api/msc/posture/kinds":
            self._msc_posture_get(qs, view="kinds")
            return
        if path == "/api/msc/posture/framework":
            self._msc_posture_get(qs, view="framework")
            return
        if path.startswith("/api/msc/posture/"):
            self._msc_posture_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-INTG-01 connector contract. Owner read. Empty is not Yanolja or ESB.
        if self._intg_contract_refuse_code(path):
            self._intg_contract_write_refused(path)
            return
        if path == "/api/intg/connector-contract":
            self._intg_contract_get(qs)
            return
        if path == "/api/intg/connector-contract/schema":
            self._intg_contract_get(qs, view="schema")
            return
        if path == "/api/intg/connector-contract/kinds":
            self._intg_contract_get(qs, view="kinds")
            return
        if path == "/api/intg/connector-contract/framework":
            self._intg_contract_get(qs, view="framework")
            return
        if path.startswith("/api/intg/connector-contract/"):
            self._intg_contract_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-INTG-04 connector tests. Owner read. Empty is not a bank prove or a bank feed.
        if self._intg_cap_tests_refuse_code(path):
            self._intg_cap_tests_write_refused(path)
            return
        if path == "/api/intg/connector-cap-tests":
            self._intg_cap_tests_get(qs)
            return
        if path == "/api/intg/connector-cap-tests/schema":
            self._intg_cap_tests_get(qs, view="schema")
            return
        if path == "/api/intg/connector-cap-tests/kinds":
            self._intg_cap_tests_get(qs, view="kinds")
            return
        if path == "/api/intg/connector-cap-tests/framework":
            self._intg_cap_tests_get(qs, view="framework")
            return
        if path.startswith("/api/intg/connector-cap-tests/"):
            self._intg_cap_tests_get(qs, ref_id=path.rsplit("/", 1)[-1])
            return
        # CAP-CRM-01 bound prove. Owner read. Does not invent a lead or PROVEN.
        if path == "/api/crm/lead-cap-prove":
            self._crm_lead_prove_get()
            return
        # CAP-STRAT-02 prove pack. Owner read. Progress is not this CAP. Does not invent PROVEN.
        if path == "/api/strat/radar-prove":
            self._strat_radar_prove_get()
            return
        # CAP-GGV-04 speed-to-lead prove. Owner read. Does not invent a lead, a receipt, or PROVEN.
        if path == "/api/ggv/speed-to-lead-prove":
            self._ggv_speed_prove_get()
            return
        # CAP-BZG-07 reputation observe. No scrape. No guest reply. No invented rating.
        if self._bzg_reputation_scrape(path):
            self._bzg_reputation_scrape_refused()
            return
        if self._bzg_reputation_reply(path):
            self._bzg_reputation_reply_refused()
            return
        if path in {"/api/bzg/reputation", "/api/bzg/reputation/observations"}:
            self._bzg_reputation_list(qs)
            return
        m_bzg = re.match(r"^/api/bzg/reputation/([^/]+)$", path)
        if m_bzg and m_bzg.group(1) not in {"observe", "scrape", "reply", "observations"}:
            self._bzg_reputation_read(m_bzg.group(1))
            return
        # CAP-GGV-05 social DERIVE. Stored Metricool reads only. No write. No ad spend.
        if self._ggv_social_metricool(path):
            self._ggv_social_metricool_refused()
            return
        if self._ggv_social_ads(path):
            self._ggv_social_ads_refused()
            return
        if path in {"/api/ggv/social", "/api/ggv/social/derive"}:
            self._ggv_social_get(qs)
            return
        # CAP-CRM-02 identity memory. Owner or authorised staff. Not a lead. Not a blast.
        if self._crm_identity_blast(path) or (
            path.startswith("/api/crm/") and (qs.get("blast") or [""])[0].strip()
        ):
            self._crm_identity_blast_refused()
            return
        if path == "/api/crm/identity":
            self._crm_identity_list(qs)
            return
        m_crm = re.match(r"^/api/crm/identity/([^/]+)$", path)
        if m_crm and m_crm.group(1) not in {"note", "link", "merge", "blast"}:
            self._crm_identity_read(m_crm.group(1))
            return
        # CAP-CORE-11 SOP Factory v1. Owner or role. Anon → 403. Not live without approve.
        if path == "/api/sop":
            self._sop_list()
            return
        m_sop = re.match(r"^/api/sop/([^/]+)$", path)
        if m_sop:
            self._sop_read(m_sop.group(1))
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
        # Before /api/leads/<id> so "triage" is not treated as a lead id.
        if path == "/api/leads/triage":
            self._get_leads_triage(qs)
            return
        m_lead = re.match(r"^/api/leads/([^/]+)$", path)
        if m_lead:
            self._get_lead(m_lead.group(1))
            return

        if path in ("/", "/index.html"):
            self.path = "/content-2.0.html"
        elif path in ("/progress", "/progress/"):
            self.path = "/progress.html"
        elif path in (
            "/integration-health",
            "/integration-health/",
            "/integration-health.html",
            "/dashboards/integration-health.html",
        ):
            self._integration_health_page()
            return
        elif path in (
            "/tech-registry",
            "/tech-registry/",
            "/tech-registry.html",
            "/dashboards/tech-registry.html",
        ):
            self._tech_registry_page()
            return
        elif path in (
            "/12wy-prove",
            "/12wy-prove/",
            "/12wy-prove.html",
            "/dashboards/12wy-prove.html",
        ):
            self._strat_12wy_page()
            return
        elif path in (
            "/escalation-burndown",
            "/escalation-burndown/",
            "/escalation-burndown.html",
            "/dashboards/escalation-burndown.html",
        ):
            self._escalation_burndown_page()
            return
        elif path in (
            "/sale-evidence-pack",
            "/sale-evidence-pack/",
            "/sale-evidence-pack.html",
            "/dashboards/sale-evidence-pack.html",
        ):
            self._sale_pack_page()
            return
        elif path in (
            "/buyer-dataroom",
            "/buyer-dataroom/",
            "/buyer-dataroom.html",
            "/dashboards/buyer-dataroom.html",
        ):
            self._buyer_room_page()
            return
        elif path in (
            "/buyer-mode",
            "/buyer-mode/",
            "/buyer-mode.html",
            "/dashboards/buyer-mode.html",
        ):
            self._buyer_mode_page()
            return
        elif path in (
            "/attack-audit",
            "/attack-audit/",
            "/attack-audit.html",
            "/dashboards/attack-audit.html",
        ):
            self._attack_audit_page()
            return
        elif path in (
            "/restore-drill",
            "/restore-drill/",
            "/restore-drill.html",
            "/dashboards/restore-drill.html",
        ):
            self._restore_drill_page()
            return
        elif path in (
            "/failure-domains",
            "/failure-domains/",
            "/failure-domains.html",
            "/dashboards/failure-domains.html",
        ):
            self._failure_domains_page()
            return
        elif path in (
            "/crown-jewels",
            "/crown-jewels/",
            "/crown-jewels.html",
            "/dashboards/crown-jewels.html",
        ):
            self._crown_jewel_page()
            return
        elif path in (
            "/crm-connector-prove",
            "/crm-connector-prove/",
            "/crm-connector-prove.html",
            "/dashboards/crm-connector-prove.html",
        ):
            self._crm_connector_page()
            return
        elif path in (
            "/gws-integrate-prove",
            "/gws-integrate-prove/",
            "/gws-integrate-prove.html",
            "/dashboards/gws-integrate-prove.html",
        ):
            self._gws_prove_page()
            return
        elif path in (
            "/crm-package-intel",
            "/crm-package-intel/",
            "/crm-package-intel.html",
            "/dashboards/crm-package-intel.html",
        ):
            self._pkg_intel_page()
            return
        elif path in (
            "/msc-assets",
            "/msc-assets/",
            "/msc-assets.html",
            "/dashboards/msc-assets.html",
        ):
            self._msc_assets_page()
            return
        elif path in (
            "/msc-compliance",
            "/msc-compliance/",
            "/msc-compliance.html",
            "/dashboards/msc-compliance.html",
        ):
            self._msc_compliance_page()
            return
        elif path in (
            "/msc-cyber",
            "/msc-cyber/",
            "/msc-cyber.html",
            "/dashboards/msc-cyber.html",
        ):
            self._msc_cyber_page()
            return
        elif path in (
            "/msc-records",
            "/msc-records/",
            "/msc-records.html",
            "/dashboards/msc-records.html",
        ):
            self._msc_records_page()
            return
        elif path in (
            "/intg-secrets",
            "/intg-secrets/",
            "/intg-secrets.html",
            "/dashboards/intg-secrets.html",
        ):
            self._intg_secrets_page()
            return
        elif path in (
            "/ggv-client-profitability",
            "/ggv-client-profitability/",
            "/ggv-client-profitability.html",
            "/dashboards/ggv-client-profitability.html",
        ):
            self._ggv_pnl_page()
            return
        elif path in (
            "/ggv-strategy-machine",
            "/ggv-strategy-machine/",
            "/ggv-strategy-machine.html",
            "/dashboards/ggv-strategy-machine.html",
        ):
            self._ggv_strategy_page()
            return
        elif path in (
            "/amg-journey-workflow",
            "/amg-journey-workflow/",
            "/amg-journey-workflow.html",
            "/dashboards/amg-journey-workflow.html",
        ):
            self._amg_journey_page()
            return
        elif path in (
            "/amg-daily-ops-state",
            "/amg-daily-ops-state/",
            "/amg-daily-ops-state.html",
            "/dashboards/amg-daily-ops-state.html",
        ):
            self._amg_ops_page()
            return
        elif path in (
            "/amg-packages-products",
            "/amg-packages-products/",
            "/amg-packages-products.html",
            "/dashboards/amg-packages-products.html",
        ):
            self._amg_packages_page()
            return
        elif path in (
            "/amg-revenue-yield",
            "/amg-revenue-yield/",
            "/amg-revenue-yield.html",
            "/dashboards/amg-revenue-yield.html",
        ):
            self._amg_yield_page()
            return
        elif path in (
            "/ggv-intercompany-client",
            "/ggv-intercompany-client/",
            "/ggv-intercompany-client.html",
            "/dashboards/ggv-intercompany-client.html",
        ):
            self._ggv_ic_page()
            return
        elif path in (
            "/bzg-venue-pnl",
            "/bzg-venue-pnl/",
            "/bzg-venue-pnl.html",
            "/dashboards/bzg-venue-pnl.html",
        ):
            self._bzg_pnl_page()
            return
        elif path in (
            "/bzg-variance-waste",
            "/bzg-variance-waste/",
            "/bzg-variance-waste.html",
            "/dashboards/bzg-variance-waste.html",
        ):
            self._bzg_var_page()
            return
        elif path in (
            "/bzg-allocation-engine",
            "/bzg-allocation-engine/",
            "/bzg-allocation-engine.html",
            "/dashboards/bzg-allocation-engine.html",
        ):
            self._bzg_alloc_page()
            return
        elif path in (
            "/bzg-bom-yield",
            "/bzg-bom-yield/",
            "/bzg-bom-yield.html",
            "/dashboards/bzg-bom-yield.html",
        ):
            self._bzg_bom_page()
            return
        elif path in (
            "/amg-service-improve",
            "/amg-service-improve/",
            "/amg-service-improve.html",
            "/dashboards/amg-service-improve.html",
        ):
            self._amg_improve_page()
            return
        elif path in (
            "/amg-sla-incident",
            "/amg-sla-incident/",
            "/amg-sla-incident.html",
            "/dashboards/amg-sla-incident.html",
        ):
            self._amg_sla_page()
            return
        elif path in (
            "/amg-pms-orchestration",
            "/amg-pms-orchestration/",
            "/amg-pms-orchestration.html",
            "/dashboards/amg-pms-orchestration.html",
        ):
            self._amg_pms_page()
            return
        elif path in (
            "/hr-hiring-onboarding",
            "/hr-hiring-onboarding/",
            "/hr-hiring-onboarding.html",
            "/dashboards/hr-hiring-onboarding.html",
        ):
            self._hr_hire_page()
            return
        elif path in (
            "/hr-training-competency",
            "/hr-training-competency/",
            "/hr-training-competency.html",
            "/dashboards/hr-training-competency.html",
        ):
            self._hr_train_page()
            return
        elif path in (
            "/hr-payroll-inputs",
            "/hr-payroll-inputs/",
            "/hr-payroll-inputs.html",
            "/dashboards/hr-payroll-inputs.html",
        ):
            self._hr_pay_page()
            return
        elif path in (
            "/hr-retention-signals",
            "/hr-retention-signals/",
            "/hr-retention-signals.html",
            "/dashboards/hr-retention-signals.html",
        ):
            self._hr_ret_page()
            return
        elif path in (
            "/fin-mgmt-reporting",
            "/fin-mgmt-reporting/",
            "/fin-mgmt-reporting.html",
            "/dashboards/fin-mgmt-reporting.html",
        ):
            self._fin_mgmt_page()
            return
        elif path in (
            "/msc-posture",
            "/msc-posture/",
            "/msc-posture.html",
            "/dashboards/msc-posture.html",
        ):
            self._msc_posture_page()
            return
        elif path in (
            "/connector-contract",
            "/connector-contract/",
            "/connector-contract.html",
            "/dashboards/connector-contract.html",
        ):
            self._intg_contract_page()
            return
        elif path in (
            "/connector-cap-tests",
            "/connector-cap-tests/",
            "/connector-cap-tests.html",
            "/dashboards/connector-cap-tests.html",
        ):
            self._intg_cap_tests_page()
            return
        elif path in (
            "/crm-lead-cap-prove",
            "/crm-lead-cap-prove/",
            "/crm-lead-cap-prove.html",
            "/dashboards/crm-lead-cap-prove.html",
        ):
            self._crm_lead_prove_page()
            return
        elif path in (
            "/radar-prove",
            "/radar-prove/",
            "/radar-prove.html",
            "/dashboards/radar-prove.html",
        ):
            self._strat_radar_page()
            return
        elif path in (
            "/speed-to-lead-prove",
            "/speed-to-lead-prove/",
            "/speed-to-lead-prove.html",
            "/dashboards/speed-to-lead-prove.html",
        ):
            self._ggv_speed_page()
            return
        elif path in (
            "/bzg-reputation",
            "/bzg-reputation/",
            "/bzg-reputation.html",
            "/dashboards/bzg-reputation.html",
        ):
            self._bzg_reputation_page()
            return
        elif path in (
            "/ggv-social",
            "/ggv-social/",
            "/ggv-social.html",
            "/dashboards/ggv-social.html",
        ):
            self._ggv_social_page()
            return
        elif path in (
            "/crm-identity",
            "/crm-identity/",
            "/crm-identity.html",
            "/dashboards/crm-identity.html",
        ):
            self._crm_identity_page()
            return
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
        if path == "/api/integration-health":
            self._integration_health_write_refused()
            return
        if path == "/api/tech-registry" or path.startswith("/api/tech-registry/"):
            self._tech_registry_write_refused()
            return
        if path == "/api/strat/12wy-prove":
            self._strat_12wy_write_refused()
            return
        if path == "/api/core/escalation-burndown" or path.startswith("/api/core/escalation-burndown/"):
            self._escalation_burndown_write_refused()
            return
        if path == "/api/sale-evidence-pack" or path.startswith("/api/sale-evidence-pack/") or self._sale_pack_export_code(path):
            self._sale_pack_write_refused(path)
            return
        if path == "/api/buyer-dataroom" or path.startswith("/api/buyer-dataroom/") or self._buyer_room_refuse_code(path):
            self._buyer_room_write_refused(path)
            return
        if path == "/api/buyer-mode" or (path.startswith("/api/buyer-mode/") and not self._sale_pack_export_code(path)):
            self._buyer_mode_write_refused(path)
            return
        if path == "/api/attack-audit" or path.startswith("/api/attack-audit/"):
            self._attack_audit_write_refused(path)
            return
        if path == "/api/restore-drill" or path.startswith("/api/restore-drill/"):
            self._restore_drill_write_refused(path)
            return
        if path == "/api/failure-domains" or path.startswith("/api/failure-domains/"):
            self._failure_domains_write_refused(path)
            return
        if path == "/api/crown-jewels" or path.startswith("/api/crown-jewels/"):
            self._crown_jewel_write_refused(path)
            return
        if path == "/api/crm-connector-prove" or path.startswith("/api/crm-connector-prove/"):
            self._crm_connector_write_refused(path)
            return
        if path == "/api/gws-integrate-prove" or path.startswith("/api/gws-integrate-prove/"):
            self._gws_prove_write_refused(path)
            return
        if path == "/api/crm/lead-cap-prove" or path.startswith("/api/crm/lead-cap-prove/"):
            self._crm_lead_prove_write_refused(path)
            return
        if path == "/api/strat/radar-prove" or path.startswith("/api/strat/radar-prove/"):
            self._strat_radar_write_refused(path)
            return
        if path == "/api/ggv/speed-to-lead-prove" or path.startswith("/api/ggv/speed-to-lead-prove/"):
            self._ggv_speed_write_refused(path)
            return
        if self._pkg_intel_refuse_code(path):
            self._pkg_intel_write_refused(path)
            return
        if path == "/api/crm/package-intel/register":
            self._pkg_intel_register()
            return
        if path == "/api/crm/package-intel" or path.startswith("/api/crm/package-intel/"):
            self._pkg_intel_write_refused(path)
            return
        if self._msc_assets_refuse_code(path):
            self._msc_assets_write_refused(path)
            return
        if path == "/api/msc/assets/register":
            self._msc_assets_register()
            return
        if path == "/api/msc/assets" or path.startswith("/api/msc/assets/"):
            self._msc_assets_write_refused(path)
            return
        if self._msc_compliance_refuse_code(path):
            self._msc_compliance_write_refused(path)
            return
        if path == "/api/msc/compliance" or path.startswith("/api/msc/compliance/"):
            self._msc_compliance_write_refused(path)
            return
        if self._msc_cyber_refuse_code(path):
            self._msc_cyber_write_refused(path)
            return
        if path == "/api/msc/cyber" or path.startswith("/api/msc/cyber/"):
            self._msc_cyber_write_refused(path)
            return
        if self._msc_records_refuse_code(path):
            self._msc_records_write_refused(path)
            return
        if path == "/api/msc/records" or path.startswith("/api/msc/records/"):
            self._msc_records_write_refused(path)
            return
        if self._intg_secrets_refuse_code(path):
            self._intg_secrets_write_refused(path)
            return
        if path == "/api/intg/secrets" or path.startswith("/api/intg/secrets/"):
            self._intg_secrets_write_refused(path)
            return
        if self._ggv_pnl_refuse_code(path):
            self._ggv_pnl_write_refused(path)
            return
        if path == "/api/ggv/client-profitability" or path.startswith("/api/ggv/client-profitability/"):
            self._ggv_pnl_write_refused(path)
            return
        if self._ggv_strategy_refuse_code(path):
            self._ggv_strategy_write_refused(path)
            return
        if path == "/api/ggv/strategy-machine" or path.startswith("/api/ggv/strategy-machine/"):
            self._ggv_strategy_write_refused(path)
            return
        if self._amg_journey_refuse_code(path):
            self._amg_journey_write_refused(path)
            return
        if path == "/api/amg/journey-workflow" or path.startswith("/api/amg/journey-workflow/"):
            self._amg_journey_write_refused(path)
            return
        if self._amg_ops_refuse_code(path):
            self._amg_ops_write_refused(path)
            return
        if path == "/api/amg/daily-ops-state" or path.startswith("/api/amg/daily-ops-state/"):
            self._amg_ops_write_refused(path)
            return
        if self._amg_packages_refuse_code(path):
            self._amg_packages_write_refused(path)
            return
        if path == "/api/amg/packages-products" or path.startswith("/api/amg/packages-products/"):
            self._amg_packages_write_refused(path)
            return
        if self._amg_yield_refuse_code(path):
            self._amg_yield_write_refused(path)
            return
        if path == "/api/amg/revenue-yield" or path.startswith("/api/amg/revenue-yield/"):
            self._amg_yield_write_refused(path)
            return
        if self._ggv_ic_refuse_code(path):
            self._ggv_ic_write_refused(path)
            return
        if path == "/api/ggv/intercompany-client" or path.startswith("/api/ggv/intercompany-client/"):
            self._ggv_ic_write_refused(path)
            return
        if self._bzg_pnl_refuse_code(path):
            self._bzg_pnl_write_refused(path)
            return
        if path == "/api/bzg/venue-pnl" or path.startswith("/api/bzg/venue-pnl/"):
            self._bzg_pnl_write_refused(path)
            return
        if self._bzg_var_refuse_code(path):
            self._bzg_var_write_refused(path)
            return
        if path == "/api/bzg/variance-waste" or path.startswith("/api/bzg/variance-waste/"):
            self._bzg_var_write_refused(path)
            return
        if self._bzg_alloc_refuse_code(path):
            self._bzg_alloc_write_refused(path)
            return
        if path == "/api/bzg/allocation-engine" or path.startswith("/api/bzg/allocation-engine/"):
            self._bzg_alloc_write_refused(path)
            return
        if self._bzg_bom_refuse_code(path):
            self._bzg_bom_write_refused(path)
            return
        if path == "/api/bzg/bom-yield" or path.startswith("/api/bzg/bom-yield/"):
            self._bzg_bom_write_refused(path)
            return
        if self._amg_improve_refuse_code(path):
            self._amg_improve_write_refused(path)
            return
        if path == "/api/amg/service-improve" or path.startswith("/api/amg/service-improve/"):
            self._amg_improve_write_refused(path)
            return
        if self._amg_sla_refuse_code(path):
            self._amg_sla_write_refused(path)
            return
        if path == "/api/amg/sla-incident" or path.startswith("/api/amg/sla-incident/"):
            self._amg_sla_write_refused(path)
            return
        if self._amg_pms_refuse_code(path):
            self._amg_pms_write_refused(path)
            return
        if path == "/api/amg/pms-orchestration" or path.startswith("/api/amg/pms-orchestration/"):
            self._amg_pms_write_refused(path)
            return
        if self._hr_hire_refuse_code(path):
            self._hr_hire_write_refused(path)
            return
        if path == "/api/hr/hiring-onboarding" or path.startswith("/api/hr/hiring-onboarding/"):
            self._hr_hire_write_refused(path)
            return
        if self._hr_train_refuse_code(path):
            self._hr_train_write_refused(path)
            return
        if path == "/api/hr/training-competency" or path.startswith("/api/hr/training-competency/"):
            self._hr_train_write_refused(path)
            return
        if self._hr_pay_refuse_code(path):
            self._hr_pay_write_refused(path)
            return
        if path == "/api/hr/payroll-inputs" or path.startswith("/api/hr/payroll-inputs/"):
            self._hr_pay_write_refused(path)
            return
        if self._hr_ret_refuse_code(path):
            self._hr_ret_write_refused(path)
            return
        if path == "/api/hr/retention-signals" or path.startswith("/api/hr/retention-signals/"):
            self._hr_ret_write_refused(path)
            return
        if self._fin_mgmt_refuse_code(path):
            self._fin_mgmt_write_refused(path)
            return
        if path == "/api/fin/mgmt-reporting" or path.startswith("/api/fin/mgmt-reporting/"):
            self._fin_mgmt_write_refused(path)
            return
        if self._msc_posture_refuse_code(path):
            self._msc_posture_write_refused(path)
            return
        if path == "/api/msc/posture" or path.startswith("/api/msc/posture/"):
            self._msc_posture_write_refused(path)
            return
        if self._intg_contract_refuse_code(path):
            self._intg_contract_write_refused(path)
            return
        if path == "/api/intg/connector-contract" or path.startswith("/api/intg/connector-contract/"):
            self._intg_contract_write_refused(path)
            return
        if self._intg_cap_tests_refuse_code(path):
            self._intg_cap_tests_write_refused(path)
            return
        if path == "/api/intg/connector-cap-tests" or path.startswith("/api/intg/connector-cap-tests/"):
            self._intg_cap_tests_write_refused(path)
            return
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

        if path == "/api/sop/draft":
            self._sop_draft_post()
            return
        if path == "/api/sop/version":
            self._sop_version_post()
            return
        if path == "/api/sop/approve":
            self._sop_approve_post()
            return
        if self._bzg_reputation_scrape(path):
            self._bzg_reputation_scrape_refused()
            return
        if self._bzg_reputation_reply(path):
            self._bzg_reputation_reply_refused()
            return
        if path == "/api/bzg/reputation/observe":
            self._bzg_reputation_post("observe", _bzg_rep.record_observation)
            return
        if path in {"/api/bzg/reputation", "/api/bzg/reputation/observations"}:
            self._bzg_reputation_summary_refused()
            return
        if self._ggv_social_metricool(path):
            self._ggv_social_metricool_refused()
            return
        if self._ggv_social_ads(path):
            self._ggv_social_ads_refused()
            return
        if path in {"/api/ggv/social", "/api/ggv/social/derive"} or path.startswith("/api/ggv/social/"):
            self._ggv_social_post()
            return
        if self._crm_identity_blast(path):
            self._crm_identity_blast_refused()
            return
        if path == "/api/crm/identity":
            self._crm_identity_post("register", _crm_ident.register_customer)
            return
        if path == "/api/crm/identity/note":
            self._crm_identity_post("note", _crm_ident.append_note)
            return
        if path == "/api/crm/identity/link":
            self._crm_identity_post("link", _crm_ident.propose_link)
            return
        if path == "/api/crm/identity/merge":
            self._crm_identity_post("merge", _crm_ident.merge_people)
            return

        if path == "/api/intel/eval-cost":
            self._intel_eval_cost_post()
            return
        if self._intel_rule_handled(path, "POST"):
            return

        self._send_err(404, "not found")

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        if self._intel_rule_handled(path, "PATCH"):
            return
        if path == "/api/tech-registry" or path.startswith("/api/tech-registry/"):
            self._tech_registry_write_refused()
            return
        if path == "/api/strat/12wy-prove":
            self._strat_12wy_write_refused()
            return
        if path == "/api/core/escalation-burndown" or path.startswith("/api/core/escalation-burndown/"):
            self._escalation_burndown_write_refused()
            return
        if path == "/api/sale-evidence-pack" or path.startswith("/api/sale-evidence-pack/") or self._sale_pack_export_code(path):
            self._sale_pack_write_refused(path)
            return
        if path == "/api/buyer-dataroom" or path.startswith("/api/buyer-dataroom/") or self._buyer_room_refuse_code(path):
            self._buyer_room_write_refused(path)
            return
        if path == "/api/buyer-mode" or (path.startswith("/api/buyer-mode/") and not self._sale_pack_export_code(path)):
            self._buyer_mode_write_refused(path)
            return
        if path == "/api/attack-audit" or path.startswith("/api/attack-audit/"):
            self._attack_audit_write_refused(path)
            return
        if path == "/api/restore-drill" or path.startswith("/api/restore-drill/"):
            self._restore_drill_write_refused(path)
            return
        if path == "/api/failure-domains" or path.startswith("/api/failure-domains/"):
            self._failure_domains_write_refused(path)
            return
        if path == "/api/crown-jewels" or path.startswith("/api/crown-jewels/"):
            self._crown_jewel_write_refused(path)
            return
        if path == "/api/crm-connector-prove" or path.startswith("/api/crm-connector-prove/"):
            self._crm_connector_write_refused(path)
            return
        if path == "/api/gws-integrate-prove" or path.startswith("/api/gws-integrate-prove/"):
            self._gws_prove_write_refused(path)
            return
        if path == "/api/crm/lead-cap-prove" or path.startswith("/api/crm/lead-cap-prove/"):
            self._crm_lead_prove_write_refused(path)
            return
        if path == "/api/strat/radar-prove" or path.startswith("/api/strat/radar-prove/"):
            self._strat_radar_write_refused(path)
            return
        if path == "/api/ggv/speed-to-lead-prove" or path.startswith("/api/ggv/speed-to-lead-prove/"):
            self._ggv_speed_write_refused(path)
            return
        if self._crm_identity_blast(path) or path == "/api/crm/identity" or path.startswith("/api/crm/identity/"):
            self._crm_identity_append_only_refused()
            return
        if path == "/api/bzg/reputation" or path.startswith("/api/bzg/reputation/"):
            self._bzg_reputation_append_only_refused()
            return
        if path == "/api/ggv/social" or path.startswith("/api/ggv/social/"):
            self._ggv_social_write_refused(path)
            return
        if self._pkg_intel_refuse_code(path):
            self._pkg_intel_write_refused(path)
            return
        if path == "/api/crm/package-intel" or path.startswith("/api/crm/package-intel/"):
            self._pkg_intel_write_refused(path)
            return
        if self._msc_assets_refuse_code(path):
            self._msc_assets_write_refused(path)
            return
        if path == "/api/msc/assets" or path.startswith("/api/msc/assets/"):
            self._msc_assets_write_refused(path)
            return
        if self._msc_compliance_refuse_code(path):
            self._msc_compliance_write_refused(path)
            return
        if path == "/api/msc/compliance" or path.startswith("/api/msc/compliance/"):
            self._msc_compliance_write_refused(path)
            return
        if self._msc_cyber_refuse_code(path):
            self._msc_cyber_write_refused(path)
            return
        if path == "/api/msc/cyber" or path.startswith("/api/msc/cyber/"):
            self._msc_cyber_write_refused(path)
            return
        if self._msc_records_refuse_code(path):
            self._msc_records_write_refused(path)
            return
        if path == "/api/msc/records" or path.startswith("/api/msc/records/"):
            self._msc_records_write_refused(path)
            return
        if self._intg_secrets_refuse_code(path):
            self._intg_secrets_write_refused(path)
            return
        if path == "/api/intg/secrets" or path.startswith("/api/intg/secrets/"):
            self._intg_secrets_write_refused(path)
            return
        if self._ggv_pnl_refuse_code(path):
            self._ggv_pnl_write_refused(path)
            return
        if path == "/api/ggv/client-profitability" or path.startswith("/api/ggv/client-profitability/"):
            self._ggv_pnl_write_refused(path)
            return
        if self._ggv_strategy_refuse_code(path):
            self._ggv_strategy_write_refused(path)
            return
        if path == "/api/ggv/strategy-machine" or path.startswith("/api/ggv/strategy-machine/"):
            self._ggv_strategy_write_refused(path)
            return
        if self._amg_journey_refuse_code(path):
            self._amg_journey_write_refused(path)
            return
        if path == "/api/amg/journey-workflow" or path.startswith("/api/amg/journey-workflow/"):
            self._amg_journey_write_refused(path)
            return
        if self._amg_ops_refuse_code(path):
            self._amg_ops_write_refused(path)
            return
        if path == "/api/amg/daily-ops-state" or path.startswith("/api/amg/daily-ops-state/"):
            self._amg_ops_write_refused(path)
            return
        if self._amg_packages_refuse_code(path):
            self._amg_packages_write_refused(path)
            return
        if path == "/api/amg/packages-products" or path.startswith("/api/amg/packages-products/"):
            self._amg_packages_write_refused(path)
            return
        if self._amg_yield_refuse_code(path):
            self._amg_yield_write_refused(path)
            return
        if path == "/api/amg/revenue-yield" or path.startswith("/api/amg/revenue-yield/"):
            self._amg_yield_write_refused(path)
            return
        if self._ggv_ic_refuse_code(path):
            self._ggv_ic_write_refused(path)
            return
        if path == "/api/ggv/intercompany-client" or path.startswith("/api/ggv/intercompany-client/"):
            self._ggv_ic_write_refused(path)
            return
        if self._bzg_pnl_refuse_code(path):
            self._bzg_pnl_write_refused(path)
            return
        if path == "/api/bzg/venue-pnl" or path.startswith("/api/bzg/venue-pnl/"):
            self._bzg_pnl_write_refused(path)
            return
        if self._bzg_var_refuse_code(path):
            self._bzg_var_write_refused(path)
            return
        if path == "/api/bzg/variance-waste" or path.startswith("/api/bzg/variance-waste/"):
            self._bzg_var_write_refused(path)
            return
        if self._bzg_alloc_refuse_code(path):
            self._bzg_alloc_write_refused(path)
            return
        if path == "/api/bzg/allocation-engine" or path.startswith("/api/bzg/allocation-engine/"):
            self._bzg_alloc_write_refused(path)
            return
        if self._bzg_bom_refuse_code(path):
            self._bzg_bom_write_refused(path)
            return
        if path == "/api/bzg/bom-yield" or path.startswith("/api/bzg/bom-yield/"):
            self._bzg_bom_write_refused(path)
            return
        if self._amg_improve_refuse_code(path):
            self._amg_improve_write_refused(path)
            return
        if path == "/api/amg/service-improve" or path.startswith("/api/amg/service-improve/"):
            self._amg_improve_write_refused(path)
            return
        if self._amg_sla_refuse_code(path):
            self._amg_sla_write_refused(path)
            return
        if path == "/api/amg/sla-incident" or path.startswith("/api/amg/sla-incident/"):
            self._amg_sla_write_refused(path)
            return
        if self._amg_pms_refuse_code(path):
            self._amg_pms_write_refused(path)
            return
        if path == "/api/amg/pms-orchestration" or path.startswith("/api/amg/pms-orchestration/"):
            self._amg_pms_write_refused(path)
            return
        if self._hr_hire_refuse_code(path):
            self._hr_hire_write_refused(path)
            return
        if path == "/api/hr/hiring-onboarding" or path.startswith("/api/hr/hiring-onboarding/"):
            self._hr_hire_write_refused(path)
            return
        if self._hr_train_refuse_code(path):
            self._hr_train_write_refused(path)
            return
        if path == "/api/hr/training-competency" or path.startswith("/api/hr/training-competency/"):
            self._hr_train_write_refused(path)
            return
        if self._hr_pay_refuse_code(path):
            self._hr_pay_write_refused(path)
            return
        if path == "/api/hr/payroll-inputs" or path.startswith("/api/hr/payroll-inputs/"):
            self._hr_pay_write_refused(path)
            return
        if self._hr_ret_refuse_code(path):
            self._hr_ret_write_refused(path)
            return
        if path == "/api/hr/retention-signals" or path.startswith("/api/hr/retention-signals/"):
            self._hr_ret_write_refused(path)
            return
        if self._fin_mgmt_refuse_code(path):
            self._fin_mgmt_write_refused(path)
            return
        if path == "/api/fin/mgmt-reporting" or path.startswith("/api/fin/mgmt-reporting/"):
            self._fin_mgmt_write_refused(path)
            return
        if self._msc_posture_refuse_code(path):
            self._msc_posture_write_refused(path)
            return
        if path == "/api/msc/posture" or path.startswith("/api/msc/posture/"):
            self._msc_posture_write_refused(path)
            return
        if self._intg_contract_refuse_code(path):
            self._intg_contract_write_refused(path)
            return
        if path == "/api/intg/connector-contract" or path.startswith("/api/intg/connector-contract/"):
            self._intg_contract_write_refused(path)
            return
        if self._intg_cap_tests_refuse_code(path):
            self._intg_cap_tests_write_refused(path)
            return
        if path == "/api/intg/connector-cap-tests" or path.startswith("/api/intg/connector-cap-tests/"):
            self._intg_cap_tests_write_refused(path)
            return
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
        path = urlparse(self.path).path
        if self._intel_rule_handled(path, "PUT"):
            return
        if path == "/api/tech-registry" or path.startswith("/api/tech-registry/"):
            self._tech_registry_write_refused()
            return
        if path == "/api/strat/12wy-prove":
            self._strat_12wy_write_refused()
            return
        if path == "/api/core/escalation-burndown" or path.startswith("/api/core/escalation-burndown/"):
            self._escalation_burndown_write_refused()
            return
        if path == "/api/sale-evidence-pack" or path.startswith("/api/sale-evidence-pack/") or self._sale_pack_export_code(path):
            self._sale_pack_write_refused(path)
            return
        if path == "/api/buyer-dataroom" or path.startswith("/api/buyer-dataroom/") or self._buyer_room_refuse_code(path):
            self._buyer_room_write_refused(path)
            return
        if path == "/api/buyer-mode" or (path.startswith("/api/buyer-mode/") and not self._sale_pack_export_code(path)):
            self._buyer_mode_write_refused(path)
            return
        if path == "/api/attack-audit" or path.startswith("/api/attack-audit/"):
            self._attack_audit_write_refused(path)
            return
        if path == "/api/restore-drill" or path.startswith("/api/restore-drill/"):
            self._restore_drill_write_refused(path)
            return
        if path == "/api/failure-domains" or path.startswith("/api/failure-domains/"):
            self._failure_domains_write_refused(path)
            return
        if path == "/api/crown-jewels" or path.startswith("/api/crown-jewels/"):
            self._crown_jewel_write_refused(path)
            return
        if path == "/api/crm-connector-prove" or path.startswith("/api/crm-connector-prove/"):
            self._crm_connector_write_refused(path)
            return
        if path == "/api/gws-integrate-prove" or path.startswith("/api/gws-integrate-prove/"):
            self._gws_prove_write_refused(path)
            return
        if path == "/api/crm/lead-cap-prove" or path.startswith("/api/crm/lead-cap-prove/"):
            self._crm_lead_prove_write_refused(path)
            return
        if path == "/api/strat/radar-prove" or path.startswith("/api/strat/radar-prove/"):
            self._strat_radar_write_refused(path)
            return
        if path == "/api/ggv/speed-to-lead-prove" or path.startswith("/api/ggv/speed-to-lead-prove/"):
            self._ggv_speed_write_refused(path)
            return
        if self._crm_identity_blast(path) or path == "/api/crm/identity" or path.startswith("/api/crm/identity/"):
            self._crm_identity_append_only_refused()
            return
        if path == "/api/bzg/reputation" or path.startswith("/api/bzg/reputation/"):
            self._bzg_reputation_append_only_refused()
            return
        if path == "/api/ggv/social" or path.startswith("/api/ggv/social/"):
            self._ggv_social_write_refused(path)
            return
        if self._pkg_intel_refuse_code(path):
            self._pkg_intel_write_refused(path)
            return
        if path == "/api/crm/package-intel" or path.startswith("/api/crm/package-intel/"):
            self._pkg_intel_write_refused(path)
            return
        if self._msc_assets_refuse_code(path):
            self._msc_assets_write_refused(path)
            return
        if path == "/api/msc/assets" or path.startswith("/api/msc/assets/"):
            self._msc_assets_write_refused(path)
            return
        if self._msc_compliance_refuse_code(path):
            self._msc_compliance_write_refused(path)
            return
        if path == "/api/msc/compliance" or path.startswith("/api/msc/compliance/"):
            self._msc_compliance_write_refused(path)
            return
        if self._msc_cyber_refuse_code(path):
            self._msc_cyber_write_refused(path)
            return
        if path == "/api/msc/cyber" or path.startswith("/api/msc/cyber/"):
            self._msc_cyber_write_refused(path)
            return
        if self._msc_records_refuse_code(path):
            self._msc_records_write_refused(path)
            return
        if path == "/api/msc/records" or path.startswith("/api/msc/records/"):
            self._msc_records_write_refused(path)
            return
        if self._intg_secrets_refuse_code(path):
            self._intg_secrets_write_refused(path)
            return
        if path == "/api/intg/secrets" or path.startswith("/api/intg/secrets/"):
            self._intg_secrets_write_refused(path)
            return
        if self._ggv_pnl_refuse_code(path):
            self._ggv_pnl_write_refused(path)
            return
        if path == "/api/ggv/client-profitability" or path.startswith("/api/ggv/client-profitability/"):
            self._ggv_pnl_write_refused(path)
            return
        if self._ggv_strategy_refuse_code(path):
            self._ggv_strategy_write_refused(path)
            return
        if path == "/api/ggv/strategy-machine" or path.startswith("/api/ggv/strategy-machine/"):
            self._ggv_strategy_write_refused(path)
            return
        if self._amg_journey_refuse_code(path):
            self._amg_journey_write_refused(path)
            return
        if path == "/api/amg/journey-workflow" or path.startswith("/api/amg/journey-workflow/"):
            self._amg_journey_write_refused(path)
            return
        if self._amg_ops_refuse_code(path):
            self._amg_ops_write_refused(path)
            return
        if path == "/api/amg/daily-ops-state" or path.startswith("/api/amg/daily-ops-state/"):
            self._amg_ops_write_refused(path)
            return
        if self._amg_packages_refuse_code(path):
            self._amg_packages_write_refused(path)
            return
        if path == "/api/amg/packages-products" or path.startswith("/api/amg/packages-products/"):
            self._amg_packages_write_refused(path)
            return
        if self._amg_yield_refuse_code(path):
            self._amg_yield_write_refused(path)
            return
        if path == "/api/amg/revenue-yield" or path.startswith("/api/amg/revenue-yield/"):
            self._amg_yield_write_refused(path)
            return
        if self._ggv_ic_refuse_code(path):
            self._ggv_ic_write_refused(path)
            return
        if path == "/api/ggv/intercompany-client" or path.startswith("/api/ggv/intercompany-client/"):
            self._ggv_ic_write_refused(path)
            return
        if self._bzg_pnl_refuse_code(path):
            self._bzg_pnl_write_refused(path)
            return
        if path == "/api/bzg/venue-pnl" or path.startswith("/api/bzg/venue-pnl/"):
            self._bzg_pnl_write_refused(path)
            return
        if self._bzg_var_refuse_code(path):
            self._bzg_var_write_refused(path)
            return
        if path == "/api/bzg/variance-waste" or path.startswith("/api/bzg/variance-waste/"):
            self._bzg_var_write_refused(path)
            return
        if self._bzg_alloc_refuse_code(path):
            self._bzg_alloc_write_refused(path)
            return
        if path == "/api/bzg/allocation-engine" or path.startswith("/api/bzg/allocation-engine/"):
            self._bzg_alloc_write_refused(path)
            return
        if self._bzg_bom_refuse_code(path):
            self._bzg_bom_write_refused(path)
            return
        if path == "/api/bzg/bom-yield" or path.startswith("/api/bzg/bom-yield/"):
            self._bzg_bom_write_refused(path)
            return
        if self._amg_improve_refuse_code(path):
            self._amg_improve_write_refused(path)
            return
        if path == "/api/amg/service-improve" or path.startswith("/api/amg/service-improve/"):
            self._amg_improve_write_refused(path)
            return
        if self._amg_sla_refuse_code(path):
            self._amg_sla_write_refused(path)
            return
        if path == "/api/amg/sla-incident" or path.startswith("/api/amg/sla-incident/"):
            self._amg_sla_write_refused(path)
            return
        if self._amg_pms_refuse_code(path):
            self._amg_pms_write_refused(path)
            return
        if path == "/api/amg/pms-orchestration" or path.startswith("/api/amg/pms-orchestration/"):
            self._amg_pms_write_refused(path)
            return
        if self._hr_hire_refuse_code(path):
            self._hr_hire_write_refused(path)
            return
        if path == "/api/hr/hiring-onboarding" or path.startswith("/api/hr/hiring-onboarding/"):
            self._hr_hire_write_refused(path)
            return
        if self._hr_train_refuse_code(path):
            self._hr_train_write_refused(path)
            return
        if path == "/api/hr/training-competency" or path.startswith("/api/hr/training-competency/"):
            self._hr_train_write_refused(path)
            return
        if self._hr_pay_refuse_code(path):
            self._hr_pay_write_refused(path)
            return
        if path == "/api/hr/payroll-inputs" or path.startswith("/api/hr/payroll-inputs/"):
            self._hr_pay_write_refused(path)
            return
        if self._hr_ret_refuse_code(path):
            self._hr_ret_write_refused(path)
            return
        if path == "/api/hr/retention-signals" or path.startswith("/api/hr/retention-signals/"):
            self._hr_ret_write_refused(path)
            return
        if self._fin_mgmt_refuse_code(path):
            self._fin_mgmt_write_refused(path)
            return
        if path == "/api/fin/mgmt-reporting" or path.startswith("/api/fin/mgmt-reporting/"):
            self._fin_mgmt_write_refused(path)
            return
        if self._msc_posture_refuse_code(path):
            self._msc_posture_write_refused(path)
            return
        if path == "/api/msc/posture" or path.startswith("/api/msc/posture/"):
            self._msc_posture_write_refused(path)
            return
        if self._intg_contract_refuse_code(path):
            self._intg_contract_write_refused(path)
            return
        if path == "/api/intg/connector-contract" or path.startswith("/api/intg/connector-contract/"):
            self._intg_contract_write_refused(path)
            return
        if self._intg_cap_tests_refuse_code(path):
            self._intg_cap_tests_write_refused(path)
            return
        if path == "/api/intg/connector-cap-tests" or path.startswith("/api/intg/connector-cap-tests/"):
            self._intg_cap_tests_write_refused(path)
            return
        # Legacy whole-plan PUT no longer supported as bulk replace;
        # accept single-slot body via save semantics for compat.
        if path == "/api/planner":
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

    def _require_integration_health_owner(self, body: dict | None = None) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as Progress."""
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
                    "message": "Integration Health is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        return identity

    def _integration_health_page(self) -> None:
        identity = self._require_integration_health_owner()
        if identity is None:
            return
        page = DASHBOARDS / "integration-health.html"
        if not page.is_file():
            self._send_json(
                {"ok": False, "error": "page_missing", "message": "Integration Health page is missing."},
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _integration_health_get(self) -> None:
        identity = self._require_integration_health_owner()
        if identity is None:
            return
        try:
            report = _integration_health.build_report()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _integration_health_write_refused(self) -> None:
        identity = self._require_integration_health_owner()
        if identity is None:
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Integration Health is read-only. No external writes.",
                "external_writes": False,
                "ledger_write": False,
            },
            status=405,
        )

    def _require_tech_registry_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as Integration Health."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Tech registry is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        return identity

    def _tech_registry_page(self) -> None:
        identity = self._require_tech_registry_owner()
        if identity is None:
            return
        page = DASHBOARDS / "tech-registry.html"
        if not page.is_file():
            self._send_json(
                {"ok": False, "error": "page_missing", "message": "Tech registry page is missing."},
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _tech_registry_get(self, qs: dict, entry_id: str | None = None) -> None:
        identity = self._require_tech_registry_owner()
        if identity is None:
            return
        kind = (qs.get("kind") or [""])[0].strip().lower() or None
        try:
            if entry_id:
                report = _tech_registry.read_entry(entry_id, kind=kind)
            else:
                report = _tech_registry.build_registry(kind=kind)
        except _tech_registry.RegistryError as exc:
            status = 404 if exc.code == "not_found" else 400
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _tech_registry_write_refused(self) -> None:
        identity = self._require_tech_registry_owner()
        if identity is None:
            return
        try:
            _tech_registry.refuse_external_write({})
        except _tech_registry.RegistryError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Tech registry is read-only. No external writes.",
                "external_writes": False,
                "ledger_write": False,
            },
            status=405,
        )

    def _require_strat_12wy_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the tech registry."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "12WY prove is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        return identity

    def _strat_12wy_page(self) -> None:
        identity = self._require_strat_12wy_owner()
        if identity is None:
            return
        page = DASHBOARDS / "12wy-prove.html"
        if not page.is_file():
            self._send_json(
                {"ok": False, "error": "page_missing", "message": "12WY prove page is missing."},
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _strat_12wy_prove(self) -> None:
        identity = self._require_strat_12wy_owner()
        if identity is None:
            return
        try:
            report = _strat_12wy.build_prove()
        except _strat_12wy.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=400,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _strat_12wy_write_refused(self) -> None:
        identity = self._require_strat_12wy_owner()
        if identity is None:
            return
        try:
            _strat_12wy.refuse_external_write({})
        except _strat_12wy.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    **_strat_12wy.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "12WY prove pack is read-only.",
                "external_writes": False,
                "ledger_write": False,
            },
            status=405,
        )

    def _require_crm_lead_prove_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the 12WY prove."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Lead CAP prove is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        return identity

    def _crm_lead_prove_page(self) -> None:
        identity = self._require_crm_lead_prove_owner()
        if identity is None:
            return
        page = DASHBOARDS / "crm-lead-cap-prove.html"
        if not page.is_file():
            self._send_json(
                {"ok": False, "error": "page_missing", "message": "Lead CAP prove page is missing."},
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _crm_lead_prove_get(self) -> None:
        identity = self._require_crm_lead_prove_owner()
        if identity is None:
            return
        try:
            report = _crm_lead_prove.build_prove()
        except _crm_lead_prove.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=400,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _crm_lead_prove_hint(self, path: str) -> dict:
        if path.endswith("/klaviyo"):
            return {"klaviyo": True}
        if path.endswith("/metricool"):
            return {"metricool": True}
        if path.endswith("/leads"):
            return {"invent_lead": True}
        return {}

    def _crm_lead_prove_write_refused(self, path: str) -> None:
        identity = self._require_crm_lead_prove_owner()
        if identity is None:
            return
        try:
            _crm_lead_prove.refuse_external_write(self._crm_lead_prove_hint(path))
        except _crm_lead_prove.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "klaviyo_write": False,
                    "metricool_write": False,
                    "invented_leads": False,
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Lead CAP prove is read-only.",
                "external_writes": False,
                "ledger_write": False,
            },
            status=405,
        )

    def _require_strat_radar_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the 12WY prove."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Owner Radar prove is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        return identity

    def _strat_radar_page(self) -> None:
        identity = self._require_strat_radar_owner()
        if identity is None:
            return
        page = DASHBOARDS / "radar-prove.html"
        if not page.is_file():
            self._send_json(
                {"ok": False, "error": "page_missing", "message": "Owner Radar prove page is missing."},
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _strat_radar_prove_get(self) -> None:
        identity = self._require_strat_radar_owner()
        if identity is None:
            return
        try:
            report = _strat_radar.build_prove()
        except _strat_radar.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=400,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _strat_radar_hint(self, path: str) -> dict:
        if path.endswith("/task"):
            return {"create_task": True}
        if path.endswith("/progress"):
            return {"progress": True}
        if path.endswith("/proven"):
            return {"proven": True}
        return {}

    def _strat_radar_write_refused(self, path: str) -> None:
        identity = self._require_strat_radar_owner()
        if identity is None:
            return
        try:
            _strat_radar.refuse_external_write(self._strat_radar_hint(path))
        except _strat_radar.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "create_task": False,
                    "progress_used_as_cap": False,
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Owner Radar prove is read-only.",
                "external_writes": False,
                "ledger_write": False,
            },
            status=405,
        )

    def _require_ggv_speed_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the lead CAP prove."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Speed-to-lead prove is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=403,
            )
            return None
        return identity

    def _ggv_speed_page(self) -> None:
        identity = self._require_ggv_speed_owner()
        if identity is None:
            return
        page = DASHBOARDS / "speed-to-lead-prove.html"
        if not page.is_file():
            self._send_json(
                {"ok": False, "error": "page_missing", "message": "Speed-to-lead prove page is missing."},
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _ggv_speed_prove_get(self) -> None:
        identity = self._require_ggv_speed_owner()
        if identity is None:
            return
        try:
            report = _ggv_speed.build_prove()
        except _ggv_speed.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                },
                status=400,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _ggv_speed_hint(self, path: str) -> dict:
        if path.endswith("/klaviyo"):
            return {"klaviyo": True}
        if path.endswith("/metricool"):
            return {"metricool": True}
        if path.endswith("/activecampaign") or path.endswith("/ac"):
            return {"activecampaign": True}
        if path.endswith("/crm"):
            return {"external_crm": True}
        if path.endswith("/leads"):
            return {"invent_lead": True}
        if path.endswith("/receipts"):
            return {"invent_receipt": True}
        if path.endswith("/proven") or path.endswith("/ready"):
            return {"proven": True}
        return {}

    def _ggv_speed_write_refused(self, path: str) -> None:
        identity = self._require_ggv_speed_owner()
        if identity is None:
            return
        try:
            _ggv_speed.refuse_external_write(self._ggv_speed_hint(path))
        except _ggv_speed.ProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "klaviyo_write": False,
                    "metricool_write": False,
                    "activecampaign_write": False,
                    "invented_leads": False,
                    "invented_receipts": False,
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Speed-to-lead prove is read-only.",
                "external_writes": False,
                "ledger_write": False,
            },
            status=405,
        )

    def _require_burndown_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the 12WY prove."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Escalation burn-down is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "needs_matt_auto_cleared": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "needs_matt_auto_cleared": False,
                },
                status=403,
            )
            return None
        return identity

    def _escalation_burndown_page(self) -> None:
        identity = self._require_burndown_owner()
        if identity is None:
            return
        page = DASHBOARDS / "escalation-burndown.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Escalation burn-down page is missing.",
                    "needs_matt_auto_cleared": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _escalation_burndown_get(self) -> None:
        identity = self._require_burndown_owner()
        if identity is None:
            return
        try:
            report = _burndown.build_report()
        except _burndown.BurndownError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "needs_matt_auto_cleared": False,
                },
                status=400,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _escalation_burndown_write_refused(self) -> None:
        identity = self._require_burndown_owner()
        if identity is None:
            return
        try:
            _burndown.refuse_needs_matt_clear({})
        except _burndown.BurndownError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "needs_matt_auto_cleared": False,
                    **_burndown.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Escalation burn-down is read-only. Needs Matt is not auto-cleared.",
                "external_writes": False,
                "ledger_write": False,
                "needs_matt_auto_cleared": False,
            },
            status=405,
        )

    def _require_sale_pack_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the burn-down."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Sale evidence pack is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "vdr_export": False,
                    "buyer_export": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "vdr_export": False,
                    "buyer_export": False,
                },
                status=403,
            )
            return None
        return identity

    def _sale_pack_export_code(self, path: str) -> str | None:
        if path in {
            "/api/vdr/export",
            "/api/sale-evidence-pack/export",
            "/api/sale-evidence-pack/vdr",
        }:
            return "vdr"
        if path in {
            "/api/buyer-mode/export",
            "/api/buyer/export",
            "/api/sale-evidence-pack/buyer-export",
        }:
            return "buyer"
        return None

    def _sale_pack_page(self) -> None:
        identity = self._require_sale_pack_owner()
        if identity is None:
            return
        page = DASHBOARDS / "sale-evidence-pack.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Sale evidence pack page is missing.",
                    "vdr_export": False,
                    "buyer_export": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _sale_pack_get(self, qs: dict, control_id: str | None = None, domains_only: bool = False) -> None:
        identity = self._require_sale_pack_owner()
        if identity is None:
            return
        export = (qs.get("export") or [""])[0]
        fill = (qs.get("fill") or [""])[0]
        vdr = (qs.get("vdr") or [""])[0]
        entity = (qs.get("entity") or [""])[0] or None
        domain = (qs.get("domain") or [""])[0] or None
        try:
            _sale_pack.guard_query(export=export, fill=fill, vdr=vdr)
            if domains_only:
                full = _sale_pack.build_pack()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "domains": full["domains"],
                    "unmapped": full["unmapped"],
                    "framework_skeleton": full["framework_skeleton"],
                    "vdr_export": False,
                    "buyer_export": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif control_id:
                report = _sale_pack.read_control(control_id)
            else:
                report = _sale_pack.build_pack(entity=entity, domain=domain)
        except _sale_pack.SalePackError as exc:
            status = 404 if exc.code == "not_found" else 400
            if exc.code in {
                "vdr_export_refused",
                "buyer_export_refused",
                "fill_refused",
                "writes_refused",
            }:
                status = 405
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "vdr_export": False,
                    "buyer_export": False,
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "vdr_export": False,
                    "buyer_export": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _sale_pack_write_refused(self, path: str) -> None:
        identity = self._require_sale_pack_owner()
        if identity is None:
            return
        try:
            if self._sale_pack_export_code(path) == "vdr":
                _sale_pack.refuse_vdr_export({})
            elif self._sale_pack_export_code(path) == "buyer":
                _sale_pack.refuse_buyer_export({})
            else:
                _sale_pack.refuse_external_write({})
        except _sale_pack.SalePackError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "vdr_export": False,
                    "buyer_export": False,
                    **_sale_pack.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Sale evidence pack is read-only. No buyer export and no filled evidence.",
                "external_writes": False,
                "ledger_write": False,
                "vdr_export": False,
                "buyer_export": False,
            },
            status=405,
        )

    def _require_buyer_room_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the sale pack."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Buyer data room is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                },
                status=403,
            )
            return None
        return identity

    def _buyer_room_refuse_code(self, path: str) -> str | None:
        if path in {"/api/buyer-dataroom/share", "/api/vdr/share"}:
            return "share"
        if path in {"/api/buyer-dataroom/export", "/api/buyer-dataroom/download"}:
            return "export"
        if path in {"/api/buyer-dataroom/grant", "/api/vdr/grant"}:
            return "grant"
        if path in {"/api/buyer-dataroom/upload", "/api/buyer-dataroom/fill"}:
            return "fill"
        return None

    def _buyer_room_page(self) -> None:
        identity = self._require_buyer_room_owner()
        if identity is None:
            return
        page = DASHBOARDS / "buyer-dataroom.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Buyer data room page is missing.",
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _buyer_room_get(self, qs: dict, folder_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_buyer_room_owner()
        if identity is None:
            return
        export = (qs.get("export") or [""])[0]
        fill = (qs.get("fill") or [""])[0]
        share = (qs.get("share") or [""])[0]
        buyer = (qs.get("buyer") or [""])[0]
        entity = (qs.get("entity") or [""])[0] or None
        folder = (qs.get("folder") or [""])[0] or None
        try:
            _buyer_room.guard_query(export=export, fill=fill, share=share, buyer=buyer)
            if view == "tree":
                full = _buyer_room.build_room(entity=entity, folder=folder)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "tree": full["tree"],
                    "folders": full["folders"],
                    "framework_skeleton": full["framework_skeleton"],
                    "on_disk": False,
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                    "document_count": 0,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "checklist":
                full = _buyer_room.build_room(entity=entity, folder=folder)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "checklist": full["checklist"],
                    "slot_count": full["slot_count"],
                    "empty_slots": full["empty_slots"],
                    "filled_slots": full["filled_slots"],
                    "document_count": 0,
                    "unmapped": full["unmapped"],
                    "framework_skeleton": full["framework_skeleton"],
                    "on_disk": False,
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif folder_id:
                report = _buyer_room.read_folder(folder_id)
            else:
                report = _buyer_room.build_room(entity=entity, folder=folder)
        except _buyer_room.BuyerDataroomError as exc:
            status = 404 if exc.code == "not_found" else 400
            if exc.code in {
                "vdr_share_refused",
                "vdr_export_refused",
                "buyer_access_refused",
                "fill_refused",
                "writes_refused",
            }:
                status = 405
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "on_disk": False,
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "on_disk": False,
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _buyer_room_write_refused(self, path: str) -> None:
        identity = self._require_buyer_room_owner()
        if identity is None:
            return
        code = self._buyer_room_refuse_code(path)
        try:
            if code == "share" or path.endswith("/share"):
                _buyer_room.refuse_share({})
            elif code == "export" or path.endswith("/export") or path.endswith("/download"):
                _buyer_room.refuse_export({})
            elif code == "grant" or path.endswith("/grant"):
                _buyer_room.refuse_buyer_access({})
            elif code == "fill" or path.endswith("/upload") or path.endswith("/fill"):
                _buyer_room.refuse_fill({})
            else:
                _buyer_room.refuse_external_write({})
        except _buyer_room.BuyerDataroomError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "on_disk": False,
                    "buyer_access": False,
                    "live_share": False,
                    "vdr_export": False,
                    **_buyer_room.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Buyer data room is read-only. No share, no export, and no filled document.",
                "external_writes": False,
                "ledger_write": False,
                "on_disk": False,
                "buyer_access": False,
                "live_share": False,
                "vdr_export": False,
            },
            status=405,
        )

    def _require_buyer_mode_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the data room."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Buyer mode is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "buyer_grant": False,
                    "live_share": False,
                    "buyer_export": False,
                    "crown_jewels_opened": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "buyer_grant": False,
                    "live_share": False,
                    "buyer_export": False,
                },
                status=403,
            )
            return None
        return identity

    def _buyer_mode_refuse_code(self, path: str) -> str | None:
        if path in {"/api/buyer-mode/grant", "/api/buyer-mode/access"}:
            return "grant"
        if path in {"/api/buyer-mode/share"}:
            return "share"
        if path in {"/api/buyer-mode/reveal", "/api/buyer-mode/unhide"}:
            return "reveal"
        if path in {"/api/buyer-mode/fill", "/api/buyer-mode/upload"}:
            return "fill"
        if path in {"/api/buyer-mode/blend", "/api/buyer-mode/cross"}:
            return "cross"
        if path in {"/api/buyer-mode/production"}:
            return "production"
        return None

    def _buyer_mode_page(self) -> None:
        identity = self._require_buyer_mode_owner()
        if identity is None:
            return
        page = DASHBOARDS / "buyer-mode.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Buyer mode page is missing.",
                    "buyer_grant": False,
                    "buyer_export": False,
                    "crown_jewels_opened": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _buyer_mode_fail(self, exc: _buyer_mode.BuyerModeError) -> None:
        status = 404 if exc.code == "not_found" else 400
        if exc.code in {
            "buyer_export_refused",
            "buyer_grant_refused",
            "buyer_share_refused",
            "hide_refused",
            "fill_refused",
            "cross_company_refused",
            "writes_refused",
            "production_refused",
        }:
            status = 405
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "external_writes": False,
                "ledger_write": False,
                "on_disk": False,
                "buyer_grant": False,
                "buyer_access": False,
                "live_share": False,
                "buyer_export": False,
                "crown_jewels_opened": False,
                "cross_company_exposed": False,
            },
            status=status,
        )

    def _buyer_mode_get(self, qs: dict, surface_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_buyer_mode_owner()
        if identity is None:
            return
        try:
            _buyer_mode.guard_query(
                export=(qs.get("export") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                share=(qs.get("share") or [""])[0],
                grant=(qs.get("grant") or [""])[0],
                buyer=(qs.get("buyer") or [""])[0],
                reveal=(qs.get("reveal") or [""])[0],
                unhide=(qs.get("unhide") or [""])[0],
                cross=(qs.get("cross") or [""])[0],
                blend=(qs.get("blend") or [""])[0],
                production=(qs.get("production") or [""])[0],
            )
            entity = (qs.get("entity") or [""])[0] or None
            if view == "surfaces":
                full = _buyer_mode.build_mode(entity=entity)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "surfaces": full["surfaces"],
                    "diligence_surfaces": full["diligence_surfaces"],
                    "ask_surfaces": full["ask_surfaces"],
                    "diligence_surface_count": full["diligence_surface_count"],
                    "ask_surface_count": full["ask_surface_count"],
                    "approved_count": full["approved_count"],
                    "framework_skeleton": full["framework_skeleton"],
                    "buyer_grant": False,
                    "buyer_export": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "hides":
                full = _buyer_mode.build_mode(entity=entity)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "hides": full["hides"],
                    "hide_count": full["hide_count"],
                    "hides_default_hidden": full["hides_default_hidden"],
                    "crown_jewels_opened": False,
                    "cross_company_exposed": False,
                    "framework_skeleton": full["framework_skeleton"],
                    "buyer_grant": False,
                    "buyer_export": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "exports":
                full = _buyer_mode.build_mode(entity=entity)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "exports": full["exports"],
                    "export_count": full["export_count"],
                    "empty_exports": full["empty_exports"],
                    "filled_exports": full["filled_exports"],
                    "framework_skeleton": full["framework_skeleton"],
                    "buyer_grant": False,
                    "buyer_export": False,
                    "controlled_export": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif surface_id:
                report = _buyer_mode.read_surface(surface_id)
            else:
                report = _buyer_mode.build_mode(entity=entity)
        except _buyer_mode.BuyerModeError as exc:
            self._buyer_mode_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "buyer_grant": False,
                    "buyer_export": False,
                    "crown_jewels_opened": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _buyer_mode_write_refused(self, path: str) -> None:
        identity = self._require_buyer_mode_owner()
        if identity is None:
            return
        code = self._buyer_mode_refuse_code(path)
        try:
            if code == "grant" or path.endswith("/grant") or path.endswith("/access"):
                _buyer_mode.refuse_grant({})
            elif code == "share" or path.endswith("/share"):
                _buyer_mode.refuse_share({})
            elif code == "reveal" or path.endswith("/reveal") or path.endswith("/unhide"):
                _buyer_mode.refuse_reveal({})
            elif code == "fill" or path.endswith("/fill") or path.endswith("/upload"):
                _buyer_mode.refuse_fill({})
            elif code == "cross" or path.endswith("/blend") or path.endswith("/cross"):
                _buyer_mode.refuse_cross({})
            elif code == "production" or path.endswith("/production"):
                _buyer_mode.refuse_production({})
            elif path.endswith("/export") or path.endswith("/download"):
                _buyer_mode.refuse_export({})
            else:
                _buyer_mode.refuse_external_write({})
        except _buyer_mode.BuyerModeError as exc:
            flags = _buyer_mode.honesty_flags()
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "on_disk": False,
                    "buyer_grant": False,
                    "live_share": False,
                    "buyer_export": False,
                    "crown_jewels_opened": False,
                    **flags,
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Buyer mode is read-only. No grant, no share, and no filled export.",
                "external_writes": False,
                "ledger_write": False,
                "buyer_grant": False,
                "live_share": False,
                "buyer_export": False,
            },
            status=405,
        )

    def _require_attack_audit_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as buyer mode."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Attack audit is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "attack_run": False,
                    "licence_granted": False,
                    "buyer_grant": False,
                    "buyer_export": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "attack_run": False,
                    "licence_granted": False,
                    "buyer_grant": False,
                },
                status=403,
            )
            return None
        return identity

    def _attack_audit_refuse_code(self, path: str) -> str | None:
        if path in {"/api/attack-audit/run", "/api/attack-audit/attack", "/api/attack-audit/redteam"}:
            return "attack"
        if path in {"/api/attack-audit/fill", "/api/attack-audit/upload"}:
            return "fill"
        if path in {"/api/attack-audit/grant", "/api/attack-audit/access"}:
            return "grant"
        if path in {"/api/attack-audit/share"}:
            return "share"
        if path in {"/api/attack-audit/export", "/api/attack-audit/download"}:
            return "export"
        if path in {"/api/attack-audit/transfer", "/api/attack-audit/licence-grant"}:
            return "licence"
        if path in {"/api/attack-audit/production"}:
            return "production"
        return None

    def _attack_audit_page(self) -> None:
        identity = self._require_attack_audit_owner()
        if identity is None:
            return
        page = DASHBOARDS / "attack-audit.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Attack audit page is missing.",
                    "attack_run": False,
                    "licence_granted": False,
                    "buyer_grant": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _attack_audit_fail(self, exc: _attack_audit.AttackAuditError) -> None:
        status = 404 if exc.code == "not_found" else 400
        if exc.code in {
            "attack_refused",
            "fill_refused",
            "buyer_grant_refused",
            "buyer_share_refused",
            "buyer_export_refused",
            "licence_refused",
            "writes_refused",
            "production_refused",
        }:
            status = 405
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "external_writes": False,
                "ledger_write": False,
                "on_disk": False,
                "attack_run": False,
                "licence_granted": False,
                "buyer_grant": False,
                "buyer_export": False,
                "wolf_ip_transferred": False,
            },
            status=status,
        )

    def _attack_audit_get(self, qs: dict, section_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_attack_audit_owner()
        if identity is None:
            return
        try:
            _attack_audit.guard_query(
                attack=(qs.get("attack") or [""])[0],
                run=(qs.get("run") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                share=(qs.get("share") or [""])[0],
                grant=(qs.get("grant") or [""])[0],
                buyer=(qs.get("buyer") or [""])[0],
                export=(qs.get("export") or [""])[0],
                licence=(qs.get("licence") or [""])[0],
                transfer=(qs.get("transfer") or [""])[0],
                production=(qs.get("production") or [""])[0],
            )
            entity = (qs.get("entity") or [""])[0] or None
            if view == "sections":
                full = _attack_audit.build_audit(entity=entity)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "sections": full["sections"],
                    "section_count": full["section_count"],
                    "item_count": full["item_count"],
                    "framework_skeleton": full["framework_skeleton"],
                    "attack_run": False,
                    "buyer_grant": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "packs":
                full = _attack_audit.build_audit(entity=entity)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "packs": full["packs"],
                    "pack_count": full["pack_count"],
                    "empty_packs": full["empty_packs"],
                    "filled_packs": full["filled_packs"],
                    "framework_skeleton": full["framework_skeleton"],
                    "attack_run": False,
                    "buyer_grant": False,
                    "transition_pack_written": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "licence":
                full = _attack_audit.build_audit(entity=entity)
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "licence": full["licence"],
                    "licence_preserved": full["licence_preserved"],
                    "licence_granted": False,
                    "wolf_ip_transferred": False,
                    "framework_skeleton": full["framework_skeleton"],
                    "attack_run": False,
                    "buyer_grant": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif section_id:
                report = _attack_audit.read_section(section_id)
            else:
                report = _attack_audit.build_audit(entity=entity)
        except _attack_audit.AttackAuditError as exc:
            self._attack_audit_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "attack_run": False,
                    "licence_granted": False,
                    "buyer_grant": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _attack_audit_write_refused(self, path: str) -> None:
        identity = self._require_attack_audit_owner()
        if identity is None:
            return
        code = self._attack_audit_refuse_code(path)
        try:
            if code == "attack" or path.endswith("/run") or path.endswith("/attack") or path.endswith("/redteam"):
                _attack_audit.refuse_attack({})
            elif code == "fill" or path.endswith("/fill") or path.endswith("/upload"):
                _attack_audit.refuse_fill({})
            elif code == "grant" or path.endswith("/grant") or path.endswith("/access"):
                _attack_audit.refuse_grant({})
            elif code == "share" or path.endswith("/share"):
                _attack_audit.refuse_share({})
            elif code == "export" or path.endswith("/export") or path.endswith("/download"):
                _attack_audit.refuse_export({})
            elif code == "licence" or path.endswith("/transfer") or path.endswith("/licence-grant"):
                _attack_audit.refuse_licence({})
            elif code == "production" or path.endswith("/production"):
                _attack_audit.refuse_production({})
            else:
                _attack_audit.refuse_external_write({})
        except _attack_audit.AttackAuditError as exc:
            flags = _attack_audit.honesty_flags()
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "on_disk": False,
                    "attack_run": False,
                    "licence_granted": False,
                    "buyer_grant": False,
                    "buyer_export": False,
                    "wolf_ip_transferred": False,
                    **flags,
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Attack audit is read-only. No attack, no filled pack, and no buyer grant.",
                "external_writes": False,
                "ledger_write": False,
                "attack_run": False,
                "licence_granted": False,
                "buyer_grant": False,
            },
            status=405,
        )

    def _require_restore_drill_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the sale pack."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Restore drill is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "production_mutated": False,
                    "nas_destructive": False,
                    "b2_destructive": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "live_restore": False,
                },
                status=403,
            )
            return None
        return identity

    def _restore_drill_refuse_code(self, path: str) -> str | None:
        if path in {
            "/api/restore-drill/run",
            "/api/restore-drill/restore",
            "/api/restore-drill/execute",
        }:
            return "live_restore"
        if path in {"/api/restore-drill/nas", "/api/restore-drill/nas/delete"}:
            return "nas"
        if path in {"/api/restore-drill/b2", "/api/restore-drill/b2/delete"}:
            return "b2"
        if path in {"/api/restore-drill/production", "/api/restore-drill/production/mutate"}:
            return "production"
        return None

    def _restore_drill_page(self) -> None:
        identity = self._require_restore_drill_owner()
        if identity is None:
            return
        page = DASHBOARDS / "restore-drill.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Restore drill page is missing.",
                    "live_restore": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _restore_drill_get(self, qs: dict, step_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_restore_drill_owner()
        if identity is None:
            return
        try:
            _restore_drill.guard_query(
                restore=(qs.get("restore") or [""])[0],
                run=(qs.get("run") or [""])[0],
                delete=(qs.get("delete") or [""])[0],
                nas=(qs.get("nas") or [""])[0],
                b2=(qs.get("b2") or [""])[0],
                production=(qs.get("production") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
            )
            if view == "checklist":
                full = _restore_drill.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "checklist": full["checklist"],
                    "checklist_count": full["checklist_count"],
                    "checklist_executed": full["checklist_executed"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "schema":
                full = _restore_drill.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "log":
                full = _restore_drill.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "log": full["log"],
                    "log_valid": full["log_valid"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif step_id:
                report = _restore_drill.read_step(step_id)
            else:
                report = _restore_drill.build_framework()
        except _restore_drill.RestoreDrillError as exc:
            status = 404 if exc.code == "not_found" else 400
            if exc.code in {
                "live_restore_refused",
                "production_refused",
                "nas_destructive_refused",
                "b2_destructive_refused",
                "ready_refused",
                "proven_refused",
                "success_refused",
                "writes_refused",
                "historical_not_proof",
            }:
                status = 405
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "production_mutated": False,
                    "nas_destructive": False,
                    "b2_destructive": False,
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _restore_drill_write_refused(self, path: str) -> None:
        identity = self._require_restore_drill_owner()
        if identity is None:
            return
        try:
            code = self._restore_drill_refuse_code(path)
            if code == "live_restore":
                _restore_drill.refuse_live_restore({})
            elif code == "nas":
                _restore_drill.refuse_nas({})
            elif code == "b2":
                _restore_drill.refuse_b2({})
            elif code == "production":
                _restore_drill.refuse_production({})
            else:
                _restore_drill.refuse_external_write({})
        except _restore_drill.RestoreDrillError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "production_mutated": False,
                    "nas_destructive": False,
                    "b2_destructive": False,
                    **_restore_drill.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Restore drill is read-only. No live restore and no NAS or B2 delete.",
                "external_writes": False,
                "ledger_write": False,
                "live_restore": False,
            },
            status=405,
        )

    def _require_failure_domains_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the restore drill."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Failure domains are Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "production_mutated": False,
                    "nas_destructive": False,
                    "b2_destructive": False,
                    "independence_proved": False,
                    "beta_equals_production": False,
                    "slots_filled": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "live_restore": False,
                    "independence_proved": False,
                },
                status=403,
            )
            return None
        return identity

    def _failure_domains_refuse_code(self, path: str) -> str | None:
        if path in {
            "/api/failure-domains/run",
            "/api/failure-domains/restore",
            "/api/failure-domains/execute",
        }:
            return "live_restore"
        if path in {"/api/failure-domains/nas", "/api/failure-domains/nas/delete"}:
            return "nas"
        if path in {"/api/failure-domains/b2", "/api/failure-domains/b2/delete"}:
            return "b2"
        if path in {"/api/failure-domains/production", "/api/failure-domains/production/mutate"}:
            return "production"
        if path in {"/api/failure-domains/prove", "/api/failure-domains/independence"}:
            return "prove"
        if path == "/api/failure-domains/collapse":
            return "collapse"
        if path == "/api/failure-domains/fill":
            return "fill"
        if path == "/api/failure-domains/playbook":
            return "playbook"
        return None

    def _failure_domains_page(self) -> None:
        identity = self._require_failure_domains_owner()
        if identity is None:
            return
        page = DASHBOARDS / "failure-domains.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Failure domains page is missing.",
                    "live_restore": False,
                    "independence_proved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _failure_domains_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_failure_domains_owner()
        if identity is None:
            return
        try:
            _failure_domains.guard_query(
                restore=(qs.get("restore") or [""])[0],
                run=(qs.get("run") or [""])[0],
                delete=(qs.get("delete") or [""])[0],
                nas=(qs.get("nas") or [""])[0],
                b2=(qs.get("b2") or [""])[0],
                production=(qs.get("production") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                collapse=(qs.get("collapse") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                playbook=(qs.get("playbook") or [""])[0],
            )
            if view == "checklist":
                full = _failure_domains.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "checklist": full["checklist"],
                    "checklist_count": full["checklist_count"],
                    "checklist_executed": full["checklist_executed"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "independence_proved": False,
                    "slots_filled": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "schema":
                full = _failure_domains.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "independence_proved": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "log":
                full = _failure_domains.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "log": full["log"],
                    "log_valid": full["log_valid"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "beta_equals_production": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "domains":
                full = _failure_domains.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "domains": full["domains"],
                    "domain_count": full["domain_count"],
                    "separation": full["separation"],
                    "beta_equals_production": False,
                    "independence_proved": False,
                    "slots_filled": False,
                    "live_restore": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                try:
                    report = _failure_domains.read_step(ref_id)
                except _failure_domains.FailureDomainError as exc:
                    if exc.code != "not_found":
                        raise
                    report = _failure_domains.read_domain(ref_id)
            else:
                report = _failure_domains.build_framework()
        except _failure_domains.FailureDomainError as exc:
            status = 404 if exc.code == "not_found" else 400
            if exc.code in {
                "live_restore_refused",
                "production_refused",
                "nas_destructive_refused",
                "b2_destructive_refused",
                "ready_refused",
                "proven_refused",
                "collapse_refused",
                "independence_refused",
                "slots_refused",
                "playbook_refused",
                "success_refused",
                "writes_refused",
            }:
                status = 405
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "production_mutated": False,
                    "nas_destructive": False,
                    "b2_destructive": False,
                    "beta_equals_production": False,
                    "independence_proved": False,
                    "slots_filled": False,
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "independence_proved": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _failure_domains_write_refused(self, path: str) -> None:
        identity = self._require_failure_domains_owner()
        if identity is None:
            return
        try:
            code = self._failure_domains_refuse_code(path)
            if code == "live_restore":
                _failure_domains.refuse_live_restore({})
            elif code == "nas":
                _failure_domains.refuse_nas({})
            elif code == "b2":
                _failure_domains.refuse_b2({})
            elif code == "production":
                _failure_domains.refuse_production({})
            elif code == "prove":
                _failure_domains.refuse_independence({})
            elif code == "collapse":
                _failure_domains.refuse_collapse({})
            elif code == "fill":
                _failure_domains.refuse_fill({})
            elif code == "playbook":
                _failure_domains.refuse_playbook({})
            else:
                _failure_domains.refuse_external_write({})
        except _failure_domains.FailureDomainError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "production_mutated": False,
                    "nas_destructive": False,
                    "b2_destructive": False,
                    "beta_equals_production": False,
                    "independence_proved": False,
                    "slots_filled": False,
                    **_failure_domains.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Failure-domain prove is read-only. Beta is not Production. Slots stay empty.",
                "external_writes": False,
                "ledger_write": False,
                "live_restore": False,
                "independence_proved": False,
                "slots_filled": False,
            },
            status=405,
        )

    def _require_crown_jewel_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Crown-jewel register is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Crown-jewel register is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "production_mutated": False,
                    "nas_destructive": False,
                    "b2_destructive": False,
                    "independence_proved": False,
                    "crown_jewels_opened": False,
                    "protection_proved": False,
                    "protected_count": None,
                    "cr_resolved": False,
                    "slots_filled": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "live_restore": False,
                    "crown_jewels_opened": False,
                    "independence_proved": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _crown_jewel_refuse_code(self, path: str) -> str | None:
        if path in {
            "/api/crown-jewels/run",
            "/api/crown-jewels/restore",
            "/api/crown-jewels/execute",
        }:
            return "live_restore"
        if path in {"/api/crown-jewels/nas", "/api/crown-jewels/nas/delete"}:
            return "nas"
        if path in {"/api/crown-jewels/b2", "/api/crown-jewels/b2/delete"}:
            return "b2"
        if path in {"/api/crown-jewels/production", "/api/crown-jewels/production/mutate"}:
            return "production"
        if path in {"/api/crown-jewels/prove", "/api/crown-jewels/independence"}:
            return "prove"
        if path == "/api/crown-jewels/collapse":
            return "collapse"
        if path == "/api/crown-jewels/fill":
            return "fill"
        if path in {"/api/crown-jewels/playbook", "/api/crown-jewels/open", "/api/crown-jewels/copy"}:
            return "playbook"
        if path in {"/api/crown-jewels/protect", "/api/crown-jewels/protected"}:
            return "protect"
        if path == "/api/crown-jewels/resolve":
            return "resolve"
        if path == "/api/crown-jewels/ready":
            return "ready"
        if path in {"/api/crown-jewels/prove-ready", "/api/crown-jewels/proven"}:
            return "proven"
        return None

    def _crown_jewel_fail(self, exc: _crown_jewel.CrownJewelError, *, default: int = 400) -> None:
        status = default
        if exc.code == "not_found":
            status = 404
        elif exc.code in {
            "live_restore_refused",
            "production_refused",
            "nas_destructive_refused",
            "b2_destructive_refused",
            "ready_refused",
            "proven_refused",
            "collapse_refused",
            "independence_refused",
            "slots_refused",
            "playbook_refused",
            "protection_refused",
            "resolve_refused",
            "success_refused",
            "writes_refused",
            "alchemist_refused",
        }:
            status = 405
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "external_writes": False,
                "ledger_write": False,
                "live_restore": False,
                "production_mutated": False,
                "nas_destructive": False,
                "b2_destructive": False,
                "beta_equals_production": False,
                "independence_proved": False,
                "protection_proved": False,
                "crown_jewels_opened": False,
                "protected_count": None,
                "contents": None,
                "slots_filled": False,
                "cr_resolved": False,
                **_crown_jewel.honesty_flags(),
            },
            status=status,
        )

    def _crown_jewel_page(self) -> None:
        identity = self._require_crown_jewel_owner()
        if identity is None:
            return
        page = DASHBOARDS / "crown-jewels.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Crown-jewel page is missing.",
                    "live_restore": False,
                    "crown_jewels_opened": False,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _crown_jewel_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_crown_jewel_owner()
        if identity is None:
            return
        try:
            _crown_jewel.guard_query(
                restore=(qs.get("restore") or [""])[0],
                run=(qs.get("run") or [""])[0],
                delete=(qs.get("delete") or [""])[0],
                nas=(qs.get("nas") or [""])[0],
                b2=(qs.get("b2") or [""])[0],
                production=(qs.get("production") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                collapse=(qs.get("collapse") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                playbook=(qs.get("playbook") or [""])[0],
                open=(qs.get("open") or [""])[0],
                protect=(qs.get("protect") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
            )
            if view == "checklist":
                full = _crown_jewel.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "checklist": full["checklist"],
                    "checklist_count": full["checklist_count"],
                    "checklist_executed": full["checklist_executed"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "independence_proved": False,
                    "crown_jewels_opened": False,
                    "slots_filled": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                    "honesty": full["honesty"],
                }
            elif view == "schema":
                full = _crown_jewel.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "crown_jewels_opened": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                    "honesty": full["honesty"],
                }
            elif view == "log":
                full = _crown_jewel.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "log": full["log"],
                    "log_valid": full["log_valid"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "live_restore": False,
                    "crown_jewels_opened": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                    "honesty": full["honesty"],
                }
            elif view == "domains":
                full = _crown_jewel.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "domains": full["domains"],
                    "domain_count": full["domain_count"],
                    "separation": full["separation"],
                    "beta_equals_production": False,
                    "independence_proved": False,
                    "slots_filled": False,
                    "live_restore": False,
                    "crown_jewels_opened": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                    "honesty": full["honesty"],
                }
            elif view in {"register", "systems"}:
                full = _crown_jewel.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "systems": full["systems"],
                    "system_count": full["system_count"],
                    "identified_count": full["identified_count"],
                    "protected_count": None,
                    "identified_is_protected": False,
                    "crown_jewels_opened": False,
                    "contents": None,
                    "protection_proved": False,
                    "independence_proved": False,
                    "live_restore": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                try:
                    report = _crown_jewel.read_step(ref_id)
                except _crown_jewel.CrownJewelError as exc:
                    if exc.code != "not_found":
                        raise
                    try:
                        report = _crown_jewel.read_system(ref_id)
                    except _crown_jewel.CrownJewelError as exc2:
                        if exc2.code != "not_found":
                            raise
                        report = _crown_jewel.read_domain(ref_id)
            else:
                report = _crown_jewel.build_framework()
        except _crown_jewel.CrownJewelError as exc:
            self._crown_jewel_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "live_restore": False,
                    "crown_jewels_opened": False,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _crown_jewel_write_refused(self, path: str) -> None:
        identity = self._require_crown_jewel_owner()
        if identity is None:
            return
        try:
            code = self._crown_jewel_refuse_code(path)
            if code == "live_restore":
                _crown_jewel.refuse_live_restore({})
            elif code == "nas":
                _crown_jewel.refuse_nas({})
            elif code == "b2":
                _crown_jewel.refuse_b2({})
            elif code == "production":
                _crown_jewel.refuse_production({})
            elif code == "prove":
                _crown_jewel.refuse_independence({})
            elif code == "collapse":
                _crown_jewel.refuse_collapse({})
            elif code == "fill":
                _crown_jewel.refuse_fill({})
            elif code == "playbook":
                _crown_jewel.refuse_playbook({})
            elif code == "protect":
                _crown_jewel.refuse_protection({})
            elif code == "resolve":
                _crown_jewel.refuse_resolve({})
            elif code == "ready":
                _crown_jewel.refuse_ready({})
            elif code == "proven":
                _crown_jewel.refuse_proven({})
            else:
                _crown_jewel.refuse_external_write({})
        except _crown_jewel.CrownJewelError as exc:
            self._crown_jewel_fail(exc, default=405)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Crown-jewel register is read-only. Contents stay closed. Slots stay empty.",
                "external_writes": False,
                "ledger_write": False,
                "live_restore": False,
                "crown_jewels_opened": False,
                "independence_proved": False,
                "protected_count": None,
                "cr_resolved": False,
                "slots_filled": False,
            },
            status=405,
        )

    def _require_crm_connector_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the other proves."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Connector prove is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "send": False,
                    "klaviyo_called": False,
                    "ac_called": False,
                    "conflated": False,
                    "external_crm_write": False,
                    "cr_resolved": False,
                    "sends": None,
                    "subscribers": None,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "send": False,
                    "external_crm_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _crm_connector_refuse_code(self, path: str) -> str | None:
        if path in {"/api/crm-connector-prove/send", "/api/crm-connector-prove/blast"}:
            return "send"
        if path in {"/api/crm-connector-prove/klaviyo-write", "/api/crm-connector-prove/klaviyo"}:
            return "klaviyo"
        if path in {"/api/crm-connector-prove/ac-write", "/api/crm-connector-prove/activecampaign"}:
            return "ac"
        if path in {"/api/crm-connector-prove/crm-write", "/api/crm-connector-prove/write"}:
            return "crm"
        if path == "/api/crm-connector-prove/conflate":
            return "conflate"
        if path in {"/api/crm-connector-prove/production", "/api/crm-connector-prove/production/mutate"}:
            return "production"
        if path in {"/api/crm-connector-prove/prove", "/api/crm-connector-prove/proven"}:
            return "prove"
        if path == "/api/crm-connector-prove/resolve":
            return "resolve"
        if path in {"/api/crm-connector-prove/metricool", "/api/crm-connector-prove/metricool-write"}:
            return "metricool"
        if path == "/api/crm-connector-prove/fill":
            return "fill"
        if path == "/api/crm-connector-prove/ready":
            return "ready"
        return None

    def _crm_connector_page(self) -> None:
        identity = self._require_crm_connector_owner()
        if identity is None:
            return
        page = DASHBOARDS / "crm-connector-prove.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Connector prove page is missing.",
                    "send": False,
                    "external_crm_write": False,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _crm_connector_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_crm_connector_owner()
        if identity is None:
            return
        try:
            _crm_connector.guard_query(
                send=(qs.get("send") or [""])[0],
                write=(qs.get("write") or [""])[0],
                klaviyo=(qs.get("klaviyo") or [""])[0],
                ac=(qs.get("ac") or [""])[0],
                conflate=(qs.get("conflate") or [""])[0],
                production=(qs.get("production") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                metricool=(qs.get("metricool") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                subscribers=(qs.get("subscribers") or [""])[0],
            )
            if view == "checklist":
                full = _crm_connector.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "checklist": full["checklist"],
                    "checklist_count": full["checklist_count"],
                    "checklist_executed": full["checklist_executed"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "send": False,
                    "conflated": False,
                    "external_crm_write": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "schema":
                full = _crm_connector.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "send": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "log":
                full = _crm_connector.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "log": full["log"],
                    "log_valid": full["log_valid"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "send": False,
                    "sends": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "connectors":
                full = _crm_connector.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "connectors": full["connectors"],
                    "connector_count": full["connector_count"],
                    "distinction": full["distinction"],
                    "conflated": False,
                    "klaviyo_called": False,
                    "ac_called": False,
                    "send": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "brands":
                full = _crm_connector.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "brands": full["brands"],
                    "brand_count": full["brand_count"],
                    "subscribers": None,
                    "sends": None,
                    "send": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "gaps":
                full = _crm_connector.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "gaps": full["gaps"],
                    "gap_count": full["gap_count"],
                    "sends": None,
                    "send": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _crm_connector.read_ref(ref_id)
            else:
                report = _crm_connector.build_framework()
        except _crm_connector.ConnectorProveError as exc:
            status = 404 if exc.code == "not_found" else 400
            if exc.code in {
                "send_refused",
                "klaviyo_write_refused",
                "ac_write_refused",
                "crm_write_refused",
                "metricool_write_refused",
                "conflate_refused",
                "production_refused",
                "ready_refused",
                "proven_refused",
                "resolve_refused",
                "slots_refused",
                "invent_metrics_refused",
                "success_refused",
                "writes_refused",
                "alchemist_refused",
            }:
                status = 405
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "send": False,
                    "klaviyo_called": False,
                    "ac_called": False,
                    "conflated": False,
                    "external_crm_write": False,
                    "production_mutated": False,
                    "cr_resolved": False,
                    "sends": None,
                    "subscribers": None,
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "send": False,
                    "external_crm_write": False,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _crm_connector_write_refused(self, path: str) -> None:
        identity = self._require_crm_connector_owner()
        if identity is None:
            return
        try:
            code = self._crm_connector_refuse_code(path)
            if code == "send":
                _crm_connector.refuse_send({})
            elif code == "klaviyo":
                _crm_connector.refuse_klaviyo_write({})
            elif code == "ac":
                _crm_connector.refuse_ac_write({})
            elif code == "crm":
                _crm_connector.refuse_crm_write({})
            elif code == "metricool":
                _crm_connector.refuse_metricool({})
            elif code == "conflate":
                _crm_connector.refuse_conflate({})
            elif code == "production":
                _crm_connector.refuse_production({})
            elif code == "prove":
                _crm_connector.refuse_proven({})
            elif code == "resolve":
                _crm_connector.refuse_resolve({})
            elif code == "fill":
                _crm_connector.refuse_fill({})
            elif code == "ready":
                _crm_connector.refuse_ready({})
            else:
                _crm_connector.refuse_external_write({})
        except _crm_connector.ConnectorProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "send": False,
                    "klaviyo_called": False,
                    "ac_called": False,
                    "conflated": False,
                    "external_crm_write": False,
                    "production_mutated": False,
                    "cr_resolved": False,
                    "sends": None,
                    "subscribers": None,
                    **_crm_connector.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Connector prove is read-only. Klaviyo is not ActiveCampaign. No send.",
                "external_writes": False,
                "ledger_write": False,
                "send": False,
                "external_crm_write": False,
                "conflated": False,
                "cr_resolved": False,
            },
            status=405,
        )

    def _require_pkg_intel_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Package register is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Package register is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "price": None,
                    "pricing_is_truth": False,
                    "booking_mutated": False,
                    "market_package_count": None,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "price": None,
                    "booking_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _pkg_intel_refuse_code(self, path: str) -> str | None:
        if path in {"/api/crm/package-intel/price", "/api/crm/package-intel/pricing"}:
            return "price"
        if path in {"/api/crm/package-intel/booking", "/api/crm/package-intel/book"}:
            return "booking"
        if path in {"/api/crm/package-intel/prove", "/api/crm/package-intel/proven"}:
            return "prove"
        if path == "/api/crm/package-intel/ready":
            return "ready"
        if path == "/api/crm/package-intel/resolve":
            return "resolve"
        if path in {"/api/crm/package-intel/production", "/api/crm/package-intel/production/mutate"}:
            return "production"
        if path in {"/api/crm/package-intel/fill", "/api/crm/package-intel/invent"}:
            return "fill"
        if path in {"/api/crm/package-intel/demand", "/api/crm/package-intel/margin"}:
            return "metrics"
        return None

    def _pkg_intel_fail(self, exc: _pkg_intel.PackageIntelError) -> None:
        status = 400
        if exc.code in {
            "price_refused",
            "booking_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "invent_metrics_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "price": None,
                "pricing_is_truth": False,
                "booking_mutated": False,
                "market_package_count": None,
                "ledger_write": False,
                "cr_resolved": False,
                **_pkg_intel.honesty_flags(),
            },
            status=status,
        )

    def _pkg_intel_write_refused(self, path: str) -> None:
        identity = self._require_pkg_intel_owner()
        if identity is None:
            return
        try:
            code = self._pkg_intel_refuse_code(path)
            if code == "price":
                _pkg_intel.refuse_price({})
            elif code == "booking":
                _pkg_intel.refuse_booking({})
            elif code == "prove":
                _pkg_intel.refuse_proven({})
            elif code == "ready":
                _pkg_intel.refuse_ready({})
            elif code == "resolve":
                _pkg_intel.refuse_resolve({})
            elif code == "production":
                _pkg_intel.refuse_production({})
            elif code == "fill":
                _pkg_intel.refuse_fill({})
            elif code == "metrics":
                _pkg_intel.refuse_invent_metrics({})
            else:
                _pkg_intel.refuse_external_write({})
        except _pkg_intel.PackageIntelError as exc:
            self._pkg_intel_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Package register does not invent a price or a booking.",
                "price": None,
                "pricing_is_truth": False,
                "booking_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
            },
            status=405,
        )

    def _pkg_intel_page(self) -> None:
        identity = self._require_pkg_intel_owner()
        if identity is None:
            return
        page = DASHBOARDS / "crm-package-intel.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Package register page is missing.",
                    "price": None,
                    "booking_mutated": False,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _pkg_intel_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_pkg_intel_owner()
        if identity is None:
            return
        try:
            _pkg_intel.guard_query(
                price=(qs.get("price") or [""])[0],
                booking=(qs.get("booking") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                demand=(qs.get("demand") or [""])[0],
                margin=(qs.get("margin") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _pkg_intel.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "price": None,
                    "pricing_is_truth": False,
                    "booking_mutated": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "products":
                full = _pkg_intel.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": full["empty"],
                    "recorded_count": full["recorded_count"],
                    "market_package_count": None,
                    "products": full["products"],
                    "price": None,
                    "pricing_is_truth": False,
                    "booking_mutated": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "brands":
                full = _pkg_intel.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "brands": full["brands"],
                    "brands_are_not_packages": True,
                    "price": None,
                    "booking_mutated": False,
                    "market_package_count": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _pkg_intel.read_product(ref_id)
            else:
                report = _pkg_intel.build_register()
        except _pkg_intel.PackageIntelError as exc:
            self._pkg_intel_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _pkg_intel_register(self) -> None:
        identity = self._require_pkg_intel_owner()
        if identity is None:
            return
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_payload",
                    "message": f"invalid JSON: {exc}",
                    "price": None,
                    "booking_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=400,
            )
            return
        try:
            out = _pkg_intel.register_product(body, person_id=identity.get("person_id") or "")
        except _pkg_intel.PackageIntelError as exc:
            self._pkg_intel_fail(exc)
            return
        out["person_id"] = identity.get("person_id")
        out["honesty"] = _pkg_intel.honesty_flags()
        self._send_json(out)

    def _require_msc_assets_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Asset register is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Asset register is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "inventory_count": None,
                    "payment": None,
                    "service_proved": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "inventory_count": None,
                    "payment": None,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _msc_assets_refuse_code(self, path: str) -> str | None:
        if path in {"/api/msc/assets/payment", "/api/msc/assets/money"}:
            return "payment"
        if path in {"/api/msc/assets/inventory", "/api/msc/assets/count"}:
            return "inventory"
        if path in {"/api/msc/assets/prove", "/api/msc/assets/proven"}:
            return "prove"
        if path == "/api/msc/assets/ready":
            return "ready"
        if path == "/api/msc/assets/resolve":
            return "resolve"
        if path in {"/api/msc/assets/production", "/api/msc/assets/production/mutate"}:
            return "production"
        if path in {"/api/msc/assets/fill", "/api/msc/assets/invent"}:
            return "fill"
        return None

    def _msc_assets_fail(self, exc: _msc_assets.AssetRegisterError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "inventory_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "inventory_count": None,
                "payment": None,
                "service_proved": False,
                "ledger_write": False,
                "cr_resolved": False,
                **_msc_assets.honesty_flags(),
            },
            status=status,
        )

    def _msc_assets_write_refused(self, path: str) -> None:
        identity = self._require_msc_assets_owner()
        if identity is None:
            return
        try:
            code = self._msc_assets_refuse_code(path)
            if code == "payment":
                _msc_assets.refuse_payment({})
            elif code == "inventory":
                _msc_assets.refuse_inventory({})
            elif code == "prove":
                _msc_assets.refuse_proven({})
            elif code == "ready":
                _msc_assets.refuse_ready({})
            elif code == "resolve":
                _msc_assets.refuse_resolve({})
            elif code == "production":
                _msc_assets.refuse_production({})
            elif code == "fill":
                _msc_assets.refuse_fill({})
            else:
                _msc_assets.refuse_external_write({})
        except _msc_assets.AssetRegisterError as exc:
            self._msc_assets_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Asset register does not invent an inventory count or a payment.",
                "inventory_count": None,
                "payment": None,
                "service_proved": False,
                "ledger_write": False,
                "cr_resolved": False,
            },
            status=405,
        )

    def _msc_assets_page(self) -> None:
        identity = self._require_msc_assets_owner()
        if identity is None:
            return
        page = DASHBOARDS / "msc-assets.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Asset register page is missing.",
                    "inventory_count": None,
                    "payment": None,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _msc_assets_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_msc_assets_owner()
        if identity is None:
            return
        try:
            _msc_assets.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                count=(qs.get("count") or [""])[0],
                inventory=(qs.get("inventory") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _msc_assets.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "inventory_count": None,
                    "payment": None,
                    "service_proved": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "register":
                full = _msc_assets.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": full["empty"],
                    "recorded_count": full["recorded_count"],
                    "recorded_is_inventory": False,
                    "inventory_count": None,
                    "rows": full["rows"],
                    "payment": None,
                    "service_proved": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "venues":
                full = _msc_assets.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "venues": full["venues"],
                    "locations_are_not_assets": True,
                    "inventory_count": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _msc_assets.read_asset(ref_id)
            else:
                report = _msc_assets.build_register()
        except _msc_assets.AssetRegisterError as exc:
            self._msc_assets_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _msc_assets_register(self) -> None:
        identity = self._require_msc_assets_owner()
        if identity is None:
            return
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_payload",
                    "message": f"invalid JSON: {exc}",
                    "inventory_count": None,
                    "payment": None,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=400,
            )
            return
        try:
            out = _msc_assets.register_asset(body, person_id=identity.get("person_id") or "")
        except _msc_assets.AssetRegisterError as exc:
            self._msc_assets_fail(exc)
            return
        out["person_id"] = identity.get("person_id")
        out["honesty"] = _msc_assets.honesty_flags()
        self._send_json(out)

    def _require_msc_compliance_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Compliance pack is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Compliance pack is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "compliance_proved": False,
                    "licence_status": None,
                    "current": False,
                    "payment": None,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "compliance_proved": False,
                    "licence_status": None,
                    "payment": None,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _msc_compliance_refuse_code(self, path: str) -> str | None:
        if path in {"/api/msc/compliance/payment", "/api/msc/compliance/money"}:
            return "payment"
        if path in {
            "/api/msc/compliance/licence-status",
            "/api/msc/compliance/current",
            "/api/msc/compliance/compliant",
        }:
            return "licence_status"
        if path in {"/api/msc/compliance/cloudflare", "/api/msc/compliance/cf"}:
            return "cloudflare"
        if path in {"/api/msc/compliance/access", "/api/msc/compliance/cf-access"}:
            return "access"
        if path in {"/api/msc/compliance/prove", "/api/msc/compliance/proven"}:
            return "prove"
        if path == "/api/msc/compliance/ready":
            return "ready"
        if path == "/api/msc/compliance/resolve":
            return "resolve"
        if path in {"/api/msc/compliance/production", "/api/msc/compliance/production/mutate"}:
            return "production"
        if path in {"/api/msc/compliance/fill", "/api/msc/compliance/note"}:
            return "fill"
        return None

    def _msc_compliance_fail(self, exc: _msc_compliance.CompliancePackError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "licence_status_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "compliance_proved": False,
                "licence_status": None,
                "current": False,
                "payment": None,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
                **_msc_compliance.honesty_flags(),
            },
            status=status,
        )

    def _msc_compliance_write_refused(self, path: str) -> None:
        identity = self._require_msc_compliance_owner()
        if identity is None:
            return
        try:
            code = self._msc_compliance_refuse_code(path)
            if code == "payment":
                _msc_compliance.refuse_payment({})
            elif code == "licence_status":
                _msc_compliance.refuse_licence_status({})
            elif code == "cloudflare":
                _msc_compliance.refuse_cloudflare({})
            elif code == "access":
                _msc_compliance.refuse_access({})
            elif code == "prove":
                _msc_compliance.refuse_proven({})
            elif code == "ready":
                _msc_compliance.refuse_ready({})
            elif code == "resolve":
                _msc_compliance.refuse_resolve({})
            elif code == "production":
                _msc_compliance.refuse_production({})
            elif code == "fill":
                _msc_compliance.refuse_fill({})
            else:
                _msc_compliance.refuse_external_write({})
        except _msc_compliance.CompliancePackError as exc:
            self._msc_compliance_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Compliance pack does not store evidence or a current licence.",
                "compliance_proved": False,
                "licence_status": None,
                "payment": None,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
            },
            status=405,
        )

    def _msc_compliance_page(self) -> None:
        identity = self._require_msc_compliance_owner()
        if identity is None:
            return
        page = DASHBOARDS / "msc-compliance.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Compliance pack page is missing.",
                    "compliance_proved": False,
                    "licence_status": None,
                    "payment": None,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _msc_compliance_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_msc_compliance_owner()
        if identity is None:
            return
        try:
            _msc_compliance.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                licence_status=(qs.get("licence_status") or [""])[0],
                current=(qs.get("current") or [""])[0],
                compliant=(qs.get("compliant") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _msc_compliance.build_pack()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "compliance_proved": False,
                    "licence_status": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _msc_compliance.build_pack()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    "empty_is_compliance": False,
                    "compliance_proved": False,
                    "licence_status": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "pack":
                full = _msc_compliance.build_pack()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    "compliance_proved": False,
                    "licence_status": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _msc_compliance.read_kind(ref_id)
            else:
                report = _msc_compliance.build_pack()
        except _msc_compliance.CompliancePackError as exc:
            self._msc_compliance_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _require_msc_cyber_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Cyber baseline is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Cybersecurity baseline is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "security_proved": False,
                    "mfa_status": None,
                    "device_posture": None,
                    "audited_access": None,
                    "current": False,
                    "payment": None,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "security_proved": False,
                    "mfa_status": None,
                    "device_posture": None,
                    "payment": None,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _msc_cyber_refuse_code(self, path: str) -> str | None:
        if path in {"/api/msc/cyber/payment", "/api/msc/cyber/money"}:
            return "payment"
        if path in {
            "/api/msc/cyber/mfa-status",
            "/api/msc/cyber/device-posture-status",
            "/api/msc/cyber/posture",
            "/api/msc/cyber/current",
        }:
            return "posture"
        if path in {"/api/msc/cyber/cloudflare", "/api/msc/cyber/cf"}:
            return "cloudflare"
        if path in {"/api/msc/cyber/access", "/api/msc/cyber/cf-access"}:
            return "access"
        if path in {"/api/msc/cyber/prove", "/api/msc/cyber/proven"}:
            return "prove"
        if path == "/api/msc/cyber/ready":
            return "ready"
        if path == "/api/msc/cyber/resolve":
            return "resolve"
        if path in {"/api/msc/cyber/production", "/api/msc/cyber/production/mutate"}:
            return "production"
        if path in {"/api/msc/cyber/fill", "/api/msc/cyber/note"}:
            return "fill"
        return None

    def _msc_cyber_fail(self, exc: _msc_cyber.CyberBaselineError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "posture_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "security_proved": False,
                "mfa_status": None,
                "device_posture": None,
                "audited_access": None,
                "current": False,
                "payment": None,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
                **_msc_cyber.honesty_flags(),
            },
            status=status,
        )

    def _msc_cyber_write_refused(self, path: str) -> None:
        identity = self._require_msc_cyber_owner()
        if identity is None:
            return
        try:
            code = self._msc_cyber_refuse_code(path)
            if code == "payment":
                _msc_cyber.refuse_payment({})
            elif code == "posture":
                _msc_cyber.refuse_posture({})
            elif code == "cloudflare":
                _msc_cyber.refuse_cloudflare({})
            elif code == "access":
                _msc_cyber.refuse_access({})
            elif code == "prove":
                _msc_cyber.refuse_proven({})
            elif code == "ready":
                _msc_cyber.refuse_ready({})
            elif code == "resolve":
                _msc_cyber.refuse_resolve({})
            elif code == "production":
                _msc_cyber.refuse_production({})
            elif code == "fill":
                _msc_cyber.refuse_fill({})
            else:
                _msc_cyber.refuse_external_write({})
        except _msc_cyber.CyberBaselineError as exc:
            self._msc_cyber_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Cybersecurity baseline does not store evidence or current MFA.",
                "security_proved": False,
                "mfa_status": None,
                "device_posture": None,
                "payment": None,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
            },
            status=405,
        )

    def _msc_cyber_page(self) -> None:
        identity = self._require_msc_cyber_owner()
        if identity is None:
            return
        page = DASHBOARDS / "msc-cyber.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Cybersecurity baseline page is missing.",
                    "security_proved": False,
                    "mfa_status": None,
                    "payment": None,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _msc_cyber_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_msc_cyber_owner()
        if identity is None:
            return
        try:
            _msc_cyber.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                mfa=(qs.get("mfa") or [""])[0],
                mfa_status=(qs.get("mfa_status") or [""])[0],
                device_posture=(qs.get("device_posture") or qs.get("device-posture") or [""])[0],
                posture=(qs.get("posture") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _msc_cyber.build_baseline()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "security_proved": False,
                    "mfa_status": None,
                    "device_posture": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _msc_cyber.build_baseline()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    "empty_is_security": False,
                    "security_proved": False,
                    "mfa_status": None,
                    "device_posture": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "baseline":
                full = _msc_cyber.build_baseline()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    "security_proved": False,
                    "mfa_status": None,
                    "device_posture": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _msc_cyber.read_kind(ref_id)
            else:
                report = _msc_cyber.build_baseline()
        except _msc_cyber.CyberBaselineError as exc:
            self._msc_cyber_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _require_msc_records_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Records register is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Records register is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "defensibility_proved": False,
                    "records_status": None,
                    "retention": None,
                    "legal_hold": None,
                    "current": False,
                    "payment": None,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "defensibility_proved": False,
                    "records_status": None,
                    "retention": None,
                    "legal_hold": None,
                    "payment": None,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _msc_records_refuse_code(self, path: str) -> str | None:
        if path in {"/api/msc/records/payment", "/api/msc/records/money"}:
            return "payment"
        if path in {
            "/api/msc/records/retention-status",
            "/api/msc/records/legal-hold-status",
            "/api/msc/records/hold",
            "/api/msc/records/current",
        }:
            return "current"
        if path in {"/api/msc/records/cloudflare", "/api/msc/records/cf"}:
            return "cloudflare"
        if path in {"/api/msc/records/access", "/api/msc/records/cf-access"}:
            return "access"
        if path in {"/api/msc/records/prove", "/api/msc/records/proven"}:
            return "prove"
        if path == "/api/msc/records/ready":
            return "ready"
        if path == "/api/msc/records/resolve":
            return "resolve"
        if path in {"/api/msc/records/production", "/api/msc/records/production/mutate"}:
            return "production"
        if path in {"/api/msc/records/fill", "/api/msc/records/note"}:
            return "fill"
        return None

    def _msc_records_fail(self, exc: _msc_records.RecordsDefensibilityError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "defensibility_proved": False,
                "records_status": None,
                "retention": None,
                "legal_hold": None,
                "current": False,
                "payment": None,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
                **_msc_records.honesty_flags(),
            },
            status=status,
        )

    def _msc_records_write_refused(self, path: str) -> None:
        identity = self._require_msc_records_owner()
        if identity is None:
            return
        try:
            code = self._msc_records_refuse_code(path)
            if code == "payment":
                _msc_records.refuse_payment({})
            elif code == "current":
                _msc_records.refuse_current({})
            elif code == "cloudflare":
                _msc_records.refuse_cloudflare({})
            elif code == "access":
                _msc_records.refuse_access({})
            elif code == "prove":
                _msc_records.refuse_proven({})
            elif code == "ready":
                _msc_records.refuse_ready({})
            elif code == "resolve":
                _msc_records.refuse_resolve({})
            elif code == "production":
                _msc_records.refuse_production({})
            elif code == "fill":
                _msc_records.refuse_fill({})
            else:
                _msc_records.refuse_external_write({})
        except _msc_records.RecordsDefensibilityError as exc:
            self._msc_records_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Records register does not store evidence or a live legal hold.",
                "defensibility_proved": False,
                "records_status": None,
                "retention": None,
                "legal_hold": None,
                "payment": None,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
            },
            status=405,
        )

    def _msc_records_page(self) -> None:
        identity = self._require_msc_records_owner()
        if identity is None:
            return
        page = DASHBOARDS / "msc-records.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Records register page is missing.",
                    "defensibility_proved": False,
                    "records_status": None,
                    "payment": None,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _msc_records_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_msc_records_owner()
        if identity is None:
            return
        try:
            _msc_records.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                records=(qs.get("records") or [""])[0],
                records_status=(qs.get("records_status") or [""])[0],
                retention=(qs.get("retention") or [""])[0],
                retention_status=(qs.get("retention_status") or qs.get("retention-status") or [""])[0],
                legal_hold=(qs.get("legal_hold") or qs.get("legal-hold") or [""])[0],
                hold=(qs.get("hold") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _msc_records.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "defensibility_proved": False,
                    "records_status": None,
                    "retention": None,
                    "legal_hold": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _msc_records.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    "empty_is_defensibility": False,
                    "defensibility_proved": False,
                    "records_status": None,
                    "retention": None,
                    "legal_hold": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "register":
                full = _msc_records.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    "defensibility_proved": False,
                    "records_status": None,
                    "retention": None,
                    "legal_hold": None,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _msc_records.read_kind(ref_id)
            else:
                report = _msc_records.build_register()
        except _msc_records.RecordsDefensibilityError as exc:
            self._msc_records_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _require_intg_secrets_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Secrets framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Secrets framework is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "separation_proved": False,
                    "live_vault": False,
                    "vault": None,
                    "rotation": None,
                    "separation": None,
                    "current": False,
                    "payment": None,
                    "pointer_is_proof": False,
                    "contents_read": False,
                    "secret_store_write": False,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "separation_proved": False,
                    "live_vault": False,
                    "vault": None,
                    "rotation": None,
                    "separation": None,
                    "payment": None,
                    "pointer_is_proof": False,
                    "contents_read": False,
                    "secret_store_write": False,
                    "cloudflare_mutated": False,
                    "access_mutated": False,
                    "ledger_write": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _intg_secrets_refuse_code(self, path: str) -> str | None:
        if path in {"/api/intg/secrets/payment", "/api/intg/secrets/money"}:
            return "payment"
        if path in {
            "/api/intg/secrets/live-vault",
            "/api/intg/secrets/rotation-status",
            "/api/intg/secrets/separation-status",
            "/api/intg/secrets/current",
        }:
            return "current"
        if path in {"/api/intg/secrets/secret-store", "/api/intg/secrets/external"}:
            return "secret-store"
        if path in {"/api/intg/secrets/cloudflare", "/api/intg/secrets/cf"}:
            return "cloudflare"
        if path in {"/api/intg/secrets/access", "/api/intg/secrets/cf-access"}:
            return "access"
        if path in {"/api/intg/secrets/prove", "/api/intg/secrets/proven"}:
            return "prove"
        if path == "/api/intg/secrets/ready":
            return "ready"
        if path == "/api/intg/secrets/resolve":
            return "resolve"
        if path in {"/api/intg/secrets/production", "/api/intg/secrets/production/mutate"}:
            return "production"
        if path in {"/api/intg/secrets/fill", "/api/intg/secrets/note"}:
            return "fill"
        return None

    def _intg_secrets_fail(self, exc: _intg_secrets.SecretsEnvError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "current_refused",
            "secret_store_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "separation_proved": False,
                "live_vault": False,
                "vault": None,
                "rotation": None,
                "separation": None,
                "current": False,
                "payment": None,
                "pointer_is_proof": False,
                "contents_read": False,
                "secret_store_write": False,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
                **_intg_secrets.honesty_flags(),
            },
            status=status,
        )

    def _intg_secrets_write_refused(self, path: str) -> None:
        identity = self._require_intg_secrets_owner()
        if identity is None:
            return
        try:
            code = self._intg_secrets_refuse_code(path)
            if code == "payment":
                _intg_secrets.refuse_payment({})
            elif code == "current":
                _intg_secrets.refuse_current({})
            elif code == "secret-store":
                _intg_secrets.refuse_secret_store({})
            elif code == "cloudflare":
                _intg_secrets.refuse_cloudflare({})
            elif code == "access":
                _intg_secrets.refuse_access({})
            elif code == "prove":
                _intg_secrets.refuse_proven({})
            elif code == "ready":
                _intg_secrets.refuse_ready({})
            elif code == "resolve":
                _intg_secrets.refuse_resolve({})
            elif code == "production":
                _intg_secrets.refuse_production({})
            elif code == "fill":
                _intg_secrets.refuse_fill({})
            else:
                _intg_secrets.refuse_external_write({})
        except _intg_secrets.SecretsEnvError as exc:
            self._intg_secrets_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Secrets framework does not store a secret or a live vault.",
                "separation_proved": False,
                "live_vault": False,
                "vault": None,
                "rotation": None,
                "separation": None,
                "payment": None,
                "pointer_is_proof": False,
                "contents_read": False,
                "secret_store_write": False,
                "cloudflare_mutated": False,
                "access_mutated": False,
                "ledger_write": False,
                "cr_resolved": False,
            },
            status=405,
        )

    def _intg_secrets_page(self) -> None:
        identity = self._require_intg_secrets_owner()
        if identity is None:
            return
        page = DASHBOARDS / "intg-secrets.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Secrets framework page is missing.",
                    "separation_proved": False,
                    "live_vault": False,
                    "payment": None,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _intg_secrets_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_intg_secrets_owner()
        if identity is None:
            return
        try:
            _intg_secrets.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                vault=(qs.get("vault") or [""])[0],
                live_vault=(qs.get("live_vault") or qs.get("live-vault") or [""])[0],
                rotation=(qs.get("rotation") or [""])[0],
                separation=(qs.get("separation") or [""])[0],
                current=(qs.get("current") or [""])[0],
                secret=(qs.get("secret") or [""])[0],
                secret_store=(qs.get("secret_store") or qs.get("secret-store") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _intg_secrets.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "separation_proved": False,
                    "live_vault": False,
                    "vault": None,
                    "rotation": None,
                    "separation": None,
                    "payment": None,
                    "pointer_is_proof": False,
                    "contents_read": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _intg_secrets.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    "empty_is_separation": False,
                    "separation_proved": False,
                    "live_vault": False,
                    "vault": None,
                    "rotation": None,
                    "separation": None,
                    "payment": None,
                    "pointer_is_proof": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "register":
                full = _intg_secrets.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    "separation_proved": False,
                    "live_vault": False,
                    "vault": None,
                    "rotation": None,
                    "separation": None,
                    "payment": None,
                    "pointer_is_proof": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "pointers":
                full = _intg_secrets.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "pointers": full["pointers"],
                    "pointer_is_proof": False,
                    "checks_are_proof": False,
                    "contents_read": False,
                    "separation_proved": False,
                    "live_vault": False,
                    "payment": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _intg_secrets.read_kind(ref_id)
            else:
                report = _intg_secrets.build_register()
        except _intg_secrets.SecretsEnvError as exc:
            self._intg_secrets_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _ggv_pnl_quiet(self) -> dict:
        return {
            "profitability_proved": False,
            "live_pnl": False,
            "empty_is_pnl": False,
            "revenue": None,
            "cost": None,
            "margin": None,
            "fx": None,
            "current": False,
            "target_is_actual": False,
            "payment": None,
            "money": None,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
        }

    def _require_ggv_pnl_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Profitability framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        quiet = self._ggv_pnl_quiet()
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Client profitability framework is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **quiet,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **quiet,
                },
                status=403,
            )
            return None
        return identity

    def _ggv_pnl_refuse_code(self, path: str) -> str | None:
        if path in {"/api/ggv/client-profitability/payment", "/api/ggv/client-profitability/money"}:
            return "payment"
        if path in {"/api/ggv/client-profitability/bank", "/api/ggv/client-profitability/transfer"}:
            return "bank"
        if path in {"/api/ggv/client-profitability/zayen", "/api/ggv/client-profitability/books"}:
            return "books"
        if path in {
            "/api/ggv/client-profitability/revenue",
            "/api/ggv/client-profitability/cost",
            "/api/ggv/client-profitability/margin",
            "/api/ggv/client-profitability/fx",
            "/api/ggv/client-profitability/live-pnl",
            "/api/ggv/client-profitability/current",
        }:
            return "current"
        if path in {"/api/ggv/client-profitability/cloudflare", "/api/ggv/client-profitability/cf"}:
            return "cloudflare"
        if path in {"/api/ggv/client-profitability/access", "/api/ggv/client-profitability/cf-access"}:
            return "access"
        if path in {"/api/ggv/client-profitability/prove", "/api/ggv/client-profitability/proven"}:
            return "prove"
        if path == "/api/ggv/client-profitability/ready":
            return "ready"
        if path == "/api/ggv/client-profitability/resolve":
            return "resolve"
        if path in {
            "/api/ggv/client-profitability/production",
            "/api/ggv/client-profitability/production/mutate",
        }:
            return "production"
        if path in {"/api/ggv/client-profitability/fill", "/api/ggv/client-profitability/note"}:
            return "fill"
        if path in {"/api/ggv/client-profitability/score", "/api/ggv/client-profitability/credits"}:
            return "score"
        return None

    def _ggv_pnl_fail(self, exc: _ggv_pnl.ClientProfitabilityError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "score_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._ggv_pnl_quiet(),
                **_ggv_pnl.honesty_flags(),
            },
            status=status,
        )

    def _ggv_pnl_write_refused(self, path: str) -> None:
        identity = self._require_ggv_pnl_owner()
        if identity is None:
            return
        try:
            code = self._ggv_pnl_refuse_code(path)
            if code == "payment":
                _ggv_pnl.refuse_payment({})
            elif code == "bank":
                _ggv_pnl.refuse_bank({})
            elif code == "books":
                _ggv_pnl.refuse_books({})
            elif code == "current":
                _ggv_pnl.refuse_current({})
            elif code == "cloudflare":
                _ggv_pnl.refuse_cloudflare({})
            elif code == "access":
                _ggv_pnl.refuse_access({})
            elif code == "prove":
                _ggv_pnl.refuse_proven({})
            elif code == "ready":
                _ggv_pnl.refuse_ready({})
            elif code == "resolve":
                _ggv_pnl.refuse_resolve({})
            elif code == "production":
                _ggv_pnl.refuse_production({})
            elif code == "fill":
                _ggv_pnl.refuse_fill({})
            elif code == "score":
                _ggv_pnl.refuse_score({})
            else:
                _ggv_pnl.refuse_external_write({})
        except _ggv_pnl.ClientProfitabilityError as exc:
            self._ggv_pnl_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Client profitability framework does not store a P&L or a payment.",
                **self._ggv_pnl_quiet(),
            },
            status=405,
        )

    def _ggv_pnl_page(self) -> None:
        identity = self._require_ggv_pnl_owner()
        if identity is None:
            return
        page = DASHBOARDS / "ggv-client-profitability.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Client profitability page is missing.",
                    **self._ggv_pnl_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _ggv_pnl_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_ggv_pnl_owner()
        if identity is None:
            return
        try:
            _ggv_pnl.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                revenue=(qs.get("revenue") or [""])[0],
                cost=(qs.get("cost") or [""])[0],
                margin=(qs.get("margin") or [""])[0],
                fx=(qs.get("fx") or [""])[0],
                live_pnl=(qs.get("live_pnl") or qs.get("live-pnl") or [""])[0],
                current=(qs.get("current") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _ggv_pnl.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._ggv_pnl_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _ggv_pnl.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._ggv_pnl_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "register":
                full = _ggv_pnl.build_register()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._ggv_pnl_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _ggv_pnl.read_kind(ref_id)
            else:
                report = _ggv_pnl.build_register()
        except _ggv_pnl.ClientProfitabilityError as exc:
            self._ggv_pnl_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _ggv_strategy_quiet(self) -> dict:
        return {
            "empty_is_machine": False,
            "empty_is_learning": False,
            "empty_is_ready": False,
            "proved": False,
            "live_strategy_machine": False,
            "governed_learning": False,
            "current": False,
            "strategy_score": None,
            "revenue": None,
            "learn_outcome": None,
            "metricool_write": False,
            "metricool_called": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
        }

    def _require_ggv_strategy_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Strategy framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Strategy framework is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._ggv_strategy_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._ggv_strategy_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _ggv_strategy_refuse_code(self, path: str) -> str | None:
        if path in {"/api/ggv/strategy-machine/payment", "/api/ggv/strategy-machine/money"}:
            return "payment"
        if path in {"/api/ggv/strategy-machine/bank", "/api/ggv/strategy-machine/transfer"}:
            return "bank"
        if path in {"/api/ggv/strategy-machine/zayen", "/api/ggv/strategy-machine/books"}:
            return "books"
        if path in {"/api/ggv/strategy-machine/metricool", "/api/ggv/strategy-machine/metricool-write"}:
            return "metricool"
        if path in {
            "/api/ggv/strategy-machine/strategy-score",
            "/api/ggv/strategy-machine/revenue",
            "/api/ggv/strategy-machine/learn-outcome",
            "/api/ggv/strategy-machine/current",
        }:
            return "current"
        if path in {"/api/ggv/strategy-machine/cloudflare", "/api/ggv/strategy-machine/cf"}:
            return "cloudflare"
        if path in {"/api/ggv/strategy-machine/access", "/api/ggv/strategy-machine/cf-access"}:
            return "access"
        if path in {"/api/ggv/strategy-machine/prove", "/api/ggv/strategy-machine/proven"}:
            return "prove"
        if path == "/api/ggv/strategy-machine/ready":
            return "ready"
        if path == "/api/ggv/strategy-machine/resolve":
            return "resolve"
        if path in {
            "/api/ggv/strategy-machine/production",
            "/api/ggv/strategy-machine/production/mutate",
        }:
            return "production"
        if path in {"/api/ggv/strategy-machine/score", "/api/ggv/strategy-machine/credits"}:
            return "score"
        if path in {"/api/ggv/strategy-machine/fill", "/api/ggv/strategy-machine/note"}:
            return "fill"
        if path == "/api/ggv/strategy-machine/alchemist":
            return "alchemist"
        return None

    def _ggv_strategy_fail(self, exc: _ggv_strategy.StrategyMachineError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "metricool_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._ggv_strategy_quiet(),
                **_ggv_strategy.honesty_flags(),
            },
            status=status,
        )

    def _ggv_strategy_write_refused(self, path: str) -> None:
        identity = self._require_ggv_strategy_owner()
        if identity is None:
            return
        try:
            code = self._ggv_strategy_refuse_code(path)
            if code == "payment":
                _ggv_strategy.refuse_payment({})
            elif code == "bank":
                _ggv_strategy.refuse_bank({})
            elif code == "books":
                _ggv_strategy.refuse_books({})
            elif code == "metricool":
                _ggv_strategy.refuse_metricool({})
            elif code == "current":
                _ggv_strategy.refuse_current({})
            elif code == "cloudflare":
                _ggv_strategy.refuse_cloudflare({})
            elif code == "access":
                _ggv_strategy.refuse_access({})
            elif code == "prove":
                _ggv_strategy.refuse_proven({})
            elif code == "ready":
                _ggv_strategy.refuse_ready({})
            elif code == "resolve":
                _ggv_strategy.refuse_resolve({})
            elif code == "production":
                _ggv_strategy.refuse_production({})
            elif code == "score":
                _ggv_strategy.refuse_score({})
            elif code == "fill":
                _ggv_strategy.refuse_fill({})
            elif code == "alchemist":
                _ggv_strategy.refuse_alchemist({})
            else:
                _ggv_strategy.refuse_external_write({})
        except _ggv_strategy.StrategyMachineError as exc:
            self._ggv_strategy_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Strategy framework does not store a live strategy machine.",
                **self._ggv_strategy_quiet(),
            },
            status=405,
        )

    def _ggv_strategy_page(self) -> None:
        identity = self._require_ggv_strategy_owner()
        if identity is None:
            return
        page = DASHBOARDS / "ggv-strategy-machine.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Strategy machine page is missing.",
                    **self._ggv_strategy_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _ggv_strategy_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_ggv_strategy_owner()
        if identity is None:
            return
        try:
            _ggv_strategy.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                metricool=(qs.get("metricool") or [""])[0],
                strategy_score=(qs.get("strategy_score") or qs.get("strategy-score") or [""])[0],
                revenue=(qs.get("revenue") or [""])[0],
                learn_outcome=(qs.get("learn_outcome") or qs.get("learn-outcome") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _ggv_strategy.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._ggv_strategy_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _ggv_strategy.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._ggv_strategy_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _ggv_strategy.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._ggv_strategy_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _ggv_strategy.read_kind(ref_id)
            else:
                report = _ggv_strategy.build_framework()
        except _ggv_strategy.StrategyMachineError as exc:
            self._ggv_strategy_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _amg_journey_quiet(self) -> dict:
        return {
            "empty_is_journey": False,
            "empty_is_operations": False,
            "empty_is_ready": False,
            "proved": False,
            "live_journey": False,
            "guest_operations": False,
            "current": False,
            "booking_count": None,
            "occupancy": None,
            "yanolja_live": False,
            "yanolja_called": False,
            "yanolja_write": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
        }

    def _require_amg_journey_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Journey framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Guest journey framework is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._amg_journey_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._amg_journey_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _amg_journey_refuse_code(self, path: str) -> str | None:
        if path in {"/api/amg/journey-workflow/payment", "/api/amg/journey-workflow/money"}:
            return "payment"
        if path in {"/api/amg/journey-workflow/bank", "/api/amg/journey-workflow/transfer"}:
            return "bank"
        if path in {"/api/amg/journey-workflow/zayen", "/api/amg/journey-workflow/books"}:
            return "books"
        if path in {"/api/amg/journey-workflow/yanolja", "/api/amg/journey-workflow/yanolja-write"}:
            return "yanolja"
        if path in {
            "/api/amg/journey-workflow/booking-count",
            "/api/amg/journey-workflow/occupancy",
            "/api/amg/journey-workflow/current",
        }:
            return "current"
        if path in {"/api/amg/journey-workflow/cloudflare", "/api/amg/journey-workflow/cf"}:
            return "cloudflare"
        if path in {"/api/amg/journey-workflow/access", "/api/amg/journey-workflow/cf-access"}:
            return "access"
        if path in {"/api/amg/journey-workflow/prove", "/api/amg/journey-workflow/proven"}:
            return "prove"
        if path == "/api/amg/journey-workflow/ready":
            return "ready"
        if path == "/api/amg/journey-workflow/resolve":
            return "resolve"
        if path in {
            "/api/amg/journey-workflow/production",
            "/api/amg/journey-workflow/production/mutate",
        }:
            return "production"
        if path in {"/api/amg/journey-workflow/score", "/api/amg/journey-workflow/credits"}:
            return "score"
        if path in {"/api/amg/journey-workflow/fill", "/api/amg/journey-workflow/note"}:
            return "fill"
        if path == "/api/amg/journey-workflow/alchemist":
            return "alchemist"
        return None

    def _amg_journey_fail(self, exc: _amg_journey.JourneyWorkflowError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "yanolja_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._amg_journey_quiet(),
                **_amg_journey.honesty_flags(),
            },
            status=status,
        )

    def _amg_journey_write_refused(self, path: str) -> None:
        identity = self._require_amg_journey_owner()
        if identity is None:
            return
        try:
            code = self._amg_journey_refuse_code(path)
            if code == "payment":
                _amg_journey.refuse_payment({})
            elif code == "bank":
                _amg_journey.refuse_bank({})
            elif code == "books":
                _amg_journey.refuse_books({})
            elif code == "yanolja":
                _amg_journey.refuse_yanolja({})
            elif code == "current":
                _amg_journey.refuse_current({})
            elif code == "cloudflare":
                _amg_journey.refuse_cloudflare({})
            elif code == "access":
                _amg_journey.refuse_access({})
            elif code == "prove":
                _amg_journey.refuse_proven({})
            elif code == "ready":
                _amg_journey.refuse_ready({})
            elif code == "resolve":
                _amg_journey.refuse_resolve({})
            elif code == "production":
                _amg_journey.refuse_production({})
            elif code == "score":
                _amg_journey.refuse_score({})
            elif code == "fill":
                _amg_journey.refuse_fill({})
            elif code == "alchemist":
                _amg_journey.refuse_alchemist({})
            else:
                _amg_journey.refuse_external_write({})
        except _amg_journey.JourneyWorkflowError as exc:
            self._amg_journey_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Journey framework does not store a live journey workflow.",
                **self._amg_journey_quiet(),
            },
            status=405,
        )

    def _amg_journey_page(self) -> None:
        identity = self._require_amg_journey_owner()
        if identity is None:
            return
        page = DASHBOARDS / "amg-journey-workflow.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Guest journey page is missing.",
                    **self._amg_journey_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _amg_journey_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_amg_journey_owner()
        if identity is None:
            return
        try:
            _amg_journey.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                booking_count=(qs.get("booking_count") or qs.get("booking-count") or [""])[0],
                occupancy=(qs.get("occupancy") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _amg_journey.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._amg_journey_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _amg_journey.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._amg_journey_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _amg_journey.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._amg_journey_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _amg_journey.read_kind(ref_id)
            else:
                report = _amg_journey.build_framework()
        except _amg_journey.JourneyWorkflowError as exc:
            self._amg_journey_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _amg_ops_quiet(self) -> dict:
        return {
            "empty_is_ops": False,
            "empty_is_operations": False,
            "empty_is_ready": False,
            "proved": False,
            "live_ops": False,
            "hotel_operations": False,
            "current": False,
            "occupancy": None,
            "adr": None,
            "revpar": None,
            "yanolja_live": False,
            "yanolja_called": False,
            "yanolja_write": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_occupancy": False,
            "invented_adr": False,
            "invented_revpar": False,
        }

    def _require_amg_ops_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Daily ops framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Daily hotel operating state is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._amg_ops_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._amg_ops_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _amg_ops_refuse_code(self, path: str) -> str | None:
        if path in {"/api/amg/daily-ops-state/payment", "/api/amg/daily-ops-state/money"}:
            return "payment"
        if path in {"/api/amg/daily-ops-state/bank", "/api/amg/daily-ops-state/transfer"}:
            return "bank"
        if path in {"/api/amg/daily-ops-state/zayen", "/api/amg/daily-ops-state/books"}:
            return "books"
        if path in {"/api/amg/daily-ops-state/yanolja", "/api/amg/daily-ops-state/yanolja-write"}:
            return "yanolja"
        if path in {
            "/api/amg/daily-ops-state/adr",
            "/api/amg/daily-ops-state/revpar",
            "/api/amg/daily-ops-state/current",
            "/api/amg/daily-ops-state/occupancy-value",
        }:
            return "current"
        if path in {"/api/amg/daily-ops-state/cloudflare", "/api/amg/daily-ops-state/cf"}:
            return "cloudflare"
        if path in {"/api/amg/daily-ops-state/access", "/api/amg/daily-ops-state/cf-access"}:
            return "access"
        if path in {"/api/amg/daily-ops-state/prove", "/api/amg/daily-ops-state/proven"}:
            return "prove"
        if path == "/api/amg/daily-ops-state/ready":
            return "ready"
        if path == "/api/amg/daily-ops-state/resolve":
            return "resolve"
        if path in {
            "/api/amg/daily-ops-state/production",
            "/api/amg/daily-ops-state/production/mutate",
        }:
            return "production"
        if path in {"/api/amg/daily-ops-state/score", "/api/amg/daily-ops-state/credits"}:
            return "score"
        if path in {"/api/amg/daily-ops-state/fill", "/api/amg/daily-ops-state/note"}:
            return "fill"
        if path == "/api/amg/daily-ops-state/alchemist":
            return "alchemist"
        return None

    def _amg_ops_fail(self, exc: _amg_ops.DailyOpsStateError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "yanolja_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._amg_ops_quiet(),
                **_amg_ops.honesty_flags(),
            },
            status=status,
        )

    def _amg_ops_write_refused(self, path: str) -> None:
        identity = self._require_amg_ops_owner()
        if identity is None:
            return
        try:
            code = self._amg_ops_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail == "occupancy":
                code = "current"
            elif code is None and tail in {
                "arrivals",
                "departures",
                "in-house",
                "out-of-order",
                "notes",
            }:
                code = "fill"
            if code == "payment":
                _amg_ops.refuse_payment({})
            elif code == "bank":
                _amg_ops.refuse_bank({})
            elif code == "books":
                _amg_ops.refuse_books({})
            elif code == "yanolja":
                _amg_ops.refuse_yanolja({})
            elif code == "current":
                _amg_ops.refuse_current({})
            elif code == "cloudflare":
                _amg_ops.refuse_cloudflare({})
            elif code == "access":
                _amg_ops.refuse_access({})
            elif code == "prove":
                _amg_ops.refuse_proven({})
            elif code == "ready":
                _amg_ops.refuse_ready({})
            elif code == "resolve":
                _amg_ops.refuse_resolve({})
            elif code == "production":
                _amg_ops.refuse_production({})
            elif code == "score":
                _amg_ops.refuse_score({})
            elif code == "fill":
                _amg_ops.refuse_fill({})
            elif code == "alchemist":
                _amg_ops.refuse_alchemist({})
            else:
                _amg_ops.refuse_external_write({})
        except _amg_ops.DailyOpsStateError as exc:
            self._amg_ops_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Daily ops framework does not store a live daily ops state.",
                **self._amg_ops_quiet(),
            },
            status=405,
        )

    def _amg_ops_page(self) -> None:
        identity = self._require_amg_ops_owner()
        if identity is None:
            return
        page = DASHBOARDS / "amg-daily-ops-state.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Daily hotel operating state page is missing.",
                    **self._amg_ops_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _amg_ops_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_amg_ops_owner()
        if identity is None:
            return
        try:
            _amg_ops.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                occupancy=(qs.get("occupancy") or [""])[0],
                adr=(qs.get("adr") or [""])[0],
                revpar=(qs.get("revpar") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _amg_ops.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._amg_ops_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _amg_ops.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._amg_ops_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _amg_ops.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._amg_ops_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _amg_ops.read_kind(ref_id)
            else:
                report = _amg_ops.build_framework()
        except _amg_ops.DailyOpsStateError as exc:
            self._amg_ops_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _amg_packages_quiet(self) -> dict:
        return {
            "empty_is_catalog": False,
            "empty_is_products": False,
            "empty_is_ready": False,
            "proved": False,
            "live_catalog": False,
            "live_packages": False,
            "commercial_products": False,
            "current": False,
            "packages": None,
            "sold_count": None,
            "margin_idr": None,
            "yanolja_live": False,
            "yanolja_called": False,
            "yanolja_write": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_packages": False,
            "invented_sold": False,
            "invented_margin": False,
        }

    def _require_amg_packages_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Packages framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Packages as products is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._amg_packages_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._amg_packages_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _amg_packages_refuse_code(self, path: str) -> str | None:
        if path in {"/api/amg/packages-products/payment", "/api/amg/packages-products/money"}:
            return "payment"
        if path in {"/api/amg/packages-products/bank", "/api/amg/packages-products/transfer"}:
            return "bank"
        if path in {"/api/amg/packages-products/zayen", "/api/amg/packages-products/books"}:
            return "books"
        if path in {"/api/amg/packages-products/yanolja", "/api/amg/packages-products/yanolja-write"}:
            return "yanolja"
        if path in {
            "/api/amg/packages-products/sold",
            "/api/amg/packages-products/sold-count",
            "/api/amg/packages-products/packages",
            "/api/amg/packages-products/margin-idr",
            "/api/amg/packages-products/current",
        }:
            return "current"
        if path in {"/api/amg/packages-products/cloudflare", "/api/amg/packages-products/cf"}:
            return "cloudflare"
        if path in {"/api/amg/packages-products/access", "/api/amg/packages-products/cf-access"}:
            return "access"
        if path in {"/api/amg/packages-products/prove", "/api/amg/packages-products/proven"}:
            return "prove"
        if path == "/api/amg/packages-products/ready":
            return "ready"
        if path == "/api/amg/packages-products/resolve":
            return "resolve"
        if path in {
            "/api/amg/packages-products/production",
            "/api/amg/packages-products/production/mutate",
        }:
            return "production"
        if path in {"/api/amg/packages-products/score", "/api/amg/packages-products/credits"}:
            return "score"
        if path in {"/api/amg/packages-products/fill", "/api/amg/packages-products/note"}:
            return "fill"
        if path == "/api/amg/packages-products/alchemist":
            return "alchemist"
        return None

    def _amg_packages_fail(self, exc: _amg_packages.PackagesProductsError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "yanolja_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._amg_packages_quiet(),
                **_amg_packages.honesty_flags(),
            },
            status=status,
        )

    def _amg_packages_write_refused(self, path: str) -> None:
        identity = self._require_amg_packages_owner()
        if identity is None:
            return
        try:
            code = self._amg_packages_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail == "margin":
                code = "current"
            elif code is None and tail in {
                "stay",
                "activity",
                "stay+activity",
                "sop",
                "notes",
            }:
                code = "fill"
            if code == "payment":
                _amg_packages.refuse_payment({})
            elif code == "bank":
                _amg_packages.refuse_bank({})
            elif code == "books":
                _amg_packages.refuse_books({})
            elif code == "yanolja":
                _amg_packages.refuse_yanolja({})
            elif code == "current":
                _amg_packages.refuse_current({})
            elif code == "cloudflare":
                _amg_packages.refuse_cloudflare({})
            elif code == "access":
                _amg_packages.refuse_access({})
            elif code == "prove":
                _amg_packages.refuse_proven({})
            elif code == "ready":
                _amg_packages.refuse_ready({})
            elif code == "resolve":
                _amg_packages.refuse_resolve({})
            elif code == "production":
                _amg_packages.refuse_production({})
            elif code == "score":
                _amg_packages.refuse_score({})
            elif code == "fill":
                _amg_packages.refuse_fill({})
            elif code == "alchemist":
                _amg_packages.refuse_alchemist({})
            else:
                _amg_packages.refuse_external_write({})
        except _amg_packages.PackagesProductsError as exc:
            self._amg_packages_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Packages framework does not store a live package catalog.",
                **self._amg_packages_quiet(),
            },
            status=405,
        )

    def _amg_packages_page(self) -> None:
        identity = self._require_amg_packages_owner()
        if identity is None:
            return
        page = DASHBOARDS / "amg-packages-products.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Packages as products page is missing.",
                    **self._amg_packages_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _amg_packages_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_amg_packages_owner()
        if identity is None:
            return
        try:
            _amg_packages.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                packages=(qs.get("packages") or [""])[0],
                sold=(qs.get("sold") or [""])[0],
                margin=(qs.get("margin") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _amg_packages.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._amg_packages_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _amg_packages.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._amg_packages_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _amg_packages.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._amg_packages_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _amg_packages.read_kind(ref_id)
            else:
                report = _amg_packages.build_framework()
        except _amg_packages.PackagesProductsError as exc:
            self._amg_packages_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _amg_yield_quiet(self) -> dict:
        return {
            "empty_is_revenue": False,
            "empty_is_yield": False,
            "empty_is_ready": False,
            "proved": False,
            "live_revenue": False,
            "live_yield": False,
            "yield_machinery": False,
            "current": False,
            "rates": None,
            "occupancy": None,
            "adr": None,
            "revpar": None,
            "yield_value": None,
            "yanolja_live": False,
            "yanolja_called": False,
            "yanolja_write": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_rates": False,
            "invented_occupancy": False,
            "invented_adr": False,
            "invented_revpar": False,
        }

    def _require_amg_yield_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Revenue framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Hotel revenue and yield is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._amg_yield_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._amg_yield_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _amg_yield_refuse_code(self, path: str) -> str | None:
        if path in {"/api/amg/revenue-yield/payment", "/api/amg/revenue-yield/money"}:
            return "payment"
        if path in {"/api/amg/revenue-yield/bank", "/api/amg/revenue-yield/transfer"}:
            return "bank"
        if path in {"/api/amg/revenue-yield/zayen", "/api/amg/revenue-yield/books"}:
            return "books"
        if path in {"/api/amg/revenue-yield/yanolja", "/api/amg/revenue-yield/yanolja-write"}:
            return "yanolja"
        if path == "/api/amg/revenue-yield/current":
            return "current"
        if path in {"/api/amg/revenue-yield/cloudflare", "/api/amg/revenue-yield/cf"}:
            return "cloudflare"
        if path in {"/api/amg/revenue-yield/access", "/api/amg/revenue-yield/cf-access"}:
            return "access"
        if path in {"/api/amg/revenue-yield/prove", "/api/amg/revenue-yield/proven"}:
            return "prove"
        if path == "/api/amg/revenue-yield/ready":
            return "ready"
        if path == "/api/amg/revenue-yield/resolve":
            return "resolve"
        if path in {
            "/api/amg/revenue-yield/production",
            "/api/amg/revenue-yield/production/mutate",
        }:
            return "production"
        if path in {"/api/amg/revenue-yield/score", "/api/amg/revenue-yield/credits"}:
            return "score"
        if path in {"/api/amg/revenue-yield/fill", "/api/amg/revenue-yield/note"}:
            return "fill"
        if path == "/api/amg/revenue-yield/alchemist":
            return "alchemist"
        return None

    def _amg_yield_fail(self, exc: _amg_yield.RevenueYieldError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "yanolja_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._amg_yield_quiet(),
                **_amg_yield.honesty_flags(),
            },
            status=status,
        )

    def _amg_yield_write_refused(self, path: str) -> None:
        identity = self._require_amg_yield_owner()
        if identity is None:
            return
        try:
            code = self._amg_yield_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {"rates", "occupancy", "adr", "revpar", "yield"}:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _amg_yield.refuse_payment({})
            elif code == "bank":
                _amg_yield.refuse_bank({})
            elif code == "books":
                _amg_yield.refuse_books({})
            elif code == "yanolja":
                _amg_yield.refuse_yanolja({})
            elif code == "current":
                _amg_yield.refuse_current({})
            elif code == "cloudflare":
                _amg_yield.refuse_cloudflare({})
            elif code == "access":
                _amg_yield.refuse_access({})
            elif code == "prove":
                _amg_yield.refuse_proven({})
            elif code == "ready":
                _amg_yield.refuse_ready({})
            elif code == "resolve":
                _amg_yield.refuse_resolve({})
            elif code == "production":
                _amg_yield.refuse_production({})
            elif code == "score":
                _amg_yield.refuse_score({})
            elif code == "fill":
                _amg_yield.refuse_fill({})
            elif code == "alchemist":
                _amg_yield.refuse_alchemist({})
            else:
                _amg_yield.refuse_external_write({})
        except _amg_yield.RevenueYieldError as exc:
            self._amg_yield_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Revenue framework does not store live revenue or yield.",
                **self._amg_yield_quiet(),
            },
            status=405,
        )

    def _amg_yield_page(self) -> None:
        identity = self._require_amg_yield_owner()
        if identity is None:
            return
        page = DASHBOARDS / "amg-revenue-yield.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Hotel revenue and yield page is missing.",
                    **self._amg_yield_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _amg_yield_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_amg_yield_owner()
        if identity is None:
            return
        try:
            _amg_yield.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                rates=(qs.get("rates") or [""])[0],
                occupancy=(qs.get("occupancy") or [""])[0],
                adr=(qs.get("adr") or [""])[0],
                revpar=(qs.get("revpar") or [""])[0],
                hotel_yield=(qs.get("yield") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _amg_yield.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._amg_yield_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _amg_yield.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._amg_yield_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _amg_yield.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._amg_yield_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _amg_yield.read_kind(ref_id)
            else:
                report = _amg_yield.build_framework()
        except _amg_yield.RevenueYieldError as exc:
            self._amg_yield_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _amg_improve_quiet(self) -> dict:
        return {
            "empty_is_review_loop": False,
            "empty_is_service_improve": False,
            "empty_is_ready": False,
            "proved": False,
            "live_review": False,
            "live_improve": False,
            "improve_machinery": False,
            "current": False,
            "review": None,
            "review_score": None,
            "finding": None,
            "action": None,
            "action_outcome": None,
            "owner": None,
            "due": None,
            "guest_blast": False,
            "public_post": False,
            "yanolja_live": False,
            "yanolja_called": False,
            "yanolja_write": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_review": False,
            "invented_finding": False,
            "invented_action": False,
        }

    def _require_amg_improve_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Service improve framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Service improvement loop is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._amg_improve_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._amg_improve_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _amg_improve_refuse_code(self, path: str) -> str | None:
        if path in {"/api/amg/service-improve/payment", "/api/amg/service-improve/money"}:
            return "payment"
        if path in {"/api/amg/service-improve/bank", "/api/amg/service-improve/transfer"}:
            return "bank"
        if path in {"/api/amg/service-improve/zayen", "/api/amg/service-improve/books"}:
            return "books"
        if path in {"/api/amg/service-improve/yanolja", "/api/amg/service-improve/yanolja-write"}:
            return "yanolja"
        if path in {
            "/api/amg/service-improve/guest-blast",
            "/api/amg/service-improve/guest",
            "/api/amg/service-improve/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/amg/service-improve/public-post",
            "/api/amg/service-improve/public",
            "/api/amg/service-improve/post",
            "/api/amg/service-improve/publish",
        }:
            return "public_post"
        if path == "/api/amg/service-improve/current":
            return "current"
        if path in {"/api/amg/service-improve/cloudflare", "/api/amg/service-improve/cf"}:
            return "cloudflare"
        if path in {"/api/amg/service-improve/access", "/api/amg/service-improve/cf-access"}:
            return "access"
        if path in {"/api/amg/service-improve/prove", "/api/amg/service-improve/proven"}:
            return "prove"
        if path == "/api/amg/service-improve/ready":
            return "ready"
        if path == "/api/amg/service-improve/resolve":
            return "resolve"
        if path in {
            "/api/amg/service-improve/production",
            "/api/amg/service-improve/production/mutate",
        }:
            return "production"
        if path in {"/api/amg/service-improve/score", "/api/amg/service-improve/credits"}:
            return "score"
        if path in {"/api/amg/service-improve/fill", "/api/amg/service-improve/note"}:
            return "fill"
        if path == "/api/amg/service-improve/alchemist":
            return "alchemist"
        return None

    def _amg_improve_fail(self, exc: _amg_improve.ServiceImproveError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "yanolja_refused",
            "guest_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._amg_improve_quiet(),
                **_amg_improve.honesty_flags(),
            },
            status=status,
        )

    def _amg_improve_write_refused(self, path: str) -> None:
        identity = self._require_amg_improve_owner()
        if identity is None:
            return
        try:
            code = self._amg_improve_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "review",
                "finding",
                "action",
                "owner",
                "due",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _amg_improve.refuse_payment({})
            elif code == "bank":
                _amg_improve.refuse_bank({})
            elif code == "books":
                _amg_improve.refuse_books({})
            elif code == "yanolja":
                _amg_improve.refuse_yanolja({})
            elif code == "guest_blast":
                _amg_improve.refuse_guest_blast({})
            elif code == "public_post":
                _amg_improve.refuse_public_post({})
            elif code == "current":
                _amg_improve.refuse_current({})
            elif code == "cloudflare":
                _amg_improve.refuse_cloudflare({})
            elif code == "access":
                _amg_improve.refuse_access({})
            elif code == "prove":
                _amg_improve.refuse_proven({})
            elif code == "ready":
                _amg_improve.refuse_ready({})
            elif code == "resolve":
                _amg_improve.refuse_resolve({})
            elif code == "production":
                _amg_improve.refuse_production({})
            elif code == "score":
                _amg_improve.refuse_score({})
            elif code == "fill":
                _amg_improve.refuse_fill({})
            elif code == "alchemist":
                _amg_improve.refuse_alchemist({})
            else:
                _amg_improve.refuse_external_write({})
        except _amg_improve.ServiceImproveError as exc:
            self._amg_improve_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Service improve framework does not store a live review-to-improve loop.",
                **self._amg_improve_quiet(),
            },
            status=405,
        )

    def _amg_improve_page(self) -> None:
        identity = self._require_amg_improve_owner()
        if identity is None:
            return
        page = DASHBOARDS / "amg-service-improve.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Service improvement loop page is missing.",
                    **self._amg_improve_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _amg_improve_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_amg_improve_owner()
        if identity is None:
            return
        try:
            _amg_improve.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                review=(qs.get("review") or [""])[0],
                finding=(qs.get("finding") or [""])[0],
                action=(qs.get("action") or [""])[0],
                owner=(qs.get("owner") or [""])[0],
                due=(qs.get("due") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _amg_improve.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._amg_improve_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _amg_improve.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._amg_improve_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _amg_improve.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._amg_improve_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _amg_improve.read_kind(ref_id)
            else:
                report = _amg_improve.build_framework()
        except _amg_improve.ServiceImproveError as exc:
            self._amg_improve_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _amg_sla_quiet(self) -> dict:
        return {
            "empty_is_sla_trail": False,
            "empty_is_guest_experience": False,
            "empty_is_ready": False,
            "proved": False,
            "live_request": False,
            "live_incident": False,
            "live_sla": False,
            "guest_experience_machinery": False,
            "current": False,
            "request": None,
            "incident": None,
            "incident_number": None,
            "sla": None,
            "sla_timer": None,
            "escalation": None,
            "escalation_outcome": None,
            "trail": None,
            "guest_blast": False,
            "public_post": False,
            "yanolja_live": False,
            "yanolja_called": False,
            "yanolja_write": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_incident": False,
            "invented_sla": False,
            "invented_escalation": False,
        }

    def _require_amg_sla_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. SLA/incident framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "SLA/incident trail is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._amg_sla_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._amg_sla_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _amg_sla_refuse_code(self, path: str) -> str | None:
        if path in {"/api/amg/sla-incident/payment", "/api/amg/sla-incident/money"}:
            return "payment"
        if path in {"/api/amg/sla-incident/bank", "/api/amg/sla-incident/transfer"}:
            return "bank"
        if path in {"/api/amg/sla-incident/zayen", "/api/amg/sla-incident/books"}:
            return "books"
        if path in {"/api/amg/sla-incident/yanolja", "/api/amg/sla-incident/yanolja-write"}:
            return "yanolja"
        if path in {
            "/api/amg/sla-incident/guest-blast",
            "/api/amg/sla-incident/guest",
            "/api/amg/sla-incident/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/amg/sla-incident/public-post",
            "/api/amg/sla-incident/public",
            "/api/amg/sla-incident/post",
            "/api/amg/sla-incident/publish",
        }:
            return "public_post"
        if path == "/api/amg/sla-incident/current":
            return "current"
        if path in {"/api/amg/sla-incident/cloudflare", "/api/amg/sla-incident/cf"}:
            return "cloudflare"
        if path in {"/api/amg/sla-incident/access", "/api/amg/sla-incident/cf-access"}:
            return "access"
        if path in {"/api/amg/sla-incident/prove", "/api/amg/sla-incident/proven"}:
            return "prove"
        if path == "/api/amg/sla-incident/ready":
            return "ready"
        if path == "/api/amg/sla-incident/resolve":
            return "resolve"
        if path in {
            "/api/amg/sla-incident/production",
            "/api/amg/sla-incident/production/mutate",
        }:
            return "production"
        if path in {"/api/amg/sla-incident/score", "/api/amg/sla-incident/credits"}:
            return "score"
        if path in {"/api/amg/sla-incident/fill", "/api/amg/sla-incident/note"}:
            return "fill"
        if path == "/api/amg/sla-incident/alchemist":
            return "alchemist"
        return None

    def _amg_sla_fail(self, exc: _amg_sla.SlaIncidentError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "yanolja_refused",
            "guest_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._amg_sla_quiet(),
                **_amg_sla.honesty_flags(),
            },
            status=status,
        )

    def _amg_sla_write_refused(self, path: str) -> None:
        identity = self._require_amg_sla_owner()
        if identity is None:
            return
        try:
            code = self._amg_sla_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "request",
                "incident",
                "sla",
                "escalation",
                "trail",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _amg_sla.refuse_payment({})
            elif code == "bank":
                _amg_sla.refuse_bank({})
            elif code == "books":
                _amg_sla.refuse_books({})
            elif code == "yanolja":
                _amg_sla.refuse_yanolja({})
            elif code == "guest_blast":
                _amg_sla.refuse_guest_blast({})
            elif code == "public_post":
                _amg_sla.refuse_public_post({})
            elif code == "current":
                _amg_sla.refuse_current({})
            elif code == "cloudflare":
                _amg_sla.refuse_cloudflare({})
            elif code == "access":
                _amg_sla.refuse_access({})
            elif code == "prove":
                _amg_sla.refuse_proven({})
            elif code == "ready":
                _amg_sla.refuse_ready({})
            elif code == "resolve":
                _amg_sla.refuse_resolve({})
            elif code == "production":
                _amg_sla.refuse_production({})
            elif code == "score":
                _amg_sla.refuse_score({})
            elif code == "fill":
                _amg_sla.refuse_fill({})
            elif code == "alchemist":
                _amg_sla.refuse_alchemist({})
            else:
                _amg_sla.refuse_external_write({})
        except _amg_sla.SlaIncidentError as exc:
            self._amg_sla_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "SLA/incident framework does not store a live SLA/incident trail.",
                **self._amg_sla_quiet(),
            },
            status=405,
        )

    def _amg_sla_page(self) -> None:
        identity = self._require_amg_sla_owner()
        if identity is None:
            return
        page = DASHBOARDS / "amg-sla-incident.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "SLA/incident trail page is missing.",
                    **self._amg_sla_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _amg_sla_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_amg_sla_owner()
        if identity is None:
            return
        try:
            _amg_sla.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                request=(qs.get("request") or [""])[0],
                incident=(qs.get("incident") or [""])[0],
                sla=(qs.get("sla") or [""])[0],
                escalation=(qs.get("escalation") or [""])[0],
                trail=(qs.get("trail") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _amg_sla.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._amg_sla_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _amg_sla.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._amg_sla_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _amg_sla.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._amg_sla_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _amg_sla.read_kind(ref_id)
            else:
                report = _amg_sla.build_framework()
        except _amg_sla.SlaIncidentError as exc:
            self._amg_sla_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _amg_pms_quiet(self) -> dict:
        return {
            "empty_is_pms_orchestration": False,
            "empty_is_yanolja_maturity": False,
            "empty_is_ready": False,
            "proved": False,
            "live_pms": False,
            "live_pms_orchestration": False,
            "yanolja_connector_maturity": False,
            "current": False,
            "pms": None,
            "pms_number": None,
            "rooms": None,
            "room_number": None,
            "reservations": None,
            "reservation_number": None,
            "guests": None,
            "guest_number": None,
            "orchestration": None,
            "guest_blast": False,
            "public_post": False,
            "yanolja_live": False,
            "yanolja_called": False,
            "yanolja_write": False,
            "yanolja_credentials": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_pms": False,
            "invented_rooms": False,
            "invented_reservations": False,
            "invented_guests": False,
        }

    def _require_amg_pms_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. PMS orchestration framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Hotel PMS orchestration is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._amg_pms_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._amg_pms_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _amg_pms_refuse_code(self, path: str) -> str | None:
        if path in {"/api/amg/pms-orchestration/payment", "/api/amg/pms-orchestration/money"}:
            return "payment"
        if path in {"/api/amg/pms-orchestration/bank", "/api/amg/pms-orchestration/transfer"}:
            return "bank"
        if path in {"/api/amg/pms-orchestration/zayen", "/api/amg/pms-orchestration/books"}:
            return "books"
        if path in {
            "/api/amg/pms-orchestration/yanolja",
            "/api/amg/pms-orchestration/yanolja-write",
            "/api/amg/pms-orchestration/yanolja-connector",
            "/api/amg/pms-orchestration/credentials",
        }:
            return "yanolja"
        if path in {
            "/api/amg/pms-orchestration/guest-blast",
            "/api/amg/pms-orchestration/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/amg/pms-orchestration/public-post",
            "/api/amg/pms-orchestration/public",
            "/api/amg/pms-orchestration/post",
            "/api/amg/pms-orchestration/publish",
        }:
            return "public_post"
        if path == "/api/amg/pms-orchestration/current":
            return "current"
        if path in {"/api/amg/pms-orchestration/cloudflare", "/api/amg/pms-orchestration/cf"}:
            return "cloudflare"
        if path in {"/api/amg/pms-orchestration/access", "/api/amg/pms-orchestration/cf-access"}:
            return "access"
        if path in {"/api/amg/pms-orchestration/prove", "/api/amg/pms-orchestration/proven"}:
            return "prove"
        if path == "/api/amg/pms-orchestration/ready":
            return "ready"
        if path == "/api/amg/pms-orchestration/resolve":
            return "resolve"
        if path in {
            "/api/amg/pms-orchestration/production",
            "/api/amg/pms-orchestration/production/mutate",
        }:
            return "production"
        if path in {"/api/amg/pms-orchestration/score", "/api/amg/pms-orchestration/credits"}:
            return "score"
        if path in {"/api/amg/pms-orchestration/fill", "/api/amg/pms-orchestration/note"}:
            return "fill"
        if path == "/api/amg/pms-orchestration/alchemist":
            return "alchemist"
        return None

    def _amg_pms_fail(self, exc: _amg_pms.PmsOrchestrationError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "yanolja_refused",
            "guest_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._amg_pms_quiet(),
                **_amg_pms.honesty_flags(),
            },
            status=status,
        )

    def _amg_pms_write_refused(self, path: str) -> None:
        identity = self._require_amg_pms_owner()
        if identity is None:
            return
        try:
            code = self._amg_pms_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "pms",
                "rooms",
                "reservations",
                "guests",
                "orchestration",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _amg_pms.refuse_payment({})
            elif code == "bank":
                _amg_pms.refuse_bank({})
            elif code == "books":
                _amg_pms.refuse_books({})
            elif code == "yanolja":
                _amg_pms.refuse_yanolja({})
            elif code == "guest_blast":
                _amg_pms.refuse_guest_blast({})
            elif code == "public_post":
                _amg_pms.refuse_public_post({})
            elif code == "current":
                _amg_pms.refuse_current({})
            elif code == "cloudflare":
                _amg_pms.refuse_cloudflare({})
            elif code == "access":
                _amg_pms.refuse_access({})
            elif code == "prove":
                _amg_pms.refuse_proven({})
            elif code == "ready":
                _amg_pms.refuse_ready({})
            elif code == "resolve":
                _amg_pms.refuse_resolve({})
            elif code == "production":
                _amg_pms.refuse_production({})
            elif code == "score":
                _amg_pms.refuse_score({})
            elif code == "fill":
                _amg_pms.refuse_fill({})
            elif code == "alchemist":
                _amg_pms.refuse_alchemist({})
            else:
                _amg_pms.refuse_external_write({})
        except _amg_pms.PmsOrchestrationError as exc:
            self._amg_pms_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "PMS orchestration framework does not store a live PMS orchestration.",
                **self._amg_pms_quiet(),
            },
            status=405,
        )

    def _amg_pms_page(self) -> None:
        identity = self._require_amg_pms_owner()
        if identity is None:
            return
        page = DASHBOARDS / "amg-pms-orchestration.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Hotel PMS orchestration page is missing.",
                    **self._amg_pms_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _amg_pms_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_amg_pms_owner()
        if identity is None:
            return
        try:
            _amg_pms.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                pms=(qs.get("pms") or [""])[0],
                rooms=(qs.get("rooms") or [""])[0],
                reservations=(qs.get("reservations") or [""])[0],
                guests=(qs.get("guests") or [""])[0],
                orchestration=(qs.get("orchestration") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _amg_pms.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._amg_pms_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _amg_pms.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._amg_pms_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _amg_pms.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._amg_pms_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _amg_pms.read_kind(ref_id)
            else:
                report = _amg_pms.build_framework()
        except _amg_pms.PmsOrchestrationError as exc:
            self._amg_pms_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)


    def _hr_hire_quiet(self) -> dict:
        return {
            "empty_is_hiring_onboarding": False,
            "empty_is_hr_hire_machinery": False,
            "empty_is_ready": False,
            "proved": False,
            "live_hiring": False,
            "live_hiring_onboarding": False,
            "hr_hire_machinery": False,
            "current": False,
            "requisition": None,
            "requisition_number": None,
            "candidate": None,
            "candidate_number": None,
            "hire": None,
            "hire_number": None,
            "offer": None,
            "offer_number": None,
            "onboarding": None,
            "onboarding_number": None,
            "checklist": None,
            "guest_blast": False,
            "staff_blast": False,
            "public_post": False,
            "hr_master_write": False,
            "payroll_executed": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_hire": False,
            "invented_candidate": False,
            "invented_offer": False,
            "invented_onboarding": False,
        }

    def _require_hr_hire_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Hiring & onboarding framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Hiring & Onboarding is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._hr_hire_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._hr_hire_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _hr_hire_refuse_code(self, path: str) -> str | None:
        if path in {"/api/hr/hiring-onboarding/payment", "/api/hr/hiring-onboarding/money"}:
            return "payment"
        if path in {"/api/hr/hiring-onboarding/bank", "/api/hr/hiring-onboarding/transfer"}:
            return "bank"
        if path in {"/api/hr/hiring-onboarding/zayen", "/api/hr/hiring-onboarding/books"}:
            return "books"
        if path in {
            "/api/hr/hiring-onboarding/payroll",
            "/api/hr/hiring-onboarding/payroll-execute",
        }:
            return "payroll"
        if path in {
            "/api/hr/hiring-onboarding/hr-master",
            "/api/hr/hiring-onboarding/people-master",
        }:
            return "hr_master"
        if path in {
            "/api/hr/hiring-onboarding/guest-blast",
            "/api/hr/hiring-onboarding/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/hr/hiring-onboarding/staff-blast",
            "/api/hr/hiring-onboarding/staff-broadcast",
        }:
            return "staff_blast"
        if path in {
            "/api/hr/hiring-onboarding/public-post",
            "/api/hr/hiring-onboarding/public",
            "/api/hr/hiring-onboarding/post",
            "/api/hr/hiring-onboarding/publish",
        }:
            return "public_post"
        if path == "/api/hr/hiring-onboarding/current":
            return "current"
        if path in {"/api/hr/hiring-onboarding/cloudflare", "/api/hr/hiring-onboarding/cf"}:
            return "cloudflare"
        if path in {"/api/hr/hiring-onboarding/access", "/api/hr/hiring-onboarding/cf-access"}:
            return "access"
        if path in {"/api/hr/hiring-onboarding/prove", "/api/hr/hiring-onboarding/proven"}:
            return "prove"
        if path == "/api/hr/hiring-onboarding/ready":
            return "ready"
        if path == "/api/hr/hiring-onboarding/resolve":
            return "resolve"
        if path in {
            "/api/hr/hiring-onboarding/production",
            "/api/hr/hiring-onboarding/production/mutate",
        }:
            return "production"
        if path in {"/api/hr/hiring-onboarding/score", "/api/hr/hiring-onboarding/credits"}:
            return "score"
        if path in {"/api/hr/hiring-onboarding/fill", "/api/hr/hiring-onboarding/note"}:
            return "fill"
        if path == "/api/hr/hiring-onboarding/alchemist":
            return "alchemist"
        return None

    def _hr_hire_fail(self, exc: _hr_hire.HiringOnboardingError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "payroll_refused",
            "hr_master_refused",
            "guest_blast_refused",
            "staff_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._hr_hire_quiet(),
                **_hr_hire.honesty_flags(),
            },
            status=status,
        )

    def _hr_hire_write_refused(self, path: str) -> None:
        identity = self._require_hr_hire_owner()
        if identity is None:
            return
        try:
            code = self._hr_hire_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "requisition",
                "candidate",
                "offer",
                "onboarding",
                "checklist",
                "hire",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _hr_hire.refuse_payment({})
            elif code == "bank":
                _hr_hire.refuse_bank({})
            elif code == "books":
                _hr_hire.refuse_books({})
            elif code == "payroll":
                _hr_hire.refuse_payroll({})
            elif code == "hr_master":
                _hr_hire.refuse_hr_master({})
            elif code == "guest_blast":
                _hr_hire.refuse_guest_blast({})
            elif code == "staff_blast":
                _hr_hire.refuse_staff_blast({})
            elif code == "public_post":
                _hr_hire.refuse_public_post({})
            elif code == "current":
                _hr_hire.refuse_current({})
            elif code == "cloudflare":
                _hr_hire.refuse_cloudflare({})
            elif code == "access":
                _hr_hire.refuse_access({})
            elif code == "prove":
                _hr_hire.refuse_proven({})
            elif code == "ready":
                _hr_hire.refuse_ready({})
            elif code == "resolve":
                _hr_hire.refuse_resolve({})
            elif code == "production":
                _hr_hire.refuse_production({})
            elif code == "score":
                _hr_hire.refuse_score({})
            elif code == "fill":
                _hr_hire.refuse_fill({})
            elif code == "alchemist":
                _hr_hire.refuse_alchemist({})
            else:
                _hr_hire.refuse_external_write({})
        except _hr_hire.HiringOnboardingError as exc:
            self._hr_hire_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Hiring & onboarding framework does not store a live hiring workflow.",
                **self._hr_hire_quiet(),
            },
            status=405,
        )

    def _hr_hire_page(self) -> None:
        identity = self._require_hr_hire_owner()
        if identity is None:
            return
        page = DASHBOARDS / "hr-hiring-onboarding.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Hiring & Onboarding page is missing.",
                    **self._hr_hire_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _hr_hire_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_hr_hire_owner()
        if identity is None:
            return
        try:
            _hr_hire.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                payroll=(qs.get("payroll") or [""])[0],
                hr_master=(qs.get("hr_master") or qs.get("hr-master") or [""])[0],
                requisition=(qs.get("requisition") or [""])[0],
                candidate=(qs.get("candidate") or [""])[0],
                hire=(qs.get("hire") or [""])[0],
                offer=(qs.get("offer") or [""])[0],
                onboarding=(qs.get("onboarding") or [""])[0],
                checklist=(qs.get("checklist") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                staff_blast=(qs.get("staff_blast") or qs.get("staff-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _hr_hire.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._hr_hire_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _hr_hire.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._hr_hire_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _hr_hire.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._hr_hire_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _hr_hire.read_kind(ref_id)
            else:
                report = _hr_hire.build_framework()
        except _hr_hire.HiringOnboardingError as exc:
            self._hr_hire_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)


    def _hr_train_quiet(self) -> dict:
        return {
            "empty_is_training_competency": False,
            "empty_is_hr_training_machinery": False,
            "empty_is_ready": False,
            "proved": False,
            "live_training": False,
            "live_training_competency": False,
            "hr_training_machinery": False,
            "current": False,
            "training_module": None,
            "training_module_number": None,
            "training": None,
            "training_number": None,
            "competency": None,
            "competency_score": None,
            "acknowledgement": None,
            "acknowledgement_number": None,
            "checklist": None,
            "guest_blast": False,
            "staff_blast": False,
            "public_post": False,
            "hr_master_write": False,
            "payroll_executed": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_training": False,
            "invented_competency": False,
            "invented_acknowledgement": False,
        }

    def _require_hr_train_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Training & competency framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Training & Competency is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._hr_train_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._hr_train_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _hr_train_refuse_code(self, path: str) -> str | None:
        if path in {"/api/hr/training-competency/payment", "/api/hr/training-competency/money"}:
            return "payment"
        if path in {"/api/hr/training-competency/bank", "/api/hr/training-competency/transfer"}:
            return "bank"
        if path in {"/api/hr/training-competency/zayen", "/api/hr/training-competency/books"}:
            return "books"
        if path in {
            "/api/hr/training-competency/payroll",
            "/api/hr/training-competency/payroll-execute",
        }:
            return "payroll"
        if path in {
            "/api/hr/training-competency/hr-master",
            "/api/hr/training-competency/people-master",
        }:
            return "hr_master"
        if path in {
            "/api/hr/training-competency/guest-blast",
            "/api/hr/training-competency/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/hr/training-competency/staff-blast",
            "/api/hr/training-competency/staff-broadcast",
        }:
            return "staff_blast"
        if path in {
            "/api/hr/training-competency/public-post",
            "/api/hr/training-competency/public",
            "/api/hr/training-competency/post",
            "/api/hr/training-competency/publish",
        }:
            return "public_post"
        if path == "/api/hr/training-competency/current":
            return "current"
        if path in {"/api/hr/training-competency/cloudflare", "/api/hr/training-competency/cf"}:
            return "cloudflare"
        if path in {"/api/hr/training-competency/access", "/api/hr/training-competency/cf-access"}:
            return "access"
        if path in {"/api/hr/training-competency/prove", "/api/hr/training-competency/proven"}:
            return "prove"
        if path == "/api/hr/training-competency/ready":
            return "ready"
        if path == "/api/hr/training-competency/resolve":
            return "resolve"
        if path in {
            "/api/hr/training-competency/production",
            "/api/hr/training-competency/production/mutate",
        }:
            return "production"
        if path in {"/api/hr/training-competency/score", "/api/hr/training-competency/credits"}:
            return "score"
        if path in {"/api/hr/training-competency/fill", "/api/hr/training-competency/note"}:
            return "fill"
        if path == "/api/hr/training-competency/alchemist":
            return "alchemist"
        return None

    def _hr_train_fail(self, exc: _hr_train.TrainingCompetencyError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "payroll_refused",
            "hr_master_refused",
            "guest_blast_refused",
            "staff_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._hr_train_quiet(),
                **_hr_train.honesty_flags(),
            },
            status=status,
        )

    def _hr_train_write_refused(self, path: str) -> None:
        identity = self._require_hr_train_owner()
        if identity is None:
            return
        try:
            code = self._hr_train_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "training_module",
                "training-module",
                "training",
                "competency",
                "acknowledgement",
                "checklist",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _hr_train.refuse_payment({})
            elif code == "bank":
                _hr_train.refuse_bank({})
            elif code == "books":
                _hr_train.refuse_books({})
            elif code == "payroll":
                _hr_train.refuse_payroll({})
            elif code == "hr_master":
                _hr_train.refuse_hr_master({})
            elif code == "guest_blast":
                _hr_train.refuse_guest_blast({})
            elif code == "staff_blast":
                _hr_train.refuse_staff_blast({})
            elif code == "public_post":
                _hr_train.refuse_public_post({})
            elif code == "current":
                _hr_train.refuse_current({})
            elif code == "cloudflare":
                _hr_train.refuse_cloudflare({})
            elif code == "access":
                _hr_train.refuse_access({})
            elif code == "prove":
                _hr_train.refuse_proven({})
            elif code == "ready":
                _hr_train.refuse_ready({})
            elif code == "resolve":
                _hr_train.refuse_resolve({})
            elif code == "production":
                _hr_train.refuse_production({})
            elif code == "score":
                _hr_train.refuse_score({})
            elif code == "fill":
                _hr_train.refuse_fill({})
            elif code == "alchemist":
                _hr_train.refuse_alchemist({})
            else:
                _hr_train.refuse_external_write({})
        except _hr_train.TrainingCompetencyError as exc:
            self._hr_train_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Training & competency framework does not store a live training workflow.",
                **self._hr_train_quiet(),
            },
            status=405,
        )

    def _hr_train_page(self) -> None:
        identity = self._require_hr_train_owner()
        if identity is None:
            return
        page = DASHBOARDS / "hr-training-competency.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Training & Competency page is missing.",
                    **self._hr_train_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _hr_train_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_hr_train_owner()
        if identity is None:
            return
        try:
            _hr_train.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                payroll=(qs.get("payroll") or [""])[0],
                hr_master=(qs.get("hr_master") or qs.get("hr-master") or [""])[0],
                training_module=(qs.get("training_module") or qs.get("training-module") or [""])[0],
                training=(qs.get("training") or [""])[0],
                competency=(qs.get("competency") or [""])[0],
                acknowledgement=(qs.get("acknowledgement") or [""])[0],
                checklist=(qs.get("checklist") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                staff_blast=(qs.get("staff_blast") or qs.get("staff-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _hr_train.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._hr_train_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _hr_train.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._hr_train_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _hr_train.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._hr_train_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _hr_train.read_kind(ref_id)
            else:
                report = _hr_train.build_framework()
        except _hr_train.TrainingCompetencyError as exc:
            self._hr_train_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)


    def _hr_pay_quiet(self) -> dict:
        return {
            "empty_is_payroll_inputs": False,
            "empty_is_payroll_execute": False,
            "empty_is_ready": False,
            "proved": False,
            "live_attendance": False,
            "live_payroll_inputs": False,
            "payroll_execute_machinery": False,
            "payslip_machinery": False,
            "current": False,
            "attendance": None,
            "attendance_number": None,
            "leave": None,
            "leave_number": None,
            "pay_input": None,
            "pay_input_number": None,
            "payslip": None,
            "payslip_number": None,
            "checklist": None,
            "guest_blast": False,
            "staff_blast": False,
            "public_post": False,
            "hr_master_write": False,
            "payroll_executed": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_attendance": False,
            "invented_leave": False,
            "invented_pay_input": False,
            "invented_payslip": False,
        }

    def _require_hr_pay_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Payroll inputs framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Payroll Inputs is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._hr_pay_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._hr_pay_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _hr_pay_refuse_code(self, path: str) -> str | None:
        if path in {"/api/hr/payroll-inputs/payment", "/api/hr/payroll-inputs/money"}:
            return "payment"
        if path in {"/api/hr/payroll-inputs/bank", "/api/hr/payroll-inputs/transfer"}:
            return "bank"
        if path in {"/api/hr/payroll-inputs/zayen", "/api/hr/payroll-inputs/books"}:
            return "books"
        if path in {
            "/api/hr/payroll-inputs/payroll",
            "/api/hr/payroll-inputs/payroll-execute",
        }:
            return "payroll"
        if path in {
            "/api/hr/payroll-inputs/hr-master",
            "/api/hr/payroll-inputs/people-master",
        }:
            return "hr_master"
        if path in {
            "/api/hr/payroll-inputs/guest-blast",
            "/api/hr/payroll-inputs/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/hr/payroll-inputs/staff-blast",
            "/api/hr/payroll-inputs/staff-broadcast",
        }:
            return "staff_blast"
        if path in {
            "/api/hr/payroll-inputs/public-post",
            "/api/hr/payroll-inputs/public",
            "/api/hr/payroll-inputs/post",
            "/api/hr/payroll-inputs/publish",
        }:
            return "public_post"
        if path == "/api/hr/payroll-inputs/current":
            return "current"
        if path in {"/api/hr/payroll-inputs/cloudflare", "/api/hr/payroll-inputs/cf"}:
            return "cloudflare"
        if path in {"/api/hr/payroll-inputs/access", "/api/hr/payroll-inputs/cf-access"}:
            return "access"
        if path in {"/api/hr/payroll-inputs/prove", "/api/hr/payroll-inputs/proven"}:
            return "prove"
        if path == "/api/hr/payroll-inputs/ready":
            return "ready"
        if path == "/api/hr/payroll-inputs/resolve":
            return "resolve"
        if path in {
            "/api/hr/payroll-inputs/production",
            "/api/hr/payroll-inputs/production/mutate",
        }:
            return "production"
        if path in {"/api/hr/payroll-inputs/score", "/api/hr/payroll-inputs/credits"}:
            return "score"
        if path in {"/api/hr/payroll-inputs/fill", "/api/hr/payroll-inputs/note"}:
            return "fill"
        if path == "/api/hr/payroll-inputs/alchemist":
            return "alchemist"
        return None

    def _hr_pay_fail(self, exc: _hr_pay.PayrollInputsError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "payroll_refused",
            "hr_master_refused",
            "guest_blast_refused",
            "staff_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._hr_pay_quiet(),
                **_hr_pay.honesty_flags(),
            },
            status=status,
        )

    def _hr_pay_write_refused(self, path: str) -> None:
        identity = self._require_hr_pay_owner()
        if identity is None:
            return
        try:
            code = self._hr_pay_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "attendance",
                "leave",
                "pay_input",
                "pay-input",
                "payslip",
                "checklist",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _hr_pay.refuse_payment({})
            elif code == "bank":
                _hr_pay.refuse_bank({})
            elif code == "books":
                _hr_pay.refuse_books({})
            elif code == "payroll":
                _hr_pay.refuse_payroll({})
            elif code == "hr_master":
                _hr_pay.refuse_hr_master({})
            elif code == "guest_blast":
                _hr_pay.refuse_guest_blast({})
            elif code == "staff_blast":
                _hr_pay.refuse_staff_blast({})
            elif code == "public_post":
                _hr_pay.refuse_public_post({})
            elif code == "current":
                _hr_pay.refuse_current({})
            elif code == "cloudflare":
                _hr_pay.refuse_cloudflare({})
            elif code == "access":
                _hr_pay.refuse_access({})
            elif code == "prove":
                _hr_pay.refuse_proven({})
            elif code == "ready":
                _hr_pay.refuse_ready({})
            elif code == "resolve":
                _hr_pay.refuse_resolve({})
            elif code == "production":
                _hr_pay.refuse_production({})
            elif code == "score":
                _hr_pay.refuse_score({})
            elif code == "fill":
                _hr_pay.refuse_fill({})
            elif code == "alchemist":
                _hr_pay.refuse_alchemist({})
            else:
                _hr_pay.refuse_external_write({})
        except _hr_pay.PayrollInputsError as exc:
            self._hr_pay_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Payroll inputs framework does not store a live payroll-inputs workflow.",
                **self._hr_pay_quiet(),
            },
            status=405,
        )

    def _hr_pay_page(self) -> None:
        identity = self._require_hr_pay_owner()
        if identity is None:
            return
        page = DASHBOARDS / "hr-payroll-inputs.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Payroll Inputs page is missing.",
                    **self._hr_pay_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _hr_pay_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_hr_pay_owner()
        if identity is None:
            return
        try:
            _hr_pay.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                payroll=(qs.get("payroll") or [""])[0],
                hr_master=(qs.get("hr_master") or qs.get("hr-master") or [""])[0],
                attendance=(qs.get("attendance") or [""])[0],
                leave=(qs.get("leave") or [""])[0],
                pay_input=(qs.get("pay_input") or qs.get("pay-input") or [""])[0],
                payslip=(qs.get("payslip") or [""])[0],
                checklist=(qs.get("checklist") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                staff_blast=(qs.get("staff_blast") or qs.get("staff-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _hr_pay.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._hr_pay_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _hr_pay.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._hr_pay_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _hr_pay.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._hr_pay_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _hr_pay.read_kind(ref_id)
            else:
                report = _hr_pay.build_framework()
        except _hr_pay.PayrollInputsError as exc:
            self._hr_pay_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)



    def _hr_ret_quiet(self) -> dict:
        return {
            "empty_is_retention_succession": False,
            "empty_is_people_signal": False,
            "empty_is_ready": False,
            "proved": False,
            "live_retention_signal": False,
            "live_retention_succession": False,
            "people_signal_machinery": False,
            "succession_machinery": False,
            "current": False,
            "retention_signal": None,
            "retention_signal_number": None,
            "succession_signal": None,
            "succession_signal_number": None,
            "risk_flag": None,
            "risk_flag_number": None,
            "people_signal": None,
            "people_signal_number": None,
            "checklist": None,
            "guest_blast": False,
            "staff_blast": False,
            "public_post": False,
            "hr_master_write": False,
            "payroll_executed": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_retention_signal": False,
            "invented_succession_signal": False,
            "invented_risk_flag": False,
            "invented_people_signal": False,
        }

    def _require_hr_ret_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Retention signals framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Retention & Succession Signals is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._hr_ret_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._hr_ret_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _hr_ret_refuse_code(self, path: str) -> str | None:
        if path in {"/api/hr/retention-signals/payment", "/api/hr/retention-signals/money"}:
            return "payment"
        if path in {"/api/hr/retention-signals/bank", "/api/hr/retention-signals/transfer"}:
            return "bank"
        if path in {"/api/hr/retention-signals/zayen", "/api/hr/retention-signals/books"}:
            return "books"
        if path in {
            "/api/hr/retention-signals/payroll",
            "/api/hr/retention-signals/payroll-execute",
        }:
            return "payroll"
        if path in {
            "/api/hr/retention-signals/hr-master",
            "/api/hr/retention-signals/people-master",
        }:
            return "hr_master"
        if path in {
            "/api/hr/retention-signals/guest-blast",
            "/api/hr/retention-signals/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/hr/retention-signals/staff-blast",
            "/api/hr/retention-signals/staff-broadcast",
        }:
            return "staff_blast"
        if path in {
            "/api/hr/retention-signals/public-post",
            "/api/hr/retention-signals/public",
            "/api/hr/retention-signals/post",
            "/api/hr/retention-signals/publish",
        }:
            return "public_post"
        if path == "/api/hr/retention-signals/current":
            return "current"
        if path in {"/api/hr/retention-signals/cloudflare", "/api/hr/retention-signals/cf"}:
            return "cloudflare"
        if path in {"/api/hr/retention-signals/access", "/api/hr/retention-signals/cf-access"}:
            return "access"
        if path in {"/api/hr/retention-signals/prove", "/api/hr/retention-signals/proven"}:
            return "prove"
        if path == "/api/hr/retention-signals/ready":
            return "ready"
        if path == "/api/hr/retention-signals/resolve":
            return "resolve"
        if path in {
            "/api/hr/retention-signals/production",
            "/api/hr/retention-signals/production/mutate",
        }:
            return "production"
        if path in {"/api/hr/retention-signals/score", "/api/hr/retention-signals/credits"}:
            return "score"
        if path in {"/api/hr/retention-signals/fill", "/api/hr/retention-signals/note"}:
            return "fill"
        if path == "/api/hr/retention-signals/alchemist":
            return "alchemist"
        return None

    def _hr_ret_fail(self, exc: _hr_ret.RetentionSignalsError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "payroll_refused",
            "hr_master_refused",
            "guest_blast_refused",
            "staff_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._hr_ret_quiet(),
                **_hr_ret.honesty_flags(),
            },
            status=status,
        )

    def _hr_ret_write_refused(self, path: str) -> None:
        identity = self._require_hr_ret_owner()
        if identity is None:
            return
        try:
            code = self._hr_ret_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "retention_signal",
                "retention-signal",
                "succession_signal",
                "succession-signal",
                "risk_flag",
                "risk-flag",
                "people_signal",
                "people-signal",
                "checklist",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _hr_ret.refuse_payment({})
            elif code == "bank":
                _hr_ret.refuse_bank({})
            elif code == "books":
                _hr_ret.refuse_books({})
            elif code == "payroll":
                _hr_ret.refuse_payroll({})
            elif code == "hr_master":
                _hr_ret.refuse_hr_master({})
            elif code == "guest_blast":
                _hr_ret.refuse_guest_blast({})
            elif code == "staff_blast":
                _hr_ret.refuse_staff_blast({})
            elif code == "public_post":
                _hr_ret.refuse_public_post({})
            elif code == "current":
                _hr_ret.refuse_current({})
            elif code == "cloudflare":
                _hr_ret.refuse_cloudflare({})
            elif code == "access":
                _hr_ret.refuse_access({})
            elif code == "prove":
                _hr_ret.refuse_proven({})
            elif code == "ready":
                _hr_ret.refuse_ready({})
            elif code == "resolve":
                _hr_ret.refuse_resolve({})
            elif code == "production":
                _hr_ret.refuse_production({})
            elif code == "score":
                _hr_ret.refuse_score({})
            elif code == "fill":
                _hr_ret.refuse_fill({})
            elif code == "alchemist":
                _hr_ret.refuse_alchemist({})
            else:
                _hr_ret.refuse_external_write({})
        except _hr_ret.RetentionSignalsError as exc:
            self._hr_ret_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Retention signals framework does not store a live retention/succession workflow.",
                **self._hr_ret_quiet(),
            },
            status=405,
        )

    def _hr_ret_page(self) -> None:
        identity = self._require_hr_ret_owner()
        if identity is None:
            return
        page = DASHBOARDS / "hr-retention-signals.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Retention & Succession Signals page is missing.",
                    **self._hr_ret_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _hr_ret_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_hr_ret_owner()
        if identity is None:
            return
        try:
            _hr_ret.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                payroll=(qs.get("payroll") or [""])[0],
                hr_master=(qs.get("hr_master") or qs.get("hr-master") or [""])[0],
                retention_signal=(qs.get("retention_signal") or qs.get("retention-signal") or [""])[0],
                succession_signal=(qs.get("succession_signal") or qs.get("succession-signal") or [""])[0],
                risk_flag=(qs.get("risk_flag") or qs.get("risk-flag") or [""])[0],
                people_signal=(qs.get("people_signal") or qs.get("people-signal") or [""])[0],
                checklist=(qs.get("checklist") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                staff_blast=(qs.get("staff_blast") or qs.get("staff-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _hr_ret.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._hr_ret_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _hr_ret.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._hr_ret_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _hr_ret.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._hr_ret_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _hr_ret.read_kind(ref_id)
            else:
                report = _hr_ret.build_framework()
        except _hr_ret.RetentionSignalsError as exc:
            self._hr_ret_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)



    def _fin_mgmt_quiet(self) -> dict:
        return {
            "empty_is_management_reporting": False,
            "empty_is_pnl_bs_cf": False,
            "empty_is_ready": False,
            "proved": False,
            "live_pnl": False,
            "live_balance_sheet": False,
            "live_cash_flow": False,
            "live_management_reporting": False,
            "pnl_bs_cf_machinery": False,
            "current": False,
            "pnl": None,
            "pnl_number": None,
            "balance_sheet": None,
            "balance_sheet_number": None,
            "cash_flow": None,
            "cash_flow_number": None,
            "checklist": None,
            "guest_blast": False,
            "staff_blast": False,
            "public_post": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_pnl": False,
            "invented_balance_sheet": False,
            "invented_cash_flow": False,
        }

    def _require_fin_mgmt_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Management reporting framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Management reporting is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._fin_mgmt_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._fin_mgmt_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _fin_mgmt_refuse_code(self, path: str) -> str | None:
        if path in {"/api/fin/mgmt-reporting/payment", "/api/fin/mgmt-reporting/money"}:
            return "payment"
        if path in {"/api/fin/mgmt-reporting/bank", "/api/fin/mgmt-reporting/transfer"}:
            return "bank"
        if path in {"/api/fin/mgmt-reporting/zayen", "/api/fin/mgmt-reporting/books"}:
            return "books"
        if path in {
            "/api/fin/mgmt-reporting/guest-blast",
            "/api/fin/mgmt-reporting/blast",
        }:
            return "guest_blast"
        if path in {
            "/api/fin/mgmt-reporting/staff-blast",
            "/api/fin/mgmt-reporting/staff-broadcast",
        }:
            return "staff_blast"
        if path in {
            "/api/fin/mgmt-reporting/public-post",
            "/api/fin/mgmt-reporting/public",
            "/api/fin/mgmt-reporting/post",
            "/api/fin/mgmt-reporting/publish",
        }:
            return "public_post"
        if path == "/api/fin/mgmt-reporting/current":
            return "current"
        if path in {"/api/fin/mgmt-reporting/cloudflare", "/api/fin/mgmt-reporting/cf"}:
            return "cloudflare"
        if path in {"/api/fin/mgmt-reporting/access", "/api/fin/mgmt-reporting/cf-access"}:
            return "access"
        if path in {"/api/fin/mgmt-reporting/prove", "/api/fin/mgmt-reporting/proven"}:
            return "prove"
        if path == "/api/fin/mgmt-reporting/ready":
            return "ready"
        if path == "/api/fin/mgmt-reporting/resolve":
            return "resolve"
        if path in {
            "/api/fin/mgmt-reporting/production",
            "/api/fin/mgmt-reporting/production/mutate",
        }:
            return "production"
        if path in {"/api/fin/mgmt-reporting/score", "/api/fin/mgmt-reporting/credits"}:
            return "score"
        if path in {"/api/fin/mgmt-reporting/fill", "/api/fin/mgmt-reporting/note"}:
            return "fill"
        if path == "/api/fin/mgmt-reporting/alchemist":
            return "alchemist"
        return None

    def _fin_mgmt_fail(self, exc: _fin_mgmt.FinMgmtReportingError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "guest_blast_refused",
            "staff_blast_refused",
            "public_post_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._fin_mgmt_quiet(),
                **_fin_mgmt.honesty_flags(),
            },
            status=status,
        )

    def _fin_mgmt_write_refused(self, path: str) -> None:
        identity = self._require_fin_mgmt_owner()
        if identity is None:
            return
        try:
            code = self._fin_mgmt_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "pnl",
                "balance_sheet",
                "balance-sheet",
                "cash_flow",
                "cash-flow",
                "checklist",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _fin_mgmt.refuse_payment({})
            elif code == "bank":
                _fin_mgmt.refuse_bank({})
            elif code == "books":
                _fin_mgmt.refuse_books({})
            elif code == "guest_blast":
                _fin_mgmt.refuse_guest_blast({})
            elif code == "staff_blast":
                _fin_mgmt.refuse_staff_blast({})
            elif code == "public_post":
                _fin_mgmt.refuse_public_post({})
            elif code == "current":
                _fin_mgmt.refuse_current({})
            elif code == "cloudflare":
                _fin_mgmt.refuse_cloudflare({})
            elif code == "access":
                _fin_mgmt.refuse_access({})
            elif code == "prove":
                _fin_mgmt.refuse_proven({})
            elif code == "ready":
                _fin_mgmt.refuse_ready({})
            elif code == "resolve":
                _fin_mgmt.refuse_resolve({})
            elif code == "production":
                _fin_mgmt.refuse_production({})
            elif code == "score":
                _fin_mgmt.refuse_score({})
            elif code == "fill":
                _fin_mgmt.refuse_fill({})
            elif code == "alchemist":
                _fin_mgmt.refuse_alchemist({})
            else:
                _fin_mgmt.refuse_external_write({})
        except _fin_mgmt.FinMgmtReportingError as exc:
            self._fin_mgmt_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Management reporting framework does not store a live management-reporting pack.",
                **self._fin_mgmt_quiet(),
            },
            status=405,
        )

    def _fin_mgmt_page(self) -> None:
        identity = self._require_fin_mgmt_owner()
        if identity is None:
            return
        page = DASHBOARDS / "fin-mgmt-reporting.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Management Reporting page is missing.",
                    **self._fin_mgmt_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _fin_mgmt_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_fin_mgmt_owner()
        if identity is None:
            return
        try:
            _fin_mgmt.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                pnl=(qs.get("pnl") or [""])[0],
                balance_sheet=(qs.get("balance_sheet") or qs.get("balance-sheet") or [""])[0],
                cash_flow=(qs.get("cash_flow") or qs.get("cash-flow") or [""])[0],
                checklist=(qs.get("checklist") or [""])[0],
                current=(qs.get("current") or [""])[0],
                guest_blast=(qs.get("guest_blast") or qs.get("guest-blast") or [""])[0],
                staff_blast=(qs.get("staff_blast") or qs.get("staff-blast") or [""])[0],
                public_post=(qs.get("public_post") or qs.get("public-post") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _fin_mgmt.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._fin_mgmt_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _fin_mgmt.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._fin_mgmt_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _fin_mgmt.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._fin_mgmt_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _fin_mgmt.read_kind(ref_id)
            else:
                report = _fin_mgmt.build_framework()
        except _fin_mgmt.FinMgmtReportingError as exc:
            self._fin_mgmt_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)


    def _ggv_ic_quiet(self) -> dict:
        return {
            "empty_is_billing": False,
            "empty_is_client_machinery": False,
            "empty_is_ready": False,
            "proved": False,
            "live_billing": False,
            "client_machinery": False,
            "current": False,
            "service_record": None,
            "invoice": None,
            "allocation": None,
            "arms_length": None,
            "ar_ap": None,
            "tax_treatment": None,
            "tax_claimed": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_invoice": False,
            "invented_allocation": False,
            "invented_ar_ap": False,
            "invented_tax": False,
        }

    def _require_ggv_ic_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Intercompany framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Intercompany client mode is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._ggv_ic_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._ggv_ic_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _ggv_ic_refuse_code(self, path: str) -> str | None:
        if path in {"/api/ggv/intercompany-client/payment", "/api/ggv/intercompany-client/money"}:
            return "payment"
        if path in {"/api/ggv/intercompany-client/bank", "/api/ggv/intercompany-client/transfer"}:
            return "bank"
        if path in {"/api/ggv/intercompany-client/zayen", "/api/ggv/intercompany-client/books"}:
            return "books"
        if path in {"/api/ggv/intercompany-client/tax", "/api/ggv/intercompany-client/tax-treatment"}:
            return "tax"
        if path == "/api/ggv/intercompany-client/current":
            return "current"
        if path in {"/api/ggv/intercompany-client/cloudflare", "/api/ggv/intercompany-client/cf"}:
            return "cloudflare"
        if path in {"/api/ggv/intercompany-client/access", "/api/ggv/intercompany-client/cf-access"}:
            return "access"
        if path in {"/api/ggv/intercompany-client/prove", "/api/ggv/intercompany-client/proven"}:
            return "prove"
        if path == "/api/ggv/intercompany-client/ready":
            return "ready"
        if path == "/api/ggv/intercompany-client/resolve":
            return "resolve"
        if path in {
            "/api/ggv/intercompany-client/production",
            "/api/ggv/intercompany-client/production/mutate",
        }:
            return "production"
        if path in {"/api/ggv/intercompany-client/score", "/api/ggv/intercompany-client/credits"}:
            return "score"
        if path in {"/api/ggv/intercompany-client/fill", "/api/ggv/intercompany-client/note"}:
            return "fill"
        if path == "/api/ggv/intercompany-client/alchemist":
            return "alchemist"
        return None

    def _ggv_ic_fail(self, exc: _ggv_ic.IntercompanyClientError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "tax_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._ggv_ic_quiet(),
                **_ggv_ic.honesty_flags(),
            },
            status=status,
        )

    def _ggv_ic_write_refused(self, path: str) -> None:
        identity = self._require_ggv_ic_owner()
        if identity is None:
            return
        try:
            code = self._ggv_ic_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "invoice",
                "allocation",
                "ar-ap",
                "ar_ap",
                "arms-length",
                "arms_length",
                "service-record",
                "service_record",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _ggv_ic.refuse_payment({})
            elif code == "bank":
                _ggv_ic.refuse_bank({})
            elif code == "books":
                _ggv_ic.refuse_books({})
            elif code == "tax":
                _ggv_ic.refuse_tax({})
            elif code == "current":
                _ggv_ic.refuse_current({})
            elif code == "cloudflare":
                _ggv_ic.refuse_cloudflare({})
            elif code == "access":
                _ggv_ic.refuse_access({})
            elif code == "prove":
                _ggv_ic.refuse_proven({})
            elif code == "ready":
                _ggv_ic.refuse_ready({})
            elif code == "resolve":
                _ggv_ic.refuse_resolve({})
            elif code == "production":
                _ggv_ic.refuse_production({})
            elif code == "score":
                _ggv_ic.refuse_score({})
            elif code == "fill":
                _ggv_ic.refuse_fill({})
            elif code == "alchemist":
                _ggv_ic.refuse_alchemist({})
            else:
                _ggv_ic.refuse_external_write({})
        except _ggv_ic.IntercompanyClientError as exc:
            self._ggv_ic_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Intercompany framework does not store live intercompany billing.",
                **self._ggv_ic_quiet(),
            },
            status=405,
        )

    def _ggv_ic_page(self) -> None:
        identity = self._require_ggv_ic_owner()
        if identity is None:
            return
        page = DASHBOARDS / "ggv-intercompany-client.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Intercompany client mode page is missing.",
                    **self._ggv_ic_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _ggv_ic_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_ggv_ic_owner()
        if identity is None:
            return
        try:
            _ggv_ic.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                invoice=(qs.get("invoice") or [""])[0],
                allocation=(qs.get("allocation") or [""])[0],
                ar_ap=(qs.get("ar_ap") or [""])[0],
                arms_length=(qs.get("arms_length") or [""])[0],
                service_record=(qs.get("service_record") or [""])[0],
                tax=(qs.get("tax") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _ggv_ic.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._ggv_ic_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _ggv_ic.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._ggv_ic_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _ggv_ic.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._ggv_ic_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _ggv_ic.read_kind(ref_id)
            else:
                report = _ggv_ic.build_framework()
        except _ggv_ic.IntercompanyClientError as exc:
            self._ggv_ic_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)


    def _bzg_pnl_quiet(self) -> dict:
        return {
            "empty_is_pnl": False,
            "empty_is_rollup_machinery": False,
            "empty_is_ready": False,
            "proved": False,
            "live_pnl": False,
            "rollup_machinery": False,
            "current": False,
            "venue": None,
            "revenue": None,
            "cost": None,
            "contribution": None,
            "rollup": None,
            "tax_treatment": None,
            "tax_claimed": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_revenue": False,
            "invented_cost": False,
            "invented_contribution": False,
            "invented_rollup": False,
            "invented_tax": False,
        }

    def _require_bzg_pnl_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Venue P&L framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Venue P&L is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._bzg_pnl_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._bzg_pnl_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _bzg_pnl_refuse_code(self, path: str) -> str | None:
        if path in {"/api/bzg/venue-pnl/payment", "/api/bzg/venue-pnl/money"}:
            return "payment"
        if path in {"/api/bzg/venue-pnl/bank", "/api/bzg/venue-pnl/transfer"}:
            return "bank"
        if path in {"/api/bzg/venue-pnl/zayen", "/api/bzg/venue-pnl/books"}:
            return "books"
        if path in {"/api/bzg/venue-pnl/tax", "/api/bzg/venue-pnl/tax-treatment"}:
            return "tax"
        if path == "/api/bzg/venue-pnl/current":
            return "current"
        if path in {"/api/bzg/venue-pnl/cloudflare", "/api/bzg/venue-pnl/cf"}:
            return "cloudflare"
        if path in {"/api/bzg/venue-pnl/access", "/api/bzg/venue-pnl/cf-access"}:
            return "access"
        if path in {"/api/bzg/venue-pnl/prove", "/api/bzg/venue-pnl/proven"}:
            return "prove"
        if path == "/api/bzg/venue-pnl/ready":
            return "ready"
        if path == "/api/bzg/venue-pnl/resolve":
            return "resolve"
        if path in {
            "/api/bzg/venue-pnl/production",
            "/api/bzg/venue-pnl/production/mutate",
        }:
            return "production"
        if path in {"/api/bzg/venue-pnl/score", "/api/bzg/venue-pnl/credits"}:
            return "score"
        if path in {"/api/bzg/venue-pnl/fill", "/api/bzg/venue-pnl/note"}:
            return "fill"
        if path == "/api/bzg/venue-pnl/alchemist":
            return "alchemist"
        return None

    def _bzg_pnl_fail(self, exc: _bzg_pnl.VenuePnlError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "tax_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._bzg_pnl_quiet(),
                **_bzg_pnl.honesty_flags(),
            },
            status=status,
        )

    def _bzg_pnl_write_refused(self, path: str) -> None:
        identity = self._require_bzg_pnl_owner()
        if identity is None:
            return
        try:
            code = self._bzg_pnl_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "venue",
                "venues",
                "revenue",
                "cost",
                "costs",
                "contribution",
                "rollup",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _bzg_pnl.refuse_payment({})
            elif code == "bank":
                _bzg_pnl.refuse_bank({})
            elif code == "books":
                _bzg_pnl.refuse_books({})
            elif code == "tax":
                _bzg_pnl.refuse_tax({})
            elif code == "current":
                _bzg_pnl.refuse_current({})
            elif code == "cloudflare":
                _bzg_pnl.refuse_cloudflare({})
            elif code == "access":
                _bzg_pnl.refuse_access({})
            elif code == "prove":
                _bzg_pnl.refuse_proven({})
            elif code == "ready":
                _bzg_pnl.refuse_ready({})
            elif code == "resolve":
                _bzg_pnl.refuse_resolve({})
            elif code == "production":
                _bzg_pnl.refuse_production({})
            elif code == "score":
                _bzg_pnl.refuse_score({})
            elif code == "fill":
                _bzg_pnl.refuse_fill({})
            elif code == "alchemist":
                _bzg_pnl.refuse_alchemist({})
            else:
                _bzg_pnl.refuse_external_write({})
        except _bzg_pnl.VenuePnlError as exc:
            self._bzg_pnl_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Venue P&L framework does not store a live venue P&L.",
                **self._bzg_pnl_quiet(),
            },
            status=405,
        )

    def _bzg_pnl_page(self) -> None:
        identity = self._require_bzg_pnl_owner()
        if identity is None:
            return
        page = DASHBOARDS / "bzg-venue-pnl.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Venue P&L page is missing.",
                    **self._bzg_pnl_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bzg_pnl_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_bzg_pnl_owner()
        if identity is None:
            return
        try:
            _bzg_pnl.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                venue=(qs.get("venue") or [""])[0],
                revenue=(qs.get("revenue") or [""])[0],
                cost=(qs.get("cost") or [""])[0],
                contribution=(qs.get("contribution") or [""])[0],
                rollup=(qs.get("rollup") or [""])[0],
                tax=(qs.get("tax") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _bzg_pnl.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._bzg_pnl_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _bzg_pnl.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._bzg_pnl_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _bzg_pnl.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._bzg_pnl_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _bzg_pnl.read_kind(ref_id)
            else:
                report = _bzg_pnl.build_framework()
        except _bzg_pnl.VenuePnlError as exc:
            self._bzg_pnl_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)


    def _bzg_var_quiet(self) -> dict:
        return {
            "empty_is_variance_waste": False,
            "empty_is_inventory_variance_machinery": False,
            "empty_is_ready": False,
            "proved": False,
            "live_variance_waste": False,
            "inventory_variance_machinery": False,
            "current": False,
            "variance": None,
            "waste": None,
            "comps": None,
            "voids": None,
            "analysis": None,
            "esb_mutated": False,
            "esb_sot_note": "ESB remains transactional SoT (read-only note only; no ESB mutate).",
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_variance": False,
            "invented_waste": False,
            "invented_comps": False,
            "invented_voids": False,
            "invented_analysis": False,
        }

    def _require_bzg_var_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Variance/waste framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Variance/waste is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._bzg_var_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._bzg_var_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _bzg_var_refuse_code(self, path: str) -> str | None:
        if path in {"/api/bzg/variance-waste/payment", "/api/bzg/variance-waste/money"}:
            return "payment"
        if path in {"/api/bzg/variance-waste/bank", "/api/bzg/variance-waste/transfer"}:
            return "bank"
        if path in {"/api/bzg/variance-waste/zayen", "/api/bzg/variance-waste/books"}:
            return "books"
        if path in {"/api/bzg/variance-waste/esb", "/api/bzg/variance-waste/esb-mutate", "/api/bzg/variance-waste/esb-write"}:
            return "esb"
        if path == "/api/bzg/variance-waste/current":
            return "current"
        if path in {"/api/bzg/variance-waste/cloudflare", "/api/bzg/variance-waste/cf"}:
            return "cloudflare"
        if path in {"/api/bzg/variance-waste/access", "/api/bzg/variance-waste/cf-access"}:
            return "access"
        if path in {"/api/bzg/variance-waste/prove", "/api/bzg/variance-waste/proven"}:
            return "prove"
        if path == "/api/bzg/variance-waste/ready":
            return "ready"
        if path == "/api/bzg/variance-waste/resolve":
            return "resolve"
        if path in {
            "/api/bzg/variance-waste/production",
            "/api/bzg/variance-waste/production/mutate",
        }:
            return "production"
        if path in {"/api/bzg/variance-waste/score", "/api/bzg/variance-waste/credits"}:
            return "score"
        if path in {"/api/bzg/variance-waste/fill", "/api/bzg/variance-waste/note"}:
            return "fill"
        if path == "/api/bzg/variance-waste/alchemist":
            return "alchemist"
        return None

    def _bzg_var_fail(self, exc: _bzg_var.VarianceWasteError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "esb_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._bzg_var_quiet(),
                **_bzg_var.honesty_flags(),
            },
            status=status,
        )

    def _bzg_var_write_refused(self, path: str) -> None:
        identity = self._require_bzg_var_owner()
        if identity is None:
            return
        try:
            code = self._bzg_var_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "variance",
                "waste",
                "comps",
                "voids",
                "analysis",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _bzg_var.refuse_payment({})
            elif code == "bank":
                _bzg_var.refuse_bank({})
            elif code == "books":
                _bzg_var.refuse_books({})
            elif code == "esb":
                _bzg_var.refuse_esb({})
            elif code == "current":
                _bzg_var.refuse_current({})
            elif code == "cloudflare":
                _bzg_var.refuse_cloudflare({})
            elif code == "access":
                _bzg_var.refuse_access({})
            elif code == "prove":
                _bzg_var.refuse_proven({})
            elif code == "ready":
                _bzg_var.refuse_ready({})
            elif code == "resolve":
                _bzg_var.refuse_resolve({})
            elif code == "production":
                _bzg_var.refuse_production({})
            elif code == "score":
                _bzg_var.refuse_score({})
            elif code == "fill":
                _bzg_var.refuse_fill({})
            elif code == "alchemist":
                _bzg_var.refuse_alchemist({})
            else:
                _bzg_var.refuse_external_write({})
        except _bzg_var.VarianceWasteError as exc:
            self._bzg_var_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Variance/waste framework does not store a live variance/waste analysis.",
                **self._bzg_var_quiet(),
            },
            status=405,
        )

    def _bzg_var_page(self) -> None:
        identity = self._require_bzg_var_owner()
        if identity is None:
            return
        page = DASHBOARDS / "bzg-variance-waste.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Variance/waste page is missing.",
                    **self._bzg_var_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bzg_var_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_bzg_var_owner()
        if identity is None:
            return
        try:
            _bzg_var.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                esb=(qs.get("esb") or [""])[0],
                variance=(qs.get("variance") or [""])[0],
                waste=(qs.get("waste") or [""])[0],
                comps=(qs.get("comps") or [""])[0],
                voids=(qs.get("voids") or [""])[0],
                analysis=(qs.get("analysis") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _bzg_var.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._bzg_var_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _bzg_var.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._bzg_var_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _bzg_var.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._bzg_var_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _bzg_var.read_kind(ref_id)
            else:
                report = _bzg_var.build_framework()
        except _bzg_var.VarianceWasteError as exc:
            self._bzg_var_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)


    def _bzg_alloc_quiet(self) -> dict:
        return {
            "empty_is_allocation_engine": False,
            "empty_is_shared_cost_allocation_machinery": False,
            "empty_is_ready": False,
            "proved": False,
            "live_allocation_engine": False,
            "shared_cost_allocation_machinery": False,
            "current": False,
            "kitchen": None,
            "venues": None,
            "shared_cost": None,
            "allocation": None,
            "drivers": None,
            "esb_mutated": False,
            "esb_sot_note": "ESB remains transactional SoT (read-only note only; no ESB mutate).",
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_kitchen": False,
            "invented_venues": False,
            "invented_shared_cost": False,
            "invented_allocation": False,
            "invented_drivers": False,
        }

    def _require_bzg_alloc_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Allocation framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Allocation engine is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._bzg_alloc_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._bzg_alloc_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _bzg_alloc_refuse_code(self, path: str) -> str | None:
        if path in {"/api/bzg/allocation-engine/payment", "/api/bzg/allocation-engine/money"}:
            return "payment"
        if path in {"/api/bzg/allocation-engine/bank", "/api/bzg/allocation-engine/transfer"}:
            return "bank"
        if path in {"/api/bzg/allocation-engine/zayen", "/api/bzg/allocation-engine/books"}:
            return "books"
        if path in {"/api/bzg/allocation-engine/esb", "/api/bzg/allocation-engine/esb-mutate", "/api/bzg/allocation-engine/esb-write"}:
            return "esb"
        if path == "/api/bzg/allocation-engine/current":
            return "current"
        if path in {"/api/bzg/allocation-engine/cloudflare", "/api/bzg/allocation-engine/cf"}:
            return "cloudflare"
        if path in {"/api/bzg/allocation-engine/access", "/api/bzg/allocation-engine/cf-access"}:
            return "access"
        if path in {"/api/bzg/allocation-engine/prove", "/api/bzg/allocation-engine/proven"}:
            return "prove"
        if path == "/api/bzg/allocation-engine/ready":
            return "ready"
        if path == "/api/bzg/allocation-engine/resolve":
            return "resolve"
        if path in {
            "/api/bzg/allocation-engine/production",
            "/api/bzg/allocation-engine/production/mutate",
        }:
            return "production"
        if path in {"/api/bzg/allocation-engine/score", "/api/bzg/allocation-engine/credits"}:
            return "score"
        if path in {"/api/bzg/allocation-engine/fill", "/api/bzg/allocation-engine/note"}:
            return "fill"
        if path == "/api/bzg/allocation-engine/alchemist":
            return "alchemist"
        return None

    def _bzg_alloc_fail(self, exc: _bzg_alloc.AllocationEngineError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "esb_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._bzg_alloc_quiet(),
                **_bzg_alloc.honesty_flags(),
            },
            status=status,
        )

    def _bzg_alloc_write_refused(self, path: str) -> None:
        identity = self._require_bzg_alloc_owner()
        if identity is None:
            return
        try:
            code = self._bzg_alloc_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "kitchen",
                "venues",
                "shared_cost",
                "allocation",
                "drivers",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _bzg_alloc.refuse_payment({})
            elif code == "bank":
                _bzg_alloc.refuse_bank({})
            elif code == "books":
                _bzg_alloc.refuse_books({})
            elif code == "esb":
                _bzg_alloc.refuse_esb({})
            elif code == "current":
                _bzg_alloc.refuse_current({})
            elif code == "cloudflare":
                _bzg_alloc.refuse_cloudflare({})
            elif code == "access":
                _bzg_alloc.refuse_access({})
            elif code == "prove":
                _bzg_alloc.refuse_proven({})
            elif code == "ready":
                _bzg_alloc.refuse_ready({})
            elif code == "resolve":
                _bzg_alloc.refuse_resolve({})
            elif code == "production":
                _bzg_alloc.refuse_production({})
            elif code == "score":
                _bzg_alloc.refuse_score({})
            elif code == "fill":
                _bzg_alloc.refuse_fill({})
            elif code == "alchemist":
                _bzg_alloc.refuse_alchemist({})
            else:
                _bzg_alloc.refuse_external_write({})
        except _bzg_alloc.AllocationEngineError as exc:
            self._bzg_alloc_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Allocation framework does not store a live allocation engine.",
                **self._bzg_alloc_quiet(),
            },
            status=405,
        )

    def _bzg_alloc_page(self) -> None:
        identity = self._require_bzg_alloc_owner()
        if identity is None:
            return
        page = DASHBOARDS / "bzg-allocation-engine.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Allocation engine page is missing.",
                    **self._bzg_alloc_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bzg_alloc_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_bzg_alloc_owner()
        if identity is None:
            return
        try:
            _bzg_alloc.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                esb=(qs.get("esb") or [""])[0],
                kitchen=(qs.get("kitchen") or [""])[0],
                venues=(qs.get("venues") or [""])[0],
                shared_cost=(qs.get("shared_cost") or [""])[0],
                allocation=(qs.get("allocation") or [""])[0],
                drivers=(qs.get("drivers") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _bzg_alloc.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._bzg_alloc_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _bzg_alloc.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._bzg_alloc_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _bzg_alloc.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._bzg_alloc_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _bzg_alloc.read_kind(ref_id)
            else:
                report = _bzg_alloc.build_framework()
        except _bzg_alloc.AllocationEngineError as exc:
            self._bzg_alloc_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _bzg_bom_quiet(self) -> dict:
        return {
            "empty_is_bom_yield_machinery": False,
            "empty_is_recipe_cost_standards": False,
            "empty_is_ready": False,
            "proved": False,
            "live_bom_yield_machinery": False,
            "recipe_cost_standards": False,
            "current": False,
            "bom": None,
            "yield": None,
            "waste": None,
            "theoretical_cost": None,
            "menu_engineering": None,
            "esb_mutated": False,
            "esb_sot_note": "ESB remains transactional SoT (read-only note only; no ESB mutate).",
            "payment": None,
            "money": None,
            "payment_executed": False,
            "bank_write": False,
            "books_write": False,
            "zayen_write": False,
            "alchemist_write": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
            "invented_bom": False,
            "invented_yield": False,
            "invented_waste": False,
            "invented_theoretical_cost": False,
            "invented_menu_engineering": False,
        }

    def _require_bzg_bom_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. BOM/yield framework is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "BOM/yield framework is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._bzg_bom_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._bzg_bom_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _bzg_bom_refuse_code(self, path: str) -> str | None:
        if path in {"/api/bzg/bom-yield/payment", "/api/bzg/bom-yield/money"}:
            return "payment"
        if path in {"/api/bzg/bom-yield/bank", "/api/bzg/bom-yield/transfer"}:
            return "bank"
        if path in {"/api/bzg/bom-yield/zayen", "/api/bzg/bom-yield/books"}:
            return "books"
        if path in {"/api/bzg/bom-yield/esb", "/api/bzg/bom-yield/esb-mutate", "/api/bzg/bom-yield/esb-write"}:
            return "esb"
        if path == "/api/bzg/bom-yield/current":
            return "current"
        if path in {"/api/bzg/bom-yield/cloudflare", "/api/bzg/bom-yield/cf"}:
            return "cloudflare"
        if path in {"/api/bzg/bom-yield/access", "/api/bzg/bom-yield/cf-access"}:
            return "access"
        if path in {"/api/bzg/bom-yield/prove", "/api/bzg/bom-yield/proven"}:
            return "prove"
        if path == "/api/bzg/bom-yield/ready":
            return "ready"
        if path == "/api/bzg/bom-yield/resolve":
            return "resolve"
        if path in {
            "/api/bzg/bom-yield/production",
            "/api/bzg/bom-yield/production/mutate",
        }:
            return "production"
        if path in {"/api/bzg/bom-yield/score", "/api/bzg/bom-yield/credits"}:
            return "score"
        if path in {"/api/bzg/bom-yield/fill", "/api/bzg/bom-yield/note"}:
            return "fill"
        if path == "/api/bzg/bom-yield/alchemist":
            return "alchemist"
        return None

    def _bzg_bom_fail(self, exc: _bzg_bom.BomYieldError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "books_refused",
            "esb_refused",
            "current_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._bzg_bom_quiet(),
                **_bzg_bom.honesty_flags(),
            },
            status=status,
        )

    def _bzg_bom_write_refused(self, path: str) -> None:
        identity = self._require_bzg_bom_owner()
        if identity is None:
            return
        try:
            code = self._bzg_bom_refuse_code(path)
            tail = path.rstrip("/").rsplit("/", 1)[-1]
            if code is None and tail in {
                "bom",
                "yield",
                "waste",
                "theoretical_cost",
                "menu_engineering",
            }:
                code = "current"
            elif code is None and tail == "notes":
                code = "fill"
            if code == "payment":
                _bzg_bom.refuse_payment({})
            elif code == "bank":
                _bzg_bom.refuse_bank({})
            elif code == "books":
                _bzg_bom.refuse_books({})
            elif code == "esb":
                _bzg_bom.refuse_esb({})
            elif code == "current":
                _bzg_bom.refuse_current({})
            elif code == "cloudflare":
                _bzg_bom.refuse_cloudflare({})
            elif code == "access":
                _bzg_bom.refuse_access({})
            elif code == "prove":
                _bzg_bom.refuse_proven({})
            elif code == "ready":
                _bzg_bom.refuse_ready({})
            elif code == "resolve":
                _bzg_bom.refuse_resolve({})
            elif code == "production":
                _bzg_bom.refuse_production({})
            elif code == "score":
                _bzg_bom.refuse_score({})
            elif code == "fill":
                _bzg_bom.refuse_fill({})
            elif code == "alchemist":
                _bzg_bom.refuse_alchemist({})
            else:
                _bzg_bom.refuse_external_write({})
        except _bzg_bom.BomYieldError as exc:
            self._bzg_bom_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "BOM/yield framework does not store live BOM/yield machinery.",
                **self._bzg_bom_quiet(),
            },
            status=405,
        )

    def _bzg_bom_page(self) -> None:
        identity = self._require_bzg_bom_owner()
        if identity is None:
            return
        page = DASHBOARDS / "bzg-bom-yield.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "BOM/yield page is missing.",
                    **self._bzg_bom_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bzg_bom_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_bzg_bom_owner()
        if identity is None:
            return
        try:
            _bzg_bom.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                zayen=(qs.get("zayen") or [""])[0],
                books=(qs.get("books") or [""])[0],
                esb=(qs.get("esb") or [""])[0],
                bom=(qs.get("bom") or [""])[0],
                yield_=(qs.get("yield") or [""])[0],
                waste=(qs.get("waste") or [""])[0],
                theoretical_cost=(qs.get("theoretical_cost") or [""])[0],
                menu_engineering=(qs.get("menu_engineering") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                score=(qs.get("score") or [""])[0],
                alchemist=(qs.get("alchemist") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _bzg_bom.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._bzg_bom_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _bzg_bom.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._bzg_bom_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _bzg_bom.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "bound": full["bound"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._bzg_bom_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _bzg_bom.read_kind(ref_id)
            else:
                report = _bzg_bom.build_framework()
        except _bzg_bom.BomYieldError as exc:
            self._bzg_bom_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _msc_posture_quiet(self) -> dict:
        return {
            "proved": False,
            "empty_is_prove": False,
            "empty_is_ready": False,
            "posture_score": None,
            "current": False,
            "control": None,
            "evidence": None,
            "payment": None,
            "money": None,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
        }

    def _require_msc_posture_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Posture prove is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Automated posture prove is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._msc_posture_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._msc_posture_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _msc_posture_refuse_code(self, path: str) -> str | None:
        if path in {"/api/msc/posture/payment", "/api/msc/posture/money"}:
            return "payment"
        if path in {
            "/api/msc/posture/score",
            "/api/msc/posture/live-score",
            "/api/msc/posture/posture-score",
            "/api/msc/posture/current",
        }:
            return "score"
        if path in {"/api/msc/posture/cloudflare", "/api/msc/posture/cf"}:
            return "cloudflare"
        if path in {"/api/msc/posture/access", "/api/msc/posture/cf-access"}:
            return "access"
        if path in {"/api/msc/posture/prove", "/api/msc/posture/proven"}:
            return "prove"
        if path == "/api/msc/posture/ready":
            return "ready"
        if path == "/api/msc/posture/resolve":
            return "resolve"
        if path in {"/api/msc/posture/production", "/api/msc/posture/production/mutate"}:
            return "production"
        if path in {"/api/msc/posture/fill", "/api/msc/posture/note"}:
            return "fill"
        return None

    def _msc_posture_fail(self, exc: _msc_posture.PostureProveError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "score_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._msc_posture_quiet(),
                **_msc_posture.honesty_flags(),
            },
            status=status,
        )

    def _msc_posture_write_refused(self, path: str) -> None:
        identity = self._require_msc_posture_owner()
        if identity is None:
            return
        try:
            code = self._msc_posture_refuse_code(path)
            if code == "payment":
                _msc_posture.refuse_payment({})
            elif code == "score":
                _msc_posture.refuse_score({})
            elif code == "cloudflare":
                _msc_posture.refuse_cloudflare({})
            elif code == "access":
                _msc_posture.refuse_access({})
            elif code == "prove":
                _msc_posture.refuse_proven({})
            elif code == "ready":
                _msc_posture.refuse_ready({})
            elif code == "resolve":
                _msc_posture.refuse_resolve({})
            elif code == "production":
                _msc_posture.refuse_production({})
            elif code == "fill":
                _msc_posture.refuse_fill({})
            else:
                _msc_posture.refuse_external_write({})
        except _msc_posture.PostureProveError as exc:
            self._msc_posture_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Posture prove framework does not store evidence or a live score.",
                **self._msc_posture_quiet(),
            },
            status=405,
        )

    def _msc_posture_page(self) -> None:
        identity = self._require_msc_posture_owner()
        if identity is None:
            return
        page = DASHBOARDS / "msc-posture.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Posture prove page is missing.",
                    **self._msc_posture_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _msc_posture_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_msc_posture_owner()
        if identity is None:
            return
        try:
            _msc_posture.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                score=(qs.get("score") or [""])[0],
                posture_score=(qs.get("posture_score") or qs.get("posture-score") or [""])[0],
                current=(qs.get("current") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _msc_posture.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._msc_posture_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _msc_posture.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._msc_posture_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _msc_posture.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._msc_posture_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _msc_posture.read_kind(ref_id)
            else:
                report = _msc_posture.build_framework()
        except _msc_posture.PostureProveError as exc:
            self._msc_posture_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _intg_contract_quiet(self) -> dict:
        return {
            "proved": False,
            "empty_is_prove": False,
            "empty_is_ready": False,
            "empty_is_yanolja": False,
            "empty_is_esb": False,
            "live_connector": False,
            "current": False,
            "contract": None,
            "fixture": None,
            "yanolja_called": False,
            "esb_called": False,
            "payment": None,
            "money": None,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "ledger_write": False,
            "cr_resolved": False,
            "invented_specified": False,
            "invented_proven": False,
            "invented_ready": False,
        }

    def _require_intg_contract_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Connector contract is Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Connector contract is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._intg_contract_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._intg_contract_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _intg_contract_refuse_code(self, path: str) -> str | None:
        if path in {"/api/intg/connector-contract/payment", "/api/intg/connector-contract/money"}:
            return "payment"
        if path in {"/api/intg/connector-contract/yanolja", "/api/intg/connector-contract/live-yanolja"}:
            return "yanolja"
        if path in {"/api/intg/connector-contract/esb", "/api/intg/connector-contract/live-esb"}:
            return "esb"
        if path in {"/api/intg/connector-contract/cloudflare", "/api/intg/connector-contract/cf"}:
            return "cloudflare"
        if path in {"/api/intg/connector-contract/access", "/api/intg/connector-contract/cf-access"}:
            return "access"
        if path in {"/api/intg/connector-contract/specified", "/api/intg/connector-contract/specify"}:
            return "specified"
        if path in {"/api/intg/connector-contract/prove", "/api/intg/connector-contract/proven"}:
            return "prove"
        if path == "/api/intg/connector-contract/ready":
            return "ready"
        if path == "/api/intg/connector-contract/resolve":
            return "resolve"
        if path in {"/api/intg/connector-contract/production", "/api/intg/connector-contract/production/mutate"}:
            return "production"
        if path in {"/api/intg/connector-contract/fill", "/api/intg/connector-contract/note"}:
            return "fill"
        return None

    def _intg_contract_fail(self, exc: _intg_contract.ConnectorContractError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "yanolja_refused",
            "esb_refused",
            "cloudflare_refused",
            "access_refused",
            "specified_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "slots_refused",
            "writes_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._intg_contract_quiet(),
                **_intg_contract.honesty_flags(),
            },
            status=status,
        )

    def _intg_contract_write_refused(self, path: str) -> None:
        identity = self._require_intg_contract_owner()
        if identity is None:
            return
        try:
            code = self._intg_contract_refuse_code(path)
            if code == "payment":
                _intg_contract.refuse_payment({})
            elif code == "yanolja":
                _intg_contract.refuse_yanolja({})
            elif code == "esb":
                _intg_contract.refuse_esb({})
            elif code == "cloudflare":
                _intg_contract.refuse_cloudflare({})
            elif code == "access":
                _intg_contract.refuse_access({})
            elif code == "specified":
                _intg_contract.refuse_specified({})
            elif code == "prove":
                _intg_contract.refuse_proven({})
            elif code == "ready":
                _intg_contract.refuse_ready({})
            elif code == "resolve":
                _intg_contract.refuse_resolve({})
            elif code == "production":
                _intg_contract.refuse_production({})
            elif code == "fill":
                _intg_contract.refuse_fill({})
            else:
                _intg_contract.refuse_external_write({})
        except _intg_contract.ConnectorContractError as exc:
            self._intg_contract_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Connector contract framework does not store a live connector.",
                **self._intg_contract_quiet(),
            },
            status=405,
        )

    def _intg_contract_page(self) -> None:
        identity = self._require_intg_contract_owner()
        if identity is None:
            return
        page = DASHBOARDS / "connector-contract.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Connector contract page is missing.",
                    **self._intg_contract_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _intg_contract_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_intg_contract_owner()
        if identity is None:
            return
        try:
            _intg_contract.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                yanolja=(qs.get("yanolja") or [""])[0],
                esb=(qs.get("esb") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                specified=(qs.get("specified") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "schema":
                full = _intg_contract.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._intg_contract_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _intg_contract.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._intg_contract_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _intg_contract.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._intg_contract_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _intg_contract.read_kind(ref_id)
            else:
                report = _intg_contract.build_framework()
        except _intg_contract.ConnectorContractError as exc:
            self._intg_contract_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _intg_cap_tests_quiet(self) -> dict:
        return {
            "proved": False,
            "empty_is_prove": False,
            "empty_is_ready": False,
            "empty_is_bank_feed": False,
            "live_bank_connector": False,
            "current": False,
            "fixture": None,
            "bank_feed": None,
            "bank_connector": None,
            "bank_api_called": False,
            "bank_feed_called": False,
            "payment": None,
            "money": None,
            "payment_executed": False,
            "cloudflare_mutated": False,
            "access_mutated": False,
            "score_changed": False,
            "external_write": False,
            "ledger_write": False,
            "cap_intg_01_rewritten": False,
            "cr_resolved": False,
            "invented_proven": False,
            "invented_ready": False,
        }

    def _require_intg_cap_tests_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Connector tests are Owner read."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Connector tests are Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    **self._intg_cap_tests_quiet(),
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    **self._intg_cap_tests_quiet(),
                },
                status=403,
            )
            return None
        return identity

    def _intg_cap_tests_refuse_code(self, path: str) -> str | None:
        if path in {"/api/intg/connector-cap-tests/payment", "/api/intg/connector-cap-tests/money"}:
            return "payment"
        if path in {
            "/api/intg/connector-cap-tests/bank",
            "/api/intg/connector-cap-tests/bank-api",
            "/api/intg/connector-cap-tests/live-bank",
        }:
            return "bank"
        if path in {"/api/intg/connector-cap-tests/feed", "/api/intg/connector-cap-tests/bank-feed"}:
            return "feed"
        if path == "/api/intg/connector-cap-tests/current":
            return "current"
        if path in {"/api/intg/connector-cap-tests/connector", "/api/intg/connector-cap-tests/external"}:
            return "connector"
        if path in {"/api/intg/connector-cap-tests/cloudflare", "/api/intg/connector-cap-tests/cf"}:
            return "cloudflare"
        if path in {"/api/intg/connector-cap-tests/access", "/api/intg/connector-cap-tests/cf-access"}:
            return "access"
        if path in {"/api/intg/connector-cap-tests/prove", "/api/intg/connector-cap-tests/proven"}:
            return "prove"
        if path == "/api/intg/connector-cap-tests/ready":
            return "ready"
        if path == "/api/intg/connector-cap-tests/resolve":
            return "resolve"
        if path in {
            "/api/intg/connector-cap-tests/production",
            "/api/intg/connector-cap-tests/production/mutate",
        }:
            return "production"
        if path == "/api/intg/connector-cap-tests/score":
            return "score"
        if path in {"/api/intg/connector-cap-tests/fill", "/api/intg/connector-cap-tests/note"}:
            return "fill"
        if path == "/api/intg/connector-cap-tests/rewrite":
            return "rewrite"
        return None

    def _intg_cap_tests_fail(self, exc: _intg_cap_tests.ConnectorCapTestsError) -> None:
        status = 400
        if exc.code in {
            "payment_refused",
            "bank_refused",
            "feed_refused",
            "current_refused",
            "connector_refused",
            "cloudflare_refused",
            "access_refused",
            "proven_refused",
            "ready_refused",
            "resolve_refused",
            "production_refused",
            "score_refused",
            "slots_refused",
            "writes_refused",
            "rewrite_refused",
            "alchemist_refused",
            "ledger_write_refused",
            "not_beta",
            "catalog_refused",
            "live_guard",
        }:
            status = 405
        elif exc.code == "not_found":
            status = 404
        elif exc.code == "forbidden":
            status = 403
        self._send_json(
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                **self._intg_cap_tests_quiet(),
                **_intg_cap_tests.honesty_flags(),
            },
            status=status,
        )

    def _intg_cap_tests_write_refused(self, path: str) -> None:
        identity = self._require_intg_cap_tests_owner()
        if identity is None:
            return
        try:
            code = self._intg_cap_tests_refuse_code(path)
            if code == "payment":
                _intg_cap_tests.refuse_payment({})
            elif code == "bank":
                _intg_cap_tests.refuse_bank({})
            elif code == "feed":
                _intg_cap_tests.refuse_feed({})
            elif code == "current":
                _intg_cap_tests.refuse_current({})
            elif code == "connector":
                _intg_cap_tests.refuse_connector({})
            elif code == "cloudflare":
                _intg_cap_tests.refuse_cloudflare({})
            elif code == "access":
                _intg_cap_tests.refuse_access({})
            elif code == "prove":
                _intg_cap_tests.refuse_proven({})
            elif code == "ready":
                _intg_cap_tests.refuse_ready({})
            elif code == "resolve":
                _intg_cap_tests.refuse_resolve({})
            elif code == "production":
                _intg_cap_tests.refuse_production({})
            elif code == "score":
                _intg_cap_tests.refuse_score({})
            elif code == "fill":
                _intg_cap_tests.refuse_fill({})
            elif code == "rewrite":
                _intg_cap_tests.refuse_rewrite({})
            else:
                _intg_cap_tests.refuse_external_write({})
        except _intg_cap_tests.ConnectorCapTestsError as exc:
            self._intg_cap_tests_fail(exc)
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Connector tests framework does not store a live bank connector.",
                **self._intg_cap_tests_quiet(),
            },
            status=405,
        )

    def _intg_cap_tests_page(self) -> None:
        identity = self._require_intg_cap_tests_owner()
        if identity is None:
            return
        page = DASHBOARDS / "connector-cap-tests.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Connector tests page is missing.",
                    **self._intg_cap_tests_quiet(),
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _intg_cap_tests_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_intg_cap_tests_owner()
        if identity is None:
            return
        try:
            _intg_cap_tests.guard_query(
                payment=(qs.get("payment") or [""])[0],
                money=(qs.get("money") or [""])[0],
                bank=(qs.get("bank") or [""])[0],
                feed=(qs.get("feed") or [""])[0],
                current=(qs.get("current") or [""])[0],
                connector=(qs.get("connector") or [""])[0],
                cloudflare=(qs.get("cloudflare") or [""])[0],
                access=(qs.get("access") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                production=(qs.get("production") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                write=(qs.get("write") or [""])[0],
                score=(qs.get("score") or [""])[0],
                rewrite=(qs.get("rewrite") or [""])[0],
            )
            if view == "schema":
                full = _intg_cap_tests.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    **self._intg_cap_tests_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "kinds":
                full = _intg_cap_tests.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "kinds": full["kinds"],
                    "empty": True,
                    **self._intg_cap_tests_quiet(),
                    "honesty": full["honesty"],
                }
            elif view == "framework":
                full = _intg_cap_tests.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "empty": True,
                    "recorded_count": 0,
                    "rows": [],
                    **self._intg_cap_tests_quiet(),
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _intg_cap_tests.read_kind(ref_id)
            else:
                report = _intg_cap_tests.build_framework()
        except _intg_cap_tests.ConnectorCapTestsError as exc:
            self._intg_cap_tests_fail(exc)
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _require_gws_prove_owner(self) -> dict | None:
        """CF JWT → Person; only PERS-MATT. Same Owner gate as the other proves."""
        identity = self._resolve_identity(None)
        if not identity.get("ok"):
            self._send_identity_deny(identity, required_permission="progress.read")
            return None
        person_id = identity.get("person_id")
        if person_id != _progress.PERS_MATT:
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Workspace prove is Owner (PERS-MATT) only.",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "required_person": _progress.PERS_MATT,
                    "external_writes": False,
                    "ledger_write": False,
                    "probed": False,
                    "scopes_widened": False,
                    "green_claimed": False,
                    "gmail_called": False,
                    "calendar_called": False,
                    "drive_called": False,
                    "auth_called": False,
                    "conflated": False,
                    "cr_resolved": False,
                    "messages": None,
                    "events": None,
                    "files": None,
                    "scopes": None,
                },
                status=403,
            )
            return None
        subject = identity.get("permission_subject") or identity.get("email")
        if subject and not _wi.has_permission(subject, "progress.read"):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks progress.read",
                    "person_id": person_id,
                    "required_permission": "progress.read",
                    "external_writes": False,
                    "probed": False,
                    "scopes_widened": False,
                    "cr_resolved": False,
                },
                status=403,
            )
            return None
        return identity

    def _gws_prove_refuse_code(self, path: str) -> str | None:
        if path in {"/api/gws-integrate-prove/gmail", "/api/gws-integrate-prove/gmail-write"}:
            return "gmail"
        if path in {"/api/gws-integrate-prove/calendar", "/api/gws-integrate-prove/calendar-write"}:
            return "calendar"
        if path in {"/api/gws-integrate-prove/drive", "/api/gws-integrate-prove/drive-write"}:
            return "drive"
        if path in {"/api/gws-integrate-prove/oauth", "/api/gws-integrate-prove/oauth-write", "/api/gws-integrate-prove/auth"}:
            return "auth"
        if path in {"/api/gws-integrate-prove/probe", "/api/gws-integrate-prove/probed"}:
            return "probe"
        if path in {"/api/gws-integrate-prove/scopes", "/api/gws-integrate-prove/oauth-widen"}:
            return "scopes"
        if path in {"/api/gws-integrate-prove/green", "/api/gws-integrate-prove/healthy"}:
            return "green"
        if path == "/api/gws-integrate-prove/conflate":
            return "conflate"
        if path in {"/api/gws-integrate-prove/production", "/api/gws-integrate-prove/production/mutate"}:
            return "production"
        if path in {"/api/gws-integrate-prove/prove", "/api/gws-integrate-prove/proven"}:
            return "prove"
        if path == "/api/gws-integrate-prove/resolve":
            return "resolve"
        if path == "/api/gws-integrate-prove/fill":
            return "fill"
        if path == "/api/gws-integrate-prove/ready":
            return "ready"
        return None

    def _gws_prove_page(self) -> None:
        identity = self._require_gws_prove_owner()
        if identity is None:
            return
        page = DASHBOARDS / "gws-integrate-prove.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Workspace prove page is missing.",
                    "probed": False,
                    "scopes_widened": False,
                    "green_claimed": False,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _gws_prove_get(self, qs: dict, ref_id: str | None = None, view: str | None = None) -> None:
        identity = self._require_gws_prove_owner()
        if identity is None:
            return
        try:
            _gws_prove.guard_query(
                gmail=(qs.get("gmail") or [""])[0],
                calendar=(qs.get("calendar") or [""])[0],
                drive=(qs.get("drive") or [""])[0],
                auth=(qs.get("auth") or [""])[0],
                probe=(qs.get("probe") or [""])[0],
                scopes=(qs.get("scopes") or [""])[0],
                green=(qs.get("green") or [""])[0],
                conflate=(qs.get("conflate") or [""])[0],
                production=(qs.get("production") or [""])[0],
                ready=(qs.get("ready") or [""])[0],
                proven=(qs.get("proven") or [""])[0],
                prove=(qs.get("prove") or [""])[0],
                resolve=(qs.get("resolve") or [""])[0],
                fill=(qs.get("fill") or [""])[0],
                messages=(qs.get("messages") or [""])[0],
                events=(qs.get("events") or [""])[0],
                files=(qs.get("files") or [""])[0],
                write=(qs.get("write") or [""])[0],
            )
            if view == "checklist":
                full = _gws_prove.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "checklist": full["checklist"],
                    "checklist_count": full["checklist_count"],
                    "checklist_executed": full["checklist_executed"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "probed": False,
                    "scopes_widened": False,
                    "green_claimed": False,
                    "conflated": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "schema":
                full = _gws_prove.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "schema": full["schema"],
                    "framework_skeleton": full["framework_skeleton"],
                    "probed": False,
                    "green_claimed": False,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "log":
                full = _gws_prove.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "log": full["log"],
                    "log_valid": full["log_valid"],
                    "status": full["status"],
                    "framework_skeleton": full["framework_skeleton"],
                    "probed": False,
                    "messages": None,
                    "scopes": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "surfaces":
                full = _gws_prove.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "surfaces": full["surfaces"],
                    "surface_count": full["surface_count"],
                    "distinction": full["distinction"],
                    "probed": False,
                    "conflated": False,
                    "green_claimed": False,
                    "messages": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif view == "gaps":
                full = _gws_prove.build_framework()
                report = {
                    "ok": True,
                    "cap": full["cap"],
                    "gaps": full["gaps"],
                    "gap_count": full["gap_count"],
                    "probed": False,
                    "green_claimed": False,
                    "scopes": None,
                    "ledger_write": False,
                    "honesty": full["honesty"],
                }
            elif ref_id:
                report = _gws_prove.read_ref(ref_id)
            else:
                report = _gws_prove.build_framework()
        except _gws_prove.GwsProveError as exc:
            status = 404 if exc.code == "not_found" else 400
            if exc.code in {
                "gmail_write_refused",
                "calendar_write_refused",
                "drive_write_refused",
                "oauth_write_refused",
                "probe_refused",
                "scope_widen_refused",
                "green_refused",
                "conflate_refused",
                "production_refused",
                "ready_refused",
                "proven_refused",
                "resolve_refused",
                "slots_refused",
                "invent_metrics_refused",
                "success_refused",
                "writes_refused",
                "alchemist_refused",
            }:
                status = 405
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "probed": False,
                    "scopes_widened": False,
                    "green_claimed": False,
                    "gmail_called": False,
                    "calendar_called": False,
                    "drive_called": False,
                    "auth_called": False,
                    "conflated": False,
                    "production_mutated": False,
                    "cr_resolved": False,
                    "messages": None,
                    "events": None,
                    "files": None,
                    "scopes": None,
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "read_failed",
                    "message": type(exc).__name__,
                    "external_writes": False,
                    "ledger_write": False,
                    "probed": False,
                    "scopes_widened": False,
                    "cr_resolved": False,
                },
                status=500,
            )
            return
        report["person_id"] = identity.get("person_id")
        self._send_json(report)

    def _gws_prove_write_refused(self, path: str) -> None:
        identity = self._require_gws_prove_owner()
        if identity is None:
            return
        try:
            code = self._gws_prove_refuse_code(path)
            if code == "gmail":
                _gws_prove.refuse_gmail_write({})
            elif code == "calendar":
                _gws_prove.refuse_calendar_write({})
            elif code == "drive":
                _gws_prove.refuse_drive_write({})
            elif code == "auth":
                _gws_prove.refuse_oauth_write({})
            elif code == "probe":
                _gws_prove.refuse_probe({})
            elif code == "scopes":
                _gws_prove.refuse_scope_widen({})
            elif code == "green":
                _gws_prove.refuse_green({})
            elif code == "conflate":
                _gws_prove.refuse_conflate({})
            elif code == "production":
                _gws_prove.refuse_production({})
            elif code == "prove":
                _gws_prove.refuse_proven({})
            elif code == "resolve":
                _gws_prove.refuse_resolve({})
            elif code == "fill":
                _gws_prove.refuse_fill({})
            elif code == "ready":
                _gws_prove.refuse_ready({})
            else:
                _gws_prove.refuse_external_write({})
        except _gws_prove.GwsProveError as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "external_writes": False,
                    "ledger_write": False,
                    "probed": False,
                    "scopes_widened": False,
                    "green_claimed": False,
                    "gmail_called": False,
                    "calendar_called": False,
                    "drive_called": False,
                    "auth_called": False,
                    "conflated": False,
                    "production_mutated": False,
                    "cr_resolved": False,
                    "messages": None,
                    "scopes": None,
                    **_gws_prove.honesty_flags(),
                },
                status=405,
            )
            return
        self._send_json(
            {
                "ok": False,
                "error": "writes_refused",
                "message": "Workspace prove is read-only. Gmail is not Calendar. Not GREEN. No probe.",
                "external_writes": False,
                "ledger_write": False,
                "probed": False,
                "scopes_widened": False,
                "green_claimed": False,
                "conflated": False,
                "cr_resolved": False,
            },
            status=405,
        )

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

    def _intel_eval_cost_get(self, qs: dict) -> None:
        """GET /api/intel/eval-cost — Owner summary. Does not create the ledger."""
        identity = self._require_progress_owner()
        if identity is None:
            return
        raw_limit = (qs.get("limit") or ["20"])[0]
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            self._send_json(
                {"ok": False, "error": "bad_limit", "message": "limit must be an integer"},
                status=400,
            )
            return
        try:
            out = _intel_cost.read_summary(identity.get("person_id"), limit=limit)
        except _intel_cost.IntelEvalCostError as exc:
            status = 403 if exc.code == "denied" else 400
            self._send_json(
                {"ok": False, "error": exc.code, "message": str(exc), **_intel_cost.honesty_flags()},
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json(
            {"ok": True, "person_id": identity.get("person_id"), **out}
        )

    def _intel_eval_cost_post(self) -> None:
        """POST /api/intel/eval-cost — append one call. Refuses billing and price lookup."""
        identity = self._require_progress_owner()
        if identity is None:
            return
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {"ok": False, "error": "bad_payload", "message": f"invalid JSON: {exc}"},
                status=400,
            )
            return
        try:
            out = _intel_cost.record_call(body, person_id=identity.get("person_id"))
        except _intel_cost.IntelEvalCostError as exc:
            status = 403 if exc.code == "denied" else 400
            self._send_json(
                {
                    "ok": False,
                    "error": exc.code,
                    "message": str(exc),
                    "appended": False,
                    **_intel_cost.honesty_flags(),
                },
                status=status,
            )
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json(
            {"ok": True, "person_id": identity.get("person_id"), **out}
        )

    def _intel_rule_actor(self, action: str, body: dict | None = None) -> tuple[str, bool] | None:
        """Identity required. Owner always. Role only if rbac.can already grants it.

        Does not insert a permission. Anonymous fails closed.
        """
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(
                identity, required_permission=_intel_rule.permission_for(action)
            )
            return None
        person_id = (identity.get("person_id") or "").strip()
        if not person_id:
            self._send_json(
                {
                    "ok": False,
                    "error": "denied",
                    "message": "anonymous callers are refused",
                    "appended": False,
                    "promoted": False,
                    "executed": False,
                    **_intel_rule.honesty_flags(),
                },
                status=403,
            )
            return None
        role_allowed = False
        if person_id != _intel_rule.OWNER_PERSON:
            try:
                role_allowed = bool(
                    _rbac.can(person_id, _intel_rule.permission_for(action))
                )
            except Exception:  # noqa: BLE001
                role_allowed = False
        return person_id, role_allowed

    def _intel_rule_fail(self, exc: Exception) -> None:
        code = getattr(exc, "code", "invalid")
        if code == "denied":
            status = 403
        elif code == "not_found":
            status = 404
        elif code == "writes_refused":
            status = 405
        else:
            status = 400
        self._send_json(
            {
                "ok": False,
                "error": code,
                "message": str(exc),
                "appended": False,
                "promoted": False,
                "executed": False,
                "live": False,
                **_intel_rule.honesty_flags(),
            },
            status=status,
        )

    def _intel_rule_refuse_kind(self, path: str) -> str | None:
        low = (path or "").rstrip("/")
        if low in {
            "/api/intel/approve-to-rule/promote",
            "/api/intel/approve-to-rule/auto-promote",
        }:
            return "promote"
        if low in {
            "/api/intel/approve-to-rule/proven",
            "/api/intel/approve-to-rule/ready",
        }:
            return "proven"
        if low in {
            "/api/intel/approve-to-rule/execute",
            "/api/intel/approve-to-rule/run",
        }:
            return "execute"
        if low == "/api/intel/approve-to-rule/production":
            return "production"
        return None

    def _intel_rule_refuse(self, kind: str) -> None:
        actor = self._intel_rule_actor("read")
        if actor is None:
            return
        fn = {
            "promote": _intel_rule.refuse_promote,
            "proven": _intel_rule.refuse_proven,
            "execute": _intel_rule.refuse_execute,
            "production": _intel_rule.refuse_production,
        }.get(kind, _intel_rule.refuse_method)
        try:
            fn({})
        except _intel_rule.IntelRuleError as exc:
            self._intel_rule_fail(exc)

    def _intel_rule_writes_refused(self) -> None:
        actor = self._intel_rule_actor("read")
        if actor is None:
            return
        try:
            _intel_rule.refuse_method({})
        except _intel_rule.IntelRuleError as exc:
            self._intel_rule_fail(exc)

    def _intel_rule_handled(self, path: str, method: str) -> bool:
        if path != "/api/intel/approve-to-rule" and not path.startswith(
            "/api/intel/approve-to-rule/"
        ):
            return False
        kind = self._intel_rule_refuse_kind(path)
        if method in {"PUT", "PATCH"}:
            if kind:
                self._intel_rule_refuse(kind)
            else:
                self._intel_rule_writes_refused()
            return True
        if method == "POST":
            if kind:
                self._intel_rule_refuse(kind)
                return True
            if path == "/api/intel/approve-to-rule/note":
                self._intel_rule_post("note", _intel_rule.record_note)
                return True
            if path == "/api/intel/approve-to-rule/approve":
                self._intel_rule_post("approve", _intel_rule.approve_note)
                return True
            if path == "/api/intel/approve-to-rule/rule":
                self._intel_rule_post("rule", _intel_rule.stub_rule)
                return True
            self._intel_rule_writes_refused()
            return True
        if method == "GET":
            if kind:
                self._intel_rule_refuse(kind)
                return True
            if path == "/api/intel/approve-to-rule":
                self._intel_rule_list()
                return True
            match = re.match(r"^/api/intel/approve-to-rule/([^/]+)$", path)
            reserved = {
                "note",
                "approve",
                "rule",
                "promote",
                "auto-promote",
                "proven",
                "ready",
                "execute",
                "run",
                "production",
            }
            if match and match.group(1) not in reserved:
                self._intel_rule_read(match.group(1))
                return True
            self._send_err(404, "not found")
            return True
        return False

    def _intel_rule_list(self) -> None:
        actor = self._intel_rule_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = _intel_rule.list_experiments(person_id, role_allowed=role_allowed)
        except _intel_rule.IntelRuleError as exc:
            self._intel_rule_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"ok": True, "person_id": person_id, **out})

    def _intel_rule_read(self, experiment_id: str) -> None:
        actor = self._intel_rule_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = _intel_rule.read_experiment(
                experiment_id, person_id, role_allowed=role_allowed
            )
        except _intel_rule.IntelRuleError as exc:
            self._intel_rule_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"ok": True, "person_id": person_id, **out})

    def _intel_rule_post(self, action: str, fn) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_payload",
                    "message": f"invalid JSON: {exc}",
                    "appended": False,
                    "promoted": False,
                    **_intel_rule.honesty_flags(),
                },
                status=400,
            )
            return
        actor = self._intel_rule_actor(action, body)
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = fn(body, person_id=person_id, role_allowed=role_allowed)
        except _intel_rule.IntelRuleError as exc:
            self._intel_rule_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"ok": True, "person_id": person_id, **out})

    def _sop_actor(self, action: str, body: dict | None = None) -> tuple[str, bool] | None:
        """Identity required. Owner always. Role only if rbac.can already grants it.

        Does not insert a permission. Anonymous fails closed.
        """
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(
                identity, required_permission=_sop.permission_for(action)
            )
            return None
        person_id = (identity.get("person_id") or "").strip()
        if not person_id:
            self._send_json(
                {
                    "ok": False,
                    "error": "denied",
                    "message": "anonymous callers are refused",
                    **_sop.honesty_flags(),
                },
                status=403,
            )
            return None
        role_allowed = False
        if person_id != _sop.OWNER_PERSON:
            try:
                role_allowed = bool(
                    _rbac.can(person_id, _sop.permission_for(action))
                )
            except Exception:  # noqa: BLE001
                role_allowed = False
        return person_id, role_allowed

    def _sop_fail(self, exc: Exception) -> None:
        code = getattr(exc, "code", "invalid")
        if code == "denied":
            status = 403
        elif code == "not_found":
            status = 404
        else:
            status = 400
        self._send_json(
            {
                "ok": False,
                "error": code,
                "message": str(exc),
                **_sop.honesty_flags(),
            },
            status=status,
        )

    def _sop_list(self) -> None:
        actor = self._sop_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = _sop.list_sops(person_id, role_allowed=role_allowed)
        except _sop.SopFactoryError as exc:
            self._sop_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"ok": True, "person_id": person_id, **out})

    def _sop_read(self, sop_id: str) -> None:
        actor = self._sop_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = _sop.read_sop(sop_id, person_id, role_allowed=role_allowed)
        except _sop.SopFactoryError as exc:
            self._sop_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"ok": True, "person_id": person_id, **out})

    def _sop_post(self, action: str, fn) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_payload",
                    "message": f"invalid JSON: {exc}",
                    **_sop.honesty_flags(),
                },
                status=400,
            )
            return
        actor = self._sop_actor(action, body)
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = fn(body, person_id=person_id, role_allowed=role_allowed)
        except _sop.SopFactoryError as exc:
            self._sop_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"ok": True, "person_id": person_id, **out})

    def _sop_draft_post(self) -> None:
        self._sop_post("draft", _sop.create_draft)

    def _sop_version_post(self) -> None:
        self._sop_post("version", _sop.append_version)

    def _sop_approve_post(self) -> None:
        self._sop_post("approve", _sop.approve)

    def _crm_identity_blast(self, path: str) -> bool:
        low = (path or "").lower()
        return low in {
            "/api/crm/blast",
            "/api/crm/identity/blast",
            "/api/marketing/blast",
            "/api/klaviyo/send",
            "/api/email/blast",
        }

    def _crm_actor(self, action: str, body: dict | None = None) -> tuple[str, bool] | None:
        """Identity required. Owner always. Staff only if rbac.can already grants it.

        Does not insert a permission. Anonymous fails closed.
        """
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(
                identity, required_permission=_crm_ident.permission_for(action)
            )
            return None
        person_id = (identity.get("person_id") or "").strip()
        if not person_id:
            self._send_json(
                {
                    "ok": False,
                    "error": "denied",
                    "message": "anonymous callers are refused",
                    "marketing_blast": False,
                    "identity_graph_complete": False,
                    **_crm_ident.honesty_flags(),
                },
                status=403,
            )
            return None
        role_allowed = False
        if person_id != _crm_ident.OWNER_PERSON:
            try:
                role_allowed = bool(
                    _rbac.can(person_id, _crm_ident.permission_for(action))
                )
            except Exception:  # noqa: BLE001
                role_allowed = False
        return person_id, role_allowed

    def _crm_fail(self, exc: Exception) -> None:
        code = getattr(exc, "code", "invalid")
        if code == "denied":
            status = 403
        elif code in {"not_found", "not_a_customer"}:
            status = 404
        elif code in {"marketing_refused", "append_only"}:
            status = 405
        else:
            status = 400
        self._send_json(
            {
                "ok": False,
                "error": code,
                "message": str(exc),
                "marketing_blast": False,
                "merged": False,
                "identity_graph_complete": False,
                **_crm_ident.honesty_flags(),
            },
            status=status,
        )

    def _crm_identity_blast_refused(self) -> None:
        actor = self._crm_actor("read")
        if actor is None:
            return
        try:
            _crm_ident.refuse_marketing({})
        except _crm_ident.CrmIdentityError as exc:
            self._crm_fail(exc)

    def _crm_identity_append_only_refused(self) -> None:
        if self._crm_identity_blast(urlparse(self.path).path):
            self._crm_identity_blast_refused()
            return
        actor = self._crm_actor("read")
        if actor is None:
            return
        self._crm_fail(
            _crm_ident.CrmIdentityError(
                "Customer rows and memory notes are append-only.",
                code="append_only",
            )
        )

    def _crm_identity_page(self) -> None:
        actor = self._crm_actor("read")
        if actor is None:
            return
        page = DASHBOARDS / "crm-identity.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Customer identity page is missing.",
                    "marketing_blast": False,
                    "identity_graph_complete": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _crm_identity_list(self, qs: dict) -> None:
        actor = self._crm_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        entity = (qs.get("entity") or [""])[0] or None
        try:
            out = _crm_ident.list_customers(
                person_id, role_allowed=role_allowed, entity=entity
            )
        except _crm_ident.CrmIdentityError as exc:
            self._crm_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"person_id": person_id, **out})

    def _crm_identity_read(self, customer_id: str) -> None:
        actor = self._crm_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = _crm_ident.read_customer(
                customer_id, person_id, role_allowed=role_allowed
            )
        except _crm_ident.CrmIdentityError as exc:
            self._crm_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"person_id": person_id, **out})

    def _crm_identity_post(self, action: str, fn) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_payload",
                    "message": f"invalid JSON: {exc}",
                    "marketing_blast": False,
                    **_crm_ident.honesty_flags(),
                },
                status=400,
            )
            return
        actor = self._crm_actor(action, body)
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = fn(body, person_id=person_id, role_allowed=role_allowed)
        except _crm_ident.CrmIdentityError as exc:
            self._crm_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"person_id": person_id, **out})

    def _bzg_reputation_scrape(self, path: str) -> bool:
        low = (path or "").lower().rstrip("/")
        return low in {
            "/api/bzg/reputation/scrape",
            "/api/bzg/reviews/scrape",
            "/api/google/reviews/scrape",
            "/api/tripadvisor/scrape",
        }

    def _bzg_reputation_reply(self, path: str) -> bool:
        low = (path or "").lower().rstrip("/")
        return low in {
            "/api/bzg/reputation/reply",
            "/api/bzg/reviews/reply",
            "/api/reviews/auto-reply",
        }

    def _bzg_actor(self, action: str, body: dict | None = None) -> tuple[str, bool] | None:
        """Identity required. Owner always. Staff only if rbac.can already grants it."""
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(
                identity, required_permission=_bzg_rep.permission_for(action)
            )
            return None
        person_id = (identity.get("person_id") or "").strip()
        if not person_id:
            self._send_json(
                {
                    "ok": False,
                    "error": "denied",
                    "message": "anonymous callers are refused",
                    "summary_rating": None,
                    "five_star_invented": False,
                    "scraped": False,
                    "auto_reply": False,
                    **_bzg_rep.honesty_flags(),
                },
                status=403,
            )
            return None
        role_allowed = False
        if person_id != _bzg_rep.OWNER_PERSON:
            try:
                role_allowed = bool(_rbac.can(person_id, _bzg_rep.permission_for(action)))
            except Exception:  # noqa: BLE001
                role_allowed = False
        return person_id, role_allowed

    def _bzg_fail(self, exc: Exception) -> None:
        code = getattr(exc, "code", "invalid")
        if code == "denied":
            status = 403
        elif code == "not_an_observation":
            status = 404
        elif code in {
            "scrape_refused",
            "auto_reply_refused",
            "append_only",
            "summary_refused",
        }:
            status = 405
        else:
            status = 400
        self._send_json(
            {
                "ok": False,
                "error": code,
                "message": str(exc),
                "summary_rating": None,
                "five_star_invented": False,
                "source_connected": False,
                "scraped": False,
                "auto_reply": False,
                "guest_reply_sent": False,
                **_bzg_rep.honesty_flags(),
            },
            status=status,
        )

    def _bzg_reputation_scrape_refused(self) -> None:
        actor = self._bzg_actor("read")
        if actor is None:
            return
        try:
            _bzg_rep.scrape({})
        except _bzg_rep.ReputationObserveError as exc:
            self._bzg_fail(exc)

    def _bzg_reputation_reply_refused(self) -> None:
        actor = self._bzg_actor("read")
        if actor is None:
            return
        try:
            _bzg_rep.reply_to_guest({})
        except _bzg_rep.ReputationObserveError as exc:
            self._bzg_fail(exc)

    def _bzg_reputation_summary_refused(self) -> None:
        actor = self._bzg_actor("read")
        if actor is None:
            return
        try:
            _bzg_rep.refuse_summary({})
        except _bzg_rep.ReputationObserveError as exc:
            self._bzg_fail(exc)

    def _bzg_reputation_append_only_refused(self) -> None:
        path = urlparse(self.path).path
        if self._bzg_reputation_scrape(path):
            self._bzg_reputation_scrape_refused()
            return
        if self._bzg_reputation_reply(path):
            self._bzg_reputation_reply_refused()
            return
        actor = self._bzg_actor("read")
        if actor is None:
            return
        self._bzg_fail(
            _bzg_rep.ReputationObserveError(
                "Review observations are append-only.",
                code="append_only",
            )
        )

    def _bzg_reputation_page(self) -> None:
        actor = self._bzg_actor("read")
        if actor is None:
            return
        page = DASHBOARDS / "bzg-reputation.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Review observe page is missing.",
                    "summary_rating": None,
                    "five_star_invented": False,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bzg_reputation_list(self, qs: dict) -> None:
        actor = self._bzg_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        venue = (qs.get("venue") or [""])[0] or None
        try:
            out = _bzg_rep.list_observations(
                person_id, role_allowed=role_allowed, venue=venue
            )
        except _bzg_rep.ReputationObserveError as exc:
            self._bzg_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"person_id": person_id, **out})

    def _bzg_reputation_read(self, observation_id: str) -> None:
        actor = self._bzg_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = _bzg_rep.read_observation(
                observation_id, person_id, role_allowed=role_allowed
            )
        except _bzg_rep.ReputationObserveError as exc:
            self._bzg_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"person_id": person_id, **out})

    def _bzg_reputation_post(self, action: str, fn) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_payload",
                    "message": f"invalid JSON: {exc}",
                    "summary_rating": None,
                    "five_star_invented": False,
                    **_bzg_rep.honesty_flags(),
                },
                status=400,
            )
            return
        actor = self._bzg_actor(action, body)
        if actor is None:
            return
        person_id, role_allowed = actor
        try:
            out = fn(body, person_id=person_id, role_allowed=role_allowed)
        except _bzg_rep.ReputationObserveError as exc:
            self._bzg_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"person_id": person_id, **out})

    def _ggv_social_metricool(self, path: str) -> bool:
        low = (path or "").lower().rstrip("/")
        return low in {
            "/api/ggv/social/metricool",
            "/api/ggv/social/publish",
            "/api/metricool/publish",
        }

    def _ggv_social_ads(self, path: str) -> bool:
        low = (path or "").lower().rstrip("/")
        return low in {
            "/api/ggv/social/ads",
            "/api/ggv/social/spend",
            "/api/ggv/social/boost",
        }

    def _ggv_actor(self, action: str, body: dict | None = None) -> tuple[str, bool] | None:
        """Identity required. Owner always. Staff only if rbac.can already grants it."""
        identity = self._resolve_identity(body)
        if not identity.get("ok"):
            self._send_identity_deny(
                identity, required_permission=_ggv_social.permission_for(action)
            )
            return None
        person_id = (identity.get("person_id") or "").strip()
        if not person_id:
            self._send_json(
                {
                    "ok": False,
                    "error": "denied",
                    "message": "anonymous callers are refused",
                    "metricool_write": False,
                    "invented_metrics": False,
                    "paid_ads_spend": None,
                    "blended_score": None,
                    **_ggv_social.honesty_flags(),
                },
                status=403,
            )
            return None
        role_allowed = False
        if person_id != _ggv_social.OWNER_PERSON:
            try:
                role_allowed = bool(_rbac.can(person_id, _ggv_social.permission_for(action)))
            except Exception:  # noqa: BLE001
                role_allowed = False
        return person_id, role_allowed

    def _ggv_fail(self, exc: Exception) -> None:
        code = getattr(exc, "code", "invalid")
        if code == "denied":
            status = 403
        elif code in {
            "metricool_write_refused",
            "paid_ads_refused",
            "invented_metrics",
            "read_only",
            "cr_resolve_refused",
            "invented_proven",
        }:
            status = 405
        else:
            status = 400
        self._send_json(
            {
                "ok": False,
                "error": code,
                "message": str(exc),
                "metricool_write": False,
                "invented_metrics": False,
                "paid_ads_spend": None,
                "paid_ads_called": False,
                "blended_score": None,
                "surfaces_blended": False,
                **_ggv_social.honesty_flags(),
            },
            status=status,
        )

    def _ggv_social_metricool_refused(self) -> None:
        actor = self._ggv_actor("read")
        if actor is None:
            return
        try:
            _ggv_social.metricool_write({})
        except _ggv_social.SocialDeriveError as exc:
            self._ggv_fail(exc)

    def _ggv_social_ads_refused(self) -> None:
        actor = self._ggv_actor("read")
        if actor is None:
            return
        try:
            _ggv_social.paid_ads({})
        except _ggv_social.SocialDeriveError as exc:
            self._ggv_fail(exc)

    def _ggv_social_write_refused(self, path: str) -> None:
        if self._ggv_social_metricool(path):
            self._ggv_social_metricool_refused()
            return
        if self._ggv_social_ads(path):
            self._ggv_social_ads_refused()
            return
        actor = self._ggv_actor("read")
        if actor is None:
            return
        self._ggv_fail(
            _ggv_social.SocialDeriveError(
                "Social derive views are read-only.",
                code="read_only",
            )
        )

    def _ggv_social_page(self) -> None:
        actor = self._ggv_actor("read")
        if actor is None:
            return
        page = DASHBOARDS / "ggv-social.html"
        if not page.is_file():
            self._send_json(
                {
                    "ok": False,
                    "error": "page_missing",
                    "message": "Social derive page is missing.",
                    "metricool_write": False,
                    "invented_metrics": False,
                    "paid_ads_spend": None,
                    "blended_score": None,
                },
                status=500,
            )
            return
        data = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _ggv_social_get(self, qs: dict) -> None:
        actor = self._ggv_actor("read")
        if actor is None:
            return
        person_id, role_allowed = actor
        brand = (qs.get("brand") or [""])[0]
        raw_window = (qs.get("window_days") or [""])[0].strip()
        window = None
        if raw_window:
            if not raw_window.isdigit():
                self._ggv_fail(
                    _ggv_social.SocialDeriveError(
                        "window_days must be a whole number",
                        code="invalid",
                    )
                )
                return
            window = int(raw_window)
        try:
            out = _ggv_social.derive_view(
                brand,
                person_id=person_id,
                role_allowed=role_allowed,
                window_days=window,
            )
        except _ggv_social.SocialDeriveError as exc:
            self._ggv_fail(exc)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_err(500, str(exc))
            return
        self._send_json({"person_id": person_id, **out})

    def _ggv_social_post(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_payload",
                    "message": f"invalid JSON: {exc}",
                    "metricool_write": False,
                    "invented_metrics": False,
                    "paid_ads_spend": None,
                    "blended_score": None,
                    **_ggv_social.honesty_flags(),
                },
                status=400,
            )
            return
        if not isinstance(body, dict):
            body = {}
        actor = self._ggv_actor("read", body)
        if actor is None:
            return
        try:
            if _ggv_social.looks_like_metricool_write(body):
                _ggv_social.metricool_write(body)
            elif _ggv_social.looks_like_ads(body):
                _ggv_social.paid_ads(body)
            elif _ggv_social.looks_like_invented_metric(body):
                _ggv_social.invent_metrics(body)
            else:
                _ggv_social.refuse_write(body)
        except _ggv_social.SocialDeriveError as exc:
            self._ggv_fail(exc)

    # ----- Uma Blu ops (Devi commissioning: fail-closed) -----

    def _require_uma_ops(self, body: dict | None = None) -> str | None:
        """Identity + venue.close.read + Uma or BZG F&B scope. Fail closed.

        SCOPE-BZG-UMA and SCOPE-BZG-FB are equivalent for these APIs.
        Does not grant payment approve, close verify, progress, or Owner.
        """
        permission = "venue.close.read"
        accepted = ("SCOPE-BZG-UMA", "SCOPE-BZG-FB")
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
        if not any(row.get("scope_id") in accepted for row in scopes):
            self._send_json(
                {
                    "ok": False,
                    "error": "forbidden",
                    "message": "subject lacks SCOPE-BZG-UMA or SCOPE-BZG-FB",
                    "subject": subject,
                    "person_id": person_id,
                    "required_permission": permission,
                    "required_scope": "SCOPE-BZG-UMA",
                    "accepted_scopes": list(accepted),
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

    def _get_leads_triage(self, qs: dict) -> None:
        """GET /api/leads/triage — hot/open Habitat queue. Same identity gate as list."""
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
            payload = _lead_spine.api_triage_board(
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
                # Operator click clock. Not an SLA target. Body may supply touched_at.
                touched = str(body.get("touched_at") or "").strip() or _lead_spine.now_utc_iso()
                result = _lead_spine.record_human_touch(
                    lead_id,
                    touched_at=touched,
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
                "next_action": _lead_spine.next_action_for_lead(lead),
                "speed": _lead_spine.speed_to_lead_signal(lead),
                "work_item_hook": _lead_spine.work_item_hook(lead),
                "claim_hook": _lead_spine.claim_hook(lead),
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
