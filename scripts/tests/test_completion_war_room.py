#!/usr/bin/env python3
"""Finish war room — 77 ledger projection, priority rule, no raise."""
from __future__ import annotations

import hashlib
import json
import os
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

from core import completion_war_room as war  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
HAIKAL = "haikalqilbari123@gmail.com"
AMANDA = "amanda@wolfcommand.net"
MISA = "mlsary111@gmail.com"
OUTSIDER = "not-a-seat@example.com"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
BACKUP = ROOT / "state" / "model-c-baseline-assessments.backup-20260927-w3p5.json"
PAGE = ROOT / "dashboards" / "finish-war-room.html"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_model() -> None:
    before = _sha(LEDGER)
    check("backup matches ledger", BACKUP.is_file() and _sha(BACKUP) == before)
    try:
        war.refuse_external_write({"amount": 1})
        check("writes refused", False)
    except war.WarRoomError as exc:
        check("writes refused", exc.code == "writes_refused")
    room = war.build_war_room()
    check("ledger unchanged", _sha(LEDGER) == before)
    check("read", room.get("ok") is True and room.get("read") == "READ")
    check("not staff ready", room.get("staff_ready") is False and room.get("staff_ready_count") == 0)
    check("not commissioned", room.get("human_commissioned") is False and room.get("human_commissioned_count") == 0)
    check("adoption not measured", room.get("operating_adoption") == "NOT MEASURED")
    check("no money", room.get("money") is None and room.get("payment_executed") is not True and room.get("green_kpi") is False)
    check("no ledger write", room.get("ledger_write") is False and room.get("raises") == [])
    check("system line", room.get("system_line") == "19.65 / 77 = 25.52%", str(room.get("system_line")))
    check("headline", room.get("headline", "").startswith("SYSTEM = 19.65 / 77 = 25.52%"))
    caps = room.get("capabilities") or []
    check("77 rows", len(caps) == 77 and room.get("system_n") == 77, str(len(caps)))
    ids = [row["id"] for row in caps]
    check("unique ids", len(set(ids)) == 77)
    check("no path leak", "/Users/" not in json.dumps(room))
    states = {row["system_state"] for row in caps}
    check("states canonical", states <= set(war.STATES), str(states))
    priorities = {row["priority"] for row in caps}
    check("priorities closed", priorities == set(war.PRIORITIES), str(priorities))
    by_id = {row["id"]: row for row in caps}
    check("intg-01 external p1", by_id["CAP-INTG-01"]["priority"] == "P1" and by_id["CAP-INTG-01"]["left_group"] == "external")
    check("core-02 commission", by_id["CAP-CORE-02"]["system_state"] == "READY" and by_id["CAP-CORE-02"]["left_group"] == "commission")
    check("ggv-05 future", by_id["CAP-GGV-05"]["priority"] == "P3" and by_id["CAP-GGV-05"]["left_group"] == "follow")
    check("sale-01 follows", by_id["CAP-SALE-01"]["priority"] == "P2")
    check("strat stays built", by_id["CAP-STRAT-02"]["system_state"] == "BUILT")
    for row in caps:
        check(
            f"{row['id']} flags false",
            row["staff_ready"] is False and row["human_commissioned"] is False and row["operating_adoption"] == "NOT MEASURED",
        )
        check(f"{row['id']} priority ignores a rename", war.priority_of(row["id"]) == row["priority"])
    groups = room["groups"]
    flat = groups["finish"] + groups["commission"] + groups["external"] + groups["follow"]
    check("groups partition", sorted(flat) == sorted(ids) and len(flat) == 77, str({k: len(v) for k, v in groups.items()}))
    check("critical is p0 p1", len(room["critical_path"]) == 32)
    check("refusals not applied", all(item["decision"] == "not raised" for item in room["raise_refusals"]))
    page = PAGE.read_text(encoding="utf-8")
    check("page bound", "beta-owner-safe" in page and "Finish war room" in page)
    check("page no pay", ">Pay<" not in page and ">Settle<" not in page)
    check("page mobile", "@media (max-width: 860px)" in page)
    check("page truth", 'data-surface="empire"' in page and "wolf-truth.js" in page)
    left = war.render_what_is_left(room)
    path_doc = war.render_critical_path(room)
    check("left has groups", "Must finish in the next 6 days" in left and "Must commission" in left and "Waiting on an external system" in left)
    check("left names yanolja work", "CAP-INTG-01" in left and "Connector code/tests/contract" in left)
    check("path orders kernel first", "1. CAP-CORE-02" in path_doc and "CAP-INTG-01" in path_doc)
    check("docs not vague dashboard", "improve dashboard" not in left.lower() and "finish finance" not in left.lower())


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
    before = _sha(LEDGER)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if method != "GET":
            data = json.dumps({} if body is None else body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=data)
        try:
            with urlopen(req, timeout=90) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode())
                except json.JSONDecodeError:
                    return resp.status, raw
        except HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed

    try:
        st, anon = call("GET", "/api/owner/war-room", None)
        check(
            "anon api 403",
            st == 403 and isinstance(anon, dict) and anon.get("ui", {}).get("component") == "permission-denied",
            str(anon)[:240],
        )
        st, outsider = call("GET", "/api/owner/war-room", OUTSIDER)
        check("outsider api 403", st == 403, str(st))
        for label, subject in (("devi", DEVI), ("amanda", AMANDA), ("haikal", HAIKAL), ("misa", MISA)):
            st, body = call("GET", "/api/owner/war-room", subject)
            check(
                f"{label} api 403",
                st == 403 and isinstance(body, dict) and body.get("ui", {}).get("component") == "permission-denied",
                str(body)[:180],
            )
        st, owner = call("GET", "/api/owner/war-room", MATT)
        check("owner api 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(type(owner)))
        if isinstance(owner, dict):
            check("owner line", owner.get("system_line") == "19.65 / 77 = 25.52%")
            check("owner counts", owner.get("staff_ready_count") == 0 and owner.get("human_commissioned_count") == 0)
            check("owner adoption", owner.get("operating_adoption") == "NOT MEASURED")
            check("owner rows", len(owner.get("capabilities") or []) == 77)
            check("owner no path", "/Users/" not in json.dumps(owner))
        st, missing = call("GET", "/api/owner/war-room/nope", MATT)
        check("unknown view 404", st == 404, str(st))
        for method in ("POST", "PUT", "PATCH"):
            code, body = call(method, "/api/owner/war-room", MATT, {"amount": 1})
            check(f"owner {method} 405", code == 405, str(body)[:160])
            code, body = call(method, "/api/owner/war-room", None, {})
            check(f"anon {method} 403", code == 403, str(code))
        for path in ("/finish-war-room", "/finish-war-room.html", "/dashboards/finish-war-room.html"):
            st, page = call("GET", path, None)
            check(f"anon {path} 403", st == 403, str(st))
            st, devi_page = call("GET", path, DEVI)
            denied = devi_page if isinstance(devi_page, dict) else {}
            check(
                f"devi {path} 403",
                st == 403 and denied.get("ui", {}).get("component") == "permission-denied",
                str(devi_page)[:160],
            )
        st, page_ok = call("GET", "/finish-war-room", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page_ok, (bytes, bytearray)) and b"Finish war room" in page_ok and b">Pay<" not in page_ok,
            str(st),
        )
        check("ledger still unchanged", _sha(LEDGER) == before)

        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        check("chrome present", chrome.is_file())
        if not chrome.is_file():
            return

        class _Proxy(BaseHTTPRequestHandler):
            subject = MATT

            def log_message(self, fmt: str, *args) -> None:
                return

            def do_GET(self):  # noqa: N802
                req = Request(
                    f"http://127.0.0.1:{port}{self.path}",
                    headers={"X-Wolf-Subject": _Proxy.subject, "Accept": "*/*"},
                    method="GET",
                )
                try:
                    with urlopen(req, timeout=90) as resp:
                        body = resp.read()
                        ctype = resp.headers.get("Content-Type") or "text/html"
                        code = resp.status
                except HTTPError as exc:
                    body = exc.read()
                    ctype = exc.headers.get("Content-Type") if exc.headers else "text/html"
                    code = exc.code
                self.send_response(code)
                self.send_header("Content-Type", ctype or "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        proxy = ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
        pport = proxy.server_address[1]
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        import subprocess

        shots = (
            ("owner-desktop", MATT, 1280, "/finish-war-room", ("Finish war room", "19.65 / 77 = 25.52%", "STAFF READY", "NOT MEASURED", "CAP-CORE-01", 'data-war-room-ready="1"', 'data-overflow="no"')),
            ("owner-mobile", MATT, 390, "/finish-war-room", ("CAP-INTG-01", "P0", "NOT MEASURED", 'data-overflow="no"')),
            ("staff-denied", DEVI, 390, "/finish-war-room", ("permission-denied",)),
        )
        for label, subject, width, path, needles in shots:
            _Proxy.subject = subject
            proc = subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--virtual-time-budget=20000",
                    f"--window-size={width},900",
                    "--dump-dom",
                    f"http://127.0.0.1:{pport}{path}",
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )
            dom = proc.stdout or ""
            for needle in needles:
                check(f"{label} shows {needle}", needle in dom, (proc.stderr or dom)[-240:])
        proxy.shutdown()
    finally:
        httpd.shutdown()


def main() -> int:
    test_model()
    test_http_and_headless()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
