# RULE ★ Build Factory Self-Driving — 2026-09-17

**LOCKED by Matthew.** Founder must not poll the engineering factory.

## Roles unchanged

| Role | Owns |
|------|------|
| Peaches | Orchestration through completion; state; advance; escalate only on true blockers |
| Grok | Plan / review actual diff / red-team |
| Cursor | Application code on Beta only |

Peaches never writes Wolf application code to “speed up” the factory.

## Loop after Matt approves a slice ONCE

START → GROK_PLAN → CURSOR_BUILD → TESTS → GROK_REVIEW → (FIX→CURSOR_FIX→TESTS→GROK_REREVIEW)* → PEACHES_VERIFY → REPORT_MATT → STOP

Matt does **not** type `status` / `continue` / `is it done` between stages.

## Heartbeats to Matt

1. STARTED (optional, one line)  
2. BLOCKED (only DECISION / HUMAN_ACTION / SAFETY / FACTORY_FAILURE)  
3. FINISHED (full evidence)

Not blockers: Cursor still running, Grok reviewing, tests running, waiting for exit, recoverable transport fail, in-scope red-team finding Cursor can fix.

## Red-team fix loop

In-scope FAIL → Peaches records → Cursor bounded fix → tests → Grok re-review → auto continue. Escalate only if fix expands approved scope / policy.

## Completion detection

**Preferred child launch (Peaches runtime):** Mac `Shell` with background (`block_until_ms` 0) so completion is tracked, then Await / completion wake OR `bf_watch.py` on the written pid+log. Do **not** rely on untracked `nohup` from a short remote shell — those children can be reaped without writing EXIT.

On launch of Cursor Local (`cursor-agent -p …`) or any factory child:

1. Write/update `state/build-factory/runs/<run_id>.json`  
2. Point `state/build-factory/ACTIVE` at that run_id  
3. Capture wrapper pid + log path  
4. Prefer staying in-session until exit is verified (Await / log EXIT line)  
5. If turn must end: leave ACTIVE + rely on `build-factory-watch` routine + treat Shell-completion wakes as mandatory advance for ACTIVE runs (**never silent**)  
6. Verify CLAIMED≠VERIFIED: only mark CURSOR_DONE when log has EXIT and/or process gone + commit/artifact evidence

## Timeouts

Default Cursor slice soft timeout: 45 minutes. Hard escalate: 90 minutes with no log progress. Inspect pid + log before escalate. No blind re-launch of destructive ops.

## Restart recovery

On Peaches wake / Mac reconnect: read ACTIVE run → bf_watch → resume stage or report BLOCKED. Do not rely on chat alone.

## State schema (minimum)

run_id, slice, approved_scope, stage, grok_plan_ref, cursor_log, cursor_pid, head_commit, tests, review_status, findings[], fix_attempts, blocker, final_state, updated_at

## Forbidden

Matt-as-poller · silent ignore of ACTIVE completion · Dual Approval in this mission · Authority seed · Production · Wolf app code changes for this fix


## MUST — Deployed-route UI gate (2026-09-17)

Before marking a UI / `serve_beta.py` slice **FINISHED**:

1. Restart Beta via LaunchAgent (`scripts/beta_restart.py` or `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta`). Never touch `:8787`.
2. `python3 scripts/prove_deployed_ui_routes.py` must **PASS** against real `127.0.0.1:8788`.
3. Ephemeral/unit HTTP greens alone are **not** acceptance.

Canon: `docs/RULE-UI-Finished-Deployed-Route-2026-09-17.md`.


---

## Amendment 2026-09-18 — Overnight stall repair

**Event:** BF-uma-close-nits Cursor finished 2026-09-17 21:58 WITA (`CURSOR_DONE`, commit `4259d31`) but stayed `WAITING_CURSOR` until Matt `status` at 2026-09-18 06:07 WITA (~8h9m). **90-DAY DISAPPEARANCE TEST: FAIL.**

### Root cause (compound)

1. **Completion detection defect:** `bf_watch.py` required log line `EXIT:N` for `child_done`. Cursor agent prints `CURSOR_DONE` only → `next_action=INSPECT` not `ADVANCE`.
2. **Dead watcher overnight:** build-factory-watch cron was `*/5 8-19` weekdays — last tick ~19:55; Cursor finished 21:58; no overnight ticks until morning.
3. **Advisory-only watch:** `bf_watch` never wrote the next stage. Advancement depended on Peaches being woken and acting — founder dependency for ordinary engineering state changes.

### Fix

- `bf_watch.py`: `CURSOR_DONE` + process gone ⇒ treat as EXIT:0 / ADVANCE
- `bf_advance.py`: deterministic `WAITING_CURSOR` → `GROK_REVIEW` + `WAKE.json` (`require_matt=false`)
- Watch routine schedule: weekday `*/5` **24h** (overnight ACTIVE missions)
- Tests: `scripts/tests/test_build_factory_advance.py`
- Proof: `docs/deliveries/FACTORY-ADVANCE-PROOF-2026-09-18.md`

### Remaining limitation

Auto-advance persists GROK_REVIEW + WAKE. Grok review body still needs Peaches/watch to execute (software cannot replace Grok judgment). It must **not** wait for Matt status.

---

## Amendment 2026-09-18 — Deterministic lane queue

**Software:** `scripts/build-factory/bf_queue.py` (extended `bf_watch.py` / `bf_advance.py`).  
**Tests:** `scripts/tests/test_build_factory_queue.py` · proving: `scripts/build-factory/proving/prove_queue_mission.py`  
**Proof:** `docs/deliveries/FACTORY-QUEUE-PROOF-2026-09-18.md`

### Machine

Persisted mission file: `state/build-factory/missions/<id>.json` (runtime gitignored; tests use temp dirs).

A mission has an **ordered authorised lane list**. Each lane: `id`, `bound`, `status`, persisted `retry_count`, optional `completion_commit`.

| Rule | Behaviour |
|------|-----------|
| Slice close | Selects next authorised runnable lane and can start it — **no human pick** |
| Policy block | Lane → `BLOCKED` with reason; later authorised safe lanes continue |
| Grok FAIL | → `WAITING_CURSOR_FIX`; increment persisted retry count |
| Retry ceiling | Constant `RETRY_CEILING=2` (3 attempts total); exhaustion → `ESCALATED`, no loop |
| Restart | Reconstruct from mission file only — never memory-only flags |
| Completion commit | Restart must **not** relaunch a lane that already has `completion_commit` |
| No invention | Lanes outside the mission list are refused |
| Boundaries | `guard_lane_bound()` refuses Production / external-write / owner-authority even if a lane asks |

Idempotent: duplicate completion / watcher / Grok-FAIL events do not double-complete or increment past the ceiling.

This is **deterministic queue software**, not a new agent. Peaches still orchestrates Grok judgment; Cursor still writes application code. No maturity credit from proving missions.
