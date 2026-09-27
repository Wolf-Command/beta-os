#!/usr/bin/env python3
"""Pack 4 — dashboard truth, data quality, staleness. Beta only."""
from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import dashboard_truth as truth  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0
MATT = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
NOW = datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def fresh(**overrides):
    base = {
        "available": True,
        "readable": True,
        "authoritative": True,
        "verification": "VERIFIED",
        "presence": "PRESENT",
        "time_class": "CURRENT",
        "measure": "ACTUAL",
        "build": "LIVE",
        "observed_at": NOW.isoformat(),
        "as_of": NOW.isoformat(),
        "external": False,
        "commissioned": True,
        "human_commissioned": False,
    }
    base.update(overrides)
    return base


def test_classifier() -> None:
    live = truth.classify(fresh())
    check("live when verified and in window", live["display_state"] == "LIVE", live["display_state"])
    check("live is current-class", live["time_class"] == "CURRENT" and live["shown_as_current"] is True)

    current = truth.classify(fresh(build="BUILT", observed_at=(NOW - timedelta(hours=2)).isoformat()))
    check("built fresh is current not live", current["display_state"] == "CURRENT", current["display_state"])

    stale = truth.classify(fresh(observed_at=(NOW - timedelta(days=3)).isoformat()))
    check("old verified fact is stale", stale["display_state"] == "STALE", stale["display_state"])
    check("stale is not shown as current", stale["shown_as_current"] is False and stale["stale_shown_as_current"] is False)
    check("stale time class is not current", stale["time_class"] != "CURRENT")

    forced = truth.mark_stale("projection disagrees with canonical state")
    check("shared stale mark", forced["display_state"] == "STALE" and forced["shown_as_current"] is False)

    agreed = truth.projection_status("SAME", "SAME")
    check("agreeing projection can be live", agreed["display_state"] == "LIVE", agreed["display_state"])
    split = truth.projection_status("CANON", "CARD")
    check("disagreeing projection is stale", split["display_state"] == "STALE")

    unknown = truth.classify(fresh(presence="UNKNOWN"))
    empty = truth.classify(fresh(presence="EMPTY", build="BUILT"))
    check("unknown is not empty", unknown["display_state"] == "UNKNOWN" and unknown["presence"] == "UNKNOWN")
    check("empty can be current", empty["display_state"] == "CURRENT" and empty["presence"] == "EMPTY", empty["display_state"])
    check("empty plain says not unknown", "not an unknown" in empty["plain"])

    claimed = truth.classify(fresh(verification="CLAIMED"))
    check("claimed is not verified", claimed["claim_state"] == "CLAIMED" and claimed["display_state"] == "NEEDS REVIEW")
    check("claimed is not live", claimed["display_state"] != "LIVE" and claimed["display_state"] != "CURRENT")

    found = truth.classify(fresh(authoritative=False))
    check("source found is not authoritative", found["authority"] == "SOURCE_FOUND" and found["display_state"] == "NEEDS REVIEW")

    historical = truth.classify(fresh(time_class="HISTORICAL"))
    check("historical is not current", historical["time_class"] == "HISTORICAL" and historical["display_state"] not in {"LIVE", "CURRENT"})

    estimate = truth.classify(fresh(measure="ESTIMATE"))
    check("estimate is not actual display", estimate["measure"] == "ESTIMATE" and estimate["display_state"] == "NEEDS REVIEW")

    designed = truth.classify(fresh(build="DESIGNED"))
    tested = truth.classify(fresh(build="TESTED"))
    check("designed is not live", designed["display_state"] == "NEEDS REVIEW" and designed["build_state"] == "DESIGNED")
    check("tested is not live", tested["display_state"] == "CURRENT" and tested["build_state"] == "TESTED", tested["display_state"])

    external = truth.classify(fresh(external=True, commissioned=False))
    check("uncommissioned external is not live", external["display_state"] == "NEEDS REVIEW" and external["commissioned"] is False)

    closed = truth.fail_closed("reader missing")
    check("failure is unavailable", closed["display_state"] == "UNAVAILABLE")
    check("failure is not zero", "0" not in closed["plain"] and closed["presence"] != "EMPTY")

    secret = truth.public_text("token sk-live-abc /Users/wolfterminal/secret")
    check("secret text withheld", "sk-" not in secret and "/Users/" not in secret)


