#!/usr/bin/env python3
"""ATRIUM-SOD-1B — real finance team structure (AP + temp AR).

Supersedes Matt-as-preparer. Decision: 2026-09-29 PICK ATRIUM-SOD-1
(Matt UPDATE 29 Sep 14:10 — real staffing). Beta catalog + atrium beta DB only.
Does not invent legal names. Does not flip staff_ready / human_commissioned.
Finance Officer seat stays VACANT. Ending Zayen's temp AR later = data only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import atrium_fc_authority as fc  # noqa: E402
from core import atrium_historical as hist  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.scope import upsert_assignment_scope  # noqa: E402
from core.staff_access import (  # noqa: E402
    AP_ASSIGNMENT,
    AP_AUTH,
    AP_EMAIL,
    AP_PERSON,
    AP_POSITION,
    ATRIUM_DENIED,
    ATRIUM_GRANTS,
    ATRIUM_OFFICER_DENIED,
    ATRIUM_SUBMIT,
    ENTITY_AMG,
    ROLE_ATRIUM_AP,
    ROLE_ATRIUM_AR,
    ROLE_ATRIUM_FINANCE,
    ROLE_ATRIUM_FINANCIAL_CONTROLLER,
    SCOPE_AMG_FINANCE,
    ZAYEN_AR_ASSIGNMENT,
    ZAYEN_AR_POSITION,
    ZAYEN_FC_ASSIGNMENT,
    ZAYEN_PERSON,
)

CATALOG = ROOT / "catalog" / "content_library.sqlite"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
EVIDENCE_DIR = ROOT / "state" / "atrium-sod"
COMMISSION_JOURNAL = "JRN-ATRIUMSOD1B-COMM1"
LEGACY_OWNER_JOURNAL = "JRN-ATRIUMSOD1-COMM1"
COMMISSION_AMOUNT = 50_000.0
AP_DISPLAY = "zenitalfathan"  # email local-part only; legal_name NULL

TEST_ARTIFACT_JOURNALS = (
    "JRN-MUM7ZLIY-746",
    "JRN-MULZIJ3N-117",
    "JRN-HUMFIX-PREP1",
    "JRN-HUMFIX-PREP2",
    LEGACY_OWNER_JOURNAL,
)

FC_POST_PERM = (
    "PERM-ATRIUM-JOURNAL-POST",
    "atrium.journal.post",
    "atrium.journal",
    "post",
    "POST /api/journals/:id/post. FC only; SoD preparer≠poster; APPROVED only.",
)

ZAYEN_FEEDBACK_13_32 = (
    "[ATRIUM-SOD-1 Matt relay 29 Sep 13:32 WITA] "
    "Missing preparer seat under the Controller — Finance Officer / General Accountant "
    "seat required so Controller is not also the preparer. Linked to AMG finance capability."
)

ZAYEN_FEEDBACK_1B = (
    "[ATRIUM-SOD-1B Matt UPDATE 29 Sep 14:10 WITA] "
    "Preparer model replaced: Accounts Payable = zenitalfathan@gmail.com; "
    "Accounts Receivable = Zayen temporary separate assignment; "
    "Finance Officer seat remains VACANT. SoD stays person_id based."
)

ZAYEN_SOD_ITEMS = (
    (
        "COMM-ZAYEN-SOD-REVIEW",
        "Review / return commissioning journal",
        "1. Open Atrium Finance Journal workbench.\n"
        f"2. Open {COMMISSION_JOURNAL} (SUBMITTED, prepared by Accounts Payable).\n"
        "3. Inspect lines + commissioning memo evidence.\n"
        "4. Return with a reason OR proceed to Approve. Screenshot, PASS/FAIL, DONE.",
        "Screenshot of journal with evidence visible",
        "/amg/finance#workbench",
    ),
    (
        "COMM-ZAYEN-SOD-APPROVE",
        "Approve commissioning journal (SoD)",
        "1. Open the SUBMITTED commissioning journal prepared by Accounts Payable (not you).\n"
        "2. Approve it (you must not be the preparer).\n"
        "3. Confirm you cannot approve a journal you prepared as AR.\n"
        "4. Screenshot APPROVED state, PASS/FAIL, DONE.",
        "Screenshot of APPROVED journal",
        "/amg/finance#workbench",
    ),
    (
        "COMM-ZAYEN-SOD-POST",
        "Post approved commissioning journal",
        "1. After approval, Post the journal to the General Ledger.\n"
        "2. Confirm Post is only available on APPROVED (not your own prepare).\n"
        "3. Screenshot POSTED confirmation, PASS/FAIL, DONE.",
        "Screenshot of POSTED journal",
        "/amg/finance#workbench",
    ),
    (
        "COMM-ZAYEN-SOD-GL",
        "Confirm posted lines in General Ledger",
        "1. Open General Ledger.\n"
        "2. Confirm the commissioning journal lines appear, marked Wolf-created.\n"
        "3. Confirm historical empty-state honesty if no other history.\n"
        "4. Screenshot, PASS/FAIL, DONE.",
        "Screenshot of GL with commissioning lines",
        "/amg/finance#ledger",
    ),
    (
        "COMM-ZAYEN-SOD-AR-TEMP",
        "Temporary Accounts Receivable tasks (plain language)",
        "1. You hold a temporary Accounts Receivable assignment (separate from Controller).\n"
        "2. You may prepare AR journals from receivables work.\n"
        "3. You must NOT approve or post journals you prepared — Owner Matt interim approves "
        "until another Controller exists.\n"
        "4. Ending this AR assignment later is a data change only (no code change). "
        "Acknowledge, PASS/FAIL, DONE.",
        "Acknowledgement note",
        "/amg/finance",
    ),
)

AP_SOD_ITEMS = (
    (
        "COMM-AP-SOD-PREPARE",
        "Prepare commissioning journal (Accounts Payable)",
        "1. Open Atrium Finance.\n"
        "2. Prepare a small balanced commissioning journal (not a real hotel bill).\n"
        "3. Attach the labelled commissioning memo (not a fake invoice).\n"
        "4. Validate. Screenshot, PASS/FAIL, DONE.\n"
        "HELD until Peaches verifies Cloudflare allow for zenitalfathan@gmail.com.",
        "Screenshot of draft/validated commissioning journal",
        "/amg/finance#workbench",
    ),
    (
        "COMM-AP-SOD-SUBMIT",
        "Submit commissioning journal for Controller review",
        "1. Submit the validated commissioning journal.\n"
        "2. Confirm you cannot Approve or Post.\n"
        "3. Screenshot SUBMITTED state, PASS/FAIL, DONE.\n"
        "HELD until Peaches verifies Cloudflare allow.",
        "Screenshot of SUBMITTED journal",
        "/amg/finance#workbench",
    ),
)

OWNER_FO_VACANT = (
    "COMM-OWNER-SOD-FO-VACANT",
    "Finance Officer seat still vacant",
    "1. ROLE-AMG-FINANCE-OFFICER + POS-AMG-FINANCE-OFFICER-1 remain VACANT (no assignment).\n"
    "2. Real preparers: Accounts Payable (zenitalfathan@gmail.com) + temporary AR (Zayen).\n"
    "3. CF email to add: zenitalfathan@gmail.com (Peaches verifies allow before AP activate).\n"
    "4. PASS when acknowledged.",
    "Acknowledgement note",
    "/amg/finance",
)


def _ts() -> str:
    return wi.now_utc_iso()


def _ensure_permission(
    conn: sqlite3.Connection,
    perm_id: str,
    code: str,
    resource: str,
    action: str,
    desc: str,
    ts: str,
) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET
          code=excluded.code,
          resource=excluded.resource,
          action=excluded.action,
          description=excluded.description,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (perm_id, code, resource, action, desc, ts, ts),
    )


def _grant(conn: sqlite3.Connection, role_id: str, code: str, ts: str) -> None:
    row = conn.execute(
        "SELECT permission_id FROM org_permissions WHERE code=?",
        (code,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"permission missing: {code}")
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, row[0], ts, ts),
    )


def _strip_denied(conn: sqlite3.Connection, role_id: str, codes: tuple[str, ...]) -> None:
    for code in codes:
        conn.execute(
            """
            DELETE FROM org_role_permissions
            WHERE role_id=? AND permission_id IN (
              SELECT permission_id FROM org_permissions WHERE code=?
            )
            """,
            (role_id, code),
        )


def ensure_finance_officer_vacant(conn: sqlite3.Connection) -> dict:
    """Keep ROLE/POS Finance Officer; leave VACANT."""
    ts = _ts()
    fo = conn.execute(
        "SELECT role_id, display_name FROM org_roles WHERE role_id=?",
        (ROLE_ATRIUM_FINANCE,),
    ).fetchone()
    pos = conn.execute(
        "SELECT position_id, position_label, status FROM org_positions WHERE position_id=?",
        ("POS-AMG-FINANCE-OFFICER-1",),
    ).fetchone()
    active = conn.execute(
        """
        SELECT assignment_id, person_id FROM org_assignments
        WHERE position_id='POS-AMG-FINANCE-OFFICER-1' AND status='ACTIVE' AND end_at IS NULL
        """
    ).fetchone()
    for _pid, code, *_rest in ATRIUM_GRANTS:
        _grant(conn, ROLE_ATRIUM_FINANCE, code, ts)
    _grant(conn, ROLE_ATRIUM_FINANCE, ATRIUM_SUBMIT, ts)
    _strip_denied(conn, ROLE_ATRIUM_FINANCE, ATRIUM_OFFICER_DENIED)
    return {
        "finance_officer_role": dict(fo) if fo else None,
        "finance_officer_position": dict(pos) if pos else None,
        "finance_officer_assignment": "VACANT" if not active else dict(active),
    }


def ensure_preparer_role(
    conn: sqlite3.Connection,
    *,
    role_id: str,
    display_name: str,
    position_id: str,
    position_label: str,
    ts: str,
) -> dict:
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, ?, NULL, 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name=excluded.display_name,
          role_type='OPERATING',
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (role_id, display_name, ts, ts),
    )
    for row in ATRIUM_GRANTS:
        _ensure_permission(conn, *row, ts)
    for _pid, code, *_rest in ATRIUM_GRANTS:
        _grant(conn, role_id, code, ts)
    _grant(conn, role_id, ATRIUM_SUBMIT, ts)
    _strip_denied(conn, role_id, ATRIUM_OFFICER_DENIED + ATRIUM_DENIED)
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, NULL, NULL, ?, 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id,
          entity_id=excluded.entity_id,
          position_label=excluded.position_label,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (position_id, role_id, ENTITY_AMG, position_label, ts, ts),
    )
    return {"role_id": role_id, "position_id": position_id, "display_name": display_name}


def find_person_by_email(conn: sqlite3.Connection, email: str) -> str | None:
    row = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (email.lower(),),
    ).fetchone()
    return str(row[0]) if row else None


def ensure_ap_person(conn: sqlite3.Connection) -> dict:
    """Exactly one Person for zenitalfathan@gmail.com. Do not invent legal name."""
    ts = _ts()
    existing = find_person_by_email(conn, AP_EMAIL)
    if existing and existing != AP_PERSON:
        raise RuntimeError(
            f"REFUSE: {AP_EMAIL} already bound to {existing} (want {AP_PERSON})"
        )
    person_id = existing or AP_PERSON
    # Prefer any authorised display; else local-part. legal_name stays NULL.
    prior = conn.execute(
        "SELECT display_name, legal_name FROM org_persons WHERE person_id=?",
        (person_id,),
    ).fetchone()
    display = (prior[0] if prior and prior[0] else AP_DISPLAY).strip() or AP_DISPLAY
    legal = prior[1] if prior else None  # never invent
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET
          display_name=COALESCE(NULLIF(excluded.display_name, ''), org_persons.display_name),
          legal_name=org_persons.legal_name,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (person_id, display, legal, ts, ts),
    )
    auth = conn.execute(
        """
        SELECT auth_identity_id, person_id, status FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (AP_EMAIL.lower(),),
    ).fetchone()
    if auth is None:
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
            """,
            (AP_AUTH, person_id, AP_EMAIL.lower(), ts, ts),
        )
    else:
        conn.execute(
            """
            UPDATE org_auth_identities
            SET status='ACTIVE', is_primary=1, person_id=?, updated_at=?
            WHERE provider='email' AND lower(identifier)=?
            """,
            (person_id, ts, AP_EMAIL.lower()),
        )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          person_id=excluded.person_id,
          position_id=excluded.position_id,
          status='ACTIVE',
          end_at=NULL,
          is_primary=1,
          updated_at=excluded.updated_at
        """,
        (AP_ASSIGNMENT, person_id, AP_POSITION, ts, ts, ts),
    )
    upsert_assignment_scope(conn, AP_ASSIGNMENT, SCOPE_AMG_FINANCE, ts, ts)
    return {
        "person_id": person_id,
        "email": AP_EMAIL.lower(),
        "display_name": display,
        "legal_name": legal,
        "auth_identity_id": AP_AUTH,
        "assignment_id": AP_ASSIGNMENT,
        "position_id": AP_POSITION,
        "role_id": ROLE_ATRIUM_AP,
        "cf_email_pending": AP_EMAIL.lower(),
        "commissioning": "HELD_UNTIL_CF_ACCESS",
    }


