"""Grok work bridge: event-driven claim/lease protocol for worker 'grok_bot'.

Canonical work items stay in WI (control_plane.sqlite). This module adds a lease
table next to them and an append-only, hash-chained, HMAC-signed audit table.
Every state change is a compare-and-set inside ONE SQLite transaction opened
with BEGIN IMMEDIATE, so across threads and processes exactly one caller wins.

    AVAILABLE --claim(nonce)--> CLAIMED(lease_id, claimant, claimed_at, lease_expires_at, attempt)
    CLAIMED --complete(lease_id, unexpired)--> COMPLETED
    CLAIMED --fail(lease_id, unexpired)--> FAILED            (or AVAILABLE, attempt+1, with --retryable)
    CLAIMED --lease expires--> AVAILABLE (attempt+1, new nonce)  ... after max_attempts --> FAILED

Guarantee (stated honestly): AT MOST ONE VALID LEASE at a time, AT-LEAST-ONCE
execution. If a lease expires while its holder is still working, the item can be
re-claimed and executed again; only the first valid COMPLETE is stored. Every
claim returns an idempotency_key (work_item_id + attempt) and the stable
work_item_id; side-effecting tasks must honour them.

Eligibility is an ALLOWLIST enforced in the store, inside the claim
transaction: only canonical states in CLAIMABLE_ITEM_STATES can be offered or
claimed. Owner-gated (NEEDS_YOU, DECISION_PENDING), terminal and every other
state never can. A worker result never walks an item through or out of an Owner
gate: complete() applies at most ONE direct, compare-and-set transition
(RUNNING -> READY_TO_TEST) and otherwise leaves the canonical state untouched.

GitHub is ONLY a doorbell (grok_doorbell.py): an issue holding the opaque work
item id and a WI-verified nonce. It is not the queue, state, payload store,
result store, audit authority, scheduler or control plane. WI never reads
GitHub; recovery works with GitHub unavailable.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from . import paths, real_evidence, work_items, worker_registry

TZ = ZoneInfo("Asia/Makassar")
WORKER = "grok_bot"                 # the INTENDED worker. Never used as an executor attribution.
REGISTRY_WORKER = "grok_bot_sub"
STATES = ("AVAILABLE", "CLAIMED", "COMPLETED", "FAILED")
DEFAULT_LEASE_SECONDS = 1800
MAX_LEASE_SECONDS = 4 * 3600
DEFAULT_MAX_ATTEMPTS = 3
MAX_RENEWALS = 12
MAX_RESULT_BYTES = 2 * 1024 * 1024
MAX_REASON_CHARS = 500

# ALLOWLIST of canonical WI states that permit machine execution. Anything else is refused.
CLAIMABLE_ITEM_STATES = frozenset({"DISPATCHED_SHADOW", "RUNNING"})
OWNER_GATED_ITEM_STATES = frozenset({"NEEDS_YOU", "DECISION_PENDING"})
assert CLAIMABLE_ITEM_STATES <= set(work_items.STATES)
assert not (OWNER_GATED_ITEM_STATES | work_items.TERMINAL) <= CLAIMABLE_ITEM_STATES

AUDIT_KEY_ENV = "WOLF_INTELLIGENCE_GROK_AUDIT_KEY_FILE"
ANCHOR_MIRROR_ENV = "WOLF_INTELLIGENCE_GROK_AUDIT_ANCHOR_MIRROR"
ANCHOR_FORMAT = "wi-grok-audit-anchor/1"
PIN_FORMAT = "wi-grok-audit-pin/1"
ANCHOR_LOG_FORMAT = "wi-grok-audit-anchor-log/1"
MIN_KEY_BYTES = 32

RESERVED_IDENTITIES = frozenset({
    "grok_bot", "grok_bot_sub", "wi", "wi-recovery", "overnight-tick", "cli", "peaches", "bridge", "grok_bridge",
})

_WID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_CLAIMANT = re.compile(r"^[A-Za-z0-9_.:@\-]{1,80}$")
_LEASE = re.compile(r"^lease_[0-9a-f]{24}$")

# Clock is injectable for tests (epoch seconds).
_now: Callable[[], float] = time.time


class AuditIntegrityError(RuntimeError):
    """The audit key is missing while signed rows exist. Fail closed: nothing is written."""


def now() -> float:
    return float(_now())


def wita(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, TZ).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def bridge_dir() -> Path:
    return paths.STATE_ROOT / "grok_bridge"


def results_dir() -> Path:
    return bridge_dir() / "results"


def audit_key_path() -> Path:
    env = os.environ.get(AUDIT_KEY_ENV, "").strip()
    return Path(env) if env else bridge_dir() / "keys" / "audit-hmac.key"


def anchor_path() -> Path:
    return bridge_dir() / "audit-anchor.json"


def pin_path() -> Path:
    return bridge_dir() / "audit-pin.json"


def anchor_log_path() -> Path:
    return bridge_dir() / "audit-anchor-log.jsonl"


def idempotency_key(wid: str, attempt: int) -> str:
    return f"{wid}:attempt-{int(attempt)}"


# --------------------------------------------------------------------------- audit key + anchor
def _read_key_bytes() -> bytes | None:
    p = audit_key_path()
    if not p.exists():
        return None
    try:
        raw = p.read_text().strip()
        return bytes.fromhex(raw) if raw else b""
    except (OSError, ValueError):
        return None


def _write_key_atomically(key_hex: str) -> None:
    p = audit_key_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_name(f".{p.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(key_hex + "\n")
    try:
        os.link(str(tmp), str(p))
    except FileExistsError:
        pass
    finally:
        tmp.unlink(missing_ok=True)


def _pin_body_mac(key: bytes, body: dict[str, Any]) -> str:
    return _mac(key, json.dumps({k: v for k, v in body.items() if k != "pin_hmac"}, sort_keys=True))


def _write_pin(key: bytes, legacy_max_seq: int) -> None:
    body = {"format": PIN_FORMAT, "legacy_max_seq": int(legacy_max_seq), "created_at": wita(now())}
    body["pin_hmac"] = _pin_body_mac(key, body)
    p = pin_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps(body, sort_keys=True) + "\n")
    os.replace(tmp, p)


def _read_pin() -> dict[str, Any] | None:
    try:
        return json.loads(pin_path().read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"format": "UNREADABLE"}


def _load_key(*, create: bool, conn: sqlite3.Connection | None = None) -> bytes | None:
    """HMAC key in a 0600 file OUTSIDE the database. Created once (atomic link), never printed."""
    p = audit_key_path()
    if not p.exists():
        if not create:
            return None
        key_hex = secrets.token_hex(MIN_KEY_BYTES)
        _write_key_atomically(key_hex)
        key = bytes.fromhex(key_hex)
        legacy_max = 0
        if conn is not None:
            row = conn.execute("SELECT MAX(seq) AS s FROM grok_bridge_audit").fetchone()
            legacy_max = int(row["s"] or 0)
        _write_pin(key, legacy_max)
        return key
    key = _read_key_bytes()
    if key is None:
        return None
    if len(key) < MIN_KEY_BYTES:
        raise AuditIntegrityError("audit HMAC key too short")
    return key


def _mac(key: bytes, msg: str) -> str:
    return hmac.new(key, msg.encode(), hashlib.sha256).hexdigest()


def _anchor_body_mac(key: bytes, body: dict[str, Any]) -> str:
    return _mac(key, json.dumps({k: v for k, v in body.items() if k != "anchor_hmac"}, sort_keys=True))


def _read_anchor() -> dict[str, Any] | None:
    try:
        return json.loads(anchor_path().read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"format": "UNREADABLE"}


def _read_anchor_log() -> list[dict[str, Any]]:
    p = anchor_log_path()
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    except (OSError, ValueError):
        return [{"format": "UNREADABLE"}]
    return out


def _log_entry_mac(key: bytes, entry: dict[str, Any]) -> str:
    return _mac(key, json.dumps({k: v for k, v in entry.items() if k != "log_hmac"}, sort_keys=True))


def _append_anchor_log(key: bytes, body: dict[str, Any]) -> None:
    entry = {"format": ANCHOR_LOG_FORMAT, "seq": body["seq"], "row_sha256": body["row_sha256"],
             "rows": body["rows"], "hmac_from_seq": body["hmac_from_seq"], "updated_at": body["updated_at"]}
    entry["log_hmac"] = _log_entry_mac(key, entry)
    text = json.dumps(entry, sort_keys=True) + "\n"
    p = anchor_log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(text)
    mirror = os.environ.get(ANCHOR_MIRROR_ENV, "").strip()
    if mirror:
        mp = Path(mirror) / "audit-anchor-log.jsonl"
        mp.parent.mkdir(parents=True, exist_ok=True)
        with open(mp, "a", encoding="utf-8") as fh:
            fh.write(text)


def _verify_existing_anchor(conn: sqlite3.Connection, anchor: dict[str, Any], head_at_start: int | None) -> None:
    """Refuse to commit if the on-disk anchor no longer matches the DB (truncation/replay guard)."""
    row = conn.execute("SELECT row_sha256 FROM grok_bridge_audit WHERE seq=?", (anchor["seq"],)).fetchone()
    if row is None or row["row_sha256"] != anchor["row_sha256"]:
        raise AuditIntegrityError("anchor no longer matches DB")
    if head_at_start is not None and anchor["seq"] > head_at_start:
        raise AuditIntegrityError("anchor seq ahead of transaction start head")


def _write_anchor(conn: sqlite3.Connection, key: bytes) -> str | None:
    """Write the head anchor (inside the write transaction, so writers are serialized). Returns prior text."""
    head = conn.execute("SELECT seq, row_sha256 FROM grok_bridge_audit ORDER BY seq DESC LIMIT 1").fetchone()
    if head is None:
        return None
    first = conn.execute("SELECT MIN(seq) AS s FROM grok_bridge_audit WHERE row_hmac IS NOT NULL").fetchone()["s"]
    count = conn.execute("SELECT COUNT(*) AS n FROM grok_bridge_audit").fetchone()["n"]
    body = {"format": ANCHOR_FORMAT, "seq": head["seq"], "row_sha256": head["row_sha256"], "rows": count,
            "hmac_from_seq": first, "updated_at": wita(now())}
    body["anchor_hmac"] = _anchor_body_mac(key, body)
    p = anchor_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    prior = p.read_text() if p.exists() else None
    tmp = p.with_name(f".{p.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps(body, sort_keys=True) + "\n")
    os.replace(tmp, p)
    _append_anchor_log(key, body)
    return prior


def _restore_anchor(prior: str | None) -> None:
    p = anchor_path()
    try:
        if prior is None:
            p.unlink(missing_ok=True)
        else:
            tmp = p.with_name(f".{p.name}.{secrets.token_hex(4)}.tmp")
            fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write(prior if prior.endswith("\n") else prior + "\n")
            os.replace(tmp, p)
    except OSError:
        pass


# --------------------------------------------------------------------------- store
def _connect() -> sqlite3.Connection:
    paths.ensure_dirs()
    conn = sqlite3.connect(str(paths.SQLITE_PATH), timeout=60, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_LEASE_EXTRA_COLS = {"dispatcher": "TEXT", "executed_by": "TEXT", "completed_by": "TEXT", "completed_at": "REAL"}


def init_schema(conn: sqlite3.Connection) -> None:
    """Create/migrate the bridge tables. Always called inside BEGIN IMMEDIATE (see _Tx)."""
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
    have = {r["name"] for r in conn.execute("PRAGMA table_info(grok_leases)")}
    for col, typ in _LEASE_EXTRA_COLS.items():
        if col not in have:
            conn.execute(f"ALTER TABLE grok_leases ADD COLUMN {col} {typ}")
    if "row_hmac" not in {r["name"] for r in conn.execute("PRAGMA table_info(grok_bridge_audit)")}:
        conn.execute("ALTER TABLE grok_bridge_audit ADD COLUMN row_hmac TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_grok_leases_state ON grok_leases(state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_grok_audit_item ON grok_bridge_audit(work_item_id)")
    # Append-only: prior audit rows can never be rewritten or deleted through SQL. Corrections are new rows.
    conn.execute("""CREATE TRIGGER IF NOT EXISTS grok_audit_no_update BEFORE UPDATE ON grok_bridge_audit
                    BEGIN SELECT RAISE(ABORT, 'grok_bridge_audit is append-only'); END""")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS grok_audit_no_delete BEFORE DELETE ON grok_bridge_audit
                    BEGIN SELECT RAISE(ABORT, 'grok_bridge_audit is append-only'); END""")


