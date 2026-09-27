# GROK PLAN — GGV Content Machine x NAS Haikal Prep — 2026-09-22

**Run id:** `BF-wolf-ggv-content-nas-haikal-prep-20260922`
**Prior:** NAS Library Upload P0 ENGINEERING PASS=60 (staff_ready=false; Haikal human not_started)
**Bound:** Beta `:8788` only. Production `:8787` sacred — no mutate.
**Head note:** shared dirty `serve_beta` OK to extend surgically; defer commit if needed.

## Goal
Make GGV Content Machine (CAP-GGV-01) actually drive through the new NAS Library path so Haikal can human-test upload/search/preview/download on Beta without inventing staff go-live.

Wolf = staff interface. NAS = canonical media (already under `_Imports/Wolf-Library`). Do NOT invent a second upload product. Do NOT destroy NAS. Do NOT invent CAP PROVEN/READY or staff_ready=true.

## In scope
1. Content Engine 2.0 / Smart Upload operator path for Haikal subject: clear next-action when NAS connected; NAS badge + provenance visible on phone + desktop.
2. GGV Content Machine desk (or existing content hub) surfaces: library search hits NAS-backed assets; empty states honest; fail-closed wrong brand.
3. Haikal retest checklist doc (upload → search → preview → select/ZIP → wrong-scope deny) — engineering artifact, not human sign-off.
4. Integration Health still shows ClickUp+Telegram RETIRED.
5. Tests: unit + live Beta prove under temporary `development_assertion`, then restore `cloudflare_access`. Honesty proven=false ready=false staff_ready=false.
6. `:8787` pid untouched.

## Out of scope
- Haikal human sign-off (Needs Matt / Needs Staff — park after engineering PASS)
- Matthew adding Cloudflare Access seats (Owner-only)
- Full 40k NAS tree hash; B2 restore; Production deploy
- FIN/HR/Trading; invent PROVEN/READY; Metricool publish; Email auto-send

## Success / EXIT
- Suite PASS FAIL=0
- Live `:8788` Haikal subject can complete library loop in-process; wrong-scope 403
- Checklist doc written; staff_ready remains false
- GROK-REVIEW + claim; `:8787` untouched

## Cursor rules
- ASCII prompts only
- Prefer Shell-tracked short pointer prompt to this plan
- Read RULE-Wolf-Connection-Commissioning-NAS-GoLive-2026-09-22.md
- Preserve Haikal-liked UX; fix architecture underneath

EXIT: SUCCESS when tests + review evidence written.
