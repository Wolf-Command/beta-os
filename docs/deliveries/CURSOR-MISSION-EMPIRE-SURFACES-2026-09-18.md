# Cursor mission — Empire entity surfaces (P2)

Date: 18 September 2026
Workspace: /Users/wolfterminal/beta-os
Surface: Beta only. Restart only with `python3 scripts/beta_restart.py`.
Do not touch Production :8787.

## Goal

Make EMPIRE / GGV / AMG / BZG Progress surfaces honest and parallel after the Owner cockpit card slice. Do not rebuild `/progress`. Do not touch the Empire primary `WOLF TRANSFORM` card (already shipped in `17bc052`).

## Current truth (do not break)

- Empire primary card: `WOLF TRANSFORM` + one SYSTEM headline from ledger + five unscored Model E lines.
- Live SYSTEM is computed (sum 19.45 → 25.3). Never hard-code.
- Domain `pct` / `visual_pct` on GGV / AMG / BZG are legacy ESTIMATED — not SYSTEM.
- Nav stays Empire · GGV · AMG · BZG (BZG may keep deep links to `/bzg` and `/bzg/uma-blu`).
- `scripts/tests/test_dashboard_truth.py` and `scripts/tests/test_progress_dashboard.py` stay green.

## Change only entity surfaces

1. **AMG** — add a dedicated `render` branch (same class as GGV). Title `AMG · Atrium`. Show plain_phase, biggest_gap, and domain estimate labelled **ESTIMATED**. Do not invent Atrium stage machinery if overlay lacks it — empty/honest is fine.
2. **GGV** — keep Habitat stages. Make the domain percent line read as a domain estimate ESTIMATED (never SYSTEM). Keep Metricool WRITE_LOCKED honesty.
3. **BZG** — keep Uma stages + bzg_pulse + `/bzg` links. Domain percent labelled ESTIMATED. Do not invent petty-cash numbers.
4. **Empire** — leave the primary `WOLF TRANSFORM` card alone. Optional only: if entity panels still show decorative Status vocabulary chips, do not reintroduce them on Empire.

Do not invent Model E scores. Do not write ledger / credits / CAP maturity. Do not restructure Needs you / Owner pulse / Build Factory beyond what entity views already share.

## Tests

Add or adjust:

- AMG has dedicated panel markup (not only the generic fallback title).
- GGV / AMG / BZG domain percent copy includes ESTIMATED (or equivalent honesty label already used).
- Empire still has `WOLF TRANSFORM` and one SYSTEM headline bind.
- No hard-coded 25.3 or live 28.
- Existing dashboard truth + progress dashboard suites stay green.

Run `python3 scripts/tests/test_dashboard_truth.py` and `python3 scripts/tests/test_progress_dashboard.py`.

## Git

One bounded commit. Message: `fix: Empire GGV AMG BZG surfaces honest ESTIMATED`

Never `git add .`.
Never reset the tree.
Never stage:

- scripts/migrations/migrate_phase2_6_team_readiness.py
- scripts/phase26_team.py
- scripts/skills/__init__.py
- scripts/wolf_intelligence.py

No Production, bank, ESB, ClickUp, Telegram, email, Metricool, Klaviyo, or Sheets writes.

## Done line

Print exactly:

COMMIT: <hash>
TESTS: PASS=<n> FAIL=<n>
SYSTEM: <computed, not typed>
EXIT:0
CURSOR_DONE
