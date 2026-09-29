#!/usr/bin/env python3
"""Universal My Work — projection + delegation chain + commissioning + reports.

Decision served: Matt 29 Sep 2026 07:20 P0 UNIVERSAL MY WORK.
Canonical model stays core_work_items (+ core_work_delegations / evidence files).
COMPLETED (DONE) ≠ VERIFIED. staff_ready / human_commissioned stay false.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core import audit as _audit
from core import evidence as _evidence
from core import rbac as _rbac
from core import work_items as wi

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
BLOB_LOCAL = BETA_ROOT / "state" / "work-evidence" / "blobs"
BLOB_NAS = Path("/Volumes/05-Wolf-Vault-Mirror/wolf-command/work-evidence")
LEGACY_PROPOSAL = BETA_ROOT / "state" / "legacy" / "proposed-migration.json"
LEGACY_CANDIDATES = BETA_ROOT / "state" / "legacy" / "legacy-work-candidates.json"
TZ8 = timezone(timedelta(hours=8))
WITA = ZoneInfo("Asia/Makassar")
BOUND = "beta-universal-my-work"

# Engineering repair queue — not a Person. owner/executor stay null.
ENGINEERING_QUEUE = "ENGINEERING"
ROUTING_NEEDS = "NEEDS_ROUTING"
ROUTING_HELD = "HELD"  # HUMFIX-1B: premature RETEST held while repair finishes
ROUTING_HELD_CF = "HELD_UNTIL_CF_ACCESS"  # HEADCHEF-1: commissioning held for Peaches activate

# Presentation labels (plain words). DB statuses stay machine codes.
STATUS_LABEL = {
    "OPEN": "ASSIGNED",
    "IN_PROGRESS": "IN PROGRESS",
    "BLOCKED": "BLOCKED",
    "WAITING": "WAITING",
    "RETURNED": "RETURNED",
    "REASSIGNED": "REASSIGNED",
    "COMPLETED": "DONE",
    "AWAITING_VERIFY": "AWAITING VERIFY",
    "VERIFIED": "VERIFIED",
    "CANCELLED": "CANCELLED",
}

ACTIVE_WORK = frozenset(
    {"OPEN", "IN_PROGRESS", "BLOCKED", "WAITING", "RETURNED", "REASSIGNED"}
)

# assignee_in_source → person_id (reliable name map only)
_SOURCE_ASSIGNEE_MAP = {
    "devi": "PERS-DEVI",
    "ni putu devi parwati": "PERS-DEVI",
    "amanda": "PERS-AMANDA",
    "haikal": "PERS-HAIKAL",
    "zayen": "PERS-ZAYEN",
    "mr wolf / owner": "PERS-MATT",
    "mr_wolf": "PERS-MATT",
    "mr wolf": "PERS-MATT",
    "matt": "PERS-MATT",
}

_OWNER_AUTHORITY_HINTS = (
    "decide",
    "approve",
    "payment",
    "bank",
    "credential",
    "owner",
    "authority",
    "policy",
    "payroll",
    "hire",
    "fire",
    "salary",
    "contract sign",
)

SECTION_TITLES = {
    "today": "TODAY",
    "do_this_next": "DO THIS NEXT",
    "attention": "NEEDS ATTENTION",
    "waiting": "WAITING",
    "completed": "COMPLETED",
}


class MyWorkError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def format_wita(value: str | None) -> str:
    """Present a stored UTC/ISO stamp as Asia/Makassar local time with WITA label.

    Store stays UTC. Empty/unparseable values pass through unchanged.
    """
    text = (value or "").strip()
    if not text:
        return ""
    try:
        stamp = text.replace("Z", "+00:00")
        moment = datetime.fromisoformat(stamp)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        local = moment.astimezone(WITA)
        return local.strftime("%Y-%m-%d %H:%M") + " WITA"
    except ValueError:
        return text


def blob_root() -> Path:
    """NAS canonical when mounted; otherwise local Beta staging.

    Tests/shots may set WOLF_WORK_EVIDENCE_BLOBS to an isolated temp directory
    so fixture files never land in the live Beta evidence tree.
    """
    override = (os.environ.get("WOLF_WORK_EVIDENCE_BLOBS") or "").strip()
    if override:
        path = Path(override).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    try:
        if BLOB_NAS.parent.exists() and BLOB_NAS.parent.is_mount():
            BLOB_NAS.mkdir(parents=True, exist_ok=True)
            return BLOB_NAS
    except OSError:
        pass
    BLOB_LOCAL.mkdir(parents=True, exist_ok=True)
    return BLOB_LOCAL


def status_label(status: str | None) -> str:
    s = (status or "").strip().upper()
    return STATUS_LABEL.get(s, s or "UNKNOWN")


def _person_name(conn, person_id: str | None) -> str:
    pid = (person_id or "").strip()
    if not pid:
        return ""
    row = conn.execute(
        "SELECT display_name FROM org_persons WHERE person_id=?", (pid,)
    ).fetchone()
    return str(row[0] or pid) if row else pid


def _active_assignment(conn, person_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT a.assignment_id, a.position_id, p.role_id, p.position_label,
               r.display_name AS role_label, a.is_primary
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_roles r ON r.role_id = p.role_id
        WHERE a.person_id = ? AND a.status = 'ACTIVE' AND a.end_at IS NULL
        ORDER BY a.is_primary DESC, a.assignment_id
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    return dict(row) if row else None


def list_work_receivers(conn=None) -> list[dict[str, Any]]:
    """Every real Person with an active Assignment who can receive work."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.is_primary,
                   pers.display_name,
                   pos.position_id, pos.position_label, pos.role_id,
                   r.display_name AS role_label
            FROM org_assignments a
            JOIN org_persons pers ON pers.person_id = a.person_id
            JOIN org_positions pos ON pos.position_id = a.position_id
            JOIN org_roles r ON r.role_id = pos.role_id
            WHERE a.status = 'ACTIVE' AND a.end_at IS NULL
              AND pers.status = 'ACTIVE'
              AND a.person_id NOT LIKE 'PERS-%DEMO%'
              AND a.person_id NOT LIKE 'PERS-P4-%'
              AND pos.role_id NOT LIKE '%FIXTURE%'
            ORDER BY pers.display_name, a.is_primary DESC
            """
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "person_id": row["person_id"],
                    "name": row["display_name"],
                    "assignment_id": row["assignment_id"],
                    "role_id": row["role_id"],
                    "role": row["role_label"],
                    "position": row["position_label"],
                    "is_primary": bool(row["is_primary"]),
                }
            )
        return out
    finally:
        if own:
            c.close()


def _checklist_href(item: dict[str, Any]) -> str:
    try:
        steps = json.loads(item["checklist_json"]) if item.get("checklist_json") else []
    except (TypeError, json.JSONDecodeError):
        steps = []
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("href"):
                return str(step["href"])
    return ""


def enrich_card(conn, item: dict[str, Any]) -> dict[str, Any]:
    """Card fields required by MYWORK-1 Part B + HUMANCOMM-1 commissioning."""
    wid = str(item.get("work_item_id") or "")
    owner = item.get("executor_person_id") or item.get("owner_person_id")
    accountable = item.get("accountable_person_id") or item.get("owner_person_id")
    requested = item.get("requested_by_person_id") or item.get("created_by_person_id")
    ev_files = conn.execute(
        "SELECT COUNT(*) FROM core_work_evidence_files WHERE work_item_id=?",
        (wid,),
    ).fetchone()[0]
    chain = delegation_chain(wid, conn=conn)
    status = str(item.get("status") or "")
    origin = str(item.get("origin") or "")
    is_commissioning = origin in {"commissioning", "commissioning-retest"}
    open_href = _checklist_href(item)
    next_step = (item.get("what_happens_next") or "").strip()
    if not next_step:
        if status == "OPEN":
            next_step = "Accept and start, or open the instructions."
        elif status == "IN_PROGRESS":
            next_step = (
                "Attach evidence, choose PASS or FAIL, then mark DONE."
                if is_commissioning
                else "Attach evidence, then mark DONE."
            )
        elif status == "AWAITING_VERIFY":
            next_step = "Waiting for Owner / verifier. Your PASS is recorded."
        elif status == "COMPLETED":
            next_step = "Waiting for verification. DONE is not VERIFIED."
        elif status == "VERIFIED":
            next_step = "Verified. Outcome is on record."
        elif status == "BLOCKED":
            next_step = "Clear the block or reassign."
        elif status == "WAITING":
            next_step = "Waiting on another person or system."
        elif status == "RETURNED":
            next_step = "Returned — fix and resubmit with evidence."
        else:
            next_step = "Open the task."
    queue_label = ""
    if origin == "commissioning-repair" and not owner:
        queue_label = ENGINEERING_QUEUE
    return {
        "id": wid,
        "work_item_id": wid,
        "title": item.get("title") or "",
        "what": item.get("title") or "",
        "requested_by": _person_name(conn, requested),
        "requested_by_person_id": requested,
        "current_owner": _person_name(conn, owner) or queue_label or "Unassigned",
        "current_owner_person_id": owner,
        "accountable": _person_name(conn, accountable),
        "accountable_person_id": accountable,
        "due": format_wita(item.get("due_at")) or item.get("due_at"),
        "due_at_utc": item.get("due_at"),
        "company_site_department": item.get("scope_label") or item.get("owning_entity_id"),
        "priority": item.get("priority"),
        "instructions": item.get("instructions") or item.get("description") or "",
        "checklist": json.loads(item["checklist_json"]) if item.get("checklist_json") else [],
        "open_href": open_href,
        "evidence_required": item.get("evidence_required") or "",
        "evidence_files": int(ev_files or 0),
        "status": status,
        "status_label": status_label(status),
        "what_happens_next": next_step,
        "next_step": next_step,
        "href": f"/my-work/item/{wid}",
        "delegation_hops": len(chain),
        "origin": item.get("origin"),
        "import_label": item.get("import_label"),
        "commissioning_capability_id": item.get("commissioning_capability_id"),
        "commissioning_result": item.get("commissioning_result"),
        "human_result": item.get("human_result"),
        "human_comment": item.get("human_comment"),
        "opened_at": item.get("opened_at"),
        "opened_at_display": format_wita(item.get("opened_at")),
        "routing_state": item.get("routing_state"),
        "routing_reason": item.get("routing_reason"),
        "is_commissioning": is_commissioning,
        "requires_human_result": is_commissioning,
        "engineering_queue": origin == "commissioning-repair" and not owner,
        "staff_ready": False,
        "human_commissioned": False,
    }


def _mine_rows(conn, person_id: str) -> list[dict[str, Any]]:
    """Personal My Work — exclude NEEDS_ROUTING, HELD retests, and engineering-queue repairs."""
    rows = conn.execute(
        """
        SELECT * FROM core_work_items
        WHERE status != 'CANCELLED'
          AND COALESCE(routing_state, '') NOT IN (?, ?, ?)
          AND (
            owner_person_id = ?
            OR executor_person_id = ?
            OR accountable_person_id = ?
          )
          AND NOT (
            origin = 'commissioning-repair'
            AND (owner_person_id IS NULL OR owner_person_id = '')
            AND (executor_person_id IS NULL OR executor_person_id = '')
          )
        ORDER BY priority ASC, due_at IS NULL, due_at ASC, updated_at DESC
        LIMIT 80
        """,
        (ROUTING_NEEDS, ROUTING_HELD, ROUTING_HELD_CF, person_id, person_id, person_id),
    ).fetchall()
    return [dict(r) for r in rows]


def build_universal_sections(
    person_id: str,
    *,
    conn=None,
    extra_today: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """TODAY / DO THIS NEXT / NEEDS ATTENTION / WAITING / COMPLETED.

    HUMANCOMM-1: first 3 non-retest active items in TODAY; the rest in DO THIS NEXT.
    HUMFIX-1C: open commissioning-retest cards always lead TODAY (all of them),
    so RETEST work is never pushed out by plan cards or the 3-slot cadence.
    """
    own = conn is None
    c = conn or wi.db_connect()
    try:
        mine = _mine_rows(c, person_id)
        cards = [enrich_card(c, r) for r in mine]
        active = [
            card
            for card in cards
            if card["status"] in {"OPEN", "IN_PROGRESS", "RETURNED"}
            and card.get("current_owner_person_id") == person_id
        ]
        active_sorted = sorted(
            active, key=lambda x: (x.get("priority") or 3, x.get("due") or "9999")
        )
        retests = [
            card
            for card in active_sorted
            if card.get("origin") == "commissioning-retest"
        ]
        routine = [
            card
            for card in active_sorted
            if card.get("origin") != "commissioning-retest"
        ]
        filler = list(extra_today or []) + routine
        today = retests + filler[:3]
        do_next = filler[3:8]
        attention = [
            card
            for card in cards
            if card["status"] in {"BLOCKED", "RETURNED", "REASSIGNED"}
            or (
                card.get("commissioning_result") == "FAIL"
                and card["status"] != "VERIFIED"
            )
        ]
        waiting = [card for card in cards if card["status"] == "WAITING"]
        for card in cards:
            if (
                card.get("accountable_person_id") == person_id
                and card.get("current_owner_person_id")
                and card.get("current_owner_person_id") != person_id
                and card["status"] in ACTIVE_WORK
            ):
                if card not in waiting:
                    waiting.append(card)
        completed = [
            card
            for card in cards
            if card["status"] in {"COMPLETED", "AWAITING_VERIFY", "VERIFIED"}
        ][:12]
        return [
            {
                "key": "today",
                "title": SECTION_TITLES["today"],
                "empty": not today,
                "empty_message": None if today else "Nothing is assigned to you for today.",
                "items": today,
            },
            {
                "key": "do_this_next",
                "title": SECTION_TITLES["do_this_next"],
                "empty": not do_next,
                "empty_message": None if do_next else "Nothing to do next.",
                "items": do_next,
            },
            {
                "key": "attention",
                "title": SECTION_TITLES["attention"],
                "empty": not attention,
                "empty_message": None if attention else "Nothing needs your attention.",
                "items": attention[:20],
            },
            {
                "key": "waiting",
                "title": SECTION_TITLES["waiting"],
                "empty": not waiting,
                "empty_message": None if waiting else "You are not waiting on anyone.",
                "items": waiting[:20],
            },
            {
                "key": "completed",
                "title": SECTION_TITLES["completed"],
                "empty": not completed,
                "empty_message": None if completed else "Nothing completed recently.",
                "items": completed,
            },
        ]
    finally:
        if own:
            c.close()


def can_assign_to(
    actor_person_id: str,
    target_person_id: str,
    entity_id: str,
    *,
    conn=None,
) -> bool:
    """Who can assign to whom — from permissions/scope, not department walls."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        if not wi.person_can_see_entity(actor_person_id, entity_id, conn=c):
            return False
        if not wi.person_can_see_entity(target_person_id, entity_id, conn=c):
            return False
        ev = _rbac.evaluate(
            actor_person_id, "work.assign", {"entity_id": entity_id}, conn=c
        )
        if ev.get("allowed"):
            return True
        # Owner / overwatch can intervene within visible entity scope.
        row = c.execute(
            """
            SELECT r.role_type, r.display_name
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.person_id = ? AND a.status = 'ACTIVE' AND a.end_at IS NULL
            """,
            (actor_person_id,),
        ).fetchone()
        if row and str(row["role_type"] or "").upper() == "EXECUTIVE" and "owner" in str(
            row["display_name"] or ""
        ).lower():
            return True
        # Create permission also allows assign-on-create to in-scope holders.
        ev2 = _rbac.evaluate(
            actor_person_id, "work.create", {"entity_id": entity_id}, conn=c
        )
        return bool(ev2.get("allowed"))
    finally:
        if own:
            c.close()


