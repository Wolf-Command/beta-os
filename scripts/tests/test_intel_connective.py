#!/usr/bin/env python3
"""Sprint2 P4 Intel Connective — AKR/DM/fail-safe into BZG/GGV/AMG next actions."""
from __future__ import annotations

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
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import amg_ops_pack as amg  # noqa: E402
from core import ggv_ops_pack as ggv  # noqa: E402
from core import intel_connective as ic  # noqa: E402
from core import intel_eval_cost as ledger  # noqa: E402
from core import request_auth as ra  # noqa: E402
from core import uma_ops_console as uma  # noqa: E402

PASS = 0
FAIL = 0

CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp() -> Path:
    td = Path(tempfile.mkdtemp(prefix="intel-connect-", dir=str(ROOT / "state")))
    return td


def _empty_eval(td: Path) -> Path:
    return td / "intel_eval_empty.sqlite"


def _seed_fail_safe(td: Path) -> Path:
    db = td / "intel_eval_fail.sqlite"
    os.environ["WOLF_ALLOW_LIVE_INTEL_EVAL"] = "1"
    try:
        ledger.record_call(
            {
                "model": "none",
                "route": "intel.connective.test",
                "outcome": "ERROR",
                "provenance": {"source": "test", "surface": "intel_connective"},
            },
            person_id="PERS-MATT",
            db_path=db,
        )
    finally:
        os.environ.pop("WOLF_ALLOW_LIVE_INTEL_EVAL", None)
    return db


def test_honesty_and_refuses() -> None:
    flags = ic.honesty_flags()
    check("bound", flags.get("bound") == "beta-intel-connect-safe")
    check("no agent zoo", flags.get("agent_zoo") is False and flags.get("agent") is False)
    check("no auto promote", flags.get("auto_promote") is False)
    check("no auto execute", flags.get("auto_execute") is False)
    check("no invent proven", flags.get("invented_proven") is False and flags.get("proven") is False)
    check("no invent ready", flags.get("invented_ready") is False and flags.get("ready") is False)
    check("not orphan dashboard", flags.get("orphan_dashboard") is False)
    check("changes work flag", flags.get("changes_work") is True)
    schema = ic.schema_document()
    check("schema surfaces", schema["surfaces"] == ["bzg", "ggv", "amg"])
    try:
        ic.refuse_auto_promote({})
        check("promote raises", False)
    except ic.IntelConnectiveError as exc:
        check("promote refused", exc.code == "promote_refused")
    try:
        ic.refuse_auto_execute({})
        check("execute raises", False)
    except ic.IntelConnectiveError as exc:
        check("execute refused", exc.code == "execute_refused")
    try:
        ic.refuse_proven({})
        check("proven raises", False)
    except ic.IntelConnectiveError as exc:
        check("proven refused", exc.code == "proven_refused")
    try:
        ic.refuse_money({})
        check("money raises", False)
    except ic.IntelConnectiveError as exc:
        check("money refused", exc.code == "money_refused")
    try:
        ic.recommend_for_next_action("fin", {"code": "x", "label": "y"})
        check("bad surface raises", False)
    except ic.IntelConnectiveError as exc:
        check("bad surface", exc.code == "bad_surface")


def test_ggv_decision_memory_changes_work(td: Path) -> None:
    eval_db = _empty_eval(td)
    base = {"code": "qualify", "label": "Record qualification", "hook": "qualify"}
    rec = ic.recommend_for_next_action("ggv", base, eval_db=eval_db)
    check("ggv ok", rec.get("ok") is True and rec.get("bound") == ic.BOUND)
    check("ggv question crm", rec.get("question") == "Is Habitat CRM cut over?")
    # Live Decision Memory may or may not be seeded; either OWNER_DECISION or NOT_FOUND is honest.
    check(
        "ggv status honest",
        rec.get("status")
        in (
            "OWNER_DECISION",
            "NOT_FOUND",
            "CANONICAL",
            "NOT_CANONICAL",
            "UNKNOWN",
            "INACCESSIBLE",
            "CONFLICTED",
        ),
        str(rec.get("status")),
    )
    if rec.get("status") == "OWNER_DECISION":
        check("ggv changes work on DM hit", rec.get("changes_work") is True)
        check(
            "ggv effective differs",
            rec["effective_next"]["label"] != base["label"]
            or "CRM" in rec["effective_next"]["label"]
            or "Spine" in rec["effective_next"]["label"],
        )
        check(
            "ggv kind dm or combined",
            rec.get("kind") in ("decision_memory", "combined", "provider_fail_safe"),
        )
        check(
            "ggv decision id present",
            isinstance(rec.get("decision"), dict) and bool(rec["decision"].get("id")),
        )
    check("ggv no auto execute", rec.get("auto_execute") is False and rec.get("auto_promote") is False)

    bzg = ic.recommend_for_next_action(
        "bzg",
        {"code": "today", "label": "Review Uma Blu Today", "hook": "today"},
        eval_db=eval_db,
    )
    check("bzg ok", bzg.get("ok") is True)
    if bzg.get("status") == "OWNER_DECISION":
        check("bzg clickup changes work", bzg.get("changes_work") is True)
        check(
            "bzg clickup in label",
            "ClickUp" in bzg["effective_next"]["label"] or "Wolf" in bzg["effective_next"]["label"],
        )


