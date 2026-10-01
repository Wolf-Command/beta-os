#!/usr/bin/env python3
"""Wave 2.03 — CRM identity read. Separate stores. No merge.

Habitat is a sheet count. core_leads are fixtures without email or phone.
One AMG guest profile has both fields. Nothing else in these reads carries
them, so no pair is compared and no master table is written.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
GLANCE = BETA_ROOT / "state" / "habitat-leads-glance.json"
GUEST_DB = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/state/guest-profiles.db")
IDENTITY_DB = BETA_ROOT / "catalog" / "crm_identity.sqlite"


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def _habitat() -> dict[str, Any]:
    if not GLANCE.is_file():
        return {"present": False, "count": None, "state": "UNKNOWN", "join_keys": "UNAVAILABLE"}
    try:
        data = json.loads(GLANCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "present": False,
            "count": None,
            "state": "UNKNOWN",
            "join_keys": "UNAVAILABLE",
            "why": f"Glance unreadable ({type(exc).__name__}).",
        }
    count = data.get("real_lead_count")
    return {
        "present": True,
        "state": "LIVE_COUNT" if isinstance(count, int) else "UNKNOWN",
        "count": count if isinstance(count, int) else None,
        "as_of_wita": data.get("as_of_wita"),
        "sot": data.get("sot"),
        "tab": data.get("tab"),
        "write": data.get("write"),
        "authorised_read": data.get("authorised_read"),
        "email_rows": None,
        "phone_rows": None,
        "join_keys": "UNAVAILABLE",
        "why": "The authorised glance is a count. It does not carry email or phone rows.",
    }


def _core_leads() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        return {"present": False, "count": None, "state": "UNKNOWN", "join_keys": "UNAVAILABLE"}
    conn = _ro(CATALOG_DB)
    try:
        rows = conn.execute(
            "SELECT entity_id, brand_id, source_system, provenance_json FROM core_leads"
        ).fetchall()
        email_rows = 0
        phone_rows = 0
        for row in rows:
            try:
                prov = json.loads(row["provenance_json"] or "{}")
            except json.JSONDecodeError:
                prov = {}
            if not isinstance(prov, dict):
                continue
            for key, value in prov.items():
                name = str(key).lower()
                if value and "email" in name:
                    email_rows += 1
                if value and ("phone" in name or "mobile" in name):
                    phone_rows += 1
        systems = sorted({row["source_system"] for row in rows})
    finally:
        conn.close()
    return {
        "present": True,
        "count": len(rows),
        "source_systems": systems,
        "fixture_only": systems == ["fixture"],
        "email_rows": email_rows,
        "phone_rows": phone_rows,
        "join_keys": "UNAVAILABLE" if email_rows == 0 and phone_rows == 0 else "PARTIAL",
        "state": "FIXTURE" if systems == ["fixture"] else "PARTIAL",
        "why": "core_leads is not the Habitat sheet. These rows have no email or phone.",
    }


def _guest() -> dict[str, Any]:
    if not GUEST_DB.is_file():
        return {"present": False, "guests": None, "state": "UNKNOWN", "join_keys": "UNAVAILABLE"}
    conn = _ro(GUEST_DB)
    try:
        guests = int(conn.execute("SELECT COUNT(*) FROM guests").fetchone()[0])
        visits = int(conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0])
        observations = int(conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0])
        flagged = conn.execute(
            """
            SELECT
              SUM(CASE WHEN primary_email IS NOT NULL AND trim(primary_email) != '' THEN 1 ELSE 0 END),
              SUM(CASE WHEN primary_phone IS NOT NULL AND trim(primary_phone) != '' THEN 1 ELSE 0 END)
            FROM guests
            """
        ).fetchone()
        businesses = [row[0] for row in conn.execute("SELECT DISTINCT business FROM visits")]
    finally:
        conn.close()
    email_rows = int(flagged[0] or 0)
    phone_rows = int(flagged[1] or 0)
    return {
        "present": True,
        "guests": guests,
        "visits": visits,
        "observations": observations,
        "businesses": businesses,
        "email_rows": email_rows,
        "phone_rows": phone_rows,
        "values_omitted": True,
        "state": "PARTIAL" if guests else "UNKNOWN",
        "why": "One AMG guest profile. Contact values stay in the file. They are not copied here.",
    }


def load_identity() -> dict[str, Any]:
    habitat = _habitat()
    leads = _core_leads()
    guest = _guest()
    identity_db = IDENTITY_DB.is_file()
    join_possible = (
        (habitat.get("email_rows") or 0) > 0 or (habitat.get("phone_rows") or 0) > 0
    ) and (
        (leads.get("email_rows") or 0) > 0 or (leads.get("phone_rows") or 0) > 0 or (guest.get("email_rows") or 0) > 0
    )
    return {
        "ok": True,
        "pack": "WAVE2-03",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "one_crm": False,
        "master_table_written": identity_db,
        "join": {
            "state": "PARTIAL" if join_possible else "UNAVAILABLE",
            "matched_pairs": None,
            "compared": False,
            "why": (
                "A shared email or phone exists in more than one of these reads."
                if join_possible
                else "No two of these reads carry email or phone together. No pair was compared and no link was written."
            ),
        },
        "sources": {
            "habitat_sheet": habitat,
            "core_leads": leads,
            "guest_profiles": guest,
            "ggv_onboard": {
                "state": "SHELL",
                "table": None,
                "count": None,
                "why": "The catalog has no invite or onboard identity table. That is not zero clients.",
            },
        },
        "why": "Three stores, three questions. They are not one customer record.",
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "one_crm": False,
        "message": "CRM identity does not write the Habitat sheet, a merge, or a master person row.",
    }
