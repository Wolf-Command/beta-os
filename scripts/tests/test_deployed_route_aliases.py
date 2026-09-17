#!/usr/bin/env python3
"""Ephemeral + optional live proves for Progress-class clean URL aliases.

Ephemeral ThreadingHTTPServer covers rewrite logic in serve_beta.Handler.
Live :8788 is optional here (SKIP if down) — prove_deployed_routes.py owns
the hard live gate.
"""
from __future__ import annotations

import inspect
import os
import socket
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PROVE = SCRIPTS / "prove_deployed_routes.py"

PAGES = (
    ("progress", "Wolf · Progress"),
    ("habitat-operator", "Habitat Operator"),
    ("uma-blu-close", "Uma Blu · Daily Close"),
)


def _port_up(port: int = 8788) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def _fetch(url: str) -> tuple[int, str]:
    req = Request(url, method="GET", headers={"Cache-Control": "no-cache"})
    try:
        with urlopen(req, timeout=8) as resp:
            return int(resp.status), resp.read().decode("utf-8", "replace")
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace") if e.fp else ""
        return int(e.code), body


class TestDeployedRouteAliases(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import serve_beta as sb

        Handler = None
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
        if Handler is None:
            raise unittest.SkipTest("BetaHandler not found in serve_beta")
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()

    def test_clean_paths_return_200_html_with_markers(self) -> None:
        for slug, marker in PAGES:
            code, body = _fetch(f"{self.base}/{slug}")
            self.assertEqual(code, 200, f"/{slug} status={code}")
            self.assertIn(marker, body, f"/{slug} missing marker {marker!r}")
            self.assertIn("<html", body.lower())

    def test_dashboards_rewrite_returns_200(self) -> None:
        for slug, marker in PAGES:
            path = f"/dashboards/{slug}.html"
            code, body = _fetch(f"{self.base}{path}")
            self.assertEqual(code, 200, f"{path} status={code}")
            self.assertIn(marker, body, f"{path} missing marker {marker!r}")

    def test_html_direct_still_200(self) -> None:
        for slug, marker in PAGES:
            code, body = _fetch(f"{self.base}/{slug}.html")
            self.assertEqual(code, 200, f"/{slug}.html status={code}")
            self.assertIn(marker, body)

    def test_optional_live_8788_matrix(self) -> None:
        force = os.environ.get("WOLF_PROVE_DEPLOYED", "").strip().lower() in ("1", "true", "yes")
        if not force and not _port_up(8788):
            print("SKIP live :8788 — Beta down (prove_deployed_routes.py owns hard gate)")
            self.skipTest("Beta :8788 down")
        if not PROVE.is_file():
            self.fail(f"missing {PROVE}")
        try:
            proc = subprocess.run(
                [sys.executable, str(PROVE)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except URLError as exc:
            if force:
                raise
            self.skipTest(f"live prove unreachable: {exc}")
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        if proc.returncode != 0 and not force and not _port_up(8788):
            self.skipTest("live prove failed while Beta flapped")
        self.assertEqual(
            proc.returncode,
            0,
            f"live prove failed rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
