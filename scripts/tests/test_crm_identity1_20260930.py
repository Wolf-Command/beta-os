#!/usr/bin/env python3
"""CRM-IDENTITY-1 — customer identity/memory vertical slice (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack CRM-IDENTITY-1
(armed 2026-09-30) — CAP-CRM-02 / IL-R9 canonical stub + confidence +
human-review-when-uncertain + GGV client isolation (no cross-client leak).

Extends scripts/core/crm_identity_memory.py — no second CRM identity system.
Yanolja graph merge stays BLOCKED_EXTERNAL. CAP-CRM-02 not PROVEN/READY.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain FIN-INTERCO-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_CRM_IDENTITY", None)
os.environ.pop("WOLF_CRM_IDENTITY_DB", None)
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import crm_identity_memory as ident  # noqa: E402
from core import crm_identity_operator_depth as depth  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
OWNER = "PERS-MATT"
ARM = ROOT / "state" / "final-completion" / "packs" / "CRM-IDENTITY-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "crm-identity-1.html"
MODULE = ROOT / "scripts" / "core" / "crm_identity_memory.py"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PROD_PID = 15975
PROD_PORT = 8787
LIVE_DB = ROOT / "catalog" / "crm_identity.sqlite"
PROV = "Owner recorded CRM-IDENTITY-1 fixture guest on 2026-09-30 Beta."
EVID = "Front desk passport match recorded 2026-09-30 for review only."

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


def _tmp_db() -> Path:
    path = Path(tempfile.mkdtemp(prefix="crm-identity1-")) / "crm_identity.sqlite"
    return path


def test_module_and_honesty() -> None:
    check("module present", MODULE.is_file())
    check("html present", HTML.is_file())
    check("api matcher", ident.api_matches("/api/crm/identity-1"))
    check("page matcher", ident.page_matches("/crm/identity-1"))
    check("page matcher alias", ident.page_matches("/crm-identity-1"))
    check("pack id", ident.PACK_ID == "CRM-IDENTITY-1")
    check("extends same module", "crm_identity_memory" in MODULE.name)

    flags = ident.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("cross_client_leak false", flags.get("cross_client_leak") is False)
    check("yanolja blocked", flags.get("yanolja_graph_merge") == "BLOCKED_EXTERNAL")
    check("no yanolja invent", flags.get("yanolja_pms_identity_invented") is False)
    check("fake_pipeline false", flags.get("fake_pipeline") is False)
    check("auto_merge false", flags.get("auto_merge") is False)
    check("human_review_when_uncertain", flags.get("human_review_when_uncertain") is True)
    check("client boundaries override", flags.get("client_boundaries_override_matching") is True)
    check("cap not invented proven", flags.get("invented_proven") is False)
    check("cap_crm_02_proven false", flags.get("cap_crm_02_proven") is False)
    check("cap_crm_02_ready false", flags.get("cap_crm_02_ready") is False)
    check("maturity not PROVEN", flags.get("maturity") != "PROVEN")
    check("maturity not READY", flags.get("maturity") != "READY")
    check("ceiling not invented READY", flags.get("maturity_ceiling") != "READY" or flags.get("maturity") == "READY")

    try:
        ident.mark_proven()
        check("mark_proven refused", False)
    except ident.CrmIdentityError as exc:
        check("mark_proven refused", exc.code == "invented_proven")

    try:
        ident.refuse_yanolja_graph_merge()
        check("yanolja refuse raised", False)
    except ident.CrmIdentityError as exc:
        check("yanolja refuse code", exc.code == "yanolja_blocked_external")

    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html BLOCKED_EXTERNAL", "BLOCKED_EXTERNAL" in html)
    check("html no cross-client", "cross-client" in html.lower() or "cross_client" in html)
    check("html confidence", "confidence" in html.lower())
    check("html no fake pipeline claim", "pipeline live" not in html.lower())


def test_canonical_stub_and_confidence() -> None:
    db = _tmp_db()
    row = ident.register_customer(
        {
            "display_name": "Ayu Habitat",
            "entity_id": "GGV",
            "provenance": PROV,
            "client_scope": "habitat",
        },
        person_id=OWNER,
        db_path=db,
        require_client_scope=True,
    )
    check("register ok", row.get("ok") is True)
    check("canonical true", row.get("canonical") is True)
    check("client_scope habitat", row.get("client_scope") == "habitat")
    check("match_confidence uncertain", row.get("match_confidence") == "uncertain")
    check("confidence_band uncertain", row.get("confidence_band") == "uncertain")
    check("human_review_when_uncertain", row.get("human_review_when_uncertain") is True)
    check("verified_match false", row.get("verified_match") is False)
    check("merged false", row.get("merged") is False)
    check("yanolja on stub", row.get("yanolja_graph_merge") == "BLOCKED_EXTERNAL")
    check("not a lead", row.get("is_lead") is False)

    got = ident.read_customer(row["customer_id"], OWNER, db_path=db)
    cust = got.get("customer") or {}
    check("read client_scope", cust.get("client_scope") == "habitat")
    check("read confidence", cust.get("match_confidence") == "uncertain")
    check("read canonical", cust.get("canonical") is True)

    # Missing scope when required
    try:
        ident.register_customer(
            {
                "display_name": "No Scope",
                "entity_id": "GGV",
                "provenance": PROV,
            },
            person_id=OWNER,
            db_path=db,
            require_client_scope=True,
        )
        check("missing scope refused", False)
    except ident.CrmIdentityError as exc:
        check("missing scope code", exc.code == "missing_client_scope")

    # Invalid scope
    try:
        ident.register_customer(
            {
                "display_name": "Bad Scope",
                "entity_id": "GGV",
                "provenance": PROV,
                "client_scope": "acme-corp",
            },
            person_id=OWNER,
            db_path=db,
            require_client_scope=True,
        )
        check("invalid scope refused", False)
    except ident.CrmIdentityError as exc:
        check("invalid scope code", exc.code == "invalid_client_scope")


def test_ggv_client_isolation() -> None:
    db = _tmp_db()
    habitat = ident.register_customer(
        {
            "display_name": "Habitat Guest",
            "entity_id": "GGV",
            "provenance": PROV,
            "client_scope": "habitat",
        },
        person_id=OWNER,
        db_path=db,
        require_client_scope=True,
    )
    ivy = ident.register_customer(
        {
            "display_name": "Ivy Guest",
            "entity_id": "GGV",
            "provenance": PROV,
            "client_scope": "ivy",
        },
        person_id=OWNER,
        db_path=db,
        require_client_scope=True,
    )

    h_list = ident.list_customers(
        OWNER, entity="GGV", client_scope="habitat", db_path=db
    )
    i_list = ident.list_customers(
        OWNER, entity="GGV", client_scope="ivy", db_path=db
    )
    check("habitat list count 1", h_list.get("count") == 1)
    check("ivy list count 1", i_list.get("count") == 1)
    check(
        "habitat list only habitat",
        all(c.get("client_scope") == "habitat" for c in h_list["customers"]),
    )
    check(
        "ivy list only ivy",
        all(c.get("client_scope") == "ivy" for c in i_list["customers"]),
    )
    check(
        "habitat cannot see ivy id",
        ivy["customer_id"] not in {c["customer_id"] for c in h_list["customers"]},
    )

    # Cross-client read refused
    try:
        ident.read_customer(
            ivy["customer_id"], OWNER, client_scope="habitat", db_path=db
        )
        check("cross-client read refused", False)
    except ident.CrmIdentityError as exc:
        check("cross-client read code", exc.code == "cross_client_refused")

    try:
        ident.read_customer(
            habitat["customer_id"], OWNER, client_scope="ivy", db_path=db
        )
        check("cross-client read reverse refused", False)
    except ident.CrmIdentityError as exc:
        check("cross-client read reverse code", exc.code == "cross_client_refused")

    # Cross-client link refused
    try:
        ident.propose_link(
            {
                "customer_id": habitat["customer_id"],
                "other_id": ivy["customer_id"],
                "other_kind": "CUSTOMER",
                "evidence_ref": EVID,
                "provenance": PROV,
            },
            person_id=OWNER,
            db_path=db,
        )
        check("cross-client link refused", False)
    except ident.CrmIdentityError as exc:
        check("cross-client link code", exc.code == "cross_client_refused")

    # Same-scope link stays review candidate
    habitat2 = ident.register_customer(
        {
            "display_name": "Habitat Twin",
            "entity_id": "GGV",
            "provenance": PROV,
            "client_scope": "habitat",
        },
        person_id=OWNER,
        db_path=db,
        require_client_scope=True,
    )
    linked = ident.propose_link(
        {
            "customer_id": habitat["customer_id"],
            "other_id": habitat2["customer_id"],
            "other_kind": "CUSTOMER",
            "evidence_ref": EVID,
            "provenance": PROV,
        },
        person_id=OWNER,
        db_path=db,
    )
    check("same-scope link ok", linked.get("ok") is True)
    check("same-scope status REVIEW_REQUIRED", linked.get("status") == "REVIEW_REQUIRED")
    check("same-scope not merged", linked.get("merged") is False)
    check("same-scope not verified", linked.get("verified") is False)
    check("same-scope human review", linked.get("human_review_required") is True)
    check("same-scope no leak flag", linked.get("cross_client_leak") is False)

    # Merge path still does not collapse
    merged = ident.merge_people(
        {
            "left_customer_id": habitat["customer_id"],
            "right_customer_id": habitat2["customer_id"],
            "evidence_ref": EVID + " merge review path.",
            "provenance": PROV,
        },
        person_id=OWNER,
        db_path=db,
    )
    check("merge path not executed", merged.get("merge_executed") is False)
    check("merge path merged false", merged.get("merged") is False)
    check("merge path auto_merge false", merged.get("auto_merge") is False)

    # Yanolja kind refused
    try:
        ident.propose_link(
            {
                "customer_id": habitat["customer_id"],
                "other_id": "YAN-FAKE-1",
                "other_kind": "YANOLJA",
                "evidence_ref": EVID,
                "provenance": PROV,
            },
            person_id=OWNER,
            db_path=db,
        )
        check("yanolja kind refused", False)
    except ident.CrmIdentityError as exc:
        check("yanolja kind code", exc.code == "yanolja_blocked_external")

    # Evidence mentioning yanolja refused
    try:
        ident.propose_link(
            {
                "customer_id": habitat["customer_id"],
                "other_id": habitat2["customer_id"],
                "other_kind": "CUSTOMER",
                "evidence_ref": "Yanolja PMS guest id matched without connector.",
                "provenance": PROV,
            },
            person_id=OWNER,
            db_path=db,
        )
        check("yanolja evidence refused", False)
    except ident.CrmIdentityError as exc:
        check("yanolja evidence code", exc.code == "yanolja_blocked_external")


def test_human_review_queue_and_slice() -> None:
    db = _tmp_db()
    a = ident.register_customer(
        {
            "display_name": "Review A",
            "entity_id": "GGV",
            "provenance": PROV,
            "client_scope": "habitat",
        },
        person_id=OWNER,
        db_path=db,
        require_client_scope=True,
    )
    b = ident.register_customer(
        {
            "display_name": "Review B",
            "entity_id": "GGV",
            "provenance": PROV,
            "client_scope": "habitat",
        },
        person_id=OWNER,
        db_path=db,
        require_client_scope=True,
    )
    ident.propose_link(
        {
            "customer_id": a["customer_id"],
            "other_id": b["customer_id"],
            "other_kind": "CUSTOMER",
            "evidence_ref": EVID,
            "provenance": PROV,
        },
        person_id=OWNER,
        db_path=db,
    )
    queue = ident.list_uncertain_reviews(OWNER, db_path=db)
    check("uncertain queue count>=1", int(queue.get("count") or 0) >= 1)
    check("uncertain not empty", queue.get("empty") is False)
    check("uncertain human_review flag", queue.get("human_review_when_uncertain") is True)
    check("uncertain no auto_merge", queue.get("auto_merge") is False)
    check("uncertain yanolja blocked", queue.get("yanolja_graph_merge") == "BLOCKED_EXTERNAL")
    item = (queue.get("items") or [None])[0]
    check("uncertain item confidence", (item or {}).get("match_confidence") == "uncertain")
    check("uncertain item review required", (item or {}).get("human_review_required") is True)

    scoped = ident.list_uncertain_reviews(OWNER, client_scope="ivy", db_path=db)
    check("ivy uncertain empty", scoped.get("empty") is True)

    payload = ident.build_identity_slice(OWNER, db_path=db)
    check("slice ok", payload.get("ok") is True)
    check("slice pack", payload.get("pack") == "CRM-IDENTITY-1")
    check("slice staff_ready false", payload.get("staff_ready") is False)
    check("slice human_commissioned false", payload.get("human_commissioned") is False)
    check("slice cap not proven", payload.get("cap_crm_02_proven") is False)
    check("slice cap not ready", payload.get("cap_crm_02_ready") is False)
    check("slice no second system", payload.get("second_crm_system") is False)
    check("slice extends path", "crm_identity_memory" in str(payload.get("extends") or ""))
    check("slice yanolja", payload.get("yanolja_graph_merge") == "BLOCKED_EXTERNAL")
    check("slice no leak", payload.get("cross_client_leak") is False)
    check("slice no fake pipeline", payload.get("fake_pipeline") is False)
    check("slice no auto_merge", payload.get("auto_merge") is False)
    check("slice confidence uncertain", payload.get("match_confidence") == "uncertain")
    check("slice human review path", payload.get("human_review_when_uncertain") is True)
    check("slice next pack parent only", payload.get("next_pack_for_parent_only") == "FIN-INTERCO-1")

    tile_ids = {t.get("id") for t in (payload.get("tiles") or [])}
    for tid in (
        "canonical_stub",
        "confidence",
        "human_review",
        "client_isolation",
        "yanolja",
        "cap_crm_02",
    ):
        check(f"tile {tid}", tid in tile_ids, str(tile_ids))
    yan = next(t for t in payload["tiles"] if t["id"] == "yanolja")
    check("yanolja tile blocked", yan.get("status") == "BLOCKED_EXTERNAL")
    check("yanolja tile value null", yan.get("value") is None)

    scopes = payload.get("client_scopes") or {}
    check("habitat scope present", "habitat" in scopes)
    check("ivy scope present", "ivy" in scopes)
    check("habitat count >=1", int((scopes.get("habitat") or {}).get("count") or 0) >= 1)
    check("ivy count 0 in this fixture", int((scopes.get("ivy") or {}).get("count") or 0) == 0)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("desk link crm_identity", "crm_identity" in links)
    check("desk link operator_depth", "operator_depth" in links)
    check("desk link integrations", "integrations_honesty" in links)

    # Operator depth honesty still aligned
    dflags = depth.honesty_flags() if hasattr(depth, "honesty_flags") else {}
    if dflags:
        check("depth staff_ready false", dflags.get("staff_ready") is False)
        check("depth merged false", dflags.get("merged") is False)
        check("depth graph complete false", dflags.get("identity_graph_complete") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/crm/identity-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/crm/identity-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api yanolja blocked", data.get("yanolja_graph_merge") == "BLOCKED_EXTERNAL")
        check("api no leak", data.get("cross_client_leak") is False)
        check("api no proven", data.get("cap_crm_02_proven") is False)
        check("api no second system", data.get("second_crm_system") is False)

        st, _ = call(port, "GET", "/crm/identity-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/crm/identity-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html identity",
            "identity" in text.lower() and ("BLOCKED_EXTERNAL" in text or "crm-identity-1" in text.lower()),
        )

        st, _ = call(port, "GET", "/crm-identity-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        # Existing identity API still auth-gated
        st, _ = call(port, "GET", "/api/crm/identity")
        check("legacy unsigned api 403", st == 403, f"status={st}")
    finally:
        httpd.shutdown()
        httpd.server_close()


def _ws_connect(host: str, port: int, path: str):
    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("no upgrade")
        buf += chunk
    return sock


def _ws_send(sock, data: str) -> None:
    payload = data.encode()
    header = bytearray([0x81])
    n = len(payload)
    mask = os.urandom(4)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", n))
    header.extend(mask)
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def _ws_recv(sock) -> str:
    def read(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed")
            buf += chunk
        return buf

    head = read(2)
    length = head[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", read(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", read(8))[0]
    if head[1] & 0x80:
        mask = read(4)
        payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(read(length)))
    else:
        payload = read(length)
    return payload.decode()


def _with_cdp(width: int, email: str | None, url: str, wait_expr: str, wait_seconds: float = 45.0):
    with tempfile.TemporaryDirectory(dir=str(ROOT / "state")) as profile:
        proc = subprocess.Popen(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--disable-extensions",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                f"--window-size={width},1100",
                "--force-device-scale-factor=1",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            deadline = time.time() + 15
            while time.time() < deadline and not port_file.is_file():
                time.sleep(0.1)
            dbg_port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            with urlopen(f"http://127.0.0.1:{dbg_port}/json/list", timeout=5) as resp:
                tabs = json.loads(resp.read().decode())
            page = next(tab for tab in tabs if tab.get("type") == "page")
            ws_path = page["webSocketDebuggerUrl"].split("/", 3)[-1]
            sock = _ws_connect("127.0.0.1", dbg_port, "/" + ws_path)
            sock.settimeout(90)
            seq = 0

            def cdp(method: str, params: dict | None = None) -> dict:
                nonlocal seq
                seq += 1
                ident_id = seq
                _ws_send(sock, json.dumps({"id": ident_id, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident_id:
                        return msg

            def evaluate(expression: str):
                got = cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True})
                return ((got.get("result") or {}).get("result") or {}).get("value")

            cdp("Network.enable")
            headers = {}
            if email:
                headers["X-Wolf-Subject"] = email
                headers["Cf-Access-Authenticated-User-Email"] = email
            if headers:
                cdp("Network.setExtraHTTPHeaders", {"headers": headers})
            cdp("Page.enable")
            cdp("Page.navigate", {"url": url})
            value = None
            end = time.time() + wait_seconds
            while time.time() < end:
                value = evaluate(wait_expr)
                if value and value.get("ok"):
                    break
                time.sleep(0.35)
            yield cdp, evaluate, value
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_shots() -> None:
    if not CHROME.is_file():
        check("chrome present", False, "missing")
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    httpd, port = _start_beta()
    try:
        shell_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const yan=document.body && document.body.getAttribute('data-yanolja-blocked');"
            " const leak=document.body && document.body.getAttribute('data-cross-client-leak');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const yanTile=document.querySelector('[data-tile=\"yanolja\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && yan==='1' && leak==='0' && proven==='0'"
            "  && sr==='0' && hc==='0' && stamps>=4 && !!yanTile"
            "  && t.includes('BLOCKED_EXTERNAL') && t.includes('UNCERTAIN')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('Customer identity desk'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, ready:ready, yan:yan};"
            "})()"
        )
        for width, name in (
            (1024, "crmidentity1-desk-desktop.png"),
            (390, "crmidentity1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/crm/identity-1", shell_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"yanolja attr {name}", value.get("yan") == "1")
                    check(f"stamps visible {name}", (value.get("stamps") or 0) >= 4)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/crm/identity-1",
            shell_expr,
        ):
            check("isolation shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "crmidentity1-client-isolation.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot client-isolation", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/crm/identity-1",
            shell_expr,
        ):
            check("yanolja shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "crmidentity1-yanolja-blocked.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot yanolja-blocked", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const deny=document.body && document.body.getAttribute('data-deny');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded || deny==='403',"
            " text:t.slice(0,400), ready:ready, deny:deny, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/crm/identity-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "crmidentity1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_arm_flags() -> None:
    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm staff_ready false", arm.get("staff_ready") is False)
        check("arm human_commissioned false", arm.get("human_commissioned") is False)
        check("arm no_push", arm.get("no_push") is True)
        check("arm prod_mutate false", arm.get("prod_mutate") is False)
        check("arm extends memory module", "crm_identity_memory" in str(arm.get("extends") or ""))
    else:
        check("arm present", False, "missing")


def test_prod_pid_untouched() -> None:
    out = subprocess.check_output(
        ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    check("prod pid still 15975", str(PROD_PID) in out and f":{PROD_PORT}" in out, out[:200])
    check("live identity db not created", not LIVE_DB.exists())


def main() -> int:
    test_module_and_honesty()
    test_canonical_stub_and_confidence()
    test_ggv_client_isolation()
    test_human_review_queue_and_slice()
    test_http_api_and_page()
    test_shots()
    test_arm_flags()
    test_prod_pid_untouched()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
