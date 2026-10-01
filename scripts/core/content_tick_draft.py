#!/usr/bin/env python3
"""Pack 4 — one Habitat card: comment, apply, tick.

The current cycle file is the V1 JSON whose dates contain today. Beta
catalog plans end 2026-09-27, so they are the previous fortnight.

Tick tries a Metricool draft. Write-to-publish is fail-closed, so the
live path does not open the network and records a Misa queue item instead.
Publish stays off. full_tree_indexed stays false.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

WITA = timezone(timedelta(hours=8))
BETA = Path.home() / "beta-os"
WS = Path.home() / ".openclaw/workspace/wolf-system"
CYCLE_FILE = WS / "dashboards/data/content-plans/habitat-2026-09-28-11.json"
ATRIUM_CYCLE = WS / "dashboards/data/content-plans/atrium-2026-09-28-11.json"
CATALOG = BETA / "catalog" / "content_library.sqlite"
MEDIA_ROOT = Path("/Volumes/01-Media-Library")
BRAND = "habitat"
CYCLE_KEY = "2026-09-28-11"

WHY_HABITAT = (
    "V1 habitat-2026-09-28-11.json runs 2026-09-28 through 2026-10-11, which "
    "contains 2026-10-01. Atrium has a file with the same window. Beta "
    "content_plans period_end is 2026-09-27, the previous fortnight. Habitat "
    "is the brand the Beta publish gate already locks. Feed titles in the "
    "current file are blank and were not filled in."
)


def _now() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _stamp(**extra: Any) -> dict[str, Any]:
    out = {
        "ok": True,
        "staff_ready": False,
        "human_commissioned": False,
        "human_proven": False,
        "publish": "OFF",
        "metricool_publish": False,
        "full_tree_indexed": False,
        "haikal_upload_retest": "OPEN",
        "brand": BRAND,
        "surface": "content_tick_draft",
        "next": (
            "PACK-01 Owner cockpit. Pack 4 finished on the Habitat fallback "
            "queue. Finance SoD stays closed."
        ),
    }
    out.update(extra)
    return out


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS content_cycle_notes (
          id INTEGER PRIMARY KEY,
          brand TEXT,
          cycle_key TEXT,
          card_id TEXT,
          kind TEXT,
          body TEXT,
          actor TEXT,
          created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS content_misa_queue (
          id TEXT PRIMARY KEY,
          brand TEXT,
          cycle_key TEXT,
          card_id TEXT,
          scheduled_date TEXT,
          title TEXT,
          state TEXT,
          reason TEXT,
          metricool_draft_id TEXT,
          publish TEXT,
          library_where TEXT,
          created_at TEXT
        )
        """
    )
    return conn


def load_cycle(path: Path | None = None) -> dict[str, Any]:
    src = path or CYCLE_FILE
    if not src.is_file():
        return _stamp(ok=False, error="cycle_file_missing", path=str(src))
    data = json.loads(src.read_text(encoding="utf-8"))
    posts = list(data.get("posts") or [])
    stories = list(data.get("stories") or [])
    cards = []
    for kind, rows in (("post", posts), ("story", stories)):
        for row in rows:
            title = (row.get("title") or "").strip()
            cards.append({
                "id": row.get("id"),
                "kind": kind,
                "date": row.get("date"),
                "n": row.get("n"),
                "title": title,
                "title_blank": title == "",
                "type": row.get("type") or row.get("meta") or "",
                "body": (row.get("body") or row.get("caption_angle") or "")[:400],
            })
    return _stamp(
        ok=True,
        why_brand=WHY_HABITAT,
        cycle={
            "brand": data.get("brand_id"),
            "handle": data.get("handle"),
            "cycle_key": data.get("cycle_key"),
            "cycle_start": data.get("cycle_start"),
            "cycle_end": data.get("cycle_end"),
            "cadence_line": data.get("cadence_line"),
            "source": str(src),
            "open_mode": "ro",
            "on_beta_disk": False,
            "beta_catalog_plans_end": "2026-09-27",
            "atrium_same_window_file": ATRIUM_CYCLE.is_file(),
        },
        counts={"posts": len(posts), "stories": len(stories), "cards": len(cards)},
        cards=cards,
    )


def _card(cycle: dict[str, Any], card_id: str) -> dict[str, Any] | None:
    for card in cycle.get("cards") or []:
        if str(card.get("id")) == str(card_id):
            return card
    return None


