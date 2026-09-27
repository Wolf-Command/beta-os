#!/usr/bin/env python3
"""F2 machine half for CORE-01, 02, 03, 04, 06, 07, 09, 10.

Lifecycle writes go to a temp copy from canonical_guard.backup_catalog.
The live catalog is read only. Unsigned, spoofed, and bad-JWT callers stay
denied on Beta. No Cloudflare session is minted. The ledger file is not
edited. Staff ready and human commissioned stay unset.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import approvals as apr  # noqa: E402
from core import audit as audit_mod  # noqa: E402
from core import business_dashboard as desk  # noqa: E402
from core import canonical_guard  # noqa: E402
from core import evidence as evidence_mod  # noqa: E402
from core import exceptions as exceptions_mod  # noqa: E402
from core import ledger_class  # noqa: E402
from core import owner_command  # noqa: E402
from core import rbac  # noqa: E402
from core import staffing  # noqa: E402
from core import work_items as wi  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
PRESERVED = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
THIRD = "GEX-41967006-311f-4ab0-9802-1e6db54ce18e"
MATT = "PERS-MATT"
HAIKAL = "PERS-HAIKAL"
DEVI = "PERS-DEVI"
ENTITY = "ENT-GGV"
UMA = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
CONTENT = {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"}
SPOOF = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
API_PATHS = (
    "/api/core/me",
    "/api/core/entities",
    "/api/core/entities/ENT-GGV",
    "/api/core/roles",
    "/api/core/persons/PERS-HAIKAL/assignments",
    "/api/core/me/assignments",
    "/api/core/permissions",
    "/api/core/me/permissions",
    "/api/core/work-items",
    "/api/core/work-items/WI-NONE",
    "/api/core/approvals",
    "/api/core/approvals/APR-NONE",
    "/api/owner/command",
)
PAGE_PATHS = ("/content-2.0", "/bzg/uma-blu", "/wolf", "/ggv/finance", "/signout")
PUBLIC_PATHS = (
    "/api/core/me",
    "/api/core/entities",
    "/api/core/work-items",
    "/api/core/approvals",
    "/api/owner/command",
    "/wolf",
)

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _listener(pid: str) -> str:
    proc = subprocess.run(
        ["ps", "-p", pid, "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout or "").strip()


def _beta_pid() -> str:
    proc = subprocess.run(
        ["lsof", "-nP", "-iTCP:8788", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in (proc.stdout or "").splitlines():
        if "127.0.0.1:8788" not in line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            return parts[1]
    return ""


def _live_counts() -> dict[str, int]:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        def n(sql: str) -> int:
            return int(conn.execute(sql).fetchone()[0])

        preserved = conn.execute(
            "SELECT status, invalidate_reason FROM core_evidence_records WHERE evidence_id=?",
            (PRESERVED,),
        ).fetchone()
        return {
            "evidence": n("SELECT COUNT(*) FROM core_evidence_records"),
            "exceptions": n("SELECT COUNT(*) FROM core_governance_exceptions"),
            "decisions": n("SELECT COUNT(*) FROM core_approval_decisions"),
            "requests": n("SELECT COUNT(*) FROM core_approval_requests"),
            "work": n("SELECT COUNT(*) FROM core_work_items"),
            "policies": n("SELECT COUNT(*) FROM core_governance_policies"),
            "persons": n("SELECT COUNT(*) FROM org_persons"),
            "assignments": n("SELECT COUNT(*) FROM org_assignments"),
            "preserved_invalid": int(
                preserved is not None
                and preserved[0] == "INVALIDATED"
                and preserved[1] == "P4-TEST cleanup"
            ),
        }
    finally:
        conn.close()


def _origin(method: str, path: str, headers: dict[str, str] | None = None, body: bytes | None = None):
    conn = HTTPConnection(ORIGIN[0], ORIGIN[1], timeout=8)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        raw = resp.read(4096)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
    finally:
        conn.close()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return status, parsed, location


def _public(path: str):
    conn = HTTPSConnection(PUBLIC_HOST, timeout=15)
    try:
        conn.request("GET", path, headers={"User-Agent": "wolf-f2-machine"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        www = resp.getheader("WWW-Authenticate") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, www, server


def _ggv(report: dict) -> dict:
    for card in report.get("companies") or []:
        if card.get("entity_id") == ENTITY:
            return card
    return {}


def test_listeners(beta_pid: str) -> None:
    prod = _listener(PROD_PID)
    check("prod pid 15975 still serve.py", "serve.py" in prod and "8787" in prod, prod[:180])
    beta = _listener(beta_pid) if beta_pid else ""
    check("beta command is serve_beta.py", "serve_beta.py" in beta, beta[:180])
    print(f"NOTE  beta_pid={beta_pid} prod_pid={PROD_PID}")


def test_routes(live_before: dict[str, int]) -> None:
    callers = (
        ("unsigned", {}),
        ("spoof email", {"Cf-Access-Authenticated-User-Email": SPOOF}),
        ("subject header", {"X-Wolf-Subject": MATT}),
        ("bad jwt", {"Cf-Access-Jwt-Assertion": BAD_JWT}),
    )
    for path in API_PATHS:
        for label, headers in callers:
            status, body, _loc = _origin("GET", path, headers)
            error = str(body.get("error") or "")
            leaked = any(
                key in body
                for key in ("entities", "assignments", "permissions", "work_items", "requests")
            )
            if label == "bad jwt" and path == "/api/owner/command":
                jwt_ok = error in {"invalid_token", "forbidden"}
            elif label == "bad jwt":
                jwt_ok = error == "invalid_token"
            else:
                jwt_ok = error in {"missing_auth", "forbidden"}
            check(
                f"{label} GET {path} denied",
                status == 403 and jwt_ok and not leaked,
                f"status={status} error={error} leaked={leaked}",
            )
    for path in PAGE_PATHS:
        if path == "/signout":
            continue
        for label, headers in callers:
            status, _body, _loc = _origin("GET", path, headers)
            check(f"{label} GET {path} denied", status == 403, f"status={status}")
    status, _body, location = _origin("GET", "/signout")
    check(
        "unsigned signout redirects to access logout",
        status == 302 and "cdn-cgi/access/logout" in location and "8787" not in location,
        f"status={status} location={location[:120]}",
    )
    status, body, _loc = _origin("GET", "/api/core/auth-mode")
    mode = body.get("auth_mode")
    logout = str(body.get("access_logout_url") or "")
    check(
        "auth-mode is cloudflare access without a printed audience",
        status == 200 and mode == "cloudflare_access" and "access/logout" in logout,
        f"status={status} mode={mode}",
    )
    print("NOTE  auth-mode audience value not printed")
    post = json.dumps({"title": "f2 isolated"}).encode()
    for path in ("/api/core/work-items", "/api/core/approvals"):
        status, body, _loc = _origin("POST", path, {"Content-Type": "application/json"}, post)
        check(
            f"unsigned POST {path} denied",
            status == 403 and str(body.get("error") or "") in {"missing_auth", "forbidden"},
            f"status={status} error={body.get('error')}",
        )
    for path in PUBLIC_PATHS:
        status, location, www, server = _public(path)
        parts = urlsplit(location)
        check(
            f"public {path} login redirect",
            status == 302
            and parts.hostname == LOGIN_HOST
            and parts.path == LOGIN_PATH
            and www.startswith("Cloudflare-Access")
            and server.lower() == "cloudflare",
            f"status={status} host={parts.hostname} path={parts.path} server={server}",
        )
    after = _live_counts()
    check("live work count unchanged after unsigned posts", after["work"] == live_before["work"], str(after["work"]))
    check(
        "live approval requests unchanged after unsigned posts",
        after["requests"] == live_before["requests"],
        str(after["requests"]),
    )


def test_isolated(live_before: dict[str, int]) -> None:
    dest = canonical_guard.isolate_runtime_catalog()
    copy_dir = dest.parent
    try:
        check("isolated copy is not the live catalog", dest.resolve() != CATALOG.resolve())
        check("isolated copy is under tmp-f1", "tmp-f1" in str(dest))
        check("LIVE_CATALOG_DB stays the real file", audit_mod.LIVE_CATALOG_DB == CATALOG.resolve())

        name_denied = rbac.can("Haikal", "content.plan.read", CONTENT) is False
        email_denied = rbac.can("haikal@example.invalid", "content.plan.read", CONTENT) is False
        check("display name is not an allow", name_denied)
        check("email string is not an allow", email_denied)
        check("Haikal lacks organisation.entity.read", rbac.can(HAIKAL, "organisation.entity.read", CONTENT) is False)
        check("Haikal lacks organisation.role.read", rbac.can(HAIKAL, "organisation.role.read", CONTENT) is False)
        check("Haikal holds content.plan.read", rbac.can(HAIKAL, "content.plan.read", CONTENT) is True)
        check("Haikal lacks venue.close.read on Uma", rbac.can(HAIKAL, "venue.close.read", UMA) is False)
        check("Devi lacks organisation.entity.read", rbac.can(DEVI, "organisation.entity.read", CONTENT) is False)
        check("Devi lacks content.plan.read", rbac.can(DEVI, "content.plan.read", CONTENT) is False)
        check("Devi holds venue.close.read on Uma", rbac.can(DEVI, "venue.close.read", UMA) is True)
        check("Devi lacks finance.nota.read", rbac.can(DEVI, "finance.nota.read", {"entity_id": ENTITY}) is False)
        check("Matt holds organisation.entity.read", rbac.can(MATT, "organisation.entity.read", CONTENT) is True)
        check("Matt holds organisation.role.read", rbac.can(MATT, "organisation.role.read", CONTENT) is True)

        active = staffing.list_assignments_for_person(HAIKAL, include_ended=False)
        ended = staffing.list_assignments_for_person(HAIKAL, include_ended=True)
        active_ids = {row["assignment_id"] for row in active}
        ended_ids = {row["assignment_id"]: row["status"] for row in ended}
        check("active assignment is ASG-HAIKAL-CD-1", active_ids == {"ASG-HAIKAL-CD-1"}, str(sorted(active_ids)))
        check("ended assignment is not active", ended_ids.get("ASG-HAIKAL-VE-1") == "ENDED", str(ended_ids))
        check("email string has no assignments", staffing.list_assignments_for_person(SPOOF) == [])

        before_snap = desk.read_snapshot()
        before_work = len(before_snap.get("work") or [])
        before_cmd = owner_command.build_command(verified_person_id=MATT)
        before_ledger = before_cmd.get("ledger_classification") or {}
        before_valid = (before_ledger.get("evidence") or {}).get("valid_operational")
        before_invalid = (before_ledger.get("evidence") or {}).get("invalid_test")
        before_ex = (before_cmd.get("exceptions") or {})
        ggv_before = _ggv(before_cmd)
        check(
            "owner exceptions valid operational is 0 before the copy writes",
            before_ex.get("valid_operational_count") == 0 and before_ex.get("invalid_test_count") == 3,
            str(before_ex.get("valid_operational_count")),
        )
        check(
            "GGV exception card value is the valid count",
            (ggv_before.get("exceptions") or {}).get("value") == 0
            and (ggv_before.get("exceptions") or {}).get("invalid_test") == 3,
            str(ggv_before.get("exceptions")),
        )
        check("cadence is not done", before_ex.get("cadence_done") is False)
        check(
            "preserved evidence is classified invalid on the copy",
            PRESERVED in ((before_ledger.get("evidence") or {}).get("invalid_test_ids") or []),
        )

        item = wi.create_work_item(
            title="F2 isolated work item",
            owning_entity_id=ENTITY,
            verified_person_id=MATT,
            owner_person_id=MATT,
            owner_org_assignment_id="ASG-MATT-OWNER-1",
        )
        wid = item["work_item_id"]
        check("work item created OPEN", item.get("status") == "OPEN", str(item.get("status")))
        try:
            wi.verify_work_item(wid, verified_person_id=MATT)
            check("verify from OPEN denied", False, "verify returned")
        except wi.WorkItemError as exc:
            check("verify from OPEN denied", exc.code == "illegal_transition", exc.code)
        still = wi.get_work_item(wid)
        check("illegal verify left OPEN", still and still.get("status") == "OPEN", str(still))
        trail = ["OPEN"]
        for fn, expect in (
            (wi.start_work_item, "IN_PROGRESS"),
            (wi.block_work_item, "BLOCKED"),
            (wi.start_work_item, "IN_PROGRESS"),
            (wi.claim_complete, "COMPLETED"),
            (wi.verify_work_item, "VERIFIED"),
        ):
            row = fn(wid, verified_person_id=MATT)
            trail.append(row.get("status"))
            check(f"work reached {expect}", row.get("status") == expect, str(row.get("status")))
        print("NOTE  trail=" + ">".join(trail))
        try:
            wi.create_work_item(
                title="F2 name creator",
                owning_entity_id=ENTITY,
                verified_person_id="Matt",
            )
            check("display name cannot create a work item", False, "create returned")
        except wi.WorkItemError as exc:
            check(
                "display name cannot create a work item",
                exc.code in {"unknown_owner", "entity_out_of_scope", "missing_verified_person"},
                exc.code,
            )

        after_work = desk.read_snapshot()
        proof = desk.prove_propagation(before_snap, after_work)
        check("dashboard propagation did not claim a ledger write", proof.get("ledger_write") is False)
        check(
            "work item changed the dashboard digest",
            proof.get("before_digest") and proof.get("before_digest") != proof.get("after_digest"),
        )
        check(
            "snapshot work list grew by one",
            len(after_work.get("work") or []) == before_work + 1,
            str(len(after_work.get("work") or [])),
        )
        ids = {row.get("work_item_id") for row in after_work.get("work") or []}
        check("new work item is on the snapshot", wid in ids)

        opened = apr.create_approval_request(
            title="F2 isolated approval",
            owning_entity_id=ENTITY,
            required_permission_code="content.plan.read",
            verified_person_id=MATT,
            requested_by_assignment_id="ASG-MATT-OWNER-1",
            request_type="GENERAL",
        )
        rid = opened["approval_request_id"]
        check("approval request is PENDING", opened.get("status") == "PENDING", str(opened.get("status")))
        pending_cmd = owner_command.build_command(verified_person_id=MATT)
        pending_card = (_ggv(pending_cmd).get("approvals") or {})
        check(
            "owner card shows the pending approval",
            pending_card.get("value") == 1 and pending_card.get("state") == "READ",
            str(pending_card),
        )
        try:
            apr.reject_request(rid, verified_person_id=DEVI, reason="Devi lacks this permission")
            check("Devi cannot decide the approval", False, "reject returned")
        except apr.ApprovalError as exc:
            check(
                "Devi cannot decide the approval",
                exc.code in {"rbac_denied", "required_permission_denied"},
                exc.code,
            )
        try:
            apr.approve_request(rid, verified_person_id="Matt", reason="name is not a person id")
            check("display name cannot decide", False, "approve returned")
        except apr.ApprovalError as exc:
            check("display name cannot decide", exc.http_status in {400, 403}, exc.code)
        decided = apr.approve_request(
            rid,
            verified_person_id=MATT,
            decided_by_assignment_id="ASG-MATT-OWNER-1",
            reason="F2 isolated approve",
        )
        check(
            "approval reached APPROVED",
            (decided.get("request") or {}).get("status") == "APPROVED",
            str((decided.get("request") or {}).get("status")),
        )
        check("decision actor is the person id", (decided.get("decision") or {}).get("decided_by_person_id") == MATT)
        closed = owner_command.build_command(verified_person_id=MATT)
        closed_card = (_ggv(closed).get("approvals") or {})
        check(
            "owner card drops the approval after it is decided",
            closed_card.get("value") == 0,
            str(closed_card),
        )
        rejected_open = apr.create_approval_request(
            title="F2 isolated rejection",
            owning_entity_id=ENTITY,
            required_permission_code="content.plan.read",
            verified_person_id=MATT,
            requested_by_assignment_id="ASG-MATT-OWNER-1",
            request_type="GENERAL",
        )
        rejected = apr.reject_request(
            rejected_open["approval_request_id"],
            verified_person_id=MATT,
            decided_by_assignment_id="ASG-MATT-OWNER-1",
            reason="F2 isolated reject",
        )
        check(
            "second request reached REJECTED",
            (rejected.get("request") or {}).get("status") == "REJECTED",
            str((rejected.get("request") or {}).get("status")),
        )

        human = evidence_mod.submit_evidence(
            entity_id=ENTITY,
            evidence_type="work_note",
            governed_object_type="work_item",
            governed_object_id=wid,
            verified_person_id=MATT,
            submitted_by_assignment_id="ASG-MATT-OWNER-1",
            source_type="HUMAN",
            source_reference="F2-isolated-note",
        )
        hid = human["evidence_id"]
        check(
            "fresh human evidence is valid operational",
            ledger_class.record_class("core_evidence_records", human) == ledger_class.VALID,
        )
        shown = owner_command.build_command(verified_person_id=MATT)
        shown_ev = (shown.get("ledger_classification") or {}).get("evidence") or {}
        check(
            "owner evidence valid count rose by one",
            shown_ev.get("valid_operational") == (before_valid or 0) + 1,
            str(shown_ev.get("valid_operational")),
        )
        invalid = evidence_mod.invalidate_evidence(
            hid,
            verified_person_id=MATT,
            reason="F2 isolated invalidate",
        )
        check("invalidated evidence is INVALID_TEST", ledger_class.is_invalid_or_test("core_evidence_records", invalid))
        test_row = evidence_mod.submit_evidence(
            entity_id=ENTITY,
            evidence_type="work_note",
            governed_object_type="work_item",
            governed_object_id=wid,
            verified_person_id=MATT,
            source_type="TEST",
            source_reference="F2-isolated-test-source",
        )
        check(
            "TEST source evidence is INVALID_TEST while stored",
            ledger_class.is_invalid_or_test("core_evidence_records", test_row),
        )
        after_ev = owner_command.build_command(verified_person_id=MATT)
        after_class = (after_ev.get("ledger_classification") or {}).get("evidence") or {}
        check(
            "owner evidence valid count returned to the start",
            after_class.get("valid_operational") == before_valid,
            str(after_class.get("valid_operational")),
        )
        check(
            "owner evidence invalid count rose",
            (after_class.get("invalid_test") or 0) >= (before_invalid or 0) + 1,
            str(after_class.get("invalid_test")),
        )
        check(
            "preserved evidence id still classified invalid",
            PRESERVED in (after_class.get("invalid_test_ids") or []),
        )

        before_ex_n = int(
            sqlite3.connect(str(dest)).execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0]
        )
        try:
            exceptions_mod.request_exception(
                entity_id=ENTITY,
                governed_object_type="evidence_requirement",
                governed_object_id="EVR-HABITAT-CONTENT-PUBLISH",
                control_type="EVIDENCE_REQUIREMENT",
                control_reference="EVR-HABITAT-CONTENT-PUBLISH",
                reason="F2 isolated request with no registered control",
                verified_person_id=MATT,
            )
            check("unregistered control cannot open an exception", False, "request returned")
        except exceptions_mod.ExceptionError as exc:
            check("unregistered control cannot open an exception", exc.code == "not_exceptionable", exc.code)
        after_ex_n = int(
            sqlite3.connect(str(dest)).execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0]
        )
        check("exception table did not grow", after_ex_n == before_ex_n, str(after_ex_n))
        final_cmd = owner_command.build_command(verified_person_id=MATT)
        final_ex = final_cmd.get("exceptions") or {}
        check(
            "exceptions stay 0 valid and 3 INVALID/TEST",
            final_ex.get("valid_operational_count") == 0 and final_ex.get("invalid_test_count") == 3,
            str(final_ex.get("invalid_test_count")),
        )
        check("cadence still not done", final_ex.get("cadence_done") is False)
        ids = {row.get("id") for row in final_ex.get("items") or []}
        check("third rejected exception is still listed", THIRD in ids)
        classes = {
            row.get("id"): row.get("record_class")
            for row in final_ex.get("items") or []
        }
        check(
            "listed exceptions are INVALID_TEST",
            classes.get(THIRD) == "INVALID_TEST" and all(value == "INVALID_TEST" for value in classes.values()),
            str(classes),
        )
        check("staff ready stays false", final_cmd.get("staff_ready") is False)
        check("human commissioned stays false", final_cmd.get("human_commissioned") is False)
    finally:
        shutil.rmtree(copy_dir, ignore_errors=True)
    check("isolated copy removed", not copy_dir.exists())
    after = _live_counts()
    for key in (
        "evidence",
        "exceptions",
        "decisions",
        "requests",
        "work",
        "policies",
        "persons",
        "assignments",
        "preserved_invalid",
    ):
        check(f"live {key} unchanged", after[key] == live_before[key], f"{live_before[key]} -> {after[key]}")


def main() -> int:
    digest = hashlib.sha256(LEDGER.read_bytes()).hexdigest()
    beta_pid = _beta_pid()
    live_before = _live_counts()
    print(
        "NOTE  live "
        + " ".join(f"{key}={value}" for key, value in live_before.items())
    )
    test_listeners(beta_pid)
    test_routes(live_before)
    test_isolated(live_before)
    check("ledger file unchanged", hashlib.sha256(LEDGER.read_bytes()).hexdigest() == digest)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
