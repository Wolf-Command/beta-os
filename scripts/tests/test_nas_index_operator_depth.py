#!/usr/bin/env python3
"""NAS Index Operator Depth — acceptance (Beta :8788 only).

Browse/filter/search facets + indexed object detail.
Optional READ-only _needs_sorting sample. full_tree_indexed=false.
No Haikal human fake. No NAS destroy. No invent PROVEN/READY/staff_ready.
No Metricool publish. Do not false-resolve CRs.
Production :8787 untouched.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BETA = Path("/Users/wolfterminal/beta-os")
SCRIPTS = BETA / "scripts"
BASE = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
HAIKAL = "haikalqilbari123@gmail.com"
AMANDA = "amanda@wolfcommand.net"
MISA = "mlsary111@gmail.com"
MATT = "mrwolf@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"

sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("WOLF_TEST_MODE", "1")
os.environ.setdefault("BETA_AUTH_MODE", "development_assertion")

from core import nas_index_operator_depth as ops  # noqa: E402
from core import nas_library as nas  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

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


def http(method: str, path: str, body: dict | None = None, headers: dict | None = None, base: str = BASE):
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    req = Request(base + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=120) as resp:
            raw_b = resp.read().decode(errors="replace")
            if raw_b.lstrip().startswith(("<!", "<html", "<HTML")):
                return resp.status, {"ok": True, "html": True, "len": len(raw_b)}
            try:
                payload = json.loads(raw_b) if raw_b else {}
            except json.JSONDecodeError:
                payload = {"ok": True, "raw": raw_b[:200]}
            return resp.status, payload
    except HTTPError as e:
        raw_b = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw_b) if raw_b else {}
        except json.JSONDecodeError:
            payload = {"raw": raw_b[:400]}
        return e.code, payload
    except (URLError, TimeoutError, OSError) as e:
        return 0, {"ok": False, "error": "connection_error", "message": str(e)}


def port_up(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def main() -> int:
    global PROD_PID_BEFORE

    # --- Unit honesty ---
    check("01 honesty proven false", ops.HONESTY["proven"] is False)
    check("02 honesty ready false", ops.HONESTY["ready"] is False)
    check("03 honesty staff_ready false", ops.HONESTY["staff_ready"] is False)
    check("04 honesty full_tree false", ops.HONESTY["full_tree_indexed"] is False)
    check("05 haikal human not_started", ops.HONESTY["haikal_human_status"] == "not_started")
    check("06 metricool false", ops.HONESTY["metricool_publish"] is False)
    check("07 cr_resolved false", ops.HONESTY["cr_resolved"] is False)

    flags = ops.honesty_flags()
    check("08 flags slice ops", flags.get("nas_index_operator_depth") is True)
    check("09 flags continue prior", flags.get("nas_index_continue") is True)

    shell_flags = shell.honesty_flags()
    check("10 shell nas_index_operator_depth", shell_flags.get("nas_index_operator_depth") is True)
    check("11 shell full_tree false", shell_flags.get("full_tree_indexed") is False)
    check("12 shell staff_ready false", shell_flags.get("staff_ready") is False)

    reg = nas.registry()
    check("13 registry ok", reg.get("ok") is True)
    check("14 registry full_tree false", reg.get("full_tree_indexed") is False)
    check("15 indexing full_tree false", reg["indexing_state"].get("full_tree_indexed") is False)
    check("16 needs_sorting readonly flag", reg.get("needs_sorting_readonly") is True)
    check("17 refused tops listed", "#recycle" in (reg.get("refused_sample_tops") or []))

    # media type helpers
    check("18 png→image", nas.media_type_from_filename("x.png") == "image")
    check("19 mp4→video", nas.media_type_from_filename("x.mp4") == "video")

    # refuse archive / recycle
    try:
        nas._safe_top_folder_name("_clickup-attachment-archive")
        check("20 archive refused", False, "should raise")
    except nas.NasLibraryError as exc:
        check("20 archive refused", exc.code in ("nas_folder_refused", "nas_folder_not_safe"))
    try:
        nas._safe_top_folder_name("#recycle")
        check("21 recycle refused", False, "should raise")
    except nas.NasLibraryError as exc:
        check("21 recycle refused", exc.code in ("nas_folder_refused", "nas_folder_not_safe", "nas_folder_invalid"))

    # needs_sorting READ-only (EMPTY honesty OK)
    ns = nas.inventory_needs_sorting_sample(cap=10)
    check("22 needs_sorting ok", ns.get("ok") is True, str(ns.get("error")))
    check("23 needs_sorting non-destructive", ns.get("destructive") is False)
    check("24 needs_sorting no Volumes in items", "/Volumes/" not in json.dumps(ns.get("items") or []))
    if ns.get("empty"):
        check("25 needs_sorting EMPTY honesty", bool(ns.get("empty_message")))
    else:
        check("25 needs_sorting has files", int(ns.get("files_indexed") or 0) > 0)

    # CAP / CR honesty
    caps = ops.cap_honesty()
    check("26 CAP-GGV-01 BUILT", caps.get("CAP-GGV-01") == "BUILT")
    check("27 CAP-GGV-05 BUILT", caps.get("CAP-GGV-05") == "BUILT")
    check("28 CAP-GGV-03 SPECIFIED", caps.get("CAP-GGV-03") == "SPECIFIED")
    check("29 CAP-GGV-06 SPECIFIED", caps.get("CAP-GGV-06") == "SPECIFIED")
    check("30 CR OPEN", caps.get("cr_8c1fa12404180c02") == "OPEN")
    check("31 connection CR OPEN", caps.get("cr_connection_commissioning") == "OPEN")
    check("32 false_resolve refused", caps.get("false_resolve_refused") is True)

    # Unit browse / detail against live catalog
    conn = sqlite3.connect(str(BETA / "catalog" / "content_library.sqlite"))
    conn.row_factory = sqlite3.Row
    nas.migrate_schema(conn)
    haikal_scopes = shell.scopes_from_assignments(shell.assignments_for_person("PERS-HAIKAL"))
    browse = nas.browse_nas_index(conn, folder="GGV", limit=10, scopes=haikal_scopes)
    check("33 browse GGV ok", browse.get("ok") is True)
    check("34 browse no Volumes", "/Volumes/" not in json.dumps(browse))
    check("35 browse full_tree false", browse["indexing_state"].get("full_tree_indexed") is False)

    try:
        nas.browse_nas_index(conn, folder="AMG-Atrium", scopes=haikal_scopes)
        check("36 haikal AMG-Atrium 403", False, "should raise")
    except nas.NasLibraryError as exc:
        check("36 haikal AMG-Atrium 403", exc.http == 403)

    facets = nas.nas_index_facets(conn, scopes=haikal_scopes)
    check("37 facets ok", facets.get("ok") is True)
    check("38 facets folders list", isinstance(facets.get("folders"), list))

    # object detail
    row = conn.execute("SELECT id, rel FROM nas_index WHERE rel LIKE 'GGV/%' LIMIT 1").fetchone()
    if row is None:
        row = conn.execute("SELECT id, rel FROM nas_index LIMIT 1").fetchone()
    check("39 have indexed row", row is not None)
    oid = int(row["id"]) if row else 0
    if oid:
        detail = nas.get_nas_index_object(conn, oid, scopes=haikal_scopes if "GGV" in (row["rel"] or "") else shell.scopes_from_assignments(shell.assignments_for_person("PERS-MATT")))
        check("40 detail ok", detail.get("ok") is True)
        check("41 detail rel only", "/Volumes/" not in json.dumps(detail))
        check("42 detail path honesty", (detail.get("path_honesty") or {}).get("rel_only") is True)
    else:
        check("40 detail ok", False, "no rows")
        check("41 detail rel only", False)
        check("42 detail path honesty", False)

    # operator desk unit (no live server)
    desk = ops.operator_depth_desk(verified_person_id="PERS-HAIKAL", folder="GGV", limit=15)
    check("43 desk ok", desk.get("ok") is True)
    check("44 desk staff_ready false", desk.get("staff_ready") is False)
    check("45 desk proven false", desk.get("proven") is False)
    check("46 desk no Volumes", "/Volumes/" not in json.dumps(desk))
    check("47 desk CR OPEN", (desk.get("caps") or {}).get("cr_8c1fa12404180c02") == "OPEN")

    try:
        ops.operator_depth_desk(verified_person_id="PERS-OUTSIDER-FAKE")
        check("48 outsider desk 403", False)
    except ops.NasIndexOpsError as exc:
        check("48 outsider desk 403", exc.http == 403)

    # refuse codes
    check("49 refuse metricool", ops.refuse_code("/api/nas/index/metricool") == "metricool_refused")
    check("50 refuse proven", ops.refuse_code("/api/nas/index/proven") == "proven_refused")
    check("51 refuse full-tree", ops.refuse_code("/api/nas/index/full-tree") == "full_tree_refused")
    check("52 browse not refuse", ops.refuse_code("/api/nas/index/browse") is None)

    conn.close()

    # --- Ports / Production sacred ---
    check("53 :8788 up", port_up(8788))
    check("54 :8787 up", port_up(8787))
    PROD_PID_BEFORE = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("55 prod pid recorded", bool(PROD_PID_BEFORE), PROD_PID_BEFORE)

    # Live APIs (require development_assertion on Beta for X-Wolf-Subject)
    st, anon = http("GET", "/api/nas/index/operator-depth")
    check("56 anon desk 403", st in (401, 403), str(anon)[:120])

    st, desk_live = http(
        "GET", "/api/nas/index/operator-depth?folder=GGV&limit=10",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("57 haikal desk 200", st == 200 and desk_live.get("ok") is True, str(desk_live)[:200])
    check("58 live staff_ready false", desk_live.get("staff_ready") is False)
    check("59 live full_tree false", desk_live.get("full_tree_indexed") is False)
    check("60 live no Volumes", "/Volumes/" not in json.dumps(desk_live))
    check("61 live CR OPEN", (desk_live.get("caps") or {}).get("cr_8c1fa12404180c02") == "OPEN")

    st, browse_live = http(
        "GET", "/api/nas/index/browse?folder=GGV&media_type=image&limit=10",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("62 browse facet 200", st == 200 and browse_live.get("ok") is True, str(browse_live)[:160])

    st, deny = http(
        "GET", "/api/nas/index/browse?folder=AMG-Atrium&limit=5",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("63 wrong-scope 403", st == 403, str(deny)[:160])

    st, facets_live = http("GET", "/api/nas/index/facets", headers={"X-Wolf-Subject": HAIKAL})
    check("64 facets 200", st == 200 and facets_live.get("ok") is True)

    # object detail + next-action
    items = (browse_live.get("items") or desk_live.get("browse", {}).get("items") or [])
    if not items:
        st, search = http(
            "GET", "/api/nas/index/search?folder=GGV&limit=5",
            headers={"X-Wolf-Subject": HAIKAL},
        )
        items = search.get("items") or []
    check("65 have browse items", len(items) > 0, str(len(items)))
    if items:
        oid = items[0]["id"]
        st, detail = http(
            "GET", f"/api/nas/index/objects/{oid}",
            headers={"X-Wolf-Subject": HAIKAL},
        )
        check("66 detail 200", st == 200 and detail.get("ok") is True, str(detail)[:160])
        check("67 detail rel", bool((detail.get("object") or {}).get("rel")))
        check("68 detail no Volumes", "/Volumes/" not in json.dumps(detail))

        st, touch = http(
            "POST",
            f"/api/nas/index/objects/{oid}/next-action-touch",
            body={"note": "test next-action touch"},
            headers={"X-Wolf-Subject": HAIKAL},
        )
        check("69 next-action 200", st == 200 and touch.get("ok") is True, str(touch)[:160])
        check("70 touch refreshes nas strip", isinstance(touch.get("nas_readiness"), dict))
        check("71 touch no metricool", touch.get("metricool_publish") is False)
    else:
        for n in ("66 detail 200", "67 detail rel", "68 detail no Volumes", "69 next-action 200", "70 touch refreshes nas strip", "71 touch no metricool"):
            check(n, False, "no items")

    # Amanda / Misa / Owner seats
    for label, email in (("amanda", AMANDA), ("misa", MISA), ("owner", MATT)):
        st, body = http("GET", "/api/nas/index/operator-depth?limit=5", headers={"X-Wolf-Subject": email})
        check(f"72 {label} desk 200", st == 200 and body.get("ok") is True, str(body)[:100])

    st, out = http("GET", "/api/nas/index/operator-depth", headers={"X-Wolf-Subject": OUTSIDER})
    check("73 outsider 403", st == 403, str(out)[:120])

    # needs_sorting sample
    st, ns_live = http(
        "POST",
        "/api/nas/index/needs-sorting-sample",
        body={"cap": 10},
        headers={"X-Wolf-Subject": MATT},
    )
    check("74 needs_sorting 200", st == 200 and ns_live.get("ok") is True, str(ns_live)[:200])
    check("75 needs_sorting non-destructive", ns_live.get("destructive") is False)
    check("76 needs_sorting staff_ready false", ns_live.get("staff_ready") is False)

    # refuse archive via needs-sorting body folder
    st, bad = http(
        "POST",
        "/api/nas/index/needs-sorting-sample",
        body={"folder": "_clickup-attachment-archive", "cap": 5},
        headers={"X-Wolf-Subject": MATT},
    )
    check("77 archive folder 403", st == 403, str(bad)[:120])

    st, bad2 = http(
        "POST",
        "/api/nas/index/needs-sorting-sample",
        body={"folder": "#recycle", "cap": 5},
        headers={"X-Wolf-Subject": MATT},
    )
    check("78 recycle 403", st == 403, str(bad2)[:120])

    # refuse invent paths
    st, met = http("GET", "/api/nas/index/metricool", headers={"X-Wolf-Subject": HAIKAL})
    check("79 metricool refuse 403", st == 403, str(met)[:100])
    st, prov = http("POST", "/api/nas/index/proven", body={}, headers={"X-Wolf-Subject": HAIKAL})
    check("80 proven refuse 403", st == 403)

    # page surface
    st, page = http("GET", "/content-2.0", headers={"X-Wolf-Subject": HAIKAL})
    # content-2.0 may be HTML 200 without JSON
    check("81 content page reachable", st in (200, 302) or st == 200)

    # Production must not have these routes (or 404)
    st, prod = http("GET", "/api/nas/index/operator-depth", base=PROD)
    check("82 prod depth 404", st in (404, 403, 401), f"st={st}")

    pid_after = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("83 prod pid unchanged", pid_after == PROD_PID_BEFORE, f"{PROD_PID_BEFORE}→{pid_after}")
    check("84 beta still up", port_up(8788))

    # search enhanced facets
    st, search_f = http(
        "GET",
        "/api/nas/index/search?folder=GGV&media_type=image&limit=10",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("85 search media_type 200", st == 200 and search_f.get("ok") is True)
    check("86 search no Volumes", "/Volumes/" not in json.dumps(search_f))

    print(f"\nRESULT  PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
