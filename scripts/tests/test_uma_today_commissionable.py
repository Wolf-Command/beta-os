#!/usr/bin/env python3
"""Uma Blu Today commissionable loop (Beta). Temp DB only.

Attention-first cards, why on blocked cards, example rows excluded from
attention_count, Daily Close href, float NOT_FOUND, no staff grant.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"

from core.blocker_explain import WHY_OPENING_FLOAT, WHY_POLICY_REQUIRED  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
TODAY_HTML = ROOT / "dashboards" / "bzg-uma-blu.html"
PETTY_HTML = ROOT / "dashboards" / "bzg-uma-blu-petty.html"

PASS = 0
FAIL = 0

FORBIDDEN_STAGE = (
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


def patch_catalog(mod, path: Path) -> None:
    mod.CATALOG_DB = path


def main() -> int:
    src = (SCRIPTS / "core" / "uma_ops_console.py").read_text(encoding="utf-8").lower()
    check(
        "ops console does not insert org_persons",
        "insert into org_persons" not in src,
    )
    check(
        "ops console does not invent a closer name field",
        "closer_name" not in src,
    )

    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(ROOT),
        text=True,
    )
    for path in FORBIDDEN_STAGE:
        check(f"not staged {path}", path not in staged)

    today_html = TODAY_HTML.read_text(encoding="utf-8")
    petty_html = PETTY_HTML.read_text(encoding="utf-8")
    check("Today page renders why", "c.why" in today_html)
    check("Today page renders classification", "classification_label" in today_html)
    check("petty page keeps NOT FOUND", "NOT FOUND" in petty_html)
    check("petty page says OPENING BALANCE REQUIRED", "OPENING BALANCE REQUIRED" in petty_html)

    td = tempfile.mkdtemp(prefix="uma-today-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        shutil.copy2(LIVE_DB, db)
        patch_catalog(ops, db)
        from core import audit as audit
        from core import venue_close as venue_close

        patch_catalog(audit, db)
        patch_catalog(venue_close, db)

        conn = ops.db_connect(db)
        ops.ensure_schema(conn)
        conn.execute("DELETE FROM bzg_ops_purchase_requests")
        conn.execute("DELETE FROM bzg_ops_petty_movements")
        conn.execute("DELETE FROM bzg_ops_petty_days")
        conn.commit()

        persons_before = conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]

        ops.insert_pr_row(
            pr_id="PR-UMA-LIVE-POLICY",
            state="POLICY_REQUIRED",
            supplier_name="Kitchen gas",
            purpose="Cylinder refill",
            example=False,
            conn=conn,
        )
        ops.insert_pr_row(
            pr_id="PR-UMA-EX-POLICY",
            state="POLICY_REQUIRED",
            supplier_name="Example equipment hire",
            purpose="Example policy row",
            example=True,
            conn=conn,
        )
        ops.insert_pr_row(
            pr_id="PR-UMA-EX-WAIT",
            state="REQUESTED",
            supplier_name="Example produce supplier",
            purpose="Weekend greens",
            example=True,
            conn=conn,
        )
        ops.seed_fixture_petty(conn)
        conn.commit()

        today = ops.today_cards(conn=conn)
        cards = today.get("cards") or []
        check("Today returns cards", isinstance(cards, list) and len(cards) >= 4, str(len(cards)))

        kinds = [c.get("kind") for c in cards]
        check("history teaser is last", kinds and kinds[-1] == "history", str(kinds))
        seen_quiet = False
        ordered = True
        for card in cards:
            if card.get("kind") == "history":
                continue
            if card.get("attention"):
                if seen_quiet:
                    ordered = False
            else:
                seen_quiet = True
        check("Today returns ordered attention cards", ordered, str(kinds))

        def one(kind: str) -> dict:
            return next(c for c in cards if c.get("kind") == kind)

        policy = one("policy_required")
        waiting = one("prs_waiting_approval")
        petty = one("petty_cash")
        close = one("daily_close")
        issues = one("issues")

        check(
            "live policy card sorts before example waiting card",
            kinds.index("policy_required") < kinds.index("prs_waiting_approval"),
            str(kinds),
        )
        check(
            "policy attention_count excludes example",
            policy.get("attention_count") == 1 and policy.get("example_count") == 1,
            str({k: policy.get(k) for k in ("attention_count", "example_count", "count")}),
        )
        check(
            "example waiting card attention_count is 0",
            waiting.get("attention_count") == 0 and waiting.get("example_count") == 1,
            str(waiting.get("attention_count")),
        )
        counts_ok = True
        for card in cards:
            if card.get("kind") in ("daily_close", "history"):
                continue
            items = card.get("items") or []
            live_n = sum(1 for item in items if not item.get("example"))
            ex_n = sum(1 for item in items if item.get("example"))
            if card.get("attention_count") != live_n or card.get("example_count") != ex_n:
                counts_ok = False
        check("example:true excluded from non-example attention counts", counts_ok)

        blocked_why = True
        blocked_detail = ""
        for card in cards:
            if not (card.get("blocked") or card.get("attention")):
                continue
            if not card.get("why") or not card.get("classification"):
                blocked_why = False
                blocked_detail = str(card.get("kind"))
                break
        check("why present on blocked cards", blocked_why, blocked_detail)
        check(
            "policy why is the helper sentence",
            policy.get("why") == WHY_POLICY_REQUIRED
            and policy.get("classification") == "NEEDS_POLICY"
            and policy.get("classification") != "NEEDS_MATT",
            str(policy.get("why")),
        )
        check(
            "daily close href points at existing route",
            close.get("href") == "/uma-blu-close",
            str(close.get("href")),
        )
        close_blob = close.get("close") or {}
        check(
            "daily close surfaces state only",
            "variance" not in close_blob
            and "threshold" not in close_blob
            and "closer" not in close
            and "closer_name" not in close_blob,
            str(close_blob),
        )
        check(
            "float still NOT_FOUND",
            today.get("float_status") == "NOT_FOUND"
            and today.get("opening_float") is None
            and (today.get("honesty") or {}).get("float") == "NOT_FOUND",
            str(today.get("float_status")),
        )
        petty_labels = " ".join(str(i.get("label") or "") for i in petty.get("items") or [])
        check(
            "petty card keeps float NOT FOUND",
            "NOT FOUND" in petty_labels and petty.get("title") == "OPENING BALANCE REQUIRED",
            petty.get("title"),
        )
        check(
            "petty why is opening-float helper sentence",
            petty.get("why") == WHY_OPENING_FLOAT
            and petty.get("classification") == "NEEDS_POLICY"
            and petty.get("attention_count") == 0,
            str(petty.get("why")),
        )
        listed = ops.list_petty(conn=conn)
        check(
            "petty list float_status NOT_FOUND",
            listed.get("float_status") == "NOT_FOUND" and listed.get("opening_float") is None,
            str(listed.get("float_status")),
        )
        check("issues card present", issues.get("href") == "/bzg/uma-blu/issues")
        check(
            "issues attention_count excludes examples",
            issues.get("attention_count")
            == sum(1 for i in (issues.get("items") or []) if not i.get("example")),
        )
        check(
            "history teaser reuses audit lines",
            isinstance(cards[-1].get("teaser"), list),
        )

        doc_path = ops.write_commissioning_readiness()
        persons_after = conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]
        check(
            "readiness write does not grant staff",
            persons_before == persons_after and doc_path.is_file(),
            f"{persons_before} -> {persons_after}",
        )
        doc = json.loads(doc_path.read_text(encoding="utf-8"))
        required = (
            "intended_operator_role",
            "permissions_required",
            "can",
            "cannot",
            "remaining_blockers",
            "commissioning_test_steps",
        )
        check(
            "commissioning doc has required fields",
            all(doc.get(key) for key in required),
            str(sorted(doc)),
        )
        check(
            "no live staff grant and no invented float or closer",
            doc.get("staff_grant") is False
            and doc.get("devi_auto_commission") is False
            and doc.get("invented_float") is False
            and doc.get("invented_closer") is False
            and doc.get("human_commissioning") == "NOT_DONE",
            str(doc.get("staff_grant")),
        )
        blockers = {b.get("id"): b for b in doc.get("remaining_blockers") or []}
        check(
            "readiness float blocker stays NOT_FOUND",
            (blockers.get("opening_float") or {}).get("status") == "NOT_FOUND",
            str(blockers.get("opening_float")),
        )
        closer = blockers.get("closer") or {}
        check(
            "readiness closer is waiting not a named person",
            "WAITING" in str(closer.get("status") or "")
            and "Devi" not in str(closer.get("status") or ""),
            str(closer.get("status")),
        )
        conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
