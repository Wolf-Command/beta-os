#!/usr/bin/env python3
"""Phase 1 Wolf Intelligence helpers — permissions, memory governance, DB helpers.

Identity note: Cloudflare JWT is NOT wired yet.
Current Beta subject resolution is DEVELOPMENT_IDENTITY_ASSERTION only
(X-Wolf-Subject / JSON subject / query subject). It is spoofable.
Prefer resolve_development_identity_assertion(). Legacy name
resolve_authenticated_subject() remains as a thin alias — it does NOT mean
real authentication occurred. Production must use Cloudflare Access JWT.
Timezone: store published_at_utc as UTC; planning/display day = Asia/Makassar.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
TZ = ZoneInfo("Asia/Makassar")

SHOT_LIST_NOTE = (
    "Suggested coverage. Adapt based on conditions, talent and creative "
    "opportunities on location."
)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def has_permission(
    subject: str | None,
    permission: str,
    *,
    brand_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Canonical path preferred: email → Person → Assignment → Role → Scope → Permission.

    Legacy `permissions` email rows remain TRANSITIONAL fallback only when no Person
    exists yet. Email is a DEVELOPMENT identity input, not permission truth.
    """
    email = (subject or "").strip().lower()
    if not email or "@" not in email:
        return False
    own = conn is None
    c = conn or db_connect()
    try:
        # Prefer canonical RBAC when Person is known
        try:
            from core import identity as _identity
            from core import rbac as _rbac

            person = _identity.resolve_person_from_email(email, conn=c)
            if person and person.get("person_id"):
                target = _rbac.default_content_target()
                # Content Machine brand_id is a content-library brand, not org_brands —
                # keep GGV content target; do not invent org brand from client brand strings.
                return _rbac.can(
                    person["person_id"], permission, target, conn=c
                )
        except Exception:
            # Fall through to transitional legacy if core unavailable mid-boot
            pass

        # TRANSITIONAL: legacy email subject rows (no Person mapped)
        row = c.execute(
            """
            SELECT 1 FROM permissions
            WHERE lower(subject)=?
              AND permission=?
              AND (brand_id IS NULL OR brand_id=? OR ifnull(?, '')='')
            LIMIT 1
            """,
            (email, permission, brand_id or "", brand_id or ""),
        ).fetchone()
        return row is not None
    finally:
        if own:
            c.close()



KNOWN_PERMISSIONS = (
    "can_create_plan",
    "can_edit_plan",
    "can_approve_plan",
    "can_view_plan",
    "can_update_production",
    "can_upload",
    "can_use_wolf_intelligence",
)


def list_permissions(
    subject: str | None,
    *,
    brand_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, bool]:
    """Return {permission: bool} for known bits — data-driven, emails as subjects."""
    return {
        p: has_permission(subject, p, brand_id=brand_id, conn=conn)
        for p in KNOWN_PERMISSIONS
    }


def resolve_subject(headers: dict | None, body: dict | None) -> str | None:
    """Pull subject from X-Wolf-Subject header or JSON body.subject — no CF invent."""
    subj = None
    if headers:
        for k, v in headers.items():
            if k.lower() == "x-wolf-subject":
                subj = (v or "").strip()
                break
    if not subj and body:
        subj = (body.get("subject") or body.get("actor") or "").strip()
    return subj or None



def resolve_development_identity_assertion(request_like) -> str | None:
    """DEVELOPMENT_IDENTITY_ASSERTION — spoofable Beta subject email.

    Reads X-Wolf-Subject header or JSON body.subject / actor.
    This is NOT authentication. Cloudflare Access JWT is NOT wired.
    Do not treat the returned value as a verified login.
    """
    headers = None
    body = None
    if isinstance(request_like, dict):
        headers = request_like.get("headers") or {}
        body = request_like.get("body") or {}
    else:
        # http.server handler duck-typing
        headers = {k: v for k, v in getattr(request_like, "headers", {}).items()}
        body = getattr(request_like, "_wolf_body_cache", None) or {}
    return resolve_subject(headers, body if isinstance(body, dict) else {})


def resolve_authenticated_subject(request_like) -> str | None:
    """LEGACY ALIAS — does NOT imply real authentication.

    Calls resolve_development_identity_assertion(). Kept so Content Machine
    permission gates keep working unchanged. Prefer the honest name in new code.
    """
    return resolve_development_identity_assertion(request_like)


def operational_lane_clause(column: str = "data_lane") -> str:
    """SQL fragment: prefer operational; treat NULL legacy as operational only when explicit."""
    return f"(ifnull({column}, 'operational') = 'operational')"