def test_provider_fail_safe_changes_work(td: Path) -> None:
    eval_db = _seed_fail_safe(td)
    base = {"code": "touch", "label": "Record touch", "hook": "touch"}
    rec = ic.recommend_for_next_action("amg", base, eval_db=eval_db)
    check("fail-safe active", rec["provider_fail_safe"]["active"] is True)
    check("fail-safe changes work", rec.get("changes_work") is True)
    check(
        "fail-safe in label",
        "fail-safe" in rec["effective_next"]["label"].lower()
        or "deterministic" in rec["effective_next"]["label"].lower()
        or "desk actions" in rec["effective_next"]["label"].lower(),
    )
    check("prefer deterministic", rec["provider_fail_safe"]["prefer_deterministic"] is True)
    check("not a bill", rec["provider_fail_safe"]["not_a_bill"] is True)
    check("no invent prices", rec["provider_fail_safe"]["invent_prices"] is False)
    check("no auto execute on fail-safe", rec["provider_fail_safe"]["auto_execute"] is False)


def test_bzg_attach_and_uma_today(td: Path) -> None:
    os.environ["WOLF_INTEL_EVAL_DB"] = str(_empty_eval(td))
    try:
        payload = uma.today_cards(person_id="PERS-MATT")
        check("uma today ok", payload.get("ok") is True)
        check("uma intel strip", isinstance(payload.get("intel_connective"), dict))
        check("uma intel bound", payload.get("intel_bound") == ic.BOUND)
        check("uma next_action present", isinstance(payload.get("next_action"), dict))
        strip = payload["intel_connective"]
        check("uma strip not orphan", strip.get("orphan_dashboard") is False)
        check("uma strip no auto execute", strip.get("auto_execute") is False)
        now = payload.get("now")
        if now and now.get("intel_recommendation"):
            check("uma now has intel", isinstance(now["intel_recommendation"], dict))
    finally:
        os.environ.pop("WOLF_INTEL_EVAL_DB", None)


def test_ggv_board_intel(td: Path) -> None:
    os.environ["WOLF_INTEL_EVAL_DB"] = str(_empty_eval(td))
    db = td / "catalog.sqlite"
    shutil.copy(CATALOG, db)
    try:
        board = ggv.build_board(verified_person_id="PERS-AMANDA", db_path=db)
        check("ggv board ok", board.get("ok") is True)
        check("ggv intel strip", isinstance(board.get("intel_connective"), dict))
        check("ggv intel bound", board.get("intel_bound") == ic.BOUND)
        leads = board.get("leads") or []
        if leads:
            card = leads[0]
            check("ggv card has loop next", isinstance(card.get("loop_next_action"), dict))
            check(
                "ggv card intel",
                isinstance(card.get("intel_recommendation"), dict)
                or isinstance(
                    (card.get("loop_next_action") or {}).get("intel_recommendation"),
                    dict,
                ),
            )
            ir = card.get("intel_recommendation") or (
                card.get("loop_next_action") or {}
            ).get("intel_recommendation")
            if ir:
                check("ggv card no auto promote", ir.get("auto_promote") is False)
                check("ggv card no orphan", ir.get("orphan_dashboard") is False)
    finally:
        os.environ.pop("WOLF_INTEL_EVAL_DB", None)


def test_amg_day_loop_intel(td: Path) -> None:
    os.environ["WOLF_INTEL_EVAL_DB"] = str(_seed_fail_safe(td))
    db = td / "amg.sqlite"
    try:
        board = amg.build_board(verified_person_id="PERS-MATT", db_path=db)
        day = board.get("day_loop") or {}
        check("amg day loop present", isinstance(day, dict) and day.get("bound") == "beta-amg-day-safe")
        check("amg day next action", isinstance(day.get("day_next_action"), dict))
        check("amg intel strip", isinstance(day.get("intel_connective"), dict))
        check("amg intel bound", day.get("intel_bound") == ic.BOUND)
        nxt = day.get("day_next_action") or {}
        ir = day.get("intel_recommendation") or nxt.get("intel_recommendation") or {}
        check("amg changes work under fail-safe", ir.get("changes_work") is True or day.get("intel_connective", {}).get("changes_work") is True)
        check(
            "amg fail-safe in next",
            "fail-safe" in str(nxt.get("label") or "").lower()
            or "desk actions" in str(nxt.get("label") or "").lower()
            or ir.get("changes_work") is True,
        )
    finally:
        os.environ.pop("WOLF_INTEL_EVAL_DB", None)


