#!/usr/bin/env python3
"""BZG-OUTLET-1 — Canonical BZG Outlet Registry + hierarchy scopes.

Decision served: Matt-ordered Owner sprint Finance Core / BZG multi-outlet
(inventory state/finance-core-sprint/INVENTORY-20260929.json §D; sibling of
CORE-ENT-1). Seeds org_outlet_registry under ENT-BZG with explicit statuses
only. Updates Pool Bar OU from HOOK → PRE-OPENING. Does not invent people,
ops metrics, or flip staff_ready / human_commissioned. Beta only. No prod.
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

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
OU_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-OPERATING-UNITS.json"
REGISTRY_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-OUTLET-REGISTRY.json"
MIGRATION_ID = "bzg_outlet1_20260929"
PACK = "BZG-OUTLET-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

HARI = "PERS-HARIYANTO"
DEVI = "PERS-DEVI"
ASG_HARI = "ASG-HARIYANTO-HEAD-CHEF-1"
ASG_DEVI_FB = "ASG-DEVI-FB-OPS-1"
ASG_DEVI_CLOSER = "ASG-DEVI-CLOSER-UMA-1"
ASG_ZAYEN_BZG = "ASG-ZAYEN-BZG-FC-1"
ASG_ZAYEN_FC = "ASG-ZAYEN-FC-1"


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


def _assert_assignments(conn: sqlite3.Connection) -> dict[str, str]:
    """Regression: existing seats stay ACTIVE; no new people invented."""
    out: dict[str, str] = {}
    for asg in (ASG_HARI, ASG_DEVI_FB, ASG_DEVI_CLOSER, ASG_ZAYEN_BZG, ASG_ZAYEN_FC):
        row = conn.execute(
            """
            SELECT status, end_at, person_id FROM org_assignments
            WHERE assignment_id=?
            """,
            (asg,),
        ).fetchone()
        if not row or row[0] != "ACTIVE" or row[1] is not None:
            raise RuntimeError(f"required assignment not ACTIVE: {asg} → {row}")
        out[asg] = row[2]
    if out[ASG_HARI] != HARI:
        raise RuntimeError("Hariyanto assignment person mismatch")
    if out[ASG_DEVI_FB] != DEVI or out[ASG_DEVI_CLOSER] != DEVI:
        raise RuntimeError("Devi assignment person mismatch")
    return out


def _update_atrium_ou(ts: str) -> dict[str, Any]:
    refuse = _refuse_path(ATRIUM_DB)
    if refuse:
        raise RuntimeError(f"refuse atrium path: {refuse}")
    if not ATRIUM_DB.is_file():
        return {"skipped": True, "reason": "atrium.sqlite missing"}
    conn = sqlite3.connect(str(ATRIUM_DB))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operating_unit_registry (
              operating_unit_id TEXT PRIMARY KEY,
              legal_entity_id TEXT NOT NULL,
              parent_brand_id TEXT,
              display_name TEXT NOT NULL,
              status TEXT NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            )
            """
        )
        note = (
            "Measurable BZG operating unit under Rainforest (BZG-RAIN). "
            "Not a second brand_id. Canonical registry: org_outlet_registry "
            "(BZG-OUTLET-1). Status PRE-OPENING until human confirm."
        )
        conn.execute(
            """
            INSERT INTO operating_unit_registry (
              operating_unit_id, legal_entity_id, parent_brand_id,
              display_name, status, note, created_at
            ) VALUES (?, 'ENT-BZG', 'BZG-RAIN', 'Pool Bar', 'PRE-OPENING', ?, ?)
            ON CONFLICT(operating_unit_id) DO UPDATE SET
              status='PRE-OPENING',
              note=excluded.note,
              display_name=excluded.display_name,
              parent_brand_id=excluded.parent_brand_id
            """,
            ("OU-BZG-RAIN-POOL", note, ts),
        )
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "journal_lines" in tables:
            cols = {
                r[1]
                for r in conn.execute("PRAGMA table_info(journal_lines)").fetchall()
            }
            if "outlet_id" not in cols:
                conn.execute("ALTER TABLE journal_lines ADD COLUMN outlet_id TEXT")
        conn.commit()
        row = conn.execute(
            "SELECT status, parent_brand_id FROM operating_unit_registry "
            "WHERE operating_unit_id=?",
            ("OU-BZG-RAIN-POOL",),
        ).fetchone()
        jl_cols = {
            r[1]
            for r in conn.execute("PRAGMA table_info(journal_lines)").fetchall()
        } if "journal_lines" in tables else set()
        return {
            "ou_status": row[0] if row else None,
            "parent_brand_id": row[1] if row else None,
            "outlet_id_column": "outlet_id" in jl_cols,
        }
    finally:
        conn.close()