def ensure_zayen_ar_temp(conn: sqlite3.Connection) -> dict:
    """Keep FC; add separate temporary AR assignment. Ending AR later = data only."""
    ts = _ts()
    fc_asg = conn.execute(
        """
        SELECT assignment_id, person_id, status FROM org_assignments
        WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (ZAYEN_FC_ASSIGNMENT,),
    ).fetchone()
    if not fc_asg:
        raise RuntimeError("ASG-ZAYEN-FC-1 must stay ACTIVE")
    conn.execute(
        """
        UPDATE org_assignments SET is_primary=1, updated_at=?
        WHERE assignment_id=?
        """,
        (ts, ZAYEN_FC_ASSIGNMENT),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 0, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          person_id=excluded.person_id,
          position_id=excluded.position_id,
          status='ACTIVE',
          end_at=NULL,
          is_primary=0,
          updated_at=excluded.updated_at
        """,
        (ZAYEN_AR_ASSIGNMENT, ZAYEN_PERSON, ZAYEN_AR_POSITION, ts, ts, ts),
    )
    upsert_assignment_scope(conn, ZAYEN_AR_ASSIGNMENT, SCOPE_AMG_FINANCE, ts, ts)
    return {
        "fc_assignment_id": ZAYEN_FC_ASSIGNMENT,
        "ar_assignment_id": ZAYEN_AR_ASSIGNMENT,
        "ar_position_id": ZAYEN_AR_POSITION,
        "ar_role_id": ROLE_ATRIUM_AR,
        "note": (
            "Zayen temporary AR. Ending ASG-ZAYEN-AR-1 later is a data change only "
            "(set status=ENDED / end_at); no code change required."
        ),
    }


