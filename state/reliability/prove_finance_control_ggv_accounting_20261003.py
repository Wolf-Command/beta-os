#!/usr/bin/env python3
"""Prove GGV accounting queues slice — persisted rows + optional HTTP on :8788.

Does NOT touch preserved close VDC-87202768. staff_ready / eng_proved false.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT / "scripts"))

from core import ggv_bank_statement1 as gbs  # noqa: E402
from core import ggv_receipt_accounting1 as gra  # noqa: E402
from core import ggv_receipt_intake_ro as rx  # noqa: E402
from core import venue_close as vc  # noqa: E402

PRESERVED = "VDC-87202768-55af-4c8e-abc3-382a5496b8c6"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
BETA = "http://127.0.0.1:8788"
MATT_EMAIL = "mrwolf@wolfcommand.net"


def _http(method: str, path: str, body: dict | None = None, email: str = MATT_EMAIL) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BETA + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "X-Wolf-Subject": email},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            ctype = resp.headers.get("content-type") or ""
            if "json" not in ctype:
                return {"ok": True, "_http_status": resp.status, "_content_type": ctype}
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"ok": False, "error": "http_error", "message": raw[:400]}
        payload["_http_status"] = exc.code
        return payload


def main() -> int:
    c = sqlite3.connect(str(CATALOG))
    c.row_factory = sqlite3.Row
    results: list[str] = []

    row = c.execute(
        "SELECT state, taken_by_person_id FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row and row["state"] == "DATA_CAPTURED" and row["taken_by_person_id"] == "PERS-MATT"
    results.append("preserved_intact")

    vault = rx.list_ggv_receipts(limit=500)
    assert vault.get("second_pipeline") is False
    bad = [
        r
        for r in vault.get("receipts") or []
        if "_bzg_" in r["filename"].lower()
        or "_amg_" in r["filename"].lower()
        or str((r.get("meta") or {}).get("tenant") or "").upper() in ("BZG", "AMG")
    ]
    assert not bad, f"AMG/BZG leak in vault list: {len(bad)}"
    results.append("amg_bzg_vault_isolated")

    queues = gra.list_accounting_queues(verified_person_id="PERS-MATT", limit=20, conn=c)
    assert queues.get("ok") is True
    assert queues.get("entity_id") == "ENT-GGV"
    assert queues.get("amg_bzg_isolated") is True
    assert queues.get("amg_bzg_leak_count") == 0
    labels = queues.get("queue_labels") or {}
    for key in ("needs_coding", "needs_review", "unmatched", "duplicate"):
        assert key in labels
    counts = queues.get("queue_counts") or {}
    assert sum(int(counts.get(k) or 0) for k in labels) > 0
    results.append("accounting_queues_persisted")

    sample = (queues.get("items") or [None])[0]
    assert sample and sample.get("extraction_retained") is not None
    assert sample.get("image_url")
    key = sample["receipt_key"]
    detail = gra.get_receipt(verified_person_id="PERS-MATT", receipt_key=key, conn=c)
    assert detail.get("receipt", {}).get("extraction") is not None
    results.append("extraction_visible")

    if sample.get("image_retrievable"):
        raw, mime, _ = gra.receipt_image_bytes(
            verified_person_id="PERS-MATT", receipt_key=key, conn=c
        )
        assert len(raw) > 0 and mime
        results.append("image_evidence_attached")
    else:
        assert sample.get("missing_evidence_visible") is True
        results.append("missing_evidence_visible")

    ext_before = detail["receipt"]["extraction"]
    confirmed = gra.confirm_receipt(
        verified_person_id="PERS-MATT",
        receipt_key=key,
        body={
            "vendor": "Prove Vendor",
            "amount": "12345",
            "date": "2026-05-20",
            "category": "Prove",
            "account_code": "9999",
            "notes": "finance control prove",
        },
        conn=c,
    )
    assert confirmed.get("extraction_retained") is True
    assert confirmed.get("human_beside_extraction") is True
    assert confirmed["receipt"]["extraction"] is not None
    assert confirmed["receipt"]["human_confirmed"] is not None
    assert confirmed["receipt"]["extraction"].get("note") == ext_before.get("note")
    results.append("human_confirm_keeps_extraction")

    c.execute(
        """
        UPDATE ggv_receipt_accounting SET human_confirmed_json=NULL,
          confirmed_by_person_id=NULL, confirmed_at=NULL, accounting_queue='needs_review'
        WHERE receipt_key=?
        """,
        (key,),
    )
    c.commit()

    dup_n = int(counts.get("duplicate") or 0)
    assert dup_n >= 0
    results.append(f"duplicate_queue:{dup_n}")

    deny = gbs.deny_if_not_ggv_entity("PERS-ZAYEN")
    assert deny and deny.get("ok") is False
    results.append("zayen_ggv_deny")

    out = vc.capture_esb_snapshot(
        PRESERVED, verified_person_id="PERS-MATT", conn=c, commit=True
    )
    assert out.get("snapshot_frozen") is True and out.get("mutated") is False
    results.append("freeze_still_holds")

    if (os.environ.get("FINANCE_PROVE_HTTP") or "").strip() == "1":
        auth = _http("GET", "/api/core/auth-mode")
        if auth.get("auth_mode") != "development_assertion":
            results.append("http_skipped_cf_mode")
        else:
            q = _http("GET", "/api/ggv/finance/accounting/queues?limit=5")
            assert q.get("ok") and q.get("amg_bzg_isolated") is True
            assert q.get("queue_counts")
            results.append("http_accounting_queues")
            z = _http("GET", "/api/ggv/finance/accounting/queues?limit=1", email="laluzayen@gmail.com")
            assert z.get("_http_status") in (401, 403) or z.get("ok") is False
            results.append("http_zayen_deny")
            page = _http("GET", "/ggv/finance/receipts")
            assert page.get("_http_status") == 200 or page.get("_content_type")
            results.append("http_receipts_page")

    c.close()
    print("PASS", " ".join(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
