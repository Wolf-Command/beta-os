#!/usr/bin/env python3
"""BACKUP-RESTORE-DRILL-1 — Non-destructive restore drill (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
BACKUP-RESTORE-DRILL-1 (armed 2026-09-30 after OWNER-EXCEPTIONS-LIVE-1
PASS_VERIFIED). Extends 2026-09-19 PICK CAP-DR-01 restore-drill framework
beyond skeleton-only: runs an approved copy into a new empty temp directory,
verifies sha256, and records an honest drill log.

Never mutates Production, NAS, or B2. Never deletes sources. Never claims
full DR READY. Ceiling for this pack is PROVEN for *non-destructive temp
drill only*. staff_ready / human_commissioned stay false.
Preserves BACKUP-HEALTH-1 + RELIABILITY-1 + restore_drill refuse_* guards.
Does not auto-chain PIPE-RELIABILITY-AUTO-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import reliability1 as _reliability1
from core import restore_drill as _restore_drill

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BACKUPS_DIR = BETA_ROOT / "state" / "backups"
FIXTURE_DIR = BETA_ROOT / "state" / "final-completion" / "fixtures"
DRILL_LOG_PATH = (
    BETA_ROOT / "state" / "final-completion" / "packs" / "BACKUP-RESTORE-DRILL-1-LOG.json"
)

PACK_ID = "BACKUP-RESTORE-DRILL-1"
SCHEMA_ID = "wolf.backup-restore-drill-1.v1"
LOG_SCHEMA_ID = "wolf.backup-restore-drill-1.log.v1"
BOUND = "beta-backup-restore-drill-safe"
CAP_ID = "CAP-DR-01"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))

# Board honesty status — NOT a fake full-DR PASS/READY.
HONESTY_STATUS = "DRILL_RAN_NON_DESTRUCTIVE"
CEILING = "PROVEN_NON_DESTRUCTIVE_ONLY"
CLOSES_TOWARD = ("CAP-DR-01", "reliability restore")
PRESERVED_PACKS = ("BACKUP-HEALTH-1", "RELIABILITY-1")

PAGE_PATHS = frozenset(
    {
        "/ops/backup-restore-drill-1",
        "/ops/backup-restore-drill-1/",
        "/ops/backup-restore-drill",
        "/ops/backup-restore-drill/",
        "/backup-restore-drill-1",
        "/backup-restore-drill-1/",
        "/backup-restore-drill-1.html",
        "/dashboards/backup-restore-drill-1.html",
    }
)
API_PATH = "/api/ops/backup-restore-drill-1"

_FORBIDDEN_TARGET_TOKENS = (
    "/production",
    "money.sqlite",
    "/nas/",
    "b2:",
    "b2://",
    "backblaze",
    "alchemist",
    "wolf-system",
)


class BackupRestoreDrill1Error(ValueError):
    """Fail closed. Does not mutate prod/NAS/B2 or invent full-DR READY."""

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
        "cap": CAP_ID,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_probe_read_only": True,
        "no_push": True,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "source_deleted": False,
        "full_dr_ready_claimed": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "proven_scope": "non_destructive_temp_only",
        "ceiling": CEILING,
        "shell_ne_complete": True,
        "classification": "INTERNALLY_SOLVABLE",
        "closes_toward": list(CLOSES_TOWARD),
        "honesty_status": HONESTY_STATUS,
        "backup_health1_preserved": True,
        "reliability1_preserved": True,
        "restore_drill_guards_preserved": True,
        "next_pack_for_parent_only": "PIPE-RELIABILITY-AUTO-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
    }


def refuse_production(_body: dict | None = None) -> None:
    raise BackupRestoreDrill1Error(
        "Production mutation is refused on BACKUP-RESTORE-DRILL-1.",
        code="production_refused",
    )


def refuse_nas(_body: dict | None = None) -> None:
    raise BackupRestoreDrill1Error(
        "NAS destructive access is refused on BACKUP-RESTORE-DRILL-1.",
        code="nas_destructive_refused",
    )


def refuse_b2(_body: dict | None = None) -> None:
    raise BackupRestoreDrill1Error(
        "B2 destructive access is refused on BACKUP-RESTORE-DRILL-1.",
        code="b2_destructive_refused",
    )


def refuse_live_restore(_body: dict | None = None) -> None:
    raise BackupRestoreDrill1Error(
        "Live/destructive restore is refused. Only temp-dir non-destructive copy is authorised.",
        code="live_restore_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise BackupRestoreDrill1Error(
        "Full DR READY is refused. Non-destructive drill ≠ DR READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Board is read-only after drill. Destructive / commissioning writes refuse."""
    payload = body or {}
    if not isinstance(payload, dict):
        raise BackupRestoreDrill1Error("Write payload refused.", code="write_refused")

    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if action in {"nas"}:
        refuse_nas(payload)
    if action in {"b2"}:
        refuse_b2(payload)
    if action in {"production"}:
        refuse_production(payload)
    if action in {"restore", "run", "execute", "live", "copy"}:
        refuse_live_restore(payload)
    if action in {"ready", "proven"}:
        refuse_ready(payload) if action == "ready" else None
        if action == "proven":
            raise BackupRestoreDrill1Error(
                "Ledger maturity raise / full PROVEN claim refused.",
                code="proven_refused",
            )

    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "production",
            "kill",
            "8787",
            "15975",
        }:
            refuse_production(payload)
        if token in {"nas", "nas-delete", "nas-wipe", "nas-destructive"}:
            refuse_nas(payload)
        if token in {"b2", "b2-delete", "b2-destructive", "backblaze"}:
            refuse_b2(payload)
        if token in {
            "live-restore",
            "destructive-restore",
            "restore-prod",
            "run-live",
            "restore",
            "run",
            "execute",
        }:
            refuse_live_restore(payload)
        if token in {
            "staff-ready",
            "human-commissioned",
            "ready",
            "full-dr-ready",
            "dr-ready",
        }:
            refuse_ready(payload)
        if token in {"proven", "raise-ledger", "model-c-write"}:
            raise BackupRestoreDrill1Error(
                "Ledger maturity raise / full PROVEN claim refused.",
                code="proven_refused",
            )

    # Also exercise framework refuse_* so guards stay pinned.
    try:
        _restore_drill.refuse_external_write(payload)
    except _restore_drill.RestoreDrillError as exc:
        raise BackupRestoreDrill1Error(str(exc), code=exc.code) from exc
    raise BackupRestoreDrill1Error(
        "BACKUP-RESTORE-DRILL-1 board is read-only after the authorised temp drill.",
        code="write_refused",
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _guard_source(path: Path) -> Path:
    resolved = path.resolve()
    low = str(resolved).lower()
    for token in _FORBIDDEN_TARGET_TOKENS:
        if token in low:
            raise BackupRestoreDrill1Error(
                f"Source path refused ({token}).",
                code="source_refused",
            )
    try:
        resolved.relative_to(BETA_ROOT)
    except ValueError as exc:
        raise BackupRestoreDrill1Error(
            "Source must be under Beta root.",
            code="not_beta",
        ) from exc
    if not resolved.is_file():
        raise BackupRestoreDrill1Error(
            f"Source artifact missing: {resolved}",
            code="source_missing",
        )
    return resolved


def _guard_target_dir(path: Path) -> Path:
    resolved = path.resolve()
    low = str(resolved).lower()
    for token in _FORBIDDEN_TARGET_TOKENS:
        if token in low:
            raise BackupRestoreDrill1Error(
                f"Target path refused ({token}).",
                code="target_refused",
            )
    tmp_root = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp_root)
    except ValueError as exc:
        raise BackupRestoreDrill1Error(
            "Target must be under the system temp directory.",
            code="target_not_temp",
        ) from exc
    # Refuse targeting Beta root, production, or existing populated trees.
    try:
        resolved.relative_to(BETA_ROOT)
        raise BackupRestoreDrill1Error(
            "Target must not be under Beta root.",
            code="target_in_beta",
        )
    except ValueError:
        pass
    return resolved


