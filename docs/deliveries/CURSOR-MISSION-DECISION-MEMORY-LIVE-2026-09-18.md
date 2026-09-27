# CURSOR MISSION — CAP-INTEL-04 Decision Memory live prove

**Start from:** `7ff5208` (`scripts/core/decision_memory.py`). Do not rewrite the module. Extend it.
**Beta only.** Workspace `/Users/wolfterminal/beta-os`.
**Do not** edit `state/model-c-baseline-assessments.json`, `state/model-c-score-history.jsonl`, the Progress dashboard, `scripts/serve_beta.py` routes, Production, `scripts/habitat-lead-sync.py`, ClickUp scripts, or any CRM cutover flag.

## Preserve the split

DECISION ≠ APPROVAL ≠ AUDIT EVENT.

- Decision Memory stores the decision, its statement, and provenance.
- Approval Engine stays the approval authority. Do not call it to mint an approval.
- Audit Spine stays the event history. Call existing `scripts/core/audit.py` `record_event` when a decision is recorded. Do not modify audit history functions. `honesty_flags()["replaces_audit"]` stays false.
- No UPDATE/DELETE of decision rows. Existing triggers stay. `update_decision` / `delete_decision` stay NotImplemented.

## Permissions

Canonical codes, same shape as `scripts/migrations/migrate_rbac_permissions.py` (`content.plan.read`):

- `decision.memory.read`
- `decision.memory.record`

Add them with a new Beta migration. Do not grant them to any live staff role. Do not hard-code a person email or person id into a grant.

`record_decision` and `recall` fail closed unless the caller passes a permission context that `scripts/core/rbac.py` `evaluate` would allow for that code. Tests use fixture roles in a temp DB.

Real rows are written only by an explicit seed function, not by an HTTP route and not by skipping the check. The seed is the Owner-governed path: it runs only when called, it uses the module's existing Beta path guard, it refuses any path outside Beta, and each inserted row still goes through `record_decision` plus an audit event. No second write path.

If the Beta decision DB path cannot be proved safe, do not write it. Report that and keep the real rows in the test seed only. Do not weaken the guard.

## Real decisions — copy, do not invent

Record only the decisions below. Actor string: `Matthew Goss`. Do not invent a person UUID. If `org_persons` already has a Matthew row, copy that id into provenance. If it does not, leave person id empty.

`occurred_at`: use a timestamp only when the cited file contains one. Otherwise store the date only (`2026-09-18` or the file's date). Do not invent a clock.

`approval_ref`: empty unless the cited file contains an approval id.

`outcome`: empty (`OUTCOME_UNKNOWN`) unless the cited file states an outcome that already happened. "Cutover is off" is the chosen option, not an outcome.

`options_considered`: empty, with `empty_options_reason` = `Owner stated the decision. No option list in the source.` Unless the cited file actually lists options. Do not draft options.

Stable ids (use these, do not mint random ids for these four):

1. `DEC-ARCH-CLICKUP-2026-09-18`
   - scope: Wolf system
   - statement: ClickUp is removed from Wolf's target architecture. Wolf Core Work Items are the future task primitive. Existing ClickUp remains legacy evidence until a controlled retirement. Retirement is not done in this slice.
   - provenance: this mission, quoting the Owner audit 2026-09-18. Date only.
   - exact recall key: `What is Wolf's ClickUp policy?`

2. `DEC-MODEL-C-CREDITS-2026-09-17`
   - scope: Wolf system
   - Read `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md` and copy the locked credit table verbatim into `chosen_option`. Expected values if the file matches: ABSENT 0, SPECIFIED 0.05, BUILT 0.25, PROVEN 0.80, READY 1.00. If the file disagrees, STOP and write the mismatch. Do not guess.
   - provenance: that file plus `docs/deliveries/MODEL-C-NUMERIC-CREDITS-LOCK-EVENT-2026-09-17.md` if present.
   - exact recall key: `What are the current SYSTEM maturity credits?`

3. `DEC-CRM-HABITAT-CUTOVER-2026-09-18`
   - scope: GGV / Habitat
   - statement: Historical lead archaeology is preserved. No fabricated first-touch history. A post-cutover clean book is later. CRM cutover is currently OFF. No cutover_at, no operator, no live lead ingestion, no staff grant, no Work Item creation. The old Habitat sync is unchanged.
   - provenance: this mission, quoting the Owner audit 2026-09-18. Date only.
   - exact recall key: `Is Habitat CRM cut over?`

4. `DEC-CRM-KLAVIYO-RECEIPT-2026-09-18`
   - scope: GGV / Habitat
   - statement: For Klaviyo-source Habitat leads, Klaviyo `profile.created` may be the receipt time. It is stored as source observed time with provenance RECEIVED_BY_KLAVIYO_SOURCE. It does not claim upstream form-submit time.
   - provenance: this mission, quoting the Owner audit 2026-09-18, and `docs/deliveries/CURSOR-MISSION-HABITAT-KLAVIYO-READER-2026-09-18.md` if that file says the same. Date only.
   - exact recall key: `What does Klaviyo created mean for Habitat lead receipt?`

No fifth decision unless you find another Owner sentence in a committed file with equal explicitness. Do not add one from inference.

## Correction

Read `docs/deliveries/OVERNIGHT-P1-MATURITY-UPDATES-2026-09-17.md` and `docs/deliveries/EVIDENCE-REMEDIATION-DR01-INTG07-2026-09-18.md`.

Record a real pair only if the first file explicitly claimed CAP-DR-01 or CAP-INTG-07 PROVEN and the second file explicitly rejects that and keeps them SPECIFIED.

If both sentences exist:

- original decision remains (overnight claim, cited)
- new decision points at the old id via existing `corrects_decision_id`
- recall of the maturity question returns the current interpretation (still SPECIFIED) and `get_decision` on the old id still returns the old row

If either sentence is missing, do not invent the pair. Keep correction coverage on the existing fixture tests in `scripts/tests/test_decision_memory.py`.

## Recall

Rows with `query_keys` match only on exact casefolded equality with a registered key. A shared word is not a hit.

Rows without `query_keys` keep today's substring match so the existing tests stay green.

These queries must return NOT FOUND:

- `Should we import historical ClickUp leads now?`
- `Who owns Habitat ads?`
- `What is Uma Blu's morning close time?`

No vector search. No embeddings. No model call.

## Tests

- Existing `python3 scripts/tests/test_decision_memory.py` still PASS.
- New tests for: exact key hit, adjacent miss, RBAC deny, seed refuses a non-Beta path, audit event written, append-only still blocks UPDATE/DELETE, correction pair only if the real docs qualified (otherwise the fixture correction tests remain the proof).
- Tests use a temp DB. They must not write the live Beta decision DB except the one explicit seed invocation, and only if the path guard passes.

## Commit

Commit only the files this slice touched. Do not `git add -A`. Do not commit `state/model-c-baseline-assessments.json`.

End the log with these lines and nothing required after them:

```
COMMIT: <hash>
TESTS: PASS=<n> FAIL=0
REAL: <count of real decisions seeded>
EXIT:0
CURSOR_DONE
```

If you cannot finish safely, do not print EXIT:0. Print EXIT:1 and the blocker.
