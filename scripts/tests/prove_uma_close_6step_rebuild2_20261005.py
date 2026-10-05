#!/usr/bin/env python3
"""Playwright iPhone 14 proof for UMA-CLOSE-6STEP-REBUILD-2 on probe server."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path("/Users/wolfterminal/beta-os")
PROBE = Path("/Users/wolfterminal/hist-close-nav-work/probe_server.py")
PHOTO = "/Users/wolfterminal/hist-close-nav-work/test-shift-report-PEACHES-TEST.png"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8798
TAG = "6step-rebuild2-wolf"
EMAIL = "mrwolf@wolfcommand.net"
BASE = f"http://127.0.0.1:{PORT}"

DUMP = """() => {
  const s = document.querySelector('.step-screen.on');
  const vis = e => e && e.offsetParent !== null;
  return {
    screen: s && s.id,
    top: [...document.querySelectorAll('.top-msg.on,.msg')].filter(vis).map(e => e.innerText),
    buttons: [...(s || document).querySelectorAll('button')].filter(vis).map(b => b.id + ':' + b.innerText.trim() + (b.disabled ? '(disabled)' : '')),
    text: (s ? s.innerText : '').replace(/\\n+/g, ' | ').slice(0, 1200)
  };
}"""


def main() -> int:
    env = {
        **dict(__import__("os").environ),
        "WOLF_CLOSE_VISION_DRY": "1",
        "BETA_LLM_DRY_RUN": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, str(PROBE), str(PORT), TAG],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(3)
    out: list[dict] = []
    submit_results: list[str] = []
    yes_api: list = []
    ro = False
    sep03_ok = False
    check_no_figures = False
    check_no_diff = False
    err: str | None = None
    try:
        with sync_playwright() as p:
            browser = p.webkit.launch()
            ctx = browser.new_context(
                **p.devices["iPhone 14"],
                extra_http_headers={
                    "X-Wolf-Subject": EMAIL,
                    "Cf-Access-Authenticated-User-Email": EMAIL,
                },
            )
            page = ctx.new_page()
            reqs: list[tuple] = []
            page.on(
                "response",
                lambda r: reqs.append(
                    (r.request.method, r.url.replace(BASE, "").split("?")[0], r.status)
                )
                if "/api/" in r.url
                else None,
            )

            def snap(label: str) -> None:
                time.sleep(1.5)
                d = page.evaluate(DUMP)
                d["label"] = label
                out.append(d)

            page.goto(f"{BASE}/uma-blu-close?business_date=2026-09-29", wait_until="networkidle")
            time.sleep(2)
            snap("opened_29sep_photo_only")
            check_no_figures = "DO THESE FIGURES MATCH" not in (out[-1].get("text") or "")
            check_no_diff = "ESB DATA DIFFERENCE FOUND" not in (out[-1].get("text") or "")

            with page.expect_file_chooser() as fc:
                page.locator("#btnUploadShift").tap()
            fc.value.set_files(PHOTO)
            time.sleep(3)
            snap("after_upload")

            page.reload(wait_until="networkidle")
            time.sleep(2)
            snap("fresh_resume_after_upload")
            if page.locator("#btnReadShift").is_visible():
                page.locator("#btnReadShift").tap()
                time.sleep(3)
            snap("after_read")

            n0 = len(reqs)
            page.locator("#btnShiftYes").tap()
            time.sleep(2)
            yes_api = [x for x in reqs[n0:] if x[0] == "POST" and "confirm-shift-figures" in x[1]]
            snap("after_yes")

            if page.locator("#btnShiftDiffContinue").is_visible():
                page.locator("#btnShiftDiffContinue").tap()
                time.sleep(2)
            snap("esb_diff_continue")

            bank_amounts = {"BNI": (2545000, 145000), "BRI": (4465000, 1065000)}
            for bank, (edc_amt, qris_amt) in bank_amounts.items():
                btn = page.locator(f'button[data-action="add"][data-bank="{bank}"]')
                if btn.count() and btn.is_visible():
                    with page.expect_file_chooser() as fc:
                        btn.tap()
                    fc.value.set_files(PHOTO)
                    time.sleep(3)
                    edit = page.locator(f"#btnBankEdit-{bank}")
                    if edit.is_visible():
                        edit.tap()
                        time.sleep(1)
                        page.locator(f"#editEdc-{bank}").fill(str(edc_amt))
                        page.locator(f"#editQris-{bank}").fill(str(qris_amt))
                        page.locator(f"#btnBankSaveEdit-{bank}").tap()
                        time.sleep(1)
                    correct = page.locator(f"#btnBankCorrect-{bank}")
                    if correct.is_visible():
                        correct.tap()
                        time.sleep(3)
            snap("banks_done")

            page.reload(wait_until="networkidle")
            time.sleep(2)
            snap("fresh_resume_after_banks")

            page.wait_for_selector("#stepCash.on", timeout=30000)
            page.locator("#cashAmt").tap()
            page.locator("#cashAmt").fill("4400000")
            page.locator("#cashAmt").dispatch_event("input")
            page.locator("#cashWhy").fill("Petty timing")
            page.locator("#btnCashNext").tap()
            time.sleep(3)
            snap("cash_counted")

            page.locator("#btnReviewNext").tap()
            time.sleep(2)
            snap("review")

            for _ in range(10):
                btn = page.locator("#btnSubmitException")
                if btn.is_visible() and not btn.is_disabled():
                    btn.tap()
                    time.sleep(0.4)
            time.sleep(2)
            if page.locator("#resultTitle").is_visible():
                submit_results.append(page.locator("#resultTitle").inner_text())
            snap("submit_result")

            page.locator("#btnViewClose").tap()
            time.sleep(2)
            snap("view_close_readonly")
            ro = "Continue to submit" not in (out[-1].get("text") or "")

            page2 = ctx.new_page()
            page2.goto(f"{BASE}/uma-blu-close?business_date=2026-09-03", wait_until="networkidle")
            time.sleep(2)
            d3 = page2.evaluate(DUMP)
            d3["label"] = "sep03_discovery"
            out.append(d3)
            sep03_ok = "USE THIS REPORT" in (d3.get("text") or "") or "Shift report photo found" in (d3.get("text") or "")

            page.locator("#btnBackChoose").tap()
            time.sleep(2)
            snap("back_missing")

            browser.close()
    except Exception as exc:
        err = str(exc)
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        td = ROOT / "catalog" / "backups" / f"tmp-histnav-probe-{TAG}"
        if td.exists():
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    proof = {
        "steps": out,
        "submit_results": submit_results,
        "error": err,
        "checks": {
            "photo_only_first": check_no_figures and check_no_diff,
            "yes_api": len(yes_api) >= 1 or any(s.get("label") == "after_yes" and "Figures confirmed" in str(s.get("top")) for s in out),
            "view_close_readonly": ro,
            "sep03_discovery": sep03_ok,
        },
    }
    out_path = ROOT / "state/reliability/UMA-CLOSE-6STEP-REBUILD-2-HARNESS-2026-10-05.json"
    out_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2))
    ok = all(proof["checks"].values()) and submit_results and "EXCEPTION" in submit_results[0]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
