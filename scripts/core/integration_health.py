#!/usr/bin/env python3
"""Owner Integration Health — Beta read-only.

Bound: beta-integration-health-readonly. Serves the 2026-09-19 plan
docs/deliveries/GROK-PLAN-INTEGRATION-HEALTH-READONLY-2026-09-19.md.

Statuses come only from local reads of readers that already exist.
Missing source → UNKNOWN or NOT_CONFIGURED. This module does not open
the network, does not write connectors, and does not touch the Model C ledger.
"""
from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from core import cf_access
from core import esb_close_snapshot as _esb
from core import request_auth as _request_auth
from core import uma_alchemist_ro as _alc

BETA_ROOT = Path(__file__).resolve().parents[2]

ALLOWED = ("UNKNOWN", "NOT_CONFIGURED", "READ_OK", "DEGRADED", "ERROR")
_ALLOWED = frozenset(ALLOWED)

# Hard-coded statements. This module does not read or write the ledger.
LEDGER_UNCHANGED = {
    "CAP-INTG-01": "ABSENT",
    "CAP-INTG-07": "SPECIFIED",
}


def _status(value: str) -> str:
    if value in _ALLOWED:
        return value
    return "ERROR"


def _row(
    cap_id: str,
    name: str,
    status: str,
    *,
    source: str,
    evidence: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "cap_id": cap_id,
        "name": name,
        "status": _status(status),
        "source": source,
        "evidence": evidence,
        "external_writes": False,
        "promotes_ledger": False,
    }
    if cap_id in LEDGER_UNCHANGED:
        out["ledger_maturity_unchanged"] = LEDGER_UNCHANGED[cap_id]
    if out["status"] == "ERROR" and status not in _ALLOWED:
        out["evidence"] = "Status token refused. " + evidence
    return out


def _source(source_id: str, status: str, evidence: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "status": _status(status),
        "evidence": evidence,
        "external_writes": False,
    }


def _refused_path(path: Path) -> str | None:
    text = str(path)
    if text.endswith("money.sqlite") or "/Production" in text or "/wolf-system/" in text:
        return "refuses production or wolf-system path"
    return None


def _read_esb(path: Path | str | None) -> dict[str, Any]:
    """Presence of the ESB close warehouse. No snapshot write. No network."""
    try:
        resolved = _esb.resolve_esb_path(path)
    except Exception as exc:  # noqa: BLE001
        return _row(
            "CAP-INTG-02",
            "ESB Connector",
            "ERROR",
            source="esb_close_snapshot",
            evidence=f"path resolve failed: {type(exc).__name__}",
        )
    refused = _refused_path(resolved)
    if refused:
        return _row(
            "CAP-INTG-02",
            "ESB Connector",
            "ERROR",
            source="esb_close_snapshot",
            evidence=refused,
        )
    if not resolved.is_file():
        return _row(
            "CAP-INTG-02",
            "ESB Connector",
            "NOT_CONFIGURED",
            source="esb_close_snapshot",
            evidence="ESB warehouse file is not present. Not treated as readable.",
        )
    try:
        conn = _esb._connect_ro(resolved)
    except _esb.EsbSnapshotError as exc:
        status = "NOT_CONFIGURED" if exc.code == "esb_missing" else "ERROR"
        return _row(
            "CAP-INTG-02",
            "ESB Connector",
            status,
            source="esb_close_snapshot",
            evidence=f"{exc.code}: warehouse not readable",
        )
    except (OSError, sqlite3.Error) as exc:
        return _row(
            "CAP-INTG-02",
            "ESB Connector",
            "ERROR",
            source="esb_close_snapshot",
            evidence=f"readonly open failed: {type(exc).__name__}",
        )
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sales'"
        ).fetchone()
    except sqlite3.Error as exc:
        return _row(
            "CAP-INTG-02",
            "ESB Connector",
            "ERROR",
            source="esb_close_snapshot",
            evidence=f"schema read failed: {type(exc).__name__}",
        )
    finally:
        conn.close()
    if not row:
        return _row(
            "CAP-INTG-02",
            "ESB Connector",
            "DEGRADED",
            source="esb_close_snapshot",
            evidence="Warehouse file opened read-only. sales table is missing. settlement_api UNAVAILABLE.",
        )
    return _row(
        "CAP-INTG-02",
        "ESB Connector",
        "READ_OK",
        source="esb_close_snapshot",
        evidence=(
            "Warehouse file opened read-only and sales table is present. "
            "settlement_api UNAVAILABLE. This is not a full ESB connector prove."
        ),
    )


