# CURSOR MISSION — Wolf Core Delegation (Beta OS only)

**Date:** 2026-09-17 (WITA)  
**Grok planned:** YES against HEAD `acfae32` (Approval Grok gap CLOSED: `dd039b2` + `04a3d63` + re-review PASS)  
**Peaches:** Governor only — no application coding.  
**Implementer:** Cursor Local Agent on Wolfs-Mac-Studio  
**Repo:** `/Users/wolfterminal/beta-os/` · Branch `build/wolf-command-rebuild` (start CLEAN)  
**Commit:** `feat(core): add deterministic delegation`  
**No remote. No Production. No live Authority Limits seed (must remain 0).**  
**No re-delegation. No dual/SoD/UI/LLM/holiday automation.**

---

## Constitutional rules (non-negotiable)

1. **IDENTITY NEVER DELEGATES.** Authenticated Person is always the actor. Never rewrite Person/AuthIdentity. Never act “as” the delegator.
2. **Delegation does not create power.** Grant ≤ what delegator currently holds (Permission + Scope + Authority). Re-evaluate at **use** time fail-closed (not only at create).
3. **NO RE-DELEGATION.** `allow_redelegation=0` always this slice; creating a delegation whose basis is another delegation → deny.
4. **Self-approval laundering blocked.** Approval self-approval rules still apply to the **actual** authenticated decider. `delegator_person_id == delegate_person_id` refused. Circular chains impossible because no re-delegation.
5. **Approval Decision actor = delegate.** Record `authority_basis_type=DELEGATION` + `authority_basis_delegation_id`. Never store delegator as `decided_by_person_id`.

---

## Relationship to Core

| Primitive | Role |
|-----------|------|
| Person / Auth | Identity of actor (unchanged) |
| Assignment | Delegator + delegate must have ACTIVE assignments (delegate_assignment_id required when used) |
| RBAC | WHAT — permission_id/code on grant; evaluate native OR via valid delegation |
| Scope | WHERE — entity_id + scope_id; no silent widen |
| Authority | HOW MUCH — optional `delegated_cap_amount`+`currency`; effective cap = min(delegator within_authority capacity, grant cap); live limits stay **0** (temp fixtures only) |
| Approval | Decide may succeed via valid delegation covering `approval.decide` + required_permission; decision stamps basis |
| Audit | create / used / denied / revoked / expired |

---

## Preflight + backup

```bash
cd /Users/wolfterminal/beta-os
git status -sb   # CLEAN at acfae32 or later docs-only
TS=$(TZ=Asia/Makassar date +%Y%m%d-%H%M%S)
cp -p catalog/content_library.sqlite "catalog/backups/pre-delegation-${TS}.sqlite"
shasum -a 256 "catalog/backups/pre-delegation-${TS}.sqlite" | tee "state/delegation-backup-${TS}.sha256"
# Prove live org_authority_limits = 0 before/after
```

---

## Schema — `core_delegations`

Structured columns only (no opaque JSON for security meaning):

- `delegation_id` TEXT PK (`DLG-…`)
- `delegator_person_id` TEXT NOT NULL
- `delegator_assignment_id` TEXT NOT NULL
- `delegate_person_id` TEXT NOT NULL
- `delegate_assignment_id` TEXT NOT NULL
- `entity_id` TEXT NOT NULL
- `scope_id` TEXT NOT NULL
- `permission_id` TEXT NOT NULL
- `permission_code` TEXT NOT NULL  — denormalized for audit; must match permission_id
- `authority_limit_id` TEXT NULL — optional reference snapshot of a limit used at create (informational)
- `delegated_cap_amount` TEXT NULL — decimal string; required when permission is amount-sensitive / when grant is for spend-like approve
- `currency` TEXT NULL
- `effective_from` TEXT NOT NULL
- `effective_to` TEXT NOT NULL  — **required** (no accidental permanent)
- `status` TEXT NOT NULL CHECK IN (`SCHEDULED`,`ACTIVE`,`EXPIRED`,`REVOKED`)
- `reason` TEXT NULL
- `created_at` TEXT NOT NULL
- `created_by_person_id` TEXT NOT NULL  — must equal verified creator (=delegator this slice, or Matt governance)
- `revoked_at` TEXT NULL
- `revoked_by_person_id` TEXT NULL
- `revoke_reason` TEXT NULL
- `correlation_id` TEXT NOT NULL
- `allow_redelegation` INTEGER NOT NULL DEFAULT 0 CHECK (=0)
- `linked_work_item_id` TEXT NULL — optional; receiving WI ≠ granting power

