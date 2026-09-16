#!/usr/bin/env python3
"""Sync Metricool READ analytics into Beta performance_records (idempotent upsert).

No Metricool write. Join brands via brand_external_ids (blogId), not label strings.
Timezone: published_at_utc stored UTC; display/planning day Asia/Makassar.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metricool_read_client import (  # noqa: E402
    MetricoolReadError,
    analytics_all_content,
    window_days_range,
)
from wolf_intelligence import db_connect, now_iso  # noqa: E402

TZ = ZoneInfo("Asia/Makassar")
EXTERNAL_SYSTEM = "metricool"


def resolve_blog_id(conn, brand_key: str) -> str | None:
    row = conn.execute(
        """
        SELECT external_id FROM brand_external_ids
        WHERE brand_key=? AND external_system=? AND status='ACTIVE'
        LIMIT 1
        """,
        (brand_key, EXTERNAL_SYSTEM),
    ).fetchone()
    return str(row["external_id"]) if row else None


def _num(*vals) -> float | None:
    for v in vals:
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, dict):
            iv = v.get("value")
            if isinstance(iv, (int, float)):
                return float(iv)
        if isinstance(v, str):
            s = v.strip().replace(",", "")
            try:
                return float(s)
            except Exception:
                continue
    return None


def _published_at_raw(post: dict) -> tuple[str | None, str | None]:
    tz_name = None
    v = post.get("publishedAt")
    if isinstance(v, dict):
        tz_name = v.get("timezone")
        v = v.get("dateTime")
    if not v:
        v = post.get("publishDate") or post.get("date") or post.get("published_at")
        tz_name = None
    return (str(v) if v else None, tz_name)


def to_published_at_utc(post: dict) -> str | None:
    """Parse Metricool publish time → UTC ISO. Never invent."""
    raw, tz_name = _published_at_raw(post)
    if not raw:
        return None
    s = str(raw).strip()
    # Common shapes: 2026-09-01T10:00:00 or with offset
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        elif re.search(r"[+-]\d{2}:\d{2}$", s):
            dt = datetime.fromisoformat(s)
        else:
            # Naive — Metricool profiles use Asia/Makassar
            zone = ZoneInfo(tz_name) if tz_name else TZ
            dt = datetime.fromisoformat(s).replace(tzinfo=zone)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except Exception:
        return None


def _caption(post: dict) -> str | None:
    for k in ("content", "text", "caption", "message", "description", "title"):
        v = post.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()[:4000]
    return None


def _permalink(post: dict) -> str | None:
    for k in ("url", "permalink", "link", "postUrl"):
        v = post.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def normalise_row(
    post: dict,
    *,
    brand_key: str,
    blog_id: str,
    network: str,
    surface: str,
    dual_count_risk: int = 0,
) -> dict | None:
    pid = post.get("postId") or post.get("id") or post.get("post_id")
    if pid in (None, ""):
        return None
    rate = _num(post.get("engagement"))
    count = _num(post.get("interactions"))
    if count is None and rate is None:
        parts = [_num(post.get(k)) for k in ("likes", "comments", "shares", "saved", "saves")]
        parts = [p for p in parts if p is not None]
        count = sum(parts) if parts else None
    pub_utc = to_published_at_utc(post)
    caption = _caption(post)
    permalink = _permalink(post)
    blob = json.dumps(
        {
            "pid": str(pid),
            "network": network,
            "surface": surface,
            "published_at_utc": pub_utc,
            "reach": _num(post.get("reach")),
            "engagement": count,
        },
        sort_keys=True,
    )
    ch = hashlib.sha256(blob.encode()).hexdigest()[:16]
    raw_ref = hashlib.sha256(
        json.dumps(post, sort_keys=True, default=str).encode()
    ).hexdigest()[:24]
    return {
        "brand_key": brand_key,
        "external_system": EXTERNAL_SYSTEM,
        "external_profile_id": str(blog_id),
        "network": network,
        "surface": surface,
        "external_post_id": str(pid),
        "permalink": permalink,
        "published_at_utc": pub_utc,
        "content_type": post.get("type") or post.get("publishType"),
        "caption": caption,
        "reach": _num(post.get("reach")),
        "impressions": _num(post.get("impressionsTotal"), post.get("impressions")),
        "views": _num(post.get("views"), post.get("plays")),
        "likes": _num(post.get("likes"), post.get("reactions")),
        "comments": _num(post.get("comments")),
        "shares": _num(post.get("shares")),
        "saves": _num(post.get("saved"), post.get("saves")),
        "engagement": count,
        "engagement_rate_pct": rate,
        "fetched_at": now_iso(),
        "data_lane": "operational",
        "dual_count_risk": dual_count_risk,
        "content_hash": ch,
        "raw_ref": raw_ref,
    }


def upsert_performance(conn, row: dict) -> str:
    """Idempotent upsert. Returns 'insert' | 'update'."""
    existing = conn.execute(
        """
        SELECT id FROM performance_records
        WHERE external_profile_id=? AND network=? AND surface=? AND external_post_id=?
        """,
        (
            row["external_profile_id"],
            row["network"],
            row["surface"],
            row["external_post_id"],
        ),
    ).fetchone()
    cols = [
        "brand_key", "external_system", "external_profile_id", "network", "surface",
        "external_post_id", "permalink", "published_at_utc", "content_type", "caption",
        "reach", "impressions", "views", "likes", "comments", "shares", "saves",
        "engagement", "engagement_rate_pct", "fetched_at", "data_lane",
        "dual_count_risk", "content_hash", "raw_ref",
    ]
    vals = [row.get(c) for c in cols]
    if existing:
        sets = ", ".join(f"{c}=?" for c in cols if c not in ("external_profile_id", "network", "surface", "external_post_id"))
        upd_cols = [c for c in cols if c not in ("external_profile_id", "network", "surface", "external_post_id")]
        conn.execute(
            f"UPDATE performance_records SET {sets} WHERE id=?",
            [row.get(c) for c in upd_cols] + [existing["id"]],
        )
        return "update"
    conn.execute(
        f"INSERT INTO performance_records ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
        vals,
    )
    return "insert"


def _dedupe_reels_against_posts(posts: list, reels: list) -> tuple[list, list, int]:
    """If same postId appears in both posts and reels, keep reel surface only; flag dual_count_risk."""
    post_ids = set()
    for p in posts:
        pid = p.get("postId") or p.get("id") or p.get("post_id")
        if pid is not None:
            post_ids.add(str(pid))
    dual = 0
    cleaned_posts = []
    reel_ids = set()
    for r in reels:
        pid = r.get("postId") or r.get("id") or r.get("post_id")
        if pid is not None:
            reel_ids.add(str(pid))
    for p in posts:
        pid = p.get("postId") or p.get("id") or p.get("post_id")
        if pid is not None and str(pid) in reel_ids:
            dual += 1
            continue  # conservative: drop post duplicate; keep reel
        cleaned_posts.append(p)
    return cleaned_posts, reels, dual


def sync_metricool_performance(
    brand_key: str = "habitat",
    window_days: int = 60,
    network: str = "instagram",
    *,
    conn=None,
) -> dict[str, Any]:
    """Pull READ-only analytics and upsert. Soft-fails with ok=False if API down."""
    own = conn is None
    c = conn or db_connect()
    report: dict[str, Any] = {
        "ok": False,
        "brand_key": brand_key,
        "window_days": window_days,
        "network": network,
        "blog_id": None,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "by_surface": {"post": 0, "reel": 0, "story": 0},
        "dual_count_flags": 0,
        "errors": [],
        "oldest_published_at_utc": None,
        "newest_published_at_utc": None,
    }
    try:
        blog_id = resolve_blog_id(c, brand_key)
        if not blog_id:
            report["errors"].append(f"No brand_external_ids mapping for {brand_key}/metricool")
            return report
        report["blog_id"] = blog_id
        start, end = window_days_range(window_days)
        report["window_start"] = start
        report["window_end"] = end
        try:
            bundle = analytics_all_content(blog_id, network=network, start=start, end=end)
        except MetricoolReadError as exc:
            report["errors"].append(str(exc))
            return report
        for surf, err in (bundle.get("_errors") or {}).items():
            report["errors"].append(f"{surf}: {err}")

        posts, reels, dual_n = _dedupe_reels_against_posts(
            list(bundle.get("posts") or []),
            list(bundle.get("reels") or []),
        )
        report["dual_count_flags"] = dual_n
        stories = list(bundle.get("stories") or [])

        pub_dates: list[str] = []
        for surface, rows, risk in (
            ("post", posts, 0),
            ("reel", reels, 1 if dual_n else 0),
            ("story", stories, 0),
        ):
            for post in rows:
                # Flag individual reels that collided
                dcr = risk
                if surface == "reel" and dual_n:
                    dcr = 1
                row = normalise_row(
                    post,
                    brand_key=brand_key,
                    blog_id=blog_id,
                    network=network,
                    surface=surface,
                    dual_count_risk=dcr,
                )
                if not row:
                    report["skipped"] += 1
                    continue
                action = upsert_performance(c, row)
                if action == "insert":
                    report["inserted"] += 1
                else:
                    report["updated"] += 1
                report["by_surface"][surface] = report["by_surface"].get(surface, 0) + 1
                if row.get("published_at_utc"):
                    pub_dates.append(row["published_at_utc"])

        if pub_dates:
            report["oldest_published_at_utc"] = min(pub_dates)
            report["newest_published_at_utc"] = max(pub_dates)
        if own:
            c.commit()
        report["ok"] = True
        report["total_upserted"] = report["inserted"] + report["updated"]
        return report
    finally:
        if own:
            c.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Metricool READ → Beta performance_records")
    ap.add_argument("--brand", default="habitat")
    ap.add_argument("--window-days", type=int, default=60)
    ap.add_argument("--network", default="instagram")
    args = ap.parse_args()
    report = sync_metricool_performance(
        brand_key=args.brand,
        window_days=args.window_days,
        network=args.network,
    )
    # Never print secrets; report is counts only
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
