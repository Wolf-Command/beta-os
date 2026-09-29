# HUMFIX-1C RESULT — staff-facing gaps from HUMFIX-1B shots

29 Sep 2026. Decision: Matt relay / HUMFIX-1B Peaches eye gaps (extends HUMFIX-1B).  
Branch `build/wolf-command-rebuild`. Beta `:8788` + atrium-finance `:8790` only. Production `:8787` pid **15975** READ ONLY. Local commits only. `BETA_AUTH_MODE` unchanged (`cloudflare_access` on live Beta). `staff_ready` / `human_commissioned` not flipped. 12 RETEST work items left OPEN + actionable (history kept; not closed/recreated).

Mode: ENGINEERING PASS only — not staff ready, not human commissioned.

## Fixes

| # | Defect | Fix |
|---|--------|-----|
| 1 | Haikal TODAY topped by stale habitat fortnight 14–27 Sep (Working draft + Approved), RETESTs buried | `_stored_plan_items` filters to Asia/Makassar **today** window; status dupes collapse to one card; commissioning-retest cards always lead TODAY (all of them). |
| 2 | Zayen My Work: "You cannot approve or post a journal" | Boundary derived from live permission codes (`draft`/`approve`/`reject`/`post`). FC: prepare + approve/reject (not own); cannot post/pay/bank/other company. |
| 3 | Header strip showed `SPECIALIST_* · ROLE-*` | Staff chrome: plain seat title (`Zayen · Atrium Financial Controller`, `Content · Creative Director`). Owner/debug may still show codes. |
| 4 | Atrium phone = "Z" only; desktop truncated title | Navbar always shows name + seat title; wrap instead of truncate on 1024 and 390. |

## Verification

First opsfix3 pass failed mid-shot (`sidecar_unavailable`) → sidecar restarted → re-run green. Honest counts:

| Suite | Result |
|-------|--------|
| `test_humfix1c_20260929.py` | PASS=51 FAIL=0 |
| `test_humfix1b_20260929.py` | PASS=48 FAIL=0 |
| `test_humfix1_20260929.py` | PASS=36 FAIL=0 |
| `test_mywork1_20260929.py` | PASS=112 FAIL=0 |
| `test_mywork1b_20260929.py` | PASS=53 FAIL=0 |
| `test_humancomm1_20260929.py` | PASS=60 FAIL=0 |
| `test_staff_access_20260928.py` | PASS=275 FAIL=0 |
| `test_role_routing_20260928.py` | PASS=84 FAIL=0 |
| `test_atrium_full_mount_20260928.py` | PASS=80 FAIL=0 |
| `test_opsfix3_20260929.py` | PASS=89 FAIL=0 (re-run after sidecar restart) |
| shots `humfix1c_shots.py` | 6/6 files (>3 KB) |

### Assertion updates (intent preserved, not loosened)

- opsfix1/2/3 + staff_access: current-window only (stale 14–27 Sep habitat must not appear); Haikal My Work shot marker → `Retest`.

## Shots

Under `docs/wolf/ops/shots/`:

- `humfix1c-haikal-mywork-{desktop,phone}.png`
- `humfix1c-zayen-mywork-{desktop,phone}.png`
- `humfix1c-zayen-header-{desktop,phone}.png`

## PIDs / commits

| Process | PID |
|---------|-----|
| Prod `:8787` | **15975** (untouched) |
| Beta `:8788` | **13176** |
| Atrium `:8790` | **16059** (restarted after opsfix3 mid-suite death) |

| Repo | Commit |
|------|--------|
| beta-os | `fcf5a83` |
| atrium-finance | `2f5d938` |

## RETESTs (12 OPEN)

Haikal: `WI-1e3435eb…`, `WI-2a6edd45…`, `WI-fa0f1e2e…`, `WI-cbbbaf8c…`  
Zayen: `WI-4049b070…`, `WI-1b6f3982…`, `WI-41cd93c3…`, `WI-a3a4044c…`, `WI-4e4566db…`, `WI-1804769a…`, `WI-2649ab6e…`, `WI-3e07075e…`
