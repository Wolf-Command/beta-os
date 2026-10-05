# Pack PULSE-RADAR-HONESTY-3 2026-10-01: atrium href_hold → /amg-ops-pack#occ (prove crumb off pulse).
#!/usr/bin/env python3
"""Owner Home live pulse — READ-ONLY aggregate glance tiles (UX-PACK-09 / 09b).

Each tile: WHAT · number/state · WHERE (href) · honesty stamp
  LIVE | PARTIAL | EMPTY | BLOCKED

Never invent occupancy %, revenue, covers, rates, or pipeline counts.
Prefer existing Beta SoT loaders. staff_ready=false always.
Mount: GET /api/owner/pulse-ro  (Beta :8788 only).

UX-PACK-09b: deepen PARTIAL/BLOCKED toward real LIVE without inventing —
  occ clearer BLOCKED+WHERE; Uma EMPTY when no close filed; leads DEMO demote; PULSE-LEADS-BACKUP-HONESTY-2 DEMO/STALE stamps;
  kuta prefer tonight competitor status over far-future atrium stay.
"""
from __future__ import annotations
import json

from datetime import datetime, timezone, timedelta
from typing import Any

WITA = timezone(timedelta(hours=8))
OWNER = "PERS-MATT"


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")



def _parse_idr_amount(raw: Any) -> int | None:
    """Parse printed IDR/Rp strings (e.g. 'IDR 1.050.000', 'Rp 1.200.000,00')."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).replace("\xa0", " ").replace("Rp", "").replace("IDR", "").strip()
    if not s:
        return None
    # Indonesian thousands with '.' and optional decimal ',xx'
    if "," in s:
        s = s.split(",", 1)[0]
    s = s.replace(".", "").replace(" ", "")
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits) if digits else None


def _kuta_night_covers_today(night: Any, today: str) -> bool:
    """True when status.night window includes today's WITA date."""
    if not night:
        return False
    s = str(night)
    # Forms: '2026-09-30 → 2026-10-01' or 'tonight 30 Sep–1 Oct'
    if today in s:
        return True
    try:
        y, m, d = today.split("-")
        # loose day-month match in sub/night prose
        return False
    except Exception:  # noqa: BLE001
        return False


def _tile(
    *,
    id: str,
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
        "what": what,
        "state": stamp,
        "value": value,
        "href": href,
        "where": href,
        "why": why,
        "source": source,
        "loud": stamp in {"EMPTY", "BLOCKED"},
    }
    if extra:
        out.update(extra)
    return out


def _occ_tile() -> dict[str, Any]:
    href = "/amg/sales-desk#occ"  # PACK-03: pulse opens the sales-desk occ card
    hold_href = "/amg/sales-desk#occ"
    try:
        from core.amg_occ_truth1 import build_slice

        slice_ = build_slice()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="atrium_occ",
            what="Atrium occupancy",
            state="EMPTY",
            value=None,
            href=href,
            why=f"OCC truth loader failed ({type(exc).__name__}). No occupancy invented.",
            source="amg_occ_truth1.build_slice",
            extra={"href_hold": hold_href},
        )
    blocked = bool(slice_.get("occupancy_blocked") or slice_.get("occupancy_unknown"))
    pms = slice_.get("pms_connected")
    yanolja = bool(slice_.get("yanolja_live"))
    tiles = slice_.get("honesty_tiles") or slice_.get("tiles") or []
    occ_row = next((t for t in tiles if isinstance(t, dict) and t.get("id") == "occupancy"), None)
    yanolja_row = next((t for t in tiles if isinstance(t, dict) and t.get("id") == "yanolja"), None)
    # Confirm external hold also has no inventable % (RO honesty only)
    hold_null = True
    try:
        from core.occupancy_external_hold1 import build_board as _hold_board

        hold = _hold_board()
        hold_null = hold.get("occupancy_pct") is None and hold.get("occupancy") is None
    except Exception:  # noqa: BLE001
        hold = None
    if blocked or not pms:
        blocker = (yanolja_row or {}).get("why") or (
            "INT-YAN-WOLF / CAP-AMG-01 BLOCKED_EXTERNAL — Yanolja PMS not connected."
        )
        why = (
            f"Occupancy UNKNOWN (not zero, not invented). {blocker} "
            f"WHERE: {href} · hold desk {hold_href}."
        )
        if (occ_row or {}).get("why"):
            why = (
                f"{(occ_row or {}).get('why')} Blocker: INT-YAN-WOLF / CAP-AMG-01 external. "
                f"WHERE: {href} · {hold_href}."
            )
        return _tile(
            id="atrium_occ",
            what="Atrium occupancy",
            state="BLOCKED",
            value=None,
            href=href,
            why=why,
            source="amg_occ_truth1+occupancy_external_hold1",
            extra={
                "pms_connected": bool(pms),
                "yanolja_live": yanolja,
                "occupancy_unknown": True,
                "blocker": "INT-YAN-WOLF / CAP-AMG-01",
                "href_hold": hold_href,
                "hold_occupancy_null": hold_null,
            },
        )
    # Live path reserved — still refuse invent if value missing
    pct = (occ_row or {}).get("value")
    if pct is None:
        return _tile(
            id="atrium_occ",
            what="Atrium occupancy",
            state="EMPTY",
            value=None,
            href=href,
            why="OCC desk present but no occupancy value on record. Not invented.",
            source="amg_occ_truth1",
            extra={"href_hold": hold_href},
        )
    freshness = slice_.get("freshness") or slice_.get("last_success")
    rooms_total = slice_.get("rooms_total")
    vacant = slice_.get("rooms_vacant")
    display = pct
    if isinstance(pct, (int, float)) and isinstance(rooms_total, int) and isinstance(vacant, int):
        display = f"{pct:.0f}% · {vacant} vacant / {rooms_total} rooms"
    return _tile(
        id="atrium_occ",
        what="Atrium occupancy",
        state="LIVE",
        value=display,
        href=href,
        why=(
            f"LIVE from Yanolja last-read ({freshness}). "
            "Vacant vs rooms, not guests. Arrivals/in-house UNKNOWN. "
            "source=Yanolja Inventory+RoomInfo."
        ),
        source="yanolja_last_read",
        extra={
            "pms_connected": True,
            "yanolja_live": True,
            "occupancy_unknown": False,
            "occupancy_pct": pct if isinstance(pct, (int, float)) else None,
            "rooms_total": rooms_total,
            "rooms_vacant": vacant,
            "guests": None,
            "freshness": freshness,
            "href_hold": hold_href,
        },
    )


