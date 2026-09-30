#!/usr/bin/env python3
"""INTG-TRUTH-1 — Integration honesty board (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack INTG-TRUTH-1
(armed 2026-09-30) — MB-015 / INT-* SPECIFIED honesty.

Builds a connector registry from Integrations.csv + PHASE3-INTEGRATIONS-AUDIT.json.
Safe local probes only (ESB warehouse RO, Metricool status() with no creds load).
Never invents last_success timestamps or fake connector success.
Never expands write authority. Never exposes secrets.
staff_ready / human_commissioned stay false.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
AUDIT_PATH = BETA_ROOT / "state" / "final-completion" / "PHASE3-INTEGRATIONS-AUDIT.json"
CSV_PATH = BETA_ROOT / "docs" / "canon" / "build-dashboard" / "Integrations.csv"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK = "INTG-TRUTH-1"
SCHEMA_ID = "wolf.intg-truth-board.v1"
WRITE_AUTHORITY = "NONE_EXPANDED"

PAGE_PATHS = frozenset(
    {
        "/ops/integrations-status",
        "/ops/integrations-status/",
        "/integrations-status",
        "/integrations-status/",
        "/integrations-status.html",
        "/dashboards/integrations-status.html",
    }
)

WITA = timezone(timedelta(hours=8))


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") == "/api/ops/integrations-status"


def _load_csv() -> list[dict[str, Any]]:
    if not CSV_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            iid = (raw.get("Integration ID") or "").strip()
            if not iid:
                continue
            last_raw = (raw.get("Last success") or "").strip()
            rows.append(
                {
                    "integration_id": iid,
                    "source": (raw.get("Source") or "").strip() or None,
                    "target": (raw.get("Target") or "").strip() or None,
                    "purpose": (raw.get("Purpose") or "").strip() or None,
                    "method": (raw.get("Method") or "").strip() or None,
                    "dashboard_status": (raw.get("Status") or "").strip() or None,
                    "owner": (raw.get("Owner") or "").strip() or None,
                    "criticality": (raw.get("Criticality") or "").strip() or None,
                    "fallback": (raw.get("Fallback") or "").strip() or None,
                    # CSV blank last-success stays null — never invent.
                    "last_success": last_raw or None,
                    "related_requirement_ids": [iid],
                    "seed": "integrations_csv",
                }
            )
    return rows


def _load_audit() -> dict[str, Any]:
    if not AUDIT_PATH.is_file():
        return {"connectors": [], "counts": {}}
    data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"connectors": [], "counts": {}}
    return data


def _merge_row(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Prefer non-null richer fields; never invent last_success from empty."""
    out = dict(base)
    for key, val in extra.items():
        if key == "last_success":
            # Only keep a timestamp if already known; never invent from blank.
            if out.get("last_success") is None and val:
                out["last_success"] = val
            continue
        if key == "related_requirement_ids":
            a = list(out.get("related_requirement_ids") or [])
            b = list(val or [])
            seen = set(a)
            for item in b:
                if item not in seen:
                    a.append(item)
                    seen.add(item)
            out["related_requirement_ids"] = a
            continue
        if key == "evidence_notes":
            a = list(out.get("evidence_notes") or [])
            b = list(val or [])
            for note in b:
                if note not in a:
                    a.append(note)
            out["evidence_notes"] = a
            continue
        if key == "purpose":
            cur = out.get("purpose") or ""
            if isinstance(val, str) and len(val) > len(str(cur)):
                out["purpose"] = val
            elif not cur and val:
                out["purpose"] = val
            continue
        if out.get(key) in (None, "", []) and val not in (None, "", []):
            out[key] = val
        elif key in ("blocked_external", "secrets_exposed") and val is True:
            out[key] = True
        elif key == "audit_status" and not out.get("audit_status") and val:
            out[key] = val
        elif key == "probe_status" and not out.get("probe_status") and val:
            out[key] = val
    return out