def grant_fc_post(conn: sqlite3.Connection) -> dict:
    ts = _ts()
    _ensure_permission(conn, *FC_POST_PERM, ts)
    _grant(conn, ROLE_ATRIUM_FINANCIAL_CONTROLLER, FC_POST_PERM[1], ts)
    for _pid, code, *_rest in ATRIUM_GRANTS:
        _grant(conn, ROLE_ATRIUM_FINANCIAL_CONTROLLER, code, ts)
    for code in ("atrium.journal.approve", "atrium.journal.reject", ATRIUM_SUBMIT):
        _grant(conn, ROLE_ATRIUM_FINANCIAL_CONTROLLER, code, ts)
    conn.execute(
        """
        UPDATE org_permissions
        SET description=?, updated_at=?
        WHERE permission_id='PERM-ATRIUM-JOURNAL-POST'
        """,
        (FC_POST_PERM[4], ts),
    )
    return {
        "role": ROLE_ATRIUM_FINANCIAL_CONTROLLER,
        "granted_post": True,
        "sod": "preparer_person_id",
    }


def archive_test_journals(atrium_path: Path) -> dict:
    results = []
    for jid in TEST_ARTIFACT_JOURNALS:
        reason = (
            "automated test artifact — superseded by ATRIUM-SOD-1B (Owner interim preparer retired)"
            if jid == LEGACY_OWNER_JOURNAL
            else "automated test artifact"
        )
        try:
            results.append(fc.archive_test_artifact(jid, atrium_db=atrium_path, reason=reason))
        except fc.FcAuthorityError as exc:
            results.append({"ok": False, "journal_id": jid, "error": str(exc)})
    return {"archived": results}