Indexes: status, delegator, delegate, entity, permission, effective window, correlation.

**No UPDATE of security fields after create** except status transitions (activate/expire/revoke). Material grant fields immutable → revoke + new row to change.

Append-only history: do **not** delete rows. Revoke sets status=REVOKED.

Lazy status:
- SCHEDULED → ACTIVE when now >= effective_from and now < effective_to and not revoked
- ACTIVE → EXPIRED when now >= effective_to
- REVOKED sticky

Do **not** invent a business max duration. Require `effective_to > effective_from`.

---

## Approval decisions — additive columns

Alter `core_approval_decisions` (idempotent migration):

- `authority_basis_type` TEXT NOT NULL DEFAULT `NATIVE` CHECK IN (`NATIVE`,`DELEGATION`)
- `authority_basis_delegation_id` TEXT NULL

When decide succeeds via delegation: type=DELEGATION + id set. Native path: NATIVE + NULL.

---

## Permissions (Matt-only live)

Seed ACTIVE:

- `delegation.read`
- `delegation.create`
- `delegation.revoke`

Grant **only** `ROLE-MATT`. Delete any other role grants. Live seeded `core_delegations` count = **0**.

---

## Service — `scripts/core/delegation.py`

### create_delegation(...)
- verified_person_id only (client cannot forge delegator/delegate)
- This slice: creator must be delegator **or** PERS-MATT
- delegator != delegate
- Both assignments ACTIVE, belong to named persons, end_at NULL
- entity exists; scope exists and is bound to delegator assignment covering entity (reuse scope cover helpers)
- permission ACTIVE; **delegator** must `rbac.evaluate` ALLOW for permission_code in target context of entity/scope
- If `delegated_cap_amount` set: currency required; amount >= 0; delegator must `within_authority` for at least that amount (temp fixtures only on live=0 world → create of capped spend grants on live without fixtures must fail closed — OK)
- If permission is `approval.decide` or amount-bearing approve codes used in tests: require cap when tests use spend; for `approval.decide` alone without amount, cap may be NULL
- Refuse if `allow_redelegation` != 0
- Refuse if attempt to set basis from another delegation (no field for parent — simply no re-delegate API)
- Audit `delegation.created`
- Optional WI link: create does not grant power

### revoke_delegation(...)
- verified = delegator or Matt; need `delegation.revoke`
- PENDING uses: status → REVOKED; history kept
- Audit `delegation.revoked`

### get / list
- Scope visibility like approvals (entity visible to person)
- Lazy expire/activate on read

### evaluate_delegation(person_id, permission_code, target_context, amount_context=None) → dict
Return structure:
```
{
  "allowed": bool,
  "reason": str,
  "delegation_id": str|None,
  "delegator_person_id": str|None,
  "effective_cap_amount": str|None,
  "currency": str|None,
}
```

Fail-closed checks at **use** time:
1. Person is delegate on a row that is ACTIVE (after lazy)
2. permission_code matches
3. entity_id matches target entity; scope covers target (brand/loc/dept) — no widen
4. Delegate still ACTIVE assignment (= delegate_assignment_id)
5. Delegator still ACTIVE assignment (= delegator_assignment_id)
6. Delegator **still** holds native RBAC for permission in that target (if lost → deny)
7. If amount present: effective_cap = min(delegated_cap if set, delegator’s within_authority threshold); amount must be ≤ effective_cap; if delegated_cap NULL and amount required by within_authority path → deny missing_cap or fall through to within_authority on **delegator** then compare
8. No re-delegation path

### effective_permission(person_id, permission_code, target, amount=None)
- If native `rbac.evaluate` allows → NATIVE
- Else if `evaluate_delegation` allows → DELEGATION
- Else deny

---

## Approval integration (`scripts/core/approvals.py` `_decide`)