def test_registry() -> None:
    report = truth.source_registry()
    ids = [row["source_id"] for row in report["sources"]]
    check("seven sources", ids == list(truth.SOURCE_IDS), str(ids))
    check("vocabulary", report["vocabulary"] == list(truth.DISPLAY_STATES))
    check("distinctions present", len(report["distinctions"]) == 6)
    check("register not commissioned", report["human_commissioned"] is False and report["staff_ready"] is False)
    check("no network and no ledger write", report["network_probes"] is False and report["ledger_write"] is False)
    for row in report["sources"]:
        check(
            f"{row['source_id']} honest flags",
            row["commissioned"] is False
            and row["human_commissioned"] is False
            and row["staff_ready"] is False
            and row["display_state"] in truth.DISPLAY_STATES
            and row["stale_shown_as_current"] is False
            and "/Users/" not in json.dumps(row),
            row["display_state"],
        )
        if row["display_state"] == "STALE":
            check(f"{row['source_id']} stale not current", row["shown_as_current"] is False)
    by_id = {row["source_id"]: row for row in report["sources"]}
    check("yanolja unavailable", by_id["yanolja"]["display_state"] == "UNAVAILABLE", by_id["yanolja"]["display_state"])
    check("yanolja not a number", by_id["yanolja"]["presence"] != "EMPTY")
    check("esb not live", by_id["esb"]["display_state"] not in {"LIVE", "CURRENT"})
    check("wolf core read", by_id["wolf_core"]["display_state"] in {"CURRENT", "UNAVAILABLE", "UNKNOWN", "NEEDS REVIEW"})
    check("finance not a live figure", by_id["finance_ledgers"]["display_state"] != "LIVE")
    check("klaviyo not called live", by_id["klaviyo"]["display_state"] != "LIVE")
    stamp = truth.stamp("my-work")
    check("staff stamp is wolf core only", [r["source_id"] for r in stamp["sources"]] == ["wolf_core"])
    check("staff stamp hides store counts", "store_counts" not in stamp["sources"][0])
    try:
        truth.stamp("nope")
        check("unknown surface refused", False)
    except truth.TruthError as exc:
        check("unknown surface refused", exc.code == "unknown_surface")
    spec = truth.ui_spec()
    check("shell reuses wolfnav", spec["header"] == "wolfnav" and spec["nav"] == "wolfnav")
    check("ui has empty error denied", spec["empty"] == "wolf-empty" and spec["error"] == "wolf-error" and spec["permission_denied"] == "wolf-denied")


def test_files() -> None:
    css = (ROOT / "dashboards" / "assets" / "wolf-truth.css").read_text(encoding="utf-8")
    js = (ROOT / "dashboards" / "assets" / "wolf-truth.js").read_text(encoding="utf-8")
    page = (ROOT / "dashboards" / "dashboard-truth.html").read_text(encoding="utf-8")
    for state, token in (
        ("LIVE", "wolf-state-live"),
        ("CURRENT", "wolf-state-current"),
        ("STALE", "wolf-state-stale"),
        ("UNKNOWN", "wolf-state-unknown"),
        ("UNAVAILABLE", "wolf-state-unavailable"),
        ("NEEDS REVIEW", "wolf-state-needs-review"),
    ):
        check(f"css {state}", token in css)
        check(f"js {state}", state in js)
    check("css empty error denied", "wolf-empty" in css and "wolf-error" in css and "wolf-denied" in css)
    check("js empty error denied", "wolf-empty" in js and "wolf-error" in js and "wolf-denied" in js)
    check("page distinctions", "HISTORICAL is not CURRENT" in page and "EMPTY is not UNKNOWN" in page)
    check("page no second nav", 'id="wolfnav"' not in page)
    check("page mobile", "max-width: 860px" in page or "@media (max-width: 860px)" in css)
    for rel, surface in (
        ("owner-empire-pack.html", "empire"),
        ("my-work.html", "my-work"),
        ("amg-ops-pack.html", "amg"),
        ("ggv-ops-pack.html", "ggv"),
        ("bzg.html", "bzg"),
    ):
        text = (ROOT / "dashboards" / rel).read_text(encoding="utf-8")
        check(f"{rel} stamp", f'data-surface="{surface}"' in text and "wolf-truth.js" in text)
    my_work = (ROOT / "dashboards" / "my-work.html").read_text(encoding="utf-8")
    check("my-work still has no role ids", "ROLE-" not in my_work and "PERS-" not in my_work)


