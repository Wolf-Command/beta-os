# GROK PLAN — Devi BZG F&B Operations Lead (RBAC + receive + close ops) — 2026-09-19

## Class
NEW CAPABILITY (role/assignment/permissions) — Owner-authorised. Grill: Owner Decision Memory `DEC-DEVI-BZG-FB-OPS-LEAD-2026-09-19` is the grill/authority. No Matt re-ask for individual F&B ops perms.

## Decision
Owner: Devi = **BZG F&B OPERATIONS LEAD**. Full BZG F&B operational access.  
`OPERATIONAL ≠ UNLIMITED MONETARY / BANK / GOVERNANCE`.

## Must NOT
- Resurrect ENDED `SCOPE-BZG-ENTITY` on `ASG-DEVI-HFB-UMA-1` (history preserved; ENDED-scope protection intact)
- Hard-code `PERS-DEVI` exceptions in app logic
- Grant GGV / AMG / Wolf admin / Crown Jewels / payment_approve / bank / accounting / tax / Owner
- Invent monetary limits or independent verifier person
- Interrupt / rewrite Haikal content work
- Touch Production / WIP four / Alchemist writes

## Build (canonical path)
1. **Permission audit** (document in delivery): map existing BZG/F&B org_permissions → GRANT / SEPARATE AUTHORITY / DENIED.
2. Create/ensure org permission codes (ACTIVE) including at least one discoverable receive code matching `uma_devi_p0.discover_receive_permission` (`venue.receive` or `bzg.pr.receive` preferred).
3. Create role `ROLE-BZG-FB-OPS-LEAD` display **"BZG F&B OPERATIONS LEAD"** (or rename/alias carefully — prefer new role).
4. Grant role (ALLOW):
   - work.read/create/update/complete/assign (ops Work Items)
   - evidence.record.read/submit
   - venue.close.read + **venue.close.submit** (PERFORM/SUBMIT)
   - venue.receive / bzg.pr.receive (new)
   - venue.close.resolve_exception if ops-appropriate
   - Do **NOT** grant: venue.close.verify (independent verify separated), bzg.pr.payment_approve, progress.read, approval.decide, test.spend
5. Scope: create `SCOPE-BZG-FB` (or venue-set scope covering Uma now, extensible) — **not** entity-wide resurrection. Keep `SCOPE-BZG-UMA` ACTIVE for Uma APIs until FB scope is wired into `_require_uma_ops` equivalently.
6. New Assignment `ASG-DEVI-FB-OPS-1` Person PERS-DEVI → ROLE-BZG-FB-OPS-LEAD → scopes (FB + UMA as needed). Leave old HFB assignment history; may END Uma-only HFB assignment **only if** new assignment fully covers ops — prefer keep HFB inactive/ended cleanly without resurrecting ENTITY.
7. Today UX: if authenticated F&B Ops Lead can act → give action (not "Needs staff"). Waiting on [role] / Policy required when true.
8. Close UX: show perform/submit for Ops Lead; keep verify hidden/denied unless separate role.
9. Receive Goods: available when role has receive; partial/complete/evidence semantics already in `uma_devi_p0`.
10. Tests: fixture RBAC + PERS-DEVI prove; ENDED ENTITY stays ENDED after migrate; anon 403; payment_approve still 0 for Devi; receive allow for Ops Lead.

## Prove bar → notify
**DEVI F&B ACCESS READY TO RETEST** with: role, scope, permissions, receiving, close, deliberately denied, tests, deployed proof.

## After DONE
Update CR (resolve engineering items only with evidence). Auto close_slice → next (`model-c-evidence-recon`). Mission continues — do not wait for Devi human retest.