def _write_commissioning_memo(preparer_label: str, preparer_person_id: str) -> dict:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / "commissioning-memo-atriumsod1.png"
    width, height = 640, 360
    rows = []
    label_lines = [
        "WOLF COMMISSIONING MEMO — NOT A REAL BUSINESS DOCUMENT",
        "ATRIUM-SOD-1B · ENT-AMG · 2026-09-29",
        f"Journal: {COMMISSION_JOURNAL}",
        f"Prepared by: Accounts Payable ({preparer_label} · {preparer_person_id})",
        "Amount: IDR 50,000 balanced (Cash float / Revenue offset)",
        "Purpose: Controller SoD approve+post commissioning only",
        "Do not treat as hotel accounting evidence / not a fake invoice",
    ]
    for y in range(height):
        row = bytearray()
        row.append(0)
        for _x in range(width):
            if 40 <= y <= 100:
                row.extend((20, 40, 60))
            elif 120 <= y <= 280:
                row.extend((15, 23, 42))
            else:
                row.extend((10, 14, 28))
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9))
    text = b"Label\x00WOLF COMMISSIONING MEMO - ATRIUM-SOD-1B - NOT A REAL BUSINESS DOCUMENT"
    png += chunk(b"tEXt", text) + chunk(b"IEND", b"")
    path.write_bytes(png)
    txt = EVIDENCE_DIR / "commissioning-memo-atriumsod1.txt"
    txt.write_text("\n".join(label_lines) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path),
        "txt": str(txt),
        "sha256": digest,
        "label": "WOLF COMMISSIONING MEMO — ATRIUM-SOD-1B — NOT A REAL BUSINESS DOCUMENT",
        "lines": label_lines,
    }


