# APPROVAL ENGINE — honesty table (Beta transitional)

**Status:** BUILT+TESTED on Beta (`build/wolf-command-rebuild`) — 2026-09-17  
**Lock:** Live Authority Limits remain **0** until Matt approves business authority policy.

| Capability | Status |
|------------|--------|
| Approval Request + Decision models | BUILT |
| REQUESTED ≠ APPROVED ≠ EXECUTED | BUILT (approve does not execute source; WI complete ≠ approve) |
| Self-approval default deny (flag) | BUILT (`BETA_APPROVAL_DENY_SELF_APPROVAL=1` default) |
| SPEND/EXCEPTION require amount+currency at create; APPROVE always runs `within_authority` when material | BUILT (APR-RT-001) |
| Matt-only `approval.*` permissions | BUILT (live seed) |
| Linked `APPROVAL_REQUIRED` Work Item | BUILT (optional; complete/verify does not approve) |
| Dual approval orchestration | NOT BUILT |
| Delegation / SoD engine | NOT BUILT |
| Approval UI | NOT BUILT |
| AI / LLM approver | NOT BUILT |
| Live Authority policy | NOT CONFIGURED (`org_authority_limits` seeded live = 0) |

## Path

```
Person → Assignment → Role → Permission (WHAT: approval.decide + required_permission_code)
                           ↘ Scope (WHERE: owning_entity + brand/loc/dept)
                           ↘ Authority Limit (HOW MUCH: within_authority on material approve)
                           ↘ Approval Request/Decision (specific decision evidence)
```

Authority = capacity. Approval = specific decision evidence. Approval never creates Authority.

## Tables

- `core_approval_requests` — PENDING → APPROVED|REJECTED|CANCELLED|EXPIRED  
- `core_approval_decisions` — append-only APPROVED|REJECTED (failed attempts = audit only)

## APIs

| method | path | perm |
|--------|------|------|
| POST | `/api/core/approvals` | approval.request |
| GET | `/api/core/approvals` | approval.read |
| GET | `/api/core/approvals/{id}` | approval.read |
| POST | `/api/core/approvals/{id}/approve` | approval.decide |
| POST | `/api/core/approvals/{id}/reject` | approval.decide |
| POST | `/api/core/approvals/{id}/cancel` | approval.cancel |

Requester / decider from verified identity only — client `requested_by_*` / `decided_by_*` ignored.

## Audit actions

`approval.requested` · `approval.decide_attempt` · `approval.granted` · `approval.rejected` · `approval.cancelled` · `approval.expired` · `approval.authority_denied` · `approval.self_denied`

## Isolation

Tests run on **temp DB copy** only. Fixture Authority Limits + `PERM-TEST-SPEND` activated on temp only. Live `org_authority_limits` = 0; live approval rows = 0; live audit count must not rise from tests.

Locked ★ 17 Sep 2026 — `build/wolf-command-rebuild` only.
