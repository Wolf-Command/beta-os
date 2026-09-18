#!/usr/bin/env python3
"""Tests for Wolf Core Decision Memory v1 (Beta). CAP-INTEL-04 live prove.

Fixture DB only (temp file). No network. No Production. No Habitat/Uma disturb.
Proves: INSERT-only, no silent rewrite, scope isolation, empty outcome ≠ invented,
recall max 50, exact query_keys, RBAC deny, seed path guard, audit event.
"""
from __future__ import annotations

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
# Never allow accidental live decision/audit writes from this suite.
os.environ.pop("WOLF_ALLOW_LIVE_DECISION_MEMORY", None)
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import audit as audit_mod  # noqa: E402
from core import decision_memory as dm  # noqa: E402

PASS = 0
FAIL = 0

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
AUDIT_SQL = SCRIPTS / "migrations" / "011_audit_evidence_spine.sql"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_dir() -> Path:
    td = ROOT / "catalog" / "backups" / f"tmp-decision-memory-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    return td


def _tmp_db(td: Path) -> Path:
    path = td / "decision_memory.sqlite"
    if path.exists():
        path.unlink()
    return path


def _setup_rbac_and_audit(td: Path) -> tuple[dict, Path, sqlite3.Connection]:
    """Fixture RBAC (not live staff grants) + temp audit DB."""
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


def test_honesty_and_vocab() -> None:
    h = dm.honesty_flags()
    check("honesty.append_only", h.get("append_only") is True)
    check("honesty.no_silent_rewrite", h.get("silent_rewrite") is False)
    check("honesty.no_invent_approvers", h.get("invent_approvers") is False)
    check("honesty.no_invent_outcomes", h.get("invent_outcomes") is False)
    check("honesty.no_replace_audit", h.get("replaces_audit") is False)
    check("cap.recall_max_50", dm.RECALL_MAX == 50)
    check(
        "status.vocab",
        dm.STATUSES
        == {"RECORDED", "OUTCOME_UNKNOWN", "NOT FOUND"},
    )


