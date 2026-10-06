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
4. **Closing the issue.** WI closes it on COMPLETED, FAILED or REVOKED (comment `WI: COMPLETED` / `WI: FAILED` / `WI: REVOKED`). Also closes as `WI: RE_RUNG` when a lease expired and a new doorbell with a new nonce was opened, or `WI: SUPERSEDED` after `rering`. Doorbell closes triggered by worker `complete`/`fail`/`release` are attributed to **WI** (`actor=wi`, `triggered_by=<lease holder>` in audit detail).
5. **Recovery.** The hourly overnight tick runs **`verify_audit_chain()` first**. If verification fails it emits `grok_bridge.audit_chain_broken` and **skips** lease recovery (`skipped_due_to_audit_failure`). When the chain is healthy it calls `release_expired()`. `grok-bridge release-expired` does the same on demand. Expired leases go back to AVAILABLE with attempt+1, a new nonce and a new doorbell. Doorbells that failed or never went out are re-rung (but `DISABLED` items are not re-selected every tick while the doorbell is off).

## Protocol guarantees

- **At most one valid lease, at-least-once execution.** Exactly one claimant holds an unexpired lease at a time. If a lease expires while work continues, the item can be re-claimed and executed again; only the first valid `complete` is stored. Every successful `claim` returns an `idempotency_key` (`<work_item_id>:attempt-<n>`) and the stable `work_item_id`; side-effecting tasks must honour them.
- **Atomic claim.** Every lease transition is a compare-and-set inside one `BEGIN IMMEDIATE` SQLite transaction. Exactly one claimer wins; the rest get `ALREADY_CLAIMED`. Tested with 20 and 50 parallel CLI processes.
- **Valid lease required.** `complete`, `fail` and `renew` need the matching `lease_id` and an unexpired lease. Rejections (`STALE_LEASE`, `BAD_LEASE_ID`, `SECRET_SHAPED_REJECTED`, …) record **`actor = caller`** (or `unidentified-caller`) with `lease_holder` in audit detail. Successful rows keep `actor = lease holder`. Pass `--caller` on `renew`/`complete`/`fail`. A second `complete` returns `ALREADY_COMPLETED`.
- **Nonce rotation.** The nonce changes on every re-offer / recovery cycle, so an old doorbell cannot claim a newer attempt (`NONCE_MISMATCH`).
- **Claim allowlist.** Only **`DISPATCHED_SHADOW`** is claimable by default. **`RUNNING`** is claimable only when the item's `dispatch.route == "grok_bridge"` (re-claim after a released lease). **`QUEUED` is not claimable.** `claim()` moves `DISPATCHED_SHADOW → RUNNING` (compare-and-set). Owner-gated (`NEEDS_YOU`, `DECISION_PENDING`), terminal and every other state are refused (`ITEM_NOT_CLAIMABLE` / `ITEM_TERMINAL`). `renew`/`complete` re-check claimability inside their transaction; if the Owner gated the item, `renew` returns `ITEM_NOT_CLAIMABLE` and `complete` quarantines the result (`RESULT_QUARANTINED`, exit 3) without writing into the work item.
- **Reserved identities.** `claim --claimant`, `complete --executed-by` and `--caller` must not be any of: `grok_bot`, `grok_bot_sub`, `wi`, `wi-recovery`, `overnight-tick`, `cli`, `peaches`, `bridge`, `grok_bridge`, or the row's `dispatcher`. Returns `RESERVED_IDENTITY` (audited). `offer --dispatcher` may still be `wi`/`peaches`/`cli`.
- **Owner gate safety.** `work_items.update_fields()` never writes `state` or `history` (column-scoped UPDATE inside `BEGIN IMMEDIATE`). `work_items.transition()` also runs read+check+write inside `BEGIN IMMEDIATE`. A worker cannot revert an Owner gate by writing dispatch/result back over `NEEDS_YOU`/`CANCELLED`.
- **Attempt limit.** After `max_attempts` (default 3), the item goes to FAILED with `reassign_flag` set. `reassign_candidates` lists human-commissioned, non-metered, ungated workers (today `claude_pro_sub`, `codex_sub`, `cursor_sub`). Flag only: no automatic dispatch, never a metered fallback. The canonical item walks to `EXCEPTION` only from `DISPATCHED_SHADOW` or `RUNNING`.
- **Identity fields.** `dispatcher` (from `offer --dispatcher`), `claimed_by` / `completed_by` (lease holder), `executed_by` (declared by holder, defaults to holder). Never attributed to `grok_bot` unless that was the claimant. Stored on the lease row, in audit detail, and in the work item `result` dict.
- **Post-commit item updates.** After a committed `claim`/`complete`/`fail`/`release`, work-item updates are best-effort. On failure the CLI still returns the committed lease result with `item_update_error` set. `release_expired()` reconciles `COMPLETED` leases whose item `result` lacks that `lease_id` (`RECONCILED` audit row).
- **Audit.** Every transition and rejection appends a row to `grok_bridge_audit` with who, when, lease id, attempt, from/to state, outcome and a sha256 of the result, evidence or **redacted** reason. Rows are hash-chained and **HMAC-signed** (key in `STATE_ROOT/grok_bridge/keys/audit-hmac.key`, mode 0600, created atomically via tmp+link; keys shorter than 32 bytes are refused). On first key creation an HMAC-signed **`audit-pin.json`** records `legacy_max_seq` (max audit seq at key creation; 0 for a fresh DB). Rows with `seq > legacy_max_seq` must be signed; if any exist, **`audit-anchor.json`** must exist and match. Stripping all HMACs and deleting the anchor fails verification. Before re-signing the anchor, writers verify the existing anchor still matches the DB; mismatch raises `AuditIntegrityError` (fail closed — truncation cannot be laundered by a later write). Each new anchor head is appended to **`audit-anchor-log.jsonl`** (HMAC-signed lines; anchor seq never decreases). Set **`WOLF_INTELLIGENCE_GROK_AUDIT_ANCHOR_MIRROR`** to a directory to mirror the log off-host (`<dir>/audit-anchor-log.jsonl`). `verify_audit_chain()` reads rows, anchor, pin and log inside one `BEGIN IMMEDIATE`. The anchor is written before COMMIT (still inside the writer lock); a crash between anchor write and COMMIT reads as **TRUNCATED** until the next write — fail-safe. Rows are **append-only** (SQLite triggers block UPDATE/DELETE). Corrections are new rows via `correct`. Broken chain on overnight tick emits `grok_bridge.audit_chain_broken` and skips recovery.
- **Audit limits (Owner decision).** The key, pin, anchor and log all live under the same uid as the worker wrapper. A same-uid attacker who deletes the key, pin, anchor, anchor log **and** the mirror can still rewrite history. Mitigations: run the bridge worker as a **different uid** from WI, and/or set `WOLF_INTELLIGENCE_GROK_AUDIT_ANCHOR_MIRROR` to off-host storage.
- **Result storage.** Results under `STATE_ROOT/grok_bridge/results/<id>/<lease_id>.result`; sha256 on the work item. Results for gated items go to `results/<id>/quarantine/<lease_id>.result` only. Secret-shaped results refused (`SECRET_SHAPED_REJECTED`); lease stays valid for redacted retry.
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