def delegate_work(
    work_item_id: str,
    *,
    from_person_id: str,
    to_person_id: str,
    note: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """Accountable owner stays; executor becomes the delegate. Chain recorded."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise MyWorkError("Work item not found.", code="not_found", http_status=404)
        if item["status"] in wi.TERMINAL:
            raise MyWorkError("Cannot delegate a closed item.", code="terminal")
        entity = str(item["owning_entity_id"])
        if not can_assign_to(from_person_id, to_person_id, entity, conn=c):
            raise MyWorkError(
                "You cannot assign this work to that person in this scope.",
                code="assign_denied",
                http_status=403,
            )
        accountable = item.get("accountable_person_id") or item.get("owner_person_id") or from_person_id
        from_asg = (_active_assignment(c, from_person_id) or {}).get("assignment_id")
        to_asg = (_active_assignment(c, to_person_id) or {}).get("assignment_id")
        ts = wi.now_utc_iso()
        did = f"WDEL-{uuid.uuid4()}"
        c.execute(
            """
            INSERT INTO core_work_delegations (
              delegation_id, work_item_id, from_person_id, to_person_id,
              from_assignment_id, to_assignment_id, status, offered_at, accepted_at,
              note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'ACCEPTED', ?, ?, ?, ?)
            """,
            (
                did,
                work_item_id,
                from_person_id,
                to_person_id,
                from_asg,
                to_asg,
                ts,
                ts,
                (note or "").strip() or None,
                ts,
            ),
        )
        c.execute(
            """
            UPDATE core_work_items
            SET accountable_person_id = COALESCE(accountable_person_id, ?),
                executor_person_id = ?,
                owner_person_id = ?,
                owner_org_assignment_id = ?,
                status = CASE WHEN status = 'OPEN' THEN 'IN_PROGRESS' ELSE status END,
                started_at = COALESCE(started_at, ?),
                what_happens_next = ?,
                updated_at = ?
            WHERE work_item_id = ?
            """,
            (
                accountable,
                to_person_id,
                to_person_id,
                to_asg,
                ts,
                f"Delegated to {_person_name(c, to_person_id)}. Accountable remains {_person_name(c, accountable)}.",
                ts,
                work_item_id,
            ),
        )
        updated = wi.get_work_item(work_item_id, conn=c)
        _audit.safe_record(
            action="work.delegate",
            result="SUCCEEDED",
            source="universal_my_work",
            actor_type="PERSON",
            verified_person_id=from_person_id,
            actor_person_id=from_person_id,
            entity_id=entity,
            resource_type="work_item",
            resource_id=work_item_id,
            metadata={
                "from": from_person_id,
                "to": to_person_id,
                "accountable": accountable,
                "delegation_id": did,
            },
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "work_item": updated,
            "delegation_id": did,
            "chain": delegation_chain(work_item_id, conn=c),
            "card": enrich_card(c, updated or {}),
        }
    finally:
        if own:
            c.close()


def delegation_chain(work_item_id: str, *, conn=None) -> list[dict[str, Any]]:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT * FROM core_work_delegations
            WHERE work_item_id = ?
            ORDER BY offered_at ASC, created_at ASC
            """,
            (work_item_id,),
        ).fetchall()
        out = []
        for r in rows:
            offered_raw = r["offered_at"]
            accepted_raw = r["accepted_at"]
            out.append(
                {
                    "delegation_id": r["delegation_id"],
                    "from_person_id": r["from_person_id"],
                    "from_name": _person_name(c, r["from_person_id"]),
                    "to_person_id": r["to_person_id"],
                    "to_name": _person_name(c, r["to_person_id"]),
                    "status": r["status"],
                    # Raw UTC kept for machines; *_display is Asia/Makassar + WITA.
                    "offered_at": offered_raw,
                    "accepted_at": accepted_raw,
                    "offered_at_display": format_wita(offered_raw),
                    "accepted_at_display": format_wita(accepted_raw),
                    "note": r["note"],
                }
            )
        return out
    finally:
        if own:
            c.close()