def test_ledger_honesty() -> None:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger size 77", len(data) == 77)
    for cap in ("CAP-INTEL-01", "CAP-INTEL-02", "CAP-INTEL-03", "CAP-INTEL-04", "CAP-INTEL-05"):
        check(f"{cap} present", cap in data)
    check("CAP-INTEL-01 stays BUILT", data["CAP-INTEL-01"][0] == "BUILT")
    check("CAP-INTEL-05 stays SPECIFIED", data["CAP-INTEL-05"][0] == "SPECIFIED")
    check("no invent PROVEN on INTEL-01", data["CAP-INTEL-01"][0] != "PROVEN")
    check("no invent READY on INTEL-05", data["CAP-INTEL-05"][0] != "READY")


def test_wip_untouched() -> None:
    for rel in WIP:
        path = ROOT / rel
        check(f"wip exists {rel}", path.is_file())


def test_http_anon_403() -> None:
    ra._ENV_LOADED = True
    import inspect

    import serve_beta as sb

    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
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
            with urlopen(req, timeout=30) as resp:
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
        for path in (
            "/api/ggv/ops-pack",
            "/api/ggv/ops-pack/loop",
            "/api/amg/ops-pack",
            "/api/amg/ops-pack/day-loop",
            "/api/bzg/uma-blu/today",
            "/ggv-ops-pack",
            "/amg-ops-pack",
        ):
            st, _ = call("GET", path, None)
            check(f"anon GET {path} 403", st == 403, str(st))

        st, board = call("GET", "/api/ggv/ops-pack", MATT)
        check(
            "owner ggv board intel",
            st == 200
            and isinstance(board, dict)
            and isinstance(board.get("intel_connective"), dict)
            and board.get("intel_bound") == ic.BOUND,
            str(board)[:200] if isinstance(board, dict) else str(board),
        )
        st, day = call("GET", "/api/amg/ops-pack/day-loop", MATT)
        check(
            "owner amg day intel",
            st == 200
            and isinstance(day, dict)
            and isinstance(day.get("day_next_action"), dict)
            and day.get("intel_bound") == ic.BOUND,
            str(day)[:200] if isinstance(day, dict) else str(day),
        )
        st, today = call("GET", "/api/bzg/uma-blu/today", MATT)
        check(
            "owner uma today intel",
            st == 200
            and isinstance(today, dict)
            and isinstance(today.get("intel_connective"), dict)
            and today.get("intel_bound") == ic.BOUND,
            str(today)[:200] if isinstance(today, dict) else str(today),
        )

        for path in (
            "/api/ggv/ops-pack/auto-promote",
            "/api/ggv/ops-pack/auto-execute",
            "/api/amg/ops-pack/intel-execute",
            "/api/bzg/uma-blu/intel-promote",
        ):
            st, body = call("POST", path, MATT, {})
            check(
                f"refuse {path}",
                st == 405
                and isinstance(body, dict)
                and body.get("error") in ("promote_refused", "execute_refused"),
                str(body)[:180],
            )
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_sources() -> None:
    src = (SCRIPTS / "core" / "intel_connective.py").read_text(encoding="utf-8")
    check("bound in module", "beta-intel-connect-safe" in src)
    check("no ledger dump", "json.dump(" not in src)
    check("compose akr dm", "knowledge_resolution" in src and "provider_fail_safe" in src)
    ggv_src = (SCRIPTS / "core" / "ggv_ops_pack.py").read_text(encoding="utf-8")
    check("ggv wired", "intel_connective" in ggv_src and "attach_to_next_action" in ggv_src)
    amg_src = (SCRIPTS / "core" / "amg_ops_pack.py").read_text(encoding="utf-8")
    check("amg wired", "intel_connective" in amg_src and "day_next_action" in amg_src)
    uma_src = (SCRIPTS / "core" / "uma_ops_console.py").read_text(encoding="utf-8")
    check("bzg wired", "intel_connective" in uma_src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve import", "intel_connective" in serve)
    check("serve ggv refuse promote", "/api/ggv/ops-pack/auto-promote" in serve)
    check("serve amg refuse execute", "/api/amg/ops-pack/intel-execute" in serve)
    check("serve bzg refuse promote", "/api/bzg/uma-blu/intel-promote" in serve)
    page = (ROOT / "dashboards" / "ggv-ops-pack.html").read_text(encoding="utf-8")
    check("ggv page intel", "intel_recommendation" in page)
    amg_page = (ROOT / "dashboards" / "amg-ops-pack.html").read_text(encoding="utf-8")
    check("amg page next", "day_next_action" in amg_page)
    for rel in WIP:
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())


def main() -> int:
    td = _tmp()
    try:
        test_honesty_and_refuses()
        test_ggv_decision_memory_changes_work(td)
        test_provider_fail_safe_changes_work(td)
        test_bzg_attach_and_uma_today(td)
        test_ggv_board_intel(td)
        test_amg_day_loop_intel(td)
        test_ledger_honesty()
        test_wip_untouched()
        test_sources()
        test_http_anon_403()
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
