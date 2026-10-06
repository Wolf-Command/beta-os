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
| grok_bot_sub | subscription | event-driven doorbell + lease (`grok_bridge.py`, see GROK-BRIDGE.md) | no, not push-dispatchable |
| xai_api | metered_api | not configured | **yes** |
| gemini_api | billing_unverified | generateContent, flash allowlist only | no |
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
