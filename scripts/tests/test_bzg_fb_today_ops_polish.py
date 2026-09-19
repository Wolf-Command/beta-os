#!/usr/bin/env python3
"""BZG F&B Today ops polish — Ops Lead affordances.

Fixture is a copy of the catalog. PERS-DEVI / ROLE-BZG-FB-OPS-LEAD
capabilities decide Today actions. No payment grant, no ENTITY resurrect,
no fake transactions, no Alchemist write, no Production touch.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("WOLF_TEST_MODE", "1")
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import rbac  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PASS = 0
FAIL = 0
UMA = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py":
        "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py":
        "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py":
        "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py":
        "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}
SCORE = ROOT / "state" / "model-c-baseline-assessments.json"
HUMAN_CR = "CR-0fc49fa643fb2c26"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entity_end(conn: sqlite3.Connection):
    return conn.execute(
        """
        SELECT status, end_at FROM org_assignment_scopes
        WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND scope_id='SCOPE-BZG-ENTITY'
        """
    ).fetchone()


def pay_grants(conn: sqlite3.Connection) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id=rp.permission_id
        WHERE rp.role_id='ROLE-BZG-FB-OPS-LEAD' AND p.code='bzg.pr.payment_approve'
          AND rp.effect='ALLOW'
        """
    ).fetchone()[0]


def drop_allow(conn: sqlite3.Connection, code: str) -> None:
    conn.execute(
        """
        DELETE FROM org_role_permissions
        WHERE role_id='ROLE-BZG-FB-OPS-LEAD'
          AND permission_id=(SELECT permission_id FROM org_permissions WHERE code=?)
        """,
        (code,),
    )
    conn.commit()


def card_of(payload: dict, kind: str) -> dict | None:
    for card in payload.get("cards") or []:
        if card.get("kind") == kind:
            return card
    return None


