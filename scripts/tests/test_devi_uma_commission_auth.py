#!/usr/bin/env python3
"""Devi Uma commission auth gate — Beta only.

Fail-closed /api/bzg/uma-blu/* : no identity or no SCOPE-BZG-UMA → 403.
Devi + SCOPE-BZG-UMA → 200 on allowed reads.
No payment approve, closer submit, float invent, or Progress for Devi.
Does not mark HUMAN COMMISSIONED. Does not touch :8787.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
TEAM = "https://wolfcommand.cloudflareaccess.com"
AUD = "test-audience-devi-uma-auth"
KID = "test-kid-devi-uma"

DEVI = "deviputu236@gmail.com"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"

READS = (
    "/api/bzg/uma-blu/today",
    "/api/bzg/uma-blu/prs",
    "/api/bzg/uma-blu/issues",
    "/api/bzg/uma-blu/history",
    "/api/bzg/uma-blu/honesty",
    "/api/bzg/uma-blu/petty",
)

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


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def mint_rsa_pair():
    from cryptography.hazmat.primitives.asymmetric import rsa

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private, private.public_key()


def public_jwk(public_key, kid: str) -> dict:
    numbers = public_key.public_numbers()
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _b64url(n),
        "e": _b64url(e),
    }


def mint_jwt(private_key, *, kid: str, claims: dict) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    h_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    sig = private_key.sign(signing_input, PKCS1v15(), hashes.SHA256())
    return f"{h_b64}.{p_b64}.{_b64url(sig)}"


def base_claims(email: str) -> dict:
    now = int(time.time())
    return {
        "iss": TEAM,
        "aud": AUD,
        "email": email,
        "exp": now + 3600,
        "iat": now - 10,
        "sub": "test-sub-" + email.split("@", 1)[0],
    }


def main() -> int:
    os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
    os.environ["BETA_CF_ACCESS_TEAM_DOMAIN"] = TEAM
    os.environ["BETA_CF_ACCESS_AUD"] = AUD

    import core.cf_access as cf
    import core.request_auth as ra
    import serve_beta as sb

    ra._ENV_LOADED = True
    priv, pub = mint_rsa_pair()
    jwks = {"keys": [public_jwk(pub, KID)]}
    cf.clear_jwks_cache()
    cf.set_jwks_fetcher_for_tests(lambda _domain: jwks)

    devi_tok = mint_jwt(priv, kid=KID, claims=base_claims(DEVI))
    matt_tok = mint_jwt(priv, kid=KID, claims=base_claims(MATT))
    amanda_tok = mint_jwt(priv, kid=KID, claims=base_claims(AMANDA))

    conn = sqlite3.connect(str(LIVE_DB))
    conn.row_factory = sqlite3.Row
    try:
        active = [
            r["scope_id"]
            for r in conn.execute(
                """
                SELECT scope_id FROM org_assignment_scopes
                WHERE assignment_id='ASG-DEVI-HFB-UMA-1' AND status='ACTIVE'
                """
            )
        ]
        check("Devi ACTIVE scope is only SCOPE-BZG-UMA", active == ["SCOPE-BZG-UMA"], str(active))
        closer_n = conn.execute(
            """
            SELECT COUNT(*) FROM org_assignments a
            JOIN org_positions p ON p.position_id=a.position_id
            WHERE p.role_id='ROLE-BZG-CLOSER' AND a.status='ACTIVE'
            """
        ).fetchone()[0]
        check("ROLE-BZG-CLOSER has 0 people", closer_n == 0, str(closer_n))
        hfb = {
            r[0]
            for r in conn.execute(
                """
                SELECT p.code FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id=rp.permission_id
                WHERE rp.role_id='ROLE-BZG-HFB' AND rp.effect='ALLOW'
                """
            )
        }
        check("HFB has venue.close.read", "venue.close.read" in hfb)
        check("HFB has work.read", "work.read" in hfb)
        check("HFB lacks venue.close.submit", "venue.close.submit" not in hfb)
        check("HFB lacks payment_approve", "bzg.pr.payment_approve" not in hfb)
        matt_uma = conn.execute(
            """
            SELECT 1 FROM org_assignments a
            JOIN org_assignment_scopes s ON s.assignment_id=a.assignment_id
            WHERE a.person_id='PERS-MATT' AND a.status='ACTIVE' AND a.end_at IS NULL
              AND s.scope_id='SCOPE-BZG-UMA' AND s.status='ACTIVE' AND s.end_at IS NULL
            """
        ).fetchone()
        check("Matt also holds SCOPE-BZG-UMA", matt_uma is not None)
    finally:
        conn.close()

    serve_text = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("gate calls _resolve_identity path via _require_permission", "_require_uma_ops" in serve_text)
    check("does not invent payment_approve grant", "GRANT bzg.pr.payment_approve" not in serve_text)
    check(
        "no HUMAN COMMISSIONED mark in gate",
        "HUMAN COMMISSIONED" not in serve_text.split("def _require_uma_ops", 1)[-1][:800],
    )

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        print(f"\n{PASS} passed, {FAIL} failed")
        return 1

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def call(path: str, headers: dict | None = None, payload: dict | None = None):
        data = None
        hdrs = dict(headers or {})
        method = "GET"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
            method = "POST"
        req = Request(f"http://127.0.0.1:{port}{path}", data=data, headers=hdrs, method=method)
        try:
            with urlopen(req, timeout=8) as resp:
                return resp.status, json.loads(resp.read().decode())
        except HTTPError as exc:
            raw = exc.read().decode()
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {"raw": raw[:300]}
            return exc.code, body

    try:
        st, body = call("/api/bzg/uma-blu/today")
        check(
            "no identity today 403",
            st == 403 and body.get("ok") is False,
            f"{st} {body.get('error')}",
        )
        st, body = call("/api/bzg/uma-blu/petty", payload={"amount": 1})
        check("no identity petty POST 403", st == 403, f"{st} {body.get('error')}")

        amanda_h = {"Cf-Access-Jwt-Assertion": amanda_tok}
        st, body = call("/api/bzg/uma-blu/today", headers=amanda_h)
        check(
            "Amanda no Uma scope 403",
            st == 403 and body.get("error") == "forbidden",
            f"{st} {body.get('error')} {body.get('message')}",
        )

        devi_h = {"Cf-Access-Jwt-Assertion": devi_tok}
        for path in READS:
            st, body = call(path, headers=devi_h)
            check(
                f"Devi {path} 200",
                st == 200 and body.get("ok") is True,
                f"{st} {str(body)[:180]}",
            )

        matt_h = {"Cf-Access-Jwt-Assertion": matt_tok}
        st, body = call("/api/bzg/uma-blu/honesty", headers=matt_h)
        check(
            "Matt with SCOPE-BZG-UMA honesty 200",
            st == 200 and body.get("ok") is True,
            f"{st} {str(body)[:180]}",
        )

        real_scopes = sb._scope.list_active_scopes_for_person

        def _scopes_without_uma(person_id, conn=None):
            rows = real_scopes(person_id, conn=conn)
            if person_id == "PERS-DEVI":
                return [
                    r
                    for r in rows
                    if r.get("scope_id") not in ("SCOPE-BZG-UMA", "SCOPE-BZG-FB")
                ]
            return rows

        sb._scope.list_active_scopes_for_person = _scopes_without_uma
        try:
            st, body = call("/api/bzg/uma-blu/today", headers=devi_h)
            check(
                "Devi without SCOPE-BZG-UMA 403",
                st == 403 and body.get("required_scope") == "SCOPE-BZG-UMA",
                f"{st} {body.get('error')} {body.get('message')}",
            )
        finally:
            sb._scope.list_active_scopes_for_person = real_scopes

        st, body = call("/api/bzg/uma-blu/pay", headers=devi_h, payload={"amount": 1})
        check(
            "Devi payment route 403",
            st == 403 and body.get("error") == "forbidden",
            f"{st} {body.get('error')}",
        )
        st, body = call("/api/bzg/uma-blu/float", headers=devi_h, payload={"opening_float": 100})
        check("Devi float invent route 403", st == 403, f"{st} {body.get('error')}")

        st, body = call("/api/venue-close/capabilities", headers=devi_h)
        can = body.get("can") or {}
        check(
            "Devi close submit allowed and verify denied",
            st == 200 and can.get("submit") is True and can.get("verify") is False,
            f"{st} submit={can.get('submit')} verify={can.get('verify')} {body.get('error')}",
        )
        check(
            "Devi payment_approve still denied",
            can.get("payment_approve") is False,
            str(can.get("payment_approve")),
        )

        st, body = call("/api/progress", headers=devi_h)
        check(
            "Devi Progress 403",
            st == 403 and body.get("person_id") == "PERS-DEVI",
            f"{st} {body.get('error')} {body.get('person_id')}",
        )
        st, body = call("/api/progress/honesty", headers=devi_h)
        check("Devi Progress honesty 403", st == 403, f"{st} {body.get('error')}")
    finally:
        httpd.shutdown()
        cf.set_jwks_fetcher_for_tests(None)

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