def write_memory_item(
    conn: sqlite3.Connection,
    *,
    brand_id: str | None,
    mem_type: str,
    text: str,
    scope: str = "BRAND",
    source_type: str | None = None,
    source_id: str | None = None,
    evidence_refs: list | None = None,
    confidence: float | None = None,
    approval_state: str = "PROPOSED",
    status: str | None = None,
    approved_by: str | None = None,
) -> int:
    """Insert memory. RULE: ACTIVE only if APPROVED — otherwise force non-ACTIVE."""
    approval_state = (approval_state or "PROPOSED").upper()
    if status is None:
        status = "ACTIVE" if approval_state == "APPROVED" else "PROPOSED"
    status = status.upper()
    # Enforce ACTIVE ⇒ APPROVED
    if status == "ACTIVE" and approval_state != "APPROVED":
        status = "PROPOSED"
    cur = conn.execute(
        """
        INSERT INTO memory_items (
          brand_id, type, scope, text, source_type, source_id, evidence_refs,
          confidence, status, approval_state, approved_by, created_at, version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            brand_id,
            mem_type.upper(),
            scope,
            text.strip(),
            source_type,
            source_id,
            json.dumps(evidence_refs or []),
            confidence,
            status,
            approval_state,
            approved_by if approval_state == "APPROVED" else None,
            now_iso(),
        ),
    )
    return int(cur.lastrowid)


def active_memory(conn: sqlite3.Connection, brand_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT * FROM memory_items
        WHERE brand_id=? AND status='ACTIVE' AND approval_state='APPROVED'
        ORDER BY id
        """,
        (brand_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def log_skill_run(
    conn: sqlite3.Connection,
    *,
    skill_name: str,
    brand_id: str | None,
    plan_id: int | None,
    payload: dict,
    data_lane: str = "operational",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO skill_runs (
          skill_name, brand_id, plan_id, input_json, result_json, evidence_json,
          confidence, assumptions_json, missing_information_json, status, created_at, data_lane
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            skill_name,
            brand_id,
            plan_id,
            json.dumps(payload.get("input") or {}),
            json.dumps(payload.get("result")),
            json.dumps(payload.get("evidence") or []),
            payload.get("confidence"),
            json.dumps(payload.get("assumptions") or []),
            json.dumps(payload.get("missing_information") or []),
            payload.get("status") or "ok",
            now_iso(),
            data_lane,
        ),
    )
    return int(cur.lastrowid)


def fortnight_bounds(anchor: date | None = None) -> tuple[str, str]:
    d = anchor or datetime.now(TZ).date()
    # Align to Monday start of current week, then 14-day window
    monday = d - timedelta(days=d.weekday())
    end = monday + timedelta(days=13)
    return monday.isoformat(), end.isoformat()


BRAND_TITLE_NAMES = {
    "habitat": "Habitat",
    "umablu": "Uma Blu",
    "atrium": "Atrium",
    "selo": "Selo",
    "tropik": "Tropik",
}


def brand_title_name(brand_id: str, display_name: str | None = None) -> str:
    """Short brand name for human plan titles."""
    bid = (brand_id or "").strip().lower()
    if bid in BRAND_TITLE_NAMES:
        return BRAND_TITLE_NAMES[bid]
    if display_name:
        return str(display_name).split("/")[0].strip() or (bid.title() if bid else "Brand")
    return bid.title() if bid else "Brand"


def format_fortnight_title(
    brand_id: str,
    period_start: str,
    period_end: str,
    display_name: str | None = None,
) -> str:
    """Human plan title, e.g. Habitat Fortnight Sep 14—27."""
    name = brand_title_name(brand_id, display_name)
    try:
        start = date.fromisoformat(str(period_start)[:10])
        end = date.fromisoformat(str(period_end)[:10])
    except ValueError:
        return f"{name} Fortnight"
    if start.month == end.month and start.year == end.year:
        span = f"{start.strftime('%b')} {start.day}—{end.day}"
    else:
        span = f"{start.strftime('%b')} {start.day}—{end.strftime('%b')} {end.day}"
    return f"{name} Fortnight {span}"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def skill_envelope(
    result: Any,
    *,
    evidence: list | None = None,
    confidence: float = 0.5,
    assumptions: list | None = None,
    missing_information: list | None = None,
) -> dict:
    return {
        "result": result,
        "evidence": evidence or [],
        "confidence": confidence,
        "assumptions": assumptions or [],
        "missing_information": missing_information or [],
    }