def _seed_registry() -> list[dict[str, Any]]:
    """Union of CSV + Phase3 audit, deduped by integration_id (richest wins)."""
    by_id: dict[str, dict[str, Any]] = {}
    for row in _load_csv():
        iid = row["integration_id"]
        by_id[iid] = {
            **row,
            "audit_status": None,
            "probe_status": None,
            "blocked_external": False,
            "write_authority": WRITE_AUTHORITY,
            "secrets_exposed": False,
            "evidence_notes": [],
            "probe_notes": None,
            "last_probed_at": None,
        }
    audit = _load_audit()
    for conn in audit.get("connectors") or []:
        if not isinstance(conn, dict):
            continue
        iid = str(conn.get("integration_id") or "").strip()
        if not iid:
            continue
        mapped = {
            "integration_id": iid,
            "source": conn.get("source"),
            "target": conn.get("target"),
            "purpose": conn.get("purpose"),
            "method": conn.get("method"),
            "dashboard_status": conn.get("dashboard_status"),
            "audit_status": conn.get("audit_status"),
            "probe_status": conn.get("probe_status"),
            "write_authority": WRITE_AUTHORITY,
            "secrets_exposed": bool(conn.get("secrets_exposed") is True),
            "blocked_external": bool(conn.get("blocked_external") is True),
            "related_requirement_ids": list(conn.get("related_requirement_ids") or []),
            "evidence_notes": list(conn.get("evidence_notes") or []),
            "last_success": conn.get("last_success"),  # may be null
            "owner": conn.get("owner"),
            "criticality": conn.get("criticality"),
            "fallback": conn.get("fallback"),
            "last_probed_at": conn.get("last_probed_at"),
            "probe_notes": conn.get("probe_notes"),
            "seed": "phase3_audit",
        }
        if iid in by_id:
            by_id[iid] = _merge_row(by_id[iid], mapped)
        else:
            by_id[iid] = mapped
    return list(by_id.values())


def _venue_close_count() -> int | None:
    if not CATALOG_DB.is_file():
        return None
    try:
        uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            n = conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
            return int(n)
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return None


def _safe_esb_probe() -> dict[str, Any]:
    """Warehouse facts only — never invent P&L or last_success."""
    from core import integration_health as ih

    row = ih._read_esb(None)
    closes = _venue_close_count()
    return {
        "warehouse_status": row.get("status"),
        "evidence": row.get("evidence"),
        "venue_daily_closes_count": closes,
        "pnl_invented": False,
        "last_success": None,
        "write": False,
    }


def _safe_metricool_probe() -> dict[str, Any]:
    """status() only — no credential load, no network call."""
    from core import integration_health as ih

    row = ih._read_metricool()
    return {
        "status": row.get("status"),
        "evidence": row.get("evidence"),
        "wolf_runtime": False,  # Metricool MCP is agent-host; Wolf runtime not wired
        "last_success": None,
        "write": False,
        "creds_loaded": False,
        "network_called": False,
    }


