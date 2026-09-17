# GROK REVIEW — Uma Blu Daily Close + Exception Handover

**Commit:** `909954d7748122f9725f8687e3c46d5eda75cd30`  
**Parent:** `3f9a8381f8d96b1d5cdf537a429ea61a7be7b967`  
**Run:** BF-uma-blu-daily-close-20260917  
**Slice:** BZG — Uma Blu Daily Close + Exception Handover  
**Reviewer:** Grok (build-factory)  
**Date:** 2026-09-17 (Asia/Makassar / WITA)

## Verdict

**PASS_WITH_NITS**

In-scope behaviour matches approved plan/mission. Honesty flags correct. No invented thresholds. No Devi hardcode. No ESB writes. Habitat untouched. No Production paths. Mandatory cases covered by `scripts/tests/test_uma_blu_daily_close.py` (62 passed, 0 failed on Mac Studio re-run during review). Nits below do not block ship.

## Scope check

| Gate | Result |
|------|--------|
| Uma Blu (`BZG-UMA`) only | **PASS** — entity/brand constants + UNIQUE(entity, brand, date); no other venues |
| Beta only / no Production | **PASS** — `venue_close.db_connect` refuses `wolf-system`, `/Production`, `money.sqlite`; ESB path refuses Production/money |
| No ESB writes | **PASS** — `esb_close_snapshot` opens `mode=ro`; test asserts warehouse mtime unchanged |
| Habitat untouched | **PASS** — no Habitat paths in `909954d`; migrate refuses if `content_planner` count changes; tests prove live planner unchanged (6→6) |
| No invented variance thresholds | **PASS** — `venue_close_variance_policies` live count 0; non-zero variance → `VARIANCE_REQUIRES_POLICY` (never ACCEPT) |
| Live monetary authority unchanged | **PASS** — migrate + tests: `org_authority_limits` stays 0 |
| Client cannot submit expected totals / variance / state | **PASS** — `_venue_close_refuse_overrides` on open/capture/declare/reconcile; core APIs do not accept client state/totals |
| No `if Devi` hardcode | **PASS** — HFB via `find_hfb_assignee` role/assignment/scope; static scan for `== "PERS-DEVI"` clean |
| SoD closer/resolver ≠ sole verifier | **PASS** — `verify_close` raises `sod_self_verify` when verifier == resolver; tested |
| ROLE-BZG-CLOSER 0 assignments | **PASS** — position seeded, closer active assignments = 0, commissioning WAITING |
| PERS-DEVI + AUTH email | **PASS** — `deviputu236@gmail.com` (HR-authorised), ROLE-BZG-HFB + SCOPE-BZG-UMA |

Approved scope respected. Out-of-scope (POS, Alchemist, ClickUp, other venues, Habitat publish, ESB writes, Production) not touched.

## Honesty flags verified

| Flag | Expected | Observed |
|------|----------|----------|
| `settlement_api` | `UNAVAILABLE` | **OK** — module constant + `honesty_flags()` + UI display + canon |
| `esb_cash_basis` | `PAYMENT_LINES_NOT_SETTLEMENT` | **OK** — payment-line sum labelled `ESB_CASH_FROM_PAYMENTS` / not settlement |
| `live_variance_threshold` | `0` | **OK** — live DB count 0; reconcile never ACCEPT without policy |
| `live_monetary_authority` | `0` | **OK** — unchanged at 0 |

Canon `docs/canon/UMA-BLU-DAILY-CLOSE.md` matches implementation.

## Mandatory cases covered

Re-ran `python3 scripts/tests/test_uma_blu_daily_close.py` → **62 passed, 0 failed**.

Covered:
- Empty / incomplete ESB day blocks capture (`esb_empty_day`)
- Idempotent open by (entity, brand, date)
- ESB fingerprint + cash_from_payments from payment lines
- Declared cash → `EVIDENCE_SUBMITTED`; not auto-verified
- Variance 0 + fresh fingerprint → system `VERIFIED_CLOSED`
- Non-zero variance → `VARIANCE_REQUIRES_POLICY` (never ACCEPT)
- Exception WI owned by HFB assignee via role (PERS-DEVI found by role, not hardcode)
- SoD self-verify denied; Matt can verify
- Stale fingerprint blocks reconcile
- Client override refusal wired in serve_beta
- Live honesty counts 0; Habitat slots unchanged; ESB mtime unchanged
- Closer WAITING (0 live assignments)

