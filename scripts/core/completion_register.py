#!/usr/bin/env python3
"""Wolf Completion Register — Owner index of incomplete work (Beta only).

Mandate: docs/deliveries/GROK-PLAN-COMPLETION-REGISTER-2026-09-19.md
Slice: BF-completion-register-20260919

Register rows are the Owner-facing index. Work Items stay the task primitive.
No DELETE. OPEN closes only through mark_resolved with resolution_evidence.
Maturity words alone are not proof. Does not invent policy, float, authority,
or NEEDS_MATT. Counts are computed by summary_for_owner at read time.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
MODEL_C_LEDGER = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
MODEL_E_AUS = BETA_ROOT / "state" / "model-e-au-discovery.json"
MODEL_C_CATALOG = BETA_ROOT / "docs" / "MODEL-C-CAPABILITY-CATALOG.md"
FACTORY_MISSIONS = BETA_ROOT / "state" / "build-factory" / "missions"
FACTORY_RUNS = BETA_ROOT / "state" / "build-factory" / "runs"
CLAIMS_DIR = BETA_ROOT / "state" / "build-claims"
CUTOVER_PATH = BETA_ROOT / "state" / "uma" / "cutover.json"
REVIEW_DIR = BETA_ROOT / "docs" / "deliveries"
ENDED_SCOPE_REVIEW = (
    REVIEW_DIR / "GROK-REVIEW-DEVI-UMA-COMMISSION-AUTH-275d1c7-2026-09-19.md"
)

TZ8 = timezone(timedelta(hours=8))

STATES = frozenset(
    {
        "OPEN",
        "IN_PROGRESS",
        "BLOCKED",
        "WAITING_HUMAN",
        "WAITING_EXTERNAL",
        "VERIFYING",
        "RESOLVED",
    }
)
UNRESOLVED = frozenset(STATES - {"RESOLVED"})
BLOCKER_CLASSES = frozenset(
    {
        "NEEDS_MATT",
        "NEEDS_STAFF",
        "NEEDS_POLICY",
        "NEEDS_EXTERNAL_ACCESS",
        "NEEDS_ENGINEERING",
        "NEEDS_EVIDENCE",
        "NEEDS_COMMISSIONING",
        "NEEDS_ADOPTION",
    }
)
# Owner "material" list excludes the engineering dump.
MATERIAL_EXCLUDED = frozenset({"NEEDS_ENGINEERING"})
DEBT_MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT"})
MATURITY_WORDS = frozenset(
    {"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY", "NOT STARTED", "COMMISSIONING", "ADOPTED"}
)
HUMAN_DONE = frozenset(
    {"DONE", "HUMAN_COMMISSIONED", "PASS", "COMMISSIONED", "COMPLETE", "COMPLETED"}
)
LANE_OPEN = frozenset(
    {"BLOCKED", "ESCALATED", "PARKED", "FAILED", "FAILING", "WAKE", "ABORTED", "ABORT"}
)

VIEW_BY_PREFIX = {
    "D-CORE": "Core",
    "D-GGV": "GGV",
    "D-AMG": "AMG",
    "D-BZG": "BZG",
    "D-HR": "Core",
    "D-FIN": "Core",
    "D-PROC": "Core",
    "D-CRM": "Core",
    "D-MSC": "Core",
    "D-STRAT": "Core",
    "D-INTEL": "Intelligence",
    "D-INTG": "Integrations",
    "D-DR": "Core",
    "D-SALE": "Sale Readiness",
}

SUMMARY_KEYS = (
    "total_open",
    "in_progress",
    "blocked",
    "needs_matt",
    "needs_staff",
    "needs_policy",
    "needs_external",
    "commissioning_adoption_debt",
    "oldest_material",
    "recently_resolved",
)

OLDEST_LIMIT = 8
RESOLVED_LIMIT = 5
REVIEW_SCAN_N = 6

_PROOF_HINT = re.compile(
    r"(/|\\|\.py\b|\.md\b|\.json\b|PASS=|[0-9a-f]{7,})",
    re.IGNORECASE,
)


class CompletionRegisterError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_db_path(resolved: Path) -> None:
    s = str(resolved)
    if "wolf-system" in s:
        raise CompletionRegisterError(
            f"completion register refuses wolf-system path: {resolved}",
            code="refused_path",
        )
    if "/Production" in s or s.endswith("money.sqlite") or ":8787" in s:
        raise CompletionRegisterError(
            f"completion register refuses production path: {resolved}",
            code="refused_path",
        )
    in_beta = "beta-os" in s
    test_ok = _under_test_process()
    if not in_beta and not test_ok:
        raise CompletionRegisterError(
            f"completion register refuses non-beta DB: {resolved}",
            code="refused_path",
        )


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BETA_ROOT))
    except ValueError:
        return str(path)


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def dedup_key(
    *,
    capability: str | None,
    item_type: str | None,
    title: str | None,
    entity: str | None,
) -> str:
    cap = _norm(capability)
    ent = _norm(entity)
    if cap:
        return f"cap:{cap}|ent:{ent}"
    return f"type:{_norm(item_type)}|title:{_norm(title)}|ent:{ent}"


def _item_id(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"CR-{digest}"


def _view_key_from_token(token: str | None) -> str:
    raw = (token or "").strip().upper()
    for prefix, view in VIEW_BY_PREFIX.items():
        if raw.startswith(prefix) or f"{prefix} " in raw or raw.startswith(prefix + "—"):
            return view
    head = raw.split("—")[0].strip()
    if head in VIEW_BY_PREFIX:
        return VIEW_BY_PREFIX[head]
    return "Core"


def load_catalog_caps(catalog_path: Path | None = None) -> dict[str, dict[str, str]]:
    """CAP-ID → name, scope, domain label, view_key. Missing file → empty."""
    path = catalog_path or MODEL_C_CATALOG
    if not path.is_file():
        return {}
    domain = ""
    view_key = "Core"
    out: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### (D-[A-Z]+) — (.+?) \(\d+\)\s*$", line)
        if m:
            domain = f"{m.group(1)} — {m.group(2).strip()}"
            view_key = VIEW_BY_PREFIX.get(m.group(1), "Core")
            continue
        m = re.match(
            r"^\| (CAP-[A-Z0-9]+-\d+) \| ([^|]+) \| [^|]+ \| ([^|]+) \|",
            line,
        )
        if m and domain:
            out[m.group(1)] = {
                "name": m.group(2).strip(),
                "scope": m.group(3).strip(),
                "domain": domain,
                "view_key": view_key,
            }
    return out


def db_connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    _assert_db_path(resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def _db_file(conn: sqlite3.Connection) -> Path:
    for _seq, name, file_path in conn.execute("PRAGMA database_list"):
        if name == "main" and file_path:
            return Path(file_path).resolve()
    return Path()


def _refuse_live_mutation(conn: sqlite3.Connection) -> None:
    """Tests may read the live register. They may not harvest or resolve it."""
    if not _under_test_process():
        return
    if (os.environ.get("WOLF_ALLOW_LIVE_COMPLETION_REGISTER") or "").strip() == "1":
        return
    if _db_file(conn) == CATALOG_DB.resolve():
        raise CompletionRegisterError(
            "test mode refuses mutations on the live catalog; pass a temp db_path",
            code="live_guard",
        )


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS wolf_completion_items (
          id TEXT PRIMARY KEY,
          dedup_key TEXT NOT NULL UNIQUE,
          domain TEXT,
          capability TEXT,
          entity TEXT,
          item_type TEXT,
          title TEXT,
          why_it_matters TEXT,
          state TEXT NOT NULL,
          blocker_class TEXT,
          owner_role TEXT,
          dependency TEXT,
          evidence TEXT,
          source TEXT,
          first_seen TEXT NOT NULL,
          last_checked TEXT NOT NULL,
          next_action TEXT,
          resolution_evidence TEXT,
          resolved_at TEXT,
          work_item_id TEXT,
          view_key TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_wolf_completion_state
          ON wolf_completion_items(state);
        CREATE INDEX IF NOT EXISTS idx_wolf_completion_blocker
          ON wolf_completion_items(blocker_class);
        CREATE INDEX IF NOT EXISTS idx_wolf_completion_view
          ON wolf_completion_items(view_key);
        """
    )
    conn.commit()