def _write_docs(ts: str, seeded: int) -> None:
    ou_payload = {
        "schema": "wolf.bzg.operating-units.v1",
        "as_of_wita": ts,
        "pack": PACK,
        "rule": "measurable operating unit under parent brand — not a second brand_id",
        "legal_entity_id": "ENT-BZG",
        "supersedes": "CORE-ENT-1 HOOK",
        "units": [
            {
                "operating_unit_id": "OU-BZG-RAIN-POOL",
                "display_name": "Pool Bar",
                "parent_brand_id": "BZG-RAIN",
                "parent_brand_name": "Blu Zone Rainforest Restaurant & Bar",
                "parent_outlet_id": "BZG-RAIN",
                "status": "PRE-OPENING",
                "note": (
                    "Canonical row also in org_outlet_registry. PRE-OPENING — "
                    "no human F&B commissioning evidence; not a second brand_id."
                ),
            }
        ],
        "sidecar_columns": [
            "journal_lines.operating_unit_id (nullable)",
            "journal_lines.outlet_id (nullable, additive BZG-OUTLET-1)",
        ],
        "registry": (
            "catalog.org_outlet_registry + "
            "state/finance-core-sprint/BZG-OUTLET-REGISTRY.json"
        ),
    }
    OU_DOC.parent.mkdir(parents=True, exist_ok=True)
    OU_DOC.write_text(json.dumps(ou_payload, indent=2) + "\n", encoding="utf-8")

    conn = outlets.db_connect(DB)
    try:
        rows = outlets.list_outlets(conn)
    finally:
        conn.close()
    reg_payload = {
        "schema": "wolf.bzg.outlet-registry.v1",
        "as_of_wita": ts,
        "pack": PACK,
        "legal_entity_id": "ENT-BZG",
        "hierarchy": (
            "LEGAL_ENTITY → OUTLET → cost_centre_id / revenue_centre_id (nullable)"
        ),
        "allowed_statuses": sorted(outlets.ALLOWED_STATUSES),
        "status_rationale": {
            "BZG-UMA": "OPEN — primary operating outlet (brand LIVE)",
            "BZG-RAIN": (
                "PRE-OPENING — target ~7 Oct; no human F&B commissioning evidence "
                "for this outlet (prefer PRE-OPENING over COMMISSIONING)"
            ),
            "OU-BZG-RAIN-POOL": (
                "PRE-OPENING — under BZG-RAIN; no human confirm; not a brand_id"
            ),
            "future_config": (
                "BZG-MERAH / BZG-ROOF / BZG-RS / BZG-CAT = PRE-OPENING future "
                "config rows; not OPEN; no fake ops metrics"
            ),
        },
        "seeded_count": seeded,
        "outlets": rows,
        "owner_addendum": (
            "After Finance Core + BZG multi-outlet + non-HR V1 retirement finishes: "
            "do NOT chain another major feature pack. Next = Rebuild Completion & "
            "Exit Report only."
        ),
    }
    REGISTRY_DOC.write_text(json.dumps(reg_payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    refuse = _refuse_path(DB)
    if refuse:
        print(json.dumps({"ok": False, "error": f"refuse catalog: {refuse}"}))
        return 2
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"pre-bzg-outlet1-{stamp()}.sqlite"
    backup = premig_backup(DB, backup)
    ts = now_iso()

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        seats = _assert_assignments(conn)
        seeded = outlets.seed_registry(conn, ts)
        hari_scopes = [
            r[0]
            for r in conn.execute(
                """
                SELECT scope_id FROM org_assignment_scopes
                WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
                """,
                (ASG_HARI,),
            ).fetchall()
        ]
        if "SCOPE-BZG-FB" not in hari_scopes:
            raise RuntimeError("Hariyanto missing SCOPE-BZG-FB")
        fb_targets = [
            (r[0], r[1])
            for r in conn.execute(
                "SELECT target_type, target_id FROM org_scope_targets "
                "WHERE scope_id='SCOPE-BZG-FB'"
            ).fetchall()
        ]
        if ("entity", "ENT-BZG") not in fb_targets:
            raise RuntimeError("SCOPE-BZG-FB must target entity ENT-BZG")
        if any(t[0] == "brand" for t in fb_targets):
            raise RuntimeError("SCOPE-BZG-FB must not hardcode brand targets")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    atrium = _update_atrium_ou(ts)
    _write_docs(ts, seeded)

    c2 = outlets.db_connect(DB)
    try:
        hari_out = {o["outlet_id"] for o in outlets.outlets_for_person(HARI, c2)}
        devi_out = {o["outlet_id"] for o in outlets.outlets_for_person(DEVI, c2)}
        uma = outlets.get_outlet("BZG-UMA", c2)
        pool = outlets.get_outlet("OU-BZG-RAIN-POOL", c2)
    finally:
        c2.close()

    result = {
        "ok": True,
        "migration_id": MIGRATION_ID,
        "backup": str(backup),
        "backup_sha256": _sha256(backup),
        "seeded": seeded,
        "seats": seats,
        "atrium": atrium,
        "hariyanto_outlets_sample": sorted(hari_out)[:8],
        "hariyanto_covers_all_bzg": hari_out
        >= {"BZG-UMA", "BZG-RAIN", "OU-BZG-RAIN-POOL"},
        "devi_covers_uma": "BZG-UMA" in devi_out,
        "uma_status": uma["status"] if uma else None,
        "pool_status": pool["status"] if pool else None,
        "pool_parent": pool["parent_outlet_id"] if pool else None,
        "staff_ready": False,
        "human_commissioned": False,
        "as_of_wita": ts,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
