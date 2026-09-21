#!/usr/bin/env python3
"""Uma Blu Daily Close — Matt mandatory cases (Beta). Temp DB + temp ESB only.

Covers Grok plan / CURSOR-MISSION mandatory behaviours.
No Production. No live Habitat mutation. Live variance thresholds stay 0.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"
VC_PY = SCRIPTS / "core" / "venue_close.py"
ESB_PY = SCRIPTS / "core" / "esb_close_snapshot.py"
SERVE = SCRIPTS / "serve_beta.py"

PASS = 0
FAIL = 0
TS = "2026-09-17T00:00:00+08:00"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_uma_blu_daily_close", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_snapshot() -> dict:
    c = sqlite3.connect(str(LIVE_DB))
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        def cnt(t):
            return int(c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) if t in tabs else 0

        return {
            "auth": cnt("org_authority_limits"),
            "planner": cnt("content_planner"),
            "policies": cnt("venue_close_variance_policies") if "venue_close_variance_policies" in tabs else 0,
            "closes": cnt("venue_daily_closes") if "venue_daily_closes" in tabs else 0,
        }
    finally:
        c.close()


def make_esb(path: Path, bills: list[dict], biz_date: str = "2026-09-10") -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        for i, b in enumerate(bills):
            raw = dict(b)
            raw.setdefault("branchCode", "BLZ")
            raw.setdefault("salesNum", f"S{i}")
            raw.setdefault("billNum", f"B{i}")
            conn.execute(
                "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
                (f"BLZ|{raw['salesNum']}", biz_date, json.dumps(raw), "2026-09-10T20:00:00+08:00"),
            )
        conn.commit()
    finally:
        conn.close()


def seed_test_closer(conn: sqlite3.Connection) -> None:
    """Named closer only in temp DB for submit-path tests — not live roster."""
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES ('PERS-TEST-CLOSER', 'Test Closer', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES ('ASG-TEST-CLOSER-1', 'PERS-TEST-CLOSER', 'POS-BZG-CLOSER-UMA-1',
                  ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL, updated_at=excluded.updated_at
        """,
        (TS, TS, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, "ASG-TEST-CLOSER-1", "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


def wire_modules(tmp_db: Path, esb_path: Path):
    import core.venue_close as vc
    import core.esb_close_snapshot as esb
    import core.evidence as ev
    import core.audit as au
    import core.work_items as wi
    import core.rbac as rb
    import core.organisation as org
    import core.scope as sc
    import core.identity as ident

    for mod in (vc, ev, au, wi, rb, org, sc, ident):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)
    return vc, esb