def store_evidence_file(
    work_item_id: str,
    *,
    filename: str,
    content: bytes,
    uploaded_by_person_id: str,
    content_type: str | None = None,
    note: str | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise MyWorkError("Work item not found.", code="not_found", http_status=404)
        entity = str(item["owning_entity_id"])
        if not _rbac.evaluate(
            uploaded_by_person_id, "evidence.record.submit", {"entity_id": entity}, conn=c
        ).get("allowed"):
            # Soft path: owner/executor/accountable, or Owner on engineering repairs.
            holders = {
                item.get("owner_person_id"),
                item.get("executor_person_id"),
                item.get("accountable_person_id"),
            }
            eng_repair = (
                item.get("origin") == "commissioning-repair"
                and uploaded_by_person_id == "PERS-MATT"
            )
            if uploaded_by_person_id not in holders and not eng_repair:
                raise MyWorkError(
                    "evidence.record.submit denied",
                    code="rbac_denied",
                    http_status=403,
                )
        root = blob_root()
        file_id = f"WEF-{uuid.uuid4()}"
        safe_name = Path(filename or "evidence.bin").name.replace("..", "_")
        dest_dir = root / work_item_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{file_id}-{safe_name}"
        dest.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        ts = wi.now_utc_iso()
        # Link via evidence spine when types exist.
        evidence_id = None
        try:
            et = c.execute(
                "SELECT evidence_type FROM core_evidence_types WHERE evidence_type='work_file'"
            ).fetchone()
            if not et:
                c.execute(
                    """
                    INSERT INTO core_evidence_types (
                      evidence_type, description, status, created_at, updated_at
                    ) VALUES ('work_file', 'File attached to a work item', 'ACTIVE', ?, ?)
                    """,
                    (ts, ts),
                )
            ev = _evidence.submit_evidence(
                entity_id=entity,
                evidence_type="work_file",
                governed_object_type="WORK_ITEM",
                governed_object_id=work_item_id,
                verified_person_id=uploaded_by_person_id,
                source_reference=(note or safe_name)[:240],
                object_ref=str(dest),
                content_hash=digest,
                conn=c,
                commit=False,
            )
            evidence_id = ev.get("evidence_id") if isinstance(ev, dict) else None
        except Exception:
            evidence_id = None
        c.execute(
            """
            INSERT INTO core_work_evidence_files (
              file_id, work_item_id, evidence_id, filename, content_type,
              byte_size, storage_path, sha256, uploaded_by_person_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                work_item_id,
                evidence_id,
                safe_name,
                content_type,
                len(content),
                str(dest),
                digest,
                uploaded_by_person_id,
                ts,
            ),
        )
        c.execute(
            """
            UPDATE core_work_items
            SET completion_evidence_reference = ?,
                updated_at = ?
            WHERE work_item_id = ?
            """,
            (str(dest), ts, work_item_id),
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "file_id": file_id,
            "evidence_id": evidence_id,
            "storage_path": str(dest),
            "sha256": digest,
            "byte_size": len(content),
            "nas_canonical": str(root).startswith("/Volumes/"),
        }
    finally:
        if own:
            c.close()


def _evidence_count(conn, work_item_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM core_work_evidence_files WHERE work_item_id=?",
        (work_item_id,),
    ).fetchone()
    return int(row[0] or 0)


def list_evidence_files(
    work_item_id: str,
    *,
    conn=None,
) -> list[dict[str, Any]]:
    """Read-only evidence trail for a work item (metadata only; no blob bytes).

    Honest under the test write guard: uses whatever catalog connection the
    caller supplies (temp copy in tests) and never invents files. Paths are
    returned as stored so callers can verify they land under blob_root().
    """
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT file_id, work_item_id, evidence_id, filename, content_type,
                   byte_size, storage_path, sha256, uploaded_by_person_id, created_at
            FROM core_work_evidence_files
            WHERE work_item_id=?
            ORDER BY created_at ASC, file_id ASC
            """,
            (work_item_id,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            created_raw = r["created_at"]
            out.append(
                {
                    "file_id": r["file_id"],
                    "work_item_id": r["work_item_id"],
                    "evidence_id": r["evidence_id"],
                    "filename": r["filename"],
                    "content_type": r["content_type"],
                    "byte_size": int(r["byte_size"] or 0),
                    "storage_path": r["storage_path"],
                    "sha256": r["sha256"],
                    "uploaded_by_person_id": r["uploaded_by_person_id"],
                    "created_at": created_raw,
                    "created_at_display": format_wita(created_raw),
                }
            )
        return out
    finally:
        if own:
            c.close()


def _is_commissioning_origin(origin: str | None) -> bool:
    return str(origin or "") in {"commissioning", "commissioning-retest"}


def record_opened(
    work_item_id: str,
    *,
    viewer_person_id: str,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """First detail open by owner/executor stamps opened_at once."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise MyWorkError("Work item not found.", code="not_found", http_status=404)
        viewer = (viewer_person_id or "").strip()
        is_holder = viewer in {
            item.get("owner_person_id"),
            item.get("executor_person_id"),
        }
        stamped = False
        if is_holder and not item.get("opened_at"):
            ts = wi.now_utc_iso()
            c.execute(
                "UPDATE core_work_items SET opened_at=?, updated_at=? WHERE work_item_id=?",
                (ts, ts, work_item_id),
            )
            stamped = True
            _audit.safe_record(
                action="work.opened",
                result="SUCCEEDED",
                source="universal_my_work",
                actor_type="PERSON",
                verified_person_id=viewer,
                actor_person_id=viewer,
                entity_id=item.get("owning_entity_id"),
                resource_type="work_item",
                resource_id=work_item_id,
                metadata={"opened_at": ts},
                conn=c,
                commit=False,
            )
            if commit:
                c.commit()
            item = wi.get_work_item(work_item_id, conn=c) or item
        return {"ok": True, "work_item": item, "opened_stamped": stamped}
    finally:
        if own:
            c.close()


def set_human_result(
    work_item_id: str,
    *,
    person_id: str,
    result: str,
    comment: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """Employee PASS/FAIL — separate from Peaches/Owner verification."""
    res = (result or "").strip().upper()
    if res not in {"PASS", "FAIL"}:
        raise MyWorkError("human_result must be PASS or FAIL", code="invalid_result")
    note = (comment or "").strip()
    if res == "FAIL" and not note:
        raise MyWorkError(
            "When you choose FAIL, say what is wrong or could be better.",
            code="comment_required",
        )
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise MyWorkError("Work item not found.", code="not_found", http_status=404)
        if not _is_commissioning_origin(item.get("origin")):
            raise MyWorkError(
                "PASS/FAIL is only for commissioning items.",
                code="not_commissioning",
            )
        if person_id not in {
            item.get("owner_person_id"),
            item.get("executor_person_id"),
        }:
            raise MyWorkError(
                "Only the person doing this work can choose PASS or FAIL.",
                code="rbac_denied",
                http_status=403,
            )
        if item["status"] in wi.TERMINAL:
            raise MyWorkError("This item is closed.", code="terminal")
        ts = wi.now_utc_iso()
        c.execute(
            """
            UPDATE core_work_items
            SET human_result=?, human_comment=?, updated_at=?
            WHERE work_item_id=?
            """,
            (res, note or None, ts, work_item_id),
        )
        _audit.safe_record(
            action="work.human_result",
            result="SUCCEEDED",
            source="universal_my_work",
            actor_type="PERSON",
            verified_person_id=person_id,
            actor_person_id=person_id,
            entity_id=item.get("owning_entity_id"),
            resource_type="work_item",
            resource_id=work_item_id,
            metadata={"human_result": res, "has_comment": bool(note)},
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "work_item": wi.get_work_item(work_item_id, conn=c),
            "human_result": res,
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        if own:
            c.close()


def _find_linked_repair(conn, parent_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM core_work_items
        WHERE parent_work_item_id=? AND origin='commissioning-repair'
          AND status NOT IN ('CANCELLED')
        ORDER BY created_at DESC LIMIT 1
        """,
        (parent_id,),
    ).fetchone()
    return dict(row) if row else None


def create_engineering_repair(
    parent: dict[str, Any],
    *,
    note: str | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """FAIL → repair owned by ENGINEERING queue (not the employee)."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        parent_id = str(parent["work_item_id"])
        existing = _find_linked_repair(c, parent_id)
        if existing:
            return existing
        entity = str(parent["owning_entity_id"])
        ts = wi.now_utc_iso()
        repair = wi.create_work_item(
            title=f"Repair: {parent.get('title')}",
            description=(
                f"Engineering repair for failed commissioning {parent_id}. "
                f"Human FAIL comment: {(note or parent.get('human_comment') or '').strip() or '—'}. "
                f"Evidence: {parent.get('completion_evidence_reference') or 'see attachments'}."
            ),
            owning_entity_id=entity,
            work_type="EXCEPTION",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id=None,
            owner_org_assignment_id=None,
            parent_work_item_id=parent_id,
            source_id=f"commissioning-repair:{parent_id}",
            priority=1,
            conn=c,
            commit=False,
        )
        c.execute(
            """
            UPDATE core_work_items
            SET origin='commissioning-repair',
                owner_person_id=NULL,
                owner_org_assignment_id=NULL,
                executor_person_id=NULL,
                accountable_person_id='PERS-MATT',
                scope_label=?,
                import_label=?,
                commissioning_capability_id=?,
                evidence_required='Commit ref + test evidence that the defect is fixed.',
                instructions=?,
                what_happens_next='Engineering fixes the defect, attaches commit/test evidence, marks DONE. A retest is then issued to the same person.',
                updated_at=?
            WHERE work_item_id=?
            """,
            (
                ENGINEERING_QUEUE,
                f"{ENGINEERING_QUEUE} queue — not staff",
                parent.get("commissioning_capability_id"),
                (
                    "This is an engineering repair. Do not assign it back to the employee. "
                    "Fix the defect, attach a commit reference and test evidence, then mark DONE."
                ),
                ts,
                repair["work_item_id"],
            ),
        )
        repair = wi.get_work_item(repair["work_item_id"], conn=c) or repair
        _audit.safe_record(
            action="work.commissioning.repair_created",
            result="SUCCEEDED",
            source="universal_my_work",
            actor_type="SYSTEM",
            entity_id=entity,
            resource_type="work_item",
            resource_id=repair["work_item_id"],
            metadata={
                "parent": parent_id,
                "queue": ENGINEERING_QUEUE,
                "capability": parent.get("commissioning_capability_id"),
            },
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return repair
    finally:
        if own:
            c.close()


def create_retest_for_repair(
    repair_item_id: str,
    *,
    commit_ref: str | None = None,
    actor_person_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """When a repair is fixed with evidence, issue RETEST to the original person."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        repair = wi.get_work_item(repair_item_id, conn=c)
        if not repair or repair.get("origin") != "commissioning-repair":
            raise MyWorkError("Not a commissioning repair item.", code="not_repair")
        parent_id = repair.get("parent_work_item_id")
        parent = wi.get_work_item(parent_id, conn=c) if parent_id else None
        if not parent:
            raise MyWorkError("Parent commissioning item missing.", code="no_parent")
        existing = c.execute(
            """
            SELECT work_item_id FROM core_work_items
            WHERE origin='commissioning-retest'
              AND parent_work_item_id=?
              AND status NOT IN ('CANCELLED')
            ORDER BY created_at DESC LIMIT 1
            """,
            (repair_item_id,),
        ).fetchone()
        if existing:
            return wi.get_work_item(str(existing[0]), conn=c) or {}
        person = parent.get("owner_person_id") or parent.get("executor_person_id")
        if not person:
            raise MyWorkError("Original person unknown for retest.", code="no_person")
        asg = parent.get("owner_org_assignment_id") or _asg(c, person)
        href = _checklist_href(parent) or "/my-work"
        instructions = (
            f"Retest after engineering repair.\n"
            f"1. Open the same surface again: {href}\n"
            f"2. Repeat the original check.\n"
            f"3. Attach a fresh screenshot or photo.\n"
            f"4. Choose PASS or FAIL.\n"
            f"5. Tap DONE.\n"
            f"Repair: {repair_item_id}."
            + (f" Commit: {commit_ref}." if commit_ref else "")
        )
        item = wi.create_work_item(
            title=f"Retest: {parent.get('title')}",
            description=instructions,
            owning_entity_id=str(parent["owning_entity_id"]),
            work_type="AUDIT_FINDING",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id=person,
            owner_org_assignment_id=asg,
            parent_work_item_id=repair_item_id,
            source_id=f"commissioning-retest:{repair_item_id}",
            priority=2,
            conn=c,
            commit=False,
        )
        ts = wi.now_utc_iso()
        c.execute(
            """
            UPDATE core_work_items
            SET origin='commissioning-retest',
                accountable_person_id=?,
                executor_person_id=?,
                requested_by_person_id='PERS-MATT',
                instructions=?,
                evidence_required=?,
                checklist_json=?,
                scope_label=?,
                commissioning_capability_id=?,
                what_happens_next=?,
                updated_at=?
            WHERE work_item_id=?
            """,
            (
                person,
                person,
                instructions,
                parent.get("evidence_required") or "Fresh screenshot after the fix",
                json.dumps([{"step": "Retest the surface", "href": href}]),
                parent.get("scope_label"),
                parent.get("commissioning_capability_id"),
                "Retest is in your My Work TODAY. Attach evidence, choose PASS/FAIL, mark DONE.",
                ts,
                item["work_item_id"],
            ),
        )
        if commit_ref:
            c.execute(
                "UPDATE core_work_items SET repair_commit_ref=?, updated_at=? WHERE work_item_id=?",
                (commit_ref.strip(), ts, repair_item_id),
            )
        retest = wi.get_work_item(item["work_item_id"], conn=c) or item
        _audit.safe_record(
            action="work.commissioning.retest_issued",
            result="SUCCEEDED",
            source="universal_my_work",
            actor_type="PERSON" if actor_person_id else "SYSTEM",
            verified_person_id=actor_person_id,
            actor_person_id=actor_person_id,
            entity_id=parent.get("owning_entity_id"),
            resource_type="work_item",
            resource_id=retest["work_item_id"],
            metadata={
                "repair": repair_item_id,
                "original": parent_id,
                "person": person,
                "commit_ref": commit_ref,
            },
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return retest
    finally:
        if own:
            c.close()


def mark_done(
    work_item_id: str,
    *,
    verified_person_id: str,
    outcome: str | None = None,
    human_result: str | None = None,
    human_comment: str | None = None,
    repair_commit_ref: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """DONE = completion claim. Commissioning gates evidence + PASS/FAIL.

    Does not verify. Does not flip staff_ready / human_commissioned. Does not
    move SYSTEM %.
    """
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise MyWorkError("Work item not found.", code="not_found", http_status=404)
        origin = str(item.get("origin") or "")
        repair_out = None
        retest_out = None

        if _is_commissioning_origin(origin):
            hr = (human_result or item.get("human_result") or "").strip().upper()
            comment = (
                human_comment
                if human_comment is not None
                else item.get("human_comment")
            )
            missing: list[str] = []
            if _evidence_count(c, work_item_id) < 1 and not (
                item.get("completion_evidence_reference") or ""
            ).strip():
                missing.append("required evidence (screenshot, photo, document, or note file)")
            if hr not in {"PASS", "FAIL"}:
                missing.append("PASS or FAIL choice")
            if hr == "FAIL" and not (comment or "").strip():
                missing.append("comment explaining what is wrong or could be better")
            if missing:
                raise MyWorkError(
                    "DONE is blocked until you add: " + "; ".join(missing) + ".",
                    code="done_blocked",
                )
            set_human_result(
                work_item_id,
                person_id=verified_person_id,
                result=hr,
                comment=comment,
                identity=identity,
                conn=c,
                commit=False,
            )
            item = wi.get_work_item(work_item_id, conn=c) or item
            if hr == "PASS":
                item = wi.claim_awaiting_verify(
                    work_item_id,
                    verified_person_id=verified_person_id,
                    outcome=outcome or "Employee PASS — awaiting verify",
                    identity=identity,
                    conn=c,
                    commit=False,
                )
                ts = wi.now_utc_iso()
                c.execute(
                    """
                    UPDATE core_work_items
                    SET what_happens_next=?, updated_at=?
                    WHERE work_item_id=?
                    """,
                    (
                        "AWAITING VERIFY — Owner or work.verify will confirm HUMAN PASS.",
                        ts,
                        work_item_id,
                    ),
                )
            else:
                item = wi.claim_complete(
                    work_item_id,
                    verified_person_id=verified_person_id,
                    outcome=outcome or "Employee FAIL",
                    identity=identity,
                    conn=c,
                    commit=False,
                )
                ts = wi.now_utc_iso()
                c.execute(
                    """
                    UPDATE core_work_items
                    SET commissioning_result='FAIL',
                        what_happens_next=?,
                        updated_at=?
                    WHERE work_item_id=?
                    """,
                    (
                        "FAIL recorded. Engineering repair created. You do not own the repair.",
                        ts,
                        work_item_id,
                    ),
                )
                item = wi.get_work_item(work_item_id, conn=c) or item
                repair_out = create_engineering_repair(
                    item,
                    note=item.get("human_comment"),
                    conn=c,
                    commit=False,
                )
        elif origin == "commissioning-repair":
            if _evidence_count(c, work_item_id) < 1 and not (
                repair_commit_ref or item.get("repair_commit_ref") or ""
            ).strip():
                raise MyWorkError(
                    "DONE is blocked until repair evidence or a commit ref is attached.",
                    code="done_blocked",
                )
            item = wi.claim_complete(
                work_item_id,
                verified_person_id=verified_person_id,
                outcome=outcome or "Repair fixed",
                identity=identity,
                conn=c,
                commit=False,
            )
            if repair_commit_ref:
                c.execute(
                    "UPDATE core_work_items SET repair_commit_ref=?, updated_at=? WHERE work_item_id=?",
                    (repair_commit_ref.strip(), wi.now_utc_iso(), work_item_id),
                )
            retest_out = create_retest_for_repair(
                work_item_id,
                commit_ref=repair_commit_ref or item.get("repair_commit_ref"),
                actor_person_id=verified_person_id,
                identity=identity,
                conn=c,
                commit=False,
            )
        else:
            item = wi.claim_complete(
                work_item_id,
                verified_person_id=verified_person_id,
                outcome=outcome,
                identity=identity,
                conn=c,
                commit=False,
            )

        if commit:
            c.commit()
        final = wi.get_work_item(work_item_id, conn=c) or item
        return {
            "ok": True,
            "work_item": final,
            "status_label": status_label(final.get("status")),
            "verified": False,
            "repair_item": repair_out,
            "retest_item": retest_out,
            "staff_ready": False,
            "human_commissioned": False,
            "system_percent_unchanged": True,
        }
    finally:
        if own:
            c.close()


def verify_commissioning(
    work_item_id: str,
    *,
    verifier_person_id: str,
    result: str,
    note: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """Owner/work.verify only. PASS→VERIFIED HUMAN PASS. REJECT→person. FAIL→repair."""
    res = (result or "").strip().upper()
    if res not in {"PASS", "FAIL", "REJECT", "RETURN"}:
        raise MyWorkError(
            "result must be PASS, FAIL, or REJECT",
            code="invalid_result",
        )
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise MyWorkError("Work item not found.", code="not_found", http_status=404)
        if item["status"] not in {"AWAITING_VERIFY", "COMPLETED"}:
            raise MyWorkError(
                "Only AWAITING VERIFY (or DONE) commissioning tasks can be verified.",
                code="not_awaiting",
            )
        entity = str(item["owning_entity_id"])
        allowed = _rbac.evaluate(
            verifier_person_id, "work.verify", {"entity_id": entity}, conn=c
        ).get("allowed")
        if not allowed and verifier_person_id != "PERS-MATT":
            raise MyWorkError("work.verify denied", code="rbac_denied", http_status=403)
        ts = wi.now_utc_iso()
        repair = None
        if res == "PASS":
            if item["status"] == "COMPLETED":
                # Allow verify from COMPLETED for non-loop legacy path.
                updated = wi.verify_work_item(
                    work_item_id,
                    verified_person_id=verifier_person_id,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            else:
                updated = wi.verify_work_item(
                    work_item_id,
                    verified_person_id=verifier_person_id,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            c.execute(
                """
                UPDATE core_work_items
                SET commissioning_result='PASS',
                    outcome=COALESCE(?, outcome),
                    what_happens_next='VERIFIED HUMAN PASS recorded. Not staff_ready. Not human_commissioned. SYSTEM % unchanged.',
                    updated_at=?
                WHERE work_item_id=?
                """,
                ((note or "VERIFIED HUMAN PASS").strip(), ts, work_item_id),
            )
        elif res in {"REJECT", "RETURN"}:
            c.execute(
                """
                UPDATE core_work_items
                SET status='RETURNED',
                    outcome=?,
                    what_happens_next=?,
                    updated_at=?
                WHERE work_item_id=?
                """,
                (
                    (note or "Needs better evidence").strip(),
                    f"Returned for better evidence: {(note or 'please attach clearer proof').strip()}",
                    ts,
                    work_item_id,
                ),
            )
            updated = wi.get_work_item(work_item_id, conn=c)
        else:
            c.execute(
                """
                UPDATE core_work_items
                SET commissioning_result='FAIL',
                    status='COMPLETED',
                    outcome=?,
                    what_happens_next='Verifier FAIL — engineering repair issued.',
                    updated_at=?
                WHERE work_item_id=?
                """,
                ((note or "Verifier FAIL").strip(), ts, work_item_id),
            )
            updated = wi.get_work_item(work_item_id, conn=c)
            repair = create_engineering_repair(
                updated or item,
                note=note,
                conn=c,
                commit=False,
            )
        _audit.safe_record(
            action="work.commissioning.verify",
            result="SUCCEEDED",
            source="universal_my_work",
            actor_type="PERSON",
            verified_person_id=verifier_person_id,
            actor_person_id=verifier_person_id,
            entity_id=entity,
            resource_type="work_item",
            resource_id=work_item_id,
            metadata={
                "commissioning_result": res,
                "capability": item.get("commissioning_capability_id"),
                "staff_ready": False,
                "human_commissioned": False,
            },
            conn=c,
            commit=False,
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "work_item": wi.get_work_item(work_item_id, conn=c) or updated,
            "commissioning_result": res,
            "repair_item": repair,
            "staff_ready": False,
            "human_commissioned": False,
            "system_percent_unchanged": True,
        }
    finally:
        if own:
            c.close()


def execution_report(
    *,
    person_id: str | None = None,
    period: str = "week",
    viewer_person_id: str,
    conn=None,
) -> dict[str, Any]:
    """Owner + authorised managers. Plain factual counts. No AI judgement labels."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        if not _viewer_may_report(c, viewer_person_id):
            raise MyWorkError("Execution report denied.", code="forbidden", http_status=403)
        days = {"day": 1, "week": 7, "month": 30}.get((period or "week").lower(), 7)
        since = (datetime.now(TZ8) - timedelta(days=days)).isoformat()
        people = [person_id] if person_id else [
            r["person_id"] for r in list_work_receivers(c)
        ]
        people = list(dict.fromkeys(people))
        rows_out = []
        for pid in people:
            name = _person_name(c, pid)
            assigned = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR accountable_person_id=?)
                  AND created_at >= ?
                """,
                (pid, pid, since),
            ).fetchone()[0]
            accepted = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=?)
                  AND started_at IS NOT NULL AND started_at >= ?
                """,
                (pid, pid, since),
            ).fetchone()[0]
            completed = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=?)
                  AND completed_at IS NOT NULL AND completed_at >= ?
                """,
                (pid, pid, since),
            ).fetchone()[0]
            verified = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR accountable_person_id=?)
                  AND verified_at IS NOT NULL AND verified_at >= ?
                """,
                (pid, pid, since),
            ).fetchone()[0]
            overdue = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=?)
                  AND status IN ('OPEN','IN_PROGRESS','BLOCKED','WAITING','RETURNED')
                  AND due_at IS NOT NULL AND due_at < ?
                """,
                (pid, pid, now_iso()),
            ).fetchone()[0]
            blocked = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=?)
                  AND status='BLOCKED'
                """,
                (pid, pid),
            ).fetchone()[0]
            returned = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=?)
                  AND status='RETURNED'
                """,
                (pid, pid),
            ).fetchone()[0]
            delegated = c.execute(
                """
                SELECT COUNT(*) FROM core_work_delegations
                WHERE from_person_id=? AND offered_at >= ?
                """,
                (pid, since),
            ).fetchone()[0]
            personally = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE executor_person_id=?
                  AND completed_at IS NOT NULL AND completed_at >= ?
                  AND (accountable_person_id IS NULL OR accountable_person_id = executor_person_id
                       OR accountable_person_id = ?)
                """,
                (pid, since, pid),
            ).fetchone()[0]
            # Personally executed ≈ completed where executor is this person and no onward delegation after start.
            with_evidence = c.execute(
                """
                SELECT COUNT(DISTINCT w.work_item_id)
                FROM core_work_items w
                JOIN core_work_evidence_files f ON f.work_item_id = w.work_item_id
                WHERE (w.owner_person_id=? OR w.executor_person_id=?)
                  AND w.completed_at IS NOT NULL AND w.completed_at >= ?
                """,
                (pid, pid, since),
            ).fetchone()[0]
            unresolved = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=? OR accountable_person_id=?)
                  AND status IN ('OPEN','IN_PROGRESS','BLOCKED','WAITING','RETURNED','REASSIGNED')
                """,
                (pid, pid, pid),
            ).fetchone()[0]
            avg_row = c.execute(
                """
                SELECT AVG(
                  (julianday(completed_at) - julianday(COALESCE(started_at, created_at))) * 24.0
                ) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=?)
                  AND completed_at IS NOT NULL AND completed_at >= ?
                """,
                (pid, pid, since),
            ).fetchone()[0]
            avg_hours = round(float(avg_row), 2) if avg_row is not None else None
            on_time = c.execute(
                """
                SELECT COUNT(*) FROM core_work_items
                WHERE (owner_person_id=? OR executor_person_id=?)
                  AND completed_at IS NOT NULL AND completed_at >= ?
                  AND (due_at IS NULL OR completed_at <= due_at)
                """,
                (pid, pid, since),
            ).fetchone()[0]
            sentence = (
                f"Assigned {int(assigned)}; delegated {int(delegated)}; "
                f"personally completed {int(personally)}; verified {int(verified)}."
            )
            rows_out.append(
                {
                    "person_id": pid,
                    "name": name,
                    "assigned": int(assigned),
                    "accepted": int(accepted),
                    "completed": int(completed),
                    "verified": int(verified),
                    "on_time": int(on_time),
                    "overdue": int(overdue),
                    "blocked": int(blocked),
                    "returned": int(returned),
                    "evidence_completeness_completed_with_file": int(with_evidence),
                    "average_completion_hours": avg_hours,
                    "delegated_onward": int(delegated),
                    "personally_executed": int(personally),
                    "unresolved": int(unresolved),
                    "sentence": sentence,
                }
            )
        return {
            "ok": True,
            "bound": BOUND,
            "period": period,
            "since": since,
            "people": rows_out,
            "staff_ready": False,
            "human_commissioned": False,
            "ai_judgement": False,
        }
    finally:
        if own:
            c.close()


def _viewer_may_report(conn, person_id: str) -> bool:
    row = conn.execute(
        """
        SELECT r.role_type, r.display_name, r.role_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_roles r ON r.role_id = p.role_id
        WHERE a.person_id = ? AND a.status = 'ACTIVE' AND a.end_at IS NULL
        """,
        (person_id,),
    ).fetchall()
    for r in row:
        label = str(r["display_name"] or "").lower()
        kind = str(r["role_type"] or "").upper()
        rid = str(r["role_id"] or "")
        if kind == "EXECUTIVE" and "owner" in label:
            return True
        if rid.endswith("-GM") or "general manager" in label:
            return True
        if "creative director" in label or rid.endswith("CREATIVE-DIRECTOR"):
            return True
        if "f&b" in label and "lead" in label:
            return True
    return False


def war_room_commissioning_queue(conn=None) -> dict[str, Any]:
    """Real Work Items replace OPSFIX-3 passive test cards."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT * FROM core_work_items
            WHERE origin = 'commissioning'
              AND status NOT IN ('CANCELLED', 'VERIFIED')
              AND COALESCE(routing_state, '') NOT IN (?, ?)
            ORDER BY priority ASC, created_at ASC
            """,
            (ROUTING_HELD, ROUTING_HELD_CF),
        ).fetchall()
        queue = [enrich_card(c, dict(r)) for r in rows]
        return {
            "ok": True,
            "title": "GIVE THIS TO A HUMAN NOW",
            "queue": queue,
            "human_test_cards": [],
            "source": "core_work_items",
            "feedback_href": "/progress#commissioning",
            "staff_ready": False,
            "human_commissioned": False,
            "note": (
                "Real commissioning Work Items. DONE creates evidence. "
                "VERIFIED HUMAN PASS is a separate verification step. "
                "Nobody becomes staff_ready or human_commissioned by code."
            ),
        }
    finally:
        if own:
            c.close()


