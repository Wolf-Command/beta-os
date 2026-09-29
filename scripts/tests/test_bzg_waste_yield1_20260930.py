#!/usr/bin/env python3
"""BZG-WASTE-YIELD-1 — Waste/yield variance honesty desk (facts only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BZG-WASTE-YIELD-1
(armed 2026-09-30) after CONTENT-ENGINE-LIVE-1 PASS_VERIFIED.
Honesty UNKNOWN when slots empty. Amanda deny. Unsigned 403.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain FIN-AP-AR-SHELL-1 / HEADCHEF / Exit Report.
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
from core import bzg_bom_yield as bom  # noqa: E402
from core import bzg_ops_desk1 as ops  # noqa: E402
from core import bzg_variance_waste as var  # noqa: E402
from core import bzg_waste_yield1 as desk  # noqa: E402
from core import bzg_venue_pnl as vpnl  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
AMANDA = "amanda@wolfcommand.net"
HARI = "hariyanto@bluzone.group"
ARM = ROOT / "state" / "final-completion" / "packs" / "BZG-WASTE-YIELD-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "bzg-waste-yield.html"
MODULE = ROOT / "scripts" / "core" / "bzg_waste_yield1.py"
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
    check("api matcher", desk.api_matches("/api/bzg/waste-yield"))
    check("api trailing slash", desk.api_matches("/api/bzg/waste-yield/"))
    check("api not variance", not desk.api_matches("/api/bzg/variance-waste"))
    check("page /bzg/waste-yield", desk.page_matches("/bzg/waste-yield"))
    check("page alias", desk.page_matches("/bzg-waste-yield"))
    check("page desk alias", desk.page_matches("/bzg/waste-yield-desk"))
    check("pack id", desk.PACK_ID == "BZG-WASTE-YIELD-1")
    check("schema id", desk.SCHEMA_ID == "wolf.bzg-waste-yield-1.v1")
    check("cap variance", desk.CAP_VARIANCE == "CAP-BZG-04")
    check("cap bom", desk.CAP_BOM == "CAP-BZG-06")
    check("preserves ops desk", "BZG-OPS-DESK-1" in desk.PRESERVED_PACKS)
    check("preserves venuepl", "BZG-VENUEPL-1" in desk.PRESERVED_PACKS)
    check("preserves variance", "BZG-VARIANCE-WASTE-V1" in desk.PRESERVED_PACKS)
    check("preserves bom", "BZG-BOM-YIELD-V1" in desk.PRESERVED_PACKS)

    flags = desk.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_waste false", flags.get("invented_waste") is False)
    check("invented_yield false", flags.get("invented_yield") is False)
    check("invented_variance false", flags.get("invented_variance") is False)
    check("unknown when missing", flags.get("unknown_when_facts_missing") is True)
    check("zero as success false", flags.get("zero_as_success") is False)
    check("live_variance false", flags.get("live_variance_waste") is False)
    check("live_bom false", flags.get("live_bom_yield_machinery") is False)
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("cap04 proven false", flags.get("cap_bzg_04_proven") is False)
    check("cap06 proven false", flags.get("cap_bzg_06_proven") is False)
    check("ledger var specified", flags.get("ledger_maturity_variance") == "SPECIFIED")
    check("ledger bom specified", flags.get("ledger_maturity_bom") == "SPECIFIED")
    check("does not replace variance", flags.get("replaces_variance_waste_page") is False)
    check("does not replace bom", flags.get("replaces_bom_yield_page") is False)
    check("does not replace ops", flags.get("replaces_ops_desk_page") is False)
    check("does not replace venuepl", flags.get("replaces_venue_pnl_page") is False)
    check("amanda deny flag", flags.get("amanda_deny_bzg") is True)
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "FIN-AP-AR-SHELL-1",
    )
    check("cursor did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)

    for refuse_fn, code in (
        (desk.refuse_fake_numbers, "fake_numbers_refused"),
        (desk.refuse_proven, "score_refused"),
        (desk.refuse_ready, "ready_refused"),
        (desk.refuse_payment, "payment_refused"),
    ):
        try:
            refuse_fn({})
            check(f"{code} raised", False)
        except desk.BzgWasteYield1Error as exc:
            check(f"{code} code", exc.code == code, f"got={exc.code}")

    try:
        desk.refuse_external_write({"waste": 12.5})
        check("write waste refused", False)
    except desk.BzgWasteYield1Error as exc:
        check("write waste code", exc.code == "fake_numbers_refused", f"got={exc.code}")

    try:
        desk.refuse_external_write({"yield": 0.92})
        check("write yield refused", False)
    except desk.BzgWasteYield1Error as exc:
        check("write yield code", exc.code == "fake_numbers_refused", f"got={exc.code}")

    try:
        desk.refuse_external_write({"variance": 3})
        check("write variance refused", False)
    except desk.BzgWasteYield1Error as exc:
        check(
            "write variance code",
            exc.code == "fake_numbers_refused",
            f"got={exc.code}",
        )

    try:
        desk.refuse_external_write({"note": "x"})
        check("generic write refused", False)
    except desk.BzgWasteYield1Error as exc:
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
    check("desk pack", payload.get("pack") == "BZG-WASTE-YIELD-1")
    check("desk staff_ready false", payload.get("staff_ready") is False)
    check("desk human_commissioned false", payload.get("human_commissioned") is False)
    check("desk live_variance false", payload.get("live_variance_waste") is False)
    check("desk live_bom false", payload.get("live_bom_yield_machinery") is False)

    vp = payload.get("variance_panel") or {}
    check("variance panel present", isinstance(vp, dict))
    check("variance empty", vp.get("empty") is True)
    check("variance recorded 0", vp.get("recorded_count") == 0)
    check("variance live false", vp.get("live_variance_waste") is False)
    slots = vp.get("slots") or []
    check("variance slots 6", len(slots) == 6, str(len(slots)))
    check(
        "variance slots UNKNOWN",
        all(s.get("status") in {"UNKNOWN", "EMPTY"} for s in slots),
    )
    check(
        "variance values UNKNOWN",
        all(s.get("value") == "UNKNOWN" for s in slots),
    )

    bp = payload.get("bom_yield_panel") or {}
    check("bom panel present", isinstance(bp, dict))
    check("bom empty", bp.get("empty") is True)
    check("bom recorded 0", bp.get("recorded_count") == 0)
    check("bom live false", bp.get("live_bom_yield_machinery") is False)
    bslots = bp.get("slots") or []
    check("bom slots 6", len(bslots) == 6, str(len(bslots)))
    check(
        "bom slots UNKNOWN",
        all(s.get("status") in {"UNKNOWN", "EMPTY"} for s in bslots),
    )

    sc = payload.get("status_checks") or {}
    check("status all_unknown", sc.get("all_unknown") is True)
    check("status variance empty", sc.get("variance_empty") is True)
    check("status bom empty", sc.get("bom_empty") is True)
    check(
        "next parent only",
        payload.get("next_pack_for_parent_only") == "FIN-AP-AR-SHELL-1",
    )
    check(
        "cursor did not auto-start",
        payload.get("cursor_did_not_auto_start_next_pack") is True,
    )
    try:
        desk.build_desk("PERS-AMANDA")
        check("amanda desk raised", False)
    except desk.BzgWasteYield1Error as exc:
        check("amanda desk forbidden", exc.code == "forbidden", f"got={exc.code}")


def test_shell_grammar() -> None:
    wy = next((g for g in shell.BZG_GRAMMAR if g.get("key") == "waste_yield"), None)
    check("waste_yield grammar live", wy is not None and wy.get("state") == "live")
    check("waste_yield href", (wy or {}).get("href") == "/bzg/waste-yield")
    ops_g = next((g for g in shell.BZG_GRAMMAR if g.get("key") == "operations"), None)
    check("ops grammar still live", (ops_g or {}).get("href") == "/bzg/ops-desk")
    vpl = next((g for g in shell.BZG_GRAMMAR if g.get("key") == "venue_pnl"), None)
    check("venue_pnl grammar still live", (vpl or {}).get("href") == "/bzg/venue-pnl")


def test_http_surface() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/bzg/waste-yield", ZAYEN)
        check("Zayen api 200", st == 200, str(st))
        data = json.loads(body.decode())
        check("Zayen ok", data.get("ok") is True)
        check(
            "Zayen all_unknown",
            (data.get("status_checks") or {}).get("all_unknown") is True,
        )
        check(
            "Zayen variance empty",
            (data.get("variance_panel") or {}).get("empty") is True,
        )
        check("Zayen staff_ready false", data.get("staff_ready") is False)
        check("Zayen invented_waste false", (data.get("honesty") or {}).get("invented_waste") is False)

        st, body = call(port, "GET", "/api/bzg/waste-yield", MATT)
        check("Matt api 200", st == 200, str(st))
        matt = json.loads(body.decode())
        check("Matt bom panel", isinstance(matt.get("bom_yield_panel"), dict))

        st, body = call(port, "GET", "/api/bzg/waste-yield", AMANDA)
        check("Amanda api 403", st == 403, str(st))
        deny = json.loads(body.decode())
        check(
            "Amanda deny message",
            "not on this assignment" in (deny.get("message") or "").lower()
            or deny.get("error") == "forbidden",
        )

        st, body = call(port, "GET", "/api/bzg/waste-yield", None)
        check("unsigned api 403", st == 403, str(st))

        st, body = call(port, "GET", "/bzg/waste-yield", ZAYEN)
        check("page Zayen 200", st == 200, str(st))
        html = body.decode(errors="replace")
        check("page has Waste title", "Waste / Yield" in html or "Waste / Yield Desk" in html)
        check("page has UNKNOWN honesty", "UNKNOWN" in html)

        st, _ = call(port, "GET", "/bzg/waste-yield-desk", MATT)
        check("alias desk Matt 200", st == 200, str(st))

        st, body = call(port, "GET", "/bzg/waste-yield", AMANDA)
        check("page Amanda 403", st == 403, str(st))
        deny_html = body.decode(errors="replace")
        check(
            "Amanda page Access denied",
            "Access denied" in deny_html or "not on this assignment" in deny_html.lower(),
        )

        st, body = call(port, "GET", "/bzg/waste-yield", None)
        check("unsigned page 403", st == 403, str(st))
        unsigned_html = body.decode(errors="replace")
        check(
            "unsigned Access denied",
            "Access denied" in unsigned_html or "signed-in" in unsigned_html.lower(),
        )

        st, _ = call(port, "GET", "/api/bzg/waste-yield", HARI)
        check("Hari api 403", st == 403, str(st))

        # Preserve prior surfaces
        st, body = call(port, "GET", "/api/bzg/ops-desk", MATT)
        check("ops desk preserved 200", st == 200, str(st))
        ops_data = json.loads(body.decode())
        check("ops desk still ok", ops_data.get("ok") is True)
        check(
            "ops desk master still insufficient",
            (ops_data.get("venue_pnl_panel") or {}).get("master_status")
            == "insufficient_facts",
        )

        st, body = call(port, "GET", "/api/bzg/venue-pnl/rollup", ZAYEN)
        check("venuepl rollup preserved 200", st == 200, str(st))
        roll = json.loads(body.decode())
        check(
            "venuepl master still insufficient",
            (roll.get("master") or {}).get("status") == "insufficient_facts",
        )

        st, body = call(port, "GET", "/api/bzg/variance-waste", MATT)
        check("variance-waste preserved 200", st == 200, str(st))

        st, body = call(port, "GET", "/api/bzg/bom-yield", MATT)
        check("bom-yield preserved 200", st == 200, str(st))

        st, body = call(port, "POST", "/api/bzg/waste-yield", ZAYEN, {"waste": 1000})
        check("POST waste refused 403", st == 403, str(st))
        post = json.loads(body.decode())
        check(
            "POST fake_numbers code",
            post.get("error") == "fake_numbers_refused",
            str(post.get("error")),
        )

        st, body = call(port, "POST", "/api/bzg/waste-yield", MATT, {"yield": 0.88})
        check("POST yield refused 403", st == 403, str(st))
        post2 = json.loads(body.decode())
        check(
            "POST yield fake_numbers",
            post2.get("error") == "fake_numbers_refused",
            str(post2.get("error")),
        )

        st, body = call(port, "POST", "/api/bzg/waste-yield/ready", MATT, {"ready": True})
        check("POST ready refused 403", st == 403, str(st))
    finally:
        httpd.shutdown()


def test_prod_untouched() -> None:
    try:
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
        check("ARM pack id", data.get("pack") == "BZG-WASTE-YIELD-1")
        check("ARM staff_ready false", data.get("staff_ready") is False)
        check("ARM human_commissioned false", data.get("human_commissioned") is False)
        check("ARM no_push", data.get("no_push") is True)
        check("ARM prod_mutate false", data.get("prod_mutate") is False)
        check(
            "ARM next parent FIN-AP-AR-SHELL-1",
            data.get("next_pack_for_parent") == "FIN-AP-AR-SHELL-1",
        )


def test_shots_exist() -> None:
    expected = [
        "bzgwasteyield1-desk-desktop.png",
        "bzgwasteyield1-desk-phone.png",
        "bzgwasteyield1-unknown-desktop.png",
        "bzgwasteyield1-unknown-phone.png",
        "bzgwasteyield1-amanda-deny-desktop.png",
        "bzgwasteyield1-amanda-deny-phone.png",
        "bzgwasteyield1-unsigned-deny-desktop.png",
        "bzgwasteyield1-unsigned-deny-phone.png",
    ]
    check("shots dir exists", SHOTS.is_dir())
    for n in expected:
        p = SHOTS / n
        check(
            f"shot {n}",
            p.is_file() and p.stat().st_size > 800,
            f"size={p.stat().st_size if p.is_file() else 0}",
        )


def main() -> int:
    test_module_and_honesty()
    test_authority()
    test_desk_payload()
    test_shell_grammar()
    test_http_surface()
    test_prod_untouched()
    test_arm_present()
    test_shots_exist()

    # Preserve prior honesty via module re-check (smoke)
    var_fw = var.build_framework()
    check("variance smoke empty", var_fw.get("empty") is True)
    check("variance smoke recorded 0", var_fw.get("recorded_count") == 0)
    bom_fw = bom.build_framework()
    check("bom smoke empty", bom_fw.get("empty") is True)
    check("bom smoke recorded 0", bom_fw.get("recorded_count") == 0)
    ops_desk = ops.build_desk("PERS-MATT")
    check("ops desk smoke ok", ops_desk.get("ok") is True)
    check(
        "ops desk smoke insufficient",
        (ops_desk.get("venue_pnl_panel") or {}).get("master_status")
        == "insufficient_facts",
    )
    roll = vpnl.build_outlet_rollup()
    check(
        "venuepl smoke insufficient_facts",
        (roll.get("master") or {}).get("status") == "insufficient_facts",
    )

    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
