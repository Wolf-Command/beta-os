#!/usr/bin/env python3
"""Staff daily home — one role-based page over Wolf Core.

Decision served: 2026-09-24 People Are Not Roles owner lock, extending the
2026-09-22 Empire Home staff landing. Not a new task database.

Person is greeting and attribution only. Role picks the experience.
Assignment and Scope pick what is visible. Reads core_work_items,
core_approval_requests, core_governance_exceptions, and core_evidence_records.
No notification table is invented.
"""
from __future__ import annotations

from typing import Any

from core import identity
from core import work_items as wi

BOUND = "beta-staff-home"
SCHEMA_ID = "wolf.staff-home.v1"

_MONEY = frozenset({"payment.execute", "payment.approve"})
_BANK = frozenset({"vendor.bank.change"})
_GOVERN = frozenset({"governance.exception.authorise", "governance.exception.revoke"})

_BRAND_DESK = {
    "BZG-UMA": ("Open today's Uma Blu work", "/bzg/uma-blu"),
}

_GENERIC_DESK = {
    "ROLE-CONTENT-MGMT": ("Open content", "/content-2.0"),
    "ROLE-CONTENT-CREW": ("Open content", "/content-2.0"),
    "ROLE-CONTENT": ("Open content", "/content-2.0"),
    "ROLE-AMG-GM": ("Open the hotel desk", "/amg-ops-pack"),
    "ROLE-AMG-OPS": ("Open the hotel desk", "/amg-ops-pack"),
    "ROLE-GGV-LEAD": ("Open the pipeline", "/ggv-ops-pack"),
}


class StaffHomeError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_code(path: str) -> str | None:
    refused = {
        "/api/staff/home/proven": "proven",
        "/api/staff/home/ready": "ready",
        "/api/staff/home/money": "money",
        "/api/staff/home/payment": "money",
        "/api/staff/home/bank": "money",
        "/api/staff/home/production": "production",
    }
    return refused.get(path)


def refuse_path(path: str) -> None:
    code = refuse_code(path) or "writes_refused"
    raise StaffHomeError(
        "This page does not move money, change a bank, or mark work proven.",
        code=f"{code}_refused",
    )


def _demo(*parts: Any) -> bool:
    blob = " ".join(str(p or "") for p in parts).upper()
    return "DEMO" in blob or "FIXTURE" in blob


def _owner_role(row: dict[str, Any]) -> bool:
    label = str(row.get("role_label") or "").lower()
    kind = str(row.get("role_type") or "").upper()
    return kind == "EXECUTIVE" and "owner" in label


def _finance_role(row: dict[str, Any]) -> bool:
    blob = f"{row.get('role_id') or ''} {row.get('role_label') or ''}".lower()
    return "accountant" in blob or "finance" in blob


def _creative_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    label = str(row.get("role_label") or "").strip().lower()
    return label == "creative director" or role.endswith("CREATIVE-DIRECTOR")


def _bzg_lead_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    label = str(row.get("role_label") or "").lower()
    return role.endswith("FB-OPS-LEAD") or ("f&b" in label and "lead" in label)


def _assignments(conn, person_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT a.assignment_id, a.is_primary, a.position_id,
               p.role_id, p.entity_id, p.position_label,
               r.display_name AS role_label, r.role_type
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_roles r ON r.role_id = p.role_id
        WHERE a.person_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        ORDER BY a.is_primary DESC, a.assignment_id
        """,
        (person_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _scopes_for(conn, assignment_ids: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for aid in assignment_ids:
        rows = conn.execute(
            """
            SELECT s.scope_id, sc.display_name
            FROM org_assignment_scopes s
            LEFT JOIN org_scopes sc ON sc.scope_id = s.scope_id
            WHERE s.assignment_id = ?
              AND s.status = 'ACTIVE'
              AND s.end_at IS NULL
            ORDER BY s.scope_id
            """,
            (aid,),
        ).fetchall()
        for row in rows:
            sid = str(row["scope_id"] or "")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            out.append({"id": sid, "label": str(row["display_name"] or sid)})
    return out


def _brands(conn, scope_ids: list[str]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for sid in scope_ids:
        try:
            rows = conn.execute(
                """
                SELECT t.target_id, b.display_name
                FROM org_scope_targets t
                LEFT JOIN org_brands b ON b.brand_id = t.target_id
                WHERE t.scope_id = ? AND t.target_type = 'brand'
                ORDER BY t.target_id
                """,
                (sid,),
            ).fetchall()
        except Exception:
            rows = []
        for row in rows:
            bid = str(row["target_id"] or "")
            if not bid or bid in seen:
                continue
            seen.add(bid)
            name = str(row["display_name"] or "").strip() or bid
            found.append({"id": bid, "name": name})
    return found


def _permission_codes(conn, person_id: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT perm.code
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_role_permissions rp
          ON rp.role_id = p.role_id AND rp.effect = 'ALLOW'
        JOIN org_permissions perm ON perm.permission_id = rp.permission_id
        WHERE a.person_id = ?
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        """,
        (person_id,),
    ).fetchall()
    return {str(r["code"]) for r in rows if r["code"]}


