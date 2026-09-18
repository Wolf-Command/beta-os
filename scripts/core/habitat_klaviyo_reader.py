#!/usr/bin/env python3
"""Habitat Klaviyo read-only ingestion v1. Beta prove. Not cutover.

profile.created is lead received for source system klaviyo.
That clock means RECEIVED_BY_KLAVIYO_SOURCE.
It does not prove the instant a human submitted an enquiry upstream.
wolf_ingested_at is wolf first seen. Event recorded_at is the ingestion clock.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from core import lead_spine as _spine

SOURCE_SYSTEM = "klaviyo"
CLOCK = "profile.created"
CLOCK_MEANING = "RECEIVED_BY_KLAVIYO_SOURCE"
CLOCK_NOTE = "Does not prove the instant a human submitted an enquiry upstream."

LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS core_lead_ingest_runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  completed_at TEXT NULL,
  state TEXT NOT NULL CHECK (state IN ('RUNNING', 'INCOMPLETE', 'COMPLETE')),
  cursor_next TEXT NULL,
  pages_examined INTEGER NOT NULL DEFAULT 0,
  records_examined INTEGER NOT NULL DEFAULT 0,
  inserted INTEGER NOT NULL DEFAULT 0,
  already_present INTEGER NOT NULL DEFAULT 0,
  skipped INTEGER NOT NULL DEFAULT 0,
  errors INTEGER NOT NULL DEFAULT 0,
  oldest_source_at TEXT NULL,
  newest_source_at TEXT NULL,
  boundary_at TEXT NOT NULL,
  detail_json TEXT NOT NULL
);
"""


class _PageHalt(Exception):
    """Stop this page without treating the run as complete."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def ensure_ledger(conn: sqlite3.Connection) -> None:
    conn.executescript(LEDGER_SQL)


def _parse_ts(value: str) -> datetime:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt


def _usable_url(url: str) -> bool:
    """A real URL. page[cursor] may be percent-encoded or not. Neither form is required."""
    if not url or any(ch.isspace() for ch in url):
        return False
    lowered = url.lower()
    if lowered.startswith("https://"):
        rest = url[len("https://") :]
    elif lowered.startswith("http://"):
        rest = url[len("http://") :]
    else:
        return False
    if not rest or rest[0] in "/?#":
        return False
    host = rest.split("/", 1)[0].split("?", 1)[0]
    if not host or host.startswith("."):
        return False
    return True


def _classify_next(page: dict[str, Any]) -> tuple[str, str | None]:
    links = page.get("links")
    if links is None:
        return ("last", None)
    if not isinstance(links, dict):
        return ("bad", None)
    nxt = links.get("next", None)
    if nxt is None:
        return ("last", None)
    if isinstance(nxt, str) and nxt.strip() == "":
        return ("last", None)
    if not isinstance(nxt, str):
        return ("bad", None)
    cleaned = nxt.strip()
    if not _usable_url(cleaned):
        return ("bad", cleaned)
    return ("next", cleaned)


def _raw_next_str(page: Any) -> str | None:
    if not isinstance(page, dict):
        return None
    kind, url = _classify_next(page)
    if kind == "next":
        return url
    return None


def _mint_run_id() -> str:
    return f"INGRUN-{uuid.uuid4()}"


def _loads_detail(raw: str | None) -> dict[str, Any]:
    try:
        obj = json.loads(raw or "{}")
    except json.JSONDecodeError:
        obj = {}
    if not isinstance(obj, dict):
        obj = {}
    ids = obj.get("examined_ids")
    if not isinstance(ids, list):
        obj["examined_ids"] = []
    return obj


def _dumps(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _load_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM core_lead_ingest_runs WHERE run_id=?",
        (run_id,),
    ).fetchone()
    if row is None:
        raise _spine.LeadSpineError("ingest run not found", code="not_found")
    return dict(row)


def _save_run(conn: sqlite3.Connection, run: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE core_lead_ingest_runs SET
          started_at=?,
          completed_at=?,
          state=?,
          cursor_next=?,
          pages_examined=?,
          records_examined=?,
          inserted=?,
          already_present=?,
          skipped=?,
          errors=?,
          oldest_source_at=?,
          newest_source_at=?,
          boundary_at=?,
          detail_json=?
        WHERE run_id=?
        """,
        (
            run["started_at"],
            run["completed_at"],
            run["state"],
            run["cursor_next"],
            run["pages_examined"],
            run["records_examined"],
            run["inserted"],
            run["already_present"],
            run["skipped"],
            run["errors"],
            run["oldest_source_at"],
            run["newest_source_at"],
            run["boundary_at"],
            run["detail_json"],
            run["run_id"],
        ),
    )
    conn.commit()


