
# Pack IA-HIDE-DEAD-1 2026-10-01: Owner glance hrefs leave prove surfaces; routes remain.
# Pack PULSE-RADAR-HONESTY-3 2026-10-01: EMPTY/BLOCKED empty_reason+blocked_reason+precise_state; orphan prove hrefs → hubs; never invent green.
#!/usr/bin/env python3
"""Owner Radar RO desk — UX-PACK-12 deepen (Beta :8788 only).

Useful RO glance: WHAT matters tonight / this week · honesty stamps ·
links into real boards (pulse, 12WY, Mars/wire, exceptions, Needs You).

Never invent pulse counts, scores, Mars meters, occupancy, or revenue.
Prefer existing prove/empire/exceptions/pulse loaders. staff_ready=false.
Mount: GET /api/owner/radar-ro
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
WITA = timezone(timedelta(hours=8))
PACK = "UX-PACK-12"
SCHEMA = "wolf.owner-radar-ro.v1"
WIRE_VERIFY = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "METRICOOL-RUNTIME-WIRE-1-PEACHES-VERIFY.json"
)


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _card(
    *,
    id: str,
    section: str,
    what: str,
    state: str,
    value: Any,
    href: str,
    why: str,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stamp = state if state in {"LIVE", "PARTIAL", "EMPTY", "BLOCKED"} else "PARTIAL"
    out: dict[str, Any] = {
        "id": id,
        "section": section,  # tonight | this_week | honesty | boards
        "what": what,
        "state": stamp,
        "value": value,
        "href": href,
        "where": href,
        "why": why,
        "source": source,
        "loud": stamp in {"EMPTY", "BLOCKED"},
        "precise_state": stamp,
    }
    # PULSE-RADAR-HONESTY-3: structured EMPTY/BLOCKED reasons (never invent green)
    if stamp == "EMPTY":
        out["empty_reason"] = why
        out["blocked_reason"] = None
    elif stamp == "BLOCKED":
        out["blocked_reason"] = why
        out["empty_reason"] = None
    else:
        out["empty_reason"] = None
        out["blocked_reason"] = None
    if extra:
        out.update(extra)
        # re-assert loud + reasons if state forced later by caller
        st2 = out.get("state") or stamp
        if st2 == "EMPTY" and not out.get("empty_reason"):
            out["empty_reason"] = out.get("why") or why
            out["loud"] = True
            out["precise_state"] = "EMPTY"
        if st2 == "BLOCKED" and not out.get("blocked_reason"):
            out["blocked_reason"] = out.get("why") or why
            out["loud"] = True
            out["precise_state"] = "BLOCKED"
    return out


def _safe_pulse() -> dict[str, Any]:
    try:
        from core import owner_pulse_ro as pulse

        return pulse.load_pulse_ro() or {}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"pulse_ro:{exc}", "tiles": [], "counts": {}}


def _safe_12wy() -> dict[str, Any]:
    try:
        from core import strat_12wy_prove as wy

        return wy.build_prove() or {}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"12wy:{exc}"}


def _safe_radar_strip() -> dict[str, Any]:
    try:
        from core import owner_empire_pack as emp

        return emp.radar_strip() or {}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"radar_strip:{exc}", "display": "EMPTY", "loud": True}


def _safe_radar_prove() -> dict[str, Any]:
    try:
        from core import strat_radar_prove as radar

        return radar.build_prove() or {}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"radar_prove:{exc}"}


def _safe_exceptions() -> dict[str, Any]:
    try:
        from core import owner_exceptions_live1 as ex

        return ex.public_payload() or {}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"exceptions:{exc}", "items": []}


def _safe_needs_you() -> dict[str, Any]:
    try:
        from core import owner_needs_you1 as ny

        return ny.public_payload() or {}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"needs_you:{exc}", "arm_boards": []}


def _wire_card() -> dict[str, Any]:
    """Metricool / runtime wire honesty — no invented engagement."""
    if not WIRE_VERIFY.exists():
        return _card(
            id="wire",
            section="this_week",
            what="Wire / Metricool runtime",
            state="EMPTY",
            value="verify file ABSENT",
            href="/content-2.0",
            why="METRICOOL-RUNTIME-WIRE-1 verify JSON not on Beta. Not inventing brands or engagement.",
            source="metricool_runtime_wire1_verify",
        )
    try:
        data = json.loads(WIRE_VERIFY.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return _card(
            id="wire",
            section="this_week",
            what="Wire / Metricool runtime",
            state="BLOCKED",
            value="verify unreadable",
            href="/content-2.0",
            why=f"Verify JSON present but unreadable ({exc}). No invent.",
            source="metricool_runtime_wire1_verify",
        )
    status = str(data.get("status") or "UNKNOWN")
    runtime = data.get("runtime") or {}
    brands = runtime.get("brands_wired")
    eng = runtime.get("engagement_values")
    wolf_http = runtime.get("wolf_http")
    verified = data.get("verified_at")
    # PASS_VERIFIED pack ≠ live engagement numbers
    if eng in (None, "NOT_RUNTIME_null") or wolf_http == "EXTERNAL_BLOCKER":
        state = "PARTIAL"
        value = f"{status} · brands {brands if brands is not None else '—'} · engagement NOT live"
        why = (
            f"Pack {status} at {verified or 'MISSING'}. brands_wired={brands}. "
            f"engagement_values={eng}. wolf_http={wolf_http}. "
            "Not claiming live IG engagement. WHERE: /content-2.0 (Metricool READ wired; prove page hidden)."
        )
    else:
        state = "PARTIAL"
        value = f"{status} · brands {brands}"
        why = (
            f"Pack {status}. Engagement field present but Radar does not invent a score. "
            f"WHERE: /content-2.0 (Metricool READ wired; prove page hidden)."
        )
    return _card(
        id="wire",
        section="this_week",
        what="Wire / Metricool runtime",
        state=state,
        value=value,
        href="/content-2.0",
        why=why,
        source="metricool_runtime_wire1_verify",
        extra={
            "pack_status": status,
            "brands_wired": brands,
            "engagement_values": eng,
            "wolf_http": wolf_http,
            "verified_at": verified,
        },
    )


def _tonight_from_pulse(pulse: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = pulse.get("tiles") or []
    want = ("atrium_occ", "kuta_rates", "bzg_night", "backup")
    by_id = {t.get("id"): t for t in tiles if isinstance(t, dict)}
    out: list[dict[str, Any]] = []
    for tid in want:
        t = by_id.get(tid)
        if not t:
            continue
        out.append(
            _card(
                id=f"tonight_{tid}",
                section="tonight",
                what=t.get("what") or tid,
                state=t.get("state") or "PARTIAL",
                value=t.get("value"),
                href=t.get("href") or t.get("where") or "/owner-empire-pack",
                why=t.get("why") or "From Owner pulse RO.",
                source=f"pulse_ro:{t.get('source') or tid}",
                extra={"pulse_id": tid, "loud": bool(t.get("loud"))},
            )
        )
    if not out:
        out.append(
            _card(
                id="tonight_pulse",
                section="tonight",
                what="Tonight pulse",
                state="EMPTY",
                value="pulse tiles not read",
                href="/owner-empire-pack",
                why="Pulse RO returned no tonight tiles. Nothing invented.",
                source="pulse_ro",
            )
        )
    return out


def _this_week_cards(
    wy: dict[str, Any],
    radar_strip: dict[str, Any],
    prove: dict[str, Any],
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    clock = (wy.get("clock") or {}) if isinstance(wy, dict) else {}
    score = (wy.get("score") or {}) if isinstance(wy, dict) else {}
    score_state = str(score.get("state") or "EMPTY")
    if score_state not in {"LIVE", "PARTIAL", "EMPTY", "BLOCKED"}:
        # prove uses EMPTY for no tactics — keep EMPTY, never invent 0%
        score_state = "EMPTY" if score_state.upper() == "EMPTY" else "PARTIAL"
    cards.append(
        _card(
            id="12wy",
            section="this_week",
            what="12-Week Year (CAP-STRAT-01)",
            state=score_state if score_state != "LIVE" else "PARTIAL",  # score EMPTY≠LIVE
            value=(
                f"{clock.get('display') or 'period UNKNOWN'} · score {score_state}"
                f" · planned {score.get('planned') if score.get('planned') is not None else '—'} · done {score.get('done') if score.get('done') is not None else '—'}"
            ),
            href="/progress",
            why=score.get("why")
            or "12WY prove RO. EMPTY is not 0%. No tactics invented. Helm dated pack may lag clock.",
            source="strat_12wy_prove",
            extra={
                "cap": "CAP-STRAT-01",
                "week": clock.get("week"),
                "period": clock.get("period"),
                "score_percent": score.get("percent"),  # may be null — honesty
                "href_helm": "/dashboards/deliveries/12wy-2026-09-18.html",
            },
        )
    )

    # Force 12wy card state: if score EMPTY keep EMPTY (loud)
    if str(score.get("state") or "").upper() == "EMPTY":
        cards[-1]["state"] = "EMPTY"
        cards[-1]["loud"] = True
        cards[-1]["precise_state"] = "EMPTY"
        cards[-1]["empty_reason"] = (
            cards[-1].get("why")
            or "No evidenced planned tactics this week. EMPTY, not 0%. Score does not create NOW."
        )
        cards[-1]["blocked_reason"] = None

    bird = ((prove.get("surfaces") or {}).get("birdseye") or {}) if isinstance(prove, dict) else {}
    mars_state = "EMPTY"
    mars_why = (
        "V1 Wolf to Mars tile punch is 'meter EMPTY'. Beta Radar does not invent a Mars meter. "
        "Bird's-eye tile-mars is named on the Owner board text; satisfied stays false until Pulse+Exceptions named."
    )
    tiles = bird.get("tiles") or []
    if "tile-mars" in tiles:
        mars_state = "EMPTY"  # named but meter empty — not PARTIAL greenwash
        mars_why = (
            f"tile-mars present on birdseye ({bird.get('tile_count')} tiles). "
            "Meter remains EMPTY (V1 punch). Not inventing progress. WHERE: /owner/radar (prove surface hidden from Owner glance)."
        )
    cards.append(
        _card(
            id="mars",
            section="this_week",
            what="Wolf to Mars",
            state=mars_state,
            value="meter EMPTY",
            href="/owner/radar",
            why=mars_why,
            source="strat_radar_prove.birdseye+v1_radar_html",
            extra={"tile": "tile-mars", "birdseye_satisfied": bird.get("satisfied")},
        )
    )

    cards.append(_wire_card())

    display = radar_strip.get("display") or "EMPTY"
    rstate = "EMPTY" if display in {"EMPTY", "UNWIRED"} else "PARTIAL"
    cards.append(
        _card(
            id="radar_cap",
            section="honesty",
            what="Radar CAP-STRAT-02",
            state=rstate,
            value=f"{display} · maturity {radar_strip.get('maturity') or 'UNKNOWN'}",
            href="/owner/radar",
            why=radar_strip.get("why")
            or "Catalog intent Pulse+Exceptions not named on Owner Radar text. Counts not invented.",
            source="owner_empire_pack.radar_strip",
            extra={
                "cap": radar_strip.get("cap") or "CAP-STRAT-02",
                "pulse_count": radar_strip.get("pulse_count"),
                "exception_count": radar_strip.get("exception_count"),
                "cr_id": radar_strip.get("cr_id"),
                "cr_state": radar_strip.get("cr_state"),
                "progress_used_as_cap": radar_strip.get("progress_used_as_cap"),
            },
        )
    )
    return cards


def _attention_cards(ex: dict[str, Any], needs: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    items = [i for i in (ex.get("items") or []) if isinstance(i, dict)]
    # Prefer blocked / money_risk for "matters tonight"
    blocked = [i for i in items if i.get("blocked")]
    money = [i for i in items if i.get("money_risk") and not i.get("blocked")]
    picked = (blocked + money + items)[:6]
    if picked:
        for i, item in enumerate(picked):
            state = "BLOCKED" if item.get("blocked") else "PARTIAL"
            cards.append(
                _card(
                    id=f"ex_{i}_{item.get('id') or item.get('kind') or i}",
                    section="tonight" if item.get("blocked") or item.get("money_risk") else "honesty",
                    what=item.get("title") or item.get("kind") or "Exception",
                    state=state,
                    value=("blocked · " if item.get("blocked") else "")
                    + ("money risk · " if item.get("money_risk") else "")
                    + f"severity {item.get('severity') or 'MISSING'}",
                    href=(item.get("href") if item.get("href") and "exceptions-live" not in str(item.get("href")) else None) or "/owner/radar",
                    why=(item.get("detail") or "")[:280]
                    + " Severity MISSING when not on record — not invented.",
                    source="owner_exceptions_live1",
                    extra={
                        "kind": item.get("kind"),
                        "owner_role": item.get("owner_role"),
                        "money_risk": bool(item.get("money_risk")),
                        "blocked": bool(item.get("blocked")),
                    },
                )
            )
    else:
        cards.append(
            _card(
                id="exceptions",
                section="honesty",
                what="Exceptions",
                state="EMPTY" if ex.get("ok") else "BLOCKED",
                value="no material items read" if ex.get("ok") else "exceptions RO failed",
                href="/owner/radar",
                why=ex.get("error")
                or "Exceptions board returned no items. Empty stays empty.",
                source="owner_exceptions_live1",
            )
        )

    connective = needs.get("total_connective_count")
    arm_count = needs.get("arm_count")
    empty_arms = needs.get("empty_arm_count")
    if needs.get("ok"):
        boards = [b for b in (needs.get("arm_boards") or []) if isinstance(b, dict) and not b.get("empty")]
        top = sorted(boards, key=lambda b: int(b.get("count") or 0), reverse=True)[:4]
        summary = ", ".join(
            f"{b.get('label')}:{b.get('count')}" for b in top
        ) or "no connective arms"
        cards.append(
            _card(
                id="needs_you",
                section="tonight",
                what="Needs You (connective)",
                state="PARTIAL" if connective else "EMPTY",
                value=f"{connective} connective · {arm_count} arms · empty {empty_arms} · {summary}",
                href="/staff-ops-routing",
                why=(
                    "Counts from live Needs-You strips only. No invented urgency. "
                    "Open Needs You desk or an arm desk from the board."
                ),
                source="owner_needs_you1",
                extra={
                    "total_connective_count": connective,
                    "arm_count": arm_count,
                    "empty_arm_count": empty_arms,
                    "top_arms": [
                        {
                            "id": b.get("id"),
                            "label": b.get("label"),
                            "count": b.get("count"),
                            "href": b.get("desk_href") or b.get("href"),
                        }
                        for b in top
                    ],
                    "href_staff_ops": "/staff-ops-routing",
                },
            )
        )
    else:
        cards.append(
            _card(
                id="needs_you",
                section="tonight",
                what="Needs You (connective)",
                state="BLOCKED",
                value="needs-you RO failed",
                href="/staff-ops-routing",
                why=needs.get("error") or "Needs You payload unavailable. No invent.",
                source="owner_needs_you1",
            )
        )
    return cards


def _board_links() -> list[dict[str, Any]]:
    return [
        {"label": "Owner Home + Pulse", "href": "/owner-empire-pack"},
        {"label": "FINISH WOLF", "href": "/finish-war-room"},
        {"label": "Needs You desk", "href": "/staff-ops-routing"},
        {"label": "Exceptions live", "href": "/owner/radar"},
        {"label": "Progress / 12WY", "href": "/progress"},
        {"label": "Content (Metricool READ)", "href": "/content-2.0"},
        {"label": "Integrations", "href": "/integration-health"},
        {"label": "My Work", "href": "/my-work"},
        {"label": "Uma Blu desk", "href": "/bzg/uma-blu"},
        {"label": "Kuta rates", "href": "/kuta-rates"},
    ]


def load_radar_ro() -> dict[str, Any]:
    pulse = _safe_pulse()
    wy = _safe_12wy()
    radar_strip = _safe_radar_strip()
    prove = _safe_radar_prove()
    ex = _safe_exceptions()
    needs = _safe_needs_you()

    cards: list[dict[str, Any]] = []
    cards.extend(_tonight_from_pulse(pulse))
    cards.extend(_attention_cards(ex, needs))
    cards.extend(_this_week_cards(wy, radar_strip, prove))

    # Deduplicate by id while preserving order
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for c in cards:
        cid = str(c.get("id"))
        if cid in seen:
            continue
        seen.add(cid)
        deduped.append(c)

    counts = {"tiles": len(deduped), "LIVE": 0, "PARTIAL": 0, "EMPTY": 0, "BLOCKED": 0}
    empty_blocked_index: list[dict[str, Any]] = []
    for c in deduped:
        st = c.get("state") or "PARTIAL"
        if st in counts:
            counts[st] += 1
        if st in {"EMPTY", "BLOCKED"}:
            # ensure structured reasons always present on loud tiles
            if st == "EMPTY" and not c.get("empty_reason"):
                c["empty_reason"] = c.get("why") or "EMPTY — reason not invented green"
            if st == "BLOCKED" and not c.get("blocked_reason"):
                c["blocked_reason"] = c.get("why") or "BLOCKED — reason not invented green"
            c["precise_state"] = st
            c["loud"] = True
            empty_blocked_index.append(
                {
                    "id": c.get("id"),
                    "state": st,
                    "precise_state": c.get("precise_state"),
                    "empty_reason": c.get("empty_reason"),
                    "blocked_reason": c.get("blocked_reason"),
                    "why": c.get("why"),
                    "href": c.get("href"),
                }
            )

    pulse_counts = pulse.get("counts") or {}
    residuals = [
        "Full V1 multi-tile mission control / live Mars meter not claimed",
        "EMPTY:12wy — No evidenced planned tactics (W4); EMPTY≠0%; Owner seed or ACCEPT-EMPTY",
        "EMPTY:mars — V1 meter EMPTY punch; progress not invented",
        "EMPTY:radar_cap — CAP-STRAT-02 Pulse+Exceptions names ABSENT on board text",
        "BLOCKED:exceptions — commissioning FAIL / daily-close / bank-statement money-risk stay BLOCKED",
        "PARTIAL:wire — Metricool brands LIVE; engagement NOT live (WRITE OFF)",
        "Screenshots / desktop_gate still need Owner CF (UX-PACK-10) — park Integrations JWT",
    ]

    return {
        "ok": True,
        "reason": "owner_radar_ro",
        "staff_ready": False,
        "human_commissioned": False,
        "claim": "PARTIAL_RO_DESK",
        "migration_state": "PARTIAL",
        "read_only": True,
        "as_of_wita": _now_wita(),
        "surface": "/owner/radar",
        "pack": PACK,
        "schema": SCHEMA,
        "honesty": (
            "Owner Radar deepen (UX-PACK-12) + PULSE-RADAR-HONESTY-3. "
            "EMPTY/BLOCKED carry empty_reason/blocked_reason/precise_state. "
            "No invented scores, Mars meters, occ, or revenue. Prove crumbs href → hubs. "
            "Finance SoD unchanged. staff_ready=false. desktop_gate_ready=false."
        ),
        "honesty_pack": "PULSE-RADAR-HONESTY-3",
        "cards": deduped,
        "counts": counts,
        "empty_blocked_index": empty_blocked_index,
        "sections": {
            "tonight": [c for c in deduped if c.get("section") == "tonight"],
            "this_week": [c for c in deduped if c.get("section") == "this_week"],
            "honesty": [c for c in deduped if c.get("section") == "honesty"],
        },
        "boards": _board_links(),
        "pulse_ref": {
            "ok": bool(pulse.get("ok")),
            "counts": pulse_counts,
            "href": "/owner-empire-pack",
            "api": "/api/owner/pulse-ro",
        },
        "exceptions_ref": {
            "ok": bool(ex.get("ok")),
            "operational_count": ex.get("operational_count"),
            "open_board_count": ex.get("open_board_count"),
            "href": "/owner/radar",
        },
        "needs_you_ref": {
            "ok": bool(needs.get("ok")),
            "total_connective_count": needs.get("total_connective_count"),
            "arm_count": needs.get("arm_count"),
            "href": "/staff-ops-routing",
        },
        "banner": {
            "state": "PARTIAL",
            "text": (
                "PARTIAL Owner Radar desk — not V1 mission-control dump, not fake green scores. "
                "EMPTY / BLOCKED stay loud with stamped reasons. SYSTEM% is not copied here. "
                "PULSE-RADAR-HONESTY-3 · desktop_gate_ready=false."
            ),
        },
        "residuals": residuals,
        "desktop_gate_ready": False,
        "finance_sod_unchanged": True,
    }


if __name__ == "__main__":
    import json as _j

    print(_j.dumps(load_radar_ro(), indent=2, default=str)[:6000])
