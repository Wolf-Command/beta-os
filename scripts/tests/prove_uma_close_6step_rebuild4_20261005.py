#!/usr/bin/env python3
"""Playwright iPhone 14 proof for UMA-CLOSE-6STEP-REBUILD-4."""
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
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8800
TAG = sys.argv[2] if len(sys.argv) > 2 else "6step-rebuild4-wolf"
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
    text: (s ? s.innerText : '').replace(/\\n+/g, ' | ').slice(0, 1600)
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
    evroot = Path(tempfile.mkdtemp(prefix="tmp-evroot-rb4-"))
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
    empty_read_msg = False
    sep03_banks_ok = False
    sep03_resume_banks = False
    sep03_slips = 0
    sep03_cash_ok = False
    sep03_submit_posts: list = []
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

            # 29 Sep non-regression walk
            page.goto(f"{BASE}/uma-blu-close?business_date=2026-09-29", wait_until="networkidle")
            time.sleep(2)
            snap("29_open")
            with page.expect_file_chooser() as fc:
                page.locator("#btnUploadShift").tap()
            fc.value.set_files(PHOTO)
            time.sleep(3)
            page.reload(wait_until="networkidle")
            time.sleep(2)
            if page.locator("#btnUseShift, #btnUseUnlinkedShift").count():
                page.locator("#btnUseShift, #btnUseUnlinkedShift").first.tap()
                time.sleep(3)
            snap("29_read")
            page.locator("#btnShiftYes").tap()
            time.sleep(4)
            snap("29_yes")
            if page.locator("#btnShiftDiffContinue").is_visible():
                page.locator("#btnShiftDiffContinue").tap()
                time.sleep(3)
            snap("29_banks")
            for bank, (edc_amt, qris_amt) in {
                "BNI": (2545000, 145000),
                "BRI": (4465000, 1065000),
            }.items():
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
                view_close_ok = (
                    page.locator("#stepViewClose.on").count() > 0
                    and page.locator("#btnViewCloseBack").is_visible()
                )
                page.locator("#btnViewCloseBack").tap()
                time.sleep(1)

            # 3 Sep EDIT-confirm drives banks + resume
            page.goto(f"{BASE}/uma-blu-close?business_date=2026-09-03", wait_until="networkidle")
            time.sleep(2)
            snap("03_open")
            if page.locator("#btnUseUnlinkedShift").is_visible():
                page.locator("#btnUseUnlinkedShift").tap()
                time.sleep(4)
            snap("03_after_read")
            msg = page.locator("#msg").inner_text() or ""
            empty_read_msg = "Nothing read" in msg
            page.locator("#btnShiftYes").tap()
            time.sleep(2)
            yes_blocked = "Nothing read" in (page.locator("#msg").inner_text() or "")
            snap("03_yes_blocked")
            page.locator("#btnShiftEdit").tap()
            time.sleep(1)
            page.locator("#editGross").fill("8000000")
            page.locator("#editCash").fill("3000000")
            page.locator("#editBills").fill("40")
            page.locator("#editPax").fill("80")
            page.locator("#editBniEdc").fill("2000000")
            page.locator("#editBniQris").fill("100000")
            page.locator("#editBriEdc").fill("3000000")
            page.locator("#editBriQris").fill("500000")
            page.locator("#btnShiftSaveEdit").tap()
            time.sleep(3)
            page.locator("#btnShiftYes").tap()
            time.sleep(4)
            if page.locator("#btnShiftDiffContinue").is_visible():
                page.locator("#btnShiftDiffContinue").tap()
                time.sleep(3)
            snap("03_banks")
            banks_text = page.locator("#stepBanks").inner_text()
            sep03_banks_ok = (
                "BNI" in banks_text
                and "BRI" in banks_text
                and "Rp2.000.000" in banks_text.replace(",", ".")
                and "Rp3.000.000" in banks_text.replace(",", ".")
                and "MANDIRI" in banks_text
            )
            sep03_slips = page.locator("[data-action='use-slip']").count()
            page.reload(wait_until="networkidle")
            time.sleep(3)
            snap("03_resume")
            sep03_resume_banks = page.locator("#stepBanks.on").count() > 0

            def use_slip_for_bank(bank: str, edc: int, qris: int) -> None:
                slip = page.locator("[data-action='use-slip']").first
                if not slip.is_visible():
                    return
                slip.tap()
                time.sleep(1)
                page.locator(f'[data-pick-bank="{bank}"]').tap()
                time.sleep(3)
                edit = page.locator(f"#btnBankEdit-{bank}")
                if edit.is_visible():
                    edit.tap()
                    time.sleep(0.8)
                    page.locator(f"#editEdc-{bank}").fill(str(edc))
                    page.locator(f"#editQris-{bank}").fill(str(qris))
                    page.locator(f"#btnBankSaveEdit-{bank}").tap()
                    time.sleep(0.8)
                correct = page.locator(f"#btnBankCorrect-{bank}")
                if correct.is_visible():
                    correct.tap()
                    time.sleep(2.5)

            use_slip_for_bank("BNI", 2_000_000, 100_000)
            use_slip_for_bank("BRI", 3_000_000, 500_000)
            snap("03_banks_done")
            if page.locator("#stepBanks.on").count():
                next_btn = page.locator("#btnBanksNext")
                if next_btn.is_visible():
                    next_btn.tap()
                    time.sleep(2)
            if page.locator("#stepCash.on").count() == 0:
                page.wait_for_selector("#stepCash.on", timeout=30000)
            cash_text = page.locator("#stepCash").inner_text()
            sep03_cash_ok = (
                "3.000.000" in cash_text.replace(",", ".")
                and "EXPECTED CASH" in cash_text.upper()
            )
            snap("03_cash")
            page.locator("#cashAmt").fill("3000000")
            page.locator("#btnCashNext").tap()
            time.sleep(2)
            page.locator("#btnReviewNext").tap()
            time.sleep(2)
            n1 = len(reqs)
            for _ in range(10):
                if page.locator("#btnSubmitException").is_visible():
                    page.locator("#btnSubmitException").tap()
                    time.sleep(0.3)
            sep03_submit_posts[:] = [
                x for x in reqs[n1:] if x[0] == "POST" and "staff-submit" in x[1]
            ]
            snap("03_result")
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
        "empty_read_msg": empty_read_msg,
        "sep03_banks_ok": sep03_banks_ok,
        "sep03_resume_banks": sep03_resume_banks,
        "sep03_slip_buttons": sep03_slips,
        "sep03_cash_ok": sep03_cash_ok,
        "sep03_submit_post_count": len(sep03_submit_posts),
        "view_close_readonly": view_close_ok,
        "zero_live_writes": zero_live,
        "error": err,
    }
    out_path = ROOT / "state/reliability/UMA-CLOSE-6STEP-REBUILD-4-HARNESS-2026-10-05.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(evroot, ignore_errors=True)
    print(json.dumps(result, indent=2))
    ok = (
        zero_live
        and yes_blocked
        and empty_read_msg
        and sep03_banks_ok
        and sep03_resume_banks
        and sep03_slips >= 4
        and sep03_cash_ok
        and len(sep03_submit_posts) == 1
        and view_close_ok
        and len(submit_posts) == 1
        and err is None
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