def ensure_fixture_source() -> Path:
    """Small stamped fixture used when no backup artifact is preferred/available."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / "backup-restore-drill1-fixture-20260930.bin"
    if not path.is_file():
        payload = (
            b"BACKUP-RESTORE-DRILL-1 fixture\n"
            b"pack=BACKUP-RESTORE-DRILL-1\n"
            b"cap=CAP-DR-01\n"
            b"non_destructive=true\n"
            b"created=2026-09-30T07:36:00+08:00\n"
        )
        path.write_bytes(payload)
    return path


def pick_source(*, prefer_fixture: bool = False) -> Path:
    """Pick an existing Beta backup artifact, else the stamped fixture."""
    if prefer_fixture:
        return ensure_fixture_source()
    if BACKUPS_DIR.is_dir():
        candidates = sorted(
            [
                p
                for p in BACKUPS_DIR.glob("content_library*.sqlite*")
                if p.is_file() and p.stat().st_size > 0
            ],
            key=lambda p: (p.stat().st_size, p.name),
        )
        if candidates:
            return candidates[0]
    return ensure_fixture_source()


def load_drill_log(path: Path | str | None = None) -> dict[str, Any] | None:
    log_path = Path(path) if path else DRILL_LOG_PATH
    if not log_path.is_file():
        return None
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_drill_log(payload: dict[str, Any], path: Path | str | None = None) -> Path:
    log_path = Path(path) if path else DRILL_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return log_path


def run_non_destructive_drill(
    *,
    source: Path | str | None = None,
    prefer_fixture: bool = False,
    log_path: Path | str | None = None,
    keep_target: bool = True,
) -> dict[str, Any]:
    """Copy one Beta backup artifact into a new empty temp dir; verify sha256.

    Target is always tempfile.mkdtemp under the system temp directory.
    Never touches Production, NAS, or B2. Never deletes the source.
    """
    recorded_at = _now_wita()
    drill_id = f"{PACK_ID}-{recorded_at[:10].replace('-', '')}"
    src = _guard_source(Path(source) if source else pick_source(prefer_fixture=prefer_fixture))

    target_dir = Path(tempfile.mkdtemp(prefix="backup-restore-drill1-"))
    target_dir = _guard_target_dir(target_dir)
    # Ensure empty (mkdtemp is empty by definition).
    if any(target_dir.iterdir()):
        raise BackupRestoreDrill1Error(
            "Target temp directory was not empty.",
            code="target_not_empty",
        )

    dest = target_dir / src.name
    status = "FAIL"
    reason = None
    source_sha = None
    target_sha = None
    bytes_copied = 0
    sha_match = False

    try:
        source_sha = _sha256_file(src)
        shutil.copy2(src, dest)
        if not dest.is_file():
            raise BackupRestoreDrill1Error(
                "Copy did not create target file.",
                code="copy_failed",
            )
        bytes_copied = dest.stat().st_size
        target_sha = _sha256_file(dest)
        sha_match = source_sha == target_sha and bytes_copied == src.stat().st_size
        if not sha_match:
            reason = "sha256 mismatch source→target"
            status = "FAIL"
        else:
            status = "SUCCESS"
            reason = None
    except BackupRestoreDrill1Error as exc:
        status = "FAIL"
        reason = str(exc)
    except OSError as exc:
        status = "FAIL"
        reason = f"OSError: {exc}"

    # Source must still exist (non-destructive).
    source_still_present = src.is_file()
    if not source_still_present:
        status = "FAIL"
        reason = (reason or "") + " · source deleted — forbidden"
        source_still_present = False

    honesty_status = HONESTY_STATUS if status == "SUCCESS" else "FAIL"
    log: dict[str, Any] = {
        "schema_id": LOG_SCHEMA_ID,
        "pack": PACK_ID,
        "cap": CAP_ID,
        "drill_id": drill_id,
        "recorded_at": recorded_at,
        "status": status,
        "honesty_status": honesty_status,
        "result": status,
        "reason": reason,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "secrets_written": False,
        "source_deleted": not source_still_present,
        "source_still_present": source_still_present,
        "ready_claimed": False,
        "proven_claimed": False,
        "full_dr_ready_claimed": False,
        "proven_scope": "non_destructive_temp_only",
        "ceiling": CEILING,
        "shell_ne_complete": True,
        "classification": "INTERNALLY_SOLVABLE",
        "source_path": str(src),
        "target_path": str(target_dir),
        "target_file": str(dest) if dest.exists() else None,
        "source_sha256": source_sha,
        "target_sha256": target_sha,
        "sha256_match": sha_match,
        "bytes_copied": bytes_copied,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_pid_held": PROD_PID_HELD,
        "framework_not_run_log_preserved": True,
        "historical_counts_as_this_drill": False,
    }
    written = write_drill_log(log, log_path)

    if not keep_target and target_dir.is_dir():
        # Optional cleanup for unit tests; default keeps evidence under /tmp.
        shutil.rmtree(target_dir, ignore_errors=True)
        log["target_cleaned"] = True
    else:
        log["target_cleaned"] = False

    log["log_path"] = str(written)
    # Re-write with log_path / target_cleaned.
    write_drill_log(log, written)
    return log


def last_drill_summary(log: dict[str, Any] | None = None) -> dict[str, Any]:
    """Board-facing summary. Never invents SUCCESS without a real log."""
    row = log if log is not None else load_drill_log()
    if not row:
        return {
            "id": "restore_drill_non_destructive",
            "label": "Non-destructive restore drill",
            "status": "NOT_RUN",
            "honesty_status": "NOT_RUN",
            "last_drill_at": None,
            "target_path": None,
            "source_path": None,
            "production_mutated": False,
            "sha256_match": None,
            "live_restore": False,
            "notes": "No BACKUP-RESTORE-DRILL-1 log yet.",
            "success_invented": False,
            "full_dr_ready_claimed": False,
        }
    status = str(row.get("status") or "UNKNOWN").upper()
    honesty = str(row.get("honesty_status") or "").upper()
    if status == "SUCCESS":
        board_status = HONESTY_STATUS
    elif status == "FAIL":
        board_status = "FAIL"
    else:
        board_status = status
    if not honesty and status == "SUCCESS":
        honesty = HONESTY_STATUS
    return {
        "id": "restore_drill_non_destructive",
        "label": "Non-destructive restore drill",
        "status": board_status,
        "honesty_status": honesty or board_status,
        "drill_status": status,
        "last_drill_at": row.get("recorded_at"),
        "target_path": row.get("target_path"),
        "target_file": row.get("target_file"),
        "source_path": row.get("source_path"),
        "production_mutated": False,
        "live_restore": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "sha256_match": row.get("sha256_match"),
        "source_sha256": row.get("source_sha256"),
        "target_sha256": row.get("target_sha256"),
        "bytes_copied": row.get("bytes_copied"),
        "drill_id": row.get("drill_id"),
        "ceiling": row.get("ceiling") or CEILING,
        "proven_scope": row.get("proven_scope") or "non_destructive_temp_only",
        "full_dr_ready_claimed": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "shell_ne_complete": True,
        "notes": (
            "Approved non-destructive temp-dir drill ran. "
            "sha256 verified. Not full DR READY (NAS/B2 restore still EXTERNAL/HUMAN)."
            if status == "SUCCESS"
            else f"Drill status {status}: {row.get('reason') or 'see log'}"
        ),
        "success_invented": False,
        "pass_invented": False,
        "probe_mode": "non_destructive_temp",
        "log_path": str(DRILL_LOG_PATH),
    }


def _preserved_backup_health() -> dict[str, Any]:
    # Lazy import + honesty_flags only (avoid nested build_board recursion).
    try:
        from core import backup_health1 as _backup_health1  # noqa: PLC0415

        flags = _backup_health1.honesty_flags()
        honest = (
            flags.get("fake_backup_success") is False
            and flags.get("invented_restore_pass") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
        )
        status = "PRESERVED" if honest else "BROKEN"
        notes = (
            "BACKUP-HEALTH-1 honesty flags intact (no fake backup success / restore PASS)."
            if status == "PRESERVED"
            else "BACKUP-HEALTH-1 honesty pin broken — investigate."
        )
    except Exception as exc:  # noqa: BLE001
        status = "UNKNOWN"
        notes = f"Could not load BACKUP-HEALTH-1: {type(exc).__name__}"
        honest = False
    return {
        "id": "backup_health1",
        "label": "BACKUP-HEALTH-1 preserved",
        "status": status,
        "source": "core.backup_health1",
        "honest": bool(honest) if status != "UNKNOWN" else None,
        "notes": notes,
        "probe_mode": "read_only",
        "success_invented": False,
    }


def _preserved_reliability1() -> dict[str, Any]:
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


def _framework_guards_preserved() -> dict[str, Any]:
    """Pin that restore_drill refuse_* still fail-closed for live/prod/nas/b2."""
    checks: dict[str, bool] = {}
    for name, fn, code in (
        ("refuse_live_restore", _restore_drill.refuse_live_restore, "live_restore_refused"),
        ("refuse_production", _restore_drill.refuse_production, "production_refused"),
        ("refuse_nas", _restore_drill.refuse_nas, "nas_destructive_refused"),
        ("refuse_b2", _restore_drill.refuse_b2, "b2_destructive_refused"),
    ):
        try:
            fn({})
            checks[name] = False
        except _restore_drill.RestoreDrillError as exc:
            checks[name] = exc.code == code
        except Exception:  # noqa: BLE001
            checks[name] = False
    ok = all(checks.values())
    # Framework log must still be able to emit NOT_RUN (skeleton preserved).
    try:
        framework = _restore_drill.build_framework()
        framework_ok = (
            framework.get("live_restore") is False
            and framework.get("production_mutated") is False
        )
    except Exception:  # noqa: BLE001
        framework_ok = False
    status = "PRESERVED" if ok and framework_ok else "BROKEN"
    return {
        "id": "restore_drill_guards",
        "label": "restore_drill refuse_* preserved",
        "status": status,
        "source": "core.restore_drill",
        "checks": checks,
        "framework_ok": framework_ok,
        "notes": (
            "Framework refuse_live_restore / refuse_production / refuse_nas / refuse_b2 intact."
            if status == "PRESERVED"
            else "Framework guards broken — investigate."
        ),
        "probe_mode": "read_only",
        "success_invented": False,
    }


def build_board(*, ensure_drill: bool = False, prefer_fixture: bool = False) -> dict[str, Any]:
    """Public board. Optionally run the drill once if no log yet (pack EXIT path)."""
    as_of = _now_wita()
    log = load_drill_log()
    if ensure_drill and (log is None or str(log.get("status") or "").upper() == "NOT_RUN"):
        log = run_non_destructive_drill(prefer_fixture=prefer_fixture)
    summary = last_drill_summary(log)
    stamps = [
        summary,
        {
            "id": "cap_dr_01_scope",
            "label": "CAP-DR-01 scope",
            "status": CEILING if summary.get("status") == HONESTY_STATUS else "BUILT",
            "source": "BACKUP-RESTORE-DRILL-1",
            "notes": (
                "PROVEN for non-destructive temp-dir drill only. "
                "Full DR READY (NAS/B2) remains shell_ne_complete / EXTERNAL_HUMAN if unauthorised."
            ),
            "full_dr_ready_claimed": False,
            "ready_claimed": False,
            "proven_claimed": False,
            "shell_ne_complete": True,
            "success_invented": False,
        },
        _framework_guards_preserved(),
        _preserved_backup_health(),
        _preserved_reliability1(),
    ]
    flags = honesty_flags()
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
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "source_deleted": False,
        "full_dr_ready_claimed": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "proven_scope": "non_destructive_temp_only",
        "ceiling": CEILING,
        "shell_ne_complete": True,
        "classification": "INTERNALLY_SOLVABLE",
        "closes_toward": list(CLOSES_TOWARD),
        "honesty_status": summary.get("honesty_status"),
        "last_drill_at": summary.get("last_drill_at"),
        "status": summary.get("status"),
        "target_path": summary.get("target_path"),
        "source_path": summary.get("source_path"),
        "sha256_match": summary.get("sha256_match"),
        "stamps": stamps,
        "drill": summary,
        "log": log,
        "preserved_packs": list(PRESERVED_PACKS),
        "next_pack_for_parent_only": "PIPE-RELIABILITY-AUTO-1",
        "cursor_did_not_auto_start_next": True,
        "backup_health1_preserved": True,
        "reliability1_preserved": True,
        "restore_drill_guards_preserved": True,
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "no_push",
                "write_authority_expanded",
                "secrets_exposed",
            )
        },
    }


def public_payload() -> dict[str, Any]:
    return build_board(ensure_drill=False)


def drill_is_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when SUCCESS implies real sha256 match + temp target + no prod mutate."""
    pack = payload if payload is not None else build_board()
    if pack.get("production_mutated") is True:
        return False
    if pack.get("full_dr_ready_claimed") is True or pack.get("ready_claimed") is True:
        return False
    if pack.get("live_restore") is True:
        return False
    drill = pack.get("drill") or {}
    status = str(drill.get("status") or pack.get("status") or "").upper()
    if status == HONESTY_STATUS:
        target = str(drill.get("target_path") or "")
        tmp_root = str(Path(tempfile.gettempdir()).resolve())
        target_ok = False
        if target:
            try:
                Path(target).resolve().relative_to(Path(tmp_root))
                target_ok = True
            except (ValueError, OSError):
                # macOS often surfaces /var/... vs /private/var/...
                target_ok = target.startswith(tmp_root) or (
                    "/var/folders/" in target and "backup-restore-drill1-" in target
                )
        return (
            drill.get("sha256_match") is True
            and drill.get("production_mutated") is False
            and bool(drill.get("target_path"))
            and target_ok
        )
    if status in ("FAIL", "NOT_RUN", "UNKNOWN", "MISSING"):
        return pack.get("production_mutated") is False
    # Never treat bare SUCCESS/PASS/READY as honest board status.
    if status in _restore_drill._SUCCESS_STATUS | {"READY", "PROVEN"}:  # noqa: SLF001
        return False
    return False
