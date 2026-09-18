# Cursor mission — Uma Today / petty cash / daily close (P3)

Date: 18 September 2026
Workspace: /Users/wolfterminal/beta-os
Surface: Beta only. Restart only with `python3 scripts/beta_restart.py` after routes land.
Do not touch Production :8787.

## Goal

Complete the next Uma Blu ops vertical after `db93583`: real **Petty cash** surface wired into **Today**, with **Daily close** still the existing close page (link only). Do not rebuild `venue_close.py`. Do not invent an opening float.

## Current truth (do not break)

- BZG / Uma shells + Today + bills + issues + honesty APIs exist (`scripts/core/uma_ops_console.py`, dashboards `bzg*.html`).
- Daily close lives at `/uma-blu-close` (`venue_close.py`). Link it. Do not fork.
- Live Beta already serves `/bzg` `/bzg/uma-blu` `/uma-blu-close` 200.
- Honesty today: `float=NOT_IN_SLICE`, `petty_cash_page=NOT_IN_SLICE`.
- Opening float baseline is **NOT FOUND** in authorised discovery. Missing float is a gap, not permission to invent one.
- Devi is not in Beta `org_persons`. Do not insert her. Do not invent a cashier person id.
- Zayen owns ledger / CoA / tax / bank accounting. Out of scope.
- `scripts/tests/test_uma_ops_console.py` and `scripts/tests/test_uma_blu_daily_close.py` must stay green.

## Build

1. **Petty cash page** at `/bzg/uma-blu/petty` → `dashboards/bzg-uma-blu-petty.html`.
   - Same Wolf chrome / Uma nav as Today.
   - Replace every nav `Petty cash — later` disabled span with a real link on Uma pages.
2. **Operational petty record** in Beta catalog (new tables OK).
   - Movements only: business_date, direction (OUT/IN), amount, currency as given (blank if missing — never guess), purpose, example flag, work_item_id link, evidence_id optional.
   - States for a day-tin summary: `OPEN` / `COUNTED` / `VARIANCE_NOTED` / `CLOSED_CLAIMED` — or quieter equivalent. Do not invent a variance threshold. If count ≠ expected and no policy row exists, surface `POLICY_REQUIRED` / blocked honesty — never invent a limit number.
   - Opening float field: store only if provided by fixture/input. If absent, honesty and UI must say **NOT FOUND** / unavailable — never default to 0 as if known.
3. **API**
   - `GET /api/bzg/uma-blu/petty` — list + honesty.
   - Optional thin POST for fixture/demo movement under test mode only if needed for proves. No ESB/ClickUp/Telegram/bank write helpers.
4. **Today**
   - Add a quiet card when petty has open / policy-required / uncounted items. Omit when clean.
   - Keep existing PR + daily-close cards.
5. **Honesty**
   - Flip `petty_cash_page` to `BUILT`.
   - Keep `float` as `NOT_FOUND` (or equivalent) until a real float is authorised — never `OK` with a made-up number.
   - Keep `payment_execution=NOT_BUILT`, `authority_limits_invented=false`.
6. **Fixtures**
   - ≤3 example petty movements labelled Example. Prefer 0 live rows after migrate on the real catalog.
7. **Restart**
   - After code lands, run `python3 scripts/beta_restart.py` once so `/bzg/uma-blu/petty` paints on :8788. Do not touch :8787.

## Do not

- Invent float, variance threshold, cashier, Devi seat, or IDR 5M (or any) authority limit.
- Call or import `wolf-system/scripts/bzg-petty-cash.py` as a live writer.
- Write ESB, ClickUp, Telegram, bank, Metricool, Klaviyo, Sheets.
- Edit Model C ledger / credits / CAP maturity / Progress dashboard.
- Stage dirty WIP: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py`.
- `git add .` or reset the tree.

## Tests

Extend `scripts/tests/test_uma_ops_console.py` (or add `test_uma_petty_cash.py` and keep ops suite green):

- Petty route + page 200 (ephemeral or post-restart).
- Nav links petty on Uma pages (no disabled label left for petty).
- Float honesty is NOT FOUND / unavailable without invented number.
- Quiet Today when no open petty items; card appears when fixture open item exists.
- Existing daily close suite still PASS.
- Forbidden write-helper scan still clean.

Run:

```bash
python3 scripts/tests/test_uma_ops_console.py
python3 scripts/tests/test_uma_blu_daily_close.py
```

## Git

One bounded commit. Message: `feat: Uma Blu petty cash surface on Today`

## Done line

Print exactly:

COMMIT: <hash>
TESTS: PASS=<n> FAIL=<n>
ROUTES: /bzg/uma-blu/petty
SYSTEM: <computed from ledger if touched Progress — else leave unchanged>
EXIT:0
CURSOR_DONE
