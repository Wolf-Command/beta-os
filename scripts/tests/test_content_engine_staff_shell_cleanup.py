#!/usr/bin/env python3
"""Staff shell cleanup folded into BF-content-engine-haikal-fail-repair-20260924.

Beta file + shell gate. staff_ready stays false. Does not touch :8787.
"""
from __future__ import annotations

import re
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import content_engine_repair as repair  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
SEAT = ROOT / "scripts/migrations/migrate_role_position_assignment.py"

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


def visible(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style\b[^>]*>.*?</style>", "", html, flags=re.S | re.I)
    return html


def main() -> int:
    raw = HTML.read_text(encoding="utf-8")
    who = shell.build_whoami(person_id="PERS-HAIKAL", email="haikalqilbari123@gmail.com")
    owner = shell.build_whoami(person_id="PERS-MATT", email="mrwolf@wolfcommand.net")
    served = shell.inject_shell(raw.encode("utf-8"), rel="content-2.0.html", whoami=who).decode("utf-8")
    owner_html = shell.inject_shell(raw.encode("utf-8"), rel="content-2.0.html", whoami=owner).decode("utf-8")
    vis = visible(served)

    log("ce-staff-shell" in served, "staff shell class")
    log("CONTENT ENGINE" in vis, "content engine title")
    log('id="brandSelect"' in vis and 'id="ceMenuBtn"' in vis, "menu and brand selector")
    log('id="staffHello"' in vis and ">profile<" in vis, "greeting and profile")
    for label in ("CONTENT PLAN", "LIBRARY", "UPLOAD"):
        log(label in vis, f"staff tab {label}")
    log("staff-wi-nav" not in served and "WOLF INTELLIGENCE" not in vis, "wolf intelligence hidden from staff nav")
    for banned in (
        ">Boards<",
        ">Wolf<",
        'data-wolf-dir="up"',
        'data-wolf-dir="back"',
        'data-wolf-dir="home"',
        "Dev identity",
        "SPECIALIST_CONTENT",
        "ROLE-CONTENT",
        "haikalqilbari123@gmail.com",
        "nas-banner ok",
    ):
        log(banned not in vis, f"staff view omits {banned}")
    log('id="wolfnav"' not in served, "staff page has no engineering nav")
    log('id="wolfnav"' in owner_html and "Dev identity" in owner_html, "owner keeps system chrome")
    log('id="uploadRetry"' in vis and "/api/assets/zip" in raw, "retry and zip preserved")
    ol = re.search(r'<ol class="upload-lifecycle" id="uploadLifecycle"[^>]*>', raw)
    log(bool(ol and "hidden" in ol.group(0)), "seven-stage pipeline starts hidden")
    log('id="uploadLiveStatus"' in raw, "in-flight status line")
    log('value="broll"' not in raw, "upload does not offer broll as media type")
    log('aria-label="Media type"' in raw and 'aria-label="Content type"' in raw, "media type separate from content type")
    log("Wolf Intelligence · unavailable" in vis and ">Content Engine<" in vis, "hamburger app switcher")
    for label in ("Photo", "Video", "Audio", "Graphic"):
        log(f">{label}<" in raw, f"media label {label}")
    log('class="lib-title"' in raw and "staffCardTitle" in raw, "library human title")
    log("canonical_name||a.name" not in raw.split("loadLibrary = async function", 1)[-1].split("openPreview26", 1)[0],
        "grid omits technical names")
    preview = raw.split("async function openPreview26", 1)[-1][:1800]
    log("staffCardTitle(a)" in preview and "k\">Brand" in preview and "k\">Location" in preview and "k\">Media type" in preview and "k\">Content type" in preview, "preview shows title brand location media and content type")
    log(repair.staff_media_label("video") == "Video" and repair.staff_media_label("audio") == "Audio", "canon media labels")
    log(repair.staff_media_label("graphic") == "Graphic" and repair.staff_media_label("broll") == "", "broll stays debt")
    log(repair.staff_library_title("habitat-villa", "pool-wide") == "habitat villa · pool wide", "subject detail title")
    log(repair.staff_library_title("", "") == "Untitled", "missing subject is untitled")
    log(repair.all_brands_authorised(1) is False, "single brand has no all-brands")
    log(repair.all_brands_authorised(4) is True, "multi brand may use all brands")
    seat = SEAT.read_text(encoding="utf-8")
    log("ASG-HAIKAL-CD-1" in seat and "ROLE-GGV-CREATIVE-DIRECTOR" in seat, "creative director assignment kept")
    log("staff_ready = true" not in raw and "staff_ready=true" not in raw, "page does not invent staff_ready")
    log(shell.honesty_flags().get("staff_ready") is False, "shell staff_ready false")
    log(who.get("landing") == "/content-2.0", "content landing unchanged")

    js = raw.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/content-engine-staff-shell.js")
    tmp.write_text(js, encoding="utf-8")
    syntax = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(syntax.returncode == 0, "board js syntax", (syntax.stderr or "OK")[:180])

    s = socket.socket()
    s.settimeout(1.5)
    up8787 = s.connect_ex(("127.0.0.1", 8787)) == 0
    s.close()
    log(up8787, "production :8787 still up")

    print("\n".join(LINES))
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
