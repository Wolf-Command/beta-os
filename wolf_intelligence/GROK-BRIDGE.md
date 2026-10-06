# Grok work bridge (event-driven, claim/lease)

Owner order 2026-10-06 09:03 WITA: close the Grok push/pull gap without a polling loop. **Paid spend stays OFF.**

## Flow
1. A canonical WI work item is offered to `grok_bot` (`grok-bridge offer <id>` or `grok_bridge.offer()`). It becomes **AVAILABLE** in `grok_leases` (in `control_plane.sqlite`, next to `work_items`).
2. **Doorbell.** WI immediately opens a GitHub issue in the private repo `wolfcommand/wolf-grok-bridge`, assigned to `wolfcommand` and labelled `wi-doorbell`. The title and body carry only the work-item id and a one-time nonce.
3. **Grok side.** A Grok routine fires on *issue assigned*. It parses the body, then on the Studio runs `claim`, does the work, and runs `complete` or `fail` with the `lease_id`. The task content comes back only from `claim` over the Studio machine pipe, never through GitHub.
4. **Closing the issue.** WI closes it on COMPLETED or FAILED (comment `WI: COMPLETED` / `WI: FAILED`). It also closes it as `WI: RE_RUNG` when a lease expired and a new doorbell with a new nonce was opened.
5. **Recovery.** The hourly overnight tick calls `release_expired()`; `grok-bridge release-expired` does the same on demand. Expired leases go back to AVAILABLE with attempt+1, a new nonce and a new doorbell. Doorbells that failed or never went out are re-rung. This is lease recovery, not polling.

## Protocol guarantees
- **Atomic claim.** Every transition is a compare-and-set inside one `BEGIN IMMEDIATE` SQLite transaction. Exactly one claimer wins; the rest get `ALREADY_CLAIMED`. Tested with 20 threads and with 20 separate CLI processes.
- **Valid lease required.** `complete`, `fail` and `renew` need the matching `lease_id` and an unexpired lease. Otherwise they return `STALE_LEASE`, and the rejection is recorded. A second `complete` returns `ALREADY_COMPLETED`.
- **Nonce rotation.** The nonce changes on every re-offer, so an old doorbell cannot claim a newer attempt (`NONCE_MISMATCH`).
- **Attempt limit.** After `max_attempts` (default 3), the item goes to FAILED with `reassign_flag` set. `reassign_candidates` lists human-commissioned, non-metered, ungated workers (today `claude_pro_sub`, `codex_sub`, `cursor_sub`). It is a flag only: there is no automatic dispatch and never a metered fallback. The canonical item walks to EXCEPTION.
- **Audit.** Every transition and every rejection appends a row to `grok_bridge_audit` with who, when, lease id, attempt, from/to state, outcome and a sha256 of the result, evidence or reason. Rows are hash-chained (`verify_audit_chain()`). Events are mirrored to `events.jsonl` (`grok_bridge.*`).
- **Result storage.** Results are stored under `STATE_ROOT/grok_bridge/results/<id>/<lease_id>.result`, and their sha256 goes on the work item. Results that look like secrets are refused (`SECRET_SHAPED_REJECTED`); the lease stays valid so the claimant can redact and retry.
- **Doorbell failure is safe.** The item stays AVAILABLE, `doorbell_state=FAILED` is recorded, nothing raises, and recovery re-rings it. The doorbell is off unless `WOLF_INTELLIGENCE_GROK_DOORBELL=github`.

## Doorbell issue format (exact)
- Repo `wolfcommand/wolf-grok-bridge` (private). Assignee `wolfcommand`. Label `wi-doorbell`.
- Title: `WI doorbell <work_item_id>`
- Body (3 lines, nothing else):
```
wi-grok-doorbell/1
work_item_id: wi_63f9132d232a
nonce: 66eef1c0b54419a5cb1138a139c11f16
```
- Closing comment: `WI: COMPLETED`, `WI: FAILED`, `WI: RE_RUNG` or `WI: SUPERSEDED`.

