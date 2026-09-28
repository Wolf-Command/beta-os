#!/usr/bin/env python3
"""CAP-CORE-11 SOP loop. Temp factory file only. Ledger stays SPECIFIED."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)
os.environ.pop("WOLF_ALLOW_LIVE_SOP_FACTORY", None)
os.environ.pop("WOLF_SOP_FACTORY_DB", None)

from core import sop_factory as sop  # noqa: E402
from core.canonical_guard import CanonicalGuardError, assert_write_allowed  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
LIVE_SOP = ROOT / "catalog" / "sop_factory.sqlite"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
CR_ID = "CR-c4ed4e3fa9f15a40"
ROLE = "PERS-SOP-ROLE"

NOTE = "Shift note: tin count was skipped on the Uma close."
LEARN = "The miss was the missing line on the close card, not the count itself."
BODY = "Count the tin before the drawer is closed and record the number."
BODY2 = "Count the tin, then write the number on the close card before lockup."
USE = "The close card used the approved tin-count line and no other version."


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _canonical() -> tuple[int, int, int, str | None, str | None, str | None]:
    conn = _ro(CATALOG)
    try:
        evidence = int(conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
        exceptions = int(
            conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0]
        )
        approvals = int(conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0])
        status = conn.execute(
            "SELECT status FROM core_evidence_records WHERE evidence_id=?",
            (EVIDENCE_ID,),
        ).fetchone()
        cr = conn.execute(
            "SELECT state, blocker_class FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    return (
        evidence,
        exceptions,
        approvals,
        None if status is None else str(status[0]),
        None if cr is None else str(cr[0]),
        None if cr is None else str(cr[1]),
    )


def _expect(name: str, fn, code: str) -> None:
    try:
        fn()
    except sop.SopFactoryError as exc:
        check(name, exc.code == code, f"code={exc.code}")
        return
    check(name, False, "no error")


def _draft(**overrides: object) -> dict:
    body: dict = {"title": "Tin count", "body": BODY, "evidence_note": NOTE}
    body.update(overrides)
    return body


def main() -> None:
    before = _canonical()
    ledger_hash = hashlib.sha256(LEDGER.read_bytes()).hexdigest()
    live_before = LIVE_SOP.exists()
    scratch = ROOT / "state" / "build-factory" / "tmp-f1" / f"sop-loop-{os.getpid()}"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "sop_factory.sqlite"
    rewrite = scratch / "tin-count.md"

    check("live sop absent before", live_before is False)
    _expect(
        "anon learn denied",
        lambda: sop.record_learning(
            {"version_id": "VER-00000000-0000-4000-8000-000000000001", "learning_note": LEARN},
            person_id=None,
            db_path=path,
        ),
        "denied",
    )
    check("anon learn created no file", not path.exists())

    rewrite.write_text("first text\n", encoding="utf-8")
    rewrite.write_text("rewritten text with no version row\n", encoding="utf-8")
    _expect(
        "file rewrite refused",
        lambda: sop.refuse_unversioned_rewrite({"path": str(rewrite), "body": "rewritten"}),
        "unversioned",
    )
    check("rewrite created no factory file", not path.exists())

    try:
        assert_write_allowed(LIVE_SOP)
        check("live sop write refused", False, "guard allowed the live factory")
    except CanonicalGuardError as exc:
        check("live sop write refused", "canonical Beta write" in str(exc), str(exc))

    made = sop.create_draft(_draft(), person_id=sop.OWNER_PERSON, db_path=path)
    version_1 = str(made["version_id"])
    sop_id = str(made["sop_id"])
    check("draft not live", made.get("live") is False)
    check("draft staff_ready false", made.get("honesty", {}).get("staff_ready") is False)

    learned = sop.record_learning(
        {"version_id": version_1, "learning_note": LEARN},
        person_id=sop.OWNER_PERSON,
        db_path=path,
    )
    check("learning appended", learned.get("appended") is True and learned.get("live") is False)
    check("learning does not train", learned.get("honesty", {}).get("train_staff") is False)

    early = sop.loop_status(sop_id, sop.OWNER_PERSON, db_path=path)
    check("versioning empty before change", (early.get("stages") or {}).get("versioning") == "EMPTY")
    check("approval empty before approve", (early.get("stages") or {}).get("approval") == "EMPTY")
    check("learning present", (early.get("stages") or {}).get("learning") == "PRESENT")

    _expect(
        "ack before approve refused",
        lambda: sop.acknowledge(
            {"version_id": version_1},
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "not_approved",
    )
    _expect(
        "use before approve refused",
        lambda: sop.record_use(
            {"version_id": version_1, "use_note": USE},
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "not_live",
    )

    approved_1 = sop.approve(
        {"version_id": version_1},
        person_id=sop.OWNER_PERSON,
        db_path=path,
    )
    check("first approve live", approved_1.get("live") is True)
    check("first approve kept version", approved_1.get("version_unchanged") is True)

    proposed = sop.append_version(
        {
            "sop_id": sop_id,
            "title": "Tin count",
            "body": BODY2,
            "evidence_note": NOTE,
        },
        person_id=sop.OWNER_PERSON,
        db_path=path,
    )
    version_2 = str(proposed["version_id"])
    check("proposed version is 2", proposed.get("version_n") == 2)
    check("proposed not live", proposed.get("live") is False)
    check("live stays version 1", proposed.get("live_version_id") == version_1)

    _expect(
        "ack of unapproved change refused",
        lambda: sop.acknowledge(
            {"version_id": version_2},
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "not_approved",
    )
    _expect(
        "use of unapproved change refused",
        lambda: sop.record_use(
            {"version_id": version_2, "use_note": USE},
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "not_live",
    )
    _expect(
        "role without grant denied",
        lambda: sop.approve(
            {"version_id": version_2},
            person_id=ROLE,
            role_allowed=False,
            db_path=path,
        ),
        "denied",
    )

    approved_2 = sop.approve(
        {"version_id": version_2},
        person_id=ROLE,
        role_allowed=True,
        db_path=path,
    )
    check("change approver stored", approved_2.get("live") is True)
    check("change gate is role", approved_2.get("gate") == "role")

    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT version_n, body FROM sop_versions WHERE sop_id=? ORDER BY version_n",
            (sop_id,),
        ).fetchall()
        check("two versions stored", len(rows) == 2, str(len(rows)))
        check("version 1 body retained", rows[0][1] == BODY, str(rows[0][1])[:80])
        check("version 2 body is the change", rows[1][1] == BODY2)
        approver = conn.execute(
            "SELECT decided_by, gate FROM sop_approvals WHERE version_id=?",
            (version_2,),
        ).fetchone()
        check("approver row is the role gate", approver == (ROLE, "role"), str(approver))
        try:
            conn.execute(
                "UPDATE sop_versions SET body=? WHERE version_id=?",
                ("silent rewrite", version_1),
            )
            conn.commit()
            check("version update aborted", False, "update committed")
        except sqlite3.IntegrityError as exc:
            check("version update aborted", "append-only" in str(exc), str(exc))
    finally:
        conn.close()

    ack = sop.acknowledge(
        {"version_id": version_2},
        person_id=ROLE,
        role_allowed=True,
        db_path=path,
    )
    check("ack appended", ack.get("appended") is True)
    check("ack is not staff ready", ack.get("staff_ready") is False)
    check("ack is not commissioning", ack.get("human_commissioned") is False)
    check("ack does not train staff", ack.get("trains_staff") is False)
    _expect(
        "second ack refused",
        lambda: sop.acknowledge(
            {"version_id": version_2},
            person_id=ROLE,
            role_allowed=True,
            db_path=path,
        ),
        "already_acknowledged",
    )

    used = sop.record_use(
        {"version_id": version_2, "use_note": USE},
        person_id=ROLE,
        role_allowed=True,
        db_path=path,
    )
    check("use appended", used.get("appended") is True and used.get("live") is True)
    check("use is not adoption", used.get("operating_adoption") is False)
    _expect(
        "old live use refused",
        lambda: sop.record_use(
            {"version_id": version_1, "use_note": USE},
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "not_live",
    )

    status = sop.loop_status(sop_id, sop.OWNER_PERSON, db_path=path)
    stages = status.get("stages") or {}
    for name in (
        "evidence",
        "learning",
        "proposed_change",
        "approval",
        "versioning",
        "acknowledgement",
        "use",
    ):
        check(f"stage {name}", stages.get(name) == "PRESENT", str(stages.get(name)))
    check("approver recorded", status.get("approver_recorded") is True)
    check("prior body retained", status.get("prior_body_retained") is True)
    check("status staff_ready false", status.get("staff_ready") is False)
    check("status commissioned false", status.get("human_commissioned") is False)
    check("status adoption false", status.get("operating_adoption") is False)
    check("version count 2", status.get("version_count") == 2)
    check("ledger not raised", (status.get("honesty") or {}).get("model_c_maturity_raised") is False)
    check("cr not mutated", (status.get("honesty") or {}).get("cr_mutated") is False)
    check("maturity still ledger", (status.get("honesty") or {}).get("ledger_maturity") == "SPECIFIED")

    missing = sop.loop_status(sop_id, sop.OWNER_PERSON, db_path=scratch / "missing.sqlite")
    check("missing file version count unset", missing.get("version_count") is None)
    check("missing file not zero versions", missing.get("version_count") != 0)
    check("missing file stage absent", (missing.get("stages") or {}).get("use") == "ABSENT")
    check("missing file not created", not (scratch / "missing.sqlite").exists())

    after = _canonical()
    check("canonical counts unchanged", after == before, f"{before} -> {after}")
    check(
        "ledger bytes unchanged",
        hashlib.sha256(LEDGER.read_bytes()).hexdigest() == ledger_hash,
    )
    check("live sop still absent", LIVE_SOP.exists() is False)

    print(
        "COUNTS "
        f"versions={status.get('version_count')} "
        f"learnings={status.get('learning_count')} "
        f"approvals={status.get('approval_count')} "
        f"acks={status.get('acknowledgement_count')} "
        f"uses={status.get('use_count')} "
        f"approver_recorded={status.get('approver_recorded')} "
        f"prior_retained={status.get('prior_body_retained')} "
        f"staff_ready={status.get('staff_ready')} "
        f"commissioned={status.get('human_commissioned')} "
        f"adoption={status.get('operating_adoption')}"
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        raise SystemExit(1)
    print("EXIT: SUCCESS")


if __name__ == "__main__":
    main()
