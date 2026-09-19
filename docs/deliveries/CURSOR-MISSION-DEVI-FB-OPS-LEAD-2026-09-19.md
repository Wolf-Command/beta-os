# CURSOR MISSION — Devi BZG F&B Operations Lead — 2026-09-19

**Decision:** `DEC-DEVI-BZG-FB-OPS-LEAD-2026-09-19`  
**Lane:** Beta `:8788` only. Production `:8787` not touched.  
**Result:** DEVI F&B ACCESS READY TO RETEST

Devi (`PERS-DEVI`) is **BZG F&B OPERATIONS LEAD**. Operational access is not payment, bank, or Owner access.

## Permission audit

Existing BZG / F&B / work / evidence / close codes, plus the receive code this slice created. Classification is what `ROLE-BZG-FB-OPS-LEAD` does with them.

| Code | Class | Why |
| --- | --- | --- |
| work.read | GRANT | Ops work items |
| work.create | GRANT | Ops work items |
| work.update | GRANT | Ops work items |
| work.complete | GRANT | Ops work items |
| work.assign | GRANT | Ops work items |
| evidence.record.read | GRANT | Evidence on ops actions |
| evidence.record.submit | GRANT | Evidence on ops actions |
| venue.close.read | GRANT | Read the close |
| venue.close.submit | GRANT | Perform / submit the close |
| venue.close.resolve_exception | GRANT | Resolve an ops exception |
| venue.receive | GRANT | New ACTIVE code. `discover_receive_permission` finds it |
| venue.close.verify | SEPARATE AUTHORITY | Independent verifier. Not granted |
| work.verify | SEPARATE AUTHORITY | Not granted |
| bzg.pr.payment_approve | DENIED | Exists. Not granted. Payment stays with finance |
| progress.read | DENIED | Owner / `ROLE-MATT` only |
| approval.decide | DENIED | Not an F&B ops grant |
| approval.request / approval.read / approval.cancel | DENIED | Not granted |
| evidence.requirement.manage | DENIED | Not granted |
| test.spend.approve | DENIED | INACTIVE test code. Not granted |
| GGV / AMG / Wolf admin / Crown / bank / accounting / tax / Owner | DENIED | No grant. No new permission invented |

## What landed

- Role `ROLE-BZG-FB-OPS-LEAD`, display **BZG F&B OPERATIONS LEAD**
- Assignment `ASG-DEVI-FB-OPS-1` → `PERS-DEVI`, scopes `SCOPE-BZG-FB` (Uma brand, extensible) and `SCOPE-BZG-UMA`
- Old `ASG-DEVI-HFB-UMA-1` is **ENDED** so close verify is not inherited. Its scopes were not rewritten
- `SCOPE-BZG-ENTITY` on that old assignment stays **ENDED** at `2026-09-19T13:43:22+08:00`. Daily-close seed no longer revives an ENDED assignment
- Uma APIs accept `SCOPE-BZG-UMA` or `SCOPE-BZG-FB`
- Today: if this person can act, the chip is **You can act** (not Needs staff) and the link stays. Otherwise **Waiting on [role]** or **Policy required**
- Close: perform / submit buttons show when `venue.close.submit` is allowed. Verify stays hidden and the note says it is a separate role
- Receive: the goods form shows when the role has `venue.receive`. Partial / complete / evidence behaviour is unchanged. No Alchemist write

## Deliberately denied for PERS-DEVI

`bzg.pr.payment_approve`, `venue.close.verify`, `progress.read`, `approval.decide`, `test.spend.approve`. Anonymous receive is 403.

## Prove

- `python3 scripts/tests/test_devi_fb_ops_lead.py` → `PASS=60 FAIL=0`
- `python3 scripts/tests/test_devi_feedback_p0.py` → `PASS=63 FAIL=0`
- `python3 scripts/tests/test_devi_uma_commission_auth.py` → `PASS=28 FAIL=0` (submit allowed, verify and payment denied, Progress 403)
- `python3 scripts/tests/test_ended_scope_no_resurrect.py` → `PASS=16 FAIL=0`
- `python3 scripts/tests/test_uma_blu_daily_close.py` → `70 passed, 0 failed`
- `:8788` Today and Close pages return 200. Anonymous receive and capabilities return 403. `:8787` still listening
- WIP four hashes unchanged. No Alchemist write

Human phone retest is still open (`CR-0fc49fa643fb2c26` stays `WAITING_HUMAN`). Engineering items `CR-72f388f568c4d100` and `CR-5ef9e1221c325bb1` are resolved from this proof.

Signed-in phone click-through was not run here. Cloudflare Access blocks an anonymous browser session. The capability tests above are the proof that Devi can receive and submit, and cannot pay or verify.
