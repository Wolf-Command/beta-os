# CURSOR PACK — IZA-UMA-CAPTAIN-CASHIER-1 (Beta only · LOCAL · no push)

Workspace: `/Users/wolfterminal/beta-os`  
Branch: `build/wolf-command-rebuild` (local only — **no origin/push**)  
Prod `:8787`: **READ-ONLY**. Never mutate prod.  
`staff_ready=false` · `human_commissioned=false`  
`credit_override=OWNER_ORDER`

HR stamp (read first): `state/iza-uma/HR-RECONCILE-20261002.md` (+ `.json`)  
Architecture: `state/iza-uma/ROLE-ARCHITECTURE.md`  
Owner order: Iza Uma Blu Captain + Cashier + tonight Daily Close (P0)

## Goal (credit-light — prefer seed/config over rewrites)

1. **Person** — CREATE `PERS-IZA` only if absent. Match email `izazaen00@gmail.com` or refuse duplicate.  
   - display_name / legal_name from HR: **Iza Zainatulloh Hulhidayati**  
   - AuthIdentity `AUTH-IZA-EMAIL` provider=email identifier=`izazaen00@gmail.com`  
   - Do **not** invent emp fields into org_persons beyond name/status (no salary/bank). Optional note in migration comment: HR emp `BZG26023002`.
2. **Roles** — CREATE if absent:  
   - `ROLE-BZG-CASHIER` display **Cashier** DEPT-BZG-FB OPERATING SPECIFIED  
   - `ROLE-BZG-CAPTAIN` display **Floor Captain** DEPT-BZG-FB OPERATING SPECIFIED  
   Seed **identical** CASHIER_BUNDLE grants on both roles (Captain ⊇ Cashier by composition). Reuse existing permission_ids for venue.close.read/submit + evidence + work loop grants (same codes already on ROLE-BZG-CLOSER). Do not create finance/bank/Owner/admin/HR/AMG/GGV grants.
3. **Position / Assignment / Scope** —  
   - `POS-BZG-CAPTAIN-UMA-1` → ROLE-BZG-CAPTAIN · ENT-BZG · BZG-UMA · DEPT-BZG-FB · label `Floor Captain · Uma Blu`  
   - `ASG-IZA-CAPTAIN-UMA-1` ACTIVE primary for PERS-IZA  
   - Attach `SCOPE-BZG-UMA` only (not SCOPE-BZG-ENTITY / finance / AMG / GGV)
4. **Daily Close multi-closer** — INSERT `venue_closer_roster` `VCR-UMA-2` ACTIVE for PERS-IZA / POS-BZG-CAPTAIN-UMA-1 / ASG-IZA-CAPTAIN-UMA-1. **Do not** modify or end `VCR-UMA-1` / Devi closer assignment. Variance policies stay empty. EDC terminals stay NEEDS CONFIGURATION. No invented EDC IDs/tolerances.
5. **UI ACL (minimal code)** — In `scripts/serve_beta.py` close_roles frozenset for `/uma-blu-close` + `/bzg/daily-close`, add **`ROLE-BZG-CAPTAIN`** (reusable — not email). Do not hardcode PERS-IZA / Iza name. Prefer one small edit.
6. **Tests** — Add focused tests (new file OK):  
   - PERS-IZA + auth email bind  
   - Captain role has cashier bundle perms  
   - Iza ACTIVE assignment scoped BZG-UMA only  
   - roster has Devi + Iza (multi-closer)  
   - close_roles source contains ROLE-BZG-CAPTAIN  
   - no `if Iza` / no Devi replacement  
   Run: new tests + `scripts/tests/test_uma_blu_daily_close.py` + `scripts/tests/test_bzg_daily_close_till_edc_1.py` (must stay green).
7. **Migration** — `scripts/migrations/migrate_iza_uma_captain_cashier_1.py` (+ tiny SQL if needed). Idempotent. Run against `catalog/content_library.sqlite` Beta only.
8. **Stamps** — Write RESULT under `state/iza-uma/IZA-UMA-CAPTAIN-CASHIER-1-RESULT.md` (+ json). Keep `staff_ready=false` `human_commissioned=false`. CF login binding = Owner-gated checklist only (do not claim CF live).
9. **Commit** — Local only, explicit paths, clear message. **No push.**

## Prove (engineering; CF later)

- Simulated/API: `active_role_ids(PERS-IZA)` includes `ROLE-BZG-CAPTAIN`  
- `rbac.evaluate(PERS-IZA, 'venue.close.submit', {entity_id:ENT-BZG, brand_id:BZG-UMA})` ALLOW  
- `rbac.evaluate` for finance.* / AMG / GGV DENY or no grant  
- Unsigned `/uma-blu-close` still 403  
- Dev-assertion subject `izazaen00@gmail.com` (only if BETA_AUTH_MODE=development_assertion in test harness) reaches close page roles — do not weaken CF production path

## Do not

- Create Gmail draft (already exists)  
- Replace Devi / hardcode single closer  
- Invent EDC IDs, variance tolerances, names, employee IDs  
- Dual cursor-agent · mutate prod :8787 · push · mark staff_ready/human_commissioned true  
- Grant finance/bank/Owner/admin/HR/AMG/GGV  
- Bypass unfinished Daily Close controls for tonight

## Exit

`EXIT:0` when migration applied, tests green, RESULT stamped, local commit done.
