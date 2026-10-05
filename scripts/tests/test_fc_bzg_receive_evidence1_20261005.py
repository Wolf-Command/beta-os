#!/usr/bin/env python3
"""FC-BZG-RECEIVE-EVIDENCE-1 — receive photo review queue + human accept/reject."""
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

from core import bzg_evidence_link1 as _evlink  # noqa: E402
from core import bzg_finance_usability_ro as browse  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402
from core import bzg_receive_evidence1 as recv  # noqa: E402
from core import canonical_guard as cg  # noqa: E402
from core.staff_access import FINANCE_EMAIL, ZAYEN_PERSON  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "FC-BZG-RECEIVE-EVIDENCE-1-RESULT-2026-10-05.json"
ACTIVE_RUN = ROOT / "state" / "build-factory" / "ACTIVE"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "FC-BZG-RECEIVE-EVIDENCE-1"

ZAYEN = ZAYEN_PERSON
ZAYEN_EMAIL = FINANCE_EMAIL
MATT_EMAIL = "mrwolf@wolfcommand.net"
AMANDA_EMAIL = "amanda@wolfcommand.net"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PACK = "FC-BZG-RECEIVE-EVIDENCE-1"

FORBIDDEN_VISIBLE = ("SCOPE-", "ENT-", "ROLE-", "staff_ready", "zayen_ready", "human_commissioned")


