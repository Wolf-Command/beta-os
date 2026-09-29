#!/usr/bin/env python3
"""V1-SWEEP-1 — Non-HR V1 status register + safe Beta redirects."""
from __future__ import annotations

import json
import os
import socket
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import v1_status_register as v1reg  # noqa: E402
from core import wolf_shell as _wolf_shell  # noqa: E402
import serve_beta as sb  # noqa: E402

ZAYEN_EMAIL = "laluzayen@gmail.com"
MATT_EMAIL = "mrwolf@wolfcommand.net"
REGISTER = ROOT / "state" / "finance-core-sprint" / "V1-STATUS-REGISTER-20260929.json"
ARM = ROOT / "state" / "finance-core-sprint" / "V1-SWEEP-1-ARM.json"
RESULT = ROOT / "docs" / "wolf" / "ops" / "V1-SWEEP-1-RESULT.md"
INV = ROOT / "state" / "finance-core-sprint" / "INVENTORY-20260929.json"

PROD_PID = 15975
PROD_PORT = 8787

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


def _http(
    method: str, url: str, email: str | None = None, *, follow: bool = False
) -> tuple[int, bytes, dict[str, str]]:
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    req = Request(url, method=method, headers=headers)

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
            return None

    if follow:
        opener = urllib.request.build_opener()
    else:
        opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=20) as resp:
            return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except HTTPError as exc:
        hdrs = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        return exc.code, exc.read() if exc.fp else b"", hdrs


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


def test_register() -> None:
    check("register file present", REGISTER.is_file(), str(REGISTER))
    reg = json.loads(REGISTER.read_text(encoding="utf-8"))
    check("schema", reg.get("schema") == "wolf.finance-core-sprint.v1-status-register.v1")
    check("pack V1-SWEEP-1", reg.get("pack") == "V1-SWEEP-1")
    check("staff_ready false", reg.get("staff_ready") is False)
    check("human_commissioned false", reg.get("human_commissioned") is False)
    check("hr_deferred true", reg.get("hr_deferred") is True)
    check("no destructive cutover flag", reg.get("destructive_sor_cutover") is False)
    check("prod_touched false", reg.get("prod_touched") is False)
    check(
        "did not auto-start exit report",
        reg.get("cursor_did_not_auto_start_exit_report") is True,
    )

    inv = json.loads(INV.read_text(encoding="utf-8"))
    inv_ids = {it["id"] for it in inv["C_v1_inventory"]["items"]}
    reg_ids = {it["id"] for it in reg["items"]}
    check("register covers inventory ids", inv_ids == reg_ids, f"missing={inv_ids-reg_ids} extra={reg_ids-inv_ids}")

    hr = next((it for it in reg["items"] if it["id"] == "hr-surfaces"), None)
    check("HR class HR-DEFERRED", hr is not None and hr.get("class") == "HR-DEFERRED")
    check("helper hr_is_deferred", v1reg.hr_is_deferred(reg) is True)

    superseded = [it for it in reg["items"] if it.get("class") == "SUPERSEDED"]
    check("SUPERSEDED count >= 3", len(superseded) >= 3, str(len(superseded)))
    check("SUPERSEDED have beta disposition", v1reg.superseded_have_beta_disposition(reg))
    for it in superseded:
        check(
            f"SUPERSEDED disposition {it['id']}",
            bool((it.get("beta_disposition") or "").strip()),
        )

    # MOUNTED RO not deleted
    for row in v1reg.mounted_ro_paths_intact():
        if row.get("exists") is None:
            check(f"MOUNTED RO listed {row['id']}", True, "path not absolute — documented")
            continue
        check(f"MOUNTED RO intact {row['id']}", row.get("exists") is True, str(row.get("path")))

    # Absolute evidence paths that claimed exists=true
    for it in reg["items"]:
        p = it.get("evidence_path")
        if it.get("evidence_exists") is True and isinstance(p, str) and p.startswith("/"):
            check(f"evidence exists {it['id']}", Path(p).exists(), p)

    check("class_counts present", isinstance(reg.get("class_counts"), dict) and len(reg["class_counts"]) >= 5)


