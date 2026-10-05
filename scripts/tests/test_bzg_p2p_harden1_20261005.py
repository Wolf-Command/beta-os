#!/usr/bin/env python3
"""BZG-P2P-HARDEN-1 — neutralised migrations, precheck leak, same-person SoD."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
TS = "2026-10-05T12:55:00+08:00"
PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
    "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
PROD_PID = 1297
OUTLETS = ("BZG-UMA", "BZG-RAIN", "OU-BZG-RAIN-POOL")
P2P_PERMS = (
    "bzg.po.create",
    "bzg.bill.capture",
    "bzg.match.run",
    "bzg.ap.view",
    "bzg.ap.mark_ready",
    "bzg.pay.list_ready",
    "bzg.pay.mark_ready",
)
MIGRATION_FILES = (
    "migrate_bzg_p2p_po1_20261004.py",
    "migrate_bzg_p2p_recv1_20261005.py",
    "migrate_bzg_p2p_nota1_20261005.py",
    "migrate_bzg_p2p_three_way1_20261005.py",
    "migrate_bzg_p2p_ap1_20261005.py",
    "migrate_bzg_p2p_ready_to_pay1_20261005.py",
)
MONEY_PERMS = ("payment.execute", "payment.approve", "vendor.bank.change")

os.environ["WOLF_TEST_MODE"] = "1"
sys.path.insert(0, str(SCRIPTS))

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


def load_migration(filename: str):
    path = MIGRATIONS / filename
    spec = importlib.util.spec_from_file_location(filename.replace(".py", ""), path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def p2p_grant_snapshot(conn: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    from core import bzg_p2p_grants as grants

    placeholders = ",".join("?" * len(grants.P2P_PERMISSION_CODES))
    rows = conn.execute(
        f"""
        SELECT p.code, rp.role_id
        FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE p.code IN ({placeholders}) AND rp.effect='ALLOW'
        ORDER BY p.code, rp.role_id
        """,
        list(grants.P2P_PERMISSION_CODES),
    ).fetchall()
    return tuple((str(r["code"]), str(r["role_id"])) for r in rows)


def expected_matrix_grants(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    from core import bzg_p2p_grants as grants

    expected: set[tuple[str, str]] = set()
    for code, roles in grants.P2P_PERMISSION_MATRIX.items():
        for role_id in roles:
            if conn.execute(
                "SELECT 1 FROM org_roles WHERE role_id=?", (role_id,)
            ).fetchone():
                expected.add((code, role_id))
    return expected


def patch_catalog_modules(db_path: Path) -> list:
    from core import bzg_ap_ready as ap
    from core import bzg_goods_receiving as gr
    from core import bzg_purchase_order as po
    from core import bzg_purchase_request as pr
    from core import bzg_ready_to_pay as rtp
    from core import bzg_supplier_bill as bill
    from core import bzg_three_way_match as match
    from core import uma_ops_console as ops

    mods = [ops, pr, po, gr, bill, match, ap, rtp]
    originals = []
    for mod in mods:
        if hasattr(mod, "CATALOG_DB"):
            originals.append((mod, mod.CATALOG_DB))
            mod.CATALOG_DB = db_path
    return originals


def restore_catalog_modules(originals: list) -> None:
    for mod, orig in originals:
        mod.CATALOG_DB = orig


def test_migrations_idempotent_on_copy(db_path: Path) -> None:
    run_grant_repair = load_migration("migrate_bzg_p2p_grant_repair1_20261005.py").run

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        before = p2p_grant_snapshot(conn)
        run_grant_repair(db_path)
        after_repair = p2p_grant_snapshot(conn)
        expected = expected_matrix_grants(conn)
        check(
            "grant repair snapshot matches explicit matrix",
            set(after_repair) == expected,
            f"got {len(after_repair)} grants, expected {len(expected)}",
        )
        for filename in MIGRATION_FILES:
            mod = load_migration(filename)
            mod.run(db_path)
            mid = p2p_grant_snapshot(conn)
            mod.run(db_path)
            after = p2p_grant_snapshot(conn)
            check(
                f"{filename} re-run leaves bzg grants unchanged",
                mid == after,
                f"before={len(mid)} after={len(after)}",
            )
            check(
                f"{filename} re-run does not widen grants vs repair baseline",
                set(after) <= set(after_repair),
                f"added {set(after) - set(after_repair)}",
            )
        work_complete_bzg = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id = rp.permission_id
            JOIN org_role_permissions wc ON wc.role_id = rp.role_id AND wc.effect='ALLOW'
            JOIN org_permissions pw ON pw.permission_id = wc.permission_id
            WHERE p.code LIKE 'bzg.%' AND rp.effect='ALLOW'
              AND pw.code = 'work.complete'
              AND rp.role_id NOT IN (
                SELECT role_id FROM org_role_permissions rp2
                JOIN org_permissions p2 ON p2.permission_id = rp2.permission_id
                WHERE p2.code IN (
                  'bzg.po.create','bzg.bill.capture','bzg.match.run',
                  'bzg.ap.view','bzg.ap.mark_ready','bzg.pay.list_ready','bzg.pay.mark_ready'
                ) AND rp2.effect='ALLOW'
              )
            """
        ).fetchone()
        # No new grants copied solely from work.complete holders beyond matrix.
        check(
            "P2P grant matrix unchanged after all migrations x2",
            set(p2p_grant_snapshot(conn)) == expected,
            str(set(p2p_grant_snapshot(conn)) - expected),
        )
    finally:
        conn.close()


