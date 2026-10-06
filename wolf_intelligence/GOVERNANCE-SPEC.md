# WI capacity governance build spec (build/wi-capacity-governance-1)

Owner: Matt Goss. Directive 2026-10-06 09:49 WITA: **PEACHES CAPACITY IS PROTECTED CAPACITY.**
You (the builder) implement this in the current worktree only. Python stdlib only (no new deps). Keep it additive:
do not rewrite existing modules beyond small hooks; do not weaken any existing test or gate.

## HARD RULES FOR THE BUILDER
- Work ONLY inside this worktree. Never touch ~/beta-os, ~/wi-runtime, ~/wi-capacity-1, ~/wi-real-workers*, any other dir.
- Never run git push / git pull / git checkout / git reset / git rebase. You may `git add` + `git commit` in this worktree.
- Never start a server on ports 8787, 8788 or 8799. Never call any network API (Anthropic/OpenAI/Gemini/xAI/Cursor).
  Tests must be fully offline and must set WOLF_INTELLIGENCE_STATE_ROOT and WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT to temp dirs.
- Never read or print secrets / .env values / API keys.
- Paid/metered spend stays OFF everywhere. Never raise or set WOLF_INTELLIGENCE_MAX_COST_USD / _MAX_DAILY_COST_USD.

## Concepts
Peaches (Chief of Staff) runs inside Grok Bot (worker id `grok_bot_sub`). Peaches/Grok is the Owner interface,
orchestrator, delegator, exception manager and result synthesizer; NOT the default builder/coder/debugger/researcher/
reviewer/analyst. Default flow: intent -> canonical WI work item -> classify -> select qualified worker -> dispatch ->
review/red-team where required -> evidence -> WI state update -> Peaches synthesizes.

Routing priority (lexicographic): QUALITY, then SPECIALISATION, then ALREADY-PAID (included) CAPACITY, then LATENCY,
then MARGINAL COST, subject to governance and availability. Never equalise percentages, never waste allowance, never
lower quality to use a subscription (a worker below the class quality floor is never eligible; capacity only reorders
workers inside the same quality tie band).

## Deliverable 1: canonical governance files (versioned in git, loaded at startup, FAIL CLOSED)
- `wolf_intelligence/config/governance/worker-allocation-policy.json` (version, policy_id, effective_from, all rules,
  thresholds, reason codes, protected classes, class -> family mapping, quality floors, specialisation, imbalance
  thresholds, reserve config). NOTHING may come from chat memory/prompt context.
- `wolf_intelligence/config/governance/worker-allocation-policy.schema.json` (JSON-Schema-style document) and a
  stdlib validator in code that enforces it. Schema MUST pin invariants with `const`/`enum`, e.g.
  `metered_fallback: "NEVER"`, `paid_spend: "OFF"`, `on_demand_policy: "NEVER_ENABLE"`, the exact allowed Grok reason
  code set, protected classes non-empty, thresholds monotonic (conserve < reserve < exhausted), numbers in range.
  A file that parses but violates an invariant is INVALID (cannot be used to fail open).
- `wolf_intelligence/config/governance/capacity-observed.json`: seed observations (Deliverable 2).
- New module `wolf_intelligence/governance.py`:
  `load_policy(path=None) -> PolicyLoad` with fields ok, mode ("ENFORCED" | "FAIL_CLOSED"), policy, sha256, errors.
  Missing / unreadable / invalid JSON / schema-invalid / invariant-violating -> mode FAIL_CLOSED: every Grok
  substantive dispatch DENIED, all metered spend DENIED, every decision carries `owner_action_required: true` and code
  `OWNER_ACTION_REQUIRED`, and an audit event `GOVERNANCE_POLICY_FAIL_CLOSED` is appended under
  `$STATE_ROOT/governance/audit.jsonl`. In FAIL_CLOSED, non-Grok subscription/local work may still be routed only
  using a hardcoded conservative default (quality-first order from benchmark evidence, never Grok, never metered),
  OR queued — your choice, but it must never be MORE permissive than ENFORCED. An env override
  `WOLF_INTELLIGENCE_GOVERNANCE_POLICY` may point at another file (tests), but it goes through the same validator.
  Loaded once at process startup (owner UI main() and CLI) and recorded (sha256 + mode) in the decision records.

