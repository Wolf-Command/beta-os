#!/usr/bin/env python3
"""BACKUP-HEALTH-1 — Backup/recovery health stamps (Beta catalog + atrium RO).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BACKUP-HEALTH-1
(armed 2026-09-30 after ESB-TRUTH-1 PASS_VERIFIED). Closes toward reliability
backup.

Surfaces last-backup / restore-drill honesty from Beta catalog ledger +
restore-drill framework + atrium RO staging (monitoring-snapshot). Never
invents backup success or restore-drill PASS. Missing stamps stay
UNKNOWN/MISSING. Preserves RELIABILITY-1 honesty.
staff_ready / human_commissioned stay false.
Does not auto-chain FIN-CASH-TRUTH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import reliability1 as _reliability1
from core import restore_drill as _restore_drill

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

# Atrium RO staging — never read live ~/.openclaw in scheduled context;
# interactive Beta board prefers the same staged atrium RO facts.
ATRIUM_RO_ROOT = Path("/Users/wolfterminal/monitoring-snapshot")
ATRIUM_BACKUP_STATUS = ATRIUM_RO_ROOT / "raw" / "backup_status.json"
ATRIUM_NAS_KEEPALIVE = ATRIUM_RO_ROOT / "raw" / "nas-keepalive.log"
ATRIUM_MANIFEST = ATRIUM_RO_ROOT / "manifest.json"

PACK_ID = "BACKUP-HEALTH-1"
SCHEMA_ID = "wolf.backup-health-1.v1"
BOUND = "beta-backup-health-safe"
CAP_ID = "CAP-DR-01"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
SNAPSHOT_STALE_MINUTES = 90

PAGE_PATHS = frozenset(
    {
        "/ops/backup-health-1",
        "/ops/backup-health-1/",
        "/ops/backup-health",
        "/ops/backup-health/",
        "/backup-health-1",
        "/backup-health-1/",
        "/backup-health",
        "/backup-health/",
        "/backup-health-1.html",
        "/dashboards/backup-health-1.html",
    }
)
API_PATH = "/api/ops/backup-health-1"

CLOSES_TOWARD = ("reliability backup",)
CEILING = "BUILT"
PRESERVED_PACKS = ("RELIABILITY-1", "ESB-TRUTH-1")


class BackupHealth1Error(ValueError):
    """Fail closed. Does not invent backup/restore success or mutate prod."""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _now_dt() -> datetime:
    return datetime.now(WITA)


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
        "cap": CAP_ID,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "fake_backup_success": False,
        "invented_backup_ok": False,
        "invented_restore_pass": False,
        "restore_drill_pass_invented": False,
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
        "reliability1_preserved": True,
        "next_pack_for_parent_only": "FIN-CASH-TRUTH-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
    }


def refuse_fake_backup_success(_body: dict | None = None) -> None:
    raise BackupHealth1Error(
        "Backup success cannot be invented on BACKUP-HEALTH-1.",
        code="backup_success_refused",
    )


def refuse_fake_restore_pass(_body: dict | None = None) -> None:
    raise BackupHealth1Error(
        "Restore-drill PASS cannot be invented on BACKUP-HEALTH-1.",
        code="restore_pass_refused",
    )


def refuse_prod_mutate(_body: dict | None = None) -> None:
    raise BackupHealth1Error(
        "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
        code="prod_mutate_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise BackupHealth1Error("Write payload refused.", code="write_refused")

    # Nested action tokens first
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if action in {"restore", "run", "execute", "pass", "success", "drill-pass"}:
        refuse_fake_restore_pass(payload)
    if (
        payload.get("restore_pass")
        or payload.get("drill_pass")
        or payload.get("live_restore")
        or payload.get("restore")
        or payload.get("run")
    ):
        refuse_fake_restore_pass(payload)
    if (
        payload.get("backup_success")
        or payload.get("fake_backup")
        or payload.get("invent_backup")
        or payload.get("local_ok") is True
    ):
        refuse_fake_backup_success(payload)

    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "restore",
            "restore-drill",
            "restore-pass",
            "restore-success",
            "drill-pass",
            "drill-passed",
            "drill-success",
            "drill-status",
            "live-restore",
            "fake-restore",
            "invent-restore",
            "invent-drill-pass",
            "run-restore",
            "execute-restore",
            "run",
            "execute",
        }:
            refuse_fake_restore_pass(payload)
        if token in {
            "backup-success",
            "fake-backup",
            "fake-backup-success",
            "invent-backup",
            "paint-backup-ok",
            "force-backup-ok",
            "backup-ok",
            "b2-ok-force",
            "local-ok-force",
            "status-success",
            "force-success",
            "paint-ok",
            "paint-success",
        }:
            refuse_fake_backup_success(payload)
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "kill",
            "restart-prod",
            "8787",
            "15975",
        }:
            refuse_prod_mutate(payload)
        if token in {"staff-ready", "human-commissioned", "proven", "ready"}:
            raise BackupHealth1Error(
                "Commissioning flags / PROVEN / READY are refused.",
                code="ready_refused",
            )
    raise BackupHealth1Error(
        "BACKUP-HEALTH-1 is a read-only stamps board. Writes refused.",
        code="write_refused",
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _parse_iso(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=WITA)
        return dt.astimezone(WITA)
    except ValueError:
        return None


def _atrium_snapshot_freshness() -> dict[str, Any]:
    """RO freshness of atrium staging. STALE if missing or >90 min."""
    manifest = _read_json(ATRIUM_MANIFEST)
    if not manifest:
        return {
            "id": "atrium_snapshot",
            "label": "Atrium RO snapshot",
            "status": "MISSING",
            "source": str(ATRIUM_MANIFEST),
            "generated_at": None,
            "age_minutes": None,
            "stale": True,
            "notes": "monitoring-snapshot/manifest.json missing — atrium RO unavailable.",
            "probe_mode": "read_only",
            "success_invented": False,
        }
    generated = manifest.get("generated_at")
    dt = _parse_iso(str(generated) if generated is not None else None)
    if dt is None:
        return {
            "id": "atrium_snapshot",
            "label": "Atrium RO snapshot",
            "status": "UNKNOWN",
            "source": str(ATRIUM_MANIFEST),
            "generated_at": generated,
            "age_minutes": None,
            "stale": True,
            "notes": "manifest present but generated_at unparseable.",
            "probe_mode": "read_only",
            "success_invented": False,
        }
    age_min = (_now_dt() - dt).total_seconds() / 60.0
    stale = age_min > SNAPSHOT_STALE_MINUTES
    return {
        "id": "atrium_snapshot",
        "label": "Atrium RO snapshot",
        "status": "STALE" if stale else "PRESENT",
        "source": str(ATRIUM_MANIFEST),
        "generated_at": generated,
        "age_minutes": round(age_min, 1),
        "stale": stale,
        "notes": (
            f"Snapshot age {age_min:.0f} min "
            f"({'STALE >' + str(SNAPSHOT_STALE_MINUTES) + 'm' if stale else 'within window'})."
        ),
        "probe_mode": "read_only",
        "success_invented": False,
    }


def _stamp_last_backup() -> dict[str, Any]:
    """Last-backup stamp from atrium RO backup_status.json. Never invents ok."""
    data = _read_json(ATRIUM_BACKUP_STATUS)
    if data is None:
        return {
            "id": "last_backup",
            "label": "Last backup (atrium RO)",
            "status": "MISSING",
            "source": str(ATRIUM_BACKUP_STATUS),
            "last_run": None,
            "local_ok": None,
            "b2_ok": None,
            "secrets_encrypted_ok": None,
            "local_size_bytes": None,
            "files_count": None,
            "git_push": None,
            "atrium_git_push": None,
            "notes": "backup_status.json missing from atrium RO staging — stamp MISSING.",
            "probe_mode": "read_only",
            "success_invented": False,
            "fake_backup_success": False,
        }

    # Surface reported flags as RO facts only — do not upgrade to "recovery healthy".
    local_ok = data.get("local_ok")
    b2_ok = data.get("b2_ok")
    secrets_ok = data.get("secrets_encrypted_ok")
    last_run = data.get("last_run")
    git_push = data.get("git_push") if isinstance(data.get("git_push"), list) else None
    atrium_push = None
    if git_push:
        for row in git_push:
            if isinstance(row, str) and row.lower().startswith("atrium:"):
                atrium_push = row
                break

    # Status is PRESENT when the stamp file exists — not SUCCESS.
    # If both local/b2 reported false → stamp still PRESENT with honest flags.
    if local_ok is None and b2_ok is None and last_run is None:
        status = "UNKNOWN"
        notes = "backup_status present but core fields empty — UNKNOWN."
    else:
        status = "PRESENT"
        notes = (
            "Atrium RO stamp only. local_ok/b2_ok are reported flags, "
            "not a restore-drill pass and not invented recovery health."
        )

    return {
        "id": "last_backup",
        "label": "Last backup (atrium RO)",
        "status": status,
        "source": str(ATRIUM_BACKUP_STATUS),
        "last_run": last_run,
        "local_ok": local_ok if isinstance(local_ok, bool) else None,
        "b2_ok": b2_ok if isinstance(b2_ok, bool) else None,
        "b2_error": data.get("b2_error"),
        "secrets_encrypted_ok": secrets_ok if isinstance(secrets_ok, bool) else None,
        "local_size_bytes": data.get("local_size_bytes"),
        "files_count": data.get("files_count"),
        "git_push": git_push,
        "atrium_git_push": atrium_push,
        "local_path_reported": data.get("local_path"),
        "notes": notes,
        "probe_mode": "read_only",
        "success_invented": False,
        "fake_backup_success": False,
    }


def _stamp_restore_drill() -> dict[str, Any]:
    """Restore-drill stamp.

    Prefer BACKUP-RESTORE-DRILL-1 non-destructive log when present
    (lifts NOT_RUN → DRILL_RAN_NON_DESTRUCTIVE). Otherwise framework NOT_RUN.
    Never invent SUCCESS/PASS/READY without that authorised drill log.
    """
    # Lazy import avoids circular import with backup_restore_drill1.
    try:
        from core import backup_restore_drill1 as _brd  # noqa: PLC0415

        log = _brd.load_drill_log()
    except Exception:  # noqa: BLE001
        log = None

    if isinstance(log, dict) and str(log.get("status") or "").upper() == "SUCCESS":
        sha_ok = log.get("sha256_match") is True
        prod_mut = log.get("production_mutated") is True
        if sha_ok and not prod_mut:
            return {
                "id": "restore_drill",
                "label": "Restore drill (Beta)",
                "status": "DRILL_RAN_NON_DESTRUCTIVE",
                "source": "core.backup_restore_drill1",
                "drill_status": "SUCCESS",
                "honesty_status": "DRILL_RAN_NON_DESTRUCTIVE",
                "last_drill_at": log.get("recorded_at"),
                "target_path": log.get("target_path"),
                "source_path": log.get("source_path"),
                "production_mutated": False,
                "live_restore": False,
                "sha256_match": True,
                "framework_skeleton": "BUILT",
                "historical_is_this_drill": False,
                "full_dr_ready_claimed": False,
                "proven_scope": "non_destructive_temp_only",
                "notes": (
                    "BACKUP-RESTORE-DRILL-1 authorised non-destructive temp-dir drill "
                    "ran with sha256 match. Not full DR READY (NAS/B2)."
                ),
                "probe_mode": "non_destructive_temp",
                "success_invented": False,
                "pass_invented": False,
            }

    try:
        framework = _restore_drill.build_framework()
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "restore_drill",
            "label": "Restore drill (Beta)",
            "status": "UNKNOWN",
            "source": "core.restore_drill",
            "drill_status": None,
            "live_restore": False,
            "framework_skeleton": None,
            "historical_is_this_drill": False,
            "notes": f"restore_drill framework unavailable: {type(exc).__name__}",
            "probe_mode": "read_only",
            "success_invented": False,
            "pass_invented": False,
        }

    status = str(framework.get("status") or "NOT_RUN").upper()
    # Absolute honesty: never promote to SUCCESS/PASS from this pack alone.
    if status in _restore_drill._SUCCESS_STATUS:  # noqa: SLF001
        return {
            "id": "restore_drill",
            "label": "Restore drill (Beta)",
            "status": "UNKNOWN",
            "source": "core.restore_drill",
            "drill_status": status,
            "live_restore": False,
            "framework_skeleton": framework.get("framework_skeleton"),
            "historical_is_this_drill": False,
            "notes": (
                f"Framework returned {status}; BACKUP-HEALTH-1 will not surface "
                "invented/elevated PASS. Holding UNKNOWN."
            ),
            "probe_mode": "read_only",
            "success_invented": False,
            "pass_invented": False,
            "refused_elevated_pass": True,
        }

    historical = framework.get("historical") or {}
    return {
        "id": "restore_drill",
        "label": "Restore drill (Beta)",
        "status": status if status else "NOT_RUN",
        "source": "core.restore_drill",
        "drill_status": status if status else "NOT_RUN",
        "live_restore": False,
        "framework_skeleton": framework.get("framework_skeleton"),
        "checklist_executed": framework.get("checklist_executed"),
        "checklist_count": framework.get("checklist_count"),
        "historical_id": (historical or {}).get("id") if isinstance(historical, dict) else None,
        "historical_is_this_drill": bool((historical or {}).get("is_this_drill"))
        if isinstance(historical, dict)
        else False,
        "historical_counts_as_live_success": bool(
            (historical or {}).get("counts_as_live_success")
        )
        if isinstance(historical, dict)
        else False,
        "notes": (
            "Framework skeleton only. Status stays NOT_RUN until an authorised "
            "CAP-bound drill records a real result elsewhere. Historical 2026-08-29 "
            "is not this drill."
        ),
        "probe_mode": "read_only",
        "success_invented": False,
        "pass_invented": False,
    }


def _stamp_cap_dr_01() -> dict[str, Any]:
    """CAP-DR-01 maturity from Beta catalog ledger. Never raises."""
    maturity = _restore_drill.ledger_cap_state(LEDGER_JSON)
    if maturity in ("PROVEN", "READY"):
        # Do not invent higher — but if ledger already higher, report as-read with pin.
        notes = (
            f"Ledger reads {maturity}. This pack does not claim or raise maturity; "
            "ceiling for this board remains BUILT unless Owner already raised."
        )
        board_status = maturity
    elif maturity == "UNKNOWN":
        notes = "CAP-DR-01 row missing or unreadable in Beta catalog ledger."
        board_status = "UNKNOWN"
    else:
        notes = (
            f"Ledger maturity {maturity}. Owner rejected PROVEN 2026-09-18 until "
            "deterministic CAP-bound restore-drill proof. This pack does not raise."
        )
        board_status = maturity

    return {
        "id": "cap_dr_01",
        "label": "CAP-DR-01 (Beta catalog)",
        "status": board_status,
        "source": str(LEDGER_JSON),
        "maturity": maturity,
        "catalog_db_present": CATALOG_DB.is_file(),
        "notes": notes,
        "probe_mode": "read_only",
        "success_invented": False,
        "maturity_raised": False,
        "proven_claimed": False,
        "ready_claimed": False,
    }


def _stamp_historical_b2() -> dict[str, Any]:
    """Historical B2 drill retained as history only — not live success."""
    hist = _restore_drill.HISTORICAL
    return {
        "id": "historical_b2_drill",
        "label": "Historical B2 drill",
        "status": "HISTORICAL",
        "source": hist.get("document"),
        "historical_id": hist.get("id"),
        "is_this_drill": bool(hist.get("is_this_drill")),
        "counts_as_live_success": bool(hist.get("counts_as_live_success")),
        "counts_as_ready": bool(hist.get("counts_as_ready")),
        "notes": hist.get("why"),
        "probe_mode": "read_only",
        "success_invented": False,
        "pass_invented": False,
    }


def _stamp_nas_keepalive() -> dict[str, Any]:
    """NAS keepalive RO tail from atrium staging. Never invents OK."""
    path = ATRIUM_NAS_KEEPALIVE
    if not path.is_file():
        return {
            "id": "nas_keepalive",
            "label": "NAS keepalive (atrium RO)",
            "status": "MISSING",
            "source": str(path),
            "tail": None,
            "notes": "nas-keepalive.log missing from atrium RO staging.",
            "probe_mode": "read_only",
            "success_invented": False,
        }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {
            "id": "nas_keepalive",
            "label": "NAS keepalive (atrium RO)",
            "status": "UNKNOWN",
            "source": str(path),
            "tail": None,
            "notes": "nas-keepalive.log unreadable.",
            "probe_mode": "read_only",
            "success_invented": False,
        }
    lines = [ln for ln in text.splitlines() if ln.strip()]
    tail = lines[-5:] if lines else []
    joined = "\n".join(tail)
    # Honest classification from text — never invent green health.
    if re.search(r"\bRED\b", joined) or "dropped" in joined.lower():
        status = "PARTIAL"
        notes = "Atrium RO tail shows RED/dropped shares — not painted OK."
    elif re.search(r"\bOK\b", joined) and not re.search(r"\bRED\b", joined):
        status = "PRESENT"
        notes = "Atrium RO tail present; not a restore proof."
    elif not tail:
        status = "UNKNOWN"
        notes = "Log empty — UNKNOWN."
    else:
        status = "PRESENT"
        notes = "Atrium RO tail present; classify without inventing backup success."

    return {
        "id": "nas_keepalive",
        "label": "NAS keepalive (atrium RO)",
        "status": status,
        "source": str(path),
        "tail": tail,
        "notes": notes,
        "probe_mode": "read_only",
        "success_invented": False,
    }


def _stamp_reliability1_preserved() -> dict[str, Any]:
    """Pin that RELIABILITY-1 honesty remains intact (no invent uptime)."""
    try:
        board = _reliability1.build_board()
        honest = _reliability1.sidecar_is_honest(board)
        fake = board.get("fake_uptime") is True or board.get("invented_uptime") is True
        status = "PRESERVED" if honest and not fake else "BROKEN"
        notes = (
            "RELIABILITY-1 probe board still honest (no fake uptime)."
            if status == "PRESERVED"
            else "RELIABILITY-1 honesty pin broken — investigate."
        )
    except Exception as exc:  # noqa: BLE001
        status = "UNKNOWN"
        notes = f"Could not load RELIABILITY-1: {type(exc).__name__}"
        honest = False

    return {
        "id": "reliability1",
        "label": "RELIABILITY-1 preserved",
        "status": status,
        "source": "core.reliability1",
        "sidecar_honest": bool(honest) if status != "UNKNOWN" else None,
        "notes": notes,
        "probe_mode": "read_only",
        "success_invented": False,
    }


def build_board() -> dict[str, Any]:
    """Public backup/recovery health stamps board. Auth is caller's job."""
    as_of = _now_wita()
    stamps = [
        _atrium_snapshot_freshness(),
        _stamp_last_backup(),
        _stamp_restore_drill(),
        _stamp_cap_dr_01(),
        _stamp_historical_b2(),
        _stamp_nas_keepalive(),
        _stamp_reliability1_preserved(),
    ]

    # Absolute honesty pins on every stamp.
    _allowed_restore = {
        "NOT_RUN",
        "UNKNOWN",
        "MISSING",
        "DRILL_RAN_NON_DESTRUCTIVE",
        "FAIL",
    }
    for row in stamps:
        row["success_invented"] = False
        row.setdefault("fake_backup_success", False)
        row.setdefault("pass_invented", False)
        # Never paint restore as bare SUCCESS/PASS/READY on this board.
        # DRILL_RAN_NON_DESTRUCTIVE is the authorised honesty lift.
        if row.get("id") == "restore_drill":
            st = str(row.get("status") or "").upper()
            if st in _restore_drill._SUCCESS_STATUS or st in {"READY", "PROVEN"}:  # noqa: SLF001
                row["status"] = "UNKNOWN"
                row["pass_invented"] = False
                row["refused_elevated_pass"] = True
            elif st not in _allowed_restore and st:
                row["status"] = "UNKNOWN"
                row["pass_invented"] = False
                row["refused_elevated_pass"] = True

    by_status: dict[str, int] = {}
    for row in stamps:
        st = str(row.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1

    restore = next((s for s in stamps if s.get("id") == "restore_drill"), {})
    last_backup = next((s for s in stamps if s.get("id") == "last_backup"), {})
    flags = honesty_flags()
    restore_status = str(restore.get("status") or "").upper()

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap": CAP_ID,
        "as_of_wita": as_of,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "fake_backup_success": False,
        "invented_backup_ok": False,
        "invented_restore_pass": False,
        "restore_drill_pass_invented": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "last_drill_at": restore.get("last_drill_at"),
        "production_mutated": False,
        "counts": {
            "total": len(stamps),
            "by_status": by_status,
        },
        "stamps": stamps,
        "honesty": {
            "last_backup_is_not_restore": True,
            "restore_drill_status": restore.get("status"),
            "restore_drill_not_pass": restore_status
            not in _restore_drill._SUCCESS_STATUS,  # noqa: SLF001
            "restore_drill_lifted_non_destructive": restore_status
            == "DRILL_RAN_NON_DESTRUCTIVE",
            "last_drill_at": restore.get("last_drill_at"),
            "target_path": restore.get("target_path"),
            "production_mutated": False,
            "full_dr_ready_claimed": False,
            "historical_not_this_drill": True,
            "backup_status_source": "atrium_ro_monitoring_snapshot",
            "catalog_source": "beta_ledger+restore_drill+backup_restore_drill1",
            "missing_stays_missing": True,
            "uptime_policy_from_reliability1": "null_never_invent",
            "prod_probe": "read_only",
            "prod_pid_held": PROD_PID_HELD,
        },
        "preserved_packs": list(PRESERVED_PACKS),
        "next_pack_for_parent_only": "FIN-CASH-TRUTH-1",
        "cursor_did_not_auto_start_next": True,
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "proven_claimed",
                "ready_claimed",
                "reliability1_preserved",
                "no_push",
            )
        },
    }