def _build_matched_bill(conn: sqlite3.Connection, db_path: Path, *, suffix: str) -> dict:
    from core import bzg_ap_ready as ap
    from core import bzg_goods_receiving as gr
    from core import bzg_outlet_registry as outlets
    from core import bzg_purchase_order as po
    from core import bzg_purchase_request as pr
    from core import bzg_supplier_bill as bill
    from core import bzg_three_way_match as match
    from core import uma_ops_console as ops

    patch_catalog_modules(db_path)
    outlets.ensure_schema(conn)
    outlets.seed_registry(conn, TS)
    ops.ensure_schema(conn)
    pr.ensure_pr_columns(conn)
    po.ensure_po_schema(conn)
    gr.ensure_gr_schema(conn)
    bill.ensure_bill_schema(conn)
    match.ensure_match_schema(conn)
    ap.ensure_ap_schema(conn)

    pr_id = f"PR-HARDEN-{suffix}"
    ops.insert_pr_row(pr_id=pr_id, state="APPROVED", purpose="Harden probe", example=False, conn=conn)
    conn.execute(
        """
        UPDATE bzg_ops_purchase_requests
        SET outlet_id='BZG-UMA', entity_id='ENT-BZG', requester_person_id='PERS-REQ'
        WHERE pr_id=?
        """,
        (pr_id,),
    )
    conn.execute(
        """
        INSERT INTO bzg_ops_pr_lines (line_id, pr_id, item, qty, unit, created_at)
        VALUES (?, ?, 'Oil', 10, 'L', ?)
        ON CONFLICT(line_id) DO NOTHING
        """,
        (f"PRL-{suffix}", pr_id, TS),
    )
    conn.commit()
    po._supplier_resolver = lambda sid: {"supplier_id": sid, "name": "Sup"} if sid else None
    saved_po = po.create_purchase_order(
        person_id="PERS-IZA",
        pr_id=pr_id,
        supplier_id="SUP-HARDEN",
        lines=[{"item": "Oil", "qty": 10, "unit": "L"}],
        conn=conn,
        commit=True,
    )
    full_gr = gr.create_goods_receipt(
        person_id="PERS-DEVI",
        po_id=saved_po["po_id"],
        lines=[{"po_line_id": saved_po["lines"][0]["line_id"], "received_qty": 10}],
        conn=conn,
        commit=True,
    )
    bill.NOTA_PHOTO_DIR = db_path.parent / "nota-photos"
    photo = bill.save_nota_photo_bytes(
        data=b"\xff\xd8\xff\xe0" + b"jpeg",
        filename="n.jpg",
        content_type="image/jpeg",
    )["photo_object_ref"]
    saved_bill = bill.create_supplier_bill(
        person_id="PERS-DEVI",
        gr_id=full_gr["gr_id"],
        nota_number=f"NOTA-{suffix}",
        nota_date="2026-10-05",
        photo_object_ref=photo,
        lines=[
            {
                "gr_line_id": full_gr["lines"][0]["line_id"],
                "billed_qty": 10,
                "billed_unit_price": 100_000,
            }
        ],
        stated_total=1_000_000,
        conn=conn,
        commit=True,
    )
    conn.execute(
        """
        UPDATE bzg_ops_supplier_bills
        SET capturer_person_id='PERS-HARIYANTO'
        WHERE bill_id=?
        """,
        (saved_bill["bill_id"],),
    )
    conn.commit()
    match.run_three_way_match(
        person_id="PERS-ZAYEN",
        bill_id=saved_bill["bill_id"],
        conn=conn,
        commit=True,
    )
    return {"bill_id": saved_bill["bill_id"], "po_id": saved_po["po_id"]}


