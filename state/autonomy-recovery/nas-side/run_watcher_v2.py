#!/usr/bin/env python3
"""NAS entrypoint: real SSH ForceCommand transport + NasSupervisor tick.

Safe defaults:
  - --once runs a single tick
  - --dry-run never calls recover-watchdog (logs DRY_RUN instead)
  - --probe-host/--probe-port override Studio target (for miss-detection drill)

Never prints key material. Never touches Prod.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from watcher import NasSupervisor, Transport, now_iso  # type: ignore

DEFAULT_ROOT = Path(
    os.environ.get(
        "WOLF_RECOVERY_ROOT",
        str(Path.home() / ".ssh" / "wolf-recovery"),
    )
)


class SshForcedTransport(Transport):
    def __init__(
        self,
        *,
        key: Path,
        known_hosts: Path,
        host: str,
        port: int,
        user: str = "wolfrecover",
        dry_run: bool = False,
        connect_timeout: int = 8,
        pipe_url: str | None = None,
    ):
        self.key = key
        self.known_hosts = known_hosts
        self.host = host
        self.port = port
        self.user = user
        self.dry_run = dry_run
        self.connect_timeout = connect_timeout
        self.pipe_url = pipe_url or f"http://{host}:2223/pipe-health"

    def _ssh(self, remote_cmd: str) -> tuple[int, str]:
        if remote_cmd not in ("status", "recover-watchdog"):
            return 97, "DENIED_CMD"
        cmd = [
            "/usr/bin/ssh",
            "-i",
            str(self.key),
            "-p",
            str(self.port),
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "IdentityAgent=none",
            "-o",
            "PreferredAuthentications=publickey",
            "-o",
            "NumberOfPasswordPrompts=0",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={self.known_hosts}",
            "-o",
            f"ConnectTimeout={self.connect_timeout}",
            "-o",
            "ProxyCommand=/usr/local/bin/tailscale nc %h %p",
            "-T",
            f"{self.user}@{self.host}",
            remote_cmd,
        ]
        try:
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.connect_timeout + 15,
                check=False,
            )
            out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
            return p.returncode, out
        except Exception as e:
            return 98, f"SSH_EXC {type(e).__name__}"

    @staticmethod
    def _parse_status(text: str) -> dict[str, Any]:
        d: dict[str, Any] = {"ok": False, "raw_preview": text[:240]}
        m = re.search(r"GROK_APP\s+(\S+)", text)
        if not m:
            d["error"] = "NO_GROK_APP_TOKEN"
            return d
        d["ok"] = True
        d["GROK_APP"] = m.group(1)
        wm = re.search(
            r"WATCHDOG\s+supervisor=(\S+)\s+heartbeat=(\S+)\s+keepalive=(\S+)",
            text,
        )
        if wm:
            d["supervisor"] = wm.group(1)
            d["heartbeat"] = wm.group(2)
            d["keepalive"] = wm.group(3)
        hm = re.search(r"STATUS host=(\S+)", text)
        if hm:
            d["host"] = hm.group(1)
        return d

    def _pipe_http(self) -> dict[str, Any]:
        """Probe Studio pipe-health over Tailscale nc (Synology curl times out)."""
        host = self.host
        port = 2223
        try:
            if self.pipe_url and "://" in self.pipe_url:
                rest = self.pipe_url.split("://", 1)[1]
                hp = rest.split("/", 1)[0]
                if ":" in hp:
                    host, ps = hp.rsplit(":", 1)
                    port = int(ps)
                else:
                    host = hp
        except Exception:
            pass
        # Proven on Synology: (printf + sleep) | tailscale nc
        shell = (
            "( printf 'GET /pipe-health HTTP/1.0\\r\\nHost: pipe\\r\\nConnection: close\\r\\n\\r\\n'; "
            "sleep 1 ) | /usr/local/bin/tailscale nc %s %s"
        ) % (host, port)
        try:
            out = subprocess.check_output(
                shell, shell=True, stderr=subprocess.DEVNULL, timeout=self.connect_timeout + 3
            )
            text = out.decode("utf-8", errors="replace")
            if "\r\n\r\n" in text:
                body = text.split("\r\n\r\n", 1)[1]
            elif "\n\n" in text:
                body = text.split("\n\n", 1)[1]
            else:
                body = text
            body = body.strip()
            if "{" in body:
                body = body[body.index("{") :]
            if not body:
                return {
                    "pipe_http_ok": False,
                    "PIPE": "PIPE_DEAD",
                    "pipe_ok": False,
                    "pipe_reason": "HTTP_EMPTY",
                }
            data = json.loads(body)
            return {
                "pipe_http_ok": True,
                "PIPE": data.get("pipe") or ("PIPE_OK" if data.get("pipe_ok") else "PIPE_DEAD"),
                "pipe_ok": bool(data.get("pipe_ok")),
                "pipe_reason": data.get("reason"),
                "pipe_app_pid": data.get("app_pid"),
                "pipe_state": data.get("state"),
            }
        except Exception as e:
            return {
                "pipe_http_ok": False,
                "PIPE": "PIPE_DEAD",
                "pipe_ok": False,
                "pipe_reason": f"HTTP_{type(e).__name__}",
            }

    def status(self) -> dict[str, Any]:
        rc, out = self._ssh("status")
        if rc != 0:
            base: dict[str, Any] = {
                "ok": False,
                "error": f"STATUS_RC_{rc}",
                "raw_preview": out[:240],
            }
        else:
            base = self._parse_status(out)
        base.update(self._pipe_http())
        return base

    def recover_watchdog(self) -> dict[str, Any]:
        if self.dry_run:
            return {"ok": True, "result": "DRY_RUN_RECOVER_WATCHDOG", "dry_run": True}
        rc, out = self._ssh("recover-watchdog")
        ok = rc == 0 and "RECOVER_WATCHDOG_DONE" in out
        return {
            "ok": ok,
            "result": "RECOVER_WATCHDOG_DONE" if ok else f"RECOVER_RC_{rc}",
            "raw_preview": out[:240],
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", default=True)
    ap.add_argument("--dry-run", action="store_true", help="Do not invoke recover-watchdog")
    ap.add_argument("--probe-host", default="100.113.26.51")
    ap.add_argument("--probe-port", type=int, default=2222)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--miss-threshold", type=int, default=3)
    ap.add_argument("--label", default="live")
    ap.add_argument("--pipe-url", default=None)
    args = ap.parse_args()

    root = Path(args.root)
    key = root / "id_ed25519"
    kh = root / "known_hosts"
    if not key.exists():
        print(json.dumps({"error": "KEY_MISSING", "path": str(key.name)}))
        return 2

    transport = SshForcedTransport(
        key=key,
        known_hosts=kh,
        host=args.probe_host,
        port=args.probe_port,
        dry_run=args.dry_run,
        pipe_url=args.pipe_url,
    )
    state_path = root / f"watcher_v2.{args.label}.state.json"
    audit_path = root / f"watcher_v2.{args.label}.audit.jsonl"
    # Reset latch for healthy reprime is caller's job
    sup = NasSupervisor(
        transport,
        state_path,
        audit_path,
        miss_threshold=args.miss_threshold,
    )
    st = sup.tick()
    summary = {
        "ts_wita": now_iso(),
        "label": args.label,
        "probe_host": args.probe_host,
        "probe_port": args.probe_port,
        "dry_run": args.dry_run,
        "last_event": st.last_event,
        "consecutive_misses": st.consecutive_misses,
        "armed": st.armed,
        "recovery_attempts": st.recovery_attempts,
        "state_file": state_path.name,
        "audit_file": audit_path.name,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
