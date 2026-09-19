# GROK PLAN — Devi Uma commissioning P0 (Close history + PR detail/receive) — 2026-09-19

## Mandate
Real Devi phone feedback. Highest priority. Full Uma commissioning stays NOT_DONE until these work.

## Goals (this slice)
1. **Close**: Today + Previous Closes (list + detail) from existing `venue_daily_closes` / evidence / audit. No second close store. No invent prior closes.
2. **PR detail**: Mobile detail for a PR (Wolf or Existing/Alchemist) with source fields only — no invent.
3. **Receive Goods**: Append-only Wolf receive action with partial support when line quantities exist; Evidence/Audit; do not rewrite Alchemist as verified.
4. **Today for Devi**: Prefer actionable cards for her role; non-actionable → “Waiting on [role] — no action needed from you.” Global rule.
5. **Close buttons**: Hide/disable actions she cannot perform (capability-aware).
6. **Completion Register**: leave items OPEN until evidenced; update when each is proven.

## Explicit defer (register stays OPEN / NEEDS_POLICY)
- Full PR field editing that rewrites Alchemist → **append-only correction only** in this slice; free-form edit semantics stay NEEDS_POLICY.
- Granting Devi payment approval → **do not**. Show Waiting for approval + role if known.

## Design

### Close history
- `/uma-blu-close` UI: tabs **Today** | **Previous**
- Previous: `GET` list from venue_daily_closes newest-first (business_date, state, declared cash, ESB snapshot fields if present, variance/exception flags, operator labels if stored — never invent)
- Detail: existing close record + evidence refs + audit sentences; legacy vs Wolf-verified chip if applicable
- If zero history: honest empty (“No previous closes recorded in Wolf yet”) — Alchemist has cash_count=0 so do not fake

### PR detail route
- `/bzg/uma-blu/bills/<pr_id_or_num>` or query `?pr=`
- Merge Wolf PR + Alchemist RO projection by pr_num / provenance
- Show: pr_num, supplier, dept, requester, date, lines (from pr_order_lines if interpretable), status, Existing chip
- Actions section: only actions permitted for authenticated person

### Receive Goods
- New append-only table e.g. `bzg_ops_receipt_events` + line rows (Beta catalog) with provenance, receiver person_id, timestamps, partial/complete, notes, evidence_id
- POST gated by venue receive permission (discover from existing RBAC; fail closed)
- Partial: outstanding = requested − sum(received); status COMPLETE only when outstanding≈0
- Alchemist “Received” remains source claim; Wolf receipt is separate

### Today filter
- `today_cards` accepts operator context: filter to actionable for HFB/Devi; unpaid ledger / opening float may move to Issues or “Waiting on policy/finance” copy without fake Open→
- Implement helper `actionable_for(person, card)` 

### Permission UX Close
- Read capability from existing auth; disable Open/Submit/Reconcile if denied; plain explanation

## Tests
- Close list/detail empty + with fixture closes
- PR detail renders Alchemist fixture without inventing amount
- Receive partial then complete
- Today non-actionable wording
- Close buttons hidden when denied
- No Alchemist writes
- WIP four preserved

## Success / Matt ping
When mobile prove + Peaches verify: **DEVI FEEDBACK FIX READY TO RETEST** with screenshots and exact action list.

## Slice
`BF-devi-feedback-p0-20260919`
