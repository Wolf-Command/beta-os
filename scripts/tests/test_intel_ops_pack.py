#!/usr/bin/env python3
"""Intel Ops pack v2 — Today ask, recall, approve-to-rule handoff on one desk."""
from __future__ import annotations

import json
import os
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

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import intel_ops_pack as pack  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_05 = "CR-be51980bd1194448"
CR_AU = "CR-dca0ad62e1b0032e"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
PAGE = ROOT / "dashboards" / "intel-ops-pack.html"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
BACKUPS = ROOT / "catalog" / "backups"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _cr(cr_id: str) -> str | None:
    conn = sqlite3.connect(str(CATALOG))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (cr_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_honesty() -> None:
    seat = pack.seat_for("PERS-MATT")
    check("owner seat", seat is not None and seat["money"] is False and seat["can_ask"] is True)
    check("devi forbidden", pack.seat_for("PERS-DEVI") is None)
    check("amanda forbidden", pack.seat_for("PERS-AMANDA") is None)
    check("haikal forbidden", pack.seat_for("PERS-HAIKAL") is None)
    check("misa forbidden", pack.seat_for("PERS-MISA") is None)
    flags = pack.honesty_flags()
    ledger = _ledger()
    check(
        "caps match ledger",
        flags["cap_intel_01"] == ledger["CAP-INTEL-01"][0]
        and flags["cap_intel_02"] == ledger["CAP-INTEL-02"][0]
        and flags["cap_intel_03"] == ledger["CAP-INTEL-03"][0]
        and flags["cap_intel_04"] == ledger["CAP-INTEL-04"][0]
        and flags["cap_intel_05"] == ledger["CAP-INTEL-05"][0]
        and flags["caps_raised"] is False,
    )
    check(
        "not invented prove",
        flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["proven"] is False
        and flags["ready"] is False
        and flags["auto_promote"] is False
        and flags["rule_execution"] is False
        and flags["live_rule"] is False,
    )
    check(
        "crs open",
        flags["cr_05_id"] == CR_05
        and flags["cr_05_state"] == "OPEN"
        and flags["cr_05_resolved"] is False
        and flags["cr_au_id"] == CR_AU
        and flags["cr_au_state"] == "OPEN"
        and flags["cr_au_resolved"] is False
        and flags["au_intel_02_wolf_started"] is False,
    )
    check("bound", flags["bound"] == "beta-intel-safe")
    check("hidden money", "finance" in flags["hidden"] and "payment" in flags["hidden"])
    check("no permission invent", flags["permission_grant_invented"] is False and flags["live_rbac_mutated"] is False)
    for fn, code in (
        (pack.refuse_payment, "payment_refused"),
        (pack.refuse_bank, "bank_refused"),
        (pack.refuse_finance, "finance_refused"),
        (pack.refuse_hr, "hr_refused"),
        (pack.refuse_trading, "trading_refused"),
        (pack.refuse_proven, "proven_refused"),
        (pack.refuse_ready, "ready_refused"),
        (pack.refuse_resolve, "resolve_refused"),
        (pack.refuse_promote, "promote_refused"),
        (pack.refuse_execute, "execute_refused"),
        (pack.refuse_production, "production_refused"),
    ):
        try:
            fn({})
            check(code, False)
        except pack.IntelOpsPackError as exc:
            check(code, exc.code == code)
    try:
        pack.pack_db("/Users/wolfterminal/wolf-system/intel.sqlite")
        check("wolf-system path", False)
    except pack.IntelOpsPackError as exc:
        check("wolf-system refused", exc.code == "not_beta")
    page = PAGE.read_text(encoding="utf-8")
    check("page bound", "beta-intel-safe" in page)
    check("page no money button", ">Pay<" not in page and ">Settle<" not in page)
    check("page no auto-promote", "No auto-promote" in page or "auto-promote" in page.lower())
    check("page stub honesty", "stub" in page.lower() and "live rule" in page.lower())
    source = (SCRIPTS / "core" / "intel_ops_pack.py").read_text(encoding="utf-8")
    for name in WIP:
        check(f"module does not reference {Path(name).name}", Path(name).name not in source)


def test_loop() -> None:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    db = BACKUPS / f"tmp-intel-ops-pack-test-{os.getpid()}.sqlite"
    rules = BACKUPS / f"tmp-intel-ops-rules-test-{os.getpid()}.sqlite"
    for path in (db, rules):
        if path.exists():
            path.unlink()
    ask = pack.ask_question(
        question="What is Wolf's ClickUp policy?",
        scope="Wolf system",
        verified_person_id="PERS-MATT",
        db_path=db,
    )
    check(
        "ask returns honest outcome",
        ask.get("ok") is True
        and ask.get("status") in {"OWNER_DECISION", "AUTHORISED", "NOT_FOUND", "NEEDS_HUMAN", "UNKNOWN", "CONFLICTED"}
        and ask.get("promoted") is False
        and ask.get("live_rule") is False
        and ask.get("persisted") is True,
        str(ask.get("status")),
    )
    check("ask provenance labels", isinstance(ask.get("provenance"), list))
    check("ask honesty no llm", (ask.get("honesty") or {}).get("llm_as_evidence") is False)
    today = pack.today_strip(db)
    check(
        "today shows last ask",
        today.get("empty") is False
        and today.get("status") == ask.get("status")
        and today.get("next_human_action") == ask.get("next_human_action"),
    )
    recall = pack.recall_decisions(
        scope="Wolf system",
        query="",
        verified_person_id="PERS-MATT",
    )
    check(
        "recall empty is not invent",
        recall.get("ok") is True
        and recall.get("permission_grant_invented") is False
        and recall.get("live_rbac_mutated") is False
        and (recall.get("count") or 0) >= 0
        and ("invented history" in str(recall.get("why") or "").lower() or recall.get("count", 0) > 0),
    )
    if recall.get("count", 0) == 0:
        check("empty recall loud", recall.get("loud") is True and recall.get("empty") is True)
    else:
        check("recall returns rows", isinstance(recall.get("decisions"), list) and len(recall["decisions"]) > 0)
    note = pack.handoff_note(
        {"experiment_note": "Track D v2 handoff. Stub is not a live rule."},
        verified_person_id="PERS-MATT",
        rule_db_path=rules,
    )
    check(
        "note append only",
        note.get("appended") is True
        and note.get("state") == "NOTED"
        and note.get("promoted") is False
        and note.get("live") is False
        and note.get("approved") is False,
    )
    queue = pack.queue_summary(verified_person_id="PERS-MATT", rule_db_path=rules)
    check(
        "queue stub honesty",
        queue.get("state_counts", {}).get("NOTED") == 1
        and queue.get("auto_promote") is False
        and queue.get("live_rule") is False
        and queue.get("promoted_count") == 0,
    )
    try:
        pack.handoff_note(
            {"experiment_note": "x", "promote": True},
            verified_person_id="PERS-MATT",
            rule_db_path=rules,
        )
        check("promote on note refused", False)
    except pack.IntelOpsPackError as exc:
        check("promote on note refused", exc.code in {"promote_refused", "writes_refused"})
    try:
        pack.handoff_note(
            {"experiment_note": "x", "proven": True},
            verified_person_id="PERS-MATT",
            rule_db_path=rules,
        )
        check("proven on note refused", False)
    except pack.IntelOpsPackError as exc:
        check("proven on note refused", exc.code in {"proven_refused", "writes_refused"})
    try:
        pack.require_actor("PERS-DEVI")
        check("devi require raises", False)
    except pack.IntelOpsPackError as exc:
        check("devi require forbidden", exc.code == "forbidden")
    desk = pack.build_desk(
        verified_person_id="PERS-MATT",
        db_path=db,
        rule_db_path=rules,
    )
    check(
        "desk composes loop",
        desk.get("ok") is True
        and desk.get("today", {}).get("status") == ask.get("status")
        and desk.get("queue", {}).get("note_count") == 1
        and desk.get("caps", {}).get("CAP-INTEL-01") == _ledger()["CAP-INTEL-01"][0]
        and desk.get("caps", {}).get("CAP-INTEL-05") == "SPECIFIED"
        and desk.get("crs", {}).get(CR_05, {}).get("resolved") is False,
    )
    for path in (db, rules):
        if path.exists():
            path.unlink()


def test_api() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    ledger_before = LEDGER.read_text(encoding="utf-8")
    cr05_before = _cr(CR_05)
    cr_au_before = _cr(CR_AU)

    def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if method != "GET":
            data = json.dumps({} if body is None else body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(
            f"http://127.0.0.1:{port}{url_path}",
            headers=headers,
            method=method,
            data=data,
        )
        try:
            with urlopen(req, timeout=60) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode())
                except json.JSONDecodeError:
                    return resp.status, raw
        except HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed

    try:
        st, _anon = call("GET", "/api/intel/ops-pack", None)
        check("anon GET pack 403", st == 403, str(st))
        st, _out = call("GET", "/api/intel/ops-pack", OUTSIDER)
        check("outsider GET 403", st == 403, str(st))
        for label, subject in (("devi", DEVI), ("amanda", AMANDA), ("haikal", HAIKAL), ("misa", MISA)):
            st, _body = call("GET", "/api/intel/ops-pack", subject)
            check(f"{label} GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/intel/ops-pack", MATT)
        check(
            "owner GET 200",
            st == 200 and isinstance(owner, dict) and owner.get("ok") is True,
            str(owner)[:300] if isinstance(owner, dict) else str(owner)[:120],
        )
        if isinstance(owner, dict):
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check(
                "owner caps honest",
                (owner.get("caps") or {}).get("CAP-INTEL-01") == _ledger()["CAP-INTEL-01"][0]
                and (owner.get("caps") or {}).get("CAP-INTEL-05") == "SPECIFIED"
                and (owner.get("honesty") or {}).get("caps_raised") is False,
            )
            check(
                "owner money off",
                owner.get("payment_executed") is False
                and owner.get("money") is None
                and owner.get("auto_promote") is False,
            )
        st, ask = call(
            "POST",
            "/api/intel/ops-pack/ask",
            MATT,
            {"question": "What is Wolf's ClickUp policy?", "scope": "Wolf system"},
        )
        check(
            "owner ask 200",
            st == 200 and isinstance(ask, dict) and ask.get("ok") is True and ask.get("status"),
            str(ask)[:240] if isinstance(ask, dict) else str(st),
        )
        if isinstance(ask, dict):
            check("ask no promote", ask.get("promoted") is False and ask.get("live_rule") is False)
            check("ask provenance", isinstance(ask.get("provenance"), list))
        st, recall = call("GET", "/api/intel/ops-pack/recall?scope=Wolf%20system", MATT)
        check("owner recall 200", st == 200 and isinstance(recall, dict) and recall.get("ok") is True)
        st, queue = call("GET", "/api/intel/ops-pack/queue", MATT)
        check(
            "owner queue 200",
            st == 200
            and isinstance(queue, dict)
            and queue.get("auto_promote") is False
            and queue.get("live_rule") is False,
        )
        st, note = call(
            "POST",
            "/api/intel/ops-pack/note",
            MATT,
            {"experiment_note": "API handoff note. Not a live rule."},
        )
        check(
            "owner note 200",
            st == 200
            and isinstance(note, dict)
            and note.get("appended") is True
            and note.get("state") == "NOTED"
            and note.get("promoted") is False,
            str(note)[:240] if isinstance(note, dict) else str(st),
        )
        for method, path in (
            ("POST", "/api/intel/ops-pack/payment"),
            ("POST", "/api/intel/ops-pack/bank"),
            ("POST", "/api/intel/ops-pack/proven"),
            ("POST", "/api/intel/ops-pack/ready"),
            ("POST", "/api/intel/ops-pack/resolve"),
            ("POST", "/api/intel/ops-pack/promote"),
            ("POST", "/api/intel/ops-pack/execute"),
            ("PUT", "/api/intel/ops-pack"),
            ("PATCH", "/api/intel/ops-pack/production"),
        ):
            code, body = call(method, path, MATT, {"amount": 1, "proven": True})
            check(f"{method} {path} refused", code == 405, str(body)[:180])
        st, _anon_post = call("POST", "/api/intel/ops-pack/ask", None, {"question": "x"})
        check("anon POST ask 403", st == 403, str(st))
        st, _anon_note = call("POST", "/api/intel/ops-pack/note", None, {"experiment_note": "x"})
        check("anon POST note 403", st == 403, str(st))
        st, _anon_orch = call("GET", "/api/intel/orchestrate", None)
        check("anon orchestrate 403", st == 403, str(st))
        st, _anon_rule = call("POST", "/api/intel/approve-to-rule/note", None, {"experiment_note": "x"})
        check("anon approve-to-rule note 403", st == 403, str(st))
        st, page = call("GET", "/intel-ops-pack", None)
        check("anon page 403", st == 403, str(st))
        st, page_ok = call("GET", "/intel-ops-pack", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page_ok, (bytes, bytearray))
            and b"beta-intel-safe" in page_ok
            and b">Pay<" not in page_ok,
        )
        st, uma = call("GET", "/api/bzg/uma-blu/today", MATT)
        check("uma route still present", st in {200, 403}, str(st))
        st, ggv = call("GET", "/api/ggv/ops-pack", None)
        check("ggv anon still 403", st == 403, str(st))
        st, amg = call("GET", "/api/amg/ops-pack", None)
        check("amg anon still 403", st == 403, str(st))
        st, empire = call("GET", "/api/owner/empire-pack", None)
        check("empire anon still 403", st == 403, str(st))
        st, harden = call("GET", "/api/core/harden-pack", None)
        check("harden anon still 403", st == 403, str(st))
    finally:
        httpd.shutdown()
    check("ledger bytes unchanged", LEDGER.read_text(encoding="utf-8") == ledger_before)
    check("cr05 unchanged", _cr(CR_05) == cr05_before == "OPEN")
    check("cr au unchanged", _cr(CR_AU) == cr_au_before == "OPEN")


def main() -> int:
    test_honesty()
    test_loop()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
