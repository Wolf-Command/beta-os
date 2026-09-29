#!/usr/bin/env python3
"""HUMANCOMM-1 — employee commissioning loop, repair/retest, legacy routing (Beta).

Decision served: Matt 29 Sep 2026 11:12 START HUMAN COMMISSIONING NOW.
Isolated temp store only — never mutates live core_work_items for flow tests.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "tests"))

import importlib.util  # noqa: E402

import serve_beta as sb  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_home import build_home  # noqa: E402

_mig_path = ROOT / "scripts" / "migrations" / "migrate_humancomm1_20260929.py"
_spec = importlib.util.spec_from_file_location("migrate_humancomm1_20260929", _mig_path)
mig = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(mig)

OWNER = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
ZAYEN = "laluzayen@gmail.com"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
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


def call(port: int, method: str, path: str, email: str | None = None, body: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if email:
        headers["X-Wolf-Subject"] = email
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, data=data, method=method)
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def _temp_store():
    tmp = Path(tempfile.mkdtemp(prefix="tmp-humancomm1-", dir=str(ROOT / "state")))
    db = tmp / "catalog.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CATALOG, db)
    mig.run(db_path=db, apply_routing=True)
    prev = os.environ.get("WOLF_WORK_EVIDENCE_BLOBS")
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    return tmp, db, blobs, prev


def _restore_blobs(prev):
    if prev is None:
        os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
    else:
        os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = prev


def test_done_blocked_without_evidence() -> None:
    tmp, db, _blobs, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        row = c.execute(
            """
            SELECT work_item_id FROM core_work_items
            WHERE origin='commissioning' AND owner_person_id='PERS-DEVI' AND status='OPEN'
            LIMIT 1
            """
        ).fetchone()
        wid = row["work_item_id"]
        wi.start_work_item(wid, verified_person_id="PERS-DEVI", conn=c, commit=False)
        blocked = False
        try:
            umw.mark_done(
                wid,
                verified_person_id="PERS-DEVI",
                human_result="PASS",
                conn=c,
                commit=False,
            )
        except umw.MyWorkError as exc:
            blocked = exc.code == "done_blocked"
            check("done blocked message clear", "evidence" in str(exc).lower() or "PASS" in str(exc), str(exc))
        check("DONE blocked without evidence", blocked)
        # Still blocked without PASS/FAIL even with evidence.
        umw.store_evidence_file(
            wid, filename="a.txt", content=b"shot", uploaded_by_person_id="PERS-DEVI", conn=c, commit=False
        )
        blocked2 = False
        try:
            umw.mark_done(wid, verified_person_id="PERS-DEVI", conn=c, commit=False)
        except umw.MyWorkError as exc:
            blocked2 = exc.code == "done_blocked"
        check("DONE blocked without PASS/FAIL", blocked2)
        c.close()
    finally:
        _restore_blobs(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_fail_repair_retest_loop() -> None:
    tmp, db, _blobs, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        row = c.execute(
            """
            SELECT work_item_id, owner_person_id, commissioning_capability_id
            FROM core_work_items
            WHERE origin='commissioning' AND owner_person_id='PERS-ZAYEN' AND status='OPEN'
            LIMIT 1
            """
        ).fetchone()
        wid = row["work_item_id"]
        person = row["owner_person_id"]
        wi.start_work_item(wid, verified_person_id=person, conn=c, commit=False)
        umw.store_evidence_file(
            wid, filename="bad.png", content=b"png", uploaded_by_person_id=person, conn=c, commit=False
        )
        done = umw.mark_done(
            wid,
            verified_person_id=person,
            human_result="FAIL",
            human_comment="Ledger shows wrong currency",
            conn=c,
            commit=False,
        )
        repair = done.get("repair_item") or {}
        check("employee FAIL creates repair", bool(repair.get("work_item_id")))
        check(
            "repair on ENGINEERING queue",
            repair.get("origin") == "commissioning-repair"
            and not repair.get("owner_person_id")
            and not repair.get("executor_person_id"),
            str(repair.get("owner_person_id")),
        )
        check(
            "repair not owned by employee",
            repair.get("owner_person_id") != person,
            str(repair.get("owner_person_id")),
        )
        rid = repair["work_item_id"]
        umw.store_evidence_file(
            rid,
            filename="fix.txt",
            content=b"commit abc123 fixed",
            uploaded_by_person_id="PERS-MATT",
            conn=c,
            commit=False,
        )
        fixed = umw.mark_done(
            rid,
            verified_person_id="PERS-MATT",
            repair_commit_ref="abc123",
            outcome="fixed",
            conn=c,
            commit=False,
        )
        retest = fixed.get("retest_item") or {}
        check("retest issued after repair DONE", bool(retest.get("work_item_id")))
        check(
            "retest to same person",
            retest.get("owner_person_id") == person,
            str(retest.get("owner_person_id")),
        )
        check("retest origin", retest.get("origin") == "commissioning-retest")
        # Retest lands in their My Work TODAY/DO THIS NEXT.
        sections = umw.build_universal_sections(person, conn=c)
        pool = []
        for s in sections:
            if s.get("key") in {"today", "do_this_next"}:
                pool.extend(s.get("items") or [])
        check(
            "retest visible in My Work",
            any(it.get("work_item_id") == retest["work_item_id"] for it in pool),
        )
        c.commit()
        c.close()
    finally:
        _restore_blobs(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_pass_awaiting_verify() -> None:
    tmp, db, _blobs, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        row = c.execute(
            """
            SELECT work_item_id FROM core_work_items
            WHERE origin='commissioning' AND owner_person_id='PERS-AMANDA' AND status='OPEN'
            LIMIT 1
            """
        ).fetchone()
        wid = row["work_item_id"]
        wi.start_work_item(wid, verified_person_id="PERS-AMANDA", conn=c, commit=False)
        umw.store_evidence_file(
            wid, filename="ok.txt", content=b"ok", uploaded_by_person_id="PERS-AMANDA", conn=c, commit=False
        )
        done = umw.mark_done(
            wid,
            verified_person_id="PERS-AMANDA",
            human_result="PASS",
            conn=c,
            commit=False,
        )
        check(
            "PASS → AWAITING_VERIFY",
            (done.get("work_item") or {}).get("status") == "AWAITING_VERIFY",
            str((done.get("work_item") or {}).get("status")),
        )
        check("DONE does not verify", done.get("verified") is False)
        check("staff_ready false", done.get("staff_ready") is False)
        check("human_commissioned false", done.get("human_commissioned") is False)
        check("system % unchanged", done.get("system_percent_unchanged") is True)
        ver = umw.verify_commissioning(
            wid, verifier_person_id="PERS-MATT", result="PASS", note="good", conn=c, commit=False
        )
        check("verified HUMAN PASS", ver.get("commissioning_result") == "PASS")
        check("status VERIFIED", (ver.get("work_item") or {}).get("status") == "VERIFIED")
        check("verify still not staff_ready", ver.get("staff_ready") is False)
        c.commit()
        c.close()
    finally:
        _restore_blobs(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_legacy_needs_routing() -> None:
    tmp, db, _blobs, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        n_needs = c.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE origin='legacy' AND routing_state='NEEDS_ROUTING'"
        ).fetchone()[0]
        check("legacy NEEDS_ROUTING present", n_needs >= 1, str(n_needs))
        null_owner = c.execute(
            """
            SELECT COUNT(*) FROM core_work_items
            WHERE origin='legacy' AND routing_state='NEEDS_ROUTING'
              AND (owner_person_id IS NULL OR owner_person_id='')
            """
        ).fetchone()[0]
        check("NEEDS_ROUTING owner null", null_owner == n_needs, f"{null_owner}/{n_needs}")
        # Not in Devi My Work.
        sections = umw.build_universal_sections("PERS-DEVI", conn=c)
        for s in sections:
            for it in s.get("items") or []:
                check(
                    "no NEEDS_ROUTING in Devi My Work",
                    it.get("routing_state") != "NEEDS_ROUTING",
                    it.get("work_item_id"),
                )
        over = umw.owner_work_exceptions(conn=c)
        check(
            "NEEDS_ROUTING on Overwatch",
            any(it.get("routing_state") == "NEEDS_ROUTING" for it in over),
        )
        c.close()
    finally:
        _restore_blobs(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_live_results_and_tick() -> None:
    tmp, db, _blobs, prev = _temp_store()
    try:
        c = wi.db_connect(db)
        snap = umw.live_commissioning_results(conn=c)
        check("live results ok", snap.get("ok") is True)
        check("live results rows", isinstance(snap.get("rows"), list))
        applied = umw.commissioning_tick_apply(conn=c, commit=True)
        check("tick never auto-verifies", applied.get("auto_verify_pass") is False)
        c.close()
    finally:
        _restore_blobs(prev)
        shutil.rmtree(tmp, ignore_errors=True)


def test_live_catalog_invariants() -> None:
    conn = sqlite3.connect(str(CATALOG))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(core_work_items)")}
    for col in ("human_result", "human_comment", "opened_at", "routing_state", "routing_reason"):
        check(f"live column {col}", col in cols)
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='core_work_items'"
    ).fetchone()[0]
    check("live status allows AWAITING_VERIFY", "AWAITING_VERIFY" in (sql or ""))
    comm = conn.execute(
        "SELECT COUNT(*) FROM core_work_items WHERE origin='commissioning'"
    ).fetchone()[0]
    check("live commissioning still 28", comm == 28, str(comm))
    legacy = conn.execute(
        "SELECT COUNT(*) FROM core_work_items WHERE origin='legacy'"
    ).fetchone()[0]
    check("live legacy still 148", legacy == 148, str(legacy))
    # Sample instruction rewrite — no Matt-explains language.
    instr = conn.execute(
        """
        SELECT instructions FROM core_work_items
        WHERE commissioning_capability_id='COMM-DEVI-UMA-TODAY'
        """
    ).fetchone()[0]
    check("devi instructions numbered", instr and "1." in instr and "DONE" in instr, str(instr)[:80])
    check("devi instructions no Matt explain", "matt will" not in (instr or "").lower())
    conn.close()


def test_shots() -> None:
    import base64

    import test_mywork1b_20260929 as m1b

    SHOTS.mkdir(parents=True, exist_ok=True)
    check("chrome present", CHROME.is_file())
    if not CHROME.is_file():
        return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)

    conn = sqlite3.connect(str(CATALOG))
    conn.row_factory = sqlite3.Row
    wid = conn.execute(
        """
        SELECT work_item_id FROM core_work_items
        WHERE origin='commissioning' AND owner_person_id='PERS-DEVI' AND status='OPEN'
        LIMIT 1
        """
    ).fetchone()["work_item_id"]
    conn.close()

    ready = "(() => ({ok: document.body && document.body.getAttribute('data-ready')==='1'}))()"
    # Devi detail: wait until PASS/FAIL controls exist, then scroll them into view.
    ready_devi = (
        "(() => {"
        " const pass=document.getElementById('hpass');"
        " const done=document.getElementById('done');"
        " if (!pass || !done || document.body.getAttribute('data-ready')!=='1') return {ok:false};"
        " document.getElementById('act').scrollIntoView({block:'start'});"
        " return {ok:true};"
        "})()"
    )
    ready_header = (
        "(() => {"
        " const hello=document.querySelector('#wolfnav-hello');"
        " const label=document.querySelector('.nv-ctx-label');"
        " if (!hello || !(hello.textContent||'').includes('ROLE-MATT')) return {ok:false};"
        " return {ok:true, ctxLabel:(label && getComputedStyle(label).color) || ''};"
        "})()"
    )
    targets = [
        ("humancomm1-devi-commissioning-phone.png", DEVI, f"/my-work/item/{wid}", 390, ready_devi),
        ("humancomm1-zayen-mywork.png", ZAYEN, "/my-work", 390, ready),
        ("humancomm1-amanda-mywork.png", AMANDA, "/my-work", 390, ready),
        ("humancomm1-haikal-mywork.png", HAIKAL, "/my-work", 390, ready),
        ("humancomm1-commissioning-live.png", OWNER, "/commissioning-live", 1280, ready),
        ("humancomm1-owner-overwatch.png", OWNER, "/my-work", 1280, ready),
        ("humancomm1-needs-routing.png", OWNER, "/my-work", 1280, ready),
        ("humancomm1-header-1024.png", OWNER, "/my-work", 1024, ready_header),
    ]
    try:
        for name, email, path, width, wait_expr in targets:
            url = f"http://127.0.0.1:{port}{path}"
            for cdp, _evaluate, value in m1b._with_cdp(width, email, url, wait_expr, wait_seconds=40.0):
                check(f"chrome ready {name}", bool(value and value.get("ok")), str(value)[:160])
                if name == "humancomm1-header-1024.png":
                    check(
                        "CONTEXT label not dark-on-dark",
                        "234" in str((value or {}).get("ctxLabel") or "")
                        or "eaf3f2" in str((value or {}).get("ctxLabel") or "").lower()
                        or "rgb(234" in str((value or {}).get("ctxLabel") or ""),
                        str((value or {}).get("ctxLabel")),
                    )
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 4000, str(dest.stat().st_size if dest.is_file() else 0))
    finally:
        httpd.shutdown()


def main() -> int:
    print("=== HUMANCOMM-1 ===")
    test_live_catalog_invariants()
    test_done_blocked_without_evidence()
    test_fail_repair_retest_loop()
    test_pass_awaiting_verify()
    test_legacy_needs_routing()
    test_live_results_and_tick()
    test_shots()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
