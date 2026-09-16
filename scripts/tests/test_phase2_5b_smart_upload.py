#!/usr/bin/env python3
"""Phase 2.5B Smart Upload Naming — acceptance tests (:8788 only).

Uses data_lane=test fixtures so ops Library stays clean.
Never touches :8787 / Metricool write / publish / live AI / semantic match.
"""
from __future__ import annotations

import json
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BETA = Path("/Users/wolfterminal/beta-os")
SCRIPTS = BETA / "scripts"
BASE = "http://127.0.0.1:8788"
HAIKAL = "haikalqilbari123@gmail.com"
STRANGER = "nobody@example.com"
FIXTURES = BETA / "scripts" / "tests" / "fixtures_smart_upload"

sys.path.insert(0, str(SCRIPTS))
import wolf_naming as wn  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def http(method: str, path: str, body: dict | None = None, headers: dict | None = None, raw: bytes | None = None, content_type: str | None = None):
    data = raw
    if body is not None and raw is None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None and raw is None:
        req.add_header("Content-Type", "application/json")
    if content_type:
        req.add_header("Content-Type", content_type)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_b = resp.read().decode()
            payload = json.loads(raw_b) if raw_b else {}
            return resp.status, payload
    except urllib.error.HTTPError as e:
        raw_b = e.read().decode()
        try:
            payload = json.loads(raw_b) if raw_b else {}
        except json.JSONDecodeError:
            payload = {"raw": raw_b}
        return e.code, payload


def make_png(path: Path, color=(40, 120, 200)) -> None:
    """Minimal valid 1x1 PNG via zlib-less hardcoded bytes."""
    # Precomputed 1x1 PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf"
        b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path.write_bytes(png)


def make_jpeg(path: Path) -> None:
    # Minimal JPEG (1x1)
    jpeg = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x03, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
        0x7F, 0xFF, 0xD9,
    ])
    path.write_bytes(jpeg)


