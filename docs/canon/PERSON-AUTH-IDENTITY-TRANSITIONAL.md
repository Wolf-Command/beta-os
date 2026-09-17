# Person + Authentication Identity — Transitional Architecture

**Slice:** WOLF CORE — PERSON + AUTHENTICATION IDENTITY  
**Scope:** `/Users/wolfterminal/beta-os/` only  
**Date:** 2026-09-16

## Status (DESIGNED ≠ BUILT ≠ TESTED ≠ LIVE)

| Piece | Status |
| --- | --- |
| Person schema (`org_persons`) | **BUILT** |
| AuthenticationIdentity schema (`org_auth_identities`) | **BUILT** |
| Seed of 4 known Beta subjects (Matt/Amanda/Haikal/Misa) | **BUILT** |
| Transitional email → Person adapter | **TESTED** |
| Read APIs `/api/core/persons`, `/me` | **BUILT** |
| Real authentication (CF JWT → Person bind) | **BUILT** (see `REAL-AUTH-BINDING-TRANSITIONAL.md`) |
| CF JWT verification (JWKS + iss + required aud) | **BUILT+TESTED** (fixtures); LIVE pending AUD |
| Role / Position / Assignment / RBAC / Authority | **BUILT** (separate slices; access control NOT LIVE) |
| LIVE for staff trust of identity | **NO** — AUD operator step + LIVE gate pending |

## Principle

A human is **not** an email address.

- `person_id` is stable (e.g. `PERS-MATT`)
- Email is an `org_auth_identities` row (`provider=email`, `identifier=…`)
- Changing email must not destroy Person history

## DEVELOPMENT_IDENTITY_ASSERTION

Only when `BETA_AUTH_MODE=development_assertion` is **explicitly** set:

- `X-Wolf-Subject`
- JSON `subject` / `actor`
- query `subject`
- UI optional switcher (dev mode only)

Honest name: `resolve_development_identity_assertion()`  
Normal mode (`cloudflare_access`, including when mode unset) **ignores** those channels and requires a verified `Cf-Access-Jwt-Assertion`.

`/api/core/me` returns:

- `identity_assurance: "cloudflare_access_verified"` when JWT verified
- `identity_assurance: "development_assertion"` in explicit dev mode
- `real_authentication: true` only for verified Cloudflare path

## Known security blocker (updated)

Impersonation via subject headers is closed in normal mode. Remaining for LIVE: Matt must set `BETA_CF_ACCESS_AUD` and confirm tunnel → origin JWT path. Unknown verified emails are denied (no auto Person).

## Migration

- `scripts/migrations/006_person_auth_identity.sql`
- `scripts/migrations/migrate_person_auth_identity.py`
