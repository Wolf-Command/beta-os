# Wolf Intelligence — working status (build continues until morning)

## Working now
- Owner UI **http://127.0.0.1:8799/** via LaunchAgent KeepAlive (`com.wolfcommand.wolf-intelligence-owner-ui`)
- SQLite canonical work-item store + JSON mirror + events/audit
- Shadow dispatcher create→route→recommend→isolated submit
- Worker health report (Grok/Cursor/Peaches CONNECTED; Anthropic CONNECTED via OpenClaw auth-profiles; ChatGPT PARTIAL; OpenAI API/Gemini UNAVAILABLE empty keys; Ollama CONNECTED RETIRE CANDIDATE)
- Local Ollama benchmarks wrote real scores for llama3.2:3b only
- Learning outcomes + stats store; hourly overnight tick
- Shadow compare vs factory (cursor) agreement high; $0 expensive execute

## Stub / deferred
- Paid API benchmarks (not run — avoid spend spikes)
- ChatGPT/Grok consumer plan USD (UNKNOWN — need Owner account UI)
- Beta `/owner/intelligence` route code ready; **Beta reload held** (Daily Close/Petty safety). Use sidecar until reload window.
- Live (non-shadow) dispatch — Owner DN-006

See `config/decisions-needed.json` and `OWNER-UI-HOWTO.md`.
