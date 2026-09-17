# Real Authentication Binding — Transitional (Beta)

**Slice:** WOLF CORE — REAL AUTH BINDING (Cloudflare Access JWT → Person)  
**Scope:** `/Users/wolfterminal/beta-os/` only  
**Date:** 2026-09-17  
**Branch:** `build/wolf-command-rebuild`

## Status (DESIGNED ≠ BUILT ≠ TESTED ≠ LIVE)

| Piece | Status |
| --- | --- |
| `core.cf_access` JWKS + RS256 verify (iss + **required aud** + exp + iat) | **BUILT** |
| `core.request_auth` single entry for serve | **BUILT** |
| Bind verified email → AuthIdentity → Person (no auto-create) | **BUILT** |
| Fail-closed default `BETA_AUTH_MODE=cloudflare_access` (incl. local :8788) | **BUILT** |
| Explicit `development_assertion` mode | **BUILT** |
| Unit tests with local RSA JWT fixtures | **TESTED** (see `scripts/tests/test_real_auth_binding.py`) |
| `BETA_CF_ACCESS_AUD` configured in live `.env` | **OPERATOR** (Matt copies AUD tag) |
| Access control LIVE for staff trust | **NO** — binding built; full LIVE gate still pending Matt AUD + tunnel verify |
| Onboarding UI / password / SSO / MFA / RBAC admin | **NOT BUILT** (out of slice) |

## Honesty labels

| `identity_assurance` | meaning |
| --- | --- |
| `cloudflare_access_verified` | JWT verified cryptographically; Person bound |
| `development_assertion` | Explicit `BETA_AUTH_MODE=development_assertion` only |
| `none` | Missing/invalid auth or misconfigured AUD |

`real_authentication: true` only when assurance is `cloudflare_access_verified`.

## Rules (Matt)

- Do **not** trust `Cf-Access-Authenticated-User-Email` alone.
- Verify `Cf-Access-Jwt-Assertion` with JWKS + iss + **required** aud + exp.
- Do **not** auto-create Persons for unknown verified emails (`unknown_identity`).
- Client `X-Wolf-Subject` / JSON `subject` / query `subject` / `localStorage` **cannot** override a verified JWT.
- Local `:8788` without JWT is **denied** in normal mode (no localhost shortcut).

## Env

```
BETA_AUTH_MODE=cloudflare_access          # default when unset
BETA_CF_ACCESS_TEAM_DOMAIN=https://wolfcommand.cloudflareaccess.com
BETA_CF_ACCESS_AUD=<AUD tag from Zero Trust → Access → Applications → beta>
```

AUD: Cloudflare Zero Trust → Access → Applications → app protecting `beta.wolfcommand.net` → **Application Audience (AUD) Tag**.

## NOT LIVE

Staff must not treat Beta as production-authenticated until AUD is set, tunnel path is verified end-to-end, and Peaches/Matt accept the LIVE gate. Content Machine mutations remain usable for authorised identities when JWT binds correctly, or under explicit development_assertion for local tests.
