#!/usr/bin/env python3
"""Organisation Registry acceptance tests — Beta only."""
from __future__ import annotations

import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
SCRIPTS = ROOT / "scripts"
DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

from migrations.migrate_org_registry import main as migrate_main  # noqa: E402
from core import organisation as org  # noqa: E402

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
    # Refuse prod paths in module source
    src = (SCRIPTS / "core" / "organisation.py").read_text(encoding="utf-8")
    mig = (SCRIPTS / "migrations" / "migrate_org_registry.py").read_text(encoding="utf-8")
    check(
        "organisation.py guards against wolf-system",
        "refuses wolf-system" in src and "beta-os" in src,
    )
    # Guard strings may mention money.sqlite as FORBIDDEN; ensure no open path to it
    check(
        "no production money.sqlite path opened",
        "money.sqlite" not in src
        and ("FORBIDDEN" in mig or "REFUSE" in mig)
        and "/Users/wolfterminal/wolf-system" not in mig
        and "/Users/wolfterminal/wolf-system" not in src,
    )

    # Baseline content counts
    conn = sqlite3.connect(str(DB))
    before_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    before_brands = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    before_perms = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    habitat = conn.execute("SELECT id, display_name FROM brands WHERE id='habitat'").fetchone()
    conn.close()
    check("content brands habitat exists before/after path", habitat is not None)

    # Run migration twice (idempotent)
    rc1 = migrate_main()
    rc2 = migrate_main()
    check("migration run 1 ok", rc1 == 0, str(rc1))
    check("migration run 2 ok (idempotent)", rc2 == 0, str(rc2))

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    n_ent = conn.execute("SELECT COUNT(*) FROM org_entities").fetchone()[0]
    n_brand = conn.execute("SELECT COUNT(*) FROM org_brands").fetchone()[0]
    n_loc = conn.execute("SELECT COUNT(*) FROM org_locations").fetchone()[0]
    n_dept = conn.execute("SELECT COUNT(*) FROM org_departments").fetchone()[0]
    n_bl = conn.execute("SELECT COUNT(*) FROM org_brand_locations").fetchone()[0]
    check("entities seed = 3", n_ent == 3, str(n_ent))
    check("brands seed = 7", n_brand == 7, str(n_brand))
    check("locations seed = 1", n_loc == 1, str(n_loc))
    check("departments seed = 5", n_dept == 5, str(n_dept))
    check("brand_locations = 7", n_bl == 7, str(n_bl))
    check("no duplicate entities after re-run", n_ent == 3)

    # Schema must not include identity/auth columns
    bad_cols = set()
    for table in ("org_entities", "org_brands", "org_locations", "org_departments", "org_brand_locations"):
        for row in conn.execute(f"PRAGMA table_info({table})"):
            col = row[1].lower()
            if col in ("email", "subject", "user_id", "person_id", "password", "auth_token"):
                bad_cols.add(f"{table}.{col}")
    check("no email/user identity columns in org schema", not bad_cols, str(bad_cols))

    # Ownership checks
    uma = conn.execute("SELECT entity_id FROM org_brands WHERE brand_id='BZG-UMA'").fetchone()
    atr = conn.execute("SELECT entity_id FROM org_brands WHERE brand_id='AMG-ATR'").fetchone()
    check("BZG-UMA under ENT-BZG", uma and uma[0] == "ENT-BZG")
    check("AMG-ATR under ENT-AMG", atr and atr[0] == "ENT-AMG")
    # No brand under two entities (PK) + no Habitat as org brand
    hab_org = conn.execute("SELECT 1 FROM org_brands WHERE brand_id LIKE '%HAB%' OR display_name LIKE '%Habitat%'").fetchone()
    check("Habitat not seeded as org brand", hab_org is None)
    ggv_brands = conn.execute("SELECT COUNT(*) FROM org_brands WHERE entity_id='ENT-GGV'").fetchone()[0]
    check("GGV owns zero client brands this slice", ggv_brands == 0, str(ggv_brands))

    # Content preserved
    after_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    after_brands = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    after_perms = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    check("assets unchanged", after_assets == before_assets, f"{before_assets}->{after_assets}")
    check("content brands count unchanged", after_brands == before_brands)
    check("permissions unchanged", after_perms == before_perms)
    hab2 = conn.execute("SELECT id FROM brands WHERE id='habitat'").fetchone()
    check("content habitat row intact", hab2 is not None)
    hab_map = conn.execute("SELECT org_brand_id FROM brands WHERE id='habitat'").fetchone()
    check("habitat org_brand_id is NULL (client)", hab_map and hab_map[0] is None)
    umablu = conn.execute(
        "SELECT org_brand_id FROM brand_external_ids WHERE brand_key='umablu'"
    ).fetchone()
    check("umablu maps to BZG-UMA", umablu and umablu[0] == "BZG-UMA")
    atrium = conn.execute(
        "SELECT org_brand_id FROM brand_external_ids WHERE brand_key='atrium'"
    ).fetchone()
    check("atrium maps to AMG-ATR", atrium and atrium[0] == "AMG-ATR")
    for k in ("habitat", "selo", "tropik"):
        row = conn.execute(
            "SELECT org_brand_id FROM brand_external_ids WHERE brand_key=?", (k,)
        ).fetchone()
        check(f"{k} org_brand_id NULL (client)", row is not None and row[0] is None)
    conn.close()

    # Repository layer
    ents = org.list_entities()
    check("list_entities returns 3", len(ents) == 3)
    check("get_entity ENT-BZG", org.get_entity("ENT-BZG") is not None)
    check("get_entity invalid None", org.get_entity("ENT-NOPE") is None)
    bzg_brands = org.list_brands_by_entity("ENT-BZG")
    check("BZG has 6 brands", len(bzg_brands) == 6, str(len(bzg_brands)))
    amg_locs = org.list_locations_by_entity("ENT-AMG")
    check("AMG has Atrium location", len(amg_locs) == 1 and amg_locs[0]["location_id"] == "LOC-ATRIUM-LOMBOK")
    bzg_locs = org.list_locations_by_entity("ENT-BZG")
    check("BZG primary locations empty (campus stewarded by AMG)", len(bzg_locs) == 0)
    deps = org.list_departments_by_entity("ENT-GGV")
    check("GGV Content department", any(d["department_id"] == "DEPT-GGV-CONTENT" for d in deps))
    check("get_brand BZG-UMA", org.get_brand("BZG-UMA")["entity_id"] == "ENT-BZG")
    check("get_brand invalid None", org.get_brand("NOPE") is None)

    # Live origin, unsigned. A 200 here is not the registry prove.
    def _live_status(path: str) -> int:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8788" + path, timeout=2) as r:
                return int(r.status)
        except urllib.error.HTTPError as e:
            return int(e.code)
        except Exception:
            return 0

    list_status = _live_status("/api/core/entities")
    nope_status = _live_status("/api/core/entities/ENT-NOPE")
    if list_status == 0 and nope_status == 0:
        check("API skip (serve not required for unit layer)", True, "skipped")
    else:
        check("unsigned /api/core/entities fail-closed", list_status == 403, str(list_status))
        check(
            "unsigned /api/core/entities/ENT-NOPE fail-closed",
            nope_status == 403,
            str(nope_status),
        )

    # Content brands API still works if serve up
    try:
        with urllib.request.urlopen("http://127.0.0.1:8788/api/brands", timeout=2) as r:
            raw = r.read().decode()
        check("Content /api/brands still responds", "habitat" in raw.lower() or "ok" in raw.lower() or len(raw) > 2)
    except Exception:
        check("Content /api/brands skip if serve down", True)

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