def seed_commissioning_journal(atrium_path: Path, preparer_person_id: str, display_name: str) -> dict:
    """SUBMITTED journal prepared by AP person (not Matt, not Zayen)."""
    memo = _write_commissioning_memo(display_name, preparer_person_id)
    if not atrium_path.is_file():
        return {"ok": False, "error": "atrium db missing", "memo": memo}
    a = sqlite3.connect(str(atrium_path))
    a.row_factory = sqlite3.Row
    try:
        fc._ensure_schema(a)
        existing = a.execute(
            "SELECT journal_id, status, preparer_person_id FROM journal_headers WHERE journal_id=?",
            (COMMISSION_JOURNAL,),
        ).fetchone()
        if existing and existing["status"] in {"SUBMITTED", "APPROVED", "POSTED"}:
            if existing["preparer_person_id"] == preparer_person_id:
                return {
                    "ok": True,
                    "journal_id": COMMISSION_JOURNAL,
                    "status": existing["status"],
                    "preparer_person_id": existing["preparer_person_id"],
                    "already": True,
                    "memo": memo,
                    "label": "Commissioning scenario — prepared by Accounts Payable (ATRIUM-SOD-1B)",
                }
        a.execute("DELETE FROM journal_lines WHERE journal_id=?", (COMMISSION_JOURNAL,))
        a.execute("DELETE FROM journal_evidence WHERE journal_id=?", (COMMISSION_JOURNAL,))
        a.execute("DELETE FROM journal_headers WHERE journal_id=?", (COMMISSION_JOURNAL,))
        label = (
            "Commissioning scenario — prepared by Accounts Payable. "
            "ATRIUM-SOD-1B. NOT a real hotel transaction."
        )
        created_by = f"Accounts Payable ({display_name}) · {preparer_person_id}"
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type,
              source_reference, created_by, approved_by, posted_at,
              preparer_person_id, posted_by, return_reason,
              wolf_created, historical_import, verified, archived_reason, evidence_ref
            ) VALUES (
              ?, '2026-09-29', '2026-09', 'SUBMITTED', 'MANUAL',
              ?, ?, '', '',
              ?, '', '',
              1, 0, 0, '', ?
            )
            """,
            (COMMISSION_JOURNAL, label, created_by, preparer_person_id, memo["path"]),
        )
        a.execute(
            """
            INSERT INTO journal_lines (
              journal_id, line_no, account_code, department_code, debit, credit, description
            ) VALUES
              (?, 1, '1020', '100', ?, 0.0, 'ATRIUM-SOD-1B commissioning float (Wolf-created)'),
              (?, 2, '4000', '100', 0.0, ?, 'ATRIUM-SOD-1B commissioning offset (Wolf-created)')
            """,
            (COMMISSION_JOURNAL, COMMISSION_AMOUNT, COMMISSION_JOURNAL, COMMISSION_AMOUNT),
        )
        eid = fc.new_evidence_id()
        a.execute(
            """
            INSERT INTO journal_evidence (
              evidence_id, journal_id, filename, content_type, label, path,
              created_at_utc, created_by_person_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eid,
                COMMISSION_JOURNAL,
                Path(memo["path"]).name,
                "image/png",
                memo["label"],
                memo["path"],
                fc.now_utc_iso(),
                preparer_person_id,
            ),
        )
        fc._audit_transition(
            a,
            journal_id=COMMISSION_JOURNAL,
            from_status="SEED",
            to_status="SUBMITTED",
            actor_person_id=preparer_person_id,
            evidence_ref=memo["path"],
            note="Accounts Payable preparer — ATRIUM-SOD-1B commissioning",
        )
        a.commit()
        return {
            "ok": True,
            "journal_id": COMMISSION_JOURNAL,
            "status": "SUBMITTED",
            "preparer_person_id": preparer_person_id,
            "amount_idr": COMMISSION_AMOUNT,
            "evidence_id": eid,
            "already": False,
            "memo": memo,
            "label": label,
        }
    finally:
        a.close()


