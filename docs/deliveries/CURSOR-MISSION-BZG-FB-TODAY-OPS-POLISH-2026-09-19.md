# CURSOR MISSION — BZG F&B Today ops polish — 2026-09-19

**Decision:** `DEC-DEVI-BZG-FB-OPS-LEAD-2026-09-19` (FIX of the started Uma Today system, not a new system)  
**Depends:** ROLE-BZG-FB-OPS-LEAD done `8e9e844`  
**Lane:** Beta `:8788` only. Production `:8787` not touched.  
**Result:** TODAY OPS POLISH READY

Ops Lead capabilities decide the Today affordance. If she can perform, the card shows the action. It does not say Needs staff. If she cannot, it says Waiting on a role or the one other active person, or Policy required. Close perform and submit stay visible. Verify stays a separate role.

## What landed

- `scripts/core/uma_devi_p0.py` — fixture capabilities attach `action` (`Receive goods`, `Perform close`, `Resolve exception`, `Open exception`). Verified and resolved closes do not offer verify on Today. Waiting copy uses a person name only when exactly one other active assignee holds the waiting role.
- `dashboards/bzg-uma-blu.html` — phone width 480, 44px action and nav, wraps under 420px. Chip stays You can act. The button is the verb.
- `dashboards/uma-blu-close.html` — perform/submit buttons stay `data-cap="submit"`. Verify renders only when `caps.verify`. Note says verify stays with a separate role. Figures stack on a phone.
- `scripts/tests/test_bzg_fb_today_ops_polish.py` — catalog copy fixture. Stripping submit or receive on that copy removes the action. No live write.

## Refused

Payment, bank, and Owner grants. ENTITY resurrect. Fake transactions. Alchemist writes. Production. Score / Model C edits. Devi human retest (`CR-0fc49fa643fb2c26` stays `WAITING_HUMAN`). WIP four not touched.

## Prove

- `python3 scripts/tests/test_bzg_fb_today_ops_polish.py` → `PASS=70 FAIL=0`
- `python3 scripts/tests/test_devi_fb_ops_lead.py` → `PASS=60 FAIL=0`
- `python3 scripts/tests/test_devi_feedback_p0.py` → `PASS=63 FAIL=0`
- `:8788` Today and Close return 200 and serve the new markup. Anonymous Today and receive stay 403.
- Beta `serve_beta.py` restarted (`launchctl kickstart` of `net.wolfcommand.serve-beta` only). `:8787` still listening.
- Signed-in phone tap-through was not run. That would be the parked human retest. CSS and the served HTML are the phone proof here.
