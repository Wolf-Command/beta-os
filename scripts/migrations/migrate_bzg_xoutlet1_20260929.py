#!/usr/bin/env python3
"""BZG-XOUTLET-1 — Cross-outlet shared foundations (vendors / PR / close hooks).

Decision served: Matt-ordered Owner sprint BZG-XOUTLET-1 (2026-09-29);
inventory state/finance-core-sprint/INVENTORY-20260929.json §D after CORE-BOOKS-1.

Adds nullable outlet_id (+ centre hooks) on shared foundations so
LEGAL ENTITY → OUTLET → cost/revenue centre is usable across outlets.
Does NOT invent multi-outlet P&L, sales, costs, covers, allocations,
or go-live numbers. Does not flip staff_ready / human_commissioned.
Beta only. No prod. No push.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import bzg_xoutlet_foundations as xout  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
BZG_BOOKS = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium-bzg.sqlite")
FOUNDATIONS_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-XOUTLET-FOUNDATIONS.json"
ARM = ROOT / "state" / "finance-core-sprint" / "BZG-XOUTLET-1-ARM.json"
MIGRATION_ID = "bzg_xoutlet1_20260929"
PACK = "BZG-XOUTLET-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _refuse_path(db_path: Path) -> str | None:
    s = str(db_path.resolve())
    for frag in FORBIDDEN:
        if frag in s:
            return frag
    if "beta-os" not in s and "atrium-finance" not in s:
        return "not-beta-or-sidecar"
    return None


def _assert_statuses(conn: sqlite3.Connection) -> dict[str, str]:
    need = {
        "BZG-UMA": "OPEN",
        "BZG-RAIN": "PRE-OPENING",
        "OU-BZG-RAIN-POOL": "PRE-OPENING",
    }
    out: dict[str, str] = {}
    for oid, want in need.items():
        row = outlets.get_outlet(oid, conn=conn)
        if not row or row["status"] != want:
            raise RuntimeError(f"status regression {oid}: {row}")
        out[oid] = row["status"]
    for oid in ("BZG-MERAH", "BZG-ROOF", "BZG-RS", "BZG-CAT"):
        row = outlets.get_outlet(oid, conn=conn)
        if not row or row["status"] == "OPEN":
            raise RuntimeError(f"future outlet must not be OPEN: {oid} → {row}")
        out[oid] = row["status"]
    n = len(outlets.list_outlets(conn))
    if n != 7:
        raise RuntimeError(f"registry must stay at 7 rows, got {n}")
    return out


def _assert_scopes(conn: sqlite3.Connection) -> None:
    brand_tgts = conn.execute(
        "SELECT target_id FROM org_scope_targets "
        "WHERE scope_id='SCOPE-BZG-FB' AND target_type='brand'"
    ).fetchall()
    if brand_tgts:
        raise RuntimeError(f"SCOPE-BZG-FB must not hardcode brands: {brand_tgts}")
    ent = conn.execute(
        "SELECT 1 FROM org_scope_targets "
        "WHERE scope_id='SCOPE-BZG-FB' AND target_type='entity' AND target_id='ENT-BZG'"
    ).fetchone()
    if not ent:
        raise RuntimeError("SCOPE-BZG-FB must target entity ENT-BZG")


def _ensure_books_outlet_hooks() -> dict[str, Any]:
    """Additive nullable outlet_id on books-side purchase/AP hooks (all three slots)."""
    beta = Path("/Users/wolfterminal/atrium-finance/data/beta")
    targets = (
        beta / "atrium.sqlite",
        beta / "atrium-bzg.sqlite",
        beta / "atrium-ggv.sqlite",
    )
    hook_tables = (
        "inventory_purchase_orders",
        "inventory_receipts",
        "inventory_requisitions",
        "ap_payments",
    )
    out: dict[str, Any] = {}
    for path in targets:
        if not path.is_file():
            out[path.name] = {"skipped": True}
            continue
        refuse = _refuse_path(path)
        if refuse:
            raise RuntimeError(f"refuse books path {path}: {refuse}")
        conn = sqlite3.connect(str(path))
        try:
            added: list[str] = []
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            for table in hook_tables:
                if table not in tables:
                    continue
                cols = {
                    r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
                }
                if "outlet_id" not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN outlet_id TEXT")
                    added.append(table)
            jl = {
                r[1]
                for r in conn.execute("PRAGMA table_info(journal_lines)").fetchall()
            } if "journal_lines" in tables else set()
            n_j = (
                conn.execute("SELECT COUNT(*) FROM journal_headers").fetchone()[0]
                if "journal_headers" in tables
                else 0
            )
            n_a = (
                conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
                if "accounts" in tables
                else 0
            )
            conn.commit()
            out[path.name] = {
                "outlet_id_on_journal_lines": "outlet_id" in jl,
                "outlet_hooks_added": added,
                "journals": n_j,
                "accounts": n_a,
            }
        finally:
            conn.close()
    return out


def _write_docs(ts: str, panel: dict[str, Any], statuses: dict[str, str]) -> None:
    payload = {
        "schema": "wolf.bzg.xoutlet-foundations.v1",
        "as_of_wita": ts,
        "pack": PACK,
        "legal_entity_id": "ENT-BZG",
        "hierarchy": (
            "LEGAL_ENTITY → OUTLET → cost_centre_id / revenue_centre_id (nullable hooks)"
        ),
        "shared_foundations": [
            "bzg_shared_vendors.outlet_id (nullable)",
            "bzg_ops_purchase_requests.outlet_id (nullable)",
            "venue_daily_closes.outlet_id (nullable)",
            "journal_lines.outlet_id on atrium-bzg.sqlite (nullable, CORE-BOOKS-1)",
        ],
        "centres": {
            "cost_centre_id": None,
            "revenue_centre_id": None,
            "note": "Hooks only — not populated; no invented centre allocations.",
        },
        "statuses_preserved": statuses,
        "hooks": panel.get("hooks"),
        "no_fake_multi_outlet_pnl": True,
        "staff_ready": False,
        "human_commissioned": False,
        "owner_addendum": (
            "After Finance Core + BZG multi-outlet + non-HR V1 retirement finishes: "
            "do NOT chain another major feature pack. Next = Rebuild Completion & "
            "Exit Report only. Bug fixes + human commissioning OK."
        ),
        "cursor_must_not_auto_start": ["V1-SWEEP-1", "HEADCHEF"],
    }
    FOUNDATIONS_DOC.parent.mkdir(parents=True, exist_ok=True)
    FOUNDATIONS_DOC.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
    else:
        arm = {"pack": PACK}
    arm.update(
        {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "foundations_doc": str(FOUNDATIONS_DOC.relative_to(ROOT)),
            "hooks_ready": True,
            "staff_ready": False,
            "human_commissioned": False,
            "migrated_at_wita": ts,
            "result": "docs/wolf/ops/BZG-XOUTLET-1-RESULT.md",
            "owner_addendum": payload["owner_addendum"],
            "cursor_must_not_auto_start_next": True,
            "do_not_auto_start": ["V1-SWEEP-1", "HEADCHEF"],
        }
    )
    ARM.write_text(json.dumps(arm, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    refuse = _refuse_path(DB)
    if refuse:
        print(json.dumps({"ok": False, "error": f"refuse catalog: {refuse}"}))
        return 2
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"pre-bzg-xoutlet1-{stamp()}.sqlite"
    backup = premig_backup(DB, backup)
    ts = now_iso()

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        statuses = _assert_statuses(conn)
        _assert_scopes(conn)
        schema = xout.ensure_schema(conn)
        backfilled = xout.backfill_example_pr_outlet_ids(conn)
        # Prove nullable outlet_id accepts null (entity-shared) and registry id.
        xout.resolve_outlet_ref(None, conn=conn)
        xout.resolve_outlet_ref("BZG-UMA", conn=conn)
        xout.resolve_outlet_ref("OU-BZG-RAIN-POOL", conn=conn)
        panel = xout.foundations_panel(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    books = _ensure_books_outlet_hooks()
    _write_docs(ts, panel, statuses)

    # Re-read post-commit
    c2 = xout.db_connect(DB)
    try:
        hooks = xout.hook_status(c2)
        pr_cols = xout._table_cols(c2, "bzg_ops_purchase_requests")
        close_cols = xout._table_cols(c2, "venue_daily_closes")
        vendor_n = c2.execute(
            "SELECT COUNT(*) FROM bzg_shared_vendors"
        ).fetchone()[0]
        pr_with_outlet = c2.execute(
            "SELECT COUNT(*) FROM bzg_ops_purchase_requests WHERE outlet_id IS NOT NULL"
        ).fetchone()[0]
    finally:
        c2.close()

    result = {
        "ok": True,
        "migration_id": MIGRATION_ID,
        "pack": PACK,
        "backup": str(backup),
        "backup_sha256": _sha256(backup),
        "schema": schema,
        "pr_outlet_backfill": backfilled,
        "pr_rows_with_outlet_id": pr_with_outlet,
        "vendor_rows": vendor_n,
        "outlet_id_on_pr": "outlet_id" in pr_cols,
        "outlet_id_on_close": "outlet_id" in close_cols,
        "hooks": hooks,
        "statuses": statuses,
        "bzg_books": books,
        "staff_ready": False,
        "human_commissioned": False,
        "as_of_wita": ts,
        "owner_addendum_noted": True,
        "did_not_start": ["V1-SWEEP-1", "HEADCHEF"],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