def seed_my_work(conn: sqlite3.Connection, ap_person_id: str) -> dict:
    created = []
    zayen_asg = umw._asg(conn, ZAYEN_PERSON, ROLE_ATRIUM_FINANCIAL_CONTROLLER) or umw._asg(
        conn, ZAYEN_PERSON
    )
    for cap, title, intent, evidence, href in ZAYEN_SOD_ITEMS:
        before = conn.execute(
            """
            SELECT work_item_id FROM core_work_items
            WHERE origin='commissioning' AND commissioning_capability_id=?
              AND owner_person_id=? AND status NOT IN ('CANCELLED')
            """,
            (cap, ZAYEN_PERSON),
        ).fetchone()
        # Refresh instructions on existing Zayen SOD items (1B text)
        if before:
            conn.execute(
                """
                UPDATE core_work_items
                SET title=?, instructions=?, evidence_required=?,
                    checklist_json=?, updated_at=?
                WHERE work_item_id=?
                """,
                (
                    title,
                    intent,
                    evidence,
                    json.dumps([{"step": intent, "href": href}]),
                    _ts(),
                    before[0],
                ),
            )
            created.append(
                {"capability_id": cap, "work_item_id": before[0], "already": True, "refreshed": True}
            )
            continue
        item = umw._create_commission_task(
            conn,
            title=title,
            owner_person_id=ZAYEN_PERSON,
            owner_assignment_id=zayen_asg,
            entity_id=ENTITY_AMG,
            capability_id=cap,
            instructions=intent,
            evidence_required=evidence,
            href_hint=href,
            scope_label="AMG · Atrium Finance · ATRIUM-SOD-1B",
        )
        created.append(
            {
                "capability_id": cap,
                "work_item_id": item.get("work_item_id"),
                "already": False,
            }
        )

    ap_asg = umw._asg(conn, ap_person_id, ROLE_ATRIUM_AP) or umw._asg(conn, ap_person_id)
    for cap, title, intent, evidence, href in AP_SOD_ITEMS:
        item = umw._create_commission_task(
            conn,
            title=title,
            owner_person_id=ap_person_id,
            owner_assignment_id=ap_asg,
            entity_id=ENTITY_AMG,
            capability_id=cap,
            instructions=intent,
            evidence_required=evidence,
            href_hint=href,
            scope_label="AMG · Atrium Finance · ATRIUM-SOD-1B · HELD",
        )
        # Force HELD even if create path reused
        if item.get("work_item_id"):
            conn.execute(
                """
                UPDATE core_work_items
                SET routing_state=?,
                    routing_reason=?,
                    what_happens_next=?,
                    updated_at=?
                WHERE work_item_id=?
                """,
                (
                    umw.ROUTING_HELD_CF,
                    (
                        "activate when Peaches verifies zenitalfathan@gmail.com is in Beta Cloudflare "
                        "(Person/AuthIdentity + Accounts Payable Assignment ready; do not activate early)"
                    ),
                    "HELD until Peaches activates after allow/deny pass. Not visible as active My Work.",
                    _ts(),
                    item["work_item_id"],
                ),
            )
        created.append(
            {
                "capability_id": cap,
                "work_item_id": item.get("work_item_id"),
                "routing_state": umw.ROUTING_HELD_CF,
            }
        )

    # Cancel Owner interim preparer vacant item from SOD-1 if present
    conn.execute(
        """
        UPDATE core_work_items
        SET status='CANCELLED', updated_at=?,
            what_happens_next='Superseded by ATRIUM-SOD-1B — real AP hired; FO still vacant.'
        WHERE commissioning_capability_id='COMM-OWNER-SOD-PREPARER-VACANT'
          AND status NOT IN ('CANCELLED','DONE','VERIFIED')
        """,
        (_ts(),),
    )
    cap, title, intent, evidence, href = OWNER_FO_VACANT
    matt_asg = umw._asg(conn, "PERS-MATT", "ROLE-OWNER") or umw._asg(conn, "PERS-MATT")
    item = umw._create_commission_task(
        conn,
        title=title,
        owner_person_id="PERS-MATT",
        owner_assignment_id=matt_asg,
        entity_id=ENTITY_AMG,
        capability_id=cap,
        instructions=intent,
        evidence_required=evidence,
        href_hint=href,
        scope_label="AMG · Atrium Finance · ATRIUM-SOD-1B",
    )
    created.append(
        {"capability_id": cap, "work_item_id": item.get("work_item_id")}
    )
    return {"items": created}


