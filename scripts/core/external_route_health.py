#!/usr/bin/env python3
"""EXTERNAL-ROUTE-HEALTH — Beta critical external finance routes → service truth.

P0 reset 30 Sep 2026: CF Host Error 502 on /amg|/bzg|/ggv/finance was caused by
Atrium Finance sidecar :8790 down unsupervised. Beta atrium_full_mount proxies
to 127.0.0.1:8790; when down returns sidecar_unavailable 502 → CF Host Error.

This probe checks CRITICAL EXTERNAL Beta routes from outside the origin where
possible, plus local deps that cause Host Error. Safe autorecovery:
launchctl kickstart -k for net.wolfcommand.atrium-finance-sidecar ONLY when
:8790 is down and the LaunchAgent exists. Never touches prod :8787.
Never weakens auth. staff_ready / human_commissioned stay false.

Classification (unauth external probe):
  HOST_ERROR / origin 502 / sidecar_unavailable / connection refused → RED CRITICAL
  CF Access 302/challenge without Host Error → ORIGIN_REACHABLE (amber; not RED)
  200 HTML after valid auth → GREEN (identity-matrix human prove; unauth cannot claim)

Owner/War Room: surface material RED only (dedupe on transition; sustained RED
stays visible as open exception without spam events).
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
STATE_DIR = BETA_ROOT / "state" / "ops"
LATEST_PATH = STATE_DIR / "external-route-health-latest.json"
ALERT_PATH = STATE_DIR / "external-route-health-alert.json"
LOG_DIR = BETA_ROOT / "state" / "build-factory" / "logs"
AUTORECOVER_LOG = LOG_DIR / "external-route-health-autorecover.jsonl"

PACK_ID = "EXTERNAL-ROUTE-HEALTH"
SCHEMA_ID = "wolf.external-route-health.v1"
BOUND = "beta-external-route-health-safe"
PROD_PORT = 8787
PROD_PID_HELD = 15975
BETA_PORT = 8788
SIDECAR_PORT = 8790
SIDECAR_HEALTH = f"http://127.0.0.1:{SIDECAR_PORT}/api/health"
LAUNCHAGENT_LABEL = "net.wolfcommand.atrium-finance-sidecar"
LAUNCHAGENT_PLIST = (
    Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHAGENT_LABEL}.plist"
)
WITA = timezone(timedelta(hours=8))

EXTERNAL_ROUTES: tuple[dict[str, str], ...] = (
    {
        "id": "amg_finance",
        "entity": "AMG",
        "path": "/amg/finance",
        "url": "https://beta.wolfcommand.net/amg/finance",
    },
    {
        "id": "bzg_finance",
        "entity": "BZG",
        "path": "/bzg/finance",
        "url": "https://beta.wolfcommand.net/bzg/finance",
    },
    {
        "id": "ggv_finance",
        "entity": "GGV",
        "path": "/ggv/finance",
        "url": "https://beta.wolfcommand.net/ggv/finance",
    },
)

# Classes
CLASS_RED = "RED_CRITICAL"
CLASS_AMBER = "ORIGIN_REACHABLE"
CLASS_GREEN = "GREEN"
CLASS_UNKNOWN = "UNKNOWN"

_HOST_ERROR_RE = re.compile(
    r"(host\s*error|sidecar_unavailable|bad gateway|error\s*502)",
    re.IGNORECASE,
)
_CF_ACCESS_RE = re.compile(
    r"(cloudflareaccess\.com|cf-access|cdn-cgi/access)",
    re.IGNORECASE,
)


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "fake_uptime": False,
        "invented_uptime": False,
        "invented_green_health": False,
        "auth_weakened": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_port_untouched": PROD_PORT,
        "no_exit_report": True,
        "shell_only_not_full_recovery": True,
        "ceiling": "BUILT",
        "proven_claimed": False,
        "ready_claimed": False,
    }


def _run(cmd: list[str], *, timeout: float = 12.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return 1, "", f"{type(exc).__name__}: {exc}"


def _lsof_listen(port: int) -> dict[str, Any]:
    code, out, err = _run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], timeout=8.0
    )
    pids: list[int] = []
    for line in out.splitlines():
        if line.startswith("COMMAND") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        if pid not in pids:
            pids.append(pid)
    listening = bool(pids)
    return {
        "port": port,
        "listening": listening,
        "pids": pids,
        "status": "UP" if listening else "DOWN",
        "probe": "lsof_listen",
        "rc": code,
        "err": (err[:200] if err and not listening else None),
    }


def _http_get(
    url: str,
    *,
    timeout: float = 12.0,
    follow_redirects: bool = False,
    max_body: int = 8192,
) -> dict[str, Any]:
    """GET without auth. Never follow into CF Access login (stay origin-perspective)."""
    started = time.monotonic()
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "wolf-external-route-health/1.0",
            "Accept": "text/html,application/json,*/*",
        },
    )
    try:
        # Manual redirect handling so 302 is visible.
        opener = urllib.request.build_opener(
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(),
        )
        if not follow_redirects:
            class _NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
                    return None

            opener = urllib.request.build_opener(
                _NoRedirect(),
                urllib.request.HTTPHandler(),
                urllib.request.HTTPSHandler(),
            )
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(max_body)
            body = raw.decode("utf-8", errors="replace")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "ok": True,
                "status_code": int(resp.status),
                "body_snippet": body[:1200],
                "headers": {
                    "location": headers.get("location"),
                    "cf-ray": headers.get("cf-ray"),
                    "server": headers.get("server"),
                    "content-type": headers.get("content-type"),
                },
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        raw = b""
        try:
            raw = exc.read(max_body) or b""
        except Exception:  # noqa: BLE001
            raw = b""
        body = raw.decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        # HTTPError for 302 when NoRedirect returns None still surfaces as HTTPError
        return {
            "ok": False,
            "status_code": int(exc.code),
            "body_snippet": body[:1200],
            "headers": {
                "location": headers.get("location"),
                "cf-ray": headers.get("cf-ray"),
                "server": headers.get("server"),
                "content-type": headers.get("content-type"),
            },
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "error": f"HTTPError:{exc.code}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": None,
            "body_snippet": "",
            "headers": {},
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def classify_external(resp: dict[str, Any]) -> dict[str, Any]:
    """Map raw HTTP to RED_CRITICAL / ORIGIN_REACHABLE / GREEN / UNKNOWN."""
    code = resp.get("status_code")
    body = resp.get("body_snippet") or ""
    loc = (resp.get("headers") or {}).get("location") or ""
    err = (resp.get("error") or "").lower()
    blob = f"{body}\n{loc}\n{err}"

    if code is None:
        if "refused" in err or "connection" in err or "timed out" in err or "timeout" in err:
            return {
                "class": CLASS_RED,
                "reason": "connection_refused_or_timeout",
                "color": "RED",
                "critical": True,
            }
        return {
            "class": CLASS_UNKNOWN,
            "reason": "no_status",
            "color": "AMBER",
            "critical": False,
        }

    if code == 502 or _HOST_ERROR_RE.search(blob) or "sidecar_unavailable" in body:
        return {
            "class": CLASS_RED,
            "reason": "host_error_or_sidecar_unavailable_or_502",
            "color": "RED",
            "critical": True,
        }

    if code in (301, 302, 303, 307, 308) and _CF_ACCESS_RE.search(blob):
        return {
            "class": CLASS_AMBER,
            "reason": "cf_access_challenge_origin_reachable",
            "color": "AMBER",
            "critical": False,
            "note": "Unauth probe — ORIGIN_REACHABLE not RED. GREEN needs valid auth HTML.",
        }

    if code == 200 and ("<html" in body.lower() or "<!doctype" in body.lower()):
        # Only GREEN when body is not an error page.
        if _HOST_ERROR_RE.search(body):
            return {
                "class": CLASS_RED,
                "reason": "200_but_host_error_body",
                "color": "RED",
                "critical": True,
            }
        return {
            "class": CLASS_GREEN,
            "reason": "200_html_authenticated_or_public",
            "color": "GREEN",
            "critical": False,
        }

    if code == 403 and "missing_auth" in body:
        # Loopback-style fail-closed through tunnel would be unusual externally;
        # treat as origin reachable (auth held).
        return {
            "class": CLASS_AMBER,
            "reason": "origin_missing_auth_fail_closed",
            "color": "AMBER",
            "critical": False,
        }

    return {
        "class": CLASS_UNKNOWN,
        "reason": f"unclassified_status_{code}",
        "color": "AMBER",
        "critical": False,
    }


def classify_loopback(resp: dict[str, Any]) -> dict[str, Any]:
    """Loopback :8788 finance path — sidecar_unavailable is RED; missing_auth OK."""
    code = resp.get("status_code")
    body = resp.get("body_snippet") or ""
    err = (resp.get("error") or "").lower()
    if code is None:
        if "refused" in err or "connection" in err:
            return {
                "class": CLASS_RED,
                "reason": "beta_connection_refused",
                "color": "RED",
                "critical": True,
            }
        return {
            "class": CLASS_UNKNOWN,
            "reason": "loopback_no_status",
            "color": "AMBER",
            "critical": False,
        }
    if code == 502 or "sidecar_unavailable" in body or _HOST_ERROR_RE.search(body):
        return {
            "class": CLASS_RED,
            "reason": "sidecar_unavailable_502",
            "color": "RED",
            "critical": True,
        }
    if code == 403 and (
        "missing_auth" in body
        or "access denied" in body.lower()
        or "cf-access-jwt" in body.lower()
        or "identity_assurance" in body
    ):
        return {
            "class": CLASS_AMBER,
            "reason": "missing_auth_fail_closed_origin_ok",
            "color": "AMBER",
            "critical": False,
            "note": "Auth held — not Host Error. Good for unauth loopback.",
        }
    if code == 200:
        return {
            "class": CLASS_GREEN,
            "reason": "200_loopback",
            "color": "GREEN",
            "critical": False,
        }
    return {
        "class": CLASS_UNKNOWN,
        "reason": f"loopback_status_{code}",
        "color": "AMBER",
        "critical": False,
    }


def probe_cloudflared() -> dict[str, Any]:
    code, out, err = _run(["pgrep", "-lf", "cloudflared"], timeout=5.0)
    tunnel_lines = [ln for ln in out.splitlines() if "cloudflared" in ln]
    running = bool(tunnel_lines)
    return {
        "id": "cloudflared_tunnel",
        "status": "UP" if running else "DOWN",
        "running": running,
        "process_count": len(tunnel_lines),
        "sample": (tunnel_lines[0][:200] if tunnel_lines else None),
        "probe": "pgrep",
        "rc": code,
        "err": (err[:120] if err and not running else None),
        "critical_if_down": True,
    }


def probe_launchagent() -> dict[str, Any]:
    exists = LAUNCHAGENT_PLIST.is_file()
    uid = os.getuid()
    state = "missing_plist"
    pid = None
    runs = None
    raw_snip = None
    if exists:
        code, out, err = _run(
            ["launchctl", "print", f"gui/{uid}/{LAUNCHAGENT_LABEL}"],
            timeout=8.0,
        )
        raw_snip = (out or err)[:800]
        if "state = running" in (out or "") or "job state = running" in (out or ""):
            state = "running"
        elif code != 0 and ("Could not find" in (err or out) or "not found" in (err or out).lower()):
            state = "not_loaded"
        else:
            # loaded but not clearly running
            if "state = " in (out or ""):
                m = re.search(r"state = (\w+)", out or "")
                state = m.group(1) if m else "loaded_unknown"
            else:
                state = "loaded_unknown"
        m_pid = re.search(r"^\s*pid = (\d+)", out or "", re.M)
        if m_pid:
            pid = int(m_pid.group(1))
        m_runs = re.search(r"^\s*runs = (\d+)", out or "", re.M)
        if m_runs:
            runs = int(m_runs.group(1))
    return {
        "id": "launchagent_atrium_finance_sidecar",
        "label": LAUNCHAGENT_LABEL,
        "plist": str(LAUNCHAGENT_PLIST),
        "plist_exists": exists,
        "state": state,
        "pid": pid,
        "runs": runs,
        "raw_snippet": raw_snip,
        "probe": "launchctl_print",
    }


def probe_sidecar_health() -> dict[str, Any]:
    listen = _lsof_listen(SIDECAR_PORT)
    health = _http_get(SIDECAR_HEALTH, timeout=5.0, follow_redirects=False)
    healthy = listen["listening"] and health.get("status_code") == 200
    return {
        "id": "sidecar_8790",
        "port": SIDECAR_PORT,
        "listen": listen,
        "health_http": {
            "status_code": health.get("status_code"),
            "body_snippet": (health.get("body_snippet") or "")[:200],
            "error": health.get("error"),
            "elapsed_ms": health.get("elapsed_ms"),
        },
        "healthy": healthy,
        "status": "UP" if healthy else "DOWN",
        "critical_if_down": True,
    }


def probe_beta_listen() -> dict[str, Any]:
    listen = _lsof_listen(BETA_PORT)
    return {
        "id": "beta_8788",
        "port": BETA_PORT,
        "listen": listen,
        "status": listen["status"],
        "critical_if_down": True,
        "note": "Local Beta listener. External Host Error can still occur if sidecar down.",
    }


def _safe_autorecover_sidecar(*, dry_run: bool = False) -> dict[str, Any]:
    """If :8790 down and LaunchAgent plist exists → kickstart -k that label only."""
    evidence: dict[str, Any] = {
        "attempted": False,
        "dry_run": dry_run,
        "label": LAUNCHAGENT_LABEL,
        "at_wita": _now_wita(),
        "prod_touched": False,
        "unrelated_killed": False,
    }
    if not LAUNCHAGENT_PLIST.is_file():
        evidence["skipped"] = "plist_missing"
        return evidence
    listen = _lsof_listen(SIDECAR_PORT)
    if listen["listening"]:
        # Also require health 200; if listen but unhealthy still kickstart.
        health = _http_get(SIDECAR_HEALTH, timeout=4.0)
        if health.get("status_code") == 200:
            evidence["skipped"] = "sidecar_already_healthy"
            return evidence
    evidence["attempted"] = True
    evidence["pre_listen"] = listen
    uid = os.getuid()
    cmd = ["launchctl", "kickstart", "-k", f"gui/{uid}/{LAUNCHAGENT_LABEL}"]
    evidence["cmd"] = cmd
    if dry_run:
        evidence["skipped"] = "dry_run"
        return evidence
    code, out, err = _run(cmd, timeout=20.0)
    evidence["rc"] = code
    evidence["stdout"] = (out or "")[:400]
    evidence["stderr"] = (err or "")[:400]
    # Brief settle then re-probe
    time.sleep(1.5)
    post_listen = _lsof_listen(SIDECAR_PORT)
    post_health = _http_get(SIDECAR_HEALTH, timeout=5.0)
    evidence["post_listen"] = post_listen
    evidence["post_health_status"] = post_health.get("status_code")
    evidence["recovered"] = bool(
        post_listen.get("listening") and post_health.get("status_code") == 200
    )
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with AUTORECOVER_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(evidence, default=str) + "\n")
    except OSError:
        evidence["log_write_failed"] = True
    return evidence


def probe_external_routes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route in EXTERNAL_ROUTES:
        resp = _http_get(route["url"], timeout=15.0, follow_redirects=False)
        klass = classify_external(resp)
        rows.append(
            {
                **route,
                "perspective": "external_https",
                "http": {
                    "status_code": resp.get("status_code"),
                    "location": (resp.get("headers") or {}).get("location"),
                    "cf_ray": (resp.get("headers") or {}).get("cf-ray"),
                    "error": resp.get("error"),
                    "elapsed_ms": resp.get("elapsed_ms"),
                    "body_snippet": (resp.get("body_snippet") or "")[:400],
                },
                "classification": klass,
            }
        )
    return rows


def probe_loopback_routes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route in EXTERNAL_ROUTES:
        url = f"http://127.0.0.1:{BETA_PORT}{route['path']}"
        resp = _http_get(url, timeout=8.0, follow_redirects=False)
        klass = classify_loopback(resp)
        rows.append(
            {
                **route,
                "url": url,
                "perspective": "loopback_8788",
                "http": {
                    "status_code": resp.get("status_code"),
                    "error": resp.get("error"),
                    "elapsed_ms": resp.get("elapsed_ms"),
                    "body_snippet": (resp.get("body_snippet") or "")[:400],
                },
                "classification": klass,
            }
        )
    return rows


def _overall_class(
    *,
    external: list[dict[str, Any]],
    loopback: list[dict[str, Any]],
    local: dict[str, Any],
) -> dict[str, Any]:
    criticals: list[str] = []
    for row in external + loopback:
        if (row.get("classification") or {}).get("critical"):
            criticals.append(
                f"{row.get('perspective')}:{row.get('id')}:{(row.get('classification') or {}).get('reason')}"
            )
    for key in ("beta_8788", "sidecar_8790", "cloudflared_tunnel"):
        dep = local.get(key) or {}
        if dep.get("critical_if_down") and dep.get("status") == "DOWN":
            criticals.append(f"local:{key}:DOWN")

    if criticals:
        return {
            "class": CLASS_RED,
            "color": "RED",
            "critical": True,
            "reasons": criticals,
            "summary": "RED CRITICAL — Host Error / sidecar / local dep failure",
        }

    # Prefer amber when all external are ORIGIN_REACHABLE
    ext_classes = {
        (r.get("classification") or {}).get("class") for r in external
    }
    if ext_classes and ext_classes <= {CLASS_AMBER, CLASS_GREEN}:
        if CLASS_GREEN in ext_classes and ext_classes == {CLASS_GREEN}:
            return {
                "class": CLASS_GREEN,
                "color": "GREEN",
                "critical": False,
                "reasons": [],
                "summary": "GREEN — authenticated HTML on all external finance routes",
            }
        return {
            "class": CLASS_AMBER,
            "color": "AMBER",
            "critical": False,
            "reasons": [],
            "summary": (
                "ORIGIN_REACHABLE — CF Access challenge / fail-closed auth. "
                "Not Host Error. Unauth probe cannot claim GREEN."
            ),
        }

    return {
        "class": CLASS_UNKNOWN,
        "color": "AMBER",
        "critical": False,
        "reasons": [],
        "summary": "UNKNOWN — unclassified probe mix",
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _dedupe_alert(overall: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Emit alert event only on transition to RED or first sustained RED stamp."""
    prev = _load_json(ALERT_PATH) or {}
    prev_class = prev.get("overall_class")
    now_class = overall.get("class")
    event: dict[str, Any] = {
        "at_wita": payload.get("as_of_wita"),
        "overall_class": now_class,
        "previous_class": prev_class,
        "transition_to_red": bool(
            now_class == CLASS_RED and prev_class != CLASS_RED
        ),
        "sustained_red": bool(now_class == CLASS_RED and prev_class == CLASS_RED),
        "cleared_red": bool(prev_class == CLASS_RED and now_class != CLASS_RED),
        "noise_suppressed": False,
        "surface_exception": now_class == CLASS_RED,
    }
    if now_class == CLASS_RED and prev_class == CLASS_RED:
        # Keep open exception visible; do not spam a new alert id every tick.
        event["noise_suppressed"] = True
        event["alert_id"] = prev.get("alert_id") or f"erh-red-{payload.get('as_of_wita')}"
    elif now_class == CLASS_RED:
        event["alert_id"] = f"erh-red-{payload.get('as_of_wita')}"
    elif event["cleared_red"]:
        event["alert_id"] = f"erh-clear-{payload.get('as_of_wita')}"
    else:
        event["alert_id"] = prev.get("alert_id")
    event["reasons"] = overall.get("reasons") or []
    _write_json(ALERT_PATH, event)
    return event


