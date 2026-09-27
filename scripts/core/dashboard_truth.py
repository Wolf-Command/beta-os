#!/usr/bin/env python3
"""Dashboard truth — one provenance layer for Beta dashboards.

Decision served: owner brief 27 Sep 2026, PACK 4 (dashboard truth,
data quality, staleness). Extends the 2026-09-18 projection rule.
Not a second task system. Not a connector. No network. No ledger write.

Display states: LIVE, CURRENT, STALE, UNKNOWN, UNAVAILABLE, NEEDS REVIEW.
A stale fact is never labelled current. Empty is not unknown. Claimed is
not verified. A file on disk is not the authority. Historical is not
current. An estimate is not an actual. Designed is not built, tested, or
live. An uncommissioned connector says so.

Wolf Core (org_* / core_*) is the control store. Yanolja stays the hotel
engine. ESB stays F&B transaction truth. Finance books are not invented.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path(__file__).resolve().parents[2]
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
FIN_FRAMEWORK_DB = BETA_ROOT / "catalog" / "fin_mgmt_reporting.sqlite"
KLAVIYO_READER = BETA_ROOT / "scripts" / "core" / "habitat_klaviyo_reader.py"

DISPLAY_STATES: tuple[str, ...] = (
    "LIVE",
    "CURRENT",
    "STALE",
    "UNKNOWN",
    "UNAVAILABLE",
    "NEEDS REVIEW",
)
_RANK = {
    "UNAVAILABLE": 0,
    "UNKNOWN": 1,
    "STALE": 2,
    "NEEDS REVIEW": 3,
    "CURRENT": 4,
    "LIVE": 5,
}

DISTINCTION_RULES: tuple[str, ...] = (
    "CLAIMED is not VERIFIED",
    "SOURCE FOUND is not AUTHORITATIVE",
    "EMPTY is not UNKNOWN",
    "HISTORICAL is not CURRENT",
    "ESTIMATE is not ACTUAL",
    "DESIGNED is not BUILT is not TESTED is not LIVE",
)

SOURCE_IDS: tuple[str, ...] = (
    "yanolja",
    "esb",
    "wolf_core",
    "nas",
    "finance_ledgers",
    "klaviyo",
    "metricool",
)

SURFACES: dict[str, tuple[str, ...] | None] = {
    "empire": None,
    "my-work": ("wolf_core",),
    "amg": ("yanolja", "wolf_core"),
    "bzg": ("esb", "wolf_core"),
    "ggv": ("klaviyo", "metricool", "nas", "wolf_core"),
}

LIVE_WINDOW_S = 15 * 60
CURRENT_WINDOW_S = 24 * 60 * 60
_SECRET_MARKERS = ("sk-", "begin private", "password=", "api_key", "secret=")
_PATH_RE = re.compile(r"(?:/Users|/Volumes|file:)[^\s\"']+")


class TruthError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def _parse_time(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _as_of(facts: dict[str, Any]) -> datetime:
    parsed = _parse_time(facts.get("as_of"))
    if parsed is not None:
        return parsed
    return datetime.now(timezone.utc)


def public_text(value: Any, *, limit: int = 420) -> str:
    """Drop secrets and absolute paths before a string leaves this module."""
    text = str(value or "").strip()
    low = text.lower()
    if any(mark in low for mark in _SECRET_MARKERS):
        return "Evidence withheld because it looked like a secret."
    text = _PATH_RE.sub("[path]", text)
    return text[:limit]


def _plain(state: str, reasons: list[str], presence: str) -> str:
    lead = {
        "LIVE": "Live. Verified inside the live window from the source that owns this.",
        "CURRENT": "Current. Verified inside the freshness window. Not a live feed.",
        "STALE": "Stale. Older than the freshness window. Not current.",
        "UNKNOWN": "Unknown. Wolf does not know. Unknown is not empty and not zero.",
        "UNAVAILABLE": "Unavailable. This source cannot be read. Nothing was invented.",
        "NEEDS REVIEW": "Needs review. Something was found, and it is not verified current truth.",
    }[state]
    extra = ""
    if presence == "EMPTY" and state in {"LIVE", "CURRENT", "NEEDS REVIEW", "STALE"}:
        extra = " Empty is a real empty read, not an unknown."
    elif state in {"STALE", "UNKNOWN", "UNAVAILABLE", "NEEDS REVIEW"} and reasons:
        extra = " " + reasons[0].rstrip(".") + "."
    return (lead + extra).strip()


def classify(facts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map observed facts to one display state. Never promotes stale to current."""
    src = dict(facts or {})
    reasons: list[str] = []
    problems: list[tuple[int, str, str]] = []

    def problem(state: str, reason: str) -> None:
        problems.append((_RANK[state], state, reason))
        reasons.append(reason)

    available = src.get("available", None)
    readable = src.get("readable", None)
    failure = src.get("failure")
    external = bool(src.get("external"))
    commissioned = src.get("commissioned") is True
    human_commissioned = src.get("human_commissioned") is True and commissioned
    verification = str(src.get("verification") or "UNVERIFIED").upper()
    if verification not in {"VERIFIED", "CLAIMED", "UNVERIFIED"}:
        verification = "UNVERIFIED"
    presence = str(src.get("presence") or "UNKNOWN").upper()
    if presence not in {"EMPTY", "PRESENT", "UNKNOWN"}:
        presence = "UNKNOWN"
    measure = str(src.get("measure") or "UNKNOWN").upper()
    if measure not in {"ESTIMATE", "ACTUAL", "UNKNOWN"}:
        measure = "UNKNOWN"
    build = str(src.get("build") or "UNKNOWN").upper()
    if build not in {"DESIGNED", "BUILT", "TESTED", "LIVE", "UNKNOWN"}:
        build = "UNKNOWN"
    time_in = str(src.get("time_class") or "UNKNOWN").upper()
    if time_in not in {"HISTORICAL", "CURRENT", "UNKNOWN"}:
        time_in = "UNKNOWN"
    authoritative = src.get("authoritative") is True

    if failure or available is False or readable is False:
        state = "UNAVAILABLE"
        why = str(failure or "source cannot be read")
        reasons.append(why)
    elif available is None or readable is None:
        state = "UNKNOWN"
        reasons.append("Wolf has not checked this source")
    else:
        if src.get("stale") is True:
            problem("STALE", str(src.get("stale_reason") or "marked stale"))
        observed = _parse_time(src.get("observed_at"))
        moment = _as_of(src)
        age: float | None = None
        if observed is None:
            problem("UNKNOWN", "no observed time")
        else:
            age = (moment - observed).total_seconds()
            if age < -120:
                problem("NEEDS REVIEW", "clock is ahead of Wolf")
            elif age > float(src.get("current_window_s") or CURRENT_WINDOW_S):
                problem("STALE", "older than the freshness window")
        if time_in == "HISTORICAL":
            problem("NEEDS REVIEW", "historical is not current")
        if measure == "ESTIMATE":
            problem("NEEDS REVIEW", "estimate is not actual")
        if verification != "VERIFIED":
            problem("NEEDS REVIEW", "claimed is not verified")
        if not authoritative:
            problem("NEEDS REVIEW", "source found is not authoritative")
        if presence == "UNKNOWN":
            problem("UNKNOWN", "presence is unknown")
        if external and not commissioned:
            problem("NEEDS REVIEW", "connector is not commissioned")
        if build == "DESIGNED":
            problem("NEEDS REVIEW", "designed is not built")
        elif build not in {"BUILT", "TESTED", "LIVE"}:
            problem("NEEDS REVIEW", "build state is not live")
        if problems:
            state = min(problems, key=lambda item: item[0])[1]
        else:
            live_window = float(src.get("live_window_s") or LIVE_WINDOW_S)
            current_window = float(src.get("current_window_s") or CURRENT_WINDOW_S)
            if (
                build == "LIVE"
                and age is not None
                and 0 <= age <= live_window
            ):
                state = "LIVE"
                reasons.append("verified inside the live window")
            elif age is not None and 0 <= age <= current_window:
                state = "CURRENT"
                if build != "LIVE":
                    reasons.append("built or tested is not a live feed")
                else:
                    reasons.append("verified inside the freshness window")
            else:
                state = "STALE"
                reasons.append("older than the freshness window")

    if state in {"LIVE", "CURRENT"} and any(
        item[1] == "STALE" for item in problems
    ):
        state = "STALE"

    if time_in == "HISTORICAL":
        time_class = "HISTORICAL"
    elif state in {"LIVE", "CURRENT"}:
        time_class = "CURRENT"
    else:
        time_class = "UNKNOWN"

    if authoritative:
        authority = "AUTHORITATIVE"
    elif readable is True:
        authority = "SOURCE_FOUND"
    else:
        authority = "UNKNOWN"

    observed_out = src.get("observed_at")
    if isinstance(observed_out, datetime):
        observed_out = observed_out.astimezone(timezone.utc).isoformat()

    envelope = {
        "display_state": state,
        "plain": _plain(state, reasons, presence if state != "UNAVAILABLE" else "UNKNOWN"),
        "claim_state": verification if verification != "UNVERIFIED" else "UNVERIFIED",
        "authority": authority,
        "presence": presence if state != "UNAVAILABLE" or presence == "EMPTY" else (
            presence if presence in {"EMPTY", "PRESENT"} else "UNKNOWN"
        ),
        "time_class": time_class,
        "measure": measure,
        "build_state": build,
        "commissioned": commissioned,
        "human_commissioned": human_commissioned,
        "staff_ready": src.get("staff_ready") is True,
        "external": external,
        "observed_at": observed_out if isinstance(observed_out, str) else None,
        "reasons": reasons[:6],
        "shown_as_current": state in {"LIVE", "CURRENT"},
        "stale_shown_as_current": False,
        "vocabulary": list(DISPLAY_STATES),
    }
    if envelope["display_state"] == "STALE":
        envelope["shown_as_current"] = False
        envelope["time_class"] = "HISTORICAL" if time_in == "HISTORICAL" else "UNKNOWN"
    if envelope["presence"] == "EMPTY" and envelope["display_state"] == "UNKNOWN":
        envelope["presence"] = "UNKNOWN"
    return envelope


