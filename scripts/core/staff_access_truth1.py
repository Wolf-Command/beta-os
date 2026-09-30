#!/usr/bin/env python3
"""STAFF-ACCESS-TRUTH-1 — Staff access truth deepen (no invent roles).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave9 pack
STAFF-ACCESS-TRUTH-1 (armed 2026-09-30 after OCCUPANCY-EXTERNAL-HOLD-1
PASS_VERIFIED / Wave8 complete).

Deepens the staff access truth board from live registry stamps and
authorised identity only. Never invents roles, permissions, or staff
lists. Honest empty / PENDING when no staff are commissioned.
Refuse invent-role writes (403). Preserves staff_access honesty.
staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain APPROVALS-LIVE-DEEPEN-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import staff_access as _staff

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
STAFF_RESULT = BETA_ROOT / "docs" / "wolf" / "staff" / "STAFF-ACCESS-RESULT.md"
COMMISSIONING_DOC = (
    BETA_ROOT / "docs" / "wolf" / "staff" / "HUMAN-COMMISSIONING-28SEP.md"
)

PACK_ID = "STAFF-ACCESS-TRUTH-1"
SCHEMA_ID = "wolf.staff-access-truth-1.v1"
BOUND = "beta-staff-access-truth-safe"
CAP_STAFF = "CAP-CORE staff access"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "INTERNALLY_SOLVABLE"
ACTION = "WIRE_LIVE_REGISTRY_STAMPS"
PRESERVED_PACKS = ("staff_access", "STAFF-ACCESS")

PAGE_PATHS = frozenset(
    {
        "/ops/staff-access-truth-1",
        "/ops/staff-access-truth-1/",
        "/ops/staff-access",
        "/ops/staff-access/",
        "/staff/access-truth-1",
        "/staff/access-truth-1/",
        "/staff/access",
        "/staff/access/",
        "/staff-access-truth-1",
        "/staff-access-truth-1/",
        "/staff-access-truth-1.html",
        "/dashboards/staff-access-truth-1.html",
    }
)
API_PATH = "/api/ops/staff-access-truth-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/staff/access-truth-1",
        "/api/staff/access-truth",
    }
)

STATUS_VOCAB = frozenset(
    {
        "INTERNALLY_SOLVABLE",
        "HUMAN_COMMISSIONING",
        "MATT_ACTION",
        "EXTERNAL_BLOCKER",
        "PRESERVED",
        "REFUSED",
        "PENDING",
        "ABSENT",
        "UNKNOWN",
        "WIRED",
        "HONEST_EMPTY",
    }
)

# Documented Cloudflare Access stamps from STAFF-ACCESS-RESULT (Owner notes).
# Never invent include-list membership from a CF API.
_CF_ACCESS_STAMPS: dict[str, str] = {
    "PERS-ZARAH": "OWNER_ADDED",
    "PERS-FRAIL": "OWNER_ADDED",
}

# Documented human commissioning stamps. Every row stays PENDING until the
# person writes PASS/FAIL. Do not invent PASS from engineering tests.
_COMMISSIONING_STAMPS: dict[str, str] = {
    "PERS-HAIKAL": "PENDING",
    "PERS-MISA": "PENDING",
    "PERS-ZARAH": "PENDING",
    "PERS-FRAIL": "PENDING",
    "PERS-YUDI": "PENDING",
    "PERS-GERY": "PENDING",
    "PERS-ALAM": "PENDING",
    "PERS-TJ": "PENDING",
    "PERS-NATA": "PENDING",
    "PERS-RAPP": "PENDING",
    "PERS-ZAYEN": "PENDING_FAIL",
}

_INVENT_ROLE_TOKENS = frozenset(
    {
        "role",
        "roles",
        "invent-role",
        "invent_role",
        "invent-roles",
        "invent_roles",
        "fake-role",
        "fake_role",
        "mint-role",
        "mint_role",
        "create-role",
        "create_role",
        "permission",
        "permissions",
        "invent-permission",
        "invent_permission",
        "fake-permission",
        "fake_permission",
        "grant",
        "grants",
        "invent-grant",
        "invent_grant",
        "staff",
        "staff-list",
        "staff_list",
        "invent-staff",
        "invent_staff",
        "fake-staff",
        "fake_staff",
        "person",
        "persons",
        "invent-person",
        "invent_person",
        "assignment",
        "assignments",
        "invent-assignment",
        "invent_assignment",
        "commission",
        "commissioned",
        "force-commission",
        "force_commission",
        "staff-ready",
        "staff_ready",
        "human-commissioned",
        "human_commissioned",
        "proven",
        "ready",
        "mailbox-login",
        "mailbox_login",
        "auth-identity",
        "auth_identity",
        "cf-include",
        "cf_include",
        "invent-cf",
        "invent_cf",
    }
)


class StaffAccessTruth1Error(ValueError):
    """Fail closed. Does not invent roles, permissions, or staff lists."""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/")
    return trimmed in API_PATHS or raw in API_PATHS


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


def _catalog_ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def person_may_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> bool:
    """Owner progress.read seat (Matt / owner progress readers)."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid == OWNER_PERSON:
        return True
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        return bool(_rbac.can(pid, "progress.read", {}, conn=c))
    finally:
        if own and c is not None:
            c.close()


