#!/usr/bin/env python3
"""Deployed-route tests.

Ephemeral/unit coverage for Progress stays in test_progress_dashboard.py.
This module adds an always-on check when real Beta :8788 serve_beta is
detectable (or when WOLF_PROVE_DEPLOYED=1), so the factory cannot miss a
stale live process again.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVE = ROOT / "scripts" / "prove_deployed_ui_routes.py"


def _port_up(port: int = 8788) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def _looks_like_serve_beta(port: int = 8788) -> bool:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).lower()
    except Exception:
        return False
    return "serve_beta" in out or ("python" in out and str(port) in out)


def should_run_deployed() -> bool:
    if os.environ.get("WOLF_PROVE_DEPLOYED", "").strip() in ("1", "true", "yes"):
        return True
    return _port_up(8788) and _looks_like_serve_beta(8788)


class TestDeployedUiRoutes(unittest.TestCase):
    def test_prove_deployed_ui_routes_when_beta_up(self) -> None:
        if not should_run_deployed():
            self.skipTest("Beta :8788 serve_beta not detectable; set WOLF_PROVE_DEPLOYED=1 to force")
        self.assertTrue(PROVE.is_file(), f"missing {PROVE}")
        proc = subprocess.run(
            [sys.executable, str(PROVE)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        self.assertEqual(proc.returncode, 0, f"prove failed rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