Replace bare RBAC-only gates for `approval.decide` and `required_permission_code` with:

1. Try native RBAC for each permission.
2. If denied, try `evaluate_delegation` for that permission + target (+ amount for required spend permission / material approve).
3. If either permission only held via delegation, set basis DELEGATION (if both native → NATIVE; if mix, prefer DELEGATION if any leg used delegation — record the delegation_id used for the required_permission leg, else decide leg).
4. Self-approval still compares **verified** to `requested_by_person_id` (blocks laundering).
5. Authority for material APPROVE:
   - Native: existing `within_authority(verified, …)`
   - Via delegation: amount must pass `evaluate_delegation` cap rules (delegator capacity ∩ grant cap). Do **not** call within_authority as if delegate owned the limit unless they natively do.
6. Decision row: `decided_by_person_id=verified` always; fill `authority_basis_*`.
7. Audit `delegation.used` on success via delegation; `delegation.denied` on failed attempt that cited delegation.

Do **not** change Person/Auth modules.

---

## HTTP (`serve_beta.py`) — minimal

| method | path | perm |
|--------|------|------|
| POST | `/api/core/delegations` | delegation.create |
| GET | `/api/core/delegations` | delegation.read |
| GET | `/api/core/delegations/{id}` | delegation.read |
| POST | `/api/core/delegations/{id}/revoke` | delegation.revoke |

Identity from verified binding only. Client `delegator_person_id` / `delegate_person_id` ignored unless equal verified where required; prefer body fields for **other** party only with server-side checks.

Honesty flags: `redelegation: DENIED`, `impersonation: BLOCKED`.

---

## Migration

`014_delegation.sql` + `migrate_delegation.py`
- Create table + indexes
- Alter approval decisions columns (SQLite: table rebuild if needed — keep append-only triggers)
- Seed Matt-only perms
- Refuse if live `org_authority_limits` != 0
- Live delegations must be 0 after migrate
- Idempotent
- Beta-os only; refuse wolf-system / Production

---

## Tests — `scripts/tests/test_delegation.py` (temp DB only)

Mandatory (map 1:1 where possible):

1. valid delegation create + ACTIVE in window
2. wrong Entity denied at evaluate
3. wrong Scope denied
4. Permission not held by delegator → create denied
5. delegate without valid Assignment → create/evaluate denied
6. before effective_from → denied
7. after effective_to → expired denied
8. revoked → denied
9. delegator inactive Assignment → evaluate denied
10. delegate remains real authenticated Person (forged delegate id refused)
11. no identity impersonation (decision actor = delegate)
12. client cannot forge delegator
13. client cannot forge delegate
14. cannot delegate more Authority than held
15. delegated cap enforced
16. delegator Authority expiry/invalid → evaluate denies (remove/expire fixture limit on temp)
17. re-delegation denied
18. approval through valid delegation succeeds (temp Authority fixtures)
19. approval above delegated cap denied
20. Approval Decision records actual delegate + DELEGATION basis
21. delegation does not bypass self-approval (requester==decider still 403)
22. audit provenance (created/used/denied/revoked)
23. live Authority Limits remain 0
24. live audit count unchanged by tests
25. live seeded delegations = 0
26. migration idempotent
27. Production path refused

Isolate like approval engine: `WOLF_TEST_MODE`, temp copy DB, patch module CATALOG_DB paths.

---

## Docs

Update `docs/canon/DELEGATION.md` honesty → BUILT+TESTED after land.  
Append ## Build record (backup SHA, counts, tests).  
Update Approval canon one line: Delegation = BUILT (evaluator) when done.

---

## Do NOT build

UI, marketplace, auto holiday, escalation, dual approval, SoD engine, recurring, AI delegate, live Authority thresholds, re-delegation, Person/Auth changes.

---

## Commit + report

One commit: `feat(core): add deterministic delegation`  
End CLEAN. No remote.

Cursor end report must include: backup path+SHA, live auth=0, live delegations=0, audit unchanged, test pass/fail, files touched.

## Final Matt block keys (Peaches fills after Grok re-review)

See Matt message — include APPROVAL GROK REVIEW GAP: CLOSED and DELEGATION fields.