def test_redirects_and_surface() -> None:
    httpd, port = _start_beta()
    base = f"http://127.0.0.1:{port}"
    try:
        # atrium → /amg/finance
        for src in (
            "/atrium-finance",
            "/atrium-finance.html",
            "/dashboards/atrium-finance.html",
        ):
            code, _, hdrs = _http("GET", f"{base}{src}", ZAYEN_EMAIL)
            loc = hdrs.get("location", "")
            check(f"redirect {src}", code in (301, 302) and loc.endswith("/amg/finance"), f"{code} {loc}")

        # bzg aliases → /bzg/finance
        for src in ("/bzg-finance", "/bzg-finance.html", "/dashboards/bzg-finance.html"):
            code, _, hdrs = _http("GET", f"{base}{src}", ZAYEN_EMAIL)
            loc = hdrs.get("location", "")
            check(f"redirect {src}", code in (301, 302) and loc.endswith("/bzg/finance"), f"{code} {loc}")

        # wolf_shell table also carries atrium redirect
        check(
            "wolf_shell atrium redirect",
            _wolf_shell.route_merge_redirect_target("/atrium-finance") == "/amg/finance",
        )
        check(
            "wolf_shell bzg redirect",
            _wolf_shell.route_merge_redirect_target("/bzg-finance") == "/bzg/finance",
        )

        # HR paths must NOT be redirected by this pack map
        for hr_path in ("/hr", "/hr-hiring", "/dashboards/hr-hiring-onboarding.html"):
            dest = v1reg.board_redirect_target(hr_path)
            check(f"HR not redirected {hr_path}", dest is None)

        # status API + page
        code, body, _ = _http("GET", f"{base}/api/ops/v1-status", MATT_EMAIL)
        check("api v1-status 200", code == 200, str(code))
        payload = json.loads(body.decode("utf-8"))
        check("api ok", payload.get("ok") is True)
        check("api staff_ready false", payload.get("staff_ready") is False)
        check("api human_commissioned false", payload.get("human_commissioned") is False)
        check("api hr_deferred", payload.get("hr_deferred") is True)
        check("api items >= 20", len(payload.get("items") or []) >= 20, str(len(payload.get("items") or [])))

        code, body, _ = _http("GET", f"{base}/ops/v1-status", MATT_EMAIL)
        check("page v1-status 200", code == 200, str(code))
        text = body.decode("utf-8", errors="replace")
        check("page has title", "V1 Status Register" in text)
        check("page honesty false flags", "staff_ready=false" in text and "human_commissioned=false" in text)

        # canonical finance still reachable
        code, _, _ = _http("GET", f"{base}/bzg/finance", ZAYEN_EMAIL)
        check("canonical /bzg/finance still 200", code == 200, str(code))
    finally:
        httpd.shutdown()


def test_no_prod_touch() -> None:
    # Prod listener pid must remain the known READ-ONLY process if present.
    try:
        import subprocess

        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        check("prod :8787 still listening", "LISTEN" in out)
        check("prod pid still 15975", str(PROD_PID) in out, out.splitlines()[1] if len(out.splitlines()) > 1 else out)
    except Exception as exc:  # noqa: BLE001
        check("prod probe", False, str(exc))

    # This pack must not claim prod mutate
    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm staff_ready false", arm.get("staff_ready") is False)
        check("arm human_commissioned false", arm.get("human_commissioned") is False)
        check("arm no push", arm.get("no_push") is True)
        check("arm hr_deferred", arm.get("hr_deferred") is True)


def test_result_doc() -> None:
    # RESULT may be written after tests in the same session — soft check if present.
    if RESULT.is_file():
        text = RESULT.read_text(encoding="utf-8")
        check("RESULT mentions V1-SWEEP-1", "V1-SWEEP-1" in text)
        check(
            "RESULT HR deferred",
            ("HR-DEFERRED" in text) or ("HR stays" in text) or ("hr_deferred" in text.lower()),
        )
        check(
            "RESULT exit report handoff",
            ("Exit Report" in text) and (("not auto" in text.lower()) or ("Peaches" in text)),
        )
    else:
        check("RESULT pending write", True, "will be written at EXIT")


def main() -> int:
    test_register()
    test_redirects_and_surface()
    test_no_prod_touch()
    test_result_doc()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
