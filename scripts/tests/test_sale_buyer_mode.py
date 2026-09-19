#!/usr/bin/env python3
"""CAP-SALE-03 buyer mode. Named surfaces. Hidden jewels. Empty exports. No grant."""
from __future__ import annotations

import ast
import csv
import hashlib
import inspect
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALCHEMIST_DB", None)
os.environ.pop("WOLF_ESB_SQLITE", None)

from core import sale_buyer_mode as mode  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "sale_buyer_mode.py"
CR_ID = "CR-b428ac5cbc8986b5"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
HIDE_IDS = {
    "HIDE-CROWN-PLAYBOOK",
    "HIDE-CROWN-REGISTRY",
    "HIDE-CROWN-WOLF-IP",
    "HIDE-CROSS-COMPANY",
}
TOKEN = "SECRET-PACK-TOKEN-991"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _by_id(rows: list[dict]) -> dict:
    return {row["id"]: row for row in rows}


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return conn.execute(
            "SELECT state, blocker_class, capability, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()


def _resolved_count() -> int:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'"
        ).fetchone()[0]
    finally:
        conn.close()


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "Entity",
        "Area",
        "Evidence / Metric",
        "Current State",
        "Target State",
        "Gap",
        "Owner",
        "Next action",
        "Status",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _blank_row(entity: str, area: str, **extra: str) -> dict[str, str]:
    row = {
        "Entity": entity,
        "Area": area,
        "Evidence / Metric": "",
        "Current State": "",
        "Target State": "",
        "Gap": "",
        "Owner": "",
        "Next action": "",
        "Status": "SPECIFIED",
    }
    row.update(extra)
    return row


