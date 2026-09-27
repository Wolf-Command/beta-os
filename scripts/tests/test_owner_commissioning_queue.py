#!/usr/bin/env python3
"""Owner Commissioning / Needs Matt queue inside Progress — P0 prove."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
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

from core import owner_commissioning_queue as ocq  # noqa: E402
from core import progress_read_model as prm  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
HAIKAL = "haikal@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"
HTML = ROOT / "dashboards" / "progress.html"
MODULE = SCRIPTS / "core" / "owner_commissioning_queue.py"
REVIEW = ROOT / "docs" / "deliveries" / "GROK-REVIEW-WOLF-OWNER-COMMISSIONING-QUEUE-P0-2026-09-22.md"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def test_honesty() -> None:
    flags = ocq.honesty_flags()
    check("bound", flags["bound"] == "beta-owner-commissioning-safe")
    check("proven false", flags["proven"] is False and flags["invented_proven"] is False)
    check("ready false", flags["ready"] is False and flags["invented_ready"] is False)
    check("staff_ready false", flags["staff_ready"] is False)
    check("no invent human commissioned", flags["invented_human_commissioned"] is False)
    check("requires submit", flags["human_commissioned_requires_submit_evidence"] is True)
    check("clickup retired", flags["clickup_retired"] is True)
    check("telegram retired", flags["telegram_retired"] is True)
    check("inside progress", flags["inside_progress_not_new_db"] is True)
    for fn, code in (
        (ocq.refuse_proven, "proven_refused"),
        (ocq.refuse_ready, "ready_refused"),
        (ocq.refuse_staff_ready, "staff_ready_refused"),
        (ocq.refuse_human_commissioned_invent, "human_commissioned_invent_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except ocq.CommissioningQueueError as exc:
            check(f"{code}", exc.code == code)


def test_seed_queue() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = Path(td)
        q = ocq.build_queue(state_override=state)
        check("queue ok", q.get("ok") is True)
        cards = q.get("cards") or []
        check("seed cards >= 8", len(cards) >= 8, str(len(cards)))
        ids = {c["id"] for c in cards}
        check("global nav matt", "CMQ-GLOBAL-NAV-OWNER" in ids)
        check("nas haikal", "CMQ-NAS-HAIKAL" in ids)
        check("smart upload", "CMQ-SMART-UPLOAD-RETEST" in ids)
        check("devi uma", "CMQ-DEVI-UMA-MOBILE" in ids)
        check("amanda ggv", "CMQ-AMANDA-GGV" in ids)
        check("amg day", "CMQ-AMG-DAY" in ids)
        check("progress needs you", "CMQ-PROGRESS-NEEDS-YOU" in ids)
        check("integration health", "CMQ-INTEGRATION-HEALTH" in ids)
        nav = next(c for c in cards if c["id"] == "CMQ-GLOBAL-NAV-OWNER")
        nas = next(c for c in cards if c["id"] == "CMQ-NAS-HAIKAL")
        check("nav needs matt", nav["audience"] == "NEEDS_MATT" and nav["person_to_test"] == "Matt")
        check("nas needs staff", nas["audience"] == "NEEDS_STAFF" and nas["person_to_test"] == "Haikal")
        check("nas staff_ready false", nas.get("staff_ready") is False)
        check("no invent commissioned", all(c.get("commissioned") is False for c in cards))
        check("proven false on cards", all(c.get("proven") is False for c in cards))
        check("ready false on cards", all(c.get("ready") is False for c in cards))
        retired = q.get("retired_systems") or []
        names = {(r.get("source_id") or "").lower() for r in retired}
        check("clickup in retired", "clickup" in names)
        check("telegram in retired", "telegram" in names)
        check("retired not commission", all(r.get("commission") is False for r in retired))
        counts = q.get("counters") or {}
        check("counters has needs matt", "NEEDS_MATT" in counts and counts["NEEDS_MATT"] >= 1)
        check("counters has needs staff", "NEEDS_STAFF" in counts and counts["NEEDS_STAFF"] >= 1)
        check("counters commissioned 0", counts.get("COMMISSIONED", -1) == 0)
        first = q.get("first_task") or {}
        check("first is needs matt p0", first.get("id") == "CMQ-GLOBAL-NAV-OWNER", str(first.get("id")))
        check("card fields", all(
            c.get("task") and c.get("do_this") and c.get("check") and c.get("open_href")
            for c in cards
        ))


def test_pass_and_problem() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = Path(td)
        # PASS path
        pass_out = ocq.submit_feedback(
            task_id="CMQ-GLOBAL-NAV-OWNER",
            feedback="PASS",
            comment="Owner reviewed nav desktop+phone",
            identity={"person_id": "PERS-MATT", "email": MATT},
            files=[
                {
                    "filename": "nav-proof.png",
                    "content_type": "image/png",
                    "data": b"\x89PNG\r\n\x1a\nfake",
                }
            ],
            state_override=state,
        )
        check("pass ok", pass_out.get("ok") is True)
        ev = pass_out.get("evidence") or {}
        check("pass evidence id", bool(ev.get("evidence_id")))
        check("pass criterion", ev.get("criterion_satisfied") is True)
        check("pass human commissioned card", ev.get("human_commissioned") is True)
        check("pass proven still false", ev.get("proven") is False)
        check("pass ready still false", ev.get("ready") is False)
        check("pass file provenance", bool((ev.get("files") or [{}])[0].get("sha256")))
        q1 = ocq.build_queue(state_override=state)
        nav = next(c for c in q1["cards"] if c["id"] == "CMQ-GLOBAL-NAV-OWNER")
        check("nav commissioned", nav["status"] == "COMMISSIONED" and nav["commissioned"] is True)
        check("commissioned count 1", q1["counters"]["COMMISSIONED"] == 1)

        # PROBLEM path + retest
        prob = ocq.submit_feedback(
            task_id="CMQ-NAS-HAIKAL",
            feedback="MOBILE PROBLEM",
            comment="Preview fails on phone",
            identity={"person_id": "PERS-MATT", "email": MATT},
            state_override=state,
            emit_retest_on_problem=True,
        )
        check("problem ok", prob.get("ok") is True)
        effects = prob.get("effects") or {}
        check("problem path", effects.get("path") == "PROBLEM")
        check("eng lane", (effects.get("engineering") or {}).get("engineering_lane") is True)
        check("matt not eng owner", effects.get("owner_manages_engineering") is False)
        check("retest emitted", bool((effects.get("retest") or {}).get("retest")))
        q2 = ocq.build_queue(state_override=state)
        nas = next(c for c in q2["cards"] if c["id"] == "CMQ-NAS-HAIKAL")
        check("nas engineering", nas["status"] == "ENGINEERING")
        retests = [c for c in q2["cards"] if c.get("status") == "RETEST"]
        check("retest card present", len(retests) >= 1, str(len(retests)))
        if retests:
            check("retest same person", retests[0]["person_to_test"] == "Haikal")
            check("retest needs staff", retests[0]["audience"] == "NEEDS_STAFF")
        hist = ocq.list_history(state_override=state)
        check("history rows >= 2", hist.get("count", 0) >= 2, str(hist.get("count")))
        check("evidence file exists", (state / "commissioning-evidence.jsonl").is_file())

        # No invent HUMAN COMMISSIONED without PASS evidence
        try:
            ocq.refuse_human_commissioned_invent({})
            check("invent refuse", False)
        except ocq.CommissioningQueueError as exc:
            check("invent refuse", exc.code == "human_commissioned_invent_refused")


def test_progress_compose() -> None:
    model = prm.build_read_model()
    check("progress ok", model.get("ok") is True)
    cmq = model.get("my_commissioning") or {}
    check("my_commissioning present", isinstance(cmq, dict) and cmq.get("ok") is True)
    empire = (model.get("views") or {}).get("Empire") or {}
    check("empire embeds queue", isinstance(empire.get("my_commissioning"), dict))
    flags = prm.honesty_flags()
    check("progress proven false", flags.get("proven") is False)
    check("progress ready false", flags.get("ready") is False)
    check("progress no invent commissioned", flags.get("invented_human_commissioned") is False)
    check("progress clickup retired", flags.get("clickup_retired") is True)


def test_html_surface() -> None:
    html = HTML.read_text(encoding="utf-8")
    check("html my commissioning", "MY COMMISSIONING" in html and "my-commissioning" in html)
    check("html feedback form", "data-cmq-form" in html and "feedback" in html)
    check("html counters", "Needs Matt" in html and "Ready to test" in html)
    check("html mobile css", "max-width: 640px" in html and "cmq-form button" in html)
    check("html start task", "Start Task 1" in html)
    check("html retired honesty", "ClickUp RETIRED" in html and "Telegram RETIRED" in html)
    check("html submit route", "/api/progress/commissioning/submit" in html)
    js = html.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/progress-cmq.js")
    tmp.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    check("progress js syntax", r.returncode == 0, (r.stderr or "OK")[:160])
    check("module exists", MODULE.is_file())


def test_http() -> None:
    ra._ENV_LOADED = True
    import inspect

    import serve_beta as sb

    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        return

    with tempfile.TemporaryDirectory() as td:
        os.environ["WOLF_COMMISSIONING_STATE_DIR"] = td
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            data = None
            if method != "GET":
                data = json.dumps({} if body is None else body).encode()
                headers["Content-Type"] = "application/json"
            req = Request(
                f"http://127.0.0.1:{port}{url_path}",
                headers=headers,
                method=method,
                data=data,
            )
            try:
                with urlopen(req, timeout=45) as resp:
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
            st, _ = call("GET", "/api/progress/commissioning", None)
            check("anon commissioning 403", st == 403, str(st))
            st, _ = call("GET", "/api/progress", None)
            check("anon progress 403", st == 403, str(st))
            st, _ = call("GET", "/api/progress/commissioning", HAIKAL)
            check("staff commissioning 403", st == 403, str(st))
            st, payload = call("GET", "/api/progress/commissioning", MATT)
            check("matt commissioning 200", st == 200 and payload.get("ok") is True, str(st))
            check("matt bound", payload.get("bound") == ocq.BOUND)
            check("matt cards", len(payload.get("cards") or []) >= 8)
            check("matt proven false", (payload.get("honesty") or {}).get("proven") is False)

            st, payload = call("GET", "/api/progress", MATT)
            check("matt progress embeds", st == 200 and isinstance((payload or {}).get("my_commissioning"), dict))

            st, payload = call(
                "POST",
                "/api/progress/commissioning/submit",
                MATT,
                {
                    "task_id": "CMQ-PROGRESS-NEEDS-YOU",
                    "feedback": "PASS",
                    "comment": "Honesty walkthrough ok",
                },
            )
            check("matt submit pass", st == 200 and payload.get("ok") is True, str(payload)[:160])
            check(
                "submit no invent proven",
                (payload.get("evidence") or {}).get("proven") is False
                and (payload.get("honesty") or {}).get("proven") is False,
            )

            st, payload = call(
                "POST",
                "/api/progress/commissioning/submit",
                MATT,
                {
                    "task_id": "CMQ-INTEGRATION-HEALTH",
                    "feedback": "PROBLEM",
                    "comment": "Retired banner unclear",
                },
            )
            check("matt submit problem", st == 200 and payload.get("ok") is True, str(payload)[:160])
            check(
                "problem eng",
                ((payload.get("effects") or {}).get("engineering") or {}).get("engineering_lane") is True,
            )

            st, payload = call(
                "POST",
                "/api/progress/commissioning/retest",
                MATT,
                {"parent_task_id": "CMQ-INTEGRATION-HEALTH"},
            )
            check("retest route", st == 200 and payload.get("ok") is True, str(payload)[:160])

            st, payload = call("GET", "/api/progress/commissioning/history", MATT)
            check("history 200", st == 200 and (payload.get("count") or 0) >= 2, str(payload)[:120])

            st, payload = call("POST", "/api/progress/commissioning/proven", MATT, {})
            check("proven refuse 405", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
            st, payload = call("POST", "/api/progress/commissioning/ready", MATT, {})
            check("ready refuse 405", st == 405 and payload.get("error") == "ready_refused", str(payload)[:120])
            st, payload = call("POST", "/api/progress/commissioning/human-commissioned", MATT, {})
            check(
                "human commissioned invent refuse",
                st == 405 and payload.get("error") == "human_commissioned_invent_refused",
                str(payload)[:120],
            )

            st, _ = call("POST", "/api/progress/commissioning/submit", HAIKAL, {"task_id": "x", "feedback": "PASS"})
            check("staff submit 403", st == 403, str(st))
            st, _ = call("GET", "/api/progress/commissioning", OUTSIDER)
            check("outsider 403", st == 403, str(st))
        finally:
            httpd.shutdown()
            os.environ.pop("WOLF_COMMISSIONING_STATE_DIR", None)


def test_ports() -> None:
    def up(port: int) -> bool:
        s = socket.socket()
        s.settimeout(1.5)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        finally:
            s.close()

    check("beta 8788 up", up(8788))
    check("prod 8787 up", up(8787))


def main() -> int:
    test_honesty()
    test_seed_queue()
    test_pass_and_problem()
    test_progress_compose()
    test_html_surface()
    test_http()
    test_ports()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
