#!/usr/bin/env python3
"""Beta Voice boards AMG/BZG/GGV — DISPLAY/RESPONSE TRACKING READ-ONLY.

NEVER send mail/Telegram. never_send=true hard-coded.
staff_ready=false. Beta only.
"""
from __future__ import annotations
import os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
WS = Path.home() / ".openclaw/workspace/wolf-system/dashboards"
ENTITIES = ("amg", "bzg", "ggv")

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "never_send": True,
        "mail_send": False, "telegram_send": False, "auto_reply_fire": False,
        "as_of_wita": _now_wita(), "surface": "voice_boards",
    }
    out.update(extra)
    return out

def _entity_ro(entity: str) -> dict[str, Any]:
    html = WS / f"{entity}-voice.html"
    py = WS / f"{entity}_voice.py"
    out: dict[str, Any] = {"entity": entity, "html_present": html.is_file(),
                           "py_present": py.is_file()}
    if html.is_file():
        try:
            t = html.read_text(encoding="utf-8", errors="replace")
            out["html_bytes"] = len(t)
            title = re.search(r"<title[^>]*>(.*?)</title>", t, re.I | re.S)
            out["title"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else None
            # API-ish references for display tracking
            out["api_refs"] = sorted(set(re.findall(r"/api/[a-zA-Z0-9_./-]+", t)))[:20]
            out["has_send_ui_markers"] = bool(re.search(r"\b(send|telegram|mailto)\b", t, re.I))
        except OSError as e:
            out["html_error"] = str(e)
    if py.is_file():
        try:
            t = py.read_text(encoding="utf-8", errors="replace")
            out["py_bytes"] = len(t)
            # Detect defs — display only
            out["py_defs"] = re.findall(r"^def\s+(\w+)\s*\(", t, re.M)[:30]
            # Hard refuse any send helper exposure
            sendish = [d for d in out["py_defs"] if re.search(r"send|telegram|mail|reply|fire", d, re.I)]
            out["sendish_defs_detected"] = sendish
            out["send_policy"] = "NEVER_INVOKE — Beta RO refuses all send paths"
        except OSError as e:
            out["py_error"] = str(e)
    return out

def load_voice_ro(entity: str | None = None) -> dict[str, Any]:
    if entity:
        entity = entity.lower().strip()
        if entity not in ENTITIES:
            return _stamp(False, "BAD_ENTITY", entity=entity, allowed=list(ENTITIES))
        one = _entity_ro(entity)
        return _stamp(one.get("html_present") or one.get("py_present"), "V1_RO_OK",
                      entities={entity: one},
                      banner=f"{entity.upper()} voice RO display/tracking only. NEVER send.")
    entities = {e: _entity_ro(e) for e in ENTITIES}
    ok = any(v.get("html_present") or v.get("py_present") for v in entities.values())
    return _stamp(
        ok, "V1_RO_OK" if ok else "NO_SOT_YET",
        entities=entities,
        banner="Voice boards RO (AMG/BZG/GGV). Display/response tracking only. NEVER send mail/TG.",
    )

def load_amg_voice_ro():
    return load_voice_ro("amg")
def load_bzg_voice_ro():
    return load_voice_ro("bzg")
def load_ggv_voice_ro():
    return load_voice_ro("ggv")

if __name__ == "__main__":
    import json
    print(json.dumps(load_voice_ro(), indent=2)[:2500])