def mark_stale(reason: str) -> dict[str, Any]:
    """Shared stale mechanism. Disagreement and expiry both land here."""
    now = datetime.now(timezone.utc).isoformat()
    return classify(
        {
            "available": True,
            "readable": True,
            "authoritative": True,
            "verification": "VERIFIED",
            "presence": "PRESENT",
            "time_class": "CURRENT",
            "measure": "ACTUAL",
            "build": "LIVE",
            "observed_at": now,
            "external": False,
            "commissioned": True,
            "stale": True,
            "stale_reason": reason or "marked stale",
        }
    )


def projection_status(canonical: str, projected: str) -> dict[str, Any]:
    """Canonical change must show on the next read, or the card is stale."""
    if canonical == projected:
        now = datetime.now(timezone.utc).isoformat()
        return classify(
            {
                "available": True,
                "readable": True,
                "authoritative": True,
                "verification": "VERIFIED",
                "presence": "PRESENT",
                "time_class": "CURRENT",
                "measure": "ACTUAL",
                "build": "LIVE",
                "observed_at": now,
                "external": False,
                "commissioned": True,
            }
        )
    return mark_stale("projection disagrees with canonical state")


def fail_closed(reason: str) -> dict[str, Any]:
    """Shared failure mechanism. A failed read is unavailable, not a zero."""
    return classify(
        {
            "available": False,
            "readable": False,
            "failure": reason or "read failed",
            "external": True,
            "commissioned": False,
            "presence": "UNKNOWN",
        }
    )