def test_live_mode() -> None:
    report = mode.build_mode()
    surfaces = _by_id(report["diligence_surfaces"])
    check("eighteen diligence surfaces", report["diligence_surface_count"] == 18, str(report["diligence_surface_count"]))
    check("three ask surfaces", report["ask_surface_count"] == 3, str(report["ask_surface_count"]))
    check("twenty-one approved", report["approved_count"] == 21)
    check("entities are the three companies", report["entities"] == ["GGV", "AMG", "BZG"])
    check("each diligence surface is one company", all(row["company_specific"] is True and row["entity"] in {"GGV", "AMG", "BZG"} for row in report["diligence_surfaces"]))
    check("no blended surface", report["blended"] is False and report["cross_company_exposed"] is False)
    check("finance surface named", surfaces["SURF-GGV-FINANCE"]["name"] == "Finance" and surfaces["SURF-GGV-FINANCE"]["approved"] is True)
    check("finance items named only", surfaces["SURF-GGV-FINANCE"]["item_count"] == 4 and surfaces["SURF-GGV-FINANCE"]["data"] is None)
    check("finance export empty", surfaces["SURF-GGV-FINANCE"]["export_slot"] == "EMPTY" and surfaces["SURF-GGV-FINANCE"]["granted"] is False)
    check("item names have no data", all(item["data"] is None and item["named"] is True for row in report["diligence_surfaces"] for item in row["items"]))
    check("named item count", report["item_count"] == 57, str(report["item_count"]))
    asks = _by_id(report["ask_surfaces"])
    ask = asks["SURF-GGV-ASK"]
    check("ask named empty", ask["ask_context"] is None and ask["answers"] == [] and ask["export_slot"] == "EMPTY" and ask["company_specific"] is True)
    check("ask not answered", report["ask_answered"] is False)
    hides = _by_id(report["hides"])
    check("four hides", set(hides) == HIDE_IDS and report["hide_count"] == 4)
    check("hides default hidden", report["hides_default_hidden"] is True and report["crown_jewels_opened"] is False)
    check(
        "hide payloads closed",
        all(row["payload"] is None and row["data"] is None and row["opened"] is False and row["default_hidden"] is True and row["export_id"] is None for row in report["hides"]),
    )
    check("cross-company hide", hides["HIDE-CROSS-COMPANY"]["class"] == "cross_company" and hides["HIDE-CROSS-COMPANY"]["approved"] is False)
    check("crown playbook hide", hides["HIDE-CROWN-PLAYBOOK"]["class"] == "crown_jewel" and hides["HIDE-CROWN-PLAYBOOK"]["visibility"] == "HIDDEN")
    exports = report["exports"]
    check("export slots match surfaces", report["export_count"] == 21 and report["empty_exports"] == 21 and report["filled_exports"] == 0)
    check(
        "exports empty",
        all(row["slot"] == "EMPTY" and row["filled"] is False and row["filename"] is None and row["bytes"] is None and row["path"] is None and row["written"] is False for row in exports),
    )
    check("no export file ids on hides", all(row["surface"].startswith("SURF-") for row in exports))
    check("no buyers", report["buyers"] == [] and report["buyer_count"] == 0 and report["buyer_grant"] is False and report["share_url"] is None)
    check("no controlled export", report["buyer_export"] is False and report["controlled_export"] is False and report["export_written"] is False and report["on_disk"] is False)
    check("canon 60 names", report["controls_read"] == 60 and report["control_list_matches_canon"] is True)
    check("growth not approved", report["unmapped"]["control_count"] == 3 and report["unmapped"]["approved"] is False and report["unmapped"]["export_count"] == 0)
    growth_ids = {row["id"] for row in report["unmapped"]["names"]}
    check("growth id unmapped", "CTRL-AMG-GROWTH-OPPORTUNITIES" in growth_ids)
    check("not approved empty on canon", report["not_approved"]["control_count"] == 0)
    check("gaps documented", len(report["gaps"]) >= 8 and any("empty" in line for line in report["gaps"]))
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-SALE-03")
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT" and flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False and flags.get("invented_proven") is False)
    check("honesty.not_ready", flags.get("invented_ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False and flags.get("cr_mutated") is False)
    check("honesty.hides closed", flags.get("crown_jewels_opened") is False and flags.get("cross_company_exposed") is False and flags.get("buyer_grant") is False)
    dumped = json.dumps(report)
    check("live mode has no PROVEN token", "PROVEN" not in dumped)
    check("live mode has no READY token", "READY" not in dumped)
    check("live mode has no download claim", "download" not in dumped and "http://" not in dumped and "https://" not in dumped)
    one = mode.read_surface("SURF-GGV-FINANCE")
    check("read finance named", one["ok"] is True and one["surface"]["export_slot"] == "EMPTY" and one["surface"]["data"] is None)
    check("read finance slot empty", (one.get("export_slot") or {}).get("slot") == "EMPTY" and (one.get("export_slot") or {}).get("filename") is None)
    check("read finance bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)
    short = mode.read_surface("GGV-FINANCE")
    check("read short id", short["surface"]["id"] == "SURF-GGV-FINANCE")
    hidden = mode.read_surface("HIDE-CROWN-PLAYBOOK")
    check("read hide stays closed", hidden["opened"] is False and hidden["payload"] is None and hidden["hide"]["payload"] is None)
    check("read hide has no path", "/Users/" not in json.dumps(hidden))
    cross = mode.read_surface("HIDE-CROSS-COMPANY")
    check("read cross stays closed", cross["payload"] is None and cross["cross_company_exposed"] is False)


def test_filters_and_honesty(td: Path) -> None:
    ggv = mode.build_mode(entity="ggv")
    check("entity filter surfaces", ggv["diligence_surface_count"] == 6 and ggv["ask_surface_count"] == 1 and ggv["entities"] == ["GGV"])
    check("entity filter items", ggv["item_count"] == 19, str(ggv["item_count"]))
    check("entity filter exports", ggv["export_count"] == 7 and ggv["empty_exports"] == 7 and ggv["filled_exports"] == 0)
    check("entity filter hides stay", ggv["hide_count"] == 4 and ggv["hides_default_hidden"] is True)
    check("entity filter unmapped", ggv["unmapped"]["control_count"] == 1)
    check("entity filter still canon source", ggv["controls_read"] == 60 and ggv["control_list_matches_canon"] is True)
    try:
        mode.build_mode(entity="HABITAT")
        check("unknown entity refused", False)
    except mode.BuyerModeError as exc:
        check("unknown entity refused", exc.code == "invalid_entity", exc.code)
    try:
        mode.read_surface("NO-SUCH")
        check("missing surface refused", False)
    except mode.BuyerModeError as exc:
        check("missing surface refused", exc.code == "not_found", exc.code)
    try:
        mode.read_surface("SURFACES")
        check("view id refused", False)
    except mode.BuyerModeError as exc:
        check("view id refused", exc.code == "not_found", exc.code)
    try:
        mode.read_surface("EXPORT")
        check("export id refused", False)
    except mode.BuyerModeError as exc:
        check("export id refused", exc.code == "buyer_export_refused", exc.code)
    try:
        mode.read_surface("GRANT")
        check("grant id refused", False)
    except mode.BuyerModeError as exc:
        check("grant id refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        mode.read_surface("SHARE")
        check("share id refused", False)
    except mode.BuyerModeError as exc:
        check("share id refused", exc.code == "buyer_share_refused", exc.code)
    try:
        mode.read_surface("REVEAL")
        check("reveal id refused", False)
    except mode.BuyerModeError as exc:
        check("reveal id refused", exc.code == "hide_refused", exc.code)
    try:
        mode.read_surface("BLEND")
        check("blend id refused", False)
    except mode.BuyerModeError as exc:
        check("blend id refused", exc.code == "cross_company_refused", exc.code)
    try:
        mode.build_mode(csv_path=td / "missing.csv")
        check("missing source not empty mode", False)
    except mode.BuyerModeError as exc:
        check("missing source not empty mode", exc.code == "not_read", exc.code)
    bad = td / "bad.csv"
    bad.write_text("Entity,Area\nGGV,Finance quality\n", encoding="utf-8")
    try:
        mode.build_mode(csv_path=bad)
        check("bad columns refused", False)
    except mode.BuyerModeError as exc:
        check("bad columns refused", exc.code == "bad_source", exc.code)
    try:
        mode.build_mode(csv_path=Path("/tmp/wolf-system/sale.csv"))
        check("wolf-system path refused", False)
    except mode.BuyerModeError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        mode.build_mode(ledger_path=Path("/tmp/Production/ledger.json"))
        check("production path refused", False)
    except mode.BuyerModeError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        mode.build_mode(csv_path=td / "alchemist-sale.csv")
        check("alchemist path refused", False)
    except mode.BuyerModeError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        mode.refuse_external_write({"proven": True})
        check("write refused", False)
    except mode.BuyerModeError as exc:
        check("write refused", exc.code == "writes_refused", exc.code)
    try:
        mode.refuse_grant({})
        check("grant refused", False)
    except mode.BuyerModeError as exc:
        check("grant refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        mode.refuse_share({})
        check("share refused", False)
    except mode.BuyerModeError as exc:
        check("share refused", exc.code == "buyer_share_refused", exc.code)
    try:
        mode.refuse_export({})
        check("export refused", False)
    except mode.BuyerModeError as exc:
        check("export refused", exc.code == "buyer_export_refused", exc.code)
    try:
        mode.refuse_reveal({})
        check("reveal refused", False)
    except mode.BuyerModeError as exc:
        check("reveal refused", exc.code == "hide_refused", exc.code)
    try:
        mode.refuse_external_write({"grant": "buyer@example.com"})
        check("payload grant refused", False)
    except mode.BuyerModeError as exc:
        check("payload grant refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        mode.refuse_external_write({"share": True})
        check("payload share refused", False)
    except mode.BuyerModeError as exc:
        check("payload share refused", exc.code == "buyer_share_refused", exc.code)
    try:
        mode.refuse_external_write({"export": "buyer"})
        check("payload export refused", False)
    except mode.BuyerModeError as exc:
        check("payload export refused", exc.code == "buyer_export_refused", exc.code)
    try:
        mode.refuse_external_write({"reveal": True})
        check("payload reveal refused", False)
    except mode.BuyerModeError as exc:
        check("payload reveal refused", exc.code == "hide_refused", exc.code)
    try:
        mode.refuse_external_write({"blend": True})
        check("payload blend refused", False)
    except mode.BuyerModeError as exc:
        check("payload blend refused", exc.code == "cross_company_refused", exc.code)
    try:
        mode.refuse_fill({"filename": "invented.pdf"})
        check("fill refused", False)
    except mode.BuyerModeError as exc:
        check("fill refused", exc.code == "fill_refused", exc.code)
    try:
        mode.refuse_production({})
        check("production refused", False)
    except mode.BuyerModeError as exc:
        check("production refused", exc.code == "production_refused", exc.code)
    try:
        mode.guard_query(grant="1")
        check("query grant refused", False)
    except mode.BuyerModeError as exc:
        check("query grant refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        mode.guard_query(export="1")
        check("query export refused", False)
    except mode.BuyerModeError as exc:
        check("query export refused", exc.code == "buyer_export_refused", exc.code)
    try:
        mode.guard_query(share="1")
        check("query share refused", False)
    except mode.BuyerModeError as exc:
        check("query share refused", exc.code == "buyer_share_refused", exc.code)
    try:
        mode.guard_query(reveal="1")
        check("query reveal refused", False)
    except mode.BuyerModeError as exc:
        check("query reveal refused", exc.code == "hide_refused", exc.code)
    try:
        mode.guard_query(blend="1")
        check("query blend refused", False)
    except mode.BuyerModeError as exc:
        check("query blend refused", exc.code == "cross_company_refused", exc.code)


def test_empty_stays_empty(td: Path) -> None:
    rows = [
        _blank_row(
            "GGV",
            "Finance quality",
            **{
                "Evidence / Metric": "bank-pack.pdf",
                "Current State": TOKEN,
                "Target State": "Sale-ready evidence continuously maintained",
                "Gap": TOKEN,
                "Owner": TOKEN,
                "Next action": TOKEN,
                "Status": "PROVEN",
            },
        ),
        _blank_row("AMG", "Growth opportunities", **{"Evidence / Metric": TOKEN}),
        _blank_row("HABITAT", "Finance quality", **{"Evidence / Metric": TOKEN}),
    ]
    path = td / "partial.csv"
    _write_csv(path, rows)
    report = mode.build_mode(csv_path=path)
    finance = _by_id(report["diligence_surfaces"])["SURF-GGV-FINANCE"]
    check("source file is not data", finance["data"] is None and finance["items"][0]["data"] is None and finance["export_slot"] == "EMPTY")
    check("status word is not a prove", finance["granted"] is False and report["filled_exports"] == 0)
    dumped = json.dumps(report)
    check("source filename not copied", "bank-pack.pdf" not in dumped)
    check("source token not copied", TOKEN not in dumped)
    check("partial not canon", report["control_list_matches_canon"] is False and report["controls_read"] == 3)
    check("partial exports empty", report["empty_exports"] == report["export_count"] and report["filled_exports"] == 0)
    check("habitat not approved", report["not_approved"]["control_count"] == 1 and report["not_approved"]["export_count"] == 0)
    check("habitat has no surface", all(row["entity"] != "HABITAT" for row in report["surfaces"]))
    check("growth stays unmapped", report["unmapped"]["control_count"] == 1 and report["unmapped"]["names"][0]["area"] == "Growth opportunities")
    check("mode still not proved", report["honesty"]["proven"] is False and report["honesty"]["invented_proven"] is False)
    check("no PROVEN token in partial", "PROVEN" not in dumped)
    dup = td / "dup.csv"
    _write_csv(dup, [_blank_row("GGV", "Finance quality"), _blank_row("GGV", "Finance quality")])
    try:
        mode.build_mode(csv_path=dup)
        check("duplicate refused", False)
    except mode.BuyerModeError as exc:
        check("duplicate refused", exc.code == "duplicate_surface", exc.code)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-SALE-03"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = mode.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    ready = json.loads(before.decode())
    ready["CAP-SALE-03"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = mode.honesty_flags(ready_path)
    check("already ready ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY")
    check("already ready is not a write", ready_flags["model_c_write"] is False and ready_flags["invented_ready"] is False)
    junk = json.loads(before.decode())
    junk["CAP-SALE-03"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = mode.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = mode.honesty_flags(catalog_db=missing_db)
    check("missing cr not invented", absent["cr_present"] is False and absent["cr_resolved"] is False and absent["cr_id"] == CR_ID)
    check("live ledger untouched after junk", LEDGER.read_bytes() == before)


def test_source_and_files() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    joined = " ".join(imported)
    check("module does not import wolf_intelligence", "wolf_intelligence" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mkdir", "mkdir" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module reads catalog read-only", "mode=ro" in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", 'path == "/api/buyer-mode"' in serve)
    check("page route registered", '"/buyer-mode"' in serve)
    check("grant route refused in server", '"/api/buyer-mode/grant"' in serve)
    check("reveal route refused in server", '"/api/buyer-mode/reveal"' in serve)
    check("prior export refuse kept", '"/api/buyer-mode/export"' in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)


def test_api(td: Path) -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ.pop("WOLF_ALCHEMIST_DB", None)
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("API handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        def call(method: str, url_path: str, subject: str | None):
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            data = b"{}" if method != "GET" else None
            req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=data)
            try:
                with urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
                    if "json" in ctype or url_path.startswith("/api/"):
                        try:
                            return resp.status, json.loads(raw.decode())
                        except json.JSONDecodeError:
                            return resp.status, raw
                    return resp.status, raw
            except HTTPError as exc:
                raw = exc.read()
                try:
                    parsed = json.loads(raw.decode())
                except json.JSONDecodeError:
                    parsed = raw
                return exc.code, parsed

        st, _anon = call("GET", "/api/buyer-mode", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/buyer-mode", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/buyer-mode", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner diligence 18", owner.get("diligence_surface_count") == 18, str(owner.get("diligence_surface_count")))
            check("owner ask 3", owner.get("ask_surface_count") == 3)
            check("owner exports empty", owner.get("empty_exports") == 21 and owner.get("filled_exports") == 0)
            check("owner hides closed", owner.get("hide_count") == 4 and owner.get("hides_default_hidden") is True and owner.get("crown_jewels_opened") is False)
            check("owner no proven token", "PROVEN" not in json.dumps(owner))
            check("owner no ready token", "READY" not in json.dumps(owner))
            check("owner no grant", owner.get("buyer_grant") is False and owner.get("buyer_export") is False and owner.get("buyer_count") == 0)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner ceiling label", (owner.get("honesty") or {}).get("maturity_ceiling") == "BUILT")
            check("owner ledger still specified", (owner.get("honesty") or {}).get("maturity") == "SPECIFIED")
        st, missing = call("GET", "/api/buyer-mode/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/buyer-mode/SURF-GGV-FINANCE", MATT)
        check("owner surface 200", st == 200 and isinstance(one, dict) and (one.get("surface") or {}).get("export_slot") == "EMPTY", str(st))
        st, surfaces = call("GET", "/api/buyer-mode/surfaces", MATT)
        check("owner surfaces 200", st == 200 and isinstance(surfaces, dict) and surfaces.get("diligence_surface_count") == 18, str(st))
        st, hides = call("GET", "/api/buyer-mode/hides", MATT)
        check("owner hides 200", st == 200 and isinstance(hides, dict) and hides.get("hides_default_hidden") is True and hides.get("crown_jewels_opened") is False, str(st))
        if isinstance(hides, dict):
            check("owner hide payloads null", all((row.get("payload") is None) for row in hides.get("hides") or []))
        st, exports = call("GET", "/api/buyer-mode/exports", MATT)
        check("owner exports 200", st == 200 and isinstance(exports, dict) and exports.get("filled_exports") == 0 and exports.get("empty_exports") == 21, str(st))
        st, page_anon = call("GET", "/buyer-mode", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/buyer-mode", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, bytes)
            and b"CAP-SALE-03" in page
            and b"Crown jewels stay hidden" in page
            and b"Cross-company intelligence stays hidden" in page
            and b"Export slots stay empty" in page
            and b"No buyer grant" in page
            and b"EMPTY" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/buyer-mode", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/buyer-mode", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/buyer-mode", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
        st, patch = call("PATCH", "/api/buyer-mode", MATT)
        check("owner PATCH refused", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:160])
        st, grant = call("POST", "/api/buyer-mode/grant", MATT)
        check("owner grant refused", st == 405 and isinstance(grant, dict) and grant.get("error") == "buyer_grant_refused", str(grant)[:200])
        st, share = call("POST", "/api/buyer-mode/share", MATT)
        check("owner share refused", st == 405 and isinstance(share, dict) and share.get("error") == "buyer_share_refused", str(share)[:200])
        st, reveal = call("GET", "/api/buyer-mode/reveal", MATT)
        check("owner reveal refused", st == 405 and isinstance(reveal, dict) and reveal.get("error") == "hide_refused", str(reveal)[:200])
        st, exported = call("GET", "/api/buyer-mode/export", MATT)
        check("owner export refused", st == 405 and isinstance(exported, dict) and exported.get("error") == "buyer_export_refused", str(exported)[:200])
        st, qgrant = call("GET", "/api/buyer-mode?grant=1", MATT)
        check("query grant refused", st == 405 and isinstance(qgrant, dict) and qgrant.get("error") == "buyer_grant_refused", str(qgrant)[:180])
        st, qblend = call("GET", "/api/buyer-mode?blend=1", MATT)
        check("query blend refused", st == 405 and isinstance(qblend, dict) and qblend.get("error") == "cross_company_refused", str(qblend)[:180])
        st, habitat = call("GET", "/api/buyer-mode?entity=HABITAT", MATT)
        check("query entity refused", st == 400 and isinstance(habitat, dict) and habitat.get("error") == "invalid_entity", str(habitat)[:180])
        st, narrowed = call("GET", "/api/buyer-mode?entity=GGV", MATT)
        check("query entity narrows", st == 200 and isinstance(narrowed, dict) and narrowed.get("entities") == ["GGV"] and narrowed.get("hide_count") == 4, str(st))
        st, vdr = call("POST", "/api/vdr/export", MATT)
        check("sale vdr export still refused", st == 405 and isinstance(vdr, dict) and vdr.get("error") == "vdr_export_refused", str(vdr)[:200])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="buyer-mode-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    try:
        test_live_mode()
        test_filters_and_honesty(td)
        test_empty_stays_empty(td)
        test_ledger_ceiling(td)
        test_source_and_files()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_ESB_SQLITE", None)
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
    check("ledger file still unchanged at exit", LEDGER.read_bytes() == ledger_before)
    check("score history unchanged", HISTORY.read_bytes() == history_before)
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger still 77", len(doc) == 77, str(len(doc)))
    check("CAP-SALE-01 stays SPECIFIED", doc["CAP-SALE-01"][0] == "SPECIFIED")
    check("CAP-SALE-02 stays SPECIFIED", doc["CAP-SALE-02"][0] == "SPECIFIED")
    check("CAP-SALE-03 stays SPECIFIED", doc["CAP-SALE-03"][0] == "SPECIFIED")
    check("CAP-SALE-04 stays SPECIFIED", doc["CAP-SALE-04"][0] == "SPECIFIED")
    check("CR row unchanged", _cr_row() == cr_before, str(_cr_row()))
    check("resolved CR count unchanged", _resolved_count() == resolved_before, str(_resolved_count()))
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
