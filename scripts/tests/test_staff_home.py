#!/usr/bin/env python3
"""P3 staff home — role experience, replacement seat, phone and desktop."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import request_auth as ra  # noqa: E402
from core import staff_home as home  # noqa: E402
from core import wolf_shell as shell  # noqa: E402
from core import work_items as wi  # noqa: E402

PASS = 0
FAIL = 0
CATALOG = ROOT / "catalog" / "content_library.sqlite"
HTML = ROOT / "dashboards" / "my-work.html"
SRC = SCRIPTS / "core" / "staff_home.py"

HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
MATT = "mrwolf@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"

REPLACE_ID = "PERS-P3-REPLACE"
REPLACE_EMAIL = "p3-replace@seed.invalid"
REPLACE_ASG = "ASG-P3-REPLACE"
REPLACE_POS = "POS-P3-CD-1"
FINANCE_ID = "PERS-P3-FINANCE"
FINANCE_EMAIL = "p3-finance@seed.invalid"
FINANCE_ASG = "ASG-P3-FINANCE"
SCRATCH_WI = "WI-P3-SCRATCH"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(CATALOG), timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _wipe_person(person_id: str, email: str, assignment_id: str, position_id: str | None = None) -> None:
    c = _conn()
    try:
        c.execute("DELETE FROM core_work_items WHERE work_item_id=?", (SCRATCH_WI,))
        c.execute("DELETE FROM org_assignment_scopes WHERE assignment_id=?", (assignment_id,))
        c.execute("DELETE FROM org_assignments WHERE assignment_id=?", (assignment_id,))
        c.execute(
            "DELETE FROM org_auth_identities WHERE person_id=? OR lower(identifier)=?",
            (person_id, email.lower()),
        )
        c.execute("DELETE FROM org_persons WHERE person_id=?", (person_id,))
        if position_id:
            c.execute("DELETE FROM org_positions WHERE position_id=?", (position_id,))
        c.commit()
    finally:
        c.close()


def _seat(
    person_id: str,
    email: str,
    display: str,
    assignment_id: str,
    position_id: str,
    source_asg: str | None,
    scope_id: str | None,
    *,
    new_position_role: str | None = None,
    copy_position_from: str | None = None,
) -> None:
    ts = wi.now_utc_iso()
    c = _conn()
    try:
        if new_position_role:
            src = c.execute(
                "SELECT entity_id, position_label FROM org_positions WHERE position_id=?",
                (copy_position_from,),
            ).fetchone()
            c.execute(
                """
                INSERT INTO org_positions (
                  position_id, role_id, entity_id, location_id, brand_id, department_id,
                  position_label, status, fte, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, NULL, NULL, ?, 'ACTIVE', 1, ?, ?)
                """,
                (
                    position_id,
                    new_position_role,
                    src["entity_id"],
                    src["position_label"],
                    ts,
                    ts,
                ),
            )
        c.execute(
            """
            INSERT INTO org_persons (
              person_id, display_name, legal_name, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'ACTIVE', ?, ?)
            """,
            (person_id, display, display, ts, ts),
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
        if source_asg:
            rows = c.execute(
                """
                SELECT scope_id FROM org_assignment_scopes
                WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
                """,
                (source_asg,),
            ).fetchall()
            scopes = [r["scope_id"] for r in rows]
        else:
            scopes = [scope_id] if scope_id else []
        for sid in scopes:
            c.execute(
                """
                INSERT INTO org_assignment_scopes (
                  assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (assignment_id, sid, ts, ts, ts),
            )
        c.commit()
    finally:
        c.close()


