# Wolf Intelligence — REAL worker commissioning summary

Generated 2026-10-06T08:47:20+08:00 (WITA). Evidence class: REAL only (synthetic dev evidence excluded).

## Workers

| Worker | Status | Billing | Commissioning state | WI connectivity | Median latency (all REAL calls) |
|---|---|---|---|---|---|
| Claude Pro (subscription) | CONNECTED | subscription | HUMAN_COMMISSIONED + WI_CONNECTED | PASS | 9094.4 ms |
| Anthropic API (metered) | GATED (metered; stays off unless Owner approves) | metered_api | GATED_METERED (needs Owner approval) | GATED | - ms |
| ChatGPT/Codex (subscription) | CONNECTED | subscription | HUMAN_COMMISSIONED + WI_CONNECTED | PASS | 12162.5 ms |
| OpenAI API (metered) | NOT CONFIGURED | metered_api | NOT_CONFIGURED | GATED | - ms |
| Cursor (subscription) | CONNECTED | subscription | HUMAN_COMMISSIONED + WI_CONNECTED | PASS | 32066.4 ms |
| Grok Bot (subscription, pull-only) | NEEDS YOU | subscription | HUMAN_COMMISSIONED / NOT_WI_PUSH_DISPATCHABLE (pull-mode PASS) | PASS | - ms |
| xAI API (metered) | NOT CONFIGURED | metered_api | NOT_CONFIGURED | GATED | - ms |
| Gemini (free path) | CONNECTED | free | WI_CONNECTED (not human-commissioned) | PASS | 10184.9 ms |
| Gemini paid (metered) | NOT CONFIGURED | metered_api | NOT_CONFIGURED | GATED | - ms |
| Ollama llama3.2:3b (local) | CONNECTED | local | WI_CONNECTED (not human-commissioned) | PASS | 1873.5 ms |

## Best current per task class (n=1 per worker: low confidence, not a universal ranking)

| Task class | Best current | Default pick (tie broken by latency) | Ranking (mean quality) | Confidence | Caveat |
|---|---|---|---|---|---|
| coding | claude_pro_sub / gemini_free / codex_sub / cursor_sub (tie) | claude_pro_sub | claude_pro_sub 1.00, gemini_free 1.00, codex_sub 1.00, cursor_sub 1.00, ollama_local 0.17 | low (n=1 per worker; margin 0.00) |  |
| debugging | gemini_free / codex_sub / claude_pro_sub / cursor_sub (tie) | gemini_free | gemini_free 1.00, codex_sub 1.00, claude_pro_sub 1.00, cursor_sub 1.00, ollama_local 0.60 | low (n=1 per worker; margin 0.00) |  |
| security | gemini_free / claude_pro_sub / codex_sub / cursor_sub (tie) | gemini_free | gemini_free 1.00, claude_pro_sub 1.00, codex_sub 1.00, cursor_sub 1.00, ollama_local 0.00 | low (n=1 per worker; margin 0.00) |  |
| finance | claude_pro_sub / codex_sub / gemini_free (tie) | claude_pro_sub | claude_pro_sub 1.00, codex_sub 1.00, gemini_free 1.00, cursor_sub 0.78, ollama_local 0.11 | low (n=1 per worker; margin 0.00) |  |
| ux_product | codex_sub / claude_pro_sub (tie) | codex_sub | codex_sub 1.00, claude_pro_sub 0.96, cursor_sub 0.94, gemini_free 0.92, ollama_local 0.22 | low (n=1 per worker; margin 0.04) |  |
| large_context | gemini_free / claude_pro_sub / codex_sub / cursor_sub (tie) | gemini_free | gemini_free 1.00, claude_pro_sub 1.00, codex_sub 1.00, cursor_sub 1.00, ollama_local 0.00 | low (n=1 per worker; margin 0.00) |  |
| vision_document | gemini_free / claude_pro_sub / codex_sub / cursor_sub (tie) | gemini_free | gemini_free 1.00, claude_pro_sub 1.00, codex_sub 1.00, cursor_sub 1.00 | low (n=1 per worker; margin 0.00) | unsupported: ollama_local |
| structured_extraction | claude_pro_sub / codex_sub / gemini_free / cursor_sub (tie) | claude_pro_sub | claude_pro_sub 1.00, codex_sub 1.00, gemini_free 1.00, cursor_sub 1.00, ollama_local 0.77 | low (n=1 per worker; margin 0.00) |  |
| reasoning_planning | claude_pro_sub / gemini_free / codex_sub / cursor_sub (tie) | claude_pro_sub | claude_pro_sub 1.00, gemini_free 1.00, codex_sub 1.00, cursor_sub 1.00, ollama_local 0.00 | low (n=1 per worker; margin 0.00) |  |

Routing never selects a metered worker and never falls back to one. Metered workers need an Owner approval record.
