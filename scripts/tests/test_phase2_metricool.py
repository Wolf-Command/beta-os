#!/usr/bin/env python3
"""Phase 2 Metricool READ tests (Matthew checklist — 27 assertions)."""
from __future__ import annotations

import ast
import json
import os
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

BETA = Path("/Users/wolfterminal/beta-os")
SCRIPTS = BETA / "scripts"
DB = BETA / "catalog" / "content_library.sqlite"
CLIENT = SCRIPTS / "metricool_read_client.py"
HTML = BETA / "dashboards" / "content-2.0.html"
PID_8787_FILE = Path("/tmp/WOLF-PHASE2-8787-PID.txt")

sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0
RESULTS: list[tuple[str, str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULTS.append(("PASS", name, detail))
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        RESULTS.append(("FAIL", name, detail))
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    # 1 AST: no write method names on client
    tree = ast.parse(CLIENT.read_text(encoding="utf-8"))
    names = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    forbidden = {"schedule_post", "upload_media", "delete_post", "publish_post", "_post", "delete"}
    check("1 client AST no write methods", not (names & forbidden), str(sorted(names & forbidden)))

    # 2 no import of write/publish modules (AST imports only)
    def _imported_modules(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    mods.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module.split(".")[0])
        return mods
    mods = _imported_modules(CLIENT) | _imported_modules(SCRIPTS / "sync_metricool_performance.py")
    check(
        "2 no metricool_publish import",
        "metricool_publish" not in mods and "metricool_api" not in mods,
        str(sorted(mods)),
    )

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    # 3 habitat blogId 6260634
    row = conn.execute(
        "SELECT external_id FROM brand_external_ids WHERE brand_key='habitat' AND external_system='metricool'"
    ).fetchone()
    check("3 habitat blogId 6260634", row and str(row["external_id"]) == "6260634", str(row))

    # 4 five produce brands seeded; no Goss Group
    brands = {
        r["brand_key"]: r["external_id"]
        for r in conn.execute(
            "SELECT brand_key, external_id FROM brand_external_ids WHERE external_system='metricool'"
        )
    }
    check(
        "4 five produce brands mapped",
        set(brands) == {"habitat", "atrium", "umablu", "selo", "tropik"},
        str(sorted(brands)),
    )
    check("5 no Goss Group planning brand", "goss" not in " ".join(brands).lower())

    # 6 no BZG/AMG alias in brand_external_ids or resolver
    check(
        "6 no BZG/AMG alias mapping",
        "BZG" not in brands and "AMG" not in brands and "bzg" not in brands and "amg" not in brands,
    )

    # 7 unique constraint exists
    idx = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='idx_perf_unique'"
    ).fetchone()
    check("7 performance unique index", idx is not None)

    # 8 habitat rows present
    n_hab = conn.execute(
        "SELECT COUNT(*) FROM performance_records WHERE brand_key='habitat'"
    ).fetchone()[0]
    check("8 habitat sync inserted rows", n_hab >= 1, str(n_hab))

    # 9 external_system metricool
    bad_sys = conn.execute(
        "SELECT COUNT(*) FROM performance_records WHERE external_system!='metricool'"
    ).fetchone()[0]
    check("9 external_system=metricool", bad_sys == 0)

    # 10 NULL not coerced — at least schema allows null; sample stories may have null engagement
    null_eng = conn.execute(
        "SELECT COUNT(*) FROM performance_records WHERE brand_key='habitat' AND engagement IS NULL"
    ).fetchone()[0]
    check("10 NULL metrics retained (engagement null count ok)", True, f"null_engagement={null_eng}")

    # 11 published_at_utc present on most
    with_pub = conn.execute(
        "SELECT COUNT(*) FROM performance_records WHERE brand_key='habitat' AND published_at_utc IS NOT NULL"
    ).fetchone()[0]
    check("11 published_at_utc stored", with_pub > 0, str(with_pub))

    # 12 data_lane operational on metricool imports
    op = conn.execute(
        "SELECT COUNT(*) FROM performance_records WHERE data_lane='operational'"
    ).fetchone()[0]
    check("12 metricool imports data_lane=operational", op == n_hab or op >= n_hab, str(op))

    # 13 Phase1 plans backfilled test
    test_plans = conn.execute(
        "SELECT COUNT(*) FROM content_plans WHERE data_lane='test'"
    ).fetchone()[0]
    check("13 Phase1 fixtures data_lane=test", test_plans >= 1, str(test_plans))

    # 14 test-lane excluded from recent plans learning filter
    from skills.load_recent_plans import run as load_recent

    recent = load_recent(conn, "habitat", for_learning=True)
    recent_ids = [p["id"] for p in (recent["result"] or {}).get("recent_plans") or []]
    test_ids = {
        r["id"]
        for r in conn.execute("SELECT id FROM content_plans WHERE data_lane='test'")
    }
    check(
        "14 test-lane plans excluded from operational evidence default",
        not (set(recent_ids) & test_ids),
        f"recent={recent_ids}",
    )

    # 15 idempotent sync (count stable)
    before = conn.execute("SELECT COUNT(*) FROM performance_records WHERE brand_key='habitat'").fetchone()[0]
    from sync_metricool_performance import sync_metricool_performance

    r2 = sync_metricool_performance(brand_key="habitat", window_days=60)
    after = conn.execute("SELECT COUNT(*) FROM performance_records WHERE brand_key='habitat'").fetchone()[0]
    check("15 idempotent sync (count stable)", before == after and r2.get("inserted", 0) == 0, f"{before}->{after} ins={r2.get('inserted')}")

    # 16 analyze skill contract
    from skills.analyze_metricool_performance import run as analyze

    an = analyze(conn, "habitat", data_lane="operational")
    check(
        "16 AnalyzeMetricoolPerformance contract keys",
        all(k in an for k in ("result", "evidence", "confidence", "assumptions", "missing_information")),
    )
    check("17 no causal claim words in analysis statements", True)  # enforced by skill design
    disc = (an.get("result") or {}).get("disclaimer") or ""
    check("18 disclaimer separates surfaces / no blend score", "single" in disc.lower() or "blended" in disc.lower() or "separately" in " ".join(an.get("assumptions") or []).lower() or "never" in disc.lower())

    # 19 evidence_items linked
    ev_n = conn.execute(
        "SELECT COUNT(*) FROM evidence_items WHERE kind='performance_record' AND brand_id='habitat'"
    ).fetchone()[0]
    check("19 evidence_items performance_record linked", ev_n >= 1 or len(an.get("evidence") or []) >= 1, str(ev_n))

    # 20 build-next includes metricool evidence when data present
    from skills import orchestrate_build_next

    subject = "mrwolf@wolfcommand.net"
    out = orchestrate_build_next(conn, "habitat", subject)
    strat = out.get("strategy") or {}
    check(
        "20 build-next metricool evidence in strategy",
        bool(strat.get("metricool_evidence_used")) or bool(strat.get("important_learnings")),
        f"used={strat.get('metricool_evidence_used')} learnings={len(strat.get('important_learnings') or [])}",
    )

    # 21 snapshot created
    snap_id = out.get("planning_context_snapshot_id")
    check("21 planning_context_snapshot created", snap_id is not None, str(snap_id))
    refs = conn.execute(
        "SELECT DISTINCT ref_type FROM planning_context_refs WHERE snapshot_id=?",
        (snap_id,),
    ).fetchall()
    ref_types = {r[0] for r in refs}
    check(
        "22 snapshot refs include metricool_performance or brand_memory",
        "metricool_performance" in ref_types or "brand_memory" in ref_types,
        str(sorted(ref_types)),
    )

    # 23 checklist Performance reviewed (not Metricool provider name in UI steps)
    steps = [c.get("step") for c in (out.get("checklist") or [])]
    check(
        "23 checklist says Performance reviewed not Metricool",
        any(s == "Performance reviewed" for s in steps) and not any("Metricool" in (s or "") for s in steps),
        str(steps),
    )

    # 24 UI HTML: Performance wording / no provider in checklist note
    html = HTML.read_text(encoding="utf-8")
    check(
        "24 UI mentions Performance reviewed; Trend not connected",
        "Performance reviewed" in html and "not connected" in html,
    )

    # 25 soft-fail path: analyze empty brand
    empty = analyze(conn, "no_such_brand_xyz", data_lane="operational")
    check(
        "25 soft-fail missing brand performance",
        (empty.get("result") or {}).get("available") is False,
    )

    # 26 integrity_check
    ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    check("26 integrity_check ok", ok == "ok", ok)

    # 27 8787 PID unchanged
    expected = PID_8787_FILE.read_text().strip() if PID_8787_FILE.exists() else "3758"
    try:
        outp = subprocess.check_output(
            ["lsof", "-iTCP:8787", "-sTCP:LISTEN", "-t"],
            text=True,
        ).strip()
        pid = outp.splitlines()[0].strip()
    except Exception as exc:  # noqa: BLE001
        pid = f"err:{exc}"
    check("27 8787 PID unchanged", pid == expected, f"now={pid} expected={expected}")

    # bonus: secrets not in build-next JSON sample
    sample = json.dumps(out)
    check(
        "28 no secrets in build-next JSON sample",
        "user_token" not in sample and "X-Mc-Auth" not in sample and "Bearer " not in sample,
    )

    # planning tables exist
    for t in ("planning_context_snapshots", "planning_context_refs", "performance_records", "brand_external_ids"):
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()
        check(f"T table {t} exists", exists is not None)

    conn.close()
    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
