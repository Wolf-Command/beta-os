# P5 — Uma Blu daily operating loop — 27 Sep 2026

Decision served: 2026-09-24 People Are Not Roles, on the existing Uma Blu close and Wolf Core work items. Not a new venue vertical. Not a new task database.

ENGINEERING PASS. Not staff ready. Not human commissioned.

Target label UMA BLU DAILY OPERATIONS — READY FOR HUMAN COMMISSIONING is not earned tonight.

Production `:8787` stayed on pid 15975 (`serve.py`). Beta `:8788` was restarted with `launchctl kickstart -k` on `net.wolfcommand.serve-beta` only. It came back as pid 4443, `scripts/serve_beta.py`. No money, bank, or payment action. No NAS write. No ESB write. No external send.

## BEFORE

Uma Blu already had a phone-width Today page, daily close, issues, bills, petty cash, purchase requests, and a loop from variance to an exception work item. The Today page also showed engineering boards (Needs-You connective, loop stages, operator depth, stock and bill consequence, manager and owner strips) in the same scroll as the shift.

- Devi is seated as BZG F&B Operations Lead (`ROLE-BZG-FB-OPS-LEAD`, `ASG-DEVI-FB-OPS-1`) on `SCOPE-BZG-FB` and `SCOPE-BZG-UMA`. Both scopes still target Uma Blu only. That was not widened. The role can submit a close and receive goods. It cannot verify a close, approve payment, or move money.
- `ROLE-BZG-CLOSER` (Venue Closing Operator) exists with close-submit and evidence read. No person is assigned to it. That is the floor seat for counting the till. A new floor role was not created.
- Live `venue_close_variance_policies` stays 0. A till that does not match ESB cash cannot be accepted. It stops at `VARIANCE_REQUIRES_POLICY` until someone opens an exception. No policy was invented to get a green close.
- ESB remains read-only. The close stores a snapshot. Wolf owns the close, the cash-count evidence, the variance, the exception, and who can see it.
- My Work from Pack 3/4 already lists Wolf Core work items. The close exception already creates one `core_work_items` row for the F&B lead assignment. There was no phone path that said so in plain language, and no single test that walked close → variance → exception → owner visibility.

## BUILT-REPAIRED

- The Uma day nav is the same on Today, Daily Close, Issues, Bills, the purchase detail, petty cash, Evidence, and Exceptions: Today, Daily Close, Issues, Bills, Purchasing, Evidence, Exceptions, My Work, Petty cash. Purchasing opens the existing bills page. My Work is `/my-work`. It is not a second task list.
- Evidence reads cash-count and exception-note ids already stored on `venue_daily_closes`. Empty copy: "No close evidence recorded in Wolf yet." Amounts are not repeated there.
- Exceptions reads the existing exception strip. A close exception links to the same work item in My Work.
- Today still leads with "What do I need to do now?" The engineering boards stay in the page for the older tests and are hidden from the shift view.
- The sentence at the top comes from capabilities, not from a person's name. The operations lead sees "You run the day's operations. You cannot pay or change a bank." The closing operator sees "You count the till and record the day. You cannot pay, change a bank, or verify your own close."
- `staff_ready` and `human_commissioned` stay false.

## VERIFIED

```
python3 scripts/tests/test_uma_daily_loop_finish.py
prod pid 15975
beta pid 2734
PASS=44 FAIL=0
EXIT: SUCCESS
```

The first run failed the phone checks because the catalog pointer was left on a deleted temporary database. That was repaired. The second run is the one above. The close chain used a copy of the catalog and a temporary ESB file dated 2099-01-15. Declared cash 150000 against ESB cash 200000 became variance -50000 and state `VARIANCE_REQUIRES_POLICY`. That state did not appear on the owner strip. Opening the exception moved the close to `EXCEPTION`, created a work item, and the owner strip then contained that date. The operations lead's My Work today list contained the same item. The temporary ESB file bytes did not change. Live variance-policy count and live close count were the same after the run. The temporary closing operator was removed. `PERS-P5-CLOSER` is not in `org_persons`.

Headless Chrome at 390px, through the Beta handler on an ephemeral port with a development subject header:

- Operations lead on Today: the operations sentence, Daily Close, My Work, hidden engineering record, sideways-scroll marker `no`.
- Same lead on Evidence: "No close evidence recorded in Wolf yet."
- Same lead on Exceptions: the Exceptions page, My Work link, sideways-scroll marker `no`.
- Closing operator on Today: "You count the till", and the same payment boundary.

Related suites after that repair:

```
python3 scripts/tests/test_bzg_fb_today_ops_polish.py
PASS=71 FAIL=0

python3 scripts/tests/test_uma_today_commissionable.py
PASS=33 FAIL=0

python3 scripts/tests/test_bzg_loop_closure.py
PASS=117 FAIL=0

python3 scripts/tests/test_bzg_operator_depth.py
PASS=84 FAIL=0

python3 scripts/tests/test_bzg_ops_needs_you_connective.py
PASS=165 FAIL=0
```