def record_zayen_finding(conn: sqlite3.Connection) -> dict:
    """Append finding; do not close or overwrite old FAIL history."""
    ts = _ts()
    finding_id = "FIND-ATRIUMSOD1-ZAYEN-PREPARER-SEAT"
    existing = conn.execute(
        """
        SELECT work_item_id FROM core_work_items
        WHERE commissioning_capability_id=? AND status NOT IN ('CANCELLED')
        """,
        (finding_id,),
    ).fetchone()
    findings_path = EVIDENCE_DIR / "findings.md"
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    if existing:
        with findings_path.open("a", encoding="utf-8") as fh:
            fh.write(
                f"\n## {ts} · {finding_id} (history preserved — ATRIUM-SOD-1B update)\n"
                f"{ZAYEN_FEEDBACK_13_32}\n{ZAYEN_FEEDBACK_1B}\n"
                f"Resolution path: AP person created; FO seat still VACANT; "
                f"finding stays open for Matt CF/hire acknowledgement.\n"
            )
        return {"finding_id": finding_id, "work_item_id": existing[0], "already": True}
    matt_asg = umw._asg(conn, "PERS-MATT", "ROLE-OWNER") or umw._asg(conn, "PERS-MATT")
    item = umw._create_commission_task(
        conn,
        title="Human commissioning finding: missing preparer seat under Controller",
        owner_person_id="PERS-MATT",
        owner_assignment_id=matt_asg,
        entity_id=ENTITY_AMG,
        capability_id=finding_id,
        instructions=ZAYEN_FEEDBACK_13_32
        + "\n"
        + ZAYEN_FEEDBACK_1B
        + "\nDo not close old FAIL history. Finance Officer seat remains VACANT.",
        evidence_required="Discovery note + Matt CF allow for AP",
        href_hint="/amg/finance",
        scope_label="AMG · Atrium Finance · finding",
    )
    with findings_path.open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n## {ts} · {finding_id}\n{ZAYEN_FEEDBACK_13_32}\n{ZAYEN_FEEDBACK_1B}\n"
            f"work_item={item.get('work_item_id')}\n"
        )
    return {
        "finding_id": finding_id,
        "work_item_id": item.get("work_item_id"),
        "already": False,
        "at": ts,
    }


