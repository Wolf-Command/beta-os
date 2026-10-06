"""Grok work bridge: event-driven claim/lease protocol for worker 'grok_bot'.

Canonical work items stay in WI (control_plane.sqlite). This module adds a lease
table next to them and an append-only, hash-chained audit table. Every state
change is a compare-and-set inside ONE SQLite transaction opened with
BEGIN IMMEDIATE, so across threads and processes exactly one caller wins.

    AVAILABLE --claim(nonce)--> CLAIMED(lease_id, claimant, claimed_at, lease_expires_at, attempt)
    CLAIMED --complete(lease_id, unexpired)--> COMPLETED
    CLAIMED --fail(lease_id, unexpired)--> FAILED            (or AVAILABLE, attempt+1, with --retryable)
    CLAIMED --lease expires--> AVAILABLE (attempt+1, new nonce)  ... after max_attempts --> FAILED

FAILED items are flagged for reassignment to the next qualified non-metered,
human-commissioned worker. Nothing is dispatched automatically and nothing ever
falls back to a metered worker.

When an item becomes AVAILABLE, WI rings the doorbell (grok_doorbell.py): a
GitHub issue holding only the work-item id and the nonce. A doorbell failure is
recorded and the item stays AVAILABLE; lease recovery (hourly tick or
`grok-bridge release-expired`) re-rings it. That is lease recovery, not polling.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from . import paths, real_evidence, work_items, worker_registry

TZ = ZoneInfo("Asia/Makassar")
WORKER = "grok_bot"
REGISTRY_WORKER = "grok_bot_sub"
STATES = ("AVAILABLE", "CLAIMED", "COMPLETED", "FAILED")
DEFAULT_LEASE_SECONDS = 1800
MAX_LEASE_SECONDS = 4 * 3600
DEFAULT_MAX_ATTEMPTS = 3
MAX_RENEWALS = 12
MAX_RESULT_BYTES = 2 * 1024 * 1024
MAX_REASON_CHARS = 500

_WID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_CLAIMANT = re.compile(r"^[A-Za-z0-9_.:@\-]{1,80}$")
_LEASE = re.compile(r"^lease_[0-9a-f]{24}$")

# Clock is injectable for tests (epoch seconds).
_now: Callable[[], float] = time.time


def now() -> float:
    return float(_now())


def wita(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, TZ).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def results_dir() -> Path:
    return paths.STATE_ROOT / "grok_bridge" / "results"


# --------------------------------------------------------------------------- store
def _connect() -> sqlite3.Connection:
    paths.ensure_dirs()
    conn = sqlite3.connect(str(paths.SQLITE_PATH), timeout=60, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS grok_leases (
          work_item_id TEXT PRIMARY KEY,
          worker TEXT NOT NULL,
          state TEXT NOT NULL CHECK (state IN ('AVAILABLE','CLAIMED','COMPLETED','FAILED')),
          nonce TEXT NOT NULL,
          lease_id TEXT, claimant TEXT, claimed_at REAL, lease_expires_at REAL,
          renewals INTEGER NOT NULL DEFAULT 0,
          attempt INTEGER NOT NULL DEFAULT 1,
          max_attempts INTEGER NOT NULL,
          lease_seconds INTEGER NOT NULL,
          offered_at REAL NOT NULL, updated_at REAL NOT NULL,
          doorbell_state TEXT NOT NULL DEFAULT 'PENDING',
          doorbell_ref TEXT, doorbell_error TEXT, doorbell_rings INTEGER NOT NULL DEFAULT 0,
          result_sha256 TEXT, result_path TEXT, evidence_sha256 TEXT,
          failure_reason TEXT, reassign_flag INTEGER NOT NULL DEFAULT 0, reassign_candidates TEXT
        )""")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS grok_bridge_audit (
          seq INTEGER PRIMARY KEY AUTOINCREMENT,
          at REAL NOT NULL, at_wita TEXT NOT NULL,
          work_item_id TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL,
          lease_id TEXT, attempt INTEGER, from_state TEXT, to_state TEXT,
          outcome TEXT NOT NULL, sha256 TEXT, detail_json TEXT NOT NULL DEFAULT '{}',
          prev_row_sha256 TEXT, row_sha256 TEXT NOT NULL
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_grok_leases_state ON grok_leases(state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_grok_audit_item ON grok_bridge_audit(work_item_id)")


def _audit(conn: sqlite3.Connection, wid: str, action: str, actor: str, outcome: str, *, lease_id: str | None = None,
           attempt: int | None = None, from_state: str | None = None, to_state: str | None = None,
           sha256: str | None = None, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    """Append one audit row inside the caller's transaction. Rows are hash-chained."""
    ts = now()
    prev = conn.execute("SELECT row_sha256 FROM grok_bridge_audit ORDER BY seq DESC LIMIT 1").fetchone()
    prev_sha = prev["row_sha256"] if prev else None
    row = {"at": ts, "at_wita": wita(ts), "work_item_id": wid, "action": action, "actor": actor, "lease_id": lease_id,
           "attempt": attempt, "from_state": from_state, "to_state": to_state, "outcome": outcome, "sha256": sha256,
           "detail_json": json.dumps(detail or {}, sort_keys=True), "prev_row_sha256": prev_sha}
    row_sha = sha256_bytes(json.dumps(row, sort_keys=True).encode())
    conn.execute(
        """INSERT INTO grok_bridge_audit (at, at_wita, work_item_id, action, actor, lease_id, attempt, from_state,
           to_state, outcome, sha256, detail_json, prev_row_sha256, row_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ts, row["at_wita"], wid, action, actor, lease_id, attempt, from_state, to_state, outcome, sha256,
         row["detail_json"], prev_sha, row_sha))
    row["row_sha256"] = row_sha
    return row


def _row(conn: sqlite3.Connection, wid: str) -> dict[str, Any] | None:
    r = conn.execute("SELECT * FROM grok_leases WHERE work_item_id=?", (wid,)).fetchone()
    return dict(r) if r else None


class _Tx:
    """BEGIN IMMEDIATE ... COMMIT (ROLLBACK on any exception)."""

    def __init__(self) -> None:
        self.conn = _connect()

    def __enter__(self) -> sqlite3.Connection:
        init_schema(self.conn)
        self.conn.execute("BEGIN IMMEDIATE")
        return self.conn

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self.conn.execute("COMMIT")
            else:
                self.conn.execute("ROLLBACK")
        finally:
            self.conn.close()


def _emit(event_type: str, wid: str, payload: dict[str, Any]) -> None:
    """Mirror to the canonical event bus after commit. The audit table is authoritative; never crash here."""
    try:
        from . import events
        events.emit(event_type, payload, work_item_id=wid)
    except Exception:  # noqa: BLE001
        pass


def public(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Lease view safe to print (no result text, no task content)."""
    if row is None:
        return None
    out = {k: row.get(k) for k in ("work_item_id", "worker", "state", "lease_id", "claimant", "attempt",
                                    "max_attempts", "lease_seconds", "renewals", "doorbell_state", "doorbell_ref",
                                    "doorbell_error", "doorbell_rings", "result_sha256", "evidence_sha256",
                                    "failure_reason", "reassign_flag")}
    for k in ("claimed_at", "lease_expires_at", "offered_at", "updated_at"):
        out[k] = wita(row.get(k))
    out["reassign_flag"] = bool(row.get("reassign_flag"))
    out["reassign_candidates"] = json.loads(row["reassign_candidates"]) if row.get("reassign_candidates") else []
    return out


def _result(ok: bool, code: str, wid: str, **extra: Any) -> dict[str, Any]:
    return {"ok": ok, "code": code, "work_item_id": wid, **extra}


def _check_wid(wid: str) -> None:
    if not isinstance(wid, str) or not _WID.match(wid):
        raise ValueError("bad work item id")


# --------------------------------------------------------------------------- policy
def reassign_candidates() -> list[str]:
    """Next qualified workers if Grok fails: human-commissioned, non-metered, ungated, push-dispatchable.

    A flag for the Owner/dispatcher only. Metered workers can never appear here.
    """
    out = []
    for wid, d in worker_registry.WORKERS.items():
        if wid == REGISTRY_WORKER or worker_registry.is_metered(wid) or d.get("gated"):
            continue
        if d.get("push_dispatchable") is False or not d.get("adapter") or not d.get("human_commissioned"):
            continue
        out.append(wid)
    return out


# --------------------------------------------------------------------------- doorbell
def _doorbell_default():
    from . import grok_doorbell
    return grok_doorbell.from_env()


def ring(wid: str, *, doorbell: Any = "env", actor: str = "wi") -> dict[str, Any]:
    """Ring the doorbell for an AVAILABLE item. Never raises; failure is recorded, item stays AVAILABLE."""
    _check_wid(wid)
    bell = _doorbell_default() if doorbell == "env" else doorbell
    with _Tx() as conn:
        row = _row(conn, wid)
        if row is None or row["state"] != "AVAILABLE":
            return _result(False, "NOT_AVAILABLE", wid, state=row and row["state"])
        nonce, attempt = row["nonce"], row["attempt"]
        if bell is None:
            conn.execute("UPDATE grok_leases SET doorbell_state='DISABLED', updated_at=? WHERE work_item_id=?", (now(), wid))
            _audit(conn, wid, "doorbell_ring", actor, "DISABLED", attempt=attempt,
                   detail={"note": "doorbell off (WOLF_INTELLIGENCE_GROK_DOORBELL unset)"})
            return _result(True, "DOORBELL_DISABLED", wid)
    # Network call outside the transaction.
    try:
        info = bell.ring(wid, nonce)
        err = None
    except Exception as exc:  # noqa: BLE001 - a doorbell must never crash WI
        info, err = None, real_evidence.redact(f"{type(exc).__name__}: {exc}")[:300]
    with _Tx() as conn:
        row = _row(conn, wid)
        still = row is not None and row["state"] == "AVAILABLE" and row["nonce"] == nonce
        if err is None:
            ref = str(info.get("ref") or "")
            if still:
                conn.execute("""UPDATE grok_leases SET doorbell_state='RUNG', doorbell_ref=?, doorbell_error=NULL,
                                doorbell_rings=doorbell_rings+1, updated_at=? WHERE work_item_id=?""", (ref, now(), wid))
            _audit(conn, wid, "doorbell_ring", actor, "RUNG" if still else "RUNG_STALE", attempt=attempt,
                   detail={"ref": ref, "kind": getattr(bell, "kind", type(bell).__name__)})
        else:
            if still:
                conn.execute("""UPDATE grok_leases SET doorbell_state='FAILED', doorbell_error=?,
                                doorbell_rings=doorbell_rings+1, updated_at=? WHERE work_item_id=?""", (err, now(), wid))
            _audit(conn, wid, "doorbell_ring", actor, "FAILED", attempt=attempt, detail={"error": err})
    if err is None:
        _emit("grok_bridge.doorbell_rung", wid, {"ref": info.get("ref"), "attempt": attempt, "actor": actor})
        if not still:
            _close_ref(wid, str(info.get("ref") or ""), "SUPERSEDED", bell, actor)
        return _result(True, "DOORBELL_RUNG", wid, doorbell_ref=info.get("ref"))
    _emit("grok_bridge.doorbell_failed", wid, {"error": err, "attempt": attempt, "actor": actor})
    return _result(False, "DOORBELL_FAILED", wid, error=err, state="AVAILABLE")


def rering(wid: str, *, doorbell: Any = "env", actor: str = "wi") -> dict[str, Any]:
    """WI-side: rotate the nonce of an AVAILABLE item, close its current doorbell as SUPERSEDED, ring a new one.

    Used when a doorbell was delivered but never answered. Never called by the Grok routine.
    """
    _check_wid(wid)
    bell = _doorbell_default() if doorbell == "env" else doorbell
    with _Tx() as conn:
        row = _row(conn, wid)
        if row is None or row["state"] != "AVAILABLE":
            return _result(False, "NOT_AVAILABLE", wid, state=row and row["state"])
        old_ref = row["doorbell_ref"]
        conn.execute("""UPDATE grok_leases SET nonce=?, doorbell_state='PENDING', doorbell_ref=NULL, updated_at=?
                        WHERE work_item_id=? AND state='AVAILABLE'""", (secrets.token_hex(16), now(), wid))
        _audit(conn, wid, "rering", actor, "NONCE_ROTATED", attempt=row["attempt"], from_state="AVAILABLE",
               to_state="AVAILABLE", detail={"old_ref": old_ref})
    _close_ref(wid, old_ref, "SUPERSEDED", bell, actor)
    return ring(wid, doorbell=bell, actor=actor)


def _close_ref(wid: str, ref: str | None, outcome: str, bell: Any, actor: str) -> None:
    if not ref or bell is None:
        return
    try:
        bell.close(ref, outcome)
        res, err = "CLOSED", None
    except Exception as exc:  # noqa: BLE001
        res, err = "FAILED", real_evidence.redact(f"{type(exc).__name__}: {exc}")[:300]
    try:
        with _Tx() as conn:
            if res == "CLOSED":
                conn.execute("UPDATE grok_leases SET doorbell_state='CLOSED' WHERE work_item_id=? AND doorbell_ref=?",
                             (wid, ref))
            _audit(conn, wid, "doorbell_close", actor, res, detail={"ref": ref, "outcome": outcome, "error": err})
    except Exception:  # noqa: BLE001
        pass
    _emit("grok_bridge.doorbell_closed", wid, {"ref": ref, "outcome": outcome, "result": res})


# --------------------------------------------------------------------------- protocol
def offer(wid: str, *, lease_seconds: int = DEFAULT_LEASE_SECONDS, max_attempts: int = DEFAULT_MAX_ATTEMPTS,
          actor: str = "wi", doorbell: Any = "env") -> dict[str, Any]:
    """Make a canonical WI work item AVAILABLE to grok_bot and ring the doorbell immediately."""
    _check_wid(wid)
    if not (60 <= int(lease_seconds) <= MAX_LEASE_SECONDS):
        raise ValueError(f"lease_seconds must be 60..{MAX_LEASE_SECONDS}")
    if not (1 <= int(max_attempts) <= 10):
        raise ValueError("max_attempts must be 1..10")
    item = work_items.get(wid)
    if item is None:
        return _result(False, "NOT_FOUND", wid)
    if item["state"] in work_items.TERMINAL:
        return _result(False, "ITEM_TERMINAL", wid, item_state=item["state"])
    with _Tx() as conn:
        row = _row(conn, wid)
        if row is not None:
            code = "ALREADY_OFFERED" if row["state"] in ("AVAILABLE", "CLAIMED") else "ALREADY_FINISHED"
            _audit(conn, wid, "offer", actor, code, attempt=row["attempt"], from_state=row["state"])
            return _result(False, code, wid, lease=public(row))
        ts = now()
        nonce = secrets.token_hex(16)
        conn.execute("""INSERT INTO grok_leases (work_item_id, worker, state, nonce, attempt, max_attempts, lease_seconds,
                        offered_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)""",
                     (wid, WORKER, "AVAILABLE", nonce, 1, int(max_attempts), int(lease_seconds), ts, ts))
        _audit(conn, wid, "offer", actor, "OFFERED", attempt=1, to_state="AVAILABLE",
               detail={"lease_seconds": int(lease_seconds), "max_attempts": int(max_attempts)})
    _set_dispatch(wid, "AVAILABLE")
    _emit("grok_bridge.offered", wid, {"worker": WORKER, "attempt": 1, "actor": actor})
    bell = ring(wid, doorbell=doorbell, actor=actor)
    with _Tx() as conn:
        row = _row(conn, wid)
    return _result(True, "OFFERED", wid, lease=public(row), doorbell=bell)


def claim(wid: str, *, claimant: str, nonce: str) -> dict[str, Any]:
    """Atomic compare-and-set AVAILABLE -> CLAIMED. Exactly one caller wins; others get ALREADY_CLAIMED."""
    _check_wid(wid)
    if not isinstance(claimant, str) or not _CLAIMANT.match(claimant):
        raise ValueError("bad claimant")
    with _Tx() as conn:
        row = _row(conn, wid)
        if row is None:
            _audit(conn, wid, "claim", claimant, "NOT_OFFERED")
            return _result(False, "NOT_OFFERED", wid)
        state, attempt = row["state"], row["attempt"]
        if state == "CLAIMED":
            expired = row["lease_expires_at"] is not None and now() >= row["lease_expires_at"]
            _audit(conn, wid, "claim", claimant, "ALREADY_CLAIMED", attempt=attempt, from_state=state,
                   detail={"lease_expired_pending_recovery": expired})
            return _result(False, "ALREADY_CLAIMED", wid, attempt=attempt,
                           lease_expired_pending_recovery=expired)
        if state in ("COMPLETED", "FAILED"):
            _audit(conn, wid, "claim", claimant, "ALREADY_FINISHED", attempt=attempt, from_state=state)
            return _result(False, "ALREADY_FINISHED", wid, state=state)
        if not isinstance(nonce, str) or not secrets.compare_digest(nonce, row["nonce"]):
            _audit(conn, wid, "claim", claimant, "NONCE_MISMATCH", attempt=attempt, from_state=state)
            return _result(False, "NONCE_MISMATCH", wid,
                           message="stale or wrong doorbell; a newer doorbell exists for this item")
        ts = now()
        lease_id = "lease_" + secrets.token_hex(12)
        expires = ts + row["lease_seconds"]
        cur = conn.execute("""UPDATE grok_leases SET state='CLAIMED', lease_id=?, claimant=?, claimed_at=?,
                              lease_expires_at=?, renewals=0, updated_at=? WHERE work_item_id=? AND state='AVAILABLE'
                              AND nonce=?""", (lease_id, claimant, ts, expires, ts, wid, row["nonce"]))
        if cur.rowcount != 1:  # defensive: cannot happen under BEGIN IMMEDIATE
            _audit(conn, wid, "claim", claimant, "ALREADY_CLAIMED", attempt=attempt, from_state=state)
            return _result(False, "ALREADY_CLAIMED", wid)
        _audit(conn, wid, "claim", claimant, "CLAIMED", lease_id=lease_id, attempt=attempt, from_state="AVAILABLE",
               to_state="CLAIMED", detail={"lease_expires_at": wita(expires)})
    _set_dispatch(wid, "CLAIMED")
    _emit("grok_bridge.claimed", wid, {"lease_id": lease_id, "claimant": claimant, "attempt": attempt})
    item = work_items.get(wid) or {}
    task = {"title": item.get("title"), "kind": item.get("kind"), "payload": item.get("payload") or {},
            "tags": item.get("tags") or []}
    return _result(True, "CLAIMED", wid, lease_id=lease_id, claimant=claimant, attempt=attempt,
                   claimed_at=wita(ts), lease_expires_at=wita(expires), lease_seconds=row["lease_seconds"], task=task)


def _lease_check(conn, wid: str, lease_id: str, actor: str, action: str) -> tuple[dict | None, dict | None]:
    """Shared lease validation. Returns (row, rejection)."""
    row = _row(conn, wid)
    if row is None:
        _audit(conn, wid, action, actor, "NOT_OFFERED", lease_id=lease_id)
        return None, _result(False, "NOT_OFFERED", wid)
    if not isinstance(lease_id, str) or not _LEASE.match(lease_id):
        _audit(conn, wid, action, actor, "BAD_LEASE_ID", attempt=row["attempt"], from_state=row["state"])
        return None, _result(False, "BAD_LEASE_ID", wid)
    if row["state"] == "COMPLETED" and row["lease_id"] == lease_id:
        _audit(conn, wid, action, actor, "ALREADY_COMPLETED", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"])
        return None, _result(False, "ALREADY_COMPLETED", wid, result_sha256=row["result_sha256"])
    if row["state"] == "FAILED" and row["lease_id"] == lease_id:
        _audit(conn, wid, action, actor, "ALREADY_FAILED", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"])
        return None, _result(False, "ALREADY_FAILED", wid)
    if row["state"] != "CLAIMED" or row["lease_id"] != lease_id:
        _audit(conn, wid, action, actor, "STALE_LEASE", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"], detail={"reason": "lease not current"})
        return None, _result(False, "STALE_LEASE", wid, state=row["state"],
                             message="this lease is no longer current; do not retry with it")
    if now() >= row["lease_expires_at"]:
        _audit(conn, wid, action, actor, "STALE_LEASE", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"], detail={"reason": "lease expired", "expired_at": wita(row["lease_expires_at"])})
        return None, _result(False, "STALE_LEASE", wid, state=row["state"], message="lease expired")
    return row, None


def renew(wid: str, *, lease_id: str, actor: str = "grok_bot") -> dict[str, Any]:
    _check_wid(wid)
    with _Tx() as conn:
        row, rej = _lease_check(conn, wid, lease_id, actor, "renew")
        if rej:
            return rej
        if row["renewals"] >= MAX_RENEWALS:
            _audit(conn, wid, "renew", actor, "RENEWAL_LIMIT", lease_id=lease_id, attempt=row["attempt"])
            return _result(False, "RENEWAL_LIMIT", wid)
        expires = now() + row["lease_seconds"]
        conn.execute("UPDATE grok_leases SET lease_expires_at=?, renewals=renewals+1, updated_at=? WHERE work_item_id=?",
                     (expires, now(), wid))
        _audit(conn, wid, "renew", actor, "RENEWED", lease_id=lease_id, attempt=row["attempt"],
               detail={"lease_expires_at": wita(expires)})
    _emit("grok_bridge.renewed", wid, {"lease_id": lease_id, "actor": actor})
    return _result(True, "RENEWED", wid, lease_id=lease_id, lease_expires_at=wita(expires))


def complete(wid: str, *, lease_id: str, result: bytes | str, evidence: bytes | str | None = None,
             actor: str = "grok_bot", doorbell: Any = "env") -> dict[str, Any]:
    """CLAIMED -> COMPLETED with the matching, unexpired lease. Stores the result in WI state with its sha256."""
    _check_wid(wid)
    if not isinstance(lease_id, str) or not _LEASE.match(lease_id):
        with _Tx() as conn:
            _row_unused, rej = _lease_check(conn, wid, lease_id, actor, "complete")
        return rej or _result(False, "BAD_LEASE_ID", wid)
    rb = result.encode("utf-8") if isinstance(result, str) else bytes(result or b"")
    eb = None if evidence is None else (evidence.encode("utf-8") if isinstance(evidence, str) else bytes(evidence))
    if not rb.strip():
        return _result(False, "EMPTY_RESULT", wid)
    if len(rb) > MAX_RESULT_BYTES or (eb is not None and len(eb) > MAX_RESULT_BYTES):
        return _result(False, "RESULT_TOO_LARGE", wid, max_bytes=MAX_RESULT_BYTES)
    text = rb.decode("utf-8", errors="replace") + ("\n" + eb.decode("utf-8", errors="replace") if eb else "")
    if real_evidence.contains_secret(text):
        with _Tx() as conn:
            _audit(conn, wid, "complete", actor, "SECRET_SHAPED_REJECTED", lease_id=lease_id,
                   sha256=sha256_bytes(rb))
        return _result(False, "SECRET_SHAPED_REJECTED", wid,
                       message="result looks like it contains a secret; redact and retry with the same lease")
    rsha = sha256_bytes(rb)
    esha = sha256_bytes(eb) if eb is not None else None
    outdir = results_dir() / wid
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = outdir / f".{lease_id}.{secrets.token_hex(4)}.tmp"
    tmp.write_bytes(rb)
    final = outdir / f"{lease_id}.result"
    try:
        with _Tx() as conn:
            row, rej = _lease_check(conn, wid, lease_id, actor, "complete")
            if rej:
                return rej
            ts = now()
            conn.execute("""UPDATE grok_leases SET state='COMPLETED', result_sha256=?, result_path=?, evidence_sha256=?,
                            updated_at=? WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                         (rsha, str(final), esha, ts, wid, lease_id))
            _audit(conn, wid, "complete", actor, "COMPLETED", lease_id=lease_id, attempt=row["attempt"],
                   from_state="CLAIMED", to_state="COMPLETED", sha256=rsha,
                   detail={"result_bytes": len(rb), "evidence_sha256": esha})
            os.replace(tmp, final)  # inside the tx: a crash before COMMIT leaves an orphan file, never a dangling sha
            if eb is not None:
                (outdir / f"{lease_id}.evidence").write_bytes(eb)
            ref = row["doorbell_ref"]
    finally:
        if tmp.exists():
            tmp.unlink()
    work_items.update_fields(wid, result={"worker": WORKER, "route": "grok_bridge", "lease_id": lease_id,
                                          "result_sha256": rsha, "evidence_sha256": esha, "result_path": str(final),
                                          "completed_at": wita(ts)})
    walked = _walk(wid, "READY_TO_TEST", f"grok_bridge completed {lease_id}")
    _set_dispatch(wid, "COMPLETED")
    _emit("grok_bridge.completed", wid, {"lease_id": lease_id, "result_sha256": rsha, "evidence_sha256": esha,
                                         "actor": actor})
    _close_ref(wid, ref, "COMPLETED", _doorbell_default() if doorbell == "env" else doorbell, actor)
    return _result(True, "COMPLETED", wid, lease_id=lease_id, result_sha256=rsha, evidence_sha256=esha,
                   item_state=walked.get("state"))


def _release_or_fail(conn, row: dict[str, Any], actor: str, reason: str, action: str) -> dict[str, Any]:
    """In-transaction: CLAIMED -> AVAILABLE (attempt+1, new nonce) or -> FAILED after max_attempts."""
    wid, ts = row["work_item_id"], now()
    if row["attempt"] < row["max_attempts"]:
        nonce = secrets.token_hex(16)
        conn.execute("""UPDATE grok_leases SET state='AVAILABLE', nonce=?, lease_id=NULL, claimant=NULL, claimed_at=NULL,
                        lease_expires_at=NULL, renewals=0, attempt=attempt+1, doorbell_state='PENDING', updated_at=?
                        WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""", (nonce, ts, wid, row["lease_id"]))
        _audit(conn, wid, action, actor, "RELEASED", lease_id=row["lease_id"], attempt=row["attempt"],
               from_state="CLAIMED", to_state="AVAILABLE", sha256=sha256_bytes(reason.encode()),
               detail={"reason": reason, "next_attempt": row["attempt"] + 1})
        return {"work_item_id": wid, "to": "AVAILABLE", "attempt": row["attempt"] + 1, "old_ref": row["doorbell_ref"]}
    cands = reassign_candidates()
    conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?, reassign_flag=1, reassign_candidates=?,
                    updated_at=? WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                 (f"{reason}; max_attempts_exhausted", json.dumps(cands), ts, wid, row["lease_id"]))
    _audit(conn, wid, action, actor, "FAILED_MAX_ATTEMPTS", lease_id=row["lease_id"], attempt=row["attempt"],
           from_state="CLAIMED", to_state="FAILED", sha256=sha256_bytes(reason.encode()),
           detail={"reason": reason, "reassign_candidates": cands, "metered_fallback": False})
    return {"work_item_id": wid, "to": "FAILED", "attempt": row["attempt"], "old_ref": row["doorbell_ref"],
            "reassign_candidates": cands}


def fail(wid: str, *, lease_id: str, reason: str, retryable: bool = False, actor: str = "grok_bot",
         doorbell: Any = "env") -> dict[str, Any]:
    """CLAIMED -> FAILED (default) or back to AVAILABLE with attempt+1 if retryable and attempts remain."""
    _check_wid(wid)
    reason_txt = real_evidence.redact(str(reason or "").strip())[:MAX_REASON_CHARS] or "unspecified"
    rsha = sha256_bytes(str(reason or "").encode())
    bell = _doorbell_default() if doorbell == "env" else doorbell
    with _Tx() as conn:
        row, rej = _lease_check(conn, wid, lease_id, actor, "fail")
        if rej:
            return rej
        if retryable and row["attempt"] < row["max_attempts"]:
            out = _release_or_fail(conn, row, actor, f"worker failed (retryable): {reason_txt}", "fail")
        else:
            cands = reassign_candidates()
            conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?, reassign_flag=1,
                            reassign_candidates=?, updated_at=? WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                         (reason_txt, json.dumps(cands), now(), wid, lease_id))
            _audit(conn, wid, "fail", actor, "FAILED", lease_id=lease_id, attempt=row["attempt"], from_state="CLAIMED",
                   to_state="FAILED", sha256=rsha, detail={"reason": reason_txt, "reassign_candidates": cands,
                                                           "metered_fallback": False})
            out = {"work_item_id": wid, "to": "FAILED", "attempt": row["attempt"], "old_ref": row["doorbell_ref"],
                   "reassign_candidates": cands}
    _after_release(out, bell, actor)
    if out["to"] == "AVAILABLE":
        return _result(True, "RELEASED_FOR_RETRY", wid, attempt=out["attempt"], reason_sha256=rsha)
    return _result(True, "FAILED", wid, reason_sha256=rsha, reassign_flag=True,
                   reassign_candidates=out["reassign_candidates"])


def _after_release(out: dict[str, Any], bell: Any, actor: str) -> None:
    wid = out["work_item_id"]
    if out["to"] == "AVAILABLE":
        _set_dispatch(wid, "AVAILABLE")
        _emit("grok_bridge.released", wid, {"attempt": out["attempt"], "actor": actor})
        _close_ref(wid, out.get("old_ref"), "RE_RUNG", bell, actor)
        ring(wid, doorbell=bell, actor=actor)
    else:
        _set_dispatch(wid, "FAILED")
        _walk(wid, "EXCEPTION", "grok_bridge failed; flagged for reassignment (no metered fallback)")
        _emit("grok_bridge.failed", wid, {"attempt": out["attempt"], "actor": actor})
        _emit("grok_bridge.reassign_flagged", wid, {"candidates": out.get("reassign_candidates") or [],
                                                     "metered_fallback": False})
        _close_ref(wid, out.get("old_ref"), "FAILED", bell, actor)


def release_expired(*, actor: str = "wi-recovery", doorbell: Any = "env") -> dict[str, Any]:
    """Lease recovery: release expired leases (or fail them after max attempts) and re-ring unrung doorbells."""
    bell = _doorbell_default() if doorbell == "env" else doorbell
    conn = _connect()
    try:
        init_schema(conn)
        expired = [r["work_item_id"] for r in conn.execute(
            "SELECT work_item_id FROM grok_leases WHERE state='CLAIMED' AND lease_expires_at<=?", (now(),))]
    finally:
        conn.close()
    released, failed = [], []
    for wid in expired:
        with _Tx() as conn:
            row = _row(conn, wid)
            if row is None or row["state"] != "CLAIMED" or now() < row["lease_expires_at"]:
                continue  # someone completed/renewed it meanwhile
            _audit(conn, wid, "lease_expired", actor, "EXPIRED", lease_id=row["lease_id"], attempt=row["attempt"],
                   from_state="CLAIMED", detail={"expired_at": wita(row["lease_expires_at"]), "claimant": row["claimant"]})
            out = _release_or_fail(conn, row, actor, "lease expired", "release")
        _after_release(out, bell, actor)
        (released if out["to"] == "AVAILABLE" else failed).append(wid)
    # Re-ring AVAILABLE items whose doorbell never went out (failed, pending, or was disabled then enabled).
    conn = _connect()
    try:
        init_schema(conn)
        pending = [r["work_item_id"] for r in conn.execute(
            "SELECT work_item_id FROM grok_leases WHERE state='AVAILABLE' AND doorbell_state IN ('PENDING','FAILED','DISABLED')")]
    finally:
        conn.close()
    rerung = []
    for wid in pending:
        if wid in released:
            continue
        r = ring(wid, doorbell=bell, actor=actor)
        rerung.append({"work_item_id": wid, "code": r["code"]})
    return {"ok": True, "code": "RECOVERY_DONE", "released": released, "failed": failed, "rerung": rerung,
            "at": wita(now())}


def status(wid: str) -> dict[str, Any]:
    _check_wid(wid)
    conn = _connect()
    try:
        init_schema(conn)
        row = _row(conn, wid)
    finally:
        conn.close()
    if row is None:
        return _result(False, "NOT_OFFERED", wid)
    return _result(True, row["state"], wid, lease=public(row))


def audit_rows(wid: str | None = None) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        init_schema(conn)
        q = "SELECT * FROM grok_bridge_audit" + (" WHERE work_item_id=?" if wid else "") + " ORDER BY seq"
        return [dict(r) for r in conn.execute(q, (wid,) if wid else ())]
    finally:
        conn.close()


def verify_audit_chain() -> dict[str, Any]:
    rows = audit_rows()
    prev = None
    for r in rows:
        body = {k: r[k] for k in ("at", "at_wita", "work_item_id", "action", "actor", "lease_id", "attempt",
                                  "from_state", "to_state", "outcome", "sha256", "detail_json", "prev_row_sha256")}
        if r["prev_row_sha256"] != prev or sha256_bytes(json.dumps(body, sort_keys=True).encode()) != r["row_sha256"]:
            return {"ok": False, "broken_at_seq": r["seq"], "rows": len(rows)}
        prev = r["row_sha256"]
    return {"ok": True, "rows": len(rows), "head": prev}


# --------------------------------------------------------------------------- work item glue
def _set_dispatch(wid: str, bridge_state: str) -> None:
    try:
        work_items.update_fields(wid, dispatch={"worker": WORKER, "route": "grok_bridge", "bridge_state": bridge_state,
                                                "mode": "REAL (event-driven doorbell + lease)"})
    except Exception:  # noqa: BLE001
        pass


def _walk(wid: str, target: str, reason: str) -> dict[str, Any]:
    """Move the canonical item to `target` along the shortest legal path of the WI state machine."""
    try:
        item = work_items.get(wid)
        if item is None:
            return {"state": None, "walked": []}
        start = item["state"]
        if start == target:
            return {"state": start, "walked": []}
        prev: dict[str, str | None] = {start: None}
        q = deque([start])
        while q:
            s = q.popleft()
            if s == target:
                break
            for n in sorted(work_items.TRANSITIONS.get(s, ())):
                if n not in prev and (n == target or n not in work_items.TERMINAL):
                    prev[n] = s
                    q.append(n)
        if target not in prev:
            return {"state": start, "walked": [], "note": f"no legal path {start}->{target}"}
        path, s = [], target
        while s != start:
            path.append(s)
            s = prev[s]  # type: ignore[assignment]
        path.reverse()
        for s in path:
            work_items.transition(wid, s, reason=reason)
        return {"state": target, "walked": path}
    except Exception as exc:  # noqa: BLE001
        return {"state": None, "walked": [], "error": type(exc).__name__}
