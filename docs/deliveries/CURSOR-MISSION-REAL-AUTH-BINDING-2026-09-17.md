# CURSOR MISSION — WOLF CORE REAL AUTHENTICATION BINDING

**Grok planned:** YES (17 Sep 2026 against HEAD `f7d1874`)
**Peaches:** Governor only — no application coding by Peaches Shell.
**Implementer:** Cursor Local Agent on Wolfs-Mac-Studio
**Repo:** `/Users/wolfterminal/beta-os/`
**Branch:** `build/wolf-command-rebuild` (start CLEAN)
**Commit:** `feat(core): bind verified Cloudflare identity`
**No remote. No merge to main. No Production. No onboarding UI. No password/SSO/MFA. No RBAC/Authority admin. No delegation/SoD.**

## Evidence Grok already verified (do not guess)

### What Beta gets today
- Tunnel: `beta.wolfcommand.net` → `http://127.0.0.1:8788` (cloudflared config).
- Origin currently uses **DEVELOPMENT_IDENTITY_ASSERTION**: `X-Wolf-Subject` / JSON `subject` / query `subject` / UI `localStorage` (`content-2.0.html`). Spoofable.
- Team domain JWKS reachable: `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/certs` (HTTP 200, 2 keys).
- Cloudflare docs (Validate JWTs): identity token header = `Cf-Access-Jwt-Assertion`; verify with JWKS at `{TEAM_DOMAIN}/cdn-cgi/access/certs`; validate **issuer** + **audience (AUD)** + signature + expiry; email from JWT claims (`email`). Prefer header JWT over cookie. Do **not** trust unsigned email headers alone.

### Prod wolf-system pattern (READ-ONLY reference — improve, do not copy blindly)
- Module `access_identity.email_from_access_jwt` verifies RS256 JWT via JWKS, issuer `*.cloudflareaccess.com`, optional aud.
- **Defect vs Matt rule:** prod also trusts `Cf-Access-Authenticated-User-Email` *before* JWT. **Beta must NOT** — Matt requires cryptographic verification. Treat bare email header as **untrusted noise** in `cloudflare_access` mode.
- Prod often leaves `access_aud` empty (aud verify off). **Beta must REQUIRE aud** in normal mode.

### AUD tag
Application Audience for the Access app that protects `beta.wolfcommand.net` was **not** found in Beta `.env` / repo.
- Implement against env `BETA_CF_ACCESS_AUD` (required when `BETA_AUTH_MODE=cloudflare_access`).
- Team domain env `BETA_CF_ACCESS_TEAM_DOMAIN` defaulting to `https://wolfcommand.cloudflareaccess.com`.
- Document in `.env.example` + transitional canon how Matt copies AUD from Zero Trust → Access → Applications → beta → Application Audience (AUD) Tag.
- Unit tests MUST mint local RS256 JWTs with a **test keypair** (do not need live CF tokens for CI).

## Preflight (print evidence)

```
hostname; whoami; pwd; git branch --show-current; git rev-parse HEAD; git status --short
```

Read: BUILD-READ-ME-FIRST, Software-First, Beta Sacred, Local Cursor Build Path, PERSON-AUTH-IDENTITY-TRANSITIONAL, RBAC + Authority transitional, this mission, current `serve_beta.py` `_require_permission` / `/api/core/me*`, `content-2.0.html` subject switcher.

## Auth modes

Env `BETA_AUTH_MODE`:

| value | when |
|-------|------|
| `cloudflare_access` | **Normal Beta default** when mode unset OR explicitly set. Fail-closed. |
| `development_assertion` | **Only** if explicitly set. For automated local tests. |

Rules:
- If mode is `cloudflare_access` and `BETA_CF_ACCESS_AUD` empty → protected routes DENY (`auth_misconfigured`), never fall back to subject assertion.
- Development mode must be **impossible accidentally**: only explicit env string match; never inferred from localhost alone.
- Responses/diagnostics must set:
  - `identity_assurance = cloudflare_access_verified` when JWT verified
  - `identity_assurance = development_assertion` when in explicit dev mode
  - `identity_assurance = none` / error otherwise
- **Never** allow header/body/query/localStorage to override a verified identity.

## Module design

### `scripts/core/cf_access.py` (new)
- `verify_access_jwt(token, *, team_domain, audience) -> dict|None`
  - Fetch JWKS from `{team_domain}/cdn-cgi/access/certs` (cache TTL ~10m)
  - Verify RS256 signature, `exp`, `iat`, `iss==team_domain`, `aud==audience` (**required**)
  - Extract email via claims `email` (and documented fallbacks only if present in CF docs: identity/custom.email — already used in prod module)
  - Fail-closed on any fault; never log token