def _row(
    source_id: str,
    name: str,
    owns: str,
    facts: dict[str, Any],
    evidence: str,
    historical_cut: str,
) -> dict[str, Any]:
    facts = dict(facts)
    facts["commissioned"] = False
    facts["human_commissioned"] = False
    facts["staff_ready"] = False
    env = classify(facts)
    env["staff_ready"] = False
    env["human_commissioned"] = False
    env["commissioned"] = False
    return {
        "source_id": source_id,
        "name": name,
        "owns": owns,
        "evidence": public_text(evidence),
        "historical_cut": historical_cut,
        "external_writes": False,
        "network_probes": False,
        **env,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _probe_yanolja() -> dict[str, Any]:
    return _row(
        "yanolja",
        "Yanolja",
        "Hotel engine for Atrium. Wolf does not own occupancy, ADR, or bookings.",
        {
            "available": False,
            "readable": False,
            "external": True,
            "failure": "no Yanolja reader",
            "presence": "UNKNOWN",
            "measure": "UNKNOWN",
            "build": "DESIGNED",
            "verification": "UNVERIFIED",
            "authoritative": False,
        },
        "No Yanolja reader was called. Occupancy was not invented. Connector is not commissioned.",
        "No feed has arrived, so Wolf stores no historical cut for Yanolja.",
    )


def _probe_esb() -> dict[str, Any]:
    from core import esb_close_snapshot as esb
    from core import integration_health as health

    try:
        report = health._read_esb(None)
        status = str(report.get("status") or "ERROR")
    except Exception as exc:  # noqa: BLE001
        return _row(
            "esb",
            "ESB",
            "F&B transaction truth. Wolf close math is not the settlement report.",
            {
                "available": False,
                "readable": False,
                "external": True,
                "failure": type(exc).__name__,
                "presence": "UNKNOWN",
            },
            "ESB warehouse could not be read. No sales figure was invented.",
            "Payment lines are not settlement. A failed read has no historical cut.",
        )
    observed = None
    try:
        path = esb.resolve_esb_path(None)
        if path.is_file():
            observed = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        observed = None
    if status == "READ_OK":
        facts = {
            "available": True,
            "readable": True,
            "external": True,
            "authoritative": False,
            "verification": "CLAIMED",
            "presence": "PRESENT",
            "time_class": "HISTORICAL",
            "measure": "ACTUAL",
            "build": "TESTED",
            "observed_at": observed or _now(),
        }
        evidence = (
            "Warehouse opened read-only and a sales table is present. "
            "Settlement API is unavailable. This is not current cash and not a commissioned connector."
        )
    elif status == "NOT_CONFIGURED":
        facts = {
            "available": False,
            "readable": False,
            "external": True,
            "failure": "ESB warehouse file is not present",
            "presence": "UNKNOWN",
        }
        evidence = "ESB warehouse file is not present. Not treated as zero sales."
    elif status == "DEGRADED":
        facts = {
            "available": True,
            "readable": True,
            "external": True,
            "authoritative": False,
            "verification": "UNVERIFIED",
            "presence": "UNKNOWN",
            "build": "BUILT",
            "observed_at": observed or _now(),
        }
        evidence = "Warehouse opened read-only. The sales table was not found. No figure was invented."
    else:
        facts = {
            "available": False,
            "readable": False,
            "external": True,
            "failure": "ESB read failed",
            "presence": "UNKNOWN",
        }
        evidence = "ESB warehouse could not be read. No sales figure was invented."
    return _row(
        "esb",
        "ESB",
        "F&B transaction truth. Wolf close math is not the settlement report.",
        facts,
        evidence,
        "Payment-line history is not settlement and is not current cash.",
    )


def _probe_wolf_core() -> dict[str, Any]:
    needed = ("org_persons", "org_roles", "org_assignments", "core_work_items")
    if not CATALOG_DB.is_file():
        return _row(
            "wolf_core",
            "Wolf Core",
            "Controls, work, evidence, and identity. Not the hotel engine or the F&B ledger.",
            {
                "available": False,
                "readable": False,
                "external": False,
                "failure": "catalog file is not present",
                "presence": "UNKNOWN",
            },
            "Wolf Core catalog file is not present. No people or work were invented.",
            "Wolf Core is the control store. It is not hotel, F&B, or finance history.",
        )
    uri = f"file:{CATALOG_DB.resolve()}?mode=ro"
    counts: dict[str, int] = {}
    try:
        conn = sqlite3.connect(uri, uri=True)
        try:
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            present = [name for name in needed if name in names]
            for name in present:
                counts[name] = int(conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
        finally:
            conn.close()
    except (OSError, sqlite3.Error) as exc:
        return _row(
            "wolf_core",
            "Wolf Core",
            "Controls, work, evidence, and identity. Not the hotel engine or the F&B ledger.",
            {
                "available": False,
                "readable": False,
                "external": False,
                "failure": type(exc).__name__,
                "presence": "UNKNOWN",
            },
            "Wolf Core catalog could not be opened read-only. No people or work were invented.",
            "Wolf Core is the control store. It is not hotel, F&B, or finance history.",
        )
    missing = [name for name in needed if name not in counts]
    if missing:
        facts = {
            "available": True,
            "readable": True,
            "external": False,
            "authoritative": True,
            "verification": "VERIFIED",
            "presence": "UNKNOWN",
            "time_class": "CURRENT",
            "measure": "ACTUAL",
            "build": "BUILT",
            "observed_at": _now(),
        }
        evidence = "Catalog opened read-only. Required control tables are missing: " + ", ".join(missing) + "."
    else:
        facts = {
            "available": True,
            "readable": True,
            "external": False,
            "authoritative": True,
            "verification": "VERIFIED",
            "presence": "PRESENT",
            "time_class": "CURRENT",
            "measure": "ACTUAL",
            "build": "BUILT",
            "observed_at": _now(),
        }
        evidence = (
            "Catalog opened read-only. org_persons, org_roles, org_assignments, "
            "and core_work_items are present. Counts are store counts, not a business KPI. "
            "Not human commissioned."
        )
    row = _row(
        "wolf_core",
        "Wolf Core",
        "Controls, work, evidence, and identity. Not the hotel engine or the F&B ledger.",
        facts,
        evidence,
        "Wolf Core is the control store. It is not hotel, F&B, or finance history.",
    )
    if counts and not missing:
        row["store_counts"] = counts
    return row


def _probe_nas() -> dict[str, Any]:
    from core import nas_library as nas

    try:
        connected = bool(nas.media_library_connected())
    except OSError:
        connected = False
    if not connected:
        return _row(
            "nas",
            "NAS",
            "File library. A mount is not a full index and not a commissioned content desk.",
            {
                "available": False,
                "readable": False,
                "external": True,
                "failure": "NAS library is not mounted",
                "presence": "UNKNOWN",
            },
            "NAS library is not mounted. No file count was invented. Connector is not commissioned.",
            "Files older than Wolf stay historical. No cut line is stored while the library is unmounted.",
        )
    return _row(
        "nas",
        "NAS",
        "File library. A mount is not a full index and not a commissioned content desk.",
        {
            "available": True,
            "readable": True,
            "external": True,
            "authoritative": False,
            "verification": "UNVERIFIED",
            "presence": "UNKNOWN",
            "measure": "UNKNOWN",
            "build": "BUILT",
            "observed_at": _now(),
        },
        "NAS library directory is present. The full tree is not claimed. No file count was invented. Not commissioned.",
        "A mounted library is not a full index. Files older than Wolf stay historical.",
    )


def _probe_finance() -> dict[str, Any]:
    owns = "External finance books are the ledger. This framework does not invent P&L, cash, or bank figures."
    cut = "External books were not opened. Wolf does not draw a historical cut it has not seen."
    if not FIN_FRAMEWORK_DB.is_file():
        return _row(
            "finance_ledgers",
            "Finance ledgers",
            owns,
            {
                "available": False,
                "readable": False,
                "external": True,
                "failure": "management-reporting framework file is not present",
                "presence": "UNKNOWN",
                "measure": "UNKNOWN",
            },
            "Management-reporting file is not on disk. Finance books were not opened. No figure was invented. Not commissioned.",
            cut,
        )
    has_row = False
    try:
        uri = f"file:{FIN_FRAMEWORK_DB.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]
            for name in tables:
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                    continue
                found = conn.execute(f"SELECT 1 FROM {name} LIMIT 1").fetchone()
                if found:
                    has_row = True
                    break
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return _row(
            "finance_ledgers",
            "Finance ledgers",
            owns,
            {
                "available": False,
                "readable": False,
                "external": True,
                "failure": "management-reporting framework could not be read",
                "presence": "UNKNOWN",
            },
            "Management-reporting file could not be read. Finance books were not opened. No figure was invented.",
            cut,
        )
    return _row(
        "finance_ledgers",
        "Finance ledgers",
        owns,
        {
            "available": True,
            "readable": True,
            "external": True,
            "authoritative": False,
            "verification": "UNVERIFIED",
            "presence": "PRESENT" if has_row else "EMPTY",
            "measure": "UNKNOWN",
            "build": "BUILT",
            "time_class": "UNKNOWN",
            "observed_at": _now(),
        },
        (
            "Management-reporting framework opened read-only. "
            + (
                "Rows exist in the framework. They are not a live P&L and not the external books."
                if has_row
                else "The framework has no rows. Empty is not a live ledger and not zero money."
            )
            + " Finance books were not opened. Not commissioned."
        ),
        cut,
    )


def _probe_klaviyo() -> dict[str, Any]:
    if not KLAVIYO_READER.is_file():
        return _row(
            "klaviyo",
            "Klaviyo",
            "Guest messaging source. A missing reader is not zero profiles.",
            {
                "available": False,
                "readable": False,
                "external": True,
                "failure": "Klaviyo reader file is not present",
                "presence": "UNKNOWN",
            },
            "Klaviyo reader file is not present. Profiles were not counted. Not commissioned.",
            "No pull has been made, so Wolf stores no Klaviyo historical cut.",
        )
    return _row(
        "klaviyo",
        "Klaviyo",
        "Guest messaging source. A reader file is not a live wire and not a profile insert.",
        {
            "available": True,
            "readable": True,
            "external": True,
            "authoritative": False,
            "verification": "UNVERIFIED",
            "presence": "UNKNOWN",
            "measure": "UNKNOWN",
            "build": "BUILT",
            "observed_at": _now(),
        },
        "The Habitat Klaviyo reader file is present. It was not imported and Klaviyo was not called. Not commissioned.",
        "No live pull. No Klaviyo historical cut is stored by this register.",
    )


def _probe_metricool() -> dict[str, Any]:
    from core import integration_health as health

    try:
        report = health._read_metricool()
        status = str(report.get("status") or "ERROR")
    except Exception as exc:  # noqa: BLE001
        status = "ERROR"
        _ = exc
    if status == "NOT_CONFIGURED":
        facts = {
            "available": False,
            "readable": False,
            "external": True,
            "failure": "Metricool is not configured",
            "presence": "UNKNOWN",
        }
        evidence = "Metricool is not configured. The status check did not call Metricool. Not commissioned."
    elif status == "READ_OK":
        facts = {
            "available": True,
            "readable": True,
            "external": True,
            "authoritative": False,
            "verification": "UNVERIFIED",
            "presence": "UNKNOWN",
            "build": "TESTED",
            "observed_at": _now(),
        }
        evidence = "Metricool status was read locally. Metricool was not called. Not commissioned."
    elif status == "UNKNOWN":
        facts = {
            "available": True,
            "readable": True,
            "external": True,
            "authoritative": False,
            "verification": "UNVERIFIED",
            "presence": "UNKNOWN",
            "build": "BUILT",
            "observed_at": _now(),
        }
        evidence = "A Metricool credential path is set. The read was not verified and Metricool was not called."
    else:
        facts = {
            "available": False,
            "readable": False,
            "external": True,
            "failure": "Metricool status could not be read",
            "presence": "UNKNOWN",
        }
        evidence = "Metricool status could not be read. Metricool was not called. Nothing was invented."
    return _row(
        "metricool",
        "Metricool",
        "Social scheduling source. Local status is not a publish and not a live metric.",
        facts,
        evidence,
        "No live pull. No Metricool historical cut is stored by this register.",
    )


_PROBES = {
    "yanolja": _probe_yanolja,
    "esb": _probe_esb,
    "wolf_core": _probe_wolf_core,
    "nas": _probe_nas,
    "finance_ledgers": _probe_finance,
    "klaviyo": _probe_klaviyo,
    "metricool": _probe_metricool,
}


def source_registry() -> dict[str, Any]:
    """Local register. Commissioned stays false. No network. No ledger write."""
    sources = []
    for source_id in SOURCE_IDS:
        try:
            sources.append(_PROBES[source_id]())
        except Exception as exc:  # noqa: BLE001
            sources.append(
                _row(
                    source_id,
                    source_id,
                    "Probe failed closed.",
                    {
                        "available": False,
                        "readable": False,
                        "external": True,
                        "failure": type(exc).__name__,
                        "presence": "UNKNOWN",
                    },
                    "This source could not be read. Nothing was invented.",
                    "No historical cut was stored.",
                )
            )
    for row in sources:
        if row["display_state"] not in DISPLAY_STATES:
            row["display_state"] = "UNKNOWN"
            row["shown_as_current"] = False
        if row["display_state"] == "STALE":
            row["shown_as_current"] = False
            row["stale_shown_as_current"] = False
        row["commissioned"] = False
        row["human_commissioned"] = False
        row["staff_ready"] = False
    return {
        "ok": True,
        "bound": "beta",
        "vocabulary": list(DISPLAY_STATES),
        "distinctions": list(DISTINCTION_RULES),
        "sources": sources,
        "staff_ready": False,
        "human_commissioned": False,
        "proven": False,
        "ready": False,
        "external_writes": False,
        "network_probes": False,
        "ledger_write": False,
    }


def stamp(surface: str) -> dict[str, Any]:
    """Plain stamp for one surface. Omits store counts."""
    key = (surface or "").strip().lower()
    if key not in SURFACES:
        raise TruthError(f"unknown surface: {key}", code="unknown_surface")
    full = source_registry()
    wanted = SURFACES[key]
    rows = []
    for row in full["sources"]:
        if wanted is not None and row["source_id"] not in wanted:
            continue
        public = dict(row)
        public.pop("store_counts", None)
        rows.append(public)
    return {
        "ok": True,
        "surface": key,
        "vocabulary": list(DISPLAY_STATES),
        "distinctions": list(DISTINCTION_RULES),
        "sources": rows,
        "staff_ready": False,
        "human_commissioned": False,
        "proven": False,
        "ready": False,
        "external_writes": False,
        "network_probes": False,
        "ledger_write": False,
    }


def ui_spec() -> dict[str, Any]:
    """Shared component names. Pages render these; they do not invent a second nav."""
    return {
        "header": "wolfnav",
        "nav": "wolfnav",
        "card": "wolf-card",
        "states": list(DISPLAY_STATES),
        "empty": "wolf-empty",
        "error": "wolf-error",
        "permission_denied": "wolf-denied",
        "status_language": list(DISTINCTION_RULES),
    }