def _apply_safe_probes(rows: list[dict[str, Any]], *, probed_at: str) -> list[dict[str, Any]]:
    esb = _safe_esb_probe()
    metricool = _safe_metricool_probe()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        iid = str(item.get("integration_id") or "")
        item["write_authority"] = WRITE_AUTHORITY
        item["secrets_exposed"] = False
        # Never invent last_success — force null unless a real non-empty value exists.
        if not item.get("last_success"):
            item["last_success"] = None

        if iid in ("INT-YAN-WOLF", "CAP-INTG-01") or (
            str(item.get("source") or "").lower() == "yanolja"
        ):
            item["audit_status"] = "BLOCKED_EXTERNAL"
            item["probe_status"] = "DOCUMENTED_BLOCKER"
            item["blocked_external"] = True
            item["last_success"] = None
            item["last_probed_at"] = probed_at
            item["probe_notes"] = (
                "No live Yanolja probe attempted. Credentials not seated. "
                "BLOCKED_EXTERNAL stamp only."
            )
            notes = list(item.get("evidence_notes") or [])
            stamp = "Yanolja BLOCKED_EXTERNAL — no fake live feed"
            if stamp not in notes:
                notes.append(stamp)
            item["evidence_notes"] = notes

        elif iid in ("INT-ESB-WOLF", "CAP-INTG-02") or (
            str(item.get("source") or "").upper() == "ESB"
        ):
            # ESB-SETTLEMENT-PATH-1: warehouse PARTIAL + settlement EXTERNAL_BLOCKER.
            wh = esb.get("warehouse_status")
            closes = esb.get("venue_daily_closes_count")
            try:
                from core import esb_settlement_path1 as _esp

                overlay = _esp.intg_probe_overlay()
            except Exception:  # noqa: BLE001
                overlay = None
            if overlay:
                item["audit_status"] = overlay.get("audit_status") or "PARTIAL_IN_BETA"
                item["probe_status"] = overlay.get("probe_status") or (
                    "WAREHOUSE_READ_OK_PARTIAL_SETTLEMENT_EXTERNAL_BLOCKER"
                    if wh == "READ_OK"
                    else f"WAREHOUSE_{wh}"
                )
                item["blocked_external"] = False
                item["last_success"] = None  # warehouse ≠ connector success
                item["last_probed_at"] = probed_at
                item["probe_notes"] = overlay.get("probe_notes") or (
                    f"ESB warehouse RO status={wh}. venue_daily_closes={closes}. "
                    "Settlement path EXTERNAL_BLOCKER."
                )
                item["probe_facts"] = {
                    "warehouse_status": wh,
                    "venue_daily_closes_count": closes,
                    "pnl_invented": False,
                    "settlement": None,
                    "fake_settlement": False,
                    **(overlay.get("probe_facts") or {}),
                }
            else:
                item["audit_status"] = "PARTIAL_IN_BETA"
                if wh == "READ_OK":
                    item["probe_status"] = "WAREHOUSE_READ_OK_PARTIAL"
                elif wh in ("NOT_CONFIGURED", "UNKNOWN"):
                    item["probe_status"] = "WAREHOUSE_ABSENT"
                else:
                    item["probe_status"] = f"WAREHOUSE_{wh}"
                item["blocked_external"] = False
                item["last_success"] = None
                item["last_probed_at"] = probed_at
                item["probe_notes"] = (
                    f"ESB warehouse RO status={wh}. "
                    f"venue_daily_closes={closes}. "
                    "PARTIAL_IN_BETA — warehouse facts only; P&L not invented; "
                    "settlement_api UNAVAILABLE."
                )
                item["probe_facts"] = {
                    "warehouse_status": wh,
                    "venue_daily_closes_count": closes,
                    "pnl_invented": False,
                }

        elif iid in ("INT-BANK-WOLF", "CAP-INTG-04") or "bank" in iid.lower():
            item["audit_status"] = item.get("audit_status") or "MISSING_OR_UNPROVEN"
            item["probe_status"] = "FILE_IMPORT_ONLY"
            item["blocked_external"] = bool(item.get("blocked_external"))
            item["last_success"] = None
            item["last_probed_at"] = probed_at
            item["probe_notes"] = (
                "Bank path is file-import-only. No direct banking API assumed. "
                "No payment write. No live statement feed invented."
            )

        elif iid == "INT-MET-WOLF" or iid == "CAP-INTG-05":
            # METRICOOL-RUNTIME-WIRE-1: per-surface honesty (not blanket NOT_RUNTIME).
            st = metricool.get("status")
            try:
                from core import metricool_runtime_wire1 as _mrw

                overlay = _mrw.intg_probe_overlay()
            except Exception:  # noqa: BLE001
                overlay = None
            if overlay:
                item["audit_status"] = overlay.get("audit_status") or "PARTIAL_IN_BETA"
                item["probe_status"] = overlay.get("probe_status") or "RUNTIME_WIRED_PARTIAL"
                item["last_success"] = None
                item["last_probed_at"] = probed_at
                item["probe_notes"] = overlay.get("probe_notes")
                item["probe_facts"] = {
                    **(overlay.get("probe_facts") or {}),
                    "status_status_fn": st,
                    "creds_loaded": False,
                    "network_called": False,
                }
            else:
                item["audit_status"] = (
                    "MISSING_OR_UNPROVEN"
                    if iid == "INT-MET-WOLF"
                    else (item.get("audit_status") or "BUILT_NOT_PROVEN")
                )
                if st == "NOT_CONFIGURED":
                    item["probe_status"] = "NOT_RUNTIME"
                else:
                    item["probe_status"] = f"STATUS_{st}"
                item["last_success"] = None
                item["last_probed_at"] = probed_at
                item["probe_notes"] = (
                    f"Wolf Metricool status()={st} (no creds loaded, no network). "
                    "Agent-host MCP-Metricool ≠ Wolf runtime connector."
                )
                item["probe_facts"] = {
                    "status": st,
                    "wolf_runtime": False,
                    "creds_loaded": False,
                    "network_called": False,
                }

        elif iid.startswith("MCP-") or str(item.get("target") or "") == "AgentHost":
            item["audit_status"] = "AGENT_HOST_ONLY"
            item["probe_status"] = "AGENT_HOST_CATALOGED"
            item["blocked_external"] = False
            item["last_success"] = None
            item["last_probed_at"] = probed_at
            item["probe_notes"] = (
                "Agent-host MCP only — not Wolf staff runtime connector. "
                "Brand/analytics stamps land via METRICOOL-RUNTIME-WIRE-1; "
                "engagement values stay NOT_RUNTIME."
            )
            if iid == "MCP-Metricool":
                notes = list(item.get("evidence_notes") or [])
                stamp = (
                    "MCP-Metricool AGENT_HOST_ONLY; INT-MET-WOLF per-surface "
                    "RUNTIME_WIRED (brands/analytics) via METRICOOL-RUNTIME-WIRE-1"
                )
                if stamp not in notes:
                    notes.append(stamp)
                item["evidence_notes"] = notes

        elif iid == "INT-GWS-WOLF" or iid == "CAP-INTG-03":
            item["audit_status"] = item.get("audit_status") or "MISSING_OR_UNPROVEN"
            item["probe_status"] = item.get("probe_status") or "NO_LIVE_PROBE"
            item["last_success"] = None
            item["last_probed_at"] = probed_at
            item["probe_notes"] = (
                "No Beta-local GWS live probe in this pack. "
                "Dashboard SPECIFIED is not a live prove."
            )

        else:
            # Generic honesty defaults
            item["audit_status"] = item.get("audit_status") or "MISSING_OR_UNPROVEN"
            item["probe_status"] = item.get("probe_status") or "DOCUMENTED_ONLY"
            item["last_success"] = None if not item.get("last_success") else item.get("last_success")
            item["last_probed_at"] = probed_at
            if not item.get("probe_notes"):
                item["probe_notes"] = "Catalogued only; no live credentialed probe."

        # Absolute honesty pins
        item["write_authority"] = WRITE_AUTHORITY
        item["secrets_exposed"] = False
        out.append(item)

    # Stable order: CSV INT-* first, then CAP-*, then MCP-*, then other
    def sort_key(r: dict[str, Any]) -> tuple[int, str]:
        iid = str(r.get("integration_id") or "")
        if iid.startswith("INT-"):
            return (0, iid)
        if iid.startswith("CAP-INTG-"):
            return (1, iid)
        if iid.startswith("MCP-"):
            return (2, iid)
        return (3, iid)

    out.sort(key=sort_key)
    return out