## Findings

1. **Severity:** low (nit) · **In-scope?** yes (correctness caution) · **Title:** Empty `branchCode` bills included in BLZ snapshot  
   **Detail:** `esb_close_snapshot.snapshot_day` skips only when `branchCode` is present and ≠ `BLZ`. Missing/blank `branchCode` is accepted into Uma totals. Fine if warehouse rows are always tagged; fail-closed would be safer for a shared warehouse.  
   **Fix hint:** Prefer `if bc != branch: continue` (require explicit BLZ), or treat blank branch as incomplete.

2. **Severity:** low (nit) · **In-scope?** yes (plan RBAC list) · **Title:** HFB grants omit `venue.close.submit`  
   **Detail:** Plan Devi RBAC listed `close_submit` + resolve + verify. Migration grants HFB read/resolve/verify (not submit); submit sits on `ROLE-BZG-CLOSER` (0 people) + `ROLE-MATT`. Matches WAITING closer commissioning and still works via Matt, but diverges from the written Devi submit grant.  
   **Fix hint:** Either add `PERM-VENUE-CLOSE-SUBMIT` to `HFB_GRANTS`, or amend canon/plan to say HFB is exception-path only.

3. **Severity:** low (nit) · **In-scope?** yes · **Title:** `RECONCILED` state never assigned  
   **Detail:** Schema + transition allow `RECONCILED`; clean path comment says “RECONCILED then VERIFIED_CLOSED” but code jumps straight to `VERIFIED_CLOSED`. Honesty of SUBMITTED ≠ RECONCILED ≠ VERIFIED still holds via `EVIDENCE_SUBMITTED` vs `VERIFIED_CLOSED`.  
   **Fix hint:** Either set `RECONCILED` briefly then verify, or drop `RECONCILED` from allowed states/docs.

4. **Severity:** low (nit) · **In-scope?** yes · **Title:** Dead second SoD check in `verify_close`  
   **Detail:** `sod_self_close` branch requires `resolver == verified`, which already raised `sod_self_verify`. Closer≠resolver self-verify path is not additionally blocked (plan: “where practical”; primary SoD is satisfied).  
   **Fix hint:** Block `submitter == verified` on exception path independently, or delete dead branch.

5. **Severity:** low (nit) · **In-scope?** yes · **Title:** Override refuse incomplete on exception/resolve/verify  
   **Detail:** `open`/`capture`/`declare-cash`/`reconcile` refuse client `state`/totals/variance; exception/resolve/verify do not. Core ignores those keys, so no override succeeds.  
   **Fix hint:** Call `_venue_close_refuse_overrides` on remaining POST handlers for defence in depth.

6. **Severity:** low (nit) · **In-scope?** yes (test honesty) · **Title:** Tautology assertion in tests  
   **Detail:** `check("never ACCEPT without policy", rec["state"] != "RECONCILED" or True)` is always true. Real coverage is the prior `VARIANCE_REQUIRES_POLICY` assert.  
   **Fix hint:** Assert `rec["state"] == "VARIANCE_REQUIRES_POLICY"` only (drop `or True`).

None of the above are ship-blocking honesty or scope violations.

## Evidence of what was read

**Inputs**
- `docs/deliveries/GROK-PLAN-UMA-BLU-DAILY-CLOSE-2026-09-17.md`
- `docs/deliveries/CURSOR-MISSION-UMA-BLU-DAILY-CLOSE-2026-09-17.md`
- `docs/canon/UMA-BLU-DAILY-CLOSE.md`

**Commit**
- `git show --stat 909954d` — 15 files, +3592; parent ancestor check vs `3f9a838` OK
- Full/partial review of:
  - `scripts/core/venue_close.py`
  - `scripts/core/esb_close_snapshot.py`
  - `scripts/migrations/021_uma_blu_daily_close.sql`
  - `scripts/migrations/migrate_uma_blu_daily_close.py`
  - `scripts/tests/test_uma_blu_daily_close.py`
  - `scripts/serve_beta.py` venue-close routes (+319 lines; no Habitat hunks)
  - `dashboards/uma-blu-close.html`
  - `scripts/core/evidence.py` (`brand_id` passthrough only)

**Habitat in 909954d:** **no** (confirmed via `--name-only` + serve_beta hunk scan).

**Tests:** `python3 scripts/tests/test_uma_blu_daily_close.py` → 62 passed, 0 failed (WITA 2026-09-17 ~15:53).
