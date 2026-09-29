#!/usr/bin/env python3
"""BZG-VENUEPL-1 — venue P&L rollup from registry + closes (honest UNKNOWN)."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import bzg_venue_pnl as vpnl  # noqa: E402
from core import entity_books as books  # noqa: E402
import serve_beta as sb  # noqa: E402

ZAYEN = "PERS-ZAYEN"
AMANDA = "PERS-AMANDA"
ZAYEN_EMAIL = "laluzayen@gmail.com"
AMANDA_EMAIL = "amanda@wolfcommand.net"
MATT_EMAIL = "mrwolf@wolfcommand.net"
HARI_EMAIL = "carolus.haryanto@gmail.com"

CATALOG = ROOT / "catalog" / "content_library.sqlite"
COMM_FLAGS = ROOT / "state" / "commissioning" / "LAST-HUMAN-COMM-LOOP-FINGERPRINT.json"
ARM = ROOT / "state" / "final-completion" / "packs" / "BZG-VENUEPL-1-ARM.json"

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS {name}" + (f" · {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL {name}" + (f" · {detail}" if detail else ""))


def _http(method: str, url: str, email: str | None = None) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    req = Request(url, method=method, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
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
    time.sleep(0.3)
    return httpd, port


def test_statuses_preserved() -> None:
    rows = outlets.list_outlets()
    by_id = {r["outlet_id"]: r for r in rows}
    check("registry still 7", len(rows) == 7)
    check("Uma OPEN", by_id.get("BZG-UMA", {}).get("status") == "OPEN")
    check(
        "Rainforest PRE-OPENING",
        by_id.get("BZG-RAIN", {}).get("status") == "PRE-OPENING",
    )
    check(
        "Pool Bar PRE-OPENING",
        by_id.get("OU-BZG-RAIN-POOL", {}).get("status") == "PRE-OPENING",
    )


def test_closes_honest_empty() -> None:
    conn = sqlite3.connect(f"file:{CATALOG.resolve()}?mode=ro", uri=True)
    try:
        n = conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
    finally:
        conn.close()
    check("venue_daily_closes still 0", n == 0, str(n))


def test_books_shell_intact() -> None:
    stamp = books.desk_stamp("ENT-BZG")
    check("BZG coa_template_shell", stamp.get("shell_kind") == "coa_template_shell")
    check("BZG accounts 200", int(stamp.get("accounts") or 0) == 200, str(stamp.get("accounts")))
    check("BZG journals 0", int(stamp.get("journals") or 0) == 0, str(stamp.get("journals")))


def test_rollup_module() -> None:
    rollup = vpnl.build_outlet_rollup()
    check("rollup ok", rollup.get("ok") is True)
    check("7 outlet cards", rollup.get("outlet_count") == 7, str(rollup.get("outlet_count")))
    check(
        "master insufficient_facts",
        rollup.get("master", {}).get("status") == "insufficient_facts",
    )
    check(
        "master revenue UNKNOWN null",
        rollup.get("master", {}).get("revenue") is None,
    )
    check("no invented revenue", rollup.get("invented_revenue") is False)
    check("staff_ready false", rollup.get("staff_ready") is False)
    check("human_commissioned false", rollup.get("human_commissioned") is False)
    check("live_pnl false", rollup.get("live_pnl") is False)
    check("ready false", rollup.get("ready") is False)
    check("proven false", rollup.get("proven") is False)
    checks = rollup.get("status_checks") or {}
    check("status uma_open", checks.get("uma_open") is True)
    check("status rain pre", checks.get("rainforest_pre_opening") is True)
    check("status pool pre", checks.get("pool_bar_pre_opening") is True)

    by_id = {c["outlet_id"]: c for c in rollup.get("outlets") or []}
    uma = by_id.get("BZG-UMA") or {}
    rain = by_id.get("BZG-RAIN") or {}
    check("Uma card OPEN", uma.get("status") == "OPEN")
    check("Rain card PRE-OPENING", rain.get("status") == "PRE-OPENING")
    for oid in ("BZG-UMA", "BZG-RAIN", "OU-BZG-RAIN-POOL"):
        card = by_id.get(oid) or {}
        slots = card.get("slots") or {}
        for kind in ("revenue", "cost", "contribution", "rollup"):
            check(
                f"{oid} {kind} UNKNOWN",
                (slots.get(kind) or {}).get("slot") == "UNKNOWN",
                str((slots.get(kind) or {}).get("slot")),
            )
            check(
                f"{oid} {kind} value null",
                (slots.get(kind) or {}).get("value") is None,
            )
        check(
            f"{oid} venue FACT",
            (slots.get("venue") or {}).get("slot") == "FACT",
        )
        check(
            f"{oid} status FACT",
            (slots.get("status") or {}).get("slot") == "FACT",
        )

    esb = (uma.get("sources_probed") or {}).get("esb_warehouse") or {}
    check("Uma ESB applicable", esb.get("applicable") is True)
    check("ESB totals not in pnl slots", esb.get("totals_in_pnl_slots") is False)
    rain_esb = (rain.get("sources_probed") or {}).get("esb_warehouse") or {}
    check("Rain ESB not applicable", rain_esb.get("applicable") is False)


def test_authority() -> None:
    check("Zayen may read", vpnl.person_may_read_venue_pnl(ZAYEN) is True)
    check("Amanda may NOT", vpnl.person_may_read_venue_pnl(AMANDA) is False)
    check("Matt may read", vpnl.person_may_read_venue_pnl("PERS-MATT") is True)


def test_writes_still_refused() -> None:
    raised = False
    try:
        vpnl.refuse_payment({})
    except vpnl.VenuePnlError as exc:
        raised = exc.code == "payment_refused"
    check("payment refused", raised)
    raised = False
    try:
        vpnl.refuse_ready({})
    except vpnl.VenuePnlError as exc:
        raised = exc.code == "ready_refused"
    check("ready refused", raised)


def test_http_surface() -> None:
    httpd, port = _start_beta()
    base = f"http://127.0.0.1:{port}"
    try:
        st, body = _http("GET", f"{base}/api/bzg/venue-pnl/rollup", ZAYEN_EMAIL)
        check("Zayen rollup 200", st == 200, str(st))
        data = json.loads(body.decode())
        check("Zayen rollup ok", data.get("ok") is True)
        check(
            "Zayen master insufficient",
            data.get("master", {}).get("status") == "insufficient_facts",
        )
        check("Zayen person", data.get("person_id") == ZAYEN)

        st, body = _http("GET", f"{base}/api/bzg/venue-pnl/rollup", MATT_EMAIL)
        check("Matt rollup 200", st == 200, str(st))

        st, body = _http("GET", f"{base}/api/bzg/venue-pnl/rollup", AMANDA_EMAIL)
        check("Amanda rollup 403", st == 403, str(st))
        deny = json.loads(body.decode())
        check("Amanda deny message", "not on this assignment" in (deny.get("message") or "").lower() or deny.get("error") == "forbidden")

        st, body = _http("GET", f"{base}/api/bzg/venue-pnl/outlets/BZG-UMA", ZAYEN_EMAIL)
        check("Uma card API 200", st == 200, str(st))
        card = json.loads(body.decode())
        check(
            "Uma card OPEN via API",
            (card.get("outlet") or {}).get("status") == "OPEN",
        )

        st, body = _http("GET", f"{base}/api/bzg/venue-pnl/outlets/BZG-RAIN", ZAYEN_EMAIL)
        check("Rain card API 200", st == 200, str(st))
        card = json.loads(body.decode())
        check(
            "Rain PRE-OPENING via API",
            (card.get("outlet") or {}).get("status") == "PRE-OPENING",
        )

        st, _ = _http("GET", f"{base}/bzg/venue-pnl", ZAYEN_EMAIL)
        check("page Zayen 200", st == 200, str(st))
        st, _ = _http("GET", f"{base}/bzg/venue-pnl", AMANDA_EMAIL)
        check("page Amanda 403", st == 403, str(st))

        st, body = _http("GET", f"{base}/api/bzg/outlets/overview", MATT_EMAIL)
        check("outlets overview still 200", st == 200, str(st))
        ov = json.loads(body.decode())
        check("outlets has venue_pnl panel", isinstance(ov.get("venue_pnl_rollup"), dict))
        check(
            "panel master insufficient",
            (ov.get("venue_pnl_rollup") or {}).get("master_status") == "insufficient_facts",
        )

        # Empty framework legacy path still works for Matt
        st, body = _http("GET", f"{base}/api/bzg/venue-pnl/framework", MATT_EMAIL)
        check("framework still empty 200", st == 200, str(st))
        fw = json.loads(body.decode())
        check("framework empty true", fw.get("empty") is True)

        st, body = _http("POST", f"{base}/api/bzg/venue-pnl/payment", ZAYEN_EMAIL)
        check("payment POST refused", st in (403, 405), str(st))

        # Hari has outlets but not board — venue-pnl should 403
        st, _ = _http("GET", f"{base}/api/bzg/venue-pnl/rollup", HARI_EMAIL)
        check("Hari rollup 403", st == 403, str(st))
    finally:
        httpd.shutdown()


def test_commissioning_flags() -> None:
    if COMM_FLAGS.is_file():
        data = json.loads(COMM_FLAGS.read_text(encoding="utf-8"))
        # Do not require specific shape — just ensure we did not flip true in this pack's honesty.
        check("comm file readable", isinstance(data, dict))
    check("module staff_ready false", vpnl.HONESTY.get("staff_ready") is False)
    check("module human_commissioned false", vpnl.HONESTY.get("human_commissioned") is False)


def test_arm_present() -> None:
    check("ARM file exists", ARM.is_file(), str(ARM))
    if ARM.is_file():
        data = json.loads(ARM.read_text(encoding="utf-8"))
        check("ARM pack id", data.get("pack") == "BZG-VENUEPL-1")


def main() -> int:
    test_statuses_preserved()
    test_closes_honest_empty()
    test_books_shell_intact()
    test_rollup_module()
    test_authority()
    test_writes_still_refused()
    test_http_surface()
    test_commissioning_flags()
    test_arm_present()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