def _create_commission_task(
    conn,
    *,
    title: str,
    owner_person_id: str,
    owner_assignment_id: str | None,
    entity_id: str,
    capability_id: str,
    instructions: str,
    evidence_required: str,
    href_hint: str,
    scope_label: str,
    priority: int = 2,
) -> dict[str, Any]:
    existing = conn.execute(
        """
        SELECT work_item_id FROM core_work_items
        WHERE origin='commissioning'
          AND commissioning_capability_id=?
          AND owner_person_id=?
          AND status NOT IN ('CANCELLED')
        """,
        (capability_id, owner_person_id),
    ).fetchone()
    if existing:
        return wi.get_work_item(str(existing[0]), conn=conn) or {}
    item = wi.create_work_item(
        title=title,
        description=instructions,
        owning_entity_id=entity_id,
        work_type="AUDIT_FINDING",
        source_type="SYSTEM",
        created_by_actor_type="SYSTEM",
        owner_person_id=owner_person_id,
        owner_org_assignment_id=owner_assignment_id,
        source_id=f"commissioning:{capability_id}",
        priority=priority,
        conn=conn,
        commit=False,
    )
    ts = wi.now_utc_iso()
    routing_state = None
    routing_reason = None
    if capability_id in {
        "COMM-HARIYANTO-RECIPE-BUILDER",
        "COMM-AP-SOD-PREPARE",
        "COMM-AP-SOD-SUBMIT",
    }:
        routing_state = ROUTING_HELD_CF
        if capability_id.startswith("COMM-AP-"):
            routing_reason = (
                "activate when Peaches verifies zenitalfathan@gmail.com is in Beta Cloudflare "
                "(Person/AuthIdentity + Accounts Payable Assignment ready; do not activate early)"
            )
        else:
            routing_reason = (
                "activate when Matt confirms carolus.haryanto@gmail.com is in Beta Cloudflare "
                "(Peaches activates only after Person/AuthIdentity, Head Chef Assignment/Scope, "
                "real Recipe Builder and all server-side allow/deny checks pass)"
            )
    conn.execute(
        """
        UPDATE core_work_items
        SET accountable_person_id = ?,
            executor_person_id = ?,
            requested_by_person_id = 'PERS-MATT',
            origin = 'commissioning',
            instructions = ?,
            evidence_required = ?,
            checklist_json = ?,
            scope_label = ?,
            commissioning_capability_id = ?,
            what_happens_next = ?,
            routing_state = COALESCE(?, routing_state),
            routing_reason = COALESCE(?, routing_reason),
            updated_at = ?
        WHERE work_item_id = ?
        """,
        (
            owner_person_id,
            owner_person_id,
            instructions,
            evidence_required,
            json.dumps([{"step": instructions, "href": href_hint}]),
            scope_label,
            capability_id,
            "Open the link, follow the steps, attach evidence, choose PASS or FAIL, then DONE. Verification is separate."
            if routing_state is None
            else "HELD until Peaches activates after allow/deny pass. Not visible as active My Work.",
            routing_state,
            routing_reason,
            ts,
            item["work_item_id"],
        ),
    )
    return wi.get_work_item(item["work_item_id"], conn=conn) or item


