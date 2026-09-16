"""Phase 2.6 Team Readiness helpers — Beta OS only. No :8787 / Metricool write / publish."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

REVIEW_LABELS = {
    "APPROVED": "APPROVED",
    "CHANGES_PENDING_REVIEW": "CHANGES PENDING REVIEW",
    "WORKING": "WORKING",
}

POST_TYPES = ("Reel·30sec", "Carousel·6 slides", "Static")
STORY_CTA = (
    "NONE", "LINK STICKER", "POLL", "QUESTION", "QUIZ", "REACTION", "DM", "OTHER",
)

READINESS_LABELS = {
    "READY_TO_USE": "READY TO USE",
    "CHECKING": "CHECKING",
    "FAILED": "FAILED",
}


def review_label(plan: dict | None) -> str:
    if not plan:
        return "WORKING"
    rs = (plan.get("review_state") or "").strip().upper()
    if rs in REVIEW_LABELS:
        return REVIEW_LABELS[rs]
    st = str(plan.get("status") or "")
    if st in ("Human_Approved", "HUMAN_APPROVED", "Approved"):
        return "APPROVED"
    return "WORKING"


def parse_detail_tags(detail: str | None) -> list[str]:
    """Detail ≥1 meaningful slug tokens → structured tags array."""
    raw = (detail or "").strip().lower()
    if not raw:
        return []
    parts = re.split(r"[\s,;/|]+", raw)
    tags = []
    for p in parts:
        t = re.sub(r"[^a-z0-9\-]+", "-", p).strip("-")
        if t and len(t) >= 2:
            tags.append(t)
    return tags


def detail_valid(detail: str | None) -> bool:
    return len(parse_detail_tags(detail)) >= 1


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_duplicates(conn, *, content_hash: str | None, file_size: int | None,
                    original_filename: str | None, canonical_filename: str | None,
                    data_lane: str = "operational") -> list[dict]:
    """Warn-level duplicate hits by hash/size/original/canonical (same lane)."""
    hits: list[dict] = []
    seen = set()
    queries = []
    if content_hash:
        queries.append(("content_hash", content_hash))
    if canonical_filename:
        queries.append(("canonical_filename", canonical_filename))
    if original_filename:
        queries.append(("original_filename", original_filename))
    for col, val in queries:
        rows = conn.execute(
            f"""
            SELECT id, brand, canonical_filename, original_filename, file_size, content_hash,
                   shoot_date, subject, library_status, readiness, data_lane
            FROM assets
            WHERE {col}=? AND ifnull(data_lane,'operational')=?
            ORDER BY id DESC LIMIT 5
            """,
            (val, data_lane),
        ).fetchall()
        for r in rows:
            d = dict(r)
            if d["id"] in seen:
                continue
            # size soft-match when hash unknown
            if file_size and d.get("file_size") and int(d["file_size"]) == int(file_size):
                d["match_reason"] = col + "+size"
            else:
                d["match_reason"] = col
            seen.add(d["id"])
            # never leak paths
            d.pop("original_path", None)
            d.pop("v2_path", None)
            hits.append(d)
    if file_size and content_hash is None:
        rows = conn.execute(
            """
            SELECT id, brand, canonical_filename, original_filename, file_size, content_hash,
                   shoot_date, subject, library_status, readiness, data_lane
            FROM assets
            WHERE file_size=? AND ifnull(data_lane,'operational')=?
            ORDER BY id DESC LIMIT 5
            """,
            (int(file_size), data_lane),
        ).fetchall()
        for r in rows:
            d = dict(r)
            if d["id"] in seen:
                continue
            d["match_reason"] = "size"
            seen.add(d["id"])
            hits.append(d)
    return hits


def brand_theme_payload(row: dict | None) -> dict:
    if not row:
        return {
            "primary": "#6ea8ff",
            "accent": "#8b7cff",
            "neutral": "#8b95a8",
            "font": "Inter, SF Pro Text, system-ui, sans-serif",
            "logo_text": "",
            "logo_url": "",
            "default_assignee": "",
        }
    theme: dict[str, Any] = {}
    try:
        theme = json.loads(row.get("theme_json") or "{}") or {}
    except (TypeError, json.JSONDecodeError):
        theme = {}
    return {
        "primary": theme.get("primary") or "#6ea8ff",
        "accent": theme.get("accent") or "#8b7cff",
        "neutral": theme.get("neutral") or "#8b95a8",
        "font": theme.get("font") or "Inter, SF Pro Text, system-ui, sans-serif",
        "logo_text": theme.get("logo_text") or row.get("display_name") or row.get("id") or "",
        "logo_url": row.get("logo_url") or theme.get("logo_url") or "",
        "default_assignee": row.get("default_assignee") or "",
    }


def readiness_from_row(row: dict) -> tuple[str, str]:
    r = (row.get("readiness") or "").strip().upper()
    if r in READINESS_LABELS:
        note = row.get("readiness_note") or {
            "READY_TO_USE": "Verified in Beta library and ready for team use.",
            "CHECKING": "Upload received; still checking integrity.",
            "FAILED": "Processing failed — re-upload or retry.",
        }.get(r, "")
        return r, note
    lib = (row.get("library_status") or row.get("status") or "").upper()
    if lib in ("LIBRARY_READY", "READY", "VERIFIED"):
        return "READY_TO_USE", "Verified in Beta library and ready for team use."
    if lib in ("FAILED",):
        return "FAILED", row.get("readiness_note") or "Processing failed — re-upload or retry."
    return "CHECKING", "Upload received; still checking integrity."


def map_post_type(body: dict) -> str:
    pt = (body.get("post_type") or "").strip()
    if pt in POST_TYPES:
        return pt
    fmt = (body.get("format") or body.get("platform") or body.get("content_type") or "").lower()
    if "carousel" in fmt or "slide" in fmt:
        return "Carousel·6 slides"
    if "static" in fmt or "feed" in fmt and "reel" not in fmt:
        return "Static"
    if "reel" in fmt or "ig_reels" in fmt or "reels" in fmt:
        return "Reel·30sec"
    return "Reel·30sec"


def content_breakdown_from_body(body: dict, kind: str) -> list[dict]:
    """Carousel slides or reel scenes: text overlay + visual suggestion."""
    bd = body.get("content_breakdown") or body.get("story_breakdown")
    if isinstance(bd, list) and bd:
        out = []
        for i, item in enumerate(bd, 1):
            if isinstance(item, dict):
                out.append({
                    "n": item.get("n") or i,
                    "text_overlay": item.get("text_overlay") or item.get("text") or item.get("overlay") or "",
                    "visual": item.get("visual") or item.get("visual_suggestion") or item.get("scene") or "",
                    "timing": item.get("timing") or "",
                })
            else:
                out.append({"n": i, "text_overlay": str(item), "visual": "", "timing": ""})
        return out
    # derive from overlays / shot_list / scene
    overlays = body.get("text_overlays") or []
    if isinstance(overlays, str):
        overlays = [s.strip() for s in overlays.split("\n") if s.strip()]
    shots = body.get("shot_list") or body.get("recommended_shot_list") or []
    if isinstance(shots, str):
        shots = [s.strip() for s in shots.split("\n") if s.strip()]
    scene = body.get("scene") or body.get("slide") or ""
    if overlays or shots or scene:
        n = max(len(overlays), len(shots), 1 if scene else 0)
        out = []
        for i in range(n):
            out.append({
                "n": i + 1,
                "text_overlay": overlays[i] if i < len(overlays) else (scene if i == 0 else ""),
                "visual": shots[i] if i < len(shots) else "",
                "timing": "",
            })
        return out
    return []


WI_QUICK_ACTIONS = [
    ("REFINE", "Refine this brief"),
    ("HOOK", "Stronger hook"),
    ("FOOTAGE", "Footage ideas"),
    ("CTA", "CTA options"),
    ("SHORTEN_CAPTION", "Shorten caption"),
    ("ANOTHER_IDEA", "Another idea"),
    ("BRAND_FIT", "Brand fit check"),
    ("SIMILAR", "Similar past posts"),
    ("PERFORMED_WELL", "What performed well"),
    ("INSPIRATION", "Inspiration"),
]


def wi_unavailable_reply(action: str) -> dict:
    return {
        "ok": True,
        "connected": False,
        "action": action,
        "message": (
            "Wolf Intelligence chat shell is ready, but live generation is not connected "
            "in this phase. No internet/NAS fabrication. APPLY TO PLAN is not available yet."
        ),
        "can_apply_to_plan": False,
    }
