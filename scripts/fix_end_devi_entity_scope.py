#!/usr/bin/env python3
"""Surgical Beta-only: end SCOPE-BZG-ENTITY on ASG-DEVI-HFB-UMA-1.
Keep SCOPE-BZG-UMA ACTIVE. Never touch Production. Never git add .
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WITA = ZoneInfo("Asia/Makassar")
ASSIGNMENT = "ASG-DEVI-HFB-UMA-1"
END_SCOPE = "SCOPE-BZG-ENTITY"
KEEP_SCOPE = "SCOPE-BZG-UMA"


def now_wita_iso() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


def backup_catalog(db: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(WITA).strftime("%Y%m%d-%H%M%S")
    dest = backup_root / f"content_library.sqlite.pre-devi-scope-narrow-{stamp}"
    shutil.copy2(db, dest)
    return dest


def discover_ended_status(c: sqlite3.Connection) -> str:
    rows = c.execute(
        """
        SELECT status, COUNT(*) AS n
        FROM org_assignment_scopes
        WHERE status != 'ACTIVE' OR end_at IS NOT NULL
        GROUP BY status
        ORDER BY n DESC
        """
    ).fetchall()
    print("EXISTING non-active / ended status histogram:")
    for r in rows:
        print(f"  status={r[0]!r} count={r[1]}")
    preferred = ("ENDED", "INACTIVE", "REVOKED", "EXPIRED")
    present = {r[0] for r in rows if r[0]}
    for p in preferred:
        if p in present:
            return p
    # If no prior ended rows, use ENDED (task default) after verifying CHECK if any.
    return "ENDED"


def prove(c: sqlite3.Connection) -> list[sqlite3.Row]:
    return c.execute(
        """
        SELECT assignment_id, scope_id, status, start_at, end_at
        FROM org_assignment_scopes
        WHERE assignment_id = ?
        ORDER BY scope_id
        """,
        (ASSIGNMENT,),
    ).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--db",
        default="/Users/wolfterminal/beta-os/catalog/content_library.sqlite",
    )
    ap.add_argument(
        "--backup-dir",
        default="/Users/wolfterminal/beta-os/state/backups",
    )
    ap.add_argument("--apply", action="store_true", help="Perform UPDATE (default: dry-run)")
    ap.add_argument(
        "--proof-out",
        default="/Users/wolfterminal/beta-os/docs/deliveries/DEVI-SCOPE-NARROW-PROOF-2026-09-19.md",
    )
    args = ap.parse_args()

    db = Path(args.db)
    if not db.is_file():
        print(f"REFUSE: catalog missing: {db}", file=sys.stderr)
        return 2

    # Refuse obvious Production paths
    s = str(db.resolve())
    if "wolf-system" in s or "/Production" in s or s.endswith("/prod/content_library.sqlite"):
        print(f"REFUSE: looks like Production path: {s}", file=sys.stderr)
        return 3

    bak = backup_catalog(db, Path(args.backup_dir))
    print(f"BACKUP={bak}")

    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    c = con.cursor()

    # Schema sniff
    cols = [r[1] for r in c.execute("PRAGMA table_info(org_assignment_scopes)")]
    print(f"org_assignment_scopes columns: {cols}")
    if "status" not in cols or "end_at" not in cols or "scope_id" not in cols:
        print("REFUSE: unexpected schema", file=sys.stderr)
        return 4

    before = prove(c)
    print("BEFORE:")
    for r in before:
        print(dict(r))

    ended_status = discover_ended_status(c)
    print(f"CHOSEN_ENDED_STATUS={ended_status}")

    target = c.execute(
        """
        SELECT assignment_id, scope_id, status, end_at
        FROM org_assignment_scopes
        WHERE assignment_id=? AND scope_id=?
        """,
        (ASSIGNMENT, END_SCOPE),
    ).fetchone()
    if not target:
        print(f"REFUSE: row not found {ASSIGNMENT}/{END_SCOPE}", file=sys.stderr)
        return 5

    keep = c.execute(
        """
        SELECT assignment_id, scope_id, status, end_at
        FROM org_assignment_scopes
        WHERE assignment_id=? AND scope_id=?
        """,
        (ASSIGNMENT, KEEP_SCOPE),
    ).fetchone()
    if not keep:
        print(f"REFUSE: keep-scope missing {ASSIGNMENT}/{KEEP_SCOPE}", file=sys.stderr)
        return 6

    end_at = now_wita_iso()
    if not args.apply:
        print(f"DRY-RUN would set status={ended_status!r} end_at={end_at}")
        con.close()
        return 0

    c.execute(
        """
        UPDATE org_assignment_scopes
        SET status = ?, end_at = ?
        WHERE assignment_id = ? AND scope_id = ?
          AND status = 'ACTIVE'
        """,
        (ended_status, end_at, ASSIGNMENT, END_SCOPE),
    )
    if c.rowcount != 1:
        print(f"REFUSE: expected 1 row updated, got {c.rowcount}", file=sys.stderr)
        con.rollback()
        return 7
    con.commit()

    after = prove(c)
    print("AFTER:")
    for r in after:
        print(dict(r))

    active = [
        dict(r)
        for r in after
        if r["status"] == "ACTIVE" and (r["end_at"] is None or str(r["end_at"]).strip() == "")
    ]
    active_scopes = {r["scope_id"] for r in active}
    ok = active_scopes == {KEEP_SCOPE}
    print(f"ACTIVE_SCOPES={sorted(active_scopes)} OK={ok}")

    proof = Path(args.proof_out)
    proof.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# DEVI SCOPE NARROW PROOF — 2026-09-19",
        "",
        f"- **When (WITA):** {end_at}",
        f"- **Catalog:** `{db}`",
        f"- **Backup:** `{bak}`",
        f"- **Assignment:** `{ASSIGNMENT}`",
        f"- **Ended:** `{END_SCOPE}` → status=`{ended_status}` end_at=`{end_at}`",
        f"- **Kept ACTIVE:** `{KEEP_SCOPE}`",
        f"- **Prove OK:** `{ok}` (ACTIVE scopes must be exactly {{{KEEP_SCOPE}}})",
        "",
        "## BEFORE",
        "```",
        *[str(dict(r)) for r in before],
        "```",
        "",
        "## AFTER",
        "```",
        *[str(dict(r)) for r in after],
        "```",
        "",
        "## SELECT proof",
        "```sql",
        f"SELECT assignment_id, scope_id, status, start_at, end_at",
        f"FROM org_assignment_scopes",
        f"WHERE assignment_id = '{ASSIGNMENT}'",
        f"  AND status = 'ACTIVE' AND (end_at IS NULL OR end_at = '');",
        "-- expect exactly one row: SCOPE-BZG-UMA",
        "```",
        "",
        "## ACTIVE rows (post)",
        "```",
        *[str(r) for r in active],
        "```",
        "",
    ]
    proof.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PROOF={proof}")
    con.close()
    return 0 if ok else 8


if __name__ == "__main__":
    raise SystemExit(main())