def _commissioning_specs() -> list[tuple]:
    """Plain employee steps — no Matt required to explain the test. Ids kept via capability."""
    return [
        # Devi
        ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-UMA-TODAY",
         "Commission Uma Today",
         "1. Open Uma Today (link below).\n"
         "2. Look at today's bills and sales.\n"
         "3. Take a phone screenshot that shows the real numbers.\n"
         "4. Attach the screenshot.\n"
         "5. Choose PASS if it looks right, or FAIL if something is wrong — and say what.\n"
         "6. Tap DONE.",
         "Phone screenshot of Uma Today", "/bzg/uma-blu", "BZG · Uma Blu"),
        ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-RECIPES",
         "Commission Recipes",
         "1. Open Recipes (link below).\n"
         "2. Open one real recipe.\n"
         "3. Take a screenshot of that recipe.\n"
         "4. Attach it, choose PASS or FAIL, tap DONE.",
         "Screenshot of a real recipe", "/bzg/uma-blu#recipes", "BZG · Uma Blu"),
        ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-PURCHASING",
         "Commission Purchasing",
         "1. Open Purchasing (link below).\n"
         "2. Confirm you see real purchase rows (not an empty demo).\n"
         "3. Screenshot the list, attach it, choose PASS or FAIL, tap DONE.",
         "Screenshot of purchasing queue", "/bzg/uma-blu#purchasing", "BZG · Uma Blu"),
        ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-ESB-SALES",
         "Commission ESB sales view",
         "1. Open Sales for Uma Blu (link below).\n"
         "2. Find a real day with totals.\n"
         "3. Screenshot it, attach it, choose PASS or FAIL, tap DONE.",
         "Screenshot of ESB sales", "/bzg/uma-blu#sales", "BZG · Uma Blu"),
        # Hariyanto — created HELD by migrate_headchef1; kept here for idempotent re-issue
        ("PERS-HARIYANTO", "ROLE-BZG-HEAD-CHEF", "ENT-BZG", "COMM-HARIYANTO-RECIPE-BUILDER",
         "Commission Recipe Builder (Hariyanto)",
         "1. Open Recipe Builder (link below).\n"
         "2. Check one real recipe's cost (real purchase/card data, or 'cost missing').\n"
         "3. Create or edit one recipe.\n"
         "4. Attach evidence, choose PASS or FAIL, tap DONE.\n"
         "Note: activate when Matt confirms carolus.haryanto@gmail.com is in Beta Cloudflare.",
         "Screenshot of Recipe Builder with real cost or cost missing; create/edit evidence",
         "/bzg/recipe-builder", "BZG · Head Chef · Recipe Builder"),
        ("PERS-DEVI", "ROLE-BZG-CLOSER", "ENT-BZG", "COMM-DEVI-DAILY-CLOSE",
         "Commission Daily Close workflow (tolerance UNSET)",
         "1. Open Daily Close (link below).\n"
         "2. Cash-variance tolerance is UNSET — do not invent a number.\n"
         "3. Run only the parts that do not need a tolerance number.\n"
         "4. Screenshot the screen showing UNSET / blocked variance, attach it, choose PASS or FAIL, tap DONE.",
         "Screenshot of Daily Close with UNSET policy control visible",
         "/uma-blu-close", "BZG · Uma Blu · Closer"),
        # Zayen
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-COMMAND",
         "Commission Atrium Command Centre",
         "1. Open Atrium Finance Command Centre (link below).\n"
         "2. Confirm the page loads with real finance tiles.\n"
         "3. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Screenshot of Command Centre", "/amg/finance", "AMG · Atrium Finance"),
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-JOURNAL",
         "Commission Journal workbench",
         "1. Open Journal workbench (link below).\n"
         "2. Confirm DRAFT→VALIDATED→SUBMITTED→APPROVED→POSTED workflow buttons match your seat.\n"
         "3. Do not approve or post a journal you prepared (SoD).\n"
         "4. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Screenshot of Journal workbench", "/amg/finance#workbench", "AMG · Atrium Finance"),
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-LEDGER",
         "Commission Ledger",
         "1. Open General Ledger (link below).\n"
         "2. Confirm amounts show in IDR.\n"
         "3. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Screenshot of Ledger", "/amg/finance#ledger", "AMG · Atrium Finance"),
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-TRIAL",
         "Commission Trial Balance",
         "1. Open Trial Balance (link below).\n"
         "2. Screenshot the balance view, attach, choose PASS or FAIL, tap DONE.",
         "Screenshot of Trial Balance", "/amg/finance#trial", "AMG · Atrium Finance"),
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-ARAP",
         "Commission AR/AP",
         "1. Open AR and AP (link below).\n"
         "2. Screenshot both views (or one clear photo of each).\n"
         "3. Attach, choose PASS or FAIL, tap DONE.",
         "Screenshots of AR and AP", "/amg/finance", "AMG · Atrium Finance"),
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-INVENTORY",
         "Commission Inventory",
         "1. Open Inventory (link below).\n"
         "2. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Screenshot of Inventory", "/amg/finance#inventory", "AMG · Atrium Finance"),
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-REPORTS",
         "Commission Reports",
         "1. Open financial reports (link below).\n"
         "2. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Screenshot of Reports", "/amg/finance#reports", "AMG · Atrium Finance"),
        ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-CONTROLS",
         "Confirm SoD + money controls",
         "1. Open Atrium Finance (link below).\n"
         "2. Confirm you can approve/post journals prepared by someone else, and cannot approve/post your own.\n"
         "3. Confirm pay and bank-detail change are denied.\n"
         "4. Attach evidence, choose PASS or FAIL, tap DONE.",
         "Evidence of SoD allow/deny + denied pay/bank", "/amg/finance", "AMG · Atrium Finance"),
        # Amanda
        ("PERS-AMANDA", "ROLE-GGV-FINANCE-OPERATOR", "ENT-GGV", "COMM-AMANDA-064A-066A",
         "Verify GGV invoices 064A–066A",
         "1. Open GGV Finance (link below).\n"
         "2. Find invoices 064A, 065A, and 066A.\n"
         "3. Check each against the source file.\n"
         "4. Attach notes or screenshots, choose PASS or FAIL, tap DONE.",
         "Verification notes for 064A–066A", "/ggv/finance", "GGV · Finance"),
        ("PERS-AMANDA", "ROLE-GGV-FINANCE-OPERATOR", "ENT-GGV", "COMM-AMANDA-067A",
         "Next genuine invoice through draft (067A if due)",
         "1. Open GGV Finance (link below).\n"
         "2. Only if a real invoice is due: prepare draft 067A. Do not invent one.\n"
         "3. Attach draft evidence, or a note that none is due.\n"
         "4. Choose PASS or FAIL, tap DONE.",
         "Draft invoice 067A or note that none is due", "/ggv/finance", "GGV · Finance"),
        # Haikal
        ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-MYWORK",
         "Commission My Work",
         "1. Open My Work on your phone (link below).\n"
         "2. Confirm you see TODAY, DO THIS NEXT, NEEDS ATTENTION, WAITING, COMPLETED.\n"
         "3. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Phone screenshot of My Work", "/my-work", "GGV · Content"),
        ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-PLAN",
         "Commission Content Plan",
         "1. Open Content Plan (link below).\n"
         "2. Confirm the header fits on a phone-width screen.\n"
         "3. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Phone screenshot of Content Plan", "/content-2.0#plan", "GGV · Content"),
        ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-LIBRARY",
         "Commission Library pagination/preview/download/upload",
         "1. Open the library (link below).\n"
         "2. Use the page numbers, preview one file, download one file, open upload.\n"
         "3. Attach screenshots of those steps, choose PASS or FAIL, tap DONE.",
         "Screenshots of pagination, preview, download, upload", "/content-2.0#library", "GGV · Content"),
        ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-HABITAT",
         "Real Habitat work from My Work",
         "1. Open My Work (link below).\n"
         "2. Open a real Habitat plan from your list.\n"
         "3. Note the next production step.\n"
         "4. Screenshot, attach, choose PASS or FAIL, tap DONE.",
         "Screenshot of Habitat plan from My Work", "/my-work", "GGV · Content"),
    ]


