# Cursor mission — Intelligence on Needs You + Uma Issues (P2)

Date: 19 September 2026
Workspace: /Users/wolfterminal/beta-os
Beta only. Restart via `python3 scripts/beta_restart.py` if handlers change. Never touch :8787.

## Goal

Wire existing Authorised Knowledge Resolver + Decision Memory + Knowledge Resolution Path into:

1. Owner `/progress` Needs You (NEEDS_MATT only)
2. Uma Blu Issues (`list_issues` + Issues page)

Deterministic explanation / provenance. **No new agent. No LLM rationale as evidence. No chain-of-thought.**

## Reuse (do not reinvent)

- `scripts/core/knowledge_resolution.py` → `resolve_question(question, scope, actor_context=...)`
- `scripts/core/decision_memory.py` (already composed inside knowledge_resolution)
- `scripts/core/authorised_knowledge.py`
- `scripts/core/uma_ops_console.py` → `list_issues`
- `scripts/core/progress_read_model.py` → `_build_commissioning_missions` / owner view

## Build

### A. Blocker explanation primitive

Add a small pure helper (prefer `scripts/core/blocker_explain.py` or a function on uma_ops_console / progress_read_model):

`explain_operating_blocker(kind, context) -> dict`

Returns only:

- `why` — one human sentence
- `classification` — exactly one of `NEEDS_MATT` | `NEEDS_STAFF` | `NEEDS_POLICY` | `NEEDS_EXTERNAL_ACCESS`
- `decision` — optional `{id, summary}` if Decision Memory hit via resolve_question
- `provenance` — optional short authorised source labels (no raw secrets)
- `status` — knowledge status if resolved (AUTHORISED_SOURCE / OWNER_DECISION / CONFLICTED / NOT_FOUND / …)
- `honesty` — never claim invented authority / float / closer

Deterministic templates first (no invent):

| kind | why | classification |
| --- | --- | --- |
| policy_required (payment / PR) | No approved monetary authority limit exists for this action. | NEEDS_POLICY |
| opening_balance_required / float NOT_FOUND | No authorised opening-float source was found. | NEEDS_POLICY (not Matt by default) |
| closer_required / WAITING_FOR_CLOSER | A named closer has not been assigned. | NEEDS_STAFF |
| missing_payment_evidence | Paid claim is not verified payment — evidence still required. | NEEDS_STAFF |
| close_exception | Daily Close has an unresolved exception. | NEEDS_STAFF |

Then optionally call `resolve_question` with scope `{"entity":"BZG","brand":"Uma Blu"}` (or OWNER for cockpit) for related decisions (e.g. ClickUp / CRM decisions only if query matches). If CONFLICTED, surface CONFLICTED. If NOT_FOUND, say so honestly. Never expose attempts chain or prompts.

### B. Uma Issues

Extend each `list_issues` row with:

- `why`
- `classification`
- `explain` (same shape as above, omit empty fields)

Update `dashboards/bzg-uma-blu-issues.html` to show Why / classification in human language. No raw IDs as primary labels. Example rows stay labelled Example and must not feed Owner Pulse.

### C. Owner Needs You classification

Tighten `_build_commissioning_missions` / owner view:

- Needs You panel = **only** `classification == NEEDS_MATT` (or bucket NEEDS_YOU that maps to Matt authority).
- Add parallel buckets visible as business exceptions, not Matt tasks:
  - Needs staff
  - Needs policy
  - Needs external access
- Derive Uma-related owner exceptions from `list_issues` **excluding** `example: true`.
- OPENING BALANCE REQUIRED must **not** auto-land in Needs You.
- CLOSER REQUIRED must **not** auto-land in Needs You.

Update `dashboards/progress.html` to render the four buckets. Keep WOLF TRANSFORM / SYSTEM projection untouched.

### D. Tests

New or extended tests (keep existing green):

- policy_required → NEEDS_POLICY + fixed why sentence
- float NOT_FOUND → NEEDS_POLICY, not NEEDS_MATT
- closer → NEEDS_STAFF, not NEEDS_MATT
- example issues excluded from Owner Pulse / Needs You
- Needs You empty when only policy/staff blockers exist
- resolve_question CONFLICTED / NOT_FOUND surfaced without CoT
- no hard-coded 25.3 regression on progress
- dirty WIP four scripts never staged

Run:

```bash
python3 scripts/tests/test_uma_ops_console.py
python3 scripts/tests/test_uma_petty_cash.py
python3 scripts/tests/test_dashboard_truth.py
# plus new test_blocker_explain.py or equivalent
```

## Forbidden

Production · external writes · payment execution · invent float/limits/closer · new agents · Model C ledger edits · `git add .` · stage dirty WIP four.

## Done line

COMMIT: <hash>
TESTS: PASS=<n> FAIL=<n>
ROUTES: /progress /bzg/uma-blu/issues
SYSTEM: unchanged
EXIT:0
CURSOR_DONE
