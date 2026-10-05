#!/usr/bin/env python3
"""Shared guard: tests cannot mutate canonical Beta or prod ledgers.

Canonical prod is refused for a test process, and any write through this
guard is refused. Canonical Beta writes from a test process are refused.
WOLF_ALLOW_LIVE_AUDIT does not open that path. A non-test process may write
canonical Beta because the Beta server is the operational writer. Setting
WOLF_CANONICAL_WRITE_OVERRIDE=1 on a non-test process is logged and still
refused when the process is a test.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BETA_CATALOG = (BETA_ROOT / "catalog" / "content_library.sqlite").resolve()
CATALOG_DIR = (BETA_ROOT / "catalog").resolve()
OVERRIDE_ENV = "WOLF_CANONICAL_WRITE_OVERRIDE"
LEGACY_ENV = "WOLF_ALLOW_LIVE_AUDIT"
LOG_PATH = BETA_ROOT / "state" / "build-factory" / "logs" / "canonical-write-override.log"

_DENY_ACTIONS = None
_REAL_CONNECT = sqlite3.connect
_INSTALLED = False


class CanonicalGuardError(RuntimeError):
    """Raised when a process tries to use a canonical ledger it must not change."""


def is_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    argv = " ".join(sys.argv).replace("\\", "/")
    if "/scripts/tests/" in f"/{argv}" or "scripts/tests/" in argv:
        return True
    if sys.argv:
        try:
            if "scripts/tests" in str(Path(sys.argv[0]).resolve()):
                return True
        except OSError:
            return False
    return False


def _resolved(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def is_prod_path(path: Path | str) -> bool:
    try:
        text = str(_resolved(path))
    except OSError:
        text = str(path)
    low = text.replace("\\", "/").lower()
    if "wolf-system" in low:
        return True
    if "/production/" in low:
        return True
    name = Path(low).name
    if name == "money.sqlite":
        return True
    return False


def is_canonical_beta_file(path: Path | str) -> bool:
    try:
        resolved = _resolved(path)
    except OSError:
        return False
    return resolved.parent == CATALOG_DIR and resolved.suffix == ".sqlite"


def decide(
    path: Path | str,
    *,
    write: bool,
    test_process: bool | None = None,
    override: bool | None = None,
) -> str:
    """Return 'allow' or 'refuse'. Does not touch the database."""
    testing = is_test_process() if test_process is None else test_process
    if is_prod_path(path):
        if testing or write:
            return "refuse"
        return "allow"
    if write and is_canonical_beta_file(path):
        if testing:
            return "refuse"
        granted = (
            (os.environ.get(OVERRIDE_ENV) or "").strip() == "1"
            if override is None
            else override
        )
        if granted:
            return "allow-override"
        return "allow"
    return "allow"


def _log(kind: str, path: Path) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    line = (
        f"{stamp} kind={kind} pid={os.getpid()} "
        f"file={path.name} test={int(is_test_process())}\n"
    )
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line)


def assert_write_allowed(path: Path | str) -> None:
    """Refuse canonical prod writes, and canonical Beta writes from tests.

    Legacy WOLF_ALLOW_LIVE_AUDIT is ignored. A test that sets
    WOLF_CANONICAL_WRITE_OVERRIDE is still refused. A non-test override is logged.
    """
    resolved = _resolved(path)
    outcome = decide(resolved, write=True)
    if outcome == "refuse":
        if is_test_process() and (os.environ.get(OVERRIDE_ENV) or "").strip() == "1":
            _log("refused-test-override", resolved)
        if is_test_process() and (os.environ.get(LEGACY_ENV) or "").strip() == "1":
            _log("refused-legacy-test-bypass", resolved)
        if is_prod_path(resolved):
            raise CanonicalGuardError(f"canonical prod refused: {resolved.name}")
        raise CanonicalGuardError(
            "test process refuses canonical Beta write; point the catalog at a temp copy"
        )
    if outcome == "allow-override":
        _log("allowed-non-test-override", resolved)


def assert_test_may_read(path: Path | str) -> None:
    resolved = _resolved(path)
    if is_test_process() and is_prod_path(resolved):
        raise CanonicalGuardError(f"test process refuses canonical prod: {resolved.name}")


def _database_path(database: object) -> Path | None:
    if isinstance(database, Path):
        return database
    if not isinstance(database, str):
        return None
    if database == ":memory:" or database.startswith("file::memory:"):
        return None
    if database.startswith("file:"):
        parsed = urlparse(database)
        raw = unquote(parsed.path or "")
        if not raw:
            return None
        return Path(raw)
    return Path(database)


def _readonly_uri(database: object, kwargs: dict) -> bool:
    if not isinstance(database, str):
        return False
    if not (kwargs.get("uri") or database.startswith("file:")):
        return False
    return "mode=ro" in database


def _mutating_sql(sql: object) -> bool:
    text = str(sql or "").lstrip().lower()
    if text.startswith("with "):
        return any(token in text for token in (" insert ", " update ", " delete ", " replace "))
    return text.startswith(
        (
            "insert",
            "update",
            "delete",
            "replace",
            "create",
            "drop",
            "alter",
            "attach",
            "vacuum",
            "reindex",
        )
    )


def _deny_actions() -> set[int]:
    global _DENY_ACTIONS
    if _DENY_ACTIONS is not None:
        return _DENY_ACTIONS
    names = (
        "SQLITE_INSERT",
        "SQLITE_UPDATE",
        "SQLITE_DELETE",
        "SQLITE_CREATE_INDEX",
        "SQLITE_CREATE_TABLE",
        "SQLITE_CREATE_TRIGGER",
        "SQLITE_CREATE_VIEW",
        "SQLITE_DROP_INDEX",
        "SQLITE_DROP_TABLE",
        "SQLITE_DROP_TRIGGER",
        "SQLITE_DROP_VIEW",
        "SQLITE_ALTER_TABLE",
        "SQLITE_REINDEX",
        "SQLITE_ATTACH",
        "SQLITE_CREATE_VTABLE",
        "SQLITE_DROP_VTABLE",
    )
    found = set()
    for name in names:
        value = getattr(sqlite3, name, None)
        if isinstance(value, int):
            found.add(value)
    _DENY_ACTIONS = found
    return found


def _arm_connection(conn: sqlite3.Connection, path: Path) -> None:
    """Deny mutating statements. sqlite3.Connection.execute is read-only in 3.14."""
    del path
    denied = _deny_actions()

    def authorizer(action, arg1, arg2, db_name, trigger):  # noqa: ANN001
        if action in denied:
            return sqlite3.SQLITE_DENY
        if action == getattr(sqlite3, "SQLITE_PRAGMA", -1) and str(arg1 or "").lower() in {
            "writable_schema",
            "journal_mode",
            "wal_checkpoint",
        }:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    conn.set_authorizer(authorizer)


def guarded_connect(database, *args, **kwargs):  # noqa: ANN001
    path = _database_path(database)
    if path is not None and is_test_process():
        assert_test_may_read(path)
        if is_canonical_beta_file(path) and not _readonly_uri(database, kwargs):
            conn = _REAL_CONNECT(database, *args, **kwargs)
            _arm_connection(conn, _resolved(path))
            return conn
    return _REAL_CONNECT(database, *args, **kwargs)


def install() -> None:
    """Patch sqlite3.connect for this test process. No-op outside tests."""
    global _INSTALLED
    if _INSTALLED or not is_test_process():
        return
    sqlite3.connect = guarded_connect  # type: ignore[assignment]
    _INSTALLED = True


TMPF1_MIN_FREE_GB = float(os.environ.get("WOLF_TMPF1_MIN_FREE_GB", "8"))


def _tmpf1_free_space_floor(src: Path, scratch: Path) -> None:
    import shutil as _sh
    need = src.stat().st_size if src.exists() else 0
    free = _sh.disk_usage(str(scratch)).free
    if free - need < TMPF1_MIN_FREE_GB * 1e9:
        try:
            import json as _js
            from datetime import datetime as _dt, timezone as _tz
            q = BETA_ROOT / "state" / "build-factory" / "NOTIFY-QUEUE.jsonl"
            with q.open("a", encoding="utf-8") as fh:
                fh.write(_js.dumps({"at": _dt.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": "STUCK",
                                    "source": "canonical_guard.backup_catalog",
                                    "reason": "studio_free_space_below_floor", "free_gb": round(free / 1e9, 2),
                                    "min_free_gb": TMPF1_MIN_FREE_GB}) + "\n")
        except Exception:  # noqa: BLE001
            pass
        raise CanonicalGuardError(
            f"REFUSE_LOW_DISK: test catalog copy would leave < {TMPF1_MIN_FREE_GB:.0f} GB free")


def _tmpf1_register_cleanup(dest_dir: Path) -> None:
    import atexit as _ax
    import shutil as _sh

    def _rm(d: Path = dest_dir) -> None:
        if os.environ.get("WOLF_KEEP_TMPF1") == "1":
            return
        _sh.rmtree(d, ignore_errors=True)

    _ax.register(_rm)


def backup_catalog(source: Path | None = None) -> Path:
    """Consistent temp copy of a canonical Beta sqlite file. Reads only."""
    src = _resolved(source or BETA_CATALOG)
    assert_test_may_read(src)
    if is_prod_path(src):
        raise CanonicalGuardError("refusing to copy canonical prod")
    scratch = BETA_ROOT / "state" / "build-factory" / "tmp-f1"
    scratch.mkdir(parents=True, exist_ok=True)
    # Owner P0 5 Oct 2026 20:50 WITA (disk RED): every test process left a full ~114 MB
    # catalog copy here and nothing removed it (53 GB). Guard + auto-remove at process exit.
    _tmpf1_free_space_floor(src, scratch)
    dest_dir = Path(tempfile.mkdtemp(prefix="wolf-f1-", dir=scratch))
    _tmpf1_register_cleanup(dest_dir)
    dest = dest_dir / src.name
    src_uri = src.as_uri() + "?mode=ro"
    src_conn = _REAL_CONNECT(src_uri, uri=True)
    dst_conn = _REAL_CONNECT(str(dest))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()
    return dest


def bind_loaded_catalogs(dest: Path) -> list[str]:
    """Point loaded CATALOG_DB globals that still name a canonical Beta file at dest.

    LIVE_CATALOG_DB stays the real canonical path so older equality checks
    still recognise it. This does not retarget prod.
    """
    bound: list[str] = []
    target = _resolved(dest)
    for name, mod in list(sys.modules.items()):
        if mod is None or not hasattr(mod, "CATALOG_DB"):
            continue
        current = getattr(mod, "CATALOG_DB")
        if not isinstance(current, Path):
            continue
        try:
            resolved = current.resolve()
        except OSError:
            continue
        if is_canonical_beta_file(resolved):
            setattr(mod, "CATALOG_DB", target)
            bound.append(name)
    return bound


def isolate_runtime_catalog() -> Path:
    """Backup the Beta catalog and retarget loaded CATALOG_DB globals."""
    install()
    dest = backup_catalog()
    bind_loaded_catalogs(dest)
    return dest