def _as_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _require_state(state: str) -> str:
    val = (state or "").strip().upper()
    if val not in UNRESOLVED:
        raise CompletionRegisterError(
            "upsert cannot set RESOLVED; use mark_resolved with resolution_evidence",
            code="use_mark_resolved",
        )
    return val


def _require_blocker(blocker: str | None) -> str | None:
    if blocker is None or str(blocker).strip() == "":
        return None
    val = str(blocker).strip().upper()
    if val not in BLOCKER_CLASSES:
        raise CompletionRegisterError(
            f"unknown blocker_class {blocker!r}",
            code="unknown_blocker",
        )
    return val


def upsert(
    conn: sqlite3.Connection,
    *,
    capability: str | None = None,
    item_type: str | None = None,
    title: str | None = None,
    entity: str | None = None,
    domain: str | None = None,
    view_key: str | None = None,
    why_it_matters: str | None = None,
    state: str = "OPEN",
    blocker_class: str | None = None,
    owner_role: str | None = None,
    dependency: str | None = None,
    evidence: str | None = None,
    source: str | None = None,
    next_action: str | None = None,
    work_item_id: str | None = None,
) -> dict[str, Any]:
    """Insert or refresh last_checked. Never deletes. Never resolves. Never reopens."""
    key = dedup_key(
        capability=capability,
        item_type=item_type,
        title=title,
        entity=entity,
    )
    if key in ("cap:|ent:", "type:|title:|ent:"):
        raise CompletionRegisterError(
            "upsert requires capability or type+title",
            code="missing_identity",
        )
    _refuse_live_mutation(conn)
    state_val = _require_state(state)
    blocker_val = _require_blocker(blocker_class)
    item_id = _item_id(key)
    stamp = now_iso()
    existing = conn.execute(
        "SELECT * FROM wolf_completion_items WHERE dedup_key=?",
        (key,),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO wolf_completion_items (
              id, dedup_key, domain, capability, entity, item_type, title,
              why_it_matters, state, blocker_class, owner_role, dependency,
              evidence, source, first_seen, last_checked, next_action,
              resolution_evidence, resolved_at, work_item_id, view_key
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item_id,
                key,
                domain,
                capability,
                entity,
                item_type,
                title,
                why_it_matters,
                state_val,
                blocker_val,
                owner_role,
                dependency,
                evidence,
                source,
                stamp,
                stamp,
                next_action,
                None,
                None,
                work_item_id,
                view_key,
            ),
        )
    else:
        # History stays. State, resolution, and first_seen are not overwritten.
        # A later harvest may refresh evidence text and last_checked only.
        conn.execute(
            """
            UPDATE wolf_completion_items
               SET last_checked=?,
                   evidence=COALESCE(?, evidence),
                   source=COALESCE(?, source),
                   why_it_matters=COALESCE(?, why_it_matters),
                   title=COALESCE(?, title),
                   domain=COALESCE(?, domain),
                   view_key=COALESCE(?, view_key),
                   next_action=COALESCE(?, next_action),
                   work_item_id=COALESCE(?, work_item_id)
             WHERE dedup_key=?
            """,
            (
                stamp,
                evidence,
                source,
                why_it_matters,
                title,
                domain,
                view_key,
                next_action,
                work_item_id,
                key,
            ),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM wolf_completion_items WHERE dedup_key=?",
        (key,),
    ).fetchone()
    out = _as_dict(row)
    assert out is not None
    return out


