#!/usr/bin/env python3
"""CAP-SALE-04 attack audit. Named sections. Empty packs. Licence preserved. No run."""
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

from core import sale_attack_audit as audit  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "sale_attack_audit.py"
CR_ID = "CR-c6e1a48e4a3e8a91"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
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


def test_live_audit() -> None:
    report = audit.build_audit()
    sections = _by_id(report["sections"])
    check("thirty sections", report["section_count"] == 30, str(report["section_count"]))
    check("entities are the three companies", report["entities"] == ["GGV", "AMG", "BZG"])
    check("each section is one company", all(row["company_specific"] is True and row["entity"] in {"GGV", "AMG", "BZG"} for row in report["sections"]))
    check("no attack run", report["attack_run"] is False and report["live_attack"] is False and report["findings_written"] is False)
    customer = sections["AUD-GGV-CUSTOMER-CONCENTRATION"]
    check("customer section named", customer["name"] == "Customer concentration" and customer["named"] is True)
    check("customer findings empty", customer["findings"] is None and customer["weakness"] is None and customer["fix"] is None and customer["data"] is None)
    check("customer not run", customer["attack_run"] is False and customer["item_count"] == 1)
    check("item names have no data", all(item["data"] is None and item["named"] is True for row in report["sections"] for item in row["items"]))
    check("named item count", report["item_count"] == 30, str(report["item_count"]))
    check("customer item id", customer["items"][0]["id"] == "CTRL-GGV-CUSTOMER-CONCENTRATION")
    growth = sections["AUD-AMG-GROWTH"]
    check("growth is a section", growth["name"] == "Growth opportunities" and growth["data"] is None and growth["item_count"] == 1)
    brand = sections["AUD-BZG-BRAND-IP"]
    check("brand section named", brand["name"] == "Brand/IP ownership" and brand["items"][0]["id"] == "CTRL-BZG-BRAND-IP-OWNERSHIP")
    packs = _by_id(report["packs"])
    check("twelve packs", report["pack_count"] == 12 and report["empty_packs"] == 12 and report["filled_packs"] == 0)
    slot = packs["PACK-GGV-SHARED-SERVICES"]
    check(
        "pack empty",
        slot["slot"] == "EMPTY" and slot["filled"] is False and slot["filename"] is None and slot["bytes"] is None and slot["path"] is None and slot["written"] is False,
    )
    check(
        "all packs empty",
        all(row["slot"] == "EMPTY" and row["filled"] is False and row["filename"] is None and row["data"] is None and row["attack_run"] is False for row in report["packs"]),
    )
    licence = report["licence"]
    check("licence id", licence["id"] == "BOUND-WOLF-LICENCE" and licence["kind"] == "licence_boundary")
    check(
        "licence preserved",
        report["licence_preserved"] is True
        and licence["preserved"] is True
        and licence["licence_granted"] is False
        and licence["wolf_ip_transferred"] is False
        and licence["architecture_copied"] is False
        and licence["payload"] is None
        and licence["data"] is None
        and licence["buyer_receipt"] is None,
    )
    check("no buyers", report["buyers"] == [] and report["buyer_count"] == 0 and report["buyer_grant"] is False and report["share_url"] is None)
    check("no export", report["buyer_export"] is False and report["transition_pack_written"] is False and report["on_disk"] is False)
    check("canon 60 names", report["controls_read"] == 60 and report["control_list_matches_canon"] is True)
    check("outside audit named not packed", report["not_in_audit"]["control_count"] == 30 and report["not_in_audit"]["in_audit"] is False and report["not_in_audit"]["pack_count"] == 0)
    check("finance not a section", all(row["area"] != "Finance quality" for row in report["sections"]))
    check("not approved empty on canon", report["not_approved"]["control_count"] == 0)
    check("gaps documented", len(report["gaps"]) >= 8 and any("empty" in line for line in report["gaps"]))
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-SALE-04")
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT" and flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False and flags.get("invented_proven") is False)
    check("honesty.not_ready", flags.get("invented_ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False and flags.get("cr_mutated") is False)
    check("honesty.no attack no grant", flags.get("attack_run") is False and flags.get("licence_granted") is False and flags.get("buyer_grant") is False)
    dumped = json.dumps(report)
    check("live audit has no PROVEN token", "PROVEN" not in dumped)
    check("live audit has no READY token", "READY" not in dumped)
    check("live audit has no download claim", "download" not in dumped and "http://" not in dumped and "https://" not in dumped)
    one = audit.read_section("AUD-GGV-CUSTOMER-CONCENTRATION")
    check("read section named", one["ok"] is True and one["section"]["findings"] is None and one["section"]["data"] is None and one["attack_run"] is False)
    check("read section bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)
    short = audit.read_section("GGV-CUSTOMER-CONCENTRATION")
    check("read short id", short["section"]["id"] == "AUD-GGV-CUSTOMER-CONCENTRATION")
    packed = audit.read_section("PACK-GGV-SHARED-SERVICES")
    check("read pack stays empty", packed["pack"]["slot"] == "EMPTY" and packed["pack"]["filename"] is None and packed["payload"] is None)
    bound = audit.read_section("BOUND-WOLF-LICENCE")
    check("read licence stays closed", bound["preserved"] is True and bound["payload"] is None and bound["licence"]["wolf_ip_transferred"] is False)
    check("read licence has no path", "/Users/" not in json.dumps(bound))


def test_filters_and_honesty(td: Path) -> None:
    ggv = audit.build_audit(entity="ggv")
    check("entity filter sections", ggv["section_count"] == 10 and ggv["entities"] == ["GGV"])
    check("entity filter items", ggv["item_count"] == 10, str(ggv["item_count"]))
    check("entity filter packs", ggv["pack_count"] == 4 and ggv["empty_packs"] == 4 and ggv["filled_packs"] == 0)
    check("entity filter licence stays", ggv["licence_preserved"] is True and ggv["licence"]["payload"] is None)
    check("entity filter outside", ggv["not_in_audit"]["control_count"] == 10)
    check("entity filter still canon source", ggv["controls_read"] == 60 and ggv["control_list_matches_canon"] is True)
    try:
        audit.build_audit(entity="HABITAT")
        check("unknown entity refused", False)
    except audit.AttackAuditError as exc:
        check("unknown entity refused", exc.code == "invalid_entity", exc.code)
    try:
        audit.read_section("NO-SUCH")
        check("missing section refused", False)
    except audit.AttackAuditError as exc:
        check("missing section refused", exc.code == "not_found", exc.code)
    try:
        audit.read_section("SECTIONS")
        check("view id refused", False)
    except audit.AttackAuditError as exc:
        check("view id refused", exc.code == "not_found", exc.code)
    try:
        audit.read_section("EXPORT")
        check("export id refused", False)
    except audit.AttackAuditError as exc:
        check("export id refused", exc.code == "buyer_export_refused", exc.code)
    try:
        audit.read_section("GRANT")
        check("grant id refused", False)
    except audit.AttackAuditError as exc:
        check("grant id refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        audit.read_section("SHARE")
        check("share id refused", False)
    except audit.AttackAuditError as exc:
        check("share id refused", exc.code == "buyer_share_refused", exc.code)
    try:
        audit.read_section("RUN")
        check("run id refused", False)
    except audit.AttackAuditError as exc:
        check("run id refused", exc.code == "attack_refused", exc.code)
    try:
        audit.read_section("TRANSFER")
        check("transfer id refused", False)
    except audit.AttackAuditError as exc:
        check("transfer id refused", exc.code == "licence_refused", exc.code)
    try:
        audit.build_audit(csv_path=td / "missing.csv")
        check("missing source not empty audit", False)
    except audit.AttackAuditError as exc:
        check("missing source not empty audit", exc.code == "not_read", exc.code)
    bad = td / "bad.csv"
    bad.write_text("Entity,Area\nGGV,Customer concentration\n", encoding="utf-8")
    try:
        audit.build_audit(csv_path=bad)
        check("bad columns refused", False)
    except audit.AttackAuditError as exc:
        check("bad columns refused", exc.code == "bad_source", exc.code)
    try:
        audit.build_audit(csv_path=Path("/tmp/wolf-system/sale.csv"))
        check("wolf-system path refused", False)
    except audit.AttackAuditError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        audit.build_audit(ledger_path=Path("/tmp/Production/ledger.json"))
        check("production path refused", False)
    except audit.AttackAuditError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        audit.build_audit(csv_path=td / "alchemist-sale.csv")
        check("alchemist path refused", False)
    except audit.AttackAuditError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        audit.refuse_external_write({"proven": True})
        check("write refused", False)
    except audit.AttackAuditError as exc:
        check("write refused", exc.code == "writes_refused", exc.code)
    try:
        audit.refuse_attack({})
        check("attack refused", False)
    except audit.AttackAuditError as exc:
        check("attack refused", exc.code == "attack_refused", exc.code)
    try:
        audit.refuse_grant({})
        check("grant refused", False)
    except audit.AttackAuditError as exc:
        check("grant refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        audit.refuse_share({})
        check("share refused", False)
    except audit.AttackAuditError as exc:
        check("share refused", exc.code == "buyer_share_refused", exc.code)
    try:
        audit.refuse_export({})
        check("export refused", False)
    except audit.AttackAuditError as exc:
        check("export refused", exc.code == "buyer_export_refused", exc.code)
    try:
        audit.refuse_licence({})
        check("licence refused", False)
    except audit.AttackAuditError as exc:
        check("licence refused", exc.code == "licence_refused", exc.code)
    try:
        audit.refuse_external_write({"run": True})
        check("payload run refused", False)
    except audit.AttackAuditError as exc:
        check("payload run refused", exc.code == "attack_refused", exc.code)
    try:
        audit.refuse_external_write({"grant": "buyer@example.com"})
        check("payload grant refused", False)
    except audit.AttackAuditError as exc:
        check("payload grant refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        audit.refuse_external_write({"share": True})
        check("payload share refused", False)
    except audit.AttackAuditError as exc:
        check("payload share refused", exc.code == "buyer_share_refused", exc.code)
    try:
        audit.refuse_external_write({"export": "pack"})
        check("payload export refused", False)
    except audit.AttackAuditError as exc:
        check("payload export refused", exc.code == "buyer_export_refused", exc.code)
    try:
        audit.refuse_external_write({"transfer": True})
        check("payload transfer refused", False)
    except audit.AttackAuditError as exc:
        check("payload transfer refused", exc.code == "licence_refused", exc.code)
    try:
        audit.refuse_fill({"filename": "invented.pdf"})
        check("fill refused", False)
    except audit.AttackAuditError as exc:
        check("fill refused", exc.code == "fill_refused", exc.code)
    try:
        audit.refuse_production({})
        check("production refused", False)
    except audit.AttackAuditError as exc:
        check("production refused", exc.code == "production_refused", exc.code)
    try:
        audit.refuse_external_write({"alchemist": True})
        check("alchemist write refused", False)
    except audit.AttackAuditError as exc:
        check("alchemist write refused", exc.code == "alchemist_refused", exc.code)
    try:
        audit.guard_query(run="1")
        check("query run refused", False)
    except audit.AttackAuditError as exc:
        check("query run refused", exc.code == "attack_refused", exc.code)
    try:
        audit.guard_query(grant="1")
        check("query grant refused", False)
    except audit.AttackAuditError as exc:
        check("query grant refused", exc.code == "buyer_grant_refused", exc.code)
    try:
        audit.guard_query(export="1")
        check("query export refused", False)
    except audit.AttackAuditError as exc:
        check("query export refused", exc.code == "buyer_export_refused", exc.code)
    try:
        audit.guard_query(licence="1")
        check("query licence refused", False)
    except audit.AttackAuditError as exc:
        check("query licence refused", exc.code == "licence_refused", exc.code)
    try:
        audit.guard_query(fill="1")
        check("query fill refused", False)
    except audit.AttackAuditError as exc:
        check("query fill refused", exc.code == "fill_refused", exc.code)


def test_empty_stays_empty(td: Path) -> None:
    rows = [
        _blank_row(
            "GGV",
            "Customer concentration",
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
        _blank_row("HABITAT", "Customer concentration", **{"Evidence / Metric": TOKEN}),
        _blank_row("GGV", "Finance quality", **{"Evidence / Metric": "finance-pack.pdf"}),
    ]
    path = td / "partial.csv"
    _write_csv(path, rows)
    report = audit.build_audit(csv_path=path)
    customer = _by_id(report["sections"])["AUD-GGV-CUSTOMER-CONCENTRATION"]
    check("source file is not data", customer["data"] is None and customer["items"][0]["data"] is None and customer["findings"] is None)
    check("status word is not a prove", customer["attack_run"] is False and report["filled_packs"] == 0)
    dumped = json.dumps(report)
    check("source filename not copied", "bank-pack.pdf" not in dumped and "finance-pack.pdf" not in dumped)
    check("source token not copied", TOKEN not in dumped)
    check("partial not canon", report["control_list_matches_canon"] is False and report["controls_read"] == 4)
    check("partial packs empty", report["empty_packs"] == report["pack_count"] and report["filled_packs"] == 0)
    check("habitat not approved", report["not_approved"]["control_count"] == 1 and report["not_approved"]["pack_count"] == 0)
    check("habitat has no section", all(row["entity"] != "HABITAT" for row in report["sections"]))
    growth = _by_id(report["sections"])["AUD-AMG-GROWTH"]
    check("growth stays a named empty section", growth["item_count"] == 1 and growth["data"] is None and growth["findings"] is None)
    check("finance stays outside", report["not_in_audit"]["control_count"] == 1 and report["not_in_audit"]["names"][0]["area"] == "Finance quality")
    check("audit still not proved", report["honesty"]["proven"] is False and report["honesty"]["invented_proven"] is False)
    check("no PROVEN token in partial", "PROVEN" not in dumped)
    check("licence still closed on partial", report["licence"]["licence_granted"] is False and report["licence"]["payload"] is None)
    dup = td / "dup.csv"
    _write_csv(dup, [_blank_row("GGV", "Customer concentration"), _blank_row("GGV", "Customer concentration")])
    try:
        audit.build_audit(csv_path=dup)
        check("duplicate refused", False)
    except audit.AttackAuditError as exc:
        check("duplicate refused", exc.code == "duplicate_section", exc.code)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-SALE-04"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = audit.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    ready = json.loads(before.decode())
    ready["CAP-SALE-04"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = audit.honesty_flags(ready_path)
    check("already ready ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY")
    check("already ready is not a write", ready_flags["model_c_write"] is False and ready_flags["invented_ready"] is False)
    junk = json.loads(before.decode())
    junk["CAP-SALE-04"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = audit.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = audit.honesty_flags(catalog_db=missing_db)
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
    check("route registered", 'path == "/api/attack-audit"' in serve)
    check("page route registered", '"/attack-audit"' in serve)
    check("run route refused in server", '"/api/attack-audit/run"' in serve)
    check("transfer route refused in server", '"/api/attack-audit/transfer"' in serve)
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

        st, _anon = call("GET", "/api/attack-audit", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/attack-audit", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/attack-audit", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner sections 30", owner.get("section_count") == 30, str(owner.get("section_count")))
            check("owner packs empty", owner.get("empty_packs") == 12 and owner.get("filled_packs") == 0)
            check("owner licence closed", owner.get("licence_preserved") is True and owner.get("licence_granted") is False and (owner.get("licence") or {}).get("payload") is None)
            check("owner no attack", owner.get("attack_run") is False)
            check("owner no proven token", "PROVEN" not in json.dumps(owner))
            check("owner no ready token", "READY" not in json.dumps(owner))
            check("owner no grant", owner.get("buyer_grant") is False and owner.get("buyer_export") is False and owner.get("buyer_count") == 0)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner ceiling label", (owner.get("honesty") or {}).get("maturity_ceiling") == "BUILT")
            check("owner ledger still specified", (owner.get("honesty") or {}).get("maturity") == "SPECIFIED")
        st, missing = call("GET", "/api/attack-audit/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/attack-audit/AUD-GGV-CUSTOMER-CONCENTRATION", MATT)
        check("owner section 200", st == 200 and isinstance(one, dict) and (one.get("section") or {}).get("findings") is None, str(st))
        st, sections = call("GET", "/api/attack-audit/sections", MATT)
        check("owner sections 200", st == 200 and isinstance(sections, dict) and sections.get("section_count") == 30, str(st))
        st, packs = call("GET", "/api/attack-audit/packs", MATT)
        check("owner packs 200", st == 200 and isinstance(packs, dict) and packs.get("filled_packs") == 0 and packs.get("empty_packs") == 12, str(st))
        st, licence = call("GET", "/api/attack-audit/licence", MATT)
        check("owner licence 200", st == 200 and isinstance(licence, dict) and licence.get("licence_preserved") is True and (licence.get("licence") or {}).get("licence_granted") is False, str(st))
        st, page_anon = call("GET", "/attack-audit", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/attack-audit", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, bytes)
            and b"CAP-SALE-04" in page
            and b"Audit sections are named" in page
            and b"Transition-pack slots stay empty" in page
            and b"Wolf licence" in page
            and b"No attack was run" in page
            and b"No buyer grant" in page
            and b"EMPTY" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/attack-audit", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/attack-audit", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/attack-audit", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
        st, patch = call("PATCH", "/api/attack-audit", MATT)
        check("owner PATCH refused", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:160])
        st, run = call("POST", "/api/attack-audit/run", MATT)
        check("owner run refused", st == 405 and isinstance(run, dict) and run.get("error") == "attack_refused", str(run)[:200])
        st, grant = call("POST", "/api/attack-audit/grant", MATT)
        check("owner grant refused", st == 405 and isinstance(grant, dict) and grant.get("error") == "buyer_grant_refused", str(grant)[:200])
        st, share = call("POST", "/api/attack-audit/share", MATT)
        check("owner share refused", st == 405 and isinstance(share, dict) and share.get("error") == "buyer_share_refused", str(share)[:200])
        st, filled = call("POST", "/api/attack-audit/fill", MATT)
        check("owner fill refused", st == 405 and isinstance(filled, dict) and filled.get("error") == "fill_refused", str(filled)[:200])
        st, transferred = call("POST", "/api/attack-audit/transfer", MATT)
        check("owner transfer refused", st == 405 and isinstance(transferred, dict) and transferred.get("error") == "licence_refused", str(transferred)[:200])
        st, exported = call("GET", "/api/attack-audit/export", MATT)
        check("owner export refused", st == 405 and isinstance(exported, dict) and exported.get("error") == "buyer_export_refused", str(exported)[:200])
        st, qrun = call("GET", "/api/attack-audit?run=1", MATT)
        check("query run refused", st == 405 and isinstance(qrun, dict) and qrun.get("error") == "attack_refused", str(qrun)[:180])
        st, qlic = call("GET", "/api/attack-audit?licence=1", MATT)
        check("query licence refused", st == 405 and isinstance(qlic, dict) and qlic.get("error") == "licence_refused", str(qlic)[:180])
        st, habitat = call("GET", "/api/attack-audit?entity=HABITAT", MATT)
        check("query entity refused", st == 400 and isinstance(habitat, dict) and habitat.get("error") == "invalid_entity", str(habitat)[:180])
        st, narrowed = call("GET", "/api/attack-audit?entity=GGV", MATT)
        check("query entity narrows", st == 200 and isinstance(narrowed, dict) and narrowed.get("entities") == ["GGV"] and narrowed.get("section_count") == 10 and narrowed.get("licence_preserved") is True, str(st))
        st, mode_export = call("GET", "/api/buyer-mode/export", MATT)
        check("buyer export still refused", st == 405 and isinstance(mode_export, dict) and mode_export.get("error") == "buyer_export_refused", str(mode_export)[:200])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="attack-audit-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    try:
        test_live_audit()
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
