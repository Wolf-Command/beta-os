#!/usr/bin/env python3
"""031 BZG Daily Close Till+EDC — idempotent Beta-only migration.

Decision served: 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner order
BZG-DAILY-CLOSE-TILL-EDC-20261002.

Seeds outlet close config for Owner's 7 outlets from canonical registry.
human_close_enabled=1 for Uma Blu only. No EDC terminal rows invented.
No ACTIVE variance policies. No PERS hardcode for closer seat.
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

DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "031_bzg_daily_close_till_edc.sql"
BACKUP_DIR = ROOT / "catalog" / "backups"
MIGRATION_ID = "031_bzg_daily_close_till_edc"
PACK = "BZG-DAILY-CLOSE-TILL-EDC-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

ENTITY = "ENT-BZG"

# Owner order titles → registry outlet_id. Display mismatches → NEEDS CONFIGURATION.
OWNER_OUTLETS: tuple[dict[str, Any], ...] = (
    {
        "outlet_id": "BZG-UMA",
        "venue_brand_id": "BZG-UMA",
        "owner_title": "Uma Blu",
        "human_close_enabled": 1,
        "till_float_idr": 1_000_000.0,
        "till_float_citation": (
            "decisions.md 2026-08-02 PICK BZG cash-audit — "
            "Rp 1,000,000 till float EXCLUDED from deposit equation"
        ),
    },
    {
        "outlet_id": "BZG-RAIN",
        "venue_brand_id": "BZG-RAIN",
        "owner_title": "Blu Zone Rainforest Restaurant & Bar",
        "human_close_enabled": 0,
        "till_float_idr": None,
        "till_float_citation": None,
    },
    {
        "outlet_id": "OU-BZG-RAIN-POOL",
        "venue_brand_id": "BZG-RAIN",
        "owner_title": "Pool Bar",
        "human_close_enabled": 0,
        "till_float_idr": None,
        "till_float_citation": None,
    },
    {
        "outlet_id": "BZG-MERAH",
        "venue_brand_id": "BZG-MERAH",
        "owner_title": "Merah Underground",
        "human_close_enabled": 0,
        "till_float_idr": None,
        "till_float_citation": None,
    },
    {
        "outlet_id": "BZG-ROOF",
        "venue_brand_id": "BZG-ROOF",
        "owner_title": "Rooftop Bar",
        "human_close_enabled": 0,
        "till_float_idr": None,
        "till_float_citation": None,
    },
    {
        "outlet_id": "BZG-RS",
        "venue_brand_id": "BZG-RS",
        "owner_title": "Room Service",
        "human_close_enabled": 0,
        "till_float_idr": None,
        "till_float_citation": None,
    },
    {
        "outlet_id": "BZG-CAT",
        "venue_brand_id": "BZG-CAT",
        "owner_title": "Catering",
        "human_close_enabled": 0,
        "till_float_idr": None,
        "till_float_citation": None,
    },
)

EVIDENCE_TYPES = (
    (
        "pos_z_report",
        "POS / Z-report photo or file at till close — tender DECLARED not VERIFIED",
    ),
    (
        "edc_settlement_slip",
        "EDC terminal settlement slip photo/file — batch total evidence, not ESB card payments",
    ),
)


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
    if "beta-os" not in s:
        return "not-beta-os"
    return None


def _norm(s: str | None) -> str:
    return " ".join((s or "").strip().lower().split())


def _title_map_status(owner_title: str, registry_display: str | None) -> str:
    if not registry_display:
        return "NEEDS CONFIGURATION"
    if _norm(owner_title) == _norm(registry_display):
        return "MATCHED"
    return "NEEDS CONFIGURATION"


def apply(conn: sqlite3.Connection) -> dict[str, Any]:
    sql = SQL.read_text(encoding="utf-8")
    conn.executescript(sql)
    ts = now_iso()

    from core import bzg_outlet_registry as outlets

    if hasattr(outlets, "ensure_schema"):
        outlets.ensure_schema(conn)
    # Prefer live registry rows; fall back to SEED display names.
    registry = {r["outlet_id"]: r for r in outlets.list_outlets(conn)}
    if not registry:
        for row in outlets.SEED:
            registry[row["outlet_id"]] = row

    seeded = 0
    for spec in OWNER_OUTLETS:
        oid = spec["outlet_id"]
        reg = registry.get(oid) or {}
        display = reg.get("display_name")
        title_status = _title_map_status(spec["owner_title"], display)
        # Empty terminal registry → always NEEDS CONFIGURATION (do not invent).
        term_n = conn.execute(
            "SELECT COUNT(*) FROM venue_close_edc_terminals WHERE outlet_id=?",
            (oid,),
        ).fetchone()[0]
        edc_status = "CONFIGURED" if int(term_n) > 0 else "NEEDS CONFIGURATION"
        note_parts = []
        if title_status == "NEEDS CONFIGURATION":
            note_parts.append(
                f"Owner title '{spec['owner_title']}' ≠ registry display "
                f"'{display or 'MISSING'}' — map visible as NEEDS CONFIGURATION"
            )
        if edc_status == "NEEDS CONFIGURATION":
            note_parts.append("EDC terminal inventory unknown — do not invent IDs")
        if spec["human_close_enabled"] == 0:
            note_parts.append("human_close_enabled=false (config present only)")
        note = "; ".join(note_parts) if note_parts else "ok"
        conn.execute(
            """
            INSERT INTO venue_close_outlet_config (
              outlet_id, entity_id, venue_brand_id, owner_title,
              registry_display_name, human_close_enabled,
              till_float_idr, till_float_citation,
              title_map_status, edc_terminal_config_status, note,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(outlet_id) DO UPDATE SET
              entity_id=excluded.entity_id,
              venue_brand_id=excluded.venue_brand_id,
              owner_title=excluded.owner_title,
              registry_display_name=excluded.registry_display_name,
              human_close_enabled=excluded.human_close_enabled,
              till_float_idr=excluded.till_float_idr,
              till_float_citation=excluded.till_float_citation,
              title_map_status=excluded.title_map_status,
              edc_terminal_config_status=excluded.edc_terminal_config_status,
              note=excluded.note,
              updated_at=excluded.updated_at
            """,
            (
                oid,
                ENTITY,
                spec["venue_brand_id"],
                spec["owner_title"],
                display,
                int(spec["human_close_enabled"]),
                spec["till_float_idr"],
                spec["till_float_citation"],
                title_status,
                edc_status,
                note,
                ts,
                ts,
            ),
        )
        seeded += 1

    for et, desc in EVIDENCE_TYPES:
        conn.execute(
            """
            INSERT INTO core_evidence_types (
              evidence_type, description, status, created_at, updated_at
            ) VALUES (?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(evidence_type) DO UPDATE SET
              description=excluded.description,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (et, desc, ts, ts),
        )

    # Honesty: never seed ACTIVE variance policies from Alchemist soft gap.
    active_pol = conn.execute(
        "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
    ).fetchone()[0]

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO schema_migrations (id, applied_at, note)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
        """,
        (
            MIGRATION_ID,
            ts,
            "BZG daily close till+EDC; outlet config; no invented terminals/tolerances",
        ),
    )

    enabled = conn.execute(
        "SELECT COUNT(*) FROM venue_close_outlet_config WHERE human_close_enabled=1"
    ).fetchone()[0]
    terminals = conn.execute(
        "SELECT COUNT(*) FROM venue_close_edc_terminals"
    ).fetchone()[0]

    return {
        "migration_id": MIGRATION_ID,
        "pack": PACK,
        "outlet_config_rows": seeded,
        "human_close_enabled_count": int(enabled),
        "edc_terminal_rows": int(terminals),
        "active_variance_policies": int(active_pol),
        "staff_ready": False,
        "human_commissioned": False,
    }


def main(db_path: Path | None = None) -> int:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        print(json.dumps({"ok": False, "error": f"refused path ({bad})", "db": str(path)}))
        return 2
    if not path.is_file():
        print(json.dumps({"ok": False, "error": "db missing", "db": str(path)}))
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"content_library-pre-{MIGRATION_ID}-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    bak_sha = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        out = apply(conn)
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(json.dumps({"ok": False, "error": str(exc), "backup": str(bak)}))
        return 1
    finally:
        conn.close()

    print(
        json.dumps(
            {
                "ok": True,
                **out,
                "backup": str(bak),
                "backup_sha256": bak_sha,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
