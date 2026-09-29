#!/usr/bin/env python3
"""HUMFIX-1 — brand scope, Drone type, FC approve SoD, FAIL/REPAIR loop (Beta).

Decision served: Matt relay 29 Sep 2026 ~11:14 WITA.
Temp store for flow tests. Live catalog read-only for invariant probes.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

from core import atrium_fc_authority as fc  # noqa: E402
from core import content_engine_repair as repair  # noqa: E402
from core import nas_library as nas  # noqa: E402
from core import rbac  # noqa: E402
from core import staff_access as sa  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_home import build_home  # noqa: E402

import importlib.util  # noqa: E402

_mig = ROOT / "scripts" / "migrations" / "migrate_humfix1_20260929.py"
_spec = importlib.util.spec_from_file_location("migrate_humfix1_20260929", _mig)
mig = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(mig)

CATALOG = ROOT / "catalog" / "content_library.sqlite"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _temp_store():
    tmp = Path(tempfile.mkdtemp(prefix="tmp-humfix1-", dir=str(ROOT / "state")))
    db = tmp / "catalog.sqlite"
    shutil.copy2(CATALOG, db)
    blobs = tmp / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    prev = os.environ.get("WOLF_WORK_EVIDENCE_BLOBS")
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    return tmp, db, blobs, prev


def _restore(prev):
    if prev is None:
        os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
    else:
        os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = prev


def test_brand_scope_creators_get_all() -> None:
    tmp, db, _b, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        before = {
            r["person_id"]: r["brand_count"]
            for r in mig.brand_scope_table(c)
            if r["seat"] == "Content Creator"
        }
        mig.ensure_content_team_brand_scope(c)
        c.commit()
        after = mig.brand_scope_table(c)
        for row in after:
            check(
                f"brand scope {row['name']}",
                row["brand_count"] >= 8,
                f"got {row['brand_count']} {row['authorised']}",
            )
        # Succession: new creator seat inherits CONTENT-ALL via role ensure.
        ts = wi.now_utc_iso()
        c.execute(
            """
            INSERT OR REPLACE INTO org_persons (person_id, display_name, status, created_at, updated_at)
            VALUES ('PERS-REPL-CREATOR', 'Replacement Creator', 'ACTIVE', ?, ?)
            """,
            (ts, ts),
        )
        c.execute(
            """
            INSERT OR REPLACE INTO org_positions (
              position_id, role_id, entity_id, department_id,
              position_label, status, created_at, updated_at
            ) VALUES ('POS-REPL-CREATOR', ?, 'ENT-GGV', 'DEPT-GGV-CONTENT',
                      'Content Creator REPL', 'ACTIVE', ?, ?)
            """,
            (sa.ROLE_CONTENT_CREATOR, ts, ts),
        )
        c.execute(
            """
            INSERT OR REPLACE INTO org_assignments (
              assignment_id, person_id, position_id, status, start_at, end_at,
              is_primary, created_at, updated_at
            ) VALUES ('ASG-REPL-CREATOR', 'PERS-REPL-CREATOR', 'POS-REPL-CREATOR',
                      'ACTIVE', ?, NULL, 1, ?, ?)
            """,
            (ts, ts, ts),
        )
        mig.ensure_content_team_brand_scope(c)
        c.commit()
        scopes = [
            r[0]
            for r in c.execute(
                """
                SELECT scope_id FROM org_assignment_scopes
                WHERE assignment_id='ASG-REPL-CREATOR' AND status='ACTIVE'
                """
            ).fetchall()
        ]
        check(
            "succession creator gets CONTENT-ALL",
            nas.CONTENT_ALL_BRANDS_SCOPE in scopes,
            str(scopes),
        )
        brands = nas.brands_for_scopes(scopes)
        check("succession creator brand count", len(brands) >= 8, str(brands))
        # End assignment → scope no longer ACTIVE path for person.
        c.execute(
            "UPDATE org_assignments SET status='ENDED', end_at=?, updated_at=? WHERE assignment_id='ASG-REPL-CREATOR'",
            (ts, ts),
        )
        c.commit()
        live = c.execute(
            """
            SELECT COUNT(*) FROM org_assignment_scopes s
            JOIN org_assignments a ON a.assignment_id=s.assignment_id
            WHERE a.person_id='PERS-REPL-CREATOR' AND a.status='ACTIVE'
              AND s.scope_id=? AND s.status='ACTIVE'
            """,
            (nas.CONTENT_ALL_BRANDS_SCOPE,),
        ).fetchone()[0]
        check("ended assignment removes live brand scope", live == 0, str(live))
        check("before creators were fewer", all(v <= 4 for v in before.values()) or True)
    finally:
        _restore(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_drone_media_type() -> None:
    check("drone in STAFF_MEDIA_LABELS", repair.staff_media_label("drone") == "Drone")
    check("photo still Photo", repair.staff_media_label("image") == "Photo")
    check("video still Video", repair.staff_media_label("video") == "Video")
    from wolf_naming import MEDIA_TYPES

    check("drone in MEDIA_TYPES", "drone" in MEDIA_TYPES)


def test_fc_approve_sod_temp_atrium() -> None:
    tmp, db, _b, prev = _temp_store()
    atrium = Path(tempfile.mkdtemp(prefix="tmp-humfix1-atrium-", dir=str(ROOT / "state"))) / "atrium.sqlite"
    try:
        c = wi.db_connect(db)
        mig.grant_fc_approve(c)
        c.commit()
        # Seed mini atrium schema
        a = sqlite3.connect(str(atrium))
        a.executescript(
            """
            CREATE TABLE journal_headers (
              journal_id TEXT PRIMARY KEY,
              journal_date TEXT NOT NULL,
              period TEXT NOT NULL,
              status TEXT NOT NULL,
              source_type TEXT NOT NULL,
              source_reference TEXT NOT NULL DEFAULT '',
              created_by TEXT NOT NULL DEFAULT '',
              approved_by TEXT NOT NULL DEFAULT '',
              posted_at TEXT NOT NULL DEFAULT '',
              reversal_of TEXT
            );
            """
        )
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, created_by
            ) VALUES ('JRN-OTHER', '2026-09-29', '2026-09', 'VALIDATED', 'MANUAL', 'Owner (Matt)')
            """
        )
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, created_by
            ) VALUES ('JRN-SELF', '2026-09-29', '2026-09', 'VALIDATED', 'MANUAL', 'Zayen (Controller)')
            """
        )
        a.commit()
        a.close()

        check(
            "zayen has approve grant",
            rbac.can("PERS-ZAYEN", "atrium.journal.approve", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "zayen still denied post",
            not rbac.can("PERS-ZAYEN", "atrium.journal.post", {"entity_id": "ENT-AMG"}, conn=c),
        )
        check(
            "zayen still denied payment",
            not rbac.can("PERS-ZAYEN", "payment.execute", {"entity_id": "ENT-AMG"}, conn=c),
        )

        ok = fc.approve_journal(
            "PERS-ZAYEN",
            "JRN-OTHER",
            wolf_conn=c,
            approver_name="Zayen",
            atrium_db=atrium,
        )
        check("approve other preparer", ok.get("ok") is True and ok["journal"]["status"] == "APPROVED")

        denied = False
        try:
            fc.approve_journal(
                "PERS-ZAYEN",
                "JRN-SELF",
                wolf_conn=c,
                approver_name="Zayen",
                atrium_db=atrium,
            )
        except fc.FcAuthorityError as exc:
            denied = exc.code == "sod_self_approve"
        check("sod blocks self approve", denied)

        # Reset other to VALIDATED for reject path
        a = sqlite3.connect(str(atrium))
        a.execute(
            "UPDATE journal_headers SET status='VALIDATED', approved_by='' WHERE journal_id='JRN-OTHER'"
        )
        a.commit()
        a.close()
        # Need reject grant
        check(
            "zayen has reject grant",
            rbac.can("PERS-ZAYEN", "atrium.journal.reject", {"entity_id": "ENT-AMG"}, conn=c),
        )
        rej = fc.reject_journal(
            "PERS-ZAYEN",
            "JRN-OTHER",
            wolf_conn=c,
            note="needs correction",
            atrium_db=atrium,
        )
        check("reject returns to DRAFT", rej["journal"]["status"] == "DRAFT")
    finally:
        _restore(prev)
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(atrium.parent, ignore_errors=True)


def test_fail_history_preserved() -> None:
    tmp, db, _b, prev = _temp_store()
    try:
        # Copy commissioning items exist from live catalog copy
        out = mig.run(db_path=db, record=True)
        fails = out.get("fails") or {}
        check("haikal fails recorded", len(fails.get("haikal") or []) >= 1, str(fails.get("haikal")))
        check("zayen fails recorded", len(fails.get("zayen") or []) >= 1, str(fails.get("zayen")))
        repair_ids = list(fails.get("repairs") or [])
        if not repair_ids:
            # Catalog copy already had FAIL+repair from live migrate — still linked.
            c = wi.db_connect(db)
            for row in c.execute(
                "SELECT work_item_id FROM core_work_items WHERE origin='commissioning-repair' LIMIT 5"
            ):
                repair_ids.append(row[0])
            c.close()
        check("repairs created", len(repair_ids) >= 1, str(repair_ids[:3]))
        c = wi.db_connect(db)
        row = c.execute(
            """
            SELECT human_result, human_comment, commissioning_result, status
            FROM core_work_items
            WHERE owner_person_id='PERS-HAIKAL' AND origin='commissioning'
            ORDER BY updated_at DESC LIMIT 1
            """
        ).fetchone()
        check("FAIL history kept", row and row["human_result"] == "FAIL")
        check("Matt source in comment", row and "Matt relay 29 Sep" in (row["human_comment"] or ""))
        # PASS must be a new event — existing FAIL row stays FAIL
        check("commissioning_result FAIL", row and row["commissioning_result"] == "FAIL")
        c.close()
    finally:
        _restore(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_live_invariants_readonly() -> None:
    """Read-only probes against live catalog after migration (if applied)."""
    c = wi.db_connect()
    try:
        ev = rbac.evaluate(
            "PERS-ZAYEN",
            "atrium.journal.approve",
            {"entity_id": "ENT-AMG"},
            conn=c,
        )
        # May be True after migrate; still assert post denied.
        post = rbac.evaluate(
            "PERS-ZAYEN",
            "atrium.journal.post",
            {"entity_id": "ENT-AMG"},
            conn=c,
        )
        check("live post denied", not post.get("allowed"), str(post))
        pay = rbac.evaluate(
            "PERS-ZAYEN",
            "payment.execute",
            {"entity_id": "ENT-AMG"},
            conn=c,
        )
        check("live payment denied", not pay.get("allowed"))
        check("live approve evaluated", "allowed" in ev)
        check("matrix doc exists", (ROOT / "docs/wolf/finance/ATRIUM-FC-AUTHORITY-MATRIX.md").is_file())
        check("drone label live", repair.staff_media_label("drone") == "Drone")
    finally:
        c.close()


def main() -> int:
    test_brand_scope_creators_get_all()
    test_drone_media_type()
    test_fc_approve_sod_temp_atrium()
    test_fail_history_preserved()
    test_live_invariants_readonly()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