def _kuta_tile() -> dict[str, Any]:
    href = "/amg/sales-desk#kuta"  # PACK-03: tonight board on the sales desk
    alt = "/amg/sales-desk#kuta"
    try:
        from core.ops_kuta_rates_ro import load_kuta_rates_ro

        payload = load_kuta_rates_ro()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="kuta_rates",
            what="Kuta rates tonight",
            state="EMPTY",
            value=None,
            href=alt,
            why=f"Kuta rates RO failed ({type(exc).__name__}). No rate invented.",
            source="ops_kuta_rates_ro",
        )
    db = payload.get("db") or {}
    recent = db.get("atrium_recent") or []
    brief = payload.get("brief") or {}
    status = payload.get("status") if isinstance(payload.get("status"), dict) else None
    today = datetime.now(WITA).strftime("%Y-%m-%d")
    if not payload.get("ok"):
        return _tile(
            id="kuta_rates",
            what="Kuta rates tonight",
            state="EMPTY",
            value=None,
            href=alt,
            why=payload.get("reason") or "No Kuta SoT yet.",
            source="ops_kuta_rates_ro",
            extra={"href_hub": href},
        )

    # Prefer morning-report status.official for TONIGHT competitor signal
    # when atrium_recent stay dates are far-future / not today.
    if status and status.get("official"):
        night = status.get("night") or ""
        gen = str(status.get("generated_at") or "")[:10]
        night_is_today = _kuta_night_covers_today(night, today) or gen == today
        parsed: list[tuple[int, str, str]] = []
        for o in status.get("official") or []:
            if not isinstance(o, dict):
                continue
            amt = _parse_idr_amount(o.get("stay"))
            if amt is None:
                continue
            parsed.append((amt, str(o.get("hotel") or "?"), str(o.get("room") or "?")))
        parsed.sort(key=lambda x: x[0])
        if parsed and night_is_today:
            cheapest = parsed[0]
            headline = status.get("headline") or f"{cheapest[1]} from {cheapest[0]:,} IDR"
            counts = status.get("counts") or {}
            stamp = "LIVE" if gen == today or _kuta_night_covers_today(night, today) else "PARTIAL"
            return _tile(
                id="kuta_rates",
                what="Kuta rates tonight",
                state=stamp,
                value=f"from {cheapest[0]:,} IDR · {cheapest[1]}",
                href=alt,
                why=(
                    f"Tonight competitor signal ({night or 'status'}) · "
                    f"cheapest official {cheapest[0]:,} IDR · {cheapest[2]}. "
                    f"Headline: {headline}. "
                    f"Official {counts.get('official', len(parsed))} · "
                    f"sold_out {counts.get('sold_out', '?')}. "
                    "LEARN only — no booking. Atrium own stay scrape may be far-future."
                ),
                source="ops_kuta_rates_ro.status.official",
                extra={
                    "href_hub": href,
                    "night": night,
                    "generated_at": status.get("generated_at"),
                    "cheapest_idr": cheapest[0],
                    "cheapest_hotel": cheapest[1],
                    "cheapest_room": cheapest[2],
                    "headline": headline,
                    "official_count": counts.get("official"),
                    "sold_out_count": counts.get("sold_out"),
                    "brief_status": brief.get("brief_status"),
                    "competitor_rates_empty": False,
                    "atrium_recent_far_future": True,
                },
            )

    # Fall back: atrium_recent (often far-future stay) — honest PARTIAL
    tonight_rows = [
        r
        for r in recent
        if isinstance(r, dict) and r.get("rate") is not None and "error" not in r
    ]
    if tonight_rows:
        row = tonight_rows[0]
        rate = row.get("rate")
        cur = row.get("currency") or "IDR"
        stay = row.get("stay_date") or "?"
        room = row.get("room_name") or "room"
        scrape = row.get("scrape_date")
        if stay == today:
            stamp = "LIVE"
        else:
            stamp = "PARTIAL"
        return _tile(
            id="kuta_rates",
            what="Kuta rates tonight",
            state=stamp,
            value=f"{rate:,.0f} {cur}" if isinstance(rate, (int, float)) else str(rate),
            href=alt,
            why=(
                f"Atrium scrape {scrape} · stay {stay} · {room}. "
                "No tonight competitor status.official usable. LEARN only — no booking."
            ),
            source="ops_kuta_rates_ro.atrium_recent",
            extra={
                "href_hub": href,
                "stay_date": stay,
                "scrape_date": scrape,
                "room_name": room,
                "brief_status": brief.get("brief_status"),
                "competitor_rates_empty": db.get("competitor_rates_empty"),
            },
        )
    if brief.get("brief_status") == "PRESENT":
        return _tile(
            id="kuta_rates",
            what="Kuta rates tonight",
            state="PARTIAL",
            value=brief.get("name") or "brief present",
            href=alt,
            why="Brief present; no tonight official or atrium_recent rate number.",
            source="ops_kuta_rates_ro.brief",
            extra={"href_hub": href},
        )
    if status is not None:
        return _tile(
            id="kuta_rates",
            what="Kuta rates tonight",
            state="PARTIAL",
            value=status.get("headline") or "status present",
            href=alt,
            why="Status JSON present but no parseable tonight official IDR.",
            source="ops_kuta_rates_ro.status",
            extra={"href_hub": href},
        )
    return _tile(
        id="kuta_rates",
        what="Kuta rates tonight",
        state="EMPTY",
        value=None,
        href=alt,
        why="Kuta RO loaded but no rate/brief/status usable for a glance number.",
        source="ops_kuta_rates_ro",
        extra={"href_hub": href},
    )


