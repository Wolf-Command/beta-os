# Wolf Intelligence — REAL workers (commissioning, routing, benchmark)

Built 2026-10-06 (WITA) on branch `build/wi-real-workers-1`, off PR #2 head `4ac2a2d`.

## One worker per provider × billing path

| worker_id | billing_class | path | gated |
|---|---|---|---|
| claude_pro_sub | subscription | `claude -p`, child env scrubbed of ANTHROPIC_API_KEY & co, preflight `claude auth status` must say `authMethod=claude.ai` | no |
| anthropic_api | metered_api | api.anthropic.com | **yes** (Owner approval record) |
| codex_sub | subscription | `codex exec --ignore-user-config -s read-only -c forced_login_method="chatgpt"`, OPENAI_API_KEY/CODEX_API_KEY scrubbed, preflight `codex login status` must say ChatGPT | no |
| openai_api | metered_api | api.openai.com (not configured) | **yes** |
| cursor_sub | subscription | `cursor-agent --print --mode ask --trust --workspace <scoped temp dir>`, CURSOR_API_KEY scrubbed, preflight `cursor-agent status` | no |
| grok_bot_sub | subscription | PULL ONLY (see below) | no, not push-dispatchable |
| xai_api | metered_api | not configured | **yes** |
| gemini_free | free (Owner-declared) | generateContent, flash allowlist only | no |
| gemini_paid | metered_api | not configured | **yes** |
| ollama_local | local | 127.0.0.1:11434 | no |

Code: `worker_registry.py` (descriptors + evidence-derived facts), `adapters/subscription_cli.py`,
`adapters/grok_pull.py`, `real_dispatch.py` (gating, no fallback, REAL evidence), `routing_policy.py`,
`real_bench/` (pack + graders + blind cross-review), `real_commission.py`, `real_report.py`.

## Billing is explicit, never environment precedence

Persistent ANTHROPIC_API_KEY injection on the Studio (value never read into evidence):
- `~/.zshenv` line 1: `export ANTHROPIC_API_KEY=…` — sourced by EVERY zsh, including non-interactive
  `zsh -c` children (Grok Bot local-exec shells, scripts, Cursor/IDE terminals). This is why unsetting it in one
  Terminal tab does not help.
- `~/.zshrc` line 13: same export again for interactive shells (same fingerprint).
- Not set via launchctl setenv, not in any LaunchAgent plist EnvironmentVariables, not in ~/.claude settings
  (no `env`, no `apiKeyHelper`), and the `ANTHROPIC_API_KEY=` line in `~/beta-os/.env` is empty.
- Proof of the hazard: with the inherited env, `claude auth status` reports `authMethod: api_key,
  apiKeySource: ANTHROPIC_API_KEY`; with the scrubbed env it reports `authMethod: claude.ai, subscriptionType: pro`.

The adapter removes the key from the child env and refuses to run unless the preflight reports the subscription.
The Anthropic API is a separate, gated worker. The persistent export was NOT modified (Owner rule).

## Grok Bot: HUMAN COMMISSIONED / NOT WI-PUSH-DISPATCHABLE

Grok Bot.app v0.66.0 has no local API, no CLI and no deep link that takes a prompt and returns an answer
(`grokbot://` and `sand://` only open the app or OAuth callbacks). The local-exec daemon is inbound: a Grok Bot cloud
session drives the Studio. Its credential file must not be replayed. So WI writes jobs to
`<REAL root>/grok_bot_pull/outbox/` and a human-started Grok Bot session answers into `inbox/`. Smallest real fix
for autonomous dispatch: a Grok Bot scheduled run that drains the outbox on a timer, or a vendor-supported Grok Bot
API/CLI.

## Evidence isolation

REAL evidence goes to `WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT` (default `~/wi-real-evidence`), never inside
`~/beta-os`. Every record carries `evidence_class=REAL, synthetic=false`; readers ignore anything else, so
synthetic dev history never reaches routing. Runs set `WOLF_INTELLIGENCE_STATE_ROOT` to a scratch dir as well.

## Run

```
R=~/wi-real-evidence/real-workers-YYYYMMDD
export WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT=$R WOLF_INTELLIGENCE_STATE_ROOT=$R/wi-state-scratch
python3 -m wolf_intelligence.real_commission billing          # no model calls
WOLF_INTELLIGENCE_LIVE_SUBMIT=1 python3 -m wolf_intelligence.real_commission connectivity
WOLF_INTELLIGENCE_LIVE_SUBMIT=1 python3 -m wolf_intelligence.real_bench.runner run --run-id bench-...
python3 -m wolf_intelligence.real_report --out-dir $R
python3 -m wolf_intelligence.real_commission approve-metered anthropic_api 1   # Owner, interactive TTY only
```

## 2026-10-06 09:39 hardening (Vesper B4-1, Owner order)

- **Gemini = CONNECTED / BILLING UNVERIFIED / SPEND BLOCKED.** Every Gemini execution path passes
  `adapters/live_gate.gemini_spend_gate`, which is the canonical f7c78f2 spend policy (`enforce_cost_cap`), with no bypass.
  A registry "free" declaration does not skip it. Path audit (wolf_intelligence/): the only Gemini endpoints are
  `adapters/gemini.py` (legacy worker `gemini`) and `adapters/subscription_cli.py` (`gemini_free`). Both call the gate
  before the endpoint, and a static test enforces this. There are no google SDK imports. Dispatch has no fallback.
  Routing excludes workers with unverified billing. The gen-1 harness no longer uses Gemini as a reviewer.
  Tests: `tests/test_gemini_gate.py` (adapters, owner caps with unverified prices, registry-free-not-a-bypass, dispatch,
  retry x3, fallback, harness, static audit).
- Outside wolf_intelligence (not changed here; they are protected surfaces):
  - `scripts/llm_orchestrator.py` `call_gemini` is a direct HTTP call. It is used by serve_beta (the Content Engine).
    Its key is read from beta-os/.env, where GEMINI_API_KEY is EMPTY.
  - `scripts/core/bzg_close_vision.py` (Daily Close) only names "gemini" in an error filter, and its `call_gemini_vision`
    delegates to an external model_router.
  These need an Owner decision.
- `config/routing-policy-real.json` and `routing_policy.learn()` now carry `label: "DRAFT - NOT WIRED"`, `wired/active: false`.
- The cursor worker runs with `--sandbox enabled` (live-verified: it can still read a staged workspace file).
