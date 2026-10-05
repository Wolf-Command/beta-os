# NOTE — CF JWT session tooling for Zayen browser residual

`2026-10-01T11:25:00+08:00` · Peaches · **INTERNAL prep only** · no invent LIVE · no widen access

## Purpose
Support human item **ZAYEN-CF-BROWSER-ENTITY-ISOLATION-UI** without claiming LIVE or opening Prod.

## Honest constraints
- Beta :8788 fail-closed without `Cf-Access-Jwt-Assertion` (403 missing_auth) — expected.
- Server-side entity isolation already **CLOSED REPAIRED+VERIFIED** (50/50).
- This note does **not** mint tokens, scrape cookies, or bypass CF Access.
- Human uses real CF Access login as zayen@ (or Owner-approved test identity mapped to PERS-ZAYEN).

## Prove checklist (human)
1. CF Access login → Beta shell as Zayen.
2. Nav / open `/amg/finance` → YES.
3. Nav / open `/bzg/finance` → YES.
4. Attempt `/ggv/finance` (direct URL + nav) → **DENY** / absent.
5. Capture screenshots; set matrix_pass only after human sign-off.

## Non-claims
staff_ready=false until broader bar · does not alone set human_commissioned · no architecture reopen unless regression.