def run_probe(
    *,
    autorecover: bool = True,
    dry_run_recover: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    """Full probe: local deps + loopback + external HTTPS + optional kickstart."""
    as_of = _now_wita()
    recover: dict[str, Any] | None = None

    beta = probe_beta_listen()
    sidecar = probe_sidecar_health()
    cloudflared = probe_cloudflared()
    launchagent = probe_launchagent()

    if autorecover and sidecar.get("status") == "DOWN" and launchagent.get("plist_exists"):
        recover = _safe_autorecover_sidecar(dry_run=dry_run_recover)
        # Re-probe local after recover attempt
        sidecar = probe_sidecar_health()
        launchagent = probe_launchagent()

    external = probe_external_routes()
    loopback = probe_loopback_routes()
    local = {
        "beta_8788": beta,
        "sidecar_8790": sidecar,
        "cloudflared_tunnel": cloudflared,
        "launchagent": launchagent,
    }
    overall = _overall_class(external=external, loopback=loopback, local=local)

    # Honesty: prior gap — local reliability lsof could show beta UP while
    # external Host Error (sidecar down). That is not painting sidecar UP;
    # it is external-route blindness. This probe closes that gap.
    health_model_gap = {
        "reliability1_probes": "local_lsof_8788_8790_8787_ro",
        "reliability1_external_https": False,
        "lied_green_sidecar_up_while_down": False,
        "blind_to_external_host_error": True,
        "note": (
            "RELIABILITY-1 was honest on sidecar DOWN via lsof, but did not probe "
            "external HTTPS. Beta :8788 UP alone could look fine while CF Host Error "
            "502 hit /amg|/bzg|/ggv/finance. Owner exceptions had no external-route RED."
        ),
    }

    payload: dict[str, Any] = {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": as_of,
        "overall": overall,
        "external_routes": external,
        "loopback_routes": loopback,
        "local_deps": local,
        "autorecover": recover,
        "health_model_gap": health_model_gap,
        "identity_matrix_gaps": [
            "Unauth probe cannot prove GREEN (200 HTML after valid CF Access + Beta auth).",
            "Human prove still required for identity-matrix seat walk on finance desks.",
            "staff_ready=false · human_commissioned=false.",
        ],
        "prod_touched": False,
        "auth_weakened": False,
        **honesty_flags(),
    }

    alert = _dedupe_alert(overall, payload) if persist else {
        "surface_exception": overall.get("class") == CLASS_RED,
        "noise_suppressed": False,
        "transition_to_red": overall.get("class") == CLASS_RED,
    }
    payload["alert"] = alert

    if persist:
        _write_json(LATEST_PATH, payload)

    return payload


def load_latest() -> dict[str, Any] | None:
    return _load_json(LATEST_PATH)


def owner_exception_items(
    *, latest: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Material Owner/War Room exceptions — only while overall RED CRITICAL."""
    pack = latest if latest is not None else load_latest()
    if not pack:
        return []
    overall = pack.get("overall") or {}
    alert = pack.get("alert") or {}
    if overall.get("class") != CLASS_RED:
        return []
    if not alert.get("surface_exception", True):
        return []
    reasons = overall.get("reasons") or []
    detail = (
        f"{overall.get('summary') or 'External finance route Host Error / sidecar down'}. "
        f"Reasons: {', '.join(reasons[:8]) or 'n/a'}. "
        f"as_of={pack.get('as_of_wita')}. "
        "Autorecover: launchctl kickstart -k atrium-finance-sidecar when plist exists."
    )
    return [
        {
            "kind": "external_route",
            "title": "CRITICAL — Beta finance external route Host Error / sidecar",
            "detail": detail[:480],
            "href": "/ops/reliability",
            "owner_role": "Owner / Ops",
            "money_risk": True,
            "blocked": True,
            "plain": detail[:480],
            "alert_id": alert.get("alert_id"),
            "deduped": bool(alert.get("noise_suppressed")),
            "source": PACK_ID,
        }
    ]


def reliability_surface(
    *, latest: dict[str, Any] | None = None, live: bool = False
) -> dict[str, Any]:
    """Compact surface for RELIABILITY-1 board / operator desk."""
    pack = run_probe(autorecover=False, persist=True) if live else (
        latest if latest is not None else load_latest()
    )
    if not pack:
        return {
            "id": "external_route_health",
            "status": "UNKNOWN",
            "class": CLASS_UNKNOWN,
            "last_probe_at": None,
            "critical": False,
            "notes": "No external-route-health tick yet. Run scripts/ops/external_route_health_tick.py",
            "uptime_pct": None,
            "invented_uptime": False,
            "painted_green": False,
        }
    overall = pack.get("overall") or {}
    return {
        "id": "external_route_health",
        "status": overall.get("color") or "UNKNOWN",
        "class": overall.get("class"),
        "summary": overall.get("summary"),
        "critical": bool(overall.get("critical")),
        "last_probe_at": pack.get("as_of_wita"),
        "external_route_count": len(pack.get("external_routes") or []),
        "red_reasons": overall.get("reasons") or [],
        "sidecar_status": ((pack.get("local_deps") or {}).get("sidecar_8790") or {}).get(
            "status"
        ),
        "cloudflared_status": (
            (pack.get("local_deps") or {}).get("cloudflared_tunnel") or {}
        ).get("status"),
        "alert": pack.get("alert"),
        "uptime_pct": None,
        "invented_uptime": False,
        "painted_green": False,
        "fake_uptime": False,
        "staff_ready": False,
        "human_commissioned": False,
        "notes": overall.get("summary"),
        "probe_command": (
            "python3 scripts/ops/external_route_health_tick.py --json"
        ),
    }


def public_payload(*, live: bool = False) -> dict[str, Any]:
    if live:
        return run_probe(autorecover=True, persist=True)
    latest = load_latest()
    if latest:
        return latest
    return run_probe(autorecover=True, persist=True)


if __name__ == "__main__":
    out = run_probe(autorecover=True, persist=True)
    print(json.dumps(out, indent=2, default=str))
