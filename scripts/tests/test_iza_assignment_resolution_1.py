#!/usr/bin/env python3
"""IZA-ASSIGNMENT-RESOLUTION-1 — roster→tonight's open close (Beta).

Authorisation (Assignment → Captain⊇Cashier/CLOSER → venue_closer_roster) is
distinct from take/submit attribution. Multi-closer OK. No RBAC loosen, no
email special-case, no person-per-day invent as the only path.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import identity as _identity  # noqa: E402
from core import venue_close as _vc  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
SERVE = SCRIPTS / "serve_beta.py"

IZA = "PERS-IZA"
IZA_EMAIL = "izazaen00@gmail.com"
DEVI = "PERS-DEVI"
HARIYANTO = "PERS-HARIYANTO"
BRAND_UMA = "BZG-UMA"
BRAND_OTHER = "BZG-OTHER-FAKE"

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


def _authz(pid: str | None, brand: str = BRAND_UMA, conn: sqlite3.Connection | None = None):
    return _vc.person_authorised_for_venue_close(pid, venue_brand_id=brand, conn=conn)


def _temp_catalog() -> tuple[Path, sqlite3.Connection]:
    td = Path(tempfile.mkdtemp(prefix="iza-asg-res-"))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return db, conn


def test_live_authorisation() -> None:
    conn = sqlite3.connect(str(LIVE_DB))
    conn.row_factory = sqlite3.Row
    try:
        iza = _authz(IZA, conn=conn)
        check("Iza authorised Uma close = ALLOW", iza.get("allowed") is True, str(iza))
        check("Iza via roster", iza.get("via") == "roster", str(iza))
        check("Iza roster VCR-UMA-2", iza.get("roster_id") == "VCR-UMA-2", str(iza))
        check("Iza role CAPTAIN", iza.get("role_id") == "ROLE-BZG-CAPTAIN", str(iza))

        devi = _authz(DEVI, conn=conn)
        check("Devi authorised Uma close = ALLOW", devi.get("allowed") is True, str(devi))
        # Devi may match oversight (FB-OPS-LEAD) before roster — either is valid ALLOW.
        check(
            "Devi via oversight or roster",
            devi.get("via") in {"oversight", "roster"},
            str(devi),
        )

        chef = _authz(HARIYANTO, conn=conn)
        check(
            "unauthorised BZG employee = DENY",
            chef.get("allowed") is False,
            str(chef),
        )

        wrong = _authz(IZA, brand=BRAND_OTHER, conn=conn)
        check(
            "authorised person wrong outlet = DENY",
            wrong.get("allowed") is False,
            str(wrong),
        )

        anon = _authz(None, conn=conn)
        check("anonymous = DENY", anon.get("allowed") is False, str(anon))
        check("anonymous reason", anon.get("reason") == "anonymous", str(anon))
    finally:
        conn.close()


def test_inactive_assignment() -> None:
    _db, conn = _temp_catalog()
    try:
        conn.execute(
            "UPDATE org_assignments SET status='ENDED', end_at=? WHERE assignment_id=?",
            ("2026-10-02T12:00:00+08:00", "ASG-IZA-CAPTAIN-UMA-1"),
        )
        conn.commit()
        # Point module CATALOG_DB at temp for any helpers that open their own conn
        prev = _vc.CATALOG_DB
        _vc.CATALOG_DB = _db
        try:
            denied = _authz(IZA, conn=conn)
            check(
                "inactive assignment = DENY",
                denied.get("allowed") is False,
                str(denied),
            )
        finally:
            _vc.CATALOG_DB = prev
    finally:
        conn.close()
        shutil.rmtree(_db.parent, ignore_errors=True)


def test_identity_path_iza() -> None:
    bound = _identity.resolve_verified_person(IZA_EMAIL)
    check("CF identity path binds PERS-IZA", bound.get("ok") is True and bound.get("person_id") == IZA, str(bound))
    if bound.get("ok"):
        authz = _authz(bound["person_id"])
        check(
            "Iza identity path → Uma close ALLOW",
            authz.get("allowed") is True,
            str(authz),
        )


def test_concurrent_take() -> None:
    db, conn = _temp_catalog()
    prev = _vc.CATALOG_DB
    _vc.CATALOG_DB = db
    os.environ["WOLF_TEST_MODE"] = "1"
    try:
        # Under test mode live writes refuse — CATALOG_DB is temp so OK.
        os.environ.pop("WOLF_TEST_MODE", None)
        _vc.ensure_take_attribution_columns(conn)
        biz = "2099-01-15"
        opened = _vc.open_or_get(
            biz,
            verified_person_id=IZA,
            venue_brand_id=BRAND_UMA,
            conn=conn,
            commit=False,
        )
        cid = opened["close_id"]
        t1 = _vc.take_open_venue_close(cid, verified_person_id=IZA, conn=conn, commit=False)
        check("Iza take ALLOW", t1.get("taken") is True, str(t1))
        check("taken_by Iza", (t1.get("taken_by_person_id") or "") == IZA, str(t1))

        concurrent_denied = False
        audit_denied = False
        try:
            _vc.take_open_venue_close(cid, verified_person_id=DEVI, conn=conn, commit=False)
        except _vc.VenueCloseError as exc:
            concurrent_denied = exc.code == "concurrent_take" and exc.http_status == 409
        # Audit row for concurrent deny
        row = conn.execute(
            """
            SELECT result, reason_code FROM core_audit_events
            WHERE action='venue_close.take' AND resource_id=?
              AND reason_code='concurrent_take'
            ORDER BY created_at DESC LIMIT 1
            """,
            (cid,),
        ).fetchone()
        if row is None:
            # audit table name may differ
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for t in ("core_audit_events", "audit_events", "wolf_audit_events"):
                if t in tabs:
                    try:
                        row = conn.execute(
                            f"""
                            SELECT result, reason_code FROM {t}
                            WHERE action='venue_close.take' AND resource_id=?
                              AND reason_code='concurrent_take'
                            ORDER BY 1 DESC LIMIT 1
                            """,
                            (cid,),
                        ).fetchone()
                    except sqlite3.Error:
                        row = None
                    if row is not None:
                        break
        audit_denied = row is not None and str(row[0]) == "DENIED"
        check("concurrent/taken close = DENY 409", concurrent_denied)
        check("concurrent take audited DENIED", audit_denied, str(row))

        # Idempotent same-person take
        t2 = _vc.take_open_venue_close(cid, verified_person_id=IZA, conn=conn, commit=False)
        check("same-person re-take idempotent", t2.get("taken") is True, str(t2))
        conn.commit()
    finally:
        _vc.CATALOG_DB = prev
        conn.close()
        shutil.rmtree(db.parent, ignore_errors=True)


def test_source_and_http_deny() -> None:
    src = SERVE.read_text(encoding="utf-8")
    check(
        "serve gate uses roster resolution",
        "person_authorised_for_venue_close" in src
        and "This close is not on your assignment." in src,
    )
    check("no Iza email special-case in venue_close authz", IZA_EMAIL not in (_vc.__file__ and Path(_vc.__file__).read_text(encoding="utf-8")))
    check(
        "CLOSE_ROSTER_ROLES includes CAPTAIN+CLOSER+CASHIER",
        {"ROLE-BZG-CAPTAIN", "ROLE-BZG-CLOSER", "ROLE-BZG-CASHIER"} <= set(_vc.CLOSE_ROSTER_ROLES),
    )

    # direct URL bypass / unsigned → DENY (live :8788 if up)
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8788/uma-blu-close",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            code = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        code = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        check("unsigned /uma-blu-close reachable", False, str(exc))
        return
    check("direct URL bypass / unsigned = DENY 403", code == 403, f"status={code}")
    if body.strip().startswith("{"):
        payload = json.loads(body)
        check(
            "unsigned message assignment deny",
            "not on your assignment" in str(payload.get("message") or "").lower()
            or payload.get("error") == "forbidden",
            str(payload)[:200],
        )


def main() -> int:
    test_live_authorisation()
    test_identity_path_iza()
    test_inactive_assignment()
    test_concurrent_take()
    test_source_and_http_deny()
    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