def test_real_seats() -> None:
    src = SRC.read_text(encoding="utf-8").lower()
    for token in ("haikal", "devi", "pers-matt", "amanda", "misa"):
        check(f"source has no {token}", token not in src)

    haikal = home.build_home("PERS-HAIKAL")
    check("creative experience", haikal["experience"] == "creative_director")
    check("creative role label", haikal["role"]["label"] == "Creative Director")
    check("creative greeting uses name", haikal["greeting"] == "Hello, Haikal")
    check("creative desk is content", haikal["desk"] == [{"label": "Open the content library", "href": "/content-2.0"}])
    check("creative no money", haikal["authority"]["move_money"] is False and haikal["authority"]["change_bank"] is False)
    check("creative no governance", haikal["authority"]["authorise_governance"] is False)
    check("creative no finance edit", haikal["authority"]["finance_edit"] is False)
    check("creative not commissioned", haikal["human_commissioned"] is False and haikal["staff_ready"] is False)
    titles = [s["title"] for s in haikal["sections"]]
    check(
        "creative four questions",
        titles == [
            "What do I need to do today?",
            "What needs my attention?",
            "What am I waiting for?",
            "What did I recently complete?",
        ],
    )
    check("creative today honest empty", haikal["sections"][0]["empty"] is True)

    devi = home.build_home("PERS-DEVI")
    check("fb lead experience", devi["experience"] == "bzg_fb_ops")
    check("fb lead role", "F&B" in (devi["role"]["label"] or "").upper())
    check("fb scopes include both", {"SCOPE-BZG-FB", "SCOPE-BZG-UMA"} <= set(devi["scopes"]))
    check("fb covers uma by venue", any("Uma" in c or "Blu" in c for c in devi["covers"]), str(devi["covers"]))
    check("fb desk is today work", any(d["href"] == "/bzg/uma-blu" for d in devi["desk"]))
    check("fb no content desk", all(d["href"] != "/content-2.0" for d in devi["desk"]))
    check("fb no finance desk", all("/finance" not in d["href"] for d in devi["desk"]))
    auth = devi["authority"]
    check(
        "fb no money bank governance",
        auth["move_money"] is False and auth["change_bank"] is False and auth["authorise_governance"] is False and auth["unrestricted"] is False,
    )
    check("fb no finance read", auth["finance_read"] is False and auth["finance_edit"] is False)

    owner = home.build_home("PERS-MATT")
    check("owner pulse", owner["experience"] == "owner_pulse")
    keys = [s["key"] for s in owner["sections"]]
    check(
        "owner six sections",
        keys == ["happening", "wrong", "authority", "blocked", "improving", "money"],
    )
    check("owner no staff questions", "What do I need to do today?" not in [s["title"] for s in owner["sections"]])
    check("owner no desk workflow", owner["desk"] == [])
    check("owner money section honest", owner["sections"][-1]["empty"] is True)
    check("owner can authorise governance", owner["authority"]["authorise_governance"] is True)
    check("owner dep retains authority", owner["founder_dependency"]["authority"] == "RETAIN")
    check("staff dep eliminates daily list", haikal["founder_dependency"]["daily_list"] == "ELIMINATE")

    page = HTML.read_text(encoding="utf-8")
    check("page has no role ids", "ROLE-" not in page and "PERS-" not in page)
    check("page viewport", 'width=device-width' in page)
    empire = (ROOT / "dashboards" / "owner-empire-pack.html").read_text(encoding="utf-8")
    check("empire has pulse mount", 'id="pulse"' in empire)


