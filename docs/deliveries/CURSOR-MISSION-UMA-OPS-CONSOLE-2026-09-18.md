# CURSOR MISSION — BZG / Uma Blu operations console, first vertical

**Beta only.** Workspace `/Users/wolfterminal/beta-os`.
**Do not** write Production, ESB, ClickUp, Telegram, bank, Alchemist sheets, or Notion.
**Do not** edit the Model C ledger, scoring rules, or the Progress dashboard.
**Do not** grant Devi or any live staff a seat. **Do not** restart the running server.

## Discovery (already done — do not reopen it)

Authorised sources read 18 Sep 2026:

- Daily Close is built. `scripts/core/venue_close.py`, `scripts/core/esb_close_snapshot.py`, page `dashboards/uma-blu-close.html`, route rewrite in `scripts/serve_beta.py` around `/uma-blu-close`. Canon `docs/canon/UMA-BLU-DAILY-CLOSE.md`. Commits `909954d` and nits `4259d31`.
- ESB is read-only. Variance policy rows are 0. Non-zero variance is `VARIANCE_REQUIRES_POLICY`. Do not invent a threshold. Do not invent a closer. `ROLE-BZG-HFB` may resolve and verify exceptions only. It may not submit a close.
- Purchase flow today is Telegram plus `wolf-system/scripts/bzg-pr-submit.py`, `bzg-pr-approve.py` (this one writes ClickUp — do not call it), and `bzg-pr-push-esb.py` (do not call it).
- Petty cash script exists at `wolf-system/scripts/bzg-petty-cash.py`. Opening float is NOT FOUND. Do not read it into this slice. Do not invent a float or a variance limit.
- Devi (Ni Putu Devi Parwati) is the ops lead in the 17 Sep discovery note. She is not in Beta `org_persons`. Do not insert her. Do not invent a cashier.
- Alchemist and Notion are transitional. Not the target store. ClickUp is not target architecture.
- Zayen owns the ledger, chart of accounts, tax, bank accounting, and statements. Do not add any of those.
- Core modules to call, not copy: `work_items.py` (`create_work_item`, `list_work_items`, `transition_status`), `approvals.py`, `evidence.py`, `audit.py`, `authority.py` (`within_authority`), `venue_close.py`.

**NO STOP BLOCKER.** Missing float and missing staff seats are gaps, not permission to invent them.

## First vertical

Build a real console, not a menu of empty pages.

Included:

1. BZG shell and Uma Blu operator shell.
2. Today.
3. PR to bill to payment-control, as an operational record.
4. Daily Close, by linking the existing close. Do not rebuild `venue_close.py`.
5. Issues.
6. History, read from the existing audit spine.

Not included:

- Petty cash page. A disabled "Petty cash — later" label is allowed. No route, no table, no number.
- Finance, venues list, procurement catalog, people admin. Disabled labels only. No fake pages.
- Payment execution, ESB write, bank write, supplier email, Telegram send.

## Navigation

Human words. Same Wolf chrome and font as `uma-blu-close.html`. Do not invent a brand colour. If you cannot find a hex already in a canon file, use the existing Wolf chrome only.

BZG (only rows that have a destination):

- Overview → `/bzg`
- Uma Blu → `/bzg/uma-blu`

Uma Blu:

- Today → `/bzg/uma-blu`
- PR and bills → `/bzg/uma-blu/bills`
- Daily close → existing `/uma-blu-close` (link, do not fork the page)
- Issues → `/bzg/uma-blu/issues`

Match the static-file rewrite style already used for `/uma-blu-close` in `scripts/serve_beta.py`.

## PR lifecycle

New Beta tables are allowed only for the operational PR record. Link `work_item_id`. Do not copy person, role, approval, evidence, or audit tables.

States, in order:

`REQUESTED` → `APPROVED` → `ORDERED` → `RECEIVED` → `BILL_RECEIVED` → `PAYMENT_REQUESTED` → `PAYMENT_APPROVED` → `PAID_CLAIMED` → `PAYMENT_VERIFIED` → `CLOSED`

Also `POLICY_REQUIRED` when a money step has no authority limit. Also `REJECTED` from `REQUESTED` only.

Rules:

- Request is not approval. Approval is not an order. Order is not receipt. Receipt is not a bill. A payment request is not a payment. A paid claim is not a verified payment.
- `PAYMENT_APPROVED` calls `authority.within_authority`. If no limit covers the amount, the transition fails and the record shows `POLICY_REQUIRED`. Do not invent a limit. Do not hard-code 5000000 or any other number.
- `PAID_CLAIMED` stores evidence that a human paid outside Wolf. It does not move money.
- `PAYMENT_VERIFIED` requires that evidence to have been verified through `evidence.py`. It is not a bank confirmation.
- Every transition appends an audit event via `audit.record_event`. No second history table.
- Expected value and currency are stored as given. Currency missing stays blank, not guessed.

Fields: PR id, venue `BZG-UMA`, requester label (fixture text, not a live person id), supplier name, purpose, expected value, currency, requested date, required-by date, quote evidence id if any, bill reference, payment evidence id, current state, work item id. Skip a field rather than invent a supplier master.

## Today

One screen. Cards in human language. No engineering ids on the card. The id can sit on the click-through.

Cards, only when the condition is true:

- PRs waiting approval
- Ordered, not received
- Bills waiting payment approval
- Payment claimed, not verified
- Daily close not started, blocked, exception, or verified (use `venue_close.list_closes` / `get_close`. Do not invent a closer name)
- Policy required (authority missing)

If a card's source is fixture data, the card says "Example".

Quiet cards are omitted. Do not show a zero count for a module that does not exist (petty cash, variance threshold).

## Issues

Exception rows only. Sources: PR records in `POLICY_REQUIRED` or missing evidence, and venue-close exceptions already opened by `venue_close`. No alert from an unknown threshold.

## History

Timeline from `audit.list_events` for these objects. Human sentence. No new store.

## Data

Seed at most 3 fixture PRs, each marked `example: true`, covering waiting approval, policy required, and paid-claim unverified. The page must say they are examples.

Do not import Alchemist, Notion, or Telegram rows.
Do not write the live close database except through existing test-safe paths. Today may read the Beta close if the path guard allows. If the live close DB is not safe to read, show "Close not loaded" rather than fake sales numbers.

## Tests

`scripts/tests/test_uma_ops_console.py`.

Prove:

- request does not equal approval
- money step with no authority limit becomes `POLICY_REQUIRED`, not approved
- paid claim does not set verified
- no write helpers toward ESB, ClickUp, bank, or Telegram
- Today hides engineering ids and labels fixtures
- Issues stay empty when nothing is wrong
- existing `test_uma_blu_daily_close.py` still passes

## Commit

Only this slice's files. Do not `git add -A`.

End the log with:

```
COMMIT: <hash>
TESTS: PASS=<n> FAIL=0
ROUTES: /bzg /bzg/uma-blu /bzg/uma-blu/bills /bzg/uma-blu/issues
EXIT:0
CURSOR_DONE
```

If you would need to invent a float, a threshold, a person, or a ledger account to finish, stop and print `EXIT:1` plus the missing fact. Do not invent it.
