#!/usr/bin/env python3
"""Factory authenticated-Beta harness (no Matt Cloudflare session).

Mints a short-lived RS256 JWT that live Beta accepts via the commissioning
simulation public JWK (`state/commissioning/cf-sim-public.jwk.json`), the same
path Content Engine Haikal round-2 used. Private key never leaves this process.
Public JWK is installed only for the prove window, then removed.

Matt = HUMAN COMMISSIONING only. This harness is for factory READY proofs against
deployed Beta (:8788 origin). It does NOT declare HUMAN READY / staff_ready.
Isolated-copy proves alone are never enough for READY.

Never prints tokens or process command lines. Never touches Production :8787.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import cf_access  # noqa: E402
from core import request_auth  # noqa: E402

ORIGIN = os.environ.get("BF_BETA_ORIGIN", "http://127.0.0.1:8788").rstrip("/")
KID = "bf-factory-auth-harness"
DEFAULT_EMAIL = "deviputu236@gmail.com"  # PERS-DEVI · ROLE-BZG-CLOSER
DEFAULT_TTL = 900


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


@contextmanager
def authenticated_session(
    email: str = DEFAULT_EMAIL,
    *,
    ttl_secs: int = DEFAULT_TTL,
    origin: str = ORIGIN,
) -> Iterator[dict[str, Any]]:
    """Yield {origin, email, headers, get, post, cleanup}. Removes sim JWK on exit."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    if request_auth.auth_mode() != request_auth.AUTH_MODE_CLOUDFLARE:
        # Still works if someone flipped mode; harness always speaks CF JWT.
        pass
    aud = request_auth.access_audience()
    if not aud:
        raise RuntimeError("BETA_CF_ACCESS_AUD unset — cannot mint Access JWT for deployed Beta")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": KID,
        "n": _b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
    }
    sim_path = cf_access.SIM_JWK_PATH
    sim_path.parent.mkdir(parents=True, exist_ok=True)
    prior = sim_path.read_text(encoding="utf-8") if sim_path.is_file() else None
    sim_path.write_text(json.dumps(jwk), encoding="utf-8")
    now = int(time.time())
    token = mint_jwt(
        private,
        kid=KID,
        claims={
            "iss": request_auth.team_domain(),
            "aud": aud,
            "email": email,
            "exp": now + int(ttl_secs),
            "iat": now - 5,
            "sub": f"bf-harness:{email}",
        },
    )
    headers = {
        "Cf-Access-Jwt-Assertion": token,
        "Accept": "application/json",
    }

    def _req(method: str, path: str, body: dict | None = None, extra: dict | None = None) -> tuple[int, bytes, str]:
        url = origin + path
        data = None
        hdrs = dict(headers)
        if extra:
            hdrs.update(extra)
        if body is not None:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read(), resp.headers.get("Content-Type") or ""
        except urllib.error.HTTPError as e:
            return e.code, e.read() or b"", e.headers.get("Content-Type") if e.headers else ""

    def get(path: str, **kw):
        return _req("GET", path, **kw)

    def post(path: str, body: dict | None = None, **kw):
        return _req("POST", path, body=body, **kw)

    try:
        yield {
            "origin": origin,
            "email": email,
            "headers": headers,  # for Playwright extra_http_headers; never log token
            "headers_no_token_meta": {"has_cf_jwt": True, "email": email},
            "get": get,
            "post": post,
            "human_commissioning_only": True,
            "staff_ready": False,
            "declares_human_ready": False,
        }
    finally:
        try:
            if prior is None:
                if sim_path.is_file():
                    sim_path.unlink()
            else:
                sim_path.write_text(prior, encoding="utf-8")
        except OSError:
            pass


def smoke_identity(email: str = DEFAULT_EMAIL) -> dict[str, Any]:
    """Prove deployed Beta accepts the harness JWT for this person. No UI."""
    with authenticated_session(email) as sess:
        code, raw, _ = sess["get"]("/api/core/auth-mode")
        mode = {}
        try:
            mode = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            mode = {}
        # Hit a gated close surface: 200/302 HTML or JSON identity, not 401/403 missing_auth
        code2, raw2, ctype = sess["get"]("/uma-blu-close", extra={"Accept": "text/html"})
        out = {
            "ok": code == 200 and code2 in (200, 302) or (code2 == 200),
            "auth_mode_http": code,
            "auth_mode": mode.get("auth_mode"),
            "gated_close_http": code2,
            "gated_close_ctype": (ctype or "")[:40],
            "email": email,
            "origin": sess["origin"],
            "staff_ready": False,
            "human_ready_declared": False,
        }
        # Prefer: not unauthenticated
        out["ok"] = bool(mode.get("auth_mode") == "cloudflare_access" and code2 not in (401, 403))
        # 403 can still mean seated deny — check body
        if code2 == 403:
            blob = (raw2 or b"").decode("utf-8", "replace")[:300].lower()
            out["ok"] = "missing_auth" not in blob and "cf-access-jwt" not in blob
            out["forbidden_body_snip"] = blob[:120]
        return out


if __name__ == "__main__":
    email = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL).strip()
    result = smoke_identity(email)
    # Never echo token material
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result.get("ok") else 1)
