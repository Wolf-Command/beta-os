# CURSOR PACK — IZA-ASSIGNMENT-RESOLUTION-1 (P0)

**Owner drain** · local beta-os `build/wolf-command-rebuild` · tip currently `8688c08` · **NO push** · prod `:8787` READ-ONLY

## Incident
Iza CF-authenticated as `izazaen00@gmail.com` / Iza Zainatulloh Hulhidayati.
UI: **Access denied — This close is not on your assignment.**
Human commissioning FAIL. Evidence stamped. Do NOT ask Iza to retry until RETEST.

## Non-negotiables
- Do NOT loosen RBAC
- Do NOT bypass assignment check
- Do NOT special-case her email
- Do NOT invent person-per-day close rows as the only path
- `staff_ready=false` · `human_commissioned=false` until Iza real PASS

## Business model (Owner)
Distinguish:
1. **Authorised to perform Uma Blu closes** (active Assignment → Floor Captain → Captain⊇Cashier → Daily Close roster VCR-UMA-2 / scope Uma)
2. **Today’s specific close taken/submitted by a person** (attribution)

Expected: any **active authorised** Uma Captain/Cashier on the Daily Close roster can **take tonight’s open Uma close** without engineering creating a person-specific record every day. Multiple authorised closers OK. Once one takes/submits: preserve attribution; prevent conflicting simultaneous completion. Deterministic + audited.

## Breakpoint hunt
Trace live Beta path for Iza:
CF identity → AuthIdentity → PERS-IZA → active Assignment → Floor Captain → BZG/Uma scope → Captain→Cashier → Daily Close roster → today’s Uma close → `/uma-blu-close`

Known deny site: `scripts/serve_beta.py` ~5700 `"This close is not on your assignment."` (also page deny ~1889).

Verify running code/data includes Captain⊇Cashier tip `876f49e` work + Daily Close tip `8688c08` — not stale process/DB.

## Tests (must green)
- Iza authorised Uma close = ALLOW
- Devi authorised Uma close = ALLOW
- unauthorised BZG employee = DENY
- authorised person wrong outlet = DENY
- inactive assignment = DENY
- anonymous = DENY
- direct URL bypass = DENY
- concurrent/taken close = deterministic + audited

## Exit
Fix reusable assignment→open-close resolution. Deploy/restart Beta as needed. Independent verify with Iza’s identity path. Stamp RESULT. Print EXIT:0 tip SHA. Peaches will then tell Matt **RETEST IZA NOW**.
