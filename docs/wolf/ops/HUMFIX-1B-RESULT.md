# HUMFIX-1B RESULT — close HUMFIX-1 gaps Peaches found by eye

29 Sep 2026. Decision: Matt relay / HUMFIX-1 Peaches eye gaps (extends HUMFIX-1).  
Branch `build/wolf-command-rebuild`. Beta `:8788` + atrium-finance `:8790` only. Production `:8787` pid **15975** READ ONLY. Local commits only — no push, no PR. `BETA_AUTH_MODE` unchanged (`cloudflare_access` on live Beta). `staff_ready` / `human_commissioned` not flipped. Disk free at start well above 15 GB gate (~185 GB avail).

Mode: HUMAN FAIL → REPAIR → RETEST. Engineering PASS only — not staff ready, not human commissioned.

## 0 — Premature RETESTs held, then re-opened

HUMFIX-1 had issued 12 OPEN RETESTs (4 Haikal + 8 Zayen) before screens were usable. Migration set `routing_state=HELD` / `routing_reason=Repair in progress — HUMFIX-1B` (status + history kept; My Work excludes HELD). After checks below passed, all 12 cleared back to actionable OPEN (`routing_state` NULL).

| Person | RETEST ids (re-opened) |
|--------|------------------------|
| Haikal | `WI-1e3435eb…`, `WI-2a6edd45…`, `WI-fa0f1e2e…`, `WI-cbbbaf8c…` |
| Zayen | `WI-4049b070…`, `WI-1b6f3982…`, `WI-41cd93c3…`, `WI-a3a4044c…`, `WI-4e4566db…`, `WI-1804769a…`, `WI-2649ab6e…`, `WI-3e07075e…` |

## 1 — Zayen General Ledger / SETUP badge

| | |
|--|--|
| **Defect** | GL showed "0 posted records", Rp 0 on 1000, header "SQLite: SETUP INCOMPLETE" — looked broken. |
| **Root cause** | Sidecar Beta DB `/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite` has **zero** `journal_headers` with `status=POSTED` (0 posted lines). Chart of accounts exists; commissioning journals PREP1/PREP2/MULZIJ are VALIDATED/APPROVED only. `system_settings.property_name` is empty string — chip previously labelled that as "SETUP INCOMPLETE". Not a wrong store/entity/period. No real AMG opening balances / posted history imported anywhere on Beta. |
| **Fix** | Do **not** invent posted numbers. Truthful empty: "No posted journal lines for ENT-AMG yet" + plain next step (approve+post; posting still Owner-policy pending). Chip text → **Property unset** when `property_name` empty. |
| **Test** | `test_humfix1b` ledger probe + chip assert; `test_opsfix1` chip; `test_atrium_full_mount` ledger marker updated to new copy (intent unchanged: page must show empty-GL truth, not a fake filled ledger). |
| **Shots** | `humfix1b-zayen-gl-desktop.png`, `humfix1b-zayen-gl-phone.png` |

## 2 — Zayen title

| | |
|--|--|
| **Defect** | Header showed "General Accountant". |
| **Root cause** | Sidecar seat title not taken from Wolf canonical FC assignment. |
| **Fix** | Assertion / `/api/me` carries `WOLF_SEAT_TITLE` from active assignment `ASG-ZAYEN-FC-1` / `ROLE-AMG-FINANCIAL-CONTROLLER` → UI "Atrium Financial Controller". No email hardcoding. |
| **Test** | `test_humfix1b` title path; live shots. |
| **Shots** | `humfix1b-zayen-title-desktop.png`, `humfix1b-zayen-title-phone.png` |

## 3 — Journal Workbench truth

| | |
|--|--|
| **Defect** | "Post to Ledger" shown though Post DENIED for FC; PREP1 already APPROVED (consumed); SoD unclear on MULZIJ. |
| **Root cause** | UI did not gate on `journalPostAllowed` / preparer SoD; tests had mutated live fixture. |
| **Fix** | UI: Post disabled + "Posting needs Owner approval — policy pending"; server stays 403. Approve hidden/disabled for own prepare with SoD copy. Seed **`JRN-HUMFIX-PREP2`** (preparer Owner Matt, VALIDATED, labelled commissioning test). `JRN-MULZIJ3N-117` created_by=`Zayen (Controller)` → Approve disabled for Zayen. Humfix1b journal tests use **temp atrium store only**; live PREP2 remains VALIDATED after suite. |
| **Test** | `test_humfix1b` SoD/post gates + live PREP2 untouched; atrium npm FC may approve not post. |
| **Shots** | `humfix1b-zayen-journals-desktop.png`, `humfix1b-zayen-journals-phone.png` |

## 4 — Content Plans / assignees / Drone / My Work cards

