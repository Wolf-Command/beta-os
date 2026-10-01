#!/usr/bin/env python3
"""Pack 1 — Owner cockpit. Read-only composition of the live pulse plus the
questions the 10-card pulse dropped.

Does not rebuild Money, the Command Brief, a 14/14 system tile, or a fresh R2
measurement. Absent or stale sources stay UNKNOWN or PARTIAL with a why.
staff_ready stays false. Writes are refused.

GET /wolf and /owner-empire-pack stay behind the owner JWT. This module does
not change that wall.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))

V1 = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system")
BRIEF_DIR = Path(
    "/Users/wolfterminal/WolfCommandSystem/WolfCommand/06-Strategy/Command-Briefs"
)
R2_STATE = V1 / "state" / "r2-sync-state.json"
OFFBOX = V1 / "state" / "atlas-control" / "offbox-backup.json"
DAEMON_STATUS = V1 / "state" / "daemon-status.json"
WOLF_TASKS = V1 / "wolf-desk" / "tasks.json"
PEACHES_THREADS = V1 / "peaches-desk" / "threads.jsonl"
BETA_THREADS = Path("/Users/wolfterminal/beta-os/peaches-desk/threads.jsonl")

DESK_HREFS = {
    "atrium_occ": "/amg/sales-desk#occ",
    "kuta_rates": "/amg/sales-desk#kuta",
    "bzg_night": "/bzg/uma-blu#closes",
}
PERSONAL_IDS = {"fitness"}


def _now() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _today() -> str:
    return datetime.now(WITA).date().isoformat()


def _card(
    *,
    id: str,
    what: str,
    state: str,
    value: Any,
    href: str | None,
    why: str,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": id,
        "what": what,
        "state": state,
        "value": value,
        "href": href,
        "where": href,
        "why": why,
        "source": source,
        "live": state == "LIVE",
        "opens_job": False,
    }
    if extra:
        out.update(extra)
    return out


def _read_json(path: Path) -> tuple[Any, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def _pulse() -> dict[str, Any]:
    try:
        from core.owner_pulse_ro import load_pulse_ro

        payload = load_pulse_ro()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "tiles": [],
            "honesty": "Pulse loader failed. No tile was invented to fill the gap.",
        }
    if not isinstance(payload, dict):
        return {"ok": False, "error": "pulse_not_object", "tiles": []}
    tiles = []
    for tile in payload.get("tiles") or []:
        if not isinstance(tile, dict):
            continue
        row = dict(tile)
        forced = DESK_HREFS.get(str(row.get("id") or ""))
        if forced:
            row["href"] = forced
            row["where"] = forced
            row["desk"] = "eng_proved"
        if row.get("id") == "bzg_night":
            row["today_api"] = "/api/bzg/uma-blu/today"
            row["today_api_auth"] = "cloudflare_jwt_fail_closed"
        tiles.append(row)
    payload = dict(payload)
    payload["tiles"] = tiles
    payload["staff_ready"] = False
    return payload


def _brief_card() -> dict[str, Any]:
    day = _today()
    path = BRIEF_DIR / f"Brief-{day}.md"
    if not path.is_file():
        return _card(
            id="brief",
            what="Command Brief",
            state="UNKNOWN",
            value=None,
            href=None,
            why=(
                f"No vault file Brief-{day}.md. The V1 master.status brief stamp "
                "is not a rebuilt brief, so it is not shown as Ready."
            ),
            source=str(path),
            extra={"rebuilt": False, "v1_stamp_used_as_live": False},
        )
    try:
        size = path.stat().st_size
    except OSError as exc:
        return _card(
            id="brief",
            what="Command Brief",
            state="UNKNOWN",
            value=None,
            href=None,
            why=f"Brief file stat failed ({type(exc).__name__}). No Ready stamp substituted.",
            source=str(path),
            extra={"rebuilt": False},
        )
    return _card(
        id="brief",
        what="Command Brief",
        state="PARTIAL",
        value=f"Brief-{day}.md present",
        href=None,
        why=(
            "Today's vault file is on disk. This cockpit did not rebuild the brief "
            "and did not copy the V1 'Ready' stamp. There is no Beta brief desk to open."
        ),
        source=str(path),
        extra={"rebuilt": False, "bytes": size, "v1_stamp_used_as_live": False, "body_copied": False},
    )


def _r2_card() -> dict[str, Any]:
    offbox, off_err = _read_json(OFFBOX)
    gap, gap_err = _read_json(R2_STATE)
    file_record: dict[str, Any] = {}
    if isinstance(gap, dict):
        for mode in ("fast", "slow"):
            summary = gap.get(f"gap_summary_{mode}") or {}
            if not isinstance(summary, dict):
                continue
            file_record[mode] = {
                "last_gap": gap.get(f"last_gap_{mode}"),
                "at": summary.get("at"),
                "objects_missing_found": summary.get("objects_missing_found"),
                "objects_still_missing": summary.get("objects_still_missing"),
                "mappings_measured": summary.get("mappings_measured"),
                "measure_only": summary.get("measure_only"),
            }
    verdict = None
    checked = None
    if isinstance(offbox, dict):
        verdict = offbox.get("verdict")
        checked = offbox.get("checked_at")
    if off_err and gap_err:
        return _card(
            id="r2_gap",
            what="R2 backup gap",
            state="UNKNOWN",
            value=None,
            href=None,
            why="Neither the off-box verdict nor r2-sync-state.json could be read. Absent is not zero.",
            source=str(OFFBOX),
            extra={"live_absent_count": None, "remeasured": False},
        )
    why = (
        "Not re-measured this pack. "
        f"offbox-backup.json verdict is {verdict or off_err} at {checked or 'unknown'}. "
        "r2-sync-state.json still holds an August gap summary, including objects_still_missing 0. "
        "That zero is the file's old line, not a current absent count. "
        "Cloudflare_R2 being configured is not a workflow."
    )
    return _card(
        id="r2_gap",
        what="R2 backup gap",
        state="PARTIAL",
        value=f"offbox {verdict or 'UNREAD'} · gap file not re-measured",
        href=None,
        why=why,
        source=str(OFFBOX),
        extra={
            "live_absent_count": None,
            "remeasured": False,
            "v1_zero_absent_used_as_live": False,
            "offbox_verdict": verdict,
            "offbox_checked_at": checked,
            "may_retire_b2": offbox.get("may_retire_b2") if isinstance(offbox, dict) else None,
            "gap_file": str(R2_STATE),
            "gap_file_record": file_record,
            "gap_read_error": gap_err,
        },
    )


def _system_card() -> dict[str, Any]:
    data, err = _read_json(DAEMON_STATUS)
    if err or not isinstance(data, dict):
        return _card(
            id="system",
            what="System faults",
            state="UNKNOWN",
            value=None,
            href=None,
            why=f"daemon-status.json {err or 'unreadable'}. No 14/14 figure was invented. No job was opened.",
            source=str(DAEMON_STATUS),
            extra={"opens_job": False, "treated_as_green": False},
        )
    daemons = {
        key: row
        for key, row in data.items()
        if key != "_events" and isinstance(row, dict)
    }
    ok = sum(1 for row in daemons.values() if row.get("status") in ("ok", "green", "alive"))
    return _card(
        id="system",
        what="System faults",
        state="PARTIAL",
        value=f"{len(daemons)} daemon records in the V1 stamp, {ok} status ok. No job opened.",
        href=None,
        why=(
            "The V1 stamp is a present-file count. Green-from-present is the failure this tile existed to catch. "
            "This cockpit does not open a job from a fault, and it does not report the stamp as Beta 14/14 green."
        ),
        source=str(DAEMON_STATUS),
        extra={
            "opens_job": False,
            "treated_as_green": False,
            "daemon_records": len(daemons),
            "status_ok_records": ok,
            "fault_job_id": None,
        },
    )


def _asks_card() -> dict[str, Any]:
    data, err = _read_json(WOLF_TASKS)
    if err or not isinstance(data, dict):
        return _card(
            id="asks",
            what="Asks from the team",
            state="UNKNOWN",
            value=None,
            href=None,
            why=f"wolf-desk/tasks.json {err or 'unreadable'}. No ask was invented.",
            source=str(WOLF_TASKS),
            extra={"answer_in_place": False, "open_count": None},
        )
    rows = data.get("tasks") if isinstance(data.get("tasks"), list) else []
    open_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("bucket") or "") == "ask"
        and row.get("status") != "done"
    ]
    count = len(open_rows)
    state = "EMPTY" if count == 0 else "PARTIAL"
    return _card(
        id="asks",
        what="Asks from the team",
        state=state,
        value=f"{count} open asks in the V1 desk file",
        href=None,
        why=(
            "Read of wolf-desk/tasks.json, bucket ask, status not done. "
            "Beta has no answer-in-place rail, so an empty read is not a rebuilt desk."
        ),
        source=str(WOLF_TASKS),
        extra={
            "answer_in_place": False,
            "open_count": count,
            "task_rows_read": len(rows),
            "titles_copied": False,
        },
    )


def _peaches_card() -> dict[str, Any]:
    if not PEACHES_THREADS.is_file():
        return _card(
            id="peaches",
            what="Talk to Peaches",
            state="UNKNOWN",
            value=None,
            href=None,
            why="V1 peaches-desk/threads.jsonl is missing. No LIVE thread desk was invented.",
            source=str(PEACHES_THREADS),
            extra={"live": False, "beta_store": BETA_THREADS.is_file(), "text_included": False},
        )
    newest = None
    count = 0
    try:
        for line in PEACHES_THREADS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            count += 1
            rec = json.loads(line)
            ts = rec.get("ts")
            if isinstance(ts, str) and (newest is None or ts > newest):
                newest = ts
    except (OSError, json.JSONDecodeError) as exc:
        return _card(
            id="peaches",
            what="Talk to Peaches",
            state="UNKNOWN",
            value=None,
            href=None,
            why=f"Thread store read failed ({type(exc).__name__}). Not marked LIVE.",
            source=str(PEACHES_THREADS),
            extra={"live": False, "text_included": False},
        )
    beta_store = BETA_THREADS.is_file()
    return _card(
        id="peaches",
        what="Talk to Peaches",
        state="PARTIAL",
        value=f"{count} V1 threads, newest {newest}. Beta store {'present' if beta_store else 'absent'}.",
        href=None,
        why=(
            "The V1 jsonl was counted. Message text was not copied. "
            "Beta has no threads.jsonl, so this is not a LIVE Peaches desk."
        ),
        source=str(PEACHES_THREADS),
        extra={
            "live": False,
            "beta_store": beta_store,
            "thread_count": count,
            "newest_ts": newest,
            "text_included": False,
        },
    )


def _content_card() -> dict[str, Any]:
    href = "/content/tick-draft"
    try:
        from core import content_tick_draft as tick

        cycle = tick.load_cycle()
        rows = tick.queue_rows()
    except Exception as exc:  # noqa: BLE001
        return _card(
            id="content",
            what="Content tick desk",
            state="PARTIAL",
            value=None,
            href=href,
            why=f"Tick-draft loader failed ({type(exc).__name__}). Publish stays off. Href is the eng-proved desk.",
            source="content_tick_draft",
            extra={"publish": "OFF", "desk": "eng_proved"},
        )
    info = cycle.get("cycle") or {}
    queue_ids = [row.get("id") for row in rows if isinstance(row, dict) and row.get("id")]
    return _card(
        id="content",
        what="Content tick desk",
        state="PARTIAL",
        value=(
            f"{info.get('brand')} {info.get('cycle_start')}→{info.get('cycle_end')} "
            f"· queue {queue_ids[-1] if queue_ids else 'none'} · publish OFF"
        ),
        href=href,
        why=(
            "Opens the Habitat tick desk from Pack 4. One brand. Publish stays off. "
            "This is not the six brand boards and not a content-health score."
        ),
        source="content_tick_draft.load_cycle",
        extra={
            "publish": "OFF",
            "desk": "eng_proved",
            "full_tree_indexed": cycle.get("full_tree_indexed"),
            "haikal_upload_retest": cycle.get("haikal_upload_retest"),
            "queue_ids": queue_ids,
        },
    )


def _money_card() -> dict[str, Any]:
    return _card(
        id="money",
        what="Money",
        state="PARTIAL",
        value=None,
        href=None,
        why=(
            "No money figure was read for this card. Finance separation of duties stays closed. "
            "Atrium finance screens are Pack 5, not this cockpit."
        ),
        source="not_read",
        extra={"figure_invented": False, "sod": "closed"},
    )


def _trading_card() -> dict[str, Any]:
    href = "/owner/trading"
    try:
        from core.owner_trading_ro import load_trading_ro

        payload = load_trading_ro(journal_history_limit=0)
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": type(exc).__name__}
    return _card(
        id="trading",
        what="Trading (personal)",
        state="PARTIAL",
        value="paper desk · no broker",
        href=href,
        why=(
            "Wave 8 personal rail. Existing /api/owner/trading-ro is PARTIAL paper. "
            "Not 14 cards. Not staff primary. Nothing trades. Holdings were not copied onto this card."
        ),
        source="owner_trading_ro.load_trading_ro",
        extra={
            "staff_primary": False,
            "live_broker": False,
            "migration_state": payload.get("migration_state") if isinstance(payload, dict) else None,
            "holdings_copied": False,
            "api": "/api/owner/trading-ro",
        },
    )


def _personal_rail(pulse: dict[str, Any]) -> list[dict[str, Any]]:
    rail = []
    for tile in pulse.get("tiles") or []:
        if tile.get("id") in PERSONAL_IDS:
            row = dict(tile)
            row["pulse_state"] = tile.get("state")
            row["state"] = "PARTIAL"
            row["live"] = False
            row["staff_primary"] = False
            row["rail"] = "owner_personal"
            row["why"] = (
                str(tile.get("why") or "")
                + " Personal rail only. The day counter is a read, not the Spartacus program, and it is not staff primary."
            )
            rail.append(row)
    rail.append(_trading_card())
    return rail


def load_cockpit() -> dict[str, Any]:
    pulse = _pulse()
    tiles = [t for t in (pulse.get("tiles") or []) if isinstance(t, dict)]
    staff = [t for t in tiles if t.get("id") not in PERSONAL_IDS]
    restored = [
        _brief_card(),
        _r2_card(),
        _system_card(),
        _asks_card(),
        _peaches_card(),
        _content_card(),
        _money_card(),
    ]
    return {
        "ok": True,
        "pack": "PACK-01",
        "reason": "OWNER_COCKPIT_RO",
        "staff_ready": False,
        "human_proven": False,
        "read_only": True,
        "writes": False,
        "as_of_wita": _now(),
        "surface": "owner_cockpit",
        "honesty": (
            "Live pulse cards stay, including UNKNOWN lines. Restored questions are "
            "UNKNOWN or PARTIAL when the source is absent, stale, or not a Beta desk. "
            "Fitness and trading are the personal rail, not staff primary. "
            "staff_ready=false."
        ),
        "auth": {
            "empire_page": (
                "GET /wolf and /owner-empire-pack call _require_owner_empire. "
                "Without a Cloudflare JWT the page is 403. This pack does not change that."
            ),
            "cockpit_json": (
                "GET /api/owner/cockpit is read-only and registered beside the other "
                "owner read routes, before the JWT wall, same pattern as /api/owner/pulse-ro."
            ),
            "cockpit_page": (
                "GET /owner/cockpit is a read board of that JSON. It is not the empire page."
            ),
        },
        "pulse": pulse,
        "staff_primary": staff,
        "restored": restored,
        "personal_rail": _personal_rail(pulse),
        "counts": {
            "pulse_tiles": len(tiles),
            "staff_primary": len(staff),
            "restored": len(restored),
        },
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "cockpit_read_only",
        "pack": "PACK-01",
        "staff_ready": False,
        "writes": False,
        "human_proven": False,
    }


if __name__ == "__main__":
    print(json.dumps(load_cockpit(), indent=2, default=str)[:5000])
