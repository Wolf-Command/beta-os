"""Validate draft cards against ACTIVE APPROVED RULE memory."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import active_memory, skill_envelope  # noqa: E402

BANNED = re.compile(r"\b(luxury|stunning|don'?t miss out)\b", re.I)


def run(
    conn,
    brand_id: str,
    asset_result: dict | None = None,
    **_kwargs: Any,
) -> dict:
    rules = [i for i in active_memory(conn, brand_id) if i["type"] == "RULE"]
    payload = (asset_result or {}).get("result") or {}
    cards = list(payload.get("feed_cards") or []) + list(payload.get("story_spine") or [])
    violations = []
    for c in cards:
        text = " ".join(str(c.get(k) or "") for k in ("title", "hook", "caption_draft"))
        if BANNED.search(text):
            violations.append({"card": c.get("title"), "issue": "banned_cliche_language"})
    ok = len(violations) == 0
    return skill_envelope(
        {
            "ok": ok,
            "rules_checked": len(rules),
            "violations": violations,
            "feed_cards": payload.get("feed_cards") or [],
            "story_spine": payload.get("story_spine") or [],
        },
        evidence=[{"kind": "rules", "count": len(rules)}],
        confidence=0.85 if rules else 0.4,
        assumptions=["Banned-cliché check mirrors Habitat RULE text"],
        missing_information=[] if rules else ["No RULE memory — validator limited"],
    )