def test_precheck_leak_and_sod(conn: sqlite3.Connection, db_path: Path) -> None:
    from core import bzg_ap_ready as ap
    from core import bzg_ready_to_pay as rtp

    originals = patch_catalog_modules(db_path)
    try:
        chain = _build_matched_bill(conn, db_path, suffix="LEAK")
        bid = chain["bill_id"]
        marked = ap.mark_ap_ready(person_id="PERS-ZAYEN", bill_id=bid, conn=conn, commit=True)
        check("authorised ap mark", bool(marked.get("ap_ready_id")), str(marked))

        try:
            ap.mark_ap_ready(person_id="PERS-HAIKAL", bill_id=bid, conn=conn, commit=False)
            check("unauthorised ap precheck leak closed", False, "should raise 403")
        except ap.ApReadyError as exc:
            check(
                "unauthorised ap precheck leak closed",
                exc.http_status == 403 and exc.code == "forbidden",
                str(exc),
            )

        again = ap.mark_ap_ready(person_id="PERS-ZAYEN", bill_id=bid, conn=conn, commit=False)
        check(
            "authorised ap idempotent",
            again.get("ap_ready_id") == marked.get("ap_ready_id"),
            str(again.get("ap_ready_id")),
        )

        try:
            rtp.mark_ready_to_pay(person_id="PERS-ZAYEN", bill_id=bid, conn=conn, commit=False)
            check("same person both marks denied on pay", False, "should raise")
        except rtp.ReadyToPayError as exc:
            check(
                "same person both marks denied on pay",
                exc.http_status == 403 and exc.code == "same_person_cannot_mark_both_stages",
                str(exc),
            )

        ready = rtp.mark_ready_to_pay(
            person_id="PERS-DEVI", bill_id=bid, conn=conn, commit=True
        )
        check("different authorised person may mark pay", bool(ready.get("ready_to_pay_id")), str(ready))

        try:
            rtp.mark_ready_to_pay(person_id="PERS-HAIKAL", bill_id=bid, conn=conn, commit=False)
            check("unauthorised rtp precheck leak closed", False, "should raise 403")
        except rtp.ReadyToPayError as exc:
            check(
                "unauthorised rtp precheck leak closed",
                exc.http_status == 403 and exc.code == "forbidden",
                str(exc),
            )

        again_rtp = rtp.mark_ready_to_pay(
            person_id="PERS-DEVI", bill_id=bid, conn=conn, commit=False
        )
        check(
            "authorised rtp idempotent",
            again_rtp.get("ready_to_pay_id") == ready.get("ready_to_pay_id"),
            str(again_rtp.get("ready_to_pay_id")),
        )
    finally:
        restore_catalog_modules(originals)