def library_lookup(name: str, *, catalog: Path | None = None) -> dict[str, Any]:
    """Say whether one name is in the assets table, or is one existing NAS file.

    Does not walk the media tree. full_tree_indexed stays false.
    """
    db = catalog or CATALOG
    needle = (name or "").strip()
    out = _stamp(
        query=needle,
        where="not_in_library",
        library_asset_count=None,
        tree_walked=False,
        nas_mounted=MEDIA_ROOT.is_dir(),
    )
    if not needle:
        out["ok"] = False
        out["error"] = "empty_query"
        return out
    if not db.is_file():
        out["where"] = "library_db_missing"
        return out
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
        out["library_asset_count"] = total
        hit = conn.execute(
            """
            SELECT id, brand, filename, slug FROM assets
            WHERE filename = ? OR slug = ? OR original_filename = ?
            LIMIT 1
            """,
            (needle, needle, needle),
        ).fetchone()
    except sqlite3.OperationalError:
        hit = None
        try:
            total = int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
            out["library_asset_count"] = total
            hit = conn.execute(
                """
                SELECT id, brand, filename, slug FROM assets
                WHERE filename = ? OR slug = ?
                LIMIT 1
                """,
                (needle, needle),
            ).fetchone()
        except sqlite3.Error as exc:
            conn.close()
            out["where"] = "library_read_error"
            out["error"] = type(exc).__name__
            return out
    conn.close()
    if hit:
        out["where"] = "library"
        out["asset_id"] = hit[0]
        out["asset_brand"] = hit[1]
        out["filename"] = hit[2]
        return out
    candidate = Path(needle)
    if candidate.is_file():
        try:
            candidate.resolve().relative_to(MEDIA_ROOT.resolve())
            under = True
        except (ValueError, OSError):
            under = False
        if under:
            out["where"] = "nas_only"
            out["path"] = str(candidate)
            out["honesty"] = "One file stat. The NAS tree was not indexed."
            return out
    out["honesty"] = (
        "Not in the assets table. Absence here is not a NAS inventory. "
        "full_tree_indexed is false."
    )
    return out


def _attempt_draft(card: dict[str, Any]) -> dict[str, Any]:
    try:
        from metricool_read_client import MetricoolWriteBlocked, assert_metricool_write_allowed

        assert_metricool_write_allowed("draft")
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": "metricool_write_blocked",
            "detail": str(exc),
            "network": False,
            "published": False,
        }
    return {
        "ok": False,
        "error": "draft_not_sent",
        "detail": "Metricool write flag is on. This pack still does not call publish or draft endpoints.",
        "network": False,
        "published": False,
    }


def comment(card_id: str, body: str, *, actor: str = "team", db: Path | None = None, cycle_path: Path | None = None) -> dict[str, Any]:
    cycle = load_cycle(cycle_path)
    if not cycle.get("ok"):
        return cycle
    card = _card(cycle, card_id)
    if card is None:
        return _stamp(ok=False, error="unknown_card", card_id=card_id)
    text = (body or "").strip()
    if not text:
        return _stamp(ok=False, error="empty_comment", card_id=card_id)
    conn = _connect(db or CATALOG)
    try:
        conn.execute(
            """
            INSERT INTO content_cycle_notes (brand, cycle_key, card_id, kind, body, actor, created_at)
            VALUES (?, ?, ?, 'comment', ?, ?, ?)
            """,
            (BRAND, CYCLE_KEY, card_id, text, actor, _now()),
        )
        conn.commit()
        note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    finally:
        conn.close()
    return _stamp(ok=True, note_id=note_id, card_id=card_id, kind="comment", body=text, actor=actor)


def apply_note(card_id: str, *, actor: str = "amanda-path", db: Path | None = None, cycle_path: Path | None = None) -> dict[str, Any]:
    cycle = load_cycle(cycle_path)
    if not cycle.get("ok"):
        return cycle
    if _card(cycle, card_id) is None:
        return _stamp(ok=False, error="unknown_card", card_id=card_id)
    conn = _connect(db or CATALOG)
    try:
        row = conn.execute(
            """
            SELECT id, body, actor FROM content_cycle_notes
            WHERE brand=? AND cycle_key=? AND card_id=? AND kind='comment'
            ORDER BY id DESC LIMIT 1
            """,
            (BRAND, CYCLE_KEY, card_id),
        ).fetchone()
        if row is None:
            return _stamp(ok=False, error="nothing_to_apply", card_id=card_id)
        conn.execute(
            """
            INSERT INTO content_cycle_notes (brand, cycle_key, card_id, kind, body, actor, created_at)
            VALUES (?, ?, ?, 'applied', ?, ?, ?)
            """,
            (BRAND, CYCLE_KEY, card_id, row["body"], actor, _now()),
        )
        conn.commit()
        applied_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    finally:
        conn.close()
    return _stamp(
        ok=True,
        applied_id=applied_id,
        card_id=card_id,
        body=row["body"],
        source_comment_id=row["id"],
        actor=actor,
        amanda_session=False,
        cycle_file_written=False,
    )


