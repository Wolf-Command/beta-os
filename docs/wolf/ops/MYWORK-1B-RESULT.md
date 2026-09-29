# MYWORK-1B result

29 Sep 2026. Beta only, branch `build/wolf-command-rebuild`. Small readability repair after MYWORK-1. Production `:8787` pid **15975** unchanged. Atrium sidecar `:8790` pid **96416** unchanged. Nobody marked `staff_ready` or `human_commissioned`. No new task engine. `BETA_AUTH_MODE` unset (unsigned `/wolf` stays 403). Local commits only — no push, no PR.

Decision served: Matt 29 Sep 2026 07:20 — P0 UNIVERSAL MY WORK (extend MYWORK-1).

Beta listener restarted via `scripts/beta_restart.py` (LaunchAgent `net.wolfcommand.serve-beta`). Unsigned `GET /api/health` is 200. Unsigned `GET /wolf` is 403.

## What changed

1. **Contrast (P0).** `wolf-tokens.css` was overriding page `--text`/`--muted` to pale shell colours (`#eaf3f2` / `#8aa6a6`), so cream-card copy was ~1.1:1. My Work item + execution report now pin `--work-ink: #1c1915` and `--work-muted: #3f3422` on `--work-card: #fffdf8` with `!important` (AA ≥ 4.5:1). Regression in `test_mywork1b_20260929.py` (token + computed style).

2. **Header overlap.** `#wolfnav` CONTEXT select now shrinks (`min-width: 0`); CONTEXT + identity wrap onto their own row under 1100px / phone. No overlap at 390, 768, 1024, 1440 (CDP bounding-box checks).

3. **Timezone.** Store stays UTC. `format_wita()` presents Asia/Makassar with a `WITA` label. Delegation chain exposes `accepted_at_display` / `offered_at_display`; card `due` is presented the same way. Raw `…Z` no longer shown in the chain UI.

4. **Duplicate TODAY.** Role dashboard no longer sets `prompt` equal to the section title; My Work hides `.prompt`. One `TODAY` `<h2>` on Devi phone.

5. **Fixture leak.** Removed MYWORK-1 test fixtures from the live Beta catalog and orphan evidence blobs. Tests/shots use isolated temp catalog + `WOLF_WORK_EVIDENCE_BLOBS`. Legacy **148** and commissioning **28** untouched. Amanda’s “Assigned 27” is 2 commissioning + 25 legacy imports (not fixture leak). Provenance: `state/work-evidence/mywork1b-fixture-cleanup.json`.

Also: war-room / execution-report derived-view refresh is best-effort under the test write guard (stops opsfix1 testability 500); Uma stale collection soft-fails when prod `recipes.sqlite` is refused under the guard (keeps Owner “wrong” honest from other sources).

## Fixture ids removed from live store

| work_item_id | title | was |
| --- | --- | --- |
| `WI-bc0c738c-4a71-4a31-81c8-3b35ed5b1ba1` | STALE probe | CANCELLED, origin null |
| `WI-b15f4668-ec8d-46dd-bf23-29449ce28975` | STALE probe | CANCELLED, origin null |
| `WI-3252aca3-dec0-4caf-8985-fd47aadbc1e3` | STALE probe | CANCELLED, origin null |

`Chain view shot` was **not** on the live catalog (only ever on temp shot DBs). Orphan evidence blob dirs under `state/work-evidence/blobs/` for test writes (no `core_work_evidence_files` rows) were removed — see cleanup JSON.

## Tests this session

| File | Result |
| --- | --- |
| `scripts/tests/test_mywork1b_20260929.py` | SUMMARY pass=53 fail=0, RESULT: PASS |
| `scripts/tests/test_mywork1_20260929.py` | SUMMARY pass=110 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix1_20260928.py` | SUMMARY pass=42 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix2_20260928.py` | SUMMARY pass=44 fail=1 — pre-existing Alchemist live drift (`order book is the alchemist history — 509`; not MYWORK-1B UI). Owner wrong-card check PASS. |
| `scripts/tests/test_opsfix3_20260929.py` | SUMMARY pass=88 fail=0, RESULT: PASS |
| `scripts/tests/test_staff_access_20260928.py` | SUMMARY pass=275 fail=0 |
| `scripts/tests/test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `scripts/tests/test_atrium_full_mount_20260928.py` | SUMMARY pass=79 fail=0 |
| `scripts/tests/test_umareal_20260928.py` | SUMMARY pass=81 fail=4 — pre-existing Alchemist register drift (pr_orders 504→509, receipt lines 452→454). Not MYWORK-1B. |
| `scripts/tests/test_opsaudit_20260928.py` | SUMMARY pass=109 fail=0, RESULT: PASS |

## Shots

`docs/wolf/ops/shots/mywork1b-*.png`: execution report, delegation chain (WITA), Devi phone (one TODAY), War Room, Owner header at 390 and 1024.

## Pids

| Process | Pid |
| --- | --- |
| Production `:8787` | 15975 (unchanged) |
| Atrium sidecar `:8790` | 96416 (unchanged) |
| Beta `:8788` | 66113 (replaced prior listener after restart) |

## Commits

Local only. No push.

- `4998727b4081db4faf1bd5fae976cb2a15bf0296` — Repair My Work cream-card contrast, header overlap, and WITA times.
- `1aef14351e603209b0d3cd563b866f98da81f422` — Record the MYWORK-1B repair commit in the result.
- `d474c7303a167130ce296ce3dce3a3da5aa643f2` — List full MYWORK-1B result commit SHAs.
- `711abfe2bb0abe1d85cb05571d3bd126df7be74a` — Close MYWORK-1B result commit list.
- `faa24a398fd4a0e1083d313a4ed30ae435a6ff45` — Fix MYWORK-1B result commit hashes.
- `995c43c89b30d528d94fd146dd88e2b05bac5198` — Close MYWORK-1B result commit hashes.

RESULT: PASS (Alchemist live-count drift on opsfix2/umareal noted; unrelated to this pack)
