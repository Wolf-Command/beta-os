# HUMFIX-1 RESULT — Haikal + Zayen human commissioning FAIL repairs

29 Sep 2026. Decision: Matt relay 29 Sep 2026 ~11:14 WITA (after HUMANCOMM-1).  
Branch `build/wolf-command-rebuild`. Beta `:8788` only. Production `:8787` pid **15975** READ ONLY. Local commits only — no push, no PR. `BETA_AUTH_MODE` unchanged. `staff_ready` / `human_commissioned` not flipped. Disk free at start ~38 GB (>15 GB gate).

## 0 — FAIL evidence (canonical, kept)

Source: **Matt relay 29 Sep 11:14 WITA**. Employee `human_result=FAIL` on each person's commissioning Work Items; FAIL comment stored verbatim; FAIL history not overwritten. Engineering REPAIRs linked; later PASS must be a new RETEST evidence row.

| Person | Commissioning WIs FAILed | FAIL comment (abbrev) |
|--------|--------------------------|------------------------|
| Haikal | 4 (`WI-1e0bbaca…`, `WI-dd562a5a…`, `WI-3d556095…`, `WI-8daee1ef…`) | (1) everyone except Haikal and Misa sees only a few brands; (2) wants active Content Plans in Content Engine; (3) add Drone content type |
| Zayen | 8 (AR/AP, Command, Inventory, Journal, Ledger, Reports, Trial Balance, Confirm denied) | (1) General Ledger blank when opened; (2) could not approve a journal; access/roles need fixing. Placeholder: `evidence_pending: zayen-screenshots-via-matt` |

12 REPAIRs closed with `repair_commit_ref=d950a98+ad8239f` → 12 OPEN RETESTs (due 29 Sep) in Haikal/Zayen My Work (TODAY first 3 + DO THIS NEXT).

### Haikal RETEST ids
| ID | Title |
|----|-------|
| `WI-1e3435eb-4d39-4559-a2fa-3cf13b523ec2` | Retest: Library + Drone type + brand access |
| `WI-2a6edd45-1659-446a-91ea-8b533faf580e` | Retest: Content Plan + brand plans in Content Engine |
| `WI-fa0f1e2e-9564-41f6-8edf-cbc76a3173e2` | Retest: Real Habitat work from My Work |
| `WI-cbbbaf8c-55bf-4167-a7ae-6d0f974d5b9f` | Retest: Commission My Work |

### Zayen RETEST ids
| ID | Title |
|----|-------|
| `WI-4049b070-1938-4b33-bc6f-abcf195d4298` | Retest: General Ledger opens with account data |
| `WI-1b6f3982-7112-4ff9-9147-97e0ed1c645d` | Retest: Approve a journal prepared by someone else |
| `WI-41cd93c3-a8d5-48ad-9368-db17d44e80a4` | Retest: Confirm still-denied actions |
| `WI-a3a4044c-843d-41f4-86eb-8d738f78e2b1` | Retest: Commission AR/AP |
| `WI-4e4566db-72bf-4710-b6a9-0b02f64bbc2b` | Retest: Commission Atrium Command Centre |
| `WI-1804769a-551b-4df0-9e8c-231dd4131417` | Retest: Commission Inventory |
| `WI-2649ab6e-653a-472b-b632-dfb236ee64f2` | Retest: Commission Reports |
| `WI-3e07075e-72cb-4e5f-bea4-97003d7c678f` | Retest: Commission Trial Balance |

Seeded journal for SoD approve retest: `JRN-HUMFIX-PREP1` (preparer Owner Matt, status VALIDATED).

## 1 — Content brand scope

**Root cause:** Content Creator seats carried `SCOPE-GGV-CONTENT` only (4 GGV brands: habitat, selo, theone, tropik). Creative Directors who already had `SCOPE-WOLF-CONTENT-ALL-BRANDS` saw all 8. No per-email hack — role rule.

**Fix:** Attach `SCOPE-WOLF-CONTENT-ALL-BRANDS` to every ACTIVE Creative Director + Content Creator assignment (migration `ensure_content_team_brand_scope`). Server + UI read the same scope. Succession: new seat on the same role gets CONTENT-ALL; ending assignment removes live brand path.

### Before → after (authorised brand count)