def build_board(*, persist_audit: bool = False) -> dict[str, Any]:
    """Public honesty board payload. Auth gating is caller's responsibility."""
    probed_at = _now_wita()
    connectors = _apply_safe_probes(_seed_registry(), probed_at=probed_at)
    by_audit: dict[str, int] = {}
    by_probe: dict[str, int] = {}
    blocked = 0
    for c in connectors:
        a = str(c.get("audit_status") or "UNKNOWN")
        p = str(c.get("probe_status") or "UNKNOWN")
        by_audit[a] = by_audit.get(a, 0) + 1
        by_probe[p] = by_probe.get(p, 0) + 1
        if c.get("blocked_external") is True:
            blocked += 1
        # Final pin — never invent success
        if not c.get("last_success"):
            c["last_success"] = None
        c["write_authority"] = WRITE_AUTHORITY
        c["secrets_exposed"] = False

    payload = {
        "ok": True,
        "pack": PACK,
        "schema": SCHEMA_ID,
        "as_of_wita": probed_at,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "invented_last_success": False,
        "fake_live_feeds": False,
        "source_files": [
            str(CSV_PATH.relative_to(BETA_ROOT)),
            str(AUDIT_PATH.relative_to(BETA_ROOT)),
        ],
        "counts": {
            "total": len(connectors),
            "blocked_external": blocked,
            "by_audit_status": by_audit,
            "by_probe_status": by_probe,
        },
        "connectors": connectors,
        "honesty": {
            "yanolja": "BLOCKED_EXTERNAL",
            "esb": "PARTIAL_IN_BETA",
            "esb_settlement": "EXTERNAL_BLOCKER",
            "esb_policy": (
                "WAREHOUSE_RO PARTIAL_IN_BETA (ESB-TRUTH-1 preserved); "
                "settlement API path + credentials EXTERNAL_BLOCKER "
                "(Felix 2026-07-19 + env-key absence); no invent settlement/P&L"
            ),
            "bank": "FILE_IMPORT_ONLY",
            "metricool_wolf": "PER_SURFACE",
            "metricool_mcp": "AGENT_HOST_ONLY",
            "metricool_policy": (
                "RUNTIME_WIRED brands+analytics catalog; "
                "NOT_RUNTIME engagement/last_success/publish values; "
                "EXTERNAL_BLOCKER Wolf HTTP when BETA_METRICOOL_ENABLED=false"
            ),
            "last_success_policy": "null_if_unknown_never_invent",
        },
        "cursor_did_not_auto_start_next_pack": True,
    }
    if persist_audit:
        _persist_audit_from_board(payload)
    return payload


