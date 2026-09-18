#!/usr/bin/env python3
"""Tests for Owner knowledge resolution path (Beta).

Compose Decision Memory + AKR. Temp DB copies for unit tests.
One live registry read-only prove. No source writes. No Model C ledger edits.
"""
from __future__ import annotations

import ast
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_DECISION_MEMORY", None)
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import audit as audit_mod  # noqa: E402
from core import decision_memory as dm  # noqa: E402
from core import knowledge_resolution as kr  # noqa: E402

PASS = 0
FAIL = 0

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
LIVE_DECISION_DB = ROOT / "catalog" / "decision_memory.sqlite"
LIVE_RBAC = ROOT / "catalog" / "backups" / "decision-memory-owner-seed-rbac.sqlite"
AUDIT_SQL = SCRIPTS / "migrations" / "011_audit_evidence_spine.sql"
MODULE_PATH = SCRIPTS / "core" / "knowledge_resolution.py"
CREDITS_DOC = "docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_dir() -> Path:
    td = ROOT / "catalog" / "backups" / f"tmp-knowledge-resolution-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    return td


def _setup_rbac_and_audit(td: Path) -> tuple[dict, Path, sqlite3.Connection]:
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

    ctx = {
        "person_id": fixture["person_id"],
        "rbac_db_path": rbac_path,
        "audit_conn": audit_conn,
        "target_context": {},
    }
    return ctx, rbac_path, audit_conn


def _seed_temp_decisions(td: Path, ctx: dict, rbac_path: Path) -> Path:
    seed_db = td / "decision_memory.sqlite"
    if seed_db.exists():
        seed_db.unlink()
    audit_path = td / "seed-audit.sqlite"
    if audit_path.exists():
        audit_path.unlink()
    ac = audit_mod.db_connect(audit_path)
    ac.executescript(AUDIT_SQL.read_text(encoding="utf-8"))
    ac.commit()
    ac.close()
    dm.seed_owner_decisions(
        db_path=seed_db,
        rbac_db_path=rbac_path,
        audit_db_path=audit_path,
        catalog_db_path=LIVE_CATALOG if LIVE_CATALOG.exists() else None,
    )
    return seed_db


def _actor(ctx: dict, db_path: Path | None = None, **extra: object) -> dict:
    out: dict = {"permission_context": ctx, **extra}
    if db_path is not None:
        out["db_path"] = db_path
    return out


def test_honesty_and_no_writes() -> None:
    h = kr.honesty_flags()
    check("honesty.decides_false", h.get("decides") is False)
    check("honesty.replaces_audit_false", h.get("replaces_audit") is False)
    check("honesty.no_agent", h.get("agent") is False)
    check("honesty.no_llm", h.get("llm") is False)

    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    write_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            n = node.name.lower()
            if any(
                w in n
                for w in (
                    "write",
                    "record",
                    "insert",
                    "update",
                    "delete",
                    "save",
                    "mutate",
                )
            ):
                write_names.append(node.name)
    check("security.no_write_functions", write_names == [], str(write_names))
    check("security.no_openai", "openai" not in src.lower())
    check("security.no_requests", "import requests" not in src)


def test_missing_scope_refused(db: Path, ctx: dict) -> None:
    raised = False
    try:
        kr.resolve_question(
            "What is Wolf's ClickUp policy?",
            None,
            actor_context=_actor(ctx, db),
        )
    except kr.KnowledgeResolutionError:
        raised = True
    # Module returns NOT_FOUND with scope refuse (or raises). Either is refuse.
    if raised:
        check("scope.missing_raises", True)
    else:
        r = kr.resolve_question(
            "What is Wolf's ClickUp policy?",
            "",
            actor_context=_actor(ctx, db),
        )
        check(
            "scope.missing_refused",
            r.get("status") == kr.STATUS_NOT_FOUND
            and "scope_refused" in str(r.get("confidence_basis")),
            str(r.get("status")),
        )


def test_no_actor_decision_fail_closed(db: Path) -> None:
    r = kr.resolve_question(
        "What is Wolf's ClickUp policy?",
        "Wolf system",
        actor_context=None,
    )
    check(
        "security.no_actor_inaccessible",
        r.get("status") == kr.STATUS_INACCESSIBLE,
        str(r.get("status")),
    )
    check("security.no_actor_escalate", r.get("escalate") is True)
    check(
        "security.no_actor_no_guess",
        r.get("answer") is None,
        str(r.get("answer"))[:80],
    )


