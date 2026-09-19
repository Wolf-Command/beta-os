#!/usr/bin/env python3
"""Devi BZG F&B Operations Lead — role, receive, close submit.

Owner decision DEC-DEVI-BZG-FB-OPS-LEAD-2026-09-19.
Proves PERS-DEVI can receive and close.submit, ENTITY stays ENDED,
payment/verify/progress stay denied, anon receive is 403.
Does not write Alchemist. Does not touch Production.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("WOLF_TEST_MODE", "1")
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import rbac  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mig = _load("migrate_devi_fb_ops_lead", SCRIPTS / "migrations" / "migrate_devi_fb_ops_lead.py")
close_mig = _load("migrate_uma_blu_daily_close", SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py")

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PASS = 0
FAIL = 0
UMA = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py":
        "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py":
        "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py":
        "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py":
        "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}
DENY = (
    "bzg.pr.payment_approve",
    "venue.close.verify",
    "progress.read",
    "approval.decide",
    "test.spend.approve",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entity_row(conn: sqlite3.Connection):
    return conn.execute(
        """
        SELECT status, end_at FROM org_assignment_scopes
        WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND scope_id='SCOPE-BZG-ENTITY'
        """
    ).fetchone()


def prove(conn: sqlite3.Connection, label: str, ent_before) -> None:
    ent = entity_row(conn)
    check(
        f"{label} ENTITY stays ENDED",
        ent is not None
        and ent["status"] == "ENDED"
        and ent["end_at"]
        and tuple(ent) == tuple(ent_before),
        str(tuple(ent) if ent else None),
    )
    role = conn.execute(
        "SELECT display_name, status FROM org_roles WHERE role_id='ROLE-BZG-FB-OPS-LEAD'"
    ).fetchone()
    check(
        f"{label} role display",
        bool(role) and role["display_name"] == "BZG F&B OPERATIONS LEAD" and role["status"] == "SPECIFIED",
        str(tuple(role) if role else None),
    )
    recv = conn.execute(
        "SELECT status FROM org_permissions WHERE code='venue.receive'"
    ).fetchone()
    check(f"{label} venue.receive ACTIVE", bool(recv) and recv["status"] == "ACTIVE", str(recv))
    check(
        f"{label} discover receive",
        p0.discover_receive_permission(conn) == "venue.receive",
    )
    asg = conn.execute(
        """
        SELECT a.status, a.end_at, p.role_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id=a.position_id
        WHERE a.assignment_id='ASG-DEVI-FB-OPS-1'
        """
    ).fetchone()
    check(
        f"{label} ASG-DEVI-FB-OPS-1 ACTIVE",
        bool(asg) and asg["status"] == "ACTIVE" and asg["end_at"] is None and asg["role_id"] == "ROLE-BZG-FB-OPS-LEAD",
        str(tuple(asg) if asg else None),
    )
    hfb = conn.execute(
        "SELECT status, end_at FROM org_assignments WHERE assignment_id='ASG-DEVI-HFB-UMA-1'"
    ).fetchone()
    check(
        f"{label} HFB assignment ended",
        bool(hfb) and hfb["status"] == "ENDED" and hfb["end_at"],
        str(tuple(hfb) if hfb else None),
    )
    scopes = {
        r["scope_id"]
        for r in conn.execute(
            """
            SELECT scope_id FROM org_assignment_scopes
            WHERE assignment_id='ASG-DEVI-FB-OPS-1' AND status='ACTIVE' AND end_at IS NULL
            """
        )
    }
    check(f"{label} FB+UMA scopes", scopes == {"SCOPE-BZG-FB", "SCOPE-BZG-UMA"}, str(scopes))
    check(
        f"{label} PERS-DEVI venue.receive",
        rbac.can("PERS-DEVI", "venue.receive", UMA, conn=conn),
    )
    check(
        f"{label} PERS-DEVI close.submit",
        rbac.can("PERS-DEVI", "venue.close.submit", UMA, conn=conn),
    )
    for code in DENY:
        check(
            f"{label} denied {code}",
            rbac.can("PERS-DEVI", code, UMA, conn=conn) is False,
        )
    grants = {
        r[0]
        for r in conn.execute(
            """
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id='ROLE-BZG-FB-OPS-LEAD' AND rp.effect='ALLOW'
            """
        )
    }
    check(f"{label} role has no deny codes", not (grants & set(DENY)), str(grants & set(DENY)))
    ordered = p0.actionable_for(
        "PERS-DEVI",
        {"kind": "ordered_not_received", "classification": "NEEDS_STAFF", "classification_label": "Needs staff"},
        conn=conn,
    )
    check(f"{label} receive card actionable", ordered["actionable"] is True)
    close = p0.actionable_for(
        "PERS-DEVI",
        {"kind": "daily_close", "close": {"status": "not_started"}, "classification_label": "Needs staff"},
        conn=conn,
    )
    check(f"{label} close card actionable", close["actionable"] is True)
    pay = p0.actionable_for(
        "PERS-DEVI",
        {"kind": "bills_waiting_payment_approval"},
        conn=conn,
    )
    check(f"{label} payment waits on finance", pay["actionable"] is False and pay["waiting_role"] == "finance")
    pol = p0.actionable_for("PERS-DEVI", {"kind": "policy_required"}, conn=conn)
    check(f"{label} policy required", pol["actionable"] is False and pol["waiting_role"] == "policy")
    painted = p0.annotate_today(
        {
            "cards": [
                {
                    "kind": "ordered_not_received",
                    "title": "Ordered, not received",
                    "attention": True,
                    "classification": "NEEDS_STAFF",
                    "classification_label": "Needs staff",
                    "href": "/bzg/uma-blu/bills",
                    "rank": 1,
                }
            ]
        },
        person_id="PERS-DEVI",
        conn=conn,
    )
    card = painted["cards"][0]
    check(f"{label} chip is You can act", card.get("classification_label") == "You can act", str(card.get("classification_label")))
    check(f"{label} action href kept", card.get("href") == "/bzg/uma-blu/bills")
    check(f"{label} nobody cannot receive", rbac.can("PERS-NOBODY", "venue.receive", UMA, conn=conn) is False)


def anon_receive_403() -> None:
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        req = Request(
            f"http://127.0.0.1:{httpd.server_address[1]}/api/bzg/uma-blu/receive",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=8) as resp:
                check("anon receive 403", False, f"status {resp.status}")
        except HTTPError as exc:
            raw = exc.read().decode()
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {}
            check("anon receive 403", exc.code == 403 and body.get("ok") is False, f"{exc.code} {body.get('error')}")
    finally:
        httpd.shutdown()


def main() -> int:
    for rel, digest in WIP.items():
        check(f"WIP unchanged {Path(rel).name}", sha(ROOT / rel) == digest)
    src_gate = (SCRIPTS / "core" / "uma_devi_p0.py").read_text(encoding="utf-8")
    check("no PERS-DEVI hard-code in p0", '== "PERS-DEVI"' not in src_gate and "== 'PERS-DEVI'" not in src_gate)
    mig_src = (SCRIPTS / "migrations" / "migrate_devi_fb_ops_lead.py").read_text(encoding="utf-8")
    check("migration does not write Alchemist", "alchemist" not in mig_src.lower() or "No Alchemist" in mig_src)
    check("payment code is deny-only", mig_src.count("bzg.pr.payment_approve") == 1)
    close_src = (SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py").read_text(encoding="utf-8")
    check("021 does not revive ENDED assignments", "status!='ENDED'" in close_src)

    td = ROOT / "catalog" / "backups" / f"tmp-fb-ops-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp = td / "content_library.sqlite"
    try:
        shutil.copy2(LIVE_DB, tmp)
        snap = sqlite3.connect(str(tmp))
        snap.row_factory = sqlite3.Row
        ent_before = entity_row(snap)
        snap.close()
        check("temp ENTITY already ENDED", bool(ent_before) and ent_before["status"] == "ENDED")

        mig.DB = tmp
        check("temp migrate 0", mig.main() == 0)
        check("temp migrate idempotent", mig.main() == 0)
        close_mig.DB = tmp
        check("021 after ops lead does not fail", close_mig.main() == 0)

        conn = sqlite3.connect(str(tmp))
        conn.row_factory = sqlite3.Row
        prove(conn, "temp", ent_before)
        conn.close()
        if FAIL:
            print(f"PASS={PASS} FAIL={FAIL}")
            return 1

        live_before = sqlite3.connect(str(LIVE_DB))
        live_before.row_factory = sqlite3.Row
        live_ent = entity_row(live_before)
        live_before.close()
        mig.DB = LIVE_DB
        check("live migrate 0", mig.main() == 0)
        check("live migrate idempotent", mig.main() == 0)
        live = sqlite3.connect(str(LIVE_DB))
        live.row_factory = sqlite3.Row
        prove(live, "live", live_ent)
        live.close()
        anon_receive_403()
    finally:
        shutil.rmtree(td, ignore_errors=True)
        mig.DB = LIVE_DB
        close_mig.DB = LIVE_DB

    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
