# Grok plan — Uma history + issues read models (P4)

Overnight lane p4 under OWNER OVERNIGHT RELEASE 2026-09-18.

## Why now

P3 petty (`99d0970`) is PASS. Ops console already exposes `/api/bzg/uma-blu/history` and `/issues`, but live History is empty (0 `uma_ops_console` audit rows) and Issues/History read models are not yet proven against petty + PR transitions as a coherent operator surface.

## Bound

Beta only. Read models + audit emit for existing Uma ops / petty transitions. No second history table. No float invention. No Devi seat. No payment execution. No Production. No Model C ledger writes. No ESB/ClickUp/Telegram/bank writes.

## Success

- Every Uma ops / petty state transition that should be auditable writes `audit.record_event` with source `uma_ops_console` (or keep existing source contract if already correct — fix emit gaps).
- History API returns human lines for those events on live Beta after fixture transitions in tests.
- Issues read model includes petty POLICY_REQUIRED / open-tin attention (not only PR policy).
- Existing pages keep working; optional thin History polish on Today only — no new Finance/Venues/People surfaces.
- Tests green; beta_restart once if route/handler changes need live paint.

## Mission

`docs/deliveries/CURSOR-MISSION-UMA-HISTORY-ISSUES-2026-09-19.md`