def test_path_outside_allowlist_refused(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What font does Habitat use?",
        "Habitat",
        actor_context=_actor(
            ctx, db, path="/tmp/not-allowlisted-secret.pdf"
        ),
    )
    check(
        "security.outside_path_refused",
        r.get("status") == kr.STATUS_INACCESSIBLE,
        str(r.get("status")),
    )
    check(
        "security.outside_path_attempt",
        any("outside" in str(a.get("detail", "")).lower() for a in r.get("attempts") or []),
    )


def test_registry_override_refused(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What font does Habitat use?",
        "Habitat",
        actor_context=_actor(
            ctx, db, sources_registry="/tmp/evil-registry.json"
        ),
    )
    check(
        "security.registry_override_refused",
        r.get("status") == kr.STATUS_INACCESSIBLE,
        str(r.get("status")),
    )


def test_clickup_owner_decision(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What is Wolf's ClickUp policy?",
        "Wolf system",
        actor_context=_actor(ctx, db),
    )
    check(
        "clickup.status_OWNER_DECISION",
        r.get("status") == kr.STATUS_OWNER_DECISION,
        str(r.get("status")),
    )
    check("clickup.escalate_false", r.get("escalate") is False)
    ans = str(r.get("answer") or "")
    check("clickup.mentions_removed", "removed" in ans.lower() or "ClickUp" in ans)
    check(
        "clickup.authority",
        r.get("authority") == kr.AUTHORITY_OWNER_DECISION,
        str(r.get("authority")),
    )


def test_clickup_uma_scope_no_bleed(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What is Wolf's ClickUp policy?",
        "Uma Blu",
        actor_context=_actor(ctx, db),
    )
    check(
        "clickup.uma_no_bleed_status",
        r.get("status") in (kr.STATUS_NOT_FOUND, kr.STATUS_INACCESSIBLE),
        str(r.get("status")),
    )
    ans = str(r.get("answer") or "")
    check(
        "clickup.uma_not_wolf_answer",
        "target architecture" not in ans.lower(),
        ans[:120],
    )


def test_system_credits(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What are the current SYSTEM maturity credits?",
        "Wolf system",
        actor_context=_actor(ctx, db),
    )
    if r.get("status") == kr.STATUS_CONFLICTED:
        print("EXIT:1 credits file and Owner decision disagree")
        print("conflict:", r.get("conflict"))
        check("credits.conflicted_mismatch", False, str(r.get("conflict")))
        return
    check(
        "credits.status_OWNER_DECISION",
        r.get("status") == kr.STATUS_OWNER_DECISION,
        str(r.get("status")),
    )
    prov_blob = str(r.get("provenance") or [])
    check(
        "credits.provenance_cites_file",
        CREDITS_DOC in prov_blob,
        prov_blob[:200],
    )
    ans = str(r.get("answer") or "")
    check("credits.has_ABSENT", "ABSENT" in ans and "0.00" in ans)
    check("credits.has_READY", "READY" in ans and "1.00" in ans)
    check("credits.escalate_false", r.get("escalate") is False)


def test_crm_cutover(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "Is Habitat CRM cut over?",
        "Habitat",
        actor_context=_actor(ctx, db),
    )
    check(
        "crm.status_OWNER_DECISION",
        r.get("status") == kr.STATUS_OWNER_DECISION,
        str(r.get("status")),
    )
    ans = str(r.get("answer") or "").lower()
    check("crm.cutover_off", "cutover" in ans and "off" in ans, ans[:160])
    check("crm.escalate_false", r.get("escalate") is False)


def test_klaviyo_receipt(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What does Klaviyo created mean for Habitat lead receipt?",
        "Habitat",
        actor_context=_actor(ctx, db),
    )
    check(
        "klaviyo.status_OWNER_DECISION",
        r.get("status") == kr.STATUS_OWNER_DECISION,
        str(r.get("status")),
    )
    ans = str(r.get("answer") or "").lower()
    check(
        "klaviyo.receipt_not_form_submit",
        "receipt" in ans or "received_by_klaviyo" in ans or "profile.created" in ans,
        ans[:160],
    )
    check(
        "klaviyo.not_form_submit_claim",
        "form-submit" in ans or "does not claim" in ans,
        ans[:160],
    )


