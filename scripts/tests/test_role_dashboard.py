#!/usr/bin/env python3
"""W3-P3 role dashboards — succession, scope, phone and desktop.

Temporary seats are removed. No production. No payment.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
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
from core import work_items as wi  # noqa: E402

PASS = 0
FAIL = 0
CATALOG = ROOT / "catalog" / "content_library.sqlite"
HTML = ROOT / "dashboards" / "my-work.html"

HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
MATT = "mrwolf@wolfcommand.net"

WI_GGV = "WI-W3P3-GGV"
WI_BZG = "WI-W3P3-BZG"
WI_AMG = "WI-W3P3-AMG"

SEATS = (
    ("PERS-W3P3-CD", "w3p3-cd@seed.invalid", "ASG-W3P3-CD", "POS-W3P3-CD"),
    ("PERS-W3P3-FB", "w3p3-fb@seed.invalid", "ASG-W3P3-FB", "POS-W3P3-FB"),
    ("PERS-W3P3-FIN-A", "w3p3-fin-a@seed.invalid", "ASG-W3P3-FIN-A", "POS-W3P3-FIN-A"),
    ("PERS-W3P3-FIN-B", "w3p3-fin-b@seed.invalid", "ASG-W3P3-FIN-B", "POS-W3P3-FIN-B"),
    ("PERS-W3P3-CL-A", "w3p3-cl-a@seed.invalid", "ASG-W3P3-CL-A", "POS-W3P3-CL-A"),
    ("PERS-W3P3-CL-B", "w3p3-cl-b@seed.invalid", "ASG-W3P3-CL-B", "POS-W3P3-CL-B"),
    ("PERS-W3P3-GM-A", "w3p3-gm-a@seed.invalid", "ASG-W3P3-GM-A", "POS-W3P3-GM-A"),
    ("PERS-W3P3-GM-B", "w3p3-gm-b@seed.invalid", "ASG-W3P3-GM-B", "POS-W3P3-GM-B"),
    ("PERS-W3P3-OWN", "w3p3-own@seed.invalid", "ASG-W3P3-OWN", "POS-W3P3-OWN"),
)


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


def _wipe() -> None:
    c = _conn()
    try:
        c.execute("DELETE FROM core_work_items WHERE work_item_id LIKE 'WI-W3P3-%'")
        c.execute("DELETE FROM org_assignment_scopes WHERE assignment_id LIKE 'ASG-W3P3-%'")
        c.execute("DELETE FROM org_assignments WHERE assignment_id LIKE 'ASG-W3P3-%' OR person_id LIKE 'PERS-W3P3-%'")
        c.execute(
            "DELETE FROM org_auth_identities WHERE person_id LIKE 'PERS-W3P3-%' OR identifier LIKE 'w3p3-%@seed.invalid'"
        )
        c.execute("DELETE FROM org_persons WHERE person_id LIKE 'PERS-W3P3-%'")
        c.execute("DELETE FROM org_positions WHERE position_id LIKE 'POS-W3P3-%'")
        c.commit()
    finally:
        c.close()


def _scopes_of(person_id: str) -> list[str]:
    c = _conn()
    try:
        rows = c.execute(
            """
            SELECT DISTINCT s.scope_id
            FROM org_assignments a
            JOIN org_assignment_scopes s ON s.assignment_id = a.assignment_id
            WHERE a.person_id = ?
              AND a.status = 'ACTIVE' AND a.end_at IS NULL
              AND s.status = 'ACTIVE' AND s.end_at IS NULL
            ORDER BY s.scope_id
            """,
            (person_id,),
        ).fetchall()
        return [str(r["scope_id"]) for r in rows]
    finally:
        c.close()


def _seat(
    person_id: str,
    email: str,
    display: str,
    assignment_id: str,
    position_id: str,
    role_id: str,
    copy_position_from: str,
    scopes: list[str],
) -> None:
    ts = wi.now_utc_iso()
    c = _conn()
    try:
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
            (position_id, role_id, src["entity_id"], src["position_label"], ts, ts),
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


def _work(work_id: str, title: str, entity: str, person_id: str, assignment_id: str) -> None:
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
              ?, ?, NULL, 'CONTENT', 'OPEN', 3,
              ?, 'HUMAN', NULL, 'PERSON',
              ?, ?, ?,
              NULL, NULL, NULL, NULL, NULL,
              NULL, NULL, ?, ?
            )
            """,
            (work_id, title, entity, person_id, person_id, assignment_id, ts, ts),
        )
        c.commit()
    finally:
        c.close()