def _pick(rows: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    for row in rows:
        if _owner_role(row):
            return "owner_pulse", row
    primary = rows[0]
    if _finance_role(primary):
        return "finance", primary
    if _creative_role(primary):
        return "creative_director", primary
    if _bzg_lead_role(primary):
        return "bzg_fb_ops", primary
    return "staff", primary


def _section(key: str, title: str, items: list[dict[str, str]], empty_message: str) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "empty": not items,
        "empty_message": None if items else empty_message,
        "items": items,
    }


def _item(item_id: str, title: str) -> dict[str, str]:
    return {"id": item_id, "title": title}


def _placeholders(n: int) -> str:
    return ",".join("?" for _ in range(n))


def _work_rows(conn, entities: set[str], statuses: tuple[str, ...], owner: str | None) -> list[dict[str, Any]]:
    if not entities or not statuses:
        return []
    sql = f"""
        SELECT work_item_id, title, status, owner_person_id, owning_entity_id,
               priority, due_at, completed_at, verified_at
        FROM core_work_items
        WHERE owning_entity_id IN ({_placeholders(len(entities))})
          AND status IN ({_placeholders(len(statuses))})
    """
    params: list[Any] = [*sorted(entities), *statuses]
    if owner:
        sql += " AND owner_person_id = ?"
        params.append(owner)
    sql += " ORDER BY priority ASC, due_at IS NULL, due_at ASC, updated_at DESC LIMIT 40"
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []


def _approval_rows(conn, entities: set[str]) -> list[dict[str, Any]]:
    if not entities:
        return []
    sql = f"""
        SELECT approval_request_id, title, status, request_type, material_amount,
               currency, requested_by_person_id, owning_entity_id,
               required_permission_code
        FROM core_approval_requests
        WHERE owning_entity_id IN ({_placeholders(len(entities))})
          AND status = 'PENDING'
        ORDER BY requested_at DESC
        LIMIT 40
    """
    try:
        return [dict(r) for r in conn.execute(sql, sorted(entities)).fetchall()]
    except Exception:
        return []


def _exception_rows(conn, entities: set[str]) -> list[dict[str, Any]]:
    if not entities:
        return []
    sql = f"""
        SELECT exception_id, reason, status, control_type, entity_id,
               requested_by_person_id
        FROM core_governance_exceptions
        WHERE entity_id IN ({_placeholders(len(entities))})
          AND status IN ('REQUESTED', 'AUTHORISED')
        ORDER BY created_at DESC
        LIMIT 40
    """
    try:
        return [dict(r) for r in conn.execute(sql, sorted(entities)).fetchall()]
    except Exception:
        return []


def _evidence_rows(conn, entities: set[str]) -> list[dict[str, Any]]:
    if not entities:
        return []
    sql = f"""
        SELECT evidence_id, evidence_type, verification_status,
               submitted_by_person_id, entity_id
        FROM core_evidence_records
        WHERE entity_id IN ({_placeholders(len(entities))})
          AND status = 'ACTIVE'
          AND verification_status = 'VERIFIED'
        ORDER BY verified_at DESC, submitted_at DESC
        LIMIT 20
    """
    try:
        return [dict(r) for r in conn.execute(sql, sorted(entities)).fetchall()]
    except Exception:
        return []


def _clean_work(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r for r in rows
        if not _demo(r.get("work_item_id"), r.get("title"), r.get("owner_person_id"))
    ]


def _desk(experience: str, role: dict[str, Any], brands: list[dict[str, str]]) -> list[dict[str, str]]:
    if experience == "owner_pulse":
        return []
    if experience == "creative_director":
        return [{"label": "Open the content library", "href": "/content-2.0"}]
    if experience == "finance":
        return [{"label": "Open finance notes", "href": "/ggv/finance"}]
    if experience == "bzg_fb_ops":
        links = []
        for brand in brands:
            pair = _BRAND_DESK.get(brand["id"])
            if pair:
                links.append({"label": pair[0], "href": pair[1]})
        return links
    pair = _GENERIC_DESK.get(str(role.get("role_id") or ""))
    if pair:
        return [{"label": pair[0], "href": pair[1]}]
    return []


def _covers(experience: str, brands: list[dict[str, str]], scopes: list[dict[str, str]]) -> list[str]:
    if experience == "creative_director":
        return ["Content library"]
    if experience == "finance":
        labels = [s["label"] for s in scopes if "finance" in s["label"].lower()]
        return labels or ["Finance notes"]
    if experience == "bzg_fb_ops":
        return [b["name"] for b in brands] or ["No venue is on this assignment yet"]
    if experience == "owner_pulse":
        return []
    return []