| | |
|--|--|
| **Defect** | Stale "Habitat Fortnight Sep 14-27" shown as current on 29 Sep; assignees as raw email; Drone visibility; plan items not in My Work. |
| **Root cause** | Plan picker preferred any "active"/approved plan without date-window ranking; assignee display used email; habitat fortnight cards not limited to current window. |
| **Fix** | Rank by date window covering today, then approved/active; older via **Plan history**. Empty current: plain "No current plan" + history control. Assignees → `org_persons.display_name` via assignment/identity (never raw email). `staff_home` surfaces assigned plan items only for current-window plans. Drone already in `MEDIA_TYPES` / `#upMediaType` + Library filter. |
| **Test** | `test_humfix1b` current/history/assignee/drone; `test_opsfix3` habitat card dedupe. |
| **Shots** | `humfix1b-haikal-plan-{desktop,phone}.png`, `humfix1b-haikal-drone-{desktop,phone}.png` (MEDIA TYPE open: Photo/Video/Audio/Graphic/**Drone**) |

## 5 — Content team usability (10 people)

Scope dedupe: non-destructive end-date of duplicate ACTIVE `(assignment_id, scope_id)` rows — **53** ended (incl. late Misa `SCOPE-WOLF-CONTENT-ALL-BRANDS` twin); **0** ACTIVE duplicate groups remain.

| Person | Assignment | Brands | Commissioning flow (temp store) |
|--------|------------|--------|----------------------------------|
| Haikal | ASG-HAIKAL-CD-1 | 8 | DONE/VERIFY PASS |
| Misa | ASG-MISA-CD-1 | 8 | DONE/VERIFY PASS |
| Zarah | ASG-ZARAH-CD-1 | 8 | DONE/VERIFY PASS |
| Frail | ASG-FRAIL-CD-1 | 8 | DONE/VERIFY PASS |
| Yudi | ASG-YUDI-CREATOR-1 | 8 | DONE/VERIFY PASS |
| Gery | ASG-GERY-CREATOR-1 | 8 | DONE/VERIFY PASS |
| Alam | ASG-ALAM-CREATOR-1 | 8 | DONE/VERIFY PASS |
| TJ | ASG-TJ-CREATOR-1 | 8 | DONE/VERIFY PASS |
| Nata | ASG-NATA-CREATOR-1 | 8 | DONE/VERIFY PASS |
| Rapp | ASG-RAPP-CREATOR-1 | 8 | DONE/VERIFY PASS |

Brands (all): atrium, umablu, selo, habitat, tropik, theone, rainforest, goss — via `SCOPE-WOLF-CONTENT-ALL-BRANDS` on canonical assignment (People ≠ Roles; succession-safe).

**Shots:** `humfix1b-yudi-brands-{desktop,phone}.png` (8 brands open), `humfix1b-rapp-mywork-phone.png`, `humfix1b-haikal-retest-mywork-{desktop,phone}.png`, `humfix1b-zayen-retest-mywork-{desktop,phone}.png`.

## 6 — Verification (HUMFIX-1 §6 + humfix1b)

First pass: atrium sidecar died mid-suite (`sidecar_unavailable` / 502 / connection refused) → FAIL on opsfix1/3, staff_access (−1), role_routing (−2), atrium_full. **Sidecar restarted (pid below); failed suites re-run to green.** Honest counts after re-run:

| Suite | Result |
|-------|--------|
| `test_humfix1b_20260929.py` | PASS=48 FAIL=0 |
| `test_humfix1_20260929.py` | PASS=36 FAIL=0 |
| `test_mywork1_20260929.py` | PASS=112 FAIL=0 |
| `test_mywork1b_20260929.py` | PASS=53 FAIL=0 |
| `test_humancomm1_20260929.py` | PASS=60 FAIL=0 |
| `test_opsfix1_20260928.py` | PASS=42 FAIL=0 (re-run after sidecar restart) |
| `test_opsfix2_20260928.py` | PASS=45 FAIL=0 |
| `test_opsfix3_20260929.py` | PASS=88 FAIL=0 (re-run) |
| `test_staff_access_20260928.py` | PASS=275 FAIL=0 (re-run) |
| `test_role_routing_20260928.py` | PASS=84 FAIL=0 (re-run) |
| `test_atrium_full_mount_20260928.py` | PASS=80 FAIL=0 (re-run) |
| `test_atrium_finance_ux_20260928.py` | PASS=212 FAIL=0 |
| `test_umareal_20260928.py` | PASS=85 FAIL=0 |
| `test_opsaudit_20260928.py` | PASS=109 FAIL=0 |
| atrium-finance npm | PASS=15 FAIL=0 |
| shots `humfix1b_shots.py` | 17/17 files (>3 KB); drone re-capture confirmed MEDIA TYPE options |

### Test marker updates (not loosened)

- `test_opsfix1`: asserts chip **"Property unset"** (same intent: live truth chip present; copy matches truthful property state).
- `test_atrium_full_mount`: ledger ready marker → **"No posted journal lines for ENT-AMG yet"** (same intent: empty GL must render honest empty, not invent lines).

## 7 — Shots index

All under `docs/wolf/ops/shots/`:

- `humfix1b-zayen-gl-{desktop,phone}.png`
- `humfix1b-zayen-journals-{desktop,phone}.png`
- `humfix1b-zayen-title-{desktop,phone}.png`
- `humfix1b-haikal-plan-{desktop,phone}.png`
- `humfix1b-haikal-drone-{desktop,phone}.png`
- `humfix1b-yudi-brands-{desktop,phone}.png`
- `humfix1b-haikal-retest-mywork-{desktop,phone}.png`
- `humfix1b-zayen-retest-mywork-{desktop,phone}.png`
- `humfix1b-rapp-mywork-phone.png`

## 8 — PIDs / commits / migration

| Process | PID |
|---------|-----|
| Prod `:8787` | **15975** (untouched) |
| Beta `:8788` | **2302** |
| Atrium `:8790` | **9496** (restarted after npm/suite collision; DB journals preserved) |

### Commits (local only — filled after commit)

| Repo | Commit |
|------|--------|
| beta-os | _(see git log)_ |
| atrium-finance | _(see git log)_ |

### Migration
```
PYTHONPATH=scripts python3 scripts/migrations/migrate_humfix1b_20260929.py --json
# hold: default; reopen after green:
PYTHONPATH=scripts python3 scripts/migrations/migrate_humfix1b_20260929.py --reopen --no-journal --json
```

### Open for Matt (unchanged)
Should FC also **post** journals prepared by someone else? Still denied — policy pending. No real POSTED AMG history on Beta until import/Owner post path exists.
