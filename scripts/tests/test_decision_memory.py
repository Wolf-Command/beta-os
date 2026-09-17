#!/usr/bin/env python3
"""Tests for Wolf Core Decision Memory v1 (Beta). CAP-INTEL-04.

Fixture DB only (temp file). No network. No Production. No Habitat/Uma disturb.
Proves: INSERT-only, no silent rewrite, scope isolation, empty outcome ≠ invented,
recall max 50.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"

from core import decision_memory as dm  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_db() -> Path:
    # Must live under beta-os (db_connect refuses non-beta paths).
    td = ROOT / "catalog" / "backups" / f"tmp-decision-memory-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    path = td / "decision_memory.sqlite"
    if path.exists():
        path.unlink()
    return path


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


def test_append_only_and_correction(db: Path) -> None:
    rec = dm.record_decision(
        title="Pick font for Habitat brand",
        scope="brand:habitat",
        options_considered=["Manrope", "Inter"],
        chosen_option="Manrope",
        outcome="shipped",
        actor="PERS-MATT",
        approval_ref="APR-TEST-1",
        provenance={"source": "test"},
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

    # UPDATE/DELETE API refused
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

    # SQL-level append-only triggers
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

    # Original row unchanged
    got = dm.get_decision(prior_id, db_path=db)
    check(
        "no silent rewrite of prior title",
        got is not None and got.get("title") == "Pick font for Habitat brand",
        str(got),
    )

    # Correction = new INSERT referencing prior
    corr = dm.correct_decision(
        prior_id,
        title="Pick font for Habitat brand (corrected)",
        scope="brand:habitat",
        options_considered=["Manrope", "Inter", "Geist"],
        chosen_option="Manrope",
        outcome="shipped",
        actor="PERS-MATT",
        provenance={"source": "test", "kind": "correction"},
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

    # Count rows = 2 (prior + correction)
    conn = sqlite3.connect(str(db))
    try:
        n = conn.execute("SELECT COUNT(*) FROM core_decision_memory").fetchone()[0]
        check("two INSERT rows after correction", n == 2, str(n))
    finally:
        conn.close()


def test_empty_outcome_unknown_not_invented(db: Path) -> None:
    rec = dm.record_decision(
        title="Vendor choice pending outcome",
        scope="brand:habitat",
        options_considered=["A", "B"],
        chosen_option="A",
        outcome=None,
        actor="PERS-MATT",
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

    # No invented approval_ref when omitted
    no_appr = dm.record_decision(
        title="No approval pointer",
        scope="brand:habitat",
        options_considered=["go"],
        chosen_option="go",
        outcome="done",
        actor="PERS-MATT",
        db_path=db,
    )
    check(
        "approval_ref not invented",
        no_appr.get("approval_ref") is None,
        str(no_appr.get("approval_ref")),
    )


def test_empty_options_requires_reason(db: Path) -> None:
    raised = False
    try:
        dm.record_decision(
            title="No options",
            scope="brand:habitat",
            options_considered=[],
            actor="PERS-MATT",
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
        db_path=db,
    )
    check("empty options with reason accepted", ok.get("status") == dm.STATUS_RECORDED)
    check(
        "empty options reason stored",
        ok.get("empty_options_reason") == "binary gate — proceed / abort only",
    )


def test_scope_isolation(db: Path) -> None:
    dm.record_decision(
        title="Habitat content cadence",
        scope="brand:habitat",
        options_considered=["daily", "weekly"],
        chosen_option="weekly",
        outcome="adopted",
        actor="PERS-MATT",
        db_path=db,
    )
    dm.record_decision(
        title="Uma close threshold",
        scope="brand:uma",
        options_considered=["strict", "lenient"],
        chosen_option="strict",
        outcome="adopted",
        actor="PERS-MATT",
        db_path=db,
    )

    habitat = dm.recall("brand:habitat", "cadence", db_path=db)
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

    uma = dm.recall("brand:uma", "threshold", db_path=db)
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


def test_recall_not_found_and_provenance(db: Path) -> None:
    dm.record_decision(
        title="Metricool read-only stance",
        scope="brand:habitat",
        options_considered=["read-only", "write"],
        chosen_option="read-only",
        outcome="locked",
        actor="PERS-MATT",
        provenance={"doc": "discovery-2026-09-17", "cap": "CAP-INTEL-04"},
        db_path=db,
    )
    hit = dm.recall("brand:habitat", "Metricool", db_path=db)
    check("recall.hit.count", hit.get("count") >= 1)
    check("recall.hit.has_provenance", bool((hit["decisions"][0]).get("provenance")))
    check(
        "recall.hit.provenance_cap",
        (hit["decisions"][0].get("provenance") or {}).get("cap") == "CAP-INTEL-04",
    )

    miss = dm.recall("brand:habitat", "zzz-no-such-decision-xyz", db_path=db)
    check(
        "recall.miss.status_NOT_FOUND",
        miss.get("status") == dm.STATUS_NOT_FOUND,
        str(miss.get("status")),
    )
    check("recall.miss.empty", miss.get("count") == 0 and miss.get("decisions") == [])


def test_recall_cap_50(db: Path) -> None:
    for i in range(60):
        dm.record_decision(
            title=f"Batch decision {i:03d}",
            scope="brand:habitat",
            options_considered=[f"opt-{i}"],
            chosen_option=f"opt-{i}",
            outcome="noted",
            actor="SYSTEM",
            db_path=db,
        )
    all_batch = dm.recall("brand:habitat", "Batch decision", db_path=db)
    check(
        "recall.cap_le_50",
        all_batch.get("count") == 50,
        str(all_batch.get("count")),
    )
    check("recall.limit_field", all_batch.get("limit") == 50)

    capped = dm.recall("brand:habitat", "Batch decision", limit=10, db_path=db)
    check("recall.limit_honoured", capped.get("count") == 10, str(capped.get("count")))

    # Caller cannot exceed RECALL_MAX
    over = dm.recall("brand:habitat", "Batch decision", limit=999, db_path=db)
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
        # Fabricate a path that looks like Production under a fake beta-os name —
        # the Production substring check fires on path content.
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


def main() -> int:
    db = _tmp_db()
    try:
        test_honesty_and_vocab()
        test_source_has_no_network_hooks()
        test_beta_path_guards()
        test_append_only_and_correction(db)
        test_empty_outcome_unknown_not_invented(db)
        test_empty_options_requires_reason(db)
        test_scope_isolation(db)
        test_recall_not_found_and_provenance(db)
        test_recall_cap_50(db)
    finally:
        # Leave temp DB for inspection; do not touch live catalog.
        pass

    print()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    # tempfile imported for clarity that tests use file-backed fixtures only
    _ = tempfile
    raise SystemExit(main())
