# Cursor mission — Owner cockpit top card

Date: 18 September 2026
Workspace: /Users/wolfterminal/beta-os
Surface: Beta only. Restart only with `python3 scripts/beta_restart.py`.
Do not touch Production :8787.

## Goal

Simplify the live `/progress` primary card. Keep the projection. Do not rebuild the page.

## Current truth (do not break)

- SYSTEM percent comes from `compute_system_from_ledger`. Live sum is 19.45, display 25.3. Do not hard-code that number.
- If status is not OK, show `SCORING PROJECTION STALE` and hide the percentage.
- Model E dials other than SYSTEM stay `Not scored yet`. Do not invent scores.
- Nav Empire / GGV / AMG / BZG and BZG links stay.
- `scripts/tests/test_dashboard_truth.py` must stay green, updated only where this slice changes the card shape.

## Change the primary card only

Replace "How far are we?" with `WOLF TRANSFORMATION`.

Show SYSTEM once:

SYSTEM — {computed percent from system.system_pct}

Technical capability built & proven

Then exactly these five lines, still unscored:

Operating Adoption — Not scored yet
Data / Measurement — Not scored yet
Founder Independence — Not scored yet
Financial Control — Not scored yet
Sale Readiness — Not scored yet

Do not also render a giant percent and a second SYSTEM row. `model_e_dials` currently prepends a SYSTEM row. Stop putting SYSTEM in that list. The headline is the only SYSTEM figure. The list is the five unscored lines.

Do not write that SYSTEM is overall transformation progress. The subtitle is "Technical capability built & proven" and nothing broader.

Move the foundations / Beta / human-commissioning phase sentence off the primary card. Put it inside the existing SYSTEM detail disclosure, or under Build Factory. Do not delete the text.

Remove the decorative status chips on the primary card (BUILT, HUMAN TESTING, LIVE, WAITING, PLANNED, POLICY, and any sibling with no count and no action). Do not replace them with new decorative pills. Leave counted, real status displays that already sit under SYSTEM detail.

Do not restructure Needs you, Owner pulse, or Build Factory in this slice, except: Needs you must not be fed fixture or example rows. If a row is marked example, drop it. Do not invent new owner actions. Empty Needs you is correct.

## Tests

Add or adjust assertions:

- Primary card title is WOLF TRANSFORMATION.
- HTML binds one SYSTEM headline to system.system_pct.
- The Model E list has five labels and none of them is SYSTEM.
- Phase sentence is not inside the primary card markup.
- Decorative vocabulary chips are absent from the primary card.
- Still no hard-coded 25.3 or live 28.
- Stale still hides the percentage.
- Fixture move SPECIFIED to BUILT still changes the computed percent by 0.20/77×100 and restores.

Run `python3 scripts/tests/test_dashboard_truth.py` and the existing progress dashboard tests. Do not weaken them to go green.

## Git

One bounded commit. Message style: `fix: Owner cockpit shows SYSTEM once`

Never `git add .`.
Never reset the tree.
Never stage these dirty files:

- scripts/migrations/migrate_phase2_6_team_readiness.py
- scripts/phase26_team.py
- scripts/skills/__init__.py
- scripts/wolf_intelligence.py

Do not edit the ledger, the credit table, or any capability state.
Do not write Production, bank, ESB, ClickUp, Telegram, email, Metricool, Klaviyo, or Sheets.

## Done line

Print exactly:

COMMIT: <hash>
TESTS: PASS=<n> FAIL=<n>
SYSTEM: <computed, not typed>
EXIT:0
CURSOR_DONE
