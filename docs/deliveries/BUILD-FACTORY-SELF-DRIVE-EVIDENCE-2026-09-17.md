# BUILD FACTORY SELF-DRIVE — Evidence 2026-09-17

## Defect recorded

Delegation: Cursor launched → Matt `status` → Grok FAIL DLG-RT-001 → Cursor fix → Matt `status` again. Founder-dependent polling = BUILD FACTORY defect.

## Fix (governance + Beta tooling only)

- `docs/RULE-Build-Factory-Self-Driving-2026-09-17.md`
- `docs/deliveries/GROK-PLAN-BUILD-FACTORY-SELF-DRIVING-2026-09-17.md`
- `scripts/build-factory/{bf_watch,bf_write_run,bf_harmless_job}.*`
- Routine **Build factory watch** (weekdays */5 08–19 WITA)
- Skill **Build factory self-drive**

## Harmless E2E (Matt poll messages: 0)

1. ACTIVE run `BF-harmless-20260917` armed
2. Child launched via **tracked Mac Shell background** (`bf_harmless_job.sh`)
3. Peaches detected completion via log `EXIT:0` + `bf_watch` → `ADVANCE` (no Matt message)
4. Stages advanced in state: TESTS → GROK_REVIEW(FAIL sim) → WAITING_CURSOR_FIX → GROK_REREVIEW(PASS) → PEACHES_VERIFY → REPORT/DONE
5. ACTIVE cleared; run JSON persists for restart recovery

**Note:** Untracked `nohup` from a short remote shell was reaped mid-sleep without EXIT — RULE forbids that path; prefer Shell-tracked children.

## Roles

Peaches = orchestration. Grok = plan/review. Cursor = app code. No Wolf application mutation. Production untouched.