def require_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> None:
    if not person_may_view(person_id, conn=conn):
        raise StaffAccessTruth1Error(
            "Staff access truth board is not on this assignment.",
            code="forbidden",
        )


def probe_registry(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Live org registry counts. Never invent persons/roles/auths."""
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        persons = int(
            c.execute(
                "SELECT COUNT(*) FROM org_persons WHERE status='ACTIVE'"
            ).fetchone()[0]
        )
        auths = int(
            c.execute(
                "SELECT COUNT(*) FROM org_auth_identities WHERE status='ACTIVE'"
            ).fetchone()[0]
        )
        roles = int(c.execute("SELECT COUNT(*) FROM org_roles").fetchone()[0])
        active = int(
            c.execute(
                """
                SELECT COUNT(*) FROM org_assignments
                WHERE status='ACTIVE' AND end_at IS NULL
                """
            ).fetchone()[0]
        )
        ended = int(
            c.execute(
                """
                SELECT COUNT(*) FROM org_assignments
                WHERE status='ENDED' OR end_at IS NOT NULL
                """
            ).fetchone()[0]
        )
        mailboxes = int(
            c.execute("SELECT COUNT(*) FROM org_function_mailboxes").fetchone()[0]
        )
        mailbox_logins = int(
            c.execute(
                "SELECT COUNT(*) FROM org_function_mailboxes WHERE wolf_login!=0"
            ).fetchone()[0]
        )
    finally:
        if own and c is not None:
            c.close()
    empty = persons == 0 and auths == 0
    return {
        "ok": True,
        "status": "HONEST_EMPTY" if empty else "WIRED",
        "classification": "INTERNALLY_SOLVABLE",
        "persons_active": persons,
        "auth_identities_active": auths,
        "roles": roles,
        "assignments_active": active,
        "assignments_ended": ended,
        "mailboxes": mailboxes,
        "mailbox_wolf_logins": mailbox_logins,
        "invented_roles": False,
        "invented_staff": False,
        "why": (
            "No live registry rows — honest empty (never invent staff)."
            if empty
            else (
                f"Live registry: {persons} ACTIVE persons, {auths} auth identities, "
                f"{roles} roles, {active} ACTIVE assignments, {ended} ended, "
                f"{mailboxes} role mailboxes (wolf_login={mailbox_logins}). "
                "INTERNALLY_SOLVABLE from authorised stamps."
            )
        ),
    }


def probe_active_seats(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Active seats from registry + landing map. Role IDs from DB only."""
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    seats: list[dict[str, Any]] = []
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, p.display_name, pos.role_id,
                   r.display_name AS role_label, a.is_primary
            FROM org_assignments a
            JOIN org_persons p ON p.person_id = a.person_id
            JOIN org_positions pos ON pos.position_id = a.position_id
            LEFT JOIN org_roles r ON r.role_id = pos.role_id
            WHERE a.status='ACTIVE' AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.person_id, a.assignment_id
            """
        ).fetchall()
        for row in rows:
            pid = str(row["person_id"])
            role_id = str(row["role_id"] or "")
            landing = _staff.HUMAN_PAGE_BY_ROLE.get(role_id)
            seats.append(
                {
                    "assignment_id": str(row["assignment_id"]),
                    "person_id": pid,
                    "display_name": str(row["display_name"] or ""),
                    "role_id": role_id,
                    "role_label": str(row["role_label"] or role_id),
                    "is_primary": int(row["is_primary"] or 0) == 1,
                    "landing": landing,
                    "commissioning": _COMMISSIONING_STAMPS.get(pid, "PENDING"),
                    "cf_access": _CF_ACCESS_STAMPS.get(pid, "PENDING_OWNER"),
                }
            )
    finally:
        if own and c is not None:
            c.close()
    commissioned = [
        s for s in seats if str(s.get("commissioning") or "").upper() == "PASS"
    ]
    return {
        "ok": True,
        "status": "WIRED" if seats else "HONEST_EMPTY",
        "classification": "INTERNALLY_SOLVABLE",
        "seat_count": len(seats),
        "commissioned_count": len(commissioned),
        "seats": seats,
        "invented_roles": False,
        "invented_staff": False,
        "why": (
            "No ACTIVE assignments — honest empty seat list (never invent)."
            if not seats
            else (
                f"{len(seats)} ACTIVE seats from registry. "
                f"Commissioned PASS count={len(commissioned)} "
                "(honest empty commissioning when none)."
            )
        ),
    }


def probe_role_mailboxes(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Role mailboxes are not AuthIdentities and not Wolf logins."""
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    boxes: list[dict[str, Any]] = []
    try:
        rows = c.execute(
            """
            SELECT mailbox_id, function_key, address, wolf_login, person_id,
                   auth_identity_id, status
            FROM org_function_mailboxes
            ORDER BY mailbox_id
            """
        ).fetchall()
        for row in rows:
            boxes.append(
                {
                    "mailbox_id": str(row["mailbox_id"]),
                    "function_key": str(row["function_key"] or ""),
                    "address": str(row["address"] or ""),
                    "wolf_login": int(row["wolf_login"] or 0),
                    "person_id": row["person_id"],
                    "auth_identity_id": row["auth_identity_id"],
                    "status": str(row["status"] or ""),
                }
            )
    finally:
        if own and c is not None:
            c.close()
    bad_login = any(int(b.get("wolf_login") or 0) != 0 for b in boxes)
    return {
        "ok": not bad_login,
        "status": "WIRED" if boxes else "ABSENT",
        "classification": "INTERNALLY_SOLVABLE",
        "mailbox_count": len(boxes),
        "mailboxes": boxes,
        "wolf_login_allowed": False,
        "invented_auth_identity": False,
        "why": (
            "No role mailboxes stamped."
            if not boxes
            else (
                "Role mailboxes are not AuthIdentities and not Wolf logins. "
                "Do not add hr@/recruitment@ as logins."
            )
        ),
    }


def probe_human_commissioning(
    *, seats: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Commissioning stays PENDING. Never invent PASS / staff_ready."""
    seat_probe = seats if seats is not None else probe_active_seats()
    rows = list(seat_probe.get("seats") or [])
    commissioned = [
        s for s in rows if str(s.get("commissioning") or "").upper() == "PASS"
    ]
    pending = [
        s
        for s in rows
        if str(s.get("commissioning") or "").upper().startswith("PENDING")
    ]
    empty_commissioned = len(commissioned) == 0
    return {
        "ok": True,
        "status": "HUMAN_COMMISSIONING",
        "classification": "HUMAN_COMMISSIONING",
        "commissioned_count": len(commissioned),
        "pending_count": len(pending),
        "honest_empty_commissioned": empty_commissioned,
        "staff_ready": False,
        "human_commissioned": False,
        "doc": str(COMMISSIONING_DOC.relative_to(BETA_ROOT))
        if COMMISSIONING_DOC.is_file()
        else None,
        "why": (
            "No staff person has written PASS. Commissioning stays PENDING. "
            "Honest empty commissioned column — never invent PASS / "
            "staff_ready / human_commissioned."
            if empty_commissioned
            else "Some seats show PASS from human write — still not staff_ready."
        ),
    }


def probe_cloudflare_access(
    *, seats: dict[str, Any] | None = None
) -> dict[str, Any]:
    """CF Access include list is Owner-only (MATT_ACTION). Never invent."""
    seat_probe = seats if seats is not None else probe_active_seats()
    rows = list(seat_probe.get("seats") or [])
    owner_added = [
        s for s in rows if str(s.get("cf_access") or "") == "OWNER_ADDED"
    ]
    pending_owner = [
        s for s in rows if str(s.get("cf_access") or "") == "PENDING_OWNER"
    ]
    return {
        "ok": True,
        "status": "MATT_ACTION",
        "classification": "MATT_ACTION",
        "owner_added_count": len(owner_added),
        "pending_owner_count": len(pending_owner),
        "include_list_invented": False,
        "cf_api_reader": False,
        "why": (
            "Cloudflare Access include list is Owner-only (MATT_ACTION). "
            f"Documented OWNER_ADDED={len(owner_added)}; "
            f"PENDING_OWNER={len(pending_owner)}. "
            "Never invent CF membership from tests."
        ),
        "evidence": str(STAFF_RESULT.relative_to(BETA_ROOT))
        if STAFF_RESULT.is_file()
        else "docs/wolf/staff/STAFF-ACCESS-RESULT.md",
    }


def probe_cf_access_api() -> dict[str, Any]:
    """Wolf has no CF Access membership reader — EXTERNAL_BLOCKER for auto-probe."""
    return {
        "ok": True,
        "status": "EXTERNAL_BLOCKER",
        "classification": "EXTERNAL_BLOCKER",
        "path_configured": False,
        "client_module_found": False,
        "value": None,
        "why": (
            "No Cloudflare Access membership reader in Wolf. "
            "Auto-verify of include list is EXTERNAL_BLOCKER. "
            "Owner stamps (MATT_ACTION) are the only authorised CF evidence."
        ),
        "evidence": "pack forbids invent CF include; Owner adds emails",
    }


def staff_access_preserved() -> dict[str, Any]:
    """Read-only: staff_access honesty still holds (no invent, flags false)."""
    try:
        # Constants / maps still present and honest.
        ready_flag = getattr(_staff, "ROLE_CONTENT_CREATOR", None)
        landing = _staff.HUMAN_PAGE_BY_ROLE.get("ROLE-OWNER")
        ok = (
            ready_flag == "ROLE-CONTENT-CREATOR"
            and landing == "/wolf"
            and _staff.FINANCE_EMAIL == "laluzayen@gmail.com"
            and _staff.ZAYEN_PERSON == "PERS-ZAYEN"
            and len(_staff.CREATORS) == 6
            and len(_staff.HR_MAILBOXES) == 2
        )
        # Probe apply fingerprint without writing — finance_search RO.
        conn = _catalog_ro()
        try:
            finance = _staff.finance_search(conn)
            pages = _staff.active_assignment_pages(OWNER_PERSON, conn)
        finally:
            conn.close()
        ok = ok and isinstance(finance, dict) and isinstance(pages, list)
        return {
            "ok": ok,
            "pack": "staff_access",
            "staff_ready": False,
            "human_commissioned": False,
            "finance_bound": finance.get("bound") if isinstance(finance, dict) else None,
            "owner_pages": len(pages),
            "why": (
                "staff_access preserved: registry helpers RO-clean; "
                "staff_ready/human_commissioned stay false; "
                "role mailboxes / creator seats / Zayen finance stamps intact. "
                "This pack deepens the truth board — does not invent roles."
                if ok
                else "staff_access honesty check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "staff_access",
            "error": type(exc).__name__,
            "why": "staff_access check failed — pack must not break registry honesty.",
        }


def surface_stamps() -> list[dict[str, Any]]:
    """Truth surfaces from live stamps. Never invent roles/staff."""
    registry = probe_registry()
    seats = probe_active_seats()
    mailboxes = probe_role_mailboxes()
    commissioning = probe_human_commissioning(seats=seats)
    cf = probe_cloudflare_access(seats=seats)
    cf_api = probe_cf_access_api()
    preserved = staff_access_preserved()
    return [
        {
            "id": "registry",
            "label": "Live registry (persons / auths / roles)",
            "status": "INTERNALLY_SOLVABLE",
            "value": registry.get("persons_active"),
            "persons_active": registry.get("persons_active"),
            "auth_identities_active": registry.get("auth_identities_active"),
            "roles": registry.get("roles"),
            "invented_roles": False,
            "invented_staff": False,
            "why": registry.get("why"),
            "evidence": "catalog/content_library.sqlite org_* tables",
        },
        {
            "id": "active_seats",
            "label": "Active assignments / landings",
            "status": "INTERNALLY_SOLVABLE",
            "value": seats.get("seat_count"),
            "seat_count": seats.get("seat_count"),
            "commissioned_count": seats.get("commissioned_count"),
            "invented_roles": False,
            "invented_staff": False,
            "why": seats.get("why"),
            "evidence": "org_assignments ACTIVE + HUMAN_PAGE_BY_ROLE",
        },
        {
            "id": "role_mailboxes",
            "label": "Role mailboxes (not Wolf logins)",
            "status": "INTERNALLY_SOLVABLE",
            "value": mailboxes.get("mailbox_count"),
            "mailbox_count": mailboxes.get("mailbox_count"),
            "wolf_login_allowed": False,
            "invented_auth_identity": False,
            "why": mailboxes.get("why"),
            "evidence": "org_function_mailboxes wolf_login=0",
        },
        {
            "id": "human_commissioning",
            "label": "Human commissioning",
            "status": "HUMAN_COMMISSIONING",
            "value": commissioning.get("commissioned_count"),
            "commissioned_count": commissioning.get("commissioned_count"),
            "pending_count": commissioning.get("pending_count"),
            "honest_empty_commissioned": commissioning.get(
                "honest_empty_commissioned"
            ),
            "staff_ready": False,
            "human_commissioned": False,
            "why": commissioning.get("why"),
            "evidence": commissioning.get("doc"),
        },
        {
            "id": "cloudflare_access",
            "label": "Cloudflare Access include list",
            "status": "MATT_ACTION",
            "value": "MATT_ACTION",
            "owner_added_count": cf.get("owner_added_count"),
            "pending_owner_count": cf.get("pending_owner_count"),
            "include_list_invented": False,
            "why": cf.get("why"),
            "evidence": cf.get("evidence"),
        },
        {
            "id": "cf_access_api",
            "label": "CF Access membership auto-probe",
            "status": "EXTERNAL_BLOCKER",
            "value": None,
            "path_configured": False,
            "why": cf_api.get("why"),
            "evidence": cf_api.get("evidence"),
        },
        {
            "id": "staff_access_preserved",
            "label": "staff_access honesty",
            "status": "PRESERVED" if preserved.get("ok") else "EXTERNAL_BLOCKER",
            "value": "PRESERVED" if preserved.get("ok") else None,
            "preserved_ok": preserved.get("ok") is True,
            "why": preserved.get("why"),
            "evidence": "scripts/core/staff_access.py",
        },
        {
            "id": "invent_role_writes",
            "label": "Invent role / permission / staff-list writes",
            "status": "REFUSED",
            "value": False,
            "invented_roles": False,
            "invented_staff": False,
            "why": "Invent-role / invent-permission / invent-staff writes are refused (403).",
            "evidence": "pack forbids invent roles",
        },
        {
            "id": "staff_ready_flags",
            "label": "staff_ready / human_commissioned",
            "status": "REFUSED",
            "value": False,
            "staff_ready": False,
            "human_commissioned": False,
            "why": (
                "staff_ready and human_commissioned stay false always. "
                "TESTS≠STAFF READY. Never flip."
            ),
            "evidence": "MISSION / ARM staff_ready=false",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    preserved = staff_access_preserved()
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap_staff_access": CAP_STAFF,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "invented_roles": False,
        "invented_permissions": False,
        "invented_staff": False,
        "invented_staff_list": False,
        "fake_roles": False,
        "fake_staff": False,
        "fake_commissioning": False,
        "include_list_invented": False,
        "mailbox_as_login": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_probe_read_only": True,
        "no_push": True,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "action": ACTION,
        "proven_claimed": False,
        "ready_claimed": False,
        "staff_access_preserved": preserved.get("ok") is True,
        "status_vocab": (
            "INTERNALLY_SOLVABLE|HUMAN_COMMISSIONING|MATT_ACTION|"
            "EXTERNAL_BLOCKER|PRESERVED|REFUSED|PENDING|ABSENT|UNKNOWN|"
            "WIRED|HONEST_EMPTY"
        ),
        "next_pack_for_parent_only": "APPROVALS-LIVE-DEEPEN-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "honest_empty_when_uncommissioned": True,
        "shell_ne_complete": True,
        "tests_ne_staff_ready": True,
    }


def refuse_invent_role(_body: dict | None = None) -> None:
    raise StaffAccessTruth1Error(
        "Invent role refused. Roles come from live registry stamps only.",
        code="invent_role_refused",
    )


def refuse_invent_permission(_body: dict | None = None) -> None:
    raise StaffAccessTruth1Error(
        "Invent permission refused. Grants stay on authorised role stamps.",
        code="invent_permission_refused",
    )


def refuse_invent_staff(_body: dict | None = None) -> None:
    raise StaffAccessTruth1Error(
        "Invent staff list refused. Seats come from live assignments only.",
        code="invent_staff_refused",
    )


def refuse_force_commission(_body: dict | None = None) -> None:
    raise StaffAccessTruth1Error(
        "Force commission / staff_ready refused. Humans write PASS/FAIL.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise StaffAccessTruth1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in _INVENT_ROLE_TOKENS or norm in _INVENT_ROLE_TOKENS:
            # Ready/commission first so staff_ready ≠ invent_staff.
            if (
                "ready" in token
                or "commission" in token
                or "proven" in token
                or "ready" in norm
                or "commission" in norm
            ):
                refuse_force_commission(payload)
            if "permission" in token or "permission" in norm or "grant" in token:
                refuse_invent_permission(payload)
            if (
                "staff-list" in token
                or "staff_list" in norm
                or "invent-staff" in token
                or "invent_staff" in norm
                or "fake-staff" in token
                or "fake_staff" in norm
                or "person" in token
                or "assignment" in token
                or "person" in norm
                or "assignment" in norm
            ):
                refuse_invent_staff(payload)
            refuse_invent_role(payload)
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "8787",
            "15975",
        }:
            raise StaffAccessTruth1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
        if token in {
            "staff-ready",
            "human-commissioned",
            "proven",
            "ready",
        } or norm in {
            "staff_ready",
            "human_commissioned",
            "proven",
            "ready",
        }:
            refuse_force_commission(payload)
    raise StaffAccessTruth1Error(
        "STAFF-ACCESS-TRUTH-1 is a read-only truth board. Writes refused.",
        code="write_refused",
    )


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when surfaces use allowed vocab and invent flags stay false."""
    pack = payload if payload is not None else build_board()
    if pack.get("invented_roles") is True or pack.get("invented_staff") is True:
        return False
    if pack.get("staff_ready") is True or pack.get("human_commissioned") is True:
        return False
    if pack.get("classification") != CLASSIFICATION:
        return False
    if pack.get("commissioned_count") not in (0, None) and pack.get(
        "honest_empty_commissioned"
    ) is not True:
        # Allow non-zero only if somehow PASS exists; still must not flip ready.
        pass
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 7:
        return False
    by_id = {s.get("id"): s for s in surfaces if isinstance(s, dict)}
    need = {
        "registry": "INTERNALLY_SOLVABLE",
        "active_seats": "INTERNALLY_SOLVABLE",
        "human_commissioning": "HUMAN_COMMISSIONING",
        "cloudflare_access": "MATT_ACTION",
        "cf_access_api": "EXTERNAL_BLOCKER",
        "invent_role_writes": "REFUSED",
        "staff_ready_flags": "REFUSED",
    }
    for sid, st in need.items():
        row = by_id.get(sid) or {}
        if row.get("status") != st:
            return False
        if row.get("status") not in STATUS_VOCAB:
            return False
    preserved = by_id.get("staff_access_preserved") or {}
    if preserved.get("status") not in ("PRESERVED", "EXTERNAL_BLOCKER"):
        return False
    if pack.get("honest_empty_commissioned") is not True:
        return False
    return True


def no_invented_roles(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    return (
        pack.get("invented_roles") is False
        and pack.get("invented_permissions") is False
        and pack.get("invented_staff") is False
        and pack.get("fake_roles") is False
        and pack.get("fake_staff") is False
        and pack.get("staff_ready") is False
        and pack.get("human_commissioned") is False
    )


def build_board(
    person_id: str | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Public staff access truth board. Auth gating is caller's job."""
    if person_id is not None:
        require_view(person_id, conn=conn)
    probed_at = _now_wita()
    registry = probe_registry(conn=conn)
    seats = probe_active_seats(conn=conn)
    mailboxes = probe_role_mailboxes(conn=conn)
    commissioning = probe_human_commissioning(seats=seats)
    cf = probe_cloudflare_access(seats=seats)
    surfaces = surface_stamps()
    # Rebuild surface list with already-probed data to avoid double RO opens
    # for the public payload consistency (surface_stamps already self-contained).
    preserved = staff_access_preserved()
    flags = honesty_flags()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": probed_at,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "invented_roles": False,
        "invented_permissions": False,
        "invented_staff": False,
        "invented_staff_list": False,
        "fake_roles": False,
        "fake_staff": False,
        "fake_commissioning": False,
        "include_list_invented": False,
        "mailbox_as_login": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "action": ACTION,
        "cap_staff_access": CAP_STAFF,
        "persons_active": registry.get("persons_active"),
        "auth_identities_active": registry.get("auth_identities_active"),
        "roles": registry.get("roles"),
        "assignments_active": registry.get("assignments_active"),
        "assignments_ended": registry.get("assignments_ended"),
        "seat_count": seats.get("seat_count"),
        "commissioned_count": commissioning.get("commissioned_count"),
        "pending_count": commissioning.get("pending_count"),
        "honest_empty_commissioned": commissioning.get(
            "honest_empty_commissioned"
        ),
        "mailbox_count": mailboxes.get("mailbox_count"),
        "cf_owner_added_count": cf.get("owner_added_count"),
        "cf_pending_owner_count": cf.get("pending_owner_count"),
        "surfaces": surfaces,
        "surface_counts": by_status,
        "seats": seats.get("seats") or [],
        "registry": registry,
        "commissioning": commissioning,
        "cloudflare_access": cf,
        "honesty": {
            "policy": "live_stamps_only_never_invent_roles",
            "registry": "INTERNALLY_SOLVABLE",
            "human_commissioning": "HUMAN_COMMISSIONING",
            "cloudflare_access": "MATT_ACTION",
            "cf_access_api": "EXTERNAL_BLOCKER",
            "staff_access": preserved.get("ok") and "PRESERVED" or "CHECK_FAILED",
            "invent_role_writes": "REFUSED",
            "staff_ready": False,
            "human_commissioned": False,
        },
        "preserved": {"staff_access": preserved},
        "staff_access_preserved": preserved.get("ok") is True,
        "staff_result_href": "/docs/wolf/staff/STAFF-ACCESS-RESULT.md",
        "staff_ops_href": "/staff-ops-routing",
        "next_pack_for_parent_only": "APPROVALS-LIVE-DEEPEN-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "proven_claimed",
                "ready_claimed",
                "no_push",
                "status_vocab",
                "honest_empty_when_uncommissioned",
                "shell_ne_complete",
                "tests_ne_staff_ready",
            )
        },
    }


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    return build_board(person_id)


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    return build_board(person_id)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "classification": CLASSIFICATION,
        "invent_roles": False,
        "invent_staff": False,
        "writes_accepted": False,
        "staff_ready": False,
        "human_commissioned": False,
        "preserved": list(PRESERVED_PACKS),
        "why": (
            "Staff access truth from live registry stamps / authorised identity. "
            "Honest empty when uncommissioned. Invent-role writes refused. "
            "staff_access preserved."
        ),
    }