def _bzg_night_tile() -> dict[str, Any]:
    href = "/bzg/uma-blu#closes"
    close_desk = "/uma-blu-close"
    # Prefer venue closes; if EMPTY keep EMPTY honesty (no invent revenue/covers).
    closes_payload = None
    try:
        from core import uma_devi_p0 as uma_devi

        closes_payload = uma_devi.previous_closes(limit=3)
    except Exception as exc:  # noqa: BLE001
        closes_payload = {
            "ok": False,
            "empty": True,
            "error": f"{type(exc).__name__}: {exc}",
        }

    if closes_payload and closes_payload.get("ok") and not closes_payload.get("empty"):
        closes = closes_payload.get("closes") or []
        top = closes[0] if closes else {}
        # Never invent revenue/covers — only stored close fields
        value_bits = []
        for key in ("business_date", "status", "state", "close_id"):
            if top.get(key) is not None:
                value_bits.append(f"{key}={top.get(key)}")
        return _tile(
            id="bzg_night",
            what="BZG / Uma last-night",
            state="LIVE" if top else "PARTIAL",
            value="; ".join(value_bits) if value_bits else f"{closes_payload.get('count')} close(s)",
            href=href,
            why="From venue_daily_closes. No cash_count. No invented revenue/covers.",
            source="uma_devi_p0.previous_closes",
            extra={
                "close_count": closes_payload.get("count"),
                "href_closes": href,
                "href_close_desk": close_desk,
            },
        )

    # No venue close filed — fall back to authorised ESB warehouse READ
    # (theoretical consumption / payment-lines snapshot). Never invent.
    esb_snap = None
    try:
        from core import esb_close_snapshot as _esb
        import sqlite3
        from pathlib import Path as _P

        esb_path = _esb.resolve_esb_path()
        max_biz = None
        if esb_path.is_file():
            uri = esb_path.resolve().as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            try:
                row = conn.execute(
                    "SELECT MAX(biz_date) FROM sales WHERE biz_date IS NOT NULL"
                ).fetchone()
                max_biz = row[0] if row else None
            finally:
                conn.close()
        if max_biz:
            esb_snap = _esb.snapshot_day(str(max_biz))
    except Exception as exc:  # noqa: BLE001
        esb_snap = {"_error": f"{type(exc).__name__}: {exc}"}

    if isinstance(esb_snap, dict) and not esb_snap.get("_error") and not esb_snap.get("incomplete"):
        totals = esb_snap.get("totals") or {}
        meta = esb_snap.get("query_meta") or {}
        biz = meta.get("business_date") or max_biz
        finished = totals.get("finished_count")
        grand = totals.get("grand_total")
        cash = totals.get("cash_from_payments")
        card = totals.get("card_from_payments")
        pulled = esb_snap.get("esb_pulled_at") or meta.get("max_pulled_at")
        # Deepen: covers/bills from uma_real_projection.operating_day (same warehouse)
        covers = None
        bills = None
        net_sales = None
        items_unmapped = None
        try:
            from core import uma_real_projection as _urp

            od = _urp.operating_day()
            sales = (od or {}).get("sales") or {}
            latest = sales.get("latest") or {}
            if str(latest.get("biz_date") or "") == str(biz):
                covers = latest.get("covers")
                bills = latest.get("bills")
                net_sales = latest.get("net_sales")
            exc = (od or {}).get("exceptions") or {}
            no_recipe = exc.get("no_recipe") or {}
            if isinstance(no_recipe, dict) and no_recipe.get("count") is not None:
                items_unmapped = no_recipe.get("count")
        except Exception:  # noqa: BLE001
            pass

        bits = [f"biz {biz}", f"finished {finished}"]
        if isinstance(covers, int):
            bits.append(f"covers {covers}")
        if isinstance(grand, (int, float)):
            bits.append(f"grand {grand:,.0f} IDR")
        value = " · ".join(bits)
        return _tile(
            id="bzg_night",
            what="BZG / Uma last-night",
            state="LIVE" if finished else "PARTIAL",
            value=value,
            href=href,
            why=(
                "No venue_daily_closes filed — using authorised ESB warehouse READ "
                f"(branch BLZ). source=ESB · freshness={pulled}. "
                "Payment-lines / theoretical consumption only — NOT settlement, "
                "NOT actual stock. Covers from sales.paxTotal (finished bills). "
                f"Cash {cash:,.0f} · Card {card:,.0f} (salesPayments). "
                "Uma /bzg/uma-blu/real/sales|operating-day|theoretical also consume esb.sqlite."
                if isinstance(cash, (int, float)) and isinstance(card, (int, float))
                else (
                    "No venue_daily_closes filed — authorised ESB warehouse READ "
                    f"(branch BLZ). source=ESB · freshness={pulled}. "
                    "Theoretical consumption only — not settlement. "
                    "Uma real/* APIs consume same warehouse."
                )
            ),
            source="ESB",
            extra={
                "close_count": 0,
                "href_closes": href,
                "href_close_desk": close_desk,
                "href_real_sales": "/api/bzg/uma-blu/real/sales",
                "href_real_operating_day": "/api/bzg/uma-blu/real/operating-day",
                "href_real_theoretical": "/api/bzg/uma-blu/real/theoretical",
                "business_date": biz,
                "finished_count": finished,
                "bills": bills if bills is not None else finished,
                "covers": covers,
                "grand_total": grand,
                "net_sales": net_sales,
                "items_unmapped_no_recipe": items_unmapped,
                "cash_from_payments": cash,
                "card_from_payments": card,
                "esb_pulled_at": pulled,
                "settlement_api": "UNAVAILABLE",
                "settlement": "EXTERNAL",
                "esb_cash_basis": "PAYMENT_LINES_NOT_SETTLEMENT",
                "theoretical_consumption_only": True,
                "provenance": "esb.sqlite sales → esb_close_snapshot + uma_real_projection.operating_day",
                "empty_venue_closes": True,
            },
        )

    # Truly empty — no closes and no ESB rows
    attn = None
    blocked = None
    try:
        from core import uma_ops_console as uma

        today = uma.today_cards() if callable(getattr(uma, "today_cards", None)) else None
        if isinstance(today, dict) and today.get("ok"):
            cards = today.get("cards") or []
            attn = sum(int(c.get("attention_count") or 0) for c in cards if isinstance(c, dict))
            blocked = sum(1 for c in cards if isinstance(c, dict) and c.get("blocked"))
    except Exception:  # noqa: BLE001
        pass

    empty_msg = (closes_payload or {}).get("empty_message") or "No previous closes recorded in Wolf yet"
    esb_err = (esb_snap or {}).get("_error") if isinstance(esb_snap, dict) else None
    why = (
        f"No close filed — {empty_msg}. ESB warehouse also empty/unreadable"
        + (f" ({esb_err})" if esb_err else "")
        + f". Night revenue/covers not on record (not invented). "
        f"File/review at {href} or Close desk {close_desk}."
    )
    if attn is not None:
        why += f" Uma Today attention {attn}" + (f" · blocked {blocked}" if blocked else "") + " is ops noise, not last-night sales."
    return _tile(
        id="bzg_night",
        what="BZG / Uma last-night",
        state="EMPTY",
        value="no close filed",
        href=href,
        why=why,
        source="venue_daily_closes",
        extra={
            "close_count": 0,
            "href_closes": href,
            "href_close_desk": close_desk,
            "attention_count": attn,
            "blocked_cards": blocked,
            "empty_message": empty_msg,
            "esb_attempted": True,
        },
    )



