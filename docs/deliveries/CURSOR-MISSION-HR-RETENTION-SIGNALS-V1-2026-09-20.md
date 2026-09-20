# CURSOR MISSION — CAP-HR-05 Retention & Succession Signals prove skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-HR-RETENTION-SIGNALS-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `hr-retention-signals-v1` on mission `owner-autonomous-20260920-w11`, after wave-11 `hr-payroll-inputs-v1` DONE (`bf4fecd` / `bf4fecdb100137a371dbc18e0073564acba5003c`). `CR-1ade9354d7443ed5` stays OPEN.

**Status:** the Retention & Succession Signals prove framework skeleton is on Beta `:8788`. It names retention_signal, succession_signal, risk_flag, checklist, and notes slots and leaves every slot empty. An empty framework is not a live retention/succession workflow and not proof of HR people-signal machinery. Retention, succession, and people-signal numbers are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-HR-05` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-1ade9354d7443ed5` stays **OPEN**. Bound `beta-hr-safe`.

## What landed

- `scripts/core/hr_retention_signals.py` — Owner read of the skeleton. Schema `wolf.cap-hr-05.retention-signals.v1` names the five slots and accepts no writes. `retention_signal`, `succession_signal`, `risk_flag`, `people_signal`, and `checklist` stay null. `live_retention_succession`, `people_signal_machinery`, and `succession_machinery` stay false. No framework file is created. `CR-1ade9354d7443ed5` is read and not written.
- `scripts/serve_beta.py` — `GET /api/hr/retention-signals`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /hr-retention-signals` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /payroll` is `payroll_refused`. `POST /hr-master` is `hr_master_refused`. `POST /guest-blast` is `guest_blast_refused`. `POST /staff-blast` is `staff_blast_refused`. `POST /public-post` is `public_post_refused`. `POST /retention_signal`, `POST /succession_signal`, `POST /risk_flag`, `POST /people_signal`, `POST /checklist`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/hr-retention-signals.html` — Owner page. It says an empty framework is not a live retention/succession workflow and not proof of HR people-signal machinery, not PROVEN, not READY, CAP-HR-05 stays SPECIFIED, the ceiling label is BUILT, no invented retention/succession/people-signal numbers, no guest blast, no staff blast, no public post, no HR master write, no payroll execute, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_hr_retention_signals.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-hr-retention-signals-v1-20260920`.

No retention, succession, or people-signal number was stored. No HR people master write. No payroll execute. No guest blast. No staff blast. No public post. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The Payroll Inputs, Training & Competency, Hiring & Onboarding, and PMS orchestration modules were not edited.

## Honesty (bound to the CR)

`CR-1ade9354d7443ed5` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Signals machinery`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-HR-05` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_retention_succession` false, `empty_is_people_signal` false, `live_retention_succession` false, `people_signal_machinery` false, `succession_machinery` false, `retention_signal` null, `succession_signal` null, `risk_flag` null, `people_signal` null, `checklist` null, `guest_blast` false, `staff_blast` false, `public_post` false, `hr_master_write` false, `payroll_executed` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented retention/succession/people-signal numbers. No guest blast. No staff blast. No public post. No payment. No payroll execute. No HR master write. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_hr_retention_signals.py` → `PASS=291 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `57054` after Beta-only kickstart (first restart was `57026`; was `54870` before lane). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/hr/retention-signals` → 403
- `curl http://127.0.0.1:8788/hr-retention-signals` → 403
- Ledger `CAP-HR-05` SPECIFIED, 77 rows. CR state OPEN, next action `Signals machinery`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
