# CURSOR MISSION — Owner knowledge resolution path

**Beta only.** Workspace `/Users/wolfterminal/beta-os`.
**Compose existing modules. Do not create an agent, a persona, a route in `scripts/serve_beta.py`, or a UI.**

Do not edit:
- `state/model-c-baseline-assessments.json`
- `state/model-c-score-history.jsonl`
- Progress dashboard
- scoring-rule docs
- `scripts/habitat-lead-sync.py`
- Production
- ClickUp scripts

## What to build

One new module, `scripts/core/knowledge_resolution.py`.

One function, `resolve_question(question, scope, *, actor_context)`.

It calls, in this order, and does not skip a step:

1. Validate scope. Refuse a missing scope. Refuse a brand scope that does not match the question's brand. No cross-brand bleed.
2. Check canonical structured truth only where a canonical field already exists. Empty canonical is `NOT_CANONICAL`. It is not `UNKNOWN`. An empty field is not a reason to ask a human.
3. Decision Memory. Call existing `recall` with the exact registered question string. RBAC still applies: no permission context means fail closed (`INACCESSIBLE` for the decision side, not a guessed answer). Rows with `query_keys` match only on exact casefolded equality.
4. Authorised Knowledge Resolver. Call existing `resolve` with the Habitat live registry `scripts/core/data/akr_habitat_live_registry.json` only. No new roots. No filesystem crawl. No public web. No source write.
5. Compare the Owner decision, if any, with the source evidence, if any.
6. Return one result. No model call. No chain of thought. No invented rationale.

## Result shape

Every result includes: `answer`, `status`, `authority`, `provenance`, `confidence_basis`, `conflict`, `attempts`.

`attempts` lists what was searched and the outcome of each search. It is not reasoning.

Allowed `status` values:

- `CANONICAL` — a canonical structured field already holds the answer
- `OWNER_DECISION` — an explicit prior Owner decision answers it, and evidence does not contradict it
- `NOT_CANONICAL` — the canonical field is empty, and that emptiness is the finding
- `CONFLICTED` — two authorities disagree. Include both sides. Do not pick the newer one.
- `INACCESSIBLE` — a required source or the decision read was blocked
- `NOT_FOUND` — searched the decision keys and the allowlist, nothing matched
- `UNKNOWN` — only when the search cannot classify. Do not use it for an empty canonical field.

If Decision Memory has an answer and AKR evidence agrees, status is `OWNER_DECISION`. Cite the canon or source file in provenance as support. Do not call that a conflict.

If they contradict, status is `CONFLICTED` with both sides. No silent preference.

A found brand fact that is not a canonical field keeps the answer. Do not relabel a retrieved fact as `NOT_CANONICAL`. Authority for that case is `AUTHORISED_SOURCE`. Status stays `OWNER_DECISION` only when a decision answered it. Otherwise use the AKR status if it is already one of the allowed words. If AKR's success word is different, keep the fact and set status to the closest allowed word that does not hide the evidence. A single retrieved fact is not `UNKNOWN`.

## Question map

Hard-code this map. Do not infer a new key from wording.

| Question (exact) | Decision key | AKR key | Scope |
| --- | --- | --- | --- |
| What is Wolf's ClickUp policy? | same string | none | Wolf system |
| What are the current SYSTEM maturity credits? | same string | none | Wolf system |
| What font does Habitat use? | none | `brand_font` only. Do not query `ui_font`. | Habitat |
| Is Habitat CRM cut over? | same string | none | Habitat |
| What does Klaviyo created mean for Habitat lead receipt? | same string | none | Habitat |
| Is the Habitat headline rule lowercase or uppercase? | none | `headline_case` | Habitat |

Any other question has no key. Search still runs (decision recall of that exact string, AKR with no matching key). Expected status is `NOT_FOUND`, with attempts filled. Do not escalate to a human.

## Prove these

Against the real Beta Decision Memory seed and the real Habitat registry. If the NAS file is unreadable, return `INACCESSIBLE` and say so. Do not stub a pass.

- ClickUp policy → `OWNER_DECISION`
- SYSTEM credits → `OWNER_DECISION`, and provenance cites `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md` because the locked table matches the decision. If the file and the decision differ, return `CONFLICTED` and stop. Do not paper over it.
- Habitat font → authorised source evidence for the brand lane (Manrope). Inter is the UI lane and must not appear as the brand answer.
- CRM cut over → `OWNER_DECISION` that cutover is off
- Klaviyo created → `OWNER_DECISION` (receipt time, not form-submit time)
- Headline case → `CONFLICTED`, both sides present
- `What is Uma Blu's morning close time?` under Habitat scope → `NOT_FOUND`, attempts recorded, `escalate` false
- Same ClickUp question under a Uma Blu scope → no Habitat/Wolf decision bleed. `NOT_FOUND` or scope refusal. Not the Wolf answer.

## Human escalation

`escalate` is true only when status is `CONFLICTED`, or a required source is `INACCESSIBLE`, or status is `UNKNOWN` after the search, or the question explicitly needs a new Owner decision and nothing is recorded.

`escalate` is false for `NOT_FOUND`, `NOT_CANONICAL`, and `OWNER_DECISION`.

Do not send mail, Telegram, or any message.

## Security tests

- No actor context: decision read fails closed
- Path outside the AKR allowlist: refused
- Uma scope does not return Habitat font
- No write functions
- `honesty` style flag: this module does not decide and does not replace audit

## Tests

New `scripts/tests/test_knowledge_resolution.py`.
Existing `test_decision_memory.py` and `test_authorised_knowledge.py` and `test_authorised_knowledge_live.py` still pass.
Use temp DB copies for unit tests. One test may call the live registry read-only. It must not write sources.

## Commit

Commit only this slice's files. Do not `git add -A`. Do not commit the Model C ledger.

Do not add a CAP-ID promotion. Do not edit the ledger.

End the log with:

```
COMMIT: <hash>
TESTS: PASS=<n> FAIL=0
EXIT:0
CURSOR_DONE
```

If the credits file and the Owner decision disagree, print `EXIT:1` and the mismatch. Do not print `EXIT:0`.
