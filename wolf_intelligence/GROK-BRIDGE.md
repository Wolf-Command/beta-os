# Grok work bridge (event-driven, claim/lease)

Owner order 2026-10-06 09:03 WITA: close the Grok push/pull gap without a polling loop. **Paid spend stays OFF.**

## GitHub is only a doorbell

GitHub is **not**:

- the queue
- canonical state
- the payload store
- the result store
- the audit authority
- the scheduler
- the control plane

WI **never reads** GitHub. The doorbell is a one-way wake-up: WI writes an issue with the work-item id and nonce; the Grok routine reads that body locally, then claims over the Studio machine pipe. Recovery (`release_expired`, lease expiry, re-ring) works with GitHub unavailable — the item stays AVAILABLE in SQLite and the audit chain remains authoritative.

See `GROK-ROUTINE-SPEC.md` for the worker-side routine.

## Flow

1. A canonical WI work item is offered to `grok_bot` (`grok-bridge offer <id> --dispatcher <who>` or `grok_bridge.offer()`). It becomes **AVAILABLE** in `grok_leases` (in `control_plane.sqlite`, next to `work_items`). The item must be in a **claimable** canonical state (see below).
2. **Doorbell.** WI creates a GitHub issue in `wolfcommand/wolf-grok-bridge` **without** an assignee, then assigns it in a separate call (standalone `issues.assigned` event). Title and body carry only the work-item id and a one-time nonce.
3. **Grok side.** A Grok routine fires on *issue assigned*. It parses the body (`grok_doorbell.parse_body`), then on the Studio runs `claim`, does the work, and runs `complete` or `fail` with the `lease_id`. Task content comes back only from `claim` over the Studio machine pipe, never through GitHub.
4. **Closing the issue.** WI closes it on COMPLETED or FAILED (comment `WI: COMPLETED` / `WI: FAILED`). Also closes as `WI: RE_RUNG` when a lease expired and a new doorbell with a new nonce was opened, or `WI: SUPERSEDED` after `rering`.
5. **Recovery.** The hourly overnight tick calls `release_expired()` and `verify_audit_chain()`. `grok-bridge release-expired` does the same on demand. Expired leases go back to AVAILABLE with attempt+1, a new nonce and a new doorbell. Doorbells that failed or never went out are re-rung.

## Protocol guarantees

- **At most one valid lease, at-least-once execution.** Exactly one claimant holds an unexpired lease at a time. If a lease expires while work continues, the item can be re-claimed and executed again; only the first valid `complete` is stored. Every successful `claim` returns an `idempotency_key` (`<work_item_id>:attempt-<n>`) and the stable `work_item_id`; side-effecting tasks must honour them.
- **Atomic claim.** Every transition is a compare-and-set inside one `BEGIN IMMEDIATE` SQLite transaction. Exactly one claimer wins; the rest get `ALREADY_CLAIMED`. Tested with 20 and 50 parallel CLI processes.
- **Valid lease required.** `complete`, `fail` and `renew` need the matching `lease_id` and an unexpired lease. Otherwise they return `STALE_LEASE`, attributed to the **original lease holder** (from the audit `CLAIMED` row), not the caller. A second `complete` returns `ALREADY_COMPLETED`.
- **Nonce rotation.** The nonce changes on every re-offer / recovery cycle, so an old doorbell cannot claim a newer attempt (`NONCE_MISMATCH`).
- **Claim allowlist.** Only canonical states in `CLAIMABLE_ITEM_STATES` (`QUEUED`, `DISPATCHED_SHADOW`, `RUNNING`) can be offered or claimed. Owner-gated (`NEEDS_YOU`, `DECISION_PENDING`), terminal and every other state are refused (`ITEM_NOT_CLAIMABLE` / `ITEM_TERMINAL`). `complete()` applies at most one direct compare-and-set step (`RUNNING` → `READY_TO_TEST`) and otherwise leaves canonical state untouched — no invented history.
- **Attempt limit.** After `max_attempts` (default 3), the item goes to FAILED with `reassign_flag` set. `reassign_candidates` lists human-commissioned, non-metered, ungated workers (today `claude_pro_sub`, `codex_sub`, `cursor_sub`). Flag only: no automatic dispatch, never a metered fallback. The canonical item walks to `EXCEPTION` only from `DISPATCHED_SHADOW` or `RUNNING`.
- **Identity fields.** `dispatcher` (from `offer --dispatcher`), `claimed_by` / `completed_by` (lease holder), `executed_by` (declared by holder, defaults to holder). Never attributed to `grok_bot` unless that was the claimant. Stored on the lease row, in audit detail, and in the work item `result` dict.
- **Audit.** Every transition and rejection appends a row to `grok_bridge_audit` with who, when, lease id, attempt, from/to state, outcome and a sha256 of the result, evidence or reason. Rows are hash-chained and **HMAC-signed** (key in `STATE_ROOT/grok_bridge/keys/audit-hmac.key`, mode 0600). A signed **head anchor** (`audit-anchor.json`) is updated on every write transaction. Rows are **append-only** (SQLite triggers block UPDATE/DELETE). Corrections are new rows via `correct` (references `corrects_seq` and `corrects_row_sha256`; original row is never rewritten). `verify_audit_chain()` detects broken chain, HMAC mismatch, truncation and forged anchors. Broken chain on overnight tick emits `grok_bridge.audit_chain_broken`.
- **Result storage.** Results under `STATE_ROOT/grok_bridge/results/<id>/<lease_id>.result`; sha256 on the work item. Secret-shaped results refused (`SECRET_SHAPED_REJECTED`); lease stays valid for redacted retry.
- **Doorbell failure is safe.** Item stays AVAILABLE, `doorbell_state=FAILED` recorded, nothing raises, recovery re-rings. Doorbell off unless `WOLF_INTELLIGENCE_GROK_DOORBELL=github`.

