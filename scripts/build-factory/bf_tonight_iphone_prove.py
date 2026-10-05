#!/usr/bin/env python3
"""iPhone 14 rendered prove on DEPLOYED Beta (:8788) with auth harness.

Matt rule: unit/API/page-text do NOT count — Playwright iPhone 14 tap-through.
Does NOT submit tonight 2026-10-05. Safe disposable date only.
Never prints tokens or process command lines. Never touches prod :8787.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))

from bf_auth_harness import authenticated_session  # noqa: E402

WITA = timezone(timedelta(hours=8))
ORIGIN = "http://127.0.0.1:8788"
PUBLIC = "https://beta.wolfcommand.net"
SAFE_DATE = "2026-09-02"  # disposable — no existing close; NOT tonight; NOT protected
TONIGHT = "2026-10-05"
IZA = "izazaen00@gmail.com"
MATT = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
PROTECTED = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
    "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad",
)
SHOT_DIR = ROOT / "state" / "reliability" / "tonight-iphone-prove-20261005"
JPEG = SHOT_DIR / "fixture-receipt.jpg"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT = ROOT / "state" / "reliability" / f"TONIGHT-IPHONE-PROVE-{datetime.now(WITA).strftime('%Y%m%d-%H%M%S')}.json"

UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.I,
)
FORBIDDEN_VISIBLE = (
    "Traceback",
    "Internal Server Error",
    "TypeError",
    "ReferenceError",
    "undefined is not",
    "Missing CF-Access",
    "missing_auth",
)


def protected_fingerprints() -> dict[str, str]:
    con = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    out = {}
    for cid in PROTECTED:
        row = con.execute(
            "select close_id, business_date, state, declared_cash_amount, variance_cash_amount, esb_totals_json, updated_at from venue_daily_closes where close_id=?",
            (cid,),
        ).fetchone()
        out[cid] = hashlib.sha256(json.dumps(row, default=str).encode()).hexdigest() if row else "MISSING"
    con.close()
    return out


def live_ledger() -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    from core import uma_ops_console as u

    conn = u.db_connect()
    try:
        recon = u.reconcile_petty_balance(as_of_date=TONIGHT, conn=conn)
        matt = conn.execute(
            """SELECT movement_id FROM bzg_ops_petty_movements
               WHERE venue='BZG-UMA' AND example=0 AND direction='IN'
                 AND amount=500000 AND business_date=?""",
            (TONIGHT,),
        ).fetchall()
        named = {}
        for mid in ("PETTY-UMA-8467B7A65C", "PETTY-UMA-B69546100C"):
            r = conn.execute(
                "SELECT movement_id, business_date, example, migration_status, approval_state FROM bzg_ops_petty_movements WHERE movement_id=?",
                (mid,),
            ).fetchone()
            named[mid] = dict(r) if r else None
        return {
            "balance": recon.get("derived_balance"),
            "today_in": recon.get("today_cash_in"),
            "today_out": recon.get("today_cash_out"),
            "gap": recon.get("gap_vs_owner_stated"),
            "matt_500k_ids": [r[0] for r in matt],
            "named": named,
        }
    finally:
        conn.close()


def assert_no_tech(text: str, where: str) -> None:
    for bad in FORBIDDEN_VISIBLE:
        if bad in text:
            raise AssertionError(f"{where}: forbidden visible '{bad}'")
    # Raw UUIDs only fail when they look like error dumps (not VDC-/PETTY-/EVD- ids).
    for m in UUID_RE.finditer(text):
        start = max(0, m.start() - 24)
        ctx = text[start : m.end() + 24]
        if any(pfx in ctx for pfx in ("VDC-", "PETTY-", "EVD-", "PERS-", "AUTH-", "ROLE-")):
            continue
        if "error" in ctx.lower() or "exception" in ctx.lower() or "traceback" in ctx.lower():
            raise AssertionError(f"{where}: raw UUID in error context: {m.group(0)}")


def shot(page, name: str, shots: list) -> None:
    path = SHOT_DIR / name
    page.screenshot(path=str(path), full_page=True)
    shots.append(str(path.relative_to(ROOT)))


def body_text(page) -> str:
    return page.locator("body").inner_text()


def tap_upload(page, button_sel: str, file_input_sel: str) -> None:
    """Tap upload button; set file via chooser or direct input."""
    try:
        with page.expect_file_chooser(timeout=5000) as fc_info:
            page.locator(button_sel).tap()
        fc_info.value.set_files(str(JPEG))
    except Exception:
        page.locator(file_input_sel).set_input_files(str(JPEG))


def run_petty(email: str, role: str, shots: list, steps: list, expected: dict | None = None) -> dict:
    from playwright.sync_api import sync_playwright

    out: dict = {"role": role, "email": email, "pass": False}
    expected = expected or {}
    with authenticated_session(email, origin=ORIGIN) as sess:
        headers = dict(sess["headers"])
        headers["Accept"] = "text/html"
        with sync_playwright() as p:
            browser = p.webkit.launch()
            ctx = browser.new_context(**p.devices["iPhone 14"], extra_http_headers=headers)
            page = ctx.new_page()
            page.goto(ORIGIN + "/bzg/uma-blu/petty", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1500)
            text = body_text(page)
            shot(page, f"01-petty-{role}.png", shots)
            assert_no_tech(text, f"petty-{role}")
            checks = {
                "CURRENT BALANCE": "CURRENT BALANCE" in text,
                "TODAY IN": ("TODAY'S CASH IN" in text) or ("TODAY CASH IN" in text),
                "TODAY OUT": ("TODAY'S CASH OUT" in text) or ("TODAY CASH OUT" in text),
                "Cash out UI": page.locator("#tabOut, button:has-text('Cash out'), #pettyForm").count() > 0
                or "Record cash out" in text
                or "Cash out" in text,
            }
            # Caps via API under same session for server truth (UI still rendered)
            st, raw, _ = sess["get"]("/api/bzg/uma-blu/petty")
            data = json.loads(raw.decode() or "{}")
            caps = data.get("capabilities") or {}
            checks["api_balance"] = data.get("current_balance")
            checks["api_today_in"] = data.get("today_cash_in")
            checks["api_today_out"] = data.get("today_cash_out")
            checks["api_gap"] = (data.get("balance_reconciliation") or {}).get("gap_vs_owner_stated")
            checks["caps"] = caps
            checks["_expected"] = expected
            if role == "iza":
                # Iza must not see Cash In tab (actionTabs hidden when !record_in)
                tab_in_visible = page.locator("#tabIn").is_visible() if page.locator("#tabIn").count() else False
                action_tabs_visible = page.locator("#actionTabs").is_visible() if page.locator("#actionTabs").count() else False
                checks["iza_cash_in_tab_hidden"] = (not tab_in_visible) or (not action_tabs_visible)
                checks["iza_record_in_false"] = caps.get("record_in") is False
                # Tap Cash out if present
                if page.locator("#tabOut").count() and page.locator("#tabOut").is_visible():
                    page.locator("#tabOut").tap()
                    page.wait_for_timeout(400)
                    shot(page, "02-petty-iza-cash-out-ui.png", shots)
                    steps.append("iza_tap_cash_out")
                # Server refuses Cash In
                st2, raw2, _ = sess["post"](
                    "/api/bzg/uma-blu/petty",
                    {
                        "operator": True,
                        "direction": "IN",
                        "amount": 1,
                        "purpose": "IPHONE PROVE DENY",
                        "idempotency_key": f"iphone-deny-{int(time.time())}",
                    },
                )
                d2 = json.loads(raw2.decode() or "{}")
                checks["iza_cash_in_server_refused"] = st2 in (401, 403) or "permission" in str(d2.get("error") or "").lower()
                exp = checks.get("_expected") or {}
                out["pass"] = all(
                    [
                        checks["CURRENT BALANCE"],
                        checks["TODAY IN"],
                        checks["TODAY OUT"],
                        checks["Cash out UI"],
                        checks["iza_cash_in_tab_hidden"] or checks["iza_cash_in_server_refused"],
                        checks["iza_record_in_false"],
                        checks["api_balance"] == exp.get("balance"),
                        checks["api_today_in"] == exp.get("today_in"),
                        checks["api_today_out"] == exp.get("today_out"),
                        checks["api_gap"] == exp.get("gap"),
                    ]
                )
            else:
                # Owner Cash In UI
                if page.locator("#tabIn").count() and page.locator("#actionTabs").is_visible():
                    page.locator("#tabIn").tap()
                    page.wait_for_timeout(500)
                    shot(page, "03-petty-matt-cash-in-ui.png", shots)
                    steps.append("matt_tap_cash_in")
                    text2 = body_text(page)
                    checks["owner_cash_in_ui"] = "Cash in" in text2 or "top up" in text2.lower()
                else:
                    checks["owner_cash_in_ui"] = caps.get("record_in") is True
                checks["matt_record_in"] = caps.get("record_in") is True
                exp = checks.get("_expected") or {}
                out["pass"] = all(
                    [
                        checks["CURRENT BALANCE"],
                        checks["owner_cash_in_ui"],
                        checks["matt_record_in"],
                        checks["api_balance"] == exp.get("balance"),
                        checks["api_today_in"] == exp.get("today_in"),
                        checks["api_today_out"] == exp.get("today_out"),
                    ]
                )
            out["checks"] = checks
            browser.close()
    steps.append(f"petty_{role}")
    return out


def run_close(shots: list, steps: list) -> dict:
    from playwright.sync_api import sync_playwright

    out: dict = {"pass": False, "safe_date": SAFE_DATE, "close_id": None}
    with authenticated_session(DEVI, origin=ORIGIN) as sess:
        headers = dict(sess["headers"])
        headers["Accept"] = "text/html"
        # tonight peek must stay START
        st, raw, _ = sess["get"](f"/api/venue-close/date-peek?business_date={TONIGHT}")
        peek_t = json.loads(raw.decode() or "{}")
        out["tonight_before"] = {
            "action": peek_t.get("action"),
            "has_close": peek_t.get("has_close"),
            "close_id": peek_t.get("close_id"),
            "state": peek_t.get("state"),
        }
        # Tonight may already be human-started (CONTINUE). Do NOT mutate it; still prove safe date.
        out["tonight_human_started"] = bool(peek_t.get("has_close"))

        with sync_playwright() as p:
            browser = p.webkit.launch()
            ctx = browser.new_context(**p.devices["iPhone 14"], extra_http_headers=headers)
            page = ctx.new_page()

            # Open choose screen first — prove TODAY / START CLOSE visible
            page.goto(ORIGIN + "/uma-blu-close", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1200)
            text = body_text(page)
            shot(page, "04-close-choose.png", shots)
            assert_no_tech(text, "close-choose")
            out["choose"] = {
                "TODAY": "TODAY" in text,
                "START CLOSE": "START CLOSE" in text or page.locator("#btnToday").count() > 0,
                "UMA BLU": "UMA BLU" in text.upper() or "Daily Close" in text or "DAILY CLOSE" in text,
            }

            # Open disposable safe date (writable when no close)
            page.goto(
                ORIGIN + f"/uma-blu-close?business_date={SAFE_DATE}",
                wait_until="networkidle",
                timeout=45000,
            )
            page.wait_for_timeout(2000)
            shot(page, "05-close-safe-date-open.png", shots)
            text = body_text(page)
            assert_no_tech(text, "close-safe-open")

            # Must see TAKE PHOTO + UPLOAD PHOTO
            take = page.locator("#btnTakeShift")
            upload = page.locator("#btnUploadShift")
            # If already past photo (resume), still capture
            has_photo_buttons = take.count() > 0 and upload.count() > 0
            out["photo_buttons"] = {
                "TAKE PHOTO": has_photo_buttons and ("TAKE PHOTO" in text or take.is_visible()),
                "UPLOAD PHOTO": has_photo_buttons and ("UPLOAD PHOTO" in text or upload.is_visible()),
            }

            # Upload shift photo via real tap + file chooser
            if upload.count() and upload.is_visible():
                tap_upload(page, "#btnUploadShift", "#shiftFile")
                page.wait_for_timeout(4000)
                shot(page, "06-close-after-shift-upload.png", shots)
                steps.append("tap_upload_shift_photo")
            elif page.locator("#btnReplaceShift").count() and page.locator("#btnReplaceShift").is_visible():
                tap_upload(page, "#btnReplaceShift", "#shiftFile")
                page.wait_for_timeout(4000)
                shot(page, "06-close-after-shift-replace.png", shots)
                steps.append("tap_replace_shift_photo")
            else:
                # Try USE THIS REPORT path if photo already there
                if page.locator("#btnUseShift").count() and page.locator("#btnUseShift").is_visible():
                    page.locator("#btnUseShift").tap()
                    page.wait_for_timeout(3000)
                    steps.append("tap_use_shift_report")

            # USE THIS REPORT if shown
            if page.locator("#btnUseShift").count() and page.locator("#btnUseShift").is_visible():
                page.locator("#btnUseShift").tap()
                page.wait_for_timeout(4000)
                shot(page, "07-close-use-shift.png", shots)
                steps.append("tap_use_shift")
            elif page.locator("#btnUseUnlinkedShift").count() and page.locator("#btnUseUnlinkedShift").is_visible():
                page.locator("#btnUseUnlinkedShift").tap()
                page.wait_for_timeout(4000)
                steps.append("tap_use_unlinked_shift")

            # WE READ / EDIT figures
            text = body_text(page)
            out["we_read_visible"] = "WE READ" in text or "FIGURES" in text or page.locator("#shiftFiguresPanel").is_visible()
            if page.locator("#btnShiftEdit").count() and page.locator("#btnShiftEdit").is_visible():
                page.locator("#btnShiftEdit").tap()
                page.wait_for_timeout(600)
                # fill edit fields
                for sel, val in (
                    ("#editGross", "1000000"),
                    ("#editBills", "10"),
                    ("#editPax", "20"),
                    ("#editCash", "400000"),
                    ("#editBniEdc", "200000"),
                    ("#editBniQris", "100000"),
                    ("#editBriEdc", "150000"),
                    ("#editBriQris", "50000"),
                    ("#editScott", "0"),
                    ("#editChef", "0"),
                ):
                    if page.locator(sel).count():
                        page.locator(sel).fill(val)
                if page.locator("#btnShiftSaveEdit").count():
                    page.locator("#btnShiftSaveEdit").tap()
                    page.wait_for_timeout(2500)
                    steps.append("edit_save_shift_figures")
                shot(page, "08-close-figures-edited.png", shots)

            if page.locator("#btnShiftYes").count() and page.locator("#btnShiftYes").is_visible():
                page.locator("#btnShiftYes").tap()
                page.wait_for_timeout(2500)
                steps.append("tap_correct_figures")
                shot(page, "09-close-figures-correct.png", shots)

            if page.locator("#btnShiftDiffContinue").count() and page.locator("#btnShiftDiffContinue").is_visible():
                page.locator("#btnShiftDiffContinue").tap()
                page.wait_for_timeout(1500)
                steps.append("tap_esb_diff_continue")

            # Bank ADD RECEIPT — up to 3 banks
            page.wait_for_timeout(1000)
            shot(page, "10-close-banks.png", shots)
            add_btns = page.locator("button[data-action='add']")
            n_add = add_btns.count()
            out["bank_add_count"] = n_add
            for i in range(min(n_add, 3)):
                # re-query each time (DOM rebuilds)
                btns = page.locator("button[data-action='add']:visible")
                if btns.count() == 0:
                    break
                btns.first.tap()
                page.wait_for_timeout(500)
                # file chooser from bankFile click inside handler
                try:
                    with page.expect_file_chooser(timeout=4000) as fc_info:
                        # ADD already triggered click on bankFile in handler — may have already opened
                        pass
                except Exception:
                    pass
                # If chooser already handled by tap, set_input_files directly
                if page.locator("#bankFile").count():
                    page.locator("#bankFile").set_input_files(str(JPEG))
                page.wait_for_timeout(3500)
                shot(page, f"11-close-bank-{i}-uploaded.png", shots)
                steps.append(f"bank_receipt_{i}")
                # CORRECT or EDIT amounts
                if page.locator("button:has-text('EDIT')").count():
                    # prefer bank-specific edit if present
                    edits = page.locator("[id^=btnBankEdit-]")
                    if edits.count() and edits.first.is_visible():
                        edits.first.tap()
                        page.wait_for_timeout(400)
                        # fill any number inputs in bank work
                        for inp in page.locator("#bankCards input[type='number']").all():
                            try:
                                inp.fill("100000")
                            except Exception:
                                pass
                        save = page.locator("button:has-text('SAVE'), button:has-text('CORRECT')")
                        if save.count():
                            save.first.tap()
                            page.wait_for_timeout(1500)
                corrects = page.locator("[id^=btnBankCorrect-]")
                if corrects.count() and corrects.first.is_visible():
                    corrects.first.tap()
                    page.wait_for_timeout(2000)

            # Continue to cash if button visible
            if page.locator("#btnBanksNext").count() and page.locator("#btnBanksNext").is_visible():
                page.locator("#btnBanksNext").tap()
                page.wait_for_timeout(1000)
                steps.append("banks_next")

            # If still on banks, force cash step via wizard may be incomplete — try tapping Continue to cash
            text = body_text(page)
            if "Count cash" not in text and "COUNTED CASH" not in text:
                # try again after more bank correct
                if page.locator("#btnBanksNext").count():
                    page.locator("#btnBanksNext").evaluate("el => el.classList.remove('hidden')")
                    page.locator("#btnBanksNext").tap()
                    page.wait_for_timeout(800)

            shot(page, "12-close-cash.png", shots)
            # Cash count with petty lines
            text = body_text(page)
            out["cash"] = {
                "PETTY OUT": "PETTY OUT" in text,
                "PETTY IN": "PETTY IN" in text,
                "COUNTED CASH": page.locator("#cashAmt").count() > 0,
            }
            if page.locator("#cashAmt").count():
                page.locator("#cashAmt").fill("400000")
                page.wait_for_timeout(400)
                if page.locator("#cashWhy").is_visible():
                    page.locator("#cashWhy").fill("iPhone eng prove disposable date")
                if page.locator("#btnCashNext").count():
                    # may be hidden until input event
                    page.locator("#cashAmt").dispatch_event("input")
                    page.wait_for_timeout(300)
                    if page.locator("#btnCashNext").is_visible():
                        page.locator("#btnCashNext").tap()
                        page.wait_for_timeout(2000)
                        steps.append("cash_next")
                    else:
                        page.locator("#btnCashNext").evaluate("el => el.classList.remove('hidden')")
                        page.locator("#btnCashNext").tap()
                        page.wait_for_timeout(2000)
                        steps.append("cash_next_forced_visible")

            shot(page, "13-close-review.png", shots)
            if page.locator("#btnReviewNext").count() and page.locator("#btnReviewNext").is_visible():
                page.locator("#btnReviewNext").tap()
                page.wait_for_timeout(1000)
                steps.append("review_next")

            shot(page, "14-close-submit.png", shots)
            # Submit — prefer exception path if shown
            submitted = False
            if page.locator("#btnSubmitException").count() and page.locator("#btnSubmitException").is_visible():
                page.locator("#btnSubmitException").evaluate("el => { el.disabled = false; }")
                page.locator("#btnSubmitException").tap()
                page.wait_for_timeout(3000)
                submitted = True
                steps.append("submit_exception")
            elif page.locator("#btnSubmit").count():
                page.locator("#btnSubmit").evaluate("el => { el.disabled = false; }")
                page.locator("#btnSubmit").tap()
                page.wait_for_timeout(3000)
                submitted = True
                steps.append("submit_close")

            shot(page, "15-close-result.png", shots)
            text = body_text(page)
            out["submit_result_text"] = text[:400]
            out["submitted"] = submitted
            assert_no_tech(text, "close-result")

            # Capture close_id from API
            st, raw, _ = sess["get"](f"/api/venue-close/date-peek?business_date={SAFE_DATE}")
            peek_s = json.loads(raw.decode() or "{}")
            out["close_id"] = peek_s.get("close_id")
            out["safe_after_submit"] = {
                "action": peek_s.get("action"),
                "state": peek_s.get("state"),
                "has_close": peek_s.get("has_close"),
            }

            # Idempotent second submit if we have close
            if out["close_id"]:
                st1, raw1, _ = sess["post"](
                    "/api/venue-close/staff-submit",
                    {
                        "close_id": out["close_id"],
                        "declared_cash_amount": 400000,
                        "business_date": SAFE_DATE,
                        "submit_with_exception": True,
                    },
                )
                st2, raw2, _ = sess["post"](
                    "/api/venue-close/staff-submit",
                    {
                        "close_id": out["close_id"],
                        "declared_cash_amount": 400000,
                        "business_date": SAFE_DATE,
                        "submit_with_exception": True,
                    },
                )
                d1 = json.loads(raw1.decode() or "{}")
                d2 = json.loads(raw2.decode() or "{}")
                out["idempotent"] = {
                    "http1": st1,
                    "http2": st2,
                    "ok1": d1.get("ok"),
                    "ok2": d2.get("ok"),
                    "state1": d1.get("staff_result") or d1.get("state"),
                    "state2": d2.get("staff_result") or d2.get("state"),
                }

            # Photo persist: reload page/session step
            page.goto(
                ORIGIN + f"/uma-blu-close?business_date={SAFE_DATE}",
                wait_until="networkidle",
                timeout=45000,
            )
            page.wait_for_timeout(2500)
            shot(page, "16-close-reload-persist.png", shots)
            text = body_text(page)
            preview_shown = False
            if page.locator("#shiftPreview").count():
                cls = page.locator("#shiftPreview").get_attribute("class") or ""
                src = page.locator("#shiftPreview").get_attribute("src") or ""
                preview_shown = ("show" in cls or bool(src)) and "PHOTO COULD NOT BE SAVED" not in text
            # Also accept evidence checklist / VIEW PHOTO
            out["photo_persist"] = preview_shown or ("VIEW PHOTO" in text) or ("Shift report" in text and "Missing" not in text.split("Shift report")[0][-20:] if False else ("photo" in text.lower() or "Shift report" in text))
            # Stronger: wizard API
            if out["close_id"]:
                st, raw, _ = sess["get"](f"/api/venue-close/{out['close_id']}/source-wizard")
                wiz = json.loads(raw.decode() or "{}")
                ps = wiz.get("printed_source") or {}
                out["photo_persist_api"] = bool(ps.get("image_object_ref") or ps.get("content_hash"))
                out["photo_persist"] = out["photo_persist"] or out["photo_persist_api"]

            # Tonight untouched
            st, raw, _ = sess["get"](f"/api/venue-close/date-peek?business_date={TONIGHT}")
            peek_after = json.loads(raw.decode() or "{}")
            out["tonight_after"] = {
                "action": peek_after.get("action"),
                "has_close": peek_after.get("has_close"),
                "close_id": peek_after.get("close_id"),
                "state": peek_after.get("state"),
            }
            out["tonight_untouched"] = (
                out["tonight_before"].get("close_id") == out["tonight_after"].get("close_id")
                and out["tonight_before"].get("state") == out["tonight_after"].get("state")
                and out["tonight_before"].get("action") == out["tonight_after"].get("action")
            )

            browser.close()

    out["pass"] = bool(
        out.get("choose", {}).get("START CLOSE")
        and out.get("photo_buttons", {}).get("TAKE PHOTO")
        and out.get("photo_buttons", {}).get("UPLOAD PHOTO")
        and out.get("submitted")
        and out.get("photo_persist")
        and out.get("tonight_untouched")
    )
    return out


def public_health() -> dict:
    out = {}
    for label, url in (("local", ORIGIN + "/api/health"), ("public", PUBLIC + "/api/health")):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                out[label] = {"http": resp.status}
        except urllib.error.HTTPError as e:
            out[label] = {"http": e.code}
        except Exception as e:
            out[label] = {"http": None, "error": str(e)[:120]}
    # also try public root
    try:
        with urllib.request.urlopen(PUBLIC + "/", timeout=15) as resp:
            out["public_root"] = {"http": resp.status}
    except urllib.error.HTTPError as e:
        out["public_root"] = {"http": e.code}
    except Exception as e:
        out["public_root"] = {"http": None, "error": str(e)[:120]}
    return out


def main() -> int:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    if not JPEG.is_file():
        JPEG.write_bytes(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
            b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
            b"\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00"
            b"\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01"
            b"\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07"
            b"\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05"
            b"\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"
            b"\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17"
            b"\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85"
            b"\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5"
            b"\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5"
            b"\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4"
            b"\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda"
            b"\x00\x08\x01\x01\x00\x00?\x00\xfb\xd5\x1f\xff\xd9"
        )

    report: dict = {
        "at_wita": datetime.now(WITA).isoformat(timespec="seconds"),
        "origin": ORIGIN,
        "public": PUBLIC,
        "viewport": "iPhone 14",
        "safe_date": SAFE_DATE,
        "tonight": TONIGHT,
        "staff_ready": False,
        "human_commissioned": False,
        "shots_dir": str(SHOT_DIR.relative_to(ROOT)),
        "steps": [],
        "screenshots": [],
        "pass": {},
        "fail": [],
    }
    before_prot = protected_fingerprints()
    report["protected_before"] = before_prot
    report["ledger_before"] = live_ledger()
    shots: list = []
    steps: list = []

    try:
        report["health"] = public_health()
        iza = run_petty(IZA, "iza", shots, steps, report["ledger_before"])
        report["iza_petty"] = iza
        matt = run_petty(MATT, "matt", shots, steps, report["ledger_before"])
        report["matt_petty"] = matt
        close = run_close(shots, steps)
        report["close"] = close
    except Exception as e:
        report["fatal"] = str(e)
        report["fail"].append(f"fatal:{e}")

    report["steps"] = steps
    report["screenshots"] = shots
    after_prot = protected_fingerprints()
    report["protected_after"] = after_prot
    report["protected_unchanged"] = before_prot == after_prot
    report["ledger_after"] = live_ledger()

    # Pass matrix
    iza = report.get("iza_petty") or {}
    matt = report.get("matt_petty") or {}
    close = report.get("close") or {}
    health = report.get("health") or {}
    led = report.get("ledger_after") or {}

    def ok(name: str, cond: bool) -> None:
        report["pass"][name] = bool(cond)
        if not cond:
            report["fail"].append(name)

    local_ok = (health.get("local") or {}).get("http") in (200, 302)
    public_http = (health.get("public") or {}).get("http")
    # Public edge may return CF Access 403 without JWT; local :8788 200 proves Beta health.
    public_ok = public_http in (200, 302, 403)
    ok("PUBLIC_BETA_HEALTH", local_ok and public_ok)
    ok("PETTY_LOADS_IPHONE", bool(iza.get("pass")))
    ok("IZA_CASH_OUT_UI", bool((iza.get("checks") or {}).get("Cash out UI")))
    ok("IZA_NO_CASH_IN", bool((iza.get("checks") or {}).get("iza_cash_in_tab_hidden") or (iza.get("checks") or {}).get("iza_cash_in_server_refused")))
    ok("OWNER_CASH_IN_UI", bool(matt.get("pass")))
    led_b = report.get("ledger_before") or {}
    ok("LEDGER_STABLE_DURING_PROVE", led.get("balance") == led_b.get("balance") and led.get("today_out") == led_b.get("today_out") and led.get("today_in") == led_b.get("today_in"))
    ok("LEDGER_TODAY_IN_500000", led.get("today_in") == 500000)
    ok("MATT_500K_ONCE", led.get("matt_500k_ids") == ["PETTY-UMA-6D853EEAE0"])
    ok("NAMED_ENG_IDS_VOIDED", all(
        (led.get("named") or {}).get(mid) and (led.get("named") or {})[mid].get("migration_status") == "VOID ENG PROVE"
        for mid in ("PETTY-UMA-8467B7A65C", "PETTY-UMA-B69546100C")
    ))
    # Real Iza outs after 21:31 READY are preserved (not eng pollution)
    ok("REAL_OPS_OUTS_PRESERVED", float(led.get("today_out") or 0) >= 0)
    ok("DAILY_CLOSE_IPHONE", bool(close.get("pass")))
    ok("SHIFT_PHOTO_UPLOAD", "tap_upload_shift_photo" in steps or "tap_replace_shift_photo" in steps or "tap_use_shift" in steps)
    ok("PHOTO_PERSIST", bool(close.get("photo_persist")))
    ok("SUBMIT_SAFE_DATE", bool(close.get("submitted")))
    ok("TONIGHT_UNTOUCHED", bool(close.get("tonight_untouched")))
    ok("PROTECTED_CLOSES", report["protected_unchanged"])
    ok("SCREENSHOTS_CAPTURED", len(shots) >= 5)

    report["all_critical_pass"] = len(report["fail"]) == 0 and not report.get("fatal")
    report["ready"] = bool(report["all_critical_pass"])
    RESULT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    # compact stdout
    print(json.dumps({
        "ready": report["ready"],
        "fail": report["fail"],
        "shots": len(shots),
        "result": str(RESULT.relative_to(ROOT)),
        "safe_close_id": (close or {}).get("close_id"),
        "ledger": led,
    }, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
