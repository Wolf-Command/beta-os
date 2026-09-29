#!/usr/bin/env python3
"""BZG-OPS-DESK-1 — Single Beta BZG ops desk (outlets + venue-pnl + foundations).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BZG-OPS-DESK-1
(armed 2026-09-30) after INTEL-LEARN-1 PASS_VERIFIED.
Honesty UNKNOWN when facts missing. Amanda deny. Unsigned 403.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain FIN-RECON-SHELL-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ["WOLF_TEST_MODE"] = "1"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import bzg_ops_desk1 as desk  # noqa: E402
from core import bzg_venue_pnl as vpnl  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
AMANDA = "amanda@wolfcommand.net"
HARI = "hariyanto@bluzone.group"
ARM = ROOT / "state" / "final-completion" / "packs" / "BZG-OPS-DESK-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "bzg-ops-desk.html"
MODULE = ROOT / "scripts" / "core" / "bzg_ops_desk1.py"
PROD_PID = 15975
PROD_PORT = 8787

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


def call(port: int, method: str, path: str, email: str | None = None, body: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, data=data, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_beta() -> tuple[ThreadingHTTPServer, int]:
    port = _free_port()

    class H(sb.BetaHandler):
        pass

    H.directory = str(ROOT / "dashboards")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), H)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.25)
    return httpd, port


def test_module_and_honesty() -> None:
    check("module present", MODULE.is_file())
    check("html present", HTML.is_file())
    check("api matcher", desk.api_matches("/api/bzg/ops-desk"))
    check("api trailing slash", desk.api_matches("/api/bzg/ops-desk/"))
    check("api not outlets", not desk.api_matches("/api/bzg/outlets/overview"))
    check("page /bzg/ops-desk", desk.page_matches("/bzg/ops-desk"))
    check("page /bzg/ops", desk.page_matches("/bzg/ops"))
    check("page alias", desk.page_matches("/bzg-ops-desk"))
    check("pack id", desk.PACK_ID == "BZG-OPS-DESK-1")
    check("schema id", desk.SCHEMA_ID == "wolf.bzg-ops-desk-1.v1")
    check("cap", desk.CAP_ID == "CAP-BZG-02")
    check("preserves outlet", "BZG-OUTLET-1" in desk.PRESERVED_PACKS)
    check("preserves xoutlet", "BZG-XOUTLET-1" in desk.PRESERVED_PACKS)
    check("preserves venuepl", "BZG-VENUEPL-1" in desk.PRESERVED_PACKS)
    check("preserves fc-shell", "FC-SHELL-2" in desk.PRESERVED_PACKS)

    flags = desk.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_sales false", flags.get("invented_sales") is False)
    check("invented_pnl false", flags.get("invented_pnl") is False)
    check("unknown when missing", flags.get("unknown_when_facts_missing") is True)
    check("zero as success false", flags.get("zero_as_success") is False)
    check("live_pnl false", flags.get("live_pnl") is False)
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("cap proven false", flags.get("cap_bzg_02_proven") is False)
    check("ledger specified", flags.get("ledger_maturity") == "SPECIFIED")
    check("does not replace outlets", flags.get("replaces_outlets_page") is False)
    check("does not replace venuepl", flags.get("replaces_venue_pnl_page") is False)
    check("amanda deny flag", flags.get("amanda_deny_bzg") is True)

    for refuse_fn, code in (
        (desk.refuse_fake_sales, "fake_sales_refused"),
        (desk.refuse_proven, "score_refused"),
        (desk.refuse_ready, "ready_refused"),
        (desk.refuse_payment, "payment_refused"),
    ):
        try:
            refuse_fn({})
            check(f"{code} raised", False)
        except desk.BzgOpsDesk1Error as exc:
            check(f"{code} code", exc.code == code, f"got={exc.code}")

    try:
        desk.refuse_external_write({"sales": 999})
        check("write sales refused", False)
    except desk.BzgOpsDesk1Error as exc:
        check("write sales code", exc.code == "fake_sales_refused", f"got={exc.code}")

    try:
        desk.refuse_external_write({"note": "x"})
        check("generic write refused", False)
    except desk.BzgOpsDesk1Error as exc:
        check("generic write code", exc.code == "write_refused", f"got={exc.code}")


def test_authority() -> None:
    check("Matt may view", desk.person_may_view("PERS-MATT") is True)
    check("Zayen may view", desk.person_may_view("PERS-ZAYEN") is True)
    check("Amanda may NOT", desk.person_may_view("PERS-AMANDA") is False)
    check("empty may NOT", desk.person_may_view("") is False)
    check("None may NOT", desk.person_may_view(None) is False)


def test_desk_payload() -> None:
    payload = desk.build_desk("PERS-MATT")
    check("desk ok", payload.get("ok") is True)
    check("desk pack", payload.get("pack") == "BZG-OPS-DESK-1")
    check("desk staff_ready false", payload.get("staff_ready") is False)
    check("desk human_commissioned false", payload.get("human_commissioned") is False)
    check("desk live_pnl false", payload.get("live_pnl") is False)
    outs = payload.get("outlets_panel") or {}
    check("outlets panel present", isinstance(outs, dict) and outs.get("outlet_count") == 7)
    check("uma open", outs.get("uma_open") is True)
    check("rain pre-opening", outs.get("rainforest_pre_opening") is True)
    check("pool pre-opening", outs.get("pool_bar_pre_opening") is True)
    vpl = payload.get("venue_pnl_panel") or {}
    check("venue panel present", isinstance(vpl, dict))
    check(
        "master insufficient",
        vpl.get("master_status") == "insufficient_facts",
        str(vpl.get("master_status")),
    )
    check("closes unknown or zero", vpl.get("closes_unknown") is True or vpl.get("venue_daily_closes") == 0)
    check("venue live_pnl false", vpl.get("live_pnl") is False)
    found = payload.get("foundations_panel") or {}
    check("foundations present", isinstance(found, dict) and found.get("hierarchy_usable") is True)
    check("no multi outlet pnl", found.get("no_multi_outlet_pnl") is True)
    check("centres not populated", found.get("centres_populated") is False)
    sc = payload.get("status_checks") or {}
    check("status uma", sc.get("uma_open") is True)
    check("status rain", sc.get("rainforest_pre_opening") is True)
    check("status pool", sc.get("pool_bar_pre_opening") is True)
    check("status master insufficient", sc.get("master_insufficient_facts") is True)
    check(
        "next parent only",
        payload.get("next_pack_for_parent_only") == "FIN-RECON-SHELL-1",
    )
    check(
        "cursor did not auto-start",
        payload.get("cursor_did_not_auto_start_next_pack") is True,
    )
    try:
        desk.build_desk("PERS-AMANDA")
        check("amanda desk raised", False)
    except desk.BzgOpsDesk1Error as exc:
        check("amanda desk forbidden", exc.code == "forbidden", f"got={exc.code}")


def test_shell_grammar() -> None:
    ops = next((g for g in shell.BZG_GRAMMAR if g.get("key") == "operations"), None)
    check("operations grammar live", ops is not None and ops.get("state") == "live")
    check("operations href ops-desk", (ops or {}).get("href") == "/bzg/ops-desk")
    outlets = next((g for g in shell.BZG_GRAMMAR if g.get("key") == "outlets"), None)
    check("outlets grammar still live", (outlets or {}).get("href") == "/bzg/outlets")
    vpl = next((g for g in shell.BZG_GRAMMAR if g.get("key") == "venue_pnl"), None)
    check("venue_pnl grammar still live", (vpl or {}).get("href") == "/bzg/venue-pnl")


def test_http_surface() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/bzg/ops-desk", ZAYEN)
        check("Zayen api 200", st == 200, str(st))
        data = json.loads(body.decode())
        check("Zayen ok", data.get("ok") is True)
        check(
            "Zayen master insufficient",
            (data.get("venue_pnl_panel") or {}).get("master_status") == "insufficient_facts",
        )
        check("Zayen outlets 7", (data.get("outlets_panel") or {}).get("outlet_count") == 7)
        check("Zayen staff_ready false", data.get("staff_ready") is False)

        st, body = call(port, "GET", "/api/bzg/ops-desk", MATT)
        check("Matt api 200", st == 200, str(st))
        matt = json.loads(body.decode())
        check("Matt foundations", isinstance(matt.get("foundations_panel"), dict))

        st, body = call(port, "GET", "/api/bzg/ops-desk", AMANDA)
        check("Amanda api 403", st == 403, str(st))
        deny = json.loads(body.decode())
        check(
            "Amanda deny message",
            "not on this assignment" in (deny.get("message") or "").lower()
            or deny.get("error") == "forbidden",
        )

        st, body = call(port, "GET", "/api/bzg/ops-desk", None)
        check("unsigned api 403", st == 403, str(st))

        st, body = call(port, "GET", "/bzg/ops-desk", ZAYEN)
        check("page Zayen 200", st == 200, str(st))
        html = body.decode(errors="replace")
        check("page has Ops Desk title", "BZG Ops Desk" in html)
        check("page has UNKNOWN honesty", "UNKNOWN" in html or "unknown" in html.lower())

        st, _ = call(port, "GET", "/bzg/ops", MATT)
        check("alias /bzg/ops Matt 200", st == 200, str(st))

        st, body = call(port, "GET", "/bzg/ops-desk", AMANDA)
        check("page Amanda 403", st == 403, str(st))
        deny_html = body.decode(errors="replace")
        check(
            "Amanda page Access denied",
            "Access denied" in deny_html or "not on this assignment" in deny_html.lower(),
        )

        st, body = call(port, "GET", "/bzg/ops-desk", None)
        check("unsigned page 403", st == 403, str(st))
        unsigned_html = body.decode(errors="replace")
        check(
            "unsigned Access denied",
            "Access denied" in unsigned_html or "signed-in" in unsigned_html.lower(),
        )

        # Hari: outlets yes, board no → ops desk deny (venue-pnl-class gate)
        st, _ = call(port, "GET", "/api/bzg/ops-desk", HARI)
        check("Hari api 403", st == 403, str(st))

        # Preserve prior surfaces
        st, body = call(port, "GET", "/api/bzg/outlets/overview", MATT)
        check("outlets overview preserved 200", st == 200, str(st))
        ov = json.loads(body.decode())
        check("outlets still has foundations", isinstance(ov.get("cross_outlet_foundations"), dict))
        check("outlets still has venue_pnl teaser", isinstance(ov.get("venue_pnl_rollup"), dict))

        st, body = call(port, "GET", "/api/bzg/venue-pnl/rollup", ZAYEN)
        check("venuepl rollup preserved 200", st == 200, str(st))
        roll = json.loads(body.decode())
        check(
            "venuepl master still insufficient",
            (roll.get("master") or {}).get("status") == "insufficient_facts",
        )

        st, body = call(port, "POST", "/api/bzg/ops-desk", ZAYEN, {"sales": 1000})
        check("POST sales refused 403", st == 403, str(st))
        post = json.loads(body.decode())
        check(
            "POST fake_sales code",
            post.get("error") == "fake_sales_refused",
            str(post.get("error")),
        )

        st, body = call(port, "POST", "/api/bzg/ops-desk/ready", MATT, {"ready": True})
        check("POST ready refused 403", st == 403, str(st))
    finally:
        httpd.shutdown()


def test_prod_untouched() -> None:
    try:
        import signal

        os.kill(PROD_PID, 0)
        alive = True
    except OSError:
        alive = False
    check("prod pid 15975 still alive", alive)
    try:
        with socket.create_connection(("127.0.0.1", PROD_PORT), timeout=2):
            listening = True
    except OSError:
        listening = False
    check("prod :8787 still listening", listening)


def test_arm_present() -> None:
    check("ARM file exists", ARM.is_file(), str(ARM))
    if ARM.is_file():
        data = json.loads(ARM.read_text(encoding="utf-8"))
        check("ARM pack id", data.get("pack") == "BZG-OPS-DESK-1")
        check("ARM staff_ready false", data.get("staff_ready") is False)
        check("ARM human_commissioned false", data.get("human_commissioned") is False)
        check("ARM no_push", data.get("no_push") is True)
        check("ARM prod_mutate false", data.get("prod_mutate") is False)


def test_shots_exist() -> None:
    expected = [
        "bzgopsdesk1-desk-desktop.png",
        "bzgopsdesk1-desk-phone.png",
        "bzgopsdesk1-unknown-desktop.png",
        "bzgopsdesk1-unknown-phone.png",
        "bzgopsdesk1-amanda-deny-desktop.png",
        "bzgopsdesk1-amanda-deny-phone.png",
        "bzgopsdesk1-unsigned-deny-desktop.png",
        "bzgopsdesk1-unsigned-deny-phone.png",
    ]
    check("shots dir exists", SHOTS.is_dir())
    for n in expected:
        p = SHOTS / n
        check(f"shot {n}", p.is_file() and p.stat().st_size > 800, f"size={p.stat().st_size if p.is_file() else 0}")


def main() -> int:
    test_module_and_honesty()
    test_authority()
    test_desk_payload()
    test_shell_grammar()
    test_http_surface()
    test_prod_untouched()
    test_arm_present()
    test_shots_exist()

    # Preserve venuepl honesty via module re-check (smoke)
    roll = vpnl.build_outlet_rollup()
    check("venuepl smoke outlet_count 7", roll.get("outlet_count") == 7)
    check(
        "venuepl smoke insufficient_facts",
        (roll.get("master") or {}).get("status") == "insufficient_facts",
    )
    check("venuepl smoke staff_ready false", roll.get("staff_ready") is False)

    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