def _habitat_leads_glance() -> dict[str, Any] | None:
    """Authorised Habitat Google Sheet READ glance (Drive-proved). Never invents.
    Paths: beta-os/state/habitat-leads-glance.json (+ mission mirror).
    """
    from pathlib import Path as _Path
    root = _Path("/Users/wolfterminal/beta-os")
    candidates = [
        root / "state" / "habitat-leads-glance.json",
        root / "state" / "final-completion" / "beta-house-20261001" / "habitat-leads-glance.json",
    ]
    for path in candidates:
        try:
            if not path.is_file():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            if not data.get("authorised_read"):
                continue
            count = data.get("real_lead_count")
            if not isinstance(count, int) or count < 0:
                continue
            return data
        except Exception:  # noqa: BLE001
            continue
    return None


def _leads_tile() -> dict[str, Any]:
    href = "/ggv-ops-pack"
    truth_href = "/ggv-ops-pack#pipeline"  # IA-HIDE-ORPHAN-PROVE-CRUMBS-2: prove leaf off Owner chrome
    try:
        from core import ggv_ops_pack as ggv

        board = ggv.build_board(verified_person_id=OWNER)
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="leads",
            what="Leads (GGV)",
            state="EMPTY",
            value=None,
            href=href,
            why=f"GGV ops pack read failed ({type(exc).__name__}). No lead invented.",
            source="ggv_ops_pack.build_board",
        )
    leads = board.get("leads") or []
    count = board.get("count")
    if count is None:
        count = len(leads) if isinstance(leads, list) else None
    demo_n = 0
    fixture_n = 0
    live_n = 0
    for lead in leads if isinstance(leads, list) else []:
        label = str(lead.get("demo_label") or "")
        prov = lead.get("provenance_json") or lead.get("provenance") or {}
        if isinstance(prov, str):
            try:
                import json as _json

                prov = _json.loads(prov)
            except Exception:  # noqa: BLE001
                prov = {}
        is_demo = (
            label.upper().startswith("DEMO")
            or lead.get("demo")
            or lead.get("example")
            or (isinstance(prov, dict) and prov.get("demo"))
            or str(lead.get("source_system") or "").lower() == "fixture"
        )
        if is_demo:
            demo_n += 1
            if str(lead.get("source_system") or "").lower() == "fixture" or (
                isinstance(prov, dict) and prov.get("demo")
            ):
                fixture_n += 1
        else:
            live_n += 1
    # Also check catalog fixture stamp if board did not expose source_system
    if demo_n == 0 and isinstance(leads, list) and leads:
        # secondary: pipeline truth live_pipeline flag
        pass
    live_pipeline = None
    try:
        from core.ggv_pipeline_truth1 import build_slice as _gpt_slice

        gpt = _gpt_slice()
        live_pipeline = bool(gpt.get("live_pipeline"))
        if gpt.get("crm_lead_count") is not None and count is None:
            count = gpt.get("crm_lead_count")
    except Exception:  # noqa: BLE001
        gpt = None

    ex = ((board.get("exceptions") or {}).get("exceptions")) or []
    nye = sum(1 for e in ex if isinstance(e, dict) and (e.get("aging") or {}).get("needs_you"))
    if board.get("empty") or count == 0:
        return _tile(
            id="leads",
            what="Leads (GGV / Habitat)",
            state="EMPTY",
            value=0,
            href=href,
            why="GGV board empty — count is zero from SoT, not invented quiet.",
            source="ggv_ops_pack",
            extra={"needs_you_exceptions": nye, "href_truth": truth_href},
        )
    # All DEMO/fixture in core_leads — prefer authorised Habitat Sheet READ if present
    if demo_n and live_n == 0:
        habitat = _habitat_leads_glance()
        if habitat and int(habitat.get("real_lead_count") or 0) > 0:
            hcount = int(habitat["real_lead_count"])
            return _tile(
                id="leads",
                what="Leads (GGV / Habitat)",
                state="LIVE",
                value=f"LIVE Habitat sheet · {hcount} leads · core_leads fixtures ignored · {nye} needs-you",
                href=href,
                why=(
                    "PULSE-LEADS-HABITAT-SHEET-1: Authorised Habitat Google Sheet READ "
                    f"(Drive LIVE+TESTED) is Owner SoT — {hcount} real Leads-tab rows. "
                    f"core_leads had {demo_n} DEMO fixtures only (not shown as operational SoT). "
                    f"live_pipeline={live_pipeline} · needs-you={nye}. "
                    "Amounts off glance. CRM/Klaviyo push OFF. "
                    f"Sheet {habitat.get('sheet_id')} · as_of {habitat.get('as_of_wita')} · "
                    f"WHERE: {href} · {truth_href}."
                ),
                source="habitat_sheet_drive_read",
                extra={
                    "count": hcount,
                    "live_count": hcount,
                    "demo_labeled": demo_n,
                    "fixture_ignored": True,
                    "needs_you_exceptions": nye,
                    "live_pipeline": live_pipeline,
                    "sot": "HABITAT_SHEET_DRIVE_READ",
                    "precise_state": "LIVE",
                    "sheet_id": habitat.get("sheet_id"),
                    "as_of_wita": habitat.get("as_of_wita"),
                    "href_truth": truth_href,
                },
            )
        # No usable Habitat glance — EMPTY/BLOCKED honest, never DEMO operational SoT
        return _tile(
            id="leads",
            what="Leads (GGV / Habitat)",
            state="EMPTY",
            value=f"EMPTY · no authorised live SoT · {demo_n} fixtures hidden",
            href=href,
            why=(
                "core_leads are DEMO fixtures only and Habitat sheet glance absent/unusable. "
                "Owner experience shows EMPTY (not DEMO). CRM write OFF. "
                f"WHERE: {href} · {truth_href}."
            ),
            source="ggv_ops_pack+NO_AUTHORITATIVE_SOT",
            extra={
                "count": 0,
                "live_count": 0,
                "demo_labeled": demo_n,
                "fixture_hidden": True,
                "needs_you_exceptions": nye,
                "live_pipeline": live_pipeline,
                "sot": "NONE",
                "precise_state": "EMPTY_NO_AUTHORITATIVE_SOT",
                "href_truth": truth_href,
            },
        )
    # Mixed or claimed live rows — still PARTIAL unless live_pipeline True AND zero DEMO
    if live_n and (demo_n or live_pipeline is False):
        return _tile(
            id="leads",
            what="Leads (GGV / Habitat)",
            state="PARTIAL",
            value=f"PARTIAL · {live_n} non-DEMO · {demo_n} DEMO · {nye} needs-you",
            href=href,
            why=(
                "PARTIAL honesty: non-DEMO rows present but live_pipeline="
                f"{live_pipeline} and/or DEMO mix remains. Not inventing full LIVE Habitat SoT. "
                f"WHERE: {href} · {truth_href}."
            ),
            source="ggv_ops_pack",
            extra={
                "count": count,
                "live_count": live_n,
                "demo_labeled": demo_n,
                "needs_you_exceptions": nye,
                "live_pipeline": live_pipeline,
                "sot": "MIXED" if demo_n else "BOARD_NON_DEMO",
                "precise_state": "PARTIAL",
                "href_truth": truth_href,
            },
        )
    # LIVE only when zero DEMO and pipeline truth says live
    stamp = "LIVE" if demo_n == 0 and live_pipeline is True else "PARTIAL"
    return _tile(
        id="leads",
        what="Leads (GGV / Habitat)",
        state=stamp,
        value=(
            f"LIVE · {live_n} live · {count} on board · {nye} needs-you"
            if stamp == "LIVE"
            else f"PARTIAL · {live_n} on board · live_pipeline={live_pipeline} · {nye} needs-you"
        ),
        href=href,
        why=(
            "LIVE Habitat/GGV lead SoT (zero DEMO; live_pipeline True). Amounts stay off this glance."
            if stamp == "LIVE"
            else "PARTIAL: board has non-DEMO rows but live_pipeline not True — not inventing LIVE."
        ),
        source="ggv_ops_pack",
        extra={
            "count": count,
            "live_count": live_n,
            "demo_labeled": demo_n,
            "needs_you_exceptions": nye,
            "live_pipeline": live_pipeline,
            "sot": "LIVE_PIPELINE" if stamp == "LIVE" else "BOARD_NON_DEMO",
            "precise_state": stamp,
            "href_truth": truth_href,
        },
    )


