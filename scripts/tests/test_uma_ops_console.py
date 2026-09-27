#!/usr/bin/env python3
"""Uma Blu ops console — mandatory behaviours (Beta). Temp DB only.

Prove: request ≠ approval; no authority → POLICY_REQUIRED; paid claim ≠ verified;
no write helpers to forbidden systems; Today hides ids / labels fixtures;
Issues empty when clean; existing daily close tests still pass.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
OPS_PY = SCRIPTS / "core" / "uma_ops_console.py"
MIG = SCRIPTS / "migrations" / "migrate_uma_ops_console.py"
CLOSE_TEST = SCRIPTS / "tests" / "test_uma_blu_daily_close.py"

PASS = 0
FAIL = 0
TS = "2026-09-18T00:00:00+08:00"

FORBIDDEN_WRITE_TERMS = (
    "clickup",
    "telegram",
    "esb_write",
    "push_esb",
    "bank_write",
    "write_to_bank",
)


def esb_refusal_only(src_lower: str) -> tuple[bool, str]:
    """The substring esb_write is the off-flag and the refusal, not a writer.

    test_bzg_loop_closure.py requires def refuse_esb_write, code
    esb_write_refused, and \"esb_write\": False. A bare substring ban
    cannot be true at the same time. Anything outside those forms fails.
    """
    if "def refuse_esb_write" not in src_lower:
        return False, "refuse_esb_write missing"
    if '"esb_write": true' in src_lower or "'esb_write': true" in src_lower:
        return False, "esb_write set true"
    residual = src_lower
    for allowed in (
        '"esb_write": false',
        "def refuse_esb_write",
        "refuse_esb_write(",
        "esb_write_refused",
    ):
        residual = residual.replace(allowed, "")
    if "esb_write" in residual:
        i = residual.find("esb_write")
        return False, residual[max(0, i - 40) : i + 48]
    return True, ""


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_ops():
    spec = importlib.util.spec_from_file_location("uma_ops_console", OPS_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def patch_catalog(mod, path: Path) -> None:
    mod.CATALOG_DB = path
    if hasattr(mod, "LIVE_CATALOG_DB"):
        # Keep live guard pointing at real live so temp writes are allowed
        pass


def grant_payment_perm(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (
          'PERM-BZG-PR-PAYMENT-APPROVE', 'bzg.pr.payment_approve',
          'bzg', 'payment_approve', 'test', 'ACTIVE', ?, ?
        )
        ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-MATT', 'PERM-BZG-PR-PAYMENT-APPROVE', 'ALLOW', ?, ?)
        """,
        (TS, TS),
    )
    # Ensure zero authority limits for this permission in temp DB
    conn.execute(
        "DELETE FROM org_authority_limits WHERE permission_id='PERM-BZG-PR-PAYMENT-APPROVE'"
    )
    conn.commit()


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"

    # --- Source hygiene: no write helpers toward forbidden systems ---
    src = OPS_PY.read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_WRITE_TERMS:
        if term == "esb_write":
            ok, detail = esb_refusal_only(src)
            check("no write helper term esb_write", ok, detail or "found in uma_ops_console.py")
        else:
            check(
                f"no write helper term {term}",
                term not in src,
                "found in uma_ops_console.py",
            )
    # Also refuse importing wolf-system bzg push scripts
    check(
        "no wolf-system bzg import",
        "bzg-pr-push" not in src and "bzg-pr-approve" not in src,
    )

    td = tempfile.mkdtemp(prefix="uma-ops-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        shutil.copy2(LIVE_DB, db)

        ops = load_ops()
        patch_catalog(ops, db)

        # Patch dependencies that share CATALOG_DB
        from core import audit as audit
        from core import authority as authority
        from core import evidence as evidence
        from core import venue_close as venue_close
        from core import work_items as work_items

        for m in (audit, authority, evidence, venue_close, work_items, ops):
            patch_catalog(m, db)

        conn = ops.db_connect(db)
        ops.ensure_schema(conn)
        grant_payment_perm(conn)

        # --- request ≠ approval ---
        created = ops.create_pr(
            requester_label="Example requester",
            supplier_name="Example greens",
            purpose="Test request only",
            expected_value=100000.0,
            currency="IDR",
            requested_date="2026-09-18",
            example=True,
            actor_type="SYSTEM",
            conn=conn,
            commit=True,
        )
        check(
            "request does not equal approval",
            created["state"] == "REQUESTED",
            str(created["state"]),
        )
        check(
            "create stays REQUESTED until transition",
            created["state"] != "APPROVED",
        )

        approved = ops.transition_pr(
            created["pr_id"],
            "APPROVED",
            verified_person_id="PERS-MATT",
            actor_type="PERSON",
            conn=conn,
            commit=True,
        )
        check(
            "approval is a separate transition",
            approved["state"] == "APPROVED",
            str(approved["state"]),
        )

        # Walk to PAYMENT_REQUESTED then attempt PAYMENT_APPROVED with no limit
        cur = created["pr_id"]
        for step in (
            "ORDERED",
            "RECEIVED",
            "BILL_RECEIVED",
            "PAYMENT_REQUESTED",
        ):
            ops.transition_pr(
                cur,
                step,
                verified_person_id="PERS-MATT",
                actor_type="PERSON",
                conn=conn,
                commit=True,
            )

        money = ops.transition_pr(
            cur,
            "PAYMENT_APPROVED",
            verified_person_id="PERS-MATT",
            actor_type="PERSON",
            conn=conn,
            commit=True,
        )
        check(
            "money step with no authority limit → POLICY_REQUIRED",
            money["state"] == "POLICY_REQUIRED",
            str(money.get("state")),
        )
        check(
            "money step did not approve payment",
            money["state"] != "PAYMENT_APPROVED",
        )

        events = audit.list_events(
            entity_id="ENT-BZG",
            source="uma_ops_console",
            limit=50,
            conn=conn,
        )
        pr_events = [
            e
            for e in events
            if e.get("resource_id") == cur and e.get("source") == "uma_ops_console"
        ]
        check(
            "transition writes uma_ops_console audit",
            any((e.get("action") or "").startswith("bzg.pr.") for e in pr_events),
            str([e.get("action") for e in pr_events][:8]),
        )
        hist = ops.list_history(conn=conn, limit=40)
        lines = [
            ln
            for ln in (hist.get("events") or [])
            if (ln.get("sentence") or "").strip()
        ]
        check(
            "history returns non-empty human line after transition",
            len(lines) >= 1,
            str(hist)[:240],
        )
        primary = next((ln for ln in lines if ln.get("resource_id") == cur), lines[0] if lines else {})
        sent = primary.get("sentence") or ""
        check(
            "history primary label is a human sentence",
            bool(sent)
            and cur not in sent
            and "PERS-" not in sent
            and not sent.startswith(("PR-", "PETTY-", "WI-", "ENT-", "EVD-", "bzg.")),
            sent,
        )

        # --- paid claim does not set verified ---
        # Seed a payment-approved fixture path via direct insert then claim
        ops.insert_pr_row(
            pr_id="PR-UMA-TEST-CLAIM",
            state="PAYMENT_APPROVED",
            requester_label="Example requester",
            supplier_name="Example dairy",
            purpose="Claim test",
            expected_value=50000.0,
            currency="IDR",
            payment_evidence_id="EVD-TEST-CLAIM-ONLY",
            example=True,
            conn=conn,
        )
        conn.commit()
        claimed = ops.transition_pr(
            "PR-UMA-TEST-CLAIM",
            "PAID_CLAIMED",
            verified_person_id="PERS-MATT",
            actor_type="PERSON",
            payment_evidence_id="EVD-TEST-CLAIM-ONLY",
            conn=conn,
            commit=True,
        )
        check(
            "paid claim does not set verified",
            claimed["state"] == "PAID_CLAIMED",
            str(claimed["state"]),
        )
        check(
            "paid claim is not PAYMENT_VERIFIED",
            claimed["state"] != "PAYMENT_VERIFIED",
        )

        # --- Today: fixtures labelled, no engineering ids on card surface ---
        ops.seed_fixture_prs(conn)
        conn.commit()
        today = ops.today_cards(conn=conn)
        check("Today returns cards structure", isinstance(today.get("cards"), list))
        check(
            "Today labels fixtures",
            today.get("fixture_notice") is True
            or any(
                it.get("example")
                for c in today.get("cards", [])
                for it in c.get("items", [])
            ),
        )
        # Card titles and item labels must not expose raw engineering ids as the headline
        surface = []
        for c in today.get("cards", []):
            surface.append(c.get("title") or "")
            for it in c.get("items", []):
                surface.append(it.get("label") or "")
        joined = " | ".join(surface)
        check(
            "Today card surface hides engineering ids",
            "PERS-" not in joined and "WI-" not in joined and "ASG-" not in joined,
            joined[:200],
        )
        # Example label present when fixture items shown
        example_labels = [
            it.get("label", "")
            for c in today.get("cards", [])
            for it in c.get("items", [])
            if it.get("example")
        ]
        check(
            "fixture cards say Example",
            all("Example" in lab for lab in example_labels) if example_labels else True,
            str(example_labels[:3]),
        )

        # --- Issues empty when nothing wrong ---
        conn.execute("DELETE FROM bzg_ops_purchase_requests")
        try:
            conn.execute("DELETE FROM bzg_ops_petty_movements")
            conn.execute("DELETE FROM bzg_ops_petty_days")
        except sqlite3.OperationalError:
            pass
        # No EXCEPTION closes assumed in temp (copy may have some — filter)
        # Clear any EXCEPTION closes in temp for this check
        try:
            conn.execute(
                "UPDATE venue_daily_closes SET state='OPEN' WHERE state='EXCEPTION'"
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()
        issues = ops.list_issues(conn=conn)
        check(
            "Issues stay empty when nothing is wrong",
            issues.get("empty") is True and len(issues.get("issues") or []) == 0,
            str(issues),
        )

        # POLICY_REQUIRED surfaces as issue
        ops.insert_pr_row(
            pr_id="PR-UMA-TEST-ISSUE",
            state="POLICY_REQUIRED",
            purpose="Needs policy",
            example=True,
            conn=conn,
        )
        conn.commit()
        issues2 = ops.list_issues(conn=conn)
        check(
            "POLICY_REQUIRED appears in Issues",
            len(issues2.get("issues") or []) >= 1,
            str(issues2),
        )

        conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

    # --- existing daily close tests still pass ---
    env = os.environ.copy()
    env["WOLF_TEST_MODE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(CLOSE_TEST)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"PASS=(\d+)\s+FAIL=(\d+)", out)
    if m:
        close_fail = int(m.group(2))
        check(
            "existing test_uma_blu_daily_close still passes",
            close_fail == 0 and proc.returncode == 0,
            f"rc={proc.returncode} {m.group(0)}",
        )
    else:
        check(
            "existing test_uma_blu_daily_close still passes",
            proc.returncode == 0,
            out[-500:],
        )

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
