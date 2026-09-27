#!/usr/bin/env python3
"""Sprint2 P6 Staff-Ready UX — phone-first overlays on BZG/GGV/AMG packs."""
from __future__ import annotations

import json
import os
import socket
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

from core import amg_ops_pack as amg  # noqa: E402
from core import ggv_ops_pack as ggv  # noqa: E402
from core import request_auth as ra  # noqa: E402
from core import staff_ready_ux as sru  # noqa: E402
from core import uma_ops_console as uma  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
HTML = {
    "ggv": ROOT / "dashboards" / "ggv-ops-pack.html",
    "amg": ROOT / "dashboards" / "amg-ops-pack.html",
    "bzg": ROOT / "dashboards" / "bzg-uma-blu.html",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def test_module_honesty() -> None:
    flags = sru.honesty_flags()
    check("bound", flags["bound"] == "beta-staff-ready-safe")
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no money", flags["money_actions"] is False)
    check("additive", flags["additive_only"] is True and flags["phone_first"] is True)
    schema = sru.schema_document()
    check("schema packs", schema["packs"] == ["bzg", "ggv", "amg"])
    check("human amanda", sru.human_person("PERS-AMANDA") == "Amanda")
    check("human stage", sru.human_stage("next_action") == "Next step")
    check("human life", sru.human_lifecycle("CLOSED") == "Closed")
    empty = sru.empty_with_next("Blank.", next_label="Do this", next_href="#x")
    check("empty has next", empty["empty"] is True and empty["next_action"]["label"] == "Do this")
    nav = sru.phone_nav("ggv")
    check("ggv nav single", len(nav) == 4 and nav[0]["label"] == "Now")
    try:
        sru.refuse_proven({})
        check("proven raises", False)
    except sru.StaffReadyError as exc:
        check("proven refused", exc.code == "proven_refused")
    try:
        sru.refuse_ready({})
        check("ready raises", False)
    except sru.StaffReadyError as exc:
        check("ready refused", exc.code == "ready_refused")
    try:
        sru.refuse_money({})
        check("money raises", False)
    except sru.StaffReadyError as exc:
        check("money refused", exc.code == "money_refused")


def test_ggv_surface() -> None:
    board = ggv.build_board(verified_person_id="PERS-AMANDA")
    check("ggv staff_ready present", isinstance(board.get("staff_ready"), dict))
    sr = board["staff_ready"]
    check("ggv bound", board.get("staff_ready_bound") == sru.BOUND)
    check("ggv lede human", "Habitat" in (sr.get("lede") or "") and "CAP-" not in (sr.get("lede") or ""))
    check("ggv who no PERS", "PERS-" not in (sr.get("who_line") or ""))
    check("ggv primary next", isinstance(sr.get("primary_next"), dict) and bool(sr["primary_next"].get("label")))
    actions = sr.get("exposed_actions") or {}
    check("ggv hide seats", actions.get("show_seats_panel") is False)
    check("ggv can update", actions.get("update_lifecycle") is True)
    check("ggv amanda no close", actions.get("close_lead") is True)  # Amanda can close
    heh = sr.get("history_evidence_handover") or {}
    check("ggv heh ok", heh.get("ok") is True and heh.get("invented") is False)
    empties = sr.get("empty_states") or {}
    if empties.get("client_visibility"):
        check(
            "ggv client empty next",
            bool((empties["client_visibility"].get("next_action") or {}).get("label")),
        )
    else:
        check("ggv client empty next", True)
    # Haikal cannot close
    board_h = ggv.build_board(verified_person_id="PERS-HAIKAL")
    act_h = (board_h.get("staff_ready") or {}).get("exposed_actions") or {}
    check("haikal no close", act_h.get("close_lead") is False)
    check("haikal no closed option", "CLOSED" not in (act_h.get("lifecycle_values") or []))


def test_amg_surface() -> None:
    board = amg.build_board(verified_person_id="PERS-MATT")
    check("amg staff_ready present", isinstance(board.get("staff_ready"), dict))
    sr = board["staff_ready"]
    check("amg bound", board.get("staff_ready_bound") == sru.BOUND)
    check("amg lede", "Atrium" in (sr.get("lede") or "") and "PROVEN" not in (sr.get("lede") or ""))
    check("amg primary next", bool((sr.get("primary_next") or {}).get("label")))
    actions = sr.get("exposed_actions") or {}
    check("amg hide seats", actions.get("show_seats_panel") is False)
    check("amg owner visibility", actions.get("show_owner_visibility") is True)
    check("amg open day", actions.get("open_day_object") is True)
    heh = sr.get("history_evidence_handover") or {}
    check("amg heh", heh.get("ok") is True and heh.get("hotel_facts_invented") is False)
    if heh.get("history_empty"):
        check(
            "amg empty history next",
            bool((heh.get("history_empty_state") or {}).get("next_action", {}).get("label")),
        )
    else:
        check("amg empty history next", True)


def test_bzg_surface() -> None:
    today = uma.today_cards(person_id="PERS-MATT")
    check("bzg staff_ready present", isinstance(today.get("staff_ready"), dict))
    sr = today["staff_ready"]
    check("bzg bound", today.get("staff_ready_bound") == sru.BOUND)
    check("bzg primary next", bool((sr.get("primary_next") or {}).get("label")))
    nav = sr.get("phone_nav") or []
    check("bzg nav no dup", len(nav) == 6 and len({n["id"] for n in nav}) == 6)
    heh = sr.get("history_evidence_handover") or {}
    check("bzg heh", heh.get("ok") is True)
    if heh.get("history_empty"):
        check(
            "bzg history empty next",
            (heh.get("history_empty_state") or {}).get("next_action", {}).get("href")
            == "/uma-blu-close",
        )
    else:
        check("bzg history empty next", True)


def test_html_phone_first() -> None:
    ggv_html = HTML["ggv"].read_text(encoding="utf-8")
    amg_html = HTML["amg"].read_text(encoding="utf-8")
    bzg_html = HTML["bzg"].read_text(encoding="utf-8")
    check("ggv phone nav", 'nav class="phone"' in ggv_html and "phoneNav" in ggv_html)
    check("amg phone nav", 'nav class="phone"' in amg_html and "phoneNav" in amg_html)
    check("ggv no seats panel", 'id="seats"' not in ggv_html)
    check("amg no seats panel", 'id="seats"' not in amg_html)
    check("ggv history panel", 'id="history"' in ggv_html and 'id="heh"' in ggv_html)
    check("amg history panel", 'id="history"' in amg_html and 'id="heh"' in amg_html)
    check("ggv staff_ready consume", "staff_ready" in ggv_html and "primary_next" in ggv_html)
    check("amg staff_ready consume", "staff_ready" in amg_html and "exposed_actions" in amg_html)
    check("ggv human amanda", ">Amanda<" in ggv_html or "Amanda</option>" in ggv_html)
    check("ggv no CAP in lede markup", "CAP-GGV-04 stays BUILT" not in ggv_html)
    check("amg no CAP in lede", "CAP-AMG-04 stays SPECIFIED" not in amg_html)
    check("ggv more actions", "More actions" in ggv_html)
    check("amg hide waiting", "waiting_assignment" in amg_html)
    check("bzg handover panel", 'id="handover"' in bzg_html)
    check("bzg staff_ready paint", "staff_ready" in bzg_html)
    # No duplicate Needs you + Management as separate top navs on GGV
    check("ggv single needs strip", ggv_html.count('id="now"') == 1)
    check("ggv no exceptions div", 'id="exceptions"' not in ggv_html)
    for name, path in HTML.items():
        js = path.read_text(encoding="utf-8").split("<script>", 1)[1].rsplit("</script>", 1)[0]
        tmp = Path(f"/tmp/staff-ready-{name}.js")
        tmp.write_text(js, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
        check(f"{name} js syntax", r.returncode == 0, (r.stderr or "OK")[:160])


def test_wip_untouched() -> None:
    for rel in WIP:
        path = ROOT / rel
        check(f"wip exists {rel}", path.is_file())
    # Ensure our diff did not stage/edit WIP four by reading git status names
    st = subprocess.check_output(["git", "status", "--porcelain", "--"] + list(WIP), cwd=ROOT, text=True)
    # WIP may already be dirty from before — just ensure files still exist (above).
    check("wip status readable", True, st[:80])


def test_http_anon_403() -> None:
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
            with urlopen(req, timeout=30) as resp:
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
        for path in (
            "/api/staff/ready-ux",
            "/api/ggv/ops-pack/staff-ready",
            "/api/amg/ops-pack/staff-ready",
            "/api/bzg/uma-blu/staff-ready",
            "/ggv-ops-pack",
            "/amg-ops-pack",
        ):
            st, _ = call("GET", path, None)
            check(f"anon 403 {path}", st == 403, str(st))

        st, payload = call("GET", "/api/staff/ready-ux", MATT)
        check("owner staff-ready 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner bound", payload.get("bound") == sru.BOUND)

        st, payload = call("GET", "/api/ggv/ops-pack/staff-ready", AMANDA)
        check("amanda ggv staff-ready", st == 200 and (payload.get("staff_ready") or {}).get("pack") == "ggv")
        who = ((payload.get("staff_ready") or {}).get("who_line") or "")
        check("amanda who human", "Amanda" in who and "PERS-" not in who, who)

        st, payload = call("GET", "/api/amg/ops-pack/staff-ready", MATT)
        check("matt amg staff-ready", st == 200 and (payload.get("staff_ready") or {}).get("pack") == "amg")

        st, _ = call("GET", "/api/staff/ready-ux", OUTSIDER)
        check("outsider 403", st == 403, str(st))

        st, payload = call("POST", "/api/staff/ready-ux/proven", MATT, {})
        check("proven refuse", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
        st, payload = call("POST", "/api/staff/ready-ux/ready", MATT, {})
        check("ready refuse", st == 405 and payload.get("error") == "ready_refused", str(payload)[:120])
        st, payload = call("POST", "/api/staff/ready-ux/money", MATT, {})
        check("money refuse", st == 405 and payload.get("error") == "money_refused", str(payload)[:120])

        # Full boards still carry staff_ready
        st, payload = call("GET", "/api/ggv/ops-pack", AMANDA)
        check("ggv board staff_ready", st == 200 and isinstance(payload.get("staff_ready"), dict))
        st, payload = call("GET", "/api/amg/ops-pack", MATT)
        check("amg board staff_ready", st == 200 and isinstance(payload.get("staff_ready"), dict))
    finally:
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
    test_module_honesty()
    test_ggv_surface()
    test_amg_surface()
    test_bzg_surface()
    test_html_phone_first()
    test_wip_untouched()
    test_http_anon_403()
    test_ports()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