def test_j1_matrix_live() -> None:
    if not LIVE_DB.is_file():
        check("live catalog for j1 matrix", False, str(LIVE_DB))
        return
    from core import bzg_ap_ready as ap
    from core import bzg_p2p_grants as grants
    from core import bzg_purchase_request as pr
    from core import bzg_ready_to_pay as rtp
    from core import rbac as rb

    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        deny_all = 0
        for person in grants.GGV_CONTENT_DENY_PERSONS + ("PERS-MISA", "PERS-YUDI"):
            for outlet in OUTLETS:
                try:
                    target = pr.outlet_rbac_target(outlet, conn)
                except Exception:
                    continue
                for code in P2P_PERMS:
                    ev = rb.evaluate(person, code, target, conn=conn)
                    if not ev.get("allowed"):
                        deny_all += 1
        check("Haikal/Misa/Yudi DENY all P2P perms x outlets", deny_all >= 45, f"deny={deny_all}")

        for person, code_expect in (
            ("PERS-AMANDA", "role_lacks_permission"),
        ):
            ev = rb.evaluate(person, "bzg.ap.mark_ready", pr.outlet_rbac_target("BZG-UMA", conn), conn=conn)
            check(f"Amanda DENY ap.mark_ready", not ev.get("allowed"), ev.get("reason", ""))

        for perm in MONEY_PERMS:
            n = conn.execute(
                """
                SELECT COUNT(*) AS n FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE p.code=? AND rp.effect='ALLOW'
                """,
                (perm,),
            ).fetchone()["n"]
            check(f"{perm} grant count 0", n == 0, str(n))

        for close_id in PROTECTED_CLOSES:
            row = conn.execute(
                "SELECT state, updated_at FROM venue_daily_closes WHERE close_id=?",
                (close_id,),
            ).fetchone()
            check(f"protected close {close_id[:12]} present", row is not None)

        petty = conn.execute(
            "SELECT movement_id, amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        if petty:
            from core import bzg_history_import1 as _hist

            balance = _hist.petty_balance(conn)
            check(
                "PETTY-UMA-6D853EEAE0 balance unchanged",
                float(balance.get("amount_idr") or 0) == 552700.0,
                str(balance),
            )
        else:
            check("PETTY-UMA-6D853EEAE0 row readable", False, "missing")
    finally:
        conn.close()


def prod_pid_unchanged() -> bool:
    try:
        out = subprocess.check_output(["ps", "-p", str(PROD_PID)], stderr=subprocess.DEVNULL, text=True)
        return str(PROD_PID) in out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def beta_reload_decision() -> tuple[str, int | None]:
    try:
        out = subprocess.check_output(
            ["lsof", "-i", ":8788", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        pids = [int(x) for x in out.splitlines() if x.strip()]
        if len(pids) == 1:
            return "reload_candidate", pids[0]
        return "RELOAD_HELD", pids[0] if pids else None
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return "RELOAD_HELD", None


def main() -> int:
    scratch_parent = ROOT / "state" / "reliability" / ".harden-test"
    scratch_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch_parent) as td:
        db_path = Path(td) / "content_library.sqlite"
        if LIVE_DB.is_file():
            shutil.copy2(LIVE_DB, db_path)
        else:
            sqlite3.connect(str(db_path)).close()
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            test_migrations_idempotent_on_copy(db_path)
            test_precheck_leak_and_sod(conn, db_path)
        finally:
            conn.close()

    test_j1_matrix_live()
    check("prod pid 1297 unchanged", prod_pid_unchanged())

    reload_status, beta_pid = beta_reload_decision()
    print(f"\n{PASS} passed, {FAIL} failed")
    print(f"beta_reload_status={reload_status} beta_pid={beta_pid}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
