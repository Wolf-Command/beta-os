#!/usr/bin/env python3
"""CAP-BZG-07 review and reputation observe v1 (Beta only).

Decision served: 2026-09-19 PICK, reputation observe v1 on Beta only
(docs/deliveries/GROK-PLAN-BZG-REPUTATION-OBSERVE-V1-2026-09-19.md).

Wolf observes reviews. It does not solicit them, scrape them, or reply to
guests. No review source is connected in this slice. When there is no source,
the view is empty and the rating is null. A 5-star score is never invented.

A human may store one append-only observation with provenance. That row is a
record of what was supplied. It is not a connected source and it is not a
reputation summary.

Honesty is bound to CR-d1aacda59180eba7. The ledger is read, not written.
Maturity ceiling is BUILT unless the ledger row is already PROVEN or READY.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "bzg_reputation.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-d1aacda59180eba7"
CAP_ID = "CAP-BZG-07"
TZ_UTC = timezone.utc

PERM_READ = "bzg.reputation.read"
PERM_OBSERVE = "bzg.reputation.observe"

VENUES = frozenset({"UMA", "RAINFOREST", "MERAH", "ROOFTOP"})
SOURCE_KIND = "OWNER_RECORD"
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY_WORDS = frozenset(
    {"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY", "LIVE", "MERGED"}
)
EMPTY_SOURCE = frozenset(
    {
        "",
        "none",
        "unknown",
        "n/a",
        "na",
        "null",
        "empty",
        "missing",
        "no-source",
        "not-a-source",
    }
)

OBSERVE_KEYS = frozenset(
    {
        "venue_id",
        "source_kind",
        "source_ref",
        "provenance",
        "observed_rating",
        "rating_scale",
        "excerpt",
    }
)
BANNED_KEYS = frozenset(
    {
        "stars",
        "star",
        "five_star",
        "rating",
        "summary_rating",
        "score",
        "proven",
        "ready",
        "maturity",
        "source_connected",
        "scraped",
        "reply_sent",
    }
)
SCRAPE_KEYS = frozenset(
    {"scrape", "serp", "crawler", "spider", "fetch_reviews", "google_scrape", "tripadvisor"}
)
REPLY_KEYS = frozenset(
    {
        "reply",
        "auto_reply",
        "guest_reply",
        "reply_to_guest",
        "message_to_guest",
        "respond",
        "response_text",
    }
)

_PERSON_RE = re.compile(r"^PERS-[A-Z0-9][A-Z0-9-]{0,40}$")
_OBS_RE = re.compile(
    r"^OBS-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)
_SCRAPE_TEXT_RE = re.compile(
    r"\b(scrape|serp|crawler|spider|fake review|invented review)\b",
    re.IGNORECASE,
)

EMPTY_NOTE = (
    "No review source is connected. No star rating was invented. "
    "Wolf does not scrape reviews and does not reply to guests."
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "bzg_reputation_observe_v1",
    "source_connected": False,
    "source_present": False,
    "configured_sources": [],
    "summary_rating": None,
    "five_star_invented": False,
    "rating_defaulted": False,
    "scraped": False,
    "fake_scrape": False,
    "auto_reply": False,
    "guest_reply_sent": False,
    "solicit_reviews": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "anon_fail_closed": True,
    "owner_or_staff_read": True,
    "invented_permission_grant": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "provenance_required": True,
}


class ReputationObserveError(ValueError):
    """Fail closed. Does not invent a rating, a scrape, or a guest reply."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act in {"observe", "record"}:
        return PERM_OBSERVE
    return PERM_READ


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_observation_id() -> str:
    return f"OBS-{uuid.uuid4()}"


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise ReputationObserveError(
            "reputation observe refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise ReputationObserveError(
            "reputation observe refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise ReputationObserveError(
            "reputation observe refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.resolve().relative_to(tmp)
    except ValueError as exc:
        raise ReputationObserveError(
            "reputation observe refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _resolve_db(db_path: Path | str | None) -> Path:
    if db_path is not None:
        path = Path(db_path)
    else:
        override = (os.environ.get("WOLF_BZG_REPUTATION_DB") or "").strip()
        path = Path(override) if override else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    if resolved.name == "content_library.sqlite":
        raise ReputationObserveError(
            "reputation observe does not write the catalog",
            code="not_beta",
        )
    return resolved


def assert_db_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_BZG_REPUTATION") or "").strip() == "1":
        return
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise ReputationObserveError(
            "test mode refuses writes to the live reputation DB; "
            "point db_path at a temp file",
            code="live_guard",
        )


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-BZG-07. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    return state or "UNKNOWN"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-d1aacda59180eba7. Does not upsert, resolve, or harvest."""
    out: dict[str, Any] = {
        "cr_id": CR_ID,
        "cr_bound": True,
        "cr_present": False,
        "cr_state": None,
        "cr_blocker": None,
        "cr_capability": CAP_ID,
        "cr_title": None,
        "cr_next_action": None,
        "cr_resolved": False,
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return out
    _assert_beta_path(path.resolve())
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            """
            SELECT state, blocker_class, capability, title, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (CR_ID,),
        ).fetchone()
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    if row is None:
        return out
    out["cr_present"] = True
    out["cr_state"] = row[0]
    out["cr_blocker"] = row[1]
    out["cr_capability"] = row[2] or CAP_ID
    out["cr_title"] = row[3]
    out["cr_next_action"] = row[4]
    out["cr_resolved"] = row[0] == "RESOLVED"
    return out


def honesty_flags(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    state = ledger_cap_state(ledger_path)
    ceiling = state if state in HIGHER_THAN_BUILT else "BUILT"
    flags = dict(HONESTY)
    flags["configured_sources"] = []
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["source_connected"] = False
    flags["source_present"] = False
    flags["summary_rating"] = None
    flags["five_star_invented"] = False
    flags["rating_defaulted"] = False
    flags["scraped"] = False
    flags["auto_reply"] = False
    flags["guest_reply_sent"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    return flags


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    raise ReputationObserveError(
        "CR resolve is refused. This slice does not close CR-d1aacda59180eba7.",
        code="cr_resolve_refused",
    )


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    raise ReputationObserveError(
        "PROVEN is not invented by this slice.",
        code="invented_proven",
    )


def invent_five_star(*_args: Any, **_kwargs: Any) -> None:
    raise ReputationObserveError(
        "A 5-star rating is not invented when no source supplied one.",
        code="invented_five_star",
    )


def scrape(_body: dict | None = None) -> None:
    raise ReputationObserveError(
        "Scraping reviews is refused. This slice does not fetch Google, TripAdvisor, or any other listing.",
        code="scrape_refused",
    )


def reply_to_guest(_body: dict | None = None) -> None:
    raise ReputationObserveError(
        "Auto-reply to guests is refused. This slice does not send a review response.",
        code="auto_reply_refused",
    )


def refuse_summary(_body: dict | None = None) -> None:
    raise ReputationObserveError(
        "A reputation summary cannot be posted. There is no connected source and no invented rating.",
        code="summary_refused",
    )


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bzg_reputation_observations (
  observation_id TEXT PRIMARY KEY,
  venue_id TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  observed_rating REAL NULL,
  rating_scale TEXT NULL,
  excerpt TEXT NULL,
  observed_by TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  provenance TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bzg_reputation_venue
  ON bzg_reputation_observations(venue_id, observed_at);

CREATE TRIGGER IF NOT EXISTS trg_bzg_reputation_no_update
BEFORE UPDATE ON bzg_reputation_observations
BEGIN
  SELECT RAISE(ABORT, 'bzg_reputation_observations is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_bzg_reputation_no_delete
BEFORE DELETE ON bzg_reputation_observations
BEGIN
  SELECT RAISE(ABORT, 'bzg_reputation_observations is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def _require_actor(person_id: str | None, *, role_allowed: bool) -> str:
    pid = (person_id or "").strip()
    if not pid:
        raise ReputationObserveError("anonymous callers are refused", code="denied")
    if pid == OWNER_PERSON:
        return "owner"
    if role_allowed is True and _PERSON_RE.match(pid):
        return "staff"
    raise ReputationObserveError(
        "reputation observe is Owner (PERS-MATT) or an authorised staff role only",
        code="denied",
    )


def _looks_like_reply(body: dict) -> bool:
    low = {str(k).lower() for k in body}
    return bool(low & REPLY_KEYS)


def _looks_like_scrape(body: dict) -> bool:
    low = {str(k).lower() for k in body}
    if low & SCRAPE_KEYS:
        return True
    kind = body.get("source_kind")
    if isinstance(kind, str) and kind.strip().upper() not in {"", SOURCE_KIND}:
        token = kind.strip().upper()
        if "SCRAPE" in token or token in {"SERP", "GOOGLE", "TRIPADVISOR", "FAKE"}:
            return True
    return False


def _reject_keys(body: dict) -> None:
    if not isinstance(body, dict):
        raise ReputationObserveError("payload must be an object", code="invalid")
    if _looks_like_reply(body):
        reply_to_guest(body)
    if _looks_like_scrape(body):
        scrape(body)
    banned = sorted(set(body) & BANNED_KEYS)
    if banned:
        if any(k in {"stars", "star", "five_star", "rating", "summary_rating"} for k in banned):
            invent_five_star()
        raise ReputationObserveError(
            "refused field " + ",".join(banned) + "; a client cannot mark PROVEN or a score",
            code="refused_field",
        )
    extra = sorted(set(body) - OBSERVE_KEYS)
    if extra:
        raise ReputationObserveError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


def _clean_text(value: Any, *, field: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise ReputationObserveError(f"{field} must be a string", code="invalid")
    text = value.strip()
    if len(text) < min_len or len(text) > max_len:
        raise ReputationObserveError(
            f"{field} length must be {min_len}..{max_len}",
            code="invalid",
        )
    if text.upper() in MATURITY_WORDS:
        raise ReputationObserveError(
            f"{field} cannot be a maturity word",
            code="invented_proven",
        )
    if _SECRET_RE.search(text):
        raise ReputationObserveError(f"{field} looks like a secret", code="invalid")
    if _SCRAPE_TEXT_RE.search(text):
        scrape({"source_ref": text})
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise ReputationObserveError(f"{field} has a control character", code="invalid")
    return text


def _venue(value: Any) -> str:
    token = _clean_text(value, field="venue_id", min_len=3, max_len=12).upper()
    if token not in VENUES:
        raise ReputationObserveError(
            "Unknown venue. This slice does not invent a venue.",
            code="invalid_venue",
        )
    return token


def _source_ref(value: Any) -> str:
    text = _clean_text(value, field="source_ref", min_len=8, max_len=240)
    if text.lower() in EMPTY_SOURCE:
        raise ReputationObserveError(
            "No review source was supplied. Nothing was stored and no rating was invented.",
            code="no_source",
        )
    return text


def _optional_rating(body: dict) -> tuple[float | None, str | None]:
    if "observed_rating" not in body or body.get("observed_rating") is None:
        if body.get("rating_scale") not in (None, ""):
            raise ReputationObserveError(
                "rating_scale without an observed rating is refused",
                code="invented_five_star",
            )
        return None, None
    raw = body.get("observed_rating")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ReputationObserveError(
            "observed_rating must be a number the caller already saw",
            code="invalid",
        )
    if raw < 1 or raw > 5:
        raise ReputationObserveError(
            "observed_rating must be between 1 and 5",
            code="invalid",
        )
    doubled = raw * 2
    if abs(doubled - round(doubled)) > 1e-9:
        raise ReputationObserveError(
            "observed_rating must be a half-step the caller already saw",
            code="invalid",
        )
    scale = body.get("rating_scale")
    if scale != "1-5":
        raise ReputationObserveError(
            "rating_scale must be 1-5 when an observed rating is supplied",
            code="invalid",
        )
    return float(raw), "1-5"


def _excerpt(body: dict) -> str | None:
    if "excerpt" not in body or body.get("excerpt") is None:
        return None
    return _clean_text(body.get("excerpt"), field="excerpt", min_len=1, max_len=400)


def _observation_id(value: Any) -> str:
    token = (value if isinstance(value, str) else "").strip()
    if not _OBS_RE.match(token):
        raise ReputationObserveError(
            "That id is not a stored observation.",
            code="not_an_observation",
        )
    return token


def _open_write(db_path: Path | str | None) -> tuple[sqlite3.Connection, Path]:
    resolved = _resolve_db(db_path)
    assert_db_writable(resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn, resolved


def _open_read(db_path: Path | str | None) -> tuple[sqlite3.Connection | None, Path]:
    resolved = _resolve_db(db_path)
    if not resolved.is_file():
        return None, resolved
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn, resolved


def _public_observation(row: sqlite3.Row) -> dict[str, Any]:
    rating = row["observed_rating"]
    return {
        "observation_id": row["observation_id"],
        "venue_id": row["venue_id"],
        "source_kind": row["source_kind"],
        "source_ref": row["source_ref"],
        "observed_rating": None if rating is None else float(rating),
        "rating_scale": row["rating_scale"],
        "excerpt": row["excerpt"],
        "observed_by": row["observed_by"],
        "observed_at": row["observed_at"],
        "provenance": row["provenance"],
        "source_connected": False,
        "summary_rating": None,
        "five_star_invented": False,
        "rating_defaulted": False,
        "scraped": False,
        "auto_reply": False,
        "guest_reply_sent": False,
    }


def _empty_payload(*, gate: str) -> dict[str, Any]:
    flags = honesty_flags()
    return {
        "ok": True,
        "gate": gate,
        "count": 0,
        "observations": [],
        "source_connected": False,
        "source_present": False,
        "configured_sources": [],
        "summary_rating": None,
        "five_star_invented": False,
        "rating_defaulted": False,
        "scraped": False,
        "auto_reply": False,
        "guest_reply_sent": False,
        "empty_because": "no_source_connected",
        "message": EMPTY_NOTE,
        "honesty": flags,
        **{k: flags[k] for k in ("ledger_maturity", "maturity_ceiling", "cr_id", "cr_state", "proven")},
    }


def list_observations(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    venue: str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read stored observations. Does not scrape. Does not invent a rating."""
    gate = _require_actor(person_id, role_allowed=role_allowed)
    venue_token = None
    if venue not in (None, ""):
        venue_token = _venue(venue)
    elif gate != "owner":
        raise ReputationObserveError(
            "Staff must name a venue. This slice does not dump every review.",
            code="missing_scope",
        )
    conn, _path = _open_read(db_path)
    if conn is None:
        return _empty_payload(gate=gate)
    try:
        if venue_token:
            rows = conn.execute(
                """
                SELECT observation_id, venue_id, source_kind, source_ref,
                       observed_rating, rating_scale, excerpt, observed_by,
                       observed_at, provenance
                FROM bzg_reputation_observations
                WHERE venue_id=?
                ORDER BY observed_at, observation_id
                """,
                (venue_token,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT observation_id, venue_id, source_kind, source_ref,
                       observed_rating, rating_scale, excerpt, observed_by,
                       observed_at, provenance
                FROM bzg_reputation_observations
                ORDER BY observed_at, observation_id
                """
            ).fetchall()
    finally:
        conn.close()
    items = [_public_observation(r) for r in rows]
    flags = honesty_flags()
    if not items:
        out = _empty_payload(gate=gate)
        out["venue_id"] = venue_token
        return out
    return {
        "ok": True,
        "gate": gate,
        "count": len(items),
        "observations": items,
        "venue_id": venue_token,
        "source_connected": False,
        "source_present": False,
        "configured_sources": [],
        "summary_rating": None,
        "five_star_invented": False,
        "rating_defaulted": False,
        "scraped": False,
        "auto_reply": False,
        "guest_reply_sent": False,
        "empty_because": None,
        "message": "Stored provenance only. No source is connected and no summary rating was computed.",
        "honesty": flags,
        "ledger_maturity": flags["ledger_maturity"],
        "maturity_ceiling": flags["maturity_ceiling"],
        "cr_id": flags["cr_id"],
        "cr_state": flags["cr_state"],
        "proven": flags["proven"],
    }


def read_observation(
    observation_id: str,
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    oid = _observation_id(observation_id)
    conn, _path = _open_read(db_path)
    if conn is None:
        raise ReputationObserveError(
            "No observation store exists. No rating was invented.",
            code="not_an_observation",
        )
    try:
        row = conn.execute(
            """
            SELECT observation_id, venue_id, source_kind, source_ref,
                   observed_rating, rating_scale, excerpt, observed_by,
                   observed_at, provenance
            FROM bzg_reputation_observations
            WHERE observation_id=?
            """,
            (oid,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ReputationObserveError(
            "No observation with that id. No rating was invented.",
            code="not_an_observation",
        )
    item = _public_observation(row)
    flags = honesty_flags()
    return {
        "ok": True,
        "gate": gate,
        "observation": item,
        "source_connected": False,
        "summary_rating": None,
        "five_star_invented": False,
        "honesty": flags,
        "ledger_maturity": flags["ledger_maturity"],
        "maturity_ceiling": flags["maturity_ceiling"],
        "cr_state": flags["cr_state"],
    }


def record_observation(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Store one observation with provenance. Does not scrape or reply."""
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body)
    venue = _venue(body.get("venue_id"))
    kind = body.get("source_kind")
    if not isinstance(kind, str) or kind.strip().upper() != SOURCE_KIND:
        if isinstance(kind, str) and (
            "SCRAPE" in kind.upper() or kind.strip().upper() in {"SERP", "GOOGLE", "TRIPADVISOR", "FAKE"}
        ):
            scrape(body)
        raise ReputationObserveError(
            "source_kind must be OWNER_RECORD. This slice does not connect a review source.",
            code="no_source",
        )
    if "source_ref" not in body or not str(body.get("source_ref") or "").strip():
        raise ReputationObserveError(
            "No review source was supplied. Nothing was stored and no rating was invented.",
            code="no_source",
        )
    source_ref = _source_ref(body.get("source_ref"))
    provenance = _clean_text(body.get("provenance"), field="provenance", min_len=12, max_len=500)
    rating, scale = _optional_rating(body)
    excerpt = _excerpt(body)
    oid = mint_observation_id()
    observed_at = now_utc_iso()
    conn, _path = _open_write(db_path)
    try:
        conn.execute(
            """
            INSERT INTO bzg_reputation_observations (
              observation_id, venue_id, source_kind, source_ref,
              observed_rating, rating_scale, excerpt, observed_by,
              observed_at, provenance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                oid,
                venue,
                SOURCE_KIND,
                source_ref,
                rating,
                scale,
                excerpt,
                person_id,
                observed_at,
                provenance,
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT observation_id, venue_id, source_kind, source_ref,
                   observed_rating, rating_scale, excerpt, observed_by,
                   observed_at, provenance
            FROM bzg_reputation_observations
            WHERE observation_id=?
            """,
            (oid,),
        ).fetchone()
    finally:
        conn.close()
    item = _public_observation(row)
    flags = honesty_flags()
    return {
        "ok": True,
        "gate": gate,
        "stored": True,
        "provenance_stored": True,
        "observation": item,
        "observed_rating": item["observed_rating"],
        "summary_rating": None,
        "five_star_invented": False,
        "rating_defaulted": False,
        "source_connected": False,
        "scraped": False,
        "auto_reply": False,
        "guest_reply_sent": False,
        "honesty": flags,
        "ledger_maturity": flags["ledger_maturity"],
        "maturity_ceiling": flags["maturity_ceiling"],
        "cr_state": flags["cr_state"],
        "proven": False if flags["ledger_maturity"] != "PROVEN" else True,
    }
