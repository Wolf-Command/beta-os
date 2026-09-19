#!/usr/bin/env python3
"""CAP-SALE-02 buyer data room. Empty folders. Empty slots. No share. No buyer."""
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

from core import sale_buyer_dataroom as room  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "sale_buyer_dataroom.py"
CR_ID = "CR-766f242208e401ad"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
FOLDER_IDS = {
    "FOLDER-FINANCE",
    "FOLDER-HR",
    "FOLDER-LEGAL",
    "FOLDER-OPS",
    "FOLDER-COMPLIANCE",
    "FOLDER-TECH",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _by_id(report: dict) -> dict:
    return {row["id"]: row for row in report["checklist"]}


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


def test_live_room() -> None:
    report = room.build_room()
    folders = {row["id"]: row for row in report["folders"]}
    check("six required folders", set(folders) == FOLDER_IDS, str(sorted(folders)))
    check("folders required", all(row["required"] is True for row in report["folders"]))
    check("folders not on disk", all(row["on_disk"] is False and row["documents"] == [] for row in report["folders"]))
    check("folder paths are logical", all(row["path"].startswith("VDR/") and not row["path"].startswith("/") for row in report["folders"]))
    check("no disk tree created", not (ROOT / "VDR").exists() and report["on_disk"] is False)
    tree = report["tree"]
    check("root is virtual", tree["id"] == "VDR" and tree["on_disk"] is False and tree["document_count"] == 0)
    check("root has six children", len(tree["children"]) == 6)
    check("no buyers", report["buyers"] == [] and report["buyer_count"] == 0 and tree["buyer_count"] == 0)
    check("no share url", tree["share_url"] is None and all(row["share_url"] is None for row in report["folders"]))
    check("canon 60 slots", report["slots_read"] == 60 and report["slot_list_matches_canon"] is True, str(report["slots_read"]))
    check("shown 60", report["slot_count"] == 60)
    check("all live slots empty", report["empty_slots"] == 60 and report["filled_slots"] == 0 and report["document_count"] == 0)
    slots = report["checklist"]
    check(
        "no filled slot",
        all(row["filled"] is False and row["document"] is None and row["filename"] is None and row["slot"] == "EMPTY" for row in slots),
    )
    check("no slot proved", all(row["proven"] is False and row["shared"] is False and row["buyer_access"] is False for row in slots))
    ids = [row["id"] for row in slots]
    check("slot ids unique", len(ids) == len(set(ids)))
    by = _by_id(report)
    finance = by["CHK-GGV-FINANCE-QUALITY"]
    check("finance folder", finance["folder"] == "FINANCE" and finance["folder_id"] == "FOLDER-FINANCE" and finance["entity"] == "GGV")
    check("finance checklist count", folders["FOLDER-FINANCE"]["checklist_count"] == 12 and folders["FOLDER-FINANCE"]["filled_slots"] == 0)
    check("hr checklist count", folders["FOLDER-HR"]["checklist_count"] == 15)
    check("legal checklist count", folders["FOLDER-LEGAL"]["checklist_count"] == 6)
    check("ops checklist count", folders["FOLDER-OPS"]["checklist_count"] == 12)
    check("compliance checklist count", folders["FOLDER-COMPLIANCE"]["checklist_count"] == 3)
    check("tech checklist count", folders["FOLDER-TECH"]["checklist_count"] == 9)
    growth = by["CHK-AMG-GROWTH-OPPORTUNITIES"]
    check("growth stays unmapped", growth["folder"] is None and growth["slot"] == "EMPTY" and growth["document"] is None)
    check("unmapped count", report["unmapped"]["checklist_count"] == 3 and report["unmapped"]["required"] is False)
    check("entities only three", {row["entity"] for row in slots} == {"GGV", "AMG", "BZG"})
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-SALE-02")
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.skeleton", flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False and flags.get("invented_proven") is False)
    check("honesty.not_ready", flags.get("invented_ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False)
    check("honesty.no_share", flags.get("live_share") is False and flags.get("vdr_share") is False and flags.get("buyer_access") is False)
    check("room export flags", report["vdr_export"] is False and report["buyer_export"] is False and report["ledger_write"] is False)
    dumped = json.dumps(report)
    check("live room has no PROVEN token", "PROVEN" not in dumped)
    check("live room has no READY token", "READY" not in dumped)
    check("live room has no download claim", "download" not in dumped and "http://" not in dumped and "https://" not in dumped)
    one = room.read_folder("FOLDER-FINANCE")
    check("read finance empty", one["ok"] is True and one["folder"]["slot"] == "EMPTY" and one["document_count"] == 0)
    check("read finance slots", len(one["checklist"]) == 12 and all(row["document"] is None for row in one["checklist"]))
    check("read finance bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)
    short = room.read_folder("TECH")
    check("read short id", short["folder"]["id"] == "FOLDER-TECH" and short["folder"]["document_count"] == 0)


def test_filters_and_honesty(td: Path) -> None:
    ggv = room.build_room(entity="ggv")
    check("entity filter", ggv["slot_count"] == 20 and {row["entity"] for row in ggv["checklist"]} == {"GGV"})
    check("entity filter keeps folders", {row["id"] for row in ggv["folders"]} == FOLDER_IDS)
    check("entity finance narrower", next(row for row in ggv["folders"] if row["id"] == "FOLDER-FINANCE")["checklist_count"] == 4)
    finance = room.build_room(folder="finance")
    check("folder filter", {row["folder"] for row in finance["checklist"]} == {"FINANCE"} and finance["slot_count"] == 12, str(finance["slot_count"]))
    check("folder filter still lists six", len(finance["folders"]) == 6)
    unknown = room.build_room(folder="UNKNOWN")
    check("unknown filter", unknown["slot_count"] == 3 and all(row["area"] == "Growth opportunities" for row in unknown["checklist"]))
    try:
        room.build_room(entity="HABITAT")
        check("unknown entity refused", False)
    except room.BuyerDataroomError as exc:
        check("unknown entity refused", exc.code == "invalid_entity", exc.code)
    try:
        room.build_room(folder="SALE")
        check("unknown folder refused", False)
    except room.BuyerDataroomError as exc:
        check("unknown folder refused", exc.code == "invalid_folder", exc.code)
    try:
        room.read_folder("NO-SUCH")
        check("missing folder refused", False)
    except room.BuyerDataroomError as exc:
        check("missing folder refused", exc.code == "not_found", exc.code)
    try:
        room.read_folder("TREE")
        check("tree id refused", False)
    except room.BuyerDataroomError as exc:
        check("tree id refused", exc.code == "not_found", exc.code)
    try:
        room.read_folder("SHARE")
        check("share id refused", False)
    except room.BuyerDataroomError as exc:
        check("share id refused", exc.code == "vdr_share_refused", exc.code)
    try:
        room.read_folder("EXPORT")
        check("export id refused", False)
    except room.BuyerDataroomError as exc:
        check("export id refused", exc.code == "vdr_export_refused", exc.code)
    try:
        room.read_folder("GRANT")
        check("grant id refused", False)
    except room.BuyerDataroomError as exc:
        check("grant id refused", exc.code == "buyer_access_refused", exc.code)
    try:
        room.build_room(csv_path=td / "missing.csv")
        check("missing source not empty room", False)
    except room.BuyerDataroomError as exc:
        check("missing source not empty room", exc.code == "not_read", exc.code)
    bad = td / "bad.csv"
    bad.write_text("Entity,Area\nGGV,Finance quality\n", encoding="utf-8")
    try:
        room.build_room(csv_path=bad)
        check("bad columns refused", False)
    except room.BuyerDataroomError as exc:
        check("bad columns refused", exc.code == "bad_source", exc.code)
    try:
        room.build_room(csv_path=Path("/tmp/wolf-system/sale.csv"))
        check("wolf-system path refused", False)
    except room.BuyerDataroomError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        room.build_room(ledger_path=Path("/tmp/Production/ledger.json"))
        check("production path refused", False)
    except room.BuyerDataroomError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        room.build_room(csv_path=td / "alchemist-sale.csv")
        check("alchemist path refused", False)
    except room.BuyerDataroomError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        room.refuse_external_write({"proven": True})
        check("write refused", False)
    except room.BuyerDataroomError as exc:
        check("write refused", exc.code == "writes_refused", exc.code)
    try:
        room.refuse_share({})
        check("share refused", False)
    except room.BuyerDataroomError as exc:
        check("share refused", exc.code == "vdr_share_refused", exc.code)
    try:
        room.refuse_export({})
        check("export refused", False)
    except room.BuyerDataroomError as exc:
        check("export refused", exc.code == "vdr_export_refused", exc.code)
    try:
        room.refuse_buyer_access({})
        check("buyer refused", False)
    except room.BuyerDataroomError as exc:
        check("buyer refused", exc.code == "buyer_access_refused", exc.code)
    try:
        room.refuse_external_write({"share": True})
        check("payload share refused", False)
    except room.BuyerDataroomError as exc:
        check("payload share refused", exc.code == "vdr_share_refused", exc.code)
    try:
        room.refuse_external_write({"export": "vdr"})
        check("payload export refused", False)
    except room.BuyerDataroomError as exc:
        check("payload export refused", exc.code == "vdr_export_refused", exc.code)
    try:
        room.refuse_external_write({"grant": "buyer@example.com"})
        check("payload grant refused", False)
    except room.BuyerDataroomError as exc:
        check("payload grant refused", exc.code == "buyer_access_refused", exc.code)
    try:
        room.refuse_fill({"document": "invented.pdf"})
        check("fill refused", False)
    except room.BuyerDataroomError as exc:
        check("fill refused", exc.code == "fill_refused", exc.code)
    try:
        room.guard_query(share="1")
        check("query share refused", False)
    except room.BuyerDataroomError as exc:
        check("query share refused", exc.code == "vdr_share_refused", exc.code)
    try:
        room.guard_query(export="vdr")
        check("query export refused", False)
    except room.BuyerDataroomError as exc:
        check("query export refused", exc.code == "vdr_export_refused", exc.code)
    try:
        room.guard_query(buyer="1")
        check("query buyer refused", False)
    except room.BuyerDataroomError as exc:
        check("query buyer refused", exc.code == "buyer_access_refused", exc.code)
    try:
        room.guard_query(fill="1")
        check("query fill refused", False)
    except room.BuyerDataroomError as exc:
        check("query fill refused", exc.code == "fill_refused", exc.code)


def test_empty_stays_empty(td: Path) -> None:
    rows = [
        _blank_row(
            "GGV",
            "Finance quality",
            **{
                "Evidence / Metric": "bank-pack.pdf",
                "Current State": "looks complete",
                "Target State": "Sale-ready evidence continuously maintained",
                "Status": "PROVEN",
            },
        ),
        _blank_row("AMG", "Growth opportunities"),
    ]
    path = td / "partial.csv"
    _write_csv(path, rows)
    report = room.build_room(csv_path=path)
    by = _by_id(report)
    finance = by["CHK-GGV-FINANCE-QUALITY"]
    check("source file is not a document", finance["document"] is None and finance["filename"] is None and finance["filled"] is False)
    check("status word is not a prove", finance["slot"] == "EMPTY" and finance["proven"] is False)
    dumped = json.dumps(report)
    check("source filename not copied", "bank-pack.pdf" not in dumped)
    check("partial not canon", report["slot_list_matches_canon"] is False and report["slots_read"] == 2)
    check("partial stays empty", report["empty_slots"] == 2 and report["filled_slots"] == 0 and report["document_count"] == 0)
    check("room still not proved", report["honesty"]["proven"] is False and report["honesty"]["invented_proven"] is False)
    check("folders still empty", all(row["documents"] == [] and row["document_count"] == 0 for row in report["folders"]))
    dup = td / "dup.csv"
    _write_csv(dup, [_blank_row("GGV", "Finance quality"), _blank_row("GGV", "Finance quality")])
    try:
        room.build_room(csv_path=dup)
        check("duplicate refused", False)
    except room.BuyerDataroomError as exc:
        check("duplicate refused", exc.code == "duplicate_slot", exc.code)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-SALE-02"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = room.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    ready = json.loads(before.decode())
    ready["CAP-SALE-02"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = room.honesty_flags(ready_path)
    check("already ready ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY")
    check("already ready is not a write", ready_flags["model_c_write"] is False and ready_flags["invented_ready"] is False)
    junk = json.loads(before.decode())
    junk["CAP-SALE-02"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = room.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = room.honesty_flags(catalog_db=missing_db)
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
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/buyer-dataroom" in serve)
    check("page route registered", "/buyer-dataroom" in serve)
    check("share route refused in server", "/api/vdr/share" in serve)
    check("grant route refused in server", "/api/buyer-dataroom/grant" in serve)
    check("sale vdr export still refused", "/api/vdr/export" in serve)
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

        st, _anon = call("GET", "/api/buyer-dataroom", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/buyer-dataroom", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/buyer-dataroom", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner sees 60", owner.get("slot_count") == 60, str(owner.get("slot_count")))
            check("owner empty slots", owner.get("empty_slots") == 60 and owner.get("filled_slots") == 0 and owner.get("document_count") == 0)
            check("owner six folders", owner.get("folder_count") == 6)
            check("owner no proven token", "PROVEN" not in json.dumps(owner))
            check("owner no ready token", "READY" not in json.dumps(owner))
            check("owner no share", owner.get("live_share") is False and owner.get("buyer_access") is False and owner.get("vdr_export") is False)
            check("owner no buyers", owner.get("buyers") == [] and owner.get("buyer_count") == 0)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner not on disk", owner.get("on_disk") is False)
        st, missing = call("GET", "/api/buyer-dataroom/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/buyer-dataroom/FOLDER-FINANCE", MATT)
        check("owner folder 200", st == 200 and isinstance(one, dict) and (one.get("folder") or {}).get("slot") == "EMPTY", str(st))
        st, tree = call("GET", "/api/buyer-dataroom/tree", MATT)
        check("owner tree 200", st == 200 and isinstance(tree, dict) and len((tree.get("tree") or {}).get("children") or []) == 6, str(st))
        st, checklist = call("GET", "/api/buyer-dataroom/checklist", MATT)
        check("owner checklist 200", st == 200 and isinstance(checklist, dict) and checklist.get("slot_count") == 60 and checklist.get("filled_slots") == 0, str(st))
        st, page_anon = call("GET", "/buyer-dataroom", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/buyer-dataroom", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page, bytes) and b"CAP-SALE-02" in page and b"No buyer access" in page and b"EMPTY" in page and b"Live share is refused" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/buyer-dataroom", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/buyer-dataroom", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/buyer-dataroom", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
        st, share = call("POST", "/api/vdr/share", MATT)
        check("owner share refused", st == 405 and isinstance(share, dict) and share.get("error") == "vdr_share_refused", str(share)[:200])
        st, share_get = call("GET", "/api/buyer-dataroom/share", MATT)
        check("owner share GET refused", st == 405 and isinstance(share_get, dict) and share_get.get("error") == "vdr_share_refused", str(share_get)[:200])
        st, exported = call("POST", "/api/buyer-dataroom/export", MATT)
        check("owner room export refused", st == 405 and isinstance(exported, dict) and exported.get("error") == "vdr_export_refused", str(exported)[:200])
        st, grant = call("POST", "/api/buyer-dataroom/grant", MATT)
        check("owner grant refused", st == 405 and isinstance(grant, dict) and grant.get("error") == "buyer_access_refused", str(grant)[:200])
        st, qshare = call("GET", "/api/buyer-dataroom?share=1", MATT)
        check("query share refused", st == 405 and isinstance(qshare, dict) and qshare.get("error") == "vdr_share_refused", str(qshare)[:180])
        st, habitat = call("GET", "/api/buyer-dataroom?entity=HABITAT", MATT)
        check("query entity refused", st == 400 and isinstance(habitat, dict) and habitat.get("error") == "invalid_entity", str(habitat)[:180])
        st, vdr = call("POST", "/api/vdr/export", MATT)
        check("sale vdr export still refused", st == 405 and isinstance(vdr, dict) and vdr.get("error") == "vdr_export_refused", str(vdr)[:200])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="buyer-dataroom-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    try:
        test_live_room()
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
    check("resolved CR count unchanged", _resolved_count() == resolved_before, str(_resolved_count()))
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