def _purchasing_tile() -> dict[str, Any]:
    href = "/bzg/uma-blu/purchasing"
    try:
        from core import uma_alchemist_ro as alc

        summary = alc.project_attention_summary()
        src = alc.source_status()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="purchasing",
            what="Purchasing / Alchemist",
            state="EMPTY",
            value=None,
            href=href,
            why=f"Alchemist RO failed ({type(exc).__name__}). No owe/paid invented.",
            source="uma_alchemist_ro",
        )
    if not isinstance(summary, dict):
        return _tile(
            id="purchasing",
            what="Purchasing / Alchemist",
            state="EMPTY",
            value=None,
            href=href,
            why="Alchemist attention summary missing. No numbers invented.",
            source="uma_alchemist_ro",
        )
    unpaid_n = summary.get("unpaid_ledger_count")
    unpaid_sum = summary.get("unpaid_ledger_sum")
    awaiting = summary.get("awaiting_devi_count")
    received = summary.get("received_count")
    src_status = summary.get("source_status") or src
    if src_status not in {"OK", "PRESENT", "LIVE"} and unpaid_n is None and awaiting is None:
        return _tile(
            id="purchasing",
            what="Purchasing / Alchemist",
            state="EMPTY",
            value=None,
            href=href,
            why=f"Alchemist source {src_status}. Owe/paid not readable — not invented.",
            source="uma_alchemist_ro",
        )
    # Honest unpaid glance from live Alchemist sqlite (legacy *path*, real counts).
    # LIVE only when source OK + process_up + DB counts prove — never invents pay/capability.
    legacy = bool(summary.get("legacy"))
    sum_bit = ""
    if isinstance(unpaid_sum, (int, float)):
        sum_bit = f" · unpaid sum {unpaid_sum:,.0f}"
    # Alchemist DB tile counts (RO) — surface into Owner pulse
    db_counts = None
    db_mtime = None
    table_count = None
    proc_up = None
    proc_pid = None
    try:
        tiles = alc.db_tile_counts()
        if isinstance(tiles, dict) and tiles.get("ok"):
            c = tiles.get("counts") or {}
            db_counts = {
                k: c[k]
                for k in (
                    "ledger",
                    "petty_cash",
                    "pr_orders",
                    "pr_order_lines",
                    "suppliers",
                    "pr_vendors",
                )
                if k in c
            }
            db_mtime = tiles.get("db_mtime_wita")
            table_count = tiles.get("table_count")
        proc = alc.process_stamp()
        if isinstance(proc, dict):
            proc_up = proc.get("process_up")
            proc_pid = proc.get("pid")
    except Exception:  # noqa: BLE001
        pass
    db_ok = isinstance(db_counts, dict) and bool(db_counts) and src_status in {"OK", "PRESENT", "LIVE"}
    # LIVE = authorised DB READ healthy; legacy_path remains true; pay_mutate stays NO.
    if db_ok and proc_up is True and unpaid_n is not None:
        stamp = "LIVE"
    elif src_status in {"OK", "PRESENT", "LIVE"} and unpaid_n is not None:
        stamp = "PARTIAL"
    else:
        stamp = "PARTIAL" if legacy or src_status not in {"OK", "PRESENT", "LIVE"} else "LIVE"
    # Readable Owner glance: attention first; DB headline second clause
    value = f"unpaid {unpaid_n}{sum_bit} · awaiting Devi {awaiting} · received {received}"
    if isinstance(db_counts, dict) and db_counts:
        value += (
            f" · ledger {db_counts.get('ledger')} · petty {db_counts.get('petty_cash')}"
            f" · PRs {db_counts.get('pr_orders')} · suppliers {db_counts.get('suppliers')}"
        )
    why_bits = [
        "Alchemist sqlite READ into Owner pulse (authorised RO).",
        f"source_status={src_status}.",
        f"process_up={proc_up} pid={proc_pid}.",
        f"DB mtime {db_mtime} · tables {table_count}.",
    ]
    if legacy:
        why_bits.append("legacy_path=true (Alchemist SoT) — not Beta-native purchasing rewrite.")
    if stamp == "LIVE":
        why_bits.append("LIVE = real unpaid/PR/DB counts readable; NOT a pay-run and NOT commissioned.")
    else:
        why_bits.append("PARTIAL — DB/process incomplete; not greenwashed.")
    why_bits.append("Pay/mutate stays NO. Finance SoD unchanged. No invented balances.")
    return _tile(
        id="purchasing",
        what="Purchasing / Alchemist",
        state=stamp,
        value=value,
        href=href,
        why=" ".join(why_bits),
        source="uma_alchemist_ro.project_attention_summary+db_tile_counts",
        extra={
            "unpaid_ledger_count": unpaid_n,
            "unpaid_ledger_sum": unpaid_sum,
            "awaiting_devi_count": awaiting,
            "received_count": received,
            "legacy": legacy,
            "legacy_path": legacy,
            "href_petty": "/bzg/uma-blu/petty",
            "href_alchemist_ro": "/api/owner/alchemist-ro",
            "db_table_count": table_count,
            "db_counts_headline": db_counts,
            "db_mtime_wita": db_mtime,
            "process_up": proc_up,
            "process_pid": proc_pid,
            "pay_mutate": False,
            "db_read_ok": db_ok,
        },
    )