def _audit(conn: sqlite3.Connection, wid: str, action: str, actor: str, outcome: str, *, lease_id: str | None = None,
           attempt: int | None = None, from_state: str | None = None, to_state: str | None = None,
           sha256: str | None = None, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    """Append one audit row inside the caller's transaction. Rows are hash-chained and HMAC-signed."""
    signed_exist = conn.execute("SELECT 1 FROM grok_bridge_audit WHERE row_hmac IS NOT NULL LIMIT 1").fetchone()
    key = _load_key(create=signed_exist is None, conn=conn)
    if key is None:
        raise AuditIntegrityError("audit HMAC key missing while signed rows exist")
    ts = now()
    prev = conn.execute("SELECT row_sha256 FROM grok_bridge_audit ORDER BY seq DESC LIMIT 1").fetchone()
    prev_sha = prev["row_sha256"] if prev else None
    row = {"at": ts, "at_wita": wita(ts), "work_item_id": wid, "action": action, "actor": actor, "lease_id": lease_id,
           "attempt": attempt, "from_state": from_state, "to_state": to_state, "outcome": outcome, "sha256": sha256,
           "detail_json": json.dumps(detail or {}, sort_keys=True), "prev_row_sha256": prev_sha}
    row_sha = sha256_bytes(json.dumps(row, sort_keys=True).encode())
    row_mac = _mac(key, row_sha)
    conn.execute(
        """INSERT INTO grok_bridge_audit (at, at_wita, work_item_id, action, actor, lease_id, attempt, from_state,
           to_state, outcome, sha256, detail_json, prev_row_sha256, row_sha256, row_hmac)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ts, row["at_wita"], wid, action, actor, lease_id, attempt, from_state, to_state, outcome, sha256,
         row["detail_json"], prev_sha, row_sha, row_mac))
    row["row_sha256"] = row_sha
    return row


def _row(conn: sqlite3.Connection, wid: str) -> dict[str, Any] | None:
    r = conn.execute("SELECT * FROM grok_leases WHERE work_item_id=?", (wid,)).fetchone()
    return dict(r) if r else None


def _item_state(conn: sqlite3.Connection, wid: str) -> str | None:
    """Canonical WI state read inside the caller's transaction (same database file)."""
    try:
        r = conn.execute("SELECT state FROM work_items WHERE id=?", (wid,)).fetchone()
    except sqlite3.OperationalError:
        return None
    return r["state"] if r else None


def _item_dispatch(conn: sqlite3.Connection, wid: str) -> dict[str, Any] | None:
    try:
        r = conn.execute("SELECT dispatch_json FROM work_items WHERE id=?", (wid,)).fetchone()
    except sqlite3.OperationalError:
        return None
    if not r or not r["dispatch_json"]:
        return None
    try:
        return json.loads(r["dispatch_json"])
    except json.JSONDecodeError:
        return None


def _item_claimable(conn: sqlite3.Connection, wid: str) -> tuple[bool, str | None, dict[str, Any] | None]:
    state = _item_state(conn, wid)
    dispatch = _item_dispatch(conn, wid)
    return claimable(state, dispatch), state, dispatch


_tx_depth = threading.local()


class _Tx:
    """BEGIN IMMEDIATE ... COMMIT (ROLLBACK on any exception). Re-anchors the audit head before COMMIT."""

    def __init__(self) -> None:
        self.conn = _connect()
        self._head0: int | None = None

    def __enter__(self) -> sqlite3.Connection:
        if getattr(_tx_depth, "active", False):
            raise RuntimeError("nested _Tx")
        _tx_depth.active = True
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            init_schema(self.conn)
            self._head0 = self.conn.execute("SELECT MAX(seq) AS s FROM grok_bridge_audit").fetchone()["s"]
        except BaseException:
            _tx_depth.active = False
            self.conn.execute("ROLLBACK")
            self.conn.close()
            raise
        return self.conn

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is not None:
                self.conn.execute("ROLLBACK")
                return
            head = self.conn.execute("SELECT MAX(seq) AS s FROM grok_bridge_audit").fetchone()["s"]
            prior, anchored = None, False
            if head != self._head0:
                key = _load_key(create=False)
                if key is not None:
                    existing = _read_anchor()
                    if existing is not None:
                        _verify_existing_anchor(self.conn, existing, self._head0)
                    prior, anchored = _write_anchor(self.conn, key), True
            try:
                self.conn.execute("COMMIT")
            except BaseException:
                if anchored:
                    _restore_anchor(prior)
                raise
        finally:
            _tx_depth.active = False
            self.conn.close()


def _emit(event_type: str, wid: str, payload: dict[str, Any]) -> None:
    """Mirror to the canonical event bus after commit. The audit table is authoritative; never crash here."""
    try:
        from . import events
        events.emit(event_type, payload, work_item_id=wid)
    except Exception:  # noqa: BLE001
        pass


def public(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Lease view safe to print (no result text, no task content, no nonce)."""
    if row is None:
        return None
    out = {k: row.get(k) for k in ("work_item_id", "worker", "state", "lease_id", "claimant", "attempt",
                                    "max_attempts", "lease_seconds", "renewals", "doorbell_state", "doorbell_ref",
                                    "doorbell_error", "doorbell_rings", "result_sha256", "evidence_sha256",
                                    "failure_reason", "reassign_flag", "dispatcher", "executed_by", "completed_by")}
    for k in ("claimed_at", "lease_expires_at", "offered_at", "updated_at", "completed_at"):
        out[k] = wita(row.get(k))
    out["claimed_by"] = row.get("claimant")
    out["intended_worker"] = row.get("worker")
    out["reassign_flag"] = bool(row.get("reassign_flag"))
    out["reassign_candidates"] = json.loads(row["reassign_candidates"]) if row.get("reassign_candidates") else []
    return out


def _result(ok: bool, code: str, wid: str, **extra: Any) -> dict[str, Any]:
    return {"ok": ok, "code": code, "work_item_id": wid, **extra}


def _check_wid(wid: str) -> None:
    if not isinstance(wid, str) or not _WID.match(wid):
        raise ValueError("bad work item id")


def _check_ident(name: str, what: str) -> str:
    if not isinstance(name, str) or not _CLAIMANT.match(name):
        raise ValueError(f"bad {what}")
    return name


def _reserved_identity(name: str | None, *, dispatcher: str | None = None) -> bool:
    if not name:
        return False
    return name in RESERVED_IDENTITIES or name == dispatcher


def _safe_followup(result: dict[str, Any], fn: Callable[[], None]) -> dict[str, Any]:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        result["followup_error"] = type(exc).__name__
    return result


def _safe_item_update(result: dict[str, Any], fn: Callable[[], None]) -> dict[str, Any]:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        result["item_update_error"] = type(exc).__name__
    return result


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


def claimable(item_state: str | None, dispatch: dict[str, Any] | None = None) -> bool:
    if item_state == "DISPATCHED_SHADOW":
        return True
    if item_state == "RUNNING" and dispatch and dispatch.get("route") == "grok_bridge":
        return True
    return False


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
                   detail={"note": "doorbell off (WOLF_INTELLIGENCE_GROK_DOORBELL unset); WI state unaffected"})
            return _result(True, "DOORBELL_DISABLED", wid)
    # Network call outside the transaction. WI only WRITES to GitHub; it never reads state back from it.
    try:
        info = bell.ring(wid, nonce)
        err = None
    except Exception as exc:  # noqa: BLE001 - a doorbell must never crash WI
        info, err = None, real_evidence.redact(f"{type(exc).__name__}: {exc}")[:300]
    with _Tx() as conn:
        row = _row(conn, wid)
        still = row is not None and row["state"] == "AVAILABLE" and row["nonce"] == nonce
        if err is None:
            if not isinstance(info, dict) or not isinstance(info.get("ref"), str):
                err = "doorbell returned invalid info"
                info = None
            else:
                ref = str(info.get("ref") or "")
                if still:
                    conn.execute("""UPDATE grok_leases SET doorbell_state='RUNG', doorbell_ref=?, doorbell_error=NULL,
                                    doorbell_rings=doorbell_rings+1, updated_at=? WHERE work_item_id=?""", (ref, now(), wid))
                _audit(conn, wid, "doorbell_ring", actor, "RUNG" if still else "RUNG_STALE", attempt=attempt,
                       detail={"ref": ref, "kind": getattr(bell, "kind", type(bell).__name__),
                               "assigned": info.get("assigned")})
        if err is not None:
            if still:
                conn.execute("""UPDATE grok_leases SET doorbell_state='FAILED', doorbell_error=?,
                                doorbell_rings=doorbell_rings+1, updated_at=? WHERE work_item_id=?""", (err, now(), wid))
            _audit(conn, wid, "doorbell_ring", actor, "FAILED", attempt=attempt, detail={"error": err})
    if err is None and isinstance(info, dict):
        ref = str(info.get("ref") or "")
        _emit("grok_bridge.doorbell_rung", wid, {"ref": ref, "attempt": attempt, "actor": actor})
        if not still:
            _close_ref(wid, ref, "SUPERSEDED", bell, actor)
        return _result(True, "DOORBELL_RUNG", wid, doorbell_ref=ref)
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


def _close_ref(wid: str, ref: str | None, outcome: str, bell: Any, actor: str, *, triggered_by: str | None = None) -> None:
    if not ref or bell is None:
        return
    try:
        bell.close(ref, outcome)
        res, err = "CLOSED", None
    except Exception as exc:  # noqa: BLE001
        res, err = "FAILED", real_evidence.redact(f"{type(exc).__name__}: {exc}")[:300]
    try:
        detail: dict[str, Any] = {"ref": ref, "outcome": outcome, "error": err}
        if triggered_by:
            detail["triggered_by"] = triggered_by
        with _Tx() as conn:
            if res == "CLOSED":
                conn.execute("UPDATE grok_leases SET doorbell_state='CLOSED' WHERE work_item_id=? AND doorbell_ref=?",
                             (wid, ref))
            _audit(conn, wid, "doorbell_close", actor, res, detail=detail)
    except Exception:  # noqa: BLE001
        pass
    _emit("grok_bridge.doorbell_closed", wid, {"ref": ref, "outcome": outcome, "result": res})


# --------------------------------------------------------------------------- protocol
def offer(wid: str, *, lease_seconds: int = DEFAULT_LEASE_SECONDS, max_attempts: int = DEFAULT_MAX_ATTEMPTS,
          actor: str = "wi", doorbell: Any = "env") -> dict[str, Any]:
    """WI-side only: make a canonical WI work item AVAILABLE to grok_bot and ring the doorbell immediately.

    `actor` is recorded as the dispatcher. The item's canonical state must be in CLAIMABLE_ITEM_STATES.
    """
    _check_wid(wid)
    _check_ident(actor, "dispatcher")
    if not (60 <= int(lease_seconds) <= MAX_LEASE_SECONDS):
        raise ValueError(f"lease_seconds must be 60..{MAX_LEASE_SECONDS}")
    if not (1 <= int(max_attempts) <= 10):
        raise ValueError("max_attempts must be 1..10")
    if work_items.get(wid) is None:
        return _result(False, "NOT_FOUND", wid)
    with _Tx() as conn:
        item_ok, item_state, _dispatch = _item_claimable(conn, wid)
        if not item_ok:
            code = "ITEM_TERMINAL" if item_state in work_items.TERMINAL else "ITEM_NOT_CLAIMABLE"
            _audit(conn, wid, "offer", actor, code, detail={"item_state": item_state,
                                                             "claimable_states": sorted(CLAIMABLE_ITEM_STATES)})
            return _result(False, code, wid, item_state=item_state, claimable_states=sorted(CLAIMABLE_ITEM_STATES))
        row = _row(conn, wid)
        if row is not None:
            code = "ALREADY_OFFERED" if row["state"] in ("AVAILABLE", "CLAIMED") else "ALREADY_FINISHED"
            _audit(conn, wid, "offer", actor, code, attempt=row["attempt"], from_state=row["state"])
            return _result(False, code, wid, lease=public(row))
        ts = now()
        nonce = secrets.token_hex(16)
        conn.execute("""INSERT INTO grok_leases (work_item_id, worker, state, nonce, attempt, max_attempts, lease_seconds,
                        offered_at, updated_at, dispatcher) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                     (wid, WORKER, "AVAILABLE", nonce, 1, int(max_attempts), int(lease_seconds), ts, ts, actor))
        _audit(conn, wid, "offer", actor, "OFFERED", attempt=1, to_state="AVAILABLE",
               detail={"lease_seconds": int(lease_seconds), "max_attempts": int(max_attempts), "dispatcher": actor,
                       "intended_worker": WORKER, "item_state": item_state})
    _set_dispatch(wid, "AVAILABLE", dispatcher=actor)
    _emit("grok_bridge.offered", wid, {"worker": WORKER, "attempt": 1, "dispatcher": actor})
    bell = ring(wid, doorbell=doorbell, actor=actor)
    with _Tx() as conn:
        row = _row(conn, wid)
    return _result(True, "OFFERED", wid, lease=public(row), doorbell=bell)


def claim(wid: str, *, claimant: str, nonce: str) -> dict[str, Any]:
    """Atomic compare-and-set AVAILABLE -> CLAIMED. Exactly one caller wins; others get ALREADY_CLAIMED.

    The canonical item's state is re-checked against the allowlist inside the same transaction.
    """
    _check_wid(wid)
    _check_ident(claimant, "claimant")
    moved = None
    lease_id = ""
    ts = 0.0
    expires = 0.0
    attempt = 0
    item_state: str | None = None
    dispatcher: str | None = None
    row: dict[str, Any] | None = None
    with _Tx() as conn:
        row = _row(conn, wid)
        if row is None:
            _audit(conn, wid, "claim", claimant, "NOT_OFFERED")
            return _result(False, "NOT_OFFERED", wid)
        state, attempt = row["state"], row["attempt"]
        dispatcher = row.get("dispatcher")
        if _reserved_identity(claimant, dispatcher=dispatcher):
            _audit(conn, wid, "claim", claimant, "RESERVED_IDENTITY", attempt=attempt, from_state=state,
                   detail={"claimant": claimant, "dispatcher": dispatcher})
            return _result(False, "RESERVED_IDENTITY", wid)
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
        item_ok, item_state, dispatch = _item_claimable(conn, wid)
        if not item_ok:
            _audit(conn, wid, "claim", claimant, "ITEM_NOT_CLAIMABLE", attempt=attempt, from_state=state,
                   detail={"item_state": item_state})
            return _result(False, "ITEM_NOT_CLAIMABLE", wid, item_state=item_state,
                           message="the canonical WI item is not in a machine-executable state; do not execute")
        ts = now()
        lease_id = "lease_" + secrets.token_hex(12)
        expires = ts + row["lease_seconds"]
        cur = conn.execute("""UPDATE grok_leases SET state='CLAIMED', lease_id=?, claimant=?, claimed_at=?,
                              lease_expires_at=?, renewals=0, executed_by=NULL, completed_by=NULL, completed_at=NULL,
                              updated_at=? WHERE work_item_id=? AND state='AVAILABLE' AND nonce=?""",
                           (lease_id, claimant, ts, expires, ts, wid, row["nonce"]))
        if cur.rowcount != 1:
            _audit(conn, wid, "claim", claimant, "ALREADY_CLAIMED", attempt=attempt, from_state=state)
            return _result(False, "ALREADY_CLAIMED", wid)
        _audit(conn, wid, "claim", claimant, "CLAIMED", lease_id=lease_id, attempt=attempt, from_state="AVAILABLE",
               to_state="CLAIMED", detail={"lease_expires_at": wita(expires), "claimed_by": claimant,
                                           "dispatcher": dispatcher, "item_state": item_state,
                                           "idempotency_key": idempotency_key(wid, attempt)})
    result = _result(True, "CLAIMED", wid, lease_id=lease_id, claimant=claimant, attempt=attempt,
                     claimed_at=wita(ts), lease_expires_at=wita(expires), lease_seconds=row["lease_seconds"],
                     idempotency_key=idempotency_key(wid, attempt))

    def _post_claim() -> None:
        nonlocal moved
        if item_state == "DISPATCHED_SHADOW":
            moved = work_items.transition_if(wid, "DISPATCHED_SHADOW", "RUNNING",
                                             reason=f"grok_bridge claimed by {claimant} ({lease_id})")
            if moved is None:
                cur_item = work_items.get(wid) or {}
                if not claimable(cur_item.get("state"), cur_item.get("dispatch")):
                    with _Tx() as conn:
                        cur = conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?,
                                              updated_at=? WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                                             ("item left machine-executable state before RUNNING transition",
                                              now(), wid, lease_id))
                        if cur.rowcount == 1:
                            _audit(conn, wid, "claim", claimant, "LEASE_REVOKED", lease_id=lease_id, attempt=attempt,
                                   from_state="CLAIMED", to_state="FAILED",
                                   detail={"reason": "item no longer claimable after claim commit"})
                    raise RuntimeError("ITEM_NOT_CLAIMABLE")
        _set_dispatch(wid, "CLAIMED", dispatcher=dispatcher, claimed_by=claimant)
        _emit("grok_bridge.claimed", wid, {"lease_id": lease_id, "claimant": claimant, "attempt": attempt})

    try:
        _post_claim()
    except RuntimeError as exc:
        if str(exc) == "ITEM_NOT_CLAIMABLE":
            return _result(False, "ITEM_NOT_CLAIMABLE", wid, item_state=(work_items.get(wid) or {}).get("state"),
                           message="the canonical WI item is not in a machine-executable state; do not execute")
        raise
    except Exception as exc:
        result["item_update_error"] = type(exc).__name__
        if str(exc) == "ITEM_NOT_CLAIMABLE":
            return _result(False, "ITEM_NOT_CLAIMABLE", wid)

    item = work_items.get(wid) or {}
    result["item_state"] = (moved or item).get("state")
    result["task"] = {"title": item.get("title"), "kind": item.get("kind"),
                      "payload": item.get("payload") or {}, "tags": item.get("tags") or []}
    return result


def _holder_of(conn: sqlite3.Connection, wid: str, lease_id: str | None) -> str | None:
    """Who was granted `lease_id` (from the audit's CLAIMED row). Possession of a lease identifies its holder."""
    if not lease_id or not _LEASE.match(lease_id):
        return None
    r = conn.execute("""SELECT actor FROM grok_bridge_audit WHERE work_item_id=? AND action='claim' AND outcome='CLAIMED'
                        AND lease_id=? ORDER BY seq LIMIT 1""", (wid, lease_id)).fetchone()
    return r["actor"] if r else None


def _lease_check(conn, wid: str, lease_id: str, caller: str | None, action: str) -> tuple[dict | None, dict | None]:
    """Shared lease validation. Rejections are attributed to the caller (or unidentified-caller)."""
    row = _row(conn, wid)
    holder = _holder_of(conn, wid, lease_id)
    actor = caller or "unidentified-caller"
    det: dict[str, Any] = {}
    if caller:
        det["caller"] = caller
    if holder:
        det["lease_holder"] = holder
    if row is None:
        _audit(conn, wid, action, actor, "NOT_OFFERED", lease_id=lease_id, detail=det)
        return None, _result(False, "NOT_OFFERED", wid)
    if not isinstance(lease_id, str) or not _LEASE.match(lease_id):
        _audit(conn, wid, action, actor, "BAD_LEASE_ID", attempt=row["attempt"], from_state=row["state"], detail=det)
        return None, _result(False, "BAD_LEASE_ID", wid)
    if row["state"] == "COMPLETED" and row["lease_id"] == lease_id:
        _audit(conn, wid, action, actor, "ALREADY_COMPLETED", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"], detail=det)
        return None, _result(False, "ALREADY_COMPLETED", wid, result_sha256=row["result_sha256"])
    if row["state"] == "FAILED" and row["lease_id"] == lease_id:
        _audit(conn, wid, action, actor, "ALREADY_FAILED", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"], detail=det)
        return None, _result(False, "ALREADY_FAILED", wid)
    if row["state"] != "CLAIMED" or row["lease_id"] != lease_id:
        _audit(conn, wid, action, actor, "STALE_LEASE", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"], detail={**det, "reason": "lease not current",
                                                "current_holder": row.get("claimant")})
        return None, _result(False, "STALE_LEASE", wid, state=row["state"],
                             message="this lease is no longer current; do not retry with it")
    if now() >= row["lease_expires_at"]:
        _audit(conn, wid, action, actor, "STALE_LEASE", lease_id=lease_id, attempt=row["attempt"],
               from_state=row["state"], detail={**det, "reason": "lease expired",
                                                "expired_at": wita(row["lease_expires_at"])})
        return None, _result(False, "STALE_LEASE", wid, state=row["state"], message="lease expired")
    return row, None


def renew(wid: str, *, lease_id: str, caller: str | None = None) -> dict[str, Any]:
    _check_wid(wid)
    if caller is not None:
        _check_ident(caller, "caller")
    with _Tx() as conn:
        row, rej = _lease_check(conn, wid, lease_id, caller, "renew")
        if rej:
            return rej
        holder = row["claimant"]
        if _reserved_identity(caller, dispatcher=row.get("dispatcher")):
            _audit(conn, wid, "renew", caller or "unidentified-caller", "RESERVED_IDENTITY", lease_id=lease_id,
                   attempt=row["attempt"], detail={"caller": caller, "lease_holder": holder})
            return _result(False, "RESERVED_IDENTITY", wid)
        item_ok, item_state, _dispatch = _item_claimable(conn, wid)
        if not item_ok:
            _audit(conn, wid, "renew", holder, "ITEM_NOT_CLAIMABLE", lease_id=lease_id, attempt=row["attempt"],
                   detail={"item_state": item_state, **({"caller": caller} if caller else {})})
            return _result(False, "ITEM_NOT_CLAIMABLE", wid, item_state=item_state)
        if row["renewals"] >= MAX_RENEWALS:
            _audit(conn, wid, "renew", holder, "RENEWAL_LIMIT", lease_id=lease_id, attempt=row["attempt"])
            return _result(False, "RENEWAL_LIMIT", wid)
        expires = now() + row["lease_seconds"]
        conn.execute("UPDATE grok_leases SET lease_expires_at=?, renewals=renewals+1, updated_at=? WHERE work_item_id=?",
                     (expires, now(), wid))
        _audit(conn, wid, "renew", holder, "RENEWED", lease_id=lease_id, attempt=row["attempt"],
               detail={"lease_expires_at": wita(expires), **({"caller": caller} if caller else {})})
    _emit("grok_bridge.renewed", wid, {"lease_id": lease_id, "claimant": holder})
    return _result(True, "RENEWED", wid, lease_id=lease_id, lease_expires_at=wita(expires))


def complete(wid: str, *, lease_id: str, result: bytes | str, evidence: bytes | str | None = None,
             executed_by: str | None = None, caller: str | None = None, doorbell: Any = "env") -> dict[str, Any]:
    """CLAIMED -> COMPLETED with the matching, unexpired lease. Stores the result in WI state with its sha256."""
    _check_wid(wid)
    if executed_by is not None:
        _check_ident(executed_by, "executed_by")
    if caller is not None:
        _check_ident(caller, "caller")
    if not isinstance(lease_id, str) or not _LEASE.match(lease_id):
        with _Tx() as conn:
            _row_unused, rej = _lease_check(conn, wid, lease_id, caller, "complete")
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
            actor = caller or "unidentified-caller"
            holder = _holder_of(conn, wid, lease_id)
            det = {"caller": caller} if caller else {}
            if holder:
                det["lease_holder"] = holder
            _audit(conn, wid, "complete", actor, "SECRET_SHAPED_REJECTED", lease_id=lease_id,
                   sha256=sha256_bytes(rb), detail=det)
        return _result(False, "SECRET_SHAPED_REJECTED", wid,
                       message="result looks like it contains a secret; redact and retry with the same lease")
    rsha = sha256_bytes(rb)
    esha = sha256_bytes(eb) if eb is not None else None
    outdir = results_dir() / wid
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = outdir / f".{lease_id}.{secrets.token_hex(4)}.tmp"
    tmp.write_bytes(rb)
    final = outdir / f"{lease_id}.result"
    bell = _doorbell_default() if doorbell == "env" else doorbell
    holder = ""
    ref: str | None = None
    ident: dict[str, Any] = {}
    quarantined: dict[str, Any] | None = None
    quarantine_ref: str | None = None
    try:
        with _Tx() as conn:
            row, rej = _lease_check(conn, wid, lease_id, caller, "complete")
            if rej:
                return rej
            holder = row["claimant"]
            executor = executed_by or holder
            if _reserved_identity(executor, dispatcher=row.get("dispatcher")) or _reserved_identity(caller, dispatcher=row.get("dispatcher")):
                actor = caller or "unidentified-caller"
                _audit(conn, wid, "complete", actor, "RESERVED_IDENTITY", lease_id=lease_id, attempt=row["attempt"],
                       detail={"executed_by": executor, "caller": caller, "lease_holder": holder})
                return _result(False, "RESERVED_IDENTITY", wid)
            item_ok, item_state, _dispatch = _item_claimable(conn, wid)
            if not item_ok:
                qdir = outdir / "quarantine"
                qdir.mkdir(parents=True, exist_ok=True)
                qpath = qdir / f"{lease_id}.result"
                qpath.write_bytes(rb)
                reason = f"item left machine-executable state: {item_state}"
                conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?, result_sha256=?, result_path=?,
                                reassign_flag=0, updated_at=? WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                             (reason, rsha, str(qpath), now(), wid, lease_id))
                _audit(conn, wid, "complete", holder, "RESULT_QUARANTINED", lease_id=lease_id, attempt=row["attempt"],
                       from_state="CLAIMED", to_state="FAILED", sha256=rsha,
                       detail={"quarantine_path": str(qpath), "item_state": item_state,
                               **({"caller": caller} if caller else {})})
                quarantine_ref = row["doorbell_ref"]
                quarantined = _result(False, "RESULT_QUARANTINED", wid, item_state=item_state, result_sha256=rsha,
                                      quarantine_path=str(qpath))
            else:
                ts = now()
                ident = {"work_item_id": wid, "dispatcher": row.get("dispatcher"), "intended_worker": row["worker"],
                         "claimed_by": holder, "executed_by": executor, "completed_by": holder,
                         "executed_by_source": "declared_by_lease_holder" if executed_by else "defaulted_to_lease_holder",
                         "claimed_at": wita(row["claimed_at"]), "completed_at": wita(ts), "attempt": row["attempt"],
                         "result_sha256": rsha, "evidence_sha256": esha,
                         "idempotency_key": idempotency_key(wid, row["attempt"])}
                if caller and caller != holder:
                    ident["cli_caller"] = caller
                conn.execute("""UPDATE grok_leases SET state='COMPLETED', result_sha256=?, result_path=?, evidence_sha256=?,
                                executed_by=?, completed_by=?, completed_at=?, updated_at=?
                                WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                             (rsha, str(final), esha, executor, holder, ts, ts, wid, lease_id))
                _audit(conn, wid, "complete", holder, "COMPLETED", lease_id=lease_id, attempt=row["attempt"],
                       from_state="CLAIMED", to_state="COMPLETED", sha256=rsha,
                       detail={"result_bytes": len(rb), **ident, **({"caller": caller} if caller else {})})
                os.replace(tmp, final)
                if eb is not None:
                    (outdir / f"{lease_id}.evidence").write_bytes(eb)
                ref = row["doorbell_ref"]
    finally:
        if tmp.exists():
            tmp.unlink()
    if quarantined is not None:
        _close_ref(wid, quarantine_ref, "REVOKED", bell, "wi", triggered_by=holder)
        return quarantined
    result_out = _result(True, "COMPLETED", wid, lease_id=lease_id, result_sha256=rsha, evidence_sha256=esha,
                         claimed_by=holder, executed_by=ident.get("executed_by"), completed_by=holder)

    def _post_complete() -> None:
        work_items.update_fields(wid, result={"route": "grok_bridge", "lease_id": lease_id, "result_path": str(final),
                                              **ident})
        moved = work_items.transition_if(wid, "RUNNING", "READY_TO_TEST",
                                         reason=f"grok_bridge result from {ident['executed_by']} ({lease_id})") \
            if (work_items.get(wid) or {}).get("state") == "RUNNING" else None
        item_state = (moved or work_items.get(wid) or {}).get("state")
        result_out["item_state"] = item_state
        result_out["item_transition"] = ("RUNNING->READY_TO_TEST" if moved
                                         else "none (result recorded; canonical state left for WI/Owner)")
        _set_dispatch(wid, "COMPLETED", dispatcher=ident["dispatcher"], claimed_by=holder,
                      executed_by=ident["executed_by"])
        _emit("grok_bridge.completed", wid, {"lease_id": lease_id, "result_sha256": rsha, "evidence_sha256": esha,
                                             "claimed_by": holder, "executed_by": ident["executed_by"]})

    _safe_item_update(result_out, _post_complete)
    _safe_followup(result_out, lambda: _close_ref(wid, ref, "COMPLETED", bell, "wi", triggered_by=holder))
    return result_out


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
               detail={"reason": reason, "next_attempt": row["attempt"] + 1, "released_holder": row["claimant"]})
        return {"work_item_id": wid, "to": "AVAILABLE", "attempt": row["attempt"] + 1, "old_ref": row["doorbell_ref"]}
    cands = reassign_candidates()
    conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?, reassign_flag=1, reassign_candidates=?,
                    updated_at=? WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                 (f"{reason}; max_attempts_exhausted", json.dumps(cands), ts, wid, row["lease_id"]))
    _audit(conn, wid, action, actor, "FAILED_MAX_ATTEMPTS", lease_id=row["lease_id"], attempt=row["attempt"],
           from_state="CLAIMED", to_state="FAILED", sha256=sha256_bytes(reason.encode()),
           detail={"reason": reason, "reassign_candidates": cands, "metered_fallback": False,
                   "last_holder": row["claimant"]})
    return {"work_item_id": wid, "to": "FAILED", "attempt": row["attempt"], "old_ref": row["doorbell_ref"],
            "reassign_candidates": cands}


def fail(wid: str, *, lease_id: str, reason: str, retryable: bool = False, caller: str | None = None,
         doorbell: Any = "env") -> dict[str, Any]:
    """CLAIMED -> FAILED (default) or back to AVAILABLE with attempt+1 if retryable and attempts remain."""
    _check_wid(wid)
    if caller is not None:
        _check_ident(caller, "caller")
    reason_txt = real_evidence.redact(str(reason or "").strip())[:MAX_REASON_CHARS] or "unspecified"
    rsha = sha256_bytes(reason_txt.encode())
    bell = _doorbell_default() if doorbell == "env" else doorbell
    holder = ""
    out: dict[str, Any] = {}
    with _Tx() as conn:
        row, rej = _lease_check(conn, wid, lease_id, caller, "fail")
        if rej:
            return rej
        holder = row["claimant"]
        if _reserved_identity(caller, dispatcher=row.get("dispatcher")):
            actor = caller or "unidentified-caller"
            _audit(conn, wid, "fail", actor, "RESERVED_IDENTITY", lease_id=lease_id, attempt=row["attempt"],
                   detail={"caller": caller, "lease_holder": holder})
            return _result(False, "RESERVED_IDENTITY", wid)
        if retryable and row["attempt"] < row["max_attempts"]:
            out = _release_or_fail(conn, row, holder, f"worker failed (retryable): {reason_txt}", "fail")
        else:
            cands = reassign_candidates()
            conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?, reassign_flag=1,
                            reassign_candidates=?, updated_at=? WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                         (reason_txt, json.dumps(cands), now(), wid, lease_id))
            _audit(conn, wid, "fail", holder, "FAILED", lease_id=lease_id, attempt=row["attempt"], from_state="CLAIMED",
                   to_state="FAILED", sha256=rsha, detail={"reason": reason_txt, "reassign_candidates": cands,
                                                           "metered_fallback": False, "failed_by": holder,
                                                           **({"caller": caller} if caller else {})})
            out = {"work_item_id": wid, "to": "FAILED", "attempt": row["attempt"], "old_ref": row["doorbell_ref"],
                   "reassign_candidates": cands}
    if out["to"] == "AVAILABLE":
        result = _result(True, "RELEASED_FOR_RETRY", wid, attempt=out["attempt"], reason_sha256=rsha)
    else:
        result = _result(True, "FAILED", wid, reason_sha256=rsha, reassign_flag=True,
                         reassign_candidates=out["reassign_candidates"])
    _safe_followup(result, lambda: _after_release(out, bell, holder))
    return result


def _after_release(out: dict[str, Any], bell: Any, holder: str) -> None:
    wid = out["work_item_id"]
    if out["to"] == "AVAILABLE":
        _set_dispatch(wid, "AVAILABLE")
        _emit("grok_bridge.released", wid, {"attempt": out["attempt"], "actor": holder})
        _close_ref(wid, out.get("old_ref"), "RE_RUNG", bell, "wi", triggered_by=holder)
        ring(wid, doorbell=bell, actor="wi")
    else:
        _set_dispatch(wid, "FAILED")
        cur = (work_items.get(wid) or {}).get("state")
        if cur in ("DISPATCHED_SHADOW", "RUNNING"):
            work_items.transition_if(wid, cur, "EXCEPTION",
                                     reason="grok_bridge failed; flagged for reassignment (no metered fallback)")
        _emit("grok_bridge.failed", wid, {"attempt": out["attempt"], "actor": holder})
        _emit("grok_bridge.reassign_flagged", wid, {"candidates": out.get("reassign_candidates") or [],
                                                     "metered_fallback": False})
        _close_ref(wid, out.get("old_ref"), "FAILED", bell, "wi", triggered_by=holder)


def _revoke_non_claimable_lease(conn: sqlite3.Connection, row: dict[str, Any], actor: str) -> dict[str, Any] | None:
    wid = row["work_item_id"]
    ok, item_state, _dispatch = _item_claimable(conn, wid)
    if ok:
        return None
    reason = f"item left machine-executable state: {item_state}"
    ts = now()
    if row["state"] == "CLAIMED":
        conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?, reassign_flag=0, updated_at=?
                        WHERE work_item_id=? AND state='CLAIMED' AND lease_id=?""",
                     (reason, ts, wid, row["lease_id"]))
        _audit(conn, wid, "lease_revoked", actor, "LEASE_REVOKED", lease_id=row["lease_id"], attempt=row["attempt"],
               from_state="CLAIMED", to_state="FAILED", detail={"item_state": item_state, "claimant": row.get("claimant")})
    else:
        conn.execute("""UPDATE grok_leases SET state='FAILED', failure_reason=?, reassign_flag=0, updated_at=?
                        WHERE work_item_id=? AND state='AVAILABLE'""", (reason, ts, wid))
        _audit(conn, wid, "lease_revoked", actor, "LEASE_REVOKED", attempt=row["attempt"], from_state="AVAILABLE",
               to_state="FAILED", detail={"item_state": item_state})
    return {"work_item_id": wid, "to": "FAILED", "attempt": row["attempt"], "old_ref": row.get("doorbell_ref"),
            "holder": row.get("claimant"), "revoked": True}


def _needs_reconcile(conn: sqlite3.Connection, row: dict[str, Any]) -> bool:
    wid = row["work_item_id"]
    try:
        r = conn.execute("SELECT result_json FROM work_items WHERE id=?", (wid,)).fetchone()
    except sqlite3.OperationalError:
        return False
    if not r or not row.get("result_path") or not row.get("result_sha256"):
        return False
    result = json.loads(r["result_json"]) if r["result_json"] else None
    return not (isinstance(result, dict) and result.get("lease_id") == row["lease_id"])


def release_expired(*, actor: str = "wi-recovery", doorbell: Any = "env") -> dict[str, Any]:
    """Lease recovery from WI state only (never reads GitHub): release expired leases (or fail them after
    max attempts) and re-ring unrung doorbells. Works with the doorbell off or GitHub unavailable."""
    bell = _doorbell_default() if doorbell == "env" else doorbell
    revoked, reconciled = [], []
    to_reconcile: list[dict[str, Any]] = []
    with _Tx() as conn:
        for row in conn.execute("SELECT * FROM grok_leases WHERE state='COMPLETED'"):
            rd = dict(row)
            if _needs_reconcile(conn, rd):
                to_reconcile.append(rd)
        for row in conn.execute("SELECT * FROM grok_leases WHERE state IN ('AVAILABLE','CLAIMED')"):
            out = _revoke_non_claimable_lease(conn, dict(row), actor)
            if out:
                revoked.append(out)
    for row in to_reconcile:
        wid = row["work_item_id"]
        ident = {"route": "grok_bridge", "lease_id": row["lease_id"], "result_path": row["result_path"],
                 "result_sha256": row["result_sha256"], "claimed_by": row.get("claimant"),
                 "executed_by": row.get("executed_by"), "completed_by": row.get("completed_by"),
                 "attempt": row["attempt"], "idempotency_key": idempotency_key(wid, row["attempt"])}
        try:
            work_items.update_fields(wid, result=ident)
            with _Tx() as conn:
                _audit(conn, wid, "reconcile", actor, "RECONCILED", lease_id=row["lease_id"], attempt=row["attempt"],
                       detail={"result_path": row["result_path"], "result_sha256": row["result_sha256"]})
            reconciled.append(wid)
        except Exception:  # noqa: BLE001
            pass
    for out in revoked:
        try:
            _close_ref(out["work_item_id"], out.get("old_ref"), "REVOKED", bell, "wi",
                       triggered_by=out.get("holder"))
        except Exception:  # noqa: BLE001
            pass
    with _Tx() as conn:
        expired = [r["work_item_id"] for r in conn.execute(
            "SELECT work_item_id FROM grok_leases WHERE state='CLAIMED' AND lease_expires_at<=?", (now(),))]
    released, failed = [], []
    for wid in expired:
        try:
            with _Tx() as conn:
                row = _row(conn, wid)
                if row is None or row["state"] != "CLAIMED" or now() < row["lease_expires_at"]:
                    continue
                _audit(conn, wid, "lease_expired", actor, "EXPIRED", lease_id=row["lease_id"], attempt=row["attempt"],
                       from_state="CLAIMED", detail={"expired_at": wita(row["lease_expires_at"]),
                                                     "claimant": row["claimant"]})
                out = _release_or_fail(conn, row, actor, "lease expired", "release")
            _after_release(out, bell, row["claimant"])
            (released if out["to"] == "AVAILABLE" else failed).append(wid)
        except Exception:  # noqa: BLE001
            continue
    doorbell_states = ("PENDING", "FAILED") if bell is None else ("PENDING", "FAILED", "DISABLED")
    with _Tx() as conn:
        pending = [r["work_item_id"] for r in conn.execute(
            f"SELECT work_item_id FROM grok_leases WHERE state='AVAILABLE' AND doorbell_state IN ({','.join('?'*len(doorbell_states))})",
            doorbell_states)]
    rerung = []
    for wid in pending:
        if wid in released:
            continue
        try:
            r = ring(wid, doorbell=bell, actor=actor)
            rerung.append({"work_item_id": wid, "code": r["code"]})
        except Exception:  # noqa: BLE001
            rerung.append({"work_item_id": wid, "code": "ERROR"})
    return {"ok": True, "code": "RECOVERY_DONE", "released": released, "failed": failed, "revoked": [o["work_item_id"] for o in revoked],
            "reconciled": reconciled, "rerung": rerung, "doorbell_enabled": bell is not None, "at": wita(now())}


def correct(seq: int, *, reason: str, actor: str) -> dict[str, Any]:
    """Append a corrective event that references an earlier audit row. The original row is never rewritten."""
    _check_ident(actor, "actor")
    reason_txt = real_evidence.redact(str(reason or "").strip())[:MAX_REASON_CHARS]
    if not reason_txt:
        raise ValueError("reason required")
    with _Tx() as conn:
        orig = conn.execute("SELECT seq, work_item_id, row_sha256, action, outcome FROM grok_bridge_audit WHERE seq=?",
                            (int(seq),)).fetchone()
        if orig is None:
            return {"ok": False, "code": "NO_SUCH_AUDIT_ROW", "seq": int(seq)}
        r = _audit(conn, orig["work_item_id"], "correction", actor, "CORRECTION",
                   sha256=sha256_bytes(reason_txt.encode()),
                   detail={"corrects_seq": orig["seq"], "corrects_row_sha256": orig["row_sha256"],
                           "corrects": f"{orig['action']}/{orig['outcome']}", "reason": reason_txt})
    return {"ok": True, "code": "CORRECTION_APPENDED", "work_item_id": orig["work_item_id"],
            "corrects_seq": orig["seq"], "row_sha256": r["row_sha256"]}


def status(wid: str) -> dict[str, Any]:
    _check_wid(wid)
    with _Tx() as conn:
        row = _row(conn, wid)
    if row is None:
        return _result(False, "NOT_OFFERED", wid)
    return _result(True, row["state"], wid, lease=public(row))


def audit_rows(wid: str | None = None) -> list[dict[str, Any]]:
    with _Tx() as conn:
        q = "SELECT * FROM grok_bridge_audit" + (" WHERE work_item_id=?" if wid else "") + " ORDER BY seq"
        return [dict(r) for r in conn.execute(q, (wid,) if wid else ())]


_ROW_FIELDS = ("at", "at_wita", "work_item_id", "action", "actor", "lease_id", "attempt", "from_state", "to_state",
               "outcome", "sha256", "detail_json", "prev_row_sha256")


def verify_audit_chain() -> dict[str, Any]:
    """Verify the whole audit: hash chain, per-row HMAC (key outside the DB), pin, anchor and anchor log."""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            init_schema(conn)
            rows = [dict(r) for r in conn.execute("SELECT * FROM grok_bridge_audit ORDER BY seq")]
            key = _load_key(create=False)
            anchor = _read_anchor()
            pin = _read_pin()
            log = _read_anchor_log()
        finally:
            conn.execute("ROLLBACK")
    finally:
        conn.close()
    problems: list[dict[str, Any]] = []
    prev, first_signed, signed, legacy = None, None, 0, 0
    key_exists = audit_key_path().exists()
    legacy_max: int | None = None
    if key_exists:
        if key is None:
            problems.append({"code": "KEY_MISSING"})
        if pin is None:
            problems.append({"code": "PIN_MISSING"})
        elif pin.get("format") == "UNREADABLE":
            problems.append({"code": "PIN_UNREADABLE"})
        elif key is not None and not hmac.compare_digest(_pin_body_mac(key, pin), str(pin.get("pin_hmac", ""))):
            problems.append({"code": "PIN_INVALID"})
        else:
            legacy_max = int(pin.get("legacy_max_seq", 0)) if pin else None
    for r in rows:
        body = {k: r[k] for k in _ROW_FIELDS}
        if r["prev_row_sha256"] != prev or sha256_bytes(json.dumps(body, sort_keys=True).encode()) != r["row_sha256"]:
            problems.append({"code": "BROKEN_CHAIN", "seq": r["seq"]})
            break
        if legacy_max is not None and r["seq"] > legacy_max and not r.get("row_hmac"):
            problems.append({"code": "UNSIGNED_ROW_ABOVE_LEGACY", "seq": r["seq"]})
            break
        if r.get("row_hmac"):
            signed += 1
            first_signed = first_signed or r["seq"]
            if key is None:
                problems.append({"code": "KEY_MISSING", "seq": r["seq"]})
                break
            if not hmac.compare_digest(_mac(key, r["row_sha256"]), r["row_hmac"]):
                problems.append({"code": "HMAC_MISMATCH", "seq": r["seq"]})
                break
        else:
            if first_signed is not None:
                problems.append({"code": "UNSIGNED_ROW_AFTER_SIGNED", "seq": r["seq"]})
                break
            legacy += 1
        prev = r["row_sha256"]
    max_seq = rows[-1]["seq"] if rows else None
    anchored_seq = None
    above_legacy = [r for r in rows if legacy_max is not None and r["seq"] > legacy_max]
    if not problems and above_legacy and anchor is None:
        problems.append({"code": "ANCHOR_MISSING"})
    if not problems and key_exists and (signed or anchor is not None or above_legacy):
        if anchor is None and above_legacy:
            problems.append({"code": "ANCHOR_MISSING"})
        elif anchor is not None:
            if key is None:
                problems.append({"code": "KEY_MISSING"})
            elif anchor.get("format") != ANCHOR_FORMAT or not hmac.compare_digest(
                    _anchor_body_mac(key, anchor), str(anchor.get("anchor_hmac", ""))):
                problems.append({"code": "ANCHOR_INVALID"})
            else:
                anchored_seq = anchor["seq"]
                by_seq = {r["seq"]: r for r in rows}
                if anchor.get("hmac_from_seq") != first_signed:
                    problems.append({"code": "SIGNATURE_START_MISMATCH", "anchor": anchor.get("hmac_from_seq"),
                                     "found": first_signed})
                if max_seq is None or max_seq < anchor["seq"] or len(rows) < int(anchor.get("rows", 0)):
                    problems.append({"code": "TRUNCATED", "anchored_seq": anchor["seq"], "max_seq": max_seq,
                                     "anchored_rows": anchor.get("rows"), "rows": len(rows)})
                elif by_seq.get(anchor["seq"], {}).get("row_sha256") != anchor["row_sha256"]:
                    problems.append({"code": "ANCHOR_ROW_MISMATCH", "seq": anchor["seq"]})
    if not problems and log:
        if log[0].get("format") == "UNREADABLE":
            problems.append({"code": "ANCHOR_LOG_UNREADABLE"})
        elif key is not None:
            last_seq = -1
            for entry in log:
                if entry.get("format") != ANCHOR_LOG_FORMAT:
                    problems.append({"code": "ANCHOR_LOG_INVALID"})
                    break
                body = {k: entry[k] for k in ("format", "seq", "row_sha256", "rows", "hmac_from_seq", "updated_at")
                        if k in entry}
                if not hmac.compare_digest(_log_entry_mac(key, body), str(entry.get("log_hmac", ""))):
                    problems.append({"code": "ANCHOR_LOG_INVALID"})
                    break
                seq = int(entry["seq"])
                if seq < last_seq:
                    problems.append({"code": "ANCHOR_REPLAY", "seq": seq, "last_seq": last_seq})
                    break
                last_seq = seq
            if not problems and anchor is not None and log:
                last = log[-1]
                if int(last["seq"]) != anchor["seq"] or last["row_sha256"] != anchor["row_sha256"]:
                    problems.append({"code": "ANCHOR_LOG_HEAD_MISMATCH"})
                elif int(last["seq"]) > anchor["seq"]:
                    problems.append({"code": "ANCHOR_REPLAY"})
    out = {"ok": not problems, "rows": len(rows), "head": prev if not problems else None, "signed_rows": signed,
           "legacy_unsigned_rows": legacy, "anchored_seq": anchored_seq, "problems": problems,
           "legacy_max_seq": legacy_max}
    if problems and problems[0].get("seq") is not None:
        out["broken_at_seq"] = problems[0]["seq"]
    return out


# --------------------------------------------------------------------------- work item glue
def _set_dispatch(wid: str, bridge_state: str, **ident: Any) -> None:
    try:
        d = {"route": "grok_bridge", "intended_worker": WORKER, "bridge_state": bridge_state,
             "mode": "REAL (event-driven doorbell + lease)"}
        d.update({k: v for k, v in ident.items() if v})
        work_items.update_fields(wid, dispatch=d)
    except Exception:  # noqa: BLE001
        pass