- Do **not** accept cookies as primary (`CF_Authorization` optional fallback only if header absent — CF docs say prefer header; either OK if same JWT verify path; **prefer header only** to match Matt + CF guidance)
- Do **not** trust `Cf-Access-Authenticated-User-Email` as proof

### Extend `scripts/core/identity.py`
- `IDENTITY_ASSURANCE_CLOUDFLARE = "cloudflare_access_verified"`
- `resolve_verified_person(email) ->` AuthIdentity(provider email/cloudflare) → Person; inactive identity/person → deny payload
- Unknown verified email → **not** auto-create Person; return onboarding/not-authorised (`unknown_identity`)
- Keep `resolve_from_development_assertion` for DEV mode only

### `scripts/core/request_auth.py` (new) — single entry for serve
`resolve_request_identity(handler) -> dict`:
1. Read `BETA_AUTH_MODE`
2. If `cloudflare_access`: require verified JWT → email → Person; ignore all client subject channels
3. If `development_assertion`: allow X-Wolf-Subject / JSON subject / query subject (existing), label honestly
4. Return `{ok, person_id, email, identity_assurance, real_authentication, error, ...}`

Wire `serve_beta.py`:
- Replace `_require_permission` / `/api/core/me*` identity resolution to use `resolve_request_identity`
- Protected first: `/api/core/me`, `/api/core/me/assignments`, `/api/core/me/scopes`, `/api/core/me/permissions`, `/api/core/me/authority-limits`, `/api/core/authority/check`, and Content Machine **mutations** that currently use `_require_permission` (upload, plan create/edit/approve, etc.)
- Remove paths where query/body subject overrides verified identity on those routes
- Static HTML may still load; APIs fail closed

### UI (`dashboards/content-2.0.html` and any other Beta subject switcher)
- Normal mode: **remove/disable** user-select / localStorage identity switcher; derive identity from `/api/core/me` (no pretend-Haikal)
- Dev mode only: optional switcher if `identity_assurance==development_assertion` from a small `/api/core/auth-mode` or me payload flag
- Stop sending `X-Wolf-Subject` in normal mode

## Local :8788 bypass (required red-team fix)

Beta binds `127.0.0.1:8788`. A local process can hit origin without Cloudflare.
**Application layer must still DENY** protected APIs without verified JWT when `BETA_AUTH_MODE=cloudflare_access`.
No “localhost = trusted” shortcut.

## Config / docs
- Update `.env.example` with `BETA_AUTH_MODE`, `BETA_CF_ACCESS_TEAM_DOMAIN`, `BETA_CF_ACCESS_AUD`
- Add `docs/canon/REAL-AUTH-BINDING-TRANSITIONAL.md` (honesty labels + NOT LIVE)
- Update Master_Build.csv honestly per Matt §13
- Backup Beta DB only if schema migration needed (prefer **no** schema change — binding uses existing Person/AuthIdentity). If you add columns, backup + SHA-256.

## Tests — `scripts/tests/test_real_auth_binding.py`

Mint RS256 JWTs with ephemeral test keys; stub JWKS fetch to test keys.

Mandatory cases from Matt §10–11:
- valid JWT → correct Person
- invalid signature / expired / wrong aud / wrong iss → DENY
- missing auth → DENY
- verified unknown email → DENY/onboarding (no auto Person)
- inactive AuthIdentity / inactive Person → DENY
- X-Wolf-Subject / JSON subject / query subject **cannot override** verified JWT
- Matt cannot become Amanda via client data
- correct Assignment/Scope/RBAC after bind
- RBAC ok but Authority exceed still denied (call within_authority)
- development mode only when env explicit
- normal mode never falls back to assertion if AUD missing or JWT missing
- local :8788 without JWT denied in cloudflare mode
- no Production writes; Content Machine still usable for authorised identities in both modes (dev tests)

Also keep existing RBAC/Authority tests green (they may set `BETA_AUTH_MODE=development_assertion`).

## Commit when green
`feat(core): bind verified Cloudflare identity` — one bounded commit, tree CLEAN.

Print evidence: hostname, mode defaults, test summary, whether `BETA_CF_ACCESS_AUD` is set in live `.env` (yes/no only — never print value), files changed.

STOP.
