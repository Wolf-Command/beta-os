#!/usr/bin/env python3
"""Owner read gate, OpenClaw policy gate, and Ask Wolf. No metered model calls."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import owner_front_door as door  # noqa: E402
from core import scoped_read_auth as auth  # noqa: E402
from core import wolf_policy_gate as gate  # noqa: E402

PASS = 0
FAIL = 0
NOW = "2026-10-06T00:00:00+00:00"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {name}")
    else:
        FAIL += 1
        print(f"FAIL {name} {detail}")


def seed(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE org_entities (
          entity_id TEXT PRIMARY KEY, legal_name TEXT, display_name TEXT,
          entity_type TEXT, status TEXT, saleable INTEGER, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_brands (
          brand_id TEXT PRIMARY KEY, entity_id TEXT, display_name TEXT,
          brand_type TEXT, status TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_locations (
          location_id TEXT PRIMARY KEY, entity_id TEXT, display_name TEXT,
          location_type TEXT, status TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_departments (
          department_id TEXT PRIMARY KEY, entity_id TEXT, ownership TEXT,
          display_name TEXT, status TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_roles (
          role_id TEXT PRIMARY KEY, display_name TEXT, department_id TEXT,
          role_type TEXT, status TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_positions (
          position_id TEXT PRIMARY KEY, role_id TEXT, entity_id TEXT,
          location_id TEXT, brand_id TEXT, department_id TEXT,
          position_label TEXT, status TEXT, fte REAL, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_persons (
          person_id TEXT PRIMARY KEY, display_name TEXT, legal_name TEXT,
          status TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_assignments (
          assignment_id TEXT PRIMARY KEY, person_id TEXT, position_id TEXT,
          start_at TEXT, end_at TEXT, status TEXT, is_primary INTEGER,
          created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_permissions (
          permission_id TEXT PRIMARY KEY, code TEXT UNIQUE, resource TEXT,
          action TEXT, description TEXT, status TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_role_permissions (
          role_id TEXT, permission_id TEXT, effect TEXT, created_at TEXT, updated_at TEXT,
          PRIMARY KEY (role_id, permission_id)
        );
        CREATE TABLE org_permission_legacy_map (
          legacy_code TEXT PRIMARY KEY, permission_id TEXT, note TEXT, created_at TEXT
        );
        CREATE TABLE org_scopes (
          scope_id TEXT PRIMARY KEY, scope_type TEXT, display_name TEXT,
          status TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE org_scope_targets (
          scope_id TEXT, target_type TEXT, target_id TEXT, created_at TEXT,
          PRIMARY KEY (scope_id, target_type, target_id)
        );
        CREATE TABLE org_assignment_scopes (
          assignment_id TEXT, scope_id TEXT, start_at TEXT, end_at TEXT,
          status TEXT, created_at TEXT, updated_at TEXT,
          PRIMARY KEY (assignment_id, scope_id, start_at)
        );
        """
    )
    conn.executemany(
        "INSERT INTO org_entities VALUES (?,?,?,?,?,?,?,?)",
        [
            ("ENT-AMG", "AMG", "AMG", "company", "ACTIVE", 0, NOW, NOW),
            ("ENT-GGV", "GGV", "GGV", "company", "ACTIVE", 0, NOW, NOW),
            ("ENT-WOLF", "Wolf", "Wolf", "group", "ACTIVE", 0, NOW, NOW),
        ],
    )
    conn.execute(
        "INSERT INTO org_departments VALUES (?,?,?,?,?,?,?)",
        ("DEPT-GGV-CONTENT", "ENT-GGV", "ENTITY", "Content", "ACTIVE", NOW, NOW),
    )
    perms = [
        ("PERM-PROGRESS", "progress.read", "progress", "read"),
        ("PERM-BOARD", "atrium.board.read", "atrium.board", "read"),
        ("PERM-DAY", "amg.day.operator", "amg.day", "operate"),
        ("PERM-PERSON", "organisation.person.read", "organisation.person", "read"),
    ]
    for pid, code, resource, action in perms:
        conn.execute(
            "INSERT INTO org_permissions VALUES (?,?,?,?,?,?,?,?)",
            (pid, code, resource, action, code, "ACTIVE", NOW, NOW),
        )
    roles = [
        ("ROLE-MATT", "Owner", ("PERM-PROGRESS", "PERM-PERSON")),
        ("ROLE-AMG", "AMG finance", ("PERM-BOARD",)),
        ("ROLE-GGV", "GGV staff", ()),
        ("ROLE-HR", "GGV people read", ("PERM-PERSON",)),
    ]
    for role_id, label, grants in roles:
        conn.execute(
            "INSERT INTO org_roles VALUES (?,?,?,?,?,?,?)",
            (role_id, label, None, "seat", "ACTIVE", NOW, NOW),
        )
        for perm_id in grants:
            conn.execute(
                "INSERT INTO org_role_permissions VALUES (?,?,?,?,?)",
                (role_id, perm_id, "ALLOW", NOW, NOW),
            )
    seats = [
        ("POS-MATT", "ROLE-MATT", "ENT-GGV", "PERS-MATT", "ASG-MATT", "SCOPE-WOLF"),
        ("POS-AMG", "ROLE-AMG", "ENT-AMG", "PERS-AMG", "ASG-AMG", "SCOPE-AMG"),
        ("POS-DEVI", "ROLE-GGV", "ENT-GGV", "PERS-DEVI", "ASG-DEVI", "SCOPE-GGV-DEVI"),
        ("POS-HR", "ROLE-HR", "ENT-GGV", "PERS-HR", "ASG-HR", "SCOPE-GGV-HR"),
        ("POS-OTHER", "ROLE-GGV", "ENT-GGV", "PERS-OTHER", "ASG-OTHER", "SCOPE-GGV-OTHER"),
    ]
    for pos, role, entity, person, asg, scope in seats:
        conn.execute(
            "INSERT INTO org_positions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (pos, role, entity, None, None, None, pos, "ACTIVE", 1, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO org_persons VALUES (?,?,?,?,?,?)",
            (person, person, None, "ACTIVE", NOW, NOW),
        )
        conn.execute(
            "INSERT INTO org_assignments VALUES (?,?,?,?,?,?,?,?,?)",
            (asg, person, pos, NOW, None, "ACTIVE", 1, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO org_scopes VALUES (?,?,?,?,?,?)",
            (scope, "entity", scope, "ACTIVE", NOW, NOW),
        )
        conn.execute(
            "INSERT INTO org_scope_targets VALUES (?,?,?,?)",
            (scope, "entity", entity, NOW),
        )
        conn.execute(
            "INSERT INTO org_assignment_scopes VALUES (?,?,?,?,?,?,?)",
            (asg, scope, NOW, None, "ACTIVE", NOW, NOW),
        )
    conn.commit()
    return conn


def test_scope(conn: sqlite3.Connection) -> None:
    owner = {"ok": True, "person_id": "PERS-MATT"}
    amg = {"ok": True, "person_id": "PERS-AMG"}
    devi = {"ok": True, "person_id": "PERS-DEVI"}
    anon = {"ok": False, "person_id": None}
    check("owner god mode", auth.decide("god_mode", owner, conn=conn)["allowed"] is True)
    check("owner cockpit", auth.decide("owner_cockpit", owner, conn=conn)["allowed"] is True)
    check("anon god mode", auth.decide("god_mode", anon, conn=conn)["allowed"] is False)
    check("devi god mode", auth.decide("god_mode", devi, conn=conn)["allowed"] is False)
    check("devi amg state", auth.decide("amg_state", devi, conn=conn)["allowed"] is False)
    check("amg state seat", auth.decide("amg_state", amg, conn=conn)["allowed"] is True)
    check("amg not owner cockpit", auth.decide("owner_cockpit", amg, conn=conn)["allowed"] is False)
    check("self person", auth.person_record_allowed("PERS-DEVI", "PERS-DEVI", conn))
    check("devi other person denied", auth.person_record_allowed("PERS-DEVI", "PERS-OTHER", conn) is False)
    check("amg cannot read ggv person", auth.person_record_allowed("PERS-AMG", "PERS-OTHER", conn) is False)
    check("hr reads ggv person", auth.person_record_allowed("PERS-HR", "PERS-OTHER", conn) is True)
    check("hr cannot read amg person", auth.person_record_allowed("PERS-HR", "PERS-AMG", conn) is False)
    check("owner reads anyone", auth.person_record_allowed("PERS-MATT", "PERS-AMG", conn) is True)
    check("route god mode", auth.classify_open_route("/api/owner/god-mode-register") == "god_mode")
    check("route sales desk", auth.classify_open_route("/api/amg/sales-desk") == "amg_state")
    check("route health open", auth.classify_open_route("/api/health") is None)


def test_policy(root: Path) -> None:
    state = gate.tick(root)
    check("not a second orchestrator", state.get("parallel_orchestrator") is False)
    check("openclaw not suitable", (state.get("openclaw") or {}).get("suitable_as_overnight_brain") is False)
    check("openclaw not marked running", (state.get("openclaw") or {}).get("running") is False)
    check(
        "python -c mention is not openclaw",
        gate.command_is_openclaw("python3 -c \"print('openclaw gateway')\"") is False,
    )
    check("openclaw gateway argv counts", gate.command_is_openclaw("openclaw gateway --port 18789") is True)
    check(
        "openclaw-gateway basename counts",
        gate.command_is_openclaw("/usr/local/bin/openclaw-gateway") is True,
    )
    check("haiku claim unverified", (state.get("openclaw") or {}).get("haiku_claim") == "UNVERIFIED")
    item = state["items"][0]
    item["status"] = "RUNNING"
    item["worker"] = "cursor"
    item["last_change"] = "2020-01-01T00:00:00+00:00"
    gate.save(state, root)
    reaped = gate.tick(root)
    stale = next(row for row in reaped["items"] if row["id"] == item["id"])
    check("stale running reaped", stale["status"] == "STALLED", stale["status"])
    try:
        gate.apply_event({"item_id": item["id"], "status": "DONE", "worker": "grok"}, root)
        check("grok event rejected", False, "accepted")
    except ValueError as exc:
        check("grok event rejected", "blocked_worker" in str(exc), str(exc))
    try:
        gate.apply_event(
            {"item_id": item["id"], "status": "DONE", "worker": "local", "source": "peaches"},
            root,
        )
        check("peaches source rejected", False, "accepted")
    except ValueError as exc:
        check("peaches source rejected", "blocked_source" in str(exc), str(exc))
    claude = gate.worker_eligibility("claude-pro", {"ANTHROPIC_API_KEY": "sk-test"})
    check("claude api key fail closed", claude["eligible"] is False and claude["metered"] is True, str(claude))
    codex = gate.worker_eligibility("codex", {"OPENAI_API_KEY": "sk-test"})
    check("codex api key fail closed", codex["eligible"] is False, str(codex))
    cursor = gate.worker_eligibility("cursor", {})
    check("cursor included", cursor["eligible"] is True and cursor["route"] == "cursor_ultra")
    asked = door.answer("What is the status of GGV Finance?", root)
    check("ggv not commissioned", "NOT HUMAN COMMISSIONED" in asked["answer"], asked["answer"])
    check("ask did not call a model", asked["model_called"] is False)
    needs = door.answer("What needs me?", root)
    check("needs you quiet", "Nothing needs you" in needs["answer"], needs["answer"])
    running = door.answer("What is running?", root)
    check("running empty after reap", "Nothing is running" in running["answer"], running["answer"])
    uma = door.answer("What happened with Arya's Uma Blu close?", root)
    check("arya unknown", "UNKNOWN" in uma["answer"], uma["answer"])


def test_http() -> None:
    import serve_beta as sb

    handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if obj is not BaseHTTPRequestHandler and isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler):
            if obj.__name__ == "BetaHandler":
                handler = obj
                break
    check("handler found", handler is not None)
    if handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(method: str, path: str, subject: str | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = b"{}" if method == "POST" else None
        if method == "POST":
            headers["Content-Type"] = "application/json"
        req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method, data=data)
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.status, resp.read()
        except HTTPError as exc:
            return exc.code, exc.read()

    status, body = call("GET", "/api/owner/god-mode-register")
    check("anon god mode 403", status == 403 and b"numerator" not in body, f"{status} {body[:180]!r}")
    status, body = call("GET", "/api/owner/god-mode-register", "deviputu236@gmail.com")
    check("staff god mode 403", status == 403 and b"GOD-MODE" not in body, f"{status} {body[:180]!r}")
    status, _body = call("GET", "/api/amg/sales-desk")
    check("anon amg desk 403", status == 403, str(status))
    status, _body = call("GET", "/api/owner/pulse-ro", "mlsary111@gmail.com")
    check("staff pulse 403", status == 403, str(status))
    status, body = call("GET", "/api/core/persons/PERS-MATT")
    try:
        parsed = json.loads(body.decode())
    except json.JSONDecodeError:
        parsed = {}
    check(
        "anon person 403",
        status == 403 and "display_name" not in json.dumps(parsed),
        f"{status} {body[:180]!r}",
    )
    status, _body = call("GET", "/owner/god-mode")
    check("anon god mode page 403", status == 403, str(status))
    httpd.shutdown()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="beta-os-gate-") as tmp:
        db_path = Path(tmp) / "beta-os" / "catalog.sqlite"
        conn = seed(db_path)
        try:
            test_scope(conn)
        finally:
            conn.close()
        test_policy(Path(tmp) / "policy")
    test_http()
    print(f"{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
