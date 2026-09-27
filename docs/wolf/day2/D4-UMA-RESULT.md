# D4 — Uma Blu close ready for commissioning — 27 Sep 2026

Extends the existing Uma Blu close and Wolf Core work items. Decision already on that path: 2026-09-24 People Are Not Roles. Not a new module.

TECHNICAL PROOF, DEPLOYED ROUTE PROOF, STAFF READINESS, HUMAN COMMISSIONING, and OPERATING ADOPTION stay separate below.

Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 4443 (`scripts/serve_beta.py`). It was not restarted. No money, bank, or payment action. No NAS write. No person was left seated on the closer role. Human commissioned: no.

## BEFORE

The two named suites were already red on the prior pack record (`docs/wolf/sprint7/P5-UMA-RESULT.md`: petty PASS=50 FAIL=3, nav PASS=110 FAIL=1). This session did not re-run them before the patch. The failing assertions and the source were read directly.

Petty, three failures, one cause family:

- `ops no write helper esb_write` scans `scripts/core/uma_ops_console.py` for the substring `esb_write`. The file contains `"esb_write": False`, `def refuse_esb_write`, and `code="esb_write_refused"`. Those are the off-flag and the refusal. `test_bzg_loop_closure.py` requires both. A substring ban and that contract cannot both be true.
- `test_uma_ops_console still passes` runs that suite as a child. It uses the same substring ban, so the child was red for the same term.
- `petty page float NOT FOUND copy` requires the words `NOT FOUND` in the petty HTML. The static banner had been rewritten to "Opening cash balance needed…" and no longer contained those words. The API still returned `float_status` `NOT_FOUND`. The 2026-09-18 petty mission requires the UI to say NOT FOUND when the float is absent, and not to show 0.

Nav, one failure:

- `serve legacy uma-blu redirect` requires the literal `"/uma-blu"` inside `scripts/serve_beta.py`. The 2026-09-22 route merge moved that path to `scripts/core/wolf_shell.py` `LEGACY_UMA_REDIRECTS` (`"/uma-blu": "/bzg/uma-blu"`). `serve_beta.py` already sends `302` with `Location` from `route_merge_redirect_target`. The same nav file's HTTP check was the runtime proof and was not the failing line.

Closer: `ROLE-BZG-CLOSER` active assignments 0. `venue_close_variance_policies` 0. `PERS-P5-CLOSER` was not in `org_persons`. Daily Close honesty on the page printed `live_variance_threshold: 0`, which is the policy count, not a sentence that no policy is set.

## DONE

- Petty and ops-console checks still forbid `clickup`, `telegram`, `push_esb`, `bank_write`, and `write_to_bank` as substrings. For `esb_write` they now fail unless `refuse_esb_write` exists, the flag is not true, and every remaining `esb_write` token is the false flag, the refusal function, or `esb_write_refused`. That is the loop-closure contract. The assertion was not deleted.
- The petty banner says "Opening float NOT FOUND" and keeps "Opening cash balance needed".
- The nav source check now requires the redirect row in `wolf_shell.py` and the `Location` send in `serve_beta.py`. The HTTP check is unchanged.
- Daily Close, phone width, says "No variance policy set" when `live_variance_threshold` is 0, says the closer seat is waiting when that is the honesty value, and links a variance stop and an exception to My Work. No policy row was inserted. No closer was assigned by this pack.
- Checklist: `docs/wolf/day2/UMA-CLOSE-COMMISSIONING-CHECKLIST.md`.

### TECHNICAL PROOF

The close chain and the 390px pages ran in `test_uma_daily_loop_finish.py` on a temporary catalog and a temporary ESB file. Live policy count and live close count were unchanged. The suite's own temporary closing operator was removed before exit.

### DEPLOYED ROUTE PROOF

Unsigned on pid 4443. Today, exceptions, My Work, the today API, close capabilities, and the variance list are 403. `/uma-blu` is 302 to `/bzg/uma-blu`. The close HTML and the petty HTML are 200 and contain the new sentences. `/api/venue-close/honesty` is 200 and reports threshold 0, monetary authority 0, settlement UNAVAILABLE, closer waiting, closer assignments 0. That honesty route was already open; this pack did not add a grant.

### STAFF READINESS

NO. A Cloudflare session as Devi was not opened on `:8788`. The development subject header is ignored there. The phone proof used an ephemeral handler.

### HUMAN COMMISSIONING

NO. Not marked. The closer role is unseated. No variance policy was written.

### OPERATING ADOPTION

NO. No live till was counted. No exception was opened on the live catalog.

## VERIFIED

Listeners before and after: pid 15975 on `:8787`, pid 4443 on `:8788`.

```
python3 scripts/tests/test_wolf_bzg_uma_nav.py
PASS=111 FAIL=0
EXIT: SUCCESS
```

`GET /uma-blu` on the ephemeral handler was 302, not 404.

```
python3 scripts/tests/test_uma_petty_cash.py
PASS=53 FAIL=0
```

Includes the child checks that `test_uma_ops_console` and `test_uma_blu_daily_close` still pass.

