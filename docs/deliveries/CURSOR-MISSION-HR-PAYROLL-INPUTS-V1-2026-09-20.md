# CURSOR MISSION — CAP-HR-04 Payroll Inputs prove skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-HR-PAYROLL-INPUTS-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `hr-payroll-inputs-v1` on mission `owner-autonomous-20260920-w11`, after wave-11 `hr-training-competency-v1` DONE (`2d873bf` / `2d873bfcd1d60f4f7b59c4a2c985d18377c3cb2a`). `CR-482b3b453867189f` stays OPEN.

**Status:** the Payroll Inputs prove framework skeleton is on Beta `:8788`. It names attendance, leave, pay_input, checklist, and notes slots and leaves every slot empty. An empty framework is not a live payroll-inputs workflow and not proof of payroll execute or payslip machinery. Attendance, leave, pay inputs, and payslips are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-HR-04` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-482b3b453867189f` stays **OPEN**. Bound `beta-hr-safe`.

## What landed

- `scripts/core/hr_payroll_inputs.py` — Owner read of the skeleton. Schema `wolf.cap-hr-04.payroll-inputs.v1` names the five slots and accepts no writes. `attendance`, `leave`, `pay_input`, `payslip`, and `checklist` stay null. `live_payroll_inputs`, `payroll_execute_machinery`, and `payslip_machinery` stay false. No framework file is created. `CR-482b3b453867189f` is read and not written.
- `scripts/serve_beta.py` — `GET /api/hr/payroll-inputs`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /hr-payroll-inputs` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /payroll` is `payroll_refused`. `POST /hr-master` is `hr_master_refused`. `POST /guest-blast` is `guest_blast_refused`. `POST /staff-blast` is `staff_blast_refused`. `POST /public-post` is `public_post_refused`. `POST /attendance`, `POST /leave`, `POST /pay_input`, `POST /payslip`, `POST /checklist`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/hr-payroll-inputs.html` — Owner page. It says an empty framework is not a live payroll-inputs workflow and not proof of payroll execute or payslip machinery, not PROVEN, not READY, CAP-HR-04 stays SPECIFIED, the ceiling label is BUILT, no invented attendance/leave/pay-input/payslip numbers, no guest blast, no staff blast, no public post, no HR master write, no payroll execute, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_hr_payroll_inputs.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-hr-payroll-inputs-v1-20260920`.

No attendance, leave, pay-input, or payslip number was stored. No HR people master write. No payroll execute. No guest blast. No staff blast. No public post. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The Training & Competency, Hiring & Onboarding, PMS orchestration, and SLA/incident modules were not edited.

## Honesty (bound to the CR)

`CR-482b3b453867189f` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Clean payroll-inputs CAP prove`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-HR-04` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_payroll_inputs` false, `empty_is_payroll_execute` false, `live_payroll_inputs` false, `payroll_execute_machinery` false, `payslip_machinery` false, `attendance` null, `leave` null, `pay_input` null, `payslip` null, `checklist` null, `guest_blast` false, `staff_blast` false, `public_post` false, `hr_master_write` false, `payroll_executed` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented attendance/leave/pay-input/payslip numbers. No guest blast. No staff blast. No public post. No payment. No payroll execute. No HR master write. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_hr_payroll_inputs.py` → `PASS=289 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `54870` (was `51942`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/hr/payroll-inputs` → 403
- `curl http://127.0.0.1:8788/hr-payroll-inputs` → 403
- Ledger `CAP-HR-04` SPECIFIED, 77 rows. CR state OPEN, next action `Clean payroll-inputs CAP prove`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
