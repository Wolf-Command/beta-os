#!/usr/bin/env python3
"""Playwright iPhone 14 proof for UMA-CLOSE-6STEP-REBUILD-1 on probe server."""
from __future__ import annotations

import json
import sys
import time
from playwright.sync_api import sync_playwright

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
BASE = f"http://127.0.0.1:{PORT}"
EMAIL = "mrwolf@wolfcommand.net"
PHOTO = "/Users/wolfterminal/hist-close-nav-work/test-shift-report-PEACHES-TEST.png"

DUMP = """() => {
  const s = document.querySelector('.step-screen.on');
  const vis = e => e && e.offsetParent !== null;
  return {
    screen: s && s.id,
    top: [...document.querySelectorAll('.top-msg.on,.msg')].filter(vis).map(e => e.innerText),
    buttons: [...(s || document).querySelectorAll('button')].filter(vis).map(b => b.id + ':' + b.innerText.trim() + (b.disabled ? '(disabled)' : '')),
    text: (s ? s.innerText : '').replace(/\\n+/g, ' | ').slice(0, 900)
  };
}"""


def main() -> int:
    out: list[dict] = []
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
        page.goto(f"{BASE}/uma-blu-close?business_date=2026-09-29", wait_until="networkidle")
        time.sleep(2)

        def snap(label: str) -> None:
            time.sleep(1.5)
            d = page.evaluate(DUMP)
            d["label"] = label
            out.append(d)

        snap("opened_29sep_shift")

        if page.locator("#btnShiftYes").is_visible():
            page.locator("#btnShiftYes").tap()
            time.sleep(1.5)
        snap("shift_yes")

        if page.locator("#btnShiftDiffContinue").is_visible():
            page.locator("#btnShiftDiffContinue").tap()
            time.sleep(2)
        snap("esb_diff_continue")

        for bank in ("BNI", "BRI"):
            btn = page.locator(f'button[data-bank="{bank}"]')
            if btn.count():
                btn.scroll_into_view_if_needed()
                if btn.is_visible():
                    btn.tap()
                time.sleep(1)
                with page.expect_file_chooser() as fc:
                    page.locator("#btnBankTake").tap()
                fc.value.set_files(PHOTO)
                time.sleep(3)
                if page.locator("#btnBankCorrect").is_visible():
                    page.locator("#btnBankCorrect").tap()
                    time.sleep(4)
                else:
                    snap(f"bank_{bank}_no_correct")
                    break
        snap("banks_done")

        page.wait_for_selector("#stepCash.on", timeout=20000)
        snap("cash_step")
        page.locator("#cashAmt").tap()
        page.locator("#cashAmt").fill("3790000")
        page.locator("#cashAmt").dispatch_event("change")
        time.sleep(3)
        snap("cash_counted")

        if page.locator("#btnCashNext").is_visible():
            page.locator("#btnCashNext").tap()
        if page.locator("#btnReviewNext").is_visible():
            page.locator("#btnReviewNext").tap()
        snap("review")

        submit_results = []
        for _ in range(3):
            if page.locator("#btnSubmitException").is_visible() and not page.locator("#btnSubmitException").is_disabled():
                page.locator("#btnSubmitException").tap()
            elif page.locator("#btnSubmit").is_visible() and not page.locator("#btnSubmit").is_disabled():
                page.locator("#btnSubmit").tap()
            time.sleep(2)
            if page.locator("#stepResult.on").count():
                submit_results.append(page.locator("#resultTitle").inner_text())
        snap("submit_result")

        page2 = ctx.new_page()
        page2.goto(f"{BASE}/uma-blu-close?business_date=2026-09-29", wait_until="networkidle")
        time.sleep(2)
        d = page2.evaluate(DUMP)
        d["label"] = "fresh_resume"
        out.append(d)
        browser.close()

    proof = {"steps": out, "submit_results": submit_results}
    print(json.dumps(proof, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
