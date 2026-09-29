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

import json
from datetime import datetime
from typing import Any

from core import identity
from core import work_items as wi
from core.nas_library import BRAND_SCOPES

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
    "ROLE-CONTENT-CREATOR": ("Open content", "/content-2.0"),
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


def _atrium_finance_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    return role in {
        "ROLE-AMG-FINANCE-OFFICER",
        "ROLE-AMG-FINANCIAL-CONTROLLER",
    }


def _finance_role(row: dict[str, Any]) -> bool:
    blob = f"{row.get('role_id') or ''} {row.get('role_label') or ''}".lower()
    return "accountant" in blob or "finance" in blob


def _content_creator_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    label = str(row.get("role_label") or "").strip().lower()
    return role == "ROLE-CONTENT-CREATOR" or label == "content creator"


def _creative_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    label = str(row.get("role_label") or "").strip().lower()
    return label == "creative director" or role.endswith("CREATIVE-DIRECTOR")


def _bzg_lead_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    label = str(row.get("role_label") or "").lower()
    return role.endswith("FB-OPS-LEAD") or ("f&b" in label and "lead" in label)


def _closer_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    label = str(row.get("role_label") or "").strip().lower()
    return role.endswith("CLOSER") or "closing operator" in label or label == "closer"


def _manager_role(row: dict[str, Any]) -> bool:
    role = str(row.get("role_id") or "")
    label = str(row.get("role_label") or "").strip().lower()
    return role.endswith("-GM") or label == "general manager"


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
    if _atrium_finance_role(primary):
        return "atrium_finance", primary
    if _finance_role(primary):
        return "finance", primary
    if _creative_role(primary):
        return "creative_director", primary
    if _content_creator_role(primary):
        return "content_creator", primary
    if _bzg_lead_role(primary):
        return "bzg_fb_ops", primary
    if _closer_role(primary):
        return "closer", primary
    if _manager_role(primary):
        return "manager", primary
    return "staff", primary


def _section(key: str, title: str, items: list[dict[str, str]], empty_message: str) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "empty": not items,
        "empty_message": None if items else empty_message,
        "items": items,
    }


def _item(item_id: str, title: str, *, href: str | None = None, status: str | None = None) -> dict[str, str]:
    row = {"id": item_id, "title": title}
    if href:
        row["href"] = href
    if status:
        row["status"] = status
    return row


def _work_href(work_item_id: str) -> str:
    return f"/my-work/item/{work_item_id}"


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
        inherited: list[str] = []
        try:
            from core import work_loop as _loop

            inherited = _loop.inherited_work_item_ids(conn, owner)
        except Exception:
            inherited = []
        if inherited:
            sql += f" AND (owner_person_id = ? OR work_item_id IN ({_placeholders(len(inherited))}))"
            params.append(owner)
            params.extend(inherited)
        else:
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
               required_permission_code, linked_work_item_id
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
          AND IFNULL(submitted_by_person_id, '') NOT LIKE 'PERS-P4-%'
          AND IFNULL(source_type, '') != 'TEST'
          AND evidence_id NOT LIKE '%DEMO%'
          AND IFNULL(source_reference, '') NOT LIKE '%fixture%'
          AND IFNULL(source_reference, '') NOT LIKE '%P4-TEST%'
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
    if experience in {"creative_director", "content_creator"}:
        return [{"label": "Open the content library", "href": "/content-2.0"}]
    if experience == "atrium_finance":
        return [{"label": "Open Atrium Finance", "href": "/amg/finance"}]
    if experience == "finance":
        return [{"label": "Open finance notes", "href": "/ggv/finance"}]
    if experience == "bzg_fb_ops":
        links = []
        for brand in brands:
            pair = _BRAND_DESK.get(brand["id"])
            if pair:
                links.append({"label": pair[0], "href": pair[1]})
        return links
    if experience == "closer":
        links = []
        for brand in brands:
            if brand["id"] == "BZG-UMA":
                links.append({"label": "Open today's close", "href": "/uma-blu-close"})
        return links
    if experience == "manager" and str(role.get("role_id") or "").startswith("ROLE-AMG-"):
        return [{"label": "Open the hotel desk", "href": "/amg-ops-pack"}]
    pair = _GENERIC_DESK.get(str(role.get("role_id") or ""))
    if pair:
        return [{"label": pair[0], "href": pair[1]}]
    return []