def _fitness_tile() -> dict[str, Any]:
    href = "/owner/fitness"
    try:
        from core.owner_fitness_ro import load_fitness_ro

        payload = load_fitness_ro()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="fitness",
            what="Fitness / Spartacus day",
            state="EMPTY",
            value=None,
            href=href,
            why=f"Fitness RO failed ({type(exc).__name__}).",
            source="owner_fitness_ro",
        )
    if not payload.get("ok"):
        return _tile(
            id="fitness",
            what="Fitness / Spartacus day",
            state="EMPTY",
            value=None,
            href=href,
            why=payload.get("reason") or "Fitness SoT not readable.",
            source="owner_fitness_ro",
        )
    day = payload.get("today_day") or {}
    plan = payload.get("today_plan") or {}
    day_num = day.get("day_num")
    tasks = plan.get("tasks") or []
    done = sum(1 for t in tasks if isinstance(t, dict) and t.get("done"))
    total = plan.get("task_count")
    if total is None:
        total = len(tasks)
    wo = []
    if day.get("wo1_done"):
        wo.append("WO1")
    if day.get("wo2_done"):
        wo.append("WO2")
    value = f"day {day_num} · plan {done}/{total}" + (f" · {','.join(wo)}" if wo else " · workouts open")
    return _tile(
        id="fitness",
        what="Fitness / Spartacus day",
        state="LIVE" if payload.get("reason") == "V1_RO_OK" else "PARTIAL",
        value=value,
        href=href,
        why="From /api/owner/fitness-ro (Spartacus sqlite RO). Fitness ≠ HR.",
        source="owner_fitness_ro",
        extra={"today_day": day_num, "plan_done": done, "plan_total": total},
    )


