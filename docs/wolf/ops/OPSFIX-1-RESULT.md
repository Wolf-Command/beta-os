# OPSFIX-1 result

28 Sep 2026. Beta only, branch `build/wolf-command-rebuild`. Extends Owner Command, My Work, the war room, and the Atrium proxy. Production `:8787` pid 15975 was not restarted. Atrium sidecar `:8790` pid 96416 was not restarted. Nobody was marked `staff_ready` or `human_commissioned`. No external write. No push.

Beta listener pid **19288** started Mon Sep 28 22:40:17 2026 from `/Users/wolfterminal/beta-os/scripts/serve_beta.py` with `BETA_AUTH_MODE` unset. Previous Beta pid 13943 was stopped. Unsigned `GET /api/health` is 200. Unsigned `GET /wolf` and `GET /bzg/uma-blu` are 403. Unsigned `GET /favicon.ico` is 200, magic `00000100`. `core_work_items` stays 0.

## Items

1. **FIXED.** Owner Command cards stayed on "Loading…" because the page only painted `#command` and left `[data-answer]` slots alone when the read was slow or rejected. `GET /api/owner/command` itself returns in well under 3 seconds for the owner. Each slot now gets the real answer, or UNKNOWN / MISSING, and a 3 second timer replaces a slot that is still loading. Signed shots `docs/wolf/ops/shots/opsfix1-owner-wolf.png` (1024) and `opsfix1-owner-wolf-phone.png` (390) show the six questions with stored answers. `documentElement.scrollWidth` was 1024 and 390.

2. **FIXED.** At 390px, Content Plan, Progress, and the shell clip horizontal overflow. The owner role chip renders in full (`Owner · OWNER · ROLE-OWNER`, scroll width equal to client width) on `/wolf` and `/progress`. Uma Blu subpages keep Here with the nav buttons and Sign out with the role chip. Shots: `opsfix1-haikal-plan-phone.png`, `opsfix1-owner-progress-phone.png`, `opsfix1-uma-sales-phone.png`. Each reported overflow false and width 390.

3. **FIXED.** The Command Centre chip follows the property profile. Profile unset shows SETUP INCOMPLETE. The sidecar was not edited or restarted. Beta injects the check into the proxied HTML. Shot `opsfix1-zayen-atrium.png` shows SETUP INCOMPLETE next to SQLite.

4. **FIXED.** For a seat allowed on `/amg/finance`, the operations desk Finance slot is a link to `/amg/finance`. Other seats keep the empty slot.

5. **FIXED.** Owner is allowed on `/amg/finance/lite` by the same seat rule as `/amg/finance`. Haikal stays 403. `atrium.board.read` was not granted.

6. **FIXED.** Beta Lead Spine shows NOT WIRED. The eight stored rows are demo and are withheld from the HTTP list and triage. They were not deleted. Owner and Haikal do not have `lead.read`, so the list API stays 403. The page does not paint demo cards.

7. **FIXED.** Creative Director and in-scope Content Creator homes project the nine stored Habitat content plans as read-only work. Provenance is `origin=historical`, `verified_by_wolf=false`, `source_system=content_plans`. Plans 1–3 stay tagged `data_lane=test`. The projection is by experience and brand scope, not by person id. Creators outside Habitat scope do not receive them. `core_work_items` stays 0. Shot `opsfix1-haikal-mywork.png`.

8. **FIXED.** Owner-only `GET /api/owner/war-room/testability` and `/finish-war-room` read `state/ops/testability-matrix.json`. The queue title is GIVE THIS TO A HUMAN NOW. Haikal is 403. Earlier FAIL text remains: "Commissioning FAIL on the earlier small desk" and "Zayen's FAIL was about the earlier desk". `staff_ready` and `human_commissioned` stay false. Shot `opsfix1-owner-warroom-testability.png`.

9. **FIXED.** `dashboards/favicon.ico` is served at `/favicon.ico` before the auth wall. Unsigned 200.

## Tests this session

| File | Result |
| --- | --- |
| `scripts/tests/test_opsfix1_20260928.py` | SUMMARY pass=41 fail=0, RESULT: PASS |
| `scripts/tests/test_staff_access_20260928.py` | SUMMARY pass=274 fail=0 |
| `scripts/tests/test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `scripts/tests/test_atrium_full_mount_20260928.py` | SUMMARY pass=79 fail=0 |
| `scripts/tests/test_umareal_20260928.py` | SUMMARY pass=85 fail=0 |
| `scripts/tests/test_opsaudit_20260928.py` | SUMMARY pass=91 fail=0, RESULT: PASS |

## Pids

| Process | Pid |
| --- | --- |
| Production `:8787` | 15975 (unchanged) |
| Atrium sidecar `:8790` | 96416 (unchanged) |
| Beta `:8788` | 19288 (replaced 13943) |

## Commits

Local only. Hash recorded on the commit that adds this file.

RESULT: PASS