def multipart(fields: dict[str, str], file_field: tuple[str, str, bytes, str]) -> tuple[bytes, str]:
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
    chunks.append(f"Content-Type: {ctype}\r\n\r\n".encode())
    chunks.append(data)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    png1 = FIXTURES / "IMG_0001.JPG"  # camera-like name (we'll use jpeg bytes with .jpg)
    png2 = FIXTURES / "DSCF1234.JPG"
    bad = FIXTURES / "evil.txt"
    make_jpeg(png1)
    make_jpeg(png2)
    bad.write_text("not media")

    # 01 health :8788
    st, health = http("GET", "/api/health")
    check("01 health :8788", st == 200 and health.get("ok") is True, str(health))

    # 02 ports
    out = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-iTCP:8788", "-sTCP:LISTEN"], text=True
    )
    check("02 :8788 listening", "127.0.0.1:8788" in out)
    check("03 :8787 still listening (untouched)", ":8787" in out)

    # 04 naming unit
    name = wn.build_canonical_filename(
        "habitat", "RAW", "video", "habitat-villa", "pool-wide", "20260915", "001", ".mp4"
    )
    check(
        "04 naming pattern",
        name == "habitat_RAW_video_habitat-villa_pool-wide_20260915_001.mp4",
        name,
    )
    edit = wn.sequence_token("EDIT", 1)
    check("05 EDIT uses v01", edit == "v01")
    check("06 slug normalize", wn.slug_normalize("Pool Wide!!") == "pool-wide")

    # 07 NAS status honest
    st, nas = http("GET", "/api/nas/status")
    check("07 nas status endpoint", st == 200 and "connected" in nas)
    check("08 nas_received never true", nas.get("nas_received") is False, str(nas))

    # 09 preview names
    st, prev = http(
        "POST",
        "/api/upload/preview-names",
        body={
            "brand": "habitat",
            "stage": "RAW",
            "media_type": "image",
            "subject": "habitat-villa",
            "shoot_date": "2026-09-15",
            "files": [
                {"original_filename": "IMG_0001.JPG", "detail": "pool-wide"},
                {"original_filename": "DSCF1234.JPG", "detail": "pool-wide"},
            ],
        },
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("09 preview-names 200", st == 200 and prev.get("ok") is True, str(prev)[:160])
    previews = prev.get("previews") or []
    check("10 preview count 2", len(previews) == 2)
    if len(previews) >= 2:
        check(
            "11 unique sequences",
            previews[0]["sequence_token"] != previews[1]["sequence_token"],
            f"{previews[0]['sequence_token']} vs {previews[1]['sequence_token']}",
        )
        check(
            "12 original preserved in preview",
            previews[0]["original_filename"] == "IMG_0001.JPG",
        )
        check("13 canonical has brand_STAGE", "habitat_RAW_image_habitat-villa" in previews[0]["canonical_filename"])

    # 14 stranger forbidden
    st, body = http(
        "POST",
        "/api/upload/preview-names",
        body={"brand": "habitat", "stage": "RAW", "media_type": "image", "subject": "x", "shoot_date": "20260915", "files": [{"original_filename": "a.jpg"}]},
        headers={"X-Wolf-Subject": STRANGER},
    )
    check("14 stranger preview 403", st == 403)

    # 15 smart upload (test lane) file 1
    fields = {
        "brand": "habitat",
        "stage": "RAW",
        "media_type": "image",
        "subject": "phase25b-test-villa",
        "detail": "pool-wide",
        "location": "umalas",
        "shoot_date": "20260915",
        "data_lane": "test",
        "batch_id": f"test-{uuid.uuid4().hex[:8]}",
    }
    raw, ctype = multipart(fields, ("file", "IMG_0001.JPG", png1.read_bytes(), "image/jpeg"))
    st, up1 = http(
        "POST",
        "/api/upload/smart",
        raw=raw,
        content_type=ctype,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("15 smart upload #1", st == 200 and up1.get("ok") is True, str(up1)[:200])
    check("16 library READY", up1.get("library_status") == "LIBRARY_READY", str(up1.get("library_status")))
    check("17 original preserved", up1.get("original_filename") in ("IMG_0001.JPG", "IMG_0001.jpg"), str(up1.get("original_filename")))
    check("18 canonical wolf name", bool(up1.get("canonical_filename")) and "habitat_RAW_image_phase25b-test-villa" in (up1.get("canonical_filename") or ""))
    check("19 no FS path in response keys", "saved_path" not in up1 and "v2_path" not in up1)
    check("20 nas_received false", up1.get("nas_received") is False)
    check("21 test lane tagged", up1.get("data_lane") == "test")
    canon1 = up1.get("canonical_filename")
    asset1 = up1.get("asset_id")

    # 22 second upload same meta → unique sequence
    raw2, ctype2 = multipart(fields, ("file", "DSCF1234.JPG", png2.read_bytes(), "image/jpeg"))
    st, up2 = http(
        "POST",
        "/api/upload/smart",
        raw=raw2,
        content_type=ctype2,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("22 smart upload #2", st == 200 and up2.get("ok") is True)
    check(
        "23 unique seq no overwrite",
        up2.get("canonical_filename") != canon1 and up2.get("sequence_token") != up1.get("sequence_token"),
        f"{up1.get('sequence_token')} vs {up2.get('sequence_token')}",
    )

    # 24 files exist on disk under library_v2/RAW with wolf names
    lib = BETA / "library_v2" / "RAW"
    check("24 file1 on disk", canon1 and (lib / canon1).is_file(), str(canon1))
    check("25 file2 on disk", up2.get("canonical_filename") and (lib / up2["canonical_filename"]).is_file())

    # 26 unsafe reject
    rawb, ctypeb = multipart(fields, ("file", "evil.txt", bad.read_bytes(), "text/plain"))
    st, bad_up = http(
        "POST",
        "/api/upload/smart",
        raw=rawb,
        content_type=ctypeb,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("26 unsafe ext rejected", st in (400, 415) and bad_up.get("ok") is not True, f"st={st} {bad_up}")

    # 27 ops library listing excludes test lane
    st, assets = http("GET", "/api/assets?brand=habitat")
    check("27 assets list 200", st == 200)
    ids = {a.get("id") for a in (assets.get("assets") or [])}
    check("28 test asset NOT in ops library", asset1 not in ids, f"asset1={asset1}")
    # confirm no paths
    blob = json.dumps(assets)
    check("29 no FS paths in assets JSON", "/Users/" not in blob and "library_v2/" not in blob)

    # 30 test lane query includes them
    st, tassets = http("GET", "/api/assets?brand=habitat&data_lane=test")
    tids = {a.get("id") for a in (tassets.get("assets") or [])}
    check("30 test lane query includes", asset1 in tids)

    # 31 meta persisted
    import sqlite3
    conn = sqlite3.connect(str(BETA / "catalog" / "content_library.sqlite"))
    row = conn.execute(
        "SELECT original_filename, canonical_filename, subject, detail, location, shoot_date, sequence_token, data_lane, library_status FROM assets WHERE id=?",
        (asset1,),
    ).fetchone()
    conn.close()
    check(
        "31 meta persisted",
        row is not None
        and row[0] in ("IMG_0001.JPG", "IMG_0001.jpg")
        and row[2] == "phase25b-test-villa"
        and row[3] == "pool-wide"
        and row[4] == "umalas"
        and row[5] == "20260915"
        and row[7] == "test"
        and row[8] == "LIBRARY_READY",
        str(row),
    )

    # 32 Content Plan still works
    st, plans = http("GET", "/api/planner/plans?brand=habitat", headers={"X-Wolf-Subject": HAIKAL})
    check("32 content plans OK", st == 200 and plans.get("ok") is True, f"count={plans.get('count')}")

    # 33 recent uploads operational (should not list test)
    st, recent = http("GET", f"/api/upload/recent?brand=habitat&data_lane=operational", headers={"X-Wolf-Subject": HAIKAL})
    check("33 recent operational 200", st == 200)
    recent_ids = {i.get("id") for i in (recent.get("items") or [])}
    check("34 test not in ops recent", asset1 not in recent_ids)

    # 35 UI page serves
    req = urllib.request.Request(BASE + "/content-2.0.html")
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode()
    check("35 content-2.0.html serves", "Smart Upload" in html and "wizStep1" in html)
    check("36 no :8787 in HTML", ":8787" not in html)

    print(f"\nRESULT  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