def tick(
    card_id: str,
    *,
    db: Path | None = None,
    cycle_path: Path | None = None,
    catalog: Path | None = None,
    draft_client: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cycle = load_cycle(cycle_path)
    if not cycle.get("ok"):
        return cycle
    card = _card(cycle, card_id)
    if card is None:
        return _stamp(ok=False, error="unknown_card", card_id=card_id)
    lib = library_lookup(card.get("title") or "", catalog=catalog) if card.get("title") else _stamp(
        where="no_file_on_card", library_asset_count=None, tree_walked=False,
    )
    if not card.get("title"):
        lib = _stamp(where="no_file_on_card", query="", tree_walked=False, full_tree_indexed=False)
    path = db or CATALOG
    conn = _connect(path)
    try:
        existing = conn.execute(
            """
            SELECT * FROM content_misa_queue
            WHERE brand=? AND cycle_key=? AND card_id=?
            ORDER BY created_at DESC LIMIT 1
            """,
            (BRAND, CYCLE_KEY, card_id),
        ).fetchone()
        if existing is not None:
            item = dict(existing)
            item["idempotent"] = True
            return _stamp(ok=True, card=card, queue=item, library=lib, idempotent=True)
        draft = draft_client(card) if draft_client else _attempt_draft(card)
        published = bool(draft.get("published"))
        if published:
            return _stamp(ok=False, error="publish_refused", card_id=card_id, network=False)
        draft_id = draft.get("draft_id") if draft.get("ok") else None
        if draft.get("ok") and draft_id:
            state = "METRICOOL_DRAFT"
            reason = "draft_recorded_publish_off"
        else:
            state = "QUEUED"
            reason = str(draft.get("error") or "metricool_failed")
            draft_id = None
        qid = "MISA-" + uuid.uuid4().hex[:12].upper()
        conn.execute(
            """
            INSERT INTO content_misa_queue (
              id, brand, cycle_key, card_id, scheduled_date, title, state, reason,
              metricool_draft_id, publish, library_where, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OFF', ?, ?)
            """,
            (
                qid, BRAND, CYCLE_KEY, card_id, card.get("date"), card.get("title") or "",
                state, reason, draft_id, lib.get("where"), _now(),
            ),
        )
        conn.commit()
        row = dict(conn.execute("SELECT * FROM content_misa_queue WHERE id=?", (qid,)).fetchone())
    finally:
        conn.close()
    return _stamp(
        ok=True,
        card=card,
        queue=row,
        library=lib,
        draft_attempt=draft,
        idempotent=False,
        network=bool(draft.get("network")),
    )


def queue_rows(db: Path | None = None) -> list[dict[str, Any]]:
    path = db or CATALOG
    if not path.is_file():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            """
            SELECT * FROM content_misa_queue
            WHERE brand=? AND cycle_key=?
            ORDER BY created_at
            """,
            (BRAND, CYCLE_KEY),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def notes_for(card_id: str, db: Path | None = None) -> list[dict[str, Any]]:
    path = db or CATALOG
    if not path.is_file():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            """
            SELECT id, kind, body, actor, created_at FROM content_cycle_notes
            WHERE brand=? AND cycle_key=? AND card_id=?
            ORDER BY id
            """,
            (BRAND, CYCLE_KEY, card_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def desk(db: Path | None = None, catalog: Path | None = None) -> dict[str, Any]:
    before = CYCLE_FILE.stat()
    cycle = load_cycle()
    after = CYCLE_FILE.stat()
    cycle["cycle_file_mtime_unchanged"] = before.st_mtime_ns == after.st_mtime_ns
    shown = (cycle.get("cards") or [])[:40]
    lib = library_lookup(
        "habitat_RAW_video_habitat-vibe_workers_20260730_001.mov",
        catalog=catalog,
    )
    cycle["cards_shown"] = shown
    cycle["cards_total"] = len(cycle.get("cards") or [])
    cycle.pop("cards", None)
    cycle["library_example"] = lib
    cycle["queue"] = queue_rows(db)
    cycle["publish"] = "OFF"
    return cycle


def refuse_publish() -> dict[str, Any]:
    return _stamp(ok=False, error="publish_off", network=False)


def handle_get(path: str) -> dict[str, Any]:
    rest = path[len("/api/content/tick-draft"):].strip("/")
    if not rest:
        return desk()
    if rest.startswith("cards/"):
        card_id = rest.split("/", 1)[1]
        cycle = load_cycle()
        card = _card(cycle, card_id)
        if card is None:
            return _stamp(ok=False, error="unknown_card", card_id=card_id)
        return _stamp(card=card, notes=notes_for(card_id), queue=[
            row for row in queue_rows() if row.get("card_id") == card_id
        ])
    return _stamp(ok=False, error="unknown_path", path=path)


def handle_post(path: str, body: dict[str, Any] | None) -> tuple[dict[str, Any], int]:
    payload = body or {}
    if path.rstrip("/").endswith("/publish"):
        return refuse_publish(), 405
    card_id = str(payload.get("card_id") or "").strip()
    if path.rstrip("/").endswith("/comment"):
        result = comment(card_id, str(payload.get("body") or ""))
        return result, 200 if result.get("ok") else 400
    if path.rstrip("/").endswith("/apply"):
        result = apply_note(card_id)
        return result, 200 if result.get("ok") else 400
    if path.rstrip("/").endswith("/tick"):
        result = tick(card_id)
        return result, 200 if result.get("ok") else 400
    return _stamp(ok=False, error="unknown_path", path=path), 404
