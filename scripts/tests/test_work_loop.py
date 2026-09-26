#!/usr/bin/env python3
"""Pack 4 — work, evidence, approval, outcome on the Beta handler.

Writes clearly marked P4-TEST rows to the Beta catalog, then removes the
mutable ones. Audit events and approval decisions stay (append-only).
Does not touch production :8787.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["WOLF_ALLOW_LIVE_AUDIT"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import delegation as dlg  # noqa: E402
from core import evidence as ev  # noqa: E402
from core import exceptions as exmod  # noqa: E402
from core import request_auth as ra  # noqa: E402
from core import sod as sod  # noqa: E402
from core import work_items as wi  # noqa: E402
from core import work_loop as loop  # noqa: E402

PASS = 0
FAIL = 0
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"

ENTITY = "ENT-GGV"
SCOPE = "SCOPE-GGV-ALL"
MATT = "mrwolf@wolfcommand.net"
MATT_ID = "PERS-MATT"
HAIKAL = "haikalqilbari123@gmail.com"

WORKER_ID = "PERS-P4-WORKER"
WORKER_EMAIL = "p4-worker@seed.invalid"
WORKER_ASG = "ASG-P4-WORKER"
WORKER_POS = "POS-P4-WORKER"
APPROVER_ID = "PERS-P4-APPROVER"
APPROVER_EMAIL = "p4-approver@seed.invalid"
APPROVER_ASG = "ASG-P4-APPROVER"
APPROVER_POS = "POS-P4-APPROVER"
APPROVER2_ID = "PERS-P4-APPROVER-2"
APPROVER2_EMAIL = "p4-approver-2@seed.invalid"
APPROVER2_ASG = "ASG-P4-APPROVER-2"
APPROVER2_POS = "POS-P4-APPROVER-2"
DELEGATE_ID = "PERS-P4-DELEGATE"
DELEGATE_EMAIL = "p4-delegate@seed.invalid"
DELEGATE_ASG = "ASG-P4-DELEGATE"
DELEGATE_POS = "POS-P4-DELEGATE"
SOD_ID = "PERS-P4-SOD"
SOD_EMAIL = "p4-sod@seed.invalid"
SOD_ASG = "ASG-P4-SOD"
SOD_POS = "POS-P4-SOD"
REPLACE_ID = "PERS-P4-REPLACE"
REPLACE_EMAIL = "p4-replace@seed.invalid"
REPLACE_ASG = "ASG-P4-REPLACE"
REPLACE_POS = "POS-P4-REPLACE"

ROLE_WORKER = "ROLE-P4-WORKER"
ROLE_APPROVER = "ROLE-P4-APPROVER"
ROLE_DELEGATE = "ROLE-P4-DELEGATE"
ROLE_SOD = "ROLE-P4-SOD"

LIMIT_ID = "AUTH-P4-TEST"
SOD_CONSTRAINT = "SOD-P4-TEST"
EVR_ID = "EVR-P4-TEST"
PERM_DECIDE = "PERM-APPROVAL-DECIDE"

WORKER_PERMS = (
    "work.create",
    "work.read",
    "work.update",
    "work.assign",
    "work.complete",
    "approval.request",
    "approval.read",
    "evidence.record.submit",
)
APPROVER_PERMS = ("approval.decide", "approval.read", "work.read")
DELEGATE_PERMS = ("approval.read", "work.read")
SOD_PERMS = WORKER_PERMS + ("approval.decide", "governance.exception.request")


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(CATALOG), timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _listen_pid(port: int) -> str:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return ""
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines[0] if lines else ""


def _purge() -> None:
    c = _conn()
    try:
        stamp = wi.now_utc_iso()
        ids = [
            r["work_item_id"]
            for r in c.execute(
                """
                SELECT work_item_id FROM core_work_items
                WHERE title LIKE 'P4-TEST%' OR source_id = 'P4-TEST'
                """
            ).fetchall()
        ]
        if ids:
            marks = ",".join("?" for _ in ids)
            c.execute(
                f"""
                UPDATE core_evidence_records
                SET status = 'INVALIDATED', invalidate_reason = 'P4-TEST cleanup',
                    invalidated_at = ?, updated_at = ?
                WHERE governed_object_id IN ({marks}) AND status != 'INVALIDATED'
                """,
                [stamp, stamp, *ids],
            )
            c.execute(
                f"""
                UPDATE core_governance_exceptions
                SET status = 'REJECTED', reject_reason = 'P4-TEST cleanup'
                WHERE status IN ('REQUESTED', 'AUTHORISED')
                  AND (
                    control_reference = ?
                    OR governed_object_id IN (
                      SELECT approval_request_id FROM core_approval_requests
                      WHERE linked_work_item_id IN ({marks}) OR title LIKE 'P4-TEST%'
                    )
                  )
                """,
                [SOD_CONSTRAINT, *ids],
            )
            c.execute(
                f"DELETE FROM core_approval_requests WHERE linked_work_item_id IN ({marks}) OR title LIKE 'P4-TEST%'",
                ids,
            )
            c.execute(f"DELETE FROM core_work_items WHERE work_item_id IN ({marks})", ids)
        else:
            c.execute("DELETE FROM core_approval_requests WHERE title LIKE 'P4-TEST%'")
            c.execute(
                """
                UPDATE core_governance_exceptions
                SET status = 'REJECTED', reject_reason = 'P4-TEST cleanup'
                WHERE control_reference = ? AND status IN ('REQUESTED', 'AUTHORISED')
                """,
                (SOD_CONSTRAINT,),
            )
        c.execute(
            "DELETE FROM core_exceptionable_controls WHERE control_reference = ?",
            (SOD_CONSTRAINT,),
        )
        c.execute("DELETE FROM core_sod_constraints WHERE constraint_id = ?", (SOD_CONSTRAINT,))
        c.execute(
            "DELETE FROM core_evidence_requirements WHERE requirement_id = ?",
            (EVR_ID,),
        )
        c.execute("DELETE FROM org_authority_limits WHERE authority_limit_id = ?", (LIMIT_ID,))
        c.execute(
            "DELETE FROM core_delegations WHERE reason LIKE 'P4-TEST%' OR delegate_person_id IN (?, ?)",
            (DELEGATE_ID, SOD_ID),
        )
        people = (
            (WORKER_ID, WORKER_EMAIL, WORKER_ASG, WORKER_POS),
            (APPROVER_ID, APPROVER_EMAIL, APPROVER_ASG, APPROVER_POS),
            (APPROVER2_ID, APPROVER2_EMAIL, APPROVER2_ASG, APPROVER2_POS),
            (DELEGATE_ID, DELEGATE_EMAIL, DELEGATE_ASG, DELEGATE_POS),
            (SOD_ID, SOD_EMAIL, SOD_ASG, SOD_POS),
            (REPLACE_ID, REPLACE_EMAIL, REPLACE_ASG, REPLACE_POS),
        )
        for pid, email, asg, pos in people:
            c.execute("DELETE FROM org_assignment_scopes WHERE assignment_id = ?", (asg,))
            c.execute("DELETE FROM org_assignments WHERE assignment_id = ? OR person_id = ?", (asg, pid))
            c.execute(
                "DELETE FROM org_auth_identities WHERE person_id = ? OR lower(identifier) = ?",
                (pid, email.lower()),
            )
            c.execute("DELETE FROM org_persons WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM org_positions WHERE position_id = ?", (pos,))
        for role in (ROLE_WORKER, ROLE_APPROVER, ROLE_DELEGATE, ROLE_SOD):
            c.execute("DELETE FROM org_role_permissions WHERE role_id = ?", (role,))
            c.execute("DELETE FROM org_roles WHERE role_id = ?", (role,))
        left = c.execute(
            "SELECT 1 FROM core_evidence_records WHERE evidence_type = 'work_note' LIMIT 1"
        ).fetchone()
        if left is None:
            c.execute("DELETE FROM core_evidence_types WHERE evidence_type = 'work_note'")
        c.commit()
    finally:
        c.close()


def _grant(c, role_id: str, codes: tuple[str, ...], ts: str) -> None:
    for code in codes:
        perm = c.execute(
            "SELECT permission_id FROM org_permissions WHERE code = ?",
            (code,),
        ).fetchone()
        if not perm:
            raise RuntimeError(f"missing permission {code}")
        c.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect = 'ALLOW', updated_at = excluded.updated_at
            """,
            (role_id, perm["permission_id"], ts, ts),
        )