def _widen(oldest: str | None, newest: str | None, created: str) -> tuple[str, str]:
    if oldest is None or _parse_ts(created) < _parse_ts(oldest):
        oldest = created
    if newest is None or _parse_ts(created) > _parse_ts(newest):
        newest = created
    return oldest, newest


def _drop_through_cursor(pages: list[Any], cursor: str | None) -> list[Any]:
    """Start at the page after the last committed cursor. If the cursor is not in
    this list, the caller already started there."""
    if not cursor:
        return pages
    for i, page in enumerate(pages):
        if _raw_next_str(page) == cursor:
            return pages[i + 1 :]
    return pages


def _provenance(email: str | None) -> dict[str, Any]:
    prov: dict[str, Any] = {
        "source": SOURCE_SYSTEM,
        "clock": CLOCK,
        "meaning": CLOCK_MEANING,
        "note": CLOCK_NOTE,
    }
    if email:
        prov["email"] = email
    return prov


def _finish(conn: sqlite3.Connection, run: dict[str, Any], state: str, detail: dict[str, Any]) -> dict[str, Any]:
    run["state"] = state
    run["completed_at"] = _spine.now_utc_iso()
    run["detail_json"] = _dumps(detail)
    _save_run(conn, run)
    return _load_run(conn, run["run_id"])


def probe_readonly(fetch_page) -> dict[str, int]:
    """Walk pages and return counts only. Does not ingest and does not write leads."""
    pages_examined = 0
    records_examined = 0
    errors = 0
    cursor: str | None = None
    seen: set[str] = set()
    while True:
        page = fetch_page(cursor)
        if page is None:
            break
        if not isinstance(page, dict):
            errors += 1
            break
        pages_examined += 1
        data = page.get("data") or []
        if isinstance(data, list):
            records_examined += len(data)
        else:
            errors += 1
            break
        kind, url = _classify_next(page)
        if kind == "bad":
            errors += 1
            break
        if kind == "last" or url is None:
            break
        if url in seen:
            errors += 1
            break
        seen.add(url)
        cursor = url
    return {
        "pages_examined": pages_examined,
        "records_examined": records_examined,
        "errors": errors,
    }


