# HUMANCOMM-1 RESULT — human commissioning loop live in My Work

29 Sep 2026. Decision: Matt 29 Sep 2026 11:12 START HUMAN COMMISSIONING NOW.  
Branch `build/wolf-command-rebuild`. Beta `:8788` only. Production `:8787` pid **15975** unchanged. Atrium sidecar `:8790` pid **96416** unchanged. `BETA_AUTH_MODE` unset (unsigned `/wolf` stays 403). Local commits only — no push, no PR. Nobody flipped `staff_ready` / `human_commissioned`. DONE never moves SYSTEM %.

## What changed

### A — Employee flow (phone-first)
- Commissioning cards/detail show: open link, plain numbered steps, evidence attach (file input + capture on phone), required PASS/FAIL, comment (“What is wrong or could be better?” — required on FAIL), DONE.
- DONE blocked until evidence + PASS/FAIL (and FAIL comment) are present — clear error message.
- Employee result stored as `human_result` / `human_comment`, separate from verifier `commissioning_result`.
- All 28 commissioning instructions rewritten (ids kept) so Matt is not needed to explain the test.
- TODAY shows first 3 active items; the rest land in DO THIS NEXT.

### B — Loop after DONE
- Employee PASS + evidence → status `AWAITING_VERIFY`.
- Verifier (Owner / `work.verify`) PASS → `VERIFIED` + VERIFIED HUMAN PASS. REJECT → back to person. FAIL → engineering repair.
- Employee FAIL → engineering repair (`origin=commissioning-repair`, owner/executor null, `scope_label=ENGINEERING`, accountable Owner for visibility). **Bug fixed:** repair is no longer owned by the employee.
- Repair DONE with commit/test evidence → automatic RETEST (`origin=commissioning-retest`) to the same person/assignment.
- `GET /api/commissioning/live-results` (owner/verify) + page `/commissioning-live`.
- `opened_at` stamped on first detail open by owner/executor.
- CLI `scripts/ops/commissioning_tick.py --json` (read-only); `--apply` creates missing repairs/retests only — never auto-verifies PASS.

### C — Legacy 148 routing audit
Provenance from `proposed-migration.json` + `legacy-work-candidates.json`. Keep only when original assignee maps to a Person with active Assignment covering the item’s entity. Else `owner=null`, `routing_state=NEEDS_ROUTING`. Matt keeps only Owner-assignee items that need owner authority.

| Owner | Before | After | Reason summary |
|-------|--------|-------|----------------|
| PERS-DEVI | 82 | 37 | Kept where assignee_in_source=Devi and ENT-BZG in scope; rest no reliable assignee |
| PERS-AMANDA | 25 | 0 | Amanda-desk rows are ENT-BZG; Amanda scopes only ENT-GGV → NEEDS_ROUTING; Notion rows had no assignee |
| PERS-HAIKAL | 10 | 0 | Source assignee was Mr Wolf / owner, not Haikal → NEEDS_ROUTING |
| PERS-MATT | 31 | 15 | Kept only Owner-assignee + owner-authority hints; routine Owner inbox → NEEDS_ROUTING |
| (null) / NEEDS_ROUTING | 0 | 96 | Management queue on Owner Overwatch; not in anyone’s My Work |
| **Total legacy** | **148** | **148** | OBSOLETE untouched; provenance kept |

### D — Overwatch
Owner Overwatch / attention shows commissioning FAILs, engineering repairs, overdue, NEEDS_ROUTING, owner-authority items, AWAITING_VERIFY. Routine work lists do not route through Owner.

### E — Cheap fixes
1. CONTEXT label colour `#eaf3f2` on dark nav (readable at 1024).
2. Identity (`.nv-hello`) wraps / full width at mid breakpoints — no “R…” truncation.
3. opsfix2 + umareal order/receipt assertions read **live Alchemist counts** (not hardcoded 504/452). Register refreshed via `write_register()` so register matches live (514 orders, 466 receipt lines). A real register↔live mismatch would still fail `test_register`.

## Live-results snapshot (tick, read-only)

```
commissioning_tick as_of=2026-09-29T11:35:45+08:00
awaiting=0 fails_no_repair=0 repairs_fixed_without_retest=0 rows=28
```

Commissioning OPEN still 28 (Devi 5, Zayen 8, Amanda 2, Haikal 4, +9 content seats ×1).

## Schema
Additive columns on `core_work_items`: `human_result`, `human_comment`, `opened_at`, `routing_state`, `routing_reason`, `repair_commit_ref`. Status CHECK rebuilt to allow `AWAITING_VERIFY`. Child FKs on evidence/delegations repaired after rename.

## Tests
| Suite | Result |
|-------|--------|
| `test_humancomm1_20260929.py` | PASS (temp store for flow; live invariants read-only) |
| `test_mywork1_20260929.py` | PASS |
| `test_mywork1b_20260929.py` | PASS |
| `test_opsfix1_20260928.py` | PASS |
| `test_opsfix2_20260928.py` | PASS |
| `test_opsfix3_20260929.py` | PASS |
| `test_staff_access_20260928.py` | PASS |
| `test_role_routing_20260928.py` | PASS |
| `test_umareal_20260928.py` | PASS (after register refresh) |
| `test_opsaudit_20260928.py` | PASS |
| `test_atrium_full_mount_20260928.py` | **3 FAIL pre-existing env** — atrium beta DB has `journal_headers=1` (test expects 0); journal shot marker “No journals found” absent. Sidecar `:8790` not modified. Not a HUMANCOMM regression. |

## Shots
`docs/wolf/ops/shots/humancomm1-*.png`: Devi phone commissioning (evidence + PASS/FAIL + comment + DONE), Zayen/Amanda/Haikal My Work, `/commissioning-live`, Owner Overwatch, NEEDS ROUTING queue, header at 1024.

## PIDs
| Process | PID |
|---------|-----|
| Beta `:8788` | **81505** (restarted via `scripts/beta_restart.py`) |
| Prod `:8787` | **15975** (untouched) |
| Atrium sidecar `:8790` | **96416** (untouched) |

## Migration / CLI
```
PYTHONPATH=scripts python3 scripts/migrations/migrate_humancomm1_20260929.py --json
PYTHONPATH=scripts python3 scripts/ops/commissioning_tick.py --json
```

## Commit
Local only: `918a15d` (+ result pin `8ea6866`) — Ship HUMANCOMM-1: employee commissioning loop in My Work.
