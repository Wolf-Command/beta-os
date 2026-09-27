# Devi Uma Blu UX preflight — 19 Sep 2026

**Verdict: FIXED** (not commissioned)

Bounded HTML/CSS/JS presentation only. No business logic, permissions, policy, or architecture change. Canonical API states (e.g. `float_status=NOT_FOUND`) preserved under human copy.

## Fixes
- Today: hide example-only fixture cards; dedupe Daily close (Now only); human titles; short nav; word-wrap
- Petty: human opening-balance banner (no NOT_FOUND in staff copy)
- Bills: hide raw `pr_id`; split live vs practice
- Issues: drop Knowledge status / provenance lines; practice demoted
- Close: add matching phone nav; soften Honesty heading
- Nav labels phone-fit: Today · Bills · Petty · Close · Issues · History

## Residual
- Daily Close action buttons still visible; server-side denial remains. Capability-aware hide not in this pass.
- Screenshots from real Beta HTML + live `today_cards()` / `list_petty()` data paint (phone 390×844). CF JWT not in screenshot path.

## Phone URL
https://beta.wolfcommand.net/bzg/uma-blu

## Evidence
docs/deliveries/devi-ux-2026-09-19/