def _seat(c, person_id, email, role_id, position_id, assignment_id, perms, ts) -> None:
    c.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, ?, NULL, 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (role_id, role_id, ts, ts),
    )
    _grant(c, role_id, perms, ts)
    c.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, NULL, NULL, ?, 'ACTIVE', 1, ?, ?)
        """,
        (position_id, role_id, ENTITY, role_id, ts, ts),
    )
    c.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, ?, ?, 'ACTIVE', ?, ?)
        """,
        (person_id, "P4 seat", "P4 seat", ts, ts),
    )
    c.execute(
        """
        INSERT INTO org_auth_identities (
          auth_identity_id, person_id, provider, identifier, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
        """,
        (f"AUTH-{assignment_id}", person_id, email, ts, ts),
    )
    c.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        """,
        (assignment_id, person_id, position_id, ts, ts, ts),
    )
    c.execute(
        """
        INSERT INTO org_assignment_scopes (
          assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
        """,
        (assignment_id, SCOPE, ts, ts, ts),
    )


def _section(payload: dict, key: str) -> dict:
    for block in payload.get("sections") or []:
        if block.get("key") == key:
            return block
    return {"items": [], "empty": True}


def _has_title(payload: dict, key: str, title: str) -> bool:
    return any(i.get("title") == title for i in _section(payload, key).get("items") or [])


def main() -> int:
    global PASS, FAIL
    prod_before = _listen_pid(8787)
    check("prod listener unchanged at start", prod_before == PROD_PID, prod_before or "down")
    limits_before = evr_before = sod_before = 0
    c = _conn()
    try:
        limits_before = c.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        evr_before = c.execute(
            "SELECT COUNT(*) FROM core_evidence_requirements WHERE status = 'ACTIVE'"
        ).fetchone()[0]
        sod_before = c.execute(
            "SELECT COUNT(*) FROM core_sod_constraints WHERE status = 'ACTIVE'"
        ).fetchone()[0]
    finally:
        c.close()

    _purge()
    ts = wi.now_utc_iso()
    c = _conn()
    try:
        _seat(c, WORKER_ID, WORKER_EMAIL, ROLE_WORKER, WORKER_POS, WORKER_ASG, WORKER_PERMS, ts)
        _seat(c, APPROVER_ID, APPROVER_EMAIL, ROLE_APPROVER, APPROVER_POS, APPROVER_ASG, APPROVER_PERMS, ts)
        _seat(c, DELEGATE_ID, DELEGATE_EMAIL, ROLE_DELEGATE, DELEGATE_POS, DELEGATE_ASG, DELEGATE_PERMS, ts)
        _seat(c, SOD_ID, SOD_EMAIL, ROLE_SOD, SOD_POS, SOD_ASG, SOD_PERMS, ts)
        c.commit()
    finally:
        c.close()

    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if obj.__name__ == "BetaHandler":
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        print(f"PASS={PASS} FAIL={FAIL}")
        return 1

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(method: str, path: str, subject: str | None, payload: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.status, resp.read()
        except HTTPError as exc:
            return exc.code, exc.read()

    def body(status: int, raw: bytes) -> dict:
        try:
            return json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            return {"_raw": raw[:200], "_status": status}

    def home(subject: str) -> dict:
        status, raw = call("GET", "/api/staff/home", subject)
        data = body(status, raw)
        data["_status"] = status
        return data

    ordinary_id = ""
    try:
        st, raw = call("GET", "/api/work-loop/items/none", None)
        check("anon open 403", st == 403, str(st))
        st, raw = call("POST", "/api/work-loop/money", WORKER_EMAIL, {})
        check("money route refused", st == 405, str(st))

        st, raw = call(
            "POST",
            "/api/work-loop/items",
            WORKER_EMAIL,
            {
                "title": "P4-TEST ordinary approval",
                "owning_entity_id": ENTITY,
                "role_id": ROLE_WORKER,
                "scope_id": SCOPE,
                "work_type": "GENERAL",
            },
        )
        created = body(st, raw)
        ordinary_id = ((created.get("work_item") or {}).get("work_item_id")) or ""
        check("ordinary created", st == 201 and bool(ordinary_id), str(st))
        check(
            "assigned by role not by a typed name",
            (created.get("work_item") or {}).get("owner_person_id") == WORKER_ID
            and (created.get("work_item") or {}).get("owner_org_assignment_id") == WORKER_ASG,
        )

        worker = home(WORKER_EMAIL)
        approver = home(APPROVER_EMAIL)
        check("worker sees it today", worker["_status"] == 200 and _has_title(worker, "today", "P4-TEST ordinary approval"))
        check("approver does not see the worker queue", not _has_title(approver, "today", "P4-TEST ordinary approval"))
        haikal = home(HAIKAL)
        check("other role does not see it", not _has_title(haikal, "today", "P4-TEST ordinary approval"))

        st, raw = call("POST", f"/api/work-loop/items/{ordinary_id}/submit", WORKER_EMAIL, {})
        submitted = body(st, raw)
        check("ordinary submit", st == 200 and (submitted.get("approval") or {}).get("status") == "PENDING", str(submitted)[:300])
        worker = home(WORKER_EMAIL)
        check("worker is waiting", _has_title(worker, "waiting", "P4-TEST ordinary approval"))
        check("worker today cleared", not _has_title(worker, "today", "P4-TEST ordinary approval"))

        c = _conn()
        try:
            c.execute(
                "UPDATE org_assignments SET status = 'ENDED', end_at = ?, updated_at = ? WHERE assignment_id = ?",
                (ts, ts, APPROVER_ASG),
            )
            _seat(
                c,
                APPROVER2_ID,
                APPROVER2_EMAIL,
                ROLE_APPROVER,
                APPROVER2_POS,
                APPROVER2_ASG,
                APPROVER_PERMS,
                ts,
            )
            c.commit()
        finally:
            c.close()
        inherited = home(APPROVER2_EMAIL)
        check(
            "replacement approver inherits the queue",
            _has_title(inherited, "attention", "P4-TEST ordinary approval"),
            json.dumps(inherited.get("sections"), default=str)[:400],
        )
        st, raw = call(
            "POST",
            f"/api/work-loop/items/{ordinary_id}/decide",
            APPROVER2_EMAIL,
            {"decision": "APPROVE", "reason": "Ordinary approval recorded."},
        )
        decided = body(st, raw)
        check(
            "ordinary approved",
            st == 200 and (decided.get("work_item") or {}).get("status") == "COMPLETED",
            str(decided)[:400],
        )
        check(
            "decision basis is native",
            (decided.get("decision") or {}).get("authority_basis_type") == "NATIVE",
            str((decided.get("decision") or {}).get("authority_basis_type")),
        )
        worker = home(WORKER_EMAIL)
        check("worker sees it done", _has_title(worker, "completed", "P4-TEST ordinary approval"))
        owner = home(MATT)
        check("owner pulse shows it done", _has_title(owner, "improving", "P4-TEST ordinary approval"))
        st, raw = call("GET", "/api/progress/governance-loop", MATT)
        progress = body(st, raw)
        done_titles = [i.get("title") for i in progress.get("completed") or []]
        check("progress live", st == 200 and progress.get("freshness") == "LIVE", str(progress)[:240])
        check("progress shows done", "P4-TEST ordinary approval" in done_titles, str(done_titles)[:240])
        check(
            "audit written",
            loop.audit_count_for(ordinary_id) >= 1
            and loop.audit_count_for((submitted.get("approval") or {}).get("approval_request_id") or "") >= 1,
        )

        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        check("chrome present", chrome.is_file())
        if chrome.is_file() and ordinary_id:
            class _Proxy(BaseHTTPRequestHandler):
                def log_message(self, *_args):  # noqa: ANN002
                    return

                def do_GET(self):  # noqa: N802
                    req = Request(
                        f"http://127.0.0.1:{port}{self.path}",
                        headers={"X-Wolf-Subject": WORKER_EMAIL, "Accept": "*/*"},
                        method="GET",
                    )
                    try:
                        with urlopen(req, timeout=30) as resp:
                            payload = resp.read()
                            ctype = resp.headers.get("Content-Type") or "text/html"
                            code = resp.status
                    except HTTPError as exc:
                        payload = exc.read()
                        ctype = exc.headers.get("Content-Type") if exc.headers else "text/html"
                        code = exc.code
                    self.send_response(code)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

            proxy = ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
            pport = proxy.server_address[1]
            threading.Thread(target=proxy.serve_forever, daemon=True).start()
            try:
                for width in (390, 1280):
                    proc = subprocess.run(
                        [
                            str(chrome),
                            "--headless=new",
                            "--disable-gpu",
                            "--virtual-time-budget=8000",
                            f"--window-size={width},844",
                            "--dump-dom",
                            f"http://127.0.0.1:{pport}/my-work/item/{ordinary_id}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=40,
                    )
                    dom = proc.stdout or ""
                    check(f"item page {width} shows the work", "P4-TEST ordinary approval" in dom, proc.stderr[-160:])
                    check(
                        f"item page {width} laid out",
                        'data-ready="1"' in dom and 'data-overflow="no"' in dom,
                    )
            finally:
                proxy.shutdown()

        # Missing evidence blocks submit, then evidence allows it.
        ev.insert_evidence_requirement_for_test(
            entity_id=ENTITY,
            action_type=loop.EVIDENCE_ACTION,
            evidence_type=loop.EVIDENCE_TYPE,
            requirement_id=EVR_ID,
            scope_id=SCOPE,
            min_count=1,
            verification_needed=0,
            allow_test_write=True,
            verified_person_id=MATT_ID,
        )
        st, raw = call(
            "POST",
            "/api/work-loop/items",
            WORKER_EMAIL,
            {
                "title": "P4-TEST missing evidence",
                "owning_entity_id": ENTITY,
                "role_id": ROLE_WORKER,
                "scope_id": SCOPE,
            },
        )
        missing = body(st, raw)
        missing_id = (missing.get("work_item") or {}).get("work_item_id")
        st, raw = call("POST", f"/api/work-loop/items/{missing_id}/submit", WORKER_EMAIL, {})
        blocked = body(st, raw)
        check("missing evidence blocks submit", st == 403 and blocked.get("error") == "missing_required_evidence", str(blocked)[:300])
        c = _conn()
        try:
            n_ap = c.execute(
                "SELECT COUNT(*) FROM core_approval_requests WHERE linked_work_item_id = ?",
                (missing_id,),
            ).fetchone()[0]
        finally:
            c.close()
        check("no approval row when evidence is missing", n_ap == 0, str(n_ap))
        st, raw = call(
            "POST",
            f"/api/work-loop/items/{missing_id}/evidence",
            WORKER_EMAIL,
            {"note": "P4-TEST note attached for the gate."},
        )
        check("evidence attached", st == 200, body(st, raw).get("error", ""))
        c = _conn()
        try:
            c.execute(
                "DELETE FROM core_evidence_requirements WHERE requirement_id = ?",
                (EVR_ID,),
            )
            c.commit()
        finally:
            c.close()

        # Denied authority. Limit is removed in cleanup.
        c = _conn()
        try:
            c.execute(
                """
                INSERT INTO org_authority_limits (
                  authority_limit_id, role_id, assignment_id, permission_id, scope_id,
                  limit_type, currency, threshold_value, comparison_rule,
                  effective_from, effective_to, status, created_at, updated_at
                ) VALUES (?, ?, NULL, ?, NULL, 'AMOUNT', 'IDR', 10, 'LTE_INCLUSIVE',
                          '2026-01-01T00:00:00+00:00', NULL, 'active', ?, ?)
                """,
                (LIMIT_ID, ROLE_APPROVER, PERM_DECIDE, ts, ts),
            )
            c.commit()
        finally:
            c.close()
        st, raw = call(
            "POST",
            "/api/work-loop/items",
            WORKER_EMAIL,
            {
                "title": "P4-TEST denied authority",
                "owning_entity_id": ENTITY,
                "role_id": ROLE_WORKER,
                "scope_id": SCOPE,
            },
        )
        denied_id = (body(st, raw).get("work_item") or {}).get("work_item_id")
        st, raw = call(
            "POST",
            f"/api/work-loop/items/{denied_id}/submit",
            WORKER_EMAIL,
            {"request_type": "SPEND", "material_amount": "100.00", "currency": "IDR"},
        )
        check("spend submitted", st == 200, body(st, raw).get("error", str(st)))
        st, raw = call(
            "POST",
            f"/api/work-loop/items/{denied_id}/decide",
            APPROVER2_EMAIL,
            {"decision": "APPROVE", "reason": "This amount is above the limit."},
        )
        denied = body(st, raw)
        check("authority denied", st == 403 and denied.get("error") == "authority_denied", str(denied)[:300])
        st, raw = call("GET", f"/api/work-loop/items/{denied_id}", WORKER_EMAIL)
        denied_open = body(st, raw)
        check(
            "denied item is not completed",
            (denied_open.get("work_item") or {}).get("status") != "COMPLETED",
            str((denied_open.get("work_item") or {}).get("status")),
        )
        c = _conn()
        try:
            c.execute("DELETE FROM org_authority_limits WHERE authority_limit_id = ?", (LIMIT_ID,))
            c.commit()
        finally:
            c.close()

        # Delegated authority. Non-material, so the amount cap is not in play.
        now = datetime.now(timezone.utc)
        created_dlg = dlg.create_delegation(
            verified_person_id=MATT_ID,
            delegate_person_id=DELEGATE_ID,
            delegator_assignment_id="ASG-MATT-OWNER-1",
            delegate_assignment_id=DELEGATE_ASG,
            entity_id=ENTITY,
            scope_id=SCOPE,
            permission_code="approval.decide",
            effective_from=(now - timedelta(minutes=5)).isoformat(),
            effective_to=(now + timedelta(days=1)).isoformat(),
            reason="P4-TEST delegation for a seated role.",
        )
        st, raw = call(
            "POST",
            "/api/work-loop/items",
            WORKER_EMAIL,
            {
                "title": "P4-TEST delegated approval",
                "owning_entity_id": ENTITY,
                "role_id": ROLE_WORKER,
                "scope_id": SCOPE,
            },
        )
        dlg_id = (body(st, raw).get("work_item") or {}).get("work_item_id")
        st, raw = call("POST", f"/api/work-loop/items/{dlg_id}/submit", WORKER_EMAIL, {})
        check("delegated item submitted", st == 200, body(st, raw).get("error", str(st)))
        st, raw = call(
            "POST",
            f"/api/work-loop/items/{dlg_id}/decide",
            DELEGATE_EMAIL,
            {"decision": "APPROVE", "reason": "Decided under delegation."},
        )
        delegated = body(st, raw)
        check(
            "delegate approved",
            st == 200 and (delegated.get("decision") or {}).get("authority_basis_type") == "DELEGATION",
            str(delegated)[:400],
        )
        check(
            "delegated item done",
            (delegated.get("work_item") or {}).get("status") == "COMPLETED",
        )
        _ = created_dlg

        # SoD blocks the same person and records an exception. Not authorised.
        sod.insert_sod_constraint_for_test(
            entity_id=ENTITY,
            process_family="APPROVAL",
            prior_action="approval.request",
            proposed_action="approval.decide",
            constraint_id=SOD_CONSTRAINT,
            relationship="SAME_PERSON_FORBIDDEN",
            allow_test_write=True,
            verified_person_id=MATT_ID,
        )
        exmod.insert_exceptionable_control_for_test(
            control_type="SOD_CONSTRAINT",
            control_reference=SOD_CONSTRAINT,
            exceptionable=1,
            allow_test_write=True,
        )
        st, raw = call(
            "POST",
            "/api/work-loop/items",
            SOD_EMAIL,
            {
                "title": "P4-TEST sod block",
                "owning_entity_id": ENTITY,
                "role_id": ROLE_SOD,
                "scope_id": SCOPE,
            },
        )
        sod_work = (body(st, raw).get("work_item") or {}).get("work_item_id")
        st, raw = call("POST", f"/api/work-loop/items/{sod_work}/submit", SOD_EMAIL, {})
        check("sod item submitted", st == 200, body(st, raw).get("error", str(st)))
        st, raw = call(
            "POST",
            f"/api/work-loop/items/{sod_work}/decide",
            SOD_EMAIL,
            {"decision": "APPROVE", "reason": "Same person must not approve this."},
        )
        sod_denied = body(st, raw)
        check(
            "sod blocked",
            st == 403 and sod_denied.get("error") == "sod_same_person_conflict",
            str(sod_denied)[:300],
        )
        exception = sod_denied.get("exception") or {}
        check(
            "exception requested not authorised",
            exception.get("status") == "REQUESTED" and exception.get("authorised_by_person_id") in (None, ""),
            str(exception)[:300],
        )
        owner = home(MATT)
        check(
            "owner sees the exception",
            _has_title(owner, "wrong", "Separation of duties blocked this approval.")
            or _has_title(owner, "authority", "Separation of duties blocked this approval."),
            json.dumps([s.get("key") for s in owner.get("sections") or []]),
        )
        c = _conn()
        try:
            c.execute("DELETE FROM core_sod_constraints WHERE constraint_id = ?", (SOD_CONSTRAINT,))
            c.execute(
                "DELETE FROM core_exceptionable_controls WHERE control_reference = ?",
                (SOD_CONSTRAINT,),
            )
            c.commit()
        finally:
            c.close()

        # Rejected work returns to the assigned role.
        st, raw = call(
            "POST",
            "/api/work-loop/items",
            WORKER_EMAIL,
            {
                "title": "P4-TEST rejected return",
                "owning_entity_id": ENTITY,
                "role_id": ROLE_WORKER,
                "scope_id": SCOPE,
            },
        )
        reject_id = (body(st, raw).get("work_item") or {}).get("work_item_id")
        st, raw = call("POST", f"/api/work-loop/items/{reject_id}/submit", WORKER_EMAIL, {})
        check("reject path submitted", st == 200, body(st, raw).get("error", str(st)))
        st, raw = call(
            "POST",
            f"/api/work-loop/items/{reject_id}/decide",
            APPROVER2_EMAIL,
            {"decision": "REJECT", "reason": "Returned to the assigned role."},
        )
        rejected = body(st, raw)
        check(
            "rejected returns in progress",
            st == 200 and (rejected.get("work_item") or {}).get("status") == "IN_PROGRESS",
            str(rejected)[:300],
        )
        worker = home(WORKER_EMAIL)
        check("rejected item is back today", _has_title(worker, "today", "P4-TEST rejected return"))
        check("rejected item left the waiting list", not _has_title(worker, "waiting", "P4-TEST rejected return"))

        # Replacement employee inherits the open queue.
        st, raw = call(
            "POST",
            "/api/work-loop/items",
            WORKER_EMAIL,
            {
                "title": "P4-TEST replacement queue",
                "owning_entity_id": ENTITY,
                "role_id": ROLE_WORKER,
                "scope_id": SCOPE,
            },
        )
        repl_work = (body(st, raw).get("work_item") or {}).get("work_item_id")
        c = _conn()
        try:
            c.execute(
                "UPDATE org_assignments SET status = 'ENDED', end_at = ?, updated_at = ? WHERE assignment_id = ?",
                (ts, ts, WORKER_ASG),
            )
            _seat(
                c,
                REPLACE_ID,
                REPLACE_EMAIL,
                ROLE_WORKER,
                REPLACE_POS,
                REPLACE_ASG,
                WORKER_PERMS,
                ts,
            )
            c.commit()
        finally:
            c.close()
        replaced = home(REPLACE_EMAIL)
        gone = home(WORKER_EMAIL)
        check(
            "replacement inherits the work queue",
            _has_title(replaced, "today", "P4-TEST replacement queue"),
            json.dumps(replaced.get("sections"), default=str)[:300],
        )
        check("ended assignment no longer has a home", gone.get("_status") == 403, str(gone.get("_status")))
        st, raw = call("GET", f"/api/work-loop/items/{repl_work}", REPLACE_EMAIL)
        check("replacement can open it", st == 200, str(st))
    finally:
        httpd.shutdown()
        _purge()
        c = _conn()
        try:
            limits_after = c.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
            evr_after = c.execute(
                "SELECT COUNT(*) FROM core_evidence_requirements WHERE status = 'ACTIVE'"
            ).fetchone()[0]
            sod_after = c.execute(
                "SELECT COUNT(*) FROM core_sod_constraints WHERE status = 'ACTIVE'"
            ).fetchone()[0]
            leftover = c.execute(
                "SELECT COUNT(*) FROM core_work_items WHERE title LIKE 'P4-TEST%' OR source_id = 'P4-TEST'"
            ).fetchone()[0]
            pending = c.execute(
                "SELECT COUNT(*) FROM core_approval_requests WHERE title LIKE 'P4-TEST%' AND status = 'PENDING'"
            ).fetchone()[0]
            people = c.execute(
                "SELECT COUNT(*) FROM org_persons WHERE person_id LIKE 'PERS-P4-%'"
            ).fetchone()[0]
        finally:
            c.close()
        check("authority limits restored", limits_after == limits_before, f"{limits_before} -> {limits_after}")
        check("evidence requirements restored", evr_after == evr_before, f"{evr_before} -> {evr_after}")
        check("sod constraints restored", sod_after == sod_before, f"{sod_before} -> {sod_after}")
        check("test work removed", leftover == 0, str(leftover))
        check("no pending test approvals", pending == 0, str(pending))
        check("test people removed", people == 0, str(people))
        prod_after = _listen_pid(8787)
        check("prod listener unchanged at end", prod_after == PROD_PID, prod_after or "down")

    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
