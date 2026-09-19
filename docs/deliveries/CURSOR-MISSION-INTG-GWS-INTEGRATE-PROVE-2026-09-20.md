# CURSOR MISSION — CAP-INTG-03 Google Workspace INTEGRATE prove — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-INTG-GWS-INTEGRATE-PROVE-2026-09-20.md`. `CR-260e724b776f2b89` next action is CAP-bound INTEGRATE prove pack. Owner lane `intg-gws-integrate-prove`. Wave-6 after intel-approve-to-rule-v1 DONE (`267618a`).

**Status:** read-only prove is on Beta `:8788`. Gmail, Calendar, Drive, and auth are named as different surfaces. Not a probe. Not a scope widen. Not GREEN. Not PROVEN. Not READY. `CAP-INTG-03` stays **BUILT**. Ceiling is **BUILT**. `CR-260e724b776f2b89` stays **OPEN**.

## What landed

- `scripts/core/gws_integrate_prove.py` — Owner prove. Ten checklist steps, all `NOT_RUN`, every slot `EMPTY`. Four surfaces: Gmail (`source_system` `gmail`), Calendar (`google-calendar`), Drive (`google-drive`), and auth (`google-oauth`). They are not the same system. Candidate reader files are absent. Health on each surface is `NOT_PROBED`, not GREEN. Messages, events, files, and scopes stay null. Machine-readable schema `wolf.cap-intg-03.gws-integrate-log.v1` accepts only a `NOT_RUN` log. No Google client is imported.
- `scripts/serve_beta.py` — `GET /api/gws-integrate-prove`, `/checklist`, `/schema`, `/log`, `/surfaces`, `/gaps`, `/<id>`, and `GET /gws-integrate-prove` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH` are 405 `writes_refused` for Owner. `POST /api/gws-integrate-prove/gmail-write` is `gmail_write_refused`. `POST /api/gws-integrate-prove/calendar-write` is `calendar_write_refused`. `POST /api/gws-integrate-prove/drive-write` is `drive_write_refused`. `POST /api/gws-integrate-prove/oauth-widen` is `scope_widen_refused`. `POST /api/gws-integrate-prove/probe` is `probe_refused`. `POST /api/gws-integrate-prove/green` is `green_refused`. `POST /api/gws-integrate-prove/conflate` is `conflate_refused`. `POST /api/gws-integrate-prove/production` is `production_refused`. `POST /api/gws-integrate-prove/prove` is `proven_refused`. `POST /api/gws-integrate-prove/resolve` is `resolve_refused`. `POST /api/gws-integrate-prove/fill` is `slots_refused`.
- `dashboards/gws-integrate-prove.html` — Owner page. It says Gmail is not Calendar, missing readers are not zero, and the pack is not GREEN.
- `scripts/tests/test_gws_integrate_prove.py` — distinct surfaces, absent readers, refuse paths, CR bind, ceiling, WIP four.

No Gmail, Calendar, or Drive call was made. No token was read. No OAuth scope was added. This is not the email-wire plan.

## Honesty (bound to the CR)

`CR-260e724b776f2b89` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `CAP-bound INTEGRATE prove pack`. This slice does not resolve the CR and does not write the ledger.

- `CAP-INTG-03` ledger state stays BUILT. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass.
- The emitted log has `status` `NOT_RUN`, `prove_id` null, `conflated` false, `probed` false, `scopes_widened` false, `green_claimed` false, `cr_resolved` false, and `messages` / `events` / `files` / `scopes` null. A log that claims a call, a probe, a scope widen, GREEN, a count (including zero or an empty scope list), READY, PROVEN, or a resolved CR is refused. It is not rewritten into a pass.
- Gaps: Gmail, Calendar, Drive, and auth reader files are `ABSENT`, not zero. Not probed is `REFUSED` as GREEN. Scope widen is `REFUSED`. Unread scopes are not zero scopes.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No Google write. No scope widen.

## Prove

`python3 scripts/tests/test_gws_integrate_prove.py` → `PASS=196 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `78495` (was `76097`). Before restart the new route was 404 on the old process.
- `curl http://127.0.0.1:8788/api/gws-integrate-prove` → 403
- `curl http://127.0.0.1:8788/gws-integrate-prove` → 403
- Ledger `CAP-INTG-03` BUILT, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
