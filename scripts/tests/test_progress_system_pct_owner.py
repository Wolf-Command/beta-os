#!/usr/bin/env python3
"""Owner SYSTEM% prove — 2026-09-19.

SYSTEM is the live ledger sum, half-up to 1 d.p. Not a frozen 25.3.
Does not write the ledger, raise maturity, or touch Production.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import socket
import sys
import threading
from decimal import Decimal, ROUND_HALF_UP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core.progress_read_model import (  # noqa: E402
    PERS_MATT,
    compute_system_from_ledger,
    build_read_model,
)

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "progress.html"
READ_MODEL = SCRIPTS / "core" / "progress_read_model.py"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py":
        "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py":
        "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py":
        "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py":
        "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}
FROZEN = f"{25}.{3}"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_pct(sum_credits: Decimal = Decimal("19.65"), n: int = 77) -> Decimal:
    exact = (sum_credits / Decimal(n)) * Decimal(100)
    return exact.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def port_up(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(1.5)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def http_get(url: str, headers: dict | None = None, timeout: float = 8) -> tuple[int, bytes]:
    req = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def main() -> int:
    ledger_before = sha(LEDGER) if LEDGER.is_file() else ""
    raw = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {}
    proven_before = sum(1 for row in raw.values() if row and str(row[0]).upper() == "PROVEN")
    ready_before = sum(1 for row in raw.values() if row and str(row[0]).upper() == "READY")

    independent = expected_pct()
    check("independent half-up is 25.5", independent == Decimal("25.5"), str(independent))

    system = compute_system_from_ledger(LEDGER)
    check("compute status OK", system.get("status") == "OK" and system.get("ok") is True, str(system.get("status")))
    check("compute n=77", system.get("n") == 77, str(system.get("n")))
    check("compute sum 19.65", system.get("sum_credits_exact") == "19.65", str(system.get("sum_credits_exact")))
    check("compute system_pct 25.5", system.get("system_pct") == 25.5, str(system.get("system_pct")))
    check("compute pct matches independent", system.get("system_pct") == float(independent))
    check("not frozen prior display", system.get("system_pct") != float(expected_pct(Decimal("19.45"))))

    model = build_read_model()
    msys = model.get("system") or {}
    empire = ((model.get("views") or {}).get("Empire") or {}).get("system") or {}
    check("read model ok", model.get("ok") is True and model.get("progress_type") == "SYSTEM_FROM_LEDGER")
    check("read model system_pct 25.5", msys.get("system_pct") == 25.5, str(msys.get("system_pct")))
    check("empire view system_pct 25.5", empire.get("system_pct") == 25.5, str(empire.get("system_pct")))
    check("integrity ok", (msys.get("integrity") or {}).get("ok") is True, str(msys.get("integrity")))
    check("ledger path is live file", str(msys.get("ledger_path") or "").endswith("model-c-baseline-assessments.json"))

    html = HTML.read_text(encoding="utf-8")
    rm = READ_MODEL.read_text(encoding="utf-8")
    check("HTML has no frozen display", FROZEN not in html)
    check("read model has no frozen display", FROZEN not in rm)
    check("HTML binds system.system_pct", "system.system_pct" in html)
    check("HTML headline uses systemPct", "SYSTEM — ${esc(systemPct)}%" in html)
    check("HTML stale hides the percent", "SCORING PROJECTION STALE" in html)

    # Authenticated Owner — same Handler as Beta, ephemeral port. Does not flip live auth.
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    import serve_beta as sb
    from core import request_auth as ra

    ra._ENV_LOADED = True
    handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            handler = obj
            break
    check("API handler found", handler is not None)
    if handler is not None:
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = httpd.server_address[1]
        check("ephemeral port is not Production", port not in (8787, 8788), str(port))
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:

            def call(path: str, subject: str | None) -> tuple[int, dict | str]:
                headers = {"Accept": "application/json"}
                if subject:
                    headers["X-Wolf-Subject"] = subject
                code, body = http_get(f"http://127.0.0.1:{port}{path}", headers, timeout=30)
                text = body.decode("utf-8", errors="replace")
                if "application/json" in headers["Accept"] and text[:1] in "{[":
                    try:
                        return code, json.loads(text)
                    except json.JSONDecodeError:
                        return code, text
                return code, text

            anon_code, anon_body = call("/api/progress", None)
            check("anon /api/progress denied", anon_code == 403, str(anon_code))
            check(
                "anon body has no system_pct",
                not (isinstance(anon_body, dict) and (anon_body.get("system") or {}).get("system_pct") == 25.5),
            )

            staff_code, staff_body = call("/api/progress", STAFF)
            check("staff /api/progress 403", staff_code == 403, str(staff_code)[:80])
            check(
                "staff is not Owner",
                isinstance(staff_body, dict) and staff_body.get("person_id") != PERS_MATT,
                str(staff_body)[:160],
            )

            code, data = call("/api/progress", MATT)
            sysd = data.get("system") if isinstance(data, dict) else {}
            check(
                "Owner /api/progress 200",
                code == 200 and isinstance(data, dict) and data.get("ok") is True,
                str(data)[:200],
            )
            check("Owner person PERS-MATT", isinstance(data, dict) and data.get("person_id") == PERS_MATT, str(data)[:120] if isinstance(data, dict) else str(data)[:120])
            check("Owner system_pct 25.5", (sysd or {}).get("system_pct") == 25.5, str((sysd or {}).get("system_pct")))
            check("Owner sum 19.65", (sysd or {}).get("sum_credits_exact") == "19.65", str((sysd or {}).get("sum_credits_exact")))
            check("Owner status OK", (sysd or {}).get("status") == "OK", str((sysd or {}).get("status")))
            empire_api = (((data.get("views") or {}).get("Empire") or {}).get("system") or {}) if isinstance(data, dict) else {}
            check("Owner Empire system_pct 25.5", empire_api.get("system_pct") == 25.5, str(empire_api.get("system_pct")))

            page_code, page = call("/progress", MATT)
            page_text = page if isinstance(page, str) else json.dumps(page)
            check("Owner /progress HTML 200", page_code == 200 and "systemPct" in page_text, str(page_code))
            check("Owner /progress has no frozen display", FROZEN not in page_text)
        finally:
            httpd.shutdown()

    # Optional live :8788. Do not flip BETA_AUTH_MODE on the running Beta process.
    check("Production :8787 still up", port_up(8787))
    if port_up(8788):
        try:
            live_code, live_body = http_get("http://127.0.0.1:8788/progress", timeout=8)
            live_html = live_body.decode("utf-8", errors="replace")
            check("live /progress 200", live_code == 200, str(live_code))
            check("live HTML binds systemPct", "systemPct" in live_html and "system.system_pct" in live_html)
            check("live HTML has no frozen display", FROZEN not in live_html)
            api_code, api_body = http_get(
                "http://127.0.0.1:8788/api/progress",
                headers={"Accept": "application/json"},
                timeout=8,
            )
            api_text = api_body.decode("utf-8", errors="replace")
            check("live anon /api/progress denied", api_code == 403, str(api_code))
            check("live anon body has no frozen display", FROZEN not in api_text)
            check("live auth not weakened", "development_assertion" not in api_text)
        except (URLError, TimeoutError, OSError) as exc:
            check("live :8788 readable", False, str(exc))
    else:
        print("SKIP  live :8788 down")

    ledger_after = sha(LEDGER)
    raw_after = json.loads(LEDGER.read_text(encoding="utf-8"))
    proven_after = sum(1 for row in raw_after.values() if row and str(row[0]).upper() == "PROVEN")
    ready_after = sum(1 for row in raw_after.values() if row and str(row[0]).upper() == "READY")
    check("ledger bytes unchanged", ledger_before == ledger_after)
    check("PROVEN count unchanged", proven_before == proven_after == 12, f"{proven_before}->{proven_after}")
    check("READY count unchanged", ready_before == ready_after == 3, f"{ready_before}->{ready_after}")
    for rel, digest in WIP.items():
        check(f"WIP frozen {Path(rel).name}", sha(ROOT / rel) == digest)

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
