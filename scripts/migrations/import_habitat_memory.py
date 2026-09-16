#!/usr/bin/env python3
"""Import Habitat FACT/RULE (clearly stated) else PROPOSED OBSERVATION from export."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wolf_intelligence import content_hash, db_connect, now_iso, write_memory_item  # noqa: E402

SUPPORT = Path("/tmp/wolf-content-plans-for-chatgpt/Habitat-Villas/supporting")
BRAND_ID = "habitat"


# Clearly stated FACTS / RULES from brand kit (do not invent beyond source text).
FACTS = [
    ("Client is GGV (Goss Group Ventures).", "Habitat-Brand.md"),
    ("Company/property owner is PT Keen Eye; GGV provides sales & marketing.", "Habitat-Brand.md"),
    ("Habitat Forest (Habitat 1): Kuta hillside, ocean view near Mandalika circuit; 10 villas; SOLD OUT.", "Habitat-Brand.md"),
    ("Habitat Garden (Habitat 2): Kuta Eat Street / main Kuta road; 18 villas; SOLD OUT; construction halfway; finished units hosting guests.", "Habitat-Brand.md"),
    ("Habitat Vibe (Habitat 3): heart of Kuta, 500m from Kuta Beach; 31 villas; some sold some available; early construction, foundations laid.", "Habitat-Brand.md"),
    ("Primary typeface is Manrope.", "Habitat-Brand.md"),
    ("Primary brand color is #79755B (Warm Brown); Secondary #EAE6D7 (Cream); Alt Primary #A6A28B; White #FFFFFF; Dark #232224.", "Habitat-Brand.md"),
    ("Content update cadence: Every Friday 09:00 WITA — developer Matt discusses construction progress and names owners.", "Habitat-Brand.md"),
    ("NAS brand asset root: /Volumes/01-Media-Library/Brand-Assets/GGV/Habitat", "Habitat-Brand.md"),
    ("Reel engine slug is habitat.", "Habitat-Brand.md"),
    ("Sub-brands include Habitat Garden and Habitat Vibe.", "Habitat-Strategy.md"),
]

RULES = [
    ("Tone: architectural journal-style. Do NOT use clichés: 'luxury', 'stunning', 'don't miss out'. Be restrained, specific (name materials), design-literate.", "Habitat-Brand.md"),
    ("Visual language: NO handheld wobble, NO trending audio — curated, not algorithmic.", "Habitat-Brand.md"),
    ("Voice: property-portfolio polish; clean architecture; lifestyle aspirational; modern and direct confident statements, not flowery copy.", "Habitat-Strategy.md"),
]

OBSERVATIONS_PROPOSED = [
    ("Brand essence described as: considered living, quiet luxury, design-literate restraint, authenticity.", "Habitat-Brand.md"),
    ("Content pillars listed: considered design; quiet luxury of space; community without compromise; materials aging beautifully; weekend morning energy.", "Habitat-Brand.md"),
    ("Instagram grid content ratio from kit: 35% construction / 25% lifestyle / 20% founder-investor / 20% architecture-location.", "Habitat-Brand.md"),
    ("Strategy kit status: KIT-BASED / best-effort — Habitat is raw-only in craft-db; no finished Habitat static/reel to validate against (as of export).", "Habitat-Strategy.md"),
    ("FILM fortnight 14–27 Sep 2026 notes: nobody posts / do not schedule; items include Fri 18 reasons not to buy; Mon 21 first villa Matt sit-down; Wed 23 owner testimonial TBC; Fri 25 hosted walk with Matt.", "FILM-14-27-Sep-2026.md"),
]


def already_imported(conn, source_id: str, text: str) -> bool:
    h = text.strip()
    row = conn.execute(
        "SELECT 1 FROM memory_items WHERE brand_id=? AND source_id=? AND text=? LIMIT 1",
        (BRAND_ID, source_id, h),
    ).fetchone()
    return row is not None


def main() -> int:
    if not SUPPORT.exists():
        print(f"supporting dir missing: {SUPPORT}")
        return 1
    conn = db_connect()
    try:
        inserted = {"FACT": 0, "RULE": 0, "OBSERVATION": 0}
        for text, src in FACTS:
            if already_imported(conn, src, text):
                continue
            mid = write_memory_item(
                conn,
                brand_id=BRAND_ID,
                mem_type="FACT",
                text=text,
                scope="BRAND",
                source_type="obsidian_export",
                source_id=src,
                confidence=0.95,
                approval_state="APPROVED",
                status="ACTIVE",
                approved_by="phase1-habitat-import",
            )
            conn.execute(
                """
                INSERT INTO evidence_items (kind, ref, content, content_hash, brand_id, linked_memory_id, created_at)
                VALUES ('obsidian_export', ?, ?, ?, ?, ?, ?)
                """,
                (str(SUPPORT / src), text[:500], content_hash(text), BRAND_ID, mid, now_iso()),
            )
            inserted["FACT"] += 1
        for text, src in RULES:
            if already_imported(conn, src, text):
                continue
            mid = write_memory_item(
                conn,
                brand_id=BRAND_ID,
                mem_type="RULE",
                text=text,
                scope="BRAND",
                source_type="obsidian_export",
                source_id=src,
                confidence=0.95,
                approval_state="APPROVED",
                status="ACTIVE",
                approved_by="phase1-habitat-import",
            )
            conn.execute(
                """
                INSERT INTO evidence_items (kind, ref, content, content_hash, brand_id, linked_memory_id, created_at)
                VALUES ('obsidian_export', ?, ?, ?, ?, ?, ?)
                """,
                (str(SUPPORT / src), text[:500], content_hash(text), BRAND_ID, mid, now_iso()),
            )
            inserted["RULE"] += 1
        for text, src in OBSERVATIONS_PROPOSED:
            if already_imported(conn, src, text):
                continue
            # PROPOSED OBSERVATION — must NOT be ACTIVE
            mid = write_memory_item(
                conn,
                brand_id=BRAND_ID,
                mem_type="OBSERVATION",
                text=text,
                scope="BRAND",
                source_type="obsidian_export",
                source_id=src,
                confidence=0.6,
                approval_state="PROPOSED",
                status="PROPOSED",
            )
            conn.execute(
                """
                INSERT INTO evidence_items (kind, ref, content, content_hash, brand_id, linked_memory_id, created_at)
                VALUES ('obsidian_export', ?, ?, ?, ?, ?, ?)
                """,
                (str(SUPPORT / src), text[:500], content_hash(text), BRAND_ID, mid, now_iso()),
            )
            inserted["OBSERVATION"] += 1
        # Guard test: attempting ACTIVE without APPROVED must demote
        write_memory_item(
            conn,
            brand_id=BRAND_ID,
            mem_type="OBSERVATION",
            text="[governance-check] Attempted ACTIVE without APPROVED — should store as PROPOSED.",
            source_type="phase1_guard",
            source_id="governance-check",
            approval_state="PROPOSED",
            status="ACTIVE",  # should be forced to PROPOSED
        )
        conn.commit()
        active = conn.execute(
            "SELECT COUNT(*) FROM memory_items WHERE brand_id=? AND status='ACTIVE' AND approval_state='APPROVED'",
            (BRAND_ID,),
        ).fetchone()[0]
        proposed = conn.execute(
            "SELECT COUNT(*) FROM memory_items WHERE brand_id=? AND approval_state='PROPOSED'",
            (BRAND_ID,),
        ).fetchone()[0]
        bad = conn.execute(
            "SELECT COUNT(*) FROM memory_items WHERE status='ACTIVE' AND approval_state!='APPROVED'",
        ).fetchone()[0]
        print(f"inserted={inserted} active_approved={active} proposed={proposed} illegal_active={bad}")
        if bad:
            return 2
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
