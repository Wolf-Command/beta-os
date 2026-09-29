"""Wolf assertion and the private Atrium Finance mount.

The sidecar is 127.0.0.1:8790. This module signs the hop. It does not print the secret.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from pathlib import Path

UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 8790
SECRETS_PATH = Path("/Users/wolfterminal/atrium-finance/data/beta/secrets.env")
ZAYEN_PERSON = "PERS-ZAYEN"
OWNER_PERSON = "PERS-MATT"
# Sidecar assertion string (unchanged). Wolf Core seat may be Financial Controller.
FINANCE_ROLE = "ROLE-AMG-FINANCE-OFFICER"
FINANCE_ROLE_CONTROLLER = "ROLE-AMG-FINANCIAL-CONTROLLER"
FINANCE_ROLES = frozenset({FINANCE_ROLE, FINANCE_ROLE_CONTROLLER})
OWNER_ROLE = "ROLE-OWNER"
ASSERTION_TTL = 60

_SENSITIVE_POST = (
    re.compile(r"^/api/journals/[^/]+/approve$"),
    re.compile(r"^/api/journals/[^/]+/post$"),
    re.compile(r"^/api/journals/[^/]+/reverse$"),
    re.compile(r"^/api/ap/payments$"),
    re.compile(r"^/api/tax/payment$"),
    re.compile(r"^/api/owner-pool/email-drafts/[^/]+/send$"),
    re.compile(r"^/api/owner-pool/email-all$"),
    re.compile(r"^/api/auth/login$"),
)


def is_product_path(path: str) -> bool:
    bare = (path or "").split("?", 1)[0]
    if bare.startswith("/api/"):
        return False
    if bare.rstrip("/") == "/amg/finance/lite" or bare.startswith("/amg/finance/lite/"):
        return False
    return bare == "/amg/finance" or bare.startswith("/amg/finance/")


def api_path(path: str) -> str:
    bare = (path or "").split("?", 1)[0]
    prefix = "/amg/finance/api"
    if bare.startswith(prefix):
        return "/api" + bare[len(prefix) :]
    return bare


def is_sensitive(method: str, path: str, wolf_role: str) -> bool:
    if wolf_role not in FINANCE_ROLES | {OWNER_ROLE}:
        return False
    api = api_path(path)
    # HUMFIX-1: FC may approve/reject (SoD enforced server-side). Post stays denied.
    if wolf_role == FINANCE_ROLE_CONTROLLER:
        from core import atrium_fc_authority as _fc

        if _fc.fc_may_approve_path(wolf_role, method, api):
            return False
        return _fc.still_denied_sensitive(method, api)
    if api == "/api/admin" or api.startswith("/api/admin/"):
        return True
    if "/bank" in api:
        return True
    if method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    return any(pattern.search(api) for pattern in _SENSITIVE_POST)


def load_assertion_secret() -> str:
    text = SECRETS_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("WOLF_ASSERTION_SECRET="):
            secret = line.split("=", 1)[1].strip()
            if secret:
                return secret
    raise RuntimeError("assertion secret missing")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def canonical(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def sign_assertion(
    secret: str,
    method: str,
    path: str,
    person_id: str,
    email: str,
    wolf_role: str,
    now: int | None = None,
) -> str:
    payload = {
        "email": email,
        "exp": int(now if now is not None else time.time()) + ASSERTION_TTL,
        "method": method.upper(),
        "path": path.split("?", 1)[0],
        "person_id": person_id,
        "v": 1,
        "wolf_role": wolf_role,
    }
    body = _b64url(canonical(payload).encode("utf-8"))
    sig = _b64url(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"v1.{body}.{sig}"


def seat_allowed(person_id: str, conn) -> tuple[bool, str]:
    from core import rbac

    pid = (person_id or "").strip()
    if pid == OWNER_PERSON:
        return True, OWNER_ROLE
    rows = conn.execute(
        """
        SELECT DISTINCT pos.role_id
        FROM org_assignments a
        JOIN org_positions pos ON pos.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
        """,
        (pid,),
    ).fetchall()
    roles = {str(row[0]) for row in rows if row[0]}
    if pid == ZAYEN_PERSON and (roles & FINANCE_ROLES):
        if not rbac.can(pid, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=conn):
            return False, ""
        # Prefer live FC seat; fall back to Officer string for legacy seats.
        if FINANCE_ROLE_CONTROLLER in roles:
            return True, FINANCE_ROLE_CONTROLLER
        return True, FINANCE_ROLE
    return False, ""
