#!/usr/bin/env python3
"""Pack 2 — segregating Uma approval and close-card evidence failure.

Temp catalog only. Does not write the live Beta catalog and does not
touch Alchemist or prod :8787.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import approvals  # noqa: E402
from core import audit  # noqa: E402
from core import evidence  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402
from core import venue_close  # noqa: E402
from core import work_items  # noqa: E402

PASS = 0
FAIL = 0
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def patch(path: Path) -> None:
    ops.CATALOG_DB = path
    evidence.CATALOG_DB = path
    audit.CATALOG_DB = path
    venue_close.CATALOG_DB = path
    work_items.CATALOG_DB = path
    approvals.CATALOG_DB = path


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="uma-pack2-", dir=str(ROOT / "state")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    patch(db)
    conn = ops.db_connect(db)
    try:
        pr = ops.create_pr(
            supplier_name="BU SEPTI",
            purpose="Pack2 segregation probe",
            lines=[{"item": "kimchi", "qty": 1, "unit": "pack"}],
            submitted=True,
            example=False,
            verified_person_id="PERS-DEVI",
            actor_type="PERSON",
            conn=conn,
            commit=False,
        )
        try:
            p0.ops_advance(
                person_id="PERS-DEVI",
                pr_id=pr["pr_id"],
                to_state="APPROVED",
                conn=conn,
                commit=False,
            )
            check("requester cannot self-approve", False, "advance returned")
        except ops.UmaOpsError as exc:
            check(
                "requester cannot self-approve",
                exc.code == "self_approval_denied",
                exc.code,
            )

        approved = p0.approve_purchase_segregated(
            person_id="PERS-MATT",
            pr_id=pr["pr_id"],
            conn=conn,
            commit=False,
        )
        row = conn.execute(
            """
            SELECT status, requested_by_person_id
            FROM core_approval_requests
            WHERE approval_request_id=?
            """,
            (approved.get("approval_request_id"),),
        ).fetchone()
        check("pr approved by other person", approved.get("state") == "APPROVED", str(approved.get("state")))
        check(
            "one approval request decided",
            bool(row) and row["status"] == "APPROVED" and row["requested_by_person_id"] == "PERS-DEVI",
            str(dict(row) if row else None),
        )
        decisions = conn.execute(
            """
            SELECT decided_by_person_id, decision
            FROM core_approval_decisions
            WHERE approval_request_id=?
            """,
            (approved.get("approval_request_id"),),
        ).fetchall()
        check(
            "decision is the other person",
            len(decisions) == 1
            and decisions[0]["decided_by_person_id"] == "PERS-MATT"
            and decisions[0]["decision"] == "APPROVED",
            str([dict(d) for d in decisions]),
        )

        biz = ops.today_biz_date()
        opened = venue_close.open_or_get(
            biz,
            verified_person_id="PERS-DEVI",
            conn=conn,
            commit=False,
        )
        cards = ops.today_cards(conn=conn)
        close_card = next(c for c in cards.get("cards") or [] if c.get("kind") == "daily_close")
        check(
            "open close without cash evidence is on the card",
            close_card.get("attention") is True
            and close_card.get("blocked") is True
            and close_card.get("explain_kind") == "close_evidence_missing"
            and "No till count was invented." in str(close_card.get("why") or ""),
            str({k: close_card.get(k) for k in ("attention", "blocked", "explain_kind", "why", "title")}),
        )
        check("close id present", bool(opened.get("close_id")))
        conn.rollback()
    finally:
        conn.close()
        patch(LIVE_DB)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
