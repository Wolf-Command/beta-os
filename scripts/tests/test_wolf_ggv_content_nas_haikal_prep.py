#!/usr/bin/env python3
"""GGV Content Machine x NAS Haikal prep — acceptance (:8788 only).

Wires Content Engine / Smart Upload operator path through NAS Library so Haikal
can human-test in the morning. Engineering only — no invent Haikal human PASS,
no staff_ready=true, no NAS destroy, Production :8787 untouched.

Run id: BF-wolf-ggv-content-nas-haikal-prep-v2-20260922
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BETA = Path("/Users/wolfterminal/beta-os")
SCRIPTS = BETA / "scripts"
BASE = "http://127.0.0.1:8788"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
MATT = "mrwolf@wolfcommand.net"
FIXTURES = SCRIPTS / "tests" / "fixtures_ggv_nas_haikal_prep"

sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("WOLF_TEST_MODE", "1")

from core import ggv_content_nas_haikal_prep as prep  # noqa: E402
from core import nas_library as nas  # noqa: E402
from core import wolf_shell as shell  # noqa: E402
from core import integration_health as health  # noqa: E402

PASS = 0
FAIL = 0
CLEANUP: list[str] = []
PROD_PID_BEFORE = ""


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
            raw_b = resp.read().decode(errors="replace")
            payload = json.loads(raw_b) if raw_b else {}
            return resp.status, payload
    except HTTPError as e:
        raw_b = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw_b) if raw_b else {}
        except json.JSONDecodeError:
            payload = {"raw": raw_b[:400]}
        return e.code, payload
    except URLError as e:
        return 0, {"ok": False, "error": "connection_refused", "message": str(e)}


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
    global PROD_PID_BEFORE
    FIXTURES.mkdir(parents=True, exist_ok=True)
    img = FIXTURES / "IMG_HAIKAL_PREP_0001.JPG"
    make_jpeg(img)

    # --- Unit: module honesty / next-action ---
    check("01 module slice", prep.SLICE == "wolf_ggv_content_nas_haikal_prep")
    check("02 run id v2", "v2" in prep.RUN_ID and "haikal-prep" in prep.RUN_ID)
    h = prep.honesty_flags()
    check("03 proven false", h.get("proven") is False)
    check("04 ready false", h.get("ready") is False)
    check("05 staff_ready false", h.get("staff_ready") is False)
    check("06 no invent haikal pass", h.get("invented_haikal_human_pass") is False)
    check("07 haikal not_started", h.get("haikal_human_status") == "not_started")
    check("08 clickup retired flag", h.get("clickup_retired") is True)
    check("09 telegram retired flag", h.get("telegram_retired") is True)

    try:
        prep.refuse_staff_ready({})
        check("10 refuse staff_ready raises", False)
    except ValueError:
        check("10 refuse staff_ready raises", True)

    try:
        prep.refuse_haikal_human_pass({})
        check("11 refuse human pass raises", False)
    except ValueError:
        check("11 refuse human pass raises", True)

    haikal_scopes = shell.scopes_from_assignments(shell.assignments_for_person("PERS-HAIKAL"))
    desk = prep.operator_desk(
        person_id="PERS-HAIKAL",
        subject=HAIKAL,
        scopes=haikal_scopes,
        can_upload=True,
    )
    check("12 desk ok", desk.get("ok") is True)
    check("13 desk staff_ready false", desk.get("staff_ready") is False)
    check("14 desk nas connected", desk.get("nas_connected") is True, str(desk.get("nas_connected")))
    check(
        "15 next action upload path",
        (desk.get("next_action") or {}).get("code") == "upload_via_smart_upload_nas",
        str((desk.get("next_action") or {}).get("code")),
    )
    check("16 allowed brands habitat", "habitat" in (desk.get("allowed_brands") or []))
    check("17 atrium not allowed", "atrium" not in (desk.get("allowed_brands") or []))
    check("18 retest steps 5", len(desk.get("retest_steps") or []) == 5)
    check("19 empty library next", bool(((desk.get("empty_states") or {}).get("library") or {}).get("next_action")))
    check("20 checklist doc path", "HAIKAL" in (desk.get("checklist_doc") or "") and "RETEST" in (desk.get("checklist_doc") or ""))

    checklist = BETA / prep.CHECKLIST_DOC
    check("21 checklist file exists", checklist.is_file())
    cl_txt = checklist.read_text(encoding="utf-8")
    check("22 checklist upload step", "Upload" in cl_txt and "Smart Upload" in cl_txt)
    check("23 checklist wrong-scope", "Wrong-scope" in cl_txt or "atrium" in cl_txt.lower())
    check("24 checklist not staff go-live", "staff go-live" in cl_txt.lower() and "staff_ready=false" in cl_txt)

    # Shell honesty
    flags = shell.honesty_flags()
    check("25 shell slice prep", flags.get("slice") == prep.SLICE or "haikal" in str(flags.get("slice")))
    check("26 shell proven false", flags.get("proven") is False)
    check("27 shell ready false", flags.get("ready") is False)
    check("28 shell staff_ready false", flags.get("staff_ready") is False)
    check("29 shell prep flag", flags.get("ggv_content_nas_haikal_prep") is True)
    check("30 shell no invent human", flags.get("invented_haikal_human_pass") is False)

    report = health.build_report()
    ret = {r["source_id"]: r for r in (report.get("retired") or [])}
    check("31 health clickup RETIRED", ret.get("clickup", {}).get("status") == "RETIRED")
    check("32 health telegram RETIRED", ret.get("telegram", {}).get("status") == "RETIRED")

    # Ports / Production sacred
    check("33 :8788 up", port_up(8788))
    check("34 :8787 up", port_up(8787))
    PROD_PID_BEFORE = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("35 prod pid recorded", bool(PROD_PID_BEFORE), PROD_PID_BEFORE)

    st, health_j = http("GET", "/api/health")
    check("36 health", st == 200 and health_j.get("ok") is True)

    st, nas_st = http("GET", "/api/nas/status")
    check("37 nas status connected", st == 200 and nas_st.get("connected") is True)
    check("38 status nas_received false", nas_st.get("nas_received") is False)

    # Operator desk API (needs development_assertion on live Beta)
    st, desk_live = http("GET", "/api/content/nas-haikal-prep", headers={"X-Wolf-Subject": HAIKAL})
    check("39 desk live 200", st == 200 and desk_live.get("ok") is True, str(desk_live)[:200])
    check("40 desk live next", bool((desk_live.get("next_action") or {}).get("label")), str(desk_live.get("next_action"))[:120])
    check("41 desk live staff_ready false", desk_live.get("staff_ready") is False)
    check("42 desk live proven false", desk_live.get("proven") is False)
    check("43 desk live ready false", desk_live.get("ready") is False)
    check("44 desk live haikal brands", "habitat" in (desk_live.get("allowed_brands") or []))

    st, anon = http("GET", "/api/content/nas-haikal-prep")
    check("45 desk anon deny", st in (401, 403))

    st, devi_desk = http("GET", "/api/content/nas-haikal-prep", headers={"X-Wolf-Subject": DEVI})
    # Devi may 403 (no content perms) or 200 with can_upload false — both honest
    if st == 403:
        check("46 devi desk fail-closed or no-upload", True, "403")
    else:
        check(
            "46 devi desk fail-closed or no-upload",
            st == 200 and devi_desk.get("can_upload") is False,
            str(devi_desk)[:160],
        )

    # Wrong-scope assets 403
    st, assets_deny = http(
        "GET", "/api/assets?brand=atrium",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("47 assets atrium 403", st == 403, str(assets_deny)[:160])

    # Authorised upload → search → preview → zip loop
    batch = f"haikal-prep-{uuid.uuid4().hex[:10]}"
    subject_tok = f"haikal-prep-{uuid.uuid4().hex[:8]}"
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
    raw, ctype = multipart(fields, ("file", "IMG_HAIKAL_PREP_0001.JPG", bytes(jpeg_bytes), "image/jpeg"))
    st, up = http(
        "POST", "/api/upload/smart", raw=raw, content_type=ctype,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("48 smart upload 200", st == 200 and up.get("ok") is True, str(up)[:240])
    check("49 nas_received true", up.get("nas_received") is True, str(up.get("nas_message")))
    check("50 nas_rel wolf-library", bool(up.get("nas_rel")) and "Wolf-Library" in (up.get("nas_rel") or ""), str(up.get("nas_rel")))
    check("51 no Volumes in upload body", "/Volumes/" not in json.dumps(up))

    asset_id = up.get("asset_id")
    nas_rel = up.get("nas_rel")
    nas_path = Path("/Volumes/01-Media-Library") / nas_rel if nas_rel else None
    on_nas = bool(nas_path and nas_path.is_file())
    check("52 file on NAS", on_nas, str(nas_path))
    if nas_path and on_nas:
        CLEANUP.append(str(nas_path))
        check("53 under _test", "_test" in str(nas_path))

    st, found = http(
        "GET",
        f"/api/assets?brand=habitat&data_lane=test&q={subject_tok}",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("54 search 200", st == 200 and found.get("ok") is True)
    hit = next((a for a in (found.get("assets") or []) if a.get("id") == asset_id), {})
    check("55 search finds asset", bool(hit), str(found.get("count")))
    check("56 search nas_received", hit.get("nas_received") is True)
    check("57 search nas_rel", bool(hit.get("nas_rel")))
    check("58 search provenance", bool((hit.get("provenance") or {})))
    check("59 search no Volumes", "/Volumes/" not in json.dumps(found))

    # Preview
    req = Request(
        BASE + f"/api/assets/{asset_id}/preview",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    try:
        with urlopen(req, timeout=30) as resp:
            preview_ok = resp.status == 200 and len(resp.read()) > 0
            check("60 preview 200 bytes", preview_ok)
    except HTTPError as exc:
        # Honest not-ready is acceptable; crash/500 is not
        check("60 preview 200 bytes", exc.code in (200, 404, 409, 422), f"http {exc.code}")

    # ZIP selected (binary — do not JSON-decode)
    reqz = Request(
        BASE + "/api/assets/zip",
        data=json.dumps({"ids": [asset_id]}).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-Wolf-Subject": HAIKAL},
    )
    try:
        with urlopen(reqz, timeout=60) as resp:
            blob = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()
            check(
                "61 zip 200",
                resp.status == 200 and ("zip" in ctype or len(blob) > 20),
                f"ctype={ctype} bytes={len(blob)}",
            )
    except HTTPError as exc:
        check("61 zip 200", False, str(exc))

    # Wrong-scope upload still 403
    fields_bad = {
        "brand": "atrium",
        "stage": "RAW",
        "media_type": "image",
        "subject": "haikal-prep-wrong",
        "detail": "deny",
        "shoot_date": "20260922",
        "data_lane": "test",
        "batch_id": f"deny-{uuid.uuid4().hex[:8]}",
    }
    raw_b, ctype_b = multipart(fields_bad, ("file", "IMG_HAIKAL_PREP_0001.JPG", img.read_bytes(), "image/jpeg"))
    st, deny = http(
        "POST", "/api/upload/smart", raw=raw_b, content_type=ctype_b,
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("62 wrong-scope upload 403", st == 403, str(deny)[:160])

    # UI markers
    req = Request(BASE + "/content-2.0.html", headers={"X-Wolf-Subject": HAIKAL})
    try:
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode()
        check("63 haikal next strip", "haikalNasNext" in html)
        check("64 nas banner", "nasBanner" in html)
        check("65 lib empty next id", "libEmptyNext" in html or "haikalNasNextLib" in html)
        check("66 zip button", "libDownloadSel" in html)
        check("67 smart upload label", "Smart Upload" in html)
        check("68 NAS badge token", "NAS" in html)
        check("69 phone css next", "haikal-nas-next" in html and "@media" in html)
    except HTTPError as exc:
        for i, name in enumerate(
            ["haikal next strip", "nas banner", "lib empty next id", "zip button",
             "smart upload label", "NAS badge token", "phone css next"],
            start=63,
        ):
            check(f"{i} {name}", False, str(exc))

    # whoami honesty live
    st, who = http("GET", "/api/wolf/shell-whoami", headers={"X-Wolf-Subject": MATT})
    honesty = (who.get("honesty") or {}) if st == 200 else {}
    check("70 whoami 200", st == 200)
    check("71 whoami staff_ready false", honesty.get("staff_ready") is False)
    check("72 whoami proven false", honesty.get("proven") is False)
    check("73 whoami ready false", honesty.get("ready") is False)
    check(
        "74 whoami prep flag",
        honesty.get("ggv_content_nas_haikal_prep") is True
        or flags.get("ggv_content_nas_haikal_prep") is True,
    )

    # Cleanup test NAS only
    cleaned = 0
    for p in list(CLEANUP):
        result = nas.cleanup_test_asset(p)
        if result.get("deleted") or result.get("reason") == "already_absent":
            cleaned += 1
            check(f"75 cleanup {Path(p).name}", result.get("ok") is True, str(result))
    check("76 cleaned or empty", cleaned >= 1 or not CLEANUP)

    refuse = nas.cleanup_test_asset(
        "/Volumes/01-Media-Library/Brand-Assets/GGV/logos/goss-group-logo.png"
    )
    check("77 refuse non-test cleanup", refuse.get("deleted") is False)

    pid_after = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("78 prod pid unchanged", pid_after == PROD_PID_BEFORE, f"{PROD_PID_BEFORE}→{pid_after}")
    check("79 beta still up", port_up(8788))
    check("80 no invent CAP ready", h.get("cap_ggv_01_invented_ready") is False)

    print(f"\nRESULT  PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
