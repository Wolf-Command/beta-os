#!/usr/bin/env python3
"""Single request-identity entry for Beta serve_beta.

Modes (env BETA_AUTH_MODE):
  cloudflare_access      — default when unset; fail-closed JWT → Person
  development_assertion  — only if explicitly set; spoofable subject channels

Never trusts Cf-Access-Authenticated-User-Email alone.
Never auto-creates Persons for unknown emails.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from core import audit as _audit
from core import cf_access
from core import identity as _identity

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_ENV_PATH = BETA_ROOT / ".env"

AUTH_MODE_CLOUDFLARE = "cloudflare_access"
AUTH_MODE_DEVELOPMENT = "development_assertion"

_ENV_LOADED = False


def _load_auth_env(path: Path | None = None) -> None:
    """Load beta-os/.env into os.environ for unset keys only."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = path or DEFAULT_ENV_PATH
    try:
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and (key not in os.environ or not (os.environ.get(key) or "").strip()):
                    os.environ[key] = val
    except OSError:
        pass
    _ENV_LOADED = True


def auth_mode() -> str:
    """Return active auth mode. Default = cloudflare_access (fail-closed)."""
    _load_auth_env()
    raw = (os.environ.get("BETA_AUTH_MODE") or "").strip()
    if raw == AUTH_MODE_DEVELOPMENT:
        return AUTH_MODE_DEVELOPMENT
    # Unset, empty, or any other value → normal fail-closed mode
    return AUTH_MODE_CLOUDFLARE


def is_development_assertion_mode() -> bool:
    return auth_mode() == AUTH_MODE_DEVELOPMENT


def team_domain() -> str:
    _load_auth_env()
    raw = (os.environ.get("BETA_CF_ACCESS_TEAM_DOMAIN") or "").strip()
    return cf_access._norm_domain(raw) if raw else cf_access.DEFAULT_TEAM_DOMAIN


def access_audience() -> str:
    _load_auth_env()
    return (os.environ.get("BETA_CF_ACCESS_AUD") or "").strip()


def _headers_dict(handler) -> dict[str, str]:
    if isinstance(handler, dict):
        return {str(k): str(v) for k, v in (handler.get("headers") or {}).items()}
    return {k: v for k, v in getattr(handler, "headers", {}).items()}


def _body_dict(handler, body: dict | None) -> dict:
    if body is not None and isinstance(body, dict):
        return body
    if isinstance(handler, dict):
        b = handler.get("body")
        return b if isinstance(b, dict) else {}
    cached = getattr(handler, "_wolf_body_cache", None)
    return cached if isinstance(cached, dict) else {}


def _query_subject(handler) -> str | None:
    if isinstance(handler, dict):
        qs = handler.get("query") or {}
        if isinstance(qs, dict):
            v = qs.get("subject")
            if isinstance(v, list):
                v = v[0] if v else None
            return (str(v).strip() if v else None) or None
        return None
    path = getattr(handler, "path", "") or ""
    qs = parse_qs(urlparse(path).query)
    return ((qs.get("subject") or [""])[0] or "").strip() or None


def _correlation_id(handler) -> str:
    if isinstance(handler, dict):
        existing = handler.get("correlation_id")
        if existing:
            return str(existing)
        cid = _audit.mint_correlation_id()
        handler["correlation_id"] = cid
        return cid
    existing = getattr(handler, "_wolf_correlation_id", None)
    if existing:
        return str(existing)
    cid = _audit.mint_correlation_id()
    try:
        setattr(handler, "_wolf_correlation_id", cid)
    except Exception:  # noqa: BLE001
        pass
    return cid


def _audit_auth_denied(
    handler,
    *,
    error: str,
    identity_assurance: str,
    source: str = "request_auth",
) -> None:
    """Integration #2: protected auth failure → SYSTEM DENIED (never store JWT)."""
    _audit.safe_record(
        action="auth.resolve",
        result="DENIED",
        source=source,
        actor_type="SYSTEM",
        identity_assurance=identity_assurance or _identity.IDENTITY_ASSURANCE_NONE,
        reason_code=error,
        correlation_id=_correlation_id(handler),
        metadata={"error": error, "auth_mode": auth_mode()},
    )


def _audit_auth_succeeded(handler, identity: dict[str, Any]) -> None:
    """Integration #1: verified auth resolution → PERSON SUCCEEDED."""
    person_id = identity.get("person_id")
    if not person_id:
        return
    _audit.safe_record(
        action="auth.resolve",
        result="SUCCEEDED",
        source="request_auth",
        actor_type="PERSON",
        verified_person_id=person_id,
        actor_person_id=person_id,
        actor_auth_identity_id=identity.get("auth_identity_id"),
        identity_assurance=identity.get("identity_assurance"),
        correlation_id=_correlation_id(handler),
        metadata={
            "auth_mode": identity.get("auth_mode") or auth_mode(),
        },
    )


def _deny(
    *,
    error: str,
    message: str,
    identity_assurance: str = _identity.IDENTITY_ASSURANCE_NONE,
    real_authentication: bool = False,
    extra: dict | None = None,
    handler=None,
    audit: bool = True,
    audit_source: str = "request_auth",
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": False,
        "error": error,
        "message": message,
        "identity_assurance": identity_assurance,
        "real_authentication": real_authentication,
        "person_id": None,
        "email": None,
        "permission_subject": None,
        "person": None,
        "auth_identity_id": None,
    }
    if extra:
        out.update(extra)
    if audit and handler is not None:
        _audit_auth_denied(
            handler,
            error=error,
            identity_assurance=identity_assurance,
            source=audit_source,
        )
    return out


