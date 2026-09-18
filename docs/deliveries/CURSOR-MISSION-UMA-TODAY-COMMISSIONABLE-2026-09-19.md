# Cursor mission — Uma Blu Today commissionable loop (P3)

Date: 19 September 2026
Workspace: /Users/wolfterminal/beta-os
Beta only. Restart via `python3 scripts/beta_restart.py` if needed. Never touch :8787.

## Goal

Make `/bzg/uma-blu` (Today) one coherent operator front door over existing:

- PR / Bill
- Petty cash
- Daily Close (existing `/uma-blu-close` — do not rebuild)
- Issues
- History

Answer: **What do I need to do now?** and **Why?**

## Do not rebuild

Reuse `uma_ops_console.py`, petty page, bills, issues, history APIs, `venue_close.py`.

## Build

1. Today cards: attention-first ordering. Include PR attention, POLICY_REQUIRED, petty OPENING BALANCE REQUIRED / count gaps, Daily Close state + link into `/uma-blu-close`, Issues count, History teaser.
2. Each attention card shows `why` + `classification` from the P2 blocker explain helper.
3. Petty: keep float NOT_FOUND / OPENING BALANCE REQUIRED. Usable around missing float.
4. Daily Close: surface state only; deep link to existing engine. No invented closer or variance threshold.
5. Commissioning readiness artifact written by tests or a small JSON under `state/build-claims/`:
   - intended operator role (e.g. Uma Blu ops lead)
   - permissions required
   - can / cannot do
   - remaining policy/data blockers
   - exact commissioning test steps
6. **No live staff grant. No Devi auto-commission. No invent closer.**

## Tests

- Today returns ordered attention cards
- Why present on blocked cards
- example:true excluded from non-example attention counts
- daily close href points at existing route
- float still NOT_FOUND
- prior uma/petty/ops/dashboard_truth suites stay green

## Forbidden

Same absolute bounds as overnight + P2. No Model C score hunting.

## Done line

COMMIT: <hash>
TESTS: PASS=<n> FAIL=<n>
ROUTES: /bzg/uma-blu /bzg/uma-blu/petty /bzg/uma-blu/issues /uma-blu-close
COMMISSIONING_READY_DOC: <path>
SYSTEM: unchanged
EXIT:0
CURSOR_DONE
