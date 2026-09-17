# Segregation of Duties — Canon (Wolf Core)

**LOCKED 2026-09-17.**  
**Status:** BUILT+TESTED on Beta (`build/wolf-command-rebuild`) — migration `017_sod_constraints`.

AUTHORISED ≠ PERMITTED TO PERFORM EVERY STEP.

Independence is Person-based. Dual Approval ≠ SoD. Authority/Permission/Delegation/Policy Binding cannot override SoD.

Missing required participation evidence → FAIL CLOSED.

Client-supplied independence / forged participation claims are IGNORED.

## API

`evaluate_sod(verified_person_id, entity_id, process_family, proposed_action, subject_id, …)`  
`approvals._decide` APPROVED path: proposed=`approval.decide` vs prior=`approval.request` (when ACTIVE constraint matches). Zero ACTIVE → `sod_not_applicable` (legacy suites green).

This slice relationship: `SAME_PERSON_FORBIDDEN` only.

## Live

Live SoD constraints = 0 until Matt configures business policy.  
No `sod.constraint.manage` live grants. Matt `sod.constraint.read` only.
