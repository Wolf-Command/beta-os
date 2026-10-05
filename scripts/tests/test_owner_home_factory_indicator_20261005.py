#!/usr/bin/env python3
"""OWNER-HOME-FACTORY-INDICATOR — read-only factory line on Owner cockpit."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import owner_cockpit as cockpit  # noqa: E402
from core import owner_factory_indicator_ro as fi  # noqa: E402

BETA = "http://127.0.0.1:8788"
LIVE_DISPATCH = ROOT / "state" / "build-factory" / "GOD-MODE-DISPATCH.json"

FIXTURE_QUEUE = {
    "staff_ready": False,
    "human_commissioned": False,
    "last_completion_at": "2026-10-04T22:00:00Z",
    "last_autonomous_dispatch_at": "2026-10-04T22:05:00Z",
    "items": [
        {"id": "A", "state": "READY", "priority": 1},
        {"id": "B", "state": "RUNNING", "priority": 2, "cursor_pid": 99999999},
        {"id": "C", "state": "BLOCKED", "priority": 3},
        {"id": "D", "state": "READY FOR HUMAN TEST", "priority": 4},
        {"id": "E", "state": "READY FOR HUMAN TEST", "priority": 5},
    ],
}

EMPTY_QUEUE = {
    "staff_ready": False,
    "human_commissioned": False,
    "items": [],
}


def _http_status(url: str) -> int | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except OSError:
        return None


class OwnerHomeFactoryIndicatorTest(unittest.TestCase):
    def test_fixture_projects_six_facts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dpath = Path(td) / "GOD-MODE-DISPATCH.json"
            lpath = Path(td) / "WRITER.lock"
            dpath.write_text(json.dumps(FIXTURE_QUEUE), encoding="utf-8")
            lpath.write_text(
                json.dumps({"state": "RUNNING", "cursor_pid": 99999999}),
                encoding="utf-8",
            )
            out = fi.load_factory_indicator(dispatch_file=dpath, lock_file=lpath)
            self.assertTrue(out["ok"])
            self.assertEqual(out["ready_queue_count"], 1)
            self.assertEqual(out["blocked_count"], 1)
            self.assertEqual(out["ready_for_human_test_count"], 2)
            self.assertEqual(out["last_completion_at"], "2026-10-04T22:00:00Z")
            self.assertEqual(out["last_autonomous_dispatch_at"], "2026-10-04T22:05:00Z")
            self.assertIn("active_workers", out)
            self.assertFalse(out["staff_ready"])
            self.assertFalse(out["human_commissioned"])
            self.assertFalse(out["eng_proved"])

    def test_empty_queue_honest_idle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dpath = Path(td) / "GOD-MODE-DISPATCH.json"
            dpath.write_text(json.dumps(EMPTY_QUEUE), encoding="utf-8")
            out = fi.load_factory_indicator(dispatch_file=dpath, lock_file=Path(td) / "missing.lock")
            self.assertEqual(out["active_workers"], 0)
            self.assertEqual(out["ready_queue_count"], 0)
            self.assertEqual(out["blocked_count"], 0)
            self.assertEqual(out["ready_for_human_test_count"], 0)
            self.assertIsNone(out["last_completion_at"])
            self.assertIsNone(out["last_autonomous_dispatch_at"])
            self.assertIn("none yet", out["line"])

    def test_does_not_mutate_dispatch_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dpath = Path(td) / "GOD-MODE-DISPATCH.json"
            dpath.write_text(json.dumps(FIXTURE_QUEUE), encoding="utf-8")
            before = dpath.read_text(encoding="utf-8")
            before_mtime = dpath.stat().st_mtime_ns
            fi.load_factory_indicator(dispatch_file=dpath)
            after = dpath.read_text(encoding="utf-8")
            after_mtime = dpath.stat().st_mtime_ns
            self.assertEqual(before, after)
            self.assertEqual(before_mtime, after_mtime)

    def test_live_dispatch_untouched_by_loader(self) -> None:
        if not LIVE_DISPATCH.is_file():
            self.skipTest("live dispatch missing")
        before = LIVE_DISPATCH.stat().st_mtime_ns
        fi.load_factory_indicator()
        after = LIVE_DISPATCH.stat().st_mtime_ns
        self.assertEqual(before, after)

    def test_no_purchasing_or_payment_side_effects(self) -> None:
        catalog = ROOT / "catalog" / "content_library.sqlite"
        if not catalog.is_file():
            self.skipTest("catalog missing")
        before = catalog.stat().st_mtime_ns
        data = cockpit.load_cockpit()
        after = catalog.stat().st_mtime_ns
        self.assertEqual(before, after)
        indicator = data.get("factory_indicator") or {}
        self.assertNotIn("payment", json.dumps(indicator).lower())
        self.assertNotIn("bzg_ops", json.dumps(indicator).lower())

    def test_cockpit_includes_factory_indicator(self) -> None:
        data = cockpit.load_cockpit()
        indicator = data.get("factory_indicator") or {}
        self.assertTrue(indicator.get("ok") or indicator.get("line"))
        self.assertFalse(data.get("staff_ready"))
        self.assertIn("active_workers", indicator)
        self.assertIn("ready_queue_count", indicator)

    def test_cockpit_write_still_refused(self) -> None:
        refused = cockpit.refuse_write()
        self.assertFalse(refused.get("ok"))
        self.assertFalse(refused.get("writes"))
        self.assertFalse(refused.get("staff_ready"))

    def test_owner_home_auth_pattern_unchanged(self) -> None:
        """Cockpit JSON stays pre-JWT read; /wolf stays owner-only."""
        st_cockpit = _http_status(f"{BETA}/api/owner/cockpit")
        if st_cockpit is None:
            self.skipTest("beta :8788 not reachable")
        self.assertEqual(st_cockpit, 200, "cockpit JSON remains readable pre-JWT wall")
        st_wolf = _http_status(f"{BETA}/wolf")
        self.assertEqual(st_wolf, 403, "Owner Home /wolf stays owner-only without JWT")


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


def smoke_owner_cockpit_pack1() -> None:
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "tests" / "test_owner_cockpit_pack1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    check("owner_cockpit_pack1 smoke", proc.returncode == 0, proc.stdout[-400:] + proc.stderr[-400:])


def main() -> int:
    global PASS, FAIL
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(OwnerHomeFactoryIndicatorTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    PASS += result.testsRun - len(result.failures) - len(result.errors)
    FAIL += len(result.failures) + len(result.errors)
    smoke_owner_cockpit_pack1()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
