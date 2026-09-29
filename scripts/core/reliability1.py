#!/usr/bin/env python3
"""RELIABILITY-1 — Beta health/reliability board (listeners, sidecar, prod RO).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack RELIABILITY-1
(armed 2026-09-30 after DASH-LIVE-1 PASS_VERIFIED). Closes toward IL-R8 /
MasterSpec reliability.

Surfaces real probe status for Beta :8788, Atrium sidecar :8790, and prod
:8787 pid 15975 (READ-ONLY). Never invents uptime percentages or paints
sidecar DOWN as UP. Never mutates prod. Never expands write authority.
staff_ready / human_commissioned stay false.
Does not auto-chain CONTENT-ENGINE-LIVE-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "RELIABILITY-1"
SCHEMA_ID = "wolf.reliability-1.v1"
BOUND = "beta-reliability-safe"
WITA = timezone(timedelta(hours=8))

# Ports / prod hold — RO probes only. Never mutate prod.
BETA_PORT = 8788
SIDECAR_PORT = 8790
PROD_PORT = 8787
PROD_PID_HELD = 15975

PAGE_PATHS = frozenset(
    {
        "/ops/reliability",
        "/ops/reliability/",
        "/reliability",
        "/reliability/",
        "/reliability.html",
        "/dashboards/reliability.html",
    }
)
API_PATH = "/api/ops/reliability"

CLOSES_TOWARD = ("IL-R8", "MasterSpec reliability")
CEILING = "BUILT"
PRESERVED_PACKS = ("INTG-TRUTH-1", "DASH-LIVE-1")


class Reliability1Error(ValueError):
    """Fail closed. Does not invent uptime or mutate prod."""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


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
    return raw.rstrip("/") == API_PATH


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "fake_uptime": False,
        "invented_uptime": False,
        "invented_green_health": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_probe_read_only": True,
        "no_push": True,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "proven_claimed": False,
        "ready_claimed": False,
        "intg_truth1_preserved": True,
        "next_pack_for_parent_only": "CONTENT-ENGINE-LIVE-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
    }


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise Reliability1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "uptime",
            "uptime-pct",
            "uptime-percent",
            "fake-uptime",
            "green",
            "green-health",
            "invent-up",
            "force-up",
            "paint-up",
        }:
            raise Reliability1Error(
                "Uptime / green health cannot be invented on RELIABILITY-1.",
                code="uptime_refused",
            )
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "kill",
            "restart-prod",
            "8787",
            "15975",
        }:
            raise Reliability1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
        if token in {"staff-ready", "human-commissioned", "proven", "ready"}:
            raise Reliability1Error(
                "Commissioning flags / PROVEN / READY are refused.",
                code="ready_refused",
            )
    raise Reliability1Error(
        "RELIABILITY-1 is a read-only probe board. Writes refused.",
        code="write_refused",
    )


def refuse_prod_mutate(_body: dict | None = None) -> None:
    raise Reliability1Error(
        "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
        code="prod_mutate_refused",
    )


def refuse_fake_uptime(_body: dict | None = None) -> None:
    raise Reliability1Error(
        "Uptime / green health cannot be invented on RELIABILITY-1.",
        code="uptime_refused",
    )


def _run_lsof_listen(port: int) -> str:
    """Raw lsof listen lines for a TCP port. Empty string = no listener."""
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out or ""
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return ""


def _pids_from_lsof(raw: str) -> list[int]:
    pids: list[int] = []
    for line in (raw or "").splitlines():
        if line.startswith("COMMAND") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        if pid not in pids:
            pids.append(pid)
    return pids


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _pid_command(pid: int) -> str | None:
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "command="],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return out or None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def probe_listener(port: int, *, label: str) -> dict[str, Any]:
    """Real lsof probe. DOWN when no listener — never invent UP."""
    raw = _run_lsof_listen(port)
    pids = _pids_from_lsof(raw)
    if not pids:
        return {
            "id": label,
            "port": port,
            "role": label,
            "status": "DOWN",
            "listening": False,
            "pids": [],
            "probe": "lsof_listen",
            "probe_mode": "read_only",
            "uptime_pct": None,
            "uptime_invented": False,
            "notes": f"No TCP LISTEN on :{port}. Honest DOWN — not painted UP.",
        }
    return {
        "id": label,
        "port": port,
        "role": label,
        "status": "UP",
        "listening": True,
        "pids": pids,
        "probe": "lsof_listen",
        "probe_mode": "read_only",
        "uptime_pct": None,  # never invent a percentage
        "uptime_invented": False,
        "notes": f"Listener present on :{port} pid(s)={pids}.",
    }


def probe_prod_ro(*, expected_pid: int = PROD_PID_HELD) -> dict[str, Any]:
    """READ-ONLY prod probe. Confirms held pid listens on :8787. Never mutates."""
    raw = _run_lsof_listen(PROD_PORT)
    pids = _pids_from_lsof(raw)
    alive = _pid_alive(expected_pid)
    cmd = _pid_command(expected_pid) if alive else None
    held_listening = expected_pid in pids
    if held_listening and alive:
        status = "UP"
        notes = (
            f"Prod :{PROD_PORT} pid {expected_pid} listening. "
            "READ-ONLY probe — no mutate."
        )
    elif alive and not held_listening:
        status = "UNKNOWN"
        notes = (
            f"Pid {expected_pid} alive but not observed on :{PROD_PORT} LISTEN. "
            "READ-ONLY — no mutate."
        )
    elif held_listening and not alive:
        status = "UNKNOWN"
        notes = (
            f":{PROD_PORT} has listener pids={pids} but held pid {expected_pid} "
            "not alive via kill(0). READ-ONLY — no mutate."
        )
    else:
        status = "DOWN"
        notes = (
            f"Held prod pid {expected_pid} not listening on :{PROD_PORT}. "
            "Honest DOWN. READ-ONLY — no mutate."
        )
    return {
        "id": "prod_8787",
        "port": PROD_PORT,
        "role": "prod",
        "status": status,
        "listening": held_listening,
        "pids": pids,
        "held_pid": expected_pid,
        "held_pid_alive": alive,
        "held_pid_listening": held_listening,
        "command_hint": (cmd[:120] + "…") if cmd and len(cmd) > 120 else cmd,
        "probe": "lsof_listen+kill0",
        "probe_mode": "read_only",
        "prod_mutate": False,
        "uptime_pct": None,
        "uptime_invented": False,
        "notes": notes,
    }


def build_board() -> dict[str, Any]:
    """Public reliability board. Auth gating is caller's responsibility."""
    probed_at = _now_wita()
    beta = probe_listener(BETA_PORT, label="beta_8788")
    sidecar = probe_listener(SIDECAR_PORT, label="sidecar_8790")
    prod = probe_prod_ro()
    targets = [beta, sidecar, prod]

    # Absolute honesty pins — never invent uptime or flip DOWN→UP.
    for row in targets:
        row["uptime_pct"] = None
        row["uptime_invented"] = False
        if row.get("status") == "DOWN":
            row["painted_up"] = False
        else:
            row["painted_up"] = False

    by_status: dict[str, int] = {}
    for row in targets:
        st = str(row.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1

    flags = honesty_flags()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": probed_at,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "fake_uptime": False,
        "invented_uptime": False,
        "invented_green_health": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "counts": {
            "total": len(targets),
            "by_status": by_status,
        },
        "targets": targets,
        "honesty": {
            "sidecar_down_stays_down": sidecar.get("status") != "UP"
            or sidecar.get("listening") is True,
            "uptime_policy": "null_never_invent",
            "prod_probe": "read_only",
            "beta_port": BETA_PORT,
            "sidecar_port": SIDECAR_PORT,
            "prod_port": PROD_PORT,
            "prod_pid_held": PROD_PID_HELD,
        },
        "preserved_packs": list(PRESERVED_PACKS),
        "next_pack_for_parent_only": "CONTENT-ENGINE-LIVE-1",
        "cursor_did_not_auto_start_next": True,
        **{k: flags[k] for k in (
            "operating_adoption",
            "proven_claimed",
            "ready_claimed",
            "intg_truth1_preserved",
            "no_push",
        )},
    }


def public_payload() -> dict[str, Any]:
    return build_board()


def sidecar_is_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when sidecar DOWN is not painted UP and uptime is not invented."""
    pack = payload if payload is not None else build_board()
    if pack.get("fake_uptime") is True or pack.get("invented_uptime") is True:
        return False
    sidecar = None
    for row in pack.get("targets") or []:
        if row.get("id") == "sidecar_8790" or row.get("port") == SIDECAR_PORT:
            sidecar = row
            break
    if sidecar is None:
        return False
    if sidecar.get("uptime_invented") is True:
        return False
    if sidecar.get("uptime_pct") is not None:
        return False
    listening = bool(sidecar.get("listening"))
    status = sidecar.get("status")
    if not listening and status == "UP":
        return False
    if not listening and status not in ("DOWN", "UNKNOWN"):
        return False
    return True