def _asg(conn, person_id: str, role_id: str | None = None) -> str | None:
    if role_id:
        row = conn.execute(
            """
            SELECT a.assignment_id FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE a.person_id=? AND p.role_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
            ORDER BY a.is_primary DESC LIMIT 1
            """,
            (person_id, role_id),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT assignment_id FROM org_assignments
            WHERE person_id=? AND status='ACTIVE' AND end_at IS NULL
            ORDER BY is_primary DESC LIMIT 1
            """,
            (person_id,),
        ).fetchone()
    return str(row[0]) if row else None


def issue_commissioning_tasks(*, conn=None, commit: bool = True) -> dict[str, Any]:
    own = conn is None
    c = conn or wi.db_connect()
    created: list[str] = []
    try:
        specs = list(_commissioning_specs())
        for pid, role in (
            ("PERS-MISA", "ROLE-GGV-CREATIVE-DIRECTOR"),
            ("PERS-ZARAH", "ROLE-GGV-CREATIVE-DIRECTOR"),
            ("PERS-FRAIL", "ROLE-GGV-CREATIVE-DIRECTOR"),
            ("PERS-YUDI", "ROLE-CONTENT-CREATOR"),
            ("PERS-GERY", "ROLE-CONTENT-CREATOR"),
            ("PERS-ALAM", "ROLE-CONTENT-CREATOR"),
            ("PERS-TJ", "ROLE-CONTENT-CREATOR"),
            ("PERS-NATA", "ROLE-CONTENT-CREATOR"),
            ("PERS-RAPP", "ROLE-CONTENT-CREATOR"),
        ):
            specs.append(
                (
                    pid,
                    role,
                    "ENT-GGV",
                    f"COMM-{pid.split('-')[1]}-MYWORK",
                    "Commission My Work for your seat",
                    "1. Open My Work (link below).\n"
                    "2. Confirm work for your seat appears.\n"
                    "3. Screenshot, attach, choose PASS or FAIL, tap DONE.",
                    "Screenshot of My Work",
                    "/my-work",
                    "GGV · Content",
                )
            )

        for pid, role, entity, cap, title, instr, evid, href, scope in specs:
            asg = _asg(c, pid, role) or _asg(c, pid)
            if not asg:
                continue
            item = _create_commission_task(
                c,
                title=title,
                owner_person_id=pid,
                owner_assignment_id=asg,
                entity_id=entity,
                capability_id=cap,
                instructions=instr,
                evidence_required=evid,
                href_hint=href,
                scope_label=scope,
            )
            if item.get("work_item_id"):
                created.append(item["work_item_id"])
        if commit:
            c.commit()
        return {"issued": len(created), "work_item_ids": created}
    finally:
        if own:
            c.close()


def import_legacy_migration(
    *,
    proposal_path: Path | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    path = Path(proposal_path) if proposal_path else LEGACY_PROPOSAL
    own = conn is None
    c = conn or wi.db_connect()
    counts = {
        "proposed": 0,
        "imported": 0,
        "duplicate_linked": 0,
        "unknown_review": 0,
        "skipped_obsolete": 0,
        "skipped_existing": 0,
        "failed": 0,
    }
    try:
        if not path.exists():
            return {**counts, "status": "NO_PROPOSAL"}
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items") if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []
        counts["proposed"] = len(items)
        for row in items:
            cls = str(row.get("classification") or "")
            if "OBSOLETE" in cls:
                counts["skipped_obsolete"] += 1
                continue
            if "DUPLICATE" in cls:
                counts["duplicate_linked"] += 1
                # Link-only: create WAITING marker with parent note, no reactivation of obsolete.
                pw = row.get("proposed_work_item") or {}
                src = str(pw.get("source_id") or "")
                if src:
                    exists = c.execute(
                        "SELECT work_item_id FROM core_work_items WHERE source_id=?",
                        (src,),
                    ).fetchone()
                    if exists:
                        counts["skipped_existing"] += 1
                        continue
                continue
            pw = row.get("proposed_work_item") or {}
            if not isinstance(pw, dict):
                counts["failed"] += 1
                continue
            src = str(pw.get("source_id") or "").strip()
            if src:
                exists = c.execute(
                    "SELECT work_item_id FROM core_work_items WHERE source_id=?",
                    (src,),
                ).fetchone()
                if exists:
                    counts["skipped_existing"] += 1
                    continue
            owner = (pw.get("owner_person_id") or "").strip() or None
            entity = (pw.get("owning_entity_id") or "ENT-GGV").strip()
            role_guess = str(row.get("proposed_role") or "")
            unclear = (not owner) or "UNKNOWN" in cls.upper() or not role_guess
            title = str(pw.get("title") or "Legacy work")
            if unclear and not owner:
                owner = "PERS-MATT"
                title = f"UNKNOWN — REVIEW: {title}"
                counts["unknown_review"] += 1
            asg = _asg(c, owner) if owner else None
            # Provenance line
            import_label = (
                pw.get("import_label")
                or f"Imported from {src or 'legacy'}, {row.get('candidate_id')}, {data.get('as_of')}"
            )
            try:
                item = wi.create_work_item(
                    title=title[:240],
                    description=str(pw.get("description") or import_label),
                    owning_entity_id=entity,
                    work_type=str(pw.get("work_type") or "GENERAL"),
                    source_type="EXTERNAL",
                    created_by_actor_type="SYSTEM",
                    owner_person_id=owner,
                    owner_org_assignment_id=asg if asg and owner else None,
                    source_id=src or f"legacy:{row.get('candidate_id')}",
                    priority=int(pw.get("priority") or 3),
                    due_at=pw.get("due_at"),
                    conn=c,
                    commit=False,
                )
                c.execute(
                    """
                    UPDATE core_work_items
                    SET origin='legacy',
                        import_label=?,
                        accountable_person_id=?,
                        executor_person_id=?,
                        requested_by_person_id='PERS-MATT',
                        scope_label=?,
                        what_happens_next='Imported legacy work. Review and act, or cancel with reason.',
                        updated_at=?
                    WHERE work_item_id=?
                    """,
                    (
                        str(import_label)[:500],
                        owner,
                        owner,
                        role_guess or entity,
                        wi.now_utc_iso(),
                        item["work_item_id"],
                    ),
                )
                counts["imported"] += 1
            except Exception:
                counts["failed"] += 1
        # Flip proposal flag on disk copy receipt only — keep proposal file as history.
        if commit:
            c.commit()
        return {**counts, "status": "IMPORTED", "proposal_path": str(path)}
    finally:
        if own:
            c.close()


def write_clickup_cut_line(path: Path) -> dict[str, Any]:
    """Documented cut-line: no new ClickUp deps/writes from Wolf; history readable."""
    record = {
        "brief": "MYWORK-1",
        "as_of": now_iso(),
        "status": "CUT_LINE_RECORDED",
        "wolf_clickup_writes": False,
        "wolf_new_clickup_dependencies": False,
        "history_readable": True,
        "nothing_deleted_in_clickup": True,
        "live_open_inbox_ids_as_of_legacy1": [
            "86exu7c40",
            "86exuxtgv",
            "86exvqrw6",
            "86exx1kxq",
            "86exzzn5a",
            "z8wf5rf9ej",
            "z8wf5rfh2a",
            "z8wf5rfjc9",
            "z8wf5rfptv",
            "z8wf5rfqa8",
        ],
        "note": (
            "ClickUp remains readable history. Wolf My Work is now the create path for "
            "new staff work. Do not delete ClickUp archive. Bridge may stay read-only."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def fingerprint_work_state(conn=None) -> str:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        row = c.execute(
            """
            SELECT COUNT(*), COALESCE(MAX(updated_at), ''),
                   COALESCE(SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN status='VERIFIED' THEN 1 ELSE 0 END), 0)
            FROM core_work_items
            """
        ).fetchone()
        raw = f"{row[0]}|{row[1]}|{row[2]}|{row[3]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    finally:
        if own:
            c.close()


def mark_derived_views_stale(*, conn=None, commit: bool = True) -> None:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        fp = fingerprint_work_state(c)
        ts = wi.now_utc_iso()
        for view_id in (
            "my-work",
            "team-dashboard",
            "department-dashboard",
            "company-dashboard",
            "owner-command",
            "owner-command-exceptions",
            "war-room",
            "war-room-commissioning",
            "execution-report",
        ):
            c.execute(
                """
                INSERT INTO core_derived_view_stamps (view_id, source_fingerprint, refreshed_at, status)
                VALUES (?, ?, ?, 'STALE')
                ON CONFLICT(view_id) DO UPDATE SET
                  source_fingerprint=excluded.source_fingerprint,
                  refreshed_at=excluded.refreshed_at,
                  status='STALE'
                """,
                (view_id, fp, ts),
            )
        if commit:
            c.commit()
    finally:
        if own:
            c.close()


def refresh_derived_view(view_id: str, *, conn=None, commit: bool = True) -> dict[str, Any]:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        fp = fingerprint_work_state(c)
        ts = wi.now_utc_iso()
        c.execute(
            """
            INSERT INTO core_derived_view_stamps (view_id, source_fingerprint, refreshed_at, status)
            VALUES (?, ?, ?, 'LIVE')
            ON CONFLICT(view_id) DO UPDATE SET
              source_fingerprint=excluded.source_fingerprint,
              refreshed_at=excluded.refreshed_at,
              status='LIVE'
            """,
            (view_id, fp, ts),
        )
        if commit:
            c.commit()
        return {"view_id": view_id, "status": "LIVE", "source_fingerprint": fp, "refreshed_at": ts}
    finally:
        if own:
            c.close()


def derived_view_status(view_id: str, *, conn=None) -> dict[str, Any]:
    own = conn is None
    c = conn or wi.db_connect()
    try:
        row = c.execute(
            "SELECT * FROM core_derived_view_stamps WHERE view_id=?",
            (view_id,),
        ).fetchone()
        current = fingerprint_work_state(c)
        if not row:
            return {"view_id": view_id, "status": "STALE", "source_fingerprint": current}
        status = "LIVE" if row["source_fingerprint"] == current and row["status"] == "LIVE" else "STALE"
        return {
            "view_id": view_id,
            "status": status,
            "source_fingerprint": current,
            "stored_fingerprint": row["source_fingerprint"],
            "refreshed_at": row["refreshed_at"],
        }
    finally:
        if own:
            c.close()


def owner_work_exceptions(conn=None) -> list[dict[str, Any]]:
    """Overwatch: commissioning FAILs, overdue, NEEDS_ROUTING, owner-authority, AWAITING_VERIFY.

    Routine OPEN work lists are not included.
    """
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT * FROM core_work_items
            WHERE status != 'CANCELLED'
              AND (
                commissioning_result = 'FAIL'
                OR origin = 'commissioning-repair'
                OR routing_state = ?
                OR status = 'AWAITING_VERIFY'
                OR status IN ('BLOCKED', 'RETURNED')
                OR (
                    status IN ('OPEN','IN_PROGRESS','WAITING')
                    AND due_at IS NOT NULL AND due_at < ?
                )
                OR (
                    owner_person_id = 'PERS-MATT'
                    AND origin = 'legacy'
                    AND COALESCE(routing_state, '') != ?
                    AND (
                      lower(title) LIKE '%decide%'
                      OR lower(title) LIKE '%approv%'
                      OR lower(title) LIKE '%payment%'
                      OR lower(title) LIKE '%bank%'
                      OR lower(title) LIKE '%credential%'
                      OR lower(import_label) LIKE '%owner%'
                    )
                )
              )
            ORDER BY priority ASC, due_at IS NULL, due_at ASC
            LIMIT 60
            """,
            (ROUTING_NEEDS, now_iso(), ROUTING_NEEDS),
        ).fetchall()
        return [enrich_card(c, dict(r)) for r in rows]
    finally:
        if own:
            c.close()


