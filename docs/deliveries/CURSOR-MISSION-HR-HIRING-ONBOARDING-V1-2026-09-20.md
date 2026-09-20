# CURSOR MISSION — CAP-HR-02 Hiring & Onboarding skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-HR-HIRING-ONBOARDING-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `hr-hiring-onboarding-v1` on mission `owner-autonomous-20260920-w11`, after wave-11 `amg-pms-orchestration-v1` DONE (`5f27c32` / `efd376f`). `CR-934f33e65b834254` stays OPEN.

**Status:** the Hiring & Onboarding workflow framework skeleton is on Beta `:8788`. It names requisition, candidate, offer, onboarding, checklist, and notes slots and leaves every slot empty. An empty framework is not a live hiring/onboarding workflow and not proof of HR hire machinery. Hires, candidates, offers, and onboarding records are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-HR-02` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-934f33e65b834254` stays **OPEN**. Bound `beta-hr-safe`.

## What landed

- `scripts/core/hr_hiring_onboarding.py` — Owner read of the skeleton. Schema `wolf.cap-hr-02.hiring-onboarding.v1` names the six slots and accepts no writes. `requisition`, `candidate`, `offer`, `onboarding`, and `checklist` stay null. `live_hiring_onboarding` and `hr_hire_machinery` stay false. No framework file is created. `CR-934f33e65b834254` is read and not written.
- `scripts/serve_beta.py` — `GET /api/hr/hiring-onboarding`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /hr-hiring-onboarding` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /payroll` is `payroll_refused`. `POST /hr-master` is `hr_master_refused`. `POST /guest-blast` is `guest_blast_refused`. `POST /staff-blast` is `staff_blast_refused`. `POST /public-post` is `public_post_refused`. `POST /requisition`, `POST /candidate`, `POST /offer`, `POST /onboarding`, `POST /checklist`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/hr-hiring-onboarding.html` — Owner page. It says an empty framework is not a live hiring/onboarding workflow and not proof of HR hire machinery, not PROVEN, not READY, CAP-HR-02 stays SPECIFIED, the ceiling label is BUILT, no invented hire/candidate/offer/onboarding numbers, no guest blast, no staff blast, no public post, no HR master write, no payroll execute, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_hr_hiring_onboarding.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-hr-hiring-onboarding-v1-20260920`.

No hire, candidate, offer, or onboarding number was stored. No HR people master write. No payroll execute. No guest blast. No staff blast. No public post. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The PMS orchestration, SLA/incident, and BOM/yield modules were not edited.

## Honesty (bound to the CR)

`CR-934f33e65b834254` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Workflows`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-HR-02` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_hiring_onboarding` false, `empty_is_hr_hire_machinery` false, `live_hiring_onboarding` false, `hr_hire_machinery` false, `requisition` null, `candidate` null, `offer` null, `onboarding` null, `checklist` null, `guest_blast` false, `staff_blast` false, `public_post` false, `hr_master_write` false, `payroll_executed` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented hire/candidate/offer/onboarding numbers. No guest blast. No staff blast. No public post. No payment. No payroll. No HR master write. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_hr_hiring_onboarding.py` → `PASS=287 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `49304` (was `46572`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/hr/hiring-onboarding` → 403
- `curl http://127.0.0.1:8788/hr-hiring-onboarding` → 403
- Ledger `CAP-HR-02` SPECIFIED, 77 rows. CR state OPEN, next action `Workflows`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
