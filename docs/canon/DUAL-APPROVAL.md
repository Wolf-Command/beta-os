# Dual Approval — Canon (Wolf Core)

**LOCKED 2026-09-17.** Extends Approval Engine. Not a second engine.  
**Status:** BUILT+TESTED on Beta (`build/wolf-command-rebuild`) — migration `015_dual_approval`.

## Question

Does this Approval Request require N independent authorised APPROVED decisions before status becomes APPROVED?

## Constitution

REQUESTED ≠ APPROVAL 1 ≠ APPROVAL 2 ≠ APPROVED ≠ EXECUTED ≠ OUTCOME

## Field

`required_decision_count` (default 1). Immutable after create (snapshot_hash). Client cannot lower.

## Independence

Person-based. One human = one counted APPROVED decision per request. Delegation does not multiply persons.

## Status

PENDING until enough independent APPROVED decisions, then APPROVED. Any REJECTED → REJECTED. No decorative PARTIALLY_APPROVED.

## Live policy

Not configured. Isolated test fixtures only. Live Authority Limits remain 0.
