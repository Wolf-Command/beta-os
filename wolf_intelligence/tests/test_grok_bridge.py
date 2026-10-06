"""Grok work bridge: claim/lease protocol, doorbell and taxonomy. No network, no paid calls."""
from __future__ import annotations

# --- State isolation (Vesper M1): before any wolf_intelligence import ---------
import atexit as _atexit
import os as _os
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile

if not _os.environ.get("WI_TEST_STATE_ISOLATED"):
    if "wolf_intelligence.paths" in _sys.modules:
        raise RuntimeError("wolf_intelligence.paths imported before test state isolation")
    _TEST_STATE_ROOT = _tempfile.mkdtemp(prefix="wi-test-state-")
    _os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = _TEST_STATE_ROOT
    _os.environ["WI_TEST_STATE_ISOLATED"] = _TEST_STATE_ROOT
    _os.environ.pop("WOLF_INTELLIGENCE_CONFIG_MIRROR", None)
    _atexit.register(_shutil.rmtree, _TEST_STATE_ROOT, True)
# -----------------------------------------------------------------------------

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import grok_bridge as gb
from wolf_intelligence import grok_doorbell as gd
from wolf_intelligence import paths, work_items, worker_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_TEXT = "Reconcile GGV bank statement Rp 141,275,000 for Uma Blu (confidential task text)"


def _guard() -> None:
    root = Path(paths.STATE_ROOT).resolve()
    live = Path(paths.LIVE_STATE_ROOT).resolve()
    if root == live or root.is_relative_to(live) or live.is_relative_to(root):
        raise RuntimeError("refusing to run tests against live Wolf Intelligence state")
    if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise RuntimeError("refusing to run tests outside the system temp dir")


_guard()


class FakeClock:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


class FakeDoorbell:
    kind = "fake"

    def __init__(self) -> None:
        self.rings: list[dict] = []
        self.closes: list[tuple[str, str]] = []
        self.n = 0
        self.lock = threading.Lock()

    def ring(self, wid: str, nonce: str) -> dict:
        with self.lock:
            self.n += 1
            body = gd.issue_body(wid, nonce)
            ref = f"https://github.com/wolfcommand/wolf-grok-bridge/issues/{self.n}"
            self.rings.append({"wid": wid, "nonce": nonce, "title": gd.issue_title(wid), "body": body, "ref": ref})
            return {"ref": ref, "number": self.n}

    def close(self, ref: str, outcome: str) -> None:
        self.closes.append((ref, outcome))


class BrokenDoorbell:
    kind = "broken"

    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc or RuntimeError("github unreachable")
        self.calls = 0

    def ring(self, wid: str, nonce: str) -> dict:
        self.calls += 1
        raise self.exc

    def close(self, ref: str, outcome: str) -> None:
        raise self.exc


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop(gd.DOORBELL_ENV, None)
        self.clock = FakeClock()
        p = mock.patch.object(gb, "_now", self.clock)
        p.start()
        self.addCleanup(p.stop)
        self.bell = FakeDoorbell()

    def new_item(self, **kw) -> str:
        return work_items.create(title=kw.get("title", TASK_TEXT), kind=kw.get("kind", "finance"),
                                 payload={"prompt": TASK_TEXT, "files": ["/private/finance/ggv.csv"]},
                                 tags=["grok_bridge_test"])["id"]

    def offered(self, **kw) -> tuple[str, str]:
        wid = self.new_item()
        out = gb.offer(wid, doorbell=self.bell, **kw)
        self.assertTrue(out["ok"], out)
        return wid, self.nonce(wid)

    def nonce(self, wid: str) -> str:
        conn = sqlite3.connect(str(paths.SQLITE_PATH))
        try:
            return conn.execute("SELECT nonce FROM grok_leases WHERE work_item_id=?", (wid,)).fetchone()[0]
        finally:
            conn.close()

    def claimed(self, **kw) -> tuple[str, str]:
        wid, nonce = self.offered(**kw)
        r = gb.claim(wid, claimant="grok-routine-1", nonce=nonce)
        self.assertEqual(r["code"], "CLAIMED", r)
        return wid, r["lease_id"]

    def to_dispatched_shadow(self, wid: str) -> None:
        work_items.transition(wid, "ROUTING", reason="test")
        work_items.transition(wid, "RECOMMENDED", reason="test")
        work_items.transition(wid, "DISPATCHED_SHADOW", reason="test")

    def to_running(self, wid: str) -> None:
        self.to_dispatched_shadow(wid)
        work_items.transition(wid, "RUNNING", reason="test")

    def outcomes(self, wid: str, action: str | None = None) -> list[str]:
        return [r["outcome"] for r in gb.audit_rows(wid) if action is None or r["action"] == action]


