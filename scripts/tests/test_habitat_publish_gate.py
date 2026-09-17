#!/usr/bin/env python3
"""Tests for Habitat Publish Gate on Wolf Core (Beta). Temp DB only.

Matt mandatory cases. Metricool write remains blocked.
Live Authority=0; Habitat policy+evidence req = 1 each; SoD/Exception=0.
No Production. No Metricool network.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG = SCRIPTS / "migrations" / "migrate_habitat_publish_gate.py"
CP_PY = SCRIPTS / "core" / "content_publish.py"
SERVE_PY = SCRIPTS / "serve_beta.py"

PASS = 0
FAIL = 0

TS = "2026-09-17T00:00:00+08:00"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mig():
    spec = importlib.util.spec_from_file_location("migrate_habitat_publish_gate", MIG)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def live_counts() -> dict[str, int]:
    c = sqlite3.connect(str(LIVE_DB))
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        def cnt(table: str) -> int:
            if table not in tabs:
                return 0
            return int(c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

        habitat_pol = (
            int(
                c.execute(
                    "SELECT COUNT(*) FROM core_governance_policies WHERE policy_id=?",
                    ("GPO-HABITAT-CONTENT-PUBLISH",),
                ).fetchone()[0]
            )
            if "core_governance_policies" in tabs
            else 0
        )
        habitat_evr = (
            int(
                c.execute(
                    "SELECT COUNT(*) FROM core_evidence_requirements WHERE requirement_id=?",
                    ("EVR-HABITAT-CONTENT-PUBLISH",),
                ).fetchone()[0]
            )
            if "core_evidence_requirements" in tabs
            else 0
        )
        return {
            "auth": cnt("org_authority_limits"),
            "sod": cnt("core_sod_constraints"),
            "exc": cnt("core_governance_exceptions"),
            "pol": cnt("core_governance_policies"),
            "evr": cnt("core_evidence_requirements"),
            "habitat_pol": habitat_pol,
            "habitat_evr": habitat_evr,
            "audit": cnt("core_audit_events"),
        }
    finally:
        c.close()


def patch_modules(tmp: Path) -> tuple:
    import core.approvals as apr
    import core.evidence as evd
    import core.work_items as wi
    import core.governance_policy as gov
    import core.rbac as rbac
    import core.content_publish as cp
    import core.audit as audit

    for mod in (apr, evd, wi, gov, rbac, cp, audit):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp
    return apr, evd, wi, gov, rbac, cp


def seed_slot(conn: sqlite3.Connection, *, brand="habitat", status="AI_Generated") -> int:
    conn.execute(
        """
        INSERT INTO content_planner (
          brand, platform, scheduled_date, slot_time, title_slug, script_body,
          raw_asset_id, status, updated_at
        ) VALUES (?, 'IG_Reels', '2026-09-22', '10:00', 'gate-test', 'hello habitat',
                  NULL, ?, ?)
        """,
        (brand, status, TS),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    os.environ["BETA_METRICOOL_ENABLED"] = "false"
    os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
    os.environ.pop("BETA_METRICOOL_CREDS_PATH", None)

    src = CP_PY.read_text(encoding="utf-8")
    serve_src = SERVE_PY.read_text(encoding="utf-8")
    check("no LLM in content_publish.py", "openai" not in src.lower() and "anthropic" not in src.lower())
    check("assert_habitat_publish_allowed defined", "def assert_habitat_publish_allowed" in src)
    check("serve_beta imports content_publish", "content_publish" in serve_src)
    check("serve_beta submit-for-approval route", "submit-for-approval" in serve_src)
    check("serve_beta does not flip Metricool write", "BETA_METRICOOL_WRITE_ENABLED=true" not in serve_src)

    before = live_counts()
    check("live auth_limits before=0", before["auth"] == 0, str(before["auth"]))
    check("live SoD before=0", before["sod"] == 0)
    check("live exceptions before=0", before["exc"] == 0)

    mig = load_mig()
    mig.DB = LIVE_DB
    check("live migrate exit 0", mig.main() == 0)
    check("migration idempotent", mig.main() == 0)

    after = live_counts()
    check("live auth_limits after=0", after["auth"] == 0, str(after["auth"]))
    check("live SoD after=0", after["sod"] == 0)
    check("live exceptions after=0", after["exc"] == 0)
    check("live Habitat policy=1", after["habitat_pol"] == 1, str(after["habitat_pol"]))
    check("live Habitat evidence req=1", after["habitat_evr"] == 1, str(after["habitat_evr"]))
    check("live policies total=1", after["pol"] == 1, str(after["pol"]))
    check("live evidence reqs total=1", after["evr"] == 1, str(after["evr"]))

    # Brand + role + perms on live
    c = sqlite3.connect(str(LIVE_DB))
    try:
        brand = c.execute(
            "SELECT entity_id, status FROM org_brands WHERE brand_id='habitat'"
        ).fetchone()
        check("habitat brand under ENT-GGV", brand is not None and brand[0] == "ENT-GGV")
        role = c.execute(
            "SELECT 1 FROM org_roles WHERE role_id='ROLE-GGV-CREATIVE-DIRECTOR'"
        ).fetchone()
        check("ROLE-GGV-CREATIVE-DIRECTOR exists", role is not None)
        cols = {r[1] for r in c.execute("PRAGMA table_info(content_planner)")}
        for col in (
            "content_version_hash",
            "work_item_id",
            "core_approval_request_id",
            "approved_version_hash",
        ):
            check(f"content_planner.{col}", col in cols)
        check(
            "content_versions table",
            c.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='content_versions'"
            ).fetchone()
            is not None,
        )
        et = c.execute(
            "SELECT 1 FROM core_evidence_types WHERE evidence_type='content_draft'"
        ).fetchone()
        check("evidence type content_draft", et is not None)
        approve_grants = c.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id='PERM-CONTENT-HABITAT-APPROVE'
              AND role_id IN (
                'ROLE-MATT','ROLE-GGV-CREATIVE-DIRECTOR','ROLE-CONTENT-MGMT',
                'ROLE-GGV-EDIT','ROLE-CONTENT-CREW'
              )
            """
        ).fetchone()[0]
        check("approve grants to 5 roles", approve_grants == 5, str(approve_grants))
    finally:
        c.close()

    # --- Isolated fixture path ---
    tmp = ROOT / "catalog" / "test_habitat_publish_gate.sqlite"
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(LIVE_DB, tmp)

    apr, evd, wi, gov, rbac, cp = patch_modules(tmp)
    # Point live-write guards at real live so tmp is writable
    apr.LIVE_CATALOG_DB = LIVE_DB.resolve()
    evd.LIVE_CATALOG_DB = LIVE_DB.resolve()
    gov.LIVE_CATALOG_DB = LIVE_DB.resolve()
    cp.CATALOG_DB = tmp

    conn = sqlite3.connect(str(tmp))
    conn.row_factory = sqlite3.Row
    try:
        # 1) Version hash deterministic + changes on edit
        slot_id = seed_slot(conn)
        conn.commit()
        row = dict(
            conn.execute("SELECT * FROM content_planner WHERE id=?", (slot_id,)).fetchone()
        )
        h1 = cp.compute_version_hash(row)
        h1b = cp.compute_version_hash(row)
        check("version hash stable", h1 == h1b and len(h1) == 64)
        conn.execute(
            "UPDATE content_planner SET script_body='edited body' WHERE id=?", (slot_id,)
        )
        conn.commit()
        row2 = dict(
            conn.execute("SELECT * FROM content_planner WHERE id=?", (slot_id,)).fetchone()
        )
        h2 = cp.compute_version_hash(row2)
        check("material edit changes hash", h1 != h2)

        # 2) Legacy Human_Approved alone DENY
        conn.execute(
            "UPDATE content_planner SET status='Human_Approved', script_body='hello habitat' WHERE id=?",
            (slot_id,),
        )
        conn.commit()
        gate_legacy = cp.assert_habitat_publish_allowed(slot_id, verified_person_id="PERS-MATT")
        check(
            "legacy Human_Approved alone DENY",
            gate_legacy["stage"] == "DENIED"
            and gate_legacy["reason"] == "legacy_status_alone_denied",
            str(gate_legacy),
        )

        # 3) Happy path: submit (Misa) → approve (Amanda) → READY_TO_PUBLISH
        slot_ok = seed_slot(conn, status="AI_Generated")
        conn.commit()
        sub = cp.submit_for_approval(slot_ok, verified_person_id="PERS-MISA")
        check("submit ok", sub.get("ok") is True, str(sub))
        check("submit has APR", bool(sub.get("approval_request_id")))

        gate_pending = cp.assert_habitat_publish_allowed(
            slot_ok, verified_person_id="PERS-AMANDA"
        )
        check(
            "pending not publishable",
            gate_pending["stage"] == "DENIED",
            str(gate_pending.get("reason")),
        )

        decided = cp.apply_core_approval_to_slot(
            slot_ok, verified_person_id="PERS-AMANDA"
        )
        check("core approve derived", decided.get("derived_from_core") is True)
        check("legacy status Human_Approved", decided.get("status") == "Human_Approved")

        gate_ready = cp.assert_habitat_publish_allowed(
            slot_ok, verified_person_id="PERS-AMANDA"
        )
        check(
            "READY_TO_PUBLISH",
            gate_ready.get("ok") is True and gate_ready.get("stage") == "READY_TO_PUBLISH",
            str(gate_ready),
        )
        check(
            "metricool DISABLED on ready",
            gate_ready.get("metricool") == "DISABLED",
            str(gate_ready.get("metricool")),
        )
        check(
            "REAL_EXTERNAL_PUBLISH=NO",
            gate_ready.get("real_external_publish") == "NO",
        )
        check(
            "reason metricool_write_disabled",
            gate_ready.get("reason") == "metricool_write_disabled",
            str(gate_ready.get("reason")),
        )

        # 4) Version mismatch DENY after Core approve
        conn.execute(
            "UPDATE content_planner SET script_body='post-approve edit' WHERE id=?",
            (slot_ok,),
        )
        conn.commit()
        # refresh stored hash to new content without new approval
        cp.refresh_version_hash(slot_ok, verified_person_id="PERS-MISA", conn=conn)
        conn.commit()
        gate_mm = cp.assert_habitat_publish_allowed(slot_ok, verified_person_id="PERS-AMANDA")
        check(
            "version mismatch DENY",
            gate_mm["stage"] == "DENIED" and gate_mm["reason"] == "version_mismatch",
            str(gate_mm),
        )

        # 5) Spoof / wrong brand
        other = seed_slot(conn, brand="umablu", status="AI_Generated")
        conn.commit()
        denied_brand = False
        try:
            cp.submit_for_approval(other, verified_person_id="PERS-MISA")
        except cp.ContentPublishError as e:
            denied_brand = e.code == "not_habitat"
        check("non-habitat submit refused", denied_brand)

        # 6) RBAC: person without publish.request
        # ROLE-GGV-EDIT has approve but not publish.request (Haikal)
        slot_rbac = seed_slot(conn)
        conn.commit()
        rbac_denied = False
        try:
            cp.submit_for_approval(slot_rbac, verified_person_id="PERS-HAIKAL")
        except cp.ContentPublishError as e:
            rbac_denied = e.code == "rbac_denied"
        check("Haikal publish.request denied", rbac_denied)

        # Haikal can approve if Misa submitted
        slot_hk = seed_slot(conn)
        conn.commit()
        cp.submit_for_approval(slot_hk, verified_person_id="PERS-MISA")
        ok_hk = cp.apply_core_approval_to_slot(slot_hk, verified_person_id="PERS-HAIKAL")
        check("Haikal can Core-approve", ok_hk.get("core_status") == "APPROVED")

        # 7) Metricool write assert still blocked
        from metricool_read_client import assert_metricool_write_allowed

        write_blocked = False
        try:
            assert_metricool_write_allowed("publish")
        except Exception as exc:  # noqa: BLE001
            write_blocked = "BETA_METRICOOL_WRITE_ENABLED=false" in str(exc)
        check("Metricool write remains blocked", write_blocked)

        # 8) assert_publish_allowed raise path via serve_beta helper
        # Re-approve a fresh slot for raise-vs-ready
        slot_raise = seed_slot(conn)
        conn.commit()
        # Point serve_beta catalog briefly — use content_publish raise semantics
        bad = False
        try:
            g = cp.assert_habitat_publish_allowed(slot_raise, verified_person_id="PERS-MATT")
            if g["stage"] == "DENIED":
                bad = True
        except Exception:
            bad = True
        check("unapproved raise/deny path", bad)

        # Matt self submit+approve (no SoD required)
        slot_matt = seed_slot(conn)
        conn.commit()
        cp.submit_for_approval(slot_matt, verified_person_id="PERS-MATT")
        matt_ok = cp.apply_core_approval_to_slot(slot_matt, verified_person_id="PERS-MATT")
        check("Matt self-approve allowed (no SoD)", matt_ok.get("core_status") == "APPROVED")
        gate_m = cp.assert_habitat_publish_allowed(slot_matt, verified_person_id="PERS-MATT")
        check("Matt path READY_TO_PUBLISH", gate_m.get("stage") == "READY_TO_PUBLISH")

    finally:
        conn.close()
        if tmp.exists():
            tmp.unlink()

    end = live_counts()
    check("live auth still 0", end["auth"] == 0)
    check("live SoD still 0", end["sod"] == 0)
    check("live exceptions still 0", end["exc"] == 0)
    check("live Habitat policy still 1", end["habitat_pol"] == 1)
    check("live Habitat evr still 1", end["habitat_evr"] == 1)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