def test_uma_morning_close_not_found(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What is Uma Blu's morning close time?",
        "Habitat",
        actor_context=_actor(ctx, db),
    )
    check(
        "uma_close.status_NOT_FOUND",
        r.get("status") == kr.STATUS_NOT_FOUND,
        str(r.get("status")),
    )
    check("uma_close.escalate_false", r.get("escalate") is False)
    check("uma_close.attempts_recorded", len(r.get("attempts") or []) >= 3)


def test_empty_canonical_not_unknown(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What font does Habitat use?",
        "Habitat",
        actor_context=_actor(
            ctx,
            db,
            canonical={"fields": {"brand_font": ""}},
        ),
    )
    # Live AKR may still find Manrope — then answer kept, not UNKNOWN.
    check(
        "empty_canon.not_UNKNOWN",
        r.get("status") != kr.STATUS_UNKNOWN,
        str(r.get("status")),
    )
    if r.get("authority") == kr.AUTHORITY_AUTHORISED_SOURCE:
        check("empty_canon.akr_kept_fact", "Manrope" in str(r.get("answer")))
    elif r.get("status") == kr.STATUS_NOT_CANONICAL:
        check("empty_canon.empty_finding", r.get("escalate") is False)


def test_live_habitat_font() -> None:
    """One live registry read-only prove. No writes."""
    if not LIVE_DECISION_DB.exists() or not LIVE_RBAC.exists():
        check("live.font.skipped_missing_seed", False, "decision db or rbac missing")
        return
    ctx = {
        "person_id": "PERS-DM-OWNER-SEED",
        "rbac_db_path": LIVE_RBAC,
        "target_context": {},
    }
    r = kr.resolve_question(
        "What font does Habitat use?",
        "Habitat",
        actor_context={"permission_context": ctx},
    )
    if r.get("status") == kr.STATUS_INACCESSIBLE:
        check(
            "live.font.inaccessible_reported",
            True,
            "NAS/source inaccessible — not stubbed",
        )
        check("live.font.escalate", r.get("escalate") is True)
        return
    ans = str(r.get("answer") or "")
    check("live.font.Manrope", "Manrope" in ans, ans[:120])
    check(
        "live.font.not_Inter_as_brand",
        "Inter" not in ans.split("Manrope")[0] if "Manrope" in ans else "Inter" not in ans,
        ans[:120],
    )
    # Stronger: brand answer value is Manrope, not Inter.
    val = r.get("answer")
    if isinstance(val, dict):
        brand_val = str(val.get("value") or val.get("brand_font") or "")
    else:
        brand_val = str(val or "")
    check("live.font.brand_value_Manrope", brand_val.strip() == "Manrope", brand_val)
    check(
        "live.font.authority_AUTHORISED_SOURCE",
        r.get("authority") == kr.AUTHORITY_AUTHORISED_SOURCE,
        str(r.get("authority")),
    )


def test_live_headline_conflicted() -> None:
    if not LIVE_RBAC.exists():
        check("live.headline.skipped", False, "rbac missing")
        return
    ctx = {
        "person_id": "PERS-DM-OWNER-SEED",
        "rbac_db_path": LIVE_RBAC,
        "target_context": {},
    }
    r = kr.resolve_question(
        "Is the Habitat headline rule lowercase or uppercase?",
        "Habitat",
        actor_context={"permission_context": ctx},
    )
    check(
        "live.headline.CONFLICTED",
        r.get("status") == kr.STATUS_CONFLICTED,
        str(r.get("status")),
    )
    conflict = r.get("conflict") or {}
    sides = conflict.get("sides") or []
    blob = str(sides).lower()
    check("live.headline.both_sides", "lowercase" in blob and "uppercase" in blob, blob[:200])
    check("live.headline.escalate_true", r.get("escalate") is True)


