"""Load ACTIVE+APPROVED brand memory for planning."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import active_memory, skill_envelope  # noqa: E402


def run(conn, brand_id: str, **_kwargs: Any) -> dict:
    items = active_memory(conn, brand_id)
    facts = [i for i in items if i["type"] == "FACT"]
    rules = [i for i in items if i["type"] == "RULE"]
    decisions = [i for i in items if i["type"] == "DECISION"]
    other = [i for i in items if i["type"] not in ("FACT", "RULE", "DECISION")]
    missing = []
    if not facts:
        missing.append("No ACTIVE APPROVED FACT memory for brand")
    if not rules:
        missing.append("No ACTIVE APPROVED RULE memory for brand")
    conf = 0.9 if facts and rules else (0.55 if items else 0.2)
    return skill_envelope(
        {
            "brand_id": brand_id,
            "count": len(items),
            "facts": [{"id": i["id"], "text": i["text"], "source_id": i["source_id"]} for i in facts],
            "rules": [{"id": i["id"], "text": i["text"], "source_id": i["source_id"]} for i in rules],
            "decisions": [{"id": i["id"], "text": i["text"], "source_id": i["source_id"]} for i in decisions],
            "other": [{"id": i["id"], "type": i["type"], "text": i["text"]} for i in other],
        },
        evidence=[{"kind": "memory_items", "count": len(items), "brand_id": brand_id}],
        confidence=conf,
        assumptions=["Only ACTIVE+APPROVED memory is used for planning"],
        missing_information=missing,
    )