## Deliverable 2: capacity model per provider (`wolf_intelligence/capacity.py`)
Record per provider/worker: worker_id, plan, included_usage_pct ({pool: pct}, only values a source reported),
remaining (null unless provider exposes it, NEVER invented), reset_at (ISO with offset or null), velocity (derived from
WI's own governance dispatch ledger: dispatch counts last 24h / 7d for that worker; pct_per_day only when two
observations of the same pool exist, else null), projected_exhaustion_before_reset (true/false/null; null when any
input unknown), on_demand ("DISABLED"/"ENABLED"/"UNKNOWN", informational; WI never changes it, and ENABLED never
permits spend), source ("owner_observed"/"api"/"ledger_derived"), observed_at (ISO with offset).
States NORMAL / CONSERVE / RESERVE / EXHAUSTED, thresholds per worker in the policy file (defaults in policy:
Grok conserve_at 30, reserve_at 60, exhausted_at 95; others conserve_at 70, reserve_at 85, exhausted_at 100).
Use the max pool pct that matters for the worker (configurable: e.g. Cursor routing uses "cursor_models").
Stale observations decay CONSERVATIVELY: effective_pct = observed_pct + decay_pct_per_hour * hours_since_observed
(config), capped at 100; observation older than `max_observation_age_hours` (config) -> state at least CONSERVE;
an unknown record -> treat per config (`unknown_state`, default CONSERVE for Grok). Decay never makes state better.
Projection true -> state at least CONSERVE.
Seed (Owner-observed 2026-10-06T09:49:00+08:00, source owner_observed):
- cursor_sub: plan "Cursor Ultra $200/mo", included_usage_pct {"cursor_models": 41, "other_models": 1},
  on_demand "DISABLED", remaining null, reset_at null.
- grok_bot_sub: plan "Grok Bot subscription", included_usage_pct {"weekly": 41}, remaining null, reset_at null,
  on_demand "UNKNOWN".
- also carry the existing design's seeds: claude_pro_sub (api, 2026-10-06T09:45:00+08:00, {"session":15,"week_all_models":1},
  on_demand "DISABLED"), codex_sub (api, 2026-10-06T09:45:00+08:00, {"week":2.0}, reset 2026-10-13T07:23:50+08:00,
  on_demand "DISABLED"), ollama_local (local, no billing).
Persisted observations live in `$STATE_ROOT/governance/capacity-observations.jsonl` (append-only); the repo seed is
merged in at load (newest observed_at per worker/pool wins). Provide `record_observation(...)` and `capacity_snapshot(now)`.
`now` must be injectable everywhere (tests, determinism).

## Deliverable 3: Grok protected reserve
Policy config `grok_reserve`: reserved for protected classes `owner_conversation`, `orchestration`,
`exception_handling`, `recovery_communication`, `critical_synthesis`. As Grok pressure rises, substantive
(non-protected) Grok work is routed away progressively and EARLIER:
- NORMAL: Grok substantive only with a valid reason code (below); a `grok_routing_penalty` still applies.
- CONSERVE: others preferred; Grok substantive only if reason code is OTHERS_UNAVAILABLE (verified) or
  EXPLICIT_JUSTIFIED; BENCHMARK_SELECTED no longer suffices.
- RESERVE: only protected classes go to Grok. Substantive -> other workers, else QUEUE.
- EXHAUSTED: nothing goes to Grok; protected classes QUEUE with a recovery note; everything else keeps flowing.
Monotonic: the set of work Grok may take must be non-increasing NORMAL -> CONSERVE -> RESERVE -> EXHAUSTED.

## Grok reason codes
Grok as a substantive worker is allowed only with one of: BENCHMARK_SELECTED (verified: Grok is in the top quality tie
band for that class in benchmark evidence), REQUIRES_GROK_ENVIRONMENT (requires justification text),
OTHERS_UNAVAILABLE (verified: no other eligible worker right now), EXPLICIT_JUSTIFIED (requires recorded justification
text, min length from config). Any other code (e.g. "peaches_can_do_it"), missing code, empty/short justification, or
an unverifiable claim -> REJECTED with code GROK_JUSTIFICATION_INVALID, audited. Protected classes need no code.

## Allocation (`wolf_intelligence/allocation.py`)
`decide(work_item, *, policy_load, capacity, ledger_view, now) -> Decision` (pure, deterministic). work_item has
id, task_class, optional requested_worker, grok_reason_code, grok_justification. Decision includes: decision
(DISPATCH | QUEUE | DENY), selected_worker, ranked candidates with per-key scores and exclusion reasons, task_family,
delegatable, protected, grok_reason_code + verdict, capacity states used, policy_sha256, policy_mode,
grok_routing_penalty used, alternatives_available (a qualified non-Grok worker with included capacity existed),
owner_action_required, decision_hash (sha256 of canonical JSON of the inputs-relevant fields; no timestamps).
Task classes: engineering family = coding, debugging, refactor, testing; reasoning/review family = reasoning_planning,
review, red_team, security, analysis, research, finance, large_context, structured_extraction, ux_product,
vision_document (config may refine); protected family = the five protected classes; operations = state_update,
evidence_collection, recovery.
Eligibility: never metered (`worker_registry.is_metered`), never billing UNVERIFIED (gemini_free while
"CONNECTED / BILLING UNVERIFIED / SPEND BLOCKED"; Gemini eligible only after billing governance proved, i.e.
billing_status VERIFIED), never below class quality floor (ollama_local only where benchmark quality >= floor),
never EXHAUSTED. Quality from `config/routing-policy-real.json` REAL benchmark rankings (cite it); tie band from config.
Specialisation from config: engineering -> cursor_sub first (Cursor first while included capacity available and
benchmark quality sufficient); reasoning/review -> claude_pro_sub and codex_sub substantial share (both specialised;
deterministic tie-break that alternates by work item id hash so neither is starved — that is NOT percentage
equalisation, just tie-break). Capacity: NORMAL > CONSERVE > RESERVE within the tie band. Then latency, then marginal cost.
If no eligible worker: QUEUE (wait), never a metered fallback. Any path that would consider a metered worker must go
through the canonical spend policy (`adapters.live_gate.enforce_cost_cap`) and governance `paid_spend: OFF` denies
first; add `metered_permitted() -> False` style check that consults both, and a test that no capacity state changes it.
Append every decision to `$STATE_ROOT/governance/dispatch-ledger.jsonl` (append-only) via `record_decision`.

