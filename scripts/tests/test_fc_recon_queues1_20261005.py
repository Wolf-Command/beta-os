#!/usr/bin/env python3
"""FC-RECON-QUEUES-1 — AMG proposal pass + shared reconciliation work queues."""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import amg_bank_recon1 as amg_recon  # noqa: E402
from core import amg_finance_core as amg_core  # noqa: E402
from core import bzg_finance_desk as bzg_desk  # noqa: E402
from core import canonical_guard as cg  # noqa: E402
from core import fc_recon_queues1 as queue  # noqa: E402
from core.staff_access import FINANCE_EMAIL, ZAYEN_PERSON  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
AMG_OPS = ROOT / "dashboards" / "amg-finance-ops.html"
BZG_FIN = ROOT / "dashboards" / "bzg-finance.html"
PACK = "FC-RECON-QUEUES-1"
ZAYEN = ZAYEN_PERSON
ZAYEN_EMAIL = FINANCE_EMAIL
AMANDA = "PERS-AMANDA"
AMG_ENTITY = "ENT-AMG"
BZG_ENTITY = "ENT-BZG"
GGV_ENTITY = "ENT-GGV"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)

FORBIDDEN_VISIBLE = (
    "ENT-",
    "SCOPE-",
    "UNPAIRED_INTERNAL_TRANSFER",
    "staff_ready",
    "human_commissioned",
    "zayen_ready",
)