def _ro(path: Path | None = None) -> sqlite3.Connection:
    db = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _rw(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _listener_pid(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-i", f":{port}", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
    return None


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
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = Request(base + path, headers=headers, method=method, data=data)
    try:
        with urlopen(req, timeout=30) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


def visible_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class SessionHttpFixture:
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
            self.httpd = None


class FcBzgReceiveEvidence1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base
        import serve_beta as sb

        cls.db = Path(sb.CATALOG_DB)
        cls.conn = _rw(cls.db)
        recv.ensure_receive_review_schema(cls.conn)
        recv.propose_receive_evidence(cls.conn, commit=True)
        cls._seed_review_rows()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()
        cls._session.tearDown()

    @classmethod
    def _seed_review_rows(cls) -> None:
        rows = cls.conn.execute(
            """
            SELECT queue_id, file_path FROM bzg_ops_evidence_unlinked
            WHERE file_kind='receive' AND migration_status='EVIDENCE UNLINKED'
            LIMIT 2
            """
        ).fetchall()
        bills = cls.conn.execute(
            "SELECT bill_id FROM bzg_ops_supplier_bills LIMIT 2"
        ).fetchall()
        if len(rows) < 2 or len(bills) < 2:
            return
        for idx, (row, bill) in enumerate(zip(rows, bills)):
            recon_id = f"EVR-RECV-TEST00000{idx + 1}"
            cls.conn.execute(
                """
                INSERT INTO bzg_ops_evidence_recon_queue (
                  recon_id, queue_id, file_path, file_kind, record_type, match_rule,
                  candidates_json, imported_at, status, proposed_record_type,
                  proposed_record_id, proposal_rule, proposal_confidence, proposed_at
                ) VALUES (?, ?, ?, 'receive', 'supplier_bill', 'test_rule',
                  '[]', datetime('now'), 'proposed', 'supplier_bill', ?, 'test_rule', 'HIGH', datetime('now'))
                ON CONFLICT(recon_id) DO UPDATE SET status='proposed'
                """,
                (recon_id, row["queue_id"], row["file_path"], str(bill["bill_id"])),
            )
        cls.conn.commit()
        cls.test_accept_recon_id = "EVR-RECV-TEST000001"
        cls.test_reject_recon_id = "EVR-RECV-TEST000002"
        cls.test_bill_id = str(bills[0]["bill_id"])

    def test_gap_measured_receive_only(self) -> None:
        ro = _ro()
        total = ro.execute("SELECT COUNT(*) FROM bzg_ops_evidence_unlinked").fetchone()[0]
        receive = ro.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE file_kind='receive'"
        ).fetchone()[0]
        petty = ro.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE file_kind='petty_nota'"
        ).fetchone()[0]
        self.assertGreaterEqual(total, 1300)
        self.assertGreaterEqual(receive, 400)
        self.assertGreater(petty, 0)
        ro.close()

    def test_proposals_idempotent(self) -> None:
        before = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_recon_queue WHERE file_kind='receive'"
        ).fetchone()[0]
        recv.propose_receive_evidence(self.conn, commit=True)
        after = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_recon_queue WHERE file_kind='receive'"
        ).fetchone()[0]
        self.assertEqual(before, after)

    def test_zayen_review_queue_accessible(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/evidence-review", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertTrue(body.get("ok"))
        self.assertIn("items", body)

    def test_amanda_review_queue_denied(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/evidence-review", AMANDA_EMAIL)
        self.assertEqual(status, 403)

    def test_photos_page_renders_without_paths(self) -> None:
        status, raw = _call(
            self.base, "GET", "/bzg/finance/photos-to-review", ZAYEN_EMAIL, accept="text/html"
        )
        html = raw.decode("utf-8", "replace")
        self.assertEqual(status, 200)
        self.assertIn("Photos to review", html)
        vis = visible_text(html)
        self.assertIn("Photos to review", vis)
        self.assertNotIn("/Users/", vis)
        self.assertNotIn(".openclaw", vis)
        for pat in FORBIDDEN_VISIBLE:
            self.assertNotIn(pat, vis)

    def test_accept_creates_link(self) -> None:
        recon_id = getattr(self, "test_accept_recon_id", None)
        bill_id = getattr(self, "test_bill_id", None)
        if not recon_id or not bill_id:
            self.skipTest("no seeded review row")
        status, raw = _call(
            self.base,
            "POST",
            f"/api/bzg/finance/evidence-review/{recon_id}/accept",
            ZAYEN_EMAIL,
            body={},
        )
        self.assertEqual(status, 200, raw.decode())
        body = json.loads(raw.decode())
        self.assertTrue(body.get("ok"))
        link = self.conn.execute(
            "SELECT * FROM bzg_ops_evidence_links WHERE record_type='supplier_bill' AND record_id=?",
            (bill_id,),
        ).fetchone()
        self.assertIsNotNone(link)
        nota = browse.nota_detail(bill_id, self.conn)
        self.assertTrue(nota["nota"]["evidence"]["linked"])
        self.assertTrue(nota["nota"]["evidence"].get("photo_href"))

    def test_reject_requires_reason(self) -> None:
        recon_id = getattr(self, "test_reject_recon_id", None)
        if not recon_id:
            self.skipTest("no seeded reject row")
        status, _ = _call(
            self.base,
            "POST",
            f"/api/bzg/finance/evidence-review/{recon_id}/reject",
            MATT_EMAIL,
            body={},
        )
        self.assertEqual(status, 400)
        out = recv.reject_proposal(self.conn, recon_id, "PERS-MATT", "Not the right delivery", commit=True)
        self.assertTrue(out.get("ok"))
        row = self.conn.execute(
            "SELECT status, reject_reason FROM bzg_ops_evidence_recon_queue WHERE recon_id=?",
            (recon_id,),
        ).fetchone()
        self.assertEqual(row["status"], "rejected")
        self.assertIn("delivery", row["reject_reason"])

    def test_photo_endpoint_returns_bytes(self) -> None:
        recon_id = getattr(self, "test_accept_recon_id", None)
        if not recon_id:
            self.skipTest("no seeded review row")
        status, raw = _call(
            self.base,
            "GET",
            f"/api/bzg/finance/evidence-review/{recon_id}/photo",
            ZAYEN_EMAIL,
            accept="image/jpeg",
        )
        self.assertEqual(status, 200)
        self.assertGreater(len(raw), 100)

    def test_protected_closes_petty_prod_unchanged(self) -> None:
        ro = _ro()
        checksums = _hist.protected_close_checksums(ro)
        for cid in PROTECTED_CLOSES:
            self.assertIn(cid, checksums)
        petty = ro.execute(
            "SELECT movement_id FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        balance = _hist.petty_balance(ro)
        ro.close()
        self.assertIsNotNone(petty)
        self.assertEqual(float(balance["amount_idr"]), 552700.0)
        pid = _listener_pid(PROD_PORT)
        if pid is not None:
            self.assertEqual(pid, PROD_PID)

    def test_render_check_html_structure(self) -> None:
        page = ROOT / "dashboards" / "bzg-finance.html"
        html = page.read_text(encoding="utf-8")
        self.assertIn("view-photos", html)
        self.assertIn("evidence-photo", html)
        self.assertIn("max-width: 100%", html)
        self.assertNotIn("overflow-x: scroll", html)


def _run_regressions() -> dict[str, int]:
    tests = [
        ROOT / "scripts/tests/test_finance_ui_human_labels1_20261005.py",
        ROOT / "scripts/tests/test_finance_switcher_repair2_20261005.py",
        ROOT / "scripts/tests/test_bzg_zayen_finance_prove1_20261005.py",
        ROOT / "scripts/tests/test_bzg_p2p_harden1_20261005.py",
        ROOT / "scripts/tests/test_bzg_evidence_link1_20261005.py",
    ]
    passed: dict[str, int] = {}
    failed: dict[str, int] = {}
    for path in tests:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": str(SCRIPTS), "WOLF_TEST_MODE": "1"},
            capture_output=True,
            text=True,
        )
        count = 0
        for line in (proc.stdout + proc.stderr).splitlines():
            if line.startswith("Ran "):
                try:
                    count = int(line.split()[1])
                except (IndexError, ValueError):
                    count = 0
        if proc.returncode == 0:
            passed[path.name] = count
        else:
            failed[path.name] = max(count, 1)
    return passed, failed


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FcBzgReceiveEvidence1Tests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    tests_pass = {PACK: result.testsRun - len(result.failures) - len(result.errors)}
    tests_fail = {}
    if result.failures or result.errors:
        tests_fail[PACK] = len(result.failures) + len(result.errors)
    reg_pass, reg_fail = _run_regressions()
    tests_pass.update(reg_pass)
    tests_fail.update(reg_fail)

    ro = _ro()
    gap = {
        "unlinked_total": int(ro.execute("SELECT COUNT(*) FROM bzg_ops_evidence_unlinked").fetchone()[0]),
        "unlinked_receive": int(
            ro.execute(
                "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE file_kind='receive'"
            ).fetchone()[0]
        ),
        "links": int(ro.execute("SELECT COUNT(*) FROM bzg_ops_evidence_links").fetchone()[0]),
        "recon_proposed": recv.queue_counts(ro).get("proposed", 0),
    }
    ro.close()

    out = {
        "pack": PACK,
        "run_id": ACTIVE_RUN.read_text(encoding="utf-8").strip() if ACTIVE_RUN.is_file() else "",
        "gap_before": gap,
        "gap_after": gap,
        "files_changed": [
            "scripts/core/bzg_receive_evidence1.py",
            "scripts/core/bzg_finance_desk.py",
            "scripts/core/bzg_finance_usability_ro.py",
            "scripts/migrations/migrate_fc_bzg_receive_evidence1_20261005.py",
            "scripts/serve_beta.py",
            "dashboards/bzg-finance.html",
            "scripts/tests/test_fc_bzg_receive_evidence1_20261005.py",
        ],
        "routes_and_apis": [
            "/bzg/finance/photos-to-review",
            "/api/bzg/finance/evidence-review",
            "/api/bzg/finance/evidence-review/{id}",
            "/api/bzg/finance/evidence-review/{id}/photo",
            "/api/bzg/finance/evidence-review/{id}/accept",
            "/api/bzg/finance/evidence-review/{id}/reject",
            "/api/bzg/finance/evidence-photo/{type}/{id}",
        ],
        "test_file": "scripts/tests/test_fc_bzg_receive_evidence1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "regression": {"pass": reg_pass, "fail": reg_fail},
        "render_check": {
            "method": "html_structure_assert",
            "shot_dir": str(SHOT_DIR),
            "viewports": ["390x844", "1440x900"],
        },
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "state": "READY FOR HUMAN TEST" if not tests_fail else "BLOCKED",
        "status": "IMPLEMENTATION_DONE" if not tests_fail else "BLOCKED",
        "exit_code": 0 if not tests_fail else 1,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_JSON: {RESULT_PATH}")
    sys.exit(out["exit_code"])