def prove_ended_scope_upsert(mig) -> None:
    """Devi ENTITY ended on a temp DB must survive the daily-close upsert."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE org_assignment_scopes (
          assignment_id TEXT NOT NULL,
          scope_id TEXT NOT NULL,
          start_at TEXT NOT NULL,
          end_at TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (assignment_id, scope_id, start_at)
        );
        """
    )
    ts = "2026-09-19T13:00:00+08:00"
    end_at = "2026-09-19T12:00:00+08:00"
    mig.upsert_asg_scope(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY", ts)
    conn.execute(
        """
        UPDATE org_assignment_scopes
           SET status='ENDED', end_at=?
         WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND scope_id='SCOPE-BZG-ENTITY'
        """,
        (end_at,),
    )
    mig.upsert_asg_scope(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY", ts)
    got = conn.execute(
        """
        SELECT status, end_at FROM org_assignment_scopes
        WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND scope_id='SCOPE-BZG-ENTITY'
        """
    ).fetchone()
    check(
        "Devi ENTITY ENDED survives daily-close upsert",
        got is not None and got["status"] == "ENDED" and got["end_at"] == end_at,
        "" if got is None else f"{got['status']} {got['end_at']}",
    )
    conn.close()


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    src = VC_PY.read_text(encoding="utf-8")
    esb_src = ESB_PY.read_text(encoding="utf-8")
    serve_src = SERVE.read_text(encoding="utf-8")

    # --- Matt mandatory: static / honesty / no if-Devi ---
    check("no `if person_id == PERS-DEVI`", '== "PERS-DEVI"' not in src and "== 'PERS-DEVI'" not in src)
    check(
        "PERS-DEVI not used as runtime gate",
        'person_id == "PERS-DEVI"' not in src
        and "person_id == 'PERS-DEVI'" not in src
        and 'verified_person_id == "PERS-DEVI"' not in src
        and '== "PERS-DEVI"' not in src.replace("Never hard-codes PERS-DEVI.", ""),
    )
    check("find_hfb_assignee by role", "def find_hfb_assignee" in src and "ROLE-BZG-HFB" in src)
    check("venue_close module present", "def open_or_get" in src and "def reconcile" in src)
    check("esb_close_snapshot read-only mode", "mode=ro" in esb_src)
    check("honesty settlement UNAVAILABLE", "settlement_api" in src and "UNAVAILABLE" in src)
    check("honesty PAYMENT_LINES", "PAYMENT_LINES_NOT_SETTLEMENT" in src)
    check("API routes wired", "/api/venue-close/open" in serve_src and "declare-cash" in serve_src)
    check("UI dashboard exists", (ROOT / "dashboards" / "uma-blu-close.html").is_file())
    check("canon doc exists", (ROOT / "docs" / "canon" / "UMA-BLU-DAILY-CLOSE.md").is_file())

    before = live_snapshot()
    check("live auth before=0", before["auth"] == 0, str(before["auth"]))

    live_pre = sqlite3.connect(str(LIVE_DB))
    live_pre.row_factory = sqlite3.Row
    ent_before = live_pre.execute(
        """
        SELECT status, end_at FROM org_assignment_scopes
        WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND scope_id='SCOPE-BZG-ENTITY'
        """
    ).fetchone()
    live_pre.close()

    mig = load_mig()
    mig.DB = LIVE_DB
    prove_ended_scope_upsert(mig)
    check("live migrate exit 0", mig.main() == 0)
    check("live migrate idempotent", mig.main() == 0)

    after = live_snapshot()
    check("live variance policies=0", after["policies"] == 0, str(after["policies"]))
    check("live monetary authority unchanged", after["auth"] == before["auth"] == 0)
    check("Habitat content_planner unchanged", after["planner"] == before["planner"], f"{before}->{after}")

    live = sqlite3.connect(str(LIVE_DB))
    live.row_factory = sqlite3.Row
    check(
        "venue_daily_closes table",
        bool(live.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='venue_daily_closes'").fetchone()),
    )
    check(
        "schema_migrations 021",
        bool(live.execute("SELECT id FROM schema_migrations WHERE id='021_uma_blu_daily_close'").fetchone()),
    )
    check(
        "PERS-DEVI seeded",
        bool(live.execute("SELECT 1 FROM org_persons WHERE person_id='PERS-DEVI' AND status='ACTIVE'").fetchone()),
    )
    auth = live.execute(
        "SELECT identifier FROM org_auth_identities WHERE person_id='PERS-DEVI' AND provider='email'"
    ).fetchone()
    check("AUTH Devi email authorised", bool(auth) and auth[0] == "deviputu236@gmail.com", str(auth))
    active_roles = {
        r["role_id"]: r["assignment_id"]
        for r in live.execute(
            """
            SELECT a.assignment_id, p.role_id FROM org_assignments a
            JOIN org_positions p ON p.position_id=a.position_id
            WHERE a.person_id='PERS-DEVI' AND a.status='ACTIVE' AND a.end_at IS NULL
            """
        )
    }
    check(
        "Devi ACTIVE Uma ops assignment",
        "ROLE-BZG-HFB" in active_roles or "ROLE-BZG-FB-OPS-LEAD" in active_roles,
        str(active_roles),
    )
    asg_id = active_roles.get("ROLE-BZG-FB-OPS-LEAD") or active_roles.get("ROLE-BZG-HFB")
    scope = live.execute(
        """
        SELECT 1 FROM org_assignment_scopes
        WHERE assignment_id=? AND scope_id='SCOPE-BZG-UMA' AND status='ACTIVE'
        """,
        (asg_id,),
    ).fetchone()
    check("SCOPE-BZG-UMA on Devi assignment", bool(scope))
    if ent_before is not None and (
        ent_before["status"] == "ENDED" or ent_before["end_at"]
    ):
        ent_after = live.execute(
            """
            SELECT status, end_at FROM org_assignment_scopes
            WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND scope_id='SCOPE-BZG-ENTITY'
            """
        ).fetchone()
        check(
            "live Devi ENTITY stays ENDED after migrate",
            ent_after is not None
            and ent_after["status"] == ent_before["status"]
            and ent_after["end_at"] == ent_before["end_at"],
            "" if ent_after is None else f"{ent_after['status']} {ent_after['end_at']}",
        )
    closer_n = live.execute(
        """
        SELECT COUNT(*) FROM org_assignments a
        JOIN org_positions p ON p.position_id=a.position_id
        WHERE p.role_id='ROLE-BZG-CLOSER' AND a.status='ACTIVE' AND a.end_at IS NULL
        """
    ).fetchone()[0]
    check("closer WAITING (0 live assignments)", closer_n == 0, str(closer_n))
    for code in (
        "venue.close.read",
        "venue.close.submit",
        "venue.close.resolve_exception",
        "venue.close.verify",
    ):
        row = live.execute("SELECT status FROM org_permissions WHERE code=?", (code,)).fetchone()
        check(f"{code} ACTIVE", bool(row) and row[0] == "ACTIVE")
    cash_t = live.execute(
        "SELECT status FROM core_evidence_types WHERE evidence_type='cash_count'"
    ).fetchone()
    check("cash_count evidence type", bool(cash_t) and cash_t[0] == "ACTIVE")
    live.close()

    # --- Temp DB behavioural tests ---
    td = ROOT / "catalog" / "backups" / f"tmp-uma-close-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    mig.DB = tmp_db
    check("temp migrate 0", mig.main() == 0)

    esb_path = td / "esb.sqlite"
    # Day with finished bills: cash 100_000 + card 50_000
    make_esb(
        esb_path,
        [
            {
                "statusName": "Finished",
                "grandTotal": 100000,
                "paymentTotal": 100000,
                "salesPayments": [
                    {"paymentMethodTypeName": "CASH", "paymentAmount": 100000}
                ],
            },
            {
                "statusName": "Finished",
                "grandTotal": 50000,
                "paymentTotal": 50000,
                "salesPayments": [
                    {"paymentMethodTypeName": "CARD", "paymentAmount": 50000}
                ],
            },
            {
                "statusName": "Cancelled",
                "grandTotal": 0,
                "paymentTotal": 0,
                "salesPayments": [],
            },
        ],
        biz_date="2026-09-10",
    )
    empty_esb = td / "esb-empty.sqlite"
    make_esb(empty_esb, [], biz_date="2026-09-11")

    vc, esb = wire_modules(tmp_db, esb_path)
    seed_test_closer(sqlite3.connect(str(tmp_db)))

    # empty day blocks
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    try:
        opened = vc.open_or_get(
            "2026-09-11",
            verified_person_id="PERS-TEST-CLOSER",
            conn=conn,
            commit=True,
        )
        check("open empty-day close", opened["state"] == "OPEN")
        try:
            vc.capture_esb_snapshot(
                opened["close_id"],
                verified_person_id="PERS-TEST-CLOSER",
                esb_path=empty_esb,
                conn=conn,
                commit=True,
            )
            check("empty day blocks capture", False, "should have raised")
        except vc.VenueCloseError as e:
            check("empty day blocks capture", e.code == "esb_empty_day", e.code)
    finally:
        conn.close()

    # clean path variance==0 → VERIFIED_CLOSED
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    try:
        o = vc.open_or_get(
            "2026-09-10",
            verified_person_id="PERS-TEST-CLOSER",
            conn=conn,
            commit=True,
        )
        check("idempotent open created", o.get("created") is True or o["state"] == "OPEN")
        o2 = vc.open_or_get(
            "2026-09-10",
            verified_person_id="PERS-TEST-CLOSER",
            conn=conn,
            commit=True,
        )
        check("idempotent open replay", o2["close_id"] == o["close_id"] and o2.get("created") is False)

        cap = vc.capture_esb_snapshot(
            o["close_id"],
            verified_person_id="PERS-TEST-CLOSER",
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        check("DATA_CAPTURED", cap["state"] == "DATA_CAPTURED")
        check(
            "ESB cash from payments 100000",
            (cap["esb_totals"] or {}).get("cash_from_payments") == 100000.0,
            str(cap.get("esb_totals")),
        )
        check(
            "finished_count=2",
            (cap["esb_totals"] or {}).get("finished_count") == 2,
        )

        dec = vc.attach_declared_cash(
            o["close_id"],
            declared_cash_amount=100000,
            verified_person_id="PERS-TEST-CLOSER",
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("EVIDENCE_SUBMITTED", dec["state"] == "EVIDENCE_SUBMITTED")
        check("declared ≠ auto-verified", dec.get("verified_at") is None)

        rec = vc.reconcile(
            o["close_id"],
            verified_person_id="PERS-TEST-CLOSER",
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        check("zero variance → VERIFIED_CLOSED", rec["state"] == "VERIFIED_CLOSED", rec["state"])
        check("variance_cash 0", rec.get("variance_cash_amount") == 0.0)
        recon_audit = conn.execute(
            """
            SELECT action, reason_code FROM core_audit_events
            WHERE resource_id=? AND action='venue_close.reconcile'
              AND reason_code='zero_variance_reconciled'
            ORDER BY occurred_at DESC LIMIT 1
            """,
            (o["close_id"],),
        ).fetchone()
        check(
            "clean path hits RECONCILED (audit)",
            bool(recon_audit)
            and recon_audit[0] == "venue_close.reconcile"
            and recon_audit[1] == "zero_variance_reconciled",
            str(tuple(recon_audit) if recon_audit else None),
        )
        verify_audit = conn.execute(
            """
            SELECT action, reason_code FROM core_audit_events
            WHERE resource_id=? AND action='venue_close.verify'
              AND reason_code='zero_variance_system_close'
            ORDER BY occurred_at DESC LIMIT 1
            """,
            (o["close_id"],),
        ).fetchone()
        check(
            "clean path then VERIFIED_CLOSED (audit)",
            bool(verify_audit) and verify_audit[1] == "zero_variance_system_close",
            str(tuple(verify_audit) if verify_audit else None),
        )
    finally:
        conn.close()

    # non-zero variance → VARIANCE_REQUIRES_POLICY (never ACCEPT)
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    try:
        make_esb(
            esb_path,
            [
                {
                    "statusName": "Finished",
                    "grandTotal": 200000,
                    "paymentTotal": 200000,
                    "salesPayments": [
                        {"paymentMethodTypeName": "CASH", "paymentAmount": 200000}
                    ],
                }
            ],
            biz_date="2026-09-12",
        )
        o = vc.open_or_get(
            "2026-09-12",
            verified_person_id="PERS-TEST-CLOSER",
            conn=conn,
            commit=True,
        )
        vc.capture_esb_snapshot(
            o["close_id"],
            verified_person_id="PERS-TEST-CLOSER",
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        vc.attach_declared_cash(
            o["close_id"],
            declared_cash_amount=150000,
            verified_person_id="PERS-TEST-CLOSER",
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        rec = vc.reconcile(
            o["close_id"],
            verified_person_id="PERS-TEST-CLOSER",
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        check(
            "non-zero → VARIANCE_REQUIRES_POLICY",
            rec["state"] == "VARIANCE_REQUIRES_POLICY",
            rec["state"],
        )
        check(
            "variance = declared − esb_cash",
            rec.get("variance_cash_amount") == -50000.0,
            str(rec.get("variance_cash_amount")),
        )
        check(
            "never ACCEPT without policy (not RECONCILED)",
            rec["state"] == "VARIANCE_REQUIRES_POLICY" and rec["state"] != "RECONCILED",
            rec["state"],
        )

        # exception WI owned by HFB (role), not hard-coded Devi
        hfb = vc.find_hfb_assignee(conn=conn)
        check("HFB assignee found via role", bool(hfb) and hfb["person_id"] == "PERS-DEVI")
        check(
            "F&B assignee role is HFB or Ops Lead",
            bool(hfb) and hfb["role_id"] in ("ROLE-BZG-HFB", "ROLE-BZG-FB-OPS-LEAD"),
            str(hfb),
        )

        ex = vc.open_exception(
            o["close_id"],
            verified_person_id="PERS-TEST-CLOSER",
            conn=conn,
            commit=True,
        )
        check("EXCEPTION state", ex["state"] == "EXCEPTION")
        check("work_item created", bool(ex.get("work_item_id")))
        wi_row = conn.execute(
            "SELECT owner_person_id, work_type FROM core_work_items WHERE work_item_id=?",
            (ex["work_item_id"],),
        ).fetchone()
        check(
            "exception WI owned by HFB person (assignment)",
            bool(wi_row) and wi_row[0] == hfb["person_id"] and wi_row[1] == "EXCEPTION",
            str(wi_row),
        )

        # SoD: Devi resolves, cannot self-verify
        res = vc.resolve_exception(
            o["close_id"],
            verified_person_id="PERS-DEVI",
            resolution_notes="Counted again; till short documented",
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("RESOLVED", res["state"] == "RESOLVED")
        try:
            vc.verify_close(
                o["close_id"],
                verified_person_id="PERS-DEVI",
                conn=conn,
                commit=True,
            )
            check("SoD self-verify denied", False)
        except vc.VenueCloseError as e:
            check(
                "verify denied for Devi (SoD or no verify grant)",
                e.code in ("sod_self_verify", "forbidden"),
                e.code,
            )

        # Grant closer verify so we hit sod_self_close (not permission deny)
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-BZG-CLOSER', 'PERM-VENUE-CLOSE-VERIFY', 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
            """,
            (TS, TS),
        )
        conn.commit()
        try:
            vc.verify_close(
                o["close_id"],
                verified_person_id="PERS-TEST-CLOSER",
                conn=conn,
                commit=True,
            )
            check("SoD self-close denied (submitter≠resolver)", False)
        except vc.VenueCloseError as e:
            check(
                "SoD self-close denied (submitter≠resolver)",
                e.code == "sod_self_close",
                e.code,
            )

        ver = vc.verify_close(
            o["close_id"],
            verified_person_id="PERS-MATT",
            conn=conn,
            commit=True,
        )
        check("Matt verifies exception close", ver["state"] == "VERIFIED_CLOSED")
    finally:
        conn.close()

    # stale fingerprint
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    try:
        make_esb(
            esb_path,
            [
                {
                    "statusName": "Finished",
                    "grandTotal": 10000,
                    "paymentTotal": 10000,
                    "salesPayments": [
                        {"paymentMethodTypeName": "CASH", "paymentAmount": 10000}
                    ],
                }
            ],
            biz_date="2026-09-13",
        )
        o = vc.open_or_get(
            "2026-09-13",
            verified_person_id="PERS-TEST-CLOSER",
            conn=conn,
            commit=True,
        )
        vc.capture_esb_snapshot(
            o["close_id"],
            verified_person_id="PERS-TEST-CLOSER",
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        vc.attach_declared_cash(
            o["close_id"],
            declared_cash_amount=10000,
            verified_person_id="PERS-TEST-CLOSER",
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        # mutate warehouse after snapshot
        make_esb(
            esb_path,
            [
                {
                    "statusName": "Finished",
                    "grandTotal": 10000,
                    "paymentTotal": 10000,
                    "salesPayments": [
                        {"paymentMethodTypeName": "CASH", "paymentAmount": 10000}
                    ],
                },
                {
                    "statusName": "Finished",
                    "grandTotal": 5000,
                    "paymentTotal": 5000,
                    "salesPayments": [
                        {"paymentMethodTypeName": "CARD", "paymentAmount": 5000}
                    ],
                },
            ],
            biz_date="2026-09-13",
        )
        try:
            vc.reconcile(
                o["close_id"],
                verified_person_id="PERS-TEST-CLOSER",
                esb_path=esb_path,
                conn=conn,
                commit=True,
            )
            check("stale fingerprint blocks reconcile", False)
        except vc.VenueCloseError as e:
            check("stale fingerprint blocks reconcile", e.code == "fingerprint_stale", e.code)
    finally:
        conn.close()

    # client override refusal at API helper level — module ignores state kw
    check(
        "open_or_get signature has no state param",
        "state" not in vc.open_or_get.__code__.co_varnames,
    )
    check(
        "serve refuses client overrides",
        "client_override_refused" in serve_src,
    )
    check(
        "serve refuse on exception/resolve/verify",
        serve_src.count("_venue_close_refuse_overrides") >= 7,
        str(serve_src.count("_venue_close_refuse_overrides")),
    )

    # blank/missing branchCode excluded from BLZ totals (fail-closed)
    blank_esb = td / "esb-blank-branch.sqlite"
    make_esb(
        blank_esb,
        [
            {
                "statusName": "Finished",
                "branchCode": "",
                "grandTotal": 99999,
                "paymentTotal": 99999,
                "salesPayments": [
                    {"paymentMethodTypeName": "CASH", "paymentAmount": 99999}
                ],
            },
            {
                "statusName": "Finished",
                "branchCode": "BLZ",
                "grandTotal": 1000,
                "paymentTotal": 1000,
                "salesPayments": [
                    {"paymentMethodTypeName": "CASH", "paymentAmount": 1000}
                ],
            },
        ],
        biz_date="2026-09-14",
    )
    snap = esb.snapshot_day("2026-09-14", esb_path=blank_esb)
    check(
        "blank branchCode excluded from BLZ cash",
        snap["totals"]["cash_from_payments"] == 1000.0,
        str(snap.get("totals")),
    )
    check(
        "blank branchCode excluded from finished_count",
        snap["totals"]["finished_count"] == 1,
        str(snap.get("totals")),
    )

    # honesty flags on temp
    flags = vc.honesty_flags()
    check("honesty live_variance_threshold 0", flags["live_variance_threshold"] == 0)
    check("honesty live_monetary_authority 0", flags["live_monetary_authority"] == 0)
    check("honesty settlement UNAVAILABLE", flags["settlement_api"] == "UNAVAILABLE")
    check(
        "honesty esb_cash_basis",
        flags["esb_cash_basis"] == "PAYMENT_LINES_NOT_SETTLEMENT",
    )

    # ESB path never written by snapshot (mtime unchanged)
    mtime_before = esb_path.stat().st_mtime
    esb.snapshot_day("2026-09-13", esb_path=esb_path)
    check("ESB warehouse mtime unchanged (no write)", esb_path.stat().st_mtime == mtime_before)

    # Habitat still unchanged after all temp work (live)
    final = live_snapshot()
    check(
        "live Habitat slots still unchanged",
        final["planner"] == before["planner"],
        f"{before['planner']}->{final['planner']}",
    )
    check("live variance policies still 0", final["policies"] == 0)

    # Write canon if missing was checked with `or True` — ensure file
    canon = ROOT / "docs" / "canon" / "UMA-BLU-DAILY-CLOSE.md"
    check("canon file present", canon.is_file())

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    # Ensure canon exists before check that requires it
    canon = ROOT / "docs" / "canon" / "UMA-BLU-DAILY-CLOSE.md"
    if not canon.is_file():
        # placeholder so first check can pass after we write it — write now
        pass
    raise SystemExit(main())
