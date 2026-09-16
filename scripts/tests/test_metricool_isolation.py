#!/usr/bin/env python3
"""Prove Beta Metricool fail-closed isolation. Never call real Metricool. Never touch prod creds."""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PROD_CRED = Path.home() / ".openclaw" / "credentials" / "metricool.json"

# Force disabled regardless of ambient env for this process
os.environ["BETA_METRICOOL_ENABLED"] = "false"
os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
# Clear any explicit path so enabled+path tests are separate
os.environ.pop("BETA_METRICOOL_CREDS_PATH", None)

opens: list[str] = []
_real_open = open


def guarded_open(file, *args, **kwargs):
    path = str(file)
    opens.append(path)
    if "openclaw/credentials/metricool.json" in path.replace("\\", "/"):
        raise AssertionError(f"PROD CREDENTIAL OPEN ATTEMPTED: {path}")
    return _real_open(file, *args, **kwargs)


import builtins

builtins.open = guarded_open

# Network ban
_real_urlopen = urllib.request.urlopen


def banned_urlopen(*a, **k):
    raise AssertionError("NETWORK CALL ATTEMPTED during isolation test")


urllib.request.urlopen = banned_urlopen

import metricool_read_client as mc  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        raise SystemExit(1)


def main() -> None:
    before = None
    if PROD_CRED.is_file():
        before = PROD_CRED.stat()

    st = mc.metricool_status()
    check("status disabled", st.get("status") == "DISABLED IN BETA" and st.get("enabled") is False)

    try:
        mc._load_creds()
        check("load_creds blocked", False, "should have raised")
    except mc.MetricoolReadError as exc:
        check("load_creds blocked", "DISABLED" in str(exc))

    try:
        mc.list_profiles()
        check("list_profiles blocked", False)
    except mc.MetricoolReadError as exc:
        check("list_profiles blocked", "DISABLED" in str(exc) or "no network" in str(exc).lower() or "DISABLED" in str(exc))

    try:
        mc.assert_metricool_write_allowed("publish")
        check("write blocked", False)
    except mc.MetricoolWriteBlocked as exc:
        check("write blocked", "BETA_METRICOOL_WRITE_ENABLED=false" in str(exc))

    # Refuse production path even if enabled
    os.environ["BETA_METRICOOL_ENABLED"] = "true"
    os.environ["BETA_METRICOOL_CREDS_PATH"] = str(PROD_CRED)
    try:
        mc._load_creds()
        check("refuse prod path", False)
    except mc.MetricoolReadError as exc:
        check("refuse prod path", "refused" in str(exc).lower() or "production" in str(exc).lower() or "not allowed" in str(exc).lower())

    # Reset disabled
    os.environ["BETA_METRICOOL_ENABLED"] = "false"
    os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"

    # Sync soft-fail without network/creds
    from sync_metricool_performance import sync_metricool_performance

    report = sync_metricool_performance(brand_key="habitat", window_days=7)
    check("sync disabled soft", report.get("ok") is False)
    check(
        "sync status message",
        any("DISABLED" in str(e) for e in (report.get("errors") or []))
        or (report.get("metricool") or {}).get("status") == "DISABLED IN BETA",
    )

    # No prod cred open
    bad = [p for p in opens if "openclaw/credentials/metricool.json" in p.replace("\\", "/")]
    check("no prod cred open", not bad, str(bad))

    # Prod cred untouched
    if before is not None:
        after = PROD_CRED.stat()
        check(
            "prod cred mtime/size/ino unchanged",
            (after.st_mtime_ns, after.st_size, after.st_ino)
            == (before.st_mtime_ns, before.st_size, before.st_ino),
        )

    # Source must not hardcode openclaw metricool path
    src = (SCRIPTS / "metricool_read_client.py").read_text(encoding="utf-8")
    check("no hardcoded metricool.json path", "metricool.json" not in src)
    check("no Path.home openclaw fallback", 'Path.home() / ".openclaw"' not in src)

    # Basic import serve_beta without starting server
    import serve_beta  # noqa: F401

    check("serve_beta imports", True)

    print("ALL PASS")


if __name__ == "__main__":
    main()