def resolve_request_identity(
    handler, body: dict | None = None, *, emit_audit: bool = True
) -> dict[str, Any]:
    """Resolve caller identity for protected Beta routes.

    cloudflare_access: JWT only; ignore client subject channels.
    development_assertion: X-Wolf-Subject / JSON subject / query subject.
    Set emit_audit=False for optional identity probes (e.g. post-commit audit attach).
    """
    mode = auth_mode()
    headers = _headers_dict(handler)

    if mode == AUTH_MODE_CLOUDFLARE:
        aud = access_audience()
        if not aud:
            return _deny(
                error="auth_misconfigured",
                message=(
                    "BETA_CF_ACCESS_AUD is required when BETA_AUTH_MODE=cloudflare_access. "
                    "Copy Application Audience (AUD) from Zero Trust → Access → Applications."
                ),
                identity_assurance=_identity.IDENTITY_ASSURANCE_NONE,
                real_authentication=False,
                handler=handler,
                audit=emit_audit,
            )
        token = cf_access.token_from_headers(headers)
        if not token:
            return _deny(
                error="missing_auth",
                message=(
                    "Cf-Access-Jwt-Assertion required. "
                    "Local :8788 without Cloudflare JWT is denied (fail-closed)."
                ),
                identity_assurance=_identity.IDENTITY_ASSURANCE_NONE,
                real_authentication=False,
                handler=handler,
                audit=emit_audit,
                audit_source="cf_access",
            )
        claims = cf_access.verify_access_jwt(
            token, team_domain=team_domain(), audience=aud
        )
        if not claims:
            return _deny(
                error="invalid_token",
                message="Cloudflare Access JWT failed cryptographic verification.",
                identity_assurance=_identity.IDENTITY_ASSURANCE_NONE,
                real_authentication=False,
                handler=handler,
                audit=emit_audit,
                audit_source="cf_access",
            )
        email = cf_access.email_from_claims(claims)
        if not email:
            return _deny(
                error="invalid_token",
                message="Verified JWT has no usable email claim.",
                identity_assurance=_identity.IDENTITY_ASSURANCE_NONE,
                real_authentication=False,
                handler=handler,
                audit=emit_audit,
                audit_source="cf_access",
            )
        bound = _identity.resolve_verified_person(email)
        if not bound.get("ok"):
            return _deny(
                error=bound.get("error") or "unknown_identity",
                message=bound.get("message") or "Identity not authorised.",
                identity_assurance=_identity.IDENTITY_ASSURANCE_CLOUDFLARE,
                real_authentication=True,
                extra={
                    "email": email,
                    "permission_subject": email,
                    "note": bound.get("note"),
                },
                handler=handler,
                audit=emit_audit,
            )
        identity = {
            "ok": True,
            "error": None,
            "message": None,
            "identity_assurance": _identity.IDENTITY_ASSURANCE_CLOUDFLARE,
            "real_authentication": True,
            "person_id": bound["person_id"],
            "email": email,
            "permission_subject": email,
            "person": bound.get("person"),
            "auth_identity_id": bound.get("auth_identity_id"),
            "auth_mode": mode,
            "note": (
                "Cloudflare Access JWT verified (JWKS + iss + aud + exp). "
                "Client subject headers/body/query ignored."
            ),
        }
        if emit_audit:
            _audit_auth_succeeded(handler, identity)
        return identity

    # development_assertion — explicit env only
    body_d = _body_dict(handler, body)
    asserted = None
    for k, v in headers.items():
        if k.lower() == "x-wolf-subject":
            asserted = (v or "").strip() or None
            break
    if not asserted:
        asserted = (body_d.get("subject") or body_d.get("actor") or "").strip() or None
    if not asserted:
        asserted = _query_subject(handler)
    if not asserted:
        return _deny(
            error="missing_subject",
            message=(
                "Provide X-Wolf-Subject header or JSON/query subject email "
                "(DEVELOPMENT_IDENTITY_ASSERTION only)."
            ),
            identity_assurance=_identity.IDENTITY_ASSURANCE_NONE,
            real_authentication=False,
            extra={"auth_mode": mode},
            handler=handler,
            audit=emit_audit,
        )
    me = _identity.resolve_from_development_assertion(asserted)
    identity = {
        "ok": True,
        "error": None,
        "message": None,
        "identity_assurance": me.get("identity_assurance"),
        "real_authentication": False,
        "person_id": me.get("person_id"),
        "email": me.get("asserted_identifier"),
        "permission_subject": me.get("asserted_identifier"),
        "person": me.get("person"),
        "auth_identity_id": me.get("auth_identity_id"),
        "asserted_identifier": me.get("asserted_identifier"),
        "auth_mode": mode,
        "note": me.get("note"),
    }
    if emit_audit:
        _audit_auth_succeeded(handler, identity)
    return identity


def auth_mode_payload() -> dict[str, Any]:
    mode = auth_mode()
    return {
        "ok": True,
        "auth_mode": mode,
        "development_assertion_allowed": mode == AUTH_MODE_DEVELOPMENT,
        "cloudflare_aud_configured": bool(access_audience()),
        "team_domain": team_domain(),
        "identity_assurance_default": (
            _identity.IDENTITY_ASSURANCE_DEVELOPMENT
            if mode == AUTH_MODE_DEVELOPMENT
            else _identity.IDENTITY_ASSURANCE_NONE
        ),
        "note": (
            "Normal Beta is cloudflare_access fail-closed. "
            "development_assertion only when BETA_AUTH_MODE is explicitly set."
        ),
    }
