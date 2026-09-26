#!/usr/bin/env python3
"""Content Engine NAS library proof on Beta :8788 as Creative Director.

Uses a short-lived public JWK so a Haikal-shaped Cloudflare Access JWT resolves
to the creative-director assignment. Removes the key when finished.
Does not touch production :8787. staff_ready stays false.
"""
from __future__ import annotations

import base64
import json
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import cf_access  # noqa: E402
from core import request_auth  # noqa: E402

CATALOG = ROOT / "catalog" / "content_library.sqlite"
HAIKAL = "haikalqilbari123@gmail.com"
BASE = "http://127.0.0.1:8788"

PASS = 0
FAIL = 0


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def mint_jwt(private_key, *, kid: str, claims: dict) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    h_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    sig = private_key.sign(f"{h_b64}.{p_b64}".encode("ascii"), PKCS1v15(), hashes.SHA256())
    return f"{h_b64}.{p_b64}.{_b64url(sig)}"


def http_json(path: str, token: str, method: str = "GET", body: dict | None = None, raw: bytes | None = None, content_type: str | None = None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode("utf-8"))
    headers = {"Cf-Access-Jwt-Assertion": token, "Accept": "application/json"}
    if body is not None and raw is None:
        headers["Content-Type"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = resp.read()
            return resp.status, dict(resp.headers), json.loads(payload.decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        raw_b = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw_b) if raw_b else {}
        except json.JSONDecodeError:
            payload = {"error": raw_b[:240]}
        return exc.code, dict(exc.headers), payload


def http_bytes(path: str, token: str, method: str = "GET", body: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Cf-Access-Jwt-Assertion": token, "Accept": "*/*"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def multipart(fields: dict[str, str], file_field: tuple[str, str, bytes, str]) -> tuple[bytes, str]:
    boundary = f"----WolfBound{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        chunks.append(value.encode() + b"\r\n")
    name, filename, payload, ctype = file_field
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
    chunks.append(f"Content-Type: {ctype}\r\n\r\n".encode())
    chunks.append(payload)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def tiny_jpeg() -> bytes:
    return bytes([
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


def nas_cards(payload: dict) -> list[dict]:
    return [row for row in (payload.get("assets") or []) if str(row.get("id", "")).startswith("nas:")]


def main() -> int:
    try:
        pid8787 = subprocess.check_output(["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True).strip()
    except subprocess.CalledProcessError:
        pid8787 = ""
    log(pid8787.splitlines()[:1] == ["15975"], "production pid unchanged before", pid8787.replace("\n", ","))

    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    photo = conn.execute(
        """
        SELECT id, original_filename, size FROM nas_index
        WHERE index_state='HASHED' AND brand_slug='atrium'
          AND lower(original_filename) LIKE '%.jpg'
          AND size BETWEEN 1000 AND 1500000
        ORDER BY size LIMIT 1
        """
    ).fetchone()
    video = conn.execute(
        """
        SELECT id, original_filename, size FROM nas_index
        WHERE index_state='HASHED' AND brand_slug='atrium'
          AND (lower(original_filename) LIKE '%.mov' OR lower(original_filename) LIKE '%.mp4')
          AND size BETWEEN 1000 AND 2500000
        ORDER BY size LIMIT 1
        """
    ).fetchone()
    conn.close()
    log(photo is not None and video is not None, "catalog has an atrium photo and video", f"photo={None if photo is None else photo['id']} video={None if video is None else video['id']}")
    if photo is None or video is None:
        print(f"EXIT: FAIL PASS={PASS} FAIL={FAIL}")
        return 1
    keyword = Path(str(photo["original_filename"])).stem
    if len(keyword) > 24:
        keyword = keyword[:24]

    sim_path = cf_access.SIM_JWK_PATH
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa

        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        numbers = private.public_key().public_numbers()
        kid = "ce-nas-round3-sim"
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": _b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
            "e": _b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
        }
        sim_path.parent.mkdir(parents=True, exist_ok=True)
        sim_path.write_text(json.dumps(jwk), encoding="utf-8")
        now = int(time.time())
        token = mint_jwt(
            private,
            kid=kid,
            claims={
                "iss": request_auth.team_domain(),
                "aud": request_auth.access_audience(),
                "email": HAIKAL,
                "exp": now + 900,
                "iat": now - 5,
                "sub": "ce-nas-round3",
            },
        )
        code, _headers, who = http_json("/api/wolf/shell-whoami", token)
        seat = ((who.get("whoami") or {}).get("active_assignment") or {})
        log(
            code == 200 and seat.get("role") == "ROLE-GGV-CREATIVE-DIRECTOR" and seat.get("source") == "org_assignments",
            "session is creative director",
            str({k: seat.get(k) for k in ("id", "role", "source")}),
        )
        kcode, _h, found = http_json(f"/api/assets?brand=atrium&q={urllib.parse.quote(keyword)}", token)
        hits = nas_cards(found)
        log(
            kcode == 200 and found.get("ok") is True and int(found.get("nas_matched") or 0) >= 1 and found.get("staff_ready") is False,
            "historical keyword search hits",
            f"q={keyword} matched={found.get('nas_matched')} cards={len(hits)}",
        )
        log("/Volumes/" not in json.dumps(found), "search does not leak volume paths")
        pcode, _h, photos = http_json("/api/assets?brand=atrium&media_type=image&q=" + urllib.parse.quote(keyword), token)
        photo_cards = [c for c in nas_cards(photos) if c.get("media_type") == "image"]
        vcode, _h, videos = http_json("/api/assets?brand=atrium&media_type=video", token)
        video_cards = [c for c in nas_cards(videos) if c.get("media_type") == "video"]
        log(pcode == 200 and bool(photo_cards), "photo results", str(len(photo_cards)))
        log(vcode == 200 and bool(video_cards), "video results", str(len(video_cards)))
        hcode, _h, habitat = http_json("/api/assets?brand=habitat&media_type=image", token)
        acode, _h, atrium = http_json("/api/assets?brand=atrium&media_type=image", token)
        habitat_brands = {c.get("brand") for c in nas_cards(habitat)}
        atrium_brands = {c.get("brand") for c in nas_cards(atrium)}
        log(
            hcode == 200 and acode == 200 and habitat_brands == {"habitat"} and "atrium" in atrium_brands and int(habitat.get("nas_matched") or 0) != int(atrium.get("nas_matched") or 0),
            "brand switching changes the library",
            f"habitat={habitat.get('nas_matched')} atrium={atrium.get('nas_matched')}",
        )
        image = photo_cards[0]
        movie = video_cards[0]
        ic, ih, ib = http_bytes(str(image.get("preview_url")) + "?play=1", token)
        log(ic == 200 and (ih.get("Content-Type") or "").startswith("image/") and len(ib) > 32, "photo preview", ih.get("Content-Type"))
        vc, vh, vb = http_bytes(str(movie.get("preview_url")) + "?play=1", token)
        log(vc == 200 and (vh.get("Content-Type") or "").startswith("video/") and len(vb) > 32, "video preview", vh.get("Content-Type"))
        nas_id = str(image["id"]).split(":", 1)[1]
        dc, dh, db = http_bytes(f"/api/content/nas-media/{nas_id}/preview?download=1", token)
        disposition = dh.get("Content-Disposition") or ""
        log(dc == 200 and disposition.lower().startswith("attachment") and len(db) > 32, "individual download", disposition[:80])
        zcode, zh, zb = http_bytes(
            "/api/assets/zip",
            token,
            method="POST",
            body={"ids": [image["id"], movie["id"]]},
        )
        log(
            zcode == 200 and (zh.get("Content-Type") or "").startswith("application/zip") and zb[:2] == b"PK",
            "multi-select zip",
            f"status={zcode} bytes={len(zb)}",
        )
        stamp = time.strftime("%Y%m%d%H%M%S")
        filename = f"WOLF-TEST-UPLOAD-{stamp}.jpg"
        raw, ctype = multipart(
            {
                "brand": "atrium",
                "stage": "RAW",
                "media_type": "image",
                "subject": "wolf-test-upload",
                "detail": filename,
                "shoot_date": "20260926",
                "data_lane": "operational",
                "batch_id": f"wolf-test-upload-{stamp}",
                "force": "1",
            },
            ("file", filename, tiny_jpeg(), "image/jpeg"),
        )
        ucode, _uh, uploaded = http_json("/api/upload/smart", token, method="POST", raw=raw, content_type=ctype)
        log(ucode == 200 and uploaded.get("ok") is True and uploaded.get("nas_received") is True, "smart upload received on NAS", str(uploaded.get("nas_rel")))
        log("/Volumes/" not in json.dumps(uploaded), "upload response hides the volume path")
        scode, _sh, searched = http_json("/api/assets?brand=atrium&q=" + urllib.parse.quote(filename), token)
        ids = {row.get("id") for row in (searched.get("assets") or [])}
        log(scode == 200 and uploaded.get("asset_id") in ids, "upload is searchable in the library", str(uploaded.get("asset_id")))
        asset_id = uploaded.get("asset_id")
        nas_path = ""
        if asset_id:
            write = sqlite3.connect(CATALOG)
            row = write.execute("SELECT nas_path, nas_received FROM assets WHERE id=?", (asset_id,)).fetchone()
            write.close()
            nas_path = str(row[0] or "") if row else ""
            log(bool(row) and int(row[1] or 0) == 1 and Path(nas_path).is_file(), "uploaded file is on the NAS path", nas_path)
            print(f"NAS_PATH {nas_path}")
        log(searched.get("staff_ready") is False, "staff_ready stays false")
    except Exception as exc:  # noqa: BLE001
        log(False, "round3 library proof", str(exc)[:400])
    finally:
        if sim_path.is_file():
            sim_path.unlink()
    try:
        pid_after = subprocess.check_output(["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True).strip()
    except subprocess.CalledProcessError:
        pid_after = ""
    log(pid_after.splitlines()[:1] == ["15975"], "production pid unchanged after", pid_after.replace("\n", ","))
    log(not sim_path.is_file(), "sim public key removed")
    print(f"EXIT: {'SUCCESS' if FAIL == 0 else 'FAIL'} PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
