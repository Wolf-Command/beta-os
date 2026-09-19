#!/usr/bin/env python3
"""CAP-SALE-01 sale evidence pack. Read-only. Empty slots stay empty. No VDR."""
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

from core import sale_evidence_pack as pack  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "sale_evidence_pack.py"
CR_ID = "CR-b7ce6d6668848b6e"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
DOMAIN_IDS = {"FINANCE", "HR", "LEGAL", "OPS", "COMPLIANCE", "TECH"}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _by_id(report: dict) -> dict:
    return {row["id"]: row for row in report["controls"]}


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return conn.execute(
            "SELECT state, blocker_class, capability, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
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


def test_live_pack() -> None:
    report = pack.build_pack()
    controls = report["controls"]
    domains = {row["id"]: row for row in report["domains"]}
    check("six required domains", set(domains) == DOMAIN_IDS, str(sorted(domains)))
    check("domains required", all(row["required"] is True for row in report["domains"]))
    check("domain evidence stays empty", all(row["evidence"] is None and row["proven"] is False for row in report["domains"]))
    check("canon 60", report["controls_read"] == 60 and report["control_list_matches_canon"] is True, str(report["controls_read"]))
    check("shown 60", report["control_count"] == 60)
    check("all live slots empty", report["empty_slots"] == 60 and report["filled_slots"] == 0, str(report["filled_slots"]))
    check("no filled control", all(row["filled"] is False and row["evidence"] is None and row["slot"] == "EMPTY" for row in controls))
    check("no control proved", all(row["proven"] is False for row in controls))
    check("controls are not capabilities", all(row["is_control"] is True and row["is_capability"] is False and row["cap"] == "CAP-SALE-01" for row in controls))
    ids = [row["id"] for row in controls]
    check("ids unique", len(ids) == len(set(ids)))
    by = _by_id(report)
    finance = by["CTRL-GGV-FINANCE-QUALITY"]
    check("finance domain", finance["domain"] == "FINANCE" and finance["entity"] == "GGV")
    check("target is not evidence", finance["target_state"] and finance["evidence"] is None)
    growth = by["CTRL-AMG-GROWTH-OPPORTUNITIES"]
    check("growth stays unmapped", growth["domain"] == "UNKNOWN" and growth["slot"] == "EMPTY")
    check("unmapped count", report["unmapped"]["control_count"] == 3 and report["unmapped"]["required"] is False)
    check("entities only three", {row["entity"] for row in controls} == {"GGV", "AMG", "BZG"})
    check("no unexpected entity", all(row["unexpected_entity"] is False for row in controls))
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-SALE-01")
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.skeleton", flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False and flags.get("invented_proven") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False)
    check("honesty.no_export", flags.get("vdr_export") is False and flags.get("buyer_export") is False)
    check("pack export flags", report["vdr_export"] is False and report["buyer_export"] is False and report["ledger_write"] is False)
    dumped = json.dumps(report)
    check("live pack has no PROVEN token", "PROVEN" not in dumped)
    check("live pack has no VDR file claim", "vdr_url" not in dumped and "download" not in dumped)
    one = pack.read_control("CTRL-BZG-COMPLIANCE")
    check("read one empty", one["ok"] is True and one["control"]["slot"] == "EMPTY" and one["control"]["domain"] == "COMPLIANCE")
    check("read one bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)


def test_filters_and_honesty(td: Path) -> None:
    ggv = pack.build_pack(entity="ggv")
    check("entity filter", ggv["control_count"] == 20 and {row["entity"] for row in ggv["controls"]} == {"GGV"})
    check("entity filter keeps domains", {row["id"] for row in ggv["domains"]} == DOMAIN_IDS)
    tech = pack.build_pack(domain="tech")
    check("domain filter", {row["domain"] for row in tech["controls"]} == {"TECH"} and tech["control_count"] == 9, str(tech["control_count"]))
    check("domain filter still lists six", len(tech["domains"]) == 6)
    unknown = pack.build_pack(domain="UNKNOWN")
    check("unknown filter", unknown["control_count"] == 3 and all(row["area"] == "Growth opportunities" for row in unknown["controls"]))
    try:
        pack.build_pack(entity="HABITAT")
        check("unknown entity refused", False)
    except pack.SalePackError as exc:
        check("unknown entity refused", exc.code == "invalid_entity", exc.code)
    try:
        pack.build_pack(domain="SALE")
        check("unknown domain refused", False)
    except pack.SalePackError as exc:
        check("unknown domain refused", exc.code == "invalid_domain", exc.code)
    try:
        pack.read_control("CTRL-NO-SUCH")
        check("missing control refused", False)
    except pack.SalePackError as exc:
        check("missing control refused", exc.code == "not_found", exc.code)
    try:
        pack.read_control("export")
        check("export id refused", False)
    except pack.SalePackError as exc:
        check("export id refused", exc.code == "not_found", exc.code)
    try:
        pack.build_pack(csv_path=td / "missing.csv")
        check("missing source not empty pack", False)
    except pack.SalePackError as exc:
        check("missing source not empty pack", exc.code == "not_read", exc.code)
    bad = td / "bad.csv"
    bad.write_text("Entity,Area\nGGV,Finance quality\n", encoding="utf-8")
    try:
        pack.build_pack(csv_path=bad)
        check("bad columns refused", False)
    except pack.SalePackError as exc:
        check("bad columns refused", exc.code == "bad_source", exc.code)
    try:
        pack.build_pack(csv_path=Path("/tmp/wolf-system/sale.csv"))
        check("wolf-system path refused", False)
    except pack.SalePackError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        pack.build_pack(ledger_path=Path("/tmp/Production/ledger.json"))
        check("production path refused", False)
    except pack.SalePackError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        pack.build_pack(csv_path=td / "alchemist-sale.csv")
        check("alchemist path refused", False)
    except pack.SalePackError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        pack.refuse_external_write({"proven": True})
        check("write refused", False)
    except pack.SalePackError as exc:
        check("write refused", exc.code == "writes_refused", exc.code)
    try:
        pack.refuse_vdr_export({"buyer": "all"})
        check("vdr refused", False)
    except pack.SalePackError as exc:
        check("vdr refused", exc.code == "vdr_export_refused", exc.code)
    try:
        pack.refuse_buyer_export({})
        check("buyer refused", False)
    except pack.SalePackError as exc:
        check("buyer refused", exc.code == "buyer_export_refused", exc.code)
    try:
        pack.refuse_external_write({"export": "vdr"})
        check("export vdr refused", False)
    except pack.SalePackError as exc:
        check("export vdr refused", exc.code == "vdr_export_refused", exc.code)
    try:
        pack.refuse_external_write({"buyer_mode": True})
        check("buyer mode refused", False)
    except pack.SalePackError as exc:
        check("buyer mode refused", exc.code == "buyer_export_refused", exc.code)
    try:
        pack.refuse_fill({"evidence": "invented bank pack"})
        check("fill refused", False)
    except pack.SalePackError as exc:
        check("fill refused", exc.code == "fill_refused", exc.code)
    try:
        pack.guard_query(export="buyer")
        check("query buyer refused", False)
    except pack.SalePackError as exc:
        check("query buyer refused", exc.code == "buyer_export_refused", exc.code)
    try:
        pack.guard_query(fill="1")
        check("query fill refused", False)
    except pack.SalePackError as exc:
        check("query fill refused", exc.code == "fill_refused", exc.code)


def test_empty_stays_empty(td: Path) -> None:
    rows = [
        _blank_row("GGV", "Finance quality", **{"Current State": "looks complete", "Target State": "Sale-ready evidence continuously maintained", "Status": "PROVEN"}),
        _blank_row("GGV", "Data quality", **{"Evidence / Metric": "source file note"}),
        _blank_row("AMG", "Growth opportunities"),
    ]
    path = td / "partial.csv"
    _write_csv(path, rows)
    report = pack.build_pack(csv_path=path)
    by = _by_id(report)
    finance = by["CTRL-GGV-FINANCE-QUALITY"]
    check("current state is not evidence", finance["current_state"] == "looks complete" and finance["evidence"] is None)
    check("status word is not a prove", finance["source_status"] == "PROVEN" and finance["proven"] is False and finance["slot"] == "EMPTY")
    check("target not copied into evidence", "Sale-ready" in (finance["target_state"] or "") and finance["filled"] is False)
    data = by["CTRL-GGV-DATA-QUALITY"]
    check("source text reported", data["evidence"] == "source file note" and data["filled"] is True and data["slot"] == "SOURCE_TEXT")
    check("source text not proved", data["proven"] is False)
    check("partial not canon", report["control_list_matches_canon"] is False and report["controls_read"] == 3)
    check("partial empty count", report["empty_slots"] == 2 and report["filled_slots"] == 1)
    check("pack still not proved", report["honesty"]["proven"] is False and report["honesty"]["invented_proven"] is False)
    check("domain evidence still none", all(row["evidence"] is None for row in report["domains"]))
    dup = td / "dup.csv"
    _write_csv(dup, [_blank_row("GGV", "Finance quality"), _blank_row("GGV", "Finance quality")])
    try:
        pack.build_pack(csv_path=dup)
        check("duplicate refused", False)
    except pack.SalePackError as exc:
        check("duplicate refused", exc.code == "duplicate_control", exc.code)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-SALE-01"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = pack.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    junk = json.loads(before.decode())
    junk["CAP-SALE-01"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = pack.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = pack.honesty_flags(catalog_db=missing_db)
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
    check("module does not mark_resolved", "mark_resolved" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/sale-evidence-pack" in serve)
    check("page route registered", "/sale-evidence-pack" in serve)
    check("vdr route refused in server", "/api/vdr/export" in serve)
    check("buyer route refused in server", "/api/buyer-mode/export" in serve)
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

        st, _anon = call("GET", "/api/sale-evidence-pack", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/sale-evidence-pack", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/sale-evidence-pack", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner sees 60", owner.get("control_count") == 60, str(owner.get("control_count")))
            check("owner empty slots", owner.get("empty_slots") == 60 and owner.get("filled_slots") == 0)
            check("owner no proven token", "PROVEN" not in json.dumps(owner))
            check("owner no export", owner.get("vdr_export") is False and owner.get("buyer_export") is False)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
        st, missing = call("GET", "/api/sale-evidence-pack/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/sale-evidence-pack/CTRL-GGV-FINANCE-QUALITY", MATT)
        check("owner one 200", st == 200 and isinstance(one, dict) and (one.get("control") or {}).get("slot") == "EMPTY", str(st))
        st, domains = call("GET", "/api/sale-evidence-pack/domains", MATT)
        check("owner domains 200", st == 200 and isinstance(domains, dict) and len(domains.get("domains") or []) == 6, str(st))
        st, page_anon = call("GET", "/sale-evidence-pack", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/sale-evidence-pack", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page, bytes) and b"CAP-SALE-01" in page and b"Buyer export is refused" in page and b"EMPTY" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/sale-evidence-pack", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/sale-evidence-pack", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/sale-evidence-pack", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
        st, vdr = call("POST", "/api/vdr/export", MATT)
        check("owner vdr refused", st == 405 and isinstance(vdr, dict) and vdr.get("error") == "vdr_export_refused", str(vdr)[:200])
        st, buyer = call("GET", "/api/buyer-mode/export", MATT)
        check("owner buyer GET refused", st == 405 and isinstance(buyer, dict) and buyer.get("error") == "buyer_export_refused", str(buyer)[:200])
        st, qexport = call("GET", "/api/sale-evidence-pack?export=vdr", MATT)
        check("query vdr refused", st == 405 and isinstance(qexport, dict) and qexport.get("error") == "vdr_export_refused", str(qexport)[:180])
        st, habitat = call("GET", "/api/sale-evidence-pack?entity=HABITAT", MATT)
        check("query entity refused", st == 400 and isinstance(habitat, dict) and habitat.get("error") == "invalid_entity", str(habitat)[:180])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="sale-evidence-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    cr_before = _cr_row()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    try:
        test_live_pack()
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
    check("CR row unchanged", _cr_row() == cr_before, str(_cr_row()))
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
