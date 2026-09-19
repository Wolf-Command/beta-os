#!/usr/bin/env python3
"""CAP-GGV-05 governed DERIVE views (Beta only).

Decision served: 2026-09-19 FIX, social DERIVE views on Beta only
(docs/deliveries/GROK-PLAN-GGV-SOCIAL-DERIVE-VIEWS-2026-09-19.md).

Wolf reads Metricool numbers already stored in performance_records for a
brand that has an ACTIVE metricool mapping. It does not call Metricool,
write Metricool, publish, or spend on ads.

NULL is not zero. Surfaces are not blended into one score. A metric that
is not in the store is named as missing. It is not invented.

Honesty is bound to CR-e20099e21930b9a6. The ledger is read, not written.
Maturity ceiling is BUILT unless the ledger row is already PROVEN or READY.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-e20099e21930b9a6"
CAP_ID = "CAP-GGV-05"
PERM_READ = "ggv.social.read"

HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
SURFACES = ("post", "reel", "story")
STORED_METRICS = (
    "reach",
    "impressions",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "engagement",
    "engagement_rate_pct",
)
NOT_IN_STORE = (
    "clicks",
    "conversions",
    "followers",
    "paid_ads_spend",
    "roas",
    "cpc",
    "cpm",
)

_BRAND_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
_PERSON_RE = re.compile(r"^PERS-[A-Z0-9][A-Z0-9-]{0,40}$")

WRITE_KEYS = frozenset(
    {
        "publish",
        "metricool_write",
        "metricool",
        "sync",
        "post_now",
        "schedule",
    }
)
ADS_KEYS = frozenset(
    {
        "spend",
        "ad_spend",
        "ads_spend",
        "paid_ads",
        "paid_ads_spend",
        "budget",
        "boost",
        "promote",
        "roas",
        "cpc",
        "cpm",
        "campaign",
    }
)
INVENT_KEYS = frozenset(
    {
        "reach",
        "impressions",
        "views",
        "likes",
        "comments",
        "shares",
        "saves",
        "engagement",
        "engagement_rate",
        "engagement_rate_pct",
        "clicks",
        "conversions",
        "followers",
        "blended_score",
        "score",
        "proven",
        "ready",
        "maturity",
    }
)

EMPTY_NOTE = (
    "No authorised Metricool-read rows for this brand. "
    "Missing numbers stay missing. Wolf does not write Metricool and does not spend on ads."
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "ggv_social_derive_views",
    "metricool_called": False,
    "metricool_write": False,
    "invented_metrics": False,
    "paid_ads_spend": None,
    "paid_ads_called": False,
    "ads_spend_invented": False,
    "blended_score": None,
    "surfaces_blended": False,
    "null_is_not_zero": True,
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
}


class SocialDeriveError(ValueError):
    """Fail closed. Does not invent a metric, a write, or ad spend."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def permission_for(_action: str = "read") -> str:
    return PERM_READ


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise SocialDeriveError(
            "social derive refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise SocialDeriveError(
            "social derive refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise SocialDeriveError(
            "social derive refuses a production path",
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
        raise SocialDeriveError(
            "social derive refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _resolve_catalog(catalog_db: Path | str | None) -> Path:
    if catalog_db is not None:
        path = Path(catalog_db)
    else:
        override = (os.environ.get("WOLF_GGV_SOCIAL_DB") or "").strip()
        path = Path(override) if override else CATALOG_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    return resolved


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-GGV-05. Does not write the ledger."""
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
    """Read CR-e20099e21930b9a6. Does not upsert, resolve, or harvest."""
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
    path = _resolve_catalog(catalog_db) if catalog_db else CATALOG_DB
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
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["metricool_called"] = False
    flags["metricool_write"] = False
    flags["invented_metrics"] = False
    flags["paid_ads_spend"] = None
    flags["paid_ads_called"] = False
    flags["ads_spend_invented"] = False
    flags["blended_score"] = None
    flags["surfaces_blended"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    return flags


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    raise SocialDeriveError(
        "CR resolve is refused. This slice does not close CR-e20099e21930b9a6.",
        code="cr_resolve_refused",
    )


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    raise SocialDeriveError(
        "PROVEN is not invented by this slice.",
        code="invented_proven",
    )


def metricool_write(_body: dict | None = None) -> None:
    raise SocialDeriveError(
        "Metricool write is refused. This slice only reads numbers already stored.",
        code="metricool_write_refused",
    )


def paid_ads(_body: dict | None = None) -> None:
    raise SocialDeriveError(
        "Paid ads spend is refused. This slice does not boost, budget, or buy reach.",
        code="paid_ads_refused",
    )


def invent_metrics(_body: dict | None = None) -> None:
    raise SocialDeriveError(
        "Metrics are not invented. Missing stored numbers stay missing.",
        code="invented_metrics",
    )


def refuse_write(_body: dict | None = None) -> None:
    raise SocialDeriveError(
        "Social derive views are read-only.",
        code="read_only",
    )


def looks_like_metricool_write(body: dict | None) -> bool:
    if not isinstance(body, dict):
        return False
    low = {str(k).lower() for k in body}
    return bool(low & WRITE_KEYS)


def looks_like_ads(body: dict | None) -> bool:
    if not isinstance(body, dict):
        return False
    low = {str(k).lower() for k in body}
    return bool(low & ADS_KEYS)


def looks_like_invented_metric(body: dict | None) -> bool:
    if not isinstance(body, dict):
        return False
    low = {str(k).lower() for k in body}
    return bool(low & INVENT_KEYS)


def _require_actor(person_id: str | None, *, role_allowed: bool) -> str:
    pid = (person_id or "").strip()
    if not pid:
        raise SocialDeriveError("anonymous callers are refused", code="denied")
    if pid == OWNER_PERSON:
        return "owner"
    if role_allowed is True and _PERSON_RE.match(pid):
        return "staff"
    raise SocialDeriveError(
        "social derive is Owner (PERS-MATT) or an authorised staff role only",
        code="denied",
    )


def _median(vals: list[float]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return float(s[mid - 1] + s[mid]) / 2.0


def _quartiles(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"q1": None, "median": None, "q3": None}
    s = sorted(vals)
    n = len(s)
    return {
        "q1": float(s[max(0, n // 4)]),
        "median": _median(s),
        "q3": float(s[min(n - 1, (3 * n) // 4)]),
    }


def _collect(rows: list[dict], field: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            continue
    return out


def _empty_view(
    brand_key: str | None,
    *,
    gate: str,
    authorised: bool,
    missing: list[str],
    note: str,
    catalog_db: Path | str | None,
) -> dict[str, Any]:
    flags = honesty_flags(catalog_db=catalog_db if catalog_db else None)
    return {
        "ok": True,
        "gate": gate,
        "cap": CAP_ID,
        "brand_key": brand_key,
        "authorised": authorised,
        "available": False,
        "source": "performance_records",
        "external_system": "metricool",
        "external_profile_id": None,
        "data_lane": "operational",
        "window_days": None,
        "window_applied": False,
        "metricool_called": False,
        "metricool_write": False,
        "invented_metrics": False,
        "paid_ads_spend": None,
        "paid_ads_called": False,
        "ads_spend_invented": False,
        "blended_score": None,
        "surfaces_blended": False,
        "by_network": {},
        "missing_surfaces": [],
        "missing_information": missing,
        "note": note,
        "assumptions": [
            "Numbers come only from stored Metricool reads on an authorised brand mapping.",
            "NULL is not zero.",
            "Surfaces are not blended into one score.",
            "Clicks, conversions, followers, and paid ads spend are not in this store.",
        ],
        "honesty": flags,
        **{k: flags[k] for k in (
            "ledger_maturity",
            "maturity_ceiling",
            "cr_id",
            "cr_state",
            "cr_resolved",
            "invented_proven",
        )},
    }


def _parse_brand(brand_key: str | None) -> str:
    brand = (brand_key or "").strip().lower()
    if not brand:
        raise SocialDeriveError("brand is required", code="brand_required")
    if not _BRAND_RE.match(brand):
        raise SocialDeriveError("brand is not a governed key", code="invalid_brand")
    return brand


def _parse_window(window_days: int | None) -> int | None:
    if window_days is None:
        return None
    try:
        days = int(window_days)
    except (TypeError, ValueError) as exc:
        raise SocialDeriveError("window_days must be a whole number", code="invalid") from exc
    if days < 1 or days > 366:
        raise SocialDeriveError("window_days must be between 1 and 366", code="invalid")
    return days


def _open_ro(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def derive_view(
    brand_key: str | None,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    catalog_db: Path | str | None = None,
    window_days: int | None = None,
) -> dict[str, Any]:
    """Read-only DERIVE view. Does not insert, update, or call Metricool."""
    gate = _require_actor(person_id, role_allowed=role_allowed)
    try:
        brand = _parse_brand(brand_key)
    except SocialDeriveError:
        if not (brand_key or "").strip():
            return _empty_view(
                None,
                gate=gate,
                authorised=False,
                missing=["brand is required"],
                note=EMPTY_NOTE,
                catalog_db=catalog_db,
            )
        raise
    days = _parse_window(window_days)
    path = _resolve_catalog(catalog_db)
    if not path.is_file():
        return _empty_view(
            brand,
            gate=gate,
            authorised=False,
            missing=["authorised Metricool store is not present"],
            note=EMPTY_NOTE,
            catalog_db=catalog_db,
        )

    conn = _open_ro(path)
    try:
        mappings = conn.execute(
            """
            SELECT external_id
            FROM brand_external_ids
            WHERE brand_key=? AND external_system='metricool' AND status='ACTIVE'
            ORDER BY external_id
            """,
            (brand,),
        ).fetchall()
        if not mappings:
            return _empty_view(
                brand,
                gate=gate,
                authorised=False,
                missing=[
                    "Brand has no ACTIVE Metricool read mapping. Numbers are not shown as zero."
                ],
                note=EMPTY_NOTE,
                catalog_db=catalog_db,
            )
        profile_ids = [str(row["external_id"]) for row in mappings]
        marks = ",".join("?" * len(profile_ids))
        sql = f"""
            SELECT network, surface, reach, impressions, views, likes, comments,
                   shares, saves, engagement, engagement_rate_pct,
                   published_at_utc, dual_count_risk
            FROM performance_records
            WHERE brand_key=?
              AND external_system='metricool'
              AND data_lane='operational'
              AND external_profile_id IN ({marks})
        """
        params: list[Any] = [brand, *profile_ids]
        if days is not None:
            sql += """
              AND published_at_utc IS NOT NULL
              AND date(published_at_utc) >= date('now', ?)
            """
            params.append(f"-{days} days")
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        undated = 0
        if days is not None:
            undated = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*) FROM performance_records
                    WHERE brand_key=? AND external_system='metricool'
                      AND data_lane='operational'
                      AND external_profile_id IN ({marks})
                      AND published_at_utc IS NULL
                    """,
                    (brand, *profile_ids),
                ).fetchone()[0]
            )
    finally:
        conn.close()

    missing: list[str] = [
        "clicks, conversions, followers, and paid ads spend are not in the authorised store"
    ]
    if days is not None and undated:
        missing.append(
            f"{undated} stored rows have no published_at and were left out of the window"
        )
    if not rows:
        missing.insert(0, "No operational Metricool-read rows for this authorised brand")
        view = _empty_view(
            brand,
            gate=gate,
            authorised=True,
            missing=missing,
            note="Authorised mapping exists. Stored performance is absent, not zero.",
            catalog_db=catalog_db,
        )
        view["external_profile_id"] = profile_ids[0] if len(profile_ids) == 1 else None
        view["external_profile_ids"] = profile_ids
        view["window_days"] = days
        view["window_applied"] = days is not None
        return view

    by_network: dict[str, Any] = {}
    seen_surfaces: set[str] = set()
    dual_n = 0
    published: list[str] = []
    for row in rows:
        network = str(row.get("network") or "").strip().lower() or "unknown"
        surface = str(row.get("surface") or "").strip().lower() or "unknown"
        seen_surfaces.add(surface)
        flag = row.get("dual_count_risk")
        if flag:
            dual_n += 1
        stamp = row.get("published_at_utc")
        if isinstance(stamp, str) and stamp:
            published.append(stamp)
        bucket = by_network.setdefault(network, {})
        bucket.setdefault(surface, []).append(row)

    shaped: dict[str, Any] = {}
    for network, surfaces in sorted(by_network.items()):
        shaped[network] = {"by_surface": {}}
        for surface, srows in sorted(surfaces.items()):
            metrics: dict[str, Any] = {}
            surface_missing: list[str] = []
            for field in STORED_METRICS:
                vals = _collect(srows, field)
                stats = _quartiles(vals)
                metrics[field] = {
                    "n": len(vals),
                    "median": stats["median"],
                    "q1": stats["q1"],
                    "q3": stats["q3"],
                }
                if not vals:
                    surface_missing.append(field)
            shaped[network]["by_surface"][surface] = {
                "n": len(srows),
                "metrics": metrics,
                "missing_metrics": surface_missing,
            }
            if surface_missing:
                missing.append(
                    f"{network}/{surface} has no stored {', '.join(surface_missing)} (not zero)"
                )

    known_missing = [s for s in SURFACES if s not in seen_surfaces]
    if known_missing:
        missing.append(
            "No stored rows for surface "
            + ", ".join(known_missing)
            + ". Those surfaces are omitted, not scored as zero."
        )

    flags = honesty_flags(catalog_db=catalog_db if catalog_db else None)
    return {
        "ok": True,
        "gate": gate,
        "cap": CAP_ID,
        "brand_key": brand,
        "authorised": True,
        "available": True,
        "source": "performance_records",
        "external_system": "metricool",
        "external_profile_id": profile_ids[0] if len(profile_ids) == 1 else None,
        "external_profile_ids": profile_ids,
        "data_lane": "operational",
        "window_days": days,
        "window_applied": days is not None,
        "row_count": len(rows),
        "dual_count_risk_rows": dual_n,
        "published_at_min": min(published) if published else None,
        "published_at_max": max(published) if published else None,
        "metricool_called": False,
        "metricool_write": False,
        "invented_metrics": False,
        "paid_ads_spend": None,
        "paid_ads_called": False,
        "ads_spend_invented": False,
        "blended_score": None,
        "surfaces_blended": False,
        "by_network": shaped,
        "missing_surfaces": known_missing,
        "missing_information": missing,
        "note": (
            "Descriptive distribution of stored Metricool reads only. "
            "Not a cause, not a blended score, not ad spend."
        ),
        "assumptions": [
            "Numbers come only from stored Metricool reads on an authorised brand mapping.",
            "NULL is not zero.",
            "Surfaces are not blended into one score.",
            "Clicks, conversions, followers, and paid ads spend are not in this store.",
        ],
        "honesty": flags,
        "ledger_maturity": flags["ledger_maturity"],
        "maturity_ceiling": flags["maturity_ceiling"],
        "cr_id": flags["cr_id"],
        "cr_state": flags["cr_state"],
        "cr_resolved": flags["cr_resolved"],
        "invented_proven": False,
    }