def test_replacement() -> None:
    _wipe_person(REPLACE_ID, REPLACE_EMAIL, REPLACE_ASG, REPLACE_POS)
    _wipe_person(FINANCE_ID, FINANCE_EMAIL, FINANCE_ASG)
    try:
        _seat(
            REPLACE_ID,
            REPLACE_EMAIL,
            "Replacement Seat",
            REPLACE_ASG,
            REPLACE_POS,
            "ASG-HAIKAL-CD-1",
            None,
            new_position_role="ROLE-GGV-CREATIVE-DIRECTOR",
            copy_position_from="POS-GGV-CREATIVE-DIRECTOR-1",
        )
        original = home.fingerprint(home.build_home("PERS-HAIKAL"))
        copy = home.fingerprint(home.build_home(REPLACE_ID))
        check("replacement fingerprint matches", original == copy, json.dumps({"original": original, "copy": copy})[:500])
        aud = shell.audience_for_person(REPLACE_ID)
        check("replacement audience from role", aud == shell.audience_for_person("PERS-HAIKAL") == "SPECIALIST_CONTENT", aud)

        ts = wi.now_utc_iso()
        c = _conn()
        try:
            c.execute(
                """
                INSERT INTO core_work_items (
                  work_item_id, title, description, work_type, status, priority,
                  owning_entity_id, source_type, source_id, created_by_actor_type,
                  created_by_person_id, owner_person_id, owner_org_assignment_id,
                  due_at, started_at, completed_at, verified_at, outcome,
                  completion_evidence_reference, parent_work_item_id, created_at, updated_at
                ) VALUES (
                  ?, 'P3 scratch today', NULL, 'CONTENT', 'OPEN', 3,
                  'ENT-GGV', 'HUMAN', NULL, 'PERSON',
                  ?, ?, ?,
                  NULL, NULL, NULL, NULL, NULL,
                  NULL, NULL, ?, ?
                )
                """,
                (SCRATCH_WI, REPLACE_ID, REPLACE_ID, REPLACE_ASG, ts, ts),
            )
            c.commit()
        finally:
            c.close()
        repl = home.build_home(REPLACE_ID)
        haikal = home.build_home("PERS-HAIKAL")
        devi = home.build_home("PERS-DEVI")
        repl_titles = repl["sections"][0]["items"]
        check("scratch shows for the owner of it", any(i["id"] == SCRATCH_WI for i in repl_titles))
        check("scratch hidden from creative director seat", all(i["id"] != SCRATCH_WI for i in haikal["sections"][0]["items"]))
        check("scratch hidden from fb lead", all(i["id"] != SCRATCH_WI for s in devi["sections"] for i in s["items"]))
        c = _conn()
        try:
            c.execute("DELETE FROM core_work_items WHERE work_item_id=?", (SCRATCH_WI,))
            c.commit()
        finally:
            c.close()
        check(
            "fingerprint matches after scratch removed",
            home.fingerprint(home.build_home("PERS-HAIKAL")) == home.fingerprint(home.build_home(REPLACE_ID)),
        )

        _seat(
            FINANCE_ID,
            FINANCE_EMAIL,
            "Finance Seat",
            FINANCE_ASG,
            "POS-GGV-EXT-ACCT",
            None,
            "SCOPE-GGV-FINANCE",
        )
        fin = home.build_home(FINANCE_ID)
        check("finance experience", fin["experience"] == "finance")
        check("finance desk", fin["desk"] == [{"label": "Open finance notes", "href": "/ggv/finance"}])
        check("finance read review", fin["authority"]["finance_read"] is True and fin["authority"]["finance_review"] is True)
        check("finance cannot edit or pay", fin["authority"]["finance_edit"] is False and fin["authority"]["move_money"] is False and fin["authority"]["change_bank"] is False)
        check("finance no governance", fin["authority"]["authorise_governance"] is False)
        check("finance not owner pulse", "happening" not in [s["key"] for s in fin["sections"]])
        check("finance audience", shell.audience_for_person(FINANCE_ID) == "SPECIALIST_FINANCE")
        check("finance dep payment retained", fin["founder_dependency"]["payment"] == "RETAIN")
        check("known haikal audience unchanged", shell.audience_for_person("PERS-HAIKAL") == "SPECIALIST_CONTENT")
        check("known devi landing unchanged", shell.build_whoami(person_id="PERS-DEVI").get("landing") == "/bzg/uma-blu")
    finally:
        _wipe_person(REPLACE_ID, REPLACE_EMAIL, REPLACE_ASG, REPLACE_POS)
        _wipe_person(FINANCE_ID, FINANCE_EMAIL, FINANCE_ASG)
        c = _conn()
        try:
            left = c.execute(
                """
                SELECT person_id FROM org_persons WHERE person_id IN (?, ?)
                UNION ALL
                SELECT position_id FROM org_positions WHERE position_id=?
                """,
                (REPLACE_ID, FINANCE_ID, REPLACE_POS),
            ).fetchall()
            wi_left = c.execute(
                "SELECT work_item_id FROM core_work_items WHERE work_item_id=?",
                (SCRATCH_WI,),
            ).fetchone()
        finally:
            c.close()
        check("replacement removed", left == [] and wi_left is None, str(left))


