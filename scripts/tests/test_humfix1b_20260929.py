#!/usr/bin/env python3
"""HUMFIX-1B — Peaches eye-gap repairs (Beta).

Decision served: Matt relay 29 Sep 2026 ~11:14 WITA / HUMFIX-1 extension.
Temp store for flow tests. Live catalog/atrium read-only for probes.
"""
from __future__ import annotations

import importlib.util
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
from core import nas_library as nas  # noqa: E402
from core import rbac  # noqa: E402
from core import staff_access as sa  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_home import build_home  # noqa: E402

_mig = ROOT / "scripts" / "migrations" / "migrate_humfix1b_20260929.py"
_spec = importlib.util.spec_from_file_location("migrate_humfix1b_20260929", _mig)
mig = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(mig)

CATALOG = ROOT / "catalog" / "content_library.sqlite"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
PASS = 0
FAIL = 0

CONTENT_TEAM = (
    ("PERS-HAIKAL", "Haikal"),
    ("PERS-MISA", "Misa"),
    ("PERS-ZARAH", "Zarah"),
    ("PERS-FRAIL", "Frail"),
    ("PERS-YUDI", "Yudi"),
    ("PERS-GERY", "Gery"),
    ("PERS-ALAM", "Alam"),
    ("PERS-TJ", "TJ"),
    ("PERS-NATA", "Nata"),
    ("PERS-RAPP", "Rapp"),
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _temp_store():
    tmp = Path(tempfile.mkdtemp(prefix="tmp-humfix1b-", dir=str(ROOT / "state")))
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


def test_held_retests_excluded() -> None:
    tmp, db, _b, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        out = mig.hold_premature_retests(c)
        c.commit()
        check("held count 12", out["count"] == 12, str(out["count"]))
        home = build_home("PERS-HAIKAL", conn=c)
        titles = []
        for sec in home.get("sections") or []:
            for item in sec.get("items") or []:
                titles.append(item.get("title") or "")
        check(
            "haikal my work hides held retests",
            not any("Retest:" in t for t in titles),
            str(titles[:8]),
        )
        reopen = mig.reopen_held_retests(c)
        c.commit()
        check("reopen restores 12", reopen["count"] == 12, str(reopen))
    finally:
        _restore(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_ledger_no_invented_posted() -> None:
    probe = mig.posted_ledger_probe(ATRIUM_DB)
    check(
        "beta atrium has zero posted journals",
        probe["posted_journals"] == 0 and probe["posted_lines"] == 0,
        str(probe),
    )
    check("property_name empty (truthful unset)", probe["property_name"] == "", str(probe))
    gl = (ROOT / ".." / "atrium-finance" / "src" / "components" / "GeneralLedgerView.tsx").resolve()
    if not gl.is_file():
        gl = Path("/Users/wolfterminal/atrium-finance/src/components/GeneralLedgerView.tsx")
    text = gl.read_text(encoding="utf-8")
    check(
        "GL empty state names ENT-AMG honestly",
        "No posted journal lines for ENT-AMG yet" in text,
    )
    chip = (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    check("chip says Property unset not SETUP INCOMPLETE live", "Property unset" in chip)
    check("chip no longer paints SETUP INCOMPLETE as primary", 'textContent = "SETUP INCOMPLETE"' not in chip)


def test_zayen_title_from_wolf_role() -> None:
    path = Path("/Users/wolfterminal/atrium-finance/server/betaMount.ts")
    text = path.read_text(encoding="utf-8")
    check(
        "betaMount maps FC title",
        "Atrium Financial Controller" in text and "WOLF_SEAT_TITLE" in text,
    )
    c = wi.db_connect(CATALOG)
    try:
        row = c.execute(
            """
            SELECT p.position_label, r.display_name, r.role_id
            FROM org_assignments a
            JOIN org_positions p ON p.position_id=a.position_id
            JOIN org_roles r ON r.role_id=p.role_id
            WHERE a.person_id='PERS-ZAYEN' AND a.status='ACTIVE'
            """
        ).fetchone()
        check(
            "canonical assignment is Atrium Financial Controller",
            row is not None
            and row[0] == "Atrium Financial Controller"
            and "FINANCIAL-CONTROLLER" in (row[2] or ""),
            str(row),
        )
    finally:
        c.close()


def test_journal_post_ui_denied_and_fresh_fixture() -> None:
    jw = Path("/Users/wolfterminal/atrium-finance/src/components/JournalWorkbenchView.tsx")
    text = jw.read_text(encoding="utf-8")
    check("workbench gates canPostJournals", "canPostJournals" in text)
    check(
        "post denied reason present",
        "Posting needs Owner approval — policy pending" in text,
    )
    check("SoD reason present", "segregation of duties" in text.lower())
    mulzij = mig.verify_mulzij_preparer(ATRIUM_DB)
    check("JRN-MULZIJ3N-117 found", mulzij.get("found") is True, str(mulzij))
    check("MULZIJ prepared by Zayen", mulzij.get("zayen_prepared") is True, str(mulzij))
    fresh = mig.seed_fresh_sod_journal(ATRIUM_DB)
    check(
        "fresh SoD journal VALIDATED by Owner",
        fresh.get("ok") and fresh.get("status") == "VALIDATED" and "Owner" in (fresh.get("created_by") or ""),
        str(fresh),
    )
    # Approve path on TEMP atrium only — never mutate live PREP2 via approve in this test.
    tmp, db, _b, prev = _temp_store()
    atrium = Path(tempfile.mkdtemp(prefix="tmp-humfix1b-atrium-", dir=str(ROOT / "state"))) / "atrium.sqlite"
    try:
        c = wi.db_connect(db)
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
            ) VALUES ('JRN-TEMP-OTHER', '2026-09-29', '2026-09', 'VALIDATED', 'MANUAL', 'Owner (Matt)')
            """
        )
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, created_by
            ) VALUES ('JRN-TEMP-SELF', '2026-09-29', '2026-09', 'VALIDATED', 'MANUAL', 'Zayen')
            """
        )
        a.commit()
        a.close()
        p = ROOT / "scripts" / "migrations" / "migrate_humfix1_20260929.py"
        sp = importlib.util.spec_from_file_location("migrate_humfix1_20260929", p)
        h1m = importlib.util.module_from_spec(sp)
        assert sp and sp.loader
        sp.loader.exec_module(h1m)
        h1m.grant_fc_approve(c)
        c.commit()
        ok = fc.approve_journal(
            "PERS-ZAYEN",
            "JRN-TEMP-OTHER",
            wolf_conn=c,
            approver_name="Zayen",
            atrium_db=atrium,
        )
        check("temp approve other preparer", ok.get("ok") is True, str(ok))
        denied = False
        try:
            fc.approve_journal(
                "PERS-ZAYEN",
                "JRN-TEMP-SELF",
                wolf_conn=c,
                approver_name="Zayen",
                atrium_db=atrium,
            )
        except fc.FcAuthorityError as exc:
            denied = exc.code == "sod_self_approve"
        check("temp sod blocks self", denied)
        live = sqlite3.connect(str(ATRIUM_DB))
        st = live.execute(
            "SELECT status FROM journal_headers WHERE journal_id='JRN-HUMFIX-PREP2'"
        ).fetchone()
        live.close()
        check("live PREP2 still VALIDATED", st and st[0] == "VALIDATED", str(st))
    finally:
        _restore(prev)
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(atrium.parent, ignore_errors=True)


def test_content_plan_current_window() -> None:
    import serve_beta as sb

    today = "2026-09-29"
    rows = [
        {
            "id": 1,
            "status": "Human_Approved",
            "period_start": "2026-09-14",
            "period_end": "2026-09-27",
        },
        {
            "id": 2,
            "status": "Working_Draft",
            "period_start": "2026-09-28",
            "period_end": "2026-10-11",
        },
    ]
    current, history = sb._rank_current_plans(rows, today)
    check("current picks in-window plan", len(current) == 1 and current[0]["id"] == 2, str(current))
    check("stale plan is history", len(history) == 1 and history[0]["id"] == 1, str(history))
    empty_c, empty_h = sb._rank_current_plans(
        [{"id": 9, "status": "Human_Approved", "period_start": "2026-09-14", "period_end": "2026-09-27"}],
        today,
    )
    check("no current when only stale", len(empty_c) == 0 and len(empty_h) == 1)
    # Live habitat: today 29 Sep → no covering plan
    c = wi.db_connect(CATALOG)
    try:
        live = [
            dict(r)
            for r in c.execute(
                """
                SELECT id, brand_id, title, status, period_start, period_end
                FROM content_plans
                WHERE brand_id='habitat' AND ifnull(data_lane,'operational')='operational'
                  AND lower(ifnull(status,'')) IN ('working_draft','human_approved','ready_for_render')
                """
            ).fetchall()
        ]
        cur, hist = sb._rank_current_plans(live, today)
        check("live habitat has no current plan on 29 Sep", len(cur) == 0, str(cur))
        check("live habitat history non-empty", len(hist) >= 1, str(len(hist)))
        name = sb._resolve_assignee_display(c, "haikalqilbari123@gmail.com")
        check("assignee email resolves to Haikal", name == "Haikal", name)
    finally:
        c.close()


def test_content_team_brands_and_commissioning_temp() -> None:
    tmp, db, _b, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        mig.dedupe_assignment_scopes(c)
        c.commit()
        table = mig.content_team_brand_table(c)
        check("content team table has 10", len(table) == 10, str(len(table)))
        for row in table:
            check(
                f"{row['name']} has 8 brands",
                row["brand_count"] >= 8 and row["has_content_all"],
                str(row),
            )
        for pid, name in CONTENT_TEAM:
            asg = c.execute(
                """
                SELECT assignment_id FROM org_assignments
                WHERE person_id=? AND status='ACTIVE'
                ORDER BY is_primary DESC LIMIT 1
                """,
                (pid,),
            ).fetchone()
            item = umw._create_commission_task(
                c,
                title=f"HUMFIX-1B commission check · {name}",
                owner_person_id=pid,
                owner_assignment_id=asg[0] if asg else None,
                entity_id="ENT-GGV",
                capability_id=f"COMM-HUMFIX1B-{pid}",
                instructions="1. Open My Work.\n2. Attach evidence.\n3. Choose PASS.\n4. Press DONE.",
                evidence_required="screenshot or note",
                href_hint="/my-work",
                scope_label="HUMFIX-1B temp",
            )
            wid = item["work_item_id"]
            wi.start_work_item(wid, verified_person_id=pid, conn=c, commit=False)
            umw.store_evidence_file(
                wid,
                filename="humfix1b-note.txt",
                content=f"Commissioning evidence for {name}".encode(),
                uploaded_by_person_id=pid,
                conn=c,
                commit=False,
            )
            done = umw.mark_done(
                wid,
                verified_person_id=pid,
                human_result="PASS",
                human_comment="temp commission ok",
                conn=c,
                commit=False,
            )
            row = c.execute(
                "SELECT status, human_result FROM core_work_items WHERE work_item_id=?",
                (wid,),
            ).fetchone()
            check(
                f"{name} commissioning reaches DONE/VERIFY",
                row is not None
                and row["human_result"] == "PASS"
                and row["status"] in {"COMPLETED", "AWAITING_VERIFY", "VERIFIED"},
                str(dict(row) if row else done),
            )
        c.commit()
    finally:
        _restore(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_drone_still_present() -> None:
    from core import content_engine_repair as repair
    from wolf_naming import MEDIA_TYPES

    check("drone media type", "drone" in MEDIA_TYPES)
    check("drone label", repair.staff_media_label("drone") == "Drone")


def main() -> int:
    test_held_retests_excluded()
    test_ledger_no_invented_posted()
    test_zayen_title_from_wolf_role()
    test_journal_post_ui_denied_and_fresh_fixture()
    test_content_plan_current_window()
    test_content_team_brands_and_commissioning_temp()
    test_drone_still_present()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
