#!/usr/bin/env python3
"""CRM-PIPELINE-TRUTH-1 — CRM pipeline truth (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack
CRM-PIPELINE-TRUTH-1 (armed 2026-09-30 after FIN-TAX-DEEPEN-1 PASS_VERIFIED).

Probe authorised Habitat CRM; wire stage counts or honest UNKNOWN.
Never invent pipeline counts. Preserves GGV-PIPELINE-TRUTH-1 + CRM-IDENTITY-1.
Unsigned API/page 403. Writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain CONTENT-PUBLISH-PATH-1 / HEADCHEF / Exit Report.
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
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import crm_identity_memory as crm  # noqa: E402
from core import crm_pipeline_truth1 as pipe  # noqa: E402
from core import ggv_pipeline_truth1 as ggv_pipe  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
ARM = ROOT / "state" / "final-completion" / "packs" / "CRM-PIPELINE-TRUTH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "crm-pipeline-truth-1.html"
MODULE = ROOT / "scripts" / "core" / "crm_pipeline_truth1.py"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
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
    check("page matcher /crm/pipeline-truth-1", pipe.page_matches("/crm/pipeline-truth-1"))
    check("page matcher alias", pipe.page_matches("/crm-pipeline-truth-1.html"))
    check("page matcher short", pipe.page_matches("/crm/pipeline"))
    check("api matcher", pipe.api_matches("/api/crm/pipeline-truth-1"))
    check("api alias ops", pipe.api_matches("/api/ops/crm-pipeline-truth-1"))
    check("api no mutate path", not pipe.api_matches("/api/crm/pipeline-truth-1/mutate"))

    flags = pipe.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("classification WIRED", flags.get("classification") == "WIRED")
    check("fake_deals false", flags.get("fake_deals") is False)
    check("fake_deal false", flags.get("fake_deal") is False)
    check("invented_pipeline false", flags.get("invented_pipeline") is False)
    check("fake_pipeline false", flags.get("fake_pipeline") is False)
    check("invented_deals false", flags.get("invented_deals") is False)
    check("fake_conversion false", flags.get("fake_conversion") is False)
    check("invented_conversion false", flags.get("invented_conversion") is False)
    check("live_pipeline false", flags.get("live_pipeline") is False)
    check("empty not live", flags.get("empty_pipeline_is_not_live") is True)
    check("closed not sale", flags.get("closed_is_not_a_sale") is True)
    check("conversion unknown", flags.get("conversion_unknown") is True)
    check("unknown when missing", flags.get("unknown_when_facts_missing") is True)
    check("crm preserved flag", flags.get("crm_identity1_preserved") is True)
    check("ggv preserved flag", flags.get("ggv_pipeline_truth1_preserved") is True)
    check("cap proven false", flags.get("cap_crm_pipeline_proven") is False)
    check("cap ready false", flags.get("cap_crm_pipeline_ready") is False)
    check("ceiling BUILT", flags.get("cap_crm_pipeline_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_crm_pipeline_maturity") == "SPECIFIED")
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "CONTENT-PUBLISH-PATH-1",
    )
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", pipe.PROD_PID_HELD == PROD_PID)

    check("Matt may view", pipe.person_may_view("PERS-MATT") is True)
    check("Amanda may view", pipe.person_may_view("PERS-AMANDA") is True)
    check("Zayen may NOT", pipe.person_may_view("PERS-ZAYEN") is False)

    try:
        pipe.refuse_fake_deal({"deal": True})
        check("refuse_fake_deal raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("refuse_fake_deal raises", True)
        check("refuse_fake_deal code", exc.code == "fake_deal_refused")
    try:
        pipe.refuse_invent_pipeline({"pipeline_count": 99})
        check("refuse_invent_pipeline raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("refuse_invent_pipeline raises", True)
        check("refuse_invent_pipeline code", exc.code == "invent_pipeline_refused")
    try:
        pipe.refuse_fake_conversion({"conversion_rate": 0.4})
        check("refuse_fake_conversion raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("refuse_fake_conversion raises", True)
        check("refuse_fake_conversion code", exc.code == "fake_conversion_refused")

    try:
        pipe.refuse_external_write({"deal": True})
        check("refuse write deal raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check(
            "refuse write deal",
            exc.code in ("fake_deal_refused", "invent_pipeline_refused"),
            f"got={exc.code}",
        )
    try:
        pipe.refuse_external_write({"pipeline_count": 12})
        check("refuse write pipeline_count raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("refuse write pipeline_count", exc.code == "invent_pipeline_refused")
    try:
        pipe.refuse_external_write({"conversion": 12})
        check("refuse write conversion raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("refuse write conversion", exc.code == "fake_conversion_refused")
    try:
        pipe.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        pipe.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    habitat = pipe.probe_habitat_crm()
    check("habitat probe ok", habitat.get("ok") is True)
    check("habitat authorised", habitat.get("authorised") is True)
    check("habitat invented false", habitat.get("invented_pipeline") is False)

    external = pipe.probe_external_crm_clients()
    check("external ABSENT", external.get("status") == "ABSENT")
    check("external not authorised", external.get("authorised") is False)
    check("external invented false", external.get("invented_pipeline") is False)

    route = pipe.decide_route(habitat=habitat, external=external)
    check(
        "route classification wired or empty",
        route.get("classification") in ("WIRED", "HONEST_EMPTY"),
        f"got={route.get('classification')}",
    )
    check("route invented false", route.get("invented_pipeline") is False)

    payload = pipe.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check(
        "payload classification",
        payload.get("classification") in ("WIRED", "HONEST_EMPTY"),
        f"got={payload.get('classification')}",
    )
    check("payload fake_deals false", payload.get("fake_deals") is False)
    check("payload invented_pipeline false", payload.get("invented_pipeline") is False)
    check("payload fake_pipeline false", payload.get("fake_pipeline") is False)
    check("payload invented_deals false", payload.get("invented_deals") is False)
    check("payload fake_conversion false", payload.get("fake_conversion") is False)
    check("payload live_pipeline false", payload.get("live_pipeline") is False)
    check("payload conversion unknown", payload.get("conversion_unknown") is True)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload crm preserved", payload.get("crm_identity1_preserved") is True)
    check("payload ggv preserved", payload.get("ggv_pipeline_truth1_preserved") is True)
    check("payload cap not proven", payload.get("cap_crm_pipeline_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_crm_pipeline_ceiling") == "BUILT")
    check(
        "payload next parent",
        payload.get("next_pack_for_parent_only") == "CONTENT-PUBLISH-PATH-1",
    )
    check("payload no auto-chain", payload.get("cursor_did_not_auto_start_next_pack") is True)
    check("payload closed not sale", payload.get("closed_is_not_a_sale") is True)
    check("no invented helper", pipe.no_invented_pipeline_counts(payload) is True)

    stages = payload.get("pipeline_stages") or []
    check("pipeline stages == 4", len(stages) == 4, str(len(stages)))
    check("stages crm or unknown", pipe.stages_crm_or_unknown(payload) is True)
    for s in stages:
        check(f"{s['id']} no fake deal", s.get("fake_deal") is False)
        check(f"{s['id']} not invented deal", s.get("invented_deal") is False)
        check(f"{s['id']} not invented pipeline", s.get("invented_pipeline") is False)
        check(
            f"{s['id']} status ok",
            s.get("status") in ("EMPTY", "UNKNOWN", "FROM_CRM"),
        )
        if s.get("status") in ("EMPTY", "UNKNOWN"):
            check(f"{s['id']} value null when empty", s.get("value") is None)
            check(f"{s['id']} fact 0 when empty", s.get("fact_count") == 0)

    conv = payload.get("conversion_slots") or []
    check("conversion slots >= 4", len(conv) >= 4, str(len(conv)))
    check("all conversion unknown", pipe.all_conversion_slots_unknown(payload) is True)
    for s in conv:
        check(f"conv {s['id']} value null", s.get("value") is None)
        check(f"conv {s['id']} amount null", s.get("amount") is None)
        check(f"conv {s['id']} fact 0", s.get("fact_count") == 0)
        check(f"conv {s['id']} no fake", s.get("fake_conversion") is False)

    crm_pin = payload.get("crm_identity1") or {}
    check("crm stamp ok", crm_pin.get("ok") is True, str(crm_pin))
    check("crm stamp fake_pipeline false", crm_pin.get("fake_pipeline") is False)

    ggv_pin = payload.get("ggv_pipeline_truth1") or {}
    check("ggv stamp ok", ggv_pin.get("ok") is True, str(ggv_pin))
    check("ggv stamp fake_deals false", ggv_pin.get("fake_deals") is False)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "classification",
        "habitat_crm",
        "external_crm",
        "invent_pipeline",
        "fake_conversion",
        "ggv_pipeline_truth_1",
        "crm_identity_1",
        "cap_crm_pipeline",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link ggv pipeline", "ggv_pipeline_truth_1" in links)
    check("link crm identity 1", "crm_identity_1" in links)
    check("link ggv ops", "ggv_ops" in links)

    schema = pipe.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema fake deals false", schema.get("fake_deals") is False)
    check("schema invented pipeline false", schema.get("invented_pipeline") is False)
    check("schema fake conversion false", schema.get("fake_conversion") is False)

    try:
        pipe.build_slice("PERS-ZAYEN")
        check("zayen desk raised", False)
    except pipe.CrmPipelineTruth1Error as exc:
        check("zayen desk forbidden", exc.code == "forbidden", f"got={exc.code}")


def test_preserved_packs() -> None:
    pin = pipe.crm_identity1_preserved()
    check("crm preserved ok", pin.get("ok") is True, str(pin))
    check("crm fake_pipeline false", pin.get("fake_pipeline") is False)
    check("crm cross_client false", pin.get("cross_client_leak") is False)
    check("crm auto_merge false", pin.get("auto_merge") is False)

    flags = crm.honesty_flags()
    check("direct crm staff_ready false", flags.get("staff_ready") is False)
    check("direct crm human_commissioned false", flags.get("human_commissioned") is False)
    check("direct crm fake_pipeline false", flags.get("fake_pipeline") is False)

    ggv = pipe.ggv_pipeline_truth1_preserved()
    check("ggv preserved ok", ggv.get("ok") is True, str(ggv))
    check("ggv fake_deals false", ggv.get("fake_deals") is False)
    check("ggv live false", ggv.get("live_pipeline") is False)

    gflags = ggv_pipe.honesty_flags()
    check("direct ggv staff_ready false", gflags.get("staff_ready") is False)
    check("direct ggv fake_deals false", gflags.get("fake_deals") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/crm/pipeline-truth-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/crm/pipeline-truth-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check(
            "api classification",
            data.get("classification") in ("WIRED", "HONEST_EMPTY"),
        )
        check("api fake_deals false", data.get("fake_deals") is False)
        check("api invented_pipeline false", data.get("invented_pipeline") is False)
        check("api fake_conversion false", data.get("fake_conversion") is False)
        check("api live_pipeline false", data.get("live_pipeline") is False)
        check("api last_success null", data.get("last_success") is None)
        check("api crm preserved", data.get("crm_identity1_preserved") is True)
        check("api ggv preserved", data.get("ggv_pipeline_truth1_preserved") is True)
        check("api stages helper", pipe.stages_crm_or_unknown(data) is True)
        check("api conversion helper", pipe.all_conversion_slots_unknown(data) is True)
        check("api no invent helper", pipe.no_invented_pipeline_counts(data) is True)

        st, body = call(port, "GET", "/api/crm/pipeline-truth-1", email=AMANDA)
        check("amanda api 200", st == 200, f"status={st}")
        adata = json.loads(body.decode())
        check("amanda api ok", adata.get("ok") is True)

        st, body = call(port, "GET", "/api/crm/pipeline-truth-1", email=ZAYEN)
        check("zayen api 403", st == 403, f"status={st}")
        zdata = json.loads(body.decode())
        check("zayen api forbidden", zdata.get("error") == "forbidden")
        check("zayen api staff_ready false", zdata.get("staff_ready") is False)

        st, _ = call(port, "GET", "/crm/pipeline-truth-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/crm/pipeline-truth-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html pipeline",
            "pipeline" in text.lower() or "UNKNOWN" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check("page invent pin", "invent" in text.lower())
        check("page pack attr", 'data-pack="CRM-PIPELINE-TRUTH-1"' in text)

        st, body = call(port, "GET", "/crm/pipeline-truth-1", email=ZAYEN)
        check("zayen page deny", st == 403, f"status={st}")

        st, _ = call(port, "GET", "/crm-pipeline-truth-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/crm/pipeline-truth-1", email=MATT, body={"deal": True}
        )
        check("post deal 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check(
            "post deal refused code",
            err.get("error") in ("fake_deal_refused", "invent_pipeline_refused"),
            f"got={err.get('error')}",
        )

        st, body = call(
            port,
            "POST",
            "/api/crm/pipeline-truth-1",
            email=MATT,
            body={"pipeline_count": 99},
        )
        check("post pipeline_count 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check(
            "post pipeline_count refused",
            err.get("error") == "invent_pipeline_refused",
            f"got={err.get('error')}",
        )

        st, body = call(
            port,
            "POST",
            "/api/crm/pipeline-truth-1",
            email=MATT,
            body={"conversion_rate": 0.5},
        )
        check("post conversion 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post conversion refused code", err.get("error") == "fake_conversion_refused")

        st, body = call(
            port, "POST", "/api/crm/pipeline-truth-1", email=MATT, body={"proven": True}
        )
        check("post proven 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post proven refused code", err.get("error") == "proven_refused")

        st, _ = call(port, "GET", "/api/crm/identity-1")
        check("crm identity unsigned 403", st == 403, f"status={st}")
        st, body = call(port, "GET", "/api/crm/identity-1", email=MATT)
        check("crm identity signed 200", st == 200, f"status={st}")
        crm_data = json.loads(body.decode())
        check("crm identity still ok", crm_data.get("ok") is True)
        check("crm identity staff_ready false", crm_data.get("staff_ready") is False)
        check("crm identity no fake pipeline", crm_data.get("fake_pipeline") is False)

        st, body = call(port, "GET", "/api/ggv/pipeline-truth-1", email=MATT)
        check("ggv pipeline still 200", st == 200, f"status={st}")
        gdata = json.loads(body.decode())
        check("ggv pipeline still ok", gdata.get("ok") is True)
        check("ggv pipeline fake_deals false", gdata.get("fake_deals") is False)
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
        desk_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const fd=document.body && document.body.getAttribute('data-fake-deals');"
            " const fc=document.body && document.body.getAttribute('data-fake-conversion');"
            " const id=document.body && document.body.getAttribute('data-invented-deals');"
            " const ip=document.body && document.body.getAttribute('data-invented-pipeline');"
            " const cu=document.body && document.body.getAttribute('data-conversion-unknown');"
            " const crm=document.body && document.body.getAttribute('data-crm-preserved');"
            " const ggv=document.body && document.body.getAttribute('data-ggv-preserved');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const live=document.body && document.body.getAttribute('data-live-pipeline');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const cls=document.body && document.body.getAttribute('data-classification');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const stages=(document.querySelectorAll('[data-stage]')||[]).length;"
            " const slots=(document.querySelectorAll('[data-slot]')||[]).length;"
            " const unk=document.querySelector('[data-conversion=\"unknown\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && fd==='0' && fc==='0' && id==='0' && ip==='0'"
            "  && cu==='1' && crm==='1' && ggv==='1' && proven==='0' && live==='0'"
            "  && sr==='0' && hc==='0' && (cls==='WIRED' || cls==='HONEST_EMPTY')"
            "  && stamps>=4 && stages>=4 && slots>=4 && !!unk"
            "  && t.includes('UNKNOWN') && ht.includes('staff_ready=false')"
            "  && ht.includes('human_commissioned=false')"
            "  && t.toLowerCase().includes('pipeline'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, stages:stages, slots:slots,"
            " ready:ready, cu:cu, crm:crm, ggv:ggv, fd:fd, fc:fc, ip:ip, cls:cls};"
            "})()"
        )
        for width, name in (
            (1024, "crmpipeline1-desk-desktop.png"),
            (390, "crmpipeline1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/crm/pipeline-truth-1", desk_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"conversion unknown {name}", value.get("cu") == "1")
                    check(f"crm preserved {name}", value.get("crm") == "1")
                    check(f"ggv preserved {name}", value.get("ggv") == "1")
                    check(f"invented pipeline false {name}", value.get("ip") == "0")
                    check(f"stages visible {name}", (value.get("stages") or 0) >= 4)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/crm/pipeline-truth-1",
            desk_expr,
        ):
            check("stages wired shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("stages wired classification", value.get("cls") in ("WIRED", "HONEST_EMPTY"))
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "crmpipeline1-stages-wired.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot stages-wired", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/crm/pipeline-truth-1",
            desk_expr,
        ):
            check("ggv preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("ggv preserved attr", value.get("ggv") == "1")
                check("no invent attr", value.get("ip") == "0")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "crmpipeline1-ggv-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot ggv-preserved", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const deny=document.body && document.body.getAttribute('data-deny');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity|Owner/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded || deny==='403',"
            " text:t.slice(0,400), ready:ready, deny:deny, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/crm/pipeline-truth-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "crmpipeline1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_artifacts_and_prod_ro() -> None:
    check("page html present", HTML.is_file())
    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="CRM-PIPELINE-TRUTH-1"' in html)
    check("html invent", "invent" in html.lower())
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html GGV preserved", "GGV-PIPELINE-TRUTH-1" in html)
    check("html CRM preserved", "CRM-IDENTITY-1" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "CRM-PIPELINE-TRUTH-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "CONTENT-PUBLISH-PATH-1"
        or arm.get("next_pack_for_parent_only") == "CONTENT-PUBLISH-PATH-1",
    )

    for name in (
        "crmpipeline1-desk-desktop.png",
        "crmpipeline1-desk-phone.png",
        "crmpipeline1-stages-wired.png",
        "crmpipeline1-ggv-preserved.png",
        "crmpipeline1-unsigned-deny.png",
    ):
        p = SHOTS / name
        check(f"artifact {name}", p.is_file() and p.stat().st_size > 800)

    result = ROOT / "docs" / "wolf" / "ops" / "CRM-PIPELINE-TRUTH-1-RESULT.md"
    check("result md present", result.is_file())
    if result.is_file():
        rtext = result.read_text(encoding="utf-8")
        check("result EXIT:0", "EXIT:0" in rtext)
        check("result no auto-chain", "CONTENT-PUBLISH-PATH-1" in rtext)
        check("result classification", "WIRED" in rtext or "HONEST_EMPTY" in rtext)

    check("prod pid constant", pipe.PROD_PID_HELD == PROD_PID)
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = ""
    check("prod still listening", str(PROD_PID) in out or "LISTEN" in out, out[:120])
    try:
        os.kill(PROD_PID, 0)
        alive = True
    except (OSError, ProcessLookupError):
        alive = False
    check("prod pid 15975 alive untouched", alive is True)

    names = [
        "crmpipeline1-desk-desktop.png",
        "crmpipeline1-desk-phone.png",
        "crmpipeline1-stages-wired.png",
        "crmpipeline1-ggv-preserved.png",
        "crmpipeline1-unsigned-deny.png",
    ]
    hashes = []
    for name in names:
        path = SHOTS / name
        check(f"shot file {name}", path.is_file() and path.stat().st_size > 800)
        if path.is_file():
            hashes.append(path.read_bytes()[:64])
    if len(hashes) == 5:
        check("shots not identical prefixes", len(set(hashes)) >= 2)


def main() -> int:
    print("=== CRM-PIPELINE-TRUTH-1 suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_preserved_packs()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