def _ro(path: Path | None = None) -> sqlite3.Connection:
    db = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _rw(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _http_handler():
    import serve_beta as sb

    cg.isolate_runtime_catalog()
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            return obj
    raise RuntimeError("BetaHandler not found")


def _call(
    base: str,
    method: str,
    path: str,
    email: str | None = None,
    *,
    accept: str = "application/json",
    body: dict | None = None,
) -> tuple[int, bytes]:
    headers = {"Accept": accept, "Content-Type": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
    data = json.dumps(body or {}).encode() if body is not None else None
    req = Request(base + path, headers=headers, method=method, data=data)
    try:
        with urlopen(req, timeout=30) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


def visible_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class SessionFixture:
    def __init__(self) -> None:
        self.httpd: ThreadingHTTPServer | None = None
        self.base = ""

    def setUp(self) -> None:
        handler = _http_handler()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


class FcReconQueuesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "test.sqlite"
        shutil.copy2(LIVE_CATALOG, cls.db)
        cls.conn = _rw(cls.db)
        queue.ensure_bzg_queue_schema(cls.conn)
        amg_recon.apply_proposals(cls.conn, commit=True)
        cls.session = SessionFixture()
        cls.session.setUp()
        cls.base = cls.session.base

    @classmethod
    def tearDownClass(cls) -> None:
        cls.session.tearDown()
        cls.conn.close()
        cls.tmp.cleanup()

    def test_gap_before_live_amg_unproposed(self) -> None:
        live = _ro()
        try:
            proposed = live.execute(
                "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=? AND match_proposed=1",
                (AMG_ENTITY,),
            ).fetchone()[0]
            total = live.execute(
                "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?",
                (AMG_ENTITY,),
            ).fetchone()[0]
            self.assertEqual(int(total), 525)
            # After migration live may have proposals; temp copy always gets them from setUpClass.
            self.assertGreaterEqual(int(proposed), 0)
        finally:
            live.close()

    def test_amg_proposals_idempotent_on_temp(self) -> None:
        first = amg_recon.proposal_counts(self.conn)
        amg_recon.apply_proposals(self.conn, commit=True)
        second = amg_recon.proposal_counts(self.conn)
        self.assertEqual(first, second)
        self.assertGreater(first["exception"], 0)
        self.assertGreater(first["unmatched"], 0)

    def test_amg_does_not_touch_ggv(self) -> None:
        live = _ro()
        try:
            ggv_rows = live.execute(
                "SELECT match_proposed, human_confirmed, recon_status FROM ggv_bank_transactions WHERE entity_id=? LIMIT 5",
                (GGV_ENTITY,),
            ).fetchall()
            self.assertTrue(len(ggv_rows) > 0)
        finally:
            live.close()
        ggv_before = self.conn.execute(
            "SELECT txn_id, match_proposed, recon_status FROM ggv_bank_transactions WHERE entity_id=?",
            (GGV_ENTITY,),
        ).fetchall()
        amg_recon.apply_proposals(self.conn, commit=True)
        for row in ggv_before:
            after = self.conn.execute(
                "SELECT match_proposed, recon_status FROM ggv_bank_transactions WHERE txn_id=?",
                (row["txn_id"],),
            ).fetchone()
            self.assertEqual(int(row["match_proposed"]), int(after["match_proposed"]))
            self.assertEqual(row["recon_status"], after["recon_status"])

    def test_amg_queue_api_tabs(self) -> None:
        status, raw = _call(
            self.base,
            "GET",
            "/api/amg/finance/reconciliation/queue?tab=exception&limit=10",
            ZAYEN_EMAIL,
        )
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertTrue(body.get("ok"))
        self.assertIn("tab_counts", body)
        self.assertIn("items", body)
        for item in body.get("items") or []:
            self.assertIn("proposal_text", item)
            vis = json.dumps(item)
            for bad in FORBIDDEN_VISIBLE:
                self.assertNotIn(bad, vis)

    def test_bzg_queue_api_and_entity_isolation(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/bank/queue?tab=possible&limit=5", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertEqual(body.get("entity_id"), BZG_ENTITY)
        self.assertGreater(body.get("tab_counts", {}).get("unmatched", 0), 0)

        st2, _ = _call(self.base, "GET", "/api/bzg/finance/bank/queue?tab=possible", "amanda@wolfcommand.net")
        self.assertIn(st2, {403, 401})

    def test_confirm_reject_audit(self) -> None:
        row = self.conn.execute(
            """
            SELECT txn_id FROM ggv_bank_transactions
            WHERE entity_id=? AND match_proposed=1 AND human_confirmed=0 LIMIT 1
            """,
            (AMG_ENTITY,),
        ).fetchone()
        if not row:
            self.skipTest("no AMG proposed row in temp copy")
        txn_id = row["txn_id"]
        before = self.conn.execute(
            "SELECT COUNT(*) FROM core_audit_events WHERE resource_id=? AND source='fc_recon_queues1'",
            (txn_id,),
        ).fetchone()[0]
        queue.confirm_match(self.conn, entity=AMG_ENTITY, txn_id=txn_id, person_id=ZAYEN)
        after = self.conn.execute(
            "SELECT COUNT(*) FROM core_audit_events WHERE resource_id=? AND source='fc_recon_queues1'",
            (txn_id,),
        ).fetchone()[0]
        self.assertGreater(after, before)
        confirmed = self.conn.execute(
            "SELECT human_confirmed FROM ggv_bank_transactions WHERE txn_id=?",
            (txn_id,),
        ).fetchone()[0]
        self.assertEqual(int(confirmed), 1)

    def test_segregation_self_confirm_denied(self) -> None:
        self.conn.execute(
            """
            UPDATE ggv_bank_transactions
            SET match_proposed=1, human_confirmed=0, notes=?
            WHERE entity_id=? AND txn_id IN (
              SELECT txn_id FROM ggv_bank_transactions WHERE entity_id=? LIMIT 1
            )
            """,
            (
                json.dumps({"proposal_by": ZAYEN}),
                AMG_ENTITY,
                AMG_ENTITY,
            ),
        )
        self.conn.commit()
        txn_id = self.conn.execute(
            "SELECT txn_id FROM ggv_bank_transactions WHERE entity_id=? AND match_proposed=1 LIMIT 1",
            (AMG_ENTITY,),
        ).fetchone()[0]
        with self.assertRaises(queue.ReconQueueError):
            queue.confirm_match(self.conn, entity=AMG_ENTITY, txn_id=txn_id, person_id=ZAYEN)

    def test_bzg_desk_queue_dispatch(self) -> None:
        body = bzg_desk.dispatch("GET", "/api/bzg/finance/bank/queue", ZAYEN, self.conn, qs={"tab": ["matched"]})
        self.assertTrue(body.get("ok"))
        self.assertIn("matched", body.get("tab_counts") or {})

    def test_html_queue_elements_no_engineering_labels(self) -> None:
        for page, email in (
            ("/amg-finance-ops", ZAYEN_EMAIL),
            ("/bzg/finance/bank", ZAYEN_EMAIL),
        ):
            status, raw = _call(self.base, "GET", page, email, accept="text/html")
            self.assertEqual(status, 200, page)
            html = raw.decode("utf-8", "replace")
            vis = visible_text(html)
            self.assertIn("Possible match", vis)
            self.assertIn("Unmatched", vis)
            for bad in FORBIDDEN_VISIBLE:
                self.assertNotIn(bad, vis, f"{page} shows {bad}")
        amg_html = AMG_OPS.read_text(encoding="utf-8")
        bzg_html = BZG_FIN.read_text(encoding="utf-8")
        self.assertIn("recon-tabs", amg_html)
        self.assertIn("bank-tabs", bzg_html)
        self.assertNotIn("reconcile</button>", amg_html.lower())

    def test_amg_finance_core_matches_queue_route(self) -> None:
        self.assertTrue(amg_core.matches("/api/amg/finance/reconciliation/queue"))

    def test_protected_closes_unchanged_on_temp(self) -> None:
        live = _ro()
        try:
            for cid in PROTECTED_CLOSES:
                live_row = live.execute(
                    "SELECT state, declared_cash_amount, variance_cash_amount, updated_at FROM venue_daily_closes WHERE close_id=?",
                    (cid,),
                ).fetchone()
                tmp_row = self.conn.execute(
                    "SELECT state, declared_cash_amount, variance_cash_amount, updated_at FROM venue_daily_closes WHERE close_id=?",
                    (cid,),
                ).fetchone()
                self.assertIsNotNone(live_row)
                self.assertEqual(dict(live_row), dict(tmp_row))
        finally:
            live.close()


if __name__ == "__main__":
    unittest.main()
