# NOTEPACK — Bank Import commissioning (honest)

`2026-10-01T11:24:15+08:00` · Peaches · **Do not invent LIVE** · write_authority=false

## End state
**CONNECTED, COMMISSIONING REQUIRED** (matrix). CONFIGURED ≠ CONNECTED ≠ TESTED ≠ COMMISSIONED.

## Human prove path (prep only — no auto ping)
1. Open Beta staff/finance desk path that surfaces Bank Import (entity-scoped).
2. Import a **non-prod / sample** statement file for an entity the person is seated on.
3. Confirm rows land in expected entity ledger only (AMG/BZG/GGV isolation).
4. Confirm no write to Prod :8787; Finance :8790 SoD unchanged unless Owner row.
5. Capture screenshot + file name + entity_id → mark COMMISSIONED only after Owner/staff pass.

## Explicit non-claims
- Not LIVE+TESTED until human prove
- Not write_authority_approved
- Does not clear human_commissioned alone
