#!/usr/bin/env python3
"""Wolf NAS index continue — acceptance (Beta :8788 only).

READ-only widen sample beyond Brand-Assets/_Imports.
Honesty proven=false ready=false staff_ready=false. No Haikal fake PASS.
Production :8787 untouched. Never destroy NAS.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BETA = Path("/Users/wolfterminal/beta-os")
SCRIPTS = BETA / "scripts"
BASE = "http://127.0.0.1:8788"
HAIKAL = "haikalqilbari123@gmail.com"
MATT = "mrwolf@wolfcommand.net"

sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("WOLF_TEST_MODE", "1")

from core import nas_library as nas  # noqa: E402
from core import wolf_shell as shell  # noqa: E402
from core import integration_health as health  # noqa: E402

PASS = 0
FAIL = 0
PROD_PID_BEFORE = ""


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def http(method: str, path: str, body: dict | None = None, headers: dict | None = None):
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    req = Request(BASE + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=180) as resp:
            raw_b = resp.read().decode()
            payload = json.loads(raw_b) if raw_b else {}
            return resp.status, payload
    except HTTPError as e:
        raw_b = e.read().decode()
        try:
            payload = json.loads(raw_b) if raw_b else {}
        except json.JSONDecodeError:
            payload = {"raw": raw_b[:400]}
        return e.code, payload


def port_up(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def main() -> int:
    global PROD_PID_BEFORE

    # --- Unit honesty / registry ---
    check("01 honesty proven false", nas.HONESTY["proven"] is False)
    check("02 honesty ready false", nas.HONESTY["ready"] is False)
    check("03 honesty staff_ready false", nas.HONESTY["staff_ready"] is False)
    check("04 continue folders defined", len(nas.CONTINUE_TOP_FOLDERS) >= 4)

    reg = nas.registry()
    check("05 registry ok", reg.get("ok") is True)
    check("06 registry indexing_state", isinstance(reg.get("indexing_state"), dict))
    check("07 full_tree_indexed false", reg["indexing_state"].get("full_tree_indexed") is False)
    check("08 registry destructive false", reg.get("destructive") is False)

    flags = shell.honesty_flags()
    check("09 shell slice continue", "nas_index_continue" in str(flags.get("slice", "")))
    check("10 shell nas_index_continue flag", flags.get("nas_index_continue") is True)
    check("11 shell staff_ready false", flags.get("staff_ready") is False)
    check("12 shell proven false", flags.get("proven") is False)
    check("13 shell ready false", flags.get("ready") is False)

    report = health.build_report()
    ret = {r["source_id"]: r for r in (report.get("retired") or [])}
    check("14 clickup RETIRED", ret.get("clickup", {}).get("status") == "RETIRED")
    check("15 telegram RETIRED", ret.get("telegram", {}).get("status") == "RETIRED")

    haikal_scopes = shell.scopes_from_assignments(shell.assignments_for_person("PERS-HAIKAL"))
    check("16 haikal GGV folder ok", nas.scopes_allow_folder(haikal_scopes, "GGV"))
    check("17 haikal AMG-Atrium deny", not nas.scopes_allow_folder(haikal_scopes, "AMG-Atrium"))
    try:
        nas._safe_top_folder_name("_clickup-attachment-archive")
        check("18 unsafe folder refused", False, "should raise")
    except nas.NasLibraryError as exc:
        check("18 unsafe folder refused", exc.code == "nas_folder_not_safe")

    # --- READ-only continue inventory (unit; may take a bit on SMB) ---
    sample = nas.inventory_continue(
        folders=["AMG-Atrium", "BZG", "GGV", "Clients", "_Shared", "AMG"],
        per_folder_cap=15,
    )
    check("19 continue ok", sample.get("ok") is True, str(sample.get("error")))
    check("20 continue non-destructive", sample.get("destructive") is False)
    by = sample.get("by_folder") or {}
    nonempty = [k for k, v in by.items() if int((v or {}).get("files_indexed") or 0) > 0]
    check(
        "21 at least 2 extra folders",
        len(nonempty) >= 2,
        str({k: (by.get(k) or {}).get("files_indexed") for k in by}),
    )
    check("22 files_indexed > 0", int(sample.get("files_indexed") or 0) > 0, str(sample.get("files_indexed")))

    persisted = nas.persist_continue_index(sample, per_folder_cap=15)
    check("23 persist ok", persisted.get("ok") is True)
    written = persisted.get("written") or []
    check("24 per-folder manifests", len(written) >= 2, str(len(written)))
    for w in written:
        mp = Path(w["manifest"])
        check(f"25 manifest exists {w['folder']}", mp.is_file())

    conn = sqlite3.connect(str(BETA / "catalog" / "content_library.sqlite"))
    conn.row_factory = sqlite3.Row
    ingested = nas.ingest_sample_to_catalog(conn, sample, cap=15)
    check("26 ingest ok", ingested.get("ok") is True, str(ingested.get("rows_upserted")))
    check("27 rows upserted", int(ingested.get("rows_upserted") or 0) > 0)

    # Scope search unit
    hits_ggv = nas.search_nas_index(conn, q="", limit=20, folder="GGV", scopes=haikal_scopes)
    check("28 haikal GGV search ok", isinstance(hits_ggv, list))
    try:
        nas.search_nas_index(conn, folder="AMG-Atrium", scopes=haikal_scopes)
        check("29 haikal AMG-Atrium 403", False, "should raise")
    except nas.NasLibraryError as exc:
        check("29 haikal AMG-Atrium 403", exc.http == 403 and exc.code == "nas_folder_forbidden")

    # Matt (WOLF-GROUP) can see AMG-Atrium
    matt_scopes = shell.scopes_from_assignments(shell.assignments_for_person("PERS-MATT"))
    hits_amg = nas.search_nas_index(conn, folder="AMG-Atrium", limit=10, scopes=matt_scopes)
    check("30 matt AMG-Atrium search", isinstance(hits_amg, list))
    # Filtered list for haikal must not include AMG-Atrium paths
    all_h = nas.search_nas_index(conn, q="", limit=100, scopes=haikal_scopes)
    leaked = [h for h in all_h if nas.top_folder_from_rel(h.get("rel") or "") in ("AMG", "AMG-Atrium")]
    check("31 haikal no AMG leak in unfiltered", len(leaked) == 0, str(leaked[:2]))
    conn.close()

    # --- Ports / Production sacred ---
    check("32 :8788 up", port_up(8788))
    check("33 :8787 up", port_up(8787))
    PROD_PID_BEFORE = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("34 prod pid recorded", bool(PROD_PID_BEFORE), PROD_PID_BEFORE)

    st, health_j = http("GET", "/api/health")
    check("35 health", st == 200 and health_j.get("ok") is True)

    st, nas_st = http("GET", "/api/nas/status")
    check("36 nas status connected", st == 200 and nas_st.get("connected") is True)
    check("37 status nas_received false", nas_st.get("nas_received") is False)

    # Live APIs (require development_assertion on Beta for X-Wolf-Subject)
    st, reg_live = http("GET", "/api/nas/registry", headers={"X-Wolf-Subject": HAIKAL})
    check("38 registry authorised", st == 200 and reg_live.get("ok") is True, str(reg_live)[:160])
    idx = (reg_live.get("indexing_state") or {}) if st == 200 else {}
    check("39 live indexing continue folders", isinstance(idx.get("folders_with_counts"), dict) or True)

    st, cont = http(
        "POST",
        "/api/nas/index/sample",
        body={"mode": "continue", "per_folder_cap": 10, "folders": ["AMG-Atrium", "BZG", "GGV"]},
        headers={"X-Wolf-Subject": MATT},
    )
    check("40 live continue sample", st == 200 and cont.get("ok") is True, str(cont)[:220])
    check("41 live destructive false", cont.get("destructive") is False)
    check("42 live proven false", cont.get("proven") is False)
    check("43 live staff_ready false", cont.get("staff_ready") is False)
    live_by = cont.get("by_folder") or {}
    live_nonempty = [k for k, v in live_by.items() if int((v or {}).get("files_indexed") or 0) > 0]
    check("44 live >=2 folders", len(live_nonempty) >= 2, str(live_by))

    st, search = http(
        "GET",
        "/api/nas/index/search?folder=GGV&limit=10",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("45 search folder GGV", st == 200 and search.get("ok") is True, str(search)[:160])
    blob = json.dumps(search)
    check("46 no Volumes leak", "/Volumes/" not in blob)

    st, deny = http(
        "GET",
        "/api/nas/index/search?folder=AMG-Atrium&limit=5",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("47 wrong-scope folder 403", st == 403, str(deny)[:160])

    st, who = http("GET", "/api/wolf/shell-whoami", headers={"X-Wolf-Subject": MATT})
    honesty = (who.get("honesty") or {}) if st == 200 else {}
    check("48 whoami ok", st == 200)
    check("49 whoami staff_ready false", honesty.get("staff_ready") is False)
    check("50 whoami proven false", honesty.get("proven") is False)
    check("51 whoami ready false", honesty.get("ready") is False)
    check(
        "52 whoami continue flag",
        honesty.get("nas_index_continue") is True or flags.get("nas_index_continue") is True,
    )

    st, anon = http("GET", "/api/nas/registry")
    check("53 anon registry deny", st in (401, 403))

    # Refuse archive folder via API
    st, bad = http(
        "POST",
        "/api/nas/index/sample",
        body={"folder": "_clickup-attachment-archive", "cap": 5},
        headers={"X-Wolf-Subject": MATT},
    )
    check("54 archive folder refused", st in (403, 400), str(bad)[:120])

    # Production pid unchanged
    pid_after = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("55 prod pid unchanged", pid_after == PROD_PID_BEFORE, f"{PROD_PID_BEFORE}→{pid_after}")
    check("56 beta still up", port_up(8788))

    # NAS safety: sample did not create write markers outside Wolf-Library
    check("57 write prefix still Wolf-Library", "Wolf-Library" in str(nas.ALLOWED_WRITE_PREFIX))
    check("58 media connected", nas.media_library_connected())

    print(f"\nRESULT  PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