## Deliverable 4: failover
Grok unavailable/exhausted must not stop canonical state updates, Cursor, Claude, Codex, local or eligible Gemini
jobs, testing, review, recovery or evidence collection. Code path: Grok state only ever removes Grok from candidates;
it never blocks the decision for other workers. Include a `grok_available: false` override (outage) in capacity.

## Deliverable 5: ROUTING IMBALANCE alarm (`wolf_intelligence/imbalance.py`)
Rolling window over the dispatch ledger (window_hours and/or window_decisions, min_samples, max_grok_share_delegatable
— all in config). Count only DELEGATABLE (non-protected) DISPATCH decisions where alternatives_available was true.
If Grok's share of those > threshold and count >= min_samples -> `ROUTING_IMBALANCE`: append audit event
(`$STATE_ROOT/governance/audit.jsonl`) and auto-tighten by raising the persisted `grok_routing_penalty`
(`$STATE_ROOT/governance/tightening.json`) by a configured step up to a configured max; subsequent decide() uses it.
Never triggers on raw capacity percentages or on protected-class work. Tightening only ever makes Grok less likely.

## Deliverable 6: no metered fallback (as above). Paid spend OFF in every capacity state.

## Startup / persistence / surfaces
- `owner_ui_server.main()` loads governance policy + capacity at startup and prints one status line (policy sha256
  prefix, mode, Grok state). Add env `WOLF_INTELLIGENCE_UI_PORT` (default stays 8799); refuse 8787 and 8788.
- GET `/api/governance/status` (token required like the board) -> policy mode/sha/version, capacity snapshot, penalty.
- POST `/api/governance/decide` (token required) body = work_item JSON -> decision (recorded in ledger).
- CLI: `python3 -m wolf_intelligence governance status` and
  `python3 -m wolf_intelligence governance decide --task-class X [--id ID] [--grok-reason CODE] [--justification T] [--now ISO]`
  printing JSON.
- `new_orchestrator_session()` (or similar) building a fresh context purely from files (no globals carried over).

## Deliverable 7: tests `wolf_intelligence/tests/test_capacity_governance.py` (offline, temp roots), one clearly named test per item:
(a) engineering does not default to Grok when Cursor eligible
(b) reasoning/review does not default to Grok when Claude or Codex eligible
(c) Grok pressure -> earlier delegation, monotonic over NORMAL->CONSERVE->RESERVE->EXHAUSTED (set of Grok-allowed
    work non-increasing; and a sweep over pct 0..100 never re-allows Grok as pct rises)
(d) Grok exhaustion/outage does not stop non-Grok workers (all non-Grok families still DISPATCH)
(e) real process restart: start `python3 -m wolf_intelligence.owner_ui_server` subprocess on a free ephemeral port
    (never 8787/8788/8799) with a temp state root, record decisions via POST, kill it, restart, compare status +
    decisions (identical decision_hash values and policy sha)
(f) new Peaches session: a separate fresh subprocess / new orchestrator context with no prior memory gives identical
    decisions
(g) no metered fallback when all subscriptions EXHAUSTED -> QUEUE, never metered worker
(h) paid spend OFF in every capacity state combination (spend env unchanged, metered never selected, live_gate denies)
(i) imbalance alarm fires on disproportionate delegatable Grok share, audit event logged, penalty raised, next
    decision shifts away; does NOT fire for protected-class work or from raw capacity percentages
(j) policy file fail closed: missing, corrupt JSON, schema-invalid, invariant flip (e.g. metered_fallback "ALLOWED",
    paid_spend "ON", extra reason code) -> FAIL_CLOSED, Grok substantive denied, metered denied, OWNER_ACTION_REQUIRED
(k) invalid/missing Grok justification rejected (missing, "peaches_can_do_it", EXPLICIT_JUSTIFIED w/o text,
    BENCHMARK_SELECTED unverifiable, OTHERS_UNAVAILABLE when others are available)
Plus capacity tests: remaining stays null unless exposed, stale decay conservative, velocity from temp ledger,
projection true/false/null, seed values exact.
The FULL existing suite must still pass: `python3 -m unittest discover -s wolf_intelligence/tests -v`.

## Docs
Add `wolf_intelligence/GOVERNANCE.md` (short: what, where config lives, states, reason codes, how to run tests).
Commit with clear messages. Do not push.