def _read_metricool() -> dict[str, Any]:
    """metricool_status() only. Does not load credentials or call the network."""
    try:
        import metricool_read_client as metricool
    except Exception as exc:  # noqa: BLE001
        return _row(
            "CAP-INTG-05",
            "Metricool Connector",
            "ERROR",
            source="metricool_read_client",
            evidence=f"reader import failed: {type(exc).__name__}",
        )
    try:
        raw = metricool.metricool_status()
    except Exception as exc:  # noqa: BLE001
        return _row(
            "CAP-INTG-05",
            "Metricool Connector",
            "ERROR",
            source="metricool_read_client",
            evidence=f"status read failed: {type(exc).__name__}",
        )
    enabled = bool(raw.get("enabled"))
    path_set = bool(raw.get("creds_path_configured"))
    write_on = bool(raw.get("write_enabled"))
    note = "status() does not load credentials and does not call Metricool."
    if write_on:
        note += " Write flag is set; this panel did not write."
    if not enabled:
        return _row(
            "CAP-INTG-05",
            "Metricool Connector",
            "NOT_CONFIGURED",
            source="metricool_read_client",
            evidence="BETA_METRICOOL_ENABLED is not on. " + note,
        )
    if not path_set:
        return _row(
            "CAP-INTG-05",
            "Metricool Connector",
            "NOT_CONFIGURED",
            source="metricool_read_client",
            evidence="Enabled but BETA_METRICOOL_CREDS_PATH is unset. " + note,
        )
    return _row(
        "CAP-INTG-05",
        "Metricool Connector",
        "UNKNOWN",
        source="metricool_read_client",
        evidence="Credential path is set. Read is not verified. " + note,
    )


def _read_cf_presence() -> dict[str, Any]:
    """Config presence only. Does not fetch JWKS or verify a JWT."""
    mode = _request_auth.auth_mode()
    if mode != _request_auth.AUTH_MODE_CLOUDFLARE:
        return _source(
            "cf_access",
            "NOT_CONFIGURED",
            f"Auth mode is {mode}. Live Cloudflare Access is not the active gate. JWKS not fetched.",
        )
    aud = _request_auth.access_audience()
    domain = _request_auth.team_domain()
    if not aud:
        return _source(
            "cf_access",
            "NOT_CONFIGURED",
            "BETA_CF_ACCESS_AUD is unset. JWKS not fetched.",
        )
    if not cf_access._ok_team_domain(domain):
        return _source(
            "cf_access",
            "ERROR",
            "Team domain shape refused. JWKS not fetched.",
        )
    return _source(
        "cf_access",
        "UNKNOWN",
        "Team domain and audience are present. JWT was not verified on this read. JWKS not fetched.",
    )


def _read_alchemist(path: Path | str | None) -> dict[str, Any]:
    """Bridge file presence. Does not project purchase rows and does not write."""
    flag = _alc.source_status()
    resolved: Path | None
    if path is not None:
        resolved = Path(path).expanduser()
    else:
        resolved = _alc.resolve_db_path()
    if resolved is None or not resolved.is_file():
        return _source(
            "alchemist",
            "NOT_CONFIGURED",
            f"Alchemist db is not attached. Published bridge flag is {flag}. No write.",
        )
    refused = _refused_path(resolved)
    if refused:
        return _source("alchemist", "ERROR", refused + f". Bridge flag {flag}.")
    try:
        conn = _alc.connect_readonly(resolved)
    except (OSError, sqlite3.Error, FileNotFoundError) as exc:
        return _source(
            "alchemist",
            "ERROR",
            f"readonly open failed: {type(exc).__name__}. Bridge flag {flag}.",
        )
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pr_orders'"
        ).fetchone()
    except sqlite3.Error as exc:
        return _source(
            "alchemist",
            "ERROR",
            f"schema read failed: {type(exc).__name__}. Bridge flag {flag}.",
        )
    finally:
        conn.close()
    if not row:
        return _source(
            "alchemist",
            "DEGRADED",
            f"File opened read-only. pr_orders is missing. Bridge flag {flag}. No write.",
        )
    return _source(
        "alchemist",
        "READ_OK",
        (
            f"File opened read-only and pr_orders is present. "
            f"Published bridge flag is {flag}. Not a Wolf-verified payment. No write."
        ),
    )