def public_payload() -> dict[str, Any]:
    return build_board()


def restore_drill_is_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when restore-drill is not painted PASS and success is not invented.

    DRILL_RAN_NON_DESTRUCTIVE is honest only when backed by a real
    BACKUP-RESTORE-DRILL-1 log (sha256 match, production_mutated=false).
    """
    pack = payload if payload is not None else build_board()
    if pack.get("fake_backup_success") is True:
        return False
    if pack.get("invented_restore_pass") is True:
        return False
    if pack.get("restore_drill_pass_invented") is True:
        return False
    restore = None
    for row in pack.get("stamps") or []:
        if row.get("id") == "restore_drill":
            restore = row
            break
    if restore is None:
        return False
    if restore.get("pass_invented") is True or restore.get("success_invented") is True:
        return False
    status = str(restore.get("status") or "").upper()
    if status in _restore_drill._SUCCESS_STATUS or status in {"READY", "PROVEN"}:  # noqa: SLF001
        return False
    if status == "DRILL_RAN_NON_DESTRUCTIVE":
        return (
            restore.get("sha256_match") is True
            and restore.get("production_mutated") is False
            and restore.get("live_restore") is False
            and bool(restore.get("last_drill_at"))
            and bool(restore.get("target_path"))
        )
    return status in ("NOT_RUN", "UNKNOWN", "MISSING", "FAIL")