def _boundary(experience: str) -> str | None:
    if experience == "finance":
        return (
            "You can read and review finance notes. "
            "You cannot pay, change a bank account, or change a governance rule."
        )
    if experience == "bzg_fb_ops":
        return (
            "You run food and beverage operations for the venues on your assignment. "
            "You cannot pay, change a bank account, or authorise a governance exception."
        )
    return None


def _founder(experience: str) -> dict[str, str]:
    if experience == "owner_pulse":
        return {
            "daily_picture": "RETAIN",
            "authority": "RETAIN",
            "empty_records": "RETAIN",
        }
    if experience == "finance":
        return {
            "note_review": "AUGMENT",
            "payment": "RETAIN",
            "bank_change": "RETAIN",
            "empty_records": "RETAIN",
        }
    return {
        "daily_list": "ELIMINATE",
        "payment": "RETAIN",
        "bank_change": "RETAIN",
        "governance_authority": "RETAIN",
        "empty_records": "RETAIN",
    }


def _staff_sections(
    conn,
    person_id: str,
    entities: set[str],
    codes: set[str],
) -> list[dict[str, Any]]:
    mine = _clean_work(_work_rows(conn, entities, ("OPEN", "IN_PROGRESS", "BLOCKED"), person_id))
    today = [_item(r["work_item_id"], r["title"]) for r in mine if r["status"] in {"OPEN", "IN_PROGRESS"}]
    blocked = [_item(r["work_item_id"], r["title"]) for r in mine if r["status"] == "BLOCKED"]
    done_rows = _clean_work(
        _work_rows(conn, entities, ("COMPLETED", "VERIFIED"), person_id)
    )
    done = [_item(r["work_item_id"], r["title"]) for r in done_rows[:8]]
    for ev in _evidence_rows(conn, entities):
        if str(ev.get("submitted_by_person_id") or "") != person_id:
            continue
        if _demo(ev.get("evidence_id"), ev.get("evidence_type"), person_id):
            continue
        done.append(_item(str(ev["evidence_id"]), f"Evidence recorded: {ev.get('evidence_type') or 'record'}"))
        if len(done) >= 8:
            break

    attention = list(blocked)
    waiting = []
    for ap in _approval_rows(conn, entities):
        if _demo(ap.get("approval_request_id"), ap.get("title"), ap.get("requested_by_person_id")):
            continue
        title = str(ap.get("title") or "Request")
        if str(ap.get("requested_by_person_id") or "") == person_id:
            waiting.append(_item(str(ap["approval_request_id"]), title))
            continue
        needed = str(ap.get("required_permission_code") or "")
        if "approval.decide" in codes and (not needed or needed in codes):
            attention.append(_item(str(ap["approval_request_id"]), title))

    return [
        _section("today", "What do I need to do today?", today[:12], "Nothing is assigned to you for today."),
        _section("attention", "What needs my attention?", attention[:12], "Nothing needs your attention."),
        _section("waiting", "What am I waiting for?", waiting[:12], "You are not waiting on anyone."),
        _section("completed", "What did I recently complete?", done[:8], "Nothing completed recently."),
    ]


