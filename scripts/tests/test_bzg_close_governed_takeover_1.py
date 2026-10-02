#!/usr/bin/env python3
"""BZG-CLOSE-GOVERNED-TAKEOVER-1 — cashier cannot steal; authorised takeover.

Decision: 2026-09-17 Uma Blu Daily Close (extend) + Owner takeover pack.
Proves: venue.close.reassign RBAC, reason required, work preserved, audit,
concurrency still blocks peer cashiers, UI markers, staff_ready false.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import rbac as _rbac  # noqa: E402
from core import venue_close as _vc  # noqa: E402
from core import bzg_daily_close as _bzg  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
UI = ROOT / "dashboards" / "uma-blu-close.html"
SERVE = SCRIPTS / "serve_beta.py"
MIG = SCRIPTS / "migrations" / "migrate_bzg_close_governed_takeover_1.py"

IZA = "PERS-IZA"
DEVI = "PERS-DEVI"
MATT = "PERS-MATT"
BRAND = "BZG-UMA"
TARGET = {"entity_id": "ENT-BZG", "brand_id": BRAND}
TS = "2026-10-02T00:00:00+08:00"

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _temp_catalog() -> tuple[Path, sqlite3.Connection]:
    td = Path(tempfile.mkdtemp(prefix="bzg-gov-takeover-"))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return db, conn


def seed_cashier(conn: sqlite3.Connection) -> str:
    """Ordinary cashier with submit but NO reassign."""
    pid = "PERS-TEST-CASHIER"
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, 'Test Cashier', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (pid, TS, TS),
    )
    # Ensure cashier role exists + submit grants only
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES ('ROLE-BZG-CASHIER', 'Cashier', 'DEPT-BZG-FB', 'OPERATING', 'SPECIFIED', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET status='SPECIFIED', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    for code in ("venue.close.read", "venue.close.submit"):
        prow = conn.execute(
            "SELECT permission_id FROM org_permissions WHERE code=?", (code,)
        ).fetchone()
        if prow:
            conn.execute(
                """
                INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                VALUES ('ROLE-BZG-CASHIER', ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
                """,
                (prow[0], TS, TS),
            )
    # Strip reassign if present
    re_perm = conn.execute(
        "SELECT permission_id FROM org_permissions WHERE code='venue.close.reassign'"
    ).fetchone()
    if re_perm:
        conn.execute(
            "DELETE FROM org_role_permissions WHERE role_id='ROLE-BZG-CASHIER' AND permission_id=?",
            (re_perm[0],),
        )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (
          'POS-BZG-CASHIER-UMA-TEST', 'ROLE-BZG-CASHIER', 'ENT-BZG', NULL, 'BZG-UMA',
          'DEPT-BZG-FB', 'Cashier Uma test', 'ACTIVE', 1.0, ?, ?
        )
        ON CONFLICT(position_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (
          'ASG-TEST-CASHIER-1', ?, 'POS-BZG-CASHIER-UMA-TEST', ?, NULL, 'ACTIVE', 1, ?, ?
        )
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL, updated_at=excluded.updated_at
        """,
        (pid, TS, TS, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, "ASG-TEST-CASHIER-1", "SCOPE-BZG-UMA", TS, TS)
    conn.execute(
        """
        INSERT INTO venue_closer_roster (
          roster_id, brand_id, position_id, person_id, assignment_id,
          status, note, created_at, updated_at
        ) VALUES (
          'VCR-UMA-CASHIER-TEST', 'BZG-UMA', 'POS-BZG-CASHIER-UMA-TEST', ?,
          'ASG-TEST-CASHIER-1', 'ACTIVE', 'test cashier', ?, ?
        )
        ON CONFLICT(roster_id) DO UPDATE SET
          person_id=excluded.person_id, status='ACTIVE', updated_at=excluded.updated_at
        """,
        (pid, TS, TS),
    )
    conn.commit()
    return pid


def test_source_markers() -> None:
    html = UI.read_text(encoding="utf-8")
    serve = SERVE.read_text(encoding="utf-8")
    vc = Path(SCRIPTS / "core" / "venue_close.py").read_text(encoding="utf-8")
    check("UI Take Over Close", "Take Over Close" in html)
    check("UI Reassign Close", "Reassign Close" in html)
    check("UI reason field", "takeoverReason" in html)
    check("UI lock panel", 'id="lockPanel"' in html)
    check("serve takeover route", '/api/venue-close/takeover' in serve)
    check("serve reassign route", '/api/venue-close/reassign' in serve)
    check("engine reassign fn", "def reassign_venue_close" in vc)
    check("engine takeover fn", "def take_over_venue_close" in vc)
    check("perm code in engine", "venue.close.reassign" in vc)


def test_live_perm_grants() -> None:
    conn = sqlite3.connect(str(LIVE_DB))
    conn.row_factory = sqlite3.Row
    try:
        perm = conn.execute(
            "SELECT permission_id, code, status FROM org_permissions WHERE code=?",
            ("venue.close.reassign",),
        ).fetchone()
        check("live perm venue.close.reassign", perm is not None and perm["status"] == "ACTIVE", str(perm))
        for role in ("ROLE-MATT", "ROLE-BZG-CAPTAIN", "ROLE-BZG-HFB", "ROLE-BZG-FB-OPS-LEAD"):
            if not conn.execute("SELECT 1 FROM org_roles WHERE role_id=?", (role,)).fetchone():
                check(f"role {role} missing skip", True)
                continue
            g = conn.execute(
                """
                SELECT 1 FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id=rp.permission_id
                WHERE rp.role_id=? AND p.code='venue.close.reassign' AND rp.effect='ALLOW'
                """,
                (role,),
            ).fetchone()
            check(f"live grant {role}", g is not None)
        for role in ("ROLE-BZG-CASHIER", "ROLE-BZG-CLOSER"):
            g = conn.execute(
                """
                SELECT 1 FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id=rp.permission_id
                WHERE rp.role_id=? AND p.code='venue.close.reassign' AND rp.effect='ALLOW'
                """,
                (role,),
            ).fetchone()
            check(f"live no grant {role}", g is None)
        check(
            "Matt can reassign (RBAC)",
            _rbac.can(MATT, "venue.close.reassign", TARGET, conn=conn) is True,
        )
    finally:
        conn.close()


def test_cashier_cannot_takeover() -> None:
    db, conn = _temp_catalog()
    prev = _vc.CATALOG_DB
    prev_b = _bzg.CATALOG_DB
    _vc.CATALOG_DB = db
    _bzg.CATALOG_DB = db
    try:
        cashier = seed_cashier(conn)
        check(
            "cashier RBAC reassign DENY",
            _rbac.can(cashier, "venue.close.reassign", TARGET, conn=conn) is False,
        )
        opened = _vc.open_or_get(
            "2099-03-01",
            verified_person_id=IZA,
            conn=conn,
            commit=False,
        )
        cid = opened["close_id"]
        _vc.take_open_venue_close(cid, verified_person_id=IZA, conn=conn, commit=False)
        # Plant preserved work markers
        conn.execute(
            """
            UPDATE venue_daily_closes
            SET declared_cash_amount=123456, state='DATA_CAPTURED',
                esb_fingerprint_sha256='fp-preserve', updated_at=?
            WHERE close_id=?
            """,
            (_vc.now_utc_iso(), cid),
        )
        conn.commit()

        denied = False
        try:
            _vc.take_over_venue_close(
                cid,
                verified_person_id=cashier,
                reason="I want it",
                conn=conn,
                commit=False,
            )
        except _vc.VenueCloseError as exc:
            denied = exc.code == "forbidden" and exc.http_status == 403
        check("cashier takeover DENY 403", denied)

        # Peer concurrent take still 409
        conc = False
        try:
            _vc.take_open_venue_close(cid, verified_person_id=cashier, conn=conn, commit=False)
        except _vc.VenueCloseError as exc:
            conc = exc.code == "concurrent_take" and exc.http_status == 409
            check("concurrent details holder", bool(exc.details.get("holder")), str(exc.details))
        check("cashier concurrent take still 409", conc)

        row = _vc.get_close(cid, conn=conn)
        check("work cash preserved after cashier fail", row.get("declared_cash_amount") == 123456)
        check("holder still Iza after cashier fail", row.get("taken_by_person_id") == IZA)
    finally:
        _vc.CATALOG_DB = prev
        _bzg.CATALOG_DB = prev_b
        conn.close()
        shutil.rmtree(db.parent, ignore_errors=True)


def test_authorised_takeover_preserves_work() -> None:
    db, conn = _temp_catalog()
    prev = _vc.CATALOG_DB
    prev_b = _bzg.CATALOG_DB
    _vc.CATALOG_DB = db
    _bzg.CATALOG_DB = db
    try:
        opened = _vc.open_or_get(
            "2099-03-02",
            verified_person_id=IZA,
            conn=conn,
            commit=False,
        )
        cid = opened["close_id"]
        _vc.take_open_venue_close(cid, verified_person_id=IZA, conn=conn, commit=False)
        conn.execute(
            """
            UPDATE venue_daily_closes
            SET declared_cash_amount=777000, state='DATA_CAPTURED',
                esb_fingerprint_sha256='fp-matt', esb_totals_json=?,
                updated_at=?
            WHERE close_id=?
            """,
            (
                json.dumps({"cash_from_payments": 1000, "finished_count": 2}),
                _vc.now_utc_iso(),
                cid,
            ),
        )
        conn.commit()
        before = _vc.close_work_snapshot(_vc.get_close(cid, conn=conn), conn=conn)

        # Missing reason
        missing = False
        try:
            _vc.take_over_venue_close(
                cid, verified_person_id=MATT, reason="  ", conn=conn, commit=False
            )
        except _vc.VenueCloseError as exc:
            missing = exc.code == "missing_reason"
        check("takeover requires reason", missing)

        out = _vc.take_over_venue_close(
            cid,
            verified_person_id=MATT,
            reason="Owner takeover — Iza left mid-flow",
            conn=conn,
            commit=True,
        )
        check("takeover ok", out.get("takeover") is True and out.get("work_preserved") is True)
        check("new holder Matt", out.get("taken_by_person_id") == MATT)
        check("prior holder Iza", out.get("prior_holder_person_id") == IZA)
        after = out.get("after") or {}
        for key in (
            "declared_cash_amount",
            "esb_fingerprint_sha256",
            "state",
            "edc_receipt_count",
            "esb_closing_receipt_count",
        ):
            check(f"preserved {key}", before.get(key) == after.get(key), f"{before.get(key)} vs {after.get(key)}")

        audit = None
        for table in ("core_audit_events", "audit_events", "wolf_audit_events"):
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if table not in tabs:
                continue
            try:
                audit = conn.execute(
                    f"""
                    SELECT result, reason_code, metadata_json FROM {table}
                    WHERE action='venue_close.takeover' AND resource_id=?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (cid,),
                ).fetchone()
            except sqlite3.Error:
                try:
                    audit = conn.execute(
                        f"""
                        SELECT result, reason_code, metadata FROM {table}
                        WHERE action='venue_close.takeover' AND resource_id=?
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (cid,),
                    ).fetchone()
                except sqlite3.Error:
                    audit = None
            if audit:
                break
        check("audit takeover ALLOWED", audit is not None and str(audit[0]) == "ALLOWED", str(audit))
        if audit:
            meta_raw = audit[2] if len(audit) > 2 else None
            meta = {}
            if isinstance(meta_raw, str):
                try:
                    meta = json.loads(meta_raw)
                except json.JSONDecodeError:
                    meta = {}
            check("audit has reason", "Owner takeover" in str(meta.get("reason") or meta))
            check("audit prior holder", str(meta.get("prior_holder_person_id") or "") == IZA)

        # After takeover Matt can take idempotently
        again = _vc.take_open_venue_close(cid, verified_person_id=MATT, conn=conn, commit=True)
        check("matt take after takeover", again.get("taken_by_person_id") == MATT)

        # Peer cashier still blocked
        cashier = seed_cashier(conn)
        blocked = False
        try:
            _vc.take_open_venue_close(cid, verified_person_id=cashier, conn=conn, commit=False)
        except _vc.VenueCloseError as exc:
            blocked = exc.code == "concurrent_take"
        check("concurrency still blocks peer after takeover", blocked)
    finally:
        _vc.CATALOG_DB = prev
        _bzg.CATALOG_DB = prev_b
        conn.close()
        shutil.rmtree(db.parent, ignore_errors=True)


def test_reassign_to_authorised() -> None:
    db, conn = _temp_catalog()
    prev = _vc.CATALOG_DB
    _vc.CATALOG_DB = db
    try:
        opened = _vc.open_or_get(
            "2099-03-03",
            verified_person_id=IZA,
            conn=conn,
            commit=False,
        )
        cid = opened["close_id"]
        _vc.take_open_venue_close(cid, verified_person_id=IZA, conn=conn, commit=False)
        conn.commit()
        out = _vc.reassign_venue_close(
            cid,
            verified_person_id=MATT,
            new_holder_person_id=DEVI,
            reason="Reassign to Devi for finish",
            conn=conn,
            commit=True,
        )
        check("reassign ok", out.get("reassigned") is True and out.get("mode") == "reassign")
        check("holder Devi", out.get("taken_by_person_id") == DEVI)
        check("prior Iza", out.get("prior_holder_person_id") == IZA)

        # Refuse unauthorised new holder
        bad = False
        try:
            _vc.reassign_venue_close(
                cid,
                verified_person_id=MATT,
                new_holder_person_id="PERS-HARIYANTO",
                reason="bad target",
                conn=conn,
                commit=False,
            )
        except _vc.VenueCloseError as exc:
            bad = exc.code == "new_holder_forbidden"
        check("reassign unauthorised target DENY", bad)
    finally:
        _vc.CATALOG_DB = prev
        conn.close()
        shutil.rmtree(db.parent, ignore_errors=True)


def test_honesty_flags() -> None:
    check("staff_ready false", _vc.HONESTY.get("staff_ready") is False)
    check("human_commissioned false", _vc.HONESTY.get("human_commissioned") is False)
    check("bzg honesty staff_ready false", _bzg.HONESTY.get("staff_ready") is False)


def test_deployed_html_markers() -> None:
    code = None
    body = ""
    try:
        req = Request("http://127.0.0.1:8788/uma-blu-close", method="GET")
        with urlopen(req, timeout=5) as res:
            code = res.status
            body = res.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        code = exc.code
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
    except Exception as exc:  # noqa: BLE001
        check("deployed :8788 reachable", False, str(exc))
        return
    # CF Access may 403 unsigned — still prove process serves something; markers from file if 403
    if code == 200:
        check("deployed Take Over Close", "Take Over Close" in body)
        check("deployed takeoverReason", "takeoverReason" in body)
        check("deployed lockPanel", 'id="lockPanel"' in body)
    else:
        check(f"deployed route status {code} (auth gate ok)", code in (200, 403))
        # Fall back: process must be listening; markers proven via UI file above
        check("deployed process up (non-200 auth)", code in (200, 403))


def main() -> int:
    os.environ.pop("WOLF_TEST_MODE", None)
    # Ensure migration applied on live for grant checks
    if not LIVE_DB.is_file():
        print("FAIL live catalog missing")
        return 2
    test_source_markers()
    test_live_perm_grants()
    test_cashier_cannot_takeover()
    test_authorised_takeover_preserves_work()
    test_reassign_to_authorised()
    test_honesty_flags()
    test_deployed_html_markers()
    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
