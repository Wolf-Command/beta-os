#!/usr/bin/env python3
"""SOP-FACTORY-1 — evidence → lesson candidate → human review gate (Beta)."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ.pop("WOLF_ALLOW_LIVE_SOP_FACTORY", None)
os.environ.pop("WOLF_SOP_FACTORY_DB", None)

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import sop_factory as sop  # noqa: E402
import serve_beta as sb  # noqa: E402

MATT = "PERS-MATT"
MATT_EMAIL = "mrwolf@wolfcommand.net"
AMANDA_EMAIL = "amanda@wolfcommand.net"
STAFF_EMAIL = "haikalqilbari123@gmail.com"

LIVE_DB = ROOT / "catalog" / "sop_factory.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
COMM_FLAGS = ROOT / "state" / "commissioning" / "LAST-HUMAN-COMM-LOOP-FINGERPRINT.json"
ARM = ROOT / "state" / "final-completion" / "packs" / "SOP-FACTORY-1-ARM.json"
PAGE = ROOT / "dashboards" / "sop-factory.html"
MODULE = ROOT / "scripts" / "core" / "sop_factory.py"

PASS = 0
FAIL = 0

NOTE = "Demo evidence: tin count was skipped on a fixture Uma close shift."
LEARN = "The miss was the missing line on the close card, not the count itself."
LESSON = "Require the tin-count line on the close card before lockup each night."
BODY = "Count the tin before the drawer is closed and record the number."


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS {name}" + (f" · {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL {name}" + (f" · {detail}" if detail else ""))


def _expect(name: str, fn, code: str) -> None:
    try:
        fn()
    except sop.SopFactoryError as exc:
        check(name, exc.code == code, f"code={exc.code}")
        return
    check(name, False, "no error")


def _http(
    method: str, url: str, email: str | None = None, body: dict | None = None
) -> tuple[int, dict | str]:
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw.decode())
            except json.JSONDecodeError:
                return resp.status, raw.decode()
    except HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw.decode())
        except json.JSONDecodeError:
            return exc.code, raw.decode()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_beta() -> tuple[ThreadingHTTPServer, int]:
    port = _free_port()

    class H(sb.BetaHandler):
        pass

    H.directory = str(ROOT / "dashboards")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.25)
    return httpd, port


def test_honesty_source() -> None:
    flags = sop.honesty_flags()
    check("honesty.pack", flags.get("pack") == "SOP-FACTORY-1")
    check("honesty.cap", flags.get("cap") == "CAP-CORE-11")
    check("honesty.human_review_gate", flags.get("human_review_gate") is True)
    check("honesty.no_auto_approve", flags.get("auto_approve") is False)
    check("honesty.not_staff_ready", flags.get("staff_ready") is False)
    check("honesty.not_commissioned", flags.get("human_commissioned") is False)
    check("honesty.adoption_false", flags.get("operating_adoption") is False)
    check("honesty.demo_not_adoption", flags.get("demo_is_live_adoption") is False)
    check("honesty.ledger_specified", flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.not_proven", flags.get("proven") is False)
    check("honesty.not_ready", flags.get("ready") is False)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN")
    src = MODULE.read_text(encoding="utf-8")
    check("module has lesson candidate", "propose_lesson_candidate" in src)
    check("module has review_decision", "def review_decision" in src)
    check("module append-only candidates", "sop_lesson_candidates is append-only" in src)
    check("page file present", PAGE.is_file())
    serve = (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    check("route review-queue", "/api/sop/review-queue" in serve)
    check("route lesson-candidate", "/api/sop/lesson-candidate" in serve)
    check("route review-decision", "/api/sop/review-decision" in serve)
    check("route page /core/sop-factory", "/core/sop-factory" in serve)
    check("live catalog sop absent", not LIVE_DB.exists())


def test_vertical_slice(scratch: Path) -> None:
    path = scratch / "slice.sqlite"
    _expect(
        "anon candidate denied",
        lambda: sop.propose_lesson_candidate(
            {"version_id": "VER-00000000-0000-4000-8000-000000000001", "lesson_note": LESSON},
            person_id=None,
            db_path=path,
        ),
        "denied",
    )
    check("anon created no file", not path.exists())

    draft = sop.create_draft(
        {"title": "Tin count", "body": BODY, "evidence_note": NOTE},
        person_id=MATT,
        db_path=path,
    )
    check("draft not live", draft.get("live") is False)
    version_id = str(draft["version_id"])

    learned = sop.record_learning(
        {"version_id": version_id, "learning_note": LEARN},
        person_id=MATT,
        db_path=path,
    )
    check("learning appended", learned.get("appended") is True)

    cand = sop.propose_lesson_candidate(
        {
            "version_id": version_id,
            "learning_id": learned["learning_id"],
            "lesson_note": LESSON,
            "demo": True,
        },
        person_id=MATT,
        db_path=path,
    )
    check("candidate pending", cand.get("review_status") == "PENDING_REVIEW")
    check("candidate not approved rule", cand.get("approved_rule") is False)
    check("candidate demo label", cand.get("demo_label") == sop.DEMO_LABEL)
    check("candidate not live", cand.get("live") is False)
    candidate_id = str(cand["candidate_id"])

    queue = sop.list_review_queue(MATT, db_path=path)
    check("queue has pending", queue.get("pending_count") == 1, str(queue.get("pending_count")))
    check(
        "queue candidate id",
        (queue.get("candidates") or [{}])[0].get("candidate_id") == candidate_id,
    )

    # DENY path — no approval, still not live
    path_deny = scratch / "deny.sqlite"
    d0 = sop.create_draft(
        {"title": "Deny path", "body": BODY, "evidence_note": NOTE},
        person_id=MATT,
        db_path=path_deny,
    )
    cdeny = sop.propose_lesson_candidate(
        {"version_id": d0["version_id"], "lesson_note": LESSON, "demo": True},
        person_id=MATT,
        db_path=path_deny,
    )
    denied = sop.review_decision(
        {
            "candidate_id": cdeny["candidate_id"],
            "decision": "DENY",
            "decision_note": "Not ready as a standing rule.",
        },
        person_id=MATT,
        db_path=path_deny,
    )
    check("deny status", denied.get("review_status") == "DENIED")
    check("deny not approved rule", denied.get("approved_rule") is False)
    check("deny not live", denied.get("live") is False)
    check("deny no approval_id", denied.get("approval_id") is None)
    read_deny = sop.read_sop(d0["sop_id"], MATT, db_path=path_deny)
    check("deny version not approved", (read_deny.get("versions") or [{}])[0].get("approved") is False)
    check("deny sop not live", read_deny.get("live") is False)
    q_after_deny = sop.list_review_queue(MATT, db_path=path_deny)
    check("deny clears queue", q_after_deny.get("pending_count") == 0)

    # APPROVE path — versioned approved draft
    approved = sop.review_decision(
        {
            "candidate_id": candidate_id,
            "decision": "APPROVE",
            "decision_note": "Human approved the demo lesson as a draft rule.",
        },
        person_id=MATT,
        db_path=path,
    )
    check("approve status", approved.get("review_status") == "APPROVED")
    check("approve is approved rule", approved.get("approved_rule") is True)
    check("approve live", approved.get("live") is True)
    check("approve has approval_id", bool(approved.get("approval_id")))
    check("approve version unchanged", approved.get("version_unchanged") is True)
    check("approve candidate unchanged", approved.get("candidate_unchanged") is True)

    body_before = sop.read_sop(draft["sop_id"], MATT, db_path=path)
    prior_body = (body_before.get("versions") or [{}])[0].get("body")
    check("prior body retained", prior_body == BODY)

    _expect(
        "second review refused",
        lambda: sop.review_decision(
            {"candidate_id": candidate_id, "decision": "DENY"},
            person_id=MATT,
            db_path=path,
        ),
        "already_reviewed",
    )

    # Append-only: update/delete refused
    conn = sqlite3.connect(str(path))
    try:
        try:
            conn.execute(
                "UPDATE sop_lesson_candidates SET lesson_note=? WHERE candidate_id=?",
                ("rewritten", candidate_id),
            )
            check("candidate update aborted", False, "update allowed")
        except sqlite3.IntegrityError as exc:
            check("candidate update aborted", "append-only" in str(exc), str(exc))
        try:
            conn.execute(
                "DELETE FROM sop_versions WHERE version_id=?", (version_id,)
            )
            check("version delete aborted", False, "delete allowed")
        except sqlite3.IntegrityError as exc:
            check("version delete aborted", "append-only" in str(exc), str(exc))
    finally:
        conn.close()

    _expect(
        "history rewrite refused",
        lambda: sop.refuse_history_rewrite({"action": "update", "version_id": version_id}),
        "append_only",
    )


def test_demo_seed(scratch: Path) -> None:
    demo = scratch / "demo-seed.sqlite"
    seeded = sop.seed_demo_vertical_slice(person_id=MATT, db_path=demo)
    check("demo seeded", seeded.get("seeded") is True)
    check("demo label", seeded.get("demo_label") == sop.DEMO_LABEL)
    check("demo pending", (seeded.get("pending_count") or 0) >= 1)
    check("demo not live", seeded.get("live") is False)
    check("demo not approved rule", seeded.get("approved_rule") is False)
    check("demo staff_ready false", seeded.get("staff_ready") is False)
    again = sop.seed_demo_vertical_slice(person_id=MATT, db_path=demo)
    check("demo idempotent", again.get("already_present") is True)
    _expect(
        "demo refuses live catalog path",
        lambda: sop.seed_demo_vertical_slice(person_id=MATT, db_path=LIVE_DB),
        "live_guard",
    )
    check("live catalog still absent", not LIVE_DB.exists())


def test_api_and_page(scratch: Path) -> None:
    path = scratch / "api.sqlite"
    os.environ["WOLF_SOP_FACTORY_DB"] = str(path)
    httpd, port = _start_beta()
    base = f"http://127.0.0.1:{port}"
    try:
        st, anon = _http("GET", f"{base}/api/sop/review-queue")
        check("unsigned review-queue 403", st == 403, str(st))
        st, _ = _http("POST", f"{base}/api/sop/lesson-candidate", None, {"lesson_note": LESSON})
        check("unsigned lesson-candidate 403", st == 403, str(st))
        st, _ = _http("POST", f"{base}/api/sop/review-decision", None, {"decision": "APPROVE"})
        check("unsigned review-decision 403", st == 403, str(st))
        st, amanda_q = _http("GET", f"{base}/api/sop/review-queue", AMANDA_EMAIL)
        check("Amanda review-queue 403", st == 403, str(st))
        st, staff_q = _http("GET", f"{base}/api/sop/review-queue", STAFF_EMAIL)
        check("staff without perm 403", st == 403, str(st))

        st, page_anon = _http("GET", f"{base}/core/sop-factory")
        check("unsigned page 403", st == 403, str(st))
        if isinstance(page_anon, str):
            check("unsigned page Access denied", "Access denied" in page_anon)
        st, page_amanda = _http("GET", f"{base}/core/sop-factory", AMANDA_EMAIL)
        check("Amanda page 403", st == 403, str(st))
        if isinstance(page_amanda, str):
            check("Amanda Access denied", "Access denied" in page_amanda)

        # Matt vertical slice via API
        st, draft = _http(
            "POST",
            f"{base}/api/sop/draft",
            MATT_EMAIL,
            {"title": "API tin count", "body": BODY, "evidence_note": NOTE},
        )
        check("Matt draft 200", st == 200 and draft.get("live") is False, str(st))
        vid = draft.get("version_id")
        st, learned = _http(
            "POST",
            f"{base}/api/sop/learn",
            MATT_EMAIL,
            {"version_id": vid, "learning_note": LEARN},
        )
        check("Matt learn 200", st == 200, str(st))
        st, cand = _http(
            "POST",
            f"{base}/api/sop/lesson-candidate",
            MATT_EMAIL,
            {
                "version_id": vid,
                "learning_id": learned.get("learning_id"),
                "lesson_note": LESSON,
                "demo": True,
            },
        )
        check("Matt candidate 200", st == 200 and cand.get("review_status") == "PENDING_REVIEW")
        st, queue = _http("GET", f"{base}/api/sop/review-queue", MATT_EMAIL)
        check("Matt queue 200", st == 200 and (queue.get("pending_count") or 0) >= 1, str(queue)[:200])
        check(
            "queue honesty stamps",
            (queue.get("honesty") or {}).get("staff_ready") is False
            and (queue.get("honesty") or {}).get("human_commissioned") is False
            and (queue.get("honesty") or {}).get("operating_adoption") is False,
        )

        st, page_matt = _http("GET", f"{base}/core/sop-factory", MATT_EMAIL)
        check("Matt page 200", st == 200, str(st))
        if isinstance(page_matt, str):
            check("Matt page title", "SOP Factory" in page_matt)
            check("Matt page honesty copy", "staff_ready" in page_matt.lower() or "Human review" in page_matt)

        st, decided = _http(
            "POST",
            f"{base}/api/sop/review-decision",
            MATT_EMAIL,
            {
                "candidate_id": cand.get("candidate_id"),
                "decision": "APPROVE",
                "decision_note": "Fixture approve for API proof.",
            },
        )
        check(
            "Matt approve via gate",
            st == 200 and decided.get("approved_rule") is True and decided.get("live") is True,
            str(decided)[:240],
        )
        st, queue2 = _http("GET", f"{base}/api/sop/review-queue", MATT_EMAIL)
        check("queue empty after approve", st == 200 and queue2.get("pending_count") == 0)

        # banned live field
        st, bad = _http(
            "POST",
            f"{base}/api/sop/review-decision",
            MATT_EMAIL,
            {"candidate_id": cand.get("candidate_id"), "decision": "DENY", "staff_ready": True},
        )
        check("refused staff_ready field", st == 400 and bad.get("error") == "refused_field", str(bad)[:200])
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_SOP_FACTORY_DB", None)


def test_preserved_flags() -> None:
    check("live sop still absent", not LIVE_DB.exists())
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    row = ledger.get("CAP-CORE-11")
    check("ledger CAP-CORE-11 SPECIFIED", isinstance(row, list) and row[0] == "SPECIFIED")
    if COMM_FLAGS.is_file():
        raw = COMM_FLAGS.read_text(encoding="utf-8")
        check("commission fingerprint no staff_ready true", '"staff_ready": true' not in raw.lower().replace(" ", ""))
    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm staff_ready false", arm.get("staff_ready") is False)
        check("arm human_commissioned false", arm.get("human_commissioned") is False)
        check("arm no_push", arm.get("no_push") is True)
        check("arm prod_mutate false", arm.get("prod_mutate") is False)


def main() -> None:
    scratch = ROOT / "state" / "build-factory" / "tmp-sop-factory-1" / f"test-{os.getpid()}"
    scratch.mkdir(parents=True, exist_ok=True)
    ledger_hash = hashlib.sha256(LEDGER.read_bytes()).hexdigest()
    live_before = LIVE_DB.exists()
    try:
        check("live absent before", live_before is False)
        test_honesty_source()
        test_vertical_slice(scratch)
        test_demo_seed(scratch)
        test_api_and_page(scratch)
        test_preserved_flags()
        check(
            "ledger unchanged",
            hashlib.sha256(LEDGER.read_bytes()).hexdigest() == ledger_hash,
        )
        check("live absent after", not LIVE_DB.exists())
    finally:
        print(f"PASS={PASS} FAIL={FAIL}")
        print(
            "COUNTS "
            f"staff_ready=False commissioned=False adoption=False "
            f"live_catalog={LIVE_DB.exists()}"
        )
    if FAIL:
        raise SystemExit(1)
    print("EXIT: SUCCESS")


if __name__ == "__main__":
    main()