def _env_checks(root: Path) -> tuple[str, str]:
    env_ex = root / ".env.example"
    if not env_ex.is_file():
        return (
            "NOT_CONFIGURED",
            ".env.example is missing. Separation config was not read as present.",
        )
    bad = False
    try:
        text = env_ex.read_text(encoding="utf-8")
    except OSError:
        return ("ERROR", ".env.example could not be read.")
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        _, _, val = s.partition("=")
        val = val.strip().strip('"').strip("'")
        if not val:
            continue
        low = val.lower()
        if low.startswith("sk-") or "begin private" in low:
            bad = True
            break
    if bad:
        return ("ERROR", ".env.example contains a live-looking secret value.")

    gi_path = root / ".gitignore"
    try:
        gi = gi_path.read_text(encoding="utf-8")
    except OSError:
        return ("DEGRADED", ".env.example is present. .gitignore could not be read.")
    gil = gi.lower()
    missing = []
    if ".env" not in gi:
        missing.append(".env")
    if ".env.*" not in gi:
        missing.append(".env.*")
    if "!.env.example" not in gi:
        missing.append("!.env.example")
    if "*.pem" not in gil:
        missing.append("*.pem")
    if "*.key" not in gil:
        missing.append("*.key")
    if "*credentials*" not in gil:
        missing.append("*credentials*")
    if "*secret*" not in gil:
        missing.append("*secret*")
    if missing:
        return (
            "DEGRADED",
            "Separation files are partial. Missing gitignore markers: " + ", ".join(missing) + ".",
        )

    sacred = root / "docs" / "RULE-Beta-Construction-Production-Sacred-2026-09-16.md"
    try:
        sacred_text = sacred.read_text(encoding="utf-8")
    except OSError:
        return (
            "DEGRADED",
            "Gitignore markers are present. Sacred Beta/Production rule file is missing.",
        )
    if "PRODUCTION IS SACRED" not in sacred_text.upper():
        return ("DEGRADED", "Sacred rule file is present but the expected line is missing.")

    if not (root / ".git").exists():
        return (
            "DEGRADED",
            "Config files match. Git index is not available here, so tracked-dotenv was not confirmed.",
        )
    try:
        proc = subprocess.run(
            ["git", "ls-files", ".env", ".env.local"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ("ERROR", "git ls-files failed. Tracked-dotenv was not confirmed.")
    if proc.returncode != 0:
        return ("ERROR", "git ls-files failed. Tracked-dotenv was not confirmed.")
    tracked = [line for line in proc.stdout.splitlines() if line.strip()]
    if tracked:
        return ("ERROR", "A dotenv file is git-tracked.")
    return (
        "READ_OK",
        (
            "Local separation files were read: .env.example, gitignore markers, "
            "sacred rule, and dotenv is not git-tracked. This is config-file evidence only. "
            "It is not a secrets vault. Ledger maturity is not changed."
        ),
    )


def _read_env(root: Path | str | None) -> dict[str, Any]:
    base = Path(root) if root is not None else BETA_ROOT
    try:
        status, evidence = _env_checks(base)
    except Exception as exc:  # noqa: BLE001
        status, evidence = "ERROR", f"env read failed: {type(exc).__name__}"
    row = _row(
        "CAP-INTG-07",
        "Secrets & Environment Separation",
        status,
        source="env_separation",
        evidence=evidence,
    )
    return row


def _absent(cap_id: str, name: str, evidence: str) -> dict[str, Any]:
    return _row(cap_id, name, "NOT_CONFIGURED", source="none", evidence=evidence)


def build_report(
    *,
    esb_path: Path | str | None = None,
    alchemist_path: Path | str | None = None,
    env_root: Path | str | None = None,
) -> dict[str, Any]:
    """Owner report. Never calls the network. Never writes a connector or the ledger."""
    esb = _read_esb(esb_path)
    metricool = _read_metricool()
    env_row = _read_env(env_root)
    cf = _read_cf_presence()
    alchemist = _read_alchemist(alchemist_path)

    connectors = [
        _absent(
            "CAP-INTG-01",
            "Yanolja Connector",
            "No Yanolja reader in beta-os. This panel does not invent one. Ledger maturity stays ABSENT.",
        ),
        esb,
        _absent(
            "CAP-INTG-03",
            "Google Workspace Connector",
            "No Beta-local Google Workspace reader was called. Gmail, Drive, and Calendar were not probed.",
        ),
        _absent(
            "CAP-INTG-04",
            "Bank Statement Connector",
            "No authorised local bank-statement reader was called. No import was run.",
        ),
        metricool,
        _absent(
            "CAP-INTG-06",
            "Technology & Capability Registries",
            "No runtime registry reader. A catalog document is not this connector. Ledger maturity stays SPECIFIED.",
        ),
        env_row,
    ]
    for item in connectors:
        item["status"] = _status(item.get("status") or "")
    return {
        "ok": True,
        "bound": "beta-integration-health-readonly",
        "vocabulary": list(ALLOWED),
        "external_writes": False,
        "ledger_write": False,
        "network_probes": False,
        "connectors": connectors,
        "sources": [cf, alchemist],
    }