def _backup_tile() -> dict[str, Any]:
    href = "/ops/backup-health-1"
    try:
        from core.backup_health1 import build_board

        board = build_board()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="backup",
            what="Backup / pipe health",
            state="EMPTY",
            value=None,
            href=href,
            why=f"Backup health loader failed ({type(exc).__name__}).",
            source="backup_health1",
        )
    stamps = board.get("stamps") or []
    by_id = {s.get("id"): s for s in stamps if isinstance(s, dict)}
    last = by_id.get("last_backup") or {}
    atrium = by_id.get("atrium_snapshot") or {}
    drill = by_id.get("restore_drill") or {}
    # Pipe / external route health (optional)
    pipe = None
    try:
        from core import external_route_health as erh

        lat = erh.load_latest() if hasattr(erh, "load_latest") else None
        if isinstance(lat, dict):
            overall = lat.get("overall") or {}
            pipe = {
                "class": overall.get("class"),
                "color": overall.get("color"),
                "as_of_wita": lat.get("as_of_wita"),
                "summary": overall.get("summary"),
            }
    except Exception:  # noqa: BLE001
        pipe = None

    bits = []
    if last.get("status"):
        bits.append(f"backup {last.get('status')}")
    if atrium.get("status"):
        bits.append(f"atrium snap {atrium.get('status')}")
    if drill.get("status"):
        bits.append(f"drill {drill.get('status')}")
    if pipe and pipe.get("class"):
        bits.append(f"pipe {pipe.get('class')}/{pipe.get('color')}")

    # Honesty: STALE atrium → PARTIAL; invented flags must stay false
    invented = bool(board.get("invented_backup_ok") or board.get("fake_backup_success"))
    if invented:
        return _tile(
            id="backup",
            what="Backup / pipe health",
            state="BLOCKED",
            value=None,
            href=href,
            why="Backup board flagged invented success — refused on Owner Home.",
            source="backup_health1",
        )
    if not bits:
        return _tile(
            id="backup",
            what="Backup / pipe health",
            state="EMPTY",
            value=None,
            href=href,
            why="Backup health board returned no usable stamps.",
            source="backup_health1",
        )
    stale = atrium.get("status") == "STALE" or atrium.get("stale") is True
    atrium_fresh = (not stale) and bool(atrium.get("status")) and str(atrium.get("status")).upper() not in {
        "STALE", "MISSING", "EMPTY", "UNKNOWN", "NONE", ""
    }
    last_ok = str(last.get("status") or "").upper() in {"PRESENT", "OK", "LIVE", "FRESH", "CURRENT"}
    # LIVE only with real fresh atrium snap evidence — never invent LIVE from STALE/AMBER alone
    if atrium_fresh and last_ok and not (pipe and pipe.get("color") == "AMBER"):
        stamp = "LIVE"
    else:
        stamp = "PARTIAL"

    def _asof(row: dict) -> str:
        for k in ("as_of_wita", "freshness", "when", "mtime_wita", "detail"):
            v = row.get(k)
            if v:
                return str(v)[:40]
        return ""

    last_asof = _asof(last)
    atrium_asof = _asof(atrium)
    drill_note = str(drill.get("note") or drill.get("detail") or "")[:48]
    deep_bits: list[str] = []
    if last.get("status"):
        deep_bits.append(
            f"backup {last.get('status')}" + (f" @{last_asof}" if last_asof else "")
        )
    if atrium.get("status"):
        deep_bits.append(
            f"atrium snap {atrium.get('status')}"
            + (f" @{atrium_asof}" if atrium_asof else "")
        )
    if drill.get("status"):
        deep_bits.append(f"drill {drill.get('status')}")
    if pipe and pipe.get("class"):
        deep_bits.append(f"pipe {pipe.get('class')}/{pipe.get('color')}")
    value = " · ".join(deep_bits or bits)
    freshness_label = "STALE atrium snap" if stale else ("fresh atrium snap" if atrium_fresh else "atrium snap not fresh")
    if stale:
        value = f"PARTIAL · {freshness_label} · " + " · ".join(deep_bits or bits)
    elif stamp == "LIVE":
        value = f"LIVE · {freshness_label} · " + " · ".join(deep_bits or bits)
    else:
        value = f"PARTIAL · {freshness_label} · " + " · ".join(deep_bits or bits)
    why = (
        "PULSE-LEADS-BACKUP-HONESTY-2: BACKUP-HEALTH-1 + external_route_health. "
        + (
            "Atrium snapshot STALE — keep PARTIAL; do not invent LIVE fresh backup. "
            if stale
            else (
                "Atrium snap fresh evidence present. "
                if atrium_fresh
                else "Atrium snap not qualifying as fresh — keep PARTIAL. "
            )
        )
        + (
            "Pipe AMBER (CF Access / unauth probe). "
            if (pipe and pipe.get("color") == "AMBER")
            else ""
        )
        + f"Drill={drill.get('status')}"
        + (
            f" ({drill_note})"
            if drill_note and drill_note != str(drill.get("status") or "")
            else ""
        )
        + ". Last backup ≠ restore proven. NAS/B2 desk tile is separate LIVE inventory stamp. "
        "staff_ready false."
    )
    return _tile(
        id="backup",
        what="Backup / pipe health",
        state=stamp,
        value=value,
        href=href,
        why=why,
        source="backup_health1+external_route_health",
        extra={
            "last_backup_status": last.get("status"),
            "last_backup_as_of": last_asof or None,
            "atrium_snapshot_status": atrium.get("status"),
            "atrium_as_of": atrium_asof or None,
            "atrium_fresh": atrium_fresh,
            "atrium_stale": stale,
            "precise_state": "PARTIAL_STALE_ATRIUM" if stale else ("LIVE" if stamp == "LIVE" else "PARTIAL"),
            "drill_status": drill.get("status"),
            "drill_note": drill_note or None,
            "pipe": pipe,
            "href_pipe_note": "external-route-health-latest.json",
            "href_nas_b2_desk": "/content-2.0",
            "stale_atrium": stale,
        },
    )




def _nas_b2_tile() -> dict[str, Any]:
    """Owner WORKFLOW: honest NAS/B2 inventory desk stamp — no fake index completeness."""
    href = "/content-2.0"
    try:
        from core import nas_b2_desk_stamp1 as nasb2

        payload = nasb2.load_nas_b2_desk()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="nas_b2_desk",
            what="NAS / B2 desk inventory",
            state="EMPTY",
            value=None,
            href=href,
            why=f"nas_b2_desk_stamp1 failed ({type(exc).__name__}).",
            source="nas_b2_desk_stamp1",
        )
    if not isinstance(payload, dict) or not payload.get("ok"):
        return _tile(
            id="nas_b2_desk",
            what="NAS / B2 desk inventory",
            state="BLOCKED",
            value=None,
            href=href,
            why="NAS/B2 desk stamp not ok — refused greenwash / invent.",
            source="nas_b2_desk_stamp1",
        )
    return _tile(
        id="nas_b2_desk",
        what="NAS / B2 desk inventory",
        state="LIVE",
        value=payload.get("value_line"),
        href=href,
        why=(
            "Owner/Content desk stamp from PROVE-NAS-B2-INVENTORY-1-DEEPEN. "
            "Shallow Media/editable/stock counts + B2 ModTime freshness + 00/02 denied honest. "
            "full_tree_indexed=false · restore NOT_RUN · Library sqlite ≠ NAS tree."
        ),
        source="nas_b2_desk_stamp1.load_nas_b2_desk",
        extra={
            "full_tree_indexed": False,
            "restore": "NOT_RUN",
            "invented_counts": False,
            "write": False,
            "pack": payload.get("pack"),
            "nas_counts": (payload.get("nas") or {}).get("counts"),
            "permission_denied_honest": (payload.get("nas") or {}).get("permission_denied_honest"),
            "b2_freshness": (payload.get("b2") or {}).get("freshness_headline_wita"),
            "library_db_honesty": payload.get("library_db_honesty"),
        },
    )


