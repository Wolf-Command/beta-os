#!/usr/bin/env python3
"""Haikal Beta content UX wave 1 — markers, title format, upload untouched."""
from __future__ import annotations

import ast
import socket
import subprocess
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
HTML = ROOT / "dashboards" / "content-2.0.html"
SERVE = ROOT / "scripts" / "serve_beta.py"

PASS = 0
FAIL = 0
LINES: list[str] = []


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _upload_slice(html: str) -> str:
    a = html.index("<!-- UPLOAD -->")
    b = html.index("<!-- WOLF INTELLIGENCE -->")
    return html[a:b]


def _load_title_fn():
    src = SERVE.read_text(encoding="utf-8")
    start = src.index("_BRAND_TITLE_NAMES = {")
    end = src.index("\ndef _ux_derive_workflow_status")
    ns: dict = {"date": date, "_wi": type("W", (), {})()}
    exec(src[start:end], ns)  # noqa: S102 — local helper, no network
    return ns["_human_fortnight_title"]


def main() -> int:
    html = HTML.read_text(encoding="utf-8")
    serve = SERVE.read_text(encoding="utf-8")

    log(HTML.is_file() and "Select all" in html and "Deselect all" in html, "01 select all / deselect all")
    log('id="libDetailedToggle"' in html and ">Detailed filters<" in html, "02 detailed filters control")
    log('id="libDetailed"' in html and "hidden" in html.split('id="libDetailed"', 1)[1][:80], "03 accordion collapsed")
    log("status-inline" in html and "production-status" in html, "04 list status control")
    for eid in ("dashLede", "planLede", "libLede", "wolfLede"):
        log(f'id="{eid}"' in html, f"05 page lede #{eid}")
    log("humanFortnightTitle" in html and "Habitat Fortnight" not in html.split("function humanFortnightTitle", 1)[0][-20:],
        "06 display title helper")
    log("BRAND_TINT" in html and "color-mix" in html and "--brand-primary" in html, "07 brand tint tokens")
    log('--font: "Inter"' in html and "style.fontFamily" not in html and 'setProperty("--font"' not in html,
        "08 shared font kept")
    log("Smart Upload" in html and "wizStep1" in html and "upDetailDefault" in html, "09 upload markers still present")
    log("metricool write" not in html.lower(), "10 no Metricool write UI")

    head = subprocess.check_output(
        ["git", "show", "HEAD:dashboards/content-2.0.html"],
        cwd=ROOT,
        text=True,
    )
    log(_upload_slice(head) == _upload_slice(html), "11 upload section byte-identical to HEAD")

    js = html.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/haikal-ux-wave1.js")
    tmp.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(r.returncode == 0, "12 board JS syntax", (r.stderr or "OK")[:180])

    title = _load_title_fn()
    log(title("habitat", "2026-09-14", "2026-09-27") == "Habitat Fortnight Sep 14—27",
        "13 habitat same-month title", title("habitat", "2026-09-14", "2026-09-27"))
    log(title("umablu", "2026-09-14", "2026-09-27") == "Uma Blu Fortnight Sep 14—27",
        "14 uma blu title", title("umablu", "2026-09-14", "2026-09-27"))
    log(title("habitat", "2026-09-28", "2026-10-11") == "Habitat Fortnight Sep 28—Oct 11",
        "15 cross-month title", title("habitat", "2026-09-28", "2026-10-11"))
    log("_human_fortnight_title" in serve and "UPDATE content_plans SET title=?" in serve,
        "16 format-on-read and new-create title write")
    # parser sanity: helper is real syntax
    ast.parse(serve)

    try:
        with urllib.request.urlopen("http://127.0.0.1:8788/content-2.0.html", timeout=8) as resp:
            served = resp.read().decode("utf-8", "replace")
        log(resp.status == 200 and "Select all" in served and "Detailed filters" in served
            and "status-inline" in served and 'id="libDetailed"' in served,
            "17 live :8788 board", f"status={resp.status}")
    except Exception as exc:  # noqa: BLE001
        log(False, "17 live :8788 board", str(exc)[:180])

    s = socket.socket()
    s.settimeout(1.5)
    up8787 = s.connect_ex(("127.0.0.1", 8787)) == 0
    s.close()
    log(up8787, "18 production :8787 still up")

    print("\n".join(LINES))
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
