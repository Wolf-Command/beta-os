#!/usr/bin/env python3
"""Cloudflare Access JWT verification for Beta (fail-closed).

Verifies Cf-Access-Jwt-Assertion cryptographically via JWKS.
Does NOT trust Cf-Access-Authenticated-User-Email.
Does NOT accept cookies as a primary path (header only).
Never logs the token.
"""
from __future__ import annotations

import base64
import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable

DEFAULT_TEAM_DOMAIN = "https://wolfcommand.cloudflareaccess.com"
JWKS_TTL_SECONDS = 600
JWT_HEADER = "Cf-Access-Jwt-Assertion"
# Explicitly untrusted — never use as proof of identity
UNTRUSTED_EMAIL_HEADER = "Cf-Access-Authenticated-User-Email"

_LOCK = threading.Lock()
_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
# Test hook: (team_domain) -> JWKS dict | None
_JWKS_FETCHER: Callable[[str], dict[str, Any] | None] | None = None


def set_jwks_fetcher_for_tests(fetcher: Callable[[str], dict[str, Any] | None] | None) -> None:
    """Replace network JWKS fetch (unit tests only). Pass None to restore."""
    global _JWKS_FETCHER
    _JWKS_FETCHER = fetcher


def clear_jwks_cache() -> None:
    with _LOCK:
        _JWKS_CACHE.clear()


def _norm_domain(domain: str) -> str:
    return str(domain or "").strip().rstrip("/")


def _b64url_decode(part: str) -> bytes:
    raw = part.encode("ascii") if isinstance(part, str) else part
    raw += b"=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw)


def _b64url_json(part: str) -> dict[str, Any]:
    return json.loads(_b64url_decode(part).decode("utf-8"))


def _ok_team_domain(domain: str) -> bool:
    d = _norm_domain(domain)
    if not d.startswith("https://"):
        return False
    host = d.split("://", 1)[-1].split("/")[0].lower()
    return host.endswith(".cloudflareaccess.com") and host.count(".") >= 2


def email_from_claims(payload: dict[str, Any] | None) -> str | None:
    """Extract email from CF Access JWT claims (documented fallbacks only)."""
    if not isinstance(payload, dict):
        return None
    for key in ("email", "identity"):
        val = payload.get(key)
        if isinstance(val, dict):
            val = val.get("email")
        email = str(val or "").strip().lower()
        if email and "@" in email:
            return email
    custom = payload.get("custom")
    if isinstance(custom, dict):
        email = str(custom.get("email") or "").strip().lower()
        if email and "@" in email:
            return email
    return None


def _fetch_jwks(team_domain: str) -> dict[str, Any] | None:
    domain = _norm_domain(team_domain)
    if not _ok_team_domain(domain):
        return None
    now = time.time()
    with _LOCK:
        hit = _JWKS_CACHE.get(domain)
        if hit and (now - hit[0]) < JWKS_TTL_SECONDS:
            return hit[1]

    data: dict[str, Any] | None = None
    if _JWKS_FETCHER is not None:
        try:
            data = _JWKS_FETCHER(domain)
        except Exception:
            return None
    else:
        url = domain + "/cdn-cgi/access/certs"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                parsed = json.loads(resp.read().decode("utf-8", "replace"))
            if isinstance(parsed, dict):
                data = parsed
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            OSError,
            json.JSONDecodeError,
        ):
            return None

    if not isinstance(data, dict) or not data.get("keys"):
        return None
    with _LOCK:
        _JWKS_CACHE[domain] = (now, data)
    return data


def _rsa_public_from_jwk(jwk: dict[str, Any]):
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

    if jwk.get("kty") != "RSA" or not jwk.get("n") or not jwk.get("e"):
        return None
    n = int.from_bytes(_b64url_decode(jwk["n"]), "big")
    e = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    return RSAPublicNumbers(e, n).public_key()


def _aud_matches(claim_aud: Any, required: str) -> bool:
    req = str(required or "").strip()
    if not req:
        return False
    if isinstance(claim_aud, str):
        return claim_aud.strip() == req
    if isinstance(claim_aud, (list, tuple)):
        return any(str(a).strip() == req for a in claim_aud)
    return False


def verify_access_jwt(
    token: str | None,
    *,
    team_domain: str,
    audience: str,
) -> dict[str, Any] | None:
    """Verify RS256 Access JWT. Returns claims dict or None (fail-closed).

    Requires: signature, exp, iat, iss==team_domain, aud==audience (required).
    Never logs the token.
    """
    raw = str(token or "").strip()
    if not raw or raw.count(".") != 2:
        return None
    if "\n" in raw or " " in raw:
        return None
    audience = str(audience or "").strip()
    if not audience:
        return None
    domain = _norm_domain(team_domain)
    if not _ok_team_domain(domain):
        return None

    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

        h_b64, p_b64, s_b64 = raw.split(".")
        header = _b64url_json(h_b64)
        payload = _b64url_json(p_b64)
    except Exception:
        return None

    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None
    if header.get("alg") != "RS256":
        return None

    jwks = _fetch_jwks(domain)
    if not jwks:
        return None
    kid = header.get("kid")
    pub = None
    keys = [j for j in (jwks.get("keys") or []) if isinstance(j, dict)]
    if kid:
        for jwk in keys:
            if jwk.get("kid") == kid:
                pub = _rsa_public_from_jwk(jwk)
                break
    else:
        for jwk in keys:
            pub = _rsa_public_from_jwk(jwk)
            if pub is not None:
                break
    if pub is None:
        return None

    try:
        sig = _b64url_decode(s_b64)
        pub.verify(
            sig,
            (h_b64 + "." + p_b64).encode("ascii"),
            PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception:
        return None

    try:
        now = int(time.time())
        exp = int(payload.get("exp"))
        iat = int(payload.get("iat"))
    except (TypeError, ValueError):
        return None
    if exp <= now:
        return None
    if iat > now + 30:
        return None

    iss = _norm_domain(str(payload.get("iss") or ""))
    if iss != domain:
        return None
    if not _aud_matches(payload.get("aud"), audience):
        return None

    if not email_from_claims(payload):
        return None
    return payload


def token_from_headers(headers: dict | None) -> str | None:
    """Prefer Cf-Access-Jwt-Assertion header only (no cookie path)."""
    if not headers:
        return None
    for k, v in headers.items():
        if str(k).lower() == JWT_HEADER.lower():
            tok = str(v or "").strip()
            return tok or None
    return None
