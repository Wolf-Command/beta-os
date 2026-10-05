# Prove checklist — Iza Uma Captain/Cashier/Daily Close (after Matt CF Allow)

**Owner-gated:** Cloudflare Access Allow for `izazaen00@gmail.com` (Matt adding). Login binding prove only after CF ready.  
`staff_ready=false` · `human_commissioned=false` until real human PASS.

## A — Already runnable NOW (no CF; Beta :8788 / catalog)

1. `sqlite3 catalog/content_library.sqlite` → `org_persons` has `PERS-IZA`, display/legal = Iza Zainatulloh Hulhidayati  
2. `org_auth_identities` → `AUTH-IZA-EMAIL` / email `izazaen00@gmail.com` → `PERS-IZA`  
3. Roles exist: `ROLE-BZG-CASHIER`, `ROLE-BZG-CAPTAIN`; Captain has same venue.close.read/submit (+ evidence/work) grants as Cashier bundle  
4. `ASG-IZA-CAPTAIN-UMA-1` ACTIVE primary → `POS-BZG-CAPTAIN-UMA-1` → scope `SCOPE-BZG-UMA` only  
5. `venue_closer_roster`: `VCR-UMA-1` Devi ACTIVE **and** `VCR-UMA-2` Iza ACTIVE (multi-closer)  
6. API/RBAC (python): `rbac.evaluate('PERS-IZA','venue.close.submit',{'entity_id':'ENT-BZG','brand_id':'BZG-UMA'})` → ALLOW  
7. Same for finance.* / AMG / GGV codes → DENY / no grant  
8. Unsigned GET `http://127.0.0.1:8788/uma-blu-close` → 403 (not 404)  
9. `serve_beta.py` close_roles includes `ROLE-BZG-CAPTAIN` (reusable)  
10. EDC terminals still NEEDS CONFIGURATION; `venue_close_variance_policies` ACTIVE count = 0  
11. Tests: pack tests + `test_uma_blu_daily_close` + `test_bzg_daily_close_till_edc_1` green  
12. Prod `:8787` health 200 untouched

## B — After Matt CF Allow (Owner-gated login binding)

1. Confirm CF Access application Allow list includes `izazaen00@gmail.com`  
2. Iza signs in via Beta tunnel URL with her Google account  
3. `/api/core/me` → `person_id=PERS-IZA`, `identity_assurance=cloudflare_access_verified`  
4. `/uma-blu-close` or `/bzg/daily-close` loads close UI (Assignment seat — not email ACL)  
5. Capabilities show submit path for Uma only; Rainforest human_close disabled  
6. Tonight close attempt: ESB snapshot + till declare (evidence required) + EDC lines — **stop honestly** on NEEDS CONFIGURATION / VARIANCE_REQUIRES_POLICY; do not invent terminals/tolerances  
7. Devi can still open/submit close (multi-closer)  
8. Human stamp PASS/FAIL → only then consider staff_ready / human_commissioned flags

## C — Explicit non-goals tonight

- Do not create another Gmail onboarding draft  
- Do not replace Devi  
- Do not invent EDC IDs / variance tolerances  
- Do not mark commissioned for scaffolding alone
