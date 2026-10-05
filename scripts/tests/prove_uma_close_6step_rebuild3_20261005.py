#!/usr/bin/env python3
"""Playwright iPhone 14 proof for UMA-CLOSE-6STEP-REBUILD-3."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path("/Users/wolfterminal/beta-os")
PROBE = Path("/Users/wolfterminal/hist-close-nav-work/probe_server.py")
PHOTO = "/Users/wolfterminal/hist-close-nav-work/test-shift-report-PEACHES-TEST.png"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
TAG = sys.argv[2] if len(sys.argv) > 2 else "6step-rebuild3-wolf"
EMAIL = "mrwolf@wolfcommand.net"
BASE = f"http://127.0.0.1:{PORT}"

LIVE_RECEIPTS = ROOT / "state" / "bzg-daily-close" / "receipts"
LIVE_PETTY = ROOT / "state" / "uma-petty-receipts"
LIVE_NOTAS = ROOT / "state" / "bzg-supplier-notas"
PHOTO_INDEX = LIVE_RECEIPTS / "photo-index.jsonl"

DUMP = """() => {
  const s = document.querySelector('.step-screen.on');
  const vis = e => e && e.offsetParent !== null;
  return {
    screen: s && s.id,
    top: [...document.querySelectorAll('.top-msg.on,.msg')].filter(vis).map(e => e.innerText),
    buttons: [...(s || document).querySelectorAll('button')].filter(vis).map(b => b.id + ':' + b.innerText.trim() + (b.disabled ? '(disabled)' : '')),
    text: (s ? s.innerText : '').replace(/\\n+/g, ' | ').slice(0, 1400)
  };
}"""


def dir_snapshot(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_dir():
        return out
    for f in sorted(path.iterdir()):
        if f.is_file():
            out[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def main() -> int:
    evroot = Path(tempfile.mkdtemp(prefix="tmp-evroot-rb3-"))
    before_receipts = dir_snapshot(LIVE_RECEIPTS)
    before_petty = dir_snapshot(LIVE_PETTY)
    before_notas = dir_snapshot(LIVE_NOTAS)
    idx_before = hashlib.sha256(PHOTO_INDEX.read_bytes()).hexdigest() if PHOTO_INDEX.is_file() else ""

    env = {
        **dict(os.environ),
        "WOLF_CLOSE_VISION_DRY": "1",
        "BETA_LLM_DRY_RUN": "1",
        "WOLF_EVIDENCE_ROOT": str(evroot),
        "WOLF_TEST_MODE": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, str(PROBE), str(PORT), TAG],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(3)
    out: list[dict] = []
    submit_posts: list = []
    yes_blocked = False
    sep03_slips = 0
    view_close_ok = False
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
                time.sleep(1.2)
                d = page.evaluate(DUMP)
                d["label"] = label
                out.append(d)

            # 29 Sep walkthrough
            page.goto(f"{BASE}/uma-blu-close?business_date=2026-09-29", wait_until="networkidle")
            time.sleep(2)
            snap("29_open")

            with page.expect_file_chooser() as fc:
                page.locator("#btnUploadShift").tap()
            fc.value.set_files(PHOTO)
            time.sleep(3)
            snap("29_upload")

            page.reload(wait_until="networkidle")
            time.sleep(2)
            if page.locator("#btnUseShift, #btnUseUnlinkedShift").count():
                use_btn = page.locator("#btnUseShift, #btnUseUnlinkedShift").first
                if use_btn.is_visible():
                    use_btn.tap()
                    time.sleep(3)
            snap("29_read")

            page.locator("#btnShiftYes").tap()
            time.sleep(4)
            snap("29_yes")

            if page.locator("#btnShiftDiffContinue").is_visible():
                page.locator("#btnShiftDiffContinue").tap()
                time.sleep(3)
            snap("29_banks")

            for bank, (edc_amt, qris_amt) in {"BNI": (2545000, 145000), "BRI": (4465000, 1065000)}.items():
                btn = page.locator(f'button[data-action="add"][data-bank="{bank}"]')
                if btn.count() and btn.is_visible():
                    with page.expect_file_chooser() as fc:
                        btn.tap()
                    fc.value.set_files(PHOTO)
                    time.sleep(3)
                    edit = page.locator(f"#btnBankEdit-{bank}")
                    if edit.is_visible():
                        edit.tap()
                        time.sleep(0.8)
                        page.locator(f"#editEdc-{bank}").fill(str(edc_amt))
                        page.locator(f"#editQris-{bank}").fill(str(qris_amt))
                        page.locator(f"#btnBankSaveEdit-{bank}").tap()
                        time.sleep(0.8)
                    correct = page.locator(f"#btnBankCorrect-{bank}")
                    if correct.is_visible():
                        correct.tap()
                        time.sleep(2.5)

            page.wait_for_selector("#stepCash.on", timeout=30000)
            page.locator("#cashAmt").tap()
            page.locator("#cashAmt").fill("4400000")
            page.locator("#cashWhy").fill("Petty timing")
            page.locator("#btnCashNext").tap()
            time.sleep(2)
            snap("29_cash")

            page.locator("#btnReviewNext").tap()
            time.sleep(2)
            snap("29_review")

            page.wait_for_selector("#stepSubmit.on", timeout=15000)
            n0 = len(reqs)
            for _ in range(10):
                if page.locator("#btnSubmitException").is_visible():
                    page.locator("#btnSubmitException").tap()
                    time.sleep(0.3)
            submit_posts = [x for x in reqs[n0:] if x[0] == "POST" and "staff-submit" in x[1]]
            snap("29_result")

            if page.locator("#btnViewClose").is_visible():
                page.locator("#btnViewClose").tap()
                time.sleep(2)
                snap("29_view_close")
                view_close_ok = (
                    page.locator("#stepViewClose.on").count() > 0
                    and page.locator("#btnViewCloseBack").is_visible()
                    and not page.locator("#btnBackCash").is_visible()
                )
                page.locator("#btnViewCloseBack").tap()
                time.sleep(1)

            # 3 Sep empty read → YES blocked → EDIT
            page.goto(f"{BASE}/uma-blu-close?business_date=2026-09-03", wait_until="networkidle")
            time.sleep(2)
            snap("03_open")

            if page.locator("#btnUseUnlinkedShift").is_visible():
                page.locator("#btnUseUnlinkedShift").tap()
                time.sleep(4)
            snap("03_empty_read")

            page.locator("#btnShiftYes").tap()
            time.sleep(2)
            yes_blocked = "Nothing read" in (page.locator("#msg").inner_text() or "")
            snap("03_yes_blocked")

            if page.locator("#btnShiftDiffContinue").is_visible():
                page.locator("#btnShiftDiffContinue").tap()
                time.sleep(2)
            sep03_slips = page.locator("[data-action='use-slip']").count()

            if page.locator("#btnShiftEdit").is_visible():
                page.locator("#btnShiftEdit").tap()
                time.sleep(1)
                page.locator("#editGross").fill("5000000")
                page.locator("#editCash").fill("1000000")
                page.locator("#editBills").fill("30")
                page.locator("#editPax").fill("50")
                page.locator("#editBniEdc").fill("500000")
                page.locator("#editBriEdc").fill("600000")
                page.locator("#btnShiftSaveEdit").tap()
                time.sleep(3)
            snap("03_edited")

            page.locator("#btnShiftYes").tap()
            time.sleep(2)
            if page.locator("#btnShiftDiffContinue").is_visible():
                page.locator("#btnShiftDiffContinue").tap()
                time.sleep(2)
            snap("03_banks_slips")
            sep03_slips = max(sep03_slips, page.locator("[data-action='use-slip']").count())

            browser.close()
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    after_receipts = dir_snapshot(LIVE_RECEIPTS)
    after_petty = dir_snapshot(LIVE_PETTY)
    after_notas = dir_snapshot(LIVE_NOTAS)
    idx_after = hashlib.sha256(PHOTO_INDEX.read_bytes()).hexdigest() if PHOTO_INDEX.is_file() else ""
    zero_live = (
        before_receipts == after_receipts
        and before_petty == after_petty
        and before_notas == after_notas
        and idx_before == idx_after
    )

    result = {
        "harness_steps": out,
        "submit_post_count": len(submit_posts),
        "yes_blocked_sep03": yes_blocked,
        "sep03_slip_buttons": sep03_slips,
        "view_close_readonly": view_close_ok,
        "zero_live_writes": zero_live,
        "error": err,
    }
    out_path = ROOT / "state/reliability/UMA-CLOSE-6STEP-REBUILD-3-HARNESS-2026-10-05.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(evroot, ignore_errors=True)
    print(json.dumps(result, indent=2))
    ok = (
        zero_live
        and yes_blocked
        and sep03_slips >= 4
        and view_close_ok
        and len(submit_posts) >= 1
        and err is None
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