def main() -> int:
    for rel, digest in WIP.items():
        check(f"WIP unchanged {Path(rel).name}", sha(ROOT / rel) == digest)
    score_before = sha(SCORE) if SCORE.is_file() else None

    src = (SCRIPTS / "core" / "uma_devi_p0.py").read_text(encoding="utf-8")
    today_html = (ROOT / "dashboards" / "bzg-uma-blu.html").read_text(encoding="utf-8")
    close_html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("no PERS-DEVI hard-code in p0", '== "PERS-DEVI"' not in src and "== 'PERS-DEVI'" not in src)
    check("no PERS-DEVI hard-code in Today", "PERS-DEVI" not in today_html)
    check("no PERS-DEVI hard-code in Close", "PERS-DEVI" not in close_html)
    check("p0 does not grant roles", "INSERT INTO org_role_permissions" not in src)
    check("p0 does not insert transactions", "INSERT INTO bzg_ops_receipt" not in src.split("def receive_goods")[0])
    check(
        "Today shows action label from capabilities",
        "c.action.label" in today_html and 'el("span", "act"' in today_html and 'el("a", "act"' in today_html,
    )
    check("Today action button is 44px", ".act" in today_html and "min-height: 44px" in today_html)
    check("Today is phone width", 'width=device-width' in today_html and "max-width: 480px" in today_html)
    check("Today wraps under 420px", "@media (max-width: 420px)" in today_html)
    check("Today never paints Needs staff when they can act", 'label === "Needs staff"' in today_html and "You can act" in today_html)
    check("Today prefers Waiting on person", 'indexOf("Waiting on ")' in today_html and "waiting_on" in today_html)
    check("Today paints Policy required", "Policy required" in today_html)
    check("Close perform/submit buttons exist", close_html.count('data-cap="submit"') >= 4)
    check("Close verify stays behind caps.verify", "caps.verify" in close_html and "Verify close" in close_html)
    check(
        "Close says verify is a separate role",
        "Verify stays with a separate role" in close_html,
    )
    check("Close is phone width", 'width=device-width' in close_html and "max-width: 480px" in close_html)
    check("Close stacks figures on a phone", "@media (max-width: 420px)" in close_html and "grid-template-columns: 1fr" in close_html)
    check("Close buttons are 44px", "min-height: 44px" in close_html)

    live = sqlite3.connect(str(LIVE_DB))
    live.row_factory = sqlite3.Row
    ent_live = tuple(entity_end(live))
    pay_live = pay_grants(live)
    receipts_live = live.execute("SELECT COUNT(*) FROM bzg_ops_receipt_events").fetchone()[0]
    human = live.execute(
        "SELECT state FROM wolf_completion_items WHERE id=?",
        (HUMAN_CR,),
    ).fetchone()
    live.close()
    check("live ENTITY already ENDED", ent_live[0] == "ENDED" and ent_live[1])
    check("live Ops Lead has no payment grant", pay_live == 0, str(pay_live))
    check("human retest still waiting", bool(human) and human[0] == "WAITING_HUMAN", str(human[0] if human else None))

    td = ROOT / "catalog" / "backups" / f"tmp-today-ops-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp = td / "content_library.sqlite"
    try:
        shutil.copy2(LIVE_DB, tmp)
        conn = sqlite3.connect(str(tmp))
        conn.row_factory = sqlite3.Row
        ent_before = tuple(entity_end(conn))
        receipts_before = conn.execute("SELECT COUNT(*) FROM bzg_ops_receipt_events").fetchone()[0]

        check("fixture receive", rbac.can("PERS-DEVI", "venue.receive", UMA, conn=conn))
        check("fixture close.submit", rbac.can("PERS-DEVI", "venue.close.submit", UMA, conn=conn))
        check("fixture verify denied", rbac.can("PERS-DEVI", "venue.close.verify", UMA, conn=conn) is False)
        check("fixture payment denied", rbac.can("PERS-DEVI", "bzg.pr.payment_approve", UMA, conn=conn) is False)
        check("fixture progress denied", rbac.can("PERS-DEVI", "progress.read", UMA, conn=conn) is False)
        check("fixture approval denied", rbac.can("PERS-DEVI", "approval.decide", UMA, conn=conn) is False)

        caps = p0.close_capabilities("PERS-DEVI", conn=conn)
        check("caps submit", caps["can"]["submit"] is True and caps["can"]["open"] is True)
        check("caps verify separated", caps["can"]["verify"] is False)
        check("caps payment not granted", caps["can"]["payment_approve"] is False)

        painted = ops.today_cards(person_id="PERS-DEVI", conn=conn)
        close = card_of(painted, "daily_close")
        check("fixture close card present", close is not None)
        if close:
            check("close not Needs staff", close.get("classification_label") != "Needs staff", str(close.get("classification_label")))
            action = close.get("action") or {}
            check("close action is perform", action.get("label") == p0.ACTION_PERFORM_CLOSE, str(action))
            check("close action href", action.get("href") == "/uma-blu-close", str(action.get("href")))
            check("close chip You can act", close.get("classification_label") == "You can act")
            check("close stays linked", close.get("href") == "/uma-blu-close")
        now = painted.get("now") or {}
        check("now is the close action", (now.get("action") or {}).get("label") == p0.ACTION_PERFORM_CLOSE, str(now.get("action")))
        for card in painted.get("cards") or []:
            if card.get("actionable") and card.get("action"):
                check(
                    f"live {card.get('kind')} not Needs staff",
                    card.get("classification_label") != "Needs staff",
                    str(card.get("classification_label")),
                )

        ordered = p0.annotate_today(
            {
                "cards": [
                    {
                        "kind": "ordered_not_received",
                        "title": "Ordered, not received",
                        "attention": True,
                        "classification": "NEEDS_STAFF",
                        "classification_label": "Needs staff",
                        "href": "/bzg/uma-blu/bills",
                        "rank": 1,
                    }
                ]
            },
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("receive action", (ordered.get("action") or {}).get("label") == p0.ACTION_RECEIVE, str(ordered.get("action")))
        check("receive not Needs staff", ordered.get("classification_label") == "You can act")
        check("receive href kept", ordered.get("href") == "/bzg/uma-blu/bills")

        pay = p0.annotate_today(
            {
                "cards": [
                    {
                        "kind": "bills_waiting_payment_approval",
                        "classification": "NEEDS_STAFF",
                        "classification_label": "Needs staff",
                        "href": "/bzg/uma-blu/bills",
                        "attention": True,
                    }
                ]
            },
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("payment not actionable", pay.get("actionable") is False and pay.get("action") is None)
        check("payment waits on finance", pay.get("classification_label") == "Waiting on finance", str(pay.get("classification_label")))
        check("payment href removed", pay.get("href") is None)

        pol = p0.annotate_today(
            {"cards": [{"kind": "policy_required", "classification": "NEEDS_POLICY", "classification_label": "Needs policy", "attention": True}]},
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("policy required label", pol.get("classification_label") == "Policy required", str(pol.get("classification_label")))
        check("policy not actionable", pol.get("actionable") is False and pol.get("action") is None)

        exc = p0.annotate_today(
            {
                "cards": [
                    {
                        "kind": "daily_close",
                        "classification_label": "Needs staff",
                        "attention": True,
                        "href": "/uma-blu-close",
                        "close": {"status": "exception", "state": "EXCEPTION"},
                    }
                ]
            },
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("exception action is resolve", (exc.get("action") or {}).get("label") == p0.ACTION_RESOLVE, str(exc.get("action")))
        check("exception is not verify", "Verify" not in str(exc.get("action")))

        blocked = p0.annotate_today(
            {
                "cards": [
                    {
                        "kind": "daily_close",
                        "classification": "NEEDS_POLICY",
                        "classification_label": "Needs policy",
                        "attention": True,
                        "close": {"status": "blocked", "state": "VARIANCE_REQUIRES_POLICY"},
                    }
                ]
            },
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("blocked close is an action", (blocked.get("action") or {}).get("label") == p0.ACTION_OPEN_EXCEPTION, str(blocked.get("action")))
        check("blocked close not Needs staff", blocked.get("classification_label") == "You can act")

        drop_allow(conn, "venue.close.submit")
        check("submit removed on fixture only", rbac.can("PERS-DEVI", "venue.close.submit", UMA, conn=conn) is False)
        waiting_close = p0.annotate_today(
            {
                "cards": [
                    {
                        "kind": "daily_close",
                        "classification_label": "Needs staff",
                        "attention": True,
                        "href": "/uma-blu-close",
                        "close": {"status": "not_started"},
                    }
                ]
            },
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("without submit, no perform action", waiting_close.get("action") is None and waiting_close.get("actionable") is False)
        check(
            "without submit, waiting on closer",
            waiting_close.get("waiting_role") == "closer"
            and str(waiting_close.get("classification_label") or "").startswith("Waiting on "),
            str(waiting_close.get("classification_label")),
        )

        drop_allow(conn, "venue.receive")
        denied_recv = p0.annotate_today(
            {
                "cards": [
                    {
                        "kind": "ordered_not_received",
                        "classification_label": "Needs staff",
                        "href": "/bzg/uma-blu/bills",
                        "attention": True,
                    }
                ]
            },
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("without receive, no goods action", denied_recv.get("action") is None and denied_recv.get("actionable") is False)
        check("without receive, policy required", denied_recv.get("classification_label") == "Policy required")

        ts = "2026-09-19T09:20:00Z"
        conn.execute(
            """
            INSERT INTO org_persons (person_id, display_name, status, created_at, updated_at)
            VALUES ('PERS-FIXTURE-WAIT', 'Fixture Waiter', 'ACTIVE', ?, ?)
            """,
            (ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (
              'ASG-FIXTURE-WAIT-1', 'PERS-FIXTURE-WAIT', 'POS-BZG-HFB-UMA-1',
              ?, NULL, 'ACTIVE', 1, ?, ?
            )
            """,
            (ts, ts, ts),
        )
        conn.commit()
        resolved = p0.annotate_today(
            {
                "cards": [
                    {
                        "kind": "daily_close",
                        "classification_label": "Needs staff",
                        "attention": True,
                        "href": "/uma-blu-close",
                        "close": {"state": "RESOLVED", "status": "in_progress"},
                    }
                ]
            },
            person_id="PERS-DEVI",
            conn=conn,
        )["cards"][0]
        check("resolved waits on the person", resolved.get("classification_label") == "Waiting on Fixture Waiter", str(resolved.get("classification_label")))
        check("resolved waiting role stays Head of F&B", resolved.get("waiting_role") == "Head of F&B")
        check("resolved has no verify action", resolved.get("action") is None and resolved.get("href") is None)

        check("fixture ENTITY unchanged", tuple(entity_end(conn)) == ent_before)
        check(
            "fixture created no receipts",
            conn.execute("SELECT COUNT(*) FROM bzg_ops_receipt_events").fetchone()[0] == receipts_before,
        )
        check("fixture still has no payment grant", pay_grants(conn) == 0)
        conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

    live2 = sqlite3.connect(str(LIVE_DB))
    live2.row_factory = sqlite3.Row
    check("live ENTITY not resurrected", tuple(entity_end(live2)) == ent_live)
    check("live payment grants unchanged", pay_grants(live2) == pay_live)
    check(
        "live receipts unchanged",
        live2.execute("SELECT COUNT(*) FROM bzg_ops_receipt_events").fetchone()[0] == receipts_live,
    )
    human2 = live2.execute(
        "SELECT state FROM wolf_completion_items WHERE id=?",
        (HUMAN_CR,),
    ).fetchone()
    live2.close()
    check("human retest not interrupted", bool(human2) and human2[0] == "WAITING_HUMAN")
    if score_before is not None:
        check("score file unchanged", sha(SCORE) == score_before)

    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
