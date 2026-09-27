#!/usr/bin/env python3
"""Matt Progress Dashboard v2 Owner Cockpit — mandatory cases (Beta).

Owner (PERS-MATT) only. Staff 403. Read-model only.
Factory health excluded from mission %. No Habitat/ESB/Metricool/Production writes.
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import os
import shutil
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_progress_dashboard.py"
OVERLAY = ROOT / "state" / "progress" / "v1_overlay.json"
HTML = ROOT / "dashboards" / "progress.html"
CANON = ROOT / "docs" / "canon" / "PROGRESS-DASHBOARD.md"
SERVE = SCRIPTS / "serve_beta.py"
CONTENT = ROOT / "dashboards" / "content-2.0.html"

# Dirty-tree paths that must remain unmodified by this slice
DIRTY_PRESERVE = [
    ROOT / "scripts" / "phase26_team.py",
    ROOT / "scripts" / "migrations" / "migrate_phase2_6_team_readiness.py",
    ROOT / "scripts" / "wolf_intelligence.py",
    ROOT / "scripts" / "skills" / "__init__.py",
]

PASS = 0
FAIL = 0
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_progress_dashboard", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> dict:
    c = sqlite3.connect(str(LIVE_DB))
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        def cnt(t):
            return int(c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) if t in tabs else -1

        return {
            "planner": cnt("content_planner"),
            "auth_limits": cnt("org_authority_limits"),
            "closes": cnt("venue_daily_closes") if "venue_daily_closes" in tabs else 0,
        }
    finally:
        c.close()


def main() -> int:
    before = live_counts()

    # --- Files exist ---
    check("progress_read_model.py exists", (SCRIPTS / "core" / "progress_read_model.py").is_file())
    check("v1_overlay.json exists", OVERLAY.is_file())
    check("progress.html exists", HTML.is_file())
    check("PROGRESS-DASHBOARD.md exists", CANON.is_file())
    check("migrate_progress_dashboard.py exists", MIG.is_file())

    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    check("overlay progress_type PARTIAL_ESTIMATE", overlay.get("progress_type") == "PARTIAL_ESTIMATE")
    check("overlay_required YES", overlay.get("overlay_required") is True)
    check("overlay CSV staleness KNOWN", overlay.get("master_build_csv_staleness") == "KNOWN")
    for row in overlay.get("rows") or []:
        check(
            f"overlay row {row.get('id')} has provenance",
            bool(row.get("source") and row.get("as_of") and row.get("confidence")),
        )
        break  # sample first; full loop below
    prov_ok = all(
        r.get("source") and r.get("as_of") and r.get("confidence") in ("DERIVED", "ESTIMATED", "CURATED")
        for r in (overlay.get("rows") or [])
    )
    check("all overlay rows have source/as_of/confidence", prov_ok, str(len(overlay.get("rows") or [])))

    # Habitat / Uma vertical honesty
    hab = (overlay.get("verticals") or {}).get("habitat") or {}
    uma = (overlay.get("verticals") or {}).get("uma_close") or {}
    hab_ids = [s.get("id") for s in (hab.get("stages") or [])]
    uma_ids = [s.get("id") for s in (uma.get("stages") or [])]
    check(
        "Habitat stages PLAN→PERFORMANCE",
        hab_ids
        == ["PLAN", "WORK", "EVIDENCE", "APPROVAL", "PUBLISH_GATE", "METRICOOL", "PERFORMANCE"],
        str(hab_ids),
    )
    met = next((s for s in (hab.get("stages") or []) if s.get("id") == "METRICOOL"), {})
    check("Habitat Metricool WRITE_LOCKED", met.get("state") == "WRITE_LOCKED")
    check(
        "Uma stages ESB→VERIFIED",
        uma_ids == ["ESB", "SNAPSHOT", "CASH", "RECONCILE", "EXCEPTION", "RESOLUTION", "VERIFIED"],
        str(uma_ids),
    )
    check("Uma WAITING_FOR_CLOSER", uma.get("waiting") == "WAITING_FOR_CLOSER")
    check("Uma variance NOT_CONFIGURED", uma.get("variance_policy") == "NOT_CONFIGURED")

    ach = overlay.get("achievements") or []
    check("achievements present", len(ach) >= 4)
    check("all achievements locked", all(a.get("locked") for a in ach))

    # --- Read model ---
    import core.progress_read_model as prm

    model = prm.build_read_model()
    check("model ok", model.get("ok") is True)
    check("model SYSTEM_FROM_LEDGER", model.get("progress_type") == "SYSTEM_FROM_LEDGER")
    check("model legacy PARTIAL_ESTIMATE", model.get("legacy_progress_type") == "PARTIAL_ESTIMATE")
    check("overall label PARTIAL ESTIMATE", (model.get("overall") or {}).get("label") == "PARTIAL ESTIMATE")
    check("overall retired_as_primary", (model.get("overall") or {}).get("retired_as_primary") is True)
    check("overall_pct is int", isinstance((model.get("overall") or {}).get("overall_pct"), int))
    pct = (model.get("overall") or {}).get("overall_pct")
    check("no fake precision (no float % display field)", "overall_pct_float" not in (model.get("overall") or {}))
    check("pct in 0..100", isinstance(pct, int) and 0 <= pct <= 100, str(pct))
    check("system dial present", (model.get("system") or {}).get("label") == "SYSTEM")
    check("system_pct computed float or None", (model.get("system") or {}).get("system_pct") is None or isinstance((model.get("system") or {}).get("system_pct"), float))

    for d, meta in (model.get("domain_weights") or {}).items():
        check(f"weight {d} labelled ESTIMATED", meta.get("label") == "ESTIMATED")

    # Factory health split — not a mission domain weight
    check(
        "Factory health NOT in domain_weights",
        "Factory health" not in (model.get("domain_weights") or {}),
        str(list((model.get("domain_weights") or {}).keys())),
    )
    check(
        "Factory health NOT in domains scorecard",
        "Factory health" not in (model.get("domains") or {}),
    )
    fh = model.get("factory_health") or {}
    check(
        "factory_health.status ∈ HEALTHY|DEGRADED|FAILING",
        fh.get("status") in ("HEALTHY", "DEGRADED", "FAILING"),
        str(fh.get("status")),
    )
    check("factory_health excluded_from_mission_pct", fh.get("excluded_from_mission_pct") is True)
    check("factory_health production UNTOUCHED", fh.get("production") == "UNTOUCHED")
    wsum = sum(float(meta.get("weight") or 0) for meta in (model.get("domain_weights") or {}).values())
    check("mission weights sum ~1.0", abs(wsum - 1.0) < 0.01, str(wsum))

    # Owner Cockpit fields
    check("owner_phase present", bool(model.get("owner_phase")))
    chips = model.get("status_chips") or []
    chip_ids = {c.get("id") for c in chips}
    check(
        "status_chips has BUILT/WAITING/POLICY",
        {"BUILT", "WAITING", "POLICY_NEEDED"}.issubset(chip_ids),
        str(chip_ids),
    )
    # v2.1 — hero chips are vocabulary (show_count False); no fake exclusive counts on Empire
    hero_chips = [c for c in chips if c.get("hero", True)]
    check(
        "hero chips omit exclusive counts (show_count False)",
        all(c.get("show_count") is False for c in hero_chips),
        str([(c.get("id"), c.get("show_count")) for c in hero_chips]),
    )
    check(
        "primary card omits decorative Status vocabulary chips",
        'aria-label="Status vocabulary"' not in HTML.read_text(encoding="utf-8"),
    )
    check(
        "primary card title WOLF TRANSFORMATION",
        "WOLF TRANSFORMATION" in HTML.read_text(encoding="utf-8"),
    )

    # v2.1 — waiting_class_for: SPECIFIED/IDEA/APPROVED → PLANNED (never auto POLICY)
    check(
        "SPECIFIED → PLANNED",
        prm.waiting_class_for({"lifecycle": "SPECIFIED", "built": False}) == "PLANNED",
    )
    check(
        "IDEA → PLANNED",
        prm.waiting_class_for({"lifecycle": "IDEA"}) == "PLANNED",
    )
    check(
        "APPROVED → PLANNED",
        prm.waiting_class_for({"lifecycle": "APPROVED"}) == "PLANNED",
    )
    check(
        "explicit UNAPPROVED_POLICY preserved",
        prm.waiting_class_for({"lifecycle": "SPECIFIED", "waiting_class": "UNAPPROVED_POLICY"})
        == "UNAPPROVED_POLICY",
    )
    empire_items = (
        ((model.get("views") or {}).get("Empire") or {}).get("technical_details") or {}
    ).get("items") or []
    # Overlay may still mark Knowledge rule as UNAPPROVED_POLICY explicitly — that's curated
    auto_mapped = [
        i
        for i in empire_items
        if (i.get("lifecycle") or "").upper() in ("SPECIFIED", "IDEA", "APPROVED")
        and i.get("waiting_class") == "UNAPPROVED_POLICY"
        and i.get("id") != "OV-KNOWLEDGE-RULE"
    ]
    check(
        "no SPECIFIED/IDEA/APPROVED auto→POLICY (except curated Knowledge row)",
        len(auto_mapped) == 0,
        str([(i.get("id"), i.get("capability")) for i in auto_mapped[:5]]),
    )
    sale_policy = [
        i
        for i in empire_items
        if i.get("domain") == "Sale Readiness" and i.get("waiting_class") == "UNAPPROVED_POLICY"
    ]
    check("Sale Readiness not inflated as POLICY", len(sale_policy) == 0, str(len(sale_policy)))

    # Curated missions / policy cards
    needs_you = model.get("needs_you") or []
    waiting_others = model.get("waiting_on_others") or []
    policies = model.get("policy_decisions") or []
    check("needs_you is list", isinstance(needs_you, list))
    check("waiting_on_others is list", isinstance(waiting_others, list))
    check("policy_decisions is list", isinstance(policies, list))
    check("needs_you has Progress ACTIVE", any(
        "Progress" in (m.get("title") or "") and m.get("status") == "ACTIVE" for m in needs_you
    ), str(needs_you))
    check("waiting_on_others has Habitat staff", any(
        "Habitat" in (m.get("title") or "") for m in waiting_others
    ), str(waiting_others))
    check("waiting_on_others has Uma closer", any(
        "Uma" in (m.get("title") or "") for m in waiting_others
    ), str(waiting_others))
    check("policy_decisions has Uma variance", any(
        "variance" in (p.get("title") or "").lower() for p in policies
    ), str(policies))
    check("policy_decisions count small (not 77)", 1 <= len(policies) <= 5, str(len(policies)))

    pulse = model.get("owner_pulse") or {}
    pulse_blob = " ".join(
        str(x)
        for key in ("working_now", "waiting_on_people", "policy_data_needed")
        for x in (pulse.get(key) or [])
    ).lower()
    check(
        "no fake Matt Core governance commission in pulse",
        "matt human commission of built core" not in pulse_blob
        and "commission core governance" not in pulse_blob,
        pulse_blob[:200],
    )
    moves = model.get("next_moves") or []
    moves_blob = " ".join(str(m.get("text") or "") for m in moves).lower()
    check(
        "no Core Matt commission fake in next_moves",
        "commission core governance" not in moves_blob,
        moves_blob,
    )
    check("owner_pulse working_now", isinstance(pulse.get("working_now"), list) and len(pulse["working_now"]) > 0)
    check(
        "owner_pulse build_system factory",
        (pulse.get("build_system") or {}).get("factory") in ("HEALTHY", "DEGRADED", "FAILING"),
    )
    moves = model.get("next_moves") or []
    check("next_moves ≤3", len(moves) <= 3, str(len(moves)))
    check("next_moves present", len(moves) >= 1)
    if moves:
        check(
            "next_moves class valid",
            moves[0].get("class") in ("ACTIVE", "WAITING", "RECOMMENDED", "APPROVED"),
            str(moves[0].get("class")),
        )
    wins = model.get("recent_wins") or []
    check("recent_wins present", len(wins) >= 1)
    road = model.get("milestone_road") or []
    check("milestone_road present", len(road) >= 4)
    unlocked = [m for m in road if m.get("unlocked")]
    check(
        "Foundations/workflow/vertical unlock evidence path",
        any(m.get("id") == "MS-FOUNDATIONS" and m.get("unlocked") for m in road),
        str([(m.get("id"), m.get("unlocked")) for m in road]),
    )
    check("Buyer Ready still locked", any(m.get("id") == "MS-BUYER" and not m.get("unlocked") for m in road))

    # Domain owner fields
    for dname, dcard in (model.get("domains") or {}).items():
        check(f"{dname} has plain_phase", bool(dcard.get("plain_phase")))
        check(f"{dname} has biggest_gap", bool(dcard.get("biggest_gap")))
        check(f"{dname} has visual_pct", isinstance(dcard.get("visual_pct"), int))
        gap = dcard.get("biggest_gap") or ""
        check(
            f"{dname} biggest_gap hides raw GPO-/EVR- ids",
            "GPO-" not in gap and "EVR-" not in gap and "PERS-" not in gap,
            gap,
        )

    empire = (model.get("views") or {}).get("Empire") or {}
    check("Empire has owner_phase", bool(empire.get("owner_phase")))
    check("Empire has next_moves", len(empire.get("next_moves") or []) <= 3)
    check("Empire technical_details present", isinstance(empire.get("technical_details"), dict))
    check("Empire has needs_you", isinstance(empire.get("needs_you"), list))
    check("Empire has waiting_on_others", isinstance(empire.get("waiting_on_others"), list))
    check("Empire has policy_decisions", isinstance(empire.get("policy_decisions"), list))
    check(
        "Empire habitat_owner stages",
        len((empire.get("habitat_owner") or {}).get("stages") or []) == 7,
    )
    check(
        "Empire uma_owner stages",
        len((empire.get("uma_owner") or {}).get("stages") or []) == 6,
    )
    check(
        "Empire uma variance blocked by business policy",
        (empire.get("uma_owner") or {}).get("variance_plain")
        == "BLOCKED BY BUSINESS POLICY. No threshold was invented.",
        str((empire.get("uma_owner") or {}).get("variance_plain")),
    )

    bf = (model.get("views") or {}).get("Build Factory") or {}
    check("Build Factory has factory_health", (bf.get("factory_health") or {}).get("status") in ("HEALTHY", "DEGRADED", "FAILING"))

    # Overall documents factory exclusion
    ov = model.get("overall") or {}
    check("overall has factory_excluded_note", "Factory" in (ov.get("factory_excluded_note") or ""))

    menu = model.get("menu") or []
    for name in ("Empire", "GGV", "AMG", "BZG"):
        check(f"primary menu has {name}", name in menu)
    menu_all = model.get("menu_all_views") or []
    for name in (
        "Empire",
        "Wolf Core",
        "GGV",
        "AMG",
        "BZG",
        "Intelligence",
        "Integrations",
        "Sale Readiness",
        "Build Factory",
        "Backlog",
    ):
        check(f"menu_all_views has {name}", name in menu_all)

    check("default view Empire", model.get("default_view") == "Empire")

    # Commissioning penalty (cap — VERIFIED 0.85 → 0.65; TESTED raw 0.55 stays ≤0.65)
    capped = prm.maturity_score("VERIFIED", human_commissioning="NOT_DONE")
    check("commissioning penalty caps VERIFIED at 0.65", capped == 0.65, str(capped))
    tested = prm.maturity_score("TESTED", human_commissioning="NOT_DONE")
    check("TESTED without commission ≤0.65", tested <= 0.65, str(tested))
    live_score = prm.maturity_score("LIVE", human_commissioning="DONE", live=True)
    check("LIVE+commissioned = 1.0", live_score == 1.0, str(live_score))
    check(
        "BUILT≠LIVE: LIVE without commission capped",
        prm.maturity_score("LIVE", human_commissioning="NOT_DONE") == 0.65,
    )

    # Distinctions on items
    sample = None
    empire_items = (
        ((model.get("views") or {}).get("Empire") or {}).get("technical_details") or {}
    ).get("items") or []
    for it in empire_items:
        if it.get("source_kind") == "overlay" and it.get("built"):
            sample = it
            break
    check("overlay item found", sample is not None)
    if sample:
        check("BUILT≠COMMISSIONED", sample.get("built") is True and sample.get("commissioned") is False)
        check("BUILT≠LIVE", sample.get("live") is False)

    # Sale readiness honesty (CSV rows carry TARGET≠ACTUAL note)
    sale = ((model.get("views") or {}).get("Sale Readiness") or {}).get("items") or []
    sale_csv = [i for i in sale if i.get("source_kind") == "sale_readiness_csv"]
    check("sale readiness CSV rows present", len(sale_csv) > 0, str(len(sale)))
    if sale_csv:
        check(
            "TARGET≠ACTUAL note on sale items",
            "NOT YET TRUSTWORTHY" in (sale_csv[0].get("target_profit_note") or ""),
        )

    # Calculation English
    calc = model.get("calculation") or {}
    check("calculation steps present", len(calc.get("steps") or []) >= 5)
    calc_blob = " ".join(calc.get("steps") or [])
    check("calculation excludes Factory from mission %", "EXCLUDED" in calc_blob or "Factory health is separate" in calc_blob)
    check("calculation states Core denominator", "item_count denominator" in calc_blob)
    canon_text = CANON.read_text(encoding="utf-8")
    check("canon has How is this calculated", "How is this calculated" in canon_text)
    check("canon has commissioning penalty", "0.65" in canon_text)
    check("canon has PARTIAL_ESTIMATE", "PARTIAL_ESTIMATE" in canon_text)
    check("canon Factory EXCLUDED", "Factory health EXCLUDED" in canon_text or "Factory health** is separate" in canon_text)

    html = HTML.read_text(encoding="utf-8")
    for needle in (
        "PARTIAL ESTIMATE",
        "How is this calculated?",
        "/api/progress",
        "BUILT",
        "COMMISSIONED",
        "WAITING_FOR_CLOSER",
        "WRITE_LOCKED",
        "Empire",
        "Owner pulse",
        "Milestone road",
        "WOLF TRANSFORMATION",
        "Technical capability built",
        "Needs you",
        "Waiting on others",
        "Policy decisions",
        "AMG · Atrium",
    ):
        check(f"HTML contains {needle}", needle in html)
    check("HTML AMG dedicated render branch", 'if (view === "AMG")' in html)
    check(
        "HTML GGV/AMG/BZG domain pct ESTIMATED",
        html.count("${esc(v.pct)}% · ESTIMATED") >= 3,
        str(html.count("${esc(v.pct)}% · ESTIMATED")),
    )
    check("HTML SYSTEM headline binds once", html.count("SYSTEM — ${esc(systemPct)}%") == 1)
    amg_view = (model.get("views") or {}).get("AMG") or {}
    check("AMG view has plain_phase", bool(amg_view.get("plain_phase")))
    check("AMG view has biggest_gap", bool(amg_view.get("biggest_gap")))
    check("AMG view has pct", isinstance(amg_view.get("pct"), (int, float)))
    for dname in ("GGV", "AMG", "BZG"):
        dv = (model.get("views") or {}).get(dname) or {}
        check(f"{dname} view pct is domain estimate field", dv.get("pct") is not None)

    # Overlay owner_cockpit provenance
    oc = overlay.get("owner_cockpit") or {}
    check("overlay owner_cockpit present", bool(oc))
    check("overlay next_moves ≤3", len(oc.get("next_moves") or []) <= 3)
    check(
        "overlay owner_cockpit provenance",
        bool(oc.get("source") and oc.get("as_of") and oc.get("confidence")),
    )

    content = CONTENT.read_text(encoding="utf-8")
    check("Owner nav Progress link", 'id="ownerProgressLink"' in content and 'href="/progress"' in content)
    check("Owner nav gated PERS-MATT", 'PERS-MATT' in content and "ownerProgressLink" in content)

    # Serve_beta wiring
    serve_src = SERVE.read_text(encoding="utf-8")
    check("serve imports progress_read_model", "progress_read_model" in serve_src)
    check("serve /api/progress", 'path == "/api/progress"' in serve_src)
    check("serve /progress rewrite", '"/progress"' in serve_src)

    # Dirty tree untouched (mtime/content presence — we assert paths still exist;
    # git will show if we edited them)
    for p in DIRTY_PRESERVE:
        check(f"dirty preserve exists {p.name}", p.is_file())

    # --- Migration on TEMP DB under beta-os path (identity/rbac refuse non-beta) ---
    mig = load_mig()
    tmp = ROOT / "catalog" / "backups" / f"tmp-progress-dash-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        tmp_db = tmp / "content_library.sqlite"
        shutil.copy2(LIVE_DB, tmp_db)
        orig_db = mig.DB
        mig.DB = tmp_db
        try:
            rc1 = mig.main()
            rc2 = mig.main()
        finally:
            mig.DB = orig_db
        check("migration exit 0", rc1 == 0, str(rc1))
        check("migration idempotent", rc2 == 0, str(rc2))
        conn = sqlite3.connect(str(tmp_db))
        try:
            perm = conn.execute(
                "SELECT status FROM org_permissions WHERE code='progress.read'"
            ).fetchone()
            check("progress.read ACTIVE", perm and perm[0] == "ACTIVE")
            matt = conn.execute(
                """
                SELECT rp.effect FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id=rp.permission_id
                WHERE p.code='progress.read' AND rp.role_id='ROLE-MATT'
                """
            ).fetchone()
            check("ROLE-MATT has progress.read", matt and matt[0] == "ALLOW")
            other = conn.execute(
                """
                SELECT COUNT(*) FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id=rp.permission_id
                WHERE p.code='progress.read' AND rp.role_id!='ROLE-MATT'
                """
            ).fetchone()[0]
            check("no staff progress.read grant", other == 0, str(other))
        finally:
            conn.close()

        # --- HTTP Owner vs staff ---
        import serve_beta as sb
        import wolf_intelligence as wi
        from core import request_auth as ra
        from core import identity as identity_mod
        from core import rbac as rbac_mod
        from core import organisation as org_mod
        from core import staffing as staffing_mod
        from core import scope as scope_mod
        from core import audit as audit_mod

        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        ra._ENV_LOADED = True
        for mod in (
            sb,
            wi,
            identity_mod,
            rbac_mod,
            org_mod,
            staffing_mod,
            scope_mod,
            audit_mod,
        ):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = tmp_db
        sb.CATALOG_DB = tmp_db

        Handler = None
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
        check("API handler found", Handler is not None)
        if Handler:
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:

                def call(path, subject):
                    req = Request(
                        f"http://127.0.0.1:{port}{path}",
                        headers={"X-Wolf-Subject": subject, "Accept": "application/json"},
                        method="GET",
                    )
                    try:
                        with urlopen(req, timeout=10) as r:
                            return r.status, json.loads(r.read().decode())
                    except HTTPError as e:
                        body = e.read().decode()
                        try:
                            data = json.loads(body)
                        except json.JSONDecodeError:
                            data = {"raw": body}
                        return e.code, data

                st, data = call("/api/progress", MATT)
                check("Matt /api/progress 200", st == 200 and data.get("ok") is True, str(data)[:200])
                check(
                    "Matt payload SYSTEM_FROM_LEDGER",
                    data.get("progress_type") == "SYSTEM_FROM_LEDGER",
                )
                check(
                    "Matt payload has system dial",
                    (data.get("system") or {}).get("label") == "SYSTEM",
                )
                check("Matt sees Empire menu", "Empire" in (data.get("menu") or []))

                st2, data2 = call("/api/progress", STAFF)
                check("staff /api/progress 403", st2 == 403, str(data2)[:200])
                check(
                    "staff forbidden message",
                    data2.get("error") in ("forbidden", "unauthorized"),
                    str(data2)[:160],
                )

                st3, data3 = call("/api/progress/view?name=GGV", MATT)
                check("Matt GGV view 200", st3 == 200 and data3.get("ok") is True, str(data3)[:160])
                hab2 = ((data3.get("view") or {}).get("habitat") or {})
                check(
                    "GGV view has Habitat vertical",
                    bool(hab2.get("stages")),
                )

                st4, _ = call("/api/progress/honesty", STAFF)
                check("staff honesty 403", st4 == 403)

                # Static /progress rewrite — may 200 HTML
                req_p = Request(
                    f"http://127.0.0.1:{port}/progress",
                    headers={"X-Wolf-Subject": MATT},
                    method="GET",
                )
                try:
                    with urlopen(req_p, timeout=10) as r:
                        body = r.read().decode("utf-8", errors="replace")
                        check("/progress serves HTML", r.status == 200 and "Wolf" in body and "Progress" in body)
                except HTTPError as e:
                    check("/progress serves HTML", False, str(e))
            finally:
                httpd.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Live isolation — planner / auth / closes unchanged by tests (migration not run on live yet)
    after = live_counts()
    check("live content_planner unchanged by tests", before["planner"] == after["planner"], f"{before} vs {after}")
    check("live auth_limits unchanged", before["auth_limits"] == after["auth_limits"])

    # Apply migration to live Beta DB (idempotent Owner grant only)
    live_rc = load_mig().main()
    check("live migration applied", live_rc == 0, str(live_rc))
    conn = sqlite3.connect(str(LIVE_DB))
    try:
        live_perm = conn.execute(
            "SELECT COUNT(*) FROM org_permissions WHERE code='progress.read' AND status='ACTIVE'"
        ).fetchone()[0]
        check("live progress.read present", live_perm == 1)
    finally:
        conn.close()

    after2 = live_counts()
    check("live planner untouched by migration", before["planner"] == after2["planner"])

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