def _ids(report: dict) -> set[str]:
    found = set()
    for section in report.get("sections") or []:
        for item in section.get("items") or []:
            found.add(str(item.get("id") or ""))
    dash = report.get("dashboard") or {}
    for section in dash.get("sections") or []:
        for item in section.get("items") or []:
            found.add(str(item.get("id") or ""))
    return found


def _section(report: dict, key: str) -> dict:
    for section in (report.get("dashboard") or {}).get("sections") or []:
        if section.get("key") == key:
            return section
    return {}


def _perf(report: dict) -> dict:
    return _section(report, "responsibilities").get("performance") or {}


def test_framework_and_succession() -> None:
    src = (SCRIPTS / "core" / "role_dashboard.py").read_text(encoding="utf-8").lower()
    home_src = (SCRIPTS / "core" / "staff_home.py").read_text(encoding="utf-8").lower()
    for token in ("haikal", "devi", "pers-matt", "amanda", "misa"):
        check(f"dashboard source has no {token}", token not in src and token not in home_src)
    page = HTML.read_text(encoding="utf-8")
    check("page has no role ids", "ROLE-" not in page and "PERS-" not in page)
    check("page uses shared truth", "wolf-truth" in page and "data-performance" in page)
    check("page viewport", "width=device-width" in page)

    _wipe()
    try:
        _seat(
            "PERS-W3P3-CD", "w3p3-cd@seed.invalid", "CD Replacement",
            "ASG-W3P3-CD", "POS-W3P3-CD", "ROLE-GGV-CREATIVE-DIRECTOR",
            "POS-GGV-CREATIVE-DIRECTOR-1", _scopes_of("PERS-HAIKAL"),
        )
        _seat(
            "PERS-W3P3-FB", "w3p3-fb@seed.invalid", "FB Replacement",
            "ASG-W3P3-FB", "POS-W3P3-FB", "ROLE-BZG-FB-OPS-LEAD",
            "POS-BZG-FB-OPS-1", _scopes_of("PERS-DEVI"),
        )
        finance_scopes = ["SCOPE-GGV-FINANCE"]
        _seat(
            "PERS-W3P3-FIN-A", "w3p3-fin-a@seed.invalid", "Finance A",
            "ASG-W3P3-FIN-A", "POS-W3P3-FIN-A", "ROLE-GGV-EXTERNAL-ACCOUNTANT",
            "POS-GGV-EXT-ACCT", finance_scopes,
        )
        _seat(
            "PERS-W3P3-FIN-B", "w3p3-fin-b@seed.invalid", "Finance B",
            "ASG-W3P3-FIN-B", "POS-W3P3-FIN-B", "ROLE-GGV-EXTERNAL-ACCOUNTANT",
            "POS-GGV-EXT-ACCT", finance_scopes,
        )
        uma = ["SCOPE-BZG-UMA"]
        _seat(
            "PERS-W3P3-CL-A", "w3p3-cl-a@seed.invalid", "Closer A",
            "ASG-W3P3-CL-A", "POS-W3P3-CL-A", "ROLE-BZG-CLOSER",
            "POS-BZG-CLOSER-UMA-1", uma,
        )
        _seat(
            "PERS-W3P3-CL-B", "w3p3-cl-b@seed.invalid", "Closer B",
            "ASG-W3P3-CL-B", "POS-W3P3-CL-B", "ROLE-BZG-CLOSER",
            "POS-BZG-CLOSER-UMA-1", uma,
        )
        atrium = ["SCOPE-AMG-ATR-DAY"]
        _seat(
            "PERS-W3P3-GM-A", "w3p3-gm-a@seed.invalid", "Manager A",
            "ASG-W3P3-GM-A", "POS-W3P3-GM-A", "ROLE-AMG-GM",
            "POS-AMG-DAY-OPERATOR-FIXTURE", atrium,
        )
        _seat(
            "PERS-W3P3-GM-B", "w3p3-gm-b@seed.invalid", "Manager B",
            "ASG-W3P3-GM-B", "POS-W3P3-GM-B", "ROLE-AMG-GM",
            "POS-AMG-DAY-OPERATOR-FIXTURE", atrium,
        )
        _seat(
            "PERS-W3P3-OWN", "w3p3-own@seed.invalid", "Owner Replacement",
            "ASG-W3P3-OWN", "POS-W3P3-OWN", "ROLE-MATT",
            "POS-OWNER-EXEC-1", _scopes_of("PERS-MATT"),
        )

        pairs = (
            ("creative", "PERS-HAIKAL", "PERS-W3P3-CD"),
            ("fb lead", "PERS-DEVI", "PERS-W3P3-FB"),
            ("finance", "PERS-W3P3-FIN-A", "PERS-W3P3-FIN-B"),
            ("closer", "PERS-W3P3-CL-A", "PERS-W3P3-CL-B"),
            ("manager", "PERS-W3P3-GM-A", "PERS-W3P3-GM-B"),
            ("owner", "PERS-MATT", "PERS-W3P3-OWN"),
        )
        built = {pid: home.build_home(pid) for _label, left, right in pairs for pid in (left, right)}
        for label, left, right in pairs:
            a = home.fingerprint(built[left])
            b = home.fingerprint(built[right])
            check(f"{label} succession fingerprint", a == b, json.dumps({"left": a, "right": b})[:700])

        creative = built["PERS-HAIKAL"]
        fb = built["PERS-DEVI"]
        fin = built["PERS-W3P3-FIN-A"]
        closer = built["PERS-W3P3-CL-A"]
        manager = built["PERS-W3P3-GM-A"]
        owner = built["PERS-MATT"]
        misa = home.build_home("PERS-MISA")

        keys = [s["key"] for s in creative["dashboard"]["sections"]]
        check(
            "staff framework keys",
            keys == ["today", "do_this", "attention", "waiting", "completed", "responsibilities"],
        )
        check("creative representative", creative["dashboard"]["representative"] == "creative_director")
        check("fb representative", fb["dashboard"]["representative"] == "bzg_fb_ops")
        check(
            "finance is the external accountant role",
            fin["experience"] == "finance"
            and fin["dashboard"]["representative"] == "external_accountant"
            and fin["dashboard"]["also_represents"] == ["finance", "external_accountant"],
        )
        check("closer representative", closer["experience"] == "closer" and closer["dashboard"]["representative"] == "closer")
        check("manager representative", manager["experience"] == "manager" and manager["dashboard"]["representative"] == "manager")
        check("owner representative", owner["dashboard"]["representative"] == "owner")
        check("misa primary is not the manager page", misa["experience"] != "manager", misa["experience"])

        check("creative desk stays content", creative["desk"] == [{"label": "Open the content library", "href": "/content-2.0"}])
        check("fb desk stays uma", any(d["href"] == "/bzg/uma-blu" for d in fb["desk"]))
        check("finance desk stays notes", fin["desk"] == [{"label": "Open finance notes", "href": "/ggv/finance"}])
        check("closer desk is the close", closer["desk"] == [{"label": "Open today's close", "href": "/uma-blu-close"}])
        check("manager desk is the hotel", manager["desk"] == [{"label": "Open the hotel desk", "href": "/amg-ops-pack"}])
        check("closer has no finance desk", all("/finance" not in d["href"] for d in closer["desk"]))
        check("manager has no content desk", all("/content" not in d["href"] for d in manager["desk"]))
        check("creative has no uma desk", all("/uma" not in d["href"] and "/bzg" not in d["href"] for d in creative["desk"]))
        check("finance has no uma desk", all("/bzg" not in d["href"] for d in fin["desk"]))

        for label, report in (
            ("creative", creative),
            ("fb", fb),
            ("finance", fin),
            ("closer", closer),
            ("manager", manager),
            ("owner", owner),
        ):
            perf = _perf(report)
            check(
                f"{label} performance missing",
                perf.get("state") == "MISSING" and perf.get("shown_as_score") is False,
                str(perf),
            )
            check(f"{label} not staff ready", report["staff_ready"] is False and report["human_commissioned"] is False)
            check(f"{label} not commissioned on dashboard", report["dashboard"]["human_commissioned"] is False)
            truth = report["dashboard"]["truth"]
            check(
                f"{label} truth not shown stale as current",
                truth.get("display_state") != "STALE" or truth.get("shown_as_current") is False,
                str(truth),
            )

        check("creative cannot pay", creative["authority"]["move_money"] is False and creative["authority"]["change_bank"] is False)
        check("closer cannot pay", closer["authority"]["move_money"] is False and closer["authority"]["authorise_governance"] is False)
        check("manager cannot pay", manager["authority"]["move_money"] is False and manager["authority"]["finance_read"] is False)
        check("finance cannot pay", fin["authority"]["move_money"] is False and fin["authority"]["finance_edit"] is False)
        check("finance can review", fin["authority"]["finance_read"] is True and fin["authority"]["finance_review"] is True)

        _work(WI_GGV, "W3 content scratch", "ENT-GGV", "PERS-W3P3-CD", "ASG-W3P3-CD")
        _work(WI_BZG, "W3 close scratch", "ENT-BZG", "PERS-W3P3-CL-A", "ASG-W3P3-CL-A")
        _work(WI_AMG, "W3 hotel scratch", "ENT-AMG", "PERS-W3P3-GM-A", "ASG-W3P3-GM-A")
        cd = home.build_home("PERS-W3P3-CD")
        haikal = home.build_home("PERS-HAIKAL")
        cl_a = home.build_home("PERS-W3P3-CL-A")
        cl_b = home.build_home("PERS-W3P3-CL-B")
        gm_a = home.build_home("PERS-W3P3-GM-A")
        gm_b = home.build_home("PERS-W3P3-GM-B")
        fin_a = home.build_home("PERS-W3P3-FIN-A")
        devi = home.build_home("PERS-DEVI")
        check("ggv scratch shows for its owner", WI_GGV in _ids(cd))
        check("ggv scratch hidden from the other creative seat", WI_GGV not in _ids(haikal))
        check("ggv scratch hidden from closer", WI_GGV not in _ids(cl_a))
        check("ggv scratch hidden from manager", WI_GGV not in _ids(gm_a))
        check("ggv scratch hidden from finance", WI_GGV not in _ids(fin_a))
        check("ggv scratch hidden from fb lead", WI_GGV not in _ids(devi))
        check("bzg scratch shows for its closer", WI_BZG in _ids(cl_a))
        check("bzg scratch hidden from the other closer", WI_BZG not in _ids(cl_b))
        check("bzg scratch hidden from fb lead", WI_BZG not in _ids(devi))
        check("bzg scratch hidden from creative", WI_BZG not in _ids(cd))
        check("bzg scratch hidden from finance", WI_BZG not in _ids(fin_a))
        check("amg scratch shows for its manager", WI_AMG in _ids(gm_a))
        check("amg scratch hidden from the other manager", WI_AMG not in _ids(gm_b))
        check("amg scratch hidden from creative", WI_AMG not in _ids(cd))
        check("amg scratch hidden from closer", WI_AMG not in _ids(cl_a))
        c = _conn()
        try:
            c.execute("DELETE FROM core_work_items WHERE work_item_id LIKE 'WI-W3P3-%'")
            c.commit()
        finally:
            c.close()
        check(
            "creative fingerprint after scratch removed",
            home.fingerprint(home.build_home("PERS-HAIKAL")) == home.fingerprint(home.build_home("PERS-W3P3-CD")),
        )
    finally:
        _wipe()


