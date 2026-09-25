#!/usr/bin/env python3
"""BF-content-engine-staff-ux-20260924 — staff Content desk chrome.

Beta file + shell gate. Does not invent staff_ready. Does not touch :8787.
"""
from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import wolf_shell as shell  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
CR = ROOT / "state" / "completion-register" / "content-engine-staff-ux-20260924.json"

PASS = 0
FAIL = 0
LINES: list[str] = []

BANNED = (
    "Operator depth",
    "operator_depth",
    "proven=",
    "ready=",
    "staff_ready",
    "human fake",
    "No Haikal",
    "NAS destroy",
    "Decision Memory",
    "Needs-You",
    "full_tree_indexed",
    "connective",
    "Haikal human",
)


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def visible_markup(html: str) -> str:
    html = re.sub(r"<!--STAFF_OMIT_ENG-->.*?<!--/STAFF_OMIT_ENG-->", "", html, flags=re.S)
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style\b[^>]*>.*?</style>", "", html, flags=re.S | re.I)
    return html


def primary_nav(html: str) -> str:
    m = re.search(r'<nav class="primary-nav"[^>]*>(.*?)</nav>', html, re.S)
    return m.group(1) if m else ""


def main() -> int:
    raw = HTML.read_text(encoding="utf-8")
    nav = primary_nav(raw)
    for label in ("CONTENT PLAN", "LIBRARY", "UPLOAD"):
        log(label in nav, f"tab {label}")
    log("WOLF INTELLIGENCE" not in nav, "wolf intelligence is not a tab")
    log(nav.count("<button") == 3, "three primary tabs", str(nav.count("<button")))
    log("Wolf Intelligence · unavailable" in raw and 'href="/content-2.0"' in raw, "hamburger app switcher")
    log('data-view="dashboard"' not in nav, "dashboard not a primary tab")
    log('id="brandSelect"' in raw, "brand selector present")
    log("staff-content-desk" in raw, "content desk marks global chrome secondary")

    who = shell.build_whoami(person_id="PERS-HAIKAL", email="haikalqilbari123@gmail.com")
    log(who.get("audience") == "SPECIALIST_CONTENT", "haikal audience", str(who.get("audience")))
    served = shell.apply_content_staff_desk(
        raw.encode("utf-8"), rel="content-2.0.html", whoami=who
    ).decode("utf-8")
    vis = visible_markup(served)
    for phrase in BANNED:
        log(phrase not in vis, f"staff chrome omits {phrase}")
    log("AKR" not in vis, "staff chrome omits AKR")
    log("Operator depth" not in served, "served staff html omits operator depth heading")

    owner = shell.build_whoami(person_id="PERS-MATT", email="mrwolf@wolfcommand.net")
    owner_html = shell.apply_content_staff_desk(
        raw.encode("utf-8"), rel="content-2.0.html", whoami=owner
    ).decode("utf-8")
    log("Operator depth" in owner_html, "owner file keeps engineering block")
    grammar = shell.intel_grammar_for_audience(who, rel="content-2.0.html")
    keys = {g.get("key") for g in grammar}
    log("decision" not in keys and "akr" not in keys, "staff grammar omits decision memory and akr", str(keys))
    owner_keys = {g.get("key") for g in shell.intel_grammar_for_audience(owner, rel="content-2.0.html")}
    log("decision" in owner_keys and "akr" in owner_keys, "owner grammar keeps decision memory and akr")

    log('class="lib-search-hero"' in vis and 'id="libSearch"' in vis, "library search hero")
    log(">More filters<" in vis, "more filters label")
    log('id="libGrid"' in vis and "lib-thumb" in raw, "thumbnail grid")
    log('id="libSelectAll"' in vis and ">Deselect<" in vis and 'id="libSelCount"' in vis, "select deselect count")
    log('id="libDownloadSel"' in vis and 'id="libDownloadProgress"' in vis, "download and progress")
    for stage in (
        "Select file",
        "Uploading",
        "Processing",
        "Saving to NAS",
        "Indexing",
        "Generating thumbnail/preview",
        "Available in Library",
        "Complete",
    ):
        log(stage in vis, f"upload stage {stage}")
    log('id="uploadLifecycle"' in vis, "upload lifecycle list")
    log('return "In progress"' in raw, "unknown upload status is not Complete")
    log("staff_ready = true" not in raw and "staff_ready=true" not in raw, "page does not invent staff_ready")

    cr = json.loads(CR.read_text(encoding="utf-8"))
    log(cr.get("staff_ready") is False, "cr staff_ready false")
    log(cr.get("proven") is False and cr.get("ready") is False, "cr proven and ready false")
    log(cr.get("cap_state") == "SPECIFIED", "cr cap stays SPECIFIED", str(cr.get("cap_state")))
    log(shell.honesty_flags().get("staff_ready") is False, "shell staff_ready false")

    js = raw.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/content-engine-staff-ux.js")
    tmp.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(r.returncode == 0, "board js syntax", (r.stderr or "OK")[:180])

    injected = shell.inject_shell(raw.encode("utf-8"), rel="content-2.0.html", whoami=who).decode("utf-8")
    log("Operator depth" not in injected, "inject strips staff engineering block")
    log('id="wolfnav"' not in injected and "Boards" not in injected, "staff inject omits engineering nav")
    log("CONTENT PLAN" in injected and 'id="staffHello"' in injected, "staff header survives inject")
    owner_injected = shell.inject_shell(raw.encode("utf-8"), rel="content-2.0.html", whoami=owner).decode("utf-8")
    log('id="wolfnav"' in owner_injected and ">Up<" in owner_injected, "owner inject keeps system nav")

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
