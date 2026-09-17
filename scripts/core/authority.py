#!/usr/bin/env python3
"""Wolf Core Authority Limits — deterministic HOW MUCH evaluator (Beta).

Permission = WHAT (core.rbac). Scope = WHERE (core.scope).
Authority Limit = material conditions (amount/currency/threshold).
Authority never creates Permission. No AI/LLM in the decision path.
Delegation / dual approval / SoD / real auth = NOT BUILT.

Conflict rule: among matching active limits, use the STRICTEST
(lowest threshold_value). Assignment-specific matches preferred over
role-level; do not average; do not ask an LLM.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
TZ8 = timezone(timedelta(hours=8))

HONESTY = {
    "real_authentication": "NOT_BUILT",
    "delegation": "NOT_BUILT",
    "dual_approval": "NOT_BUILT",
    "segregation_of_duties": "NOT_BUILT",
    "ai_decision": False,
}


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"authority refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"authority refuses wolf-system path: {resolved}")
    if "/Production" in str(resolved) or str(resolved).endswith("money.sqlite"):
        raise RuntimeError(f"authority refuses production path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _base(person_id: str, permission_code: str, target_context, amount_context) -> dict[str, Any]:
    out: dict[str, Any] = {
        "person_id": person_id,
        "permission_code": permission_code,
        "target_context": target_context or {},
        "amount_context": amount_context or {},
        "allowed": False,
        "reason": "deny_by_default",
        "evaluator": "core.authority.within_authority",
        "matched_limit": None,
        "candidates": [],
        **HONESTY,
    }
    return out


def _parse_at(amount_context: dict[str, Any] | None) -> datetime:
    raw = (amount_context or {}).get("at")
    if not raw:
        return datetime.now(TZ8)
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=TZ8)
    s = str(raw).strip()
    # Support trailing Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return datetime.now(TZ8)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ8)
    return dt


def _effective(limit: dict[str, Any], at: datetime) -> bool:
    try:
        start = datetime.fromisoformat(str(limit["effective_from"]).replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=TZ8)
    except (TypeError, ValueError):
        return False
    if at < start:
        return False
    eto = limit.get("effective_to")
    if eto:
        try:
            end = datetime.fromisoformat(str(eto).replace("Z", "+00:00"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=TZ8)
        except (TypeError, ValueError):
            return False
        if at > end:
            return False
    return True


def _coerce_amount(raw: Any) -> float | None:
    """Return float amount or None if missing/malformed/non-numeric."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def list_authority_limits_for_person(
    person_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Active limits visible via person's active assignments / roles. Minimal fields."""
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT DISTINCT
              al.authority_limit_id,
              al.role_id,
              al.assignment_id,
              al.permission_id,
              p.code AS permission_code,
              al.scope_id,
              al.limit_type,
              al.currency,
              al.threshold_value,
              al.comparison_rule,
              al.effective_from,
              al.effective_to,
              al.status
            FROM org_authority_limits al
            JOIN org_permissions p ON p.permission_id = al.permission_id
            WHERE al.status = 'active'
              AND (
                al.assignment_id IN (
                  SELECT a.assignment_id FROM org_assignments a
                  WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
                )
                OR (
                  al.assignment_id IS NULL
                  AND al.role_id IN (
                    SELECT pos.role_id
                    FROM org_assignments a
                    JOIN org_positions pos ON pos.position_id = a.position_id
                    WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
                  )
                )
              )
            ORDER BY al.threshold_value ASC, al.authority_limit_id
            """,
            (pid, pid),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def within_authority(
    person_id: str,
    permission_code: str,
    target_context: dict[str, Any] | None = None,
    amount_context: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Deterministic authority check. Deny by default. No AI."""
    from core import rbac as _rbac

    explanation = _base(person_id, permission_code, target_context, amount_context)
    pid = (person_id or "").strip()
    code_in = (permission_code or "").strip()
    if not pid or not code_in:
        explanation["reason"] = "missing_person_or_permission"
        return explanation

    own = conn is None
    c = conn or db_connect()
    try:
        # 1. RBAC WHAT + WHERE
        rbac_ev = _rbac.evaluate(pid, code_in, target_context, conn=c)
        explanation["rbac"] = {
            "allowed": rbac_ev.get("allowed"),
            "reason": rbac_ev.get("reason"),
            "permission_code": rbac_ev.get("permission_code"),
            "matched": rbac_ev.get("matched"),
        }
        if not rbac_ev.get("allowed"):
            explanation["reason"] = "rbac_denied"
            explanation["rbac_reason"] = rbac_ev.get("reason")
            return explanation

        code = rbac_ev.get("permission_code") or code_in
        explanation["permission_code"] = code
        perm_id = rbac_ev.get("permission_id") or (rbac_ev.get("matched") or {}).get("permission_id")
        if not perm_id:
            perm = _rbac.get_permission_by_code(code, conn=c)
            perm_id = perm["permission_id"] if perm else None
        if not perm_id:
            explanation["reason"] = "rbac_denied"
            explanation["rbac_reason"] = "unknown_permission"
            return explanation
        explanation["permission_id"] = perm_id

        # 2. Active Assignment
        asgs = c.execute(
            """
            SELECT a.assignment_id, a.person_id, a.position_id, a.status, a.end_at,
                   p.role_id
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE a.person_id=?
              AND a.status='ACTIVE'
              AND a.end_at IS NULL
            """,
            (pid,),
        ).fetchall()
        if not asgs:
            explanation["reason"] = "no_active_assignment"
            return explanation

        target = target_context or {}
        at = _parse_at(amount_context)

        # 3. Valid Scope covering target (reuse rbac._scope_covers_target)
        covering: list[dict[str, Any]] = []
        for asg in asgs:
            scopes = c.execute(
                """
                SELECT scope_id FROM org_assignment_scopes
                WHERE assignment_id=?
                  AND status='ACTIVE'
                  AND end_at IS NULL
                """,
                (asg["assignment_id"],),
            ).fetchall()
            for srow in scopes:
                sid = srow["scope_id"]
                if _rbac._scope_covers_target(sid, target, c):
                    covering.append(
                        {
                            "assignment_id": asg["assignment_id"],
                            "role_id": asg["role_id"],
                            "scope_id": sid,
                        }
                    )

        if not covering:
            explanation["reason"] = "scope_denied"
            return explanation

        # 4. Matching active Authority Limits (assignment first, then role)
        asg_ids = {x["assignment_id"] for x in covering}
        role_ids = {x["role_id"] for x in covering}
        covering_scope_ids = {x["scope_id"] for x in covering}

        params: list[Any] = [perm_id]
        clauses: list[str] = []
        if asg_ids:
            clauses.append(
                f"assignment_id IN ({','.join('?' * len(asg_ids))})"
            )
            params.extend(sorted(asg_ids))
        if role_ids:
            clauses.append(
                f"(assignment_id IS NULL AND role_id IN ({','.join('?' * len(role_ids))}))"
            )
            params.extend(sorted(role_ids))
        if not clauses:
            explanation["reason"] = "higher_approval_required"
            explanation["detail"] = "no_matching_authority_limit"
            return explanation

        limit_rows = c.execute(
            f"""
            SELECT *
            FROM org_authority_limits
            WHERE permission_id=?
              AND status='active'
              AND limit_type='AMOUNT'
              AND comparison_rule='LTE_INCLUSIVE'
              AND ({' OR '.join(clauses)})
            """,
            params,
        ).fetchall()

        assignment_matches: list[dict[str, Any]] = []
        role_matches: list[dict[str, Any]] = []
        seen_but_expired = False

        for row in limit_rows:
            lim = dict(row)
            # scope_id NULL = applies to any scope already validated in step 3
            sid = lim.get("scope_id")
            if sid is not None and sid not in covering_scope_ids:
                continue
            if not _effective(lim, at):
                seen_but_expired = True
                explanation["candidates"].append(
                    {
                        "authority_limit_id": lim["authority_limit_id"],
                        "skipped": "not_effective_at",
                        "effective_from": lim.get("effective_from"),
                        "effective_to": lim.get("effective_to"),
                    }
                )
                continue
            if lim.get("assignment_id"):
                if lim["assignment_id"] not in asg_ids:
                    continue
                assignment_matches.append(lim)
            else:
                if lim.get("role_id") not in role_ids:
                    continue
                role_matches.append(lim)

        matches = assignment_matches if assignment_matches else role_matches
        if not matches:
            if seen_but_expired:
                explanation["reason"] = "authority_expired"
            else:
                explanation["reason"] = "higher_approval_required"
                explanation["detail"] = "no_matching_authority_limit"
            return explanation

        # Strictest = lowest threshold_value
        matches.sort(key=lambda m: (m["threshold_value"], m["authority_limit_id"]))
        chosen = matches[0]
        explanation["candidates"] = [
            {
                "authority_limit_id": m["authority_limit_id"],
                "threshold_value": m["threshold_value"],
                "currency": m.get("currency"),
                "assignment_id": m.get("assignment_id"),
                "role_id": m.get("role_id"),
            }
            for m in matches
        ]
        explanation["matched_limit"] = {
            "authority_limit_id": chosen["authority_limit_id"],
            "threshold_value": chosen["threshold_value"],
            "currency": chosen.get("currency"),
            "assignment_id": chosen.get("assignment_id"),
            "role_id": chosen.get("role_id"),
            "scope_id": chosen.get("scope_id"),
            "comparison_rule": chosen.get("comparison_rule"),
            "conflict_resolution": "strictest_lowest_threshold",
        }

        # 5. Material conditions
        amt_ctx = amount_context or {}
        amount = _coerce_amount(amt_ctx.get("amount"))
        currency = amt_ctx.get("currency")
        if currency is not None:
            currency = str(currency).strip() or None

        if "amount" not in amt_ctx or amt_ctx.get("amount") is None:
            # missing when AMOUNT limit
            explanation["reason"] = "missing_amount"
            return explanation
        if amount is None:
            explanation["reason"] = "malformed_amount"
            return explanation
        if amount < 0:
            explanation["reason"] = "negative_amount"
            return explanation
        lim_cur = (chosen.get("currency") or "").strip()
        if not currency or currency != lim_cur:
            explanation["reason"] = "currency_mismatch"
            return explanation

        # 6. LTE_INCLUSIVE threshold
        threshold = float(chosen["threshold_value"])
        explanation["amount"] = amount
        explanation["threshold_value"] = threshold
        if amount <= threshold:
            explanation["allowed"] = True
            explanation["reason"] = "within_authority"
            return explanation

        explanation["reason"] = "higher_approval_required"
        return explanation
    finally:
        if own:
            c.close()


def within_authority_bool(
    person_id: str,
    permission_code: str,
    target_context: dict[str, Any] | None = None,
    amount_context: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> bool:
    return bool(
        within_authority(
            person_id, permission_code, target_context, amount_context, conn=conn
        ).get("allowed")
    )
