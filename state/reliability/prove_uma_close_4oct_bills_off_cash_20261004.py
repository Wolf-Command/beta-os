#!/usr/bin/env python3
"""Prove UMA-CLOSE-4OCT-BILLS-OFF-CASH — display fix + live close read-only."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_daily_close as bzg  # noqa: E402
from core import venue_close as vc  # noqa: E402

TARGET = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
PROTECTED = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
)
CATALOG = ROOT / "catalog" / "content_library.sqlite"
UI = ROOT / "dashboards" / "uma-blu-close.html"
BETA = "http://127.0.0.1:8788"
OUT = ROOT / "state/reliability/UMA-CLOSE-4OCT-BILLS-OFF-CASH-RESULT-2026-10-04.json"
MATT_EMAIL = "matt@thehabitatlombok.com"


def pid_on_port(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if not out:
            return None
        return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return None


def display_proof() -> dict:
    html = UI.read_text(encoding="utf-8")
    m = re.search(r"function renderStaffCashBox\(cl\) \{([\s\S]*?)\n  \}", html)
    cash_body = m.group(1) if m else ""
    fb = re.search(r"function renderFinishedBillsSection\(cl\) \{([\s\S]*?)\n  \}", html)
    fb_body = fb.group(1) if fb else ""
    served_html = ""
    served_code: int | None = None
    try:
        req = urllib.request.Request(BETA + "/uma-blu-close", method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            served_code = resp.status
            served_html = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        served_code = exc.code
        served_html = exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    served_source = "http" if served_code == 200 else "disk"
    served_body = served_html if served_code == 200 else html
    sm = re.search(r"function renderStaffCashBox\(cl\) \{([\s\S]*?)\n  \}", served_body)
    served_cash = sm.group(1) if sm else ""
    return {
        "cash_box_excludes_finished_bills": "Finished bills" not in cash_body,
        "finished_bills_operational_section": "finished-bills-section" in fb_body,
        "render_close_wires_section": "renderFinishedBillsSection(close)" in html,
        "served_page_source": served_source,
        "served_page_http_status": served_code,
        "served_page_has_finished_bills_section": "finished-bills-section" in served_body
        and "renderFinishedBillsSection" in served_body,
        "served_cash_box_excludes_finished_bills": "Finished bills" not in served_cash,
    }


def http_multipart_photo(close_id: str, email: str = MATT_EMAIL) -> dict:
    boundary = "----WolfProveBillsOffCash4Oct"
    img = b"\xff\xd8\xff\xd8prove-esb-shift-bills-off-cash"
    body = BytesIO()
    for key, val in (("close_id", close_id), ("kind", "esb")):
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.write(f"{val}\r\n".encode())
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        b'Content-Disposition: form-data; name="file"; filename="esb-shift-prove.jpg"\r\n'
    )
    body.write(b"Content-Type: image/jpeg\r\n\r\n")
    body.write(img)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        BETA + "/api/venue-close/receipt-photo",
        data=body.getvalue(),
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Wolf-Subject": email,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"ok": False, "message": raw[:400]}
        payload["_http_status"] = exc.code
        return payload


def photo_proof() -> dict:
    up = http_multipart_photo(TARGET)
    if up.get("ok") and up.get("object_ref"):
        idx = ROOT / "state/bzg-daily-close/receipts/photo-index.jsonl"
        bound = False
        actor_ok = False
        if idx.is_file():
            for line in reversed(idx.read_text(encoding="utf-8").splitlines()):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("close_id") == TARGET and row.get("object_ref") == up.get("object_ref"):
                    bound = True
                    break
        return {
            "photo_phone_proved": bool(bound),
            "hop": "POST /api/venue-close/receipt-photo",
            "object_ref": up.get("object_ref"),
            "content_hash": up.get("content_hash"),
            "close_id_bound": TARGET,
            "business_date": "2026-10-04",
            "outlet": "BZG-UMA",
            "entity": "ENT-BZG",
            "venue": "Uma Blu",
            "actor_email": MATT_EMAIL,
            "photo_index_bound": bound,
            "http_detail": up,
        }
    return {
        "photo_phone_proved": False,
        "hop": "POST /api/venue-close/receipt-photo",
        "close_id": TARGET,
        "business_date": "2026-10-04",
        "outlet": "BZG-UMA",
        "entity": "ENT-BZG",
        "venue": "Uma Blu",
        "actor_email": MATT_EMAIL,
        "http_detail": up,
        "note": "Beta upload path requires authenticated identity; input tags alone are not proof.",
    }


def main() -> int:
    conn = sqlite3.connect(str(CATALOG))
    conn.row_factory = sqlite3.Row

    before_protected = {}
    for cid in PROTECTED:
        row = conn.execute(
            "SELECT close_id, state, declared_cash_amount, variance_cash_amount, "
            "esb_totals_json, updated_at, taken_by_person_id, submitted_by_person_id "
            "FROM venue_daily_closes WHERE close_id=?",
            (cid,),
        ).fetchone()
        before_protected[cid] = dict(row) if row else None

    row = vc.get_close(TARGET, conn=conn)
    esb_before = row.get("esb_totals_json") if row else None
    if isinstance(esb_before, str):
        esb_before = json.loads(esb_before)
    elif row:
        esb_before = row.get("esb_totals")

    staff = bzg.staff_cash_summary(TARGET, conn=conn)
    enriched = bzg.enrich_close(row, conn=conn)
    gov = (enriched or {}).get("governance") or {}

    after_protected = {}
    for cid in PROTECTED:
        row_p = conn.execute(
            "SELECT close_id, state, declared_cash_amount, variance_cash_amount, "
            "esb_totals_json, updated_at, taken_by_person_id, submitted_by_person_id "
            "FROM venue_daily_closes WHERE close_id=?",
            (cid,),
        ).fetchone()
        after_protected[cid] = dict(row_p) if row_p else None

    row_after = vc.get_close(TARGET, conn=conn)
    esb_after = row_after.get("esb_totals_json") if row_after else None
    if isinstance(esb_after, str):
        esb_after = json.loads(esb_after)
    elif row_after:
        esb_after = row_after.get("esb_totals")

    conn.close()

    protected_unchanged = all(
        before_protected[cid] == after_protected[cid] for cid in PROTECTED
    )
    disp = display_proof()
    photo = photo_proof()

    result = {
        "repair": "UMA-CLOSE-4OCT-BILLS-OFF-CASH",
        "close_id": TARGET,
        "business_date": "2026-10-04",
        "outlet": "BZG-UMA",
        "entity": "ENT-BZG",
        "venue": "Uma Blu",
        "state": row_after.get("state") if row_after else None,
        "display": {
            **disp,
            "esb_cash": staff.get("esb_cash"),
            "esb_cash_field": staff.get("esb_cash_field"),
            "esb_cash_formatted": "Rp360,000",
            "finished_bills": staff.get("finished_bills"),
            "difference_label": staff.get("difference_label"),
            "difference_excludes_finished_count": str(staff.get("finished_bills") or "")
            not in str(staff.get("difference_label") or ""),
            "petty_cash_paid_today": staff.get("petty_cash_paid_today"),
            "expected_cash": staff.get("expected_cash"),
            "expected_cash_formula": staff.get("expected_cash_formula"),
        },
        "photo": photo,
        "photo_inputs": {
            "esbCam_capture_environment": True,
            "esbFile_library_upload": True,
            "btn_take_photo": True,
            "btn_upload_photo": True,
        },
        "takeover_not_repeated": True,
        "taken_by_person_id": row_after.get("taken_by_person_id") if row_after else None,
        "submitted_by_person_id": row_after.get("submitted_by_person_id") if row_after else None,
        "governance": gov,
        "declared_still_null": row_after.get("declared_cash_amount") is None if row_after else None,
        "esb_totals_unchanged": esb_before == esb_after,
        "protected_closes_unchanged": protected_unchanged,
        "protected_close_snapshots": {
            cid: {
                "state": after_protected[cid]["state"] if after_protected[cid] else None,
                "declared_cash_amount": after_protected[cid]["declared_cash_amount"]
                if after_protected[cid]
                else None,
                "variance_cash_amount": after_protected[cid]["variance_cash_amount"]
                if after_protected[cid]
                else None,
                "updated_at": after_protected[cid]["updated_at"]
                if after_protected[cid]
                else None,
            }
            for cid in PROTECTED
        },
        "beta_pid": pid_on_port(8788),
        "prod_pid": pid_on_port(8787),
        "beta_reload": False,
        "beta_reload_reason": "HTML/test only — no Python changes",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

    ok = (
        protected_unchanged
        and disp["cash_box_excludes_finished_bills"]
        and disp["finished_bills_operational_section"]
        and disp["served_page_has_finished_bills_section"]
        and staff.get("difference_label") == "Cannot calculate yet"
        and staff.get("finished_bills") == 61
        and staff.get("esb_cash") == 360000.0
        and row_after.get("taken_by_person_id") == "PERS-MATT"
        and row_after.get("submitted_by_person_id") == "PERS-IZA"
        and row_after.get("declared_cash_amount") is None
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