def test_http_and_headless() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            if obj.__name__ == "BetaHandler":
                Handler = obj
                break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(method: str, path: str, subject: str | None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method)
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, raw
        except HTTPError as exc:
            return exc.code, exc.read()

    try:
        _wipe_person(REPLACE_ID, REPLACE_EMAIL, REPLACE_ASG, REPLACE_POS)
        _wipe_person(FINANCE_ID, FINANCE_EMAIL, FINANCE_ASG)
        _seat(
            REPLACE_ID,
            REPLACE_EMAIL,
            "Replacement Seat",
            REPLACE_ASG,
            REPLACE_POS,
            "ASG-HAIKAL-CD-1",
            None,
            new_position_role="ROLE-GGV-CREATIVE-DIRECTOR",
            copy_position_from="POS-GGV-CREATIVE-DIRECTOR-1",
        )
        _seat(FINANCE_ID, FINANCE_EMAIL, "Finance Seat", FINANCE_ASG, "POS-GGV-EXT-ACCT", None, "SCOPE-GGV-FINANCE")

        st, raw = call("GET", "/api/staff/home", None)
        check("anon api 403", st == 403, str(st))
        st, raw = call("GET", "/my-work", None)
        check("anon page 403", st == 403, str(st))
        st, raw = call("GET", "/api/staff/home", OUTSIDER)
        check("outsider 403", st == 403, str(st))
        st, raw = call("POST", "/api/staff/home/money", MATT)
        check("money write 405", st == 405, str(st))

        def payload(subject: str) -> dict:
            status, body = call("GET", "/api/staff/home", subject)
            check(f"{subject} home 200", status == 200, str(status))
            return json.loads(body.decode())

        haikal = payload(HAIKAL)
        repl = payload(REPLACE_EMAIL)
        devi = payload(DEVI)
        fin = payload(FINANCE_EMAIL)
        owner = payload(MATT)
        check("http replacement match", home.fingerprint(haikal) == home.fingerprint(repl))
        check("http fb lead", devi.get("experience") == "bzg_fb_ops")
        check("http finance", fin.get("experience") == "finance" and fin["authority"]["move_money"] is False)
        check("http owner pulse", owner.get("experience") == "owner_pulse")
        st, raw = call("GET", "/my-work", HAIKAL)
        check("haikal page 200", st == 200 and b"My Work" in raw, str(st))
        st, raw = call("GET", "/wolf", MATT)
        check("owner wolf 200", st == 200 and b'id="pulse"' in raw, str(st))

        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        check("chrome present", chrome.is_file())
        if not chrome.is_file():
            return

        class _Proxy(BaseHTTPRequestHandler):
            subject = HAIKAL

            def log_message(self, *_args):  # noqa: ANN002
                return

            def do_GET(self):  # noqa: N802
                req = Request(
                    f"http://127.0.0.1:{port}{self.path}",
                    headers={"X-Wolf-Subject": _Proxy.subject, "Accept": "*/*"},
                    method="GET",
                )
                try:
                    with urlopen(req, timeout=30) as resp:
                        body = resp.read()
                        ctype = resp.headers.get("Content-Type") or "text/html"
                        code = resp.status
                except HTTPError as exc:
                    body = exc.read()
                    ctype = exc.headers.get("Content-Type") if exc.headers else "text/html"
                    code = exc.code
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        proxy = ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
        pport = proxy.server_address[1]
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        import subprocess

        for label, subject, width, needle, banned, ready in (
            ("cd-phone", HAIKAL, 390, "What do I need to do today?", "What's happening", "data-ready"),
            ("cd-desk", HAIKAL, 1280, "Open the content library", "Open finance notes", "data-ready"),
            ("fb-phone", DEVI, 390, "Open today's Uma Blu work", "Open the content library", "data-ready"),
            ("fin-desk", FINANCE_EMAIL, 1280, "Open finance notes", "What's happening", "data-ready"),
            ("owner-phone", MATT, 390, "Money or control at risk", "What do I need to do today?", "data-pulse-ready"),
            ("owner-desk", MATT, 1280, "What's happening", "What do I need to do today?", "data-pulse-ready"),
        ):
            _Proxy.subject = subject
            path = "/wolf" if label.startswith("owner") else "/my-work"
            proc = subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--virtual-time-budget=8000",
                    f"--window-size={width},844",
                    "--dump-dom",
                    f"http://127.0.0.1:{pport}{path}",
                ],
                capture_output=True,
                text=True,
                timeout=40,
            )
            dom = proc.stdout or ""
            check(f"{label} shows {needle}", needle in dom, proc.stderr[-180:])
            check(f"{label} hides other experience", banned not in dom)
            ready_ok = f'{ready}="1"' in dom
            overflow = 'data-overflow="no"' in dom
            check(f"{label} laid out", ready_ok and overflow, "ready" if ready_ok else "not-ready")
        proxy.shutdown()
    finally:
        _wipe_person(REPLACE_ID, REPLACE_EMAIL, REPLACE_ASG, REPLACE_POS)
        _wipe_person(FINANCE_ID, FINANCE_EMAIL, FINANCE_ASG)
        httpd.shutdown()


def test_ports() -> None:
    def up(port: int) -> bool:
        s = socket.socket()
        s.settimeout(1.5)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        finally:
            s.close()

    check("prod 8787 up", up(8787))
    check("beta 8788 up", up(8788))


def main() -> int:
    test_real_seats()
    test_replacement()
    test_http_and_headless()
    test_ports()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