def _persist_audit_from_board(payload: dict[str, Any]) -> None:
    """Update PHASE3 audit status fields from live board (read-only posture)."""
    existing = _load_audit()
    by_id = {c["integration_id"]: c for c in payload.get("connectors") or []}
    updated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for old in existing.get("connectors") or []:
        iid = str(old.get("integration_id") or "")
        live = by_id.get(iid)
        if not live:
            updated.append(old)
            continue
        row = dict(old)
        row["audit_status"] = live.get("audit_status")
        row["probe_status"] = live.get("probe_status")
        row["blocked_external"] = bool(live.get("blocked_external"))
        row["write_authority"] = WRITE_AUTHORITY
        row["secrets_exposed"] = False
        row["last_success"] = None if not live.get("last_success") else live.get("last_success")
        row["last_probed_at"] = live.get("last_probed_at")
        if live.get("probe_notes"):
            row["probe_notes"] = live.get("probe_notes")
        if live.get("evidence_notes"):
            row["evidence_notes"] = list(live.get("evidence_notes") or [])
        updated.append(row)
        seen.add(iid)
    for iid, live in by_id.items():
        if iid in seen:
            continue
        updated.append(
            {
                "integration_id": iid,
                "source": live.get("source"),
                "target": live.get("target"),
                "purpose": live.get("purpose"),
                "method": live.get("method"),
                "dashboard_status": live.get("dashboard_status"),
                "audit_status": live.get("audit_status"),
                "probe_status": live.get("probe_status"),
                "write_authority": WRITE_AUTHORITY,
                "secrets_exposed": False,
                "blocked_external": bool(live.get("blocked_external")),
                "related_requirement_ids": list(live.get("related_requirement_ids") or []),
                "evidence_notes": list(live.get("evidence_notes") or []),
                "last_success": live.get("last_success"),
                "owner": live.get("owner"),
                "criticality": live.get("criticality"),
                "fallback": live.get("fallback"),
                "last_probed_at": live.get("last_probed_at"),
                "probe_notes": live.get("probe_notes"),
            }
        )
    by_audit: dict[str, int] = {}
    for c in updated:
        a = str(c.get("audit_status") or "UNKNOWN")
        by_audit[a] = by_audit.get(a, 0) + 1
    existing["at_wita"] = payload.get("as_of_wita")
    existing["status"] = "BOARD_SYNCED_READ_ONLY"
    existing["staff_ready"] = False
    existing["human_commissioned"] = False
    existing["prod_mutate"] = False
    existing["secrets_exposed"] = False
    existing["write_authority_expanded"] = False
    existing["counts"] = {
        "total": len(updated),
        "by_audit_status": by_audit,
    }
    existing["connectors"] = updated
    existing["board_pack"] = PACK
    existing["board_schema"] = SCHEMA_ID
    AUDIT_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def public_payload(*, refresh_audit: bool = False) -> dict[str, Any]:
    return build_board(persist_audit=refresh_audit)


def yanolja_blocked(connectors: list[dict[str, Any]] | None = None) -> bool:
    rows = connectors if connectors is not None else build_board()["connectors"]
    for c in rows:
        if c.get("integration_id") == "INT-YAN-WOLF":
            return (
                c.get("audit_status") == "BLOCKED_EXTERNAL"
                and c.get("blocked_external") is True
                and c.get("last_success") is None
            )
    return False
