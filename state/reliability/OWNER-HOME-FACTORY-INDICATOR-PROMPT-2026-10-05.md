# OWNER-HOME-FACTORY-INDICATOR — small truthful factory line on Owner Home

Workspace: `/Users/wolfterminal/beta-os` only. Beta only. One finishable slice. The tree is already dirty. Do not commit, push, merge, or clean the git tree. Do not edit `scripts/build-factory/` (the factory owns it). Do not print process command lines, tokens, or secrets. No messaging anyone.

## The one step

Owner Home already exists (`dashboards/owner-cockpit.html`, `scripts/core/owner_cockpit.py`, `/api/owner/cockpit`, `/owner/cockpit` / related Owner Home surfaces). The God Mode factory queue lives at `state/build-factory/GOD-MODE-DISPATCH.json` with fields the supervisor already maintains (`items[].state`, `last_completion_at`, `last_autonomous_dispatch_at`).

Build the next step only: a **small truthful factory indicator line** on Owner Home. Do not rebuild Owner Home. Do not rebuild purchasing, AP, Ready to Pay, Recipe Builder, Daily Close, or Petty Cash. No engineering essay.

## Rules

- Show one compact, plain-language line (or tight chip row) with only these truthful counts/facts, read from existing factory state — do not invent:
  - active workers
  - ready queue count
  - blocked count
  - ready-for-human-test count
  - last completion
  - last autonomous dispatch
- Source of truth: `state/build-factory/GOD-MODE-DISPATCH.json` (and, if already used elsewhere for live workers, the factory ACTIVE / lock files the supervisor already writes). Prefer a tiny read helper that projects those fields; do not invent a second queue format.
- Owner-only or existing Owner Home auth pattern. Do not hardcode a person name. Do not expose process command lines, tokens, or secrets. Pid numbers may appear only if Owner Home already shows operational pids elsewhere; prefer counts and timestamps.
- No money movement. No purchasing writes. No GGV table writes. No mutation of protected close rows.
- If a tiny API field must be added to `/api/owner/cockpit` (or a sibling read route), keep it read-only projection. HTML-only extension of the existing board is preferred when possible.
- `staff_ready` stays false. `human_commissioned` stays false. Do not stamp PASS, READY, or ENG_PROVED.

## Page

- Add the indicator to the existing Owner Home board only. Do not redesign the page. Do not add an engineering essay, governance lecture, or factory runbook.
- Phone-friendly. Plain words.

## Hard locks

- Do not mutate these `catalog/content_library.sqlite` rows: `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`, `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`, `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`. Do not touch GGV finance tables (`ggv_bills`, `ggv_invoices`, `ggv_notas`, `ggv_vendors`, `ggv_nota_files`, `ggv_nota_history`) — leave the GGV 605 bills / 46 invoices / 33 notas alone.
- Read the live catalog only with Python `sqlite3` `mode=ro` for checks if any catalog check is needed. Tests use fixtures / temp state copies of factory JSON, not the live catalog.
- Prod pid 1297 on 127.0.0.1:8787 is sacred. Do not signal it, restart it, or touch port 8787. Production untouched.
- Beta listener at launch is pid 92970, the only listener on 127.0.0.1:8788. Reload Beta only if Python changed, and only when exactly one listener remains on 8788. HTML-only needs no reload. After any reload, 8788 must have exactly one listener and 1297 must still be the only listener on 8787.
- Leave cursor pid 2627 in `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone. No second writer. No money movement.

## Tests

Add `scripts/tests/test_owner_home_factory_indicator_20261005.py`. Cover: unauthenticated / non-owner denied as existing Owner Home rules require; indicator returns the six facts from a fixture queue; empty/idle queue yields honest zeros/nulls without inventing activity; does not mutate GOD-MODE-DISPATCH.json; no purchasing / payment side effects. Re-run a light Owner Home / cockpit smoke test if one already exists and report it still passes.

## Result

Write `state/reliability/OWNER-HOME-FACTORY-INDICATOR-RESULT-2026-10-05.json` with pack_id `OWNER-HOME-FACTORY-INDICATOR`, status, staff_ready false, human_commissioned false, eng_proved false, routes, files_changed, tests_pass / tests_fail, beta_reloaded plus 8788 listener pid, prod pid unchanged, protected_close_untouched, no_prod true, no_commit true, no_money_movement true, what_was_not_built (must include "Owner Home not rebuilt").

Stop when that result file is written.
