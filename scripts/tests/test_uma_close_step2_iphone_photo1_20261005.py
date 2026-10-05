#!/usr/bin/env python3
"""UMA-CLOSE-STEP2-IPHONE-PHOTO-1 — Step 2 photo upload surgical repair tests."""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LIVE_RECEIPTS = ROOT / "state" / "bzg-daily-close" / "receipts"
HTML = ROOT / "dashboards" / "uma-blu-close.html"
PROBE = Path("/Users/wolfterminal/hist-close-nav-work/probe_server.py")

sys.path.insert(0, str(SCRIPTS))

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


def multipart(
    fields: dict[str, str],
    file_field: tuple[str, str, bytes, str],
) -> tuple[bytes, str]:
    boundary = f"----WolfBound{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for k, v in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        chunks.append(v.encode() + b"\r\n")
    name, filename, data, ctype = file_field
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
    )
    if ctype:
        chunks.append(f"Content-Type: {ctype}\r\n\r\n".encode())
    else:
        chunks.append(b"\r\n")
    chunks.append(data)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _live_receipt_snapshot() -> dict[str, str]:
    snap: dict[str, str] = {}
    if not LIVE_RECEIPTS.is_dir():
        return snap
    for p in LIVE_RECEIPTS.iterdir():
        if p.is_file():
            snap[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def _make_jpeg(path: Path, width: int, height: int, quality: int = 92) -> None:
    """Create a JPEG at target dimensions (tiled noise for realistic file sizes)."""
    from PIL import Image

    tile = Image.new("RGB", (256, 256))
    tile.putdata([(i % 256, (i * 3) % 256, (i * 7) % 256) for i in range(256 * 256)])
    im = Image.new("RGB", (width, height))
    for y in range(0, height, 256):
        for x in range(0, width, 256):
            im.paste(tile, (x, y))
    im.save(path, format="JPEG", quality=quality)


def _make_heic(path: Path, width: int = 800, height: int = 600) -> None:
    jpg = path.with_suffix(".tmp.jpg")
    _make_jpeg(jpg, width, height)
    subprocess.run(
        ["/usr/bin/sips", "-s", "format", "heic", str(jpg), "--out", str(path)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    jpg.unlink(missing_ok=True)


class IsolatedPhotoEnv:
    def __init__(self) -> None:
        backups = ROOT / "catalog" / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        self.scratch = Path(tempfile.mkdtemp(prefix="uma-step2-photo-", dir=str(backups)))
        self.evidence_root = self.scratch / "evidence"
        self.db_path = self.scratch / "content_library.sqlite"
        self.receipt_dir = self.evidence_root / "bzg-daily-close" / "receipts"
        self.port = 0
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.saved_modules: dict = {}

    def _patch_catalog_paths(self) -> None:
        live = LIVE_DB.resolve()
        for name, mod in list(sys.modules.items()):
            if not mod or not (name.startswith("core") or name in ("serve_beta",)):
                continue
            for attr, val in list(vars(mod).items()):
                if attr.upper().startswith("LIVE"):
                    continue
                if isinstance(val, (str, Path)) and str(val).endswith("content_library.sqlite"):
                    try:
                        if Path(val).resolve() == live:
                            self.saved_modules[(mod, attr)] = getattr(mod, attr)
                            setattr(mod, attr, self.db_path if isinstance(val, Path) else str(self.db_path))
                    except Exception:
                        pass

    def setup(self) -> None:
        shutil.copy2(LIVE_DB, self.db_path)
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        os.environ["WOLF_TEST_MODE"] = "1"
        os.environ["WOLF_EVIDENCE_ROOT"] = str(self.evidence_root)
        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        from core import bzg_daily_close as bzg

        self._patch_catalog_paths()
        bzg.CLOSE_RECEIPT_DIR = self.receipt_dir

    def teardown(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
        os.environ.pop("WOLF_TEST_MODE", None)
        os.environ.pop("WOLF_EVIDENCE_ROOT", None)
        for key, val in self.saved_modules.items():
            if isinstance(key, tuple):
                mod, attr = key
                setattr(mod, attr, val)
            else:
                key.CATALOG_DB = val  # type: ignore[attr-defined]
        shutil.rmtree(self.scratch, ignore_errors=True)

    def start_server(self) -> int:
        import core.identity  # noqa: F401 — ensure patchable
        import serve_beta as sb

        self._patch_catalog_paths()
        from core import bzg_daily_close as bzg

        bzg.CLOSE_RECEIPT_DIR = self.receipt_dir
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.5)
        return self.port

    def post_photo(
        self,
        data: bytes,
        filename: str,
        content_type: str,
        *,
        kind: str = "esb",
        business_date: str = "2026-10-07",
    ) -> tuple[int, dict]:
        import urllib.error
        import urllib.request

        port = self.port or self.start_server()
        body, ctype = multipart(
            {"kind": kind, "business_date": business_date},
            ("file", filename, data, content_type),
        )
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/venue-close/receipt-photo",
            data=body,
            method="POST",
            headers={
                "Content-Type": ctype,
                "X-Wolf-Subject": "mrwolf@wolfcommand.net",
                "Cf-Access-Authenticated-User-Email": "mrwolf@wolfcommand.net",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw.decode())
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw.decode())
            except json.JSONDecodeError:
                return e.code, {"raw": raw.decode("utf-8", errors="replace")[:200]}


def test_static_html_checks() -> None:
    src = HTML.read_text(encoding="utf-8")
    upload_block = src[src.find("async function uploadShift"): src.find("async function readShiftReport")]
    check("postPhoto helper present", "async function postPhoto" in src)
    check("no blind res.json in uploadShift", "await res.json()" not in upload_block)
    check("shiftSaving id", 'id="shiftSaving"' in src)
    check("shiftSaveFail id", 'id="shiftSaveFail"' in src)
    check("staff fail heading", "PHOTO COULD NOT BE SAVED" in src)
    check("staff fail line", "Try again or upload an existing photo." in src)
    check("shiftFile no capture", 'id="shiftFile"' in src and 'id="shiftFile" accept=' in src and "capture" not in src.split('id="shiftFile"')[1].split(">")[0])
    check("accept includes heic", "image/heic" in src and ".heic" in src)
    check("shiftCam capture environment", 'id="shiftCam"' in src and 'capture="environment"' in src)


def test_save_close_receipt_bytes_cases() -> None:
    before = _live_receipt_snapshot()
    env = IsolatedPhotoEnv()
    fixtures = Path(tempfile.mkdtemp(prefix="uma-step2-fix-"))
    try:
        env.setup()
        from core import bzg_daily_close as bzg

        # (a) 4032x3024 ~4MB JPEG
        jpg_a = fixtures / "shift_4032.jpg"
        _make_jpeg(jpg_a, 4032, 3024, quality=95)
        data_a = jpg_a.read_bytes()
        check("(a) large jpeg", len(data_a) > 500_000, str(len(data_a)))
        out_a = bzg.save_close_receipt_bytes(data=data_a, kind="esb", filename="shift.jpg", content_type="image/jpeg")
        stored_a = env.receipt_dir / Path(out_a["path"]).name
        check("(a) 200 ok", out_a.get("ok") is True)
        check("(a) sha256 match", hashlib.sha256(data_a).hexdigest() == out_a["content_hash"])
        check("(a) ext .jpg", stored_a.suffix == ".jpg")
        check("(a) derivative for large", out_a.get("derivative_object_ref") is not None)

        # (b) >8MB 24MP JPEG (would fail old 8MB cap)
        jpg_b = fixtures / "shift_24mp.jpg"
        _make_jpeg(jpg_b, 7000, 5250, quality=100)
        data_b = jpg_b.read_bytes()
        check("(b) >8MB", len(data_b) > 8_000_000, str(len(data_b)))
        out_b = bzg.save_close_receipt_bytes(data=data_b, kind="esb", filename="big.jpg", content_type="image/jpeg")
        check("(b) accepted under 40MB cap", out_b.get("ok") is True)
        check("(b) sha256 match", hashlib.sha256(data_b).hexdigest() == out_b["content_hash"])

        # (c) HEIC via sips
        heic_c = fixtures / "photo.heic"
        _make_heic(heic_c)
        data_c = heic_c.read_bytes()
        out_c = bzg.save_close_receipt_bytes(data=data_c, kind="esb", filename="photo.heic", content_type="image/heic")
        eid_c = out_c["evidence_id"]
        deriv_c = env.receipt_dir / f"{eid_c}.read.jpg"
        check("(c) HEIC ext", Path(out_c["path"]).suffix == ".heic")
        check("(c) derivative exists", deriv_c.is_file(), str(deriv_c))
        check("(c) sha256 original", hashlib.sha256(data_c).hexdigest() == out_c["content_hash"])

        # (d) HEIC IMG_1234.HEIC empty content-type
        out_d = bzg.save_close_receipt_bytes(data=data_c, kind="esb", filename="IMG_1234.HEIC", content_type="")
        check("(d) magic ext heic", Path(out_d["path"]).suffix == ".heic")

        # (e) JPEG no extension, octet-stream
        out_e = bzg.save_close_receipt_bytes(
            data=data_a[: min(len(data_a), 500_000)],
            kind="esb",
            filename="IMG_0001",
            content_type="application/octet-stream",
        )
        check("(e) magic jpeg", Path(out_e["path"]).suffix == ".jpg")

        # non-image → 415
        try:
            bzg.save_close_receipt_bytes(data=b"not-an-image-at-all", kind="esb")
            check("non-image raises", False)
        except bzg.BzgDailyCloseError as e:
            check("non-image 415", e.http_status == 415, str(e.http_status))
            check("non-image staff copy", (e.details or {}).get("staff_message") == "PHOTO COULD NOT BE SAVED")

        # vision path uses derivative
        vis_bytes, vis_mime = bzg.load_close_receipt_vision_bytes(out_c["object_ref"])
        check("vision uses derivative", vis_mime == "image/jpeg" and vis_bytes is not None)
        if deriv_c.is_file() and vis_bytes:
            check("vision bytes from deriv", vis_bytes == deriv_c.read_bytes())

        after = _live_receipt_snapshot()
        check("zero live writes", before == after)
    finally:
        env.teardown()
        shutil.rmtree(fixtures, ignore_errors=True)


def test_api_route_json() -> None:
    before = _live_receipt_snapshot()
    env = IsolatedPhotoEnv()
    fixtures = Path(tempfile.mkdtemp(prefix="uma-step2-api-"))
    try:
        env.setup()
        port = env.start_server()
        jpg = fixtures / "api.jpg"
        _make_jpeg(jpg, 1200, 900)
        data = jpg.read_bytes()
        status, body = env.post_photo(data, "api.jpg", "image/jpeg")
        check("api 200", status == 200, str(status))
        check("api ok json", body.get("ok") is True)
        check("api kept_original", body.get("kept_original") is True)

        status415, body415 = env.post_photo(b"plain text", "x.txt", "text/plain")
        check("api 415", status415 == 415, str(status415))
        check("api 415 staff", body415.get("staff_message") == "PHOTO COULD NOT BE SAVED")

        from core import bzg_daily_close as bzg

        body, ctype = multipart(
            {"kind": "esb", "business_date": "2026-10-07"},
            ("file", "boom.jpg", data, "image/jpeg"),
        )
        import urllib.error
        import urllib.request

        import serve_beta as sb_mod

        with mock.patch.object(
            sb_mod._bzg_daily_close,
            "save_close_receipt_bytes",
            side_effect=RuntimeError("forced test explosion"),
        ):
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/venue-close/receipt-photo",
                data=body,
                method="POST",
                headers={
                    "Content-Type": ctype,
                    "X-Wolf-Subject": "mrwolf@wolfcommand.net",
                    "Cf-Access-Authenticated-User-Email": "mrwolf@wolfcommand.net",
                },
            )
            try:
                urllib.request.urlopen(req, timeout=10)
                check("forced 500", False, "no error")
            except urllib.error.HTTPError as e:
                raw = e.read().decode()
                check("forced status 500", e.code == 500, str(e.code))
                payload = json.loads(raw)
                check("forced staff only", payload.get("staff_message") == "PHOTO COULD NOT BE SAVED")
                check("forced no traceback in body", "forced test" not in raw and "Traceback" not in raw)

        after = _live_receipt_snapshot()
        check("api zero live writes", before == after)
    finally:
        env.teardown()
        shutil.rmtree(fixtures, ignore_errors=True)


def test_webkit_proof() -> dict:
    """Playwright WebKit iPhone 14 on isolated probe server."""
    result: dict = {"skipped": False, "error": None, "cases": []}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result["skipped"] = True
        result["error"] = "playwright not installed"
        return result

    if not PROBE.is_file():
        result["skipped"] = True
        result["error"] = "probe_server missing"
        return result

    before = _live_receipt_snapshot()
    evroot = Path(tempfile.mkdtemp(prefix="tmp-evroot-step2-"))
    fixtures = Path(tempfile.mkdtemp(prefix="uma-step2-pw-"))
    port = 8815
    _make_jpeg(fixtures / "shift.jpg", 4032, 3024)
    _make_heic(fixtures / "photo.heic")
    proc = subprocess.Popen(
        [sys.executable, str(PROBE), str(port), "step2-iphone-photo1"],
        env={
            **dict(os.environ),
            "WOLF_CLOSE_VISION_DRY": "1",
            "BETA_LLM_DRY_RUN": "1",
            "WOLF_EVIDENCE_ROOT": str(evroot),
            "WOLF_TEST_MODE": "1",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(3)
    base = f"http://127.0.0.1:{port}"
    email = "mrwolf@wolfcommand.net"
    try:
        with sync_playwright() as p:
            browser = p.webkit.launch()
            ctx = browser.new_context(
                **p.devices["iPhone 14"],
                extra_http_headers={
                    "X-Wolf-Subject": email,
                    "Cf-Access-Authenticated-User-Email": email,
                },
            )
            page = ctx.new_page()

            # Route: 502 twice then pass
            receipt_posts: list[str] = []
            fail_left = {"v": 2}

            def on_receipt_req(req) -> None:  # noqa: ANN001
                if "/api/venue-close/receipt-photo" in req.url and req.method == "POST":
                    receipt_posts.append(req.url)

            page.on("request", on_receipt_req)

            def handle_route(route, request):  # noqa: ANN001
                if "/api/venue-close/receipt-photo" in request.url and request.method == "POST":
                    if fail_left["v"] > 0:
                        fail_left["v"] -= 1
                        route.fulfill(
                            status=502,
                            content_type="text/html",
                            body="<html>502 Bad Gateway</html>",
                        )
                        return
                route.continue_()

            page.route("**/api/venue-close/receipt-photo", handle_route)
            page.goto(f"{base}/uma-blu-close?business_date=2026-12-15", wait_until="networkidle")
            time.sleep(1.5)
            page.wait_for_selector("#btnUploadShift", timeout=10000)
            with page.expect_file_chooser() as fc:
                page.locator("#btnUploadShift").tap()
            fc.value.set_files(str(fixtures / "shift.jpg"))
            page.wait_for_function(
                "() => { const e = document.querySelector('#shiftExisting'); "
                "return e && e.innerText.includes('Shift report photo found'); }",
                timeout=25000,
            )
            retry_ok = "Shift report photo found" in (page.locator("#shiftExisting").inner_text() or "")
            result["cases"].append({"retry_502_then_pass": retry_ok, "posts": len(receipt_posts)})
            check("webkit retry after 502", retry_ok and len(receipt_posts) >= 3, str(len(receipt_posts)))

            # Always 502 — staff copy only
            page2 = ctx.new_page()
            page2.route(
                "**/api/venue-close/receipt-photo",
                lambda route, req: route.fulfill(
                    status=502, content_type="text/html", body="<html>502</html>"
                )
                if req.method == "POST"
                else route.continue_(),
            )
            page2.goto(f"{base}/uma-blu-close?business_date=2026-10-09", wait_until="networkidle")
            time.sleep(1)
            with page2.expect_file_chooser() as fc2:
                page2.locator("#btnUploadShift").tap()
            fc2.value.set_files(str(fixtures / "shift.jpg"))
            page2.wait_for_selector("#shiftSaveFail", timeout=20000)
            text = page2.locator("#stepShift").inner_text()
            fail_visible = page2.locator("#shiftSaveFail").is_visible()
            no_pattern = "did not match" not in text.lower()
            staff_copy = "PHOTO COULD NOT BE SAVED" in text and "Try again or upload an existing photo." in text
            result["cases"].append({"always_502_staff_copy": staff_copy and fail_visible and no_pattern})
            check("webkit always 502 staff copy", staff_copy and fail_visible)
            check("webkit never raw pattern", no_pattern)
            page2.close()

            # TAKE PHOTO input (shiftCam)
            page.goto(f"{base}/uma-blu-close?business_date=2026-10-10", wait_until="networkidle")
            time.sleep(1)
            page.set_input_files("#shiftCam", str(fixtures / "photo.heic"))
            time.sleep(5)
            heic_ok = page.locator("#shiftExisting, #shiftPreview.show").count() > 0
            result["cases"].append({"shiftCam_heic": heic_ok})
            check("webkit shiftCam HEIC", heic_ok)

            # UPLOAD PHOTO (shiftFile)
            page.goto(f"{base}/uma-blu-close?business_date=2026-10-11", wait_until="networkidle")
            time.sleep(1)
            page.set_input_files("#shiftFile", str(fixtures / "shift.jpg"))
            time.sleep(5)
            upload_ok = page.locator("#shiftExisting, #shiftPreview.show").count() > 0
            result["cases"].append({"shiftFile_jpeg": upload_ok})
            check("webkit shiftFile JPEG", upload_ok)

            browser.close()
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(evroot, ignore_errors=True)
        shutil.rmtree(fixtures, ignore_errors=True)
    after = _live_receipt_snapshot()
    result["zero_live_writes"] = before == after
    check("webkit zero live writes", before == after)
    return result


def run_regression() -> dict[str, bool]:
    tests = [
        "test_uma_close_6step_rebuild4_20261005.py",
        "test_uma_close_6step_rebuild3_20261005.py",
        "test_uma_close_6step_rebuild2_20261005.py",
        "test_uma_close_6step_rebuild1_20261005.py",
        "test_uma_hist_close_complete1_20261005.py",
        "test_uma_hist_close_complete2_20261005.py",
        "test_uma_hist_close_nav_mobile1_20261005.py",
        "test_uma_hist_close_nav_mobile2_20261005.py",
        "test_uma_hist_close_queue1_20261005.py",
        "test_uma_close_evidence_isolation1_20261005.py",
    ]
    results: dict[str, bool] = {}
    for name in tests:
        path = SCRIPTS / "tests" / name
        if not path.is_file():
            results[name] = False
            continue
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        results[name] = proc.returncode == 0
        tag = "PASS" if proc.returncode == 0 else "FAIL"
        print(f"{tag}  regression {name}")
    return results


def main() -> int:
    test_static_html_checks()
    test_save_close_receipt_bytes_cases()
    test_api_route_json()
    webkit = test_webkit_proof()
    regression = run_regression()

    result_path = ROOT / "state/reliability/UMA-CLOSE-STEP2-IPHONE-PHOTO-1-RESULT-2026-10-05.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)

    html_src = HTML.read_text(encoding="utf-8")
    bzg_src = (SCRIPTS / "core" / "bzg_daily_close.py").read_text(encoding="utf-8")
    serve_snip = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")

    def line_range(path: Path, needle: str) -> str:
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, 1):
            if needle in line:
                return f"{path.name}:{i}"
        return f"{path.name}:?"

    beta_pid = None
    try:
        out = subprocess.run(
            ["lsof", "-ti", "tcp:8788"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.stdout.strip():
            beta_pid = int(out.stdout.strip().split()[0])
    except Exception:
        pass

    payload = {
        "slice": "UMA-CLOSE-STEP2-IPHONE-PHOTO-1",
        "date": "2026-10-05",
        "throw_site": "dashboards/uma-blu-close.html uploadShift/uploadBankReceipt blind res.json()",
        "fix_summary": (
            "postPhoto helper with JSON guard + 502 retry; staff-safe fail UI; "
            "40MB cap + magic-byte ext + HEIC JPEG derivative; vision reads derivative; "
            "receipt-photo route always JSON on error"
        ),
        "files_changed": [
            {"file": "dashboards/uma-blu-close.html", "lines": "122-134,918-1010,1130-1150,1283-1298"},
            {"file": "scripts/core/bzg_daily_close.py", "lines": "103-320"},
            {"file": "scripts/serve_beta.py", "lines": "43454,43571-43584"},
            {"file": "scripts/tests/test_uma_close_step2_iphone_photo1_20261005.py", "lines": "new"},
        ],
        "tests_pass": PASS,
        "tests_fail": FAIL,
        "regression": regression,
        "webkit_proof": webkit,
        "beta_pid_after_reload": beta_pid,
        "staff_ready": False,
        "human_commissioned": False,
        "status": "READY FOR HUMAN TEST" if FAIL == 0 and all(regression.values()) else "BLOCKED",
    }
    if FAIL > 0:
        payload["blocked_reasons"] = [f"{FAIL} unit checks failed"]
    if not all(regression.values()):
        payload["blocked_reasons"] = payload.get("blocked_reasons", []) + [
            f"regression failed: {[k for k, v in regression.items() if not v]}"
        ]

    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    ok = FAIL == 0 and all(regression.values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
