#!/usr/bin/env python3
"""Real auth binding — Cloudflare Access JWT → Person (Beta). CLAIMED ≠ VERIFIED.

Uses ephemeral RSA keypair + stubbed JWKS. No live CF tokens required.
Does not write Production / wolf-system.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import sys
import tempfile
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
AUD = "test-audience-beta-aud-tag"
KID = "test-kid-1"

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
UNKNOWN = "unknown.verified@example.com"


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
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

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


def base_claims(**overrides) -> dict:
    now = int(time.time())
    c = {
        "iss": TEAM,
        "aud": AUD,
        "email": MATT,
        "exp": now + 3600,
        "iat": now - 10,
        "sub": "test-sub",
    }
    c.update(overrides)
    return c


def main() -> int:
    # Isolate env for this process
    os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
    os.environ["BETA_CF_ACCESS_TEAM_DOMAIN"] = TEAM
    os.environ["BETA_CF_ACCESS_AUD"] = AUD
    # Force reload of request_auth env flag
    import core.request_auth as ra
    import core.cf_access as cf
    import core.identity as ident
    from core import rbac as rb
    from core import authority as auth
    import wolf_intelligence as wi

    ra._ENV_LOADED = True  # skip .env overwrite of our test env
    priv, pub = mint_rsa_pair()
    jwks = {"keys": [public_jwk(pub, KID)]}
    cf.clear_jwks_cache()
    cf.set_jwks_fetcher_for_tests(lambda _domain: jwks)

    # --- Unit: valid JWT → Person ---
    tok = mint_jwt(priv, kid=KID, claims=base_claims())
    claims = cf.verify_access_jwt(tok, team_domain=TEAM, audience=AUD)
    check("valid JWT verifies", claims is not None and claims.get("email") == MATT)
    bound = ident.resolve_verified_person(MATT)
    check("valid email → PERS-MATT", bound.get("ok") is True and bound.get("person_id") == "PERS-MATT")

    # --- Invalid signature / expired / wrong aud / wrong iss ---
    bad_priv, _ = mint_rsa_pair()
    bad_sig = mint_jwt(bad_priv, kid=KID, claims=base_claims())
    check("invalid signature DENY", cf.verify_access_jwt(bad_sig, team_domain=TEAM, audience=AUD) is None)

    expired = mint_jwt(priv, kid=KID, claims=base_claims(exp=int(time.time()) - 60))
    check("expired DENY", cf.verify_access_jwt(expired, team_domain=TEAM, audience=AUD) is None)

    wrong_aud = mint_jwt(priv, kid=KID, claims=base_claims(aud="other-aud"))
    check("wrong aud DENY", cf.verify_access_jwt(wrong_aud, team_domain=TEAM, audience=AUD) is None)

    wrong_iss = mint_jwt(
        priv, kid=KID, claims=base_claims(iss="https://evil.cloudflareaccess.com")
    )
    check("wrong iss DENY", cf.verify_access_jwt(wrong_iss, team_domain=TEAM, audience=AUD) is None)

    # --- Missing auth / misconfigured AUD ---
    missing = ra.resolve_request_identity({"headers": {}, "body": {}})
    check("missing JWT DENY", missing.get("ok") is False and missing.get("error") == "missing_auth")

    os.environ.pop("BETA_CF_ACCESS_AUD", None)
    ra._ENV_LOADED = True
    mis = ra.resolve_request_identity(
        {"headers": {"Cf-Access-Jwt-Assertion": tok}, "body": {}}
    )
    check(
        "missing AUD → auth_misconfigured",
        mis.get("ok") is False and mis.get("error") == "auth_misconfigured",
    )
    os.environ["BETA_CF_ACCESS_AUD"] = AUD

    # --- Unknown verified email — no auto Person ---
    unk_tok = mint_jwt(priv, kid=KID, claims=base_claims(email=UNKNOWN))
    unk = ra.resolve_request_identity(
        {"headers": {"Cf-Access-Jwt-Assertion": unk_tok}, "body": {}}
    )
    check(
        "unknown verified email DENY",
        unk.get("ok") is False and unk.get("error") == "unknown_identity",
    )
    before = sqlite3.connect(str(LIVE_DB)).execute(
        "SELECT COUNT(*) FROM org_persons"
    ).fetchone()[0]
    after = sqlite3.connect(str(LIVE_DB)).execute(
        "SELECT COUNT(*) FROM org_persons"
    ).fetchone()[0]
    check("no auto-create Person", before == after)

    # --- Inactive AuthIdentity / Person ---
    td = tempfile.mkdtemp(prefix="auth-bind-")
    try:
        tmp_db = Path(td) / "t.sqlite"
        tmp_db.write_bytes(LIVE_DB.read_bytes())
        conn = sqlite3.connect(str(tmp_db))
        conn.execute(
            "UPDATE org_auth_identities SET status='INACTIVE' WHERE auth_identity_id='AUTH-MATT-EMAIL'"
        )
        conn.commit()
        inactive_id = ident.resolve_verified_person(MATT, conn=conn)
        check(
            "inactive AuthIdentity DENY",
            inactive_id.get("ok") is False and inactive_id.get("error") == "inactive_identity",
        )
        conn.execute(
            "UPDATE org_auth_identities SET status='ACTIVE' WHERE auth_identity_id='AUTH-MATT-EMAIL'"
        )
        conn.execute("UPDATE org_persons SET status='INACTIVE' WHERE person_id='PERS-MATT'")
        conn.commit()
        inactive_p = ident.resolve_verified_person(MATT, conn=conn)
        check(
            "inactive Person DENY",
            inactive_p.get("ok") is False and inactive_p.get("error") == "inactive_person",
        )
        conn.close()
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)

    # --- Client subject cannot override verified JWT ---
    matt_tok = mint_jwt(priv, kid=KID, claims=base_claims(email=MATT))
    spoof = ra.resolve_request_identity(
        {
            "headers": {
                "Cf-Access-Jwt-Assertion": matt_tok,
                "X-Wolf-Subject": AMANDA,
                "Cf-Access-Authenticated-User-Email": AMANDA,
            },
            "body": {"subject": AMANDA},
            "query": {"subject": [AMANDA]},
        }
    )
    check("JWT wins over X-Wolf-Subject", spoof.get("ok") is True and spoof.get("person_id") == "PERS-MATT")
    check("JWT wins over JSON subject", spoof.get("email") == MATT)
    check(
        "bare email header not trusted as override",
        spoof.get("person_id") == "PERS-MATT" and spoof.get("identity_assurance")
        == ident.IDENTITY_ASSURANCE_CLOUDFLARE,
    )

    # Matt cannot become Amanda via client data
    check("Matt≠Amanda via client", spoof.get("person_id") != "PERS-AMANDA")

    # --- Assignments / scopes / RBAC after bind ---
    check(
        "assurance cloudflare_access_verified",
        spoof.get("identity_assurance") == "cloudflare_access_verified",
    )
    check("real_authentication true", spoof.get("real_authentication") is True)
    tgt = rb.default_content_target()
    check("Matt RBAC approve after bind", rb.can("PERS-MATT", "content.plan.approve", tgt))
    from core import staffing as st
    from core import scope as sc

    asgs = st.list_active_assignments_for_person("PERS-MATT")
    check("Matt has assignment", len(asgs) >= 1)
    scopes = sc.list_active_scopes_for_person("PERS-MATT")
    check("Matt has scope", len(scopes) >= 1)

    # RBAC ok but Authority exceed still denied (live seeded limits = 0 → deny)
    dec = auth.within_authority(
        "PERS-MATT",
        "content.plan.approve",
        tgt,
        {"amount": 100, "currency": "IDR"},
    )
    check(
        "authority still denies without limit (RBAC≠authority)",
        dec.get("allowed") is False,
        str(dec.get("reason")),
    )

    # --- development mode only when explicit ---
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    ra._ENV_LOADED = True
    check("explicit development mode", ra.auth_mode() == "development_assertion")
    dev = ra.resolve_request_identity(
        {"headers": {"X-Wolf-Subject": MATT}, "body": {}}
    )
    check(
        "dev assertion works when explicit",
        dev.get("ok") is True
        and dev.get("identity_assurance") == "development_assertion"
        and dev.get("real_authentication") is False,
    )

    os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
    # localhost must NOT imply development
    os.environ.pop("BETA_AUTH_MODE", None)
    ra._ENV_LOADED = True
    check(
        "unset mode defaults cloudflare_access",
        ra.auth_mode() == "cloudflare_access",
    )
    os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
    os.environ["BETA_CF_ACCESS_AUD"] = AUD
    ra._ENV_LOADED = True

    # bare email header alone is not enough
    email_only = ra.resolve_request_identity(
        {"headers": {"Cf-Access-Authenticated-User-Email": MATT}, "body": {}}
    )
    check(
        "email header alone DENY",
        email_only.get("ok") is False and email_only.get("error") == "missing_auth",
    )

    # never fall back to assertion if JWT missing
    no_jwt = ra.resolve_request_identity(
        {"headers": {"X-Wolf-Subject": MATT}, "body": {"subject": MATT}}
    )
    check(
        "cloudflare mode ignores subject assertion",
        no_jwt.get("ok") is False and no_jwt.get("error") == "missing_auth",
    )

    # --- HTTP API: local :8788 style without JWT denied ---
    try:
        import serve_beta as sb
        import inspect

        Handler = None
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
        check("API handler found", Handler is not None)
        if Handler:
            if hasattr(sb, "ensure_schema"):
                sb.ensure_schema()
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:

                def call(path, headers=None):
                    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})
                    try:
                        with urlopen(req, timeout=8) as r:
                            return r.status, json.loads(r.read().decode())
                    except HTTPError as e:
                        body = e.read().decode()
                        try:
                            data = json.loads(body)
                        except Exception:
                            data = {"raw": body}
                        return e.code, data

                st_code, data = call("/api/core/me")
                check(
                    "local origin without JWT DENY",
                    st_code == 403 and data.get("error") in ("missing_auth", "auth_misconfigured"),
                    str(data.get("error")),
                )

                st_code, data = call(
                    "/api/core/me",
                    headers={"X-Wolf-Subject": MATT},
                )
                check(
                    "X-Wolf-Subject alone DENY in CF mode",
                    st_code == 403 and data.get("error") == "missing_auth",
                )

                st_code, data = call(
                    "/api/core/me",
                    headers={"Cf-Access-Jwt-Assertion": matt_tok},
                )
                check("valid JWT /me 200", st_code == 200 and data.get("ok") is True)
                check("valid JWT person Matt", data.get("person_id") == "PERS-MATT")
                check(
                    "valid JWT assurance",
                    data.get("identity_assurance") == "cloudflare_access_verified",
                )

                # cannot override via query
                st_code, data = call(
                    f"/api/core/me?subject={AMANDA}",
                    headers={
                        "Cf-Access-Jwt-Assertion": matt_tok,
                        "X-Wolf-Subject": AMANDA,
                    },
                )
                check(
                    "query subject cannot become Amanda",
                    st_code == 200 and data.get("person_id") == "PERS-MATT",
                )

                st_code, data = call("/api/core/me/permissions", headers={"Cf-Access-Jwt-Assertion": matt_tok})
                check(
                    "me/permissions after bind",
                    st_code == 200 and "content.plan.approve" in (data.get("permissions") or []),
                )

                st_code, data = call(
                    "/api/core/authority/check?permission_code=content.plan.approve&amount=100&currency=IDR",
                    headers={"Cf-Access-Jwt-Assertion": matt_tok},
                )
                check("authority/check via JWT", st_code == 200 and data.get("ok") is True)
                check(
                    "authority exceed/deny still works",
                    (data.get("decision") or {}).get("allowed") is False,
                )

                # Content Machine mutation gate still works for authorised identity
                st_code, data = call(
                    "/api/core/auth-mode",
                )
                check(
                    "auth-mode endpoint",
                    st_code == 200 and data.get("auth_mode") == "cloudflare_access",
                )

                # development mode API
                os.environ["BETA_AUTH_MODE"] = "development_assertion"
                ra._ENV_LOADED = True
                st_code, data = call(
                    "/api/core/me",
                    headers={"X-Wolf-Subject": AMANDA},
                )
                check(
                    "dev mode Amanda via assertion",
                    st_code == 200
                    and data.get("person_id") == "PERS-AMANDA"
                    and data.get("identity_assurance") == "development_assertion",
                )
                # restore CF mode for cleanup
                os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
                ra._ENV_LOADED = True
            finally:
                httpd.shutdown()
    except Exception as e:
        check("API smoke", False, repr(e))

    # Content Machine has_permission still works (email path) in both conceptual modes
    check(
        "CM has_permission Matt still works",
        wi.has_permission(MATT, "can_approve_plan") is True,
    )
    check(
        "CM has_permission Amanda create",
        wi.has_permission(AMANDA, "can_create_plan") is True,
    )

    # No production path references in new modules
    cf_src = (SCRIPTS / "core" / "cf_access.py").read_text(encoding="utf-8")
    ra_src = (SCRIPTS / "core" / "request_auth.py").read_text(encoding="utf-8")
    check("cf_access never trusts email header as proof", "UNTRUSTED_EMAIL_HEADER" in cf_src)
    check("request_auth has no wolf-system path", "wolf-system" not in ra_src)
    check("no Production write in modules", "Production" not in cf_src and "/money.sqlite" not in ra_src)

    cf.set_jwks_fetcher_for_tests(None)
    cf.clear_jwks_cache()

    print()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