```
python3 scripts/tests/test_uma_daily_loop_finish.py
prod pid 15975
beta pid 4443
PASS  lead-close shows No variance policy set
PASS  lead-close links My Work
PASS  lead-close no sideways scroll
PASS  temporary closer removed
PASS=47 FAIL=0
EXIT: SUCCESS
```

Headless Chrome window `390,844`. The other phone rows in that file also passed (Today, Evidence, Exceptions, temporary closer Today).

```
python3 scripts/tests/test_uma_ops_console.py
PASS=24 FAIL=0

python3 scripts/tests/test_uma_blu_daily_close.py
70 passed, 0 failed

python3 scripts/tests/test_uma_legacy_projection.py
PASS=48 FAIL=0

python3 scripts/tests/test_uma_today_commissionable.py
PASS=33 FAIL=0

python3 scripts/tests/test_devi_feedback_p0.py
PASS=63 FAIL=0

python3 scripts/tests/test_devi_fb_ops_lead.py
PASS=60 FAIL=0

python3 scripts/tests/test_bzg_fb_today_ops_polish.py
PASS=71 FAIL=0

python3 scripts/tests/test_bzg_loop_closure.py
PASS=117 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_bzg_operator_depth.py
PASS=84 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_bzg_ops_needs_you_connective.py
PASS=165 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_bzg_mgmt_cluster.py
PASS=111 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_bzg_ops_pack.py
PASS=56 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_bzg_bom_yield.py
PASS=272 FAIL=0

python3 scripts/tests/test_bzg_allocation_engine.py
PASS=268 FAIL=0

python3 scripts/tests/test_bzg_variance_waste.py
PASS=267 FAIL=0

python3 scripts/tests/test_bzg_venue_pnl.py
PASS=261 FAIL=0

python3 scripts/tests/test_bzg_reputation_observe.py
PASS=112 FAIL=0
```

Pre-existing red, not repaired (the named repair was the petty and nav suites; this assertion was not changed):

```
python3 scripts/tests/test_devi_uma_commission_auth.py
FAIL  Devi payment route 403 — 403 payment_execution_refused
PASS=27 FAIL=1
```

The check wants HTTP 403 and `error == "forbidden"`. The route returns 403 with `payment_execution_refused`. Payment stays refused. This pack did not edit that test or the payment handler.

Live `:8788` after the suites:

```
GET /bzg/uma-blu                         403 missing_auth
GET /uma-blu                             302 Location: /bzg/uma-blu
GET /uma-blu-close                       200  (body contains "No variance policy set", "Closer seat is waiting", My Work, Today, max-width 480px)
GET /bzg/uma-blu/petty                   200  (body contains "NOT FOUND" and "Opening cash balance needed")
GET /bzg/uma-blu/exceptions              403 missing_auth
GET /my-work                             403 Sign in required.
GET /api/bzg/uma-blu/today               403 missing_auth
GET /api/bzg/uma-blu/petty               403 missing_auth
GET /api/venue-close/capabilities        403 missing_auth
GET /api/venue-close/list?state=VARIANCE_REQUIRES_POLICY  403 missing_auth
GET /api/venue-close/honesty             200
```

Honesty body keys: `live_variance_threshold` 0, `live_monetary_authority` 0, `settlement_api` UNAVAILABLE, `closer_commissioning` `WAITING FOR VERIFIED CLOSING OPERATOR`, `closer_active_assignments` 0.

Catalog after the suites: closer active assignments 0, variance policies 0, `PERS-P5-CLOSER` count 0.

## WAITING HUMAN

- Seat a real person on `ROLE-BZG-CLOSER` / `POS-BZG-CLOSER-UMA-1`, or leave it empty. This pack did not choose a person.
- Authorise a variance policy, or leave the table empty. Empty is the current truth. No threshold was invented.
- Sign in on Beta as Devi and walk the checklist.

## BLOCKERS

- BLOCKER: `ROLE-BZG-CLOSER` has no live person. The phone suite's temporary seat was removed.
- BLOCKER: `venue_close_variance_policies` is 0. A mismatched till stops. It is not accepted.
- BLOCKER: `:8788` role screens for Today, Exceptions, and My Work need Cloudflare. The development subject header is ignored there.
- BLOCKER: verify stays off the operations lead and off the closer. Payment stays off.
- Pre-existing: `test_devi_uma_commission_auth.py` PASS=27 FAIL=1. The payment route's 403 code is `payment_execution_refused`, not `forbidden`.

## NEXT HUMAN TEST

Use `docs/wolf/day2/UMA-CLOSE-COMMISSIONING-CHECKLIST.md` on a phone, signed in as Devi.

1. Today states the operations boundary and links Daily Close and My Work.
2. Daily Close says no variance policy is set and the closer seat is waiting.
3. A cash count that does not match ESB stops. Opening the exception shows it on Exceptions and My Work. No payment control.
4. Petty cash says the opening float is NOT FOUND.
5. Do not mark this commissioned from that walk. A closer and a policy are still separate human decisions.

RESULT: PASS