class ClaimRaceTests(_Base):
    def test_20_parallel_thread_claimers_exactly_one_wins(self) -> None:
        wid, nonce = self.offered()
        barrier = threading.Barrier(20)
        results: list[dict] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            barrier.wait()
            r = gb.claim(wid, claimant=f"claimer-{i}", nonce=nonce)
            with lock:
                results.append(r)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        codes = sorted(r["code"] for r in results)
        self.assertEqual(len(results), 20)
        self.assertEqual(codes.count("CLAIMED"), 1, codes)
        self.assertEqual(codes.count("ALREADY_CLAIMED"), 19, codes)
        claim_audit = self.outcomes(wid, "claim")
        self.assertEqual(claim_audit.count("CLAIMED"), 1)
        self.assertEqual(claim_audit.count("ALREADY_CLAIMED"), 19)
        winner = next(r for r in results if r["ok"])
        self.assertEqual(gb.status(wid)["lease"]["lease_id"], winner["lease_id"])

    def test_20_parallel_process_claimers_via_cli_exactly_one_wins(self) -> None:
        wid, nonce = self.offered()
        env = dict(os.environ)
        env.pop(gd.DOORBELL_ENV, None)
        procs = [subprocess.Popen([sys.executable, "-m", "wolf_intelligence", "grok-bridge", "claim", wid,
                                   "--nonce", nonce, "--claimant", f"proc-{i}"], cwd=str(REPO_ROOT), env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(20)]
        outs = []
        for p in procs:
            so, se = p.communicate(timeout=120)
            outs.append((p.returncode, json.loads(so.strip().splitlines()[-1])))
        codes = sorted(o["code"] for _, o in outs)
        self.assertEqual(codes.count("CLAIMED"), 1, codes)
        self.assertEqual(codes.count("ALREADY_CLAIMED"), 19, codes)
        self.assertEqual(sorted(rc for rc, _ in outs), [0] + [3] * 19)
        self.assertEqual(self.outcomes(wid, "claim").count("CLAIMED"), 1)

    def test_50_parallel_process_claimers_via_cli_exactly_one_wins(self) -> None:
        wid, nonce = self.offered()
        env = dict(os.environ)
        env.pop(gd.DOORBELL_ENV, None)
        procs = [subprocess.Popen([sys.executable, "-m", "wolf_intelligence", "grok-bridge", "claim", wid,
                                   "--nonce", nonce, "--claimant", f"proc-{i}"], cwd=str(REPO_ROOT), env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(50)]
        outs = []
        for p in procs:
            so, _ = p.communicate(timeout=180)
            outs.append((p.returncode, json.loads(so.strip().splitlines()[-1])))
        codes = sorted(o["code"] for _, o in outs)
        self.assertEqual(codes.count("CLAIMED"), 1, codes)
        self.assertEqual(codes.count("ALREADY_CLAIMED"), 49, codes)
        self.assertEqual(self.outcomes(wid, "claim").count("CLAIMED"), 1)
        self.assertTrue(gb.verify_audit_chain()["ok"])


class LeaseTests(_Base):
    def test_claim_returns_task_and_lease_fields(self) -> None:
        wid, nonce = self.offered(lease_seconds=600)
        r = gb.claim(wid, claimant="grok-routine-1", nonce=nonce)
        self.assertTrue(r["ok"])
        for k in ("lease_id", "claimant", "claimed_at", "lease_expires_at", "attempt", "task"):
            self.assertIn(k, r)
        self.assertRegex(r["lease_id"], r"^lease_[0-9a-f]{24}$")
        self.assertEqual(r["attempt"], 1)
        self.assertEqual(r["task"]["payload"]["prompt"], TASK_TEXT)

    def test_wrong_nonce_and_not_offered(self) -> None:
        wid, _ = self.offered()
        self.assertEqual(gb.claim(wid, claimant="x", nonce="0" * 32)["code"], "NONCE_MISMATCH")
        other = self.new_item()
        self.assertEqual(gb.claim(other, claimant="x", nonce="0" * 32)["code"], "NOT_OFFERED")
        self.assertEqual(gb.status(wid)["code"], "AVAILABLE")

    def test_stale_lease_complete_rejected_and_recorded(self) -> None:
        wid, lease = self.claimed(lease_seconds=300)
        self.clock.advance(301)
        r = gb.complete(wid, lease_id=lease, result="late answer", doorbell=self.bell)
        self.assertEqual(r["code"], "STALE_LEASE")
        self.assertFalse(r["ok"])
        rows = [x for x in gb.audit_rows(wid) if x["action"] == "complete"]
        self.assertEqual(rows[-1]["outcome"], "STALE_LEASE")
        self.assertIn("lease expired", rows[-1]["detail_json"])
        self.assertEqual(gb.status(wid)["code"], "CLAIMED")  # until recovery runs
        gb.release_expired(doorbell=self.bell)
        self.assertEqual(gb.complete(wid, lease_id=lease, result="still late", doorbell=self.bell)["code"], "STALE_LEASE")
        self.assertIsNone(gb.status(wid)["lease"]["result_sha256"])

    def test_wrong_or_malformed_lease_rejected(self) -> None:
        wid, lease = self.claimed()
        self.assertEqual(gb.complete(wid, lease_id="lease_" + "0" * 24, result="x")["code"], "STALE_LEASE")
        self.assertEqual(gb.complete(wid, lease_id="../../etc/passwd", result="x")["code"], "BAD_LEASE_ID")
        self.assertEqual(gb.fail(wid, lease_id="nope", reason="x")["code"], "BAD_LEASE_ID")
        self.assertEqual(gb.status(wid)["code"], "CLAIMED")

    def test_double_complete_rejected(self) -> None:
        wid, lease = self.claimed()
        first = gb.complete(wid, lease_id=lease, result="answer one", doorbell=self.bell)
        self.assertEqual(first["code"], "COMPLETED")
        second = gb.complete(wid, lease_id=lease, result="answer two", doorbell=self.bell)
        self.assertEqual(second["code"], "ALREADY_COMPLETED")
        self.assertEqual(gb.status(wid)["lease"]["result_sha256"], hashlib.sha256(b"answer one").hexdigest())
        self.assertEqual(self.outcomes(wid, "complete"), ["COMPLETED", "ALREADY_COMPLETED"])
        self.assertEqual(gb.fail(wid, lease_id=lease, reason="x")["code"], "ALREADY_COMPLETED")

    def test_complete_stores_result_and_moves_item_to_ready_to_test(self) -> None:
        # QUEUED item: result stored, canonical state unchanged (no invented history).
        wid, lease = self.claimed()
        hist_len = len(work_items.get(wid)["history"])
        r = gb.complete(wid, lease_id=lease, result="the answer", evidence="evidence log", doorbell=self.bell)
        self.assertEqual(r["result_sha256"], hashlib.sha256(b"the answer").hexdigest())
        self.assertEqual(r["evidence_sha256"], hashlib.sha256(b"evidence log").hexdigest())
        item = work_items.get(wid)
        self.assertEqual(item["state"], "QUEUED")
        self.assertEqual(len(item["history"]), hist_len)
        self.assertEqual(item["result"]["lease_id"], lease)
        self.assertEqual(Path(item["result"]["result_path"]).read_bytes(), b"the answer")
        self.assertIn((self.bell.rings[-1]["ref"], "COMPLETED"), self.bell.closes)
        # RUNNING path: claim moves DISPATCHED_SHADOW -> RUNNING, complete -> READY_TO_TEST (one history entry).
        wid2 = self.new_item()
        self.to_dispatched_shadow(wid2)
        gb.offer(wid2, doorbell=self.bell)
        nonce2 = self.nonce(wid2)
        hist2 = len(work_items.get(wid2)["history"])
        cr = gb.claim(wid2, claimant="grok-routine-1", nonce=nonce2)
        self.assertEqual(cr["code"], "CLAIMED")
        self.assertEqual(work_items.get(wid2)["state"], "RUNNING")
        self.assertEqual(len(work_items.get(wid2)["history"]), hist2 + 1)
        r2 = gb.complete(wid2, lease_id=cr["lease_id"], result="running answer", doorbell=self.bell)
        self.assertEqual(r2["item_state"], "READY_TO_TEST")
        self.assertEqual(r2["item_transition"], "RUNNING->READY_TO_TEST")
        item2 = work_items.get(wid2)
        self.assertEqual(item2["state"], "READY_TO_TEST")
        self.assertEqual(len(item2["history"]), hist2 + 2)

    def test_secret_shaped_result_rejected_lease_kept(self) -> None:
        wid, lease = self.claimed()
        bad = "here: sk-proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"
        r = gb.complete(wid, lease_id=lease, result=bad, doorbell=self.bell)
        self.assertEqual(r["code"], "SECRET_SHAPED_REJECTED")
        self.assertEqual(gb.status(wid)["code"], "CLAIMED")
        self.assertEqual(gb.complete(wid, lease_id=lease, result="redacted answer", doorbell=self.bell)["code"], "COMPLETED")

    def test_renew_extends_and_rejects_stale(self) -> None:
        wid, lease = self.claimed(lease_seconds=300)
        self.clock.advance(200)
        self.assertEqual(gb.renew(wid, lease_id=lease)["code"], "RENEWED")
        self.clock.advance(200)  # 400 s after claim, but renewed at 200 -> valid until 500
        self.assertEqual(gb.complete(wid, lease_id=lease, result="ok", doorbell=self.bell)["code"], "COMPLETED")
        wid2, lease2 = self.claimed(lease_seconds=300)
        self.clock.advance(400)
        self.assertEqual(gb.renew(wid2, lease_id=lease2)["code"], "STALE_LEASE")

    def test_offer_rules(self) -> None:
        wid, _ = self.offered()
        self.assertEqual(gb.offer(wid, doorbell=self.bell)["code"], "ALREADY_OFFERED")
        self.assertEqual(gb.offer("wi_doesnotexist", doorbell=self.bell)["code"], "NOT_FOUND")
        done = self.new_item()
        work_items.transition(done, "CANCELLED", reason="test")
        self.assertEqual(gb.offer(done, doorbell=self.bell)["code"], "ITEM_TERMINAL")
        with self.assertRaises(ValueError):
            gb.offer(self.new_item(), lease_seconds=5, doorbell=self.bell)


class RecoveryTests(_Base):
    def test_expiry_release_back_to_available_with_new_nonce_and_rering(self) -> None:
        wid, lease = self.claimed(lease_seconds=300, max_attempts=3)
        old_nonce = self.bell.rings[-1]["nonce"]
        old_ref = self.bell.rings[-1]["ref"]
        self.clock.advance(300)
        out = gb.release_expired(doorbell=self.bell)
        self.assertEqual(out["released"], [wid])
        st = gb.status(wid)["lease"]
        self.assertEqual(st["state"], "AVAILABLE")
        self.assertEqual(st["attempt"], 2)
        self.assertIsNone(st["lease_id"])
        self.assertEqual(st["doorbell_state"], "RUNG")
        new_nonce = self.bell.rings[-1]["nonce"]
        self.assertNotEqual(new_nonce, old_nonce)
        self.assertIn((old_ref, "RE_RUNG"), self.bell.closes)
        self.assertEqual(gb.claim(wid, claimant="late", nonce=old_nonce)["code"], "NONCE_MISMATCH")
        r = gb.claim(wid, claimant="grok-routine-2", nonce=new_nonce)
        self.assertEqual((r["code"], r["attempt"]), ("CLAIMED", 2))
        self.assertIn("EXPIRED", self.outcomes(wid, "lease_expired"))
        self.assertIn("RELEASED", self.outcomes(wid, "release"))

    def test_unexpired_lease_not_released(self) -> None:
        wid, _ = self.claimed(lease_seconds=300)
        self.clock.advance(299)
        out = gb.release_expired(doorbell=self.bell)
        self.assertNotIn(wid, out["released"])
        self.assertEqual(gb.status(wid)["code"], "CLAIMED")

    def test_max_attempts_then_failed_and_flagged_without_metered_fallback(self) -> None:
        # QUEUED item: lease fails but canonical state stays QUEUED.
        wid_q = self.new_item()
        gb.offer(wid_q, lease_seconds=60, max_attempts=2, doorbell=self.bell)
        for attempt in (1, 2):
            r = gb.claim(wid_q, claimant=f"r{attempt}", nonce=self.nonce(wid_q))
            self.assertEqual((r["code"], r["attempt"]), ("CLAIMED", attempt))
            self.clock.advance(61)
            gb.release_expired(doorbell=self.bell)
        self.assertEqual(gb.status(wid_q)["lease"]["state"], "FAILED")
        self.assertEqual(work_items.get(wid_q)["state"], "QUEUED")
        # DISPATCHED_SHADOW item: canonical state walks to EXCEPTION.
        wid, _ = self.offered(lease_seconds=60, max_attempts=2)
        self.to_dispatched_shadow(wid)
        for attempt in (1, 2):
            r = gb.claim(wid, claimant=f"r{attempt}", nonce=self.nonce(wid))
            self.assertEqual((r["code"], r["attempt"]), ("CLAIMED", attempt))
            self.clock.advance(61)
            gb.release_expired(doorbell=self.bell)
        st = gb.status(wid)["lease"]
        self.assertEqual(st["state"], "FAILED")
        self.assertTrue(st["reassign_flag"])
        self.assertIn("max_attempts_exhausted", st["failure_reason"])
        cands = st["reassign_candidates"]
        self.assertTrue(cands)
        for c in cands:
            self.assertFalse(worker_registry.is_metered(c), c)
            self.assertTrue(worker_registry.WORKERS[c].get("human_commissioned"), c)
            self.assertNotEqual(c, "grok_bot_sub")
        self.assertEqual(work_items.get(wid)["state"], "EXCEPTION")
        self.assertEqual(self.bell.closes[-1][1], "FAILED")
        self.assertIn("FAILED_MAX_ATTEMPTS", self.outcomes(wid, "release"))
        self.assertEqual(gb.claim(wid, claimant="x", nonce=self.nonce(wid))["code"], "ALREADY_FINISHED")

    def test_explicit_fail_and_retryable_fail(self) -> None:
        wid, lease = self.claimed(max_attempts=3)
        r = gb.fail(wid, lease_id=lease, reason="tool timeout", retryable=True, doorbell=self.bell)
        self.assertEqual((r["code"], r["attempt"]), ("RELEASED_FOR_RETRY", 2))
        lease2 = gb.claim(wid, claimant="r2", nonce=self.nonce(wid))["lease_id"]
        r2 = gb.fail(wid, lease_id=lease2, reason="cannot do this task", doorbell=self.bell)
        self.assertEqual(r2["code"], "FAILED")
        self.assertTrue(r2["reassign_flag"])
        self.assertTrue(all(not worker_registry.is_metered(c) for c in r2["reassign_candidates"]))
        self.assertEqual(r2["reason_sha256"], hashlib.sha256(b"cannot do this task").hexdigest())

    def test_reassign_candidates_never_metered(self) -> None:
        cands = gb.reassign_candidates()
        self.assertEqual(cands, ["claude_pro_sub", "codex_sub", "cursor_sub"])
        metered = [w for w in worker_registry.WORKERS if worker_registry.is_metered(w)]
        self.assertTrue(metered)
        self.assertFalse(set(cands) & set(metered))


class AuditTests(_Base):
    def test_audit_is_complete_and_chained(self) -> None:
        wid, nonce = self.offered(lease_seconds=300, max_attempts=3)
        self.assertEqual(gb.claim(wid, claimant="loser", nonce="f" * 32)["code"], "NONCE_MISMATCH")
        lease1 = gb.claim(wid, claimant="grok-a", nonce=nonce)["lease_id"]
        self.clock.advance(300)
        gb.complete(wid, lease_id=lease1, result="late", doorbell=self.bell)  # stale
        gb.release_expired(doorbell=self.bell)
        lease2 = gb.claim(wid, claimant="grok-b", nonce=self.nonce(wid))["lease_id"]
        gb.renew(wid, lease_id=lease2)
        gb.complete(wid, lease_id=lease2, result="final answer", evidence="proof", doorbell=self.bell)
        rows = gb.audit_rows(wid)
        seq = [(r["action"], r["outcome"]) for r in rows]
        expected = [("offer", "OFFERED"), ("doorbell_ring", "RUNG"), ("claim", "NONCE_MISMATCH"), ("claim", "CLAIMED"),
                    ("complete", "STALE_LEASE"), ("lease_expired", "EXPIRED"), ("release", "RELEASED"),
                    ("doorbell_close", "CLOSED"), ("doorbell_ring", "RUNG"), ("claim", "CLAIMED"), ("renew", "RENEWED"),
                    ("complete", "COMPLETED"), ("doorbell_close", "CLOSED")]
        self.assertEqual(seq, expected)
        for r in rows:
            self.assertTrue(r["actor"])
            self.assertTrue(r["at_wita"].endswith("+08:00"))
            self.assertRegex(r["row_sha256"], r"^[0-9a-f]{64}$")
        by = {(r["action"], r["outcome"]): r for r in rows}
        self.assertEqual(by[("claim", "CLAIMED")]["lease_id"], lease2)
        done = by[("complete", "COMPLETED")]
        self.assertEqual((done["lease_id"], done["actor"], done["from_state"], done["to_state"]),
                         (lease2, "grok-b", "CLAIMED", "COMPLETED"))
        self.assertEqual(done["sha256"], hashlib.sha256(b"final answer").hexdigest())
        self.assertIn(hashlib.sha256(b"proof").hexdigest(), done["detail_json"])
        self.assertEqual(gb.verify_audit_chain()["ok"], True)
        # Event bus mirror
        types = [e["type"] for e in __import__("wolf_intelligence.events", fromlist=["x"]).read_events(work_item_id=wid)]
        for t in ("grok_bridge.offered", "grok_bridge.claimed", "grok_bridge.released", "grok_bridge.completed",
                  "grok_bridge.doorbell_rung", "grok_bridge.doorbell_closed"):
            self.assertIn(t, types)

    def test_audit_tamper_detected(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        self.assertTrue(gb.verify_audit_chain()["ok"])
        conn = sqlite3.connect(str(paths.SQLITE_PATH))
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE grok_bridge_audit SET actor='blocked' WHERE seq=1")
            conn.row_factory = sqlite3.Row
            conn.execute("DROP TRIGGER grok_audit_no_update")
            conn.execute("DROP TRIGGER grok_audit_no_delete")
            seq = conn.execute("SELECT seq FROM grok_bridge_audit WHERE work_item_id=? AND outcome='COMPLETED'",
                               (wid,)).fetchone()[0]
            orig = dict(conn.execute("SELECT * FROM grok_bridge_audit WHERE seq=?", (seq,)).fetchone())
            conn.execute("UPDATE grok_bridge_audit SET actor='someone-else' WHERE seq=?", (seq,))
            conn.commit()
            self.assertFalse(gb.verify_audit_chain()["ok"])
            conn.execute("DROP TRIGGER IF EXISTS grok_audit_no_update")
            conn.execute("DROP TRIGGER IF EXISTS grok_audit_no_delete")
            conn.execute("UPDATE grok_bridge_audit SET actor=? WHERE seq=?", (orig["actor"], seq))
            conn.commit()
            gb.init_schema(conn)
            conn.commit()
        finally:
            conn.close()
        self.assertTrue(gb.verify_audit_chain()["ok"])


class DoorbellTests(_Base):
    def test_doorbell_contains_only_id_and_nonce(self) -> None:
        wid, nonce = self.offered()
        ring = self.bell.rings[-1]
        self.assertEqual(ring["body"], f"{gd.FORMAT_VERSION}\nwork_item_id: {wid}\nnonce: {nonce}\n")
        self.assertEqual(ring["title"], f"WI doorbell {wid}")
        self.assertEqual(gd.parse_body(ring["body"]), {"work_item_id": wid, "nonce": nonce})
        blob = ring["title"] + ring["body"]
        for forbidden in (TASK_TEXT, "GGV", "Uma Blu", "141,275,000", "finance", "/private/finance", "prompt"):
            self.assertNotIn(forbidden, blob)

    def test_github_doorbell_argv_has_no_task_text(self) -> None:
        wid = self.new_item()
        seen = []

        def fake_run(argv, **kw):
            seen.append(argv)
            out = "https://github.com/wolfcommand/wolf-grok-bridge/issues/7\n" if argv[1:3] == ["issue", "create"] else ""
            return subprocess.CompletedProcess(argv, 0, out, "")

        bell = gd.GitHubIssueDoorbell(gh="/usr/bin/false")
        with mock.patch.object(gd.subprocess, "run", side_effect=fake_run):
            r = gb.offer(wid, doorbell=bell)
            self.assertEqual(r["doorbell"]["code"], "DOORBELL_RUNG")
            lease = gb.claim(wid, claimant="g", nonce=self.nonce(wid))["lease_id"]
            gb.complete(wid, lease_id=lease, result="done", doorbell=bell)
        create = seen[0]
        self.assertEqual(create[1:3], ["issue", "create"])
        args = dict(zip(create[3::2], create[4::2]))
        self.assertEqual(args["--repo"], "wolfcommand/wolf-grok-bridge")
        self.assertNotIn("--assignee", args)  # created unassigned ...
        self.assertEqual(args["--label"], "wi-doorbell")
        assign = seen[1]  # ... then assigned in a separate call (standalone issues.assigned event)
        self.assertEqual(assign[1:4], ["issue", "edit", "https://github.com/wolfcommand/wolf-grok-bridge/issues/7"])
        self.assertEqual(dict(zip(assign[4::2], assign[5::2]))["--add-assignee"], "wolfcommand")
        self.assertEqual(gd.parse_body(args["--body"])["work_item_id"], wid)
        self.assertNotIn(TASK_TEXT, " ".join(create))
        close = seen[-1]
        self.assertEqual(close[1:4], ["issue", "close", "https://github.com/wolfcommand/wolf-grok-bridge/issues/7"])
        self.assertNotIn("done", " ".join(close[4:]).replace("--reason", ""))

    def test_doorbell_failure_is_safe(self) -> None:
        wid = self.new_item()
        broken = BrokenDoorbell()
        r = gb.offer(wid, doorbell=broken)
        self.assertTrue(r["ok"])
        self.assertEqual(r["doorbell"]["code"], "DOORBELL_FAILED")
        st = gb.status(wid)["lease"]
        self.assertEqual((st["state"], st["doorbell_state"]), ("AVAILABLE", "FAILED"))
        self.assertIn("RuntimeError", st["doorbell_error"])
        self.assertEqual(self.outcomes(wid, "doorbell_ring"), ["FAILED"])
        # Claim still works with the nonce (e.g. Owner rings manually) and recovery re-rings with a working bell.
        out = gb.release_expired(doorbell=self.bell)
        self.assertIn({"work_item_id": wid, "code": "DOORBELL_RUNG"}, out["rerung"])
        self.assertEqual(gb.status(wid)["lease"]["doorbell_state"], "RUNG")

    def test_github_doorbell_errors_never_raise_out(self) -> None:
        cases = [subprocess.CompletedProcess(["gh"], 1, "", "HTTP 404: Not Found (https://api.github.com/x)"),
                 subprocess.TimeoutExpired(["gh"], 30), FileNotFoundError("gh")]
        for case in cases:
            with self.subTest(case=type(case).__name__):
                wid = self.new_item()
                bell = gd.GitHubIssueDoorbell(gh="/nonexistent/gh")
                side = (lambda *a, **k: case) if isinstance(case, subprocess.CompletedProcess) else case
                with mock.patch.object(gd.subprocess, "run", side_effect=side):
                    r = gb.offer(wid, doorbell=bell)
                self.assertTrue(r["ok"])
                self.assertEqual(r["doorbell"]["code"], "DOORBELL_FAILED")
                self.assertEqual(gb.status(wid)["lease"]["state"], "AVAILABLE")
                self.assertIn("DoorbellError", gb.status(wid)["lease"]["doorbell_error"])

    def test_bad_issue_url_is_a_failure(self) -> None:
        wid = self.new_item()
        bell = gd.GitHubIssueDoorbell()
        ret = subprocess.CompletedProcess(["gh"], 0, "https://github.com/someone/else/issues/1\n", "")
        with mock.patch.object(gd.subprocess, "run", return_value=ret):
            self.assertEqual(gb.offer(wid, doorbell=bell)["doorbell"]["code"], "DOORBELL_FAILED")

    def test_close_failure_does_not_undo_completion(self) -> None:
        wid = self.new_item()
        gb.offer(wid, doorbell=self.bell)
        lease = gb.claim(wid, claimant="g", nonce=self.nonce(wid))["lease_id"]
        r = gb.complete(wid, lease_id=lease, result="ok", doorbell=BrokenDoorbell())
        self.assertEqual(r["code"], "COMPLETED")
        self.assertEqual(self.outcomes(wid, "doorbell_close"), ["FAILED"])

    def test_doorbell_disabled_by_default(self) -> None:
        wid = self.new_item()
        self.assertIsNone(gd.from_env())
        r = gb.offer(wid)  # env doorbell: unset -> disabled
        self.assertEqual(r["doorbell"]["code"], "DOORBELL_DISABLED")
        self.assertEqual(gb.status(wid)["lease"]["doorbell_state"], "DISABLED")
        with mock.patch.dict(os.environ, {gd.DOORBELL_ENV: "github"}):
            self.assertIsInstance(gd.from_env(), gd.GitHubIssueDoorbell)

    def test_parse_body_rejects_extra_content(self) -> None:
        good = gd.issue_body("wi_0123456789ab", "a" * 32)
        for bad in (good + "prompt: do things\n", good.replace(gd.FORMAT_VERSION, "v0"), "", "nonce: x"):
            with self.assertRaises(gd.DoorbellError):
                gd.parse_body(bad)
        with self.assertRaises(gd.DoorbellError):
            gd.issue_body("wi bad id", "a" * 32)


class CliTests(_Base):
    def run_cli(self, *args: str, stdin: str | None = None) -> tuple[int, dict]:
        env = dict(os.environ)
        env.pop(gd.DOORBELL_ENV, None)
        p = subprocess.run([sys.executable, "-m", "wolf_intelligence", "grok-bridge", *args], cwd=str(REPO_ROOT),
                           env=env, input=stdin, capture_output=True, text=True, timeout=60)
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])

    def test_cli_round_trip(self) -> None:
        gb._now = __import__("time").time  # CLI subprocesses use the real clock
        self.addCleanup(setattr, gb, "_now", self.clock)
        wid = self.new_item()
        rc, out = self.run_cli("offer", wid, "--lease-seconds", "600")
        self.assertEqual((rc, out["code"], out["doorbell"]["code"]), (0, "OFFERED", "DOORBELL_DISABLED"))
        nonce = self.nonce(wid)
        rc, c = self.run_cli("claim", wid, "--nonce", nonce, "--claimant", "grok-bot-routine")
        self.assertEqual((rc, c["code"]), (0, "CLAIMED"))
        self.assertEqual(c["task"]["payload"]["prompt"], TASK_TEXT)
        rc, again = self.run_cli("claim", wid, "--nonce", nonce, "--claimant", "dup")
        self.assertEqual((rc, again["code"]), (3, "ALREADY_CLAIMED"))
        rc, done = self.run_cli("complete", wid, "--lease", c["lease_id"], "--result-stdin", stdin="answer text")
        self.assertEqual((rc, done["code"]), (0, "COMPLETED"))
        self.assertEqual(done["result_sha256"], hashlib.sha256(b"answer text").hexdigest())
        rc, dbl = self.run_cli("complete", wid, "--lease", c["lease_id"], "--result-stdin", stdin="again")
        self.assertEqual((rc, dbl["code"]), (3, "ALREADY_COMPLETED"))
        rc, st = self.run_cli("status", wid)
        self.assertEqual((rc, st["code"]), (0, "COMPLETED"))
        rc, au = self.run_cli("audit", wid)
        self.assertTrue(au["chain"]["ok"])
        rc, bad = self.run_cli("claim", "bad id!", "--nonce", nonce, "--claimant", "x")
        self.assertEqual((rc, bad["code"]), (2, "BAD_INPUT"))
        rc, rec = self.run_cli("release-expired")
        self.assertEqual((rc, rec["code"]), (0, "RECOVERY_DONE"))

    def test_cli_fail(self) -> None:
        gb._now = __import__("time").time
        self.addCleanup(setattr, gb, "_now", self.clock)
        wid = self.new_item()
        self.run_cli("offer", wid)
        _, c = self.run_cli("claim", wid, "--nonce", self.nonce(wid), "--claimant", "g")
        rc, f = self.run_cli("fail", wid, "--lease", c["lease_id"], "--reason", "cannot reach repo")
        self.assertEqual((rc, f["code"], f["reassign_flag"]), (0, "FAILED", True))


class TickTests(_Base):
    def test_tick_runs_lease_recovery_and_survives_errors(self) -> None:
        from wolf_intelligence import overnight_tick
        with mock.patch.object(gb, "release_expired", return_value={"ok": True, "code": "RECOVERY_DONE"}) as rel:
            self.assertEqual(overnight_tick._grok_lease_recovery()["code"], "RECOVERY_DONE")
            rel.assert_called_once_with(actor="overnight-tick")
        with mock.patch.object(gb, "release_expired", side_effect=sqlite3.OperationalError("locked")):
            self.assertEqual(overnight_tick._grok_lease_recovery()["code"], "RECOVERY_ERROR")

    def test_tick_verifies_audit_chain_on_every_run(self) -> None:
        from wolf_intelligence import dispatcher, learning, overnight_tick, shadow_compare
        from wolf_intelligence.stats_store import recompute
        with mock.patch.object(work_items, "create", return_value={"id": "wi_mock"}), \
             mock.patch.object(dispatcher, "dispatch"), \
             mock.patch.object(learning, "record_outcome"), \
             mock.patch.object(shadow_compare, "run_compare", return_value={}), \
             mock.patch("wolf_intelligence.stats_store.recompute", return_value={}), \
             mock.patch.object(gb, "release_expired", return_value={"ok": True, "code": "RECOVERY_DONE"}):
            out = overnight_tick.run()
        self.assertIn("grok_audit_chain", out)
        self.assertTrue(out["grok_audit_chain"]["ok"])
        self.assertIn("grok_doorbell_enabled", out)
        self.assertIsInstance(out["grok_doorbell_enabled"], bool)


class ClaimAllowlistTests(_Base):
    _TRANSITIONS_TO: dict[str, list[str]] = {
        "ROUTING": ["ROUTING"],
        "RECOMMENDED": ["ROUTING", "RECOMMENDED"],
        "READY_TO_TEST": ["ROUTING", "RECOMMENDED", "DISPATCHED_SHADOW", "RUNNING", "READY_TO_TEST"],
        "NEEDS_YOU": ["ROUTING", "RECOMMENDED", "NEEDS_YOU"],
        "DECISION_PENDING": ["ROUTING", "RECOMMENDED", "DECISION_PENDING"],
        "EXCEPTION": ["ROUTING", "RECOMMENDED", "DISPATCHED_SHADOW", "EXCEPTION"],
        "HUMAN_PASSED": ["ROUTING", "RECOMMENDED", "DISPATCHED_SHADOW", "RUNNING", "READY_TO_TEST", "HUMAN_PASSED"],
        "BLOCKED": ["BLOCKED"],
        "CANCELLED": ["CANCELLED"],
    }

    def _to_state(self, wid: str, target: str) -> None:
        for step in self._TRANSITIONS_TO[target]:
            work_items.transition(wid, step, reason="test")

    def test_offer_refused_for_non_claimable_states(self) -> None:
        non_claimable = set(work_items.STATES) - gb.CLAIMABLE_ITEM_STATES
        for state in non_claimable:
            wid = self.new_item()
            if state != "QUEUED":
                self._to_state(wid, state)
            code = "ITEM_TERMINAL" if state in work_items.TERMINAL else "ITEM_NOT_CLAIMABLE"
            r = gb.offer(wid, doorbell=self.bell)
            self.assertEqual(r["code"], code, state)
            self.assertIsNone(gb.status(wid).get("lease"))

    def test_claim_refused_when_item_leaves_claimable_state(self) -> None:
        cases = {
            "NEEDS_YOU": ["ROUTING", "RECOMMENDED", "NEEDS_YOU"],
            "DECISION_PENDING": ["ROUTING", "RECOMMENDED", "DECISION_PENDING"],
            "CANCELLED": ["CANCELLED"],
            "BLOCKED": ["BLOCKED"],
            "HUMAN_PASSED": ["ROUTING", "RECOMMENDED", "DISPATCHED_SHADOW", "RUNNING", "READY_TO_TEST", "HUMAN_PASSED"],
        }
        for label, steps in cases.items():
            wid = self.new_item()
            gb.offer(wid, doorbell=self.bell)
            nonce = self.nonce(wid)
            for step in steps:
                work_items.transition(wid, step, reason="test")
            r = gb.claim(wid, claimant="late-claimer", nonce=nonce)
            self.assertEqual(r["code"], "ITEM_NOT_CLAIMABLE", label)
            self.assertEqual(gb.status(wid)["code"], "AVAILABLE")
            self.assertIn("ITEM_NOT_CLAIMABLE", self.outcomes(wid, "claim"))


class NoInventedHistoryTests(_Base):
    def test_complete_queued_leaves_state_and_history_unchanged(self) -> None:
        wid, lease = self.claimed()
        before = work_items.get(wid)
        gb.complete(wid, lease_id=lease, result="ok", doorbell=self.bell)
        after = work_items.get(wid)
        self.assertEqual(after["state"], before["state"])
        self.assertEqual(after["history"], before["history"])

    def test_complete_while_needs_you_stays_needs_you(self) -> None:
        wid = self.new_item()
        self.to_running(wid)
        gb.offer(wid, doorbell=self.bell)
        nonce = self.nonce(wid)
        lease = gb.claim(wid, claimant="grok-routine-1", nonce=nonce)["lease_id"]
        work_items.transition(wid, "NEEDS_YOU", reason="owner gate")
        r = gb.complete(wid, lease_id=lease, result="done", doorbell=self.bell)
        self.assertEqual(r["item_state"], "NEEDS_YOU")
        self.assertEqual(work_items.get(wid)["state"], "NEEDS_YOU")


class ExecutorIdentityTests(_Base):
    def test_dispatcher_claimant_and_result_identity_fields(self) -> None:
        wid = self.new_item()
        self.to_dispatched_shadow(wid)
        gb.offer(wid, actor="dispatch-bot", doorbell=self.bell)
        nonce = self.nonce(wid)
        claim = gb.claim(wid, claimant="grok-routine-1", nonce=nonce)
        lease = claim["lease_id"]
        offer_row = next(r for r in gb.audit_rows(wid) if r["action"] == "offer" and r["outcome"] == "OFFERED")
        self.assertEqual(json.loads(offer_row["detail_json"])["dispatcher"], "dispatch-bot")
        self.assertEqual(gb.status(wid)["lease"]["dispatcher"], "dispatch-bot")
        self.assertEqual(claim["idempotency_key"], f"{wid}:attempt-1")
        gb.renew(wid, lease_id=lease)
        gb.complete(wid, lease_id=lease, result="answer", executed_by="sub-agent", doorbell=self.bell)
        for action in ("claim", "renew", "complete"):
            row = next(r for r in gb.audit_rows(wid) if r["action"] == action
                       and r["outcome"] in ("CLAIMED", "RENEWED", "COMPLETED"))
            self.assertEqual(row["actor"], "grok-routine-1", action)
        self.assertNotIn("grok_bot", {r["actor"] for r in gb.audit_rows(wid)})
        item = work_items.get(wid)
        res = item["result"]
        for k in ("dispatcher", "claimed_by", "executed_by", "completed_by", "claimed_at", "completed_at",
                  "attempt", "result_sha256", "evidence_sha256"):
            self.assertIn(k, res, k)
        self.assertEqual(res["dispatcher"], "dispatch-bot")
        self.assertEqual(res["claimed_by"], "grok-routine-1")
        self.assertEqual(res["executed_by"], "sub-agent")
        self.assertEqual(res["completed_by"], "grok-routine-1")
        self.assertEqual(res["executed_by_source"], "declared_by_lease_holder")
        wid2, lease2 = self.claimed()
        gb.fail(wid2, lease_id=lease2, reason="nope", doorbell=self.bell)
        fail_row = next(r for r in gb.audit_rows(wid2) if r["action"] == "fail")
        self.assertEqual(fail_row["actor"], "grok-routine-1")

    def test_executed_by_defaults_to_claimant(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        res = work_items.get(wid)["result"]
        self.assertEqual(res["executed_by"], "grok-routine-1")
        self.assertEqual(res["executed_by_source"], "defaulted_to_lease_holder")

    def test_stale_complete_after_reclaim_attributed_to_original_holder(self) -> None:
        wid, nonce = self.offered(lease_seconds=300)
        old = gb.claim(wid, claimant="stalled-worker", nonce=nonce)
        old_lease = old["lease_id"]
        self.clock.advance(301)
        gb.release_expired(doorbell=self.bell)
        new = gb.claim(wid, claimant="new-worker", nonce=self.nonce(wid))
        self.assertEqual(new["code"], "CLAIMED")
        r = gb.complete(wid, lease_id=old_lease, result="late", caller="new-worker", doorbell=self.bell)
        self.assertEqual(r["code"], "STALE_LEASE")
        row = next(x for x in gb.audit_rows(wid) if x["action"] == "complete" and x["outcome"] == "STALE_LEASE")
        self.assertEqual(row["actor"], "stalled-worker")


class TamperEvidenceTests(_Base):
    def setUp(self) -> None:
        super().setUp()
        self._db_backup = paths.SQLITE_PATH.read_bytes()
        ap = gb.anchor_path()
        self._anchor_backup = ap.read_bytes() if ap.exists() else None

    def _audit_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(paths.SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def tearDown(self) -> None:
        paths.SQLITE_PATH.write_bytes(self._db_backup)
        ap = gb.anchor_path()
        if self._anchor_backup is not None:
            ap.write_bytes(self._anchor_backup)
        elif ap.exists():
            ap.unlink(missing_ok=True)
        super().tearDown()

    def _drop_triggers(self, conn: sqlite3.Connection) -> None:
        conn.execute("DROP TRIGGER IF EXISTS grok_audit_no_update")
        conn.execute("DROP TRIGGER IF EXISTS grok_audit_no_delete")

    def _recompute_sha_only(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT * FROM grok_bridge_audit ORDER BY seq").fetchall()
        prev = None
        for r in rows:
            body = {k: r[k] for k in gb._ROW_FIELDS}
            row_sha = gb.sha256_bytes(json.dumps(body, sort_keys=True).encode())
            conn.execute("UPDATE grok_bridge_audit SET prev_row_sha256=?, row_sha256=? WHERE seq=?",
                         (prev, row_sha, r["seq"]))
            prev = row_sha
        conn.commit()

    def test_append_only_triggers_block_update_and_delete(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        conn = self._audit_conn()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE grok_bridge_audit SET actor='x' WHERE seq=1")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM grok_bridge_audit WHERE seq=1")
        finally:
            conn.close()

    def test_hmac_mismatch_after_tamper_with_recomputed_chain(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        conn = self._audit_conn()
        try:
            self._drop_triggers(conn)
            seq = conn.execute("SELECT seq FROM grok_bridge_audit ORDER BY seq DESC LIMIT 1").fetchone()[0]
            conn.execute("UPDATE grok_bridge_audit SET actor='tampered' WHERE seq=?", (seq,))
            conn.commit()
            self._recompute_sha_only(conn)
        finally:
            conn.close()
        v = gb.verify_audit_chain()
        self.assertFalse(v["ok"])
        self.assertEqual(v["problems"][0]["code"], "HMAC_MISMATCH")

    def test_truncated_tail_detected(self) -> None:
        wid, nonce = self.offered(lease_seconds=300, max_attempts=3)
        gb.claim(wid, claimant="loser", nonce="f" * 32)
        lease1 = gb.claim(wid, claimant="grok-a", nonce=nonce)["lease_id"]
        self.clock.advance(300)
        gb.complete(wid, lease_id=lease1, result="late", doorbell=self.bell)
        gb.release_expired(doorbell=self.bell)
        lease2 = gb.claim(wid, claimant="grok-b", nonce=self.nonce(wid))["lease_id"]
        gb.renew(wid, lease_id=lease2)
        gb.complete(wid, lease_id=lease2, result="final answer", doorbell=self.bell)
        self.assertGreaterEqual(len(gb.audit_rows(wid)), 10)
        conn = self._audit_conn()
        try:
            self._drop_triggers(conn)
            for _ in range(5):
                conn.execute("DELETE FROM grok_bridge_audit WHERE seq=(SELECT MAX(seq) FROM grok_bridge_audit)")
            conn.commit()
        finally:
            conn.close()
        v = gb.verify_audit_chain()
        self.assertFalse(v["ok"])
        self.assertEqual(v["problems"][0]["code"], "TRUNCATED")

    def test_nulled_hmac_detected(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        conn = self._audit_conn()
        try:
            self._drop_triggers(conn)
            conn.execute("UPDATE grok_bridge_audit SET row_hmac=NULL")
            conn.commit()
        finally:
            conn.close()
        self.assertFalse(gb.verify_audit_chain()["ok"])

    def test_forged_anchor_invalid(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        ap = gb.anchor_path()
        prior = ap.read_text() if ap.exists() else None
        try:
            ap.write_text(json.dumps({"format": gb.ANCHOR_FORMAT, "seq": 99999,
                                      "row_sha256": "0" * 64, "rows": 1,
                                      "hmac_from_seq": 1, "anchor_hmac": "deadbeef"}) + "\n")
            v = gb.verify_audit_chain()
            self.assertFalse(v["ok"])
            codes = [p["code"] for p in v["problems"]]
            self.assertIn("ANCHOR_INVALID", codes)
        finally:
            if prior is None:
                ap.unlink(missing_ok=True)
            else:
                ap.write_text(prior)

    def test_audit_key_file_permissions(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        kp = gb.audit_key_path()
        self.assertTrue(kp.exists())
        self.assertEqual(oct(kp.stat().st_mode & 0o777), "0o600")
        self.assertEqual(oct(kp.parent.stat().st_mode & 0o777), "0o700")

    def test_correct_appends_without_mutating_original(self) -> None:
        wid, lease = self.claimed()
        gb.complete(wid, lease_id=lease, result="x", doorbell=self.bell)
        conn = self._audit_conn()
        try:
            orig = dict(conn.execute("SELECT * FROM grok_bridge_audit WHERE outcome='COMPLETED'").fetchone())
        finally:
            conn.close()
        seq = orig["seq"]
        r = gb.correct(seq, reason="typo in detail", actor="owner")
        self.assertTrue(r["ok"])
        conn = self._audit_conn()
        try:
            after = dict(conn.execute("SELECT * FROM grok_bridge_audit WHERE seq=?", (seq,)).fetchone())
            corr = dict(conn.execute("SELECT * FROM grok_bridge_audit WHERE action='correction'").fetchone())
        finally:
            conn.close()
        self.assertEqual(after, orig)
        detail = json.loads(corr["detail_json"])
        self.assertEqual(detail["corrects_seq"], seq)
        self.assertEqual(detail["corrects_row_sha256"], orig["row_sha256"])


class GitHubUnavailableTests(_Base):
    def test_offer_with_missing_gh_records_failure_and_stays_available(self) -> None:
        bell = gd.GitHubIssueDoorbell(gh="/nonexistent/gh")
        wid = self.new_item()
        r = gb.offer(wid, doorbell=bell)
        self.assertTrue(r["ok"])
        self.assertEqual(r["doorbell"]["code"], "DOORBELL_FAILED")
        self.assertEqual(gb.status(wid)["code"], "AVAILABLE")
        self.assertIn("FAILED", self.outcomes(wid, "doorbell_ring"))

    def test_expired_lease_recovery_with_github_unavailable(self) -> None:
        bell = gd.GitHubIssueDoorbell(gh="/nonexistent/gh")
        wid = self.new_item()
        gb.offer(wid, doorbell=bell)
        nonce = self.nonce(wid)
        lease = gb.claim(wid, claimant="grok-routine-1", nonce=nonce)
        self.assertEqual(lease["code"], "CLAIMED")
        self.clock.advance(1801)
        out = gb.release_expired(doorbell=bell)
        self.assertIn(wid, out["released"])
        self.assertEqual(gb.status(wid)["lease"]["attempt"], 2)
        self.assertEqual(work_items.get(wid)["state"], "QUEUED")

    def test_github_doorbell_has_no_read_methods(self) -> None:
        bell = gd.GitHubIssueDoorbell(gh="/nonexistent/gh")
        public = [m for m in dir(bell) if not m.startswith("_") and callable(getattr(bell, m))]
        self.assertEqual(set(public), {"close", "ring"})


class IdempotencyKeyTests(_Base):
    def test_claim_returns_idempotency_key(self) -> None:
        wid, nonce = self.offered(max_attempts=3, lease_seconds=300)
        r = gb.claim(wid, claimant="grok-routine-1", nonce=nonce)
        self.assertEqual(r["idempotency_key"], f"{wid}:attempt-1")
        self.clock.advance(301)
        gb.release_expired(doorbell=self.bell)
        r2 = gb.claim(wid, claimant="grok-routine-1", nonce=self.nonce(wid))
        self.assertEqual(r2["code"], "CLAIMED", r2)
        self.assertEqual(r2["idempotency_key"], f"{wid}:attempt-2")


class WrapperTests(_Base):
    def _run_wrapper(self, *args: str, extra_env: dict | None = None) -> tuple[int, str]:
        env = dict(os.environ)
        env.pop(gd.DOORBELL_ENV, None)
        if extra_env:
            env.update(extra_env)
        script = REPO_ROOT / "wolf_intelligence" / "bin" / "grok-bridge.sh"
        p = subprocess.run(["bash", str(script), *args], cwd=str(REPO_ROOT), env=env,
                           capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout.strip().splitlines()[-1]

    def test_wrapper_refuses_offer_and_release_expired(self) -> None:
        wid = self.new_item()
        for cmd in ("offer", "release-expired"):
            rc, line = self._run_wrapper(cmd, wid) if cmd == "offer" else self._run_wrapper(cmd)
            out = json.loads(line)
            self.assertEqual((rc, out["code"]), (2, "NOT_ALLOWED_FOR_WORKER"), cmd)

    def test_wrapper_scrubs_parent_secrets_from_child_env(self) -> None:
        fake_py = Path(tempfile.mkdtemp()) / "python3"
        fake_py.write_text('#!/usr/bin/env python3\nimport json, os\nprint(json.dumps(dict(os.environ)))\n')
        fake_py.chmod(0o755)
        env = dict(os.environ)
        env["ANTHROPIC_API_KEY"] = "dummy-not-a-key"
        env["GROK_BRIDGE_PYTHON"] = str(fake_py)
        env.pop(gd.DOORBELL_ENV, None)
        script = REPO_ROOT / "wolf_intelligence" / "bin" / "grok-bridge.sh"
        p = subprocess.run(["bash", str(script), "status", "wi_dummy"], cwd=str(REPO_ROOT), env=env,
                           capture_output=True, text=True, timeout=30)
        child_env = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertNotIn("ANTHROPIC_API_KEY", child_env)
        self.assertIn("WOLF_INTELLIGENCE_STATE_ROOT", child_env)
        self.assertEqual(child_env.get("SHELL"), "/bin/bash")


class TaxonomyTests(unittest.TestCase):
    EXPECTED = {
        "claude_pro_sub": "HUMAN COMMISSIONED / CONNECTED",
        "codex_sub": "HUMAN COMMISSIONED / CONNECTED",
        "cursor_sub": "HUMAN COMMISSIONED / CONNECTED",
        "grok_bot_sub": "HUMAN COMMISSIONED MANUALLY / WOLF DISPATCH PARTIAL",
        "gemini_api": "CONNECTED / BILLING UNVERIFIED / NOT HUMAN COMMISSIONED",
        "ollama_local": "CONNECTED / LOCAL / NOT HUMAN COMMISSIONED",
        "anthropic_api": "GATED", "openai_api": "GATED", "xai_api": "GATED", "gemini_paid": "GATED",
    }

    def state(self, wid: str, conn_pass: bool) -> str:
        d = worker_registry.WORKERS[wid]
        derived = {"connectivity_last": {"pass": conn_pass}}
        return worker_registry._commissioning_state(wid, d, "CONNECTED", derived, True)

    def test_owner_labels_with_evidence(self) -> None:
        for wid, label in self.EXPECTED.items():
            self.assertEqual(self.state(wid, True), label, wid)

    def test_no_upgrade_without_evidence(self) -> None:
        for wid in ("claude_pro_sub", "codex_sub", "cursor_sub"):
            self.assertEqual(self.state(wid, False), "HUMAN COMMISSIONED / NOT CONNECTED (no WI connectivity pass)")
        self.assertEqual(self.state("gemini_api", False), "NOT CONNECTED / BILLING UNVERIFIED / NOT HUMAN COMMISSIONED")
        self.assertEqual(self.state("ollama_local", False), "NOT CONNECTED / LOCAL / NOT HUMAN COMMISSIONED")
        for wid in ("anthropic_api", "openai_api", "xai_api", "gemini_paid"):
            self.assertEqual(self.state(wid, True), "GATED")
        d = dict(worker_registry.WORKERS["grok_bot_sub"])
        d.pop("human_commissioned")
        self.assertNotIn("HUMAN COMMISSIONED MANUALLY", worker_registry._commissioning_state("grok_bot_sub", d, "PULL_ONLY", {}, None))
        for wid in ("gemini_api", "ollama_local"):
            self.assertNotIn("human_commissioned", worker_registry.WORKERS[wid])

    def test_snapshot_carries_owner_labels(self) -> None:
        snap = json.loads((paths.CONFIG_DIR / "worker-registry.json").read_text())
        for wid, label in self.EXPECTED.items():
            self.assertEqual(snap["workers"][wid]["commissioning_state"], label, wid)
        self.assertNotIn("gemini_free", snap["workers"])

    def test_gemini_has_no_free_label(self) -> None:
        d = worker_registry.WORKERS["gemini_api"]
        for k, v in d.items():
            if k == "legacy_ids":
                continue  # old id kept only to link existing REAL evidence records
            self.assertNotIn("free", json.dumps(v).lower(), k)
        from wolf_intelligence.adapters import ADAPTER_REGISTRY
        a = ADAPTER_REGISTRY["gemini_api"]
        self.assertNotIn("free", (a.label + a.billing_class).lower())
        self.assertNotIn("gemini_free", ADAPTER_REGISTRY)
        snap = json.loads((paths.CONFIG_DIR / "worker-registry.json").read_text())["workers"]["gemini_api"]
        snap = {k: v for k, v in snap.items() if k not in ("legacy_ids", "commissioning_state_previous")}
        self.assertNotIn("free", json.dumps(snap).lower())

    def test_routing_policy_stays_draft_and_unwired(self) -> None:
        pol = json.loads((paths.CONFIG_DIR / "routing-policy-real.json").read_text())
        self.assertTrue(pol["status"].startswith("DRAFT - NOT WIRED"))
        self.assertIs(pol["wired"], False)
        pkg = paths.PKG_ROOT
        for mod in ("router.py", "dispatcher.py", "real_dispatch.py", "grok_bridge.py", "grok_doorbell.py",
                    "overnight_tick.py", "owner_ui_server.py"):
            src = (pkg / mod).read_text()
            self.assertNotIn("routing_policy", src, mod)
            self.assertNotIn("routing-policy-real", src, mod)

    def test_grok_registry_dispatch_mode(self) -> None:
        d = worker_registry.WORKERS["grok_bot_sub"]
        self.assertIs(d["push_dispatchable"], False)
        self.assertIn("grok_bridge", d["dispatch_mode"])


if __name__ == "__main__":
    unittest.main()