## Doorbell issue format (exact)

- Repo `wolfcommand/wolf-grok-bridge` (private). Assignee `wolfcommand`. Label `wi-doorbell`.
- **Create-then-assign:** issue created unassigned, then `gh issue edit --add-assignee` in a separate call so the webhook is a standalone `issues.assigned` event.
- Title: `WI doorbell <work_item_id>`
- Body (3 lines, nothing else):

```
wi-grok-doorbell/1
work_item_id: wi_63f9132d232a
nonce: 66eef1c0b54419a5cb1138a139c11f16
```

- Closing comment: `WI: COMPLETED`, `WI: FAILED`, `WI: RE_RUNG` or `WI: SUPERSEDED`.

## Commands a Grok routine runs on the Studio

Use `wolf_intelligence/bin/grok-bridge.sh`. Requires `WOLF_INTELLIGENCE_STATE_ROOT`. Defaults doorbell to `github` so completion closes the issue. Runs Python under `/usr/bin/env -i` with an allowlisted environment (parent secrets such as `ANTHROPIC_API_KEY` are not inherited). Only `claim`, `renew`, `complete`, `fail` and `status` are permitted; anything else returns `NOT_ALLOWED_FOR_WORKER`. stdout is one JSON object. Exit codes: 0 ok, 3 protocol rejection, 2 bad input/not found, 1 internal error.

```
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh claim <id> --nonce <nonce> --claimant grok-bot-routine
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh renew <id> --lease <lease_id>
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh complete <id> --lease <lease_id> --result-file <path> [--evidence-file <path>] [--executed-by <who>]
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh fail <id> --lease <lease_id> --reason "<short reason>" [--retryable]
```

The routine should stop without doing any work on any `claim` code other than `CLAIMED`.

Returned JSON (representative):

```
claim    {"attempt": 1, "claimant": "grok-bot-routine", "claimed_at": "...", "code": "CLAIMED",
          "idempotency_key": "wi_85ff981dd639:attempt-1", "lease_id": "lease_...", "ok": true, "task": {...}, ...}
complete {"code": "COMPLETED", "claimed_by": "grok-bot-routine", "executed_by": "grok-bot-routine",
          "completed_by": "grok-bot-routine", "item_state": "READY_TO_TEST", "item_transition": "RUNNING->READY_TO_TEST", ...}
```

Other codes: `ALREADY_CLAIMED`, `NONCE_MISMATCH`, `ITEM_NOT_CLAIMABLE`, `ITEM_TERMINAL`, `STALE_LEASE`, `ALREADY_COMPLETED`, `SECRET_SHAPED_REJECTED`, `NOT_ALLOWED_FOR_WORKER`, etc.

## WI-side commands

| Command | Purpose |
|---|---|
| `grok-bridge offer <id> [--lease-seconds 60..14400] [--max-attempts 1..10] [--dispatcher <who>]` | Make item AVAILABLE and ring doorbell |
| `grok-bridge release-expired` | Lease recovery + re-ring |
| `grok-bridge rering <id>` | Rotate nonce, close old doorbell as SUPERSEDED, ring new |
| `grok-bridge correct <seq> --reason <text> --actor <who>` | Append corrective audit row |
| `grok-bridge verify-audit` | Verify hash chain, HMACs and anchor |
| `grok-bridge status <id>` | Lease view (no task text) |
| `grok-bridge audit [<id>]` | Audit rows + chain verification |

## Not in this stage

- Router does not auto-offer to grok_bot; items are offered explicitly.
- `routing-policy-real.json` stays DRAFT and is not wired.
- Live WI (`~/wi-runtime`) does not run this code until reviewed and merged.