def run_ingest(
    pages,
    *,
    entity_id: str,
    brand_id: str,
    boundary_at: str,
    conn: sqlite3.Connection,
    resume_run_id: str | None = None,
) -> dict[str, Any]:
    """Ingest injected Klaviyo pages. boundary_at is required. No network."""
    if conn is None:
        raise _spine.LeadSpineError("conn required", code="invalid")
    eid = (entity_id or "").strip()
    bid = (brand_id or "").strip()
    if not eid or not bid:
        raise _spine.LeadSpineError("entity_id and brand_id required", code="missing_entity")
    if not isinstance(boundary_at, str) or not boundary_at.strip():
        raise _spine.LeadSpineError("boundary_at required", code="invalid")
    boundary = boundary_at.strip()
    try:
        boundary_dt = _parse_ts(boundary)
    except (TypeError, ValueError) as exc:
        raise _spine.LeadSpineError("boundary_at unparseable", code="invalid") from exc

    ensure_ledger(conn)
    _spine.ensure_schema(conn)

    if resume_run_id:
        run = _load_run(conn, resume_run_id)
        if run["boundary_at"] != boundary:
            raise _spine.LeadSpineError("boundary_at does not match run", code="invalid")
        run["state"] = "RUNNING"
        run["completed_at"] = None
        detail = _loads_detail(run["detail_json"])
        try:
            page_seq: Any = list(pages)
        except Exception:
            run["errors"] = int(run["errors"]) + 1
            detail["last_error"] = "page_raise"
            run["detail_json"] = _dumps(detail)
            _finish(conn, run, "INCOMPLETE", detail)
            raise
        page_seq = _drop_through_cursor(page_seq, run["cursor_next"])
        # Prior INCOMPLETE is the reason we resumed. This attempt starts clean
        # so a finished retry can be COMPLETE when errors stay 0.
        detail["prior_errors"] = int(run["errors"] or 0)
        run["errors"] = 0
        run["detail_json"] = _dumps(detail)
        _save_run(conn, run)
    else:
        started = _spine.now_utc_iso()
        run = {
            "run_id": _mint_run_id(),
            "started_at": started,
            "completed_at": None,
            "state": "RUNNING",
            "cursor_next": None,
            "pages_examined": 0,
            "records_examined": 0,
            "inserted": 0,
            "already_present": 0,
            "skipped": 0,
            "errors": 0,
            "oldest_source_at": None,
            "newest_source_at": None,
            "boundary_at": boundary,
            "detail_json": _dumps(
                {
                    "examined_ids": [],
                    "source": SOURCE_SYSTEM,
                    "clock": CLOCK,
                    "meaning": CLOCK_MEANING,
                }
            ),
        }
        conn.execute(
            """
            INSERT INTO core_lead_ingest_runs (
              run_id, started_at, completed_at, state, cursor_next,
              pages_examined, records_examined, inserted, already_present,
              skipped, errors, oldest_source_at, newest_source_at,
              boundary_at, detail_json
            ) VALUES (?, ?, NULL, 'RUNNING', NULL, 0, 0, 0, 0, 0, 0, NULL, NULL, ?, ?)
            """,
            (run["run_id"], started, boundary, run["detail_json"]),
        )
        conn.commit()
        detail = _loads_detail(run["detail_json"])
        page_seq = pages

    def _persist_progress() -> None:
        run["detail_json"] = _dumps(detail)
        _save_run(conn, run)

    try:
        for page in page_seq:
            if not isinstance(page, dict):
                raise _PageHalt("page_not_object")
            kind, next_url = _classify_next(page)
            if kind == "bad":
                run["errors"] = int(run["errors"]) + 1
                detail["last_error"] = "malformed_next"
                return _finish(conn, run, "INCOMPLETE", detail)

            data = page.get("data")
            if data is None:
                data = []
            if not isinstance(data, list):
                raise _PageHalt("data_not_list")

            page_errors = 0
            valid = 0
            before = 0
            for item in data:
                run["records_examined"] = int(run["records_examined"]) + 1
                if not isinstance(item, dict):
                    page_errors += 1
                    continue
                pid = item.get("id")
                pid_s = str(pid).strip() if pid is not None else ""
                attrs = item.get("attributes")
                if not isinstance(attrs, dict):
                    attrs = {}
                created = attrs.get("created")
                created_s = str(created).strip() if isinstance(created, str) else ""
                if pid_s:
                    detail["examined_ids"].append(pid_s)
                if not pid_s or not created_s:
                    page_errors += 1
                    continue
                try:
                    created_dt = _parse_ts(created_s)
                except (TypeError, ValueError):
                    page_errors += 1
                    continue
                valid += 1
                oldest, newest = _widen(
                    run["oldest_source_at"], run["newest_source_at"], created_s
                )
                run["oldest_source_at"] = oldest
                run["newest_source_at"] = newest
                if created_dt < boundary_dt:
                    before += 1
                    run["skipped"] = int(run["skipped"]) + 1
                    continue
                email = attrs.get("email")
                email_s = email.strip() if isinstance(email, str) and email.strip() else None
                result = _spine.ingest_observation(
                    entity_id=eid,
                    brand_id=bid,
                    source_system=SOURCE_SYSTEM,
                    source_id=pid_s,
                    source_observed_at=created_s,
                    source_stage=None,
                    provenance=_provenance(email_s),
                    observation_key=f"klaviyo:{pid_s}:received",
                    actor_type="SYSTEM",
                    conn=conn,
                )
                if result.get("created"):
                    run["inserted"] = int(run["inserted"]) + 1
                else:
                    run["already_present"] = int(run["already_present"]) + 1

            if page_errors:
                run["errors"] = int(run["errors"]) + page_errors
                detail["last_error"] = "missing_created"
                return _finish(conn, run, "INCOMPLETE", detail)

            run["pages_examined"] = int(run["pages_examined"]) + 1
            run["cursor_next"] = next_url
            _persist_progress()

            fully_before = valid > 0 and before == valid
            if kind == "last" or fully_before:
                if int(run["errors"]) == 0:
                    return _finish(conn, run, "COMPLETE", detail)
                return _finish(conn, run, "INCOMPLETE", detail)
    except Exception:
        run["errors"] = int(run["errors"]) + 1
        detail["last_error"] = "page_raise"
        _finish(conn, run, "INCOMPLETE", detail)
        raise

    return _finish(conn, run, "INCOMPLETE", detail)