## Commands a Grok routine runs on the Studio
Use `wolf_intelligence/bin/grok-bridge.sh`. It requires `WOLF_INTELLIGENCE_STATE_ROOT`, defaults the doorbell to `github` so completion closes the issue, unsets live submit, and execs `python3 -m wolf_intelligence grok-bridge`. stdout is one JSON object. Exit codes: 0 ok, 3 protocol rejection, 2 bad input/not found, 1 internal error.

```
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh claim <id> --nonce <nonce> --claimant grok-bot-routine
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh renew <id> --lease <lease_id>          # optional, long tasks
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh complete <id> --lease <lease_id> --result-file <path> [--evidence-file <path>]
   (or pipe the result: ... complete <id> --lease <lease_id> --result-stdin)
WOLF_INTELLIGENCE_STATE_ROOT=<root> <runtime>/wolf_intelligence/bin/grok-bridge.sh fail <id> --lease <lease_id> --reason "<short reason>" [--retryable]
```
The routine should stop without doing any work on any `claim` code other than `CLAIMED`: `ALREADY_CLAIMED`, `NONCE_MISMATCH`, `ALREADY_FINISHED` or `NOT_OFFERED`.

Returned JSON (real outputs):
```
claim    {"attempt": 1, "claimant": "grok-bot-routine", "claimed_at": "2026-10-06T09:17:02+08:00", "code": "CLAIMED", "lease_expires_at": "2026-10-06T09:47:02+08:00", "lease_id": "lease_fcad95941ed1b4a5e402e52f", "lease_seconds": 1800, "ok": true, "task": {"kind": "review", "payload": {"prompt": "Review this diff and list risks."}, "tags": [], "title": "example task"}, "work_item_id": "wi_85ff981dd639"}   exit 0
claim    {"attempt": 1, "code": "ALREADY_CLAIMED", "lease_expired_pending_recovery": false, "ok": false, "work_item_id": "wi_85ff981dd639"}   exit 3
claim    {"code": "ALREADY_FINISHED", "ok": false, "state": "FAILED", "work_item_id": "wi_e6f94954b89e"}   exit 3
renew    {"code": "RENEWED", "lease_expires_at": "2026-10-06T09:47:02+08:00", "lease_id": "lease_fcad95941ed1b4a5e402e52f", "ok": true, "work_item_id": "wi_85ff981dd639"}   exit 0
complete {"code": "COMPLETED", "evidence_sha256": null, "item_state": "READY_TO_TEST", "lease_id": "lease_fcad95941ed1b4a5e402e52f", "ok": true, "result_sha256": "b2fb6742c7b4988079375befd4607d67478844fa2fa508afbfc4edc67e914477", "work_item_id": "wi_85ff981dd639"}   exit 0
complete {"code": "ALREADY_COMPLETED", "ok": false, "result_sha256": "b2fb…4477", "work_item_id": "wi_85ff981dd639"}   exit 3
complete {"code": "STALE_LEASE", "message": "this lease is no longer current; do not retry with it", "ok": false, "state": "FAILED", "work_item_id": "wi_e6f94954b89e"}   exit 3
fail     {"code": "FAILED", "ok": true, "reason_sha256": "6d8c…6e4d", "reassign_candidates": ["claude_pro_sub", "codex_sub", "cursor_sub"], "reassign_flag": true, "work_item_id": "wi_e6f94954b89e"}   exit 0
fail --retryable  {"attempt": 2, "code": "RELEASED_FOR_RETRY", "ok": true, "reason_sha256": "…", "work_item_id": "…"}   exit 0
```
The other codes are `NONCE_MISMATCH`, `NOT_OFFERED`, `BAD_LEASE_ID`, `EMPTY_RESULT`, `RESULT_TOO_LARGE`, `SECRET_SHAPED_REJECTED`, `RENEWAL_LIMIT`, `BAD_INPUT` and `STATE_ROOT_REQUIRED`.

## WI-side commands
`grok-bridge offer <id> [--lease-seconds 60..14400] [--max-attempts 1..10]`, `grok-bridge release-expired`, `grok-bridge status <id>`, `grok-bridge audit [<id>]`.

## Not in this stage
- The router does not auto-offer to grok_bot yet; an item is offered explicitly.
- `routing-policy-real.json` stays DRAFT and is not wired.
- Live WI (`~/wi-runtime`) does not run this code until it is reviewed and merged.
