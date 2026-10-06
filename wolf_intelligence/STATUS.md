# Wolf Intelligence — working status

Truth ladder: BUILT → SYNTHETIC TESTED → CONNECTED → REAL WORKER TESTED → SHADOW PROVED → READY FOR HUMAN → HUMAN COMMISSIONED.

Nothing below is SHADOW PROVED. A shadow record is SHADOW PROVED only when one real run carries every one of: the factory's per-job current-system worker, Wolf's recommendation, the real outcome, the test result, the time, and cost or capacity where that number is known. Mocked and synthetic results are not that run. This checkout has no per-job BF worker file, so the current-system hint is UNKNOWN until Studio scans `state/build-factory/runs`. The router does not fill that hint with a named worker.

Wolf Intelligence is not the 06:08 P0 supervisor. It runs on the Studio and dies with it. The independent off-Studio watcher is a separate component (NAS DSM task 7).

## Phases

| Phase | Truth |
|---|---|
| 1 Control plane | BUILT / SYNTHETIC TESTED |
| 2 Workers | Health CONNECTED or PARTIAL where the probe said so. REAL WORKER TESTED only for the ollama and cursor CLI probes below. Adapter live-submit is BUILT and covered by mocked unit tests. |
| 3 Benchmarks | BUILT. Paid benches not run. |
| 4 Learning | BUILT / SYNTHETIC TESTED. A row counts as human only with a non-empty actor, a source other than synthetic, and an effective_source that starts with human. Demo and harden samples do not. History is not rewritten; the next recompute drops actor-less rows from the human counters. |
| 5 Owner UI | BUILT. Sidecar is loopback only: `127.0.0.1:8799`. POST requires `WOLF_INTELLIGENCE_UI_TOKEN` as a bearer or session token. If that token is unset, the server still starts and every POST returns 401. The token is never logged. |
| 6 Shadow compare | SYNTHETIC TESTED. Not SHADOW PROVED. |

## Workers

| Worker | Ladder | Live submit |
|---|---|---|
| ollama | REAL WORKER TESTED for the 2026-10-06 direct `/api/generate` probe (`llama3.2:3b`, about 2051 ms, `{"ok":true,"n":42}`, USD 0). Adapter live path is BUILT, not yet re-proved through the adapter on Studio. RETIRE CANDIDATE. DO_NOT_DELETE. | `execute=True` and `WOLF_INTELLIGENCE_LIVE_SUBMIT=1` → `POST 127.0.0.1:11434/api/generate`. Off by default. |
| cursor | REAL WORKER TESTED for the 2026-10-06 `cursor-agent --print --mode ask` probe (about 17792 ms, same JSON, inside the prepaid USD 300/month pool; per-call metered USD UNKNOWN). Adapter live path is BUILT, not yet re-proved through the adapter on Studio. | Same gate → `cursor-agent --print --mode ask --trust --workspace <temp dir>`. |
| grok_bot | CONNECTED (health via `~/.grokbot`). Not REAL WORKER TESTED. Plan USD UNKNOWN. | UNSUPPORTED. The Grok Bot app is not spawned. |
| peaches | CONNECTED as CoS only, not a brain. Not REAL WORKER TESTED. | UNSUPPORTED. |
| openai_chatgpt | PARTIAL. Plan USD UNKNOWN. Separate from `openai_api`. | UNSUPPORTED. |
| claude_sub | PARTIAL. Owner-declared USD 25/month, pool `claude_sub_25`, separate from `anthropic_api`. | UNSUPPORTED. |
| openai_api | UNAVAILABLE (empty key in the discovery probe). Not REAL WORKER TESTED. | Gated: key and per-call cost cap, plus the env flag. The cap is on by default: an unset cap refuses the call. No call from this change. |
| anthropic_api | CONNECTED on Studio via credential presence. Not REAL WORKER TESTED. API pool is not the USD 25 subscription. | Same paid gate. Haiku is default-fast, not best. |
| gemini | UNAVAILABLE (empty key). Free pool `gemini_free` USD 0. Not REAL WORKER TESTED. | Gated: key and cost cap. Paid model names are blocked. |

## Ledger

| Pool | Monthly USD |
|---|---|
| `cursor_sub_300` | 300 prepaid. Per-call metered USD UNKNOWN. |
| `claude_sub_25` | 25, separate from `anthropic_api`. Per-call metered USD UNKNOWN. |
| `gemini_free` | 0 |
| `ollama_local` | 0 |
| `grok_sub` | UNKNOWN. Not guessed. |
| `chatgpt_sub` | UNKNOWN. Not guessed. Separate from `openai_api`. |

## Studio commands for a real tiny shadow

Run these on the Studio, in `~/beta-os`, on this branch. They do not touch Production, Daily Close, Petty Cash, or the factory supervisor. The Owner UI stays on `127.0.0.1`.

```bash
cd ~/beta-os
unset WOLF_INTELLIGENCE_LIVE_SUBMIT

# Ollama only. Records a ledger row at USD 0. Does not take factory action.
WOLF_INTELLIGENCE_LIVE_SUBMIT=1 python3 -m wolf_intelligence live-submit --worker ollama --execute

# Cursor CLI only. Prepaid pool. Per-call USD stays UNKNOWN.
WOLF_INTELLIGENCE_LIVE_SUBMIT=1 python3 -m wolf_intelligence live-submit --worker cursor --execute

# Shadow: router recommendation is recorded, cursor and ollama run the same tiny sum, in parallel.
# SHADOW PROVED only if factory history has a per-job worker and the record has outcome, test, time, and known cost or capacity.
WOLF_INTELLIGENCE_LIVE_SUBMIT=1 python3 -m wolf_intelligence shadow-real --n 1 --primary cursor --shadow ollama
```

The tiny prompt is: Return the JSON `{"ok":true,"n":<sum of 17 and 25>}`. Expected `n` is 42.

Evidence lands in `state/wolf-intelligence/shadow/real-shadow-*.jsonl` and under `real_shadow` in `wolf_intelligence/config/shadow-compare-phase6.json`. If `state/build-factory/runs` has no per-job worker marker, `actual_current_system_worker` stays empty and the run is not SHADOW PROVED.

## Still deferred

- Paid API benchmarks.
- ChatGPT and Grok plan USD until the Owner account UI says so.
- Beta `/owner/intelligence` reload. Use the sidecar.
- READY FOR HUMAN and HUMAN COMMISSIONED. Not claimed.
