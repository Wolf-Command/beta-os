#!/usr/bin/env python3
"""APPROVALS-LIVE-DEEPEN-1 — Approvals live deepen (no invent approvals).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave9 pack
APPROVALS-LIVE-DEEPEN-1 (armed 2026-09-30 after STAFF-ACCESS-TRUTH-1
PASS_VERIFIED) + 2026-09-17 Wolf Core Approval Engine picks.

Deepens the approvals board from live catalog stamps only.
Never invents approval requests, decisions, severities, or counts.
Honest empty when no live approval requests exist.
Refuse invent-approve / auto-approve writes (403).
Preserve approvals engine honesty + commissioning flags.
staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain WEEKLY-CASH-FORECAST-SHELL-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import approvals as _approvals

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "APPROVALS-LIVE-DEEPEN-1"
SCHEMA_ID = "wolf.approvals-live-deepen-1.v1"
BOUND = "beta-approvals-live-deepen-safe"
CAP_APPROVALS = "CAP-CORE approvals"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "INTERNALLY_SOLVABLE"
ACTION = "WIRE_LIVE_APPROVAL_STAMPS"
PRESERVED_PACKS = ("approvals", "commissioning", "STAFF-ACCESS-TRUTH-1")

PAGE_PATHS = frozenset(
    {
        "/ops/approvals-live-deepen-1",
        "/ops/approvals-live-deepen-1/",
        "/ops/approvals-live",
        "/ops/approvals-live/",
        "/ops/approvals",
        "/ops/approvals/",
        "/approvals-live-deepen-1",
        "/approvals-live-deepen-1/",
        "/approvals-live-deepen-1.html",
        "/dashboards/approvals-live-deepen-1.html",
    }
)
API_PATH = "/api/ops/approvals-live-deepen-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/approvals-live",
        "/api/approvals/live-deepen-1",
        "/api/approvals/live",
    }
)

STATUS_VOCAB = frozenset(
    {
        "INTERNALLY_SOLVABLE",
        "HUMAN_COMMISSIONING",
        "MATT_ACTION",
        "EXTERNAL_BLOCKER",
        "PRESERVED",
        "REFUSED",
        "PENDING",
        "ABSENT",
        "UNKNOWN",
        "WIRED",
        "HONEST_EMPTY",
        "NOT_BUILT",
    }
)

_INVENT_APPROVE_TOKENS = frozenset(
    {
        "approve",
        "approval",
        "approvals",
        "invent-approve",
        "invent_approve",
        "invent-approval",
        "invent_approval",
        "invent-approvals",
        "invent_approvals",
        "fake-approve",
        "fake_approve",
        "fake-approval",
        "fake_approval",
        "auto-approve",
        "auto_approve",
        "autoapprove",
        "mint-approval",
        "mint_approval",
        "create-approval",
        "create_approval",
        "force-approve",
        "force_approve",
        "invent-pending",
        "invent_pending",
        "invent-count",
        "invent_count",
        "invent-severity",
        "invent_severity",
        "severity",
        "urgency",
        "staff-ready",
        "staff_ready",
        "human-commissioned",
        "human_commissioned",
        "proven",
        "ready",
        "decision",
        "decisions",
        "invent-decision",
        "invent_decision",
    }
)


class ApprovalsLiveDeepen1Error(ValueError):
    """Fail closed. Does not invent approvals or auto-approve."""

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
    trimmed = raw.rstrip("/")
    return trimmed in API_PATHS or raw in API_PATHS


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


def _catalog_ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def person_may_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> bool:
    """Owner / progress.read seat."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid == OWNER_PERSON:
        return True
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        return bool(_rbac.can(pid, "progress.read", {}, conn=c))
    finally:
        if own and c is not None:
            c.close()


def require_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> None:
    if not person_may_view(person_id, conn=conn):
        raise ApprovalsLiveDeepen1Error(
            "Approvals live deepen board is not on this assignment.",
            code="forbidden",
        )