def run(
    *,
    db_path: Path | None = None,
    atrium_path: Path | None = None,
) -> dict:
    catalog = Path(db_path or CATALOG)
    atrium = Path(atrium_path or ATRIUM_DB)
    conn = wi.db_connect(catalog)
    try:
        ts = _ts()
        out: dict = {"catalog": str(catalog), "atrium": str(atrium), "brief": "ATRIUM-SOD-1B"}
        out["seat"] = ensure_finance_officer_vacant(conn)
        out["ap_role"] = ensure_preparer_role(
            conn,
            role_id=ROLE_ATRIUM_AP,
            display_name="Accounts Payable",
            position_id=AP_POSITION,
            position_label="Accounts Payable",
            ts=ts,
        )
        out["ar_role"] = ensure_preparer_role(
            conn,
            role_id=ROLE_ATRIUM_AR,
            display_name="Accounts Receivable",
            position_id=ZAYEN_AR_POSITION,
            position_label="Accounts Receivable",
            ts=ts,
        )
        out["ap_person"] = ensure_ap_person(conn)
        out["zayen_ar"] = ensure_zayen_ar_temp(conn)
        out["fc_post"] = grant_fc_post(conn)
        out["archive"] = archive_test_journals(atrium)
        out["commission_journal"] = seed_commissioning_journal(
            atrium,
            out["ap_person"]["person_id"],
            out["ap_person"]["display_name"],
        )
        out["historical"] = hist.ensure_import_model(atrium)
        out["my_work"] = seed_my_work(conn, out["ap_person"]["person_id"])
        out["finding"] = record_zayen_finding(conn)
        out["cf_email_to_add"] = AP_EMAIL.lower()
        out["staff_ready"] = False
        out["human_commissioned"] = False
        conn.commit()
        return out
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--atrium", type=Path, default=None)
    args = ap.parse_args()
    out = run(db_path=args.db, atrium_path=args.atrium)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print("ATRIUM-SOD-1B migrate ok")
        print(f"  Finance Officer: {out['seat']['finance_officer_assignment']}")
        print(f"  AP person: {out['ap_person']['person_id']} <{out['ap_person']['email']}>")
        print(f"  AP assignment: {out['ap_person']['assignment_id']}")
        print(f"  Zayen AR temp: {out['zayen_ar']['ar_assignment_id']}")
        print(f"  Commission journal: {out['commission_journal'].get('journal_id')} "
              f"{out['commission_journal'].get('status')} "
              f"prep={out['commission_journal'].get('preparer_person_id')}")
        print(f"  CF email pending: {out['cf_email_to_add']}")
        print(f"  Historical: {out['historical'].get('status')}")
        print(f"  My Work items: {len(out['my_work']['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