def refresh_commissioning_copy(*, conn=None, commit: bool = True) -> dict[str, Any]:
    """Rewrite instructions on existing commissioning items (keep ids)."""
    own = conn is None
    c = conn or wi.db_connect()
    updated = 0
    try:
        specs = list(_commissioning_specs())
        for pid, role in (
            ("PERS-MISA", "ROLE-GGV-CREATIVE-DIRECTOR"),
            ("PERS-ZARAH", "ROLE-GGV-CREATIVE-DIRECTOR"),
            ("PERS-FRAIL", "ROLE-GGV-CREATIVE-DIRECTOR"),
            ("PERS-YUDI", "ROLE-CONTENT-CREATOR"),
            ("PERS-GERY", "ROLE-CONTENT-CREATOR"),
            ("PERS-ALAM", "ROLE-CONTENT-CREATOR"),
            ("PERS-TJ", "ROLE-CONTENT-CREATOR"),
            ("PERS-NATA", "ROLE-CONTENT-CREATOR"),
            ("PERS-RAPP", "ROLE-CONTENT-CREATOR"),
        ):
            specs.append(
                (
                    pid,
                    role,
                    "ENT-GGV",
                    f"COMM-{pid.split('-')[1]}-MYWORK",
                    "Commission My Work for your seat",
                    "1. Open My Work (link below).\n"
                    "2. Confirm work for your seat appears.\n"
                    "3. Screenshot, attach, choose PASS or FAIL, tap DONE.",
                    "Screenshot of My Work",
                    "/my-work",
                    "GGV · Content",
                )
            )
        by_cap = {s[3]: s for s in specs}
        rows = c.execute(
            """
            SELECT work_item_id, commissioning_capability_id FROM core_work_items
            WHERE origin='commissioning' AND status NOT IN ('CANCELLED','VERIFIED')
            """
        ).fetchall()
        ts = wi.now_utc_iso()
        for row in rows:
            cap = row["commissioning_capability_id"]
            spec = by_cap.get(cap)
            if not spec:
                continue
            _pid, _role, _ent, _cap, title, instr, evid, href, scope = spec
            c.execute(
                """
                UPDATE core_work_items
                SET title=?,
                    description=?,
                    instructions=?,
                    evidence_required=?,
                    checklist_json=?,
                    scope_label=?,
                    what_happens_next=?,
                    updated_at=?
                WHERE work_item_id=?
                """,
                (
                    title,
                    instr,
                    instr,
                    evid,
                    json.dumps([{"step": instr.split("\n")[0], "href": href}]),
                    scope,
                    "Open the link, follow the steps, attach evidence, choose PASS or FAIL, then DONE.",
                    ts,
                    row["work_item_id"],
                ),
            )
            updated += 1
        if commit:
            c.commit()
        return {"updated": updated}
    finally:
        if own:
            c.close()


def _person_has_active_assignment_for_entity(
    conn, person_id: str, entity_id: str
) -> bool:
    if not person_id or not entity_id:
        return False
    asg = _asg(conn, person_id)
    if not asg:
        return False
    return wi.person_can_see_entity(person_id, entity_id, conn=conn)


def _needs_owner_authority(title: str, import_label: str, classification: str) -> bool:
    blob = f"{title} {import_label} {classification}".lower()
    return any(h in blob for h in _OWNER_AUTHORITY_HINTS)