def test_http_and_headless() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler and obj.__name__ == "BetaHandler":
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
            with urlopen(req, timeout=40) as resp:
                return resp.status, resp.read()
        except HTTPError as exc:
            return exc.code, exc.read()

    _wipe()
    try:
        _seat(
            "PERS-W3P3-CD", "w3p3-cd@seed.invalid", "CD Replacement",
            "ASG-W3P3-CD", "POS-W3P3-CD", "ROLE-GGV-CREATIVE-DIRECTOR",
            "POS-GGV-CREATIVE-DIRECTOR-1", _scopes_of("PERS-HAIKAL"),
        )
        _seat(
            "PERS-W3P3-FB", "w3p3-fb@seed.invalid", "FB Replacement",
            "ASG-W3P3-FB", "POS-W3P3-FB", "ROLE-BZG-FB-OPS-LEAD",
            "POS-BZG-FB-OPS-1", _scopes_of("PERS-DEVI"),
        )
        _seat(
            "PERS-W3P3-FIN-A", "w3p3-fin-a@seed.invalid", "Finance A",
            "ASG-W3P3-FIN-A", "POS-W3P3-FIN-A", "ROLE-GGV-EXTERNAL-ACCOUNTANT",
            "POS-GGV-EXT-ACCT", ["SCOPE-GGV-FINANCE"],
        )
        _seat(
            "PERS-W3P3-CL-A", "w3p3-cl-a@seed.invalid", "Closer A",
            "ASG-W3P3-CL-A", "POS-W3P3-CL-A", "ROLE-BZG-CLOSER",
            "POS-BZG-CLOSER-UMA-1", ["SCOPE-BZG-UMA"],
        )
        _seat(
            "PERS-W3P3-GM-A", "w3p3-gm-a@seed.invalid", "Manager A",
            "ASG-W3P3-GM-A", "POS-W3P3-GM-A", "ROLE-AMG-GM",
            "POS-AMG-DAY-OPERATOR-FIXTURE", ["SCOPE-AMG-ATR-DAY"],
        )
        _seat(
            "PERS-W3P3-OWN", "w3p3-own@seed.invalid", "Owner Replacement",
            "ASG-W3P3-OWN", "POS-W3P3-OWN", "ROLE-MATT",
            "POS-OWNER-EXEC-1", _scopes_of("PERS-MATT"),
        )

        st, raw = call("GET", "/my-work", None)
        body = raw.decode("utf-8", "replace")
        check("anon my-work 403", st == 403 and "permission-denied" in body, f"{st} {body[:180]}")
        st, raw = call("GET", "/api/staff/home", None)
        body = raw.decode("utf-8", "replace")
        check("anon api 403", st == 403 and "permission-denied" in body, f"{st} {body[:180]}")
        st, _raw = call("POST", "/api/staff/home/money", MATT)
        check("money write 405", st == 405, str(st))

        def denied(path: str, subject: str, label: str) -> None:
            status, payload = call("GET", path, subject)
            text = payload.decode("utf-8", "replace")
            served = status == 200 or "<!DOCTYPE" in text
            check(f"{label} denied {path}", status == 403 and not served, f"{status} {text[:180]}")

        def finance_closed(subject: str, label: str) -> None:
            status, payload = call("GET", "/ggv/finance", subject)
            text = payload.decode("utf-8", "replace")
            check(
                f"{label} finance page not served",
                status != 200 and "<!DOCTYPE" not in text,
                f"{status} {text[:180]}",
            )

        finance_closed("w3p3-cl-a@seed.invalid", "closer")
        denied("/content-2.0", "w3p3-cl-a@seed.invalid", "closer")
        finance_closed("w3p3-gm-a@seed.invalid", "manager")
        denied("/content-2.0", "w3p3-gm-a@seed.invalid", "manager")
        denied("/amg-ops-pack", HAIKAL, "creative")
        finance_closed(HAIKAL, "creative")
        denied("/bzg/uma-blu", "w3p3-fin-a@seed.invalid", "finance")
        denied("/content-2.0", "w3p3-fin-a@seed.invalid", "finance")
        denied("/uma-blu-close", HAIKAL, "creative")
        denied("/uma-blu-close", "w3p3-gm-a@seed.invalid", "manager")
        st, raw = call("GET", "/uma-blu-close", "w3p3-cl-a@seed.invalid")
        check("closer can open today's close", st == 200 and b"Close" in raw, str(st))

        st, raw = call("GET", "/api/staff/home", "w3p3-cl-a@seed.invalid")
        closer = json.loads(raw.decode())
        check("http closer 200", st == 200 and closer.get("experience") == "closer", str(st))
        st, raw = call("GET", "/api/staff/home", "w3p3-own@seed.invalid")
        owner = json.loads(raw.decode())
        check(
            "http owner succession",
            st == 200 and home.fingerprint(owner) == home.fingerprint(home.build_home("PERS-MATT")),
            str(st),
        )

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
                    with urlopen(req, timeout=40) as resp:
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

        cases = (
            ("cd-phone", HAIKAL, 390, ("Today", "What do I need to do today?", "Open the content library", "No performance figure is on record."), ("What's happening", "Open finance notes", "Open today's close")),
            ("cd-desk", HAIKAL, 1280, ("Do this", "Open the content library", 'data-dashboard="1"'), ("Open finance notes", "Open the hotel desk")),
            ("fb-phone", DEVI, 390, ("Open today's Uma Blu work", "Needs attention", 'data-representative="bzg_fb_ops"'), ("Open the content library", "Open finance notes")),
            ("cl-phone", "w3p3-cl-a@seed.invalid", 390, ("Open today's close", "Waiting", 'data-representative="closer"'), ("Open finance notes", "Open the content library")),
            ("gm-phone", "w3p3-gm-a@seed.invalid", 390, ("Open the hotel desk", "My responsibilities", 'data-representative="manager"'), ("Open finance notes", "Open today's Uma Blu work")),
            ("fin-desk", "w3p3-fin-a@seed.invalid", 1280, ("Open finance notes", "My responsibilities", 'data-performance="MISSING"'), ("What's happening", "Open today's close")),
            ("own-phone", MATT, 390, ("What's happening", "What needs your decision", "No performance figure is on record."), ("What do I need to do today?", "Open the content library")),
            ("own-desk", MATT, 1280, ("Today", "Money or control at risk", 'data-representative="owner"'), ("What do I need to do today?",)),
        )
        for label, subject, width, needles, banned in cases:
            _Proxy.subject = subject
            proc = subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--virtual-time-budget=12000",
                    f"--window-size={width},844",
                    "--dump-dom",
                    f"http://127.0.0.1:{pport}/my-work",
                ],
                capture_output=True,
                text=True,
                timeout=45,
            )
            dom = proc.stdout or ""
            for needle in needles:
                check(f"{label} shows {needle}", needle in dom, proc.stderr[-160:])
            for ban in banned:
                check(f"{label} hides {ban}", ban not in dom)
            check(
                f"{label} laid out",
                'data-ready="1"' in dom and 'data-overflow="no"' in dom,
                "ready" if 'data-ready="1"' in dom else "not-ready",
            )
        proxy.shutdown()
    finally:
        _wipe()
        httpd.shutdown()
        c = _conn()
        try:
            left = c.execute(
                """
                SELECT person_id FROM org_persons WHERE person_id LIKE 'PERS-W3P3-%'
                UNION ALL
                SELECT position_id FROM org_positions WHERE position_id LIKE 'POS-W3P3-%'
                UNION ALL
                SELECT work_item_id FROM core_work_items WHERE work_item_id LIKE 'WI-W3P3-%'
                """
            ).fetchall()
        finally:
            c.close()
        check("temporary seats removed", left == [], str([tuple(r) for r in left]))


def main() -> int:
    test_framework_and_succession()
    test_http_and_headless()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