def _owner_sections(conn, entities: set[str], codes: set[str], person_id: str) -> list[dict[str, Any]]:
    open_rows = _clean_work(_work_rows(conn, entities, ("OPEN", "IN_PROGRESS"), None))
    blocked_rows = _clean_work(_work_rows(conn, entities, ("BLOCKED",), None))
    done_rows = _clean_work(_work_rows(conn, entities, ("COMPLETED", "VERIFIED"), None))
    happening = [_item(r["work_item_id"], r["title"]) for r in open_rows[:12]]
    blocked = [_item(r["work_item_id"], r["title"]) for r in blocked_rows[:12]]
    improving = [_item(r["work_item_id"], r["title"]) for r in done_rows[:8]]
    wrong = []
    authority = []
    money = []
    for ex in _exception_rows(conn, entities):
        if _demo(ex.get("exception_id"), ex.get("reason"), ex.get("requested_by_person_id")):
            continue
        title = str(ex.get("reason") or "Exception")
        wrong.append(_item(str(ex["exception_id"]), title))
        if str(ex.get("status")) == "REQUESTED" and codes & _GOVERN:
            authority.append(_item(str(ex["exception_id"]), title))
        control = str(ex.get("control_type") or "").lower()
        if any(word in control for word in ("pay", "bank", "finance", "money")):
            money.append(_item(str(ex["exception_id"]), title))
    for ap in _approval_rows(conn, entities):
        if _demo(ap.get("approval_request_id"), ap.get("title"), ap.get("requested_by_person_id")):
            continue
        title = str(ap.get("title") or "Request")
        aid = str(ap["approval_request_id"])
        if str(ap.get("request_type") or "") == "SPEND" or str(ap.get("material_amount") or "").strip():
            amount = str(ap.get("material_amount") or "").strip()
            label = title if not amount else f"{title} ({amount} {ap.get('currency') or ''})".strip()
            money.append(_item(aid, label))
        needed = str(ap.get("required_permission_code") or "")
        requester = str(ap.get("requested_by_person_id") or "")
        if requester != person_id and "approval.decide" in codes and (not needed or needed in codes):
            authority.append(_item(aid, title))
        if requester == person_id:
            wrong.append(_item(aid, title))
    for ev in _evidence_rows(conn, entities):
        if _demo(ev.get("evidence_id"), ev.get("evidence_type"), ev.get("submitted_by_person_id")):
            continue
        improving.append(_item(str(ev["evidence_id"]), f"Evidence checked: {ev.get('evidence_type') or 'record'}"))
        if len(improving) >= 8:
            break
    return [
        _section("happening", "What's happening", happening, "Nothing open is on record."),
        _section("wrong", "What's wrong", wrong[:12], "Nothing is marked wrong."),
        _section("authority", "What needs your decision", authority[:12], "Nothing is waiting for your decision."),
        _section("blocked", "What's blocked", blocked, "Nothing is blocked."),
        _section("improving", "What improved", improving[:8], "Nothing new has been completed."),
        _section(
            "money",
            "Money or control at risk",
            money[:12],
            "Nothing on record is flagged as money or control at risk.",
        ),
    ]


def build_home(person_id: str | None, *, conn=None) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise StaffHomeError("Sign in required.", code="forbidden")
    own = conn is None
    c = conn or wi.db_connect()
    try:
        person = identity.get_person(pid, conn=c)
        if not person or str(person.get("status") or "").upper() != "ACTIVE":
            raise StaffHomeError("This person is not active.", code="forbidden")
        rows = _assignments(c, pid)
        if not rows:
            raise StaffHomeError("No active assignment.", code="forbidden")
        experience, role = _pick(rows)
        scope_rows = _scopes_for(c, [str(r["assignment_id"]) for r in rows])
        brands = _brands(c, [s["id"] for s in scope_rows])
        codes = _permission_codes(c, pid)
        entities = wi.visible_entity_ids_for_person(pid, conn=c)
        if experience == "owner_pulse":
            sections = _owner_sections(c, entities, codes, pid)
        else:
            sections = _staff_sections(c, pid, entities, codes)
        display = str(person.get("display_name") or "").strip() or "there"
        return {
            "ok": True,
            "bound": BOUND,
            "schema": SCHEMA_ID,
            "experience": experience,
            "greeting": f"Hello, {display}",
            "person_id": pid,
            "display_name": display,
            "role": {
                "id": role.get("role_id"),
                "label": role.get("role_label") or role.get("position_label") or "Your role",
            },
            "scopes": [s["id"] for s in scope_rows],
            "covers": _covers(experience, brands, scope_rows),
            "desk": _desk(experience, role, brands),
            "boundary": _boundary(experience),
            "notifications": {
                "empty": True,
                "empty_message": "No notifications.",
                "items": [],
            },
            "authority": {
                "move_money": bool(codes & _MONEY),
                "change_bank": bool(codes & _BANK),
                "authorise_governance": bool(codes & _GOVERN),
                "finance_read": "finance.nota.read" in codes,
                "finance_review": "finance.nota.review" in codes,
                "finance_edit": "finance.nota.create" in codes or "finance.nota.edit" in codes,
                "unrestricted": False,
            },
            "sections": sections,
            "founder_dependency": _founder(experience),
            "staff_ready": False,
            "human_commissioned": False,
            "proven": False,
            "money_movement": False,
        }
    finally:
        if own:
            c.close()


def fingerprint(home: dict[str, Any]) -> dict[str, Any]:
    """Experience without the person's name, so a replacement can match."""
    return {
        "experience": home.get("experience"),
        "role_id": (home.get("role") or {}).get("id"),
        "role_label": (home.get("role") or {}).get("label"),
        "scopes": sorted(home.get("scopes") or []),
        "covers": list(home.get("covers") or []),
        "desk": list(home.get("desk") or []),
        "boundary": home.get("boundary"),
        "authority": dict(home.get("authority") or {}),
        "notifications": (home.get("notifications") or {}).get("empty_message"),
        "sections": [
            {
                "key": s.get("key"),
                "title": s.get("title"),
                "empty": s.get("empty"),
                "empty_message": s.get("empty_message"),
                "titles": [i.get("title") for i in (s.get("items") or [])],
            }
            for s in (home.get("sections") or [])
        ],
    }
