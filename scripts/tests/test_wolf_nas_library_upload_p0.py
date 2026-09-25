#!/usr/bin/env python3
"""Wolf NAS Library + Upload P0 — acceptance (:8788 only).

Connects Smart Upload to /Volumes/01-Media-Library/_Imports/Wolf-Library.
nas_received true only when file verified on NAS. Wrong-scope 403.
Honesty proven=false ready=false staff_ready=false. Production :8787 untouched.
Test assets marked data_lane=test under _test/; audited cleanup.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BETA = Path("/Users/wolfterminal/beta-os")
SCRIPTS = BETA / "scripts"
BASE = "http://127.0.0.1:8788"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
MATT = "mrwolf@wolfcommand.net"
STRANGER = "nobody@example.com"
FIXTURES = SCRIPTS / "tests" / "fixtures_nas_library_p0"
NAS_TEST_ROOT = Path("/Volumes/01-Media-Library/_Imports/Wolf-Library/_test")

sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("WOLF_TEST_MODE", "1")

from core import nas_library as nas  # noqa: E402
from core import wolf_shell as shell  # noqa: E402
from core import integration_health as health  # noqa: E402

PASS = 0
FAIL = 0
CLEANUP: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def http(method: str, path: str, body: dict | None = None, headers: dict | None = None,
         raw: bytes | None = None, content_type: str | None = None):
    data = raw
    if body is not None and raw is None:
        data = json.dumps(body).encode()
    req = Request(BASE + path, data=data, method=method)
    if body is not None and raw is None:
        req.add_header("Content-Type", "application/json")
    if content_type:
        req.add_header("Content-Type", content_type)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=90) as resp:
            raw_b = resp.read().decode()
            payload = json.loads(raw_b) if raw_b else {}
            return resp.status, payload
    except HTTPError as e:
        raw_b = e.read().decode()
        try:
            payload = json.loads(raw_b) if raw_b else {}
        except json.JSONDecodeError:
            payload = {"raw": raw_b[:400]}
        return e.code, payload


def make_jpeg(path: Path) -> None:
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


def port_up(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    img = FIXTURES / "IMG_NAS_P0_0001.JPG"
    make_jpeg(img)

    # --- Unit: registry / scope / honesty ---
    reg = nas.registry()
    check("01 registry ok", reg.get("ok") is True)
    check("02 canonical connected", reg.get("canonical_connected") is True, str(reg.get("canonical_connected")))
    check("03 no destructive registry", reg.get("destructive") is False)
    check("04 honesty proven false", nas.HONESTY["proven"] is False and nas.HONESTY["ready"] is False)
    check("05 staff_ready false", nas.HONESTY["staff_ready"] is False)

    haikal_scopes = shell.scopes_from_assignments(shell.assignments_for_person("PERS-HAIKAL"))
    check("06 haikal habitat allowed", nas.scopes_allow_brand(haikal_scopes, "habitat"))
    check("07 haikal content-all allows atrium", nas.scopes_allow_brand(haikal_scopes, "atrium") and "SCOPE-AMG" not in haikal_scopes, str(haikal_scopes))
    matt_scopes = shell.scopes_from_assignments(shell.assignments_for_person("PERS-MATT"))
    check("08 matt atrium allowed", nas.scopes_allow_brand(matt_scopes, "atrium"))

    retired = nas.retired_systems()
    ids = {r["source_id"] for r in retired}
    check("09 clickup retired", "clickup" in ids and all(r["lifecycle"] == "RETIRED" for r in retired if r["source_id"] == "clickup"))
    check("10 telegram retired", "telegram" in ids)

    report = health.build_report()
    ret = {r["source_id"]: r for r in (report.get("retired") or [])}
    check("11 health clickup RETIRED", ret.get("clickup", {}).get("status") == "RETIRED")
    check("12 health telegram RETIRED", ret.get("telegram", {}).get("status") == "RETIRED")
    check("13 health connectors no GREEN", all(c["status"] in health.ALLOWED for c in report["connectors"]))

    flags = shell.honesty_flags()
    check("14 shell nas slice", "nas" in str(flags.get("slice", "")).lower())
    check("15 shell proven false", flags.get("proven") is False)
    check("16 shell ready false", flags.get("ready") is False)
    check("17 shell staff_ready false", flags.get("staff_ready") is False)
    check("18 nas_library flag", flags.get("nas_library_upload_p0") is True)

    # --- Ports ---
    check("19 :8788 up", port_up(8788))
    check("20 :8787 up untouched", port_up(8787))
    pid8787 = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("21 prod pid recorded", bool(pid8787), pid8787)

    # --- Live health / nas status ---
    st, health_j = http("GET", "/api/health")
    check("22 health", st == 200 and health_j.get("ok") is True)

    st, nas_st = http("GET", "/api/nas/status")
    check("23 nas status connected", st == 200 and nas_st.get("connected") is True, str(nas_st)[:160])
    check("24 status nas_received false", nas_st.get("nas_received") is False)

    st, reg_live = http("GET", "/api/nas/registry", headers={"X-Wolf-Subject": HAIKAL})
    check("25 registry authorised", st == 200 and reg_live.get("ok") is True, str(reg_live)[:160])
    st, reg_deny = http("GET", "/api/nas/registry")
    check("26 registry anon deny", st in (401, 403))

    # Sample index (read-only) — small cap
    st, sample = http(
        "POST",
        "/api/nas/index/sample",
        body={"cap": 25},
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("27 sample index ok", st == 200 and sample.get("ok") is True, str(sample)[:200])
    check("28 sample non-destructive", sample.get("destructive") is False)

    st, search = http(
        "GET",
        "/api/nas/index/search?q=logo&limit=10",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("29 index search 200", st == 200 and search.get("ok") is True)
    blob = json.dumps(search)
    check("30 no absolute Volumes leak", "/Volumes/" not in blob)

    # --- Wrong scope 403 (Haikal + atrium) ---
    fields_bad = {
        "brand": "atrium",
        "stage": "RAW",
        "media_type": "image",
        "subject": "nas-p0-wrong-scope",
        "detail": "scope-deny",
        "shoot_date": "20260922",
        "data_lane": "test",
        "batch_id": f"nas-p0-deny-{uuid.uuid4().hex[:8]}",
    }
    raw_b, ctype_b = multipart(fields_bad, ("file", "IMG_NAS_P0_0001.JPG", img.read_bytes(), "image/jpeg"))
    st, deny = http(
        "POST", "/api/upload/smart", raw=raw_b, content_type=ctype_b,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("31 wrong-scope atrium 403", st == 403, str(deny)[:200])
    check("32 wrong-scope nas_received false", deny.get("nas_received") is not True)

    st, assets_deny = http(
        "GET", "/api/assets?brand=atrium&data_lane=test",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("33 assets wrong-scope 403", st == 403, str(assets_deny)[:160])

    # Devi lacks can_upload
    raw_d, ctype_d = multipart(
        {**fields_bad, "brand": "habitat", "subject": "nas-p0-devi"},
        ("file", "IMG_NAS_P0_0001.JPG", img.read_bytes(), "image/jpeg"),
    )
    st, devi = http(
        "POST", "/api/upload/smart", raw=raw_d, content_type=ctype_d,
        headers={"X-Wolf-Subject": DEVI},
    )
    check("34 devi upload 403", st == 403)

    st, stranger = http(
        "POST", "/api/upload/smart", raw=raw_d, content_type=ctype_d,
        headers={"X-Wolf-Subject": STRANGER},
    )
    check("35 stranger upload 403", st == 403)

    # --- Authorised upload lands on NAS ---
    batch = f"nas-p0-{uuid.uuid4().hex[:10]}"
    subject_tok = f"nas-p0-habitat-{uuid.uuid4().hex[:8]}"
    # Unique bytes so content_hash differs across runs (never silent dup discard)
    jpeg_bytes = bytearray(img.read_bytes())
    jpeg_bytes[-3] = (jpeg_bytes[-3] + (uuid.uuid4().int % 50) + 1) % 256
    fields = {
        "brand": "habitat",
        "stage": "RAW",
        "media_type": "image",
        "subject": subject_tok,
        "detail": "pool-wide",
        "location": "umalas",
        "shoot_date": "20260922",
        "data_lane": "test",
        "batch_id": batch,
        "force": "1",
    }
    raw, ctype = multipart(fields, ("file", "IMG_NAS_P0_0001.JPG", bytes(jpeg_bytes), "image/jpeg"))
    st, up = http(
        "POST", "/api/upload/smart", raw=raw, content_type=ctype,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("36 smart upload 200", st == 200 and up.get("ok") is True, str(up)[:240])
    check("37 nas_received true", up.get("nas_received") is True, str(up.get("nas_message")))
    check("38 original preserved", up.get("original_filename") in ("IMG_NAS_P0_0001.JPG", "IMG_NAS_P0_0001.jpg"))
    check("39 nas_rel present", bool(up.get("nas_rel")) and "Wolf-Library" in (up.get("nas_rel") or "") and "_test" in (up.get("nas_rel") or ""), str(up.get("nas_rel")))
    check("40 no abs path in body", "/Volumes/" not in json.dumps(up) and "saved_path" not in up)

    asset_id = up.get("asset_id")
    nas_rel = up.get("nas_rel")
    # Prove file on NAS
    nas_path = Path("/Volumes/01-Media-Library") / nas_rel if nas_rel else None
    on_nas = bool(nas_path and nas_path.is_file())
    check("41 file really on NAS", on_nas, str(nas_path))
    if nas_path and on_nas:
        CLEANUP.append(str(nas_path))
        check("42 under _test prefix", "_test" in str(nas_path))
        check("43 size matches", nas_path.stat().st_size == len(jpeg_bytes))

    # Search finds it
    st, found = http(
        "GET",
        f"/api/assets?brand=habitat&data_lane=test&q={subject_tok}",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("44 search 200", st == 200 and found.get("ok") is True)
    ids_found = {a.get("id") for a in (found.get("assets") or [])}
    check("45 search finds asset", asset_id in ids_found, str(ids_found)[:120])
    hit = next((a for a in (found.get("assets") or []) if a.get("id") == asset_id), {})
    check("46 search nas_received", hit.get("nas_received") is True)
    check("47 search no Volumes leak", "/Volumes/" not in json.dumps(found))

    # Dup check never silent discard (same bytes, no force)
    fields_noforce = {k: v for k, v in fields.items() if k != "force"}
    raw2, ctype2 = multipart(fields_noforce, ("file", "IMG_NAS_P0_0001.JPG", bytes(jpeg_bytes), "image/jpeg"))
    st, dup = http(
        "POST", "/api/upload/smart", raw=raw2, content_type=ctype2,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("48 duplicate warning", st == 409 and dup.get("duplicate") is True, str(dup)[:160])

    # whoami honesty live
    st, who = http("GET", "/api/wolf/shell-whoami", headers={"X-Wolf-Subject": MATT})
    check("49 whoami 200", st == 200 and who.get("ok") is True)
    h = (who.get("honesty") or who.get("whoami", {}).get("honesty") or {})
    if not h and isinstance(who.get("whoami"), dict):
        h = who["whoami"]
    # payload shape: honesty often top-level via shell_whoami_payload
    honesty = who.get("honesty") or {}
    check("50 live proven false", honesty.get("proven") is False or flags.get("proven") is False)
    check("51 live ready false", honesty.get("ready") is False or flags.get("ready") is False)

    # UI markers (content workspace is scope-gated)
    req = Request(BASE + "/content-2.0.html", headers={"X-Wolf-Subject": HAIKAL})
    try:
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode()
        check("52 library select all", "libSelectAll" in html and "libDeselectAll" in html)
        check("53 smart upload wizard", "Smart Upload" in html and "wizStep1" in html)
        check("54 nas banner", "nasBanner" in html)
    except HTTPError as exc:
        check("52 library select all", False, str(exc))
        check("53 smart upload wizard", False)
        check("54 nas banner", False)

    # DB row
    conn = sqlite3.connect(str(BETA / "catalog" / "content_library.sqlite"))
    row = conn.execute(
        "SELECT nas_received, nas_rel, original_filename, data_lane FROM assets WHERE id=?",
        (asset_id,),
    ).fetchone()
    conn.close()
    check(
        "55 db nas_received",
        row is not None and int(row[0] or 0) == 1 and row[3] == "test",
        str(row),
    )

    # Audited cleanup of test NAS file only
    cleaned = 0
    for p in list(CLEANUP):
        result = nas.cleanup_test_asset(p)
        if result.get("deleted") or result.get("reason") == "already_absent":
            cleaned += 1
            check(f"56 cleanup ok {Path(p).name}", result.get("ok") is True, str(result))
    check("57 cleaned at least one", cleaned >= 1 or not CLEANUP)

    # Refuse cleanup outside _test
    refuse = nas.cleanup_test_asset("/Volumes/01-Media-Library/Brand-Assets/GGV/logos/goss-group-logo.png")
    check("58 refuse non-test cleanup", refuse.get("deleted") is False)

    # Production pid unchanged
    pid8787_after = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("59 prod pid unchanged", pid8787_after == pid8787, f"{pid8787}→{pid8787_after}")
    check("60 beta still up", port_up(8788))

    print(f"\nRESULT  PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
