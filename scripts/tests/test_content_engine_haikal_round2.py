#!/usr/bin/env python3
"""Content Engine Haikal round 2 — shared brand context + NAS resolver.

Beta only. staff_ready stays false. Does not touch :8787.
The deployed :8788 proof uses a short-lived public JWK so a Haikal-shaped
Cloudflare Access JWT can be verified, then the file is removed.
"""
from __future__ import annotations

import base64
import json
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import cf_access  # noqa: E402
from core import content_engine_repair as repair  # noqa: E402
from core import nas_library as nas  # noqa: E402
from core import request_auth  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
EVIDENCE = ROOT / "state" / "commissioning" / "evidence" / "CE-HAIKAL-ROUND2-GATE-2026-09-25.json"
HAIKAL = "haikalqilbari123@gmail.com"
NAMES = (
    "Atrium",
    "Uma Blu",
    "Selo Group",
    "Habitat",
    "Tropik",
    "The One",
    "Blu Zone Rainforest Resto",
    "Goss Group",
)

PASS = 0
FAIL = 0
LINES: list[str] = []
GATES: dict[str, str] = {}


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def gate(key: str, ok: bool, detail: str = "") -> None:
    GATES[key] = "PASS" if ok else "FAIL"
    log(ok, key, detail)


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


def http_json(path: str, token: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8788" + path,
        data=data,
        method=method,
        headers={
            "Cf-Access-Jwt-Assertion": token,
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if data else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw[:240]}
        return exc.code, payload


def http_bytes(path: str, token: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(
        "http://127.0.0.1:8788" + path,
        headers={"Cf-Access-Jwt-Assertion": token, "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.status, resp.headers.get("Content-Type") or "", resp.read(64)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type") or "", exc.read(120)


def main() -> int:
    raw = HTML.read_text(encoding="utf-8")
    who = shell.build_whoami(person_id="PERS-HAIKAL", email=HAIKAL)
    active = who.get("active_assignment") or {}
    scopes = list(who.get("scopes") or [])
    log(active.get("id") == "ASG-HAIKAL-CD-1", "assignment id", str(active.get("id")))
    log(active.get("role") == "ROLE-GGV-CREATIVE-DIRECTOR", "assignment role", str(active.get("role")))
    log(active.get("source") == "org_assignments", "assignment source is the org table")
    log("SCOPE-WOLF-CONTENT-ALL-BRANDS" in scopes, "content-all scope present")
    log("SCOPE-AMG" not in scopes and "SCOPE-WOLF-GROUP" not in scopes, "no AMG or group scope")
    brands = nas.brands_for_scopes(scopes)
    log(len(brands) == 8, "eight content brands", str(brands))
    log(repair.library_display_title("", "", "IMG_2044.MOV") == "IMG_2044.MOV", "filename title fallback")
    log(repair.library_display_title("pool-deck", "wide", "IMG_1.JPG") == "pool deck · wide", "canonical title wins")
    log(repair.library_display_title("", "", "") == "Untitled", "untitled only without a filename")
    log(repair.staff_upload_outcome({"id": 1, "library_status": "FAILED", "nas_received": 0}) == "Failed", "failed outcome")
    log("Uploading ${n + 1} of ${total}" in raw and "✓ Complete" in raw and "Adding to Library" in raw, "simple upload status copy")
    log("All Authorised Brands" in raw and "This Brand" in raw and ">All Brands<" in raw, "header and library brand filters")
    log("Wolf Intelligence · unavailable" in raw and 'href="/content-2.0">Content Engine<' in raw, "app switcher")
    log('id="upContentClass"' in raw and 'value="broll"' not in raw, "content type separate from media")
    log("/api/brands" not in raw, "desk does not read the legacy brands endpoint")
    log(repair.public_status().get("staff_ready") is False, "repair status stays unready")
    log(repair.public_status().get("round2_run_id") == repair.ROUND2_RUN_ID, "round2 marker")

    conn = sqlite3.connect(CATALOG)
    conn.row_factory = sqlite3.Row
    try:
        seated = repair.ensure_content_all_brands_scope(conn)
        log(seated.get("ok") is True, "scope attached", str(seated.get("assignment_id")))
        other = conn.execute(
            """
            SELECT COUNT(*) FROM org_assignment_scopes
            WHERE scope_id=? AND assignment_id!=? AND status='ACTIVE'
            """,
            (nas.CONTENT_ALL_BRANDS_SCOPE, "ASG-HAIKAL-CD-1"),
        ).fetchone()[0]
        log(other == 0, "content-all scope is only on the creative director assignment", str(other))
        targets = {
            r[0]
            for r in conn.execute(
                "SELECT target_id FROM org_scope_targets WHERE scope_id=? AND target_type='brand'",
                (nas.CONTENT_ALL_BRANDS_SCOPE,),
            )
        }
        log(targets == {b["org_brand_id"] for b in repair.REQUIRED_BRANDS}, "scope targets are the eight brands")
    finally:
        conn.close()

    s = socket.socket()
    s.settimeout(1.5)
    up8787 = s.connect_ex(("127.0.0.1", 8787)) == 0
    s.close()
    log(up8787, "production :8787 still up")
    try:
        pid8787 = subprocess.check_output(["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True).strip()
    except subprocess.CalledProcessError:
        pid8787 = ""
    log(pid8787.splitlines()[:1] == ["15975"], "production pid unchanged", pid8787.replace("\n", ","))

    js = raw.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    tmp = Path("/tmp/content-engine-haikal-round2.js")
    tmp.write_text(js, encoding="utf-8")
    syntax = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=20)
    log(syntax.returncode == 0, "board js syntax", (syntax.stderr or "OK")[:180])

    evidence: dict = {
        "run_id": repair.ROUND2_RUN_ID,
        "subject": HAIKAL,
        "person_id": "PERS-HAIKAL",
        "staff_ready": False,
        "prod_8787_pid": pid8787.splitlines()[:1],
        "gates": {},
    }
    sim_path = cf_access.SIM_JWK_PATH
    private = None
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa

        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        numbers = private.public_key().public_numbers()
        kid = "ce-haikal-round2-sim"
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
        aud = request_auth.access_audience()
        now = int(time.time())
        token = mint_jwt(
            private,
            kid=kid,
            claims={
                "iss": request_auth.team_domain(),
                "aud": aud,
                "email": HAIKAL,
                "exp": now + 600,
                "iat": now - 5,
                "sub": "ce-haikal-round2",
            },
        )
        status_code, status_body = http_json("/api/content/repair-status", token)
        # repair-status is public; identity is proved on the next calls
        log(status_body.get("round2_run_id") == repair.ROUND2_RUN_ID, "deployed round2 marker", str(status_body.get("round2_run_id")))
        log(status_body.get("staff_ready") is False, "deployed staff_ready false")

        code, reg = http_json("/api/content/brand-registry", token)
        names = [b.get("display_name") for b in (reg.get("brands") or [])]
        gate("G1", code == 200 and reg.get("all_brands") is True and all(n in names for n in NAMES) and len(names) == 8, str(names))
        h_code, habitat = http_json("/api/assets?brand=habitat", token)
        a_code, atrium = http_json("/api/assets?brand=atrium", token)
        gate(
            "G2",
            h_code == 200 and a_code == 200 and habitat.get("ok") is True and atrium.get("ok") is True,
            f"habitat={h_code} atrium={a_code}",
        )
        page_code, page_type, page_head = http_bytes("/content-2.0?brand=habitat", token)
        page = page_head.decode("utf-8", "replace") if page_type.startswith("text") else ""
        # The desk is large; fetch the full HTML for the filter markers.
        full_req = urllib.request.Request(
            "http://127.0.0.1:8788/content-2.0?brand=habitat",
            headers={"Cf-Access-Jwt-Assertion": token},
        )
        with urllib.request.urlopen(full_req, timeout=20) as resp:
            html = resp.read().decode("utf-8", "replace")
            page_code = resp.status
        gate(
            "G3",
            page_code == 200 and "This Brand" in html and "All Authorised Brands" in html and "id=\"libBrand\"" in html,
            f"page={page_code}",
        )
        conn = sqlite3.connect(CATALOG)
        conn.row_factory = sqlite3.Row
        try:
            report = repair.resolve_indexed_media(conn, scopes, limit=400)
        finally:
            conn.close()
        evidence["nas_resolve"] = report
        gate(
            "G4",
            report.get("considered", 0) > 0 and report.get("resolved_thumb", 0) > 0 and report.get("untitled") == 0 and report.get("filename_title", 0) > 0,
            str({k: report.get(k) for k in ("considered", "resolved_thumb", "filename_title", "untitled", "thumb_failed")}),
        )
        code, assets = http_json("/api/assets?brand=all", token)
        sample = assets.get("assets") or []
        image = next((a for a in sample if a.get("media_type") == "image" and str(a.get("id", "")).startswith("nas:")), None)
        video = next((a for a in sample if a.get("media_type") == "video" and str(a.get("id", "")).startswith("nas:")), None)
        image_ok = video_ok = False
        if image:
            ic, it, ib = http_bytes(str(image.get("preview_url")) + "?play=1", token)
            image_ok = ic == 200 and it.startswith("image/") and len(ib) > 32
        if video:
            vc, vt, vb = http_bytes(str(video.get("preview_url")) + "?play=1", token)
            video_ok = vc == 200 and vt.startswith("video/") and len(vb) > 32
        gate("G5", image_ok and video_ok, f"image={image_ok} video={video_ok}")
        gate(
            "G6",
            'id="libSelectAll"' in html and 'id="libDeselectAll"' in html and "/api/assets/zip" in html,
            "select, deselect, and zip controls",
        )
        gate(
            "G7",
            'id="upBrand"' in html and "fillUploadBrands" in html and "persistBrand" in html and len(names) == 8,
            "upload uses the same brand provider",
        )
        gate(
            "G8",
            "Uploading ${n + 1} of ${total} · ${pct}%" in html and "Saving to NAS" in html and "Adding to Library" in html and "✓ Complete" in html,
            "simple real status copy",
        )
        rcode, recent = http_json("/api/upload/recent?brand=habitat&data_lane=operational", token)
        items = recent.get("items") or []
        outcomes = {it.get("staff_outcome") for it in items}
        gate(
            "G9",
            rcode == 200 and (not items or "Available in Library" in outcomes or "Saving" in outcomes or "Failed" in outcomes or "Processing" in outcomes),
            f"items={len(items)} outcomes={sorted(x for x in outcomes if x)}",
        )
        wcode, whoami = http_json("/api/wolf/shell-whoami", token)
        seat = ((whoami.get("whoami") or {}).get("active_assignment") or {})
        gate(
            "G10",
            wcode == 200 and seat.get("id") == "ASG-HAIKAL-CD-1" and seat.get("role") == "ROLE-GGV-CREATIVE-DIRECTOR" and seat.get("source") == "org_assignments",
            str({k: seat.get(k) for k in ("id", "role", "label", "source")}),
        )
        evidence["brand_names"] = names
        evidence["recent_outcomes"] = sorted(x for x in outcomes if x)
        evidence["whoami_assignment"] = {k: seat.get(k) for k in ("id", "role", "label", "source")}
        _ = status_code
        _ = page
    except Exception as exc:  # noqa: BLE001
        log(False, "deployed haikal sim", str(exc)[:240])
        for key in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"):
            GATES.setdefault(key, "FAIL")
        evidence["error"] = str(exc)[:400]
    finally:
        if sim_path.is_file():
            sim_path.unlink()

    evidence["gates"] = GATES
    evidence["staff_ready"] = False
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    log(EVIDENCE.is_file() and json.loads(EVIDENCE.read_text(encoding="utf-8")).get("staff_ready") is False, "evidence written")
    log(not sim_path.is_file(), "sim public key removed")

    print("\n".join(LINES))
    print(f"PASS={PASS} FAIL={FAIL}")
    print("GATES " + " ".join(f"{k}={GATES.get(k, 'FAIL')}" for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10")))
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