These two suites already failed on the committed tree before this pack (the strings they require are absent from `HEAD` as well). They were not repaired tonight:

```
python3 scripts/tests/test_uma_petty_cash.py
PASS=50 FAIL=3
ops no write helper esb_write
petty page float NOT FOUND copy
test_uma_ops_console still passes (that file fails on the same esb_write term)

python3 scripts/tests/test_wolf_bzg_uma_nav.py
PASS=110 FAIL=1
serve legacy uma-blu redirect
```

The nav HTTP checks still passed, including anon 403 on `/bzg/uma-blu`. The legacy `/uma-blu` route is not a 404. The one failure is a source-string check against `scripts/serve_beta.py`.

Live Beta after the restart, unsigned:

```
curl -sS -D - http://127.0.0.1:8788/bzg/uma-blu
HTTP/1.0 403 Forbidden
{"ok": false, "error": "missing_auth", "message": "Cf-Access-Jwt-Assertion required. Local :8788 without Cloudflare JWT is denied (fail-closed).", "required_permission": "venue.close.read"}

curl evidence, exceptions, and /api/bzg/uma-blu/evidence
403
403
403
```

Listeners after the restart:

```
Python 15975 127.0.0.1:8787  serve.py
Python 4443  127.0.0.1:8788  scripts/serve_beta.py
```

`scripts/serve_beta.py` and `scripts/core/uma_ops_console.py` already held large unrelated uncommitted diffs, so those two files were left unstaged. The evidence route, the exception work-item link, and the Today seat line are in that working tree and on the restarted Beta process. `scripts/core/uma_devi_p0.py` and `dashboards/bzg-uma-blu.html` were already dirty as well and were left unstaged for the same reason. The seat sentence and the hidden engineering record are in those working copies.

## STAFF READY?

NO.

A person who can sign in through Cloudflare on `:8788` was not proven tonight. The development subject header is ignored on that listener. The live Evidence page is empty. There is no assigned closing operator, and there is no authorised variance policy, so a real mismatched till cannot be finished. It can be recorded as an exception and shown to the operations lead and the owner strip. That path was proven on a temporary database, then removed. Shell sign-in was not switched.

## HUMAN COMMISSIONED?

NO

## BLOCKERS

- BLOCKER: `ROLE-BZG-CLOSER` has no live person. The phone proof used a temporary seat on that existing role and `SCOPE-BZG-UMA`, then deleted it. A real closing operator has to be assigned by a human.
- BLOCKER: live variance policies are still 0. Non-zero variance is not accepted. No policy was added to make a close look finished.
- BLOCKER: `:8788` role screens need a Cloudflare sign-in. Development subject headers are ignored there.
- BLOCKER: `SCOPE-BZG-FB` and `SCOPE-BZG-UMA` still target Uma Blu only. Other BZG venues were not added.
- BLOCKER: the operations lead cannot verify a close and cannot pay. Those denials were left in place.
- Pre-existing, not introduced tonight: petty suite looks for the words "NOT FOUND" and forbids the term `esb_write` in the ops console; the nav suite looks for a `"/uma-blu"` string inside `serve_beta.py`. Both miss on `HEAD`.

## NEXT HUMAN TEST

1. Sign in on Beta `:8788` as the BZG F&B Operations Lead. Open `/bzg/uma-blu` on a phone. The first line should say you run the day's operations and cannot pay or change a bank. The links should be Today, Daily Close, Issues, Bills, Purchasing, Evidence, Exceptions, My Work, and Petty cash.
2. Open Daily Close. Pull ESB for a day that has sales. Enter the cash actually counted. If it matches, the close can verify only from a separate role. If it does not match, the screen should stop and say a policy is required. Do not expect it to accept the difference.
3. Open the exception from that close. Sign in again as the operations lead. The same item should be on `/my-work` and under Exceptions, with a link into My Work. The owner strip for that date should list it. No payment button should appear.
4. Assign a real person to Venue Closing Operator (`ROLE-BZG-CLOSER`) on the Uma scope. Sign in as that person. Today should say they count the till, and that they cannot pay, change a bank, or verify their own close.
5. Confirm Evidence is empty until a cash count has been submitted, and that the sentence says so.

## FOUNDER DEPENDENCY

- Counting the till: ELIMINATE. The closing-operator role submits the count. Matt is not the counter. Seating a real person on that role is still a human step.
- Reading ESB sales into the close: AUTOMATE. The snapshot is read-only. Wolf does not write ESB.
- Non-zero variance: RETAIN. With no authorised policy, the close stops. This pack does not add a Matt approval, and it does not invent a threshold, to make the close green.
- Opening the exception: ELIMINATE. The work item is owned by the active F&B lead assignment for the venue, not by a person's name.
- Seeing it: AUTOMATE. After the exception exists, the owner strip and the lead's My Work read the same work item.
- Verifying the close: RETAIN. Verify stays on a separate role. The operations lead and the closer are not given it.
- Payment and bank changes: RETAIN. Those controls stay off this screen.

RESULT: PASS