def test_live_prove_seed_questions() -> None:
    """Against real Beta Decision Memory seed."""
    if not LIVE_DECISION_DB.exists() or not LIVE_RBAC.exists():
        check("live.seed.missing", False)
        return
    ctx = {
        "person_id": "PERS-DM-OWNER-SEED",
        "rbac_db_path": LIVE_RBAC,
        "target_context": {},
    }
    actor = {"permission_context": ctx}

    r1 = kr.resolve_question(
        "What is Wolf's ClickUp policy?", "Wolf system", actor_context=actor
    )
    check("live.clickup.OWNER_DECISION", r1.get("status") == kr.STATUS_OWNER_DECISION)

    r2 = kr.resolve_question(
        "What are the current SYSTEM maturity credits?",
        "Wolf system",
        actor_context=actor,
    )
    if r2.get("status") == kr.STATUS_CONFLICTED:
        check("live.credits.CONFLICTED_mismatch", False, str(r2.get("conflict")))
    else:
        check("live.credits.OWNER_DECISION", r2.get("status") == kr.STATUS_OWNER_DECISION)
        check(
            "live.credits.cites_doc",
            CREDITS_DOC in str(r2.get("provenance")),
        )

    r3 = kr.resolve_question(
        "Is Habitat CRM cut over?", "Habitat", actor_context=actor
    )
    check("live.crm.OWNER_DECISION", r3.get("status") == kr.STATUS_OWNER_DECISION)
    check("live.crm.off", "off" in str(r3.get("answer") or "").lower())

    r4 = kr.resolve_question(
        "What does Klaviyo created mean for Habitat lead receipt?",
        "Habitat",
        actor_context=actor,
    )
    check("live.klaviyo.OWNER_DECISION", r4.get("status") == kr.STATUS_OWNER_DECISION)

    r5 = kr.resolve_question(
        "What is Uma Blu's morning close time?",
        "Habitat",
        actor_context=actor,
    )
    check("live.uma_close.NOT_FOUND", r5.get("status") == kr.STATUS_NOT_FOUND)
    check("live.uma_close.escalate_false", r5.get("escalate") is False)

    r6 = kr.resolve_question(
        "What is Wolf's ClickUp policy?", "Uma Blu", actor_context=actor
    )
    check(
        "live.clickup.uma_no_bleed",
        r6.get("status") == kr.STATUS_NOT_FOUND
        or "target architecture" not in str(r6.get("answer") or "").lower(),
        str(r6.get("status")),
    )


def test_uma_scope_no_habitat_font(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What font does Habitat use?",
        "Uma Blu",
        actor_context=_actor(ctx, db),
    )
    check(
        "uma.font_refused_or_miss",
        r.get("status") == kr.STATUS_NOT_FOUND,
        str(r.get("status")),
    )
    check("uma.font_no_Manrope", "Manrope" not in str(r.get("answer") or ""))


def test_result_shape(db: Path, ctx: dict) -> None:
    r = kr.resolve_question(
        "What is Wolf's ClickUp policy?",
        "Wolf system",
        actor_context=_actor(ctx, db),
    )
    for key in (
        "answer",
        "status",
        "authority",
        "provenance",
        "confidence_basis",
        "conflict",
        "attempts",
    ):
        check(f"shape.has_{key}", key in r)


def main() -> int:
    td = _tmp_dir()
    try:
        test_honesty_and_no_writes()

        ctx, rbac_path, audit_conn = _setup_rbac_and_audit(td)
        db = _seed_temp_decisions(td, ctx, rbac_path)

        test_missing_scope_refused(db, ctx)
        test_no_actor_decision_fail_closed(db)
        test_path_outside_allowlist_refused(db, ctx)
        test_registry_override_refused(db, ctx)
        test_clickup_owner_decision(db, ctx)
        test_clickup_uma_scope_no_bleed(db, ctx)
        test_system_credits(db, ctx)
        test_crm_cutover(db, ctx)
        test_klaviyo_receipt(db, ctx)
        test_uma_morning_close_not_found(db, ctx)
        test_empty_canonical_not_unknown(db, ctx)
        test_uma_scope_no_habitat_font(db, ctx)
        test_result_shape(db, ctx)

        # Live prove (read-only)
        test_live_habitat_font()
        test_live_headline_conflicted()
        test_live_prove_seed_questions()

        audit_conn.close()
    finally:
        # Best-effort cleanup of temp dir contents (keep parent backups tree).
        try:
            for p in td.iterdir():
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass

    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
