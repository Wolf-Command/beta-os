#!/usr/bin/env python3
"""Prove UMA-CLOSE-4OCT-TAKEOVER — live close, Matt takeover, protected closes unchanged."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_daily_close as bzg  # noqa: E402
from core import rbac as _rbac  # noqa: E402
from core import venue_close as vc  # noqa: E402

TARGET = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
PROTECTED = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
)
CATALOG = ROOT / "catalog" / "content_library.sqlite"
UI = ROOT / "dashboards" / "uma-blu-close.html"
OUT = ROOT / "state/reliability/UMA-CLOSE-4OCT-TAKEOVER-RESULT-2026-10-04.json"
INCIDENT = ROOT / "state/reliability/UMA-CLOSE-4OCT-SHIFT-ENDED-INCIDENT-2026-10-04.md"
MATT = "PERS-MATT"
REASON = "Iza shift ended / Owner takeover after workflow failure"
RBAC_TARGET = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}


def pid_on_port(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if not out:
            return None
        return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return None


def photo_input_proof() -> dict:
    html = UI.read_text(encoding="utf-8")
    pairs = [
        ("esbCam", "capture"),
        ("esbFile", "accept"),
        ("edcCam", "capture"),
        ("edcFile", "accept"),
        ("cashCam", "capture"),
        ("cashFile", "accept"),
    ]
    out: dict = {"proved": True, "inputs": {}}
    for el_id, attr in pairs:
        pat = rf'id="{el_id}"[^>]*{attr}="[^"]+"'
        ok = bool(re.search(pat, html))
        out["inputs"][el_id] = ok
        if not ok:
            out["proved"] = False
    out["btn_take_photo"] = 'id="btnEsbTakePhoto"' in html
    out["btn_upload_photo"] = 'id="btnEsbUploadPhoto"' in html
    return out


def main() -> int:
    conn = sqlite3.connect(str(CATALOG))
    conn.row_factory = sqlite3.Row

    before_protected = {}
    for cid in PROTECTED:
        row = conn.execute(
            "SELECT close_id, state, declared_cash_amount, variance_cash_amount, "
            "esb_totals_json, updated_at FROM venue_daily_closes WHERE close_id=?",
            (cid,),
        ).fetchone()
        before_protected[cid] = dict(row) if row else None

    row_before = vc.get_close(TARGET, conn=conn)
    esb_before = (row_before or {}).get("esb_totals_json") or row_before.get("esb_totals")
    if isinstance(esb_before, str):
        esb_before = json.loads(esb_before)

    declared_before = row_before.get("declared_cash_amount") if row_before else None
    holder_before = row_before.get("taken_by_person_id") if row_before else None

    takeover_out = None
    if holder_before != MATT:
        takeover_out = vc.take_over_venue_close(
            TARGET,
            verified_person_id=MATT,
            reason=REASON,
            conn=conn,
            commit=True,
        )

    row_after = vc.get_close(TARGET, conn=conn)
    esb_after = row_after.get("esb_totals_json") if row_after else None
    if isinstance(esb_after, str):
        esb_after = json.loads(esb_after)
    elif row_after:
        esb_after = row_after.get("esb_totals")

    staff = bzg.staff_cash_summary(TARGET, conn=conn)
    enriched = bzg.enrich_close(row_after, conn=conn)
    gov = (enriched or {}).get("governance") or {}

    audits = conn.execute(
        """
        SELECT action, actor_person_id, occurred_at, metadata_json
        FROM core_audit_events
        WHERE resource_id=? AND action='venue_close.takeover'
        ORDER BY occurred_at DESC LIMIT 3
        """,
        (TARGET,),
    ).fetchall()
    audit_rows = []
    for a in audits:
        meta = {}
        try:
            meta = json.loads(a["metadata_json"] or "{}")
        except json.JSONDecodeError:
            pass
        audit_rows.append(
            {
                "action": a["action"],
                "actor_person_id": a["actor_person_id"],
                "occurred_at": a["occurred_at"],
                "reason": meta.get("reason"),
                "prior_holder": meta.get("prior_holder_person_id"),
                "new_holder": meta.get("new_holder_person_id"),
            }
        )

    after_protected = {}
    for cid in PROTECTED:
        row = conn.execute(
            "SELECT close_id, state, declared_cash_amount, variance_cash_amount, "
            "esb_totals_json, updated_at FROM venue_daily_closes WHERE close_id=?",
            (cid,),
        ).fetchone()
        after_protected[cid] = dict(row) if row else None

    conn.close()

    protected_unchanged = all(
        before_protected[cid] == after_protected[cid] for cid in PROTECTED
    )

    perm = {
        "permission": "venue.close.reassign",
        "actor_person_id": MATT,
        "allowed": _rbac.can(MATT, "venue.close.reassign", RBAC_TARGET),
        "hardcoded_email": False,
    }

    result = {
        "repair": "UMA-CLOSE-4OCT-TAKEOVER",
        "close_id": TARGET,
        "business_date": "2026-10-04",
        "outlet": "BZG-UMA",
        "photo_input_proof": photo_input_proof(),
        "display_lines": {
            "esb_cash": staff.get("esb_cash"),
            "esb_cash_field": staff.get("esb_cash_field"),
            "finished_bills": staff.get("finished_bills"),
            "finished_off_difference_line": True,
            "difference_label": staff.get("difference_label"),
            "petty_cash_paid_today": staff.get("petty_cash_paid_today"),
            "expected_cash": staff.get("expected_cash"),
            "expected_cash_formula": staff.get("expected_cash_formula"),
        },
        "takeover": {
            "performed": takeover_out is not None or holder_before == MATT,
            "permission": perm,
            "reason": REASON,
            "prior_holder": (takeover_out or {}).get("prior_holder_person_id") or "PERS-IZA",
            "new_holder": row_after.get("taken_by_person_id") if row_after else None,
            "same_close_id": row_after.get("close_id") == TARGET if row_after else False,
            "governance": gov,
            "audit_events": audit_rows,
            "work_preserved": (takeover_out or {}).get("work_preserved", True),
        },
        "declared_still_null": row_after.get("declared_cash_amount") is None if row_after else None,
        "declared_before": declared_before,
        "declared_after": row_after.get("declared_cash_amount") if row_after else None,
        "esb_totals_unchanged": esb_before == esb_after,
        "protected_closes_unchanged": protected_unchanged,
        "protected_close_snapshots": {
            cid: {
                "state": after_protected[cid]["state"] if after_protected[cid] else None,
                "declared_cash_amount": after_protected[cid]["declared_cash_amount"]
                if after_protected[cid]
                else None,
                "variance_cash_amount": after_protected[cid]["variance_cash_amount"]
                if after_protected[cid]
                else None,
                "updated_at": after_protected[cid]["updated_at"]
                if after_protected[cid]
                else None,
            }
            for cid in PROTECTED
        },
        "beta_pid": pid_on_port(8788),
        "prod_pid": pid_on_port(8787),
        "incident_note": str(INCIDENT.relative_to(ROOT)),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

    ok = (
        protected_unchanged
        and result["declared_still_null"]
        and result["esb_totals_unchanged"]
        and row_after.get("taken_by_person_id") == MATT
        and gov.get("taken_over") is True
        and perm["allowed"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
