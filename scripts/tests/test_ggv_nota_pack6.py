#!/usr/bin/env python3
"""Pack 6 — GGV nota capture on a catalog copy. Issue stays blocked."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["WOLF_TEST_MODE"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import canonical_guard  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import ggv_nota_pack6 as pack  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def _open_copy(path: Path):
    import sqlite3

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def main() -> int:
    canonical_guard.install()
    source = Path(pack.__file__).read_text(encoding="utf-8")
    check("issue function not called", "issue_invoice" not in source and "seed_ggv_sequence" not in source)
    check("auth mode untouched", "BETA_AUTH_MODE" not in source)

    live_before = pack.live_snapshot()
    live_mtime = fin.LIVE_CATALOG_DB.stat().st_mtime_ns
    books_before = pack.books_mtime_ns()
    counts = live_before["counts"]
    sequence = live_before["sequence"]
    seats = live_before["seats"]
    check("live notas empty", counts["ggv_notas"] == 0 and counts["ggv_uploads"] == 0, str(counts))
    check("live invoices empty", counts["ggv_invoices"] == 0 and counts["ggv_vendors"] == 0, str(counts))
    check(
        "seed not allocated",
        sequence.get("next_value") == 67
        and sequence.get("format") == "{n:03d}A"
        and sequence.get("rendered_seed") == "067A"
        and sequence.get("allocated") is False,
        str(sequence),
    )
    check("amanda GGV create", seats["amanda_nota_create"] is True and seats["amanda_nota_read"] is True)
    check("amanda AMG deny", seats["amanda_amg_board"] is False)
    check("zayen GGV deny", seats["zayen_nota_create"] is False and seats["zayen_nota_read"] is False)

    media_before = fin._MEDIA_ROOT
    copy_path = canonical_guard.backup_catalog()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "media"
            media.mkdir()
            conn = _open_copy(copy_path)
            try:
                other = pack.capture(conn, media, entity_id="ENT-AMG")
                check("AMG capture refused", other.get("error") == "entity_denied" and other.get("xero_write") is False)
                check("copy still empty after AMG", pack._counts(conn)["ggv_notas"] == 0)

                try:
                    pack.capture(conn, media, person_id=pack.ZAYEN)
                    check("zayen capture denied", False, "create succeeded")
                except fin.FinanceNotaError as exc:
                    check("zayen capture denied", exc.code == "forbidden", exc.code)
                check("copy still empty after Zayen", pack._counts(conn)["ggv_uploads"] == 0)

                saved = pack.capture(conn, media)
                nota = saved.get("nota") or {}
                check("copy capture ok", saved.get("ok") is True and saved.get("capture") == "copy", str(saved.get("error")))
                check("supplier is M-Mart", saved.get("supplier") == "M-Mart" and (nota.get("vendor") or {}).get("name") == "M-Mart")
                check("needs review", saved.get("workflow_state") == "needs_review" and nota.get("state") == "needs_review")
                check("amount not invented", saved.get("amount") is None and saved.get("amount_confirmed") is False)
                check("number not assigned", (saved.get("invoice_no") or "") == "" and saved.get("invoice_number") is None)
                check("listed on copy", saved.get("listed") == 1 and saved["counts"]["ggv_notas"] == 1)
                check(
                    "copy sequence unspent",
                    saved["sequence"]["next_value"] == 67 and saved["sequence"]["allocated"] is False,
                    str(saved.get("sequence")),
                )
                check("staff not ready", saved.get("staff_ready") is False and saved.get("human_proven") is False)
                row = conn.execute("SELECT entity_id, invoice_no, amount FROM ggv_notas").fetchone()
                check("row is GGV", row["entity_id"] == "ENT-GGV" and row["invoice_no"] in (None, "") and row["amount"] is None)

                blocked = pack.issue_lane(conn)
                after = pack._sequence(conn)
                check("issue blocked", blocked.get("error") == "issue_blocked" and blocked.get("_status") == 405)
                check("issue did not allocate", after["next_value"] == 67 and blocked.get("invoice_number") is None)
                check("xero refused", pack.refuse_xero().get("error") == "xero_write_blocked")
                slipped = list(media.rglob("*m-mart-slip.txt"))
                check(
                    "slip under temp media",
                    len(slipped) == 1
                    and slipped[0].is_relative_to(media)
                    and "Finance/GGV/Notas" in slipped[0].as_posix()
                    and "/Volumes/01-Media-Library" not in slipped[0].as_posix(),
                    str([p.as_posix() for p in slipped]),
                )
            finally:
                conn.close()
    finally:
        fin.set_media_root(media_before)
        shutil.rmtree(copy_path.parent, ignore_errors=True)

    check("media root restored", fin._MEDIA_ROOT == media_before)
    live_after = pack.live_snapshot()
    check("live rows still zero", live_after["counts"] == counts, str(live_after["counts"]))
    check("live seed still 67", live_after["sequence"]["next_value"] == 67 and live_after["sequence"]["allocated"] is False)
    check("live catalog mtime", fin.LIVE_CATALOG_DB.stat().st_mtime_ns == live_mtime)
    check("books mtime", pack.books_mtime_ns() == books_before, str(pack.books_mtime_ns()))

    try:
        pack.http("GET", "/pack6", {}, None)
        check("missing person denied", False, "no error")
    except fin.FinanceNotaError as exc:
        check("missing person denied", exc.code == "missing_auth" and exc.http_status == 403, exc.code)

    try:
        pack.http("GET", "/api/ggv/finance/pack6", {}, pack.ZAYEN)
        check("zayen live read denied", False, "no error")
    except fin.FinanceNotaError as exc:
        check("zayen live read denied", exc.code == "forbidden", exc.code)

    view = fin.dispatch("GET", "/api/ggv/finance/pack6", {}, {}, pack.AMANDA)
    check("route wired", view.get("pack") == "PACK-06" and view.get("live_notas") == 0 and view.get("capture") == "not_run_on_live")
    check("live view seed labeled", (view.get("sequence") or {}).get("rendered_seed") == "067A" and view.get("invoice_number") is None)
    check("phone residual open", "phone commission" in (view.get("phone_commission") or "") and view.get("human_proven") is False)

    refused = fin.dispatch("POST", "/api/ggv/finance/pack6/capture", {}, {}, pack.AMANDA)
    check("live capture refused", refused.get("error") == "live_capture_refused" and refused.get("_status") == 405)
    issued = fin.dispatch("POST", "/api/ggv/finance/pack6/issue", {}, {}, pack.AMANDA)
    check("http issue blocked", issued.get("error") == "issue_blocked" and issued.get("allocated") is False)
    xero = fin.dispatch("POST", "/api/ggv/finance/pack6/xero", {}, {}, pack.AMANDA)
    check("http xero blocked", xero.get("error") == "xero_write_blocked" and xero.get("xero_write") is False)
    check("live still empty after http", pack.live_snapshot()["counts"]["ggv_notas"] == 0)
    check("live seed after http", pack.live_snapshot()["sequence"]["next_value"] == 67)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