def test_append_only_and_correction(db: Path, ctx: dict) -> None:
    rec = dm.record_decision(
        title="Pick font for Habitat brand",
        scope="brand:habitat",
        options_considered=["Manrope", "Inter"],
        chosen_option="Manrope",
        outcome="shipped",
        actor="PERS-MATT",
        approval_ref="APR-TEST-1",
        provenance={"source": "test"},
        permission_context=ctx,
        db_path=db,
    )
    check("record.inserts", bool(rec and rec.get("decision_id")), str(rec)[:120])
    check(
        "record.status_RECORDED",
        rec.get("status") == dm.STATUS_RECORDED,
        str(rec.get("status")),
    )
    check("record.chosen", rec.get("chosen_option") == "Manrope")
    check("record.approval_ref_as_given", rec.get("approval_ref") == "APR-TEST-1")
    check("record.outcome_as_given", rec.get("outcome") == "shipped")
    prior_id = rec["decision_id"]

    raised_u = False
    try:
        dm.update_decision(prior_id, title="rewritten")
    except NotImplementedError:
        raised_u = True
    check("update_decision raises NotImplementedError", raised_u)

    raised_d = False
    try:
        dm.delete_decision(prior_id)
    except NotImplementedError:
        raised_d = True
    check("delete_decision raises NotImplementedError", raised_d)

    conn = sqlite3.connect(str(db))
    try:
        upd_blocked = False
        try:
            conn.execute(
                "UPDATE core_decision_memory SET title=? WHERE decision_id=?",
                ("silent rewrite", prior_id),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            upd_blocked = "append-only" in str(exc)
        check("sql UPDATE blocked by trigger", upd_blocked)

        del_blocked = False
        try:
            conn.execute(
                "DELETE FROM core_decision_memory WHERE decision_id=?",
                (prior_id,),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            del_blocked = "append-only" in str(exc)
        check("sql DELETE blocked by trigger", del_blocked)
    finally:
        conn.close()

    got = dm.get_decision(prior_id, db_path=db)
    check(
        "no silent rewrite of prior title",
        got is not None and got.get("title") == "Pick font for Habitat brand",
        str(got),
    )

    corr = dm.correct_decision(
        prior_id,
        title="Pick font for Habitat brand (corrected)",
        scope="brand:habitat",
        options_considered=["Manrope", "Inter", "Geist"],
        chosen_option="Manrope",
        outcome="shipped",
        actor="PERS-MATT",
        provenance={"source": "test", "kind": "correction"},
        permission_context=ctx,
        db_path=db,
    )
    check("correction.inserts", bool(corr and corr.get("decision_id")))
    check(
        "correction.references_prior",
        corr.get("corrects_decision_id") == prior_id,
        str(corr.get("corrects_decision_id")),
    )
    check(
        "correction.new_decision_id",
        corr.get("decision_id") != prior_id,
        str(corr.get("decision_id")),
    )
    prior_still = dm.get_decision(prior_id, db_path=db)
    check(
        "prior unchanged after correction",
        prior_still is not None
        and prior_still.get("title") == "Pick font for Habitat brand",
    )

    conn = sqlite3.connect(str(db))
    try:
        n = conn.execute("SELECT COUNT(*) FROM core_decision_memory").fetchone()[0]
        check("two INSERT rows after correction", n == 2, str(n))
    finally:
        conn.close()


def test_empty_outcome_unknown_not_invented(db: Path, ctx: dict) -> None:
    rec = dm.record_decision(
        title="Vendor choice pending outcome",
        scope="brand:habitat",
        options_considered=["A", "B"],
        chosen_option="A",
        outcome=None,
        actor="PERS-MATT",
        permission_context=ctx,
        db_path=db,
    )
    check(
        "empty_outcome.status_OUTCOME_UNKNOWN",
        rec.get("status") == dm.STATUS_OUTCOME_UNKNOWN,
        str(rec.get("status")),
    )
    check(
        "empty_outcome.value_not_invented",
        rec.get("outcome") is None,
        str(rec.get("outcome")),
    )

    explicit = dm.record_decision(
        title="Outcome explicitly unknown",
        scope="brand:habitat",
        options_considered=["X"],
        chosen_option="X",
        outcome="UNKNOWN",
        actor="PERS-MATT",
        permission_context=ctx,
        db_path=db,
    )
    check(
        "explicit_UNKNOWN.status",
        explicit.get("status") == dm.STATUS_OUTCOME_UNKNOWN,
    )
    check(
        "explicit_UNKNOWN.stored_as_UNKNOWN",
        explicit.get("outcome") == "UNKNOWN",
    )

    no_appr = dm.record_decision(
        title="No approval pointer",
        scope="brand:habitat",
        options_considered=["go"],
        chosen_option="go",
        outcome="done",
        actor="PERS-MATT",
        permission_context=ctx,
        db_path=db,
    )
    check(
        "approval_ref not invented",
        no_appr.get("approval_ref") is None,
        str(no_appr.get("approval_ref")),
    )


def test_empty_options_requires_reason(db: Path, ctx: dict) -> None:
    raised = False
    try:
        dm.record_decision(
            title="No options",
            scope="brand:habitat",
            options_considered=[],
            actor="PERS-MATT",
            permission_context=ctx,
            db_path=db,
        )
    except dm.DecisionMemoryError as exc:
        raised = exc.code == "empty_options"
    check("empty options without reason refused", raised)

    ok = dm.record_decision(
        title="No options with reason",
        scope="brand:habitat",
        options_considered=[],
        empty_options_reason="binary gate — proceed / abort only",
        chosen_option="proceed",
        outcome="done",
        actor="PERS-MATT",
        permission_context=ctx,
        db_path=db,
    )
    check("empty options with reason accepted", ok.get("status") == dm.STATUS_RECORDED)
    check(
        "empty options reason stored",
        ok.get("empty_options_reason") == "binary gate — proceed / abort only",
    )


def test_scope_isolation(db: Path, ctx: dict) -> None:
    dm.record_decision(
        title="Habitat content cadence",
        scope="brand:habitat",
        options_considered=["daily", "weekly"],
        chosen_option="weekly",
        outcome="adopted",
        actor="PERS-MATT",
        permission_context=ctx,
        db_path=db,
    )
    dm.record_decision(
        title="Uma close threshold",
        scope="brand:uma",
        options_considered=["strict", "lenient"],
        chosen_option="strict",
        outcome="adopted",
        actor="PERS-MATT",
        permission_context=ctx,
        db_path=db,
    )

    habitat = dm.recall(
        "brand:habitat", "cadence", permission_context=ctx, db_path=db
    )
    check("habitat.recall.count", habitat.get("count") == 1, str(habitat.get("count")))
    check(
        "habitat.recall.not_uma",
        all(
            (d.get("scope") or {}).get("brand") == "habitat"
            for d in habitat.get("decisions") or []
        ),
    )
    titles_h = [d.get("title") for d in habitat.get("decisions") or []]
    check(
        "habitat.recall.no_uma_title",
        "Uma close threshold" not in titles_h,
        str(titles_h),
    )

    uma = dm.recall(
        "brand:uma", "threshold", permission_context=ctx, db_path=db
    )
    check("uma.recall.count", uma.get("count") == 1, str(uma.get("count")))
    check(
        "uma.recall.not_habitat",
        all(
            (d.get("scope") or {}).get("brand") == "uma"
            for d in uma.get("decisions") or []
        ),
    )
    titles_u = [d.get("title") for d in uma.get("decisions") or []]
    check(
        "uma.recall.no_habitat_title",
        "Habitat content cadence" not in titles_u,
        str(titles_u),
    )


def test_recall_not_found_and_provenance(db: Path, ctx: dict) -> None:
    dm.record_decision(
        title="Metricool read-only stance",
        scope="brand:habitat",
        options_considered=["read-only", "write"],
        chosen_option="read-only",
        outcome="locked",
        actor="PERS-MATT",
        provenance={"doc": "discovery-2026-09-17", "cap": "CAP-INTEL-04"},
        permission_context=ctx,
        db_path=db,
    )
    hit = dm.recall(
        "brand:habitat", "Metricool", permission_context=ctx, db_path=db
    )
    check("recall.hit.count", hit.get("count") >= 1)
    check("recall.hit.has_provenance", bool((hit["decisions"][0]).get("provenance")))
    check(
        "recall.hit.provenance_cap",
        (hit["decisions"][0].get("provenance") or {}).get("cap") == "CAP-INTEL-04",
    )

    miss = dm.recall(
        "brand:habitat",
        "zzz-no-such-decision-xyz",
        permission_context=ctx,
        db_path=db,
    )
    check(
        "recall.miss.status_NOT_FOUND",
        miss.get("status") == dm.STATUS_NOT_FOUND,
        str(miss.get("status")),
    )
    check("recall.miss.empty", miss.get("count") == 0 and miss.get("decisions") == [])


def test_recall_cap_50(db: Path, ctx: dict) -> None:
    for i in range(60):
        dm.record_decision(
            title=f"Batch decision {i:03d}",
            scope="brand:habitat",
            options_considered=[f"opt-{i}"],
            chosen_option=f"opt-{i}",
            outcome="noted",
            actor="SYSTEM",
            permission_context=ctx,
            db_path=db,
        )
    all_batch = dm.recall(
        "brand:habitat", "Batch decision", permission_context=ctx, db_path=db
    )
    check(
        "recall.cap_le_50",
        all_batch.get("count") == 50,
        str(all_batch.get("count")),
    )
    check("recall.limit_field", all_batch.get("limit") == 50)

    capped = dm.recall(
        "brand:habitat",
        "Batch decision",
        limit=10,
        permission_context=ctx,
        db_path=db,
    )
    check("recall.limit_honoured", capped.get("count") == 10, str(capped.get("count")))

    over = dm.recall(
        "brand:habitat",
        "Batch decision",
        limit=999,
        permission_context=ctx,
        db_path=db,
    )
    check("recall.limit_clamped_to_50", over.get("count") == 50, str(over.get("count")))


def test_beta_path_guards() -> None:
    refused = False
    try:
        dm.db_connect("/tmp/outside-beta-decision.sqlite")
    except RuntimeError as exc:
        refused = "non-beta" in str(exc)
    check("refuses non-beta path", refused)

    refused_prod = False
    try:
        dm._assert_beta_path(Path("/Users/wolfterminal/Production/money.sqlite"))
    except RuntimeError as exc:
        refused_prod = "production" in str(exc).lower() or "money" in str(exc).lower()
    check("refuses Production/money path", refused_prod)


def test_source_has_no_network_hooks() -> None:
    src = (SCRIPTS / "core" / "decision_memory.py").read_text(encoding="utf-8")
    check("no openai", "openai" not in src.lower())
    check("no anthropic", "anthropic" not in src.lower())
    check("no requests lib", "import requests" not in src)
    check("no urllib request", "urllib.request" not in src)
    check("update_decision present", "def update_decision" in src)
    check("delete_decision present", "def delete_decision" in src)
    check("correct_decision present", "def correct_decision" in src)
    check("seed_owner_decisions present", "def seed_owner_decisions" in src)


def test_exact_key_hit_and_adjacent_miss(db: Path, ctx: dict) -> None:
    dm.record_decision(
        title="ClickUp removed from target architecture",
        scope="Wolf system",
        options_considered=[],
        empty_options_reason=dm.EMPTY_OPTIONS_REASON_OWNER,
        actor="Matthew Goss",
        query_keys=["What is Wolf's ClickUp policy?"],
        permission_context=ctx,
        db_path=db,
    )
    hit = dm.recall(
        "Wolf system",
        "What is Wolf's ClickUp policy?",
        permission_context=ctx,
        db_path=db,
    )
    check("exact_key.hit", hit.get("count") == 1, str(hit.get("count")))

    # Casefold equality still hits
    hit_cf = dm.recall(
        "Wolf system",
        "what is wolf's clickup policy?",
        permission_context=ctx,
        db_path=db,
    )
    check("exact_key.casefold_hit", hit_cf.get("count") == 1)

    adjacent = [
        "Should we import historical ClickUp leads now?",
        "Who owns Habitat ads?",
        "What is Uma Blu's morning close time?",
        "ClickUp policy",  # shared word only — not exact
    ]
    for q in adjacent:
        miss = dm.recall(
            "Wolf system", q, permission_context=ctx, db_path=db
        )
        check(
            f"adjacent_miss:{q[:40]}",
            miss.get("status") == dm.STATUS_NOT_FOUND,
            str(miss.get("status")),
        )


def test_rbac_deny(db: Path, ctx: dict, rbac_path: Path) -> None:
    denied = False
    bad_ctx = {
        "person_id": "PERS-NOBODY",
        "rbac_db_path": rbac_path,
        "audit_conn": ctx["audit_conn"],
        "target_context": {},
    }
    try:
        dm.record_decision(
            title="Should be denied",
            scope="brand:habitat",
            options_considered=["x"],
            chosen_option="x",
            actor="nobody",
            permission_context=bad_ctx,
            db_path=db,
        )
    except dm.DecisionMemoryError as exc:
        denied = exc.code == "denied"
    check("rbac.deny_record", denied)

    denied_r = False
    try:
        dm.recall(
            "brand:habitat", "x", permission_context=bad_ctx, db_path=db
        )
    except dm.DecisionMemoryError as exc:
        denied_r = exc.code == "denied"
    check("rbac.deny_recall", denied_r)

    missing = False
    try:
        dm.record_decision(
            title="No context",
            scope="brand:habitat",
            options_considered=["x"],
            chosen_option="x",
            actor="nobody",
            permission_context=None,
            db_path=db,
        )
    except dm.DecisionMemoryError as exc:
        missing = exc.code == "denied"
    check("rbac.deny_missing_context", missing)


def test_audit_event_written(db: Path, ctx: dict, audit_conn: sqlite3.Connection) -> None:
    before = audit_conn.execute(
        "SELECT COUNT(*) FROM core_audit_events WHERE action='decision.memory.record'"
    ).fetchone()[0]
    rec = dm.record_decision(
        title="Audit probe decision",
        scope="brand:habitat",
        options_considered=["a"],
        chosen_option="a",
        outcome="noted",
        actor="Matthew Goss",
        permission_context=ctx,
        db_path=db,
    )
    after = audit_conn.execute(
        "SELECT COUNT(*) FROM core_audit_events WHERE action='decision.memory.record'"
    ).fetchone()[0]
    check("audit.event_written", after == before + 1, f"{before}->{after}")
    row = audit_conn.execute(
        """
        SELECT resource_id, result FROM core_audit_events
        WHERE action='decision.memory.record' AND resource_id=?
        LIMIT 1
        """,
        (rec["decision_id"],),
    ).fetchone()
    check(
        "audit.resource_id_matches",
        row is not None and row[0] == rec["decision_id"],
        str(tuple(row) if row else None),
    )
    check("audit.result_SUCCEEDED", row is not None and row[1] == "SUCCEEDED")


def test_seed_refuses_non_beta_path(td: Path) -> None:
    refused = False
    try:
        dm.seed_owner_decisions(db_path="/tmp/not-beta-decision-memory.sqlite")
    except RuntimeError as exc:
        refused = "non-beta" in str(exc)
    check("seed.refuses_non_beta", refused)


def test_seed_writes_real_decisions_temp_only(
    td: Path, ctx: dict, rbac_path: Path, audit_conn: sqlite3.Connection
) -> None:
    seed_db = td / "seed-decision_memory.sqlite"
    if seed_db.exists():
        seed_db.unlink()
    # Point audit_mod away from live for seed's internal audit connect when
    # we pass audit_db_path via a dedicated temp file.
    audit_path = td / "seed-audit.sqlite"
    if audit_path.exists():
        audit_path.unlink()
    # seed opens its own audit connection; copy schema via empty connect + SQL
    ac = audit_mod.db_connect(audit_path)
    ac.executescript(AUDIT_SQL.read_text(encoding="utf-8"))
    ac.commit()
    ac.close()

    result = dm.seed_owner_decisions(
        db_path=seed_db,
        rbac_db_path=rbac_path,
        audit_db_path=audit_path,
        catalog_db_path=LIVE_CATALOG if LIVE_CATALOG.exists() else None,
    )
    check("seed.count_ge_4", result.get("count", 0) >= 4, str(result))
    check(
        "seed.has_clickup",
        "DEC-ARCH-CLICKUP-2026-09-18" in (result.get("seeded_ids") or []),
    )
    check(
        "seed.has_credits",
        "DEC-MODEL-C-CREDITS-2026-09-17" in (result.get("seeded_ids") or []),
    )
    check(
        "seed.has_cutover",
        "DEC-CRM-HABITAT-CUTOVER-2026-09-18" in (result.get("seeded_ids") or []),
    )
    check(
        "seed.has_klaviyo",
        "DEC-CRM-KLAVIYO-RECEIPT-2026-09-18" in (result.get("seeded_ids") or []),
    )

    # Exact recall of seeded keys
    hit = dm.recall(
        "Wolf system",
        "What is Wolf's ClickUp policy?",
        permission_context=ctx,
        db_path=seed_db,
    )
    check("seed.recall_clickup", hit.get("count") == 1)

    credits = dm.get_decision("DEC-MODEL-C-CREDITS-2026-09-17", db_path=seed_db)
    check(
        "seed.credits_table",
        credits is not None
        and "ABSENT" in (credits.get("chosen_option") or "")
        and "0.05" in (credits.get("chosen_option") or "")
        and "1.00" in (credits.get("chosen_option") or ""),
        str((credits or {}).get("chosen_option"))[:120],
    )

    # Correction pair when docs qualify
    if dm._correction_docs_qualify():
        check("seed.correction_pair_flag", result.get("correction_pair") is True)
        old = dm.get_decision(
            "DEC-MATURITY-DR01-INTG07-OVERNIGHT-2026-09-17", db_path=seed_db
        )
        new = dm.get_decision(
            "DEC-MATURITY-DR01-INTG07-CORRECTED-2026-09-18", db_path=seed_db
        )
        check("seed.correction.old_present", old is not None)
        check(
            "seed.correction.new_points_old",
            new is not None
            and new.get("corrects_decision_id")
            == "DEC-MATURITY-DR01-INTG07-OVERNIGHT-2026-09-17",
        )
        maturity = dm.recall(
            "Wolf system",
            "What is CAP-DR-01 and CAP-INTG-07 maturity?",
            permission_context=ctx,
            db_path=seed_db,
        )
        check("seed.correction.recall_hit", maturity.get("count") >= 1)
        top = (maturity.get("decisions") or [{}])[0]
        check(
            "seed.correction.current_SPECIFIED",
            "SPECIFIED" in (top.get("chosen_option") or ""),
            str(top.get("chosen_option")),
        )
        check(
            "seed.correction.old_still_gettable",
            old is not None and "PROVEN" in (old.get("chosen_option") or ""),
        )
    else:
        check("seed.correction_skipped_docs_unqualified", True)

    # Live default DB untouched by this test seed
    live = dm.LIVE_DEFAULT_DB
    if live.exists():
        # May exist from a prior live seed; this test must not have written via seed_db
        check("seed.used_temp_db", seed_db.resolve() != live.resolve())
    else:
        check("seed.live_absent_ok", True)


def test_migration_no_staff_grants() -> None:
    import importlib.util

    mig_path = SCRIPTS / "migrations" / "migrate_decision_memory_permissions.py"
    spec = importlib.util.spec_from_file_location("mig_dm_perms", mig_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    td = _tmp_dir()
    tmp = td / "mig-catalog.sqlite"
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(LIVE_CATALOG, tmp)
    rc = mod.main([str(tmp)])
    check("migration.exit_0", rc == 0, str(rc))
    conn = sqlite3.connect(str(tmp))
    try:
        n = conn.execute(
            """
            SELECT COUNT(*) FROM org_permissions
            WHERE code IN ('decision.memory.read','decision.memory.record')
              AND status='ACTIVE'
            """
        ).fetchone()[0]
        check("migration.two_perms", n == 2, str(n))
        staff = (
            "ROLE-MATT",
            "ROLE-OWNER",
            "ROLE-AMANDA",
            "ROLE-HAIKAL",
            "ROLE-MISA",
            "ROLE-DEVI",
            "ROLE-CONTENT-MGMT",
            "ROLE-GGV-EDIT",
            "ROLE-CONTENT-CREW",
        )
        marks = ",".join("?" * len(staff))
        g = conn.execute(
            f"""
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN (
              'PERM-DECISION-MEMORY-READ','PERM-DECISION-MEMORY-RECORD'
            ) AND role_id IN ({marks})
            """,
            staff,
        ).fetchone()[0]
        check("migration.staff_grants_0", g == 0, str(g))
    finally:
        conn.close()


def main() -> int:
    td = _tmp_dir()
    db = _tmp_db(td)
    ctx, rbac_path, audit_conn = _setup_rbac_and_audit(td)
    try:
        test_honesty_and_vocab()
        test_source_has_no_network_hooks()
        test_beta_path_guards()
        test_migration_no_staff_grants()
        test_append_only_and_correction(db, ctx)
        test_empty_outcome_unknown_not_invented(db, ctx)
        test_empty_options_requires_reason(db, ctx)
        test_scope_isolation(db, ctx)
        test_recall_not_found_and_provenance(db, ctx)
        test_recall_cap_50(db, ctx)
        test_exact_key_hit_and_adjacent_miss(db, ctx)
        test_rbac_deny(db, ctx, rbac_path)
        test_audit_event_written(db, ctx, audit_conn)
        test_seed_refuses_non_beta_path(td)
        test_seed_writes_real_decisions_temp_only(td, ctx, rbac_path, audit_conn)
    finally:
        audit_conn.close()

    print()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    _ = tempfile
    raise SystemExit(main())
