#!/usr/bin/env python3
"""CAP-INTEL-01 orchestration (Beta). No production writes. Not PROVEN."""
from __future__ import annotations

import ast
import inspect
import json
import os
import shutil
import sqlite3
import subprocess
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
os.environ.pop("WOLF_ALLOW_LIVE_DECISION_MEMORY", None)
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_ALLOW_LIVE_COMPLETION_REGISTER", None)

from core import audit as audit_mod  # noqa: E402
from core import decision_memory as dm  # noqa: E402
from core import intel_orchestration as intel  # noqa: E402
from core import knowledge_resolution as kr  # noqa: E402

PASS = 0
FAIL = 0

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
LIVE_RBAC = ROOT / "catalog" / "backups" / "decision-memory-owner-seed-rbac.sqlite"
AUDIT_SQL = SCRIPTS / "migrations" / "011_audit_evidence_spine.sql"
WORK_SQL = SCRIPTS / "migrations" / "012_work_items.sql"
MODULE_PATH = SCRIPTS / "core" / "intel_orchestration.py"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"

FORBIDDEN_STAGE = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)

REQUIRED = (
    "question",
    "status",
    "summary",
    "provenance",
    "next_human_action",
    "steps",
    "honesty",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_dir() -> Path:
    td = ROOT / "catalog" / "backups" / f"tmp-intel-orchestration-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    return td


def _setup(td: Path) -> tuple[dict, Path]:
    rbac_path = td / "rbac-fixture.sqlite"
    if rbac_path.exists():
        rbac_path.unlink()
    rbac_conn = sqlite3.connect(str(rbac_path))
    rbac_conn.row_factory = sqlite3.Row
    fixture = dm.install_owner_seed_rbac_fixture(rbac_conn)
    rbac_conn.close()

    audit_path = td / "audit-fixture.sqlite"
    if audit_path.exists():
        audit_path.unlink()
    audit_conn = audit_mod.db_connect(audit_path)
    audit_conn.executescript(AUDIT_SQL.read_text(encoding="utf-8"))
    audit_conn.commit()
    audit_conn.close()

    seed_db = td / "decision_memory.sqlite"
    if seed_db.exists():
        seed_db.unlink()
    seed_audit = td / "seed-audit.sqlite"
    if seed_audit.exists():
        seed_audit.unlink()
    ac = audit_mod.db_connect(seed_audit)
    ac.executescript(AUDIT_SQL.read_text(encoding="utf-8"))
    ac.commit()
    ac.close()
    dm.seed_owner_decisions(
        db_path=seed_db,
        rbac_db_path=rbac_path,
        audit_db_path=seed_audit,
        catalog_db_path=None,
    )
    ctx = {
        "person_id": fixture["person_id"],
        "rbac_db_path": rbac_path,
        "target_context": {},
    }
    return ctx, seed_db


def _actor(ctx: dict, db_path: Path) -> dict:
    return {"permission_context": ctx, "db_path": db_path}


def _empty_work_db(td: Path) -> Path:
    path = td / "work-items.sqlite"
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    conn.executescript(WORK_SQL.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    return path


def test_honesty_and_no_model() -> None:
    h = intel.honesty_flags()
    check("honesty.no_llm", h.get("llm_as_evidence") is False)
    check("honesty.no_cot", h.get("chain_of_thought") is False)
    check("honesty.no_jwt_claim", h.get("cloudflare_jwt_auth") is False)
    check("honesty.no_invented_authority", h.get("invented_authority") is False)
    check("honesty.not_proven", h.get("proven") is False)
    check("honesty.built", h.get("maturity") == "BUILT")
    src = MODULE_PATH.read_text(encoding="utf-8")
    check("module does not import wolf_intelligence", "wolf_intelligence" not in src)
    check("module has no llm client", "openai" not in src and "anthropic" not in src)
    tree = ast.parse(src)
    write_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("execute", "executemany", "commit") and any(
                isinstance(k, ast.keyword) and k.arg == "write" for k in node.keywords
            ):
                write_calls.append(node.func.attr)
    check("no write keyword calls", not write_calls)


def test_happy_and_not_found(ctx: dict, db: Path) -> None:
    actor = _actor(ctx, db)
    first = intel.orchestrate_institutional_question(
        "What is Wolf's ClickUp policy?",
        "Wolf system",
        actor_context=actor,
    )
    second = intel.orchestrate_institutional_question(
        "What is Wolf's ClickUp policy?",
        "Wolf system",
        actor_context=actor,
    )
    for key in REQUIRED:
        check(f"happy.has_{key}", key in first)
    check(
        "happy.OWNER_DECISION",
        first.get("status") == intel.OUTCOME_OWNER_DECISION,
        str(first.get("status")),
    )
    check("happy.next_NONE", first.get("next_human_action") == intel.ACTION_NONE)
    check("happy.summary_sentence", isinstance(first.get("summary"), str) and first["summary"].endswith("."))
    check("happy.provenance_list", isinstance(first.get("provenance"), list))
    check("happy.no_attempts", "attempts" not in first)
    check(
        "happy.no_cot_in_summary",
        "chain-of-thought" not in (first.get("summary") or ""),
    )
    check(
        "happy.honesty_cot_false",
        (first.get("honesty") or {}).get("chain_of_thought") is False,
    )
    phases = [s.get("phase") for s in first.get("steps") or []]
    for phase in ("DATA", "TOOLS", "REASONING", "SYNTHESIS", "HUMAN"):
        check(f"happy.step_{phase}", phase in phases)
    tools = [s.get("tool") for s in first.get("steps") or []]
    check("happy.tool_knowledge", "knowledge_resolution" in tools)
    check(
        "happy.deterministic",
        first.get("status") == second.get("status")
        and first.get("summary") == second.get("summary")
        and first.get("next_human_action") == second.get("next_human_action"),
    )

    missed = intel.orchestrate_institutional_question(
        "What is Uma Blu's morning close time?",
        "Habitat",
        actor_context=actor,
    )
    check(
        "not_found.status",
        missed.get("status") == intel.OUTCOME_NOT_FOUND,
        str(missed.get("status")),
    )
    check("not_found.next_NONE", missed.get("next_human_action") == intel.ACTION_NONE)
    check("not_found.no_attempts", "attempts" not in missed)


def test_conflicted_and_blocker(ctx: dict, db: Path) -> None:
    actor = _actor(ctx, db)
    original = kr.resolve_question

    def _conflicted(*_a, **_k):
        return {
            "status": kr.STATUS_CONFLICTED,
            "answer": None,
            "provenance": [
                {"authority": "AUTHORISED_SOURCE", "source_id": "headline_case"}
            ],
            "attempts": ["do-not-leak-rationale"],
            "conflict": {"sides": ["lowercase", "uppercase"]},
        }

    kr.resolve_question = _conflicted
    try:
        hit = intel.orchestrate_institutional_question(
            "Is the Habitat headline rule lowercase or uppercase?",
            "Habitat",
            actor_context=actor,
        )
    finally:
        kr.resolve_question = original
    check(
        "conflicted.status",
        hit.get("status") == intel.OUTCOME_CONFLICTED,
        str(hit.get("status")),
    )
    check(
        "conflicted.review",
        hit.get("next_human_action") == intel.ACTION_REVIEW_CONFLICT,
    )
    check("conflicted.provenance_label", "headline_case" in (hit.get("provenance") or []))
    dumped = json.dumps(hit)
    check("conflicted.hides_attempts", "do-not-leak-rationale" not in dumped)
    check(
        "conflicted.no_sides_in_summary",
        "lowercase" not in (hit.get("summary") or ""),
    )

    blocked = intel.orchestrate_institutional_question(
        "What is Wolf's ClickUp policy?",
        "Wolf system",
        actor_context={**actor, "kind": "policy_required"},
    )
    check(
        "blocker.NEEDS_POLICY",
        blocked.get("next_human_action") == intel.ACTION_NEEDS_POLICY,
        str(blocked.get("next_human_action")),
    )
    check("blocker.tool_ran", "blocker_explain" in (blocked.get("tools") or []))

    if not LIVE_RBAC.exists():
        check("conflicted live fixture unavailable", True, "rbac backup missing")
        return
    live_actor = {
        "permission_context": {
            "person_id": "PERS-DM-OWNER-SEED",
            "rbac_db_path": LIVE_RBAC,
            "target_context": {},
        }
    }
    live = intel.orchestrate_institutional_question(
        "Is the Habitat headline rule lowercase or uppercase?",
        "Habitat",
        actor_context=live_actor,
    )
    check(
        "conflicted live fixture",
        live.get("status") == intel.OUTCOME_CONFLICTED
        and live.get("next_human_action") == intel.ACTION_REVIEW_CONFLICT,
        str(live.get("status")),
    )


def test_work_item_fail_closed(td: Path, ctx: dict, db: Path) -> None:
    actor = _actor(ctx, db)
    actor["work_db_path"] = str(_empty_work_db(td))
    try:
        intel.orchestrate_institutional_question(
            "What is Wolf's ClickUp policy?",
            "Wolf system",
            actor_context=actor,
            work_item_id="WI-missing-intel-01",
        )
        check("missing work item raises", False, "returned a dict")
    except intel.IntelOrchestrationError as exc:
        check("missing work item raises", exc.code == "work_item_missing", exc.code)


def test_surface_wip_and_api(ctx: dict, db: Path) -> None:
    html = (ROOT / "dashboards" / "progress.html").read_text(encoding="utf-8")
    check("progress shows summary slot", 'id="intel-summary"' in html)
    check("progress shows status slot", 'id="intel-status"' in html)
    check("progress shows provenance slot", 'id="intel-prov"' in html)
    check("progress shows next_human_action", "next_human_action" in html)
    check("progress has no hard-coded 25.3", "25.3" not in html)
    credits = (ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md").read_text(encoding="utf-8")
    check("credits table still SPECIFIED 0.05", "| SPECIFIED | 0.05 |" in credits)
    check("credits table still BUILT 0.25", "| BUILT | 0.25 |" in credits)
    ledger = json.loads(
        (ROOT / "state" / "model-c-baseline-assessments.json").read_text(encoding="utf-8")
    )
    row = ledger.get("CAP-INTEL-01") or []
    check("ledger CAP-INTEL-01 BUILT", row and row[0] == "BUILT", str(row[:1]))
    check("ledger not PROVEN", row and row[0] != "PROVEN")

    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for path in FORBIDDEN_STAGE:
        check(f"WIP not staged {Path(path).name}", path not in staged, str(staged))

    import serve_beta as sb
    from core import request_auth as ra

    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    ra._ENV_LOADED = True
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
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:

        def call(path: str, subject: str | None):
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method="GET")
            try:
                with urlopen(req, timeout=15) as resp:
                    return resp.status, json.loads(resp.read().decode())
            except HTTPError as exc:
                body = exc.read().decode()
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = {"raw": body}
                return exc.code, data

        q = "question=What%20is%20Wolf%27s%20ClickUp%20policy%3F&scope=Wolf%20system"
        st, _anon = call(f"/api/intel/orchestrate?{q}", None)
        check("anon orchestrate 403", st == 403, str(st))
        st_staff, _staff = call(f"/api/intel/orchestrate?{q}", STAFF)
        check("staff orchestrate 403", st_staff == 403, str(st_staff))
        st_ok, data = call(f"/api/intel/orchestrate?{q}", MATT)
        check("owner orchestrate 200", st_ok == 200 and data.get("ok") is True, str(data)[:240])
        for key in ("summary", "status", "provenance", "next_human_action"):
            check(f"owner payload {key}", key in data, str(data)[:200])
        check(
            "owner honesty no jwt claim",
            (data.get("honesty") or {}).get("cloudflare_jwt_auth") is False,
        )
        check("owner payload no attempts", "attempts" not in data)
    finally:
        httpd.shutdown()


def main() -> int:
    td = _tmp_dir()
    try:
        test_honesty_and_no_model()
        ctx, db = _setup(td)
        test_happy_and_not_found(ctx, db)
        test_conflicted_and_blocker(ctx, db)
        test_work_item_fail_closed(td, ctx, db)
        test_surface_wip_and_api(ctx, db)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
