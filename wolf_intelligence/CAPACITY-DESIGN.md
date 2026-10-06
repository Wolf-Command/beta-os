# WI capacity awareness: design (DRAFT, not wired)

Owner directive 2026-10-06 09:49 WITA. Branch `build/wi-capacity-1` off `build/wi-real-workers-1`. Do not merge.

## Record (one per provider/worker)
| field | meaning |
|---|---|
| worker_id | WI worker id (cursor_sub, claude_pro_sub, codex_sub, ollama_local, gemini_free, grok_bot_sub) |
| plan | e.g. "Cursor Ultra $200/mo", "Claude Pro", "ChatGPT team (Codex)" |
| included_usage_pct | {pool: percent used}, e.g. {"cursor_models": 41, "other_models": 1}. Only values a source actually reported |
| remaining | numeric remaining capacity ONLY when the provider exposes it, otherwise null (never invented) |
| reset_at | ISO-8601 with offset, or null if unknown |
| velocity | from WI's own REAL dispatch ledger (records/dispatch.jsonl): calls in the last 24h and last 7d for the worker; pct_per_day only when two observations of included_usage_pct exist, else null |
| projected_exhaustion_before_reset | true / false / null (null whenever any input is unknown) |
| on_demand | "DISABLED" / "ENABLED" / "UNKNOWN". Informational only; WI never changes it |
| source | "owner_observed" / "api" / "ledger_derived" |
| observed_at | ISO-8601 timestamp with offset |

## Seed (`config/capacity-observed.json`)
- cursor_sub, owner_observed at 2026-10-06T09:49:00+08:00: plan "Cursor Ultra $200/mo", included_usage_pct
  {"cursor_models": 41, "other_models": 1}, on_demand "DISABLED", remaining null, reset_at null.
- claude_pro_sub, api (claude CLI /usage) at 2026-10-06T09:45:00+08:00: {"session": 15, "week_all_models": 1},
  session reset 2026-10-06T12:50:00+08:00, week reset 2026-10-10T19:00:00+08:00, usage credits off, so on_demand "DISABLED".
- codex_sub, api (codex rollout rate_limits) at 2026-10-06T09:45:00+08:00: plan "ChatGPT team", {"week": 2.0},
  reset 2026-10-13T07:23:50+08:00, credits none, so on_demand "DISABLED".
- ollama_local: plan "local", remaining null, on_demand "DISABLED" (no billing).

## Capacity state
AVAILABLE / CONSTRAINED (any pool >= 80% or projected exhaustion before reset) / EXHAUSTED (any pool >= 100% or a
recorded limit_hit since the last reset) / UNKNOWN (no record).

## Routing rule
`route_with_capacity(task_class, policy, registry, capacity)`: take the QUALITY order from `routing_policy.route`
(quality and specialisation first), then drop EXHAUSTED workers (reroute to the next) and move CONSTRAINED workers
after AVAILABLE ones only within the same quality tie group. Capacity never adds a worker. Metered workers are never
returned, whatever the capacity state. No capacity state, including on_demand "ENABLED" or every subscription
EXHAUSTED, may enable metered spend, call enforce_cost_cap with a raised cap, or change any spend env/config.
If every candidate is exhausted the result is an empty list, which means human decision, not a paid fallback.

## Tests (required)
seed loads; remaining stays null when not exposed; velocity from a temp ledger; projection true/false/null;
exhausted reroutes; constrained reorders only within a tie; exhaustive property test that no combination of
capacity states (including on_demand ENABLED) yields a metered worker or touches spend settings
(WOLF_INTELLIGENCE_MAX_COST_USD etc. unchanged, live_gate untouched).
