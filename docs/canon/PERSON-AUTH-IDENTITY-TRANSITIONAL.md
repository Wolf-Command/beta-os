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
| Real authentication (CF JWT / SSO) | **NOT BUILT** |
| CF JWT verification | **NOT BUILT** |
| Role / Position / Assignment / RBAC / Authority | **NOT BUILT** |
| LIVE for staff trust of identity | **NO** |

## Principle

A human is **not** an email address.

- `person_id` is stable (e.g. `PERS-MATT`)
- Email is an `org_auth_identities` row (`provider=email`, `identifier=…`)
- Changing email must not destroy Person history

## DEVELOPMENT_IDENTITY_ASSERTION

Beta still resolves callers via spoofable:

- `X-Wolf-Subject`
- JSON `subject` / `actor`
- query `subject`
- UI `localStorage`

Honest name: `resolve_development_identity_assertion()`  
Legacy alias: `resolve_authenticated_subject()` (does **not** mean authenticated)

`/api/core/me` returns:

- `identity_assurance: "development_assertion"`
- `real_authentication: false`

## Transitional Content Machine adapter

`permissions.subject` remains email.

Adapter: email → AuthIdentity → Person via `core.identity.resolve_person_from_email`.

Permission checks are **unchanged** (still email grants). Future RBAC will hang off Person/Assignment.

## Known security blocker

Beta impersonation remains possible until real authentication is built. This slice does **not** claim that solved.

## Migration

- `scripts/migrations/006_person_auth_identity.sql`
- `scripts/migrations/migrate_person_auth_identity.py`