def test_http_and_headless() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            if obj.__name__ == "BetaHandler":
                Handler = obj
                break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(method: str, path: str, subject: str | None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = b"{}" if method != "GET" else None
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method, data=data)
        try:
            with urlopen(req, timeout=60) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode())
                except json.JSONDecodeError:
                    return resp.status, raw.decode("utf-8", "replace")
        except HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = raw.decode("utf-8", "replace")
            return exc.code, parsed

    try:
        st, anon = call("GET", "/api/dashboard-truth", None)
        check("anon register 403", st == 403 and isinstance(anon, dict) and anon.get("ui", {}).get("component") == "permission-denied", str(st))
        st, anon_page = call("GET", "/dashboard-truth", None)
        check("anon page 403", st == 403, str(st))
        st, direct = call("GET", "/dashboard-truth.html", None)
        check("anon direct html 403", st == 403, str(direct)[:180] if not isinstance(direct, dict) else str(st))
        st, outsider = call("GET", "/api/dashboard-truth", OUTSIDER)
        check("outsider register 403", st == 403, str(st))
        st, haikal = call("GET", "/dashboard-truth", HAIKAL)
        check("staff page 403", st == 403 and isinstance(haikal, dict) and haikal.get("ui", {}).get("component") == "permission-denied", str(haikal)[:240])
        st, haikal_empire = call("GET", "/api/dashboard-truth/stamp?surface=empire", HAIKAL)
        check("staff empire stamp 403", st == 403, str(st))
        st, bad = call("GET", "/api/dashboard-truth/stamp?surface=nope", MATT)
        check("unknown surface 400", st == 400, str(bad)[:200])
        st, post_anon = call("POST", "/api/dashboard-truth", None)
        check("anon write 403", st == 403, str(st))
        st, post_owner = call("POST", "/api/dashboard-truth", MATT)
        check("owner write 405", st == 405 and isinstance(post_owner, dict) and post_owner.get("external_writes") is False, str(post_owner)[:200])
        st, owner = call("GET", "/api/dashboard-truth", MATT)
        check("owner register 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner seven sources", len(owner.get("sources") or []) == 7, str(len(owner.get("sources") or [])))
            check("owner not commissioned", owner.get("human_commissioned") is False and owner.get("staff_ready") is False)
            check("owner no path leak", "/Users/" not in json.dumps(owner))
        st, staff = call("GET", "/api/dashboard-truth/stamp?surface=my-work", HAIKAL)
        check("staff my-work stamp 200", st == 200 and isinstance(staff, dict) and staff.get("ok") is True, str(staff)[:240])
        if isinstance(staff, dict):
            ids = [r.get("source_id") for r in staff.get("sources") or []]
            check("staff sees wolf core only", ids == ["wolf_core"], str(ids))
            check("staff stamp not commissioned", staff.get("human_commissioned") is False)
        st, devi = call("GET", "/api/dashboard-truth/stamp?surface=bzg", DEVI)
        check("fb lead bzg stamp", st == 200, str(devi)[:240])
        st, page = call("GET", "/dashboard-truth", MATT)
        text = page if isinstance(page, str) else json.dumps(page)
        check("owner page 200 shell", st == 200 and 'id="wolfnav"' in text and "Data truth" in text, text[:180])

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
                    with urlopen(req, timeout=30) as resp:
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
            ("owner-desktop", MATT, 1280, "/dashboard-truth", ("Yanolja", "wolf-card", "Not commissioned")),
            ("owner-mobile", MATT, 390, "/dashboard-truth", ("ESB", "wolf-state", "Not commissioned")),
            ("staff-mobile", HAIKAL, 390, "/my-work", ("Data truth", "wolf-state")),
            ("staff-denied", HAIKAL, 1280, "/dashboard-truth", ("permission-denied",)),
        )
        for label, subject, width, path, needles in shots:
            _Proxy.subject = subject
            proc = subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--virtual-time-budget=8000",
                    f"--window-size={width},844",
                    "--dump-dom",
                    f"http://127.0.0.1:{pport}{path}",
                ],
                capture_output=True,
                text=True,
                timeout=40,
            )
            dom = proc.stdout or ""
            for needle in needles:
                check(f"{label} shows {needle}", needle in dom, (proc.stderr or dom)[-180:])
        proxy.shutdown()
    finally:
        httpd.shutdown()


def main() -> int:
    test_classifier()
    test_registry()
    test_files()
    test_http_and_headless()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
