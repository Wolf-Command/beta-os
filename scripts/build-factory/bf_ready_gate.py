#!/usr/bin/env python3
"""Durable READY FOR HUMAN TEST gate + post-READY monitor + owner notify queue.

Owner P0 5 Oct 2026 20:00 WITA. A slice is READY FOR HUMAN TEST only when ALL hold:
  1 build      - result JSON exists, status not BLOCKED/FAIL, tests_fail == 0
  2 deploy     - Beta-served code changed since dispatch is live (Beta started after the
                 last change); a held reload means NOT deployed yet
  3 service    - exactly one :8788 listener, /api/health 200
  4 public     - the slice's surfaces answer at origin and at the public edge without
                 5xx; cloudflared shows no new 'Unable to reach the origin' / request errors
  5 rendered   - the slice's result JSON carries a passing rendered workflow test
                 (rendered_workflow_test.pass / browser_proof.pass == true)
  6 stability  - 5 checks over 3 minutes after deploy, no restart (launchd runs unchanged)
Until then the queue item is DONE (progress, never blocks independent work) with
ready_gate=PENDING/FAILED. The supervisor is the only writer of the dispatch queue:
the detached verifier only writes READY-GATE-STATE.json; verdicts are applied on tick.

Post-READY monitor (every supervisor tick): a READY item whose Beta/surface health
regresses is auto-revoked (ready_revoked_at, regression=true), a BETA_REGRESSION event is
queued, a P0 repair slice is armed at priority 1, and the item is re-proved after repair.

Events -> state/build-factory/NOTIFY-QUEUE.jsonl, each with delivered=false.
Never touches Production :8787. Never signals a process. Never prints command lines.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
BF = ROOT / "state" / "build-factory"
NOTIFY = BF / "NOTIFY-QUEUE.jsonl"
STATE = BF / "READY-GATE-STATE.json"
STATE_LOCK = BF / "READY-GATE-STATE.flock"
TUNLOG = Path.home() / ".openclaw" / "logs" / "dashboards-tunnel.err.log"
METRICS = "http://127.0.0.1:20241/metrics"
ORIGIN = "http://127.0.0.1:8788"
PUBLIC = "https://beta.wolfcommand.net"
LABEL = "net.wolfcommand.serve-beta"
STAB_CHECKS = 5
STAB_SPAN_SECS = 180
NOTIFY_TYPES = frozenset({
    "READY_FOR_HUMAN_TEST", "HUMAN_TEST_BLOCKER", "FAIL_NO_SELF_REPAIR", "BETA_REGRESSION",
    "SECURITY_ISOLATION", "STUCK_RECOVERY_FAILED", "OWNER_DECISION", "MAJOR_MILESTONE",
})
STATE_HUMAN = "READY FOR HUMAN TEST"
STATE_DONE = "DONE"
GIT_LAST = BF / "GIT-SNAPSHOT-LAST.json"
VERSIONED_TOKENS = ("P0", "FINANCE", "FC-", "P2P", "BZG", "AMG", "GGV", "SECURITY", "AUTH", "RBAC", "DATA",
                    "MIGRAT", "DEPLOY", "BANK", "LEDGER", "PAYMENT", "CLOSE", "PETTY", "REPAIR")
VERSION_GLOBS = ("scripts/*.py", "scripts/core/*.py", "scripts/migrations/*.py", "scripts/build-factory/*.py",
                 "scripts/tests/*.py", "dashboards/*.html", "dashboards/*.js", "dashboards/*.css")
SERVED_GLOBS = ("scripts/*.py", "scripts/core/*.py", "dashboards/*.html", "dashboards/*.js", "dashboards/*.css")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(s: str | None) -> float | None:
    try:
        return datetime.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- notify queue
def notify(kind: str, *, dedupe_key: str | None = None, **fields: object) -> dict | None:
    if kind not in NOTIFY_TYPES:
        raise ValueError(f"unknown notify type {kind}")
    key = dedupe_key or f"{kind}:{fields.get('slice') or fields.get('subject') or ''}:{fields.get('run_id') or ''}"
    if NOTIFY.exists():
        try:
            for ln in NOTIFY.read_text(encoding="utf-8").splitlines()[-400:]:
                if ln.strip() and json.loads(ln).get("dedupe_key") == key:
                    return None
        except (OSError, ValueError):
            pass
    ev = {"id": "N-" + uuid.uuid4().hex[:10], "type": kind, "at": now_iso(), "delivered": False,
          "delivered_at": None, "dedupe_key": key, "staff_ready": False, "human_commissioned": False}
    ev.update(fields)
    BF.mkdir(parents=True, exist_ok=True)
    with NOTIFY.open("a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
    return ev


# ---------------------------------------------------------------- state file
@contextmanager
def _locked_state():
    BF.mkdir(parents=True, exist_ok=True)
    with STATE_LOCK.open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            data = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
        except (OSError, ValueError):
            data = {}
        data.setdefault("items", {})
        data.setdefault("monitor", {})
        yield data
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, STATE)
        os.chmod(STATE, 0o644)


# ---------------------------------------------------------------- probes
def _sh(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=15)
    except Exception:  # noqa: BLE001
        return ""


def _code(url: str) -> int:
    class _NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):  # noqa: D401
            return None
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.7.1 bf-ready-gate"})
    try:
        return urllib.request.build_opener(_NoRedir).open(req, timeout=10).status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:  # noqa: BLE001
        return 0


def beta_service() -> dict:
    lp = _sh(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"])
    runs = re.search(r"\bruns = (\d+)", lp)
    pid = re.search(r"\bpid = (\d+)", lp)
    lis = [int(x) for x in _sh(["lsof", "-nP", "-iTCP:8788", "-sTCP:LISTEN", "-t"]).split() if x.isdigit()]
    return {"runs": int(runs.group(1)) if runs else None, "pid": int(pid.group(1)) if pid else None,
            "listeners": sorted(set(lis)), "health": _code(ORIGIN + "/api/health")}


def tunnel() -> dict:
    m = _sh(["curl", "-s", "-m", "5", METRICS])
    err = re.search(r"^cloudflared_tunnel_request_errors (\d+)", m, re.M)
    ha = re.search(r"^cloudflared_tunnel_ha_connections (\d+)", m, re.M)
    unreach = 0
    try:
        for ln in TUNLOG.read_text(errors="replace").splitlines():
            if "127.0.0.1:8788" in ln and "Unable to reach" in ln and "originService" in ln:
                unreach += 1
    except OSError:
        unreach = -1
    return {"request_errors": int(err.group(1)) if err else None, "ha": int(ha.group(1)) if ha else None,
            "origin_unreachable_lines": unreach}


def surfaces_for(item: dict) -> list[str]:
    if item.get("surfaces"):
        return list(item["surfaces"])
    key = (str(item.get("id")) + " " + str(item.get("title") or "")).upper()
    out = []
    if "UMA" in key or "CLOSE" in key:
        out += ["/uma-blu-close", "/bzg-uma-blu"]
    if "BZG" in key or "FC-" in key or "FINANCE" in key or "P2P" in key:
        out += ["/bzg/finance"]
    if "AMG" in key or "GGV" in key or "FINANCE" in key:
        out += ["/amg/finance/"]
    return out or ["/uma-blu-close", "/bzg/finance"]


def check_once(surfaces: list[str], baseline: dict | None = None) -> dict:
    svc = beta_service()
    tun = tunnel()
    origin = {p: _code(ORIGIN + p) for p in surfaces}
    public = {p: _code(PUBLIC + p) for p in surfaces}
    fails = []
    if len(svc["listeners"]) != 1:
        fails.append(f"listeners={len(svc['listeners'])}")
    if svc["health"] != 200:
        fails.append(f"health={svc['health']}")
    for p, c in origin.items():
        if c == 0 or c >= 500:
            fails.append(f"origin{p}={c}")
    for p, c in public.items():
        if c == 0 or c >= 500:
            fails.append(f"public{p}={c}")
    if baseline:
        if baseline.get("runs") is not None and svc["runs"] is not None and svc["runs"] > baseline["runs"]:
            fails.append(f"beta_restarted runs {baseline['runs']}->{svc['runs']}")
        if (baseline.get("request_errors") is not None and tun["request_errors"] is not None
                and tun["request_errors"] > baseline["request_errors"]):
            fails.append(f"tunnel_request_errors {baseline['request_errors']}->{tun['request_errors']}")
        if (baseline.get("origin_unreachable_lines", -1) >= 0
                and tun["origin_unreachable_lines"] > baseline["origin_unreachable_lines"]):
            fails.append("cloudflared_origin_unreachable")
    return {"at": now_iso(), "ok": not fails, "fails": fails, "service": svc, "tunnel": tun,
            "origin": origin, "public": public}


# ---------------------------------------------------------------- static gates
def _result(item: dict) -> dict | None:
    rel = item.get("result_json")
    if not rel:
        return None
    p = Path(rel) if Path(rel).is_absolute() else ROOT / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _beta_started_epoch(pid: int | None) -> float | None:
    if not pid:
        return None
    et = _sh(["ps", "-o", "etime=", "-p", str(pid)]).strip()
    if not et:
        return None
    days = 0
    if "-" in et:
        d, et = et.split("-", 1)
        days = int(d)
    parts = [int(x) for x in et.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return time.time() - (days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2])


def _served_changed_after(t0: float) -> float | None:
    newest = None
    for g in SERVED_GLOBS:
        for f in ROOT.glob(g):
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if m >= t0 and (newest is None or m > newest):
                newest = m
    return newest


def static_gates(item: dict) -> dict:
    res = _result(item) or {}
    gates: dict = {}
    status = str(res.get("status") or "").upper()
    try:
        fails = int(res.get("tests_fail") or 0)
    except (TypeError, ValueError):
        fails = 1
    gates["build"] = bool(res) and not ("BLOCK" in status or "FAIL" in status or status == "ERROR") and fails == 0
    t0 = _parse(item.get("dispatched_at")) or 0
    svc = beta_service()
    changed = _served_changed_after(t0) if t0 else None
    started = _beta_started_epoch(svc["pid"])
    gates["deploy"] = changed is None or (started is not None and started >= changed)
    gates["deploy_detail"] = {"served_changed": changed is not None, "beta_started_after_change": gates["deploy"],
                              "reload_held": bool(res.get("reload_held"))}
    rw = res.get("rendered_workflow_test") or res.get("browser_proof") or {}
    gates["rendered_workflow"] = bool(isinstance(rw, dict) and rw.get("pass") is True)
    gates["versioned"], gates["versioned_detail"] = versioned(item)
    return gates


def needs_versioning(item: dict) -> bool:
    if item.get("versioned_required") is not None:
        return bool(item["versioned_required"])
    key = (str(item.get("id")) + " " + str(item.get("title") or "") + " " + str(item.get("class") or "")).upper()
    return any(t in key for t in VERSIONED_TOKENS)


def versioned(item: dict) -> tuple[bool, dict]:
    """P0 finance/security/data/auth/migration/deploy slices must be pushed to GitHub before READY.

    Reads GIT-SNAPSHOT-LAST.json (written by bf_git_snapshot.py, called by beta_restart.py before
    every reload). Passes when the last snapshot was PUSHED (remote_sha == commit) at or after the
    newest change this slice made under scripts/ or dashboards/.
    """
    if not needs_versioning(item):
        return True, {"required": False}
    try:
        snap = json.loads(GIT_LAST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, {"required": True, "reason": "no_git_snapshot"}
    t0 = _parse(item.get("dispatched_at")) or 0
    newest = None
    for g in VERSION_GLOBS:
        for f in ROOT.glob(g):
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if m >= t0 and (newest is None or m > newest):
                newest = m
    snap_at = _parse(snap.get("at"))
    pushed = snap.get("result") == "PUSHED" and bool(snap.get("pushed")) and snap.get("remote_sha") == snap.get("commit")
    fresh = newest is None or (snap_at is not None and snap_at >= newest)
    detail = {"required": True, "snapshot_result": snap.get("result"), "snapshot_at": snap.get("at"),
              "commit": (snap.get("commit") or "")[:12], "pushed": pushed, "covers_slice_changes": fresh,
              "github": snap.get("github")}
    return bool(pushed and fresh), detail


# ---------------------------------------------------------------- lifecycle
def begin(item: dict) -> dict:
    """Called by the dispatcher when a worker exits cleanly. Returns the record."""
    surfaces = surfaces_for(item)
    gates = static_gates(item)
    base = {**beta_service(), **tunnel()}
    rec = {"slice": item.get("id"), "run_id": item.get("run_id"), "status": "PENDING", "began_at": now_iso(),
           "surfaces": surfaces, "static": gates, "baseline": base, "checks": [], "verdict": None,
           "repair_of": item.get("repair_of"),
           "item_view": {k: item.get(k) for k in ("id", "title", "class", "dispatched_at", "result_json",
                                                  "surfaces", "versioned_required")}}
    with _locked_state() as st:
        st["items"][str(item.get("id"))] = rec
    if os.environ.get("BF_READY_GATE_NO_SPAWN") != "1":
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "verify", str(item.get("id"))],
                         cwd=str(ROOT), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return rec


def verify(item_id: str) -> dict:
    with _locked_state() as st:
        rec = st["items"].get(item_id)
    if not rec:
        return {"error": "no_record"}
    checks = []
    gap = STAB_SPAN_SECS / max(1, STAB_CHECKS - 1)
    for i in range(STAB_CHECKS):
        checks.append(check_once(rec["surfaces"], rec["baseline"]))
        if i < STAB_CHECKS - 1:
            time.sleep(gap)
    stab_ok = all(c["ok"] for c in checks)
    item_view = {"id": rec.get("slice"), "run_id": rec.get("run_id"), **(rec.get("item_view") or {})}
    try:
        s = static_gates(item_view) if rec.get("item_view") else rec["static"]
    except Exception:  # noqa: BLE001
        s = rec["static"]
    failures = [k for k in ("build", "deploy", "rendered_workflow", "versioned") if not s.get(k, True)]
    if not stab_ok:
        failures.append("stability")
    with _locked_state() as st:
        cur = st["items"].get(item_id, rec)
        cur["checks"] = checks
        cur["static"] = s
        cur["verdict_beta_pid"] = beta_service().get("pid")
        cur["verdict"] = "PASS" if not failures else "FAIL"
        cur["failures"] = failures
        cur["status"] = "VERDICT"
        cur["verified_at"] = now_iso()
        st["items"][item_id] = cur
    return {"verdict": "PASS" if not failures else "FAIL", "failures": failures}


def _arm_repair(queue: dict, item: dict, why: str) -> str | None:
    base = str(item.get("id"))
    rid = f"{base}-BETA-REPAIR-1"
    items = queue.setdefault("items", [])
    if any(it.get("id") == rid for it in items):
        return rid
    prompt_rel = f"state/reliability/{rid}-PROMPT.md"
    text = (
        f"# {rid} — P0 Beta regression repair for {base}\n\n"
        f"The post-READY monitor revoked READY for {base}: {why}.\n"
        "Diagnose from logs (launchd `net.wolfcommand.serve-beta` runs/exit codes, /tmp/serve_beta.log, "
        "cloudflared ~/.openclaw/logs/dashboards-tunnel.err.log, state/build-factory/BETA-RELOAD-LOG.jsonl). "
        "Fix the cause in Beta code only. NEVER restart Beta yourself: launchd owns restarts; the only reload path "
        "is `python3 scripts/beta_restart.py --reason ...` which runs the reload gate and may answer RELOAD_HELD (accept it). "
        "Never touch Production :8787 / pid 1297; never signal pids 1297/2627; never print process command lines; "
        "never commit/push/clean; never mark staff_ready/human_commissioned; do not touch real 29 Sep / 3 Oct / 4 Oct close data.\n"
        f"Write result JSON `state/reliability/{rid}-RESULT.json` with status, tests_pass, tests_fail, root_cause, files_changed.\n"
    )
    (ROOT / prompt_rel).write_text(text, encoding="utf-8")
    items.insert(0, {
        "id": rid, "priority": 1, "state": "READY", "title": f"P0 Beta regression repair for {base}",
        "predecessor": None, "repair_of": base, "auto_arm": True, "auto_fix_once": False, "strict_result": True,
        "exempt_from_credit_veto": True, "staff_ready": False, "human_commissioned": False, "rebuild": False,
        "machine_solvable": True, "max_runtime_minutes": 60, "prompt": prompt_rel,
        "cursor_log": f"state/reliability/{rid}-CURSOR.log", "result_json": f"state/reliability/{rid}-RESULT.json",
        "surfaces": surfaces_for(item), "armed_by": "bf_ready_gate_post_ready_monitor", "armed_at": now_iso(),
    })
    return rid


def _arm_proof_repair(queue: dict, item: dict, fails: list) -> str | None:
    base = str(item.get("id"))
    rid = f"{base}-PROOF-REPAIR-1"
    items = queue.setdefault("items", [])
    if any(it.get("id") == rid for it in items):
        return rid
    prompt_rel = f"state/reliability/{rid}-PROMPT.md"
    orig_result = item.get("result_json") or f"state/reliability/{base}-RESULT.json"
    text = (
        f"# {rid} — READY-gate proof repair for {base}\n\n"
        f"The durable READY gate did not promote {base}; failed gates: {', '.join(fails)}.\n"
        "READY FOR HUMAN TEST needs a real rendered workflow test, not an HTML/string assert. "
        f"Using Playwright (WebKit, iPhone 14 viewport) against an ISOLATED copy of Beta (copy the catalog DB to a temp dir, "
        f"probe server on a spare port), click through the workflow this slice built ({', '.join(surfaces_for(item))}) as the staff/Finance user would, "
        "assert the visible result, and capture screenshots. Fix any genuine defect you find in Beta code. "
        f"Then add `rendered_workflow_test: {{pass: true|false, steps: [...], screenshots: [...], viewport: 'iPhone 14'}}` to BOTH "
        f"`{orig_result}` and your own result JSON. If build tests fail, fix them and update tests_fail.\n"
        "NEVER restart Beta yourself: launchd owns restarts; the only reload path is `python3 scripts/beta_restart.py --reason ...` "
        "(may answer RELOAD_HELD — accept it). Run tests with BF_IN_TEST=1. Never touch Production :8787 / pid 1297; never signal pids "
        "1297/2627; never print process command lines; never commit/push/clean; never mark staff_ready/human_commissioned; do not touch "
        "real 29 Sep / 3 Oct / 4 Oct close data; do not touch catalog/backups.\n"
        f"Write result JSON `state/reliability/{rid}-RESULT.json` with status, tests_pass, tests_fail, rendered_workflow_test, files_changed.\n"
    )
    (ROOT / prompt_rel).write_text(text, encoding="utf-8")
    items.insert(0, {
        "id": rid, "priority": 1, "state": "READY", "title": f"READY-gate proof repair for {base}",
        "predecessor": None, "repair_of": base, "auto_arm": True, "auto_fix_once": False, "strict_result": True,
        "exempt_from_credit_veto": True, "staff_ready": False, "human_commissioned": False, "rebuild": False,
        "machine_solvable": True, "max_runtime_minutes": 60, "prompt": prompt_rel,
        "cursor_log": f"state/reliability/{rid}-CURSOR.log", "result_json": f"state/reliability/{rid}-RESULT.json",
        "surfaces": surfaces_for(item), "armed_by": "bf_ready_gate_proof_repair", "armed_at": now_iso(),
    })
    return rid


def apply_verdicts(queue: dict) -> list[str]:
    notes: list[str] = []
    by_id = {str(it.get("id")): it for it in queue.get("items") or []}
    reprove: list[dict] = []
    with _locked_state() as st:
        for sid, rec in st["items"].items():
            if rec.get("status") != "VERDICT" or rec.get("applied_at"):
                continue
            item = by_id.get(sid)
            rec["applied_at"] = now_iso()
            if not item:
                continue
            item["ready_gate"] = rec["verdict"]
            item["ready_gate_failures"] = rec.get("failures", [])
            item["staff_ready"] = False
            item["human_commissioned"] = False
            if rec["verdict"] == "PASS":
                item["state"] = STATE_HUMAN
                item["ready_at"] = now_iso()
                item.pop("ready_revoked_at", None)
                item["regression"] = False
                rec["monitor_baseline"] = {**beta_service(), **tunnel()}
                notify("READY_FOR_HUMAN_TEST", slice=sid, run_id=rec.get("run_id"), surfaces=rec.get("surfaces"),
                       dedupe_key=f"READY:{sid}:{rec.get('verified_at')}")
                notes.append(f"ready:{sid}")
                orig = item.get("repair_of")
                if orig and orig in by_id:
                    # Defer begin() until the flock is released — begin() also needs the lock.
                    reprove.append(by_id[orig])
                    notes.append(f"reprove:{orig}")
            else:
                item["state"] = STATE_DONE
                fails = rec.get("failures", [])
                kind = "HUMAN_TEST_BLOCKER"
                if "stability" in fails:
                    kind = "BETA_REGRESSION"
                    _arm_repair(queue, item, "post-deploy stability failed: " + "; ".join(
                        sorted({f for c in rec.get("checks", []) for f in c.get("fails", [])}))[:300])
                elif {"rendered_workflow", "build"} & set(fails) and not item.get("repair_of"):
                    # Self-repair once: prove/fix the rendered workflow, then the original re-proves.
                    pid_ = f"{sid}-PROOF-REPAIR-1"
                    if any(it.get("id") == pid_ and it.get("state") in (STATE_DONE, STATE_HUMAN) and it.get("ready_gate") for it in queue.get("items") or []):
                        kind = "FAIL_NO_SELF_REPAIR"
                    else:
                        _arm_proof_repair(queue, item, fails)
                        notes.append(f"proof_repair_armed:{sid}")
                notify(kind, slice=sid, run_id=rec.get("run_id"), failures=fails,
                       detail={"static": rec.get("static")}, dedupe_key=f"GATEFAIL:{sid}:{rec.get('verified_at')}")
                notes.append(f"not_ready:{sid}:{','.join(fails)}")
    for it in reprove:
        try:
            begin(it)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"reprove_error:{it.get('id')}:{exc.__class__.__name__}")
    return notes


def post_ready_monitor(queue: dict) -> list[str]:
    notes: list[str] = []
    ready = [it for it in queue.get("items") or [] if it.get("state") == STATE_HUMAN and it.get("ready_gate") == "PASS"]
    if not ready:
        return notes
    surfaces = sorted({p for it in ready for p in surfaces_for(it)})
    with _locked_state() as st:
        mon = st["monitor"]
        base = mon.get("baseline") or {**beta_service(), **tunnel()}
        chk = check_once(surfaces, {"request_errors": base.get("request_errors"),
                                    "origin_unreachable_lines": base.get("origin_unreachable_lines")})
        mon["last"] = chk
        prev_fail = bool(mon.get("consecutive_fail"))
        hard = any(f.startswith("tunnel_request_errors") or f == "cloudflared_origin_unreachable" for f in chk["fails"])
        if chk["ok"]:
            mon["consecutive_fail"] = 0
            mon["baseline"] = {**chk["service"], **chk["tunnel"]}
            return notes
        mon["consecutive_fail"] = int(mon.get("consecutive_fail") or 0) + 1
        if not (hard or prev_fail):
            return notes
        mon["baseline"] = {**chk["service"], **chk["tunnel"]}
    for it in ready:
        mine = set(surfaces_for(it))
        affected = [f for f in chk["fails"]
                    if not f.startswith(("origin/", "public/")) or f.split("=")[0].replace("origin", "").replace("public", "") in mine]
        if not affected:
            continue
        it["state"] = STATE_DONE
        it["ready_gate"] = "REVOKED"
        it["regression"] = True
        it["ready_revoked_at"] = now_iso()
        it["regression_reason"] = chk["fails"]
        rid = _arm_repair(queue, it, "; ".join(chk["fails"]))
        notify("BETA_REGRESSION", slice=it.get("id"), run_id=it.get("run_id"), failures=chk["fails"],
               repair_slice=rid, ready_revoked=True, dedupe_key=f"REGRESSION:{it.get('id')}:{it['ready_revoked_at'][:16]}")
        notes.append(f"revoked:{it.get('id')}")
    return notes


RECHECKABLE = frozenset({"deploy", "versioned", "stability"})


def recheck_after_deploy(queue: dict) -> list[str]:
    """Re-run the gate for items that failed ONLY on deploy/versioned/stability once Beta was
    reloaded (new pid) or a newer GitHub snapshot exists. Held-reload items get re-proved."""
    notes: list[str] = []
    by_id = {str(it.get("id")): it for it in queue.get("items") or []}
    svc_pid = beta_service().get("pid")
    try:
        snap_at = json.loads(GIT_LAST.read_text(encoding="utf-8")).get("at")
    except (OSError, ValueError):
        snap_at = None
    todo = []
    with _locked_state() as st:
        for sid, rec in st["items"].items():
            if rec.get("verdict") != "FAIL" or not rec.get("applied_at"):
                continue
            fails = set(rec.get("failures") or [])
            if not fails or not fails <= RECHECKABLE:
                continue
            item = by_id.get(sid)
            if not item or item.get("state") not in (STATE_DONE,):
                continue
            moved = (svc_pid and svc_pid != rec.get("verdict_beta_pid")) or (
                "versioned" in fails and snap_at and snap_at != (rec.get("static", {}).get("versioned_detail") or {}).get("snapshot_at"))
            if moved and int(rec.get("rechecks") or 0) < 6:
                todo.append((item, int(rec.get("rechecks") or 0) + 1))
    for item, n in todo:
        begin(item)
        with _locked_state() as st:
            st["items"][str(item.get("id"))]["rechecks"] = n
        item["ready_gate"] = "PENDING"
        notes.append(f"recheck:{item.get('id')}")
    return notes


def maybe_deploy(queue: dict) -> list[str]:
    """Deploy owner: if a finished slice is waiting only for its code to go live, ask for ONE gated
    reload via scripts/beta_restart.py (detached; the gate may answer RELOAD_HELD — e.g. human-test
    window, cooldown, close/petty/Finance activity). launchd still owns the Beta process."""
    waiting = []
    with _locked_state() as st:
        for sid, rec in st["items"].items():
            if rec.get("verdict") == "FAIL" and "deploy" in (rec.get("failures") or []) and \
                    set(rec.get("failures") or []) <= RECHECKABLE:
                waiting.append(sid)
        last = st["monitor"].get("deploy_requested_at")
        if not waiting:
            return []
        if last and (_parse(now_iso()) or 0) - (_parse(last) or 0) < 15 * 60:
            return []
        st["monitor"]["deploy_requested_at"] = now_iso()
    env = dict(os.environ, BF_RELOAD_CALLER="bf_ready_gate.deploy")
    subprocess.Popen([sys.executable, str(ROOT / "scripts" / "beta_restart.py"), "--reason",
                      "ready-gate deploy for " + ",".join(sorted(waiting))[:150]],
                     cwd=str(ROOT), env=env, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return [f"deploy_requested:{','.join(sorted(waiting))}"]


def tick(queue: dict) -> list[str]:
    notes = []
    for fn in (recheck_after_deploy, maybe_deploy):
        try:
            notes += fn(queue)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{fn.__name__}_error:{exc.__class__.__name__}")
    try:
        notes += apply_verdicts(queue)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"ready_gate_apply_error:{exc.__class__.__name__}")
    try:
        notes += post_ready_monitor(queue)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"post_ready_monitor_error:{exc.__class__.__name__}")
    return notes


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "verify":
        print(json.dumps(verify(sys.argv[2])))
    elif len(sys.argv) >= 2 and sys.argv[1] == "check":
        print(json.dumps(check_once(sys.argv[2:] or ["/uma-blu-close", "/bzg/finance"]), indent=1))
    else:
        print(__doc__)
