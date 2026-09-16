#!/usr/bin/env python3
"""Regression: real Content Engine board must boot — 42/42 API suite can PASS while HTML is dead.

Catches the Phase 2.6 incident class:
- JS wire throws on missing DOM (wiOpenPlan / wiRefreshContext / wiPrefill)
- Truncated HTML missing </script>
- loadPlanView still reading removed ux.counts while setView('plan') never reaches openPlan
- Dashboard never leaves Loading because init() never runs after mid-wire throw
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
HTML = ROOT / "dashboards" / "content-2.0.html"
BASE = "http://127.0.0.1:8788"
MATT = "mrwolf@wolfcommand.net"

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


def main() -> int:
    html = HTML.read_text(encoding="utf-8")

    log(HTML.is_file() and len(html) > 1000, "01 board html present", f"bytes={len(html)}")
    log("</script>" in html and "</body>" in html and "</html>" in html, "02 html closed script/body/html")

    for eid in ("wiOpenPlan", "wiRefreshContext", "wiPrefill"):
        log(f'id="{eid}"' in html, f"03 required DOM #{eid}")

    # Unguarded pattern that aborted init() in the incident
    unguarded = re.search(
        r'\$\("wiOpenPlan"\)\.addEventListener',
        html,
    )
    log(unguarded is None, "04 wiOpenPlan listener is null-guarded or absent-as-unguarded")

    # Contract: plan view must not require removed ux.counts without a Phase 2.6 loadPlanView override
    has_loadplan_override = "loadPlanView = async function" in html or 'Phase 2.6: setView("plan") calls loadPlanView' in html
    raw_counts_use = bool(re.search(r"ux\.counts\.posts", html))
    log(has_loadplan_override or not raw_counts_use, "05 loadPlanView safe vs ux.counts removal",
        f"override={has_loadplan_override} raw_counts={raw_counts_use}")

    log("renderBrief = function" in html or "renderBrief=function" in html, "06 renderBrief routed to Phase 2.6 brief UI")

    # Serve live page + JS syntax
    try:
        with urllib.request.urlopen(BASE + "/content-2.0.html", timeout=15) as resp:
            served = resp.read().decode("utf-8", "replace")
        log(resp.status == 200 and "wiOpenPlan" in served, "07 served board includes wiOpenPlan", f"status={resp.status} bytes={len(served)}")
    except Exception as e:
        log(False, "07 served board includes wiOpenPlan", str(e))
        served = html

    js_match = re.search(r"<script>(.*?)</script>", served, re.S)
    if js_match:
        tmp = Path("/tmp/WOLF-PHASE2-6-BOARD-REGRESSION.js")
        tmp.write_text(js_match.group(1), encoding="utf-8")
        try:
            r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
            log(r.returncode == 0, "08 board JS syntax", (r.stderr or "OK")[:200])
        except Exception as e:
            log(False, "08 board JS syntax", str(e))
    else:
        log(False, "08 board JS syntax", "no script block")

    # Real browser boot (Playwright) — the gap 42/42 missed
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        log(False, "09 playwright available", str(e))
        _finish()
        return 1 if FAIL else 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context()
            ctx.add_init_script(
                f"localStorage.setItem('wolf_subject','{MATT}');"
                "localStorage.setItem('wolf_brand','habitat');"
            )
            page = ctx.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(BASE + "/content-2.0.html?regression=1", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            snap = page.evaluate(
                """() => ({
                  dashSub: document.getElementById('dashSub')?.textContent || '',
                  stats: document.getElementById('dashStats')?.innerText || '',
                  attention: document.querySelectorAll('#dashAttention .item-card').length,
                })"""
            )
            page.click('button[data-view="plan"]')
            page.wait_for_timeout(1500)
            plan = page.evaluate(
                """() => ({
                  posts: document.querySelectorAll('#postsList .item-card').length,
                  stories: document.querySelectorAll('#storiesList .item-card').length,
                  title: document.getElementById('planTitle')?.textContent || '',
                  toast: document.getElementById('toast')?.textContent || '',
                })"""
            )
            browser.close()
        log(not errors, "09 no uncaught pageerrors on boot", "; ".join(errors)[:300])
        log("Loading" not in snap["dashSub"] and bool(snap["stats"]), "10 dashboard leaves Loading", snap["dashSub"][:80])
        log(plan["posts"] >= 1 and plan["stories"] >= 1, "11 content plan renders cards",
            f"posts={plan['posts']} stories={plan['stories']} toast={plan['toast'][:80]}")
    except Exception as e:
        log(False, "09-11 browser boot", str(e)[:300])

    _finish()
    return 1 if FAIL else 0


def _finish() -> None:
    summary = f"BOARD-REGRESSION PASS={PASS} FAIL={FAIL}"
    LINES.append(summary)
    text = "\n".join(LINES) + "\n"
    Path("/tmp/WOLF-PHASE2-6-BOARD-REGRESSION-OUT.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    raise SystemExit(main())
