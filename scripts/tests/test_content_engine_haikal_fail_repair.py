#!/usr/bin/env python3
"""BF-content-engine-haikal-fail-repair-20260924 — shared-root repair checks.

Beta only. staff_ready stays false. Does not touch :8787.
"""
from __future__ import annotations

import json
import re
import socket
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import content_engine_repair as repair  # noqa: E402
from core import nas_library as nas  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
CR = ROOT / "state" / "completion-register" / "content-engine-haikal-fail-repair-20260924.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
EVIDENCE = ROOT / "state" / "commissioning" / "evidence" / "CE-HAIKAL-UPLOAD-TRACE-2026-09-24.json"

PASS = 0
FAIL = 0
LINES: list[str] = []


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    raw = HTML.read_text(encoding="utf-8")
    log("BRANDS_FALLBACK" not in raw, "desk does not ship a hard-coded brand fallback")
    log("onerror=\"this.remove()\"" not in raw, "preview errors do not blank the tile")
    log("library_available" in raw, "complete path checks library_available")
    log("staff-wi-nav" in raw, "wolf intelligence nav is marked for staff hide")
    log('id="uploadRetry"' in raw, "failed-file retry control")
    log("/api/assets/zip" in raw, "zip download path preserved")
    for label in repair.LIFECYCLE:
        log(label[1].replace("✓ ", "") in raw or label[1] in raw, f"lifecycle label {label[1]}")

    who = shell.build_whoami(person_id="PERS-HAIKAL", email="haikalqilbari123@gmail.com")
    served = shell.apply_content_staff_desk(raw.encode("utf-8"), rel="content-2.0.html", whoami=who).decode("utf-8")
    log("staff-wi-nav" not in served, "staff nav hides Wolf Intelligence")
    log("CONTENT PLAN" in served and "LIBRARY" in served and "UPLOAD" in served, "staff keeps plan library upload")
    owner = shell.build_whoami(person_id="PERS-MATT", email="mrwolf@wolfcommand.net")
    owner_html = shell.apply_content_staff_desk(raw.encode("utf-8"), rel="content-2.0.html", whoami=owner).decode("utf-8")
    log("staff-wi-nav" in owner_html, "owner file still has the intelligence tab")
    log("ce-staff-shell" in served and 'id="staffHello"' in served, "staff header greeting")
    log("CONTENT ENGINE" in served and 'id="brandSelect"' in served, "staff title and brand selector")
    log("Dev identity" not in served.split("<script>", 1)[0], "staff head omits dev identity")
    lifecycle = re.search(r'<ol class="upload-lifecycle" id="uploadLifecycle"[^>]*>', raw)
    log(bool(lifecycle and "hidden" in lifecycle.group(0)), "upload pipeline is not permanent chrome")
    log("nas-banner ok" not in raw, "no healthy-NAS green banner")
    log('value="broll"' not in raw and ">Photo<" in raw and ">Graphic<" in raw, "staff media labels")
    log('aria-label="Content type"' in raw and 'value="broll"' not in raw, "content type is separate from media type")
    log(repair.staff_media_label("broll") == "" and repair.staff_media_label("image") == "Photo", "broll is not a staff media kind")
    log(repair.staff_library_title("pool-deck", "wide") == "pool deck · wide", "title uses subject and detail")
    log(repair.all_brands_authorised(1) is False and repair.all_brands_authorised(8) is True, "all brands only when multi-brand")
    seat = (ROOT / "scripts/migrations/migrate_role_position_assignment.py").read_text(encoding="utf-8")
    log("ASG-HAIKAL-CD-1" in seat and "ROLE-GGV-CREATIVE-DIRECTOR" in seat, "creative director seat preserved")

    scopes = list(who.get("scopes") or [])
    active = who.get("active_assignment") or {}
    log(active.get("id") == "ASG-HAIKAL-CD-1", "whoami active assignment is creative director", str(active.get("id")))
    log(active.get("role") == "ROLE-GGV-CREATIVE-DIRECTOR", "whoami role is creative director", str(active.get("role")))
    log("SCOPE-WOLF-CONTENT-ALL-BRANDS" in scopes, "content-all scope on assignment")
    log("SCOPE-AMG" not in scopes and "SCOPE-BZG-ENTITY" not in scopes and "SCOPE-WOLF-GROUP" not in scopes, "content scope is not finance or ops")
    log("habitat" in nas.brands_for_scopes(scopes), "haikal scope includes habitat")
    log("atrium" in nas.brands_for_scopes(scopes), "content-all scope includes atrium")
    log("goss" in nas.brands_for_scopes(scopes), "content-all scope includes goss")
    log(nas.scopes_allow_brand(scopes, "atrium") is True, "acl allows atrium via content scope")
    log(nas.scopes_allow_brand(["SCOPE-CRM-HABITAT-LEAD"], "atrium") is False, "unrelated scope still denies atrium")
    log(nas.scopes_allow_brand(["SCOPE-WOLF-GROUP"], "atrium") is True, "owner scope allows atrium")

    conn = sqlite3.connect(CATALOG)
    conn.row_factory = sqlite3.Row
    try:
        seeded = repair.ensure_registry(conn)
        brands = repair.authorised_brands(conn, scopes)
        names = {b["display_name"] for b in brands}
        log(seeded.get("source") == "org_brands+aliases", "registry source", seeded.get("source"))
        log("Habitat" in names and "Atrium" in names and "Uma Blu" in names and "Goss Group" in names, "haikal sees all content brands", str(sorted(names)))
        log(len(brands) == 8, "eight authorised brands", str(len(brands)))
        denied = repair.authorised_brands(conn, ["SCOPE-CRM-HABITAT-LEAD"])
        log(denied == [], "unrelated scope sees no content brands")
        owner_names = {b["display_name"] for b in repair.authorised_brands(conn, ["SCOPE-WOLF-GROUP"])}
        for required in (
            "Atrium",
            "Uma Blu",
            "Selo Group",
            "Habitat",
            "Tropik",
            "The One",
            "Blu Zone Rainforest Resto",
            "Goss Group",
        ):
            log(required in owner_names, f"registry name {required}")
        suggestion = repair.suggest_brand("habitat-pool.jpg", scopes, conn)
        log(suggestion.get("applied") is False and suggestion.get("confirm_required") is True, "suggestion is not applied")
        log(suggestion.get("suggestion") == "habitat", "suggestion can name habitat", str(suggestion.get("suggestion")))
        coverage = repair.start_inplace_index(conn, scopes, cap_per_brand=3)
        log(coverage.get("whole_nas") is False and coverage.get("staff_ready") is False, "index does not claim the whole NAS")
        log(coverage.get("destructive") is False, "index is not destructive")
        habitat = next((b for b in coverage.get("brands") or [] if b.get("slug") == "habitat"), {})
        log(bool(habitat.get("message")), "habitat index message", str(habitat.get("message"))[:140])
        cards = repair.nas_library_cards(conn, scopes, "habitat", limit=8)
        log(all("original_path" not in c and "/Volumes/" not in json.dumps(c) for c in cards), "nas cards hide filesystem paths", str(len(cards)))
        leaked = repair.nas_library_cards(conn, ["SCOPE-CRM-HABITAT-LEAD"], "atrium", limit=4)
        log(leaked == [], "library cards deny unauthorised brand")
        titled = repair.nas_library_cards(conn, scopes, "all", limit=12)
        log(all(c.get("staff_title") != "Untitled" for c in titled), "filename title when no canonical title", str(len(titled)))
    finally:
        conn.close()

    blocked = repair.annotate_upload(
        {
            "ok": True,
            "library_status": "LIBRARY_READY",
            "asset_id": 1,
            "content_hash": "abc",
            "nas_received": False,
            "brand": "habitat",
        },
        media_path=None,
    )
    log(blocked.get("library_available") is False and blocked.get("complete") is False, "complete blocked without NAS file")
    log(blocked.get("failed_stage") == "saving_nas", "failed stage is saving to NAS", str(blocked.get("failed_stage")))
    log(blocked.get("ui_status") != "COMPLETE", "ui status is not complete")

    thumb_src = ROOT / "state" / "content-thumbs" / "_repair_probe.png"
    thumb_src.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    Image.new("RGB", (16, 16), (20, 80, 40)).save(thumb_src, "PNG")
    ready = repair.annotate_upload(
        {
            "ok": True,
            "library_status": "LIBRARY_READY",
            "asset_id": 990001,
            "content_hash": "probehash",
            "nas_received": True,
            "brand": "habitat",
        },
        media_path=thumb_src,
    )
    reg = ready.get("registration") or {}
    log(ready.get("library_available") is True and ready.get("complete") is True, "complete only when library-available")
    log(
        reg.get("nas_file") and reg.get("hash") and reg.get("indexed") and reg.get("library") and reg.get("thumbnail"),
        "registration invariant fields",
        str({k: reg.get(k) for k in ("nas_file", "hash", "indexed", "library", "thumbnail")}),
    )
    thumb = repair.asset_thumb_path(990001)
    log(thumb.is_file() and thumb.read_bytes()[:2] == b"\xff\xd8", "photo thumb is a jpeg")
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        json.dumps(
            {
                "run_id": repair.RUN_ID,
                "subject": "haikalqilbari123@gmail.com",
                "person_id": "PERS-HAIKAL",
                "registration": reg,
                "library_available": ready.get("library_available"),
                "failed_stage_when_nas_missing": blocked.get("failed_stage"),
                "habitat_index": habitat,
                "staff_ready": False,
                "note": "Probe uses a generated PNG so the thumbnail stage is real. It is not a Haikal human PASS.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log(EVIDENCE.is_file(), "registration evidence artifact")

    try:
        repair.refuse_staff_ready({})
        log(False, "staff_ready refused")
    except repair.RepairError:
        log(True, "staff_ready refused")

    cr = json.loads(CR.read_text(encoding="utf-8"))
    log(cr.get("staff_ready") is False and cr.get("proven") is False and cr.get("ready") is False, "cr stays unready")
    log(cr.get("human_status") == "FAILED_RETEST_REQUIRED", "human status stays failed retest")
    log("staff_ready = true" not in raw and "staff_ready=true" not in raw, "page does not invent staff_ready")

    js = raw.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/content-engine-haikal-repair.js")
    tmp.write_text(js, encoding="utf-8")
    syntax = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(syntax.returncode == 0, "board js syntax", (syntax.stderr or "OK")[:200])

    s = socket.socket()
    s.settimeout(1.5)
    up8787 = s.connect_ex(("127.0.0.1", 8787)) == 0
    s.close()
    log(up8787, "production :8787 still up")

    try:
        with urllib.request.urlopen("http://127.0.0.1:8788/api/content/repair-status", timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        log(resp.status == 200 and payload.get("staff_ready") is False, "deployed repair status staff_ready false")
        log(payload.get("run_id") == repair.RUN_ID, "deployed process loaded this repair", str(payload.get("run_id")))
        log(payload.get("complete_means") == "library_available", "deployed complete means library-available")
    except Exception as exc:  # noqa: BLE001
        log(False, "deployed repair status", str(exc)[:180])

    try:
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8788/content-2.0",
                headers={"X-Wolf-Subject": "haikalqilbari123@gmail.com"},
            ),
            timeout=4,
        )
        log(False, "unauthenticated content route stays gated")
    except urllib.error.HTTPError as exc:
        log(exc.code == 403, "unauthenticated content route stays gated", str(exc.code))
    except Exception as exc:  # noqa: BLE001
        log(False, "unauthenticated content route stays gated", str(exc)[:160])

    print("\n".join(LINES))
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