def _metricool_schedule_tile() -> dict[str, Any]:
    """GGV Social glance: brands + schedule freshness READ — no engagement invent."""
    href = "/ggv-ops-pack#social"
    try:
        from core import metricool_schedule_glance1 as msg

        payload = msg.load_schedule_glance()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="metricool_schedule",
            what="Metricool schedule READ",
            state="EMPTY",
            value=None,
            href=href,
            why=f"metricool_schedule_glance1 failed ({type(exc).__name__}).",
            source="metricool_schedule_glance1",
        )
    if not isinstance(payload, dict) or not payload.get("ok"):
        return _tile(
            id="metricool_schedule",
            what="Metricool schedule READ",
            state="BLOCKED",
            value=None,
            href=href,
            why="Schedule glance stamp not ok — refused invent engagement.",
            source="metricool_schedule_glance1",
        )
    return _tile(
        id="metricool_schedule",
        what="Metricool schedule READ",
        state="LIVE",
        value=payload.get("value_line"),
        href=href,
        why=(
            "MCP getBrandSettings + getScheduledPosts READ stamped. "
            "Brands/list/schedule freshness only. WRITE OFF. engagement=null."
        ),
        source="metricool_schedule_glance1.load_schedule_glance",
        extra={
            "metricool_write": False,
            "invented_engagement": False,
            "engagement": None,
            "brands_count": (payload.get("brands") or {}).get("count"),
            "schedule_read": payload.get("schedule_read"),
            "pack": payload.get("pack"),
        },
    )


def _gws_tile() -> dict[str, Any]:
    """Owner WORKFLOW card: bind GWS draft-only / MCP LIVE stamp — no invented counts."""
    href = "/api/owner/gws-ro"
    try:
        from core import gws_draft_workflows1 as gws

        payload = gws.load_gws_ro()
    except Exception as exc:  # noqa: BLE001
        return _tile(
            id="gws_workflow",
            what="GWS workflow (draft-only)",
            state="EMPTY",
            value=None,
            href=href,
            why=f"gws_ro loader failed ({type(exc).__name__}).",
            source="gws_draft_workflows1",
        )
    if not isinstance(payload, dict) or not payload.get("ok"):
        return _tile(
            id="gws_workflow",
            what="GWS workflow (draft-only)",
            state="BLOCKED",
            value=None,
            href=href,
            why="gws-ro stamp not ok — refused greenwash.",
            source="gws_draft_workflows1",
        )
    consuming = payload.get("consuming") or []
    mcp_n = sum(1 for c in consuming if isinstance(c, dict) and c.get("status") in ("MCP_LIVE", "PULSE_CONSUMING"))
    gmail_policy = payload.get("gmail_policy") or "DRAFT_ONLY"
    value = f"Gmail {gmail_policy} · Drive READ · Calendar READ · MCP surfaces {mcp_n}"
    card = payload.get("owner_workflow_card") or {}
    return _tile(
        id="gws_workflow",
        what="GWS workflow (draft-only)",
        state="LIVE",
        value=value,
        href=href,
        why=(
            "Owner WORKFLOW card from /api/owner/gws-ro. MCP paths LIVE for executor READ "
            "(+ Gmail draft). Send/Drive-write/Calendar-write OFF. No invented message/event/file counts. "
            f"pack={payload.get('workflow_pack') or payload.get('pack')}."
        ),
        source="gws_draft_workflows1.load_gws_ro",
        extra={
            "gmail_policy": gmail_policy,
            "gmail_send": False,
            "drive_write": False,
            "calendar_write": False,
            "invented_counts": False,
            "mcp_servers": payload.get("mcp_servers"),
            "workflow_pack": payload.get("workflow_pack") or card.get("pack"),
            "href_gws_ro": href,
        },
    )


def load_pulse_ro() -> dict[str, Any]:
    tiles = [
        _occ_tile(),
        _kuta_tile(),
        _bzg_night_tile(),
        _leads_tile(),
        _purchasing_tile(),
        _gws_tile(),
        _nas_b2_tile(),
        _metricool_schedule_tile(),
        _fitness_tile(),
        _backup_tile(),
    ]
    # Drop none — all seven always present with honesty (HIDE only if we explicitly mark hide)
    visible = [t for t in tiles if t.get("state") != "HIDE"]
    live_n = sum(1 for t in visible if t.get("state") == "LIVE")
    partial_n = sum(1 for t in visible if t.get("state") == "PARTIAL")
    empty_n = sum(1 for t in visible if t.get("state") == "EMPTY")
    blocked_n = sum(1 for t in visible if t.get("state") == "BLOCKED")
    return {
        "ok": True,
        "reason": "PULSE_RO_OK",
        "staff_ready": False,
        "human_commissioned": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN",
        "migration_state": "PARTIAL",
        "read_only": True,
        "as_of_wita": _now_wita(),
        "surface": "owner_live_pulse",
        "pack": "UX-PACK-09b",
        "honesty": (
            "Dense Owner evening-brief style pulse (09b + GWS + NAS/B2 desk + Metricool schedule glance). "
            "LIVE/PARTIAL/EMPTY/BLOCKED stamps only. No invented metrics. "
            "Finance SoD unchanged. staff_ready=false."
        ),
        "tiles": visible,
        "counts": {
            "tiles": len(visible),
            "LIVE": live_n,
            "PARTIAL": partial_n,
            "EMPTY": empty_n,
            "BLOCKED": blocked_n,
        },
        "banner": "Owner Home Pulse · SoT glances · missing stays missing",
    }


if __name__ == "__main__":
    import json as _j

    print(_j.dumps(load_pulse_ro(), indent=2, default=str)[:4000])