def _covers(experience: str, brands: list[dict[str, str]], scopes: list[dict[str, str]]) -> list[str]:
    if experience in {"creative_director", "content_creator"}:
        return ["Content library"]
    if experience == "atrium_finance":
        labels = [s["label"] for s in scopes if s.get("label")]
        return labels or ["Atrium Finance"]
    if experience == "finance":
        labels = [s["label"] for s in scopes if "finance" in s["label"].lower()]
        return labels or ["Finance notes"]
    if experience == "bzg_fb_ops":
        return [b["name"] for b in brands] or ["No venue is on this assignment yet"]
    if experience == "closer":
        return [b["name"] for b in brands] or ["No venue is on this assignment yet"]
    if experience == "manager":
        labels = [s["label"] for s in scopes if s.get("label")]
        return labels or ["No site is on this assignment yet"]
    if experience == "owner_pulse":
        return []
    return []


def _boundary(experience: str) -> str | None:
    if experience == "content_creator":
        return (
            "You can work in the content library for the brands on your assignment: "
            "view, upload, and submit for review. "
            "You cannot approve, publish, open finance, HR, payroll, or Owner command."
        )
    if experience == "creative_director":
        return (
            "You review and coordinate content work for the brands on your assignment. "
            "Publish stays on the existing publish gate. "
            "You cannot pay, change a bank account, or open Owner command."
        )
    if experience == "atrium_finance":
        return (
            "You work in Atrium Finance. "
            "You can open the board, read the ledger and the chart, and send work for approval. "
            "You cannot approve or post a journal, pay, change a bank account, or open another company."
        )
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
    if experience == "closer":
        return (
            "You record today's close for the venues on your assignment. "
            "You cannot pay, change a bank account, verify your own close, or change a governance rule."
        )
    if experience == "manager":
        return (
            "You run the hotel day for the sites on your assignment. "
            "You cannot pay, change a bank account, or change a governance rule."
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


def _today_empty(experience: str) -> str:
    if experience in {"creative_director", "content_creator"}:
        return (
            "No content work is assigned to this seat yet. "
            "Plans, submissions, and production tasks for this role will appear here "
            "when they are stored on the assignment."
        )
    return "Nothing is assigned to you for today."


def _staff_date(value: str | None) -> str:
    text = (value or "").strip()[:10]
    try:
        day = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return ""
    return f"{day.day} {day.strftime('%b %Y')}"


def _plan_status_words(status: str) -> str:
    words = {
        "Working_Draft": "Working draft",
        "Human_Approved": "Approved",
        "Submitted": "Submitted",
        "Changes_Requested": "Changes requested",
    }
    if status in words:
        return words[status]
    cleaned = status.replace("_", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else "Status not recorded"


def _plan_in_scope(brand_id: str, scope_ids: set[str]) -> bool:
    brand = (brand_id or "").strip()
    needed = BRAND_SCOPES.get(brand.lower())
    if needed and scope_ids & set(needed):
        return True
    return brand in scope_ids or brand.lower() in {item.lower() for item in scope_ids}


def _plan_footnote(row: Any) -> str:
    start = _staff_date(row["period_start"] if hasattr(row, "keys") else None)
    if start:
        return f"From the Habitat plan, {start}. Not yet checked in Wolf."
    return "From the Habitat plan. Not yet checked in Wolf."


def _dedupe_plan_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one card per title+period+status. True duplicates collapse; differing status stays."""
    kept: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str, str]] = []
    for item in items:
        key = (
            str(item.get("title") or ""),
            str(item.get("date_range") or ""),
            str(item.get("status") or ""),
            str(item.get("brand_id") or ""),
        )
        prior = kept.get(key)
        if prior is None:
            kept[key] = item
            order.append(key)
            continue
        # Prefer the higher source id (later stamp) when content is the same shape.
        try:
            if int(item.get("source_id") or 0) >= int(prior.get("source_id") or 0):
                kept[key] = item
        except (TypeError, ValueError):
            kept[key] = item
    return [kept[key] for key in order]


def _stored_plan_card_items(conn, person_id: str, scope_ids: set[str]) -> list[dict[str, Any]]:
    """Plan cards assigned to this person on CURRENT plans only → My Work today."""
    from datetime import date

    today = date.today().isoformat()
    try:
        person = conn.execute(
            "SELECT display_name FROM org_persons WHERE person_id=?",
            (person_id,),
        ).fetchone()
        display = str(person[0] or "").strip() if person else ""
        emails = [
            str(r[0] or "").strip().lower()
            for r in conn.execute(
                """
                SELECT identifier FROM org_auth_identities
                WHERE person_id=? AND status='ACTIVE' AND provider='email'
                """,
                (person_id,),
            ).fetchall()
        ]
    except Exception:
        return []
    if not display and not emails:
        return []
    try:
        cards = conn.execute(
            """
            SELECT c.id, c.plan_id, c.title, c.card_type, c.body_json, c.status,
                   p.brand_id, p.period_start, p.period_end, p.title AS plan_title
            FROM content_cards c
            JOIN content_plans p ON p.id = c.plan_id
            WHERE ifnull(p.data_lane, 'operational') != 'test'
              AND lower(ifnull(p.status,'')) IN (
                'working_draft', 'human_approved', 'ready_for_render'
              )
              AND ifnull(p.period_start,'') <= ?
              AND ifnull(p.period_end,'') >= ?
            ORDER BY c.id DESC
            LIMIT 200
            """,
            (today, today),
        ).fetchall()
    except Exception:
        return []
    items: list[dict[str, Any]] = []
    for row in cards:
        brand = str(row["brand_id"] or "")
        if not _plan_in_scope(brand, scope_ids):
            continue
        try:
            body = json.loads(row["body_json"] or "{}")
        except Exception:
            body = {}
        assignee = str(body.get("assignee") or "").strip()
        if not assignee:
            continue
        al = assignee.lower()
        matched = False
        if display and (al == display.lower() or display.lower() in al):
            matched = True
        if any(al == e or e in al for e in emails if e):
            matched = True
        if not matched:
            continue
        plan_id = row["plan_id"]
        card_id = row["id"]
        title = str(row["title"] or body.get("hook") or f"Plan item {card_id}")
        items.append(
            {
                "id": f"content-card-{card_id}",
                "title": title,
                "href": f"/content-2.0?plan={plan_id}&brand={brand}#plan",
                "status": str(row["status"] or "OPEN"),
                "status_label": str(row["status"] or "Assigned"),
                "date_range": "",
                "next_step": "Open plan item",
                "brand_id": brand,
                "source_system": "content_cards",
                "source_id": str(card_id),
                "origin": "content-plan-assignment",
                "verified_by_wolf": False,
                "staff_footnote": f"Assigned on the {brand} content plan.",
            }
        )
    return items[:20]


def _stored_plan_items(conn, scope_ids: set[str]) -> list[dict[str, Any]]:
    """Read active content plans in brand scope. Same canonical store as Content Engine."""
    try:
        rows = conn.execute(
            """
            SELECT id, brand_id, title, status, period_start, period_end,
                   created_at, updated_at, data_lane
            FROM content_plans
            WHERE ifnull(data_lane, 'operational') != 'test'
              AND lower(ifnull(status,'')) IN (
                'working_draft', 'human_approved', 'ready_for_render'
              )
            ORDER BY lower(brand_id), id
            """
        ).fetchall()
    except Exception:
        return []
    items: list[dict[str, Any]] = []
    for row in rows:
        brand = str(row["brand_id"] or "")
        if not _plan_in_scope(brand, scope_ids):
            continue
        plan_id = row["id"]
        status = str(row["status"] or "")
        start = _staff_date(row["period_start"])
        end = _staff_date(row["period_end"])
        if start and end:
            date_range = f"{start} to {end}"
        elif start or end:
            date_range = start or end
        else:
            date_range = ""
        brand_label = brand.replace("_", " ").title() or "Brand"
        items.append(
            {
                "id": f"content-plan-{plan_id}",
                "title": str(row["title"] or f"{brand_label} plan {plan_id}"),
                "href": f"/content-2.0?plan={plan_id}&brand={brand}#plan",
                "status": status,
                "status_label": _plan_status_words(status),
                "date_range": date_range,
                "next_step": "Open plan",
                "brand_id": brand,
                "source_system": "content_plans",
                "source_id": str(plan_id),
                "source_timestamp": row["updated_at"] or row["created_at"],
                "import_timestamp": row["created_at"],
                "origin": "historical",
                "verified_by_wolf": False,
                "staff_footnote": _plan_footnote(row),
            }
        )
    return _dedupe_plan_items(items)


def _staff_sections(
    conn,
    person_id: str,
    entities: set[str],
    codes: set[str],
    *,
    today_empty: str,
    experience: str = "",
    scope_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Universal My Work sections over core_work_items (+ Habitat plans for content)."""
    from core import universal_my_work as umw

    extra_today: list[dict[str, Any]] = []
    if experience in {"creative_director", "content_creator"}:
        extra_today = _stored_plan_items(conn, scope_ids or set())
        extra_today.extend(
            _stored_plan_card_items(conn, person_id, scope_ids or set())
        )
    sections = umw.build_universal_sections(
        person_id, conn=conn, extra_today=extra_today
    )
    # Keep approval-queue attention/waiting from the prior projection.
    mine = _clean_work(
        _work_rows(
            conn,
            entities,
            ("OPEN", "IN_PROGRESS", "BLOCKED", "WAITING", "RETURNED", "REASSIGNED"),
            person_id,
        )
    )
    mine_ids = {str(r["work_item_id"]) for r in mine}
    by_key = {str(s.get("key")): s for s in sections}
    attention = list(by_key.get("attention", {}).get("items") or [])
    waiting = list(by_key.get("waiting", {}).get("items") or [])
    for ap in _approval_rows(conn, entities):
        if _demo(ap.get("approval_request_id"), ap.get("title"), ap.get("requested_by_person_id")):
            continue
        title = str(ap.get("title") or "Request")
        linked = str(ap.get("linked_work_item_id") or "")
        href = _work_href(linked) if linked else None
        row = _item(str(ap["approval_request_id"]), title, href=href, status="PENDING")
        if str(ap.get("requested_by_person_id") or "") == person_id or (linked and linked in mine_ids):
            waiting.append(row)
            continue
        needed = str(ap.get("required_permission_code") or "")
        if "approval.decide" in codes and (not needed or needed in codes):
            attention.append(row)
    if not (by_key.get("today", {}).get("items")):
        by_key["today"]["empty"] = True
        by_key["today"]["empty_message"] = today_empty
    by_key["attention"]["items"] = attention[:20]
    by_key["attention"]["empty"] = not attention
    by_key["attention"]["empty_message"] = None if attention else "Nothing needs your attention."
    by_key["waiting"]["items"] = waiting[:20]
    by_key["waiting"]["empty"] = not waiting
    by_key["waiting"]["empty_message"] = None if waiting else "You are not waiting on anyone."
    return [
        by_key["today"],
        by_key["do_this_next"],
        by_key["attention"],
        by_key["waiting"],
        by_key["completed"],
    ]


def _owner_sections(conn, entities: set[str], codes: set[str], person_id: str) -> list[dict[str, Any]]:
    open_rows = _clean_work(_work_rows(conn, entities, ("OPEN", "IN_PROGRESS"), None))
    blocked_rows = _clean_work(_work_rows(conn, entities, ("BLOCKED",), None))
    done_rows = _clean_work(_work_rows(conn, entities, ("COMPLETED", "VERIFIED"), None))
    happening = [
        _item(r["work_item_id"], r["title"], href=_work_href(r["work_item_id"]), status=r["status"])
        for r in open_rows[:12]
    ]
    blocked = [
        _item(r["work_item_id"], r["title"], href=_work_href(r["work_item_id"]), status=r["status"])
        for r in blocked_rows[:12]
    ]
    improving = [
        _item(r["work_item_id"], r["title"], href=_work_href(r["work_item_id"]), status=r["status"])
        for r in done_rows[:8]
    ]
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
        linked = str(ap.get("linked_work_item_id") or "")
        href = _work_href(linked) if linked else None
        if str(ap.get("request_type") or "") == "SPEND" or str(ap.get("material_amount") or "").strip():
            amount = str(ap.get("material_amount") or "").strip()
            label = title if not amount else f"{title} ({amount} {ap.get('currency') or ''})".strip()
            money.append(_item(aid, label, href=href, status="PENDING"))
        needed = str(ap.get("required_permission_code") or "")
        requester = str(ap.get("requested_by_person_id") or "")
        if requester != person_id and "approval.decide" in codes and (not needed or needed in codes):
            authority.append(_item(aid, title, href=href, status="PENDING"))
        if requester == person_id:
            wrong.append(_item(aid, title, href=href, status="PENDING"))
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
        # MYWORK-1: every seated person gets universal My Work sections.
        sections = _staff_sections(
            c,
            pid,
            entities,
            codes,
            today_empty=_today_empty(experience),
            experience=experience,
            scope_ids={str(s["id"]) for s in scope_rows},
        )
        if experience == "owner_pulse":
            from core import universal_my_work as umw

            pulse = _owner_sections(c, entities, codes, pid)
            by = {str(s.get("key")): s for s in sections}
            # HUMANCOMM-1: Overwatch is the exception surface — not a routine work list.
            overwatch_items = umw.owner_work_exceptions(c)
            awaiting_n = sum(
                1 for it in overwatch_items if it.get("status") == "AWAITING_VERIFY"
            )
            needs_routing_n = sum(
                1 for it in overwatch_items if it.get("routing_state") == "NEEDS_ROUTING"
            )
            fail_n = sum(
                1
                for it in overwatch_items
                if it.get("commissioning_result") == "FAIL"
                or it.get("origin") == "commissioning-repair"
            )
            # Owner attention = same exception set (capped), not personal routine backlog.
            by["attention"]["items"] = overwatch_items[:24]
            by["attention"]["empty"] = not overwatch_items
            by["attention"]["empty_message"] = (
                None if overwatch_items else "Nothing needs your attention."
            )
            # Owner TODAY should not be a dump of everyone else's routine work.
            by["today"]["items"] = [
                it
                for it in (by["today"].get("items") or [])
                if it.get("current_owner_person_id") == pid
                or it.get("is_commissioning")
                or it.get("routing_state") == "NEEDS_ROUTING"
            ][:8]
            by["today"]["empty"] = not by["today"]["items"]
            by["do_this_next"]["items"] = []
            by["do_this_next"]["empty"] = True
            by["do_this_next"]["empty_message"] = "Routine work does not route through Owner."
            sections = [
                by["today"],
                by["do_this_next"],
                by["attention"],
                by["waiting"],
                by["completed"],
            ]
            sections.append(
                {
                    "key": "owner_overwatch",
                    "title": "OVERWATCH",
                    "empty": not overwatch_items,
                    "empty_message": None
                    if overwatch_items
                    else "No commissioning FAILs, overdue, NEEDS ROUTING, or AWAITING VERIFY.",
                    "items": overwatch_items[:40],
                    "summary": {
                        "awaiting_verify": awaiting_n,
                        "needs_routing": needs_routing_n,
                        "commissioning_fails": fail_n,
                        "total": len(overwatch_items),
                    },
                    "note": (
                        "Commissioning FAILs, overdue, NEEDS ROUTING, owner-authority items, "
                        "and AWAITING VERIFY. Routine work does not route through the Owner."
                    ),
                    "pulse": pulse,
                }
            )
        display = str(person.get("display_name") or "").strip() or "there"
        role_label = str(role.get("role_label") or role.get("position_label") or "Your role")
        covers = _covers(experience, brands, scope_rows)
        desk = _desk(experience, role, brands)
        if any(str(row.get("role_id") or "") == "ROLE-GGV-FINANCE-OPERATOR" for row in rows):
            if not any(item.get("href") == "/ggv/finance" for item in desk):
                desk.append({"label": "Open GGV Finance", "href": "/ggv/finance"})
        boundary = _boundary(experience)
        authority = {
            "move_money": bool(codes & _MONEY),
            "change_bank": bool(codes & _BANK),
            "authorise_governance": bool(codes & _GOVERN),
            "finance_read": "finance.nota.read" in codes,
            "finance_review": "finance.nota.review" in codes,
            "finance_edit": "finance.nota.create" in codes or "finance.nota.edit" in codes,
            "unrestricted": False,
        }
        from core import role_dashboard as _dashboard

        audience = _dashboard.audience_for(str(role.get("role_id") or ""), pid)
        dashboard = _dashboard.project(
            experience=experience,
            role_id=role.get("role_id"),
            role_label=role_label,
            covers=covers,
            desk=desk,
            boundary=boundary,
            sections=sections,
            audience=audience,
            authority=authority,
        )
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
                "label": role_label,
            },
            "scopes": [s["id"] for s in scope_rows],
            "covers": covers,
            "desk": desk,
            "boundary": boundary,
            "dashboard": dashboard,
            "notifications": {
                "empty": True,
                "empty_message": "No notifications.",
                "items": [],
            },
            "authority": authority,
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
        "representative": (home.get("dashboard") or {}).get("representative"),
        "audience": (home.get("dashboard") or {}).get("audience"),
        "dashboard_sections": [
            {
                "key": s.get("key"),
                "title": s.get("title"),
                "empty": s.get("empty"),
                "titles": [i.get("title") for i in (s.get("items") or [])],
            }
            for s in ((home.get("dashboard") or {}).get("sections") or [])
        ],
    }