- Closing comment: `WI: COMPLETED`, `WI: FAILED`, `WI: RE_RUNG`, `WI: SUPERSEDED` or `WI: REVOKED`.

## Commands a Grok routine runs on the Studio

Use `wolf_intelligence/bin/grok-bridge.sh`. Requires `WOLF_INTELLIGENCE_STATE_ROOT`. Hard-coded **`/opt/homebrew/bin/python3`**, fixed **`PATH=/opt/homebrew/bin:/usr/bin:/bin`**, runtime = repo containing the script. No `GROK_BRIDGE_PYTHON` or `WI_GROK_BRIDGE_RUNTIME` overrides. Defaults doorbell to `github` so completion closes the issue. Runs Python under `/usr/bin/env -i` with an allowlisted environment (parent secrets such as `ANTHROPIC_API_KEY` are not inherited). Only `claim`, `renew`, `complete`, `fail` and `status` are permitted; anything else returns `NOT_ALLOWED_FOR_WORKER`. stdout is one JSON object. Exit codes: 0 ok, 3 protocol rejection (`RESULT_QUARANTINED`, `ITEM_NOT_CLAIMABLE`, `STALE_LEASE`, …), 2 bad input/not found, 1 internal error.

```
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh claim <id> --nonce <nonce> --claimant grok-bot-routine
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh renew <id> --lease <lease_id> [--caller grok-bot-routine]
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh complete <id> --lease <lease_id> --result-file <path> [--evidence-file <path>] [--executed-by <who>] [--caller grok-bot-routine]
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh fail <id> --lease <lease_id> --reason "<short reason>" [--retryable] [--caller grok-bot-routine]
```

The routine should stop without doing any work on any `claim` code other than `CLAIMED`.

Returned JSON (representative):

```
claim    {"attempt": 1, "claimant": "grok-bot-routine", "claimed_at": "...", "code": "CLAIMED",
          "idempotency_key": "wi_85ff981dd639:attempt-1", "lease_id": "lease_...", "ok": true, "task": {...}, ...}
complete {"code": "COMPLETED", "claimed_by": "grok-bot-routine", "executed_by": "grok-bot-routine",
          "completed_by": "grok-bot-routine", "item_state": "READY_TO_TEST", "item_transition": "RUNNING->READY_TO_TEST", ...}
```

Other codes: `ALREADY_CLAIMED`, `NONCE_MISMATCH`, `ITEM_NOT_CLAIMABLE`, `ITEM_TERMINAL`, `STALE_LEASE`, `ALREADY_COMPLETED`, `RESULT_QUARANTINED`, `RESERVED_IDENTITY`, `SECRET_SHAPED_REJECTED`, `NOT_ALLOWED_FOR_WORKER`, etc.

## WI-side commands

| Command | Purpose |
|---|---|
| `grok-bridge offer <id> [--lease-seconds 60..14400] [--max-attempts 1..10] [--dispatcher <who>]` | Make item AVAILABLE and ring doorbell |
| `grok-bridge release-expired` | Lease recovery + re-ring + reconcile + revoke non-claimable leases |
| `grok-bridge rering <id>` | Rotate nonce, close old doorbell as SUPERSEDED, ring new |
| `grok-bridge correct <seq> --reason <text> --actor <who>` | Append corrective audit row |
| `grok-bridge verify-audit` | Verify hash chain, HMACs, pin, anchor and anchor log |
| `grok-bridge status <id>` | Lease view (no task text) |
| `grok-bridge audit [<id>]` | Audit rows + chain verification |

## Not in this stage

- Router does not auto-offer to grok_bot; items are offered explicitly.
- `routing-policy-real.json` stays DRAFT and is not wired.
- Live WI (`~/wi-runtime`) does not run this code until reviewed and merged.
