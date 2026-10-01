#!/usr/bin/env python3
"""Pack 4 — Habitat tick falls back to a Misa queue item. Publish stays off."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import content_tick_draft as tick  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    before = tick.CYCLE_FILE.stat()
    cycle = tick.load_cycle()
    after = tick.CYCLE_FILE.stat()
    check("cycle ok", cycle.get("ok") is True, str(cycle.get("error")))
    check("habitat", (cycle.get("cycle") or {}).get("brand") == "habitat")
    check(
        "covers today",
        (cycle.get("cycle") or {}).get("cycle_start") == "2026-09-28"
        and (cycle.get("cycle") or {}).get("cycle_end") == "2026-10-11",
    )
    check("six posts", (cycle.get("counts") or {}).get("posts") == 6)
    blank = [c for c in cycle.get("cards") or [] if c.get("kind") == "post"]
    check("post titles blank", bool(blank) and all(c.get("title_blank") for c in blank))
    check("cycle file unchanged", before.st_mtime_ns == after.st_mtime_ns)
    check("publish off", cycle.get("publish") == "OFF" and cycle.get("staff_ready") is False)
    check("haikal retest open", cycle.get("haikal_upload_retest") == "OPEN")
    check("not full tree", cycle.get("full_tree_indexed") is False)

    lib = tick.library_lookup("habitat_RAW_video_habitat-vibe_workers_20260730_001.mov")
    check(
        "known file is library",
        lib.get("where") == "library" and lib.get("library_asset_count") == 48 and lib.get("full_tree_indexed") is False,
        str(lib),
    )
    nas_file = Path("/Volumes/01-Media-Library/Brand-Assets/GGV/logos/goss-group-logo.png")
    nas = tick.library_lookup(str(nas_file))
    check(
        "one existing nas file is nas_only",
        nas_file.is_file() and nas.get("where") == "nas_only" and nas.get("tree_walked") is False and nas.get("full_tree_indexed") is False,
        str(nas),
    )
    missing = tick.library_lookup("pack4-not-a-real-file.mov")
    check(
        "missing file is not a nas inventory",
        missing.get("where") == "not_in_library" and missing.get("tree_walked") is False and missing.get("full_tree_indexed") is False,
        str(missing),
    )

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "tick.sqlite"
        bare = tick.apply_note("s2", db=db)
        check("apply needs a comment", bare.get("error") == "nothing_to_apply")
        note = tick.comment("s2", "Use the tour line already on the card.", db=db)
        check("comment stored", note.get("ok") is True and note.get("kind") == "comment")
        applied = tick.apply_note("s2", db=db)
        check(
            "apply stores note",
            applied.get("ok") is True and applied.get("amanda_session") is False and applied.get("cycle_file_written") is False,
        )
        queued = tick.tick("s2", db=db)
        q = queued.get("queue") or {}
        check(
            "tick queues when draft is blocked",
            queued.get("ok") is True
            and q.get("state") == "QUEUED"
            and q.get("reason") == "metricool_write_blocked"
            and q.get("publish") == "OFF"
            and queued.get("network") is False,
            str(q),
        )
        again = tick.tick("s2", db=db)
        check("tick is idempotent", again.get("idempotent") is True and again.get("queue", {}).get("id") == q.get("id"))

        def ok_draft(card: dict) -> dict:
            return {"ok": True, "draft_id": "MC-DRAFT-TEST", "published": False, "network": False}

        drafted = tick.tick("s1", db=db, draft_client=ok_draft)
        dq = drafted.get("queue") or {}
        check(
            "injected draft is not a publish",
            dq.get("state") == "METRICOOL_DRAFT" and dq.get("metricool_draft_id") == "MC-DRAFT-TEST" and dq.get("publish") == "OFF",
            str(dq),
        )

        def bad_publish(card: dict) -> dict:
            return {"ok": True, "draft_id": "NO", "published": True, "network": True}

        refused = tick.tick("s3", db=db, draft_client=bad_publish)
        check("publish flag refused", refused.get("error") == "publish_refused")
        ids = [row.get("card_id") for row in tick.queue_rows(db)]
        check("refused card not queued", "s3" not in ids, str(ids))

    check("refuse publish", tick.refuse_publish().get("error") == "publish_off")
    check("cycle still unchanged", tick.CYCLE_FILE.stat().st_mtime_ns == before.st_mtime_ns)
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
