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
TZ8 = timezone(timedelta(hours=8))
WITA = ZoneInfo("Asia/Makassar")
BOUND = "beta-universal-my-work"

# Presentation labels (plain words). DB statuses stay machine codes.
STATUS_LABEL = {
    "OPEN": "ASSIGNED",
    "IN_PROGRESS": "IN PROGRESS",
    "BLOCKED": "BLOCKED",
    "WAITING": "WAITING",
    "RETURNED": "RETURNED",
    "REASSIGNED": "REASSIGNED",
    "COMPLETED": "DONE",
    "VERIFIED": "VERIFIED",
    "CANCELLED": "CANCELLED",
}

ACTIVE_WORK = frozenset(
    {"OPEN", "IN_PROGRESS", "BLOCKED", "WAITING", "RETURNED", "REASSIGNED"}
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


def enrich_card(conn, item: dict[str, Any]) -> dict[str, Any]:
    """Card fields required by MYWORK-1 Part B."""
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
    next_step = (item.get("what_happens_next") or "").strip()
    if not next_step:
        if status == "OPEN":
            next_step = "Accept and start, or open the instructions."
        elif status == "IN_PROGRESS":
            next_step = "Attach evidence, then mark DONE."
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
    return {
        "id": wid,
        "work_item_id": wid,
        "title": item.get("title") or "",
        "what": item.get("title") or "",
        "requested_by": _person_name(conn, requested),
        "requested_by_person_id": requested,
        "current_owner": _person_name(conn, owner),
        "current_owner_person_id": owner,
        "accountable": _person_name(conn, accountable),
        "accountable_person_id": accountable,
        "due": format_wita(item.get("due_at")) or item.get("due_at"),
        "due_at_utc": item.get("due_at"),
        "company_site_department": item.get("scope_label") or item.get("owning_entity_id"),
        "priority": item.get("priority"),
        "instructions": item.get("instructions") or item.get("description") or "",
        "checklist": json.loads(item["checklist_json"]) if item.get("checklist_json") else [],
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
        "staff_ready": False,
        "human_commissioned": False,
    }


def _mine_rows(conn, person_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM core_work_items
        WHERE status != 'CANCELLED'
          AND (
            owner_person_id = ?
            OR executor_person_id = ?
            OR accountable_person_id = ?
          )
        ORDER BY priority ASC, due_at IS NULL, due_at ASC, updated_at DESC
        LIMIT 80
        """,
        (person_id, person_id, person_id),
    ).fetchall()
    return [dict(r) for r in rows]


def build_universal_sections(
    person_id: str,
    *,
    conn=None,
    extra_today: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """TODAY / DO THIS NEXT / NEEDS ATTENTION / WAITING / COMPLETED."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        mine = _mine_rows(c, person_id)
        cards = [enrich_card(c, r) for r in mine]
        today = [
            card
            for card in cards
            if card["status"] in {"OPEN", "IN_PROGRESS", "RETURNED"}
            and card.get("current_owner_person_id") == person_id
        ]
        do_next = sorted(today, key=lambda x: (x.get("priority") or 3, x.get("due") or "9999"))[:5]
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
        # Also waiting when accountable but someone else is executor.
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
            card for card in cards if card["status"] in {"COMPLETED", "VERIFIED"}
        ][:12]
        if extra_today:
            today = list(extra_today) + today
        return [
            {
                "key": "today",
                "title": SECTION_TITLES["today"],
                "empty": not today,
                "empty_message": None if today else "Nothing is assigned to you for today.",
                "items": today[:20],
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
            # Soft path: owner of the item may attach a note/file for commissioning.
            if item.get("owner_person_id") != uploaded_by_person_id and item.get(
                "executor_person_id"
            ) != uploaded_by_person_id:
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


def mark_done(
    work_item_id: str,
    *,
    verified_person_id: str,
    outcome: str | None = None,
    identity: dict[str, Any] | None = None,
    conn=None,
    commit: bool = True,
) -> dict[str, Any]:
    """DONE = COMPLETED claim. Does not verify. Does not move SYSTEM %."""
    item = wi.claim_complete(
        work_item_id,
        verified_person_id=verified_person_id,
        outcome=outcome,
        identity=identity,
        conn=conn,
        commit=commit,
    )
    # Commissioning: DONE creates evidence of attempt; VERIFIED is separate.
    return {
        "ok": True,
        "work_item": item,
        "status_label": "DONE",
        "verified": False,
        "staff_ready": False,
        "human_commissioned": False,
        "system_percent_unchanged": True,
    }


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
    """PASS → VERIFIED HUMAN PASS on commissioning record. FAIL → repair item."""
    res = (result or "").strip().upper()
    if res not in {"PASS", "FAIL"}:
        raise MyWorkError("result must be PASS or FAIL", code="invalid_result")
    own = conn is None
    c = conn or wi.db_connect()
    try:
        item = wi.get_work_item(work_item_id, conn=c)
        if not item:
            raise MyWorkError("Work item not found.", code="not_found", http_status=404)
        if item["status"] != "COMPLETED":
            raise MyWorkError(
                "Only DONE (COMPLETED) commissioning tasks can be verified.",
                code="not_done",
            )
        # Owner / Peaches-style verifier: work.verify permission or Owner role.
        entity = str(item["owning_entity_id"])
        allowed = _rbac.evaluate(
            verifier_person_id, "work.verify", {"entity_id": entity}, conn=c
        ).get("allowed")
        if not allowed and verifier_person_id != "PERS-MATT":
            raise MyWorkError("work.verify denied", code="rbac_denied", http_status=403)
        ts = wi.now_utc_iso()
        if res == "PASS":
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
                    what_happens_next='VERIFIED HUMAN PASS recorded. Not staff_ready. Not human_commissioned.',
                    updated_at=?
                WHERE work_item_id=?
                """,
                ((note or "VERIFIED HUMAN PASS").strip(), ts, work_item_id),
            )
            repair = None
        else:
            c.execute(
                """
                UPDATE core_work_items
                SET commissioning_result='FAIL',
                    status='RETURNED',
                    outcome=?,
                    what_happens_next='FAIL — repair item issued. Retest will follow.',
                    updated_at=?
                WHERE work_item_id=?
                """,
                ((note or "FAIL").strip(), ts, work_item_id),
            )
            updated = wi.get_work_item(work_item_id, conn=c)
            repair = wi.create_work_item(
                title=f"Repair: {item.get('title')}",
                description=(
                    f"Repair linked to failed commissioning {work_item_id}. "
                    f"Evidence: {item.get('completion_evidence_reference') or 'see attachments'}."
                ),
                owning_entity_id=entity,
                work_type="EXCEPTION",
                source_type="SYSTEM",
                created_by_actor_type="SYSTEM",
                owner_person_id=item.get("owner_person_id"),
                owner_org_assignment_id=item.get("owner_org_assignment_id"),
                parent_work_item_id=work_item_id,
                source_id=f"commissioning-repair:{work_item_id}",
                conn=c,
                commit=False,
            )
            c.execute(
                """
                UPDATE core_work_items
                SET origin='commissioning-repair',
                    accountable_person_id=?,
                    executor_person_id=owner_person_id,
                    commissioning_capability_id=?,
                    evidence_required='Show the fix with a photo, screenshot, or document.',
                    what_happens_next='Fix the defect, attach evidence, mark DONE, then a retest task will be issued.',
                    updated_at=?
                WHERE work_item_id=?
                """,
                (
                    item.get("accountable_person_id") or item.get("owner_person_id"),
                    item.get("commissioning_capability_id"),
                    ts,
                    repair["work_item_id"],
                ),
            )
            repair = wi.get_work_item(repair["work_item_id"], conn=c)
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
            ORDER BY priority ASC, created_at ASC
            """
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
            "Open the surface, do the work, attach evidence, mark DONE. Verification is separate.",
            ts,
            item["work_item_id"],
        ),
    )
    return wi.get_work_item(item["work_item_id"], conn=conn) or item


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
        specs = [
            # Devi
            ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-UMA-TODAY",
             "Commission Uma Today", "Open Uma Today on Beta. Walk the real bills and sales view. Attach a phone screenshot.",
             "Phone screenshot of Uma Today", "/bzg/uma-blu", "BZG · Uma Blu"),
            ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-RECIPES",
             "Commission Recipes", "Open Recipes, open one real recipe detail, attach screenshot.",
             "Screenshot of a real recipe", "/bzg/uma-blu#recipes", "BZG · Uma Blu"),
            ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-PURCHASING",
             "Commission Purchasing", "Open Purchasing / Alchemist projection. Confirm real PR rows. Attach screenshot.",
             "Screenshot of purchasing queue", "/bzg/uma-blu#purchasing", "BZG · Uma Blu"),
            ("PERS-DEVI", "ROLE-BZG-FB-OPS-LEAD", "ENT-BZG", "COMM-DEVI-ESB-SALES",
             "Commission ESB sales view", "Open ESB sales projection for Uma Blu. Attach screenshot of real day totals.",
             "Screenshot of ESB sales", "/bzg/uma-blu#sales", "BZG · Uma Blu"),
            ("PERS-DEVI", "ROLE-BZG-CLOSER", "ENT-BZG", "COMM-DEVI-DAILY-CLOSE",
             "Commission Daily Close workflow (tolerance UNSET)",
             "Open Daily Close. Cash-variance tolerance is UNSET — do not invent a number. "
             "Run the parts of the workflow that do not depend on tolerance. Attach screenshot.",
             "Screenshot of Daily Close with UNSET policy control visible",
             "/uma-blu-close", "BZG · Uma Blu · Closer"),
            # Zayen
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-COMMAND",
             "Commission Atrium Command Centre", "Open Atrium Finance Command Centre. Attach screenshot.",
             "Screenshot of Command Centre", "/amg/finance", "AMG · Atrium Finance"),
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-JOURNAL",
             "Commission Journal (draft only)", "Open Journal. Draft only as your matrix allows. Do not post or approve. Attach screenshot.",
             "Screenshot of Journal draft view", "/amg/finance#journal", "AMG · Atrium Finance"),
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-LEDGER",
             "Commission Ledger", "Open General Ledger. Confirm IDR display. Attach screenshot.",
             "Screenshot of Ledger", "/amg/finance#ledger", "AMG · Atrium Finance"),
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-TRIAL",
             "Commission Trial Balance", "Open Trial Balance. Attach screenshot.",
             "Screenshot of Trial Balance", "/amg/finance#trial", "AMG · Atrium Finance"),
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-ARAP",
             "Commission AR/AP", "Open AR and AP views. Attach screenshots.",
             "Screenshots of AR and AP", "/amg/finance", "AMG · Atrium Finance"),
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-INVENTORY",
             "Commission Inventory", "Open Inventory. Attach screenshot.",
             "Screenshot of Inventory", "/amg/finance#inventory", "AMG · Atrium Finance"),
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-REPORTS",
             "Commission Reports", "Open financial reports. Attach screenshot.",
             "Screenshot of Reports", "/amg/finance#reports", "AMG · Atrium Finance"),
            ("PERS-ZAYEN", "ROLE-AMG-FINANCIAL-CONTROLLER", "ENT-AMG", "COMM-ZAYEN-CONTROLS",
             "Confirm approval/posting controls denied",
             "Confirm you cannot approve/post journals, pay, or change bank details. Attach a denial screenshot or written note.",
             "Evidence of denied approve/post/pay/bank", "/amg/finance", "AMG · Atrium Finance"),
            # Amanda
            ("PERS-AMANDA", "ROLE-GGV-FINANCE-OPERATOR", "ENT-GGV", "COMM-AMANDA-064A-066A",
             "Verify GGV invoices 064A–066A", "Open GGV Finance. Verify invoices 064A through 066A against source. Attach notes/screenshots.",
             "Verification notes for 064A–066A", "/ggv/finance", "GGV · Finance"),
            ("PERS-AMANDA", "ROLE-GGV-FINANCE-OPERATOR", "ENT-GGV", "COMM-AMANDA-067A",
             "Next genuine invoice through draft (067A if due)",
             "Only if genuinely due: prepare the next invoice as draft. Next number 067A. Do not invent a due invoice. Attach draft evidence or a note that none is due.",
             "Draft invoice 067A or note that none is due", "/ggv/finance", "GGV · Finance"),
            # Haikal
            ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-MYWORK",
             "Commission My Work", "Open My Work on phone (390px). Confirm TODAY / DO THIS NEXT / NEEDS ATTENTION / WAITING / COMPLETED. Attach screenshot.",
             "Phone screenshot of My Work", "/my-work", "GGV · Content"),
            ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-PLAN",
             "Commission Content Plan", "Open Content Plan. Confirm header fits at 390px. Attach screenshot.",
             "Phone screenshot of Content Plan", "/content-2.0#plan", "GGV · Content"),
            ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-LIBRARY",
             "Commission Library pagination/preview/download/upload",
             "On the library: use numbered pages, preview one file, download, open upload view. Attach screenshots.",
             "Screenshots of pagination, preview, download, upload", "/content-2.0#library", "GGV · Content"),
            ("PERS-HAIKAL", "ROLE-GGV-CREATIVE-DIRECTOR", "ENT-GGV", "COMM-HAIKAL-HABITAT",
             "Real Habitat work from My Work", "Open a real Habitat plan from My Work and note the next production step. Attach screenshot.",
             "Screenshot of Habitat plan from My Work", "/my-work", "GGV · Content"),
        ]
        # Other content staff — one My Work commissioning each.
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
                    "Open My Work. Confirm your assignment work appears. Attach a screenshot.",
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
            "owner-command-exceptions",
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
    """Overdue / blocked / failed commissioning for Owner Command."""
    own = conn is None
    c = conn or wi.db_connect()
    try:
        rows = c.execute(
            """
            SELECT * FROM core_work_items
            WHERE status IN ('BLOCKED', 'RETURNED')
               OR commissioning_result = 'FAIL'
               OR (
                    status IN ('OPEN','IN_PROGRESS','WAITING')
                    AND due_at IS NOT NULL AND due_at < ?
               )
            ORDER BY priority ASC, due_at IS NULL, due_at ASC
            LIMIT 40
            """,
            (now_iso(),),
        ).fetchall()
        return [enrich_card(c, dict(r)) for r in rows]
    finally:
        if own:
            c.close()