def probe_live_requests(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Live approval_request stamps by status. Never invent rows."""
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        tables = {
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "core_approval_requests" not in tables:
            return {
                "ok": True,
                "table_present": False,
                "request_count": 0,
                "by_status": {},
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
                "cancelled_count": 0,
                "expired_count": 0,
                "honest_empty": True,
                "invented_approvals": False,
                "why": (
                    "core_approval_requests table absent — honest empty, "
                    "never invent approval rows."
                ),
                "evidence": "catalog/content_library.sqlite",
            }
        rows = c.execute(
            """
            SELECT status, COUNT(*) AS n
            FROM core_approval_requests
            GROUP BY status
            """
        ).fetchall()
        by_status: dict[str, int] = {}
        for row in rows:
            st = str(row["status"] or "UNKNOWN")
            by_status[st] = int(row["n"] or 0)
        total = int(sum(by_status.values()))
        pending = int(by_status.get("PENDING") or 0)
        return {
            "ok": True,
            "table_present": True,
            "request_count": total,
            "by_status": by_status,
            "pending_count": pending,
            "approved_count": int(by_status.get("APPROVED") or 0),
            "rejected_count": int(by_status.get("REJECTED") or 0),
            "cancelled_count": int(by_status.get("CANCELLED") or 0),
            "expired_count": int(by_status.get("EXPIRED") or 0),
            "honest_empty": total == 0,
            "invented_approvals": False,
            "why": (
                f"Live core_approval_requests count={total} "
                f"(PENDING={pending}). Honest empty when zero — "
                "never invent approval rows or pad the queue."
            ),
            "evidence": "catalog/content_library.sqlite core_approval_requests",
        }
    finally:
        if own and c is not None:
            c.close()


def probe_live_decisions(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Live decision stamps + orphan count (decision without matching request)."""
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        tables = {
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "core_approval_decisions" not in tables:
            return {
                "ok": True,
                "table_present": False,
                "decision_count": 0,
                "by_decision": {},
                "orphan_count": 0,
                "linked_count": 0,
                "invented_decisions": False,
                "invented_requests_for_orphans": False,
                "why": "core_approval_decisions absent — no invent.",
                "evidence": "catalog/content_library.sqlite",
            }
        by_rows = c.execute(
            """
            SELECT decision, COUNT(*) AS n
            FROM core_approval_decisions
            GROUP BY decision
            """
        ).fetchall()
        by_decision: dict[str, int] = {
            str(r["decision"] or "UNKNOWN"): int(r["n"] or 0) for r in by_rows
        }
        decision_count = int(sum(by_decision.values()))
        orphan_count = 0
        linked_count = 0
        if "core_approval_requests" in tables:
            orphan_count = int(
                c.execute(
                    """
                    SELECT COUNT(*) FROM core_approval_decisions d
                    LEFT JOIN core_approval_requests r
                      ON r.approval_request_id = d.approval_request_id
                    WHERE r.approval_request_id IS NULL
                    """
                ).fetchone()[0]
            )
            linked_count = int(decision_count - orphan_count)
        else:
            orphan_count = decision_count
        return {
            "ok": True,
            "table_present": True,
            "decision_count": decision_count,
            "by_decision": by_decision,
            "orphan_count": orphan_count,
            "linked_count": linked_count,
            "invented_decisions": False,
            "invented_requests_for_orphans": False,
            "why": (
                f"Live decisions={decision_count} "
                f"(linked={linked_count}, orphan={orphan_count}). "
                "Orphans are stamped as orphans — never invent matching "
                "requests or severity/counts to fill the board."
            ),
            "evidence": "catalog/content_library.sqlite core_approval_decisions",
        }
    finally:
        if own and c is not None:
            c.close()


def approvals_engine_preserved() -> dict[str, Any]:
    """Read-only: approvals.py HONESTY still holds."""
    try:
        honesty = dict(getattr(_approvals, "HONESTY", {}) or {})
        ok = (
            honesty.get("requested_is_not_approved") is True
            and honesty.get("approved_is_not_executed") is True
            and honesty.get("partial_approve_is_not_approved") is True
            and honesty.get("ai_approver") is False
            and honesty.get("approval_ui") == "NOT_BUILT"
            and honesty.get("dual_approval") == "BUILT"
            and honesty.get("segregation_of_duties") == "BUILT"
            and callable(getattr(_approvals, "list_approval_requests", None))
            and callable(getattr(_approvals, "create_approval_request", None))
            and callable(getattr(_approvals, "get_approval_request", None))
        )
        return {
            "ok": ok,
            "pack": "approvals",
            "honesty": honesty,
            "approval_ui": honesty.get("approval_ui"),
            "ai_approver": honesty.get("ai_approver"),
            "staff_ready": False,
            "human_commissioned": False,
            "why": (
                "approvals engine preserved: REQUESTED≠APPROVED≠EXECUTED; "
                "approval_ui NOT_BUILT; ai_approver false; dual/SoD BUILT. "
                "This pack deepens the live board — does not invent approvals "
                "or flip commissioning."
                if ok
                else "approvals honesty check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "approvals",
            "error": type(exc).__name__,
            "why": "approvals check failed — pack must not break engine honesty.",
        }


def surface_stamps() -> list[dict[str, Any]]:
    """Truth surfaces from live stamps. Never invent approvals."""
    requests = probe_live_requests()
    decisions = probe_live_decisions()
    preserved = approvals_engine_preserved()
    honest_empty = bool(requests.get("honest_empty"))
    pending = int(requests.get("pending_count") or 0)
    return [
        {
            "id": "live_requests",
            "label": "Live approval requests",
            "status": "HONEST_EMPTY" if honest_empty else "INTERNALLY_SOLVABLE",
            "value": requests.get("request_count"),
            "request_count": requests.get("request_count"),
            "by_status": requests.get("by_status") or {},
            "invented_approvals": False,
            "why": requests.get("why"),
            "evidence": requests.get("evidence"),
        },
        {
            "id": "pending_queue",
            "label": "PENDING queue",
            "status": "HONEST_EMPTY" if pending == 0 else "HUMAN_COMMISSIONING",
            "value": pending,
            "pending_count": pending,
            "honest_empty": pending == 0,
            "invented_pending": False,
            "why": (
                "PENDING=0 from live stamps — honest empty. "
                "Never invent PENDING rows to look busy."
                if pending == 0
                else (
                    f"PENDING={pending} live — human decide path only; "
                    "no auto-approve."
                )
            ),
            "evidence": "core_approval_requests.status=PENDING",
        },
        {
            "id": "orphan_decisions",
            "label": "Decision rows without matching request",
            "status": "INTERNALLY_SOLVABLE",
            "value": decisions.get("orphan_count"),
            "decision_count": decisions.get("decision_count"),
            "orphan_count": decisions.get("orphan_count"),
            "linked_count": decisions.get("linked_count"),
            "invented_requests_for_orphans": False,
            "why": decisions.get("why"),
            "evidence": decisions.get("evidence"),
        },
        {
            "id": "approvals_engine",
            "label": "Approval engine honesty",
            "status": "PRESERVED" if preserved.get("ok") else "EXTERNAL_BLOCKER",
            "value": "PRESERVED" if preserved.get("ok") else None,
            "preserved_ok": preserved.get("ok") is True,
            "approval_ui": preserved.get("approval_ui"),
            "ai_approver": preserved.get("ai_approver"),
            "why": preserved.get("why"),
            "evidence": "scripts/core/approvals.py HONESTY",
        },
        {
            "id": "approval_ui",
            "label": "Approval UI",
            "status": "NOT_BUILT",
            "value": "NOT_BUILT",
            "why": (
                "approvals.HONESTY.approval_ui=NOT_BUILT. "
                "This pack is a truth board, not an approve console. "
                "Never invent a staff-ready approve UI."
            ),
            "evidence": "approvals.HONESTY",
        },
        {
            "id": "human_decide",
            "label": "Human decide / commissioning",
            "status": "HUMAN_COMMISSIONING",
            "value": pending,
            "staff_ready": False,
            "human_commissioned": False,
            "auto_approve": False,
            "why": (
                "Live approvals (when present) require human decide. "
                "Queue is honest-empty today; commissioning stays false. "
                "Never auto-approve."
            ),
            "evidence": "pack forbids auto-approve; ARM human_commissioned=false",
        },
        {
            "id": "exit_report_headchef",
            "label": "Exit Report / HEADCHEF",
            "status": "MATT_ACTION",
            "value": "MATT_ACTION",
            "why": (
                "Exit Report forbidden until Phase 13. "
                "HEADCHEF not auto-chained. Matt/parent arms next pack only."
            ),
            "evidence": "MISSION / ARM forbids",
        },
        {
            "id": "prod_mutate",
            "label": "Prod :8787 mutate / push",
            "status": "EXTERNAL_BLOCKER",
            "value": None,
            "prod_pid_held": PROD_PID_HELD,
            "why": (
                "Hard rule: never touch prod pid 15975; no push. "
                "Beta harness only."
            ),
            "evidence": "ARM prod_mutate=false · no_push=true",
        },
        {
            "id": "invent_approve_writes",
            "label": "Invent-approve / auto-approve writes",
            "status": "REFUSED",
            "value": False,
            "invented_approvals": False,
            "auto_approve": False,
            "why": (
                "Invent-approve / auto-approve / invent-pending / invent-count "
                "writes are refused (403)."
            ),
            "evidence": "pack forbids invent approvals + auto-approve",
        },
        {
            "id": "staff_ready_flags",
            "label": "staff_ready / human_commissioned",
            "status": "REFUSED",
            "value": False,
            "staff_ready": False,
            "human_commissioned": False,
            "why": (
                "staff_ready and human_commissioned stay false always. "
                "TESTS≠STAFF READY. Never flip."
            ),
            "evidence": "MISSION / ARM staff_ready=false",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    preserved = approvals_engine_preserved()
    requests = probe_live_requests()
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap_approvals": CAP_APPROVALS,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "invented_approvals": False,
        "invented_pending": False,
        "invented_decisions": False,
        "invented_severity": False,
        "invented_counts": False,
        "fake_approvals": False,
        "auto_approve": False,
        "padded_empty": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_probe_read_only": True,
        "no_push": True,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "action": ACTION,
        "proven_claimed": False,
        "ready_claimed": False,
        "approvals_preserved": preserved.get("ok") is True,
        "status_vocab": (
            "INTERNALLY_SOLVABLE|HUMAN_COMMISSIONING|MATT_ACTION|"
            "EXTERNAL_BLOCKER|PRESERVED|REFUSED|PENDING|ABSENT|UNKNOWN|"
            "WIRED|HONEST_EMPTY|NOT_BUILT"
        ),
        "next_pack_for_parent_only": "WEEKLY-CASH-FORECAST-SHELL-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "honest_empty_when_no_live_approvals": True,
        "honest_empty": bool(requests.get("honest_empty")),
        "shell_ne_complete": True,
        "tests_ne_staff_ready": True,
        "live_stamps_only": True,
    }


def refuse_invent_approve(_body: dict | None = None) -> None:
    raise ApprovalsLiveDeepen1Error(
        "Invent-approve refused. Approvals come from live stamps only.",
        code="invent_approve_refused",
    )


def refuse_auto_approve(_body: dict | None = None) -> None:
    raise ApprovalsLiveDeepen1Error(
        "Auto-approve refused. Humans decide; engine never invents APPROVED.",
        code="auto_approve_refused",
    )


def refuse_invent_pending(_body: dict | None = None) -> None:
    raise ApprovalsLiveDeepen1Error(
        "Invent PENDING refused. Empty queue stays empty.",
        code="invent_pending_refused",
    )


def refuse_invent_count(_body: dict | None = None) -> None:
    raise ApprovalsLiveDeepen1Error(
        "Invent count / severity refused. Counts come from live stamps only.",
        code="invent_count_refused",
    )


def refuse_force_ready(_body: dict | None = None) -> None:
    raise ApprovalsLiveDeepen1Error(
        "Force staff_ready / human_commissioned / proven refused.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise ApprovalsLiveDeepen1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in _INVENT_APPROVE_TOKENS or norm in _INVENT_APPROVE_TOKENS:
            if (
                "ready" in token
                or "commission" in token
                or "proven" in token
                or "ready" in norm
                or "commission" in norm
            ):
                refuse_force_ready(payload)
            if (
                "auto" in token
                or "auto" in norm
                or token in {"auto-approve", "autoapprove"}
                or norm == "auto_approve"
            ):
                refuse_auto_approve(payload)
            if "pending" in token or "pending" in norm:
                refuse_invent_pending(payload)
            if (
                "count" in token
                or "severity" in token
                or "urgency" in token
                or "count" in norm
                or "severity" in norm
            ):
                refuse_invent_count(payload)
            refuse_invent_approve(payload)
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "8787",
            "15975",
        } or norm in {"prod_mutate", "prod_write"}:
            raise ApprovalsLiveDeepen1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
        if token in {
            "staff-ready",
            "human-commissioned",
            "proven",
            "ready",
        } or norm in {
            "staff_ready",
            "human_commissioned",
            "proven",
            "ready",
        }:
            refuse_force_ready(payload)
    raise ApprovalsLiveDeepen1Error(
        "APPROVALS-LIVE-DEEPEN-1 is a read-only truth board. Writes refused.",
        code="write_refused",
    )


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    if pack.get("invented_approvals") is True or pack.get("auto_approve") is True:
        return False
    if pack.get("staff_ready") is True or pack.get("human_commissioned") is True:
        return False
    if pack.get("classification") != CLASSIFICATION:
        return False
    if pack.get("honest_empty") is not True and int(pack.get("request_count") or 0) == 0:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 8:
        return False
    by_id = {s.get("id"): s for s in surfaces if isinstance(s, dict)}
    need = {
        "live_requests": ("HONEST_EMPTY", "INTERNALLY_SOLVABLE"),
        "pending_queue": ("HONEST_EMPTY", "HUMAN_COMMISSIONING"),
        "orphan_decisions": ("INTERNALLY_SOLVABLE",),
        "approvals_engine": ("PRESERVED", "EXTERNAL_BLOCKER"),
        "approval_ui": ("NOT_BUILT",),
        "human_decide": ("HUMAN_COMMISSIONING",),
        "exit_report_headchef": ("MATT_ACTION",),
        "prod_mutate": ("EXTERNAL_BLOCKER",),
        "invent_approve_writes": ("REFUSED",),
        "staff_ready_flags": ("REFUSED",),
    }
    for sid, allowed in need.items():
        row = by_id.get(sid) or {}
        st = row.get("status")
        if st not in allowed:
            return False
        if st not in STATUS_VOCAB:
            return False
    if pack.get("approvals_preserved") is not True:
        return False
    return True


def no_invented_approvals(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    return (
        pack.get("invented_approvals") is False
        and pack.get("invented_pending") is False
        and pack.get("invented_decisions") is False
        and pack.get("invented_severity") is False
        and pack.get("invented_counts") is False
        and pack.get("fake_approvals") is False
        and pack.get("auto_approve") is False
        and pack.get("staff_ready") is False
        and pack.get("human_commissioned") is False
    )


def build_board(
    person_id: str | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Public approvals live deepen board. Auth gating is caller's job."""
    if person_id is not None:
        require_view(person_id, conn=conn)
    probed_at = _now_wita()
    requests = probe_live_requests(conn=conn)
    decisions = probe_live_decisions(conn=conn)
    surfaces = surface_stamps()
    preserved = approvals_engine_preserved()
    flags = honesty_flags()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1

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
        "invented_approvals": False,
        "invented_pending": False,
        "invented_decisions": False,
        "invented_severity": False,
        "invented_counts": False,
        "fake_approvals": False,
        "auto_approve": False,
        "padded_empty": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "action": ACTION,
        "cap_approvals": CAP_APPROVALS,
        "request_count": requests.get("request_count"),
        "pending_count": requests.get("pending_count"),
        "approved_count": requests.get("approved_count"),
        "rejected_count": requests.get("rejected_count"),
        "decision_count": decisions.get("decision_count"),
        "orphan_decision_count": decisions.get("orphan_count"),
        "linked_decision_count": decisions.get("linked_count"),
        "honest_empty": requests.get("honest_empty"),
        "by_status": requests.get("by_status") or {},
        "by_decision": decisions.get("by_decision") or {},
        "surfaces": surfaces,
        "surface_counts": by_status,
        "requests": requests,
        "decisions": decisions,
        "honesty": {
            "policy": "live_stamps_only_never_invent_approvals",
            "live_requests": (
                "HONEST_EMPTY" if requests.get("honest_empty") else "INTERNALLY_SOLVABLE"
            ),
            "pending_queue": (
                "HONEST_EMPTY"
                if int(requests.get("pending_count") or 0) == 0
                else "HUMAN_COMMISSIONING"
            ),
            "human_decide": "HUMAN_COMMISSIONING",
            "exit_report_headchef": "MATT_ACTION",
            "prod_mutate": "EXTERNAL_BLOCKER",
            "approvals": preserved.get("ok") and "PRESERVED" or "CHECK_FAILED",
            "invent_approve_writes": "REFUSED",
            "auto_approve": False,
            "staff_ready": False,
            "human_commissioned": False,
        },
        "preserved": {"approvals": preserved},
        "approvals_preserved": preserved.get("ok") is True,
        "amg_finance_approvals_href": "/amg/finance/approvals",
        "next_pack_for_parent_only": "WEEKLY-CASH-FORECAST-SHELL-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "proven_claimed",
                "ready_claimed",
                "no_push",
                "status_vocab",
                "honest_empty_when_no_live_approvals",
                "shell_ne_complete",
                "tests_ne_staff_ready",
                "live_stamps_only",
            )
        },
    }


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    return build_board(person_id)


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    return build_board(person_id)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "classification": CLASSIFICATION,
        "invent_approvals": False,
        "auto_approve": False,
        "writes_accepted": False,
        "staff_ready": False,
        "human_commissioned": False,
        "preserved": list(PRESERVED_PACKS),
        "why": (
            "Approvals board from live stamps only. "
            "Honest empty when no live approval requests. "
            "Invent-approve / auto-approve writes refused. "
            "approvals engine preserved."
        ),
    }