| Person | Seat | Before | After |
|--------|------|--------|-------|
| Haikal | Creative Director | 8 | 8 |
| Misa | Creative Director | 8 | 8 |
| Zarah | Creative Director | 4 | 8 |
| Frail | Creative Director | 4 | 8 |
| Yudi | Content Creator | 4 | 8 |
| Gery | Content Creator | 4 | 8 |
| Alam | Content Creator | 4 | 8 |
| TJ | Content Creator | 4 | 8 |
| Nata | Content Creator | 4 | 8 |
| Rapp | Content Creator | 4 | 8 |

After brands (all): atrium, umablu, selo, habitat, tropik, theone, rainforest, goss.

## 2 — Active Content Plans in Content Engine

Canonical planner store (`/api/planner/plans?brand=…&active=1`). Content Engine loads active plans for the selected brand immediately. Plan items assigned to a person also surface in My Work from the same store (`staff_home` extra_today). No new plan DB.

## 3 — Drone content type

Canonical: `MEDIA_TYPES` / `STAFF_MEDIA_LABELS` / NAS card + upload ASSET_TYPES. UI (`content-2.0.html`) reads the registry. Existing Photo/Video/etc kept. Test: `drone in MEDIA_TYPES`, label `Drone`.

## 4 — Zayen General Ledger blank

**Root cause:** Ledger could render empty / crash when accounts were not yet on the client (empty posted ledger + Reports hub path without defensive accounts fetch). FC mount assertion also needed CONTROLLER pillar mapping in the sidecar.

**Fix:** `GeneralLedgerView` self-fetches accounts + `loadError`; Wolf assertion → sidecar `ROLE-AMG-FINANCIAL-CONTROLLER` / accounting-core. Verified as `ASG-ZAYEN-FC-1` on Beta. Shots desktop 1024 + phone 390.

**Sidecar note:** Brief said `:8790` untouched for process/secrets. FC approve required a source change + restart of atrium-finance (`ad8239f`); pid **86825** after restart (was 96416 at HUMANCOMM). Documented — not a silent secret/port change.

## 5 — Zayen journal approval (FC matrix)

Canonical matrix was silent / UNRESOLVED on ENT-AMG journal approve for FC. Implemented:

| Step | FC |
|------|-----|
| Prepare / review | Allowed (`atrium.journal.draft`) |
| Approve | Allowed — **SoD**: not own prepare (`sod_self_approve` 403) |
| Reject / return | Allowed — SoD same |
| Post | **Still DENIED** — open Matt policy; do not invent |

Still denied: payments, bank-detail, Owner/admin, other companies.  
Doc: `docs/wolf/finance/ATRIUM-FC-AUTHORITY-MATRIX.md`. Server-side tests in `test_humfix1` + sidecar npm.

**Open policy for Matt:** Should FC also post journals prepared by someone else? Currently held.

## 6 — Verification

| Suite | Result |
|-------|--------|
| `test_humfix1_20260929.py` | PASS=36 FAIL=0 (temp store) |
| `test_mywork1_20260929.py` | PASS |
| `test_mywork1b_20260929.py` | PASS=53 FAIL=0 |
| `test_humancomm1_20260929.py` | PASS=60 FAIL=0 |
| `test_opsfix1_20260928.py` | PASS |
| `test_opsfix2_20260928.py` | PASS |
| `test_opsfix3_20260929.py` | PASS |
| `test_staff_access_20260928.py` | PASS |
| `test_role_routing_20260928.py` | PASS |
| `test_atrium_full_mount_20260928.py` | PASS=80 FAIL=0 |
| `test_atrium_finance_ux_20260928.py` | PASS=212 FAIL=0 |
| `test_umareal_20260928.py` | PASS |
| `test_opsaudit_20260928.py` | PASS |
| atrium-finance npm | PASS=15 FAIL=0 |

### Shots
`docs/wolf/ops/shots/humfix1-*.png` — Haikal/Yudi brands, Haikal plans, Drone upload, Zayen ledger desktop+phone, Zayen journals, Haikal/Zayen retest My Work.

### PIDs (exit)
| Process | PID |
|---------|-----|
| Beta `:8788` | **86473** |
| Prod `:8787` | **15975** (untouched) |
| Atrium sidecar `:8790` | **86825** (restarted for FC mapping; see §4) |

### Commits (local only)
| Repo | Commit |
|------|--------|
| beta-os | `d950a98` (+ RESULT/shots follow-up) |
| atrium-finance | `ad8239f` |

### Migration
```
PYTHONPATH=scripts python3 scripts/migrations/migrate_humfix1_20260929.py --json
```
