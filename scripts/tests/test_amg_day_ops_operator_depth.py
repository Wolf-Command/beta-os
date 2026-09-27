#!/usr/bin/env python3
"""AMG day-ops operator depth — kind filter + detail + next-action-touch."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import amg_day_ops_operator_depth as ops  # noqa: E402
from core import amg_ops_pack as pack  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
MISA = "mlsary111@gmail.com"
OUTSIDER = "not-a-seat@example.com"
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
        with urlopen(req, timeout=8) as resp:
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


def _cr(item_id: str, catalog: Path = LIVE_DB) -> str | None:
    conn = sqlite3.connect(str(catalog))
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
    check("01 bound", flags.get("bound") == "beta-amg-day-safe")
    check("02 schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("03 slice flag", flags.get("amg_day_ops_operator_depth") is True)
    check("04 proven false", flags.get("proven") is False)
    check("05 ready false", flags.get("ready") is False)
    check("06 staff_ready false", flags.get("staff_ready") is False)
    check("07 no invent occupancy", flags.get("invented_occupancy") is False)
    check("08 no yanolja write", flags.get("yanolja_write") is False)
    check("09 empty honesty", flags.get("empty_day_ops_is_not_live") is True)
    check("10 no money", flags.get("money") is None and flags.get("folio_executed") is False)

    schema = ops.schema_document()
    check("11 schema filters", schema.get("kind_filters") == list(ops.KIND_FILTERS))
    check("12 schema caps", schema.get("caps") == list(ops.CAP_IDS))

    caps = ops.cap_honesty()
    check("13 all caps specified", caps.get("all_caps_specified") is True, str(caps)[:200])
    check("14 all crs open", caps.get("all_crs_open") is True, str(caps.get("crs"))[:200])
    check("15 false resolve refused", caps.get("false_resolve_refused") is True)

    shell_flags = shell.honesty_flags()
    check("16 shell day-ops flag", shell_flags.get("amg_day_ops_operator_depth") is True)
    check("17 shell staff_ready false", shell_flags.get("staff_ready") is False)

    check("18 refuse occupancy", ops.refuse_code("/api/amg/day-ops/occupancy") == "occupancy_refused")
    check("19 refuse proven", ops.refuse_code("/api/amg/day-ops/proven") == "proven_refused")
    check("20 refuse yanolja", ops.refuse_code("/api/amg/day-ops/yanolja") == "yanolja_refused")
    check("21 desk not refuse", ops.refuse_code("/api/amg/day-ops/operator-depth") is None)

    check("22 kind hk", ops.normalize_kind_filter("hk") == "housekeeping")
    check("23 kind maint", ops.normalize_kind_filter("maint") == "maintenance")
    check("24 kind recovery", ops.normalize_kind_filter("recovery") == "service_recovery")
    try:
        ops.normalize_kind_filter("yanolja")
        check("25 bad kind raises", False)
    except ops.DayOpsDepthError as exc:
        check("25 bad kind raises", exc.code == "invalid_kind")


def test_operator_on_copy(td: Path) -> None:
    catalog = td / "catalog.sqlite"
    pack_db = td / "pack.sqlite"
    shutil.copy2(LIVE_DB, catalog)

    try:
        ops.require_day_ops_operator("PERS-OUTSIDER-FAKE", catalog_db=catalog)
        check("26 outsider 403", False)
    except ops.DayOpsDepthError as exc:
        check("26 outsider 403", exc.http_status == 403, exc.code)

    seat = ops.require_day_ops_operator("PERS-MISA", catalog_db=catalog)
    check("27 misa seat", seat.get("person_id") == "PERS-MISA")

    prove = ops.prove_rbac(person_id="PERS-MISA", catalog_db=catalog)
    check(
        "28 misa rbac",
        prove.get("can_day_ops_operator") is True
        and prove.get("live_hotel_commission") is False,
        str(prove)[:200],
    )

    # Empty desk honesty
    desk_empty = ops.operator_depth_desk(
        verified_person_id="PERS-MISA",
        kind="hk",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("29 empty desk ok", desk_empty.get("ok") is True)
    check("30 empty true", desk_empty.get("empty") is True)
    check("31 empty message", bool(desk_empty.get("empty_message")))
    check("32 staff_ready false", desk_empty.get("staff_ready") is False)
    check("33 readiness strip", isinstance(desk_empty.get("day_ops_readiness"), dict))
    check("34 needs you strip", isinstance(desk_empty.get("day_ops_needs_you"), dict))
    check(
        "35 caps specified",
        (desk_empty.get("caps") or {}).get("CAP-AMG-04") == "SPECIFIED",
    )

    # Open one object per kind
    opened_ids: dict[str, str] = {}
    for filt, kind, title in (
        ("hk", "housekeeping", "HK fixture room turn"),
        ("maint", "maintenance", "Maint fixture AC check"),
        ("incident", "incident", "Incident fixture noise"),
        ("recovery", "service_recovery", "Recovery fixture apology"),
        ("handover", "handover", "Handover fixture night notes"),
    ):
        opened = pack.open_day_object(
            {"kind": kind, "title": title, "note": f"{filt} fixture words — not PMS."},
            verified_person_id="PERS-MISA",
            db_path=pack_db,
            catalog_db=catalog,
        )
        oid = opened["object"]["object_id"]
        opened_ids[filt] = oid
        check(f"36 open {filt}", opened.get("ok") is True and bool(oid))

    desk_hk = ops.operator_depth_desk(
        verified_person_id="PERS-MISA",
        kind="hk",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("37 hk filter count", desk_hk.get("day_candidate_count") == 1, str(desk_hk.get("day_candidate_count")))
    check(
        "38 hk filter kind",
        (desk_hk.get("day_candidates") or [{}])[0].get("kind") == "housekeeping",
    )

    desk_all = ops.operator_depth_desk(
        verified_person_id="PERS-MISA",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("39 all kinds count", desk_all.get("day_candidate_count") == 5, str(desk_all.get("day_candidate_count")))
    check("40 not empty", desk_all.get("empty") is False)
    check(
        "41 readiness open",
        (desk_all.get("day_ops_readiness") or {}).get("open_count") == 5,
    )

    oid = opened_ids["incident"]
    detail = ops.object_detail(
        oid,
        verified_person_id="PERS-MISA",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("42 detail ok", detail.get("ok") is True)
    check("43 detail no occupancy", (detail.get("object") or {}).get("occupancy") is None)
    check("44 detail no adr", (detail.get("object") or {}).get("adr") is None)
    check("45 detail next action allowed", bool((detail.get("actions") or {}).get("next_action_touch")))
    check("46 detail filter", (detail.get("object") or {}).get("filter") == "incident")

    touch = ops.next_action_touch(
        oid,
        verified_person_id="PERS-MISA",
        note="Next-action touch for incident fixture",
        kind="next_action",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("47 touch ok", touch.get("ok") is True and touch.get("recorded") is True)
    check("48 touch kind", touch.get("kind") == "next_action")
    check("49 touch refreshes readiness", isinstance(touch.get("day_ops_readiness"), dict))
    check("50 touch refreshes needs-you", isinstance(touch.get("day_ops_needs_you"), dict))
    check("51 touch no folio", touch.get("folio_executed") is False)
    check("52 touch no yanolja", touch.get("yanolja_write") is False)
    check("53 touch staff_ready false", touch.get("staff_ready") is False)

    recovery = ops.next_action_touch(
        opened_ids["recovery"],
        verified_person_id="PERS-MISA",
        note="Recovery follow-up fixture",
        kind="recovery",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("54 recovery touch", recovery.get("ok") is True and recovery.get("kind") == "recovery")

    handover = ops.next_action_touch(
        opened_ids["handover"],
        verified_person_id="PERS-MISA",
        note="Handover touch fixture",
        kind="handover_touch",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("55 handover touch", handover.get("ok") is True)

    owner_desk = ops.operator_depth_desk(
        verified_person_id="PERS-MATT",
        kind="maint",
        db_path=pack_db,
        catalog_db=catalog,
    )
    check("56 owner desk", owner_desk.get("ok") is True and owner_desk.get("day_candidate_count") == 1)

    # CRs still OPEN on copy
    for cr in ops.TARGET_CRS:
        check(f"57 {cr} open", _cr(cr, catalog) == "OPEN")


def test_live_and_ports() -> None:
    check("58 :8788 up", port_up(8788))
    check("59 :8787 up", port_up(8787))
    prod_pid = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("60 prod pid recorded", bool(prod_pid), prod_pid)

    ledger = _ledger()
    for i in range(1, 8):
        cap = f"CAP-AMG-0{i}"
        check(f"61 {cap} SPECIFIED", ledger.get(cap, [None])[0] == "SPECIFIED")

    for cr in ops.TARGET_CRS:
        check(f"62 live {cr} OPEN", _cr(cr) == "OPEN")

    st, anon = http("GET", "/api/amg/day-ops/operator-depth")
    check("63 anon desk 403", st in (401, 403), str(anon)[:120])

    st, desk = http(
        "GET",
        "/api/amg/day-ops/operator-depth?kind=hk&limit=10",
        headers={"X-Wolf-Subject": MISA},
    )
    check("64 misa desk 200", st == 200 and desk.get("ok") is True, str(desk)[:200])
    check("65 live staff_ready false", desk.get("staff_ready") is False)
    check("66 live proven false", desk.get("proven") is False)
    check("67 live CAP specified", (desk.get("caps") or {}).get("all_caps_specified") is True)
    check("68 live no invent occupancy", desk.get("invented_occupancy") is False)

    st, kinds = http("GET", "/api/amg/day-ops/kinds", headers={"X-Wolf-Subject": MISA})
    check("69 kinds 200", st == 200 and kinds.get("ok") is True)

    st, rbac = http(
        "GET",
        "/api/amg/day-ops/operator-depth/rbac",
        headers={"X-Wolf-Subject": MISA},
    )
    check("70 rbac 200", st == 200 and rbac.get("can_day_ops_operator") is True, str(rbac)[:160])

    # Seed a live fixture object via ops-pack then exercise day-ops detail/touch
    st, opened = http(
        "POST",
        "/api/amg/ops-pack/day-object",
        body={
            "kind": "incident",
            "title": "Day-ops depth live fixture",
            "note": "Live prove only. Not PMS invent.",
        },
        headers={"X-Wolf-Subject": MISA},
    )
    check("71 open day object 200", st == 200 and opened.get("ok") is True, str(opened)[:160])
    oid = ((opened.get("object") or {}).get("object_id") if isinstance(opened, dict) else None) or ""

    if oid:
        st, detail = http(
            "GET",
            f"/api/amg/day-ops/objects/{oid}",
            headers={"X-Wolf-Subject": MISA},
        )
        check("72 detail 200", st == 200 and detail.get("ok") is True, str(detail)[:160])
        check("73 detail no occupancy", (detail.get("object") or {}).get("occupancy") is None)

        st, touch = http(
            "POST",
            f"/api/amg/day-ops/objects/{oid}/next-action-touch",
            body={"note": "live next-action touch", "kind": "next_action"},
            headers={"X-Wolf-Subject": MISA},
        )
        check("74 next-action 200", st == 200 and touch.get("ok") is True, str(touch)[:160])
        check("75 touch refreshes strips", isinstance(touch.get("day_ops_needs_you"), dict))
        check("76 touch staff_ready false", touch.get("staff_ready") is False)
    else:
        for n in ("72 detail 200", "73 detail no occupancy", "74 next-action 200", "75 touch refreshes strips", "76 touch staff_ready false"):
            check(n, False, "no object id")

    st, owner = http(
        "GET",
        "/api/amg/day-ops/operator-depth?kind=incident",
        headers={"X-Wolf-Subject": MATT},
    )
    check("77 owner desk 200", st == 200 and owner.get("ok") is True, str(owner)[:120])

    st, out = http(
        "GET",
        "/api/amg/day-ops/operator-depth",
        headers={"X-Wolf-Subject": OUTSIDER},
    )
    check("78 outsider 403", st == 403, str(out)[:120])

    st, occ = http(
        "GET",
        "/api/amg/day-ops/occupancy",
        headers={"X-Wolf-Subject": MISA},
    )
    check("79 occupancy refuse 403", st == 403, str(occ)[:120])

    st, prov = http(
        "POST",
        "/api/amg/day-ops/proven",
        body={},
        headers={"X-Wolf-Subject": MISA},
    )
    check("80 proven refuse 403", st == 403, str(prov)[:120])

    st, page = http("GET", "/amg-ops-pack", headers={"X-Wolf-Subject": MISA})
    check("81 page reachable", st in (200, 302))

    st, prod = http("GET", "/api/amg/day-ops/operator-depth", base=PROD)
    check("82 prod depth 404", st in (404, 403, 401), f"st={st}")

    pid_after = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("83 prod pid unchanged", pid_after == prod_pid, f"{prod_pid}→{pid_after}")
    check("84 beta still up", port_up(8788))


def main() -> int:
    wip_before = {}
    for rel in WIP:
        path = ROOT / rel
        wip_before[rel] = sha(path) if path.is_file() else "missing"

    test_honesty()
    with tempfile.TemporaryDirectory(prefix="amg-day-ops-") as tmp:
        test_operator_on_copy(Path(tmp))
    test_live_and_ports()

    for rel, before in wip_before.items():
        path = ROOT / rel
        after = sha(path) if path.is_file() else "missing"
        check(f"85 wip {path.name}", after == before)

    print(f"\nRESULT  PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
