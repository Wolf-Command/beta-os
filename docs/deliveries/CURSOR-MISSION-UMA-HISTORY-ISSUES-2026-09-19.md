# Cursor mission — Uma history + issues read models (P4)

Date: 19 September 2026
Workspace: /Users/wolfterminal/beta-os
Surface: Beta only. Restart only with `python3 scripts/beta_restart.py` if live :8788 must pick up handler changes.
Do not touch Production :8787.

## Goal

After petty `99d0970`, make **History** and **Issues** honest operator read models for Uma Blu ops: audit spine actually receives Uma transitions, History panel shows human lines, Issues includes petty attention — without inventing a second history store or new domains.

## Current truth (do not break)

- Ops + petty live: `/bzg`, `/bzg/uma-blu`, `/bills`, `/issues`, `/petty`, `/uma-blu-close` 200 on Beta.
- `list_history` reads `audit.list_events` for entity `ENT-BZG` source `uma_ops_console` (+ venue_close). Live catalog currently has **0** rows for that source — History UI shows empty.
- `list_issues` already surfaces PR POLICY_REQUIRED fixtures; petty POLICY_REQUIRED / open-tin may be missing from Issues.
- Honesty: `petty_cash_page=BUILT`, `float=NOT_FOUND`, `payment_execution=NOT_BUILT`, `authority_limits_invented=false`.
- Opening float stays NOT FOUND. Devi not in org_persons. Zayen ledger out of scope.
- `test_uma_ops_console.py`, `test_uma_petty_cash.py`, `test_uma_blu_daily_close.py` must stay green.

## Build

1. **Audit emit gaps**
   - Ensure PR transitions and petty movements / count / day-state changes that are operator-visible call `audit.record_event` with source `uma_ops_console` (match existing `AUDIT_SOURCE` / entity constants).
   - No second history table. No silent rewrite of past events.
2. **History read model**
   - Keep `/api/bzg/uma-blu/history` as the spine projection; human sentences only.
   - Tests must create ≥1 transition and assert History returns a non-empty human line (not engineering ids as the primary label).
   - Today History panel already fetches the API — fix empty root cause; do not invent a parallel widget store.
3. **Issues read model**
   - Issues include petty attention: POLICY_REQUIRED day-tin / open uncounted when present (same quiet rules as Today — omit when clean).
   - Keep PR policy / unpaid-claim classes. No invented thresholds.
4. **Honesty**
   - Do not flip float to OK. Do not invent authority limits. Do not claim payment_execution BUILT.
5. **Fixtures**
   - Prefer ephemeral test fixtures. Prefer 0 new live non-example rows on the real catalog. Label examples Example.
6. **Restart**
   - If serve handlers change, one `python3 scripts/beta_restart.py`. Never touch :8787.

## Do not

- Invent float, variance threshold, cashier, Devi seat, or any IDR authority limit.
- Write ESB, ClickUp, Telegram, bank, Metricool, Klaviyo, Sheets.
- Edit Model C ledger / credits / CAP maturity / Progress dashboard.
- Stage dirty WIP: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py`.
- `git add .` or reset the tree.
- Open Finance / Venues / Procurement / People surfaces.

## Tests

Extend `scripts/tests/test_uma_ops_console.py` and/or `test_uma_petty_cash.py` (keep both + daily close green):

- Transition → audit row with source `uma_ops_console`.
- History API returns human line after that transition.
- Issues lists petty POLICY_REQUIRED when fixture forces it; quiet when clean.
- Forbidden write-helper scan still clean.
- Existing suites PASS.

Run:

```bash
python3 scripts/tests/test_uma_ops_console.py
python3 scripts/tests/test_uma_petty_cash.py
python3 scripts/tests/test_uma_blu_daily_close.py
```

## Git

One bounded commit. Message: `fix: Uma Blu history and issues read models`

## Done line

Print exactly:

COMMIT: <hash>
TESTS: PASS=<n> FAIL=<n>
ROUTES: /bzg/uma-blu /api/bzg/uma-blu/history /api/bzg/uma-blu/issues
SYSTEM: unchanged
EXIT:0
CURSOR_DONE
