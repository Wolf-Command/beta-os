#!/usr/bin/env python3
"""EXTERNAL-ROUTE-HEALTH — classification, dedupe, safe recover gate (Beta)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import external_route_health as erh  # noqa: E402

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


def test_classify_external() -> None:
    red = erh.classify_external(
        {
            "status_code": 502,
            "body_snippet": '{"error":"sidecar_unavailable"}',
            "headers": {},
            "error": None,
        }
    )
    check("502 sidecar_unavailable → RED", red["class"] == erh.CLASS_RED and red["critical"])

    host = erh.classify_external(
        {
            "status_code": 502,
            "body_snippet": "Host Error",
            "headers": {},
            "error": None,
        }
    )
    check("Host Error body → RED", host["class"] == erh.CLASS_RED)

    amber = erh.classify_external(
        {
            "status_code": 302,
            "body_snippet": "",
            "headers": {
                "location": "https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/x"
            },
            "error": "HTTPError:302",
        }
    )
    check(
        "CF Access 302 → ORIGIN_REACHABLE not RED",
        amber["class"] == erh.CLASS_AMBER and not amber["critical"],
    )

    refused = erh.classify_external(
        {
            "status_code": None,
            "body_snippet": "",
            "headers": {},
            "error": "URLError: Connection refused",
        }
    )
    check("connection refused → RED", refused["class"] == erh.CLASS_RED)

    green = erh.classify_external(
        {
            "status_code": 200,
            "body_snippet": "<!doctype html><html><title>Finance</title></html>",
            "headers": {"content-type": "text/html"},
            "error": None,
        }
    )
    check("200 HTML → GREEN", green["class"] == erh.CLASS_GREEN)


def test_classify_loopback() -> None:
    ok = erh.classify_loopback(
        {
            "status_code": 403,
            "body_snippet": '{"error":"missing_auth"}',
            "headers": {},
            "error": None,
        }
    )
    check("loopback missing_auth → amber not RED", ok["class"] == erh.CLASS_AMBER and not ok["critical"])

    html403 = erh.classify_loopback(
        {
            "status_code": 403,
            "body_snippet": "<!DOCTYPE html><title>Access denied</title>",
            "headers": {},
            "error": None,
        }
    )
    check("loopback HTML Access denied → amber not RED", html403["class"] == erh.CLASS_AMBER and not html403["critical"])

    bad = erh.classify_loopback(
        {
            "status_code": 502,
            "body_snippet": '{"error":"sidecar_unavailable"}',
            "headers": {},
            "error": None,
        }
    )
    check("loopback sidecar_unavailable → RED", bad["class"] == erh.CLASS_RED and bad["critical"])


def test_dedupe_and_owner_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        latest = tmp_path / "latest.json"
        alert = tmp_path / "alert.json"
        with mock.patch.object(erh, "LATEST_PATH", latest), mock.patch.object(
            erh, "ALERT_PATH", alert
        ):
            overall_red = {
                "class": erh.CLASS_RED,
                "color": "RED",
                "critical": True,
                "reasons": ["external:amg_finance:host_error"],
                "summary": "RED CRITICAL",
            }
            payload = {"as_of_wita": "2026-09-30T10:50:00+08:00", "overall": overall_red}
            a1 = erh._dedupe_alert(overall_red, payload)
            check("first RED is transition", a1.get("transition_to_red") is True)
            check("first RED surfaces exception", a1.get("surface_exception") is True)

            payload2 = {"as_of_wita": "2026-09-30T10:55:00+08:00", "overall": overall_red}
            a2 = erh._dedupe_alert(overall_red, payload2)
            check("sustained RED suppresses noise", a2.get("noise_suppressed") is True)
            check("sustained still surfaces", a2.get("surface_exception") is True)
            check("alert_id stable", a2.get("alert_id") == a1.get("alert_id"))

            overall_amber = {
                "class": erh.CLASS_AMBER,
                "color": "AMBER",
                "critical": False,
                "reasons": [],
                "summary": "ORIGIN_REACHABLE",
            }
            a3 = erh._dedupe_alert(
                overall_amber, {"as_of_wita": "2026-09-30T11:00:00+08:00", "overall": overall_amber}
            )
            check("clear RED recorded", a3.get("cleared_red") is True)
            check("amber does not surface exception", a3.get("surface_exception") is False)

            pack = {
                "as_of_wita": "2026-09-30T10:50:00+08:00",
                "overall": overall_red,
                "alert": a1,
            }
            items = erh.owner_exception_items(latest=pack)
            check("owner items while RED", len(items) == 1 and items[0]["kind"] == "external_route")
            items_clear = erh.owner_exception_items(
                latest={"overall": overall_amber, "alert": a3}
            )
            check("no owner items when amber", items_clear == [])


def test_honesty_flags() -> None:
    flags = erh.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("auth not weakened", flags.get("auth_weakened") is False)
    check("prod mutate false", flags.get("prod_mutate") is False)
    check("prod port 8787 held", flags.get("prod_port_untouched") == 8787)


def test_autorecover_skips_when_healthy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plist = Path(tmp) / "net.wolfcommand.atrium-finance-sidecar.plist"
        plist.write_text("<plist/>", encoding="utf-8")
        with mock.patch.object(erh, "LAUNCHAGENT_PLIST", plist), mock.patch.object(
            erh,
            "_lsof_listen",
            return_value={"listening": True, "pids": [1], "status": "UP", "port": 8790},
        ), mock.patch.object(
            erh,
            "_http_get",
            return_value={
                "status_code": 200,
                "body_snippet": "ok",
                "headers": {},
                "error": None,
            },
        ):
            ev = erh._safe_autorecover_sidecar(dry_run=False)
            check("skip kickstart when healthy", ev.get("skipped") == "sidecar_already_healthy")
            check("not attempted when healthy", ev.get("attempted") is False)


def test_script_exists() -> None:
    tick = ROOT / "scripts" / "ops" / "external_route_health_tick.py"
    rule = ROOT / "docs" / "RULE-External-Route-Health-2026-09-30.md"
    core = ROOT / "scripts" / "core" / "external_route_health.py"
    check("tick script exists", tick.is_file())
    check("rule doc exists", rule.is_file())
    check("core module exists", core.is_file())


def main() -> int:
    os.environ.setdefault("WOLF_TEST_MODE", "1")
    test_classify_external()
    test_classify_loopback()
    test_dedupe_and_owner_items()
    test_honesty_flags()
    test_autorecover_skips_when_healthy()
    test_script_exists()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
