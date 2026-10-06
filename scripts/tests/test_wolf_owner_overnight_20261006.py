#!/usr/bin/env python3
"""Owner read gate, non-Grok control plane, and Ask Wolf.

No metered model calls. The catalog is a temp sqlite whose path contains beta-os.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import god_mode_register_ro as gm  # noqa: E402
from core import identity as ident  # noqa: E402
from core import owner_front_door as door  # noqa: E402
from core import scoped_read_auth as auth  # noqa: E402
from core import nogrok_control as gate  # noqa: E402
import nogrok_supervisor as sup  # noqa: E402

PASS = 0
FAIL = 0
NOW = "2026-10-06T00:00:00+00:00"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {name}", flush=True)
    else:
        FAIL += 1
        print(f"FAIL {name} {detail}", flush=True)


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
        CREATE TABLE org_auth_identities (
          auth_identity_id TEXT PRIMARY KEY,
          person_id TEXT NOT NULL,
          provider TEXT NOT NULL,
          identifier TEXT NOT NULL,
          status TEXT NOT NULL,
          is_primary INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_verified_at TEXT
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
        ("ROLE-AMG", "AMG board", ("PERM-BOARD",)),
        ("ROLE-DAY", "AMG day", ("PERM-DAY",)),
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
        ("POS-DAY", "ROLE-DAY", "ENT-AMG", "PERS-AMG-DAY", "ASG-DAY", "SCOPE-AMG-DAY"),
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
    idents = [
        ("AUTH-MATT", "PERS-MATT", "mrwolf@wolfcommand.net"),
        ("AUTH-AMG", "PERS-AMG", "amg.seat@wolfcommand.test"),
        ("AUTH-DAY", "PERS-AMG-DAY", "amg.day@wolfcommand.test"),
        ("AUTH-DEVI", "PERS-DEVI", "devi@wolfcommand.test"),
        ("AUTH-HR", "PERS-HR", "hr@wolfcommand.test"),
    ]
    for aid, person, email in idents:
        conn.execute(
            "INSERT INTO org_auth_identities VALUES (?,?,?,?,?,?,?,?,?)",
            (aid, person, "email", email, "ACTIVE", 1, NOW, NOW, None),
        )
    conn.commit()
    return conn


def test_scope(conn: sqlite3.Connection) -> None:
    owner = {"ok": True, "person_id": "PERS-MATT"}
    amg = {"ok": True, "person_id": "PERS-AMG"}
    day = {"ok": True, "person_id": "PERS-AMG-DAY"}
    devi = {"ok": True, "person_id": "PERS-DEVI"}
    anon = {"ok": False, "person_id": None}
    check("owner god mode", auth.decide("god_mode", owner, conn=conn)["allowed"] is True)
    check("owner cockpit", auth.decide("owner_cockpit", owner, conn=conn)["allowed"] is True)
    check("anon god mode", auth.decide("god_mode", anon, conn=conn)["allowed"] is False)
    check("devi god mode", auth.decide("god_mode", devi, conn=conn)["allowed"] is False)
    check("devi amg state", auth.decide("amg_state", devi, conn=conn)["allowed"] is False)
    check("amg board state", auth.decide("amg_state", amg, conn=conn)["allowed"] is True)
    check("amg day state", auth.decide("amg_state", day, conn=conn)["allowed"] is True)
    check("amg not owner cockpit", auth.decide("owner_cockpit", amg, conn=conn)["allowed"] is False)
    check("self person", auth.person_record_allowed("PERS-DEVI", "PERS-DEVI", conn))
    check("devi other person denied", auth.person_record_allowed("PERS-DEVI", "PERS-OTHER", conn) is False)
    check("amg cannot read ggv person", auth.person_record_allowed("PERS-AMG", "PERS-OTHER", conn) is False)
    check("hr reads ggv person", auth.person_record_allowed("PERS-HR", "PERS-OTHER", conn) is True)
    check("hr cannot read amg person", auth.person_record_allowed("PERS-HR", "PERS-AMG", conn) is False)
    check("owner reads anyone", auth.person_record_allowed("PERS-MATT", "PERS-AMG", conn) is True)
    check("route god mode", auth.classify_open_route("/api/owner/god-mode-register") == "god_mode")
    check("route pulse", auth.classify_open_route("/api/owner/pulse-ro") == "owner_cockpit")
    check("route sales desk", auth.classify_open_route("/api/amg/sales-desk") == "amg_state")
    check("route guest stay", auth.classify_open_route("/api/amg/guest-stay") == "amg_state")
    check("route health open", auth.classify_open_route("/api/health") is None)
    conn.execute("UPDATE org_scope_targets SET target_id='ENT-AMG' WHERE scope_id='SCOPE-WOLF'")
    conn.commit()
    check(
        "owner scope off ggv content denied",
        auth.decide("god_mode", owner, conn=conn)["allowed"] is False,
    )
    conn.execute("UPDATE org_scope_targets SET target_id='ENT-GGV' WHERE scope_id='SCOPE-WOLF'")
    conn.commit()
    check("owner scope restored", auth.decide("god_mode", owner, conn=conn)["allowed"] is True)


def test_policy(root: Path) -> None:
    state = gate.tick(root)
    check("orchestrator", state.get("orchestrator") == "nogrok_control")
    check("directive id", state["items"][0]["id"] == gate.DIRECTIVE_ID)
    check("directive has no blocked name", gate.blocked_name(state) is None)
    check("not commissioned", state.get("human_commissioned") is False)
    item = state["items"][0]
    item["status"] = "RUNNING"
    item["worker"] = gate.LOCAL_WORKER
    item["last_change"] = "2020-01-01T00:00:00+00:00"
    item["last_real_change"] = "2020-01-01T00:00:00+00:00"
    item["lease_until"] = None
    gate.save(state, root)
    reaped = gate.tick(root)
    stale = next(row for row in reaped["items"] if row["id"] == item["id"])
    check("stale running reaped", stale["status"] == "STALE", stale["status"])
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
    poisoned = gate.load(root)
    poisoned["items"][0]["what"] = "hand this to vesper"
    try:
        gate.save(poisoned, root)
        check("blocked name in work item rejected", False, "accepted")
    except ValueError as exc:
        check("blocked name in work item rejected", "blocked_worker" in str(exc), str(exc))
    claude = gate.worker_eligibility("claude-pro", {"ANTHROPIC_API_KEY": "sk-test"})
    check("claude api key fail closed", claude["eligible"] is False and claude["metered"] is True, str(claude))
    codex = gate.worker_eligibility("codex", {"OPENAI_API_KEY": "sk-test"})
    check("codex api key fail closed", codex["eligible"] is False and codex.get("fail_closed") is True, str(codex))
    cursor = gate.worker_eligibility("cursor", {})
    check(
        "cursor waiting capacity",
        cursor["approved"] is True
        and cursor["eligible"] is False
        and cursor["capacity"] == "WAITING_CAPACITY"
        and cursor.get("on_demand_blocked") is True
        and cursor.get("invoked") is False,
        str(cursor),
    )
    ollama = gate.worker_eligibility("ollama", {})
    check("ollama not fallback", ollama["eligible"] is False, str(ollama))
    disk = gate.disk_report()
    check("disk floor stays 100", disk["floor_gb"] == 100 and disk["floor_lowered"] is False and disk["deleted"] is False)
    asked = door.answer("What is the status of GGV Finance?", root)
    check(
        "ggv not commissioned",
        asked["answer"].startswith("GGV Finance is NOT HUMAN COMMISSIONED"),
        asked["answer"],
    )
    check("ask did not call a model", asked["model_called"] is False)
    needs = door.answer("What needs me?", root)
    check("needs you finance", "NOT HUMAN COMMISSIONED" in needs["answer"], needs["answer"])
    running = door.answer("What is running?", root)
    check("running empty after reap", "Nothing is running" in running["answer"], running["answer"])
    uma = door.answer("What happened with Arya's Uma Blu close?", root)
    check("arya unknown", "UNKNOWN" in uma["answer"] and uma["evidence"][0]["interfered"] is False, uma["answer"])
    stopped = gate.apply_owner_action("stop", item["id"], root=root)
    check("stop reversible", stopped["item"]["status"] == "STOPPED" and stopped["production_mutation"] is False)
    fixed = gate.apply_owner_action("fix", item["id"], root=root)
    check("fix requeues local", fixed["item"]["status"] == "QUEUED" and fixed["item"]["worker"] == gate.LOCAL_WORKER)
    moved = gate.apply_owner_action("reassign", item["id"], worker="cursor", root=root)
    check(
        "reassign cursor not invoked",
        moved["item"]["status"] == "WAITING_CAPACITY" and moved["item"].get("production_mutation") is False,
        str(moved["item"].get("status")),
    )
    src_control = (ROOT / "scripts" / "core" / "nogrok_control.py").read_text(encoding="utf-8")
    src_sup = (ROOT / "scripts" / "nogrok_supervisor.py").read_text(encoding="utf-8")
    check("control plane does not shell out", "subprocess" not in src_control and "os.system" not in src_control)
    check("supervisor does not shell out", "subprocess" not in src_sup and "os.system" not in src_sup)


def test_supervisor(root: Path) -> None:
    first = sup.acquire(root)
    check("supervisor acquire", first is True)
    second = sup.acquire(root)
    check("live pid not double started", second is False)
    held = gate.load(root)
    running = [row for row in held["items"] if row.get("status") == "RUNNING" and row.get("worker") == gate.LOCAL_WORKER]
    check("hold leaves local running", len(running) == 1 and running[0].get("lease_until"))
    sup.release(root)
    check("pid released", sup.read_pid(root) == 0)
    later = gate.tick(root, now=datetime(2099, 1, 1, tzinfo=timezone.utc))
    row = next(item for item in later["items"] if item["id"] == gate.DIRECTIVE_ID)
    check("expired lease leaves running", row["status"] == "STALE", row["status"])


def test_http(db_path: Path) -> None:
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
    old_catalog = ident.CATALOG_DB
    old_register = gm.REGISTER_PATH
    old_dash = sb.DASHBOARDS
    old_db_env = os.environ.get("BETA_SCOPED_AUTH_DB")
    old_state_env = os.environ.get("WOLF_CONTROL_STATE")
    os.environ["BETA_SCOPED_AUTH_DB"] = str(db_path)
    os.environ["WOLF_CONTROL_STATE"] = str(db_path.parent / "wolf-control")
    ident.CATALOG_DB = db_path
    gm.REGISTER_PATH = ROOT / "state" / "god-mode" / "GOD-MODE-REGISTER-2026-10-04.json"
    sb.DASHBOARDS = ROOT / "dashboards"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(method: str, path: str, subject: str | None = None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        data = None
        if method == "POST":
            headers["Content-Type"] = "application/json"
            data = json.dumps(body or {}).encode()
        if subject:
            headers["X-Wolf-Subject"] = subject
        req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method, data=data)
        try:
            with urlopen(req, timeout=60) as resp:
                return resp.status, resp.read()
        except HTTPError as exc:
            return exc.code, exc.read()

    def parsed(body: bytes) -> dict:
        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    try:
        status, body = call("GET", "/api/owner/god-mode-register")
        check("anon god mode 403", status == 403 and b"numerator" not in body, f"{status} {body[:180]!r}")
        status, body = call("GET", "/api/owner/god-mode-register", "devi@wolfcommand.test")
        check("staff god mode 403", status == 403 and b"GOD-MODE" not in body, f"{status} {body[:180]!r}")
        status, body = call("GET", "/api/owner/pulse-ro")
        check("anon pulse 403", status == 403, f"{status} {body[:120]!r}")
        status, body = call("GET", "/api/owner/pulse-ro", "devi@wolfcommand.test")
        check("staff pulse 403", status == 403, f"{status} {body[:120]!r}")
        status, body = call("GET", "/api/amg/sales-desk")
        check("anon amg desk 403", status == 403, str(status))
        status, body = call("GET", "/api/amg/sales-desk", "devi@wolfcommand.test")
        check("staff amg desk 403", status == 403, str(status))
        status, body = call("GET", "/api/amg/guest-stay", "devi@wolfcommand.test")
        check("staff guest stay 403", status == 403, str(status))
        status, body = call("GET", "/api/core/persons/PERS-AMG")
        data = parsed(body)
        check(
            "anon person 403",
            status == 403 and data.get("error") != "not_found" and "display_name" not in json.dumps(data),
            f"{status} {body[:180]!r}",
        )
        status, body = call("GET", "/api/core/persons/PERS-AMG", "devi@wolfcommand.test")
        data = parsed(body)
        check(
            "staff other person 403",
            status == 403 and data.get("error") != "not_found" and "amg.seat" not in body.decode(errors="replace"),
            f"{status} {body[:180]!r}",
        )
        status, body = call("GET", "/api/core/persons/PERS-NOPE", "devi@wolfcommand.test")
        check("missing person stays 403 before existence", status == 403 and b"not_found" not in body, f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/core/persons/PERS-AMG/auth-identities", "devi@wolfcommand.test")
        check("staff auth identities 403", status == 403 and b"amg.seat" not in body, f"{status} {body[:160]!r}")
        status, _body = call("GET", "/owner/god-mode")
        check("anon god mode page 403", status == 403, str(status))
        status, _body = call("GET", "/amg/sales-desk")
        check("anon sales page 403", status == 403, str(status))

        status, body = call("GET", "/api/owner/god-mode-register", "mrwolf@wolfcommand.net")
        data = parsed(body)
        check("owner god mode allowed", status == 200 and data.get("error") != "forbidden", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/owner/pulse-ro", "mrwolf@wolfcommand.net")
        data = parsed(body)
        check("owner pulse allowed", status == 200 and data.get("error") != "forbidden", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/amg/sales-desk", "mrwolf@wolfcommand.net")
        data = parsed(body)
        check("owner sales desk allowed", status == 200 and data.get("error") != "forbidden", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/amg/sales-desk", "amg.seat@wolfcommand.test")
        data = parsed(body)
        check("amg seat sales desk allowed", status == 200 and data.get("error") != "forbidden", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/amg/guest-stay", "amg.day@wolfcommand.test")
        data = parsed(body)
        check("amg day guest stay allowed", status == 200 and data.get("error") != "forbidden", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/owner/pulse-ro", "amg.seat@wolfcommand.test")
        check("amg seat pulse denied", status == 403, str(status))
        status, body = call("GET", "/amg/sales-desk", "amg.seat@wolfcommand.test")
        check("amg seat sales page allowed", status == 200, f"{status} {body[:80]!r}")
        status, body = call("GET", "/api/core/persons/PERS-DEVI", "devi@wolfcommand.test")
        data = parsed(body)
        check("self can read self", status == 200 and (data.get("person") or {}).get("person_id") == "PERS-DEVI", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/core/persons/PERS-AMG", "mrwolf@wolfcommand.net")
        data = parsed(body)
        check("owner reads other person", status == 200 and (data.get("person") or {}).get("person_id") == "PERS-AMG", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/core/persons/PERS-NOPE", "mrwolf@wolfcommand.net")
        data = parsed(body)
        check("owner missing person 404", status == 404 and data.get("error") == "not_found", f"{status} {body[:160]!r}")
        status, body = call("GET", "/api/core/persons", "devi@wolfcommand.test")
        data = parsed(body)
        ids = [row.get("person_id") for row in data.get("persons") or []]
        check("staff list is self only", status == 200 and ids == ["PERS-DEVI"], str(ids))

        status, body = call("GET", "/api/owner/front-door", "mrwolf@wolfcommand.net")
        data = parsed(body)
        tiles = ((data.get("pulse") or {}).get("tiles") or [])
        check(
            "owner front door",
            status == 200
            and data.get("human_commissioned") is False
            and data.get("staff_ready") is False
            and len(tiles) >= 6,
            f"{status} commissioned={data.get('human_commissioned')} tiles={len(tiles)} {body[:180]!r}",
        )
        status, body = call("GET", "/api/owner/front-door")
        check("anon front door 403", status == 403, str(status))
        status, body = call(
            "POST",
            "/api/owner/ask",
            "mrwolf@wolfcommand.net",
            {"question": "GGV Finance status"},
        )
        data = parsed(body)
        check(
            "ask ggv",
            status == 200 and str(data.get("answer") or "").startswith("GGV Finance is NOT HUMAN COMMISSIONED"),
            f"{status} {data.get('answer')!r}",
        )
        html = (ROOT / "dashboards" / "owner-empire-pack.html").read_text(encoding="utf-8")
        check(
            "owner home surfaces",
            all(
                token in html
                for token in (
                    'id="owner-pulse"',
                    'id="ask-wolf-form"',
                    "/api/owner/front-door",
                    "/api/owner/ask",
                    'id="running-now"',
                    'id="owner-needs-you"',
                )
            ),
        )
    finally:
        httpd.shutdown()
        ident.CATALOG_DB = old_catalog
        gm.REGISTER_PATH = old_register
        sb.DASHBOARDS = old_dash
        if old_db_env is None:
            os.environ.pop("BETA_SCOPED_AUTH_DB", None)
        else:
            os.environ["BETA_SCOPED_AUTH_DB"] = old_db_env
        if old_state_env is None:
            os.environ.pop("WOLF_CONTROL_STATE", None)
        else:
            os.environ["WOLF_CONTROL_STATE"] = old_state_env


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="beta-os-gate-") as tmp:
        db_path = Path(tmp) / "beta-os" / "catalog.sqlite"
        conn = seed(db_path)
        try:
            test_scope(conn)
        finally:
            conn.close()
        test_policy(Path(tmp) / "policy")
        test_supervisor(Path(tmp) / "supervisor")
        test_http(db_path)
    print(f"{PASS} passed, {FAIL} failed", flush=True)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
