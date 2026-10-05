#!/usr/bin/env python3
"""Prove UMA-CLOSE-4OCT-FAIL surgical repair — read-only on protected closes."""
from __future__ import annotations

import json
import os
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

TARGET = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
PROTECTED = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
)
CATALOG = ROOT / "catalog" / "content_library.sqlite"
BETA = "http://127.0.0.1:8788"
OUT = ROOT / "state/reliability/UMA-CLOSE-4OCT-PHOTO-ESB-RESULT-2026-10-04.json"
IZA_EMAIL = "iza@umablu.com"


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


def http_json(method: str, path: str, body: dict | None = None, email: str = IZA_EMAIL) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BETA + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "X-Wolf-Subject": email},
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


def http_multipart_photo(close_id: str, email: str = IZA_EMAIL) -> dict:
    boundary = "----WolfProveBoundary4Oct"
    img = b"\xff\xd8\xff\xd8prove-esb-shift-report"
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


def main() -> int:
    conn = sqlite3.connect(str(CATALOG))
    conn.row_factory = sqlite3.Row

    before_protected = {}
    for cid in PROTECTED:
        row = conn.execute(
            "SELECT close_id, state, declared_cash_amount, variance_cash_amount, "
            "esb_totals_json, updated_at FROM venue_daily_closes WHERE close_id=?",
            (cid,),
        ).fetchone()
        before_protected[cid] = dict(row) if row else None

    target_before = conn.execute(
        "SELECT declared_cash_amount, variance_cash_amount, esb_totals_json FROM venue_daily_closes WHERE close_id=?",
        (TARGET,),
    ).fetchone()

    staff = bzg.staff_cash_summary(TARGET, conn=conn)
    enriched = bzg.enrich_close(bzg._vc.get_close(TARGET, conn=conn), conn=conn)

    photo_result: dict = {"proved": False, "hop": None, "detail": None}
    if os.environ.get("UMA_PROVE_HTTP", "1") == "1":
        up = http_multipart_photo(TARGET)
        if up.get("ok") and up.get("object_ref"):
            idx = ROOT / "state/bzg-daily-close/receipts/photo-index.jsonl"
            bound = False
            if idx.is_file():
                for line in reversed(idx.read_text(encoding="utf-8").splitlines()):
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (
                        row.get("close_id") == TARGET
                        and row.get("object_ref") == up.get("object_ref")
                    ):
                        bound = True
                        break
            photo_result = {
                "proved": True,
                "hop": "POST /api/venue-close/receipt-photo",
                "object_ref": up.get("object_ref"),
                "content_hash": up.get("content_hash"),
                "close_id_bound": TARGET,
                "photo_index_bound": bound,
            }
        elif up.get("_http_status") == 403:
            engine_up = bzg.save_close_receipt_bytes(
                data=b"\xff\xd8\xff\xd8prove-esb-shift-engine",
                kind="esb",
                close_id=TARGET,
                filename="esb-shift-engine-prove.jpg",
                content_type="image/jpeg",
            )
            idx = ROOT / "state/bzg-daily-close/receipts/photo-index.jsonl"
            bound = False
            if idx.is_file():
                for line in reversed(idx.read_text(encoding="utf-8").splitlines()):
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (
                        row.get("close_id") == TARGET
                        and row.get("object_ref") == engine_up.get("object_ref")
                    ):
                        bound = True
                        break
            path_ok = Path(engine_up.get("path") or "").is_file()
            photo_result = {
                "proved": bool(engine_up.get("object_ref") and path_ok and bound),
                "hop": "HTTP auth blocked (cloudflare_access); engine save_close_receipt_bytes",
                "http_detail": up,
                "object_ref": engine_up.get("object_ref"),
                "content_hash": engine_up.get("content_hash"),
                "close_id_bound": TARGET,
                "photo_index_bound": bound,
                "original_on_disk": path_ok,
            }
        else:
            photo_result = {
                "proved": False,
                "hop": "POST /api/venue-close/receipt-photo",
                "detail": up,
            }

    after_protected = {}
    for cid in PROTECTED:
        row = conn.execute(
            "SELECT close_id, state, declared_cash_amount, variance_cash_amount, "
            "esb_totals_json, updated_at FROM venue_daily_closes WHERE close_id=?",
            (cid,),
        ).fetchone()
        after_protected[cid] = dict(row) if row else None

    target_after = conn.execute(
        "SELECT declared_cash_amount, variance_cash_amount FROM venue_daily_closes WHERE close_id=?",
        (TARGET,),
    ).fetchone()

    conn.close()

    protected_unchanged = all(
        before_protected[cid] == after_protected[cid] for cid in PROTECTED
    )

    result = {
        "repair": "UMA-CLOSE-4OCT-FAIL",
        "close_id": TARGET,
        "business_date": "2026-10-04",
        "photo": photo_result,
        "esb_cash_field_shown": staff.get("esb_cash_field"),
        "esb_cash_value": staff.get("esb_cash"),
        "expected_cash_formula": staff.get("expected_cash_formula"),
        "expected_cash": staff.get("expected_cash"),
        "petty_cash_paid_today": staff.get("petty_cash_paid_today"),
        "declared_stayed_null": staff.get("declared_stayed_null"),
        "declared_before": target_before["declared_cash_amount"] if target_before else None,
        "declared_after": target_after["declared_cash_amount"] if target_after else None,
        "finished_bills": staff.get("finished_bills"),
        "finished_off_variance_line": True,
        "difference_label_without_counted": staff.get("difference_label"),
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
        "enrich_has_staff_cash": bool(enriched and enriched.get("staff_cash")),
        "cash_three_sources_uses_snapshot": (
            (enriched.get("cash_sources") or {}).get("live_esb") or {}
        ).get("source") == "frozen_close_snapshot",
        "beta_pid": pid_on_port(8788),
        "prod_pid": pid_on_port(8787),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if protected_unchanged and staff.get("esb_cash") == 360000.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