def audit_legacy_routing(*, conn=None, commit: bool = True) -> dict[str, Any]:
    """Re-check legacy owners against provenance. Move unclear → NEEDS_ROUTING."""
    own = conn is None
    c = conn or wi.db_connect()
    before: dict[str, int] = {}
    after: dict[str, int] = {}
    moved: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    try:
        proposal = {}
        candidates_by_id: dict[str, dict] = {}
        source_by_legacy: dict[str, dict] = {}
        if LEGACY_PROPOSAL.exists():
            proposal = json.loads(LEGACY_PROPOSAL.read_text(encoding="utf-8"))
        if LEGACY_CANDIDATES.exists():
            cand_doc = json.loads(LEGACY_CANDIDATES.read_text(encoding="utf-8"))
            for cand in cand_doc.get("candidates") or []:
                if isinstance(cand, dict) and cand.get("candidate_id"):
                    candidates_by_id[str(cand["candidate_id"])] = cand
        for row in proposal.get("items") or []:
            if not isinstance(row, dict):
                continue
            pw = row.get("proposed_work_item") or {}
            src = str(pw.get("source_id") or "")
            if src:
                source_by_legacy[src] = {
                    "candidate_id": row.get("candidate_id"),
                    "classification": row.get("classification"),
                    "proposed_role": row.get("proposed_role"),
                    "assignee_in_source": (
                        candidates_by_id.get(str(row.get("candidate_id") or ""), {}).get(
                            "assignee_in_source"
                        )
                    ),
                    "source_system": (
                        candidates_by_id.get(str(row.get("candidate_id") or ""), {}).get(
                            "source_system"
                        )
                    ),
                    "proposed_owner": pw.get("owner_person_id"),
                }

        rows = c.execute(
            """
            SELECT * FROM core_work_items
            WHERE origin='legacy' AND status NOT IN ('CANCELLED')
            """
        ).fetchall()
        for r in rows:
            owner = r["owner_person_id"] or "NONE"
            before[owner] = before.get(owner, 0) + 1

        ts = wi.now_utc_iso()
        for r in rows:
            item = dict(r)
            if str(item.get("import_label") or "").upper().find("OBSOLETE") >= 0:
                after[item.get("owner_person_id") or "NONE"] = (
                    after.get(item.get("owner_person_id") or "NONE", 0) + 1
                )
                continue
            src = str(item.get("source_id") or "")
            meta = source_by_legacy.get(src) or {}
            assignee_raw = (meta.get("assignee_in_source") or "").strip()
            mapped = _SOURCE_ASSIGNEE_MAP.get(assignee_raw.lower()) if assignee_raw else None
            entity = str(item.get("owning_entity_id") or "")
            title = str(item.get("title") or "")
            reason = None
            keep_owner = None

            if mapped and _person_has_active_assignment_for_entity(c, mapped, entity):
                if mapped == "PERS-MATT":
                    if _needs_owner_authority(
                        title,
                        str(item.get("import_label") or ""),
                        str(meta.get("classification") or ""),
                    ):
                        keep_owner = "PERS-MATT"
                        reason = "Original assignee is Owner and item needs owner authority"
                    else:
                        reason = (
                            "Original assignee is Owner but item does not need owner "
                            "authority — NEEDS_ROUTING"
                        )
                else:
                    keep_owner = mapped
                    reason = f"Original assignee '{assignee_raw}' maps to {mapped} with active scope"
            else:
                if not assignee_raw:
                    reason = "No reliable original assignee in provenance"
                elif not mapped:
                    reason = f"Original assignee '{assignee_raw}' does not map to a current Person"
                else:
                    reason = (
                        f"Mapped person {mapped} has no active Assignment covering {entity}"
                    )

            wid = item["work_item_id"]
            if keep_owner:
                # Ensure owner matches mapped person; clear routing.
                c.execute(
                    """
                    UPDATE core_work_items
                    SET owner_person_id=?,
                        executor_person_id=?,
                        accountable_person_id=?,
                        owner_org_assignment_id=?,
                        routing_state=NULL,
                        routing_reason=?,
                        updated_at=?
                    WHERE work_item_id=?
                    """,
                    (
                        keep_owner,
                        keep_owner,
                        keep_owner,
                        _asg(c, keep_owner),
                        reason,
                        ts,
                        wid,
                    ),
                )
                after[keep_owner] = after.get(keep_owner, 0) + 1
                kept.append({"work_item_id": wid, "owner": keep_owner, "reason": reason})
            else:
                c.execute(
                    """
                    UPDATE core_work_items
                    SET owner_person_id=NULL,
                        executor_person_id=NULL,
                        accountable_person_id='PERS-MATT',
                        owner_org_assignment_id=NULL,
                        routing_state=?,
                        routing_reason=?,
                        what_happens_next='NEEDS ROUTING — Owner Overwatch queue. Not in anyone''s My Work.',
                        updated_at=?
                    WHERE work_item_id=?
                    """,
                    (ROUTING_NEEDS, reason, ts, wid),
                )
                after["NEEDS_ROUTING"] = after.get("NEEDS_ROUTING", 0) + 1
                moved.append(
                    {
                        "work_item_id": wid,
                        "from": item.get("owner_person_id"),
                        "reason": reason,
                        "source_id": src,
                        "assignee_in_source": assignee_raw or None,
                    }
                )

        if commit:
            c.commit()
        return {
            "before": before,
            "after": after,
            "kept": len(kept),
            "moved_to_needs_routing": len(moved),
            "moved_sample": moved[:20],
            "kept_sample": kept[:10],
        }
    finally:
        if own:
            c.close()


def live_commissioning_results(*, conn=None) -> dict[str, Any]:
    """Per person × capability counts for Owner live board."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT * FROM core_work_items
            WHERE origin IN ('commissioning', 'commissioning-retest', 'commissioning-repair')
              AND status != 'CANCELLED'
            """
        ).fetchall()
        by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for r in rows:
            item = dict(r)
            origin = item.get("origin")
            person = (
                item.get("owner_person_id")
                or item.get("executor_person_id")
                or ("ENGINEERING" if origin == "commissioning-repair" else "UNKNOWN")
            )
            cap = item.get("commissioning_capability_id") or "UNKNOWN"
            key = (str(person), str(cap))
            slot = by_key.get(key)
            if not slot:
                slot = {
                    "person_id": person,
                    "person_name": _person_name(c, person)
                    if person.startswith("PERS-")
                    else person,
                    "capability_id": cap,
                    "assigned": 0,
                    "opened": 0,
                    "in_progress": 0,
                    "done": 0,
                    "human_pass": 0,
                    "human_fail": 0,
                    "evidence_attached": 0,
                    "verified": 0,
                    "repair_created": 0,
                    "retest_issued": 0,
                    "capability_state_changed": 0,
                    "awaiting_verify": 0,
                }
                by_key[key] = slot
            if origin in {"commissioning", "commissioning-retest"}:
                slot["assigned"] += 1
                if item.get("opened_at"):
                    slot["opened"] += 1
                if item.get("status") == "IN_PROGRESS":
                    slot["in_progress"] += 1
                if item.get("status") in {"COMPLETED", "AWAITING_VERIFY", "VERIFIED"}:
                    slot["done"] += 1
                if item.get("human_result") == "PASS":
                    slot["human_pass"] += 1
                if item.get("human_result") == "FAIL":
                    slot["human_fail"] += 1
                if _evidence_count(c, item["work_item_id"]) > 0 or item.get(
                    "completion_evidence_reference"
                ):
                    slot["evidence_attached"] += 1
                if item.get("status") == "VERIFIED" or item.get("commissioning_result") == "PASS":
                    slot["verified"] += 1
                    slot["capability_state_changed"] += 1
                if item.get("status") == "AWAITING_VERIFY":
                    slot["awaiting_verify"] += 1
                if item.get("commissioning_result") == "FAIL":
                    slot["capability_state_changed"] += 1
            if origin == "commissioning-repair":
                slot["repair_created"] += 1
            if origin == "commissioning-retest":
                slot["retest_issued"] += 1

        people = sorted(by_key.values(), key=lambda x: (x["person_name"], x["capability_id"]))
        awaiting = [
            enrich_card(c, dict(r))
            for r in c.execute(
                """
                SELECT * FROM core_work_items
                WHERE status='AWAITING_VERIFY' AND origin IN ('commissioning','commissioning-retest')
                ORDER BY updated_at DESC LIMIT 40
                """
            ).fetchall()
        ]
        fails_no_repair = []
        for r in c.execute(
            """
            SELECT * FROM core_work_items
            WHERE origin IN ('commissioning','commissioning-retest')
              AND (human_result='FAIL' OR commissioning_result='FAIL')
              AND status != 'CANCELLED'
            """
        ).fetchall():
            if not _find_linked_repair(c, r["work_item_id"]):
                fails_no_repair.append(enrich_card(c, dict(r)))
        repairs_no_retest = []
        for r in c.execute(
            """
            SELECT * FROM core_work_items
            WHERE origin='commissioning-repair' AND status='COMPLETED'
            """
        ).fetchall():
            has_retest = c.execute(
                """
                SELECT 1 FROM core_work_items
                WHERE origin='commissioning-retest' AND parent_work_item_id=?
                  AND status NOT IN ('CANCELLED') LIMIT 1
                """,
                (r["work_item_id"],),
            ).fetchone()
            if not has_retest:
                repairs_no_retest.append(enrich_card(c, dict(r)))

        return {
            "ok": True,
            "as_of": now_iso(),
            "rows": people,
            "awaiting_verify": awaiting,
            "fails_without_repair": fails_no_repair,
            "repairs_fixed_without_retest": repairs_no_retest,
            "counts": {
                "people_capabilities": len(people),
                "awaiting_verify": len(awaiting),
                "fails_without_repair": len(fails_no_repair),
                "repairs_fixed_without_retest": len(repairs_no_retest),
            },
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        if own:
            c.close()


def commissioning_tick_apply(*, conn=None, commit: bool = True) -> dict[str, Any]:
    """Safe automatic steps only: missing repairs + retests. Never auto-verify PASS."""
    own = conn is None
    c = conn or wi.db_connect()
    created_repairs: list[str] = []
    created_retests: list[str] = []
    try:
        snap = live_commissioning_results(conn=c)
        for card in snap.get("fails_without_repair") or []:
            item = wi.get_work_item(card["work_item_id"], conn=c)
            if not item:
                continue
            repair = create_engineering_repair(item, note=item.get("human_comment"), conn=c, commit=False)
            created_repairs.append(repair["work_item_id"])
        for card in snap.get("repairs_fixed_without_retest") or []:
            retest = create_retest_for_repair(
                card["work_item_id"],
                commit_ref=None,
                conn=c,
                commit=False,
            )
            if retest.get("work_item_id"):
                created_retests.append(retest["work_item_id"])
        if commit:
            c.commit()
        return {
            "ok": True,
            "applied": True,
            "repairs_created": created_repairs,
            "retests_created": created_retests,
            "auto_verify_pass": False,
        }
    finally:
        if own:
            c.close()