def list_open(
    conn: sqlite3.Connection,
    *,
    view_key: str | None = None,
    blocker_class: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM wolf_completion_items WHERE state != 'RESOLVED'"
    args: list[Any] = []
    if view_key:
        sql += " AND view_key=?"
        args.append(view_key)
    if blocker_class:
        sql += " AND blocker_class=?"
        args.append(blocker_class.strip().upper())
    sql += " ORDER BY first_seen ASC, id ASC"
    if limit is not None:
        sql += " LIMIT ?"
        args.append(int(limit))
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def _proof_ok(resolution_evidence: str) -> None:
    ev = (resolution_evidence or "").strip()
    if not ev:
        raise CompletionRegisterError(
            "resolution_evidence required",
            code="evidence_required",
        )
    if ev.upper() in MATURITY_WORDS:
        raise CompletionRegisterError(
            "maturity change alone does not close",
            code="maturity_not_proof",
        )
    if not _PROOF_HINT.search(ev):
        raise CompletionRegisterError(
            "resolution_evidence must point at a commit, path, or prove result",
            code="evidence_required",
        )


def mark_resolved(
    conn: sqlite3.Connection,
    item_id: str,
    resolution_evidence: str,
) -> dict[str, Any]:
    """OPEN (any unresolved state) → RESOLVED only with real proof."""
    _refuse_live_mutation(conn)
    _proof_ok(resolution_evidence)
    row = conn.execute(
        "SELECT * FROM wolf_completion_items WHERE id=?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise CompletionRegisterError(f"unknown item {item_id}", code="not_found")
    if row["state"] == "RESOLVED":
        raise CompletionRegisterError(
            "already resolved; history is not rewritten",
            code="already_resolved",
        )
    stamp = now_iso()
    conn.execute(
        """
        UPDATE wolf_completion_items
           SET state='RESOLVED',
               resolution_evidence=?,
               resolved_at=?,
               last_checked=?
         WHERE id=? AND state != 'RESOLVED'
        """,
        (resolution_evidence.strip(), stamp, stamp, item_id),
    )
    conn.commit()
    updated = conn.execute(
        "SELECT * FROM wolf_completion_items WHERE id=?",
        (item_id,),
    ).fetchone()
    out = _as_dict(updated)
    assert out is not None
    return out


def _owner_card(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "state": row["state"],
        "blocker_class": row["blocker_class"],
        "domain": row["domain"],
        "entity": row["entity"],
        "capability": row["capability"],
        "item_type": row["item_type"],
        "why_it_matters": row["why_it_matters"],
        "first_seen": row["first_seen"],
    }


def _resolved_card(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "domain": row["domain"],
        "entity": row["entity"],
        "resolved_at": row["resolved_at"],
        "resolution_evidence": row["resolution_evidence"],
    }


def summary_for_owner(
    conn: sqlite3.Connection | None = None,
    *,
    db_path: Path | str | None = None,
    view_key: str | None = None,
) -> dict[str, Any]:
    """Counts at read time. Needs Matt = blocker_class NEEDS_MATT only, unresolved."""
    own = conn is None
    c = conn or db_connect(db_path)
    try:
        where = "state != 'RESOLVED'"
        args: list[Any] = []
        if view_key:
            where += " AND view_key=?"
            args.append(view_key)
        rows = c.execute(
            f"SELECT state, blocker_class FROM wolf_completion_items WHERE {where}",
            args,
        ).fetchall()
        total_open = in_progress = blocked = 0
        needs_matt = needs_staff = needs_policy = needs_external = 0
        commission = engineering = 0
        for row in rows:
            state = row["state"]
            blocker = row["blocker_class"] or ""
            if state == "OPEN":
                total_open += 1
            elif state == "IN_PROGRESS":
                in_progress += 1
            elif state == "BLOCKED":
                blocked += 1
            if blocker == "NEEDS_MATT":
                needs_matt += 1
            elif blocker == "NEEDS_STAFF":
                needs_staff += 1
            elif blocker == "NEEDS_POLICY":
                needs_policy += 1
            elif blocker == "NEEDS_EXTERNAL_ACCESS":
                needs_external += 1
            if blocker in ("NEEDS_COMMISSIONING", "NEEDS_ADOPTION"):
                commission += 1
            if blocker == "NEEDS_ENGINEERING":
                engineering += 1

        mat_sql = (
            "SELECT * FROM wolf_completion_items WHERE state != 'RESOLVED' "
            "AND (blocker_class IS NULL OR blocker_class != 'NEEDS_ENGINEERING')"
        )
        mat_args: list[Any] = []
        if view_key:
            mat_sql += " AND view_key=?"
            mat_args.append(view_key)
        mat_sql += " ORDER BY first_seen ASC, id ASC LIMIT ?"
        mat_args.append(OLDEST_LIMIT)
        oldest = [_owner_card(r) for r in c.execute(mat_sql, mat_args).fetchall()]

        res_sql = "SELECT * FROM wolf_completion_items WHERE state='RESOLVED'"
        res_args: list[Any] = []
        if view_key:
            res_sql += " AND view_key=?"
            res_args.append(view_key)
        res_sql += " ORDER BY resolved_at DESC, id ASC LIMIT ?"
        res_args.append(RESOLVED_LIMIT)
        recent = [_resolved_card(r) for r in c.execute(res_sql, res_args).fetchall()]

        return {
            "ok": True,
            "view_key": view_key,
            "generated_at": now_iso(),
            "total_open": total_open,
            "in_progress": in_progress,
            "blocked": blocked,
            "needs_matt": needs_matt,
            "needs_staff": needs_staff,
            "needs_policy": needs_policy,
            "needs_external": needs_external,
            "commissioning_adoption_debt": commission,
            "engineering_debt": engineering,
            "total_unresolved": len(rows),
            "oldest_material": oldest,
            "recently_resolved": recent,
        }
    finally:
        if own:
            c.close()


def _blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _seed_capability_debt(
    conn: sqlite3.Connection,
    ledger_path: Path,
    catalog_path: Path | None,
) -> int:
    if not ledger_path.is_file():
        return 0
    raw = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return 0
    caps = load_catalog_caps(catalog_path)
    n = 0
    source = _rel(ledger_path)
    for cap_id, row in raw.items():
        if not isinstance(row, (list, tuple)) or not row:
            continue
        maturity = str(row[0]).strip().upper()
        if maturity not in DEBT_MATURITY:
            continue
        meta = caps.get(str(cap_id), {})
        name = meta.get("name") or str(cap_id)
        scope = meta.get("scope") or None
        waiting = _blank(row[2]) if len(row) > 2 else None
        note = _blank(row[5]) if len(row) > 5 else None
        evidence = _blank(row[1]) if len(row) > 1 else None
        upsert(
            conn,
            capability=str(cap_id),
            item_type="CAPABILITY_DEBT",
            title=f"{cap_id} {name} is {maturity}",
            entity=scope,
            domain=meta.get("domain"),
            view_key=meta.get("view_key") or "Core",
            why_it_matters=waiting or note,
            state="OPEN",
            blocker_class="NEEDS_ENGINEERING",
            evidence=evidence,
            source=source,
            next_action=waiting,
        )
        n += 1
    return n


def _seed_model_e(conn: sqlite3.Connection, path: Path) -> int:
    if not path.is_file():
        return 0
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return 0
    n = 0
    source = _rel(path)
    for au in raw:
        if not isinstance(au, dict):
            continue
        if str(au.get("appl") or "").strip().upper() != "REQUIRED":
            continue
        au_state = str(au.get("state") or "").strip().upper()
        if au_state not in ("NOT STARTED", "COMMISSIONING"):
            continue
        cap = _blank(au.get("cap"))
        scope = _blank(au.get("scope")) or _blank(au.get("au_id"))
        blocker = "NEEDS_COMMISSIONING" if au_state == "COMMISSIONING" else "NEEDS_ADOPTION"
        domain = _blank(au.get("domain"))
        upsert(
            conn,
            capability=cap,
            item_type="ADOPTION",
            title=f"{au.get('au_id') or cap} {au.get('name') or ''} is {au_state}".strip(),
            entity=scope,
            domain=domain,
            view_key=_view_key_from_token(domain),
            why_it_matters=_blank(au.get("missing")),
            state="OPEN",
            blocker_class=blocker,
            evidence=_blank(au.get("evidence")),
            source=source,
        )
        n += 1
    return n


def _seed_factory(conn: sqlite3.Connection, missions: Path, runs: Path) -> int:
    n = 0
    if missions.is_dir():
        for path in sorted(missions.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            lanes = data.get("lanes") if isinstance(data, dict) else None
            if not isinstance(lanes, list):
                continue
            for lane in lanes:
                if not isinstance(lane, dict):
                    continue
                status = str(lane.get("status") or "").strip().upper()
                if status not in LANE_OPEN:
                    continue
                reason = _blank(lane.get("block_reason")) or _blank(lane.get("escalation_reason"))
                blocker = (
                    "NEEDS_POLICY"
                    if reason and reason.lower().startswith("policy_refuse")
                    else "NEEDS_ENGINEERING"
                )
                lane_id = _blank(lane.get("id")) or path.stem
                upsert(
                    conn,
                    item_type="FACTORY_LANE",
                    title=f"Factory lane {lane_id} is {status}",
                    entity="Factory",
                    domain="Factory",
                    view_key="Factory",
                    why_it_matters=reason,
                    state="BLOCKED" if status in ("BLOCKED", "FAILED", "FAILING", "ABORTED", "ABORT") else "OPEN",
                    blocker_class=blocker,
                    evidence=reason,
                    source=_rel(path),
                )
                n += 1
    if runs.is_dir():
        for path in sorted(runs.glob("BF-*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            stage = str(data.get("stage") or "").strip().upper()
            wake = data.get("wake")
            if stage not in LANE_OPEN and not wake:
                continue
            label = stage or ("WAKE" if wake else "OPEN")
            run_id = _blank(data.get("run_id")) or path.stem
            upsert(
                conn,
                item_type="FACTORY_RUN",
                title=f"Factory run {run_id} is {label}",
                entity="Factory",
                domain="Factory",
                view_key="Factory",
                why_it_matters=_blank(data.get("block_reason")),
                state="BLOCKED" if label in ("BLOCKED", "FAILED", "FAILING") else "OPEN",
                blocker_class="NEEDS_ENGINEERING",
                evidence=_blank(data.get("note")),
                source=_rel(path),
            )
            n += 1
    return n


def _uma_entity(data: dict[str, Any]) -> str:
    system = _blank(data.get("system"))
    if system:
        return system
    if data.get("PERSON"):
        return str(data["PERSON"])
    return "uma"


def _seed_claim_file(conn: sqlite3.Connection, path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(data, dict):
        return 0
    n = 0
    source = _rel(path)
    blockers = data.get("remaining_blockers")
    if isinstance(blockers, list):
        entity = _uma_entity(data)
        view = "BZG" if "uma" in entity.lower() or "bzg" in entity.lower() else "Core"
        for block in blockers:
            if not isinstance(block, dict):
                continue
            klass = str(block.get("classification") or "").strip().upper()
            if klass not in BLOCKER_CLASSES:
                continue
            bid = _blank(block.get("id")) or "blocker"
            status = _blank(block.get("status"))
            upsert(
                conn,
                item_type="COMMISSIONING_BLOCKER",
                title=f"{bid} {status}".strip() if status else bid,
                entity=entity,
                domain="BZG" if view == "BZG" else None,
                view_key=view,
                why_it_matters=_blank(block.get("why")),
                state="OPEN",
                blocker_class=klass,
                evidence=source,
                source=source,
            )
            n += 1
    human = _blank(data.get("HUMAN_COMMISSIONING_STATUS"))
    if human and human.upper() not in HUMAN_DONE:
        upsert(
            conn,
            item_type="COMMISSIONING",
            title="Devi commissioning not finished",
            entity="DEVI",
            domain="BZG",
            view_key="BZG",
            why_it_matters=_blank(data.get("NOTES")) or human,
            state="WAITING_HUMAN",
            blocker_class="NEEDS_COMMISSIONING",
            evidence=source,
            source=source,
        )
        n += 1
    devi_c = _blank(data.get("devi_commission"))
    if devi_c and "WAITING" in devi_c.upper():
        upsert(
            conn,
            item_type="COMMISSIONING",
            title="Devi commissioning not finished",
            entity="DEVI",
            domain="BZG",
            view_key="BZG",
            why_it_matters=devi_c,
            state="WAITING_HUMAN",
            blocker_class="NEEDS_COMMISSIONING",
            evidence=source,
            source=source,
        )
        n += 1
    if "cutover_at" in data or "CUTOVER_AT" in data:
        raw_cut = data["cutover_at"] if "cutover_at" in data else data.get("CUTOVER_AT")
        if raw_cut is None:
            upsert(
                conn,
                item_type="CUTOVER",
                title="cutover_at unset",
                entity="uma",
                domain="BZG",
                view_key="BZG",
                why_it_matters="cutover_at is null. No cutover timestamp is invented here.",
                state="OPEN",
                blocker_class="NEEDS_POLICY",
                evidence=source,
                source=source,
            )
            n += 1
    return n


def _seed_cutover_file(conn: sqlite3.Connection, path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(data, dict) or "cutover_at" not in data:
        return 0
    if data.get("cutover_at") is not None:
        return 0
    sources = data.get("sources")
    upsert(
        conn,
        item_type="CUTOVER",
        title="cutover_at unset",
        entity="uma",
        domain="BZG",
        view_key="BZG",
        why_it_matters="cutover_at is null. No cutover timestamp is invented here.",
        state="OPEN",
        blocker_class="NEEDS_POLICY",
        evidence=json.dumps({"cutover_at": None, "sources": sources}, sort_keys=True),
        source=_rel(path),
    )
    return 1


def _seed_ended_scope(conn: sqlite3.Connection, path: Path) -> int:
    if not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8")
    if "upsert_asg_scope" not in text or "ENDED" not in text:
        return 0
    upsert(
        conn,
        item_type="DEFECT",
        title="ENDED scope resurrection on daily-close assignment upsert",
        entity="SCOPE-BZG-ENTITY",
        domain="BZG",
        view_key="BZG",
        why_it_matters=(
            "Daily-close assignment upsert forces an ENDED scope back to ACTIVE. "
            "Documented follow-up, not an Owner blocker."
        ),
        state="OPEN",
        blocker_class="NEEDS_ENGINEERING",
        evidence=_rel(path),
        source=_rel(path),
    )
    return 1


def _seed_review_findings(conn: sqlite3.Connection, review_dir: Path, *, limit: int = REVIEW_SCAN_N) -> int:
    """Last N review docs. Only explicit OPEN FINDING lines, and only if the verdict is not PASS."""
    if not review_dir.is_dir():
        return 0
    files = sorted(review_dir.glob("GROK-REVIEW-*.md"))[-limit:]
    n = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        head = "\n".join(text.splitlines()[:50])
        verdict = ""
        m = re.search(r"##\s*Verdict\s*(.*)", head, re.IGNORECASE | re.DOTALL)
        if m:
            verdict = m.group(1)[:240]
        elif "Verdict" in head:
            verdict = head.split("Verdict", 1)[-1][:240]
        if re.search(r"\bPASS\b", verdict) and not re.search(r"\bFAIL\b", verdict):
            continue
        if not re.search(r"\bFAIL\b", verdict):
            continue
        for found in re.finditer(
            r"(?im)^[ \t>*-]*OPEN FINDING:\s*(.+?)\s*$",
            text,
        ):
            title = found.group(1).strip()
            if not title:
                continue
            upsert(
                conn,
                item_type="REVIEW_FINDING",
                title=title[:180],
                entity="review",
                domain=None,
                view_key="Core",
                why_it_matters=title[:180],
                state="OPEN",
                blocker_class="NEEDS_ENGINEERING",
                evidence=_rel(path),
                source=_rel(path),
            )
            n += 1
    return n


def seed_authorised_evidence(
    conn: sqlite3.Connection | None = None,
    *,
    db_path: Path | str | None = None,
    ledger_path: Path | None = None,
    catalog_path: Path | None = None,
    model_e_path: Path | None = None,
    missions_dir: Path | None = None,
    runs_dir: Path | None = None,
    claims_dir: Path | None = None,
    cutover_path: Path | None = None,
    ended_scope_review: Path | None = None,
    review_dir: Path | None = None,
    use_live_defaults: bool = True,
) -> dict[str, int]:
    """Harvest OPEN rows from authorised files. Deduped. Does not resolve."""
    own = conn is None
    c = conn or db_connect(db_path)
    _refuse_live_mutation(c)
    try:
        counts = {
            "capability_debt": 0,
            "adoption": 0,
            "factory": 0,
            "claims": 0,
            "cutover": 0,
            "defects": 0,
            "reviews": 0,
        }
        if use_live_defaults:
            ledger_path = ledger_path or MODEL_C_LEDGER
            catalog_path = catalog_path or MODEL_C_CATALOG
            model_e_path = model_e_path or MODEL_E_AUS
            missions_dir = missions_dir or FACTORY_MISSIONS
            runs_dir = runs_dir or FACTORY_RUNS
            claims_dir = claims_dir or CLAIMS_DIR
            cutover_path = cutover_path or CUTOVER_PATH
            ended_scope_review = ended_scope_review or ENDED_SCOPE_REVIEW
            review_dir = review_dir or REVIEW_DIR
        if ledger_path is not None:
            counts["capability_debt"] = _seed_capability_debt(c, ledger_path, catalog_path)
        if model_e_path is not None:
            counts["adoption"] = _seed_model_e(c, model_e_path)
        if missions_dir is not None or runs_dir is not None:
            counts["factory"] = _seed_factory(
                c,
                missions_dir or Path("/nonexistent"),
                runs_dir or Path("/nonexistent"),
            )
        if claims_dir is not None and claims_dir.is_dir():
            for path in sorted(claims_dir.glob("*.json")):
                counts["claims"] += _seed_claim_file(c, path)
        if cutover_path is not None:
            counts["cutover"] = _seed_cutover_file(c, cutover_path)
        if ended_scope_review is not None:
            counts["defects"] = _seed_ended_scope(c, ended_scope_review)
        if review_dir is not None:
            counts["reviews"] = _seed_review_findings(c, review_dir)
        return counts
    finally:
        if own:
            c.close()


if __name__ == "__main__":
    connection = db_connect()
    try:
        seeded = seed_authorised_evidence(connection)
        summary = summary_for_owner(connection)
        print(
            json.dumps(
                {"seeded": seeded, "summary_counts": {k: summary[k] for k in SUMMARY_KEYS if k not in ("oldest_material", "recently_resolved")}, "unresolved": summary["total_unresolved"], "engineering_debt": summary["engineering_debt"]},
                indent=2,
            )
        )
    finally:
        connection.close()
