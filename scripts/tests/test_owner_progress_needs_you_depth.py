#!/usr/bin/env python3
"""Owner Progress Needs-You depth — desk + detail + next-action/ack/park."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import owner_progress_needs_you_depth as ops  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"
HAIKAL = "haikalqilbari123@gmail.com"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py": None,
    "scripts/phase26_team.py": None,
    "scripts/skills/__init__.py": None,
    "scripts/wolf_intelligence.py": None,
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port_up(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def listen_pid(port: int) -> str:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True,
            timeout=5,
        )
        return out.strip().splitlines()[0]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, IndexError):
        return ""


def http(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    headers: dict | None = None,
    base: str = BETA,
) -> tuple[int, dict | str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    hdrs = {"Accept": "application/json"}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    req = Request(base + path, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except (URLError, TimeoutError, OSError) as exc:
        return 0, {"ok": False, "error": "connection", "message": str(exc)}


def _cr(item_id: str) -> str | None:
    import sqlite3

    conn = sqlite3.connect(str(LIVE_DB))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_honesty() -> None:
    flags = ops.honesty_flags()
    check("01 bound", flags.get("bound") == "beta-owner-progress-safe")
    check("02 schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("03 slice flag", flags.get("owner_progress_needs_you_depth") is True)
    check("04 proven false", flags.get("proven") is False)
    check("05 ready false", flags.get("ready") is False)
    check("06 staff_ready false", flags.get("staff_ready") is False)
    check("07 haikal not_started", flags.get("haikal_human") == "not_started")
    check("08 devi parked", flags.get("devi_retest") == "parked")
    check("09 no invent haikal", flags.get("invented_haikal_human") is False)
    check("10 no invent devi", flags.get("invented_devi_done") is False)
    check("11 empty honesty", flags.get("empty_needs_you_is_not_live") is True)
    check("12 no money", flags.get("money") is None)
    check("13 no orphan", flags.get("inside_progress_not_orphan_dashboard") is True)

    schema = ops.schema_document()
    check("14 schema filters", schema.get("kind_filters") == list(ops.KIND_FILTERS))
    check("15 schema caps", schema.get("caps") == list(ops.CAP_IDS))

    caps = ops.cap_honesty()
    check("16 CAP-CORE-11 SPECIFIED", caps.get("CAP-CORE-11") == "SPECIFIED", str(caps)[:160])
    check("17 CAP-CORE-12 BUILT", caps.get("CAP-CORE-12") == "BUILT", str(caps)[:160])
    check("18 all crs open", caps.get("all_crs_open") is True, str(caps.get("crs"))[:200])
    check("19 false resolve refused", caps.get("false_resolve_refused") is True)

    shell_flags = shell.honesty_flags()
    check("20 shell nye flag", shell_flags.get("owner_progress_needs_you_depth") is True)
    check("21 shell staff_ready false", shell_flags.get("staff_ready") is False)

    check(
        "22 refuse proven",
        ops.refuse_code("/api/progress/needs-you/proven") == "proven_refused",
    )
    check(
        "23 refuse haikal-done",
        ops.refuse_code("/api/progress/needs-you/haikal-done") == "haikal_done_refused",
    )
    check(
        "24 desk not refuse",
        ops.refuse_code("/api/progress/needs-you/operator-depth") is None,
    )
    check(
        "25 park action not refuse",
        ops.refuse_code("/api/progress/needs-you/items/x/park") is None,
    )

    check("26 kind needs_you", ops.normalize_kind_filter("needs-you") == "needs_you")
    check("27 kind morning", ops.normalize_kind_filter("morning") == "morning_seed")
    try:
        ops.normalize_kind_filter("yanolja")
        check("28 bad kind raises", False)
    except ops.NeedsYouDepthError as exc:
        check("28 bad kind raises", exc.code == "invalid_kind")


def test_operator_on_copy(td: Path) -> None:
    state = td / "needs-you-operator-state.json"
    events = td / "needs-you-operator-events.jsonl"

    try:
        ops.require_owner_operator("PERS-OUTSIDER-FAKE")
        check("29 outsider 403", False)
    except ops.NeedsYouDepthError as exc:
        check("29 outsider 403", exc.http_status == 403, exc.code)

    try:
        ops.require_owner_operator("PERS-HAIKAL")
        check("30 haikal staff 403", False)
    except ops.NeedsYouDepthError as exc:
        check("30 haikal staff 403", exc.http_status == 403)

    seat = ops.require_owner_operator("PERS-MATT")
    check("31 owner seat", seat.get("person_id") == "PERS-MATT")

    prove = ops.prove_rbac(person_id="PERS-MATT")
    check(
        "32 owner rbac",
        prove.get("can_owner_progress_operator") is True
        and prove.get("haikal_human") == "not_started",
        str(prove)[:200],
    )
    prove_out = ops.prove_rbac(person_id="PERS-OUTSIDER")
    check("33 outsider rbac false", prove_out.get("can_owner_progress_operator") is False)

    desk = ops.operator_depth_desk(
        verified_person_id="PERS-MATT",
        state_path=state,
    )
    check("34 desk ok", desk.get("ok") is True)
    check("35 staff_ready false", desk.get("staff_ready") is False)
    check("36 haikal not_started", desk.get("haikal_human") == "not_started")
    check("37 devi parked", desk.get("devi_retest") == "parked")
    check("38 readiness strip", isinstance(desk.get("progress_readiness"), dict))
    check("39 needs you strip", isinstance(desk.get("needs_you_strip"), dict))
    check("40 morning seed strip", isinstance(desk.get("morning_seed_strip"), dict))
    check(
        "41 CAP-CORE-11 specified",
        (desk.get("caps") or {}).get("CAP-CORE-11") == "SPECIFIED",
    )

    desk_ny = ops.operator_depth_desk(
        verified_person_id="PERS-MATT",
        kind="needs_you",
        state_path=state,
    )
    check("42 needs_you filter ok", desk_ny.get("ok") is True)
    check(
        "43 needs_you kinds",
        all(
            (c.get("kind") == "needs_you")
            for c in (desk_ny.get("candidates") or [])
        ),
        str([(c.get("kind"), c.get("object_id")) for c in (desk_ny.get("candidates") or [])][:5]),
    )

    desk_seed = ops.operator_depth_desk(
        verified_person_id="PERS-MATT",
        kind="morning_seed",
        state_path=state,
    )
    check("44 morning seed ok", desk_seed.get("ok") is True)
    check(
        "45 morning seed nonempty or empty honest",
        desk_seed.get("empty") is True or desk_seed.get("candidate_count", 0) > 0,
    )

    # Prefer a needs_you or morning_seed item for detail/touch
    candidates = desk.get("candidates") or []
    oid = ""
    for c in candidates:
        if c.get("kind") in ("needs_you", "morning_seed", "policy", "waiting_others"):
            oid = str(c.get("object_id") or "")
            if oid:
                break
    check("46 has candidate", bool(oid), str(candidates[:2]))

    if oid:
        detail = ops.object_detail(
            oid,
            verified_person_id="PERS-MATT",
            state_path=state,
        )
        check("47 detail ok", detail.get("ok") is True)
        check("48 detail no human done", (detail.get("object") or {}).get("human_done") is False)
        check("49 detail haikal", (detail.get("object") or {}).get("haikal_human") == "not_started")
        check("50 detail next allowed", bool((detail.get("actions") or {}).get("next_action_touch")))
        check("51 detail ack allowed", bool((detail.get("actions") or {}).get("acknowledge")))
        check("52 detail park allowed", bool((detail.get("actions") or {}).get("park")))

        touch = ops.next_action_touch(
            oid,
            verified_person_id="PERS-MATT",
            note="Owner Needs-You next-action fixture",
            kind="next_action",
            state_path=state,
            events_path=events,
        )
        check("53 touch ok", touch.get("ok") is True and touch.get("recorded") is True)
        check("54 touch kind", touch.get("kind") == "next_action")
        check("55 touch refreshes needs-you", isinstance(touch.get("needs_you_strip"), dict))
        check("56 touch staff_ready false", touch.get("staff_ready") is False)
        check("57 touch haikal not_started", touch.get("haikal_human") == "not_started")
        check("58 touch no cr resolve", touch.get("cr_resolved") is False)

        ack = ops.acknowledge(
            oid,
            verified_person_id="PERS-MATT",
            note="Owner acknowledge fixture",
            state_path=state,
            events_path=events,
        )
        check("59 ack ok", ack.get("ok") is True and ack.get("kind") == "acknowledge")

        park = ops.park(
            oid,
            verified_person_id="PERS-MATT",
            note="Owner park fixture",
            state_path=state,
            events_path=events,
        )
        check("60 park ok", park.get("ok") is True and park.get("kind") == "park")
        after = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            state_path=state,
        )
        ids = {c.get("object_id") for c in (after.get("candidates") or [])}
        check("61 park removes from strip", oid not in ids, str(sorted(ids)[:8]))
    else:
        for n in range(47, 62):
            check(f"{n} skipped no oid", False, "no candidate")

    for cr in ops.TARGET_CRS:
        check(f"62 live {cr} OPEN", _cr(cr) == "OPEN")


def test_live_and_ports() -> None:
    check("63 :8788 up", port_up(8788))
    check("64 :8787 up", port_up(8787))
    prod_pid = listen_pid(8787)
    check("65 prod pid recorded", bool(prod_pid), prod_pid)

    ledger = _ledger()
    check("66 CAP-CORE-11 SPECIFIED", ledger.get("CAP-CORE-11", [None])[0] == "SPECIFIED")
    check("67 CAP-CORE-12 BUILT", ledger.get("CAP-CORE-12", [None])[0] == "BUILT")
    for cr in ops.TARGET_CRS:
        check(f"68 live {cr} OPEN", _cr(cr) == "OPEN")

    st, anon = http("GET", "/api/progress/needs-you/operator-depth")
    check("69 anon desk 403", st in (401, 403), str(anon)[:120])

    st, desk = http(
        "GET",
        "/api/progress/needs-you/operator-depth?kind=needs_you&limit=10",
        headers={"X-Wolf-Subject": MATT},
    )
    check("70 owner desk 200", st == 200 and desk.get("ok") is True, str(desk)[:200])
    check("71 live staff_ready false", desk.get("staff_ready") is False)
    check("72 live proven false", desk.get("proven") is False)
    check("73 live haikal not_started", desk.get("haikal_human") == "not_started")
    check("74 live CAP-CORE-11", (desk.get("caps") or {}).get("CAP-CORE-11") == "SPECIFIED")

    st, kinds = http(
        "GET", "/api/progress/needs-you/kinds", headers={"X-Wolf-Subject": MATT}
    )
    check("75 kinds 200", st == 200 and kinds.get("ok") is True)

    st, rbac = http(
        "GET",
        "/api/progress/needs-you/operator-depth/rbac",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "76 rbac 200",
        st == 200 and rbac.get("can_owner_progress_operator") is True,
        str(rbac)[:160],
    )

    oid = ""
    for c in desk.get("candidates") or []:
        oid = str(c.get("object_id") or "")
        if oid:
            break
    if not oid:
        st2, desk_all = http(
            "GET",
            "/api/progress/needs-you/operator-depth",
            headers={"X-Wolf-Subject": MATT},
        )
        if st2 == 200:
            for c in desk_all.get("candidates") or []:
                oid = str(c.get("object_id") or "")
                if oid:
                    break

    if oid:
        st, detail = http(
            "GET",
            f"/api/progress/needs-you/items/{oid}",
            headers={"X-Wolf-Subject": MATT},
        )
        check("77 detail 200", st == 200 and detail.get("ok") is True, str(detail)[:160])
        check(
            "78 detail no invent human",
            (detail.get("object") or {}).get("human_done") is False,
        )

        st, touch = http(
            "POST",
            f"/api/progress/needs-you/items/{oid}/next-action-touch",
            body={"note": "live next-action touch", "kind": "next_action"},
            headers={"X-Wolf-Subject": MATT},
        )
        check("79 next-action 200", st == 200 and touch.get("ok") is True, str(touch)[:160])
        check("80 touch refreshes strips", isinstance(touch.get("needs_you_strip"), dict))
        check("81 touch staff_ready false", touch.get("staff_ready") is False)

        st, ack = http(
            "POST",
            f"/api/progress/needs-you/items/{oid}/acknowledge",
            body={"note": "live ack"},
            headers={"X-Wolf-Subject": MATT},
        )
        check("82 acknowledge 200", st == 200 and ack.get("ok") is True, str(ack)[:120])
    else:
        for n in ("77 detail 200", "78 detail no invent human", "79 next-action 200", "80 touch refreshes strips", "81 touch staff_ready false", "82 acknowledge 200"):
            check(n, False, "no object id")

    st, out = http(
        "GET",
        "/api/progress/needs-you/operator-depth",
        headers={"X-Wolf-Subject": OUTSIDER},
    )
    check("83 outsider 403", st == 403, str(out)[:120])

    st, staff = http(
        "GET",
        "/api/progress/needs-you/operator-depth",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("84 staff without owner 403", st == 403, str(staff)[:120])

    st, prov = http(
        "GET",
        "/api/progress/needs-you/proven",
        headers={"X-Wolf-Subject": MATT},
    )
    check("85 proven refuse 403", st == 403, str(prov)[:120])

    st, hak = http(
        "POST",
        "/api/progress/needs-you/haikal-done",
        body={},
        headers={"X-Wolf-Subject": MATT},
    )
    check("86 haikal-done refuse 403", st == 403, str(hak)[:120])

    st, page = http("GET", "/progress", headers={"X-Wolf-Subject": MATT})
    check("87 progress page reachable", st in (200, 302))
    # Depth panel lives on existing progress.html (no orphan dashboard)
    html_path = ROOT / "dashboards" / "progress.html"
    html = html_path.read_text(encoding="utf-8")
    check("88 progress has nye panel", "needs-you-depth" in html)
    check("89 progress has nye API", "/api/progress/needs-you/operator-depth" in html)

    st, prod = http("GET", "/api/progress/needs-you/operator-depth", base=PROD)
    check("90 prod depth 404", st in (404, 403, 401), f"st={st}")

    pid_after = listen_pid(8787)
    check("91 prod pid unchanged", pid_after == prod_pid, f"{prod_pid}→{pid_after}")
    check("92 beta still up", port_up(8788))


def main() -> int:
    wip_before = {}
    for rel in WIP:
        path = ROOT / rel
        wip_before[rel] = sha(path) if path.is_file() else "missing"

    test_honesty()
    with tempfile.TemporaryDirectory(prefix="owner-nye-") as tmp:
        test_operator_on_copy(Path(tmp))
    test_live_and_ports()

    for rel, before in wip_before.items():
        path = ROOT / rel
        after = sha(path) if path.is_file() else "missing"
        check(f"93 wip {path.name}", after == before)

    print(f"\nRESULT  PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
